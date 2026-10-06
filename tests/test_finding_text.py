"""Tests for rendering findings and fixes as text in each locale."""

import pytest

from py2exe_gui.core.fixes import (
    FINDING_CODES,
    FIX_ADD_DATA,
    FIX_CONSOLE,
    SNIPPETS,
    Finding,
    Fix,
    flag_fix,
)
from py2exe_gui.strings import LOCALES, set_locale
from py2exe_gui.ui.finding_text import (
    copy_text,
    detail_lines,
    finding_detail,
    finding_label,
    finding_title,
    fix_label,
    origin_label,
)

# Every placeholder any finding template uses, so formatting never raises.
ALL_PARAMS = {
    "module": "yaml", "pip": "PyYAML", "package": "flask", "folder": "templates",
    "bindings": "PyQt5, PySide6", "binding": "PyQt5", "path": "data.json",
    "literal": "data.json", "example": "data.json", "stream": "sys.stdout",
    "candidate": "main.py", "icon": "app.ico", "size": "32", "error": "boom",
    "line": "3", "template": "index.html", "attr": "write", "drop": "PySide6",
    "url": "http://example.com/u.json", "version": "1.x",
    # 2.0: engines
    "engine": "Nuitka", "feature": "manifest", "nuitka": "4.2.2", "plugin": "tk-inter",
    "reason": "Tkinter needs TCL included.", "tool": "patchelf", "compiler": "gcc",
}


@pytest.mark.parametrize("locale", sorted(LOCALES))
def test_every_code_renders_without_leftover_placeholders(locale):
    set_locale(locale)
    for code in FINDING_CODES:
        finding = Finding(code, "error", dict(ALL_PARAMS))
        title, detail = finding_title(finding), finding_detail(finding)
        assert title and "{" not in title, code
        assert "{" not in detail, code


def test_unknown_code_falls_back_to_the_code():
    assert finding_title(Finding("not_a_code", "info")) == "not_a_code"


def test_missing_param_does_not_raise():
    set_locale("en")
    # The template expects {module}; rendering must degrade, not crash.
    assert finding_title(Finding("missing_package", "error", {}))


def test_label_carries_the_severity_icon():
    set_locale("en")
    assert finding_label(Finding("syntax_error", "error", {"line": "1", "error": "x"})).startswith("❌")


def test_fix_labels_show_basenames_for_paths(tmp_path):
    set_locale("en")
    assert fix_label(Fix(FIX_ADD_DATA, str(tmp_path / "assets"))).endswith("assets")
    assert "--collect-data docx" in fix_label(flag_fix("--collect-data", "docx"))
    assert fix_label(Fix(FIX_CONSOLE))


def test_origin_labels_are_translated():
    set_locale("ar")
    assert origin_label("runtime") != "runtime"


def test_copy_text_prefers_snippet_then_pip():
    assert copy_text(Finding("relative_paths", "warning", snippet="resource_path")) == (
        SNIPPETS["resource_path"]
    )
    pip = Finding("missing_package", "error", {"module": "yaml", "pip": "PyYAML"})
    assert copy_text(pip) == "pip install PyYAML"
    assert copy_text(Finding("large_package", "info", {"package": "pandas"})) == ""


def test_detail_includes_fixes_note_and_snippet():
    set_locale("en")
    finding = Finding(
        "package_console_streams",
        "error",
        {"package": "tqdm"},
        (Fix(FIX_CONSOLE),),
        snippet="silence_streams",
    )
    text = "\n".join(detail_lines(finding))
    assert "tqdm" in text
    assert "Turn the console back on" in text
    assert "sys.stdout is None" in text  # the snippet
    assert "sys.stderr" in text  # the knowledge-base note
