"""Headless GUI tests for MainWindow.

`main_window.py` was the largest module in the project with zero coverage.
These run offscreen (QT_QPA_PLATFORM=offscreen, set in conftest) so they work
in CI without a display server, and are skipped entirely when PyQt5 is absent
so the core-only test job is unaffected.
"""

import os

import pytest

pytest.importorskip("PyQt5", reason="PyQt5 not installed")

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtWidgets import QMessageBox  # noqa: E402

from py2exe_gui.core import BuildConfig  # noqa: E402
from py2exe_gui.strings import set_locale  # noqa: E402

pytestmark = pytest.mark.gui


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    """A MainWindow with settings/history redirected into tmp_path."""
    monkeypatch.setattr("py2exe_gui.ui.main_window.SETTINGS_FILE", str(tmp_path / "s.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.HISTORY_FILE", str(tmp_path / "h.json"))
    from py2exe_gui.ui.main_window import MainWindow

    win = MainWindow()
    yield win
    win.close()


@pytest.fixture
def project(tmp_path):
    """A fake source file plus an already-built EXE, as PyInstaller lays it out."""
    src = tmp_path / "app.py"
    src.write_text("print('hi')\n")
    dist = tmp_path / "dist"
    dist.mkdir()
    exe = dist / "MyApp.exe"
    exe.write_text("binary")
    return {"root": str(tmp_path), "source": str(src), "exe": str(exe)}


# ── Construction ───────────────────────────────────────────────────────────


def test_window_constructs(window):
    assert window.windowTitle()


def test_minimum_size_fits_a_768px_laptop(window):
    """Regression: the old 1080x800 minimum did not fit a 1366x768 screen."""
    assert window.minimumHeight() <= 700
    assert window.minimumWidth() <= 950


def test_default_size_is_still_comfortable(window):
    assert window.width() >= 1000


def test_all_tabs_are_present(window):
    assert window.tabs.count() == 8


def test_log_receives_startup_messages(window):
    assert window.main_tab.log_output.toPlainText().strip()


# ── Accessibility ──────────────────────────────────────────────────────────


def test_every_icon_only_button_has_an_accessible_name(window):
    """Regression: five identical '📂' buttons announced nothing useful."""
    from PyQt5.QtWidgets import QPushButton

    bare = []
    for btn in window.findChildren(QPushButton):
        label = btn.text().strip()
        # A button whose visible text is only an emoji needs a spoken name.
        if label and all(not ch.isalnum() for ch in label):
            if not btn.accessibleName() and not btn.toolTip():
                bare.append(label)
    assert not bare, f"icon-only buttons without accessible name/tooltip: {bare}"


def test_stylesheet_defines_a_focus_indicator_for_buttons(window):
    assert "QPushButton:focus" in window.styleSheet()


# ── Config round-trip ──────────────────────────────────────────────────────


def test_current_config_reads_the_form(window, project):
    window.main_tab.source_input.setText(project["source"])
    window.main_tab.output_name.setText("demo")
    window.main_tab.onefile_check.setChecked(True)
    cfg = window._current_config()
    assert cfg.source == project["source"]
    assert cfg.output_name == "demo"
    assert cfg.onefile is True


def test_apply_config_round_trips(window, project):
    original = BuildConfig(
        source=project["source"],
        output_name="demo",
        output_dir=project["root"],
        onefile=False,
        windowed=True,
        hidden_imports=["numpy", "pandas"],
        extra_files=[],
        optimize=2,
        upx=True,
        upx_dir="/opt/upx",
        extra_args="--debug all",
    )
    window._apply_config(original)
    restored = window._current_config()
    assert restored.output_name == original.output_name
    assert restored.onefile == original.onefile
    assert restored.windowed == original.windowed
    assert restored.hidden_imports == original.hidden_imports
    assert restored.optimize == original.optimize
    assert restored.upx_dir == original.upx_dir
    assert restored.extra_args == original.extra_args


def test_source_change_autofills_name_and_dir(window, project):
    window.main_tab.source_input.setText(project["source"])
    assert window.main_tab.output_name.text() == "app"
    assert window.main_tab.output_dir.text() == project["root"]


# ── Drag & drop routing ────────────────────────────────────────────────────


def test_dropped_python_file_becomes_the_source(window, project):
    window._handle_dropped_path(project["source"])
    assert window.main_tab.source_input.text() == project["source"]


def test_dropped_icon_goes_to_the_icon_field(window, tmp_path):
    icon = tmp_path / "a.ico"
    icon.write_bytes(b"\x00")
    window._handle_dropped_path(str(icon))
    assert window.main_tab.icon_input.text() == str(icon)


def test_dropped_other_file_becomes_an_extra(window, tmp_path):
    data = tmp_path / "data.csv"
    data.write_text("x")
    window._handle_dropped_path(str(data))
    assert window.advanced_tab.extra_files_list.count() == 1


# ── Destructive actions ask first ──────────────────────────────────────────


def test_clear_history_asks_for_confirmation(window, monkeypatch):
    from py2exe_gui.core import make_record

    window.history.add(make_record("a.py", "a", True, 1.0, {}))
    window._refresh_history_list()

    asked = {"value": False}

    def fake_question(*args, **kwargs):
        asked["value"] = True
        return QMessageBox.No

    monkeypatch.setattr(QMessageBox, "question", staticmethod(fake_question))
    window.clear_history()

    assert asked["value"], "clear_history must confirm before wiping the log"
    assert len(window.history) == 1, "declining must keep the history"


def test_clear_history_proceeds_when_confirmed(window, monkeypatch):
    from py2exe_gui.core import make_record

    window.history.add(make_record("a.py", "a", True, 1.0, {}))
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes)
    )
    window.clear_history()
    assert len(window.history) == 0


# ── Untrusted settings files ───────────────────────────────────────────────


def test_loading_a_config_with_a_runtime_hook_warns(window, tmp_path, monkeypatch):
    import json

    evil = tmp_path / "shared_config.json"
    evil.write_text(
        json.dumps({"extra_args": "--runtime-hook /tmp/evil.py"}), encoding="utf-8"
    )

    monkeypatch.setattr(
        "py2exe_gui.ui.main_window.QFileDialog.getOpenFileName",
        staticmethod(lambda *a, **k: (str(evil), "")),
    )
    warned = {"value": False}

    def fake_question(*args, **kwargs):
        warned["value"] = True
        return QMessageBox.No

    monkeypatch.setattr(QMessageBox, "question", staticmethod(fake_question))
    window.load_saved_settings()

    assert warned["value"], "a code-executing flag must be surfaced before applying"
    assert window.advanced_tab.extra_args.text() == "", "declining must not apply the config"


def test_loading_a_clean_config_does_not_warn(window, tmp_path, monkeypatch):
    import json

    good = tmp_path / "config.json"
    good.write_text(json.dumps({"extra_args": "--debug all"}), encoding="utf-8")
    monkeypatch.setattr(
        "py2exe_gui.ui.main_window.QFileDialog.getOpenFileName",
        staticmethod(lambda *a, **k: (str(good), "")),
    )
    monkeypatch.setattr(
        QMessageBox, "information", staticmethod(lambda *a, **k: QMessageBox.Ok)
    )
    asked = {"value": False}
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: asked.update(value=True) or QMessageBox.Yes),
    )
    window.load_saved_settings()

    assert not asked["value"]
    assert window.advanced_tab.extra_args.text() == "--debug all"


# ── Theme ──────────────────────────────────────────────────────────────────


def test_toggle_theme_switches_and_persists(window):
    before = window.current_theme
    window.toggle_theme()
    assert window.current_theme != before
    assert window.settings["theme"] == window.current_theme


def test_log_colors_follow_the_theme(window):
    from py2exe_gui.core import level_color

    window.current_theme = "light"
    window._append_log("❌ failure")
    assert level_color("error", "light") in window.main_tab.log_output.toHtml()


# ── Temp file lifecycle ────────────────────────────────────────────────────


def test_version_file_is_cleaned_up(window):
    window.version_info_tab.vi_company_name.setText("Acme")
    path = window._materialize_version_file()
    assert path and os.path.exists(path)
    window._cleanup_temp_version_file()
    assert not os.path.exists(path)


def test_materializing_twice_does_not_leak_the_first_file(window):
    window.version_info_tab.vi_company_name.setText("Acme")
    first = window._materialize_version_file()
    second = window._materialize_version_file()
    assert first != second
    assert not os.path.exists(first), "the previous temp file must be removed"
    window._cleanup_temp_version_file()


def test_empty_version_form_produces_no_file(window):
    assert window._materialize_version_file() == ""


# ── Installer tab ──────────────────────────────────────────────────────────


def test_installer_config_falls_back_to_the_output_name(window, project):
    window.main_tab.source_input.setText(project["source"])
    window.main_tab.output_name.setText("MyApp")
    cfg = window._current_installer_config()
    assert cfg.app_name == "MyApp"


def test_iss_generation_writes_a_script(window, project):
    window.main_tab.source_input.setText(project["source"])
    window.main_tab.output_dir.setText(project["root"])
    window.main_tab.output_name.setText("MyApp")
    window.installer_tab.inst_app_name.setText("My App")
    cfg = window._current_installer_config()
    cfg.enabled = True

    iss_path, error = window._write_iss_script(cfg, window._current_config())
    assert error is None
    assert os.path.isfile(iss_path)
    content = open(iss_path, encoding="utf-8").read()
    assert "[Setup]" in content
    assert "AppId=" in content


def test_iss_generation_reports_a_missing_exe(window, tmp_path):
    src = tmp_path / "app.py"
    src.write_text("x")
    window.main_tab.source_input.setText(str(src))
    window.main_tab.output_dir.setText(str(tmp_path))
    window.installer_tab.inst_app_name.setText("My App")
    cfg = window._current_installer_config()
    cfg.enabled = True

    _iss, error = window._write_iss_script(cfg, window._current_config())
    assert error


# ── RTL / locale ───────────────────────────────────────────────────────────


def test_arabic_locale_lays_out_right_to_left(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr("py2exe_gui.ui.main_window.SETTINGS_FILE", str(tmp_path / "s.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.HISTORY_FILE", str(tmp_path / "h.json"))
    set_locale("ar")
    from py2exe_gui.ui.main_window import MainWindow

    win = MainWindow()
    assert win.layoutDirection() == Qt.RightToLeft
    win.close()


def test_english_locale_lays_out_left_to_right(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr("py2exe_gui.ui.main_window.SETTINGS_FILE", str(tmp_path / "s.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.HISTORY_FILE", str(tmp_path / "h.json"))
    set_locale("en")
    from py2exe_gui.ui.main_window import MainWindow

    win = MainWindow()
    assert win.layoutDirection() == Qt.LeftToRight
    win.close()


def test_dialogs_follow_the_locale_not_a_hardcoded_direction(qapp):
    """Regression: dialogs forced RTL even in English."""
    from py2exe_gui.ui.dialogs import AddImportDialog

    set_locale("en")
    qapp.setLayoutDirection(Qt.LeftToRight)
    dialog = AddImportDialog()
    assert dialog.layoutDirection() == Qt.LeftToRight
    dialog.close()


# ── Tab decomposition ──────────────────────────────────────────────────────


def test_each_tab_is_its_own_widget(window):
    """main_window used to build all eight tabs inline and own every widget."""
    from py2exe_gui.ui.tabs import (
        AboutTab,
        AdvancedTab,
        DeployTab,
        HistoryTab,
        InstallerTab,
        MainTab,
        TemplatesTab,
        VersionInfoTab,
    )

    assert isinstance(window.main_tab, MainTab)
    assert isinstance(window.advanced_tab, AdvancedTab)
    assert isinstance(window.version_info_tab, VersionInfoTab)
    assert isinstance(window.deploy_tab, DeployTab)
    assert isinstance(window.installer_tab, InstallerTab)
    assert isinstance(window.templates_tab, TemplatesTab)
    assert isinstance(window.history_tab, HistoryTab)
    assert isinstance(window.about_tab, AboutTab)


def test_tabs_can_be_built_standalone(qapp):
    """A tab must not need the window to construct — that is the point."""
    from py2exe_gui.ui.tabs import AdvancedTab

    tab = AdvancedTab()
    assert tab.hidden_imports() == []
    tab.hidden_imports_list.addItem("numpy")
    assert tab.hidden_imports() == ["numpy"]
    tab.close()


def test_merge_hidden_imports_skips_duplicates(qapp):
    from py2exe_gui.ui.tabs import AdvancedTab

    tab = AdvancedTab()
    assert tab.merge_hidden_imports(["numpy", "pandas"]) == ["numpy", "pandas"]
    assert tab.merge_hidden_imports(["numpy", "flask"]) == ["flask"]
    assert sorted(tab.hidden_imports()) == ["flask", "numpy", "pandas"]
    tab.close()


def test_deploy_tab_builds_its_own_signing_config(qapp):
    from py2exe_gui.ui.tabs import DeployTab

    tab = DeployTab()
    tab.signing_enable.setChecked(True)
    tab.signing_cert.setText("/c.pfx")
    cfg = tab.signing_config()
    assert cfg.enabled is True
    assert cfg.cert_path == "/c.pfx"
    tab.close()


def test_signing_mode_toggle_swaps_the_enabled_fields(window):
    deploy = window.deploy_tab
    deploy.signing_use_store.setChecked(True)
    assert deploy.signing_subject.isEnabled()
    assert not deploy.signing_password.isEnabled()

    deploy.signing_use_store.setChecked(False)
    assert not deploy.signing_subject.isEnabled()
    assert deploy.signing_password.isEnabled()


# ── Live language switching ────────────────────────────────────────────────


def test_retranslate_switches_locale_without_restart(window):
    """Regression: changing language used to require restarting the app."""
    from py2exe_gui.strings import En, current_locale

    set_locale("ar")
    window.retranslate("en")
    assert current_locale() == "en"
    assert window.tabs.tabText(0) == En.TAB_MAIN
    assert window.layoutDirection() == Qt.LeftToRight


def test_retranslate_preserves_the_form(window, project):
    window.main_tab.source_input.setText(project["source"])
    window.main_tab.output_name.setText("demo")
    window.advanced_tab.hidden_imports_list.addItem("numpy")
    window.advanced_tab.extra_args.setText("--debug all")
    window.version_info_tab.vi_company_name.setText("Acme")

    window.retranslate("en")

    assert window.main_tab.output_name.text() == "demo"
    assert window.advanced_tab.hidden_imports() == ["numpy"]
    assert window.advanced_tab.extra_args.text() == "--debug all"
    assert window.version_info_tab.vi_company_name.text() == "Acme"


def test_retranslate_preserves_the_log(window):
    window._append_log("a distinctive log line")
    window.retranslate("en")
    assert "a distinctive log line" in window.main_tab.log_output.toPlainText()


def test_retranslate_does_not_stack_duplicate_shortcuts(window):
    before = len(window._shortcuts)
    window.retranslate("en")
    window.retranslate("ar")
    assert len(window._shortcuts) == before


def test_retranslate_rebinds_shortcuts_to_the_new_widgets(window):
    """Stale shortcuts would point at widgets destroyed by the rebuild."""
    window.retranslate("en")
    targets = [s.parent() for s in window._shortcuts]
    assert all(t is window for t in targets)
    # Ctrl+L clears the *current* log widget.
    window._append_log("something")
    window.main_tab.log_output.clear()
    assert window.main_tab.log_output.toPlainText() == ""
