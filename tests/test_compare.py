"""Compare mode (2.0, milestone 3): running both engines and recommending one.

The recommendation is checked against real comparisons, recorded with
``py2exe-gui compare --json`` (``tests/data/compare/``): replaying the
measured numbers must give the recommendation and reasons recorded then.
"""

import io
import json
import os
from types import SimpleNamespace

import pytest

from py2exe_gui import cli
from py2exe_gui.core import compare as cmp
from py2exe_gui.core.build_runner import BuildOutcome
from py2exe_gui.core.config import BuildConfig, RuntimeKitConfig
from py2exe_gui.core.fixes import Finding
from py2exe_gui.core.project_file import ProjectConfig
from py2exe_gui.core.smoke_test import SmokeResult
from py2exe_gui.core.startup_bench import RunTiming, StartupResult
from py2exe_gui.strings import set_locale
from py2exe_gui.texts import (
    compare_table,
    reason_line,
    recommendation_lines,
    seconds_text,
    startup_text,
)

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "compare")
FIXTURES = ("yaml_onefile", "yaml_onedir", "kit_onefile", "server_onefile", "silent_onefile")


def load(name):
    with open(os.path.join(DATA, name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def row_from_json(data) -> cmp.EngineRun:
    startup = None
    if data["startup"] is not None:
        s = data["startup"]
        startup = StartupResult(
            method=s["method"], timeout=s["timeout"],
            runs=[RunTiming(r["method"], r["seconds"]) for r in s["runs"]])
    smoke = None
    if data["smoke"] is not None:
        smoke = SmokeResult(ran=True, exited_cleanly=data["smoke"]["returncode"] is not None,
                            returncode=data["smoke"]["returncode"])
    return cmp.EngineRun(
        data["engine"], built=data["built"], error=data["error"],
        findings=[Finding(code, "error") for code in data["findings"]],
        build_seconds=data["build_seconds"], output_path=data["output"],
        size_bytes=data["size_bytes"], smoke=smoke, startup=startup,
        unsupported=list(data["unsupported"]))


@pytest.mark.parametrize("name", FIXTURES)
def test_real_comparisons_replay_to_the_recorded_recommendation(name):
    data = load(name)
    rows = [row_from_json(r) for r in data["engines"]]
    rec = cmp.recommend(rows)
    assert rec.engine == data["recommendation"]
    assert [r.code for r in rec.reasons] == [r["code"] for r in data["reasons"]]
    # The median recorded is the median of the runs recorded.
    for row, raw in zip(rows, data["engines"]):
        if raw["startup"]:
            assert row.startup.median == raw["startup"]["median_seconds"]


def test_what_the_real_comparisons_found():
    onefile = {e["engine"]: e for e in load("yaml_onefile")["engines"]}
    assert onefile["nuitka"]["size_bytes"] < onefile["pyinstaller"]["size_bytes"]
    assert onefile["nuitka"]["build_seconds"] > onefile["pyinstaller"]["build_seconds"]
    kit = {e["engine"]: e for e in load("kit_onefile")["engines"]}
    assert kit["pyinstaller"]["startup"]["method"] == "probe"
    # The kit app sleeps 1.5 s in its own code: the probe stops before it.
    assert kit["pyinstaller"]["startup"]["median_seconds"] < 1.5
    assert kit["nuitka"]["findings"] == ["engine_feature_unsupported"]
    silent = load("silent_onefile")["engines"]
    assert {e["startup"]["method"] for e in silent} == {"still_running"}
    assert all(e["startup"]["median_seconds"] is None for e in silent)


# ── recommend(): every branch ─────────────────────────────────────────────


def made(engine, size, startup=None, method="exit", build=10.0, smoke=True,
         unsupported=(), built=True):
    runs = [] if startup is None else [RunTiming(method, startup)]
    return cmp.EngineRun(
        engine, built=built, build_seconds=build, size_bytes=size,
        smoke=SmokeResult(True, True, 0 if smoke else 1) if built else None,
        startup=StartupResult(method=method, runs=runs) if built else None,
        unsupported=list(unsupported))


def codes(rec):
    return [r.code for r in rec.reasons]


def test_nothing_works():
    rec = cmp.recommend([made("pyinstaller", 0, built=False), made("nuitka", 5, smoke=False)])
    assert rec.engine == "" and codes(rec) == ["not_built", "smoke_failed", "none_usable"]


def test_an_engine_lacking_a_feature_loses_even_when_faster():
    rec = cmp.recommend([made("pyinstaller", 100, 0.5),
                         made("nuitka", 50, 0.1, unsupported=["manifest"])])
    assert rec.engine == "pyinstaller" and codes(rec)[0] == "lacks_features"
    assert rec.reasons[0].params["features"] == ["manifest"]


def test_startup_decides_before_size():
    rec = cmp.recommend([made("pyinstaller", 100, 0.10), made("nuitka", 300, 0.50)])
    assert rec.engine == "pyinstaller"
    assert codes(rec) == ["startup_faster", "smaller", "builds_faster"]


def test_size_decides_when_startup_is_close():
    rec = cmp.recommend([made("pyinstaller", 300, 0.10), made("nuitka", 100, 0.12)])
    assert rec.engine == "nuitka" and codes(rec)[:2] == ["startup_similar", "smaller"]


def test_a_gap_below_50_ms_is_not_a_difference():
    # Ratio 2× but only 40 ms: nobody notices.
    rec = cmp.recommend([made("pyinstaller", 100, 0.08), made("nuitka", 100, 0.04)])
    assert rec.engine == "pyinstaller" and "no_clear_difference" in codes(rec)


def test_different_methods_are_never_compared():
    rec = cmp.recommend([made("pyinstaller", 100, 0.1, method="exit"),
                         made("nuitka", 100, 0.5, method="first_output")])
    assert "startup_not_comparable" in codes(rec)
    assert not any(r.code == "startup_faster" for r in rec.reasons)


# ── run_compare() with stand-ins for the slow parts ───────────────────────


@pytest.fixture
def project(tmp_path):
    script = tmp_path / "app.py"
    script.write_text("print(1)\n")
    return ProjectConfig(build=BuildConfig(source=str(script)))


def fake_build(log=("ok",), code=0):
    calls = []

    def build(prepared, on_line, on_stage):
        calls.append(prepared)
        for line in log:
            on_line(line)
        return BuildOutcome(code == 0, code)

    build.calls = calls
    return build


def test_each_engine_builds_into_its_own_folder(project, tmp_path):
    build = fake_build()
    phases = []
    rows = cmp.run_compare(
        project, "py", runs=2, timeout=3, build=build,
        smoke=lambda exe, timeout: SmokeResult(True, True, 0),
        bench=lambda exe, runs, timeout, probe: StartupResult(
            method="exit", runs=[RunTiming("exit", 0.1)] * runs, timeout=timeout),
        on_engine=lambda e, p: phases.append((e, p)),
        clock=iter([0.0, 2.0, 10.0, 40.0]).__next__)
    assert [r.engine for r in rows] == ["pyinstaller", "nuitka"]
    folders = [p.cwd for p in build.calls]
    assert folders == [os.path.join(str(tmp_path), "p2e_compare", "pyinstaller"),
                       os.path.join(str(tmp_path), "p2e_compare", "nuitka")]
    assert all(os.path.isdir(f) for f in folders)  # created before the build runs
    assert [r.build_seconds for r in rows] == [2.0, 30.0]
    assert phases[:3] == [("pyinstaller", "build"), ("pyinstaller", "smoke"),
                          ("pyinstaller", "startup")]
    assert all(r.startup.median == 0.1 for r in rows)
    # The project itself is untouched.
    assert project.build.output_dir == "" and project.build.engine == "pyinstaller"


def test_a_failed_build_is_diagnosed(project):
    with open(os.path.join(os.path.dirname(DATA), "nuitka", "download_declined.log"),
              encoding="utf-8") as f:
        log = f.read().splitlines()
    rows = cmp.run_compare(project, "py", engines=["nuitka"], build=fake_build(log, 1),
                           smoke=None, bench=None)
    assert not rows[0].built
    assert [f.code for f in rows[0].findings] == ["nuitka_download_declined"]


def test_the_runtime_kit_is_probed_and_nuitka_refused(project):
    project.build.runtime_kit = RuntimeKitConfig(log_redirect=True)
    probes = []
    rows = cmp.run_compare(
        project, "py", build=fake_build(),
        smoke=lambda exe, timeout: SmokeResult(True, True, 0),
        bench=lambda exe, runs, timeout, probe: probes.append(probe) or StartupResult(),
    )
    assert probes == [True]
    assert rows[1].engine == "nuitka" and not rows[1].built
    assert rows[1].unsupported == ["runtime_kit"]
    assert rows[1].findings[0].code == "engine_feature_unsupported"


def test_project_level_features_count_as_unsupported(project):
    project.manifest.enabled = True
    assert cmp.unsupported_for(project, "nuitka") == ["manifest"]
    assert cmp.unsupported_for(project, "pyinstaller") == []


def test_should_stop_ends_the_comparison(project):
    rows = cmp.run_compare(project, "py", build=fake_build(), should_stop=lambda: True)
    assert rows == []


# ── Text ──────────────────────────────────────────────────────────────────


def rows_from(name):
    return [row_from_json(r) for r in load(name)["engines"]]


def test_seconds_text():
    assert seconds_text(0.1234) == "123 ms"
    assert seconds_text(2.5) == "2.50 s"
    assert seconds_text(47.31) == "47.3 s"


@pytest.mark.parametrize("locale", ["ar", "en"])
def test_the_table_has_every_row_and_never_a_placeholder(locale):
    set_locale(locale)
    for name in FIXTURES:
        table = compare_table(rows_from(name))
        assert len(table) == 8
        for label, cells in table:
            assert label and len(cells) == 2
            assert all("{" not in c for c in cells)


def test_still_running_says_so_without_a_number():
    set_locale("en")
    silent = rows_from("silent_onefile")
    assert startup_text(silent[0].startup) == "still running after 3.00 s — no number"
    table = dict(compare_table(silent))
    assert table["Measured as"][0].startswith("neither exited")


def test_each_number_states_its_method():
    set_locale("en")
    kit = dict(compare_table(rows_from("kit_onefile")))
    assert kit["Measured as"][0] == "until the Runtime Kit is ready, before your code starts"
    assert kit["Build"][1].startswith("❌ not built")
    assert kit["Not supported"][1] == "Runtime Kit"
    server = dict(compare_table(rows_from("server_onefile")))
    assert server["Measured as"] == ["until the program first writes something"] * 2


def test_reasons_read_well_in_both_languages():
    rec = cmp.recommend(rows_from("yaml_onefile"))
    set_locale("en")
    lines = recommendation_lines(rec)
    assert lines[0] == "🏆 Recommendation: Nuitka"
    assert lines[2].startswith("• Nuitka starts faster: ")
    set_locale("ar")
    rtl = recommendation_lines(rec, isolate=True)
    assert all(line.startswith("‏") for line in rtl)
    assert "⁦" in reason_line(rec.reasons[0], isolate=True)


# ── Command line ──────────────────────────────────────────────────────────


def run_cli(*argv, yes=True):
    out, err = io.StringIO(), io.StringIO()
    console = cli.Console(yes=yes, interactive=False, out=out, err=err,
                          ask=lambda _p: "", secret=lambda _p: "")
    code = cli.main(["--lang", "en", *argv], console)
    return SimpleNamespace(code=code, out=out.getvalue(), err=err.getvalue())


@pytest.fixture
def cli_project(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "ENVS_ROOT", str(tmp_path / "envs"))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.py").write_text("print('hello')\n")
    assert run_cli("init", "app.py").code == 0
    monkeypatch.setattr(cli, "_ensure_engine", lambda engine, python, console: None)

    def fake_compare(project, python, runs, timeout, on_engine, on_stage, **kw):
        on_engine("pyinstaller", "build")
        on_stage("nuitka", "nuitka_c_compile", 55)
        return rows_from("yaml_onefile")

    monkeypatch.setattr("py2exe_gui.core.compare.run_compare", fake_compare)
    return tmp_path


def test_cli_compare_prints_the_table_and_the_reasons(cli_project):
    r = run_cli("compare")
    assert r.code == 0, r.err
    assert "PyInstaller: building…" in r.out
    assert "Start-up time" in r.out and "🏆 Recommendation: Nuitka" in r.out
    assert "p2e_compare" in r.out


def test_cli_compare_json_keeps_stdout_clean(cli_project):
    r = run_cli("compare", "--json")
    data = json.loads(r.out)  # nothing but the document on stdout
    assert data["recommendation"] == "nuitka"
    assert [e["engine"] for e in data["engines"]] == ["pyinstaller", "nuitka"]
    assert "PyInstaller: building…" in r.err


def test_cli_compare_with_nothing_usable_exits_one(cli_project, monkeypatch):
    monkeypatch.setattr("py2exe_gui.core.compare.run_compare",
                        lambda *a, **k: [made("pyinstaller", 0, built=False)])
    assert run_cli("compare").code == cli.EXIT_FAILED
