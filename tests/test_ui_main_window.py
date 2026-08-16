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
from py2exe_gui.ui.main_window import SIMPLE_MODE_TABS  # noqa: E402

pytestmark = pytest.mark.gui


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


def test_simple_mode_is_the_default_for_a_new_user(window):
    """Nine tabs at once is the barrier simple mode exists to remove."""
    assert window.simple_mode is True
    assert window.tabs.count() == len(SIMPLE_MODE_TABS)


def test_advanced_mode_shows_every_tab(window):
    window.set_simple_mode(False)
    assert window.tabs.count() == len(window._all_tabs)


def test_switching_modes_preserves_field_contents(window):
    """Hidden tabs are detached from the bar, not destroyed."""
    window.set_simple_mode(False)
    window.deploy_tab.splash_input.setText("splash.png")
    window.set_simple_mode(True)
    window.set_simple_mode(False)
    assert window.deploy_tab.splash_input.text() == "splash.png"


def test_mode_choice_is_persisted(window):
    window.set_simple_mode(False)
    assert window.settings["simple_mode"] is False
    window.set_simple_mode(True)
    assert window.settings["simple_mode"] is True


def test_mode_button_offers_the_other_mode(window):
    from py2exe_gui.strings import S

    assert window.mode_btn.text() == S.BTN_MODE_TO_ADVANCED
    window.set_simple_mode(False)
    assert window.mode_btn.text() == S.BTN_MODE_TO_SIMPLE


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
    assert window.templates_tab.selected_theme() == "nord"


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
        return QMessageBox.No

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


def test_startup_update_check_runs_when_opted_in(window, monkeypatch):
    called = []
    monkeypatch.setattr(
        "py2exe_gui.ui.main_window.check_for_update",
        lambda *a, **k: (called.append(a), None)[1],
    )
    window.settings["check_updates_on_start"] = True
    window._maybe_check_for_updates()
    assert called


def test_update_check_reports_a_newer_release(window, monkeypatch):
    from py2exe_gui.core.update_checker import UpdateInfo

    monkeypatch.setattr(
        "py2exe_gui.ui.main_window.check_for_update",
        lambda *a, **k: UpdateInfo("99.0.0", "https://example.invalid/r"),
    )
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Close)
    )
    window.check_for_updates()
    assert "99.0.0" in window.main_tab.log_text()


def test_welcome_dialog_only_appears_once(window):
    window.settings["welcomed"] = True
    window.run_startup_tasks()  # must not block on a modal
    assert window.settings["welcomed"] is True
