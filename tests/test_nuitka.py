"""The Nuitka engine (2.0, milestone 2).

Everything here is checked against what Nuitka itself printed: its ``--help``
and ``--help-plugins`` (``tests/data/nuitka/help-*-4.2.2.txt``), and logs and
reports of real builds run while writing it (``tests/data/nuitka/*.log``,
``*.xml``). Nothing in those fixtures was written by hand.
"""

import io
import os
import re
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

from py2exe_gui import cli
from py2exe_gui.core.build_runner import popen_options, prepare_build
from py2exe_gui.core.build_stages import BuildStageTracker
from py2exe_gui.core.builder import DANGEROUS_FLAGS, find_dangerous_args
from py2exe_gui.core.config import BuildConfig, RuntimeKitConfig
from py2exe_gui.core.diagnostics import bundle_relative, diagnose_output
from py2exe_gui.core.engines import get_engine
from py2exe_gui.core.engines import nuitka as nk
from py2exe_gui.core.engines.nuitka_report import read_report
from py2exe_gui.core.engines.prerequisites import Toolchain, find_c_compiler, nuitka_findings
from py2exe_gui.core.fixes import (
    FIX_FLAG,
    FIX_HIDDEN_IMPORT,
    Finding,
    Fix,
    apply_fixes,
    fix_is_applied,
    flag_fix,
    localize_finding,
    localize_fix,
    localize_fixes,
    runtime_fix,
)
from py2exe_gui.core.knowledge import load_knowledge, lookup, parse_knowledge
from py2exe_gui.core.project_doctor import examine
from py2exe_gui.core.project_file import ProjectConfig, dumps_project, loads_project
from py2exe_gui.core.size_analyzer import (
    GROUP_COMPILED,
    GROUP_RUNTIME,
    GROUP_SCRIPT,
    GROUP_STDLIB,
    analyze,
    output_path_for,
)
from py2exe_gui.core.smoke_test import locate_built_executable
from py2exe_gui.core.venv_manager import plan_environment
from py2exe_gui.core.version_info import VersionInfo

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "nuitka")
ENGINE = get_engine("nuitka")


def fixture(name: str) -> str:
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return f.read()


HELP = fixture("help-4.2.2.txt") + fixture("help-plugins-4.2.2.txt")
#: Every option name the verified Nuitka documents.
DOCUMENTED = set(re.findall(r"(?m)^\s+(--[a-z0-9][a-z0-9-]*)", HELP))


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "app.py"
    path.write_text("print('hi')\n")
    return str(path)


def busy_config(tmp_path, source, onefile=True) -> BuildConfig:
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    data_file = tmp_path / "notes.txt"
    data_file.write_text("x")
    icon = tmp_path / "app.ico"
    icon.write_bytes(b"\0\0\1\0")
    splash = tmp_path / "s.png"
    splash.write_bytes(b"png")
    return BuildConfig(
        source=source, output_name="App", output_dir=str(tmp_path / "out"), icon=str(icon),
        onefile=onefile, windowed=True, extra_files=[str(data_dir), str(data_file)],
        hidden_imports=["pkg.mod"], optimize=2, upx=True, upx_dir="/opt/upx",
        splash_image=str(splash), engine="nuitka",
    )


def option_names(command):
    return [t.split("=", 1)[0] for t in command if t.startswith("--")]


# ── Verified against the installed Nuitka ─────────────────────────────────


def test_the_verified_version_is_the_one_in_the_fixtures():
    assert nk.VERIFIED_VERSION == "4.2.2"
    assert fixture("version-4.2.2.txt").splitlines()[0] == nk.VERIFIED_VERSION
    assert 'nuitka_version="4.2.2"' in fixture("onefile_report.xml")[:300]


@pytest.mark.parametrize("platform", ["win32", "linux", "darwin"])
@pytest.mark.parametrize("onefile", [True, False])
def test_every_option_the_engine_emits_is_in_nuitkas_own_help(tmp_path, source, platform,
                                                              onefile):
    config = busy_config(tmp_path, source, onefile)
    config.extra_args = ""
    info = VersionInfo(company_name="Me", product_name="App", file_description="d",
                       legal_copyright="c", file_version="1.2.3-beta", product_version="1.2")
    extra = ENGINE.metadata_options(info, platform) + ENGINE.consent_options()
    command, error = ENGINE.build_command(config, "py", platform, extra)
    assert error is None
    for name in option_names(command):
        assert name in DOCUMENTED, name


def test_translations_and_native_flags_are_documented_options():
    for targets in nk.FROM_PYINSTALLER.values():
        for target in targets:
            assert target in DOCUMENTED, target
    for flag in nk.NATIVE_FLAGS:
        assert flag in DOCUMENTED, flag


def test_nuitka_code_running_options_need_confirmation_and_exist():
    nuitka_flags = [f for f in DANGEROUS_FLAGS if f in DOCUMENTED]
    assert "--user-plugin" in nuitka_flags and "--assume-yes-for-downloads" in nuitka_flags
    assert find_dangerous_args("--assume-yes-for-downloads") == ["--assume-yes-for-downloads"]
    assert find_dangerous_args("--force-runtime-environment-variable=PYTHONPATH=/x")


def test_supported_pythons_match_the_installed_nuitka_when_present():
    versions = pytest.importorskip("nuitka.PythonVersions")
    supported = set(versions.getSupportedPythonVersions())
    assert set(nk.SUPPORTED_PYTHONS) <= supported
    assert set(nk.EXPERIMENTAL_PYTHONS) <= set(versions.getNotYetSupportedPythonVersions())


# ── The command ───────────────────────────────────────────────────────────


def test_onefile_layout_matches_pyinstallers(tmp_path, source):
    config = BuildConfig(source=source, output_dir=str(tmp_path / "out"), engine="nuitka")
    command, error = ENGINE.build_command(config, "py", "linux")
    assert error is None
    root = str(tmp_path / "out")
    assert command[:4] == ["py", "-m", "nuitka", "--mode=onefile"]
    assert f"--output-dir={os.path.join(root, 'build', 'nuitka')}" in command
    assert f"--output-filename={os.path.join(root, 'dist', 'app')}" in command
    assert "--output-folder-name=app" in command
    assert f"--report={os.path.join(root, 'build', 'app-nuitka-report.xml')}" in command
    assert "--update-check=never" in command and "--progress-bar=none" in command
    assert "--remove-output" not in command  # the size lab reads build/nuitka/app.dist
    assert command[-1] == source


def test_folder_layout(tmp_path, source):
    config = BuildConfig(source=source, output_name="App", onefile=False, engine="nuitka")
    command, _ = ENGINE.build_command(config, "py", "win32")
    root = os.path.dirname(source)
    assert "--mode=standalone" in command and "--remove-output" in command
    assert f"--output-dir={os.path.join(root, 'dist')}" in command
    assert "--output-filename=App.exe" in command
    assert ENGINE.dist_folder(config) == os.path.join(root, "dist", "App.dist")


def test_options_map_one_to_one(tmp_path, source):
    config = busy_config(tmp_path, source)
    command, _ = ENGINE.build_command(config, "py", "win32")
    assert "--windows-console-mode=disable" in command
    assert f"--windows-icon-from-ico={config.icon}" in command
    assert f"--onefile-windows-splash-screen-image={config.splash_image}" in command
    data_dir, data_file = config.extra_files
    assert f"--include-data-dir={data_dir}=data" in command
    assert f"--include-data-files={data_file}=notes.txt" in command
    assert "--include-module=pkg.mod" in command
    assert "--python-flag=no_asserts" in command and "--python-flag=no_docstrings" in command
    assert "--enable-plugins=upx" in command and "--upx-binary=/opt/upx" in command


def test_windows_only_options_stay_off_elsewhere(tmp_path, source):
    command, _ = ENGINE.build_command(busy_config(tmp_path, source), "py", "linux")
    names = option_names(command)
    for flag in ("--windows-console-mode", "--windows-icon-from-ico",
                 "--onefile-windows-splash-screen-image"):
        assert flag not in names
    assert ENGINE.metadata_options(VersionInfo(company_name="Me"), "linux") == []


def test_the_splash_screen_is_onefile_only(tmp_path, source):
    config = busy_config(tmp_path, source, onefile=False)
    command, _ = ENGINE.build_command(config, "py", "win32")
    assert "--onefile-windows-splash-screen-image" not in option_names(command)
    assert "splash" in ENGINE.unsupported_features(config)
    config.onefile = True
    assert "splash" not in ENGINE.unsupported_features(config)


def test_never_consents_to_downloads_by_itself(tmp_path, source):
    for onefile in (True, False):
        command, _ = ENGINE.build_command(busy_config(tmp_path, source, onefile), "py", "win32")
        assert "--assume-yes-for-downloads" not in command
    assert ENGINE.consent_options() == ["--assume-yes-for-downloads"]
    assert get_engine("pyinstaller").consent_options() == []


def test_metadata_versions_are_numbers_only():
    info = VersionInfo(file_version="2.1.0-rc1", product_version="", company_name="Ü Co")
    options = ENGINE.metadata_options(info, "win32")
    assert "--file-version=2.1.0.0" in options and "--company-name=Ü Co" in options
    assert not any(o.startswith("--product-version") for o in options)
    assert ENGINE.metadata_options(VersionInfo(), "win32") == []


def test_extra_args_and_errors(tmp_path, source):
    config = BuildConfig(source=source, engine="nuitka", extra_args="--lto=no --jobs 2")
    command, _ = ENGINE.build_command(config, "py", "linux")
    assert command[-4:-1] == ["--lto=no", "--jobs", "2"]
    assert ENGINE.build_command(BuildConfig(engine="nuitka"))[0] is None


def test_feature_matrix():
    assert not ENGINE.supports("runtime_kit") and not ENGINE.supports("manifest")
    assert ENGINE.supports("version_info") and ENGINE.supports("size_report")
    config = BuildConfig(source="a.py", engine="nuitka",
                         runtime_kit=RuntimeKitConfig(crash_reporter=True))
    assert ENGINE.unsupported_features(config) == ["runtime_kit"]


# ── Output ────────────────────────────────────────────────────────────────


def test_locate_output_and_prepare(tmp_path, source):
    config = BuildConfig(source=source, output_dir=str(tmp_path / "o"), engine="nuitka")
    assert ENGINE.locate_output(config) == ""
    ENGINE.prepare_output(config)
    assert os.path.isdir(tmp_path / "o" / "build") and os.path.isdir(tmp_path / "o" / "dist")
    (tmp_path / "o" / "dist" / "app").write_bytes(b"\x7fELF")
    assert ENGINE.locate_output(config) == str(tmp_path / "o" / "dist" / "app")
    assert output_path_for(config) == ENGINE.locate_output(config)
    config.onefile = False
    folder = tmp_path / "o" / "dist" / "app.dist"
    folder.mkdir()
    (folder / "app").write_bytes(b"\x7fELF")
    assert ENGINE.locate_output(config) == str(folder)
    assert ENGINE.locate_executable(config) == str(folder / "app")
    assert locate_built_executable(str(tmp_path / "o"), "app", False, engine="nuitka") == str(
        folder / "app")
    assert locate_built_executable(str(tmp_path / "o"), "app", False) is None


# ── Progress, from real logs ──────────────────────────────────────────────


def track(log: str):
    tracker = BuildStageTracker(ENGINE.stages)
    seen, percents = [], []
    for line in log.splitlines():
        tracker.feed(line)
        if not seen or seen[-1] != tracker.stage:
            seen.append(tracker.stage)
        percents.append(tracker.percent)
    return seen, percents


def test_progress_follows_a_real_onefile_build():
    seen, percents = track(fixture("onefile_success.log"))
    assert seen == ["starting", "nuitka_python", "nuitka_c_source", "nuitka_c_compile",
                    "nuitka_c_link", "nuitka_onefile"]
    assert percents == sorted(percents) and max(percents) < 100


def test_progress_follows_a_real_folder_build():
    seen, _ = track(fixture("standalone_yaml.log"))
    assert seen[-1] == "nuitka_c_link" and "nuitka_onefile" not in seen


def test_every_stage_has_a_label_in_both_languages():
    from py2exe_gui.strings import Ar, En

    for key in ENGINE.stage_keys():
        for locale in (Ar, En):
            assert getattr(locale, f"STAGE_{key.upper()}"), key


# ── Diagnostics, from real logs ───────────────────────────────────────────


@pytest.mark.parametrize("log, code, params", [
    ("plugin_tk_inter.log", "nuitka_plugin_needed", {"plugin": "tk-inter"}),
    ("plugin_pyqt5.log", "nuitka_plugin_needed", {"plugin": "pyqt5"}),
    ("download_declined.log", "nuitka_download_declined", {"tool": "appimagetool"}),
    ("patchelf_missing.log", "nuitka_tool_missing", {"tool": "patchelf"}),
    ("readelf_missing.log", "nuitka_tool_missing", {"tool": "readelf"}),
    ("compiler_missing.log", "nuitka_compiler_failed", {}),
    ("compiler_cc_invalid.log", "nuitka_compiler_failed", {"compiler": "/nonexistent/gcc"}),
    ("syntax_error.log", "syntax_error", {"line": "1", "error": "invalid syntax"}),
    ("python_experimental.log", "nuitka_python_experimental",
     {"version": "3.15", "nuitka": "4.2.2"}),
    ("nuitka_not_installed.log", "nuitka_missing", {}),
])
def test_real_build_logs_become_findings(log, code, params):
    findings = diagnose_output(fixture(log), origin="build", engine="nuitka")
    found = [f for f in findings if f.code == code]
    assert found, [f.code for f in findings]
    for key, value in params.items():
        assert found[0].params[key] == value


def test_a_plugin_finding_carries_its_fix():
    finding = diagnose_output(fixture("plugin_tk_inter.log"), origin="build",
                              engine="nuitka")[0]
    assert finding.fixes == (flag_fix("--enable-plugins", "tk-inter"),)


def test_successful_builds_report_nothing():
    for log in ("onefile_success.log", "onefile_keep_intermediates.log",
                "standalone_yaml.log", "missing_import_build.log"):
        assert diagnose_output(fixture(log), origin="build", engine="nuitka") == [], log


def test_the_download_reason_is_nuitkas_own_words():
    finding = diagnose_output(fixture("download_declined.log"), origin="build",
                              engine="nuitka")[0]
    assert finding.params["reason"] == "Error, appimagetool is required to create a Linux installer."


def test_a_real_onefile_runtime_failure_points_at_the_data_folder(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "greeting.json").write_text("{}")
    findings = diagnose_output(fixture("onefile_runtime_missing_data.log"),
                               source=str(tmp_path / "hello.py"), engine="nuitka")
    assert [f.code for f in findings] == ["missing_data_file"]
    assert findings[0].params["path"] == "data/greeting.json"
    assert findings[0].fixes == (Fix("add_data", str(tmp_path / "data")),)


def test_nuitka_bundle_folders_are_stripped():
    assert bundle_relative("/tmp/onefile_11797_385002_KaQje6Kmucs/data/x.json",
                           nk.BUNDLE_PREFIX) == "data/x.json"
    assert bundle_relative(r"C:\apps\App.dist\data\x.json", nk.BUNDLE_PREFIX) == r"data\x.json"
    # PyInstaller's pattern is untouched by Nuitka's.
    assert bundle_relative("/home/me/App.dist/x.json") == ""


# ── Fixes in the engine's terms ───────────────────────────────────────────


@pytest.mark.parametrize("pyinstaller, nuitka", [
    ("--collect-data docx", ("--include-package-data docx",)),
    ("--collect-submodules apscheduler", ("--include-package apscheduler",)),
    ("--collect-all x", ("--include-package x", "--include-package-data x")),
    ("--copy-metadata APScheduler", ("--include-distribution-metadata APScheduler",)),
    ("--exclude-module tkinter", ("--nofollow-import-to tkinter",)),
    ("--hidden-import a.b", ("--include-module a.b",)),
    ("--collect-binaries cv2", ()),
    ("--enable-plugins pyqt5", ("--enable-plugins pyqt5",)),
])
def test_flag_fixes_translate_or_are_unsupported(pyinstaller, nuitka):
    flag, _, argument = pyinstaller.partition(" ")
    translated = localize_fix(flag_fix(flag, argument), "nuitka")
    assert tuple(f.value for f in translated) == nuitka


def test_other_fix_kinds():
    assert localize_fix(Fix(FIX_HIDDEN_IMPORT, "x"), "nuitka") == (Fix(FIX_HIDDEN_IMPORT, "x"),)
    assert localize_fix(runtime_fix("log_redirect"), "nuitka") == ()
    assert localize_fix(runtime_fix("log_redirect")) == (runtime_fix("log_redirect"),)
    # A Nuitka plugin means nothing to PyInstaller.
    assert localize_fix(flag_fix("--enable-plugins", "pyqt5"), "pyinstaller") == ()


def test_localize_finding_moves_what_has_no_equivalent():
    finding = Finding("dll_load_failed", "error", {"module": "cv2"},
                      (flag_fix("--collect-binaries", "cv2"), flag_fix("--collect-data", "cv2")),
                      alternatives=(runtime_fix("log_redirect"),))
    local = localize_finding(finding, "nuitka")
    assert local.fixes == (flag_fix("--include-package-data", "cv2"),)
    assert local.alternatives == ()
    assert local.unsupported == (flag_fix("--collect-binaries", "cv2"), runtime_fix("log_redirect"))
    assert localize_finding(finding, "pyinstaller") is finding
    fixes, missing = localize_fixes([flag_fix("--collect-all", "x"),
                                     flag_fix("--collect-submodules", "x")], "nuitka")
    assert [f.value for f in fixes] == ["--include-package x", "--include-package-data x"]
    assert missing == ()


def test_apply_fixes_writes_nuitka_options():
    config = BuildConfig(source="a.py", engine="nuitka")
    new, applied = apply_fixes(config, [flag_fix("--collect-data", "docx"),
                                        flag_fix("--collect-binaries", "cv2"),
                                        runtime_fix("crash_reporter"),
                                        Fix(FIX_HIDDEN_IMPORT, "m")])
    assert new.extra_args == "--include-package-data=docx"
    assert new.hidden_imports == ["m"] and not new.runtime_kit.crash_reporter
    assert [f.kind for f in applied] == [FIX_FLAG, FIX_HIDDEN_IMPORT]
    assert fix_is_applied(new, flag_fix("--collect-data", "docx"))
    assert not fix_is_applied(new, flag_fix("--collect-binaries", "cv2"))
    assert apply_fixes(new, [flag_fix("--collect-data", "docx")])[1] == []
    # The same fix on a PyInstaller project is written exactly as before.
    pyi, _ = apply_fixes(BuildConfig(source="a.py"), [flag_fix("--collect-data", "docx")])
    assert pyi.extra_args == "--collect-data docx"


# ── Knowledge base: per-engine fields ─────────────────────────────────────


def test_verified_plugins_are_in_the_knowledge_base():
    assert lookup("PyQt5").engines["nuitka"].plugins == ("pyqt5",)
    assert lookup("tkinter").engines["nuitka"].plugins == ("tk-inter",)
    assert flag_fix("--enable-plugins", "pyqt5") in lookup("PyQt5").build_fixes("nuitka")
    assert flag_fix("--enable-plugins", "pyqt5") not in lookup("PyQt5").build_fixes()
    assert "Tcl/Tk" in lookup("tkinter").note("en", "nuitka")
    assert lookup("tkinter").note("en") == ""


def test_every_engine_note_exists_in_both_languages():
    for name, info in load_knowledge().items():
        for engine, hints in info.engines.items():
            assert engine == "nuitka"
            if hints.notes:
                assert hints.notes.get("ar") and hints.notes.get("en"), name


def test_documented_plugins_only():
    listed = fixture("plugin-list-4.2.2.txt")
    for name, info in load_knowledge().items():
        for plugin in info.engines.get("nuitka", SimpleNamespace(plugins=())).plugins:
            assert re.search(rf"(?m)^ {re.escape(plugin)}\s", listed), (name, plugin)


@pytest.mark.parametrize("engines, error", [
    ({"cx_freeze": {}}, "unknown engine"),
    ({"nuitka": {"flags": ["x"]}}, "unknown keys"),
    ({"nuitka": {"plugins": "pyqt5"}}, "list of strings"),
    ({"nuitka": {"plugins": [""]}}, "list of strings"),
    ({"nuitka": {"notes": []}}, "notes"),
    ({"nuitka": []}, "must be an object"),
    ([], "must be an object"),
])
def test_engine_sections_are_validated(engines, error):
    with pytest.raises(ValueError, match=error):
        parse_knowledge({"packages": {"x": {"engines": engines}}})


def test_entries_without_engines_still_parse():
    parsed = parse_knowledge({"packages": {"x": {"pip": "y"}}})
    assert parsed["x"].engines == {} and parsed["x"].build_fixes("nuitka") == ()


# ── Doctor: prerequisites ─────────────────────────────────────────────────


def fake_which(found):
    return lambda name, path=None: found.get(name) if path is None else found.get(
        (path, name))


def toolchain(platform="linux", found=None, version="3.12", env=None, globs=()):
    return Toolchain(platform=platform, python_version=version, python_dir="/env/bin",
                     which=fake_which(found or {}), env=env or {},
                     glob=lambda pattern: list(globs))


LINUX_OK = {"gcc": "/usr/bin/gcc", "patchelf": "/usr/bin/patchelf",
            "readelf": "/usr/bin/readelf"}


def codes(findings):
    return [(f.code, f.params.get("tool", "")) for f in findings]


def test_a_complete_linux_machine_is_quiet():
    assert nuitka_findings(toolchain(found=LINUX_OK), lambda m: True) == []


def test_missing_pieces_on_linux():
    findings = nuitka_findings(toolchain(found={}), lambda m: False)
    assert codes(findings) == [("nuitka_missing", ""), ("nuitka_no_compiler", ""),
                               ("nuitka_tool_missing", "patchelf"),
                               ("nuitka_tool_missing", "readelf")]
    assert all(f.severity == "error" for f in findings)


def test_patchelf_next_to_the_build_interpreter_counts():
    found = {"gcc": "/usr/bin/gcc", "readelf": "/usr/bin/readelf",
             ("/env/bin", "patchelf"): "/env/bin/patchelf"}
    assert nuitka_findings(toolchain(found=found), lambda m: True) == []


def test_compilers_by_platform():
    assert find_c_compiler(toolchain(found={"clang": "/c"}))["kind"] == "clang"
    assert find_c_compiler(toolchain(env={"CC": "cc"}, found={"cc": "/usr/bin/cc"}))["kind"] == "cc"
    assert find_c_compiler(toolchain("darwin", found={"gcc": "/g", "clang": "/c"}))["kind"] == "clang"
    win = toolchain("win32", env={"ProgramFiles": r"C:\PF"},
                    globs=[r"C:\PF\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.3"])
    assert find_c_compiler(win)["kind"] == "msvc"
    assert find_c_compiler(toolchain("win32", found={"cl": "cl.exe"}))["kind"] == "msvc"
    assert find_c_compiler(toolchain("win32", found={"gcc": "gcc.exe"}))["kind"] == "mingw"
    assert find_c_compiler(toolchain("win32")) == {}


def test_no_compiler_on_windows_is_a_warning_and_on_macos_an_error():
    win = nuitka_findings(toolchain("win32"), lambda m: True)
    assert [(f.code, f.severity) for f in win] == [("nuitka_no_compiler_windows", "warning")]
    mac = nuitka_findings(toolchain("darwin"), lambda m: True)
    assert [(f.code, f.severity) for f in mac] == [("nuitka_no_compiler_macos", "error")]


@pytest.mark.parametrize("version, expected", [
    ("3.8", []), ("3.14", []), ("", []),
    ("3.15", [("nuitka_python_experimental", "warning")]),
    ("3.16", [("nuitka_python_unsupported", "error")]),
])
def test_python_versions(version, expected):
    findings = nuitka_findings(toolchain(found=LINUX_OK, version=version), lambda m: True)
    assert [(f.code, f.severity) for f in findings] == expected


def test_toolchain_for_this_interpreter_and_a_venv(tmp_path):
    here = Toolchain.for_python()
    assert here.python_version == "{}.{}".format(*sys.version_info[:2])
    env = tmp_path / "env"
    (env / "bin").mkdir(parents=True)
    (env / "pyvenv.cfg").write_text("home = /usr/bin\nversion_info = 3.11.9\n")
    assert Toolchain.for_python(str(env / "bin" / "python")).python_version == "3.11"
    assert Toolchain.for_python(str(tmp_path / "nope" / "python")).python_version == ""


def test_examine_reports_engine_limits_and_prerequisites(tmp_path):
    script = tmp_path / "app.py"
    script.write_text("import tkinter\nimport docx\n\nif __name__ == '__main__':\n    pass\n")
    config = BuildConfig(source=str(script), engine="nuitka",
                         runtime_kit=RuntimeKitConfig(log_redirect=True))
    report = examine(str(script), config, is_installed=lambda m: True,
                     extra_features=["manifest", "version_info"],
                     toolchain=toolchain(found=LINUX_OK))
    by_code = {}
    for f in report.findings:
        by_code.setdefault(f.code, []).append(f)
    features = sorted(f.params["feature"] for f in by_code["engine_feature_unsupported"])
    assert features == ["manifest", "runtime_kit"]
    plugin = by_code["nuitka_plugin_for_package"][0]
    assert plugin.params == {"package": "tkinter", "plugin": "tk-inter"}
    # python-docx's collect-data fix comes back in Nuitka's terms.
    collect = by_code["package_needs_collect"][0]
    assert collect.fixes == (flag_fix("--include-package-data", "docx"),)


def test_examine_with_pyinstaller_is_unchanged(tmp_path):
    script = tmp_path / "app.py"
    script.write_text("import docx\n\nif __name__ == '__main__':\n    pass\n")
    report = examine(str(script), BuildConfig(source=str(script)), is_installed=lambda m: True,
                     extra_features=["manifest"])
    collect = [f for f in report.findings if f.code == "package_needs_collect"][0]
    assert collect.fixes == (flag_fix("--collect-data", "docx"),)
    assert not [f for f in report.findings if f.code.startswith(("nuitka", "engine"))]


def test_a_resolved_plugin_need_is_not_reported(tmp_path):
    script = tmp_path / "app.py"
    script.write_text("import tkinter\n\nif __name__ == '__main__':\n    pass\n")
    config = BuildConfig(source=str(script), engine="nuitka",
                         extra_args="--enable-plugins=tk-inter")
    report = examine(str(script), config, is_installed=lambda m: True,
                     toolchain=toolchain(found=LINUX_OK))
    assert not [f for f in report.findings if f.code == "nuitka_plugin_for_package"]


def test_project_features_used():
    project = ProjectConfig()
    assert project.features_used() == []
    project.version_info.company_name = "Me"
    project.manifest.enabled = True
    assert project.features_used() == ["version_info", "manifest"]


# ── Size lab: the report plus the folder ──────────────────────────────────


def test_read_a_real_report():
    report = read_report(os.path.join(DATA, "standalone_yaml_report.xml"))
    assert report.ok and report.mode == "standalone" and report.nuitka_version == "4.2.2"
    assert report.file_packages["yaml/_yaml.so"] == "yaml"
    assert report.file_packages["libexpat.so.1"] == ""
    assert report.data_files["data/config.yaml"] == (26, True)
    assert ("yaml.scanner", 1066416) in report.compiled
    assert report.bytecode_bytes > 4_000_000


def test_unreadable_reports(tmp_path):
    assert not read_report(str(tmp_path / "missing.xml")).ok
    bad = tmp_path / "bad.xml"
    bad.write_text("<not-xml")
    assert not read_report(str(bad)).ok
    other = tmp_path / "other.xml"
    other.write_text("<something-else/>")
    assert not read_report(str(other)).ok


def materialize(listing: str, folder):
    """Recreate a real build's folder from its listing, as sparse files."""
    for line in listing.splitlines():
        size, rel = line.split(" ", 1)
        path = os.path.join(folder, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.truncate(int(size))


def test_size_lab_on_a_real_folder_build(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "yamlapp.py").write_text("import yaml\n")
    config = BuildConfig(source=str(root / "yamlapp.py"), onefile=False, engine="nuitka")
    materialize(fixture("standalone_yaml_listing.txt"), ENGINE.dist_folder(config))
    os.makedirs(root / "build")
    shutil.copy(os.path.join(DATA, "standalone_yaml_report.xml"), ENGINE.report_path(config))

    report = analyze(config)
    assert report.ok and report.output_path == ENGINE.dist_folder(config)
    sizes = dict(report.ranked())
    assert sizes["yaml"] == 2690457               # yaml/_yaml.so, exactly
    assert sizes[GROUP_SCRIPT] == 26              # the user's data file
    report_xml = read_report(ENGINE.report_path(config))
    assert sizes[GROUP_STDLIB] == report_xml.bytecode_bytes
    assert sizes[GROUP_COMPILED] == 15868041 - report_xml.bytecode_bytes
    assert sizes[GROUP_RUNTIME] > 0               # libexpat, _bz2.so...
    assert report.content_bytes == report.output_bytes  # every byte attributed once
    assert report.largest_files[0] == ("yamlapp", 15868041)


def test_size_lab_without_a_report(tmp_path, source):
    config = BuildConfig(source=source, onefile=False, engine="nuitka")
    assert not analyze(config).ok


# ── The headless build ────────────────────────────────────────────────────


def test_prepare_build_for_nuitka(tmp_path, source):
    project = ProjectConfig(build=BuildConfig(source=source, output_dir=str(tmp_path / "o"),
                                              engine="nuitka"))
    project.version_info.company_name = "Me"
    project.manifest.enabled = True
    python = os.path.join(str(tmp_path), "env", "bin", "python")
    prepared = prepare_build(project, python, platform="win32")
    assert prepared.engine == "nuitka" and prepared.command[1:3] == ["-m", "nuitka"]
    assert "--company-name=Me" in prepared.command
    assert "--assume-yes-for-downloads" not in prepared.command
    assert prepared.temp_files == []  # no version file, no manifest for Nuitka
    assert prepared.env["NUITKA_UPDATE_CHECK"] == "never"
    assert prepared.env["PATH"].split(os.pathsep)[0] == os.path.dirname(python)
    assert os.path.isdir(tmp_path / "o" / "build")
    consented = prepare_build(project, "py", platform="win32", allow_downloads=True)
    assert "--assume-yes-for-downloads" in consented.command


def test_a_runtime_kit_project_cannot_build_with_nuitka(source):
    project = ProjectConfig(build=BuildConfig(source=source, engine="nuitka",
                                              runtime_kit=RuntimeKitConfig(updater=True)))
    prepared = prepare_build(project, "py")
    assert prepared.command == []
    assert [(f.code, f.params["feature"]) for f in prepared.kit_errors] == [
        ("engine_feature_unsupported", "runtime_kit")]


def test_popen_options_close_stdin_for_nuitka_only():
    assert popen_options("nuitka")["stdin"] == subprocess.DEVNULL
    assert popen_options("pyinstaller") == {}
    assert popen_options("pyinstaller", {"A": "1"}) == {"env": {"A": "1"}}


def test_version_probe_never_checks_for_updates_online():
    calls = []

    def run(cmd, **kwargs):
        calls.append(kwargs.get("env") or {})
        return SimpleNamespace(returncode=0, stdout="4.2.2\nUpdate status: ...\n")

    assert ENGINE.version("py", run=run) == "4.2.2"
    assert calls[0]["NUITKA_UPDATE_CHECK"] == "never"


def test_requirements_and_environment_plan(tmp_path, source):
    assert ENGINE.requirements("linux") == (nk.REQUIREMENT, "patchelf")
    assert ENGINE.requirements("win32") == (nk.REQUIREMENT,)
    plan = plan_environment(source, str(tmp_path / "envs"), sys.executable,
                            ENGINE.requirements("linux"))
    assert plan.setup[-1][-2:] == [nk.REQUIREMENT, "patchelf"]
    pyi = plan_environment(source, str(tmp_path / "envs"), sys.executable, "pyinstaller>=6")
    assert pyi.setup[-1][-1] == "pyinstaller>=6"


def test_project_file_round_trips_the_engine(tmp_path):
    project = ProjectConfig()
    project.build.engine = "nuitka"
    loaded, warnings = loads_project(dumps_project(project, str(tmp_path)), str(tmp_path))
    assert loaded.build.engine == "nuitka" and warnings == []


# ── Command line ──────────────────────────────────────────────────────────


class FakeProcess:
    def __init__(self, lines, code, on_finish=None):
        self.stdout = iter(lines)
        self._code = code
        self._on_finish = on_finish

    def wait(self):
        if self._on_finish:
            self._on_finish()
        return self._code

    def terminate(self):
        pass


@pytest.fixture
def cli_project(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "ENVS_ROOT", str(tmp_path / "envs"))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.py").write_text("print('hello')\n")
    run_cli("init", "app.py")
    monkeypatch.setattr(get_engine("nuitka").__class__, "is_available",
                        lambda self, python, run=None: True)
    return tmp_path


def run_cli(*argv, yes=False, interactive=False, answers=()):
    out, err = io.StringIO(), io.StringIO()
    replies = list(answers)
    console = cli.Console(yes=yes, interactive=interactive, out=out, err=err,
                          ask=lambda _p: replies.pop(0) if replies else "",
                          secret=lambda _p: "")
    code = cli.main(["--lang", "en", *argv], console)
    return SimpleNamespace(code=code, out=out.getvalue(), err=err.getvalue())


def scripted_nuitka(monkeypatch, tmp_path, outcomes):
    """Each build gets the next (log fixture, exit code); returns the commands."""
    calls = []
    queue = list(outcomes)

    def popen(command, **kwargs):
        calls.append((command, kwargs))
        log, code = queue.pop(0)

        def finish():
            (tmp_path / "dist").mkdir(exist_ok=True)
            (tmp_path / "dist" / "app").write_bytes(b"\x7fELF" * 100)

        return FakeProcess([line + "\n" for line in fixture(log).splitlines()], code,
                           finish if code == 0 else None)

    monkeypatch.setattr("py2exe_gui.core.build_runner.subprocess.Popen", popen)
    return calls


def test_cli_builds_with_nuitka(cli_project, monkeypatch):
    calls = scripted_nuitka(monkeypatch, cli_project, [("onefile_success.log", 0)])
    r = run_cli("build", "--engine", "nuitka")
    assert r.code == 0, r.err
    command, kwargs = calls[0]
    assert command[1:4] == ["-m", "nuitka", "--mode=onefile"]
    assert kwargs["stdin"] == subprocess.DEVNULL
    assert "--assume-yes-for-downloads" not in command
    assert "==> [Compiling C] 55%" in r.out and "==> [Creating the single file] 90%" in r.out
    assert "Engine: Nuitka" in r.out


def test_cli_asks_before_allowing_a_download(cli_project, monkeypatch):
    calls = scripted_nuitka(monkeypatch, cli_project,
                            [("download_declined.log", 1), ("onefile_success.log", 0)])
    r = run_cli("build", "--engine", "nuitka", interactive=True, answers=["y"])
    assert r.code == 0, r.err
    assert "appimagetool" in r.out
    assert "--assume-yes-for-downloads" not in calls[0][0]
    assert "--assume-yes-for-downloads" in calls[1][0]


def test_cli_never_downloads_without_a_yes(cli_project, monkeypatch):
    calls = scripted_nuitka(monkeypatch, cli_project, [("download_declined.log", 1)])
    r = run_cli("build", "--engine", "nuitka", interactive=True, answers=["n"])
    assert r.code == cli.EXIT_FAILED and len(calls) == 1
    calls = scripted_nuitka(monkeypatch, cli_project, [("download_declined.log", 1)])
    assert run_cli("build", "--engine", "nuitka").code == cli.EXIT_CONSENT
    assert len(calls) == 1


def test_cli_allow_downloads_flag(cli_project, monkeypatch):
    calls = scripted_nuitka(monkeypatch, cli_project, [("onefile_success.log", 0)])
    assert run_cli("build", "--engine", "nuitka", "--allow-downloads").code == 0
    assert "--assume-yes-for-downloads" in calls[0][0]


def test_cli_offers_to_install_nuitka(cli_project, monkeypatch):
    monkeypatch.setattr(get_engine("nuitka").__class__, "is_available",
                        lambda self, python, run=None: False)
    r = run_cli("build", "--engine", "nuitka")
    assert r.code == cli.EXIT_CONSENT and "nuitka[onefile]" in r.out


# ── A real build (slow) ───────────────────────────────────────────────────


def _can_build_with_nuitka() -> str:
    try:
        import nuitka  # noqa: F401
    except ImportError:
        return "Nuitka is not installed"
    tc = Toolchain.for_python()
    missing = [f.code for f in nuitka_findings(tc, lambda m: True)
               if f.severity == "error"]
    return ", ".join(missing)


@pytest.mark.slow
def test_a_real_nuitka_build_runs_and_has_a_size_report(tmp_path, monkeypatch):
    reason = _can_build_with_nuitka()
    if reason:
        pytest.skip(reason)
    monkeypatch.setattr(cli, "ENVS_ROOT", str(tmp_path / "envs"))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "greeting.txt").write_text("hello from nuitka")
    (tmp_path / "app.py").write_text(
        "import os\n"
        "here = os.path.dirname(os.path.abspath(__file__))\n"
        "print(open(os.path.join(here, 'data', 'greeting.txt')).read())\n"
    )
    assert run_cli("init", "app.py").code == 0
    from py2exe_gui.core.project_file import load_project, save_project

    loaded = load_project("p2e.toml")
    loaded.project.build.engine = "nuitka"
    loaded.project.build.extra_files = [str(tmp_path / "data")]
    save_project(loaded.project, "p2e.toml")
    r = run_cli("build", yes=True)
    assert r.code == 0, r.out + r.err
    exe = tmp_path / "dist" / ("app.exe" if sys.platform == "win32" else "app")
    neutral = tmp_path / "elsewhere"
    neutral.mkdir()
    out = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60,
                         cwd=str(neutral))
    assert out.stdout.strip() == "hello from nuitka"
    size = run_cli("size")
    assert size.code == 0 and "Compiled code" in size.out
