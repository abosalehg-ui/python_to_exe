"""The engine abstraction (2.0): registry, interface, shims and migration.

The proof that the refactor is behaviour-neutral is the rest of the suite,
which runs unchanged; these tests pin down the new surface itself.
"""

import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from py2exe_gui.core import build_stages
from py2exe_gui.core import config as config_module
from py2exe_gui.core.build_runner import prepare_build
from py2exe_gui.core.builder import build_pyinstaller_command
from py2exe_gui.core.config import BuildConfig, RuntimeKitConfig
from py2exe_gui.core.diagnostics import diagnose_output
from py2exe_gui.core.engines import (
    DEFAULT_ENGINE,
    FEATURES,
    Engine,
    PyInstallerEngine,
    StageTracker,
    UnknownEngineError,
    engine_for,
    engine_names,
    features_used,
    get_engine,
    is_known_engine,
)
from py2exe_gui.core.engines import pyinstaller as pyi_engine
from py2exe_gui.core.project_file import (
    SCHEMA_VERSION,
    ProjectConfig,
    ProjectFileError,
    dumps_project,
    loads_project,
)
from py2exe_gui.core.size_analyzer import output_path_for
from py2exe_gui.strings import Ar, En


@pytest.fixture
def source_file(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("print('hi')\n")
    return str(f)


# ── Registry ──────────────────────────────────────────────────────────────


def test_registry_lists_the_default_first_and_matches_the_config_list():
    assert engine_names()[0] == DEFAULT_ENGINE == "pyinstaller"
    # config.py keeps its own copy so it can stay import-free; they must agree.
    assert tuple(engine_names()) == config_module.KNOWN_ENGINES
    assert all(is_known_engine(n) for n in engine_names())
    assert not is_known_engine("py2exe")


def test_get_engine_and_engine_for():
    assert isinstance(get_engine(), PyInstallerEngine)
    assert get_engine("") is get_engine("pyinstaller")
    assert engine_for(BuildConfig()) is get_engine("pyinstaller")
    with pytest.raises(UnknownEngineError):
        get_engine("cx_freeze")
    # Duck typing: anything with an ``engine`` attribute, or none at all.
    assert engine_for(SimpleNamespace()) is get_engine()


def test_every_engine_implements_the_interface():
    for name in engine_names():
        engine = get_engine(name)
        assert isinstance(engine, Engine)
        assert engine.name == name and engine.display_name and engine.module
        assert set(engine.feature_matrix) == set(FEATURES), name
        assert engine.stages and engine.stage_keys()[0] == "starting"
        assert engine.missing_markers and engine.missing_code


def test_the_base_class_refuses_to_guess():
    engine = Engine()
    with pytest.raises(NotImplementedError):
        engine.build_command(BuildConfig())
    with pytest.raises(NotImplementedError):
        engine.locate_output(BuildConfig())
    assert engine.log_findings("anything", "build", ()) == []
    assert engine.build_findings(BuildConfig()) == []
    assert engine.analyze_size(BuildConfig()) is None


# ── Feature matrix ────────────────────────────────────────────────────────


def test_pyinstaller_supports_every_feature():
    engine = get_engine("pyinstaller")
    assert engine.supported_features() == frozenset(FEATURES)
    busy = BuildConfig(
        source="a.py", icon="i.ico", windowed=True, upx=True, strip=True, optimize=2,
        splash_image="s.png", version_file="v.txt", manifest_file="m.xml",
        extra_files=["d"], hidden_imports=["x"],
        runtime_kit=RuntimeKitConfig(updater=True),
    )
    assert engine.unsupported_features(busy) == []


def test_features_used_lists_only_what_the_config_asks_for():
    assert features_used(BuildConfig()) == ["onefile"]
    assert features_used(BuildConfig(onefile=False)) == ["onedir"]
    used = features_used(BuildConfig(noconsole=True, icon="i.ico", upx=True, optimize=1,
                                     runtime_kit=RuntimeKitConfig(log_redirect=True)))
    assert used == ["onefile", "windowed", "icon", "upx", "optimize", "runtime_kit"]
    # In FEATURES order, always.
    assert used == [f for f in FEATURES if f in used]


def test_unsupported_features_reports_what_an_engine_lacks():
    class Tiny(Engine):
        name = "tiny"
        feature_matrix = {f: f in ("onefile", "icon") for f in FEATURES}

    tiny = Tiny()
    assert not tiny.supports("upx") and tiny.supports("icon")
    assert tiny.unsupported_features(BuildConfig(icon="i.ico", upx=True)) == ["upx"]
    assert tiny.unsupported_features(BuildConfig(onefile=False)) == ["onedir"]


# ── The command and the shim ──────────────────────────────────────────────


@pytest.mark.parametrize("platform", ["win32", "linux", "darwin"])
def test_the_shim_and_the_engine_build_the_same_command(tmp_path, source_file, platform):
    data = tmp_path / "data"
    data.mkdir()
    config = BuildConfig(
        source=source_file, output_name="App", output_dir=str(tmp_path / "out"),
        onefile=False, windowed=True, extra_files=[str(data)], hidden_imports=["x"],
        optimize=1, upx=True, upx_dir="/opt/upx", extra_args="--log-level WARN",
    )
    via_shim = build_pyinstaller_command(config, "py", platform, ["--runtime-hook", "h.py"])
    via_engine = get_engine().build_command(config, "py", platform, ["--runtime-hook", "h.py"])
    assert via_shim == via_engine
    assert via_engine[0][:3] == ["py", "-m", "PyInstaller"]


def test_the_shim_always_builds_pyinstaller(source_file, monkeypatch):
    # Even a config that names another engine gets a PyInstaller command from
    # the old function; engine_for(config) is the way to honour the choice.
    config = BuildConfig(source=source_file)
    config.engine = "something-else"
    cmd, error = build_pyinstaller_command(config)
    assert error is None and cmd[:3] == [sys.executable, "-m", "PyInstaller"]


def test_the_error_path_is_unchanged():
    assert get_engine().build_command(BuildConfig()) == build_pyinstaller_command(BuildConfig())
    assert build_pyinstaller_command(BuildConfig())[0] is None


def test_prepare_build_uses_the_configured_engine(source_file):
    prepared = prepare_build(ProjectConfig(build=BuildConfig(source=source_file)), "py")
    assert prepared.engine == "pyinstaller"
    assert prepared.command[:3] == ["py", "-m", "PyInstaller"]


# ── Versions ──────────────────────────────────────────────────────────────


def _fake_run(returncode=0, stdout="6.22.3\n", exc=None):
    calls = []

    def run(cmd, **kwargs):
        calls.append(cmd)
        if exc is not None:
            raise exc
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr="")

    run.calls = calls
    return run


def test_version_and_availability():
    engine = get_engine()
    run = _fake_run()
    assert engine.version("py", run=run) == "6.22.3"
    assert run.calls == [["py", "-m", "PyInstaller", "--version"]]
    assert engine.is_available("py", run=_fake_run())
    assert engine.version("py", run=_fake_run(returncode=1)) == ""
    assert not engine.is_available("py", run=_fake_run(exc=OSError("no python")))
    assert engine.version("py", run=_fake_run(exc=subprocess.TimeoutExpired("x", 1))) == ""
    assert engine.version("py", run=_fake_run(stdout="\n\n")) == ""


def test_version_of_the_real_interpreter_when_pyinstaller_is_installed():
    pytest.importorskip("PyInstaller")
    import PyInstaller

    assert get_engine().version(sys.executable) == PyInstaller.__version__


# ── Progress ──────────────────────────────────────────────────────────────


def test_build_stage_tracker_is_the_generic_tracker_on_pyinstaller_stages():
    tracker = build_stages.BuildStageTracker()
    assert isinstance(tracker, StageTracker)
    assert tracker.stages == pyi_engine.STAGES == build_stages.STAGES
    assert build_stages.stage_keys() == get_engine().stage_keys()
    assert isinstance(get_engine().progress_tracker(), StageTracker)


def test_a_tracker_follows_any_engines_stages():
    stages = (
        build_stages.Stage("starting", 0, 10, ()),
        build_stages.Stage("compile", 10, 90, ("compiling",)),
    )
    tracker = build_stages.BuildStageTracker(stages)
    assert tracker.feed("Compiling C files") and tracker.stage == "compile"
    assert tracker.percent == 10
    tracker.reset()
    assert tracker.stage == "starting" and tracker.percent == 0


# ── Output ────────────────────────────────────────────────────────────────


def test_locate_output_and_executable_onefile(tmp_path, source_file):
    config = BuildConfig(source=source_file, output_dir=str(tmp_path), output_name="App")
    engine = get_engine()
    assert engine.locate_output(config) == "" == engine.locate_executable(config)
    (tmp_path / "dist").mkdir()
    exe = tmp_path / "dist" / "App"
    exe.write_bytes(b"\x7fELF")
    assert engine.locate_output(config) == str(exe) == output_path_for(config)
    assert engine.locate_executable(config) == str(exe)


def test_locate_output_and_executable_onedir(tmp_path, source_file):
    config = BuildConfig(source=source_file, output_dir=str(tmp_path), onefile=False)
    folder = tmp_path / "dist" / "app"
    folder.mkdir(parents=True)
    engine = get_engine()
    assert engine.locate_output(config) == str(folder)
    assert engine.locate_executable(config) == ""  # the folder alone is not a program
    (folder / "app.exe").write_bytes(b"MZ")
    assert engine.locate_executable(config) == str(folder / "app.exe")


def test_locate_output_defaults_to_the_script_folder(source_file):
    config = BuildConfig(source=source_file)
    dist = os.path.join(os.path.dirname(source_file), "dist")
    os.makedirs(dist)
    open(os.path.join(dist, "app.exe"), "wb").close()
    assert get_engine().locate_output(config) == os.path.join(dist, "app.exe")


# ── Diagnostics ───────────────────────────────────────────────────────────


def test_diagnose_output_takes_an_engine():
    log = "C:\\Python\\python.exe: No module named PyInstaller"
    assert [f.code for f in diagnose_output(log, origin="build")] == ["pyinstaller_missing"]
    assert diagnose_output(log, origin="build", engine="pyinstaller") == diagnose_output(
        log, origin="build"
    )
    with pytest.raises(UnknownEngineError):
        diagnose_output(log, origin="build", engine="nope")


def test_engine_log_findings_hold_the_pyinstaller_patterns():
    text = (
        "ERROR: Unable to find \"C:\\p\\data\" when adding binary and data files.\n"
        "ValueError: Received icon image 'C:\\p\\a.png' which exists but is not in the "
        "correct format.\n"
    )
    codes = [f.code for f in get_engine().log_findings(text, "build", ())]
    assert codes == ["add_data_missing", "icon_wrong_format"]


# ── Config and project file ───────────────────────────────────────────────


def test_build_config_engine_round_trips_and_defaults():
    assert BuildConfig().engine == "pyinstaller"
    assert BuildConfig().to_dict()["engine"] == "pyinstaller"
    assert BuildConfig.from_dict(BuildConfig().to_dict()).engine == "pyinstaller"
    # Pre-2.0 settings have no engine; anything unknown or mistyped falls back.
    for value in (None, "", 3, "nuitka-from-the-future", ["pyinstaller"]):
        data = BuildConfig().to_dict()
        data["engine"] = value
        assert BuildConfig.from_dict(data).engine == "pyinstaller"
    old = BuildConfig().to_dict()
    del old["engine"]
    assert BuildConfig.from_dict(old).engine == "pyinstaller"


def test_project_file_writes_schema_2_with_the_engine(tmp_path):
    assert SCHEMA_VERSION == 2
    text = dumps_project(ProjectConfig(), str(tmp_path))
    assert "schema = 2" in text and 'engine = "pyinstaller"' in text
    project, warnings = loads_project(text, str(tmp_path))
    assert project.build.engine == "pyinstaller" and warnings == []


def test_a_1_6_project_file_migrates_to_pyinstaller(tmp_path):
    for text in ('schema = 1\n[build]\nonefile = false\n', "schema = 1\n"):
        project, warnings = loads_project(text, str(tmp_path))
        assert project.build.engine == "pyinstaller"
        assert warnings == []
    project, _ = loads_project('schema = 1\n[build]\nonefile = false\n', str(tmp_path))
    assert project.build.onefile is False


def test_an_unknown_engine_in_a_project_is_refused_not_replaced(tmp_path):
    with pytest.raises(ProjectFileError) as e:
        loads_project('schema = 2\n[build]\nengine = "cx_freeze"\n', str(tmp_path))
    assert e.value.code == "unknown_engine" and e.value.detail == "cx_freeze"
    for locale in (Ar, En):
        assert "{detail}" in locale.PROJECT_ERR_UNKNOWN_ENGINE


def test_a_wrongly_typed_engine_is_reported_and_ignored(tmp_path):
    project, warnings = loads_project("schema = 2\n[build]\nengine = 1\n", str(tmp_path))
    assert project.build.engine == "pyinstaller"
    assert any("build.engine" in w for w in warnings)
