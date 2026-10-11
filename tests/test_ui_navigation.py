"""The 2.1 window chrome: side navigation, Build page sections, log panel,
menus, action bar and status bar. Headless (offscreen)."""

import pytest

pytest.importorskip("py2exe_gui.qt", reason="no Qt binding (PySide6/PyQt5) installed")

from py2exe_gui.qt import QLabel, Qt, QWidget  # noqa: E402
from py2exe_gui.strings import Ar, En, S  # noqa: E402
from py2exe_gui.ui.log_panel import LogPanel  # noqa: E402
from py2exe_gui.ui.navigation import SectionView  # noqa: E402
from py2exe_gui.ui.widgets import CollapsibleSection  # noqa: E402
from tests.conftest import MemoryKeyring  # noqa: E402

pytestmark = pytest.mark.gui


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr("py2exe_gui.ui.main_window.SETTINGS_FILE", str(tmp_path / "s.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.HISTORY_FILE", str(tmp_path / "h.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.PRESETS_FILE", str(tmp_path / "p.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.KEYRING", MemoryKeyring())
    from py2exe_gui.ui.main_window import MainWindow

    win = MainWindow()
    yield win
    win.close()


# ── SectionView, on its own ────────────────────────────────────────────────


def _view():
    view = SectionView()
    a, b, c, d = QLabel("a"), QLabel("b"), QLabel("c"), QLabel("d")
    page = QWidget()
    view.add_section("one", "One", tabbed=True)
    view.add_section("two", "Two", page=page)
    view.add_page("one", a, "A")
    view.add_page("one", b, "B")
    opened = []
    view.add_page("two", c, "C")
    view.add_page("two", d, "D", reveal=lambda: opened.append("d"))
    view.finish()
    return view, (a, b, c, d), opened


def test_section_view_speaks_the_tab_widget_api(qapp):
    view, (a, b, c, d), _opened = _view()
    assert view.count() == 4
    assert [view.tabText(i) for i in range(4)] == ["A", "B", "C", "D"]
    assert view.widget(2) is c and view.indexOf(d) == 3 and view.indexOf(QLabel()) == -1
    assert view.sections() == ["one", "two"]
    assert view.current_section() == "one" and view.currentWidget() is a
    view.close()


def test_section_view_navigates_into_sub_tabs_and_composed_pages(qapp):
    view, (a, b, c, d), opened = _view()
    view.setCurrentWidget(b)
    assert view.current_section() == "one" and view.currentWidget() is b
    assert view.currentIndex() == 1
    view.setCurrentWidget(d)
    assert view.current_section() == "two"
    # A composed page reports its first leaf; the reveal hook ran for d.
    assert view.currentWidget() is c and opened == ["d"]
    view.setCurrentIndex(0)
    assert view.currentWidget() is a
    view.close()


def test_section_view_emits_the_leaf_index(qapp):
    view, (a, b, c, _d), _opened = _view()
    seen = []
    view.currentChanged.connect(seen.append)
    view.setCurrentWidget(b)
    view.setCurrentWidget(c)
    assert seen[-2:] == [1, 2]
    view.close()


def test_nav_collapses_to_icons(qapp):
    view, _widgets, _opened = _view()
    full = view.nav.width()
    view.set_collapsed(True)
    assert view.nav.is_collapsed() and view.nav.width() < full
    assert view.nav.item(0).text() == "" and view.nav.item(0).toolTip() == "One"
    view.set_collapsed(False)
    assert view.nav.item(0).text() == "One"
    view.close()


# ── CollapsibleSection ─────────────────────────────────────────────────────


def test_collapsible_section_folds_and_reports(qapp):
    content = QLabel("inside")
    section = CollapsibleSection("Title", content, subtitle="2 things")
    seen = []
    section.toggled.connect(seen.append)
    assert not section.is_expanded() and section.body.isHidden()
    assert section.header.text() == "Title" and section.subtitle.text() == "2 things"
    section.set_expanded(True)
    assert section.is_expanded() and not section.body.isHidden() and seen == [True]
    section.set_expanded(True)  # idempotent: no second signal
    assert seen == [True]
    section.set_subtitle("")
    assert section.subtitle.isHidden()
    section.close()


def test_collapsible_arrow_points_into_the_reading_direction(qapp):
    section = CollapsibleSection("T", QLabel("x"))
    section.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
    assert section.header.arrowType() == Qt.ArrowType.RightArrow
    section.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    assert section.header.arrowType() == Qt.ArrowType.LeftArrow
    section.set_expanded(True)
    assert section.header.arrowType() == Qt.ArrowType.DownArrow
    section.close()


# ── LogPanel ───────────────────────────────────────────────────────────────


def test_log_panel_folds_to_the_last_line(qapp):
    panel = LogPanel()
    assert not panel.is_expanded()
    assert panel.last_label.text() == S.LOG_PANEL_EMPTY
    panel.append_log("first")
    panel.append_log("❌ something failed")
    assert panel.last_label.text() == "❌ something failed"
    assert panel.log_text() == "first\n❌ something failed"
    panel.set_expanded(True)
    assert panel.is_expanded() and not panel.log_output.isHidden()
    panel.clear_log()
    assert panel.log_text() == "" and panel.last_label.text() == S.LOG_PANEL_EMPTY
    panel.close()


def test_log_panel_filter_and_restore(qapp):
    panel = LogPanel()
    panel.append_log("✅ ok")
    panel.append_log("❌ bad")
    panel.log_filter.setCurrentIndex(panel.log_filter.findData("error"))
    assert "bad" in panel.log_output.toPlainText()
    assert "ok" not in panel.log_output.toPlainText()
    lines = panel.log_lines()
    other = LogPanel()
    other.restore_log(lines)
    assert other.log_text() == panel.log_text()
    assert other.last_label.text() == "❌ bad"
    panel.close()
    other.close()


# ── The window ─────────────────────────────────────────────────────────────


def test_window_has_four_menus_in_both_languages(window):
    titles = [a.text() for a in window.menuBar().actions()]
    assert titles == [Ar.MENU_PROJECT, Ar.MENU_VIEW, Ar.MENU_TOOLS, Ar.MENU_HELP]
    window.retranslate("en")
    titles = [a.text() for a in window.menuBar().actions()]
    assert titles == [En.MENU_PROJECT, En.MENU_VIEW, En.MENU_TOOLS, En.MENU_HELP]


def test_theme_menu_tracks_the_theme(window):
    assert window.theme_actions["dark"].isChecked()
    window.theme_actions["light"].trigger()
    assert window.settings["theme"] == "light"
    assert window.theme_actions["light"].isChecked()
    assert not window.theme_actions["dark"].isChecked()
    assert window.settings_tab.selected_theme() == "light"


def test_language_menu_switches_the_locale(window):
    window.language_actions["en"].trigger()
    assert window.settings["locale"] == "en"
    assert window.tabs.tabText(0) == En.TAB_HOME
    assert window.language_actions["en"].isChecked()


def test_settings_page_theme_selector_applies_the_theme(window):
    window.settings_tab.theme_combo.setCurrentIndex(
        window.settings_tab.theme_combo.findData("nord"))
    assert window.settings["theme"] == "nord"


def test_log_panel_opens_with_the_build_and_the_menu_follows(window):
    assert not window.log_panel.is_expanded()
    assert not window.show_log_action.isChecked()
    window._set_building(True)
    window.log_panel.set_expanded(True)
    assert window.show_log_action.isChecked()
    assert window.settings["log_open"] is True
    window.show_log_action.trigger()
    assert not window.log_panel.is_expanded()


def test_progress_bar_is_hidden_until_a_build(window):
    assert not window.progress_bar.isVisibleTo(window)


def test_stage_changes_reach_the_status_bar(window):
    window._on_stage_changed("analyzing")
    assert Ar.STAGE_ANALYZING in window.statusBar().currentMessage()
    assert Ar.STAGE_ANALYZING in window.progress_bar.format()


def test_status_bar_starts_ready_and_names_the_interpreter(window):
    assert window.statusBar().currentMessage() == Ar.STATUS_READY
    assert "Python" in window.status_versions.text()


def test_zoom_updates_the_settings_page(window):
    window.zoom_in()
    assert window.settings_tab.font_value.text() == Ar.FONT_SIZE_FMT.format(percent=110)
    window.zoom_reset()
    assert window.settings_tab.font_value.text() == Ar.FONT_SIZE_FMT.format(percent=100)


def test_section_shortcuts_are_bound(window):
    from py2exe_gui.ui.main_window import NAV_SECTIONS

    sequences = [s.key().toString() for s in window._shortcuts]
    for number in range(1, len(NAV_SECTIONS) + 1):
        assert f"Ctrl+{number}" in sequences
    table = window.shortcut_table()
    assert any("Ctrl+B" == keys for keys, _d in table)
    assert any(Ar.SECTION_BUILD in d for _k, d in table)


def test_shortcuts_dialog_lists_every_binding(window):
    from py2exe_gui.ui.dialogs import ShortcutsDialog

    dialog = ShortcutsDialog(window.shortcut_table(), parent=window)
    assert dialog.rows() == window.shortcut_table()
    dialog.close()


def test_page_bar_names_the_section_and_the_file(window, tmp_path):
    assert window.page_title.text() == Ar.SECTION_BUILD
    assert window.page_file.text() == Ar.PAGE_FILE_NONE
    window.tabs.setCurrentWidget(window.doctor_tab)
    assert window.page_title.text() == Ar.SECTION_CHECK
    script = tmp_path / "app.py"
    script.write_text("print(1)\n")
    window.main_tab.source_input.setText(str(script))
    assert "app.py" in window.page_file.text()


def test_build_section_summaries_follow_the_form(window):
    files = window.build_page.sections["advanced"]
    assert files.subtitle.text() == Ar.BUILD_SUMMARY_NONE
    window.advanced_tab.hidden_imports_list.addItem("numpy")
    window._update_modified()
    assert "1" in files.subtitle.text()
    pre_post = window.build_page.sections["deploy"]
    assert pre_post.subtitle.text() == Ar.BUILD_SUMMARY_PRE_POST_NONE
    window.deploy_tab.signing_enable.setChecked(True)
    window._update_modified()
    assert Ar.BUILD_SUMMARY_SIGNING in pre_post.subtitle.text()


def test_retranslate_keeps_the_section_and_the_log_state(window):
    window.tabs.setCurrentWidget(window.release_tab)
    window.log_panel.set_expanded(True)
    window._append_log("kept")
    window.retranslate("en")
    assert window.tabs.currentWidget() is window.release_tab
    assert window.log_panel.is_expanded()
    assert "kept" in window.main_tab.log_text()
    assert window.page_title.text() == En.SECTION_DISTRIBUTE


def test_no_welcome_dialog_and_no_mode_button(window):
    from py2exe_gui.qt import QPushButton

    assert not hasattr(window, "mode_btn") and not hasattr(window, "theme_btn")
    texts = [b.text() for b in window.findChildren(QPushButton)]
    assert Ar.BTN_CONVERT in texts
    window.run_startup_tasks()  # nothing modal
    assert window.settings.get("welcomed") is True
