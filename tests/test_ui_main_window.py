"""Headless GUI tests for MainWindow.

`main_window.py` was the largest module in the project with zero coverage.
These run offscreen (QT_QPA_PLATFORM=offscreen, set in conftest) so they work
in CI without a display server, and are skipped entirely when no Qt binding is installed
so the core-only test job is unaffected.
"""

import os

import pytest

pytest.importorskip("py2exe_gui.qt", reason="no Qt binding (PySide6/PyQt5) installed")

from py2exe_gui.core import BuildConfig  # noqa: E402
from py2exe_gui.qt import (
    QApplication,  # noqa: E402
    QMessageBox,  # noqa: E402
    Qt,  # noqa: E402
)
from py2exe_gui.strings import S, set_locale  # noqa: E402
from py2exe_gui.ui import streaming_thread  # noqa: E402
from py2exe_gui.ui.conversion_thread import ConversionThread  # noqa: E402
from py2exe_gui.ui.env_thread import CommandThread, TaskThread  # noqa: E402
from py2exe_gui.ui.main_window import BUILD_SECTIONS, NAV_SECTIONS  # noqa: E402
from tests.conftest import MemoryKeyring  # noqa: E402

pytestmark = pytest.mark.gui


class SyncCommandThread(CommandThread):
    """The real CommandThread, run to completion on ``start()``.

    Signals are emitted on the calling thread, so a test sees the window's
    finished slot run before ``start()`` returns and nothing is left running
    when the window closes.
    """

    def start(self, *_args, **_kwargs):
        self.run()

    def isRunning(self):
        return False


class SyncTaskThread(TaskThread):
    def start(self, *_args, **_kwargs):
        self.run()

    def isRunning(self):
        return False


class SyncConversionThread(ConversionThread):
    """A build that finishes immediately with a canned outcome."""

    outcome = (True, "ok", "ok")
    last = None

    def start(self, *_args, **_kwargs):
        SyncConversionThread.last = self
        self.finished_signal.emit(*self.outcome)

    def isRunning(self):
        return False


@pytest.fixture
def sync_workers(monkeypatch):
    monkeypatch.setattr("py2exe_gui.ui.main_window.CommandThread", SyncCommandThread)
    monkeypatch.setattr("py2exe_gui.ui.main_window.TaskThread", SyncTaskThread)


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    """A MainWindow with every persisted file redirected into tmp_path.

    All three must be redirected: a test that wrote presets to the real
    per-user config directory would both leak state into the next test and
    scribble on the config of whoever ran the suite.
    """
    monkeypatch.setattr("py2exe_gui.ui.main_window.SETTINGS_FILE", str(tmp_path / "s.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.HISTORY_FILE", str(tmp_path / "h.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.PRESETS_FILE", str(tmp_path / "p.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.KEYRING", MemoryKeyring())
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


def test_every_former_tab_is_reachable_from_six_sections(window):
    """Fifteen tabs in a row overflowed the window; six sections never do."""
    assert window.tabs.sections() == list(NAV_SECTIONS)
    assert window.tabs.count() == len(window._all_tabs)
    for _key, widget, _title in window._all_tabs:
        assert window.section_of(widget) in NAV_SECTIONS


def test_a_new_user_lands_on_the_build_page_with_the_extras_folded(window):
    """Progressive disclosure replaced the simple/advanced modes."""
    assert window.tabs.current_section() == "build"
    assert window.tabs.currentWidget() is window.main_tab
    assert window.build_page.expanded_keys() == []
    assert set(window.build_page.sections) == set(BUILD_SECTIONS)


def test_navigating_to_a_folded_tab_opens_its_section(window):
    window.tabs.setCurrentWidget(window.deploy_tab)
    assert window.tabs.current_section() == "build"
    assert window.build_page.expanded_keys() == ["deploy"]
    assert window.settings["build_sections"] == ["deploy"]


def test_switching_sections_preserves_field_contents(window):
    """Pages are stacked, never rebuilt, when the person moves around."""
    window.tabs.setCurrentWidget(window.deploy_tab)
    window.deploy_tab.splash_input.setText("splash.png")
    window.tabs.setCurrentWidget(window.doctor_tab)
    window.tabs.setCurrentWidget(window.home_tab)
    window.tabs.setCurrentWidget(window.deploy_tab)
    assert window.deploy_tab.splash_input.text() == "splash.png"


def test_advanced_sections_can_be_opened_together_from_the_view_menu(window):
    window.set_advanced_sections_open(True)
    assert sorted(window.build_page.expanded_keys()) == sorted(BUILD_SECTIONS)
    assert window.advanced_sections_action.isChecked()
    window.set_advanced_sections_open(False)
    assert window.build_page.expanded_keys() == []
    assert not window.advanced_sections_action.isChecked()


def test_a_previous_advanced_mode_choice_opens_the_sections(qapp, tmp_path, monkeypatch):
    """settings['simple_mode'] from 1.x is honoured as the default state."""
    import json

    settings = tmp_path / "s.json"
    settings.write_text(json.dumps({"simple_mode": False}), encoding="utf-8")
    monkeypatch.setattr("py2exe_gui.ui.main_window.SETTINGS_FILE", str(settings))
    monkeypatch.setattr("py2exe_gui.ui.main_window.HISTORY_FILE", str(tmp_path / "h.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.PRESETS_FILE", str(tmp_path / "p.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.KEYRING", MemoryKeyring())
    from py2exe_gui.ui.main_window import MainWindow

    win = MainWindow()
    try:
        assert sorted(win.build_page.expanded_keys()) == sorted(BUILD_SECTIONS)
    finally:
        win.close()


def test_log_receives_startup_messages(window):
    assert window.main_tab.log_output.toPlainText().strip()


# ── Accessibility ──────────────────────────────────────────────────────────


def test_every_icon_only_button_has_an_accessible_name(window):
    """Regression: five identical '📂' buttons announced nothing useful."""
    from py2exe_gui.qt import QPushButton

    bare = []
    for btn in window.findChildren(QPushButton):
        label = btn.text().strip()
        # A button whose visible text is only an emoji needs a spoken name.
        if label and all(not ch.isalnum() for ch in label):
            if not btn.accessibleName() and not btn.toolTip():
                bare.append(label)
    assert not bare, f"icon-only buttons without accessible name/tooltip: {bare}"


def test_every_text_less_button_has_an_icon_a_tooltip_and_a_name(window):
    """2.1: the '📂' buttons became icon buttons; each must still speak."""
    from py2exe_gui.qt import QPushButton

    icon_buttons = [b for b in window.findChildren(QPushButton)
                    if not b.text().strip() and b.property("iconName")]
    assert len(icon_buttons) >= 10, "expected the browse / icon-studio buttons"
    for btn in icon_buttons:
        if btn is window.main_tab.readiness_btn:
            continue  # text is set once there is a score; it is hidden before
        assert not btn.icon().isNull(), btn.property("iconName")
        assert btn.toolTip() and btn.accessibleName(), btn.property("iconName")
        assert btn.width() >= 32 and btn.height() >= 32, btn.property("iconName")
    # And no text-less button that is shown lacks an icon altogether.
    bare = [b for b in window.findChildren(QPushButton)
            if not b.text().strip() and b.isVisibleTo(window) and b.icon().isNull()]
    assert not bare


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
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", staticmethod(fake_question))
    window.clear_history()

    assert asked["value"], "clear_history must confirm before wiping the log"
    assert len(window.history) == 1, "declining must keep the history"


def test_clear_history_proceeds_when_confirmed(window, monkeypatch):
    from py2exe_gui.core import make_record

    window.history.add(make_record("a.py", "a", True, 1.0, {}))
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
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
        return QMessageBox.StandardButton.No

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
        QMessageBox, "information", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    )
    asked = {"value": False}
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: asked.update(value=True) or QMessageBox.StandardButton.Yes),
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
    assert win.layoutDirection() == Qt.LayoutDirection.RightToLeft
    win.close()


def test_english_locale_lays_out_left_to_right(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr("py2exe_gui.ui.main_window.SETTINGS_FILE", str(tmp_path / "s.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.HISTORY_FILE", str(tmp_path / "h.json"))
    set_locale("en")
    from py2exe_gui.ui.main_window import MainWindow

    win = MainWindow()
    assert win.layoutDirection() == Qt.LayoutDirection.LeftToRight
    win.close()


def test_dialogs_follow_the_locale_not_a_hardcoded_direction(qapp):
    """Regression: dialogs forced RTL even in English."""
    from py2exe_gui.ui.dialogs import AddImportDialog

    set_locale("en")
    qapp.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
    dialog = AddImportDialog()
    assert dialog.layoutDirection() == Qt.LayoutDirection.LeftToRight
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
    # 2.0: the projects workspace is the first tab; Main follows it.
    assert window.tabs.tabText(0) == En.TAB_HOME
    assert window.tabs.tabText(window.tabs.indexOf(window.main_tab)) == En.TAB_MAIN
    assert window.layoutDirection() == Qt.LayoutDirection.LeftToRight


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


# ── Font zoom (Phase 9) ────────────────────────────────────────────────────


def test_zoom_in_enlarges_the_stylesheet_fonts(window):
    before = window.font_scale
    window.zoom_in()
    assert window.font_scale > before
    assert window.styleSheet()


def test_zoom_out_shrinks(window):
    window.zoom_in()
    window.zoom_in()
    before = window.font_scale
    window.zoom_out()
    assert window.font_scale < before


def test_zoom_reset_returns_to_default(window):
    from py2exe_gui.styles import DEFAULT_FONT_SCALE

    window.zoom_in()
    window.zoom_reset()
    assert window.font_scale == DEFAULT_FONT_SCALE


def test_zoom_is_clamped_at_both_ends(window):
    from py2exe_gui.styles import MAX_FONT_SCALE, MIN_FONT_SCALE

    for _ in range(50):
        window.zoom_in()
    assert window.font_scale == MAX_FONT_SCALE
    for _ in range(50):
        window.zoom_out()
    assert window.font_scale == MIN_FONT_SCALE


def test_zoom_is_persisted(window):
    window.zoom_in()
    assert window.settings["font_scale"] == window.font_scale


def test_font_scale_survives_a_corrupt_stored_value(window):
    """A hand-edited settings file must not stop the app from painting."""
    from py2exe_gui.styles import clamp_scale

    window.settings["font_scale"] = "enormous"
    assert clamp_scale(window.settings["font_scale"])


# ── Themes (Phase 9) ───────────────────────────────────────────────────────


def test_apply_theme_persists_the_preference(window):
    window.apply_theme("nord")
    assert window.settings["theme"] == "nord"
    assert window.current_theme == "nord"


def test_auto_theme_resolves_to_a_real_palette(window):
    from py2exe_gui.styles import PALETTES

    window.apply_theme("auto")
    assert window.settings["theme"] == "auto"
    assert window.current_theme in PALETTES


def test_toggle_theme_flips_between_dark_and_light(window):
    window.apply_theme("dark")
    window.toggle_theme()
    assert window.current_theme == "light"
    window.toggle_theme()
    assert window.current_theme == "dark"


def test_theme_change_recolours_existing_log_lines(window):
    """Log colours are baked in at append time, so old lines must re-render."""
    window.apply_theme("dark")
    window._append_log("❌ an error line")
    dark_html = window.main_tab.log_output.toHtml()
    window.apply_theme("light")
    assert window.main_tab.log_output.toHtml() != dark_html
    assert "an error line" in window.main_tab.log_output.toPlainText()


def test_theme_selector_reflects_the_active_theme(window):
    window.apply_theme("nord")
    assert window.settings_tab.selected_theme() == "nord"
    assert window.theme_actions["nord"].isChecked()


# ── Log filtering (Phase 9) ────────────────────────────────────────────────


def test_log_filter_shows_only_the_selected_severity(window):
    window.main_tab.clear_log()
    window._append_log("❌ a failure happened")
    window._append_log("just some information")

    index = window.main_tab.log_filter.findData("error")
    window.main_tab.log_filter.setCurrentIndex(index)

    visible = window.main_tab.log_output.toPlainText()
    assert "a failure happened" in visible
    assert "just some information" not in visible


def test_clearing_the_log_filter_restores_every_line(window):
    window.main_tab.clear_log()
    window._append_log("❌ a failure happened")
    window._append_log("just some information")

    window.main_tab.log_filter.setCurrentIndex(
        window.main_tab.log_filter.findData("error")
    )
    window.main_tab.log_filter.setCurrentIndex(window.main_tab.log_filter.findData(""))

    visible = window.main_tab.log_output.toPlainText()
    assert "a failure happened" in visible
    assert "just some information" in visible


def test_filter_with_no_matches_says_so(window):
    from py2exe_gui.strings import S

    window.main_tab.clear_log()
    window._append_log("only an info line")
    window.main_tab.log_filter.setCurrentIndex(
        window.main_tab.log_filter.findData("error")
    )
    assert S.LOG_FILTER_EMPTY in window.main_tab.log_output.toPlainText()


def test_export_writes_every_line_not_just_the_visible_ones(window):
    """Exporting under a filter must not silently drop the rest of the log."""
    window.main_tab.clear_log()
    window._append_log("❌ a failure happened")
    window._append_log("just some information")
    window.main_tab.log_filter.setCurrentIndex(
        window.main_tab.log_filter.findData("error")
    )
    exported = window.main_tab.log_text()
    assert "a failure happened" in exported
    assert "just some information" in exported


def test_clear_log_empties_the_buffer_too(window):
    window._append_log("something")
    window.main_tab.clear_log()
    assert window.main_tab.log_text() == ""


def test_log_filter_survives_a_locale_switch(window):
    window.main_tab.clear_log()
    window._append_log("❌ a failure happened")
    window.retranslate("en")
    assert "a failure happened" in window.main_tab.log_text()


# ── Icon preview (Phase 9) ─────────────────────────────────────────────────


def test_icon_preview_reports_no_icon_when_empty(window):
    from py2exe_gui.strings import S

    window.main_tab.icon_input.setText("")
    assert window.main_tab.icon_status.text() == S.ICON_PREVIEW_NONE


def test_icon_preview_reports_a_missing_file(window):
    from py2exe_gui.strings import S

    window.main_tab.icon_input.setText("/definitely/not/here.ico")
    assert window.main_tab.icon_status.text() == S.ICON_PREVIEW_INVALID


def test_icon_preview_reports_an_unreadable_file(window, tmp_path):
    from py2exe_gui.strings import S

    fake = tmp_path / "not-really.ico"
    fake.write_text("this is not an icon")
    window.main_tab.icon_input.setText(str(fake))
    assert window.main_tab.icon_status.text() == S.ICON_PREVIEW_INVALID


def test_icon_preview_offers_the_windows_sizes(window):
    from py2exe_gui.ui.tabs.main_tab import ICON_PREVIEW_SIZES

    assert [size for size, _slot in window.main_tab.icon_previews] == list(
        ICON_PREVIEW_SIZES
    )


# ── Presets (Phase 10) ─────────────────────────────────────────────────────


def test_saving_a_preset_stores_the_current_config(window, project):
    window.main_tab.source_input.setText(project["source"])
    window.presets.put("my setup", window._current_config().to_dict())
    window._refresh_presets_list()
    assert "my setup" in window.presets.names()
    assert window.templates_tab.selected_preset() == "my setup"


def _select_preset(window, name):
    combo = window.templates_tab.presets_combo
    combo.setCurrentIndex(combo.findData(name))


def test_applying_a_preset_restores_the_form(window):
    window.presets.put("named", BuildConfig(output_name="restored").to_dict())
    window._refresh_presets_list()
    _select_preset(window, "named")
    window.apply_selected_preset()
    assert window.main_tab.output_name.text() == "restored"


def test_empty_preset_list_shows_a_placeholder(window):
    from py2exe_gui.strings import S

    window._refresh_presets_list()
    assert window.templates_tab.presets_combo.currentText() == S.PRESET_NONE
    assert window.templates_tab.selected_preset() == ""


def test_applying_a_preset_with_dangerous_flags_asks_first(window, monkeypatch):
    """A preset file can be shared, so it gets the settings-file treatment."""
    asked = []

    def fake_question(*args, **kwargs):
        asked.append(args)
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", staticmethod(fake_question))
    window.presets.put(
        "hostile", BuildConfig(extra_args="--runtime-hook evil.py").to_dict()
    )
    window._refresh_presets_list()
    _select_preset(window, "hostile")
    window.apply_selected_preset()

    assert asked, "applying a preset with --runtime-hook did not prompt"


def test_presets_survive_a_locale_switch(window):
    window.presets.put("kept", BuildConfig().to_dict())
    window._refresh_presets_list()
    window.retranslate("en")
    assert "kept" in window.templates_tab.presets_combo.itemData(0)


def test_presets_are_not_written_to_the_real_user_config(window, tmp_path):
    """Guards the fixture: PRESETS_FILE must be redirected like the others."""
    window.presets.put("scratch", BuildConfig().to_dict())
    assert str(tmp_path) in window.presets.path


# ── Batch conversion (Phase 10) ────────────────────────────────────────────


def test_batch_queue_starts_empty(window):
    assert window.batch_tab.sources() == []


def test_batch_queue_accepts_files_and_drops_duplicates(window):
    window.batch_tab.set_sources(["a.py", "b.py", "a.py"])
    assert len(window.batch_tab.sources()) == 2


def test_batch_refuses_to_start_with_an_empty_queue(window, monkeypatch):
    warned = []
    monkeypatch.setattr(
        QMessageBox, "warning", staticmethod(lambda *a, **k: warned.append(a))
    )
    window.batch_tab.set_sources([])
    window.start_batch_conversion()
    assert warned
    assert window.batch_thread is None


def test_batch_queue_survives_a_locale_switch(window):
    window.batch_tab.set_sources(["a.py", "b.py"])
    window.retranslate("en")
    assert len(window.batch_tab.sources()) == 2


def test_batch_summary_reports_each_outcome(window):
    from py2exe_gui.core.batch_runner import FAILED, SUCCESS, BatchJob

    jobs = [
        BatchJob("a.py", "a", status=SUCCESS, duration_seconds=1.0),
        BatchJob("b.py", "b", status=FAILED),
    ]
    window.batch_tab.set_sources(["a.py", "b.py"])
    window.batch_tab.show_summary(jobs)
    text = window.batch_tab.summary_label.text()
    assert "2" in text
    assert "b" in text


def test_cancel_button_is_disabled_until_a_batch_runs(window):
    assert window.batch_tab.cancel_btn.isEnabled() is False
    window.batch_tab.set_running(True)
    assert window.batch_tab.cancel_btn.isEnabled() is True
    assert window.batch_tab.start_btn.isEnabled() is False


# ── Platform notices (Phase 9) ─────────────────────────────────────────────


def test_windows_only_tabs_warn_on_other_platforms():
    """The banner names the features rather than silently disabling them."""
    from py2exe_gui.ui.tabs.base import platform_notice

    notice = platform_notice("code_signing", "manifest", platform="linux")
    assert notice is not None
    assert "Linux" in notice.text()


def test_no_platform_notice_on_windows():
    from py2exe_gui.ui.tabs.base import platform_notice

    assert platform_notice("code_signing", platform="win32") is None


def test_cross_platform_features_never_warn():
    from py2exe_gui.ui.tabs.base import platform_notice

    assert platform_notice("splash", "smoke_test", platform="linux") is None


# ── Build stages (Phase 9) ─────────────────────────────────────────────────


def test_stage_signal_labels_the_progress_bar(window):
    window._on_stage_changed("analyzing")
    assert window.progress_bar.format()


def test_unknown_stage_key_leaves_the_bar_alone(window):
    before = window.progress_bar.format()
    window._on_stage_changed("not-a-real-stage")
    assert window.progress_bar.format() == before


# ── Tray (Phase 9) ─────────────────────────────────────────────────────────


def test_tray_is_constructed_without_requiring_a_tray(window):
    """Headless CI has no system tray; construction must still succeed."""
    assert window.tray is not None
    assert isinstance(window.tray.available, bool)


def test_tray_notify_is_a_noop_without_a_tray(window):
    window.tray.notify("title", "body", True)


# ── Startup tasks (Phase 9/10) ─────────────────────────────────────────────


def test_update_check_is_off_by_default(window):
    """The app must not phone home unless the user asked it to."""
    assert not window.settings.get("check_updates_on_start")


def test_startup_update_check_is_skipped_when_not_opted_in(window, monkeypatch):
    called = []
    monkeypatch.setattr(
        "py2exe_gui.ui.main_window.check_for_update",
        lambda *a, **k: called.append(a),
    )
    window._maybe_check_for_updates()
    assert not called


def test_startup_update_check_runs_when_opted_in(window, monkeypatch, sync_workers):
    called = []
    monkeypatch.setattr(
        "py2exe_gui.ui.main_window.check_for_update",
        lambda *a, **k: (called.append(a), None)[1],
    )
    window.settings["check_updates_on_start"] = True
    window._maybe_check_for_updates()
    assert called


def test_update_check_reports_a_newer_release(window, monkeypatch, sync_workers):
    from py2exe_gui.core.update_checker import UpdateInfo

    monkeypatch.setattr(
        "py2exe_gui.ui.main_window.check_for_update",
        lambda *a, **k: UpdateInfo("99.0.0", "https://example.invalid/r"),
    )
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Close)
    )
    window.check_for_updates()
    assert "99.0.0" in window.main_tab.log_text()


def test_update_check_runs_off_the_ui_thread_and_survives_an_error(window, monkeypatch):
    """A slow or absent network must not freeze the window: the check is a
    TaskThread, and an exception in it becomes a log line, not a crash."""
    started = []

    class Worker:
        def __init__(self, task):
            self.task = task
            self.slot = None
            self.finished_signal = self

        def connect(self, slot):
            self.slot = slot

        def start(self):
            started.append(self.task)

        def isRunning(self):
            return False

    monkeypatch.setattr("py2exe_gui.ui.main_window.TaskThread", Worker)
    window.check_for_updates(interactive=False)
    assert len(started) == 1 and window.statusBar().currentMessage() == S.BUSY_UPDATE_CHECK
    window.task_thread.slot(None, "socket timed out")
    assert "socket timed out" in window.main_tab.log_text()
    assert window.statusBar().currentMessage() == S.STATUS_READY


def test_welcome_dialog_only_appears_once(window):
    window.settings["welcomed"] = True
    window.run_startup_tasks()  # must not block on a modal
    assert window.settings["welcomed"] is True


# ── RTL: no double mirroring, percentages read as numbers ──────────────────


def _chevron_images(qapp, tmp_path, monkeypatch, locale):
    """The section chevron pixmap rendered under ``locale``."""
    monkeypatch.setattr("py2exe_gui.ui.main_window.SETTINGS_FILE", str(tmp_path / "s.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.HISTORY_FILE", str(tmp_path / "h.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.PRESETS_FILE", str(tmp_path / "p.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.KEYRING", MemoryKeyring())
    from py2exe_gui.qt import QSize
    from py2exe_gui.ui.main_window import MainWindow

    set_locale(locale)
    win = MainWindow()
    try:
        section = next(iter(win.build_page.sections.values()))
        icon = section._chevrons[1]  # the "closed" chevron, the directional one
        return icon.pixmap(QSize(24, 24)).toImage()
    finally:
        win.close()


def test_section_chevron_is_mirrored_exactly_once_under_rtl(qapp, tmp_path, monkeypatch):
    """chevron_left is in icons.DIRECTIONAL, so asking for it under RTL
    mirrored it twice and the arrow pointed the wrong way."""
    ltr_image = _chevron_images(qapp, tmp_path, monkeypatch, "en")
    rtl_image = _chevron_images(qapp, tmp_path, monkeypatch, "ar")
    assert ltr_image.mirrored(True, False) == rtl_image
    assert ltr_image != rtl_image


def test_progress_percent_is_isolated_under_rtl(window):
    """"%p%" inside an Arabic paragraph rendered as "%42"."""
    from py2exe_gui.bidi import LRI, PDI

    set_locale("ar")
    window.retranslate("ar")
    window.progress_bar.setVisible(True)
    window._on_stage_changed("analyzing")
    window.progress_bar.setValue(42)
    text = window.progress_label.text()
    assert f"{LRI}42%{PDI}" in text
    assert "%p" not in text and "%42" not in text
    assert S.STAGE_ANALYZING in text


def test_busy_bar_shows_no_percentage(window):
    window._set_busy(S.BUSY_ENV)
    assert window.progress_bar.isVisibleTo(window)
    assert window.progress_label.isVisibleTo(window)
    assert window.progress_bar.maximum() == 0
    assert window.progress_label.text() == S.BUSY_ENV
    window._clear_busy()
    assert not window.progress_bar.isVisibleTo(window)
    assert window.progress_bar.maximum() == 100
    assert window.statusBar().currentMessage() == S.STATUS_READY


# ── Feedback: every long task shows the bar ────────────────────────────────


def test_create_build_env_shows_the_busy_bar(window, tmp_path, monkeypatch):
    from tests.test_ui_size import FakeEnvThread, answer, make_source

    monkeypatch.setattr("py2exe_gui.ui.main_window.EnvThread", FakeEnvThread)
    monkeypatch.setattr("py2exe_gui.ui.main_window.find_uv", lambda: "")
    window.main_tab.source_input.setText(make_source(tmp_path))
    answer(monkeypatch, "question", QMessageBox.StandardButton.Yes)
    window.create_build_env()
    assert window.env_thread.started
    assert window.progress_bar.isVisibleTo(window)
    assert window.progress_label.text() == S.BUSY_ENV
    assert not window.convert_btn.isEnabled()


def test_engine_install_runs_on_a_worker_then_continues(window, tmp_path, monkeypatch):
    """Consent on the UI thread; pip on a CommandThread; the build after it."""
    import subprocess

    from tests.test_ui_size import answer, make_source

    window.main_tab.source_input.setText(make_source(tmp_path))
    answer(monkeypatch, "question", QMessageBox.StandardButton.Yes)
    runs = []

    def fake_run(cmd, **_kwargs):
        runs.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="Successfully installed\n", stderr="")

    monkeypatch.setattr("py2exe_gui.ui.env_thread.CommandThread.runner", staticmethod(fake_run))
    # The availability probe (on the UI thread, instant) says "missing".
    monkeypatch.setattr(
        "py2exe_gui.ui.main_window.subprocess.run",
        lambda *a, **k: (_ for _ in ()).throw(OSError("no PyInstaller")),
    )
    started = []

    class Worker(SyncCommandThread):
        def start(self, *args, **kwargs):
            started.append(list(self.command))
            # Nothing is bar-visible after start() in a sync thread, so look now.
            assert window.progress_bar.isVisibleTo(window)
            assert S.BUSY_INSTALLING_FMT.format(tool="PyInstaller") == window.progress_label.text()
            super().start()

    monkeypatch.setattr("py2exe_gui.ui.main_window.CommandThread", Worker)
    continued = []
    assert window._ensure_pyinstaller(then=lambda: continued.append(True)) is False
    assert started and "pip" in started[0] and runs
    assert continued == [True]
    assert not window.progress_bar.isVisibleTo(window)
    assert window.convert_btn.isEnabled()
    assert "Successfully installed" in window.main_tab.log_text()


def test_failed_install_shows_one_sentence_and_logs_pip(window, tmp_path, monkeypatch):
    import subprocess

    from tests.test_ui_size import answer

    answer(monkeypatch, "question", QMessageBox.StandardButton.Yes)
    shown = []
    answer(monkeypatch, "critical", QMessageBox.StandardButton.Ok, shown)
    monkeypatch.setattr(
        "py2exe_gui.ui.env_thread.CommandThread.runner",
        staticmethod(lambda cmd, **_k: subprocess.CompletedProcess(cmd, 1, stdout="ERROR: No matching distribution\n", stderr="")),
    )
    monkeypatch.setattr(
        "py2exe_gui.ui.main_window.subprocess.run",
        lambda *a, **k: (_ for _ in ()).throw(OSError("no PyInstaller")),
    )
    monkeypatch.setattr("py2exe_gui.ui.main_window.CommandThread", SyncCommandThread)
    continued = []
    assert window._ensure_pyinstaller(then=lambda: continued.append(True)) is False
    assert continued == []
    assert shown == [S.MSG_INSTALL_FAILED_FMT.format(tool="PyInstaller")]
    log = window.main_tab.log_text()
    assert "No matching distribution" in log
    assert S.THREAD_ERR_FAILED_FMT.format(tool="pip", code=1) in log


def test_output_folder_failure_is_a_sentence_with_the_detail_in_the_log(
    window, tmp_path, monkeypatch
):
    from tests.test_ui_size import answer, make_source

    window.main_tab.source_input.setText(make_source(tmp_path))
    monkeypatch.setattr(window, "_ensure_engine", lambda *a, **k: True)
    shown = []
    answer(monkeypatch, "critical", QMessageBox.StandardButton.Ok, shown)

    def boom(_config):
        raise OSError("[Errno 13] Permission denied: 'dist'")

    from py2exe_gui.core.engines import get_engine

    monkeypatch.setattr(get_engine("pyinstaller").__class__, "prepare_output",
                        lambda self, config: boom(config))
    window.start_conversion()
    assert shown == [S.MSG_OUTPUT_DIR_FAILED]
    assert "Permission denied" in window.main_tab.log_text()
    assert window.conversion_thread is None


# ── Outcome codes from the threads ─────────────────────────────────────────


def test_cancelled_build_is_told_by_its_status_code(window, monkeypatch):
    """Not by comparing the message against S.CONV_CANCELLED."""
    shown = []
    monkeypatch.setattr(
        QMessageBox, "critical", staticmethod(lambda *a, **k: shown.append(a[2]))
    )
    window._build_start_time = 0.0
    window.on_conversion_finished(False, "whatever text", streaming_thread.CANCELLED)
    assert shown == []
    assert window.statusBar().currentMessage() == S.STATUS_CANCELLED
    window.on_conversion_finished(False, S.CONV_FAILED_MSG, streaming_thread.FAILED)
    assert shown == [S.CONV_FAILED_MSG]
    assert window.statusBar().currentMessage() == S.STATUS_FAILED


def test_thread_error_text_translates_every_code(window):
    thread = type("T", (), {"returncode": 3, "error": "boom"})()
    assert window.thread_error_text(streaming_thread.CANCELLED) == S.THREAD_ERR_CANCELLED
    assert window.thread_error_text(streaming_thread.NOT_FOUND, "ISCC.exe") == \
        S.THREAD_ERR_NOT_FOUND_FMT.format(tool="ISCC.exe")
    assert window.thread_error_text(streaming_thread.FAILED, "ISCC.exe", thread) == \
        S.THREAD_ERR_FAILED_FMT.format(tool="ISCC.exe", code=3)
    assert window.thread_error_text(streaming_thread.ERROR, "x", thread) == \
        S.THREAD_ERR_ERROR_FMT.format(tool="x", error="boom")
    assert window.thread_error_text(streaming_thread.TIMED_OUT, "x") == \
        S.THREAD_ERR_TIMED_OUT_FMT.format(tool="x")


def test_installer_failure_code_is_translated_in_the_window(window, monkeypatch):
    shown = []
    monkeypatch.setattr(
        QMessageBox, "critical", staticmethod(lambda *a, **k: shown.append(a[2]))
    )
    window.installer_thread = type("T", (), {"returncode": 2, "error": "",
                                             "isRunning": lambda s: False})()
    window._on_installer_finished(False, streaming_thread.NOT_FOUND, interactive=True)
    expected = S.THREAD_ERR_NOT_FOUND_FMT.format(tool="ISCC.exe")
    assert expected in window.main_tab.log_text()
    assert shown == [S.LOG_INSTALLER_FAIL.format(error=expected)]
    window._on_installer_finished(False, streaming_thread.CANCELLED, interactive=True)
    assert len(shown) == 1  # a cancel is logged, never a dialog


def test_every_worker_counts_as_a_build_in_progress(window):
    class Running:
        def isRunning(self):
            return True

    for name in ("installer_thread", "post_build_thread", "package_thread",
                 "command_thread", "task_thread"):
        setattr(window, name, Running())
        assert window._build_in_progress(), name
        setattr(window, name, None)
    assert not window._build_in_progress()


def test_close_cancels_and_waits_for_every_running_worker(window, monkeypatch):
    from py2exe_gui.qt import QCloseEvent

    log = []

    class Running:
        def __init__(self, name):
            self.name = name

        def isRunning(self):
            return True

        def cancel(self):
            log.append(("cancel", self.name))

        def wait(self):
            log.append(("wait", self.name))

    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
    )
    window.installer_thread = Running("installer")
    window.post_build_thread = Running("post_build")
    window.package_thread = Running("package")
    event = QCloseEvent()
    window.closeEvent(event)
    assert event.isAccepted()
    assert {n for _, n in log} == {"installer", "post_build", "package"}
    assert ("cancel", "installer") in log and ("wait", "package") in log
    window.installer_thread = window.post_build_thread = window.package_thread = None


# ── Menus ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("locale", ["ar", "en"])
def test_menu_mnemonics_are_present_and_distinct(window, locale):
    """Each top-level menu has an &-mnemonic, and no two share a letter."""
    set_locale(locale)
    window.retranslate(locale)
    titles = [a.text() for a in window.menuBar().actions() if a.menu() is not None]
    letters = []
    for title in titles:
        assert "&" in title, title
        letters.append(title[title.index("&") + 1].lower())
    assert len(letters) == len(set(letters)), titles


# ── Fonts: the primary button scales with Ctrl+= ───────────────────────────


def test_primary_button_font_follows_the_font_scale(window):
    from py2exe_gui.styles import base_point_size

    def point_size(button):
        QApplication.instance().processEvents()
        return button.fontInfo().pointSize()

    window.zoom_reset()
    before = point_size(window.convert_btn)
    assert before == base_point_size("primary")
    window._set_font_scale(2.0)
    after = point_size(window.convert_btn)
    assert after == base_point_size("primary", 2.0) > before
    assert window.doctor_tab.score_label.fontInfo().pointSize() == base_point_size("score", 2.0)
    window.zoom_reset()


def test_prose_text_views_do_not_use_the_log_font(window):
    """The monospace log rule used to leak to every QTextEdit."""
    from py2exe_gui.qt import QFontInfo

    QApplication.instance().processEvents()
    log_family = QFontInfo(window.main_tab.log_output.font()).family()
    detail_family = QFontInfo(window.doctor_tab.detail_view.font()).family()
    body_family = QFontInfo(window.doctor_tab.summary_label.font()).family()
    assert window.main_tab.log_output.objectName() == "logOutput"
    assert detail_family == body_family
    assert window.main_tab.log_output.fontInfo().fixedPitch() or log_family != detail_family
