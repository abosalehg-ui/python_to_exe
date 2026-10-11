"""Headless GUI tests for the projects workspace (the Home tab)."""

import json
import os

import pytest

pytest.importorskip("py2exe_gui.qt", reason="no Qt binding (PySide6/PyQt5) installed")

from py2exe_gui.core.build_history import make_record  # noqa: E402
from py2exe_gui.core.project_file import ProjectConfig, save_project  # noqa: E402
from py2exe_gui.core.workspace import ProjectSummary  # noqa: E402
from py2exe_gui.qt import (
    QMessageBox,  # noqa: E402
    Qt,  # noqa: E402
)
from py2exe_gui.strings import Ar, En, set_locale  # noqa: E402
from py2exe_gui.ui.main_window import SIMPLE_MODE_TABS  # noqa: E402
from py2exe_gui.ui.tabs.home_tab import HomeTab, ProjectCard, SizeSparkline  # noqa: E402
from tests.conftest import MemoryKeyring  # noqa: E402

pytestmark = pytest.mark.gui


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr("py2exe_gui.ui.main_window.SETTINGS_FILE", str(tmp_path / "s.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.HISTORY_FILE", str(tmp_path / "h.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.PRESETS_FILE", str(tmp_path / "p.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.ENVS_ROOT", str(tmp_path / "envs"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.SIGNING_KEY_FILE",
                        str(tmp_path / "signing" / "k.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.KEYRING", MemoryKeyring())
    from py2exe_gui.ui.main_window import MainWindow

    win = MainWindow()
    yield win
    win.close()


def make_project(folder, name="أداتي", version="1.2.0", output="Tool"):
    folder.mkdir(parents=True, exist_ok=True)
    script = folder / "tool.py"
    script.write_text("print('hi')\n")
    config = ProjectConfig(name=name, version=version)
    config.build.source = str(script)
    config.build.output_name = output
    return save_project(config, str(folder / "p2e.toml")), str(script)


def answer(monkeypatch, kind, reply):
    monkeypatch.setattr(QMessageBox, kind, staticmethod(lambda *a, **k: reply))


def texts(card):
    """Every label on a card, without the bidi marks the view adds."""
    from py2exe_gui.qt import QLabel

    joined = "\n".join(label.text() for label in card.findChildren(QLabel))
    return joined.replace("\u2066", "").replace("\u2069", "").replace("\u200f", "")


# ── The tab ───────────────────────────────────────────────────────────────


def test_home_is_the_first_tab_in_both_modes(window):
    assert isinstance(window.home_tab, HomeTab)
    assert "home" in SIMPLE_MODE_TABS
    assert window.tabs.widget(0) is window.home_tab
    assert window.tabs.tabText(0) == Ar.TAB_HOME
    window.set_simple_mode(False)
    assert window.tabs.widget(0) is window.home_tab


def test_without_projects_the_window_opens_on_main_with_the_empty_notice(window):
    assert window.tabs.currentWidget() is window.main_tab
    assert window.home_tab.cards == []
    assert not window.home_tab.empty_label.isHidden()
    assert window.home_tab.empty_label.text().endswith(Ar.HOME_EMPTY)


def test_with_projects_the_window_opens_on_home(qapp, tmp_path, monkeypatch):
    path, _ = make_project(tmp_path / "proj")
    settings = tmp_path / "s.json"
    settings.write_text(json.dumps({"recent_projects": [path]}), encoding="utf-8")
    monkeypatch.setattr("py2exe_gui.ui.main_window.SETTINGS_FILE", str(settings))
    monkeypatch.setattr("py2exe_gui.ui.main_window.HISTORY_FILE", str(tmp_path / "h.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.PRESETS_FILE", str(tmp_path / "p.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.KEYRING", MemoryKeyring())
    from py2exe_gui.ui.main_window import MainWindow

    win = MainWindow()
    try:
        assert win.tabs.currentWidget() is win.home_tab
        assert [c.path for c in win.home_tab.cards] == [path]
        assert win.home_tab.empty_label.isHidden()
    finally:
        win.close()


# ── Cards ─────────────────────────────────────────────────────────────────


def test_opening_a_project_adds_a_card_with_name_version_and_no_builds(window, tmp_path):
    path, _ = make_project(tmp_path / "proj")
    assert window.open_project_path(path)
    card = window.home_tab.card_for(path)
    assert isinstance(card, ProjectCard)
    shown = texts(card)
    assert "أداتي" in shown and "1.2.0" in shown and path in shown
    assert Ar.HOME_NO_BUILDS in shown and Ar.HOME_SIZE_NONE in shown and Ar.HOME_NO_RELEASE in shown
    assert Ar.HOME_CURRENT_PROJECT in shown  # it is the open project
    assert card.sparkline.sizes == [] and card.sparkline.points() == []
    for button in (card.open_btn, card.build_btn, card.release_btn, card.forget_btn):
        assert button.isEnabled()


def test_card_shows_last_build_sparkline_and_release(window, tmp_path):
    path, source = make_project(tmp_path / "proj")
    for size, when, ok in ((7_100_000, "2026-10-11T06:00:00", True),
                           (7_400_000, "2026-10-11T08:00:00", True),
                           (0, "2026-10-11T09:00:00", False)):
        window.history.add(make_record(source, "Tool", ok, 1.0, {}, timestamp=when,
                                       size_bytes=size))
    release = tmp_path / "proj" / "release" / "1.1.0"
    release.mkdir(parents=True)
    (release / "Tool-1.1.0.exe").write_bytes(b"x")
    (release / "SHA256SUMS.txt").write_text("")
    window.open_project_path(path)
    card = window.home_tab.card_for(path)
    shown = texts(card)
    assert "❌" in card.build_label.text() and "2026-10-11 09:00" in card.build_label.text()
    assert "3" in card.build_label.text()  # three builds in the history
    assert "6.8 MB" in shown and "7.1 MB" in shown and "+293 KB" in card.size_label.text()
    assert "1.1.0" in card.release_label.text() and "2" in card.release_label.text()
    assert Ar.HOME_RELEASE_NO_CHECKSUMS not in shown
    assert card.sparkline.sizes == [7_100_000, 7_400_000]
    points = card.sparkline.points()
    assert len(points) == 2
    # Right-to-left window: the newest build is drawn at the left edge.
    assert window.layoutDirection() == Qt.LayoutDirection.RightToLeft
    assert points[-1][0] < points[0][0]
    assert "6.8 MB" in card.sparkline.toolTip() and "7.1 MB" in card.sparkline.accessibleName()


def test_sparkline_runs_left_to_right_in_english(window, tmp_path):
    path, source = make_project(tmp_path / "proj")
    for size in (1000, 2000, 1500):
        window.history.add(make_record(source, "Tool", True, 1.0, {}, size_bytes=size))
    window.open_project_path(path)
    window.retranslate("en")
    card = window.home_tab.card_for(path)
    assert window.layoutDirection() == Qt.LayoutDirection.LeftToRight
    points = card.sparkline.points()
    assert points[-1][0] > points[0][0]
    assert En.HOME_CURRENT_PROJECT in texts(card)
    assert "version 1.2.0" in texts(card)
    # Painting offscreen must not raise, in either direction.
    assert not card.sparkline.grab().isNull()
    window.retranslate("ar")
    assert not window.home_tab.card_for(path).sparkline.grab().isNull()


def test_sparkline_paints_with_default_colours_when_given_none(qapp):
    widget = SizeSparkline([3, 1, 2])
    assert not widget.grab().isNull()
    assert widget.points()[0][0] < widget.points()[-1][0]  # no parent: left to right
    assert SizeSparkline([]).grab().isNull() is False


def test_missing_project_is_shown_with_only_the_remove_button(window, tmp_path):
    gone = str(tmp_path / "gone" / "p2e.toml")
    window._remember_project(gone)
    card = window.home_tab.card_for(gone)
    assert card is not None and Ar.HOME_MISSING in texts(card)
    assert not card.open_btn.isEnabled() and not card.build_btn.isEnabled()
    assert not card.release_btn.isEnabled() and card.forget_btn.isEnabled()
    assert card.build_btn.isHidden() and not card.forget_btn.isHidden()
    assert card.name_label.text().endswith("gone")


def test_unreadable_project_names_the_reason(window, tmp_path):
    bad = tmp_path / "bad" / "p2e.toml"
    bad.parent.mkdir()
    bad.write_text('schema = 2\n[release]\ntoken = "x"\n', encoding="utf-8")
    window._remember_project(str(bad))
    card = window.home_tab.card_for(str(bad))
    shown = texts(card)
    assert Ar.HOME_UNREADABLE_FMT.split("{")[0] in shown
    assert "release.token" in shown  # the refused key, from project_error_text
    assert not card.build_btn.isEnabled()


def test_a_broken_entry_never_takes_the_view_down(window, tmp_path, monkeypatch):
    good, _ = make_project(tmp_path / "good")
    window.settings["recent_projects"] = [str(tmp_path / "x" / "p2e.toml"), good, 42, ""]
    window.refresh_home()
    assert [c.summary.status for c in window.home_tab.cards] == ["missing", "ok", "missing"]


def test_forget_removes_from_settings_menu_and_cards(window, tmp_path):
    gone = str(tmp_path / "gone" / "p2e.toml")
    kept, _ = make_project(tmp_path / "kept")
    window._remember_project(gone)
    window._remember_project(kept)
    window.home_tab.card_for(gone).forget_btn.click()
    assert window.recent_projects() == [kept]
    assert [c.path for c in window.home_tab.cards] == [kept]
    assert [a.text() for a in window.recent_menu.actions()] == [kept]
    data = json.load(open(window.settings_path if hasattr(window, "settings_path")
                          else str(tmp_path / "s.json"), encoding="utf-8"))
    assert data["recent_projects"] == [kept]
    assert os.path.isfile(kept)  # the file itself is never touched
    assert Ar.LOG_HOME_FORGOTTEN.format(path=gone) in window.main_tab.log_output.toPlainText()


# ── Actions reuse the window's paths ──────────────────────────────────────


def test_build_from_a_card_opens_the_project_and_starts_the_build(window, tmp_path,
                                                                  monkeypatch):
    path, source = make_project(tmp_path / "proj")
    window._remember_project(path)
    started = []
    monkeypatch.setattr(window, "start_conversion", lambda: started.append(True))
    window.home_tab.card_for(path).build_btn.click()
    assert started == [True]
    assert window.project_path == path and window.main_tab.source_input.text() == source
    assert window.tabs.currentWidget() is window.main_tab
    assert Ar.LOG_HOME_BUILD.format(path=path) in window.main_tab.log_output.toPlainText()


def test_build_on_the_open_project_does_not_reopen_it(window, tmp_path, monkeypatch):
    path, _ = make_project(tmp_path / "proj")
    window.open_project_path(path)
    window.main_tab.output_name.setText("Edited")  # unsaved change
    started = []
    monkeypatch.setattr(window, "start_conversion", lambda: started.append(True))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: pytest.fail("must not ask to save")))
    window.build_project(path)
    assert started == [True] and window.main_tab.output_name.text() == "Edited"


def test_release_from_a_card_opens_the_project_and_starts_the_release(window, tmp_path,
                                                                      monkeypatch):
    path, _ = make_project(tmp_path / "proj")
    window._remember_project(path)
    started = []
    monkeypatch.setattr(window, "start_release", lambda: started.append(True))
    window.home_tab.card_for(path).release_btn.click()
    assert started == [True]
    assert window.project_path == path
    assert window.tabs.currentWidget() is window.release_tab


def test_actions_refuse_while_a_build_runs(window, tmp_path, monkeypatch):
    path, _ = make_project(tmp_path / "proj")
    window._remember_project(path)
    # Set on the instance and removed again by hand: a monkeypatch would still
    # be in force when the fixture closes the window, and a "build running"
    # close asks a modal question.
    window._build_in_progress = lambda: True
    try:
        warned = []
        monkeypatch.setattr(QMessageBox, "warning",
                            staticmethod(lambda *a, **k: warned.append(a[2])))
        started = []
        monkeypatch.setattr(window, "start_conversion", lambda: started.append(True))
        monkeypatch.setattr(window, "start_release", lambda: started.append(True))
        window.build_project(path)
        window.release_project(path)
        assert warned == [Ar.MSG_DIAG_BUSY, Ar.MSG_DIAG_BUSY] and started == []
        assert window.project_path == ""
    finally:
        del window._build_in_progress


def test_a_declined_open_starts_nothing(window, tmp_path, monkeypatch):
    path, _ = make_project(tmp_path / "proj")
    config = ProjectConfig(name="x", version="1.0.0")
    config.build.source = str(tmp_path / "proj" / "tool.py")
    config.build.extra_args = "--runtime-hook evil.py"
    save_project(config, path)
    window._remember_project(path)
    answer(monkeypatch, "question", QMessageBox.StandardButton.No)
    started = []
    monkeypatch.setattr(window, "start_conversion", lambda: started.append(True))
    window.build_project(path)
    assert started == [] and window.project_path == ""


def test_open_from_a_card_is_the_window_open(window, tmp_path):
    path, _ = make_project(tmp_path / "proj")
    window._remember_project(path)
    window.home_tab.card_for(path).open_btn.click()
    assert window.project_path == path
    assert Ar.HOME_CURRENT_PROJECT in texts(window.home_tab.card_for(path))


def test_open_other_uses_the_project_dialog(window, monkeypatch):
    called = []
    monkeypatch.setattr(window, "open_project_dialog", lambda: called.append(True))
    window.home_tab.open_other_btn.click()
    assert called == [True]


def test_refresh_button_rebuilds_the_cards(window, tmp_path):
    path, _ = make_project(tmp_path / "proj")
    window.settings["recent_projects"] = [path]
    assert window.home_tab.cards == []
    window.home_tab.refresh_btn.click()
    assert [c.path for c in window.home_tab.cards] == [path]


def test_cards_follow_a_finished_build(window, tmp_path, monkeypatch):
    path, source = make_project(tmp_path / "proj")
    window.open_project_path(path)
    assert window.home_tab.card_for(path).summary.last_build is None
    answer(monkeypatch, "critical", QMessageBox.StandardButton.Ok)
    window._build_config_snapshot = {"source": source, "output_name": "Tool"}
    window._build_start_time = 0.0
    window.on_conversion_finished(False, "boom")
    card = window.home_tab.card_for(path)
    assert card.summary.last_build is not None and not card.summary.last_build.success
    assert "❌" in card.build_label.text()


def test_cards_are_rebuilt_on_theme_and_language_change(window, tmp_path):
    path, _ = make_project(tmp_path / "proj")
    window._remember_project(path)
    before = window.home_tab.card_for(path)
    window.apply_theme("light")
    after = window.home_tab.card_for(path)
    assert after is not before and after.sparkline.colors["accent"]
    window.retranslate("en")
    assert En.BTN_HOME_BUILD == window.home_tab.card_for(path).build_btn.text()
    assert window.tabs.tabText(0) == En.TAB_HOME


def test_every_home_button_has_an_accessible_name(window, tmp_path):
    from py2exe_gui.qt import QPushButton

    path, _ = make_project(tmp_path / "proj")
    window._remember_project(str(tmp_path / "gone.toml"))
    window._remember_project(path)
    for button in window.home_tab.findChildren(QPushButton):
        assert button.accessibleName(), button.text()


def test_summary_card_without_window_renders(qapp):
    """A card is a plain widget: it needs no window to be built (and tested)."""
    tab = HomeTab(None)
    tab.show_projects([ProjectSummary(path="/x/p2e.toml", name="X", version="0.1.0",
                                      sizes=[1, 2, 3])])
    assert len(tab.cards) == 1
    tab.act("build_project", "/x/p2e.toml")  # no window: nothing happens, nothing raises
    tab.show_projects([])
    assert tab.cards == [] and not tab.empty_label.isHidden()


def test_english_strings_are_used_after_switching(window, tmp_path):
    set_locale("en")
    window.retranslate("en")
    path, source = make_project(tmp_path / "proj")
    window.history.add(make_record(source, "Tool", True, 1.0, {}, size_bytes=5_000_000))
    window._remember_project(str(tmp_path / "missing.toml"))
    window.open_project_path(path)
    shown = texts(window.home_tab.card_for(path))
    assert En.HOME_LAST_BUILD_OK_FMT.split("{")[0] in shown
    assert En.HOME_SIZE_SINGLE_FMT.split("{")[0] in shown and "4.8 MB" in shown
    assert En.HOME_MISSING in texts(window.home_tab.card_for(str(tmp_path / "missing.toml")))
