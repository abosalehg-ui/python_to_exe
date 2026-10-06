"""Headless GUI tests for the Doctor tab, its wiring, and Icon Studio."""

import os
import stat
import sys

import pytest

pytest.importorskip("PyQt5", reason="PyQt5 not installed")

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtGui import QColor, QImage  # noqa: E402
from PyQt5.QtWidgets import QMessageBox  # noqa: E402

from py2exe_gui.core import BuildConfig, Finding  # noqa: E402
from py2exe_gui.core.icon_studio import ICO_SIZES, read_ico_file_sizes  # noqa: E402
from py2exe_gui.strings import En, set_locale  # noqa: E402
from py2exe_gui.ui.main_window import SIMPLE_MODE_TABS  # noqa: E402

pytestmark = pytest.mark.gui


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr("py2exe_gui.ui.main_window.SETTINGS_FILE", str(tmp_path / "s.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.HISTORY_FILE", str(tmp_path / "h.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.PRESETS_FILE", str(tmp_path / "p.json"))
    from py2exe_gui.ui.main_window import MainWindow

    win = MainWindow()
    yield win
    win.close()


def make_source(tmp_path, code):
    path = tmp_path / "proj" / "app.py"
    path.parent.mkdir(exist_ok=True)
    path.write_text(code, encoding="utf-8")
    return str(path)


def list_codes(window):
    items = []
    lst = window.doctor_tab.findings_list
    for row in range(lst.count()):
        finding = lst.item(row).data(Qt.UserRole)
        if finding is not None:
            items.append(finding.code)
    return items


# ── Tab and badge ──────────────────────────────────────────────────────────


def test_doctor_tab_is_part_of_simple_mode(window):
    assert "doctor" in SIMPLE_MODE_TABS
    shown = [window.tabs.widget(i) for i in range(window.tabs.count())]
    assert window.doctor_tab in shown
    assert len(shown) == len(SIMPLE_MODE_TABS)


def test_without_a_source_the_badge_is_hidden(window):
    window.run_doctor()
    assert window.main_tab.readiness_btn.isHidden()
    assert window.doctor_tab.apply_btn.isEnabled() is False


def test_examining_a_script_fills_the_list_and_badge(window, tmp_path):
    source = make_source(tmp_path, 'import docx\nopen("x.txt")\n')
    window.main_tab.source_input.setText(source)
    window.run_doctor()

    assert "package_needs_collect" in list_codes(window)
    assert not window.main_tab.readiness_btn.isHidden()
    assert "/100" in window.main_tab.readiness_btn.text()
    assert window.doctor_tab.apply_btn.isEnabled()


def test_clean_script_shows_all_clear(window, tmp_path):
    set_locale("en")
    window.retranslate("en")
    window.main_tab.source_input.setText(make_source(tmp_path, "print(1)\n"))
    window.run_doctor()
    assert window.doctor_tab.findings_list.item(0).text() == En.DOCTOR_ALL_CLEAR
    assert window.main_tab.readiness_btn.text() == "🩺 100/100"


def test_badge_opens_the_doctor_tab(window, tmp_path):
    window.main_tab.source_input.setText(make_source(tmp_path, "print(1)\n"))
    window.run_doctor()
    window.main_tab.readiness_btn.click()
    assert window.tabs.currentWidget() is window.doctor_tab


def test_selecting_a_finding_shows_details_and_copy(window, tmp_path):
    source = make_source(tmp_path, "import multiprocessing\nmultiprocessing.Pool()\n")
    window.main_tab.source_input.setText(source)
    window.run_doctor()
    tab = window.doctor_tab
    row = list_codes(window).index("missing_freeze_support")
    tab.findings_list.setCurrentRow(row)
    assert "freeze_support" in tab.detail_view.toPlainText()
    assert tab.copy_btn.isEnabled()

    tab.copy_selected()
    from PyQt5.QtWidgets import QApplication

    assert "freeze_support()" in QApplication.clipboard().text()


# ── Applying fixes ─────────────────────────────────────────────────────────


def test_apply_fixes_updates_the_form(window, tmp_path):
    source = make_source(tmp_path, "import tkcalendar\nimport docx\nprint(1)\n")
    window.main_tab.source_input.setText(source)
    window.run_doctor()
    window.doctor_tab._apply(rebuild=False)

    assert "babel.numbers" in window.advanced_tab.hidden_imports()
    assert "--collect-data docx" in window.advanced_tab.extra_args.text()
    assert "package_needs_collect" not in list_codes(window)
    assert "babel.numbers" in window.main_tab.log_text()


def test_unticked_findings_are_not_applied(window, tmp_path):
    source = make_source(tmp_path, "import docx\nprint(1)\n")
    window.main_tab.source_input.setText(source)
    window.run_doctor()
    lst = window.doctor_tab.findings_list
    for row in range(lst.count()):
        lst.item(row).setCheckState(Qt.Unchecked)
    assert window.doctor_tab.checked_fixes() == []


def test_apply_with_nothing_selected_says_so(window, monkeypatch):
    shown = {}
    monkeypatch.setattr(
        QMessageBox, "information",
        staticmethod(lambda *a, **k: shown.update(text=a[2]) or QMessageBox.Ok),
    )
    window.apply_doctor_fixes([])
    assert shown


def test_apply_and_rebuild_starts_a_build(window, tmp_path, monkeypatch):
    source = make_source(tmp_path, "import docx\nprint(1)\n")
    window.main_tab.source_input.setText(source)
    window.run_doctor()
    started = {}
    monkeypatch.setattr(window, "start_conversion", lambda: started.update(ok=True))
    window.doctor_tab._apply(rebuild=True)
    assert started.get("ok")


def test_console_fix_unticks_windowed(window, tmp_path):
    source = make_source(tmp_path, 'name = input("?")\n')
    window.main_tab.source_input.setText(source)
    window.main_tab.windowed_check.setChecked(True)
    window.run_doctor()
    assert "input_in_windowed" in list_codes(window)
    window.doctor_tab._apply(rebuild=False)
    assert window.main_tab.windowed_check.isChecked() is False
    assert "input_in_windowed" not in list_codes(window)


# ── Build and runtime findings ─────────────────────────────────────────────


def test_build_log_findings_are_shown(window, tmp_path):
    source = make_source(tmp_path, "import PyQt5\nprint(1)\n")
    window.main_tab.source_input.setText(source)
    window.run_doctor()
    window._build_output = [
        "ERROR: Aborting build process due to attempt to collect multiple Qt "
        "bindings packages: attempting to run hook for 'PySide6', while hook for "
        "'PyQt5' has already been run!"
    ]
    found = window._diagnose_build(BuildConfig(source=source))
    assert [f.code for f in found] == ["multiple_qt_bindings_build"]
    assert list_codes(window)[0] == "multiple_qt_bindings_build"


def test_failed_build_message_mentions_the_doctor(window, tmp_path, monkeypatch):
    source = make_source(tmp_path, "print(1)\n")
    window.main_tab.source_input.setText(source)
    window._build_config_snapshot = BuildConfig(source=source).to_dict()
    window._build_output = ["/usr/bin/python3: No module named PyInstaller"]
    shown = {}
    monkeypatch.setattr(
        QMessageBox, "critical",
        staticmethod(lambda *a, **k: shown.update(text=a[2]) or QMessageBox.Ok),
    )
    from py2exe_gui.strings import S

    window.on_conversion_finished(False, S.CONV_FAILED_MSG)
    assert "🩺" in shown["text"]


def test_smoke_output_is_diagnosed(window, tmp_path):
    source = make_source(tmp_path, "print(1)\n")
    window.main_tab.source_input.setText(source)
    window.run_doctor()
    output = (
        "Traceback (most recent call last):\n"
        "ModuleNotFoundError: No module named 'json'\n"  # stdlib: installed
    )
    window._on_smoke_result(BuildConfig(source=source), False, output)
    assert "runtime_missing_module" in list_codes(window)


def test_windowed_pass_suggests_the_diagnostic_run(window, tmp_path):
    set_locale("en")
    source = make_source(tmp_path, "print(1)\n")
    window._on_smoke_result(BuildConfig(source=source, windowed=True), True, "")
    assert "Diagnostic run" in window.main_tab.log_text()


def test_build_findings_are_dropped_when_the_source_changes(window, tmp_path):
    a = make_source(tmp_path, "print(1)\n")
    window.main_tab.source_input.setText(a)
    window._set_build_findings([Finding("file_locked", "error", {"path": "x"})], a)
    other = tmp_path / "other.py"
    other.write_text("print(2)\n")
    window.main_tab.source_input.setText(str(other))
    window.run_doctor()
    assert window._build_findings == []


def test_findings_survive_a_language_switch(window, tmp_path):
    source = make_source(tmp_path, "import docx\nprint(1)\n")
    window.main_tab.source_input.setText(source)
    window.run_doctor()
    window.retranslate("en")
    assert "package_needs_collect" in list_codes(window)
    assert "needs files" in window.doctor_tab.findings_list.item(0).text()


# ── Diagnostic run ─────────────────────────────────────────────────────────


def test_diagnostic_run_needs_a_source(window, monkeypatch):
    warned = {}
    monkeypatch.setattr(
        QMessageBox, "warning",
        staticmethod(lambda *a, **k: warned.update(ok=True) or QMessageBox.Ok),
    )
    window.start_diagnostic_run()
    assert warned.get("ok")
    assert window.diagnostic_thread is None


def test_diagnostic_result_replaces_build_findings(window, tmp_path):
    source = make_source(tmp_path, "print(1)\n")
    window.main_tab.source_input.setText(source)
    window._on_diagnostic_finished(
        BuildConfig(source=source),
        True,
        "RuntimeError: input(): lost sys.stdin",
        "",
    )
    assert list_codes(window)[0] == "input_in_windowed"
    assert window.tabs.currentWidget() is window.doctor_tab
    assert window.progress_bar.maximum() == 100


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only fake executable")
def test_diagnostic_thread_builds_runs_and_reports(qapp, tmp_path):
    from py2exe_gui.ui.diagnostic_thread import DiagnosticThread

    out = tmp_path / "diag"
    # The "build" step: a command that lays out dist/app as PyInstaller would.
    exe = out / "dist" / "app"
    script = (
        "import os, stat\n"
        f"p = {str(exe)!r}\n"
        "os.makedirs(os.path.dirname(p), exist_ok=True)\n"
        "open(p, 'w').write('#!/bin/sh\\necho \"ModuleNotFoundError: No module named \\'zz\\'\" >&2\\nexit 1\\n')\n"
        "os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR)\n"
        "print('built')\n"
    )
    config = BuildConfig(source=str(tmp_path / "app.py"), output_dir=str(out))
    thread = DiagnosticThread([sys.executable, "-c", script], config, timeout=5)
    results = []
    thread.finished_signal.connect(lambda *args: results.append(args))
    thread.run()  # synchronously: signals deliver directly on this thread

    built, output, build_log = results[0]
    assert built is True
    assert "No module named 'zz'" in output
    assert "built" in build_log
    assert os.stat(exe).st_mode & stat.S_IXUSR


def test_diagnostic_thread_reports_a_failed_build(qapp, tmp_path):
    from py2exe_gui.ui.diagnostic_thread import DiagnosticThread

    config = BuildConfig(source=str(tmp_path / "app.py"), output_dir=str(tmp_path / "d"))
    thread = DiagnosticThread(
        [sys.executable, "-c", "import sys; print('boom'); sys.exit(2)"], config
    )
    results = []
    thread.finished_signal.connect(lambda *args: results.append(args))
    thread.run()
    assert results[0][0] is False
    assert "boom" in results[0][2]


# ── Icon Studio ────────────────────────────────────────────────────────────


def test_icon_studio_writes_every_size_from_letters(qapp, tmp_path):
    from py2exe_gui.ui.icon_studio_dialog import IconStudioDialog

    dialog = IconStudioDialog(app_name="My Tool")
    assert dialog.text_input.text() == "MT"
    path = str(tmp_path / "out.ico")
    dialog.write_to(path)
    assert read_ico_file_sizes(path) == list(ICO_SIZES)
    assert dialog.saved_path == path


def test_icon_studio_from_an_image(qapp, tmp_path):
    from py2exe_gui.ui.icon_studio_dialog import IconStudioDialog

    image = QImage(300, 200, QImage.Format_ARGB32)
    image.fill(QColor("red"))
    png = str(tmp_path / "logo.png")
    assert image.save(png)

    dialog = IconStudioDialog()
    assert dialog.set_image(png)
    assert dialog.image_mode.isChecked()
    rendered = dialog.render(64)
    assert (rendered.width(), rendered.height()) == (64, 64)
    # Fitted, not stretched: the top row of a 3:2 image is transparent.
    assert rendered.pixelColor(32, 0).alpha() == 0
    assert rendered.pixelColor(32, 32).alpha() == 255
    path = str(tmp_path / "img.ico")
    dialog.write_to(path)
    assert read_ico_file_sizes(path) == list(ICO_SIZES)


def test_icon_studio_rejects_a_non_image(qapp, tmp_path):
    from py2exe_gui.ui.icon_studio_dialog import IconStudioDialog

    bogus = tmp_path / "x.png"
    bogus.write_text("not an image")
    assert IconStudioDialog().set_image(str(bogus)) is False


def test_icon_studio_with_nothing_to_draw_raises(qapp, tmp_path):
    from py2exe_gui.ui.icon_studio_dialog import IconStudioDialog

    dialog = IconStudioDialog()
    dialog.text_input.setText("")
    with pytest.raises(ValueError):
        dialog.build_ico()


def test_open_icon_studio_sets_the_icon_field(window, tmp_path, monkeypatch):
    target = str(tmp_path / "made.ico")

    def fake_exec(dialog):
        dialog.write_to(target)
        return True

    monkeypatch.setattr("py2exe_gui.ui.icon_studio_dialog.IconStudioDialog.exec_", fake_exec)
    window.open_icon_studio()
    assert window.main_tab.icon_input.text() == target


def test_already_applied_fixes_are_not_offered_again(window, tmp_path):
    source = make_source(tmp_path, "print(1)\n")
    assets = os.path.join(os.path.dirname(source), "assets")
    os.mkdir(assets)
    window.main_tab.source_input.setText(source)
    window.advanced_tab.extra_files_list.addItem(assets)
    from py2exe_gui.core import Fix

    finding = Finding(
        "missing_data_file", "error", {"path": "assets/a.json"},
        (Fix("add_data", assets),), origin="runtime", snippet="resource_path",
    )
    window._set_build_findings([finding], source)
    shown = window._build_findings[0]
    assert shown.fixes == ()
    assert shown.snippet == "resource_path"  # the advice that actually helps stays
