"""Read what went wrong after a build, and turn it into fixes.

Three sources, one output shape (``Finding``):

* the PyInstaller build log — build-time failures such as a wrong icon
  format or two Qt bindings colliding;
* ``warn-<name>.txt`` — the modules PyInstaller could not find, filtered
  down to the ones *the user's own code* imports (the raw file lists dozens
  of harmless platform modules and is why nobody reads it);
* the output of the built EXE itself — the traceback that a frozen app
  prints right before it dies.

Only patterns with a known meaning are reported. An unknown traceback is
still surfaced (its last line), but never guessed at.
"""

import os
import re
from dataclasses import dataclass, replace
from typing import Callable, Iterable, List, Optional, Sequence, Set, Tuple

from py2exe_gui.core.config import BuildConfig
from py2exe_gui.core.engines import get_engine
from py2exe_gui.core.fixes import (
    FIX_ADD_DATA,
    FIX_CONSOLE,
    FIX_HIDDEN_IMPORT,
    ORIGIN_BUILD,
    ORIGIN_RUNTIME,
    ORIGIN_WARN,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    Finding,
    Fix,
    dedupe_findings,
    flag_fix,
    localize_findings,
    runtime_fix,
    sort_findings,
)
from py2exe_gui.core.knowledge import (
    default_is_installed,
    lookup,
    pip_name_for,
)

DIAGNOSTIC_DIR = "p2e_diagnostic"

_RE_NO_MODULE = re.compile(r"No module named ['\"]?([\w.]+)['\"]?")
_RE_METADATA = re.compile(r"No package metadata was found for ['\"]?([^\s'\"]+)")
_RE_DISTRIBUTION = re.compile(r"The '([^']+)' distribution was not found")
_RE_FILE_NOT_FOUND = re.compile(
    r"FileNotFoundError: \[(?:Errno 2|WinError 2|WinError 3)\][^:]*: '((?:[^'\\]|\\.)+)'"
)
_RE_TEMPLATE = re.compile(r"TemplateNotFound: ['\"]?([^\s'\"]+)")
_RE_STREAM_NONE = re.compile(
    r"'NoneType' object has no attribute "
    r"'(write|flush|isatty|fileno|buffer|encoding|reconfigure|readline)'"
)
_RE_DLL = re.compile(r"DLL load failed while importing (\w+)")
_RE_FRAME = re.compile(r'File "([^"]+)"')
_RE_PERMISSION = re.compile(
    r"PermissionError: \[(?:WinError 5|WinError 32|Errno 13)\][^']*'(.+?)'"
)
_RE_WARN_LINE = re.compile(r"^missing module named (.+?) - imported by (.+)$")
# Split "a (top-level), b (delayed, optional)" on commas outside parentheses.
_RE_IMPORTER_SPLIT = re.compile(r",\s+(?![^()]*\))")
_RE_IMPORTER = re.compile(r"^(.*?)(?:\s+\(([^)]*)\))?$")
# Frozen extraction folders: onefile (_MEIxxxxx) and onedir (_internal).
_RE_BUNDLE_PREFIX = re.compile(r"^.*?(?:[\\/]_MEI\w+|[\\/]_internal)[\\/]")


# ── Build log and runtime output ──────────────────────────────────────────


def diagnose_output(
    text: str,
    origin: str = ORIGIN_RUNTIME,
    source: str = "",
    source_imports: Iterable[str] = (),
    knowledge_path: Optional[str] = None,
    is_installed: Callable[[str], bool] = default_is_installed,
    engine: str = "pyinstaller",
) -> List[Finding]:
    """Recognise known failures in a build log or an EXE's output.

    ``engine`` names the engine that produced the build: its own log patterns
    (``Engine.log_findings``) are added to the ones every build shares.
    """
    if not text:
        return []
    eng = get_engine(engine)
    project_dir = os.path.dirname(os.path.abspath(source)) if source else ""
    imports = set(source_imports)
    findings: List[Finding] = []

    if any(marker in text for marker in eng.missing_markers):
        findings.append(Finding(eng.missing_code, SEVERITY_ERROR, origin=origin))

    # A build log is full of hook chatter ("Failed to collect submodules ...
    # No module named 'x'") about optional extras; those patterns only mean
    # something when the EXE itself printed them.
    if origin != ORIGIN_BUILD:
        findings += _runtime_findings(
            text, origin, source, project_dir, knowledge_path, is_installed,
            eng.bundle_prefix,
        )

    # What only this engine's log says (Qt hook collisions, a bad icon...).
    findings += eng.log_findings(text, origin, imports)

    for path in _RE_PERMISSION.findall(text):
        findings.append(
            Finding("file_locked", SEVERITY_ERROR, {"path": os.path.basename(path)}, origin=origin)
        )

    if not findings and origin == ORIGIN_RUNTIME:
        last = last_exception_line(text)
        if last:
            findings.append(Finding("runtime_unhandled", SEVERITY_ERROR, {"error": last},
                                    origin=origin))

    # In the engine's own terms: a Nuitka build gets Nuitka options.
    return sort_findings(dedupe_findings(localize_findings(findings, eng.name)))


def _runtime_findings(
    text, origin, source, project_dir, knowledge_path, is_installed, bundle_prefix=None
) -> List[Finding]:
    """Failures an EXE reports about itself while starting or running."""
    findings: List[Finding] = []
    for match in _RE_NO_MODULE.finditer(text):
        module = match.group(1)
        if module == "PyInstaller":
            continue
        findings.append(_missing_module(module, origin, knowledge_path, is_installed))

    for name in _RE_METADATA.findall(text) + _RE_DISTRIBUTION.findall(text):
        dist = re.split(r"[<>=!~;\[\s]", name, maxsplit=1)[0]
        if dist:
            findings.append(
                Finding(
                    "missing_metadata",
                    SEVERITY_ERROR,
                    {"package": dist},
                    (flag_fix("--copy-metadata", dist),),
                    origin=origin,
                )
            )

    for raw in _RE_FILE_NOT_FOUND.findall(text):
        findings.append(_missing_file(raw.replace("\\\\", "\\"), project_dir, origin,
                                      bundle_prefix))

    for template in _RE_TEMPLATE.findall(text):
        folder = os.path.join(project_dir, "templates") if project_dir else ""
        fixes = (Fix(FIX_ADD_DATA, folder),) if folder and os.path.isdir(folder) else ()
        findings.append(
            Finding("template_not_found", SEVERITY_ERROR, {"template": template}, fixes,
                    origin=origin)
        )

    if "input(): lost sys.stdin" in text:
        findings.append(
            Finding("input_in_windowed", SEVERITY_ERROR, {}, (Fix(FIX_CONSOLE),), origin=origin)
        )

    for attr in _RE_STREAM_NONE.findall(text):
        findings.append(
            Finding("streams_none", SEVERITY_ERROR, {"attr": attr}, (Fix(FIX_CONSOLE),),
                    origin=origin, snippet="silence_streams",
                    alternatives=(runtime_fix("log_redirect"),))
        )

    for module in _RE_DLL.findall(text):
        package = _package_from_traceback(text, source, bundle_prefix)
        fixes = (flag_fix("--collect-binaries", package),) if package else ()
        findings.append(
            Finding("dll_load_failed", SEVERITY_ERROR,
                    {"module": module, "package": package or module}, fixes, origin=origin)
        )
    return findings


def _missing_module(module: str, origin: str, knowledge_path, is_installed) -> Finding:
    top = module.split(".")[0]
    if not is_installed(top):
        # PyInstaller can only bundle what the build interpreter can import;
        # a hidden import would not help. Same remedy as the doctor's check.
        return Finding(
            "missing_package",
            SEVERITY_ERROR,
            {"module": top, "pip": pip_name_for(top, knowledge_path)},
            origin=origin,
        )
    fixes = [Fix(FIX_HIDDEN_IMPORT, module)]
    info = lookup(top, knowledge_path)
    if info is not None:
        fixes.extend(f for f in info.build_fixes() if f not in fixes)
    return Finding(
        "runtime_missing_module",
        SEVERITY_ERROR,
        {"module": module, "pip": pip_name_for(top, knowledge_path)},
        tuple(fixes),
        origin=origin,
    )


def bundle_relative(path: str, prefix=None) -> str:
    """Strip the frozen extraction folder from ``path``.

    ``C:\\Users\\me\\AppData\\Local\\Temp\\_MEI1234\\data\\x.json`` → ``data\\x.json``.
    Relative paths come back unchanged; other absolute paths yield ''.
    ``prefix`` is the engine's pattern for that folder (PyInstaller's by default).
    """
    stripped = (prefix or _RE_BUNDLE_PREFIX).sub("", path, count=1)
    if stripped != path:
        return stripped
    if os.path.isabs(path) or re.match(r"^[A-Za-z]:[\\/]", path):
        return ""
    return path


def _missing_file(path: str, project_dir: str, origin: str, prefix=None) -> Finding:
    relative = bundle_relative(path, prefix)
    shown = relative or os.path.basename(path)
    fixes: Tuple[Fix, ...] = ()
    if relative and project_dir:
        parts = [p for p in re.split(r"[\\/]", relative) if p and p != "."]
        if parts and os.path.exists(os.path.join(project_dir, *parts)):
            fixes = (Fix(FIX_ADD_DATA, os.path.join(project_dir, parts[0])),)
    return Finding(
        "missing_data_file",
        SEVERITY_ERROR,
        {"path": shown},
        fixes,
        origin=origin,
        snippet="resource_path",
    )


def _package_from_traceback(text: str, source: str = "", prefix=None) -> str:
    """The top-level package of the deepest frame that isn't PyInstaller's."""
    script = os.path.basename(source) if source else ""
    package = ""
    for frame in _RE_FRAME.findall(text):
        relative = bundle_relative(frame, prefix) or frame
        parts = [p for p in re.split(r"[\\/]", relative) if p]
        if not parts:
            continue
        head = parts[0]
        if head.startswith(("<", "PyInstaller", "pyimod")) or len(parts) == 1:
            continue  # loader frames, or a script at the bundle root
        if head == script:
            continue
        package = head
    return package


def last_exception_line(text: str) -> str:
    """The ``SomeError: message`` line of the last traceback in ``text``."""
    if "Traceback (most recent call last)" not in text:
        return ""
    tail = text.rsplit("Traceback (most recent call last)", 1)[1]
    for line in tail.splitlines():
        stripped = line.strip()
        if re.match(r"^[A-Za-z_][\w.]*(Error|Exception|Exit|Interrupt)\b", stripped):
            return stripped[:300]
    return ""


# ── warn-<name>.txt ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class MissingModule:
    """One ``missing module named ...`` line."""

    name: str
    # (importer, import types) pairs, e.g. ("C:\\proj\\app.py", ("top-level",))
    importers: Tuple[Tuple[str, Tuple[str, ...]], ...]


def parse_warn_file(content: str) -> List[MissingModule]:
    """Parse PyInstaller's warn file into structured entries."""
    result = []
    for line in content.splitlines():
        match = _RE_WARN_LINE.match(line.strip())
        if not match:
            continue
        name = match.group(1).strip().strip("'\"")
        importers = []
        for item in _RE_IMPORTER_SPLIT.split(match.group(2)):
            m = _RE_IMPORTER.match(item.strip())
            if not m or not m.group(1):
                continue
            kinds = tuple(k.strip() for k in (m.group(2) or "").split(",") if k.strip())
            importers.append((m.group(1).strip(), kinds))
        result.append(MissingModule(name, tuple(importers)))
    return result


def warn_findings(
    missing: Sequence[MissingModule],
    source: str,
    local_modules: Iterable[str] = (),
    knowledge_path: Optional[str] = None,
) -> List[Finding]:
    """The missing modules the user's own code asked for.

    Everything imported only by the standard library or third-party packages
    is noise for this purpose (``pwd`` on Windows, ``winreg`` on Linux...),
    and so is anything imported purely inside ``try/except ImportError``.
    """
    source_path = os.path.normcase(os.path.abspath(source)) if source else ""
    local: Set[str] = set(local_modules)
    findings = []
    for entry in missing:
        if entry.name.split(".")[0] in local:
            continue
        kinds: List[str] = []
        for importer, types in entry.importers:
            if _is_user_importer(importer, source_path, local):
                kinds.extend(types or ("top-level",))
        if not kinds or all(k == "optional" for k in kinds):
            continue
        severity = SEVERITY_ERROR if "top-level" in kinds else SEVERITY_WARNING
        findings.append(
            Finding(
                "warn_missing_module",
                severity,
                {"module": entry.name, "pip": pip_name_for(entry.name, knowledge_path)},
                origin=ORIGIN_WARN,
            )
        )
    return sort_findings(findings)


def _is_user_importer(importer: str, source_path: str, local: Set[str]) -> bool:
    if importer == "__main__":
        return True
    if source_path and importer.endswith((".py", ".pyw")):
        return os.path.normcase(os.path.abspath(importer)) == source_path
    return importer.split(".")[0] in local


def build_name(config: BuildConfig) -> str:
    return config.output_name or os.path.splitext(os.path.basename(config.source))[0]


def build_root(config: BuildConfig) -> str:
    """The folder the build runs in (mirrors ``builder`` and the UI)."""
    return config.output_dir or os.path.dirname(config.source)


def warn_file_for(config: BuildConfig) -> str:
    """Where PyInstaller writes ``warn-<name>.txt`` for this config."""
    name = build_name(config)
    return os.path.join(build_root(config), "build", name, f"warn-{name}.txt")


def read_warn_findings(
    config: BuildConfig,
    local_modules: Iterable[str] = (),
    reader: Optional[Callable[[str], str]] = None,
    min_mtime: float = 0.0,
) -> List[Finding]:
    """Load and filter the warn file for ``config``; [] when absent.

    ``min_mtime`` skips a file older than the build that just ran: a build
    that failed before analysis leaves the previous run's warn file behind,
    and its findings would describe code that may since have changed.
    """
    path = warn_file_for(config)
    try:
        if min_mtime and os.path.getmtime(path) < min_mtime:
            return []
        if reader is not None:
            content = reader(path)
        else:
            with open(path, encoding="utf-8", errors="replace") as f:
                content = f.read()
    except OSError:
        return []
    return warn_findings(parse_warn_file(content), config.source, local_modules)


# ── Diagnostic run ─────────────────────────────────────────────────────────


def diagnostic_config(config: BuildConfig) -> BuildConfig:
    """A copy of ``config`` that keeps its console, built to a side folder.

    A windowed EXE that crashes shows its traceback in a dialog (or nowhere),
    so nothing can read it. The diagnostic build is the same app with the
    console left on, written to ``<output>/p2e_diagnostic`` so it never
    overwrites the real build.
    """
    return replace(
        config,
        windowed=False,
        noconsole=False,
        output_dir=os.path.join(build_root(config), DIAGNOSTIC_DIR),
        splash_image="",
    )


def needs_diagnostic_run(config: BuildConfig) -> bool:
    """Only windowed builds hide their traceback from the smoke test."""
    return bool(config.windowed or config.noconsole)


