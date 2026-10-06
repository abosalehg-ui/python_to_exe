"""Tests for post-build diagnostics: build log, warn file and EXE output.

The sample texts are verbatim PyInstaller 6 / CPython output, so a change in
those formats shows up here rather than as a silently empty Doctor tab.
"""

import os
import time

import pytest

from py2exe_gui.core.config import BuildConfig
from py2exe_gui.core.diagnostics import (
    DIAGNOSTIC_DIR,
    bundle_relative,
    diagnose_output,
    diagnostic_config,
    last_exception_line,
    needs_diagnostic_run,
    parse_warn_file,
    read_warn_findings,
    warn_file_for,
    warn_findings,
)


def installed(_module):
    return True


def runtime(text, **kwargs):
    kwargs.setdefault("is_installed", installed)
    return diagnose_output(text, origin="runtime", **kwargs)


def build(text, **kwargs):
    return diagnose_output(text, origin="build", **kwargs)


def only(findings, code):
    matches = [f for f in findings if f.code == code]
    assert len(matches) == 1, [f.code for f in findings]
    return matches[0]


# ── Runtime output ─────────────────────────────────────────────────────────

MISSING_MODULE = """Traceback (most recent call last):
  File "app.py", line 2, in <module>
ModuleNotFoundError: No module named 'babel.numbers'
[PYI-1225:ERROR] Failed to execute script 'app' due to unhandled exception!
"""


def test_missing_module_gets_hidden_import():
    finding = only(runtime(MISSING_MODULE), "runtime_missing_module")
    assert finding.params["module"] == "babel.numbers"
    assert ("hidden_import", "babel.numbers") in [(f.kind, f.value) for f in finding.fixes]


def test_missing_module_adds_knowledge_fixes():
    text = "ModuleNotFoundError: No module named 'docx.oxml'"
    finding = only(runtime(text), "runtime_missing_module")
    assert "--collect-data docx" in [f.value for f in finding.fixes]


def test_missing_module_not_installed_means_install_it():
    text = "ModuleNotFoundError: No module named 'yaml'"
    finding = only(runtime(text, is_installed=lambda m: False), "missing_package")
    assert finding.params == {"module": "yaml", "pip": "PyYAML"}
    assert finding.fixes == ()


def test_missing_metadata_copies_it():
    text = (
        "importlib.metadata.PackageNotFoundError: "
        "No package metadata was found for streamlit"
    )
    finding = only(runtime(text), "missing_metadata")
    assert [f.value for f in finding.fixes] == ["--copy-metadata streamlit"]


def test_pkg_resources_distribution_not_found_strips_the_specifier():
    text = (
        "pkg_resources.DistributionNotFound: The 'tqdm>=4.27' distribution was "
        "not found and is required by the application"
    )
    assert only(runtime(text), "missing_metadata").params["package"] == "tqdm"


def test_missing_data_file_inside_meipass(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "cfg.json").write_text("{}")
    source = str(tmp_path / "app.py")
    text = (
        "FileNotFoundError: [Errno 2] No such file or directory: "
        "'/tmp/_MEIx8Kq2a/data/cfg.json'"
    )
    finding = only(runtime(text, source=source), "missing_data_file")
    assert finding.params["path"] == "data/cfg.json"
    assert finding.fixes[0].value == os.path.join(str(tmp_path), "data")
    assert finding.snippet == "resource_path"


def test_missing_data_file_windows_path(tmp_path):
    text = (
        "FileNotFoundError: [Errno 2] No such file or directory: "
        "'C:\\\\Users\\\\me\\\\AppData\\\\Local\\\\Temp\\\\_MEI1234\\\\logo.png'"
    )
    finding = only(runtime(text, source=str(tmp_path / "app.py")), "missing_data_file")
    assert finding.params["path"] == "logo.png"
    assert finding.fixes == ()  # logo.png does not exist in the project


def test_template_not_found_bundles_templates(tmp_path):
    (tmp_path / "templates").mkdir()
    text = "jinja2.exceptions.TemplateNotFound: index.html"
    finding = only(runtime(text, source=str(tmp_path / "app.py")), "template_not_found")
    assert finding.fixes[0].value == str(tmp_path / "templates")


def test_lost_stdin():
    finding = only(runtime("RuntimeError: input(): lost sys.stdin"), "input_in_windowed")
    assert finding.fixes[0].kind == "console"


def test_none_stream():
    text = "AttributeError: 'NoneType' object has no attribute 'isatty'"
    assert only(runtime(text), "streams_none").params["attr"] == "isatty"


def test_dll_load_failure_names_the_package():
    text = """Traceback (most recent call last):
  File "app.py", line 1, in <module>
  File "PyInstaller/loader/pyimod02_importers.py", line 457, in exec_module
  File "cv2/__init__.py", line 181, in <module>
ImportError: DLL load failed while importing cv2: The specified module could not be found.
"""
    finding = only(runtime(text, source="app.py"), "dll_load_failed")
    assert finding.params["package"] == "cv2"
    assert [f.value for f in finding.fixes] == ["--collect-binaries cv2"]


def test_unknown_traceback_is_surfaced_not_guessed():
    text = 'Traceback (most recent call last):\n  File "app.py", line 3\nZeroDivisionError: division by zero\n'
    finding = only(runtime(text), "runtime_unhandled")
    assert finding.params["error"] == "ZeroDivisionError: division by zero"
    assert finding.fixes == ()


def test_clean_output_yields_nothing():
    assert runtime("hello world\n") == []
    assert runtime("") == []


# ── Build log ──────────────────────────────────────────────────────────────


def test_build_log_ignores_hook_chatter_about_missing_modules():
    text = (
        "WARNING: Failed to collect submodules for 'x' because importing 'x' "
        "raised: ModuleNotFoundError: No module named 'optional_extra'"
    )
    assert build(text) == []


def test_pyinstaller_not_installed():
    assert only(build("/usr/bin/python3: No module named PyInstaller"), "pyinstaller_missing")


QT_ERROR = (
    "ERROR: Aborting build process due to attempt to collect multiple Qt bindings "
    "packages: attempting to run hook for 'PySide6', while hook for 'PyQt5' has "
    "already been run! PyInstaller does not support multiple Qt bindings packages"
)


def test_qt_conflict_excludes_the_binding_the_code_does_not_use():
    finding = only(build(QT_ERROR, source_imports={"PyQt5"}), "multiple_qt_bindings_build")
    assert [f.value for f in finding.fixes] == ["--exclude-module PySide6"]
    finding = only(build(QT_ERROR, source_imports={"PySide6"}), "multiple_qt_bindings_build")
    assert [f.value for f in finding.fixes] == ["--exclude-module PyQt5"]


def test_unable_to_find_add_data():
    text = 'ERROR: Unable to find "/proj/missing.txt" when adding binary and data files.'
    assert only(build(text), "add_data_missing").params["path"] == "/proj/missing.txt"


def test_icon_wrong_format():
    text = (
        "ValueError: Received icon image '/proj/logo.png' which exists but is not "
        "in the correct format. On this platform, only ('exe', 'ico') images may be used"
    )
    assert only(build(text), "icon_wrong_format").params["icon"] == "logo.png"


def test_locked_output_file():
    text = "PermissionError: [WinError 5] Access is denied: 'C:\\\\proj\\\\dist\\\\app.exe'"
    assert only(build(text), "file_locked")


# ── Helpers ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "path, expected",
    [
        ("/tmp/_MEIabc123/data/x.json", "data/x.json"),
        ("C:\\Temp\\_MEI42\\x.json", "x.json"),
        ("C:\\Apps\\Tool\\_internal\\res\\a.png", "res\\a.png"),
        ("relative/file.txt", "relative/file.txt"),
        ("/home/me/elsewhere.txt", ""),
        ("D:\\elsewhere.txt", ""),
    ],
)
def test_bundle_relative(path, expected):
    assert bundle_relative(path) == expected


def test_last_exception_line_needs_a_traceback():
    assert last_exception_line("ValueError: x") == ""


# ── warn file ──────────────────────────────────────────────────────────────

WARN_SAMPLE = """
This file lists modules PyInstaller was not able to find. This does not
necessarily mean these modules are required for running your program.

missing module named pwd - imported by posixpath (delayed, conditional, optional), shutil (delayed, optional)
missing module named 'collections.abc' - imported by traceback (top-level), typing (top-level)
missing module named delayed_missing_abc - imported by /proj/app.py (delayed)
missing module named notinstalled_pkg_xyz - imported by /proj/app.py (top-level)
missing module named optional_thing - imported by /proj/app.py (optional)
missing module named yaml - imported by helpers (top-level), /proj/app.py (conditional)
missing module named helpers_sub - imported by helpers (top-level)
"""


def test_parse_warn_file_structure():
    entries = {e.name: e for e in parse_warn_file(WARN_SAMPLE)}
    assert entries["collections.abc"].importers[0] == ("traceback", ("top-level",))
    assert entries["pwd"].importers[0] == ("posixpath", ("delayed", "conditional", "optional"))
    assert entries["notinstalled_pkg_xyz"].importers == (("/proj/app.py", ("top-level",)),)


def test_warn_findings_keep_only_the_users_imports():
    findings = warn_findings(parse_warn_file(WARN_SAMPLE), "/proj/app.py", {"helpers"})
    found = {f.params["module"]: f.severity for f in findings}
    assert found == {
        "notinstalled_pkg_xyz": "error",
        "yaml": "error",  # top-level in a local module
        "delayed_missing_abc": "warning",
        "helpers_sub": "error",
    }
    assert "pwd" not in found and "optional_thing" not in found


def test_warn_findings_skip_local_modules_themselves():
    text = "missing module named helpers - imported by /proj/app.py (top-level)\n"
    assert warn_findings(parse_warn_file(text), "/proj/app.py", {"helpers"}) == []


def test_warn_file_location_matches_the_builder_layout(tmp_path):
    config = BuildConfig(source=str(tmp_path / "app.py"), output_dir=str(tmp_path / "out"))
    assert warn_file_for(config) == os.path.join(
        str(tmp_path / "out"), "build", "app", "warn-app.txt"
    )
    named = BuildConfig(source=str(tmp_path / "app.py"), output_name="Tool")
    assert warn_file_for(named) == os.path.join(str(tmp_path), "build", "Tool", "warn-Tool.txt")


def test_read_warn_findings_ignores_a_stale_file(tmp_path):
    source = tmp_path / "app.py"
    config = BuildConfig(source=str(source))
    path = warn_file_for(config)
    os.makedirs(os.path.dirname(path))
    with open(path, "w") as f:
        f.write(f"missing module named zzz - imported by {source} (top-level)\n")

    assert [f.params["module"] for f in read_warn_findings(config)] == ["zzz"]
    assert read_warn_findings(config, min_mtime=time.time() + 60) == []


def test_read_warn_findings_without_a_file(tmp_path):
    assert read_warn_findings(BuildConfig(source=str(tmp_path / "app.py"))) == []


# ── Diagnostic run ─────────────────────────────────────────────────────────


def test_diagnostic_config_keeps_the_console_and_a_side_folder(tmp_path):
    config = BuildConfig(
        source=str(tmp_path / "app.py"),
        output_dir=str(tmp_path / "out"),
        windowed=True,
        noconsole=True,
        splash_image="splash.png",
        hidden_imports=["x"],
    )
    diag = diagnostic_config(config)
    assert diag.windowed is False and diag.noconsole is False
    assert diag.output_dir == os.path.join(str(tmp_path / "out"), DIAGNOSTIC_DIR)
    assert diag.splash_image == ""
    assert diag.hidden_imports == ["x"]
    assert config.windowed is True  # original untouched


def test_needs_diagnostic_run_only_for_windowed():
    assert needs_diagnostic_run(BuildConfig(windowed=True))
    assert needs_diagnostic_run(BuildConfig(noconsole=True))
    assert not needs_diagnostic_run(BuildConfig())
