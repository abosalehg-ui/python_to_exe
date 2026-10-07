"""Compare mode: build one project with every engine, measure, recommend.

Each engine builds into its own folder, ``<output>/p2e_compare/<engine>``, so
the comparison never touches the real build. For each build the table holds
what was measured — never an estimate:

* size on disk of what the engine produced (file or folder);
* build time (wall clock of the engine's run);
* start-up time (``startup_bench``: median of several runs, with its method);
* the smoke-test result (run from a neutral folder);
* the features the project uses that the engine does not support.

The recommendation is derived from those numbers only, and every reason
behind it is returned, so the UI can show *why*.

UI-independent: callers pass callbacks for log lines and progress.
"""

import copy
import os
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

from py2exe_gui.core.build_runner import prepare_build, run_build
from py2exe_gui.core.diagnostics import build_root, diagnose_output
from py2exe_gui.core.engines import engine_names, get_engine
from py2exe_gui.core.fixes import Finding
from py2exe_gui.core.size_analyzer import path_size
from py2exe_gui.core.smoke_test import SmokeResult, run_from_neutral_folder
from py2exe_gui.core.startup_bench import (
    DEFAULT_RUNS,
    DEFAULT_TIMEOUT,
    METHOD_STILL_RUNNING,
    StartupResult,
    measure_startup,
)

COMPARE_DIR = "p2e_compare"

#: A start-up difference counts when the slower one takes at least this much
#: longer, relatively *and* absolutely (below ~50 ms nobody notices).
STARTUP_RATIO = 1.2
STARTUP_MIN_SECONDS = 0.05
#: A size difference counts from 20%.
SIZE_RATIO = 1.2


@dataclass
class EngineRun:
    """One engine's build of the project, and what was measured."""

    engine: str
    built: bool = False
    #: Why there is no build: finding codes ("engine_feature_unsupported"...).
    findings: List[Finding] = field(default_factory=list)
    error: str = ""
    build_seconds: float = 0.0
    output_path: str = ""
    size_bytes: int = 0
    smoke: Optional[SmokeResult] = None
    startup: Optional[StartupResult] = None
    unsupported: List[str] = field(default_factory=list)

    @property
    def usable(self) -> bool:
        return self.built and self.smoke is not None and self.smoke.passed


@dataclass(frozen=True)
class Reason:
    """One measured fact behind the recommendation (``code`` + values)."""

    code: str
    params: Dict[str, object] = field(default_factory=dict, hash=False, compare=False)


@dataclass
class Recommendation:
    engine: str = ""  # '' = no engine produced a working build
    reasons: List[Reason] = field(default_factory=list)


def compare_dir(config, engine: str) -> str:
    return os.path.join(build_root(config), COMPARE_DIR, engine)


def compare_project(project, engine: str):
    """A copy of ``project`` that builds with ``engine`` into its own folder."""
    copied = copy.deepcopy(project)
    copied.build.engine = engine
    copied.build.output_dir = compare_dir(project.build, engine)
    return copied


def unsupported_for(project, engine: str) -> List[str]:
    eng = get_engine(engine)
    missing = eng.unsupported_features(project.build)
    missing += [f for f in project.features_used() if not eng.supports(f) and f not in missing]
    return missing


def run_compare(
    project,
    python: str,
    engines: Sequence[str] = (),
    runs: int = DEFAULT_RUNS,
    timeout: float = DEFAULT_TIMEOUT,
    smoke_timeout: float = 8.0,
    texts: Optional[Dict[str, str]] = None,
    rtl: bool = False,
    allow_downloads: bool = False,
    on_line: Callable[[str], None] = lambda _line: None,
    on_stage: Optional[Callable[[str, str, int], None]] = None,
    on_engine: Optional[Callable[[str, str], None]] = None,
    build=run_build,
    smoke=run_from_neutral_folder,
    bench=measure_startup,
    clock: Callable[[], float] = time.monotonic,
    should_stop: Callable[[], bool] = lambda: False,
) -> List[EngineRun]:
    """Build ``project`` with each engine in turn, then measure each build.

    ``on_engine(engine, phase)`` reports "build", "smoke" and "startup";
    ``on_stage(engine, stage, percent)`` follows the build itself.
    """
    rows: List[EngineRun] = []
    for name in engines or engine_names():
        if should_stop():
            break
        row = EngineRun(name, unsupported=unsupported_for(project, name))
        rows.append(row)
        variant = compare_project(project, name)
        engine = get_engine(name)
        if on_engine:
            on_engine(name, "build")
        prepared = prepare_build(variant, python, texts, rtl, allow_downloads=allow_downloads)
        if prepared.kit_errors or prepared.error:
            row.findings = list(prepared.kit_errors)
            row.error = prepared.error
            continue
        log: List[str] = []

        def line(text: str, _log=log) -> None:
            _log.append(text)
            on_line(text)

        stage = (lambda key, pct, _n=name: on_stage(_n, key, pct)) if on_stage else None
        started = clock()
        outcome = build(prepared, line, stage)
        row.build_seconds = clock() - started
        if not outcome.ok:
            row.error = outcome.error
            row.findings = diagnose_output("\n".join(log), origin="build", engine=name)
            continue
        row.built = True
        row.output_path = engine.locate_output(variant.build)
        row.size_bytes = path_size(row.output_path) if row.output_path else 0
        exe = engine.locate_executable(variant.build)
        if on_engine:
            on_engine(name, "smoke")
        row.smoke = smoke(exe, timeout=smoke_timeout)
        if on_engine:
            on_engine(name, "startup")
        row.startup = bench(exe, runs=runs, timeout=timeout,
                            probe=variant.build.runtime_kit.enabled)
    return rows


# ── The recommendation ────────────────────────────────────────────────────


def _measured(row: EngineRun) -> Optional[float]:
    if row.startup is None or row.startup.method == METHOD_STILL_RUNNING:
        return None
    return row.startup.median


def recommend(rows: Sequence[EngineRun], default: str = "pyinstaller") -> Recommendation:
    """Pick an engine from the measurements, with every reason."""
    rec = Recommendation()
    usable = [r for r in rows if r.usable]
    for row in rows:
        if not row.built:
            rec.reasons.append(Reason("not_built", {"engine": row.engine}))
        elif not row.usable:
            rec.reasons.append(Reason("smoke_failed", {"engine": row.engine}))
    if not usable:
        rec.reasons.append(Reason("none_usable"))
        return rec
    if len(usable) == 1:
        rec.engine = usable[0].engine
        rec.reasons.append(Reason("only_working", {"engine": rec.engine}))
        return rec

    a, b = usable[0], usable[1]
    # 1. An engine that cannot do what the project asks for is out.
    lacking = [r for r in (a, b) if r.unsupported]
    if len(lacking) == 1:
        winner = b if lacking[0] is a else a
        rec.reasons.append(Reason("lacks_features", {
            "engine": lacking[0].engine, "features": list(lacking[0].unsupported),
            "other": winner.engine}))
        _add_facts(rec, a, b)
        rec.engine = winner.engine
        return rec

    facts = _add_facts(rec, a, b)
    if facts.get("startup"):
        rec.engine = facts["startup"]
    elif facts.get("size"):
        rec.engine = facts["size"]
    else:
        rec.engine = default if default in (a.engine, b.engine) else a.engine
        rec.reasons.append(Reason("no_clear_difference", {"engine": rec.engine}))
    return rec


def _add_facts(rec: Recommendation, a: EngineRun, b: EngineRun) -> Dict[str, str]:
    """Record start-up, size and build-time differences; return the winners."""
    winners: Dict[str, str] = {}
    ta, tb = _measured(a), _measured(b)
    if ta is not None and tb is not None and a.startup.method == b.startup.method:
        fast, slow = (a, b) if ta <= tb else (b, a)
        tf, ts = min(ta, tb), max(ta, tb)
        significant = tf > 0 and ts / tf >= STARTUP_RATIO and ts - tf >= STARTUP_MIN_SECONDS
        rec.reasons.append(Reason("startup_faster" if significant else "startup_similar", {
            "engine": fast.engine, "other": slow.engine, "fast": tf, "slow": ts,
            "method": a.startup.method}))
        if significant:
            winners["startup"] = fast.engine
    elif ta is not None or tb is not None or (a.startup and b.startup):
        rec.reasons.append(Reason("startup_not_comparable", {
            "a": a.engine, "b": b.engine,
            "method_a": a.startup.method if a.startup else "",
            "method_b": b.startup.method if b.startup else ""}))
    if a.size_bytes and b.size_bytes:
        small, big = (a, b) if a.size_bytes <= b.size_bytes else (b, a)
        significant = big.size_bytes / small.size_bytes >= SIZE_RATIO
        rec.reasons.append(Reason("smaller" if significant else "size_similar", {
            "engine": small.engine, "other": big.engine,
            "small": small.size_bytes, "big": big.size_bytes}))
        if significant:
            winners["size"] = small.engine
    quick, slow = (a, b) if a.build_seconds <= b.build_seconds else (b, a)
    rec.reasons.append(Reason("builds_faster", {
        "engine": quick.engine, "other": slow.engine,
        "fast": quick.build_seconds, "slow": slow.build_seconds}))
    return winners
