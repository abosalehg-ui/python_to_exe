"""Feedback without dialogs (2.1): the notice bar, the drop overlay, the
progress label and the focus order of the Build page. Headless."""

import pytest

pytest.importorskip("py2exe_gui.qt", reason="no Qt binding (PySide6/PyQt5) installed")

from py2exe_gui.qt import (  # noqa: E402
    QApplication,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDropEvent,
    QMimeData,
    QPoint,
    QPointF,
    Qt,
    QUrl,
)
from py2exe_gui.strings import Ar, S  # noqa: E402
from py2exe_gui.ui.widgets import NoticeBar  # noqa: E402
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


# ── NoticeBar on its own ───────────────────────────────────────────────────


def test_notice_bar_shows_and_closes(qapp):
    bar = NoticeBar()
    assert bar.isHidden()
    closed = []
    bar.closed.connect(lambda: closed.append(True))
    bar.show_message("saved", "success")
    assert not bar.isHidden() and bar.text() == "saved" and bar.level == "success"
    assert bar.property("level") == "success"
    bar.close_btn.click()
    assert bar.isHidden() and closed == [True]
    bar.close()


def test_notice_bar_hides_itself_after_the_timeout(qapp):
    bar = NoticeBar()
    bar.show_message("brief", "info", timeout_ms=30)
    assert not bar.isHidden()
    deadline = 200
    while deadline and not bar.isHidden():
        QApplication.instance().processEvents()
        qapp.thread().msleep(5)
        deadline -= 1
    assert bar.isHidden()
    bar.close()


def test_warning_notices_stay_until_closed(qapp):
    bar = NoticeBar()
    bar.show_message("careful", "warning")
    assert not bar._timer.isActive()
    bar.show_message("unknown level falls back", "nonsense")
    assert bar.level == "info"
    bar.close()


# ── In the window ──────────────────────────────────────────────────────────


def test_applying_a_template_notifies_instead_of_asking_to_click_ok(window, monkeypatch):
    from py2exe_gui.qt import QMessageBox

    called = []
    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda *a, **k: called.append(a) or 0))
    window.templates_tab.templates_combo.setCurrentIndex(0)
    window.apply_selected_template()
    assert not called
    assert window.notice_bar.isVisibleTo(window)
    assert window.notice_bar.level == "success"


def test_build_success_is_a_persistent_notice(window, monkeypatch):
    from py2exe_gui.qt import QMessageBox

    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda *a, **k: pytest.fail("dialog shown")))
    monkeypatch.setattr(window, "_run_post_build_actions", lambda _c: None)
    window.on_conversion_finished(True, "built")
    assert window.notice_bar.text() == "built"
    assert not window.notice_bar._timer.isActive()
    assert window.statusBar().currentMessage().startswith(Ar.STATUS_DONE_FMT.split("{")[0])


def test_notice_bar_icons_follow_the_theme(window):
    window.apply_theme("light")
    assert set(window.notice_bar._icons) == {"info", "success", "warning"}
    assert not window.notice_bar.close_btn.icon().isNull()


# ── Drag and drop overlay ──────────────────────────────────────────────────


def _drag_event(window, path):
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(path)])
    event = QDragEnterEvent(QPoint(10, 10), Qt.DropAction.CopyAction, mime,
                            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    # Qt keeps a pointer, not a copy: the mime data must outlive the event.
    event._mime = mime
    return event


def test_drag_shows_the_overlay_and_leaving_hides_it(window, tmp_path):
    window.show()
    assert window.drop_overlay.isHidden()
    window.dragEnterEvent(_drag_event(window, str(tmp_path / "x.py")))
    assert not window.drop_overlay.isHidden()
    assert window.drop_overlay.text_label.text() == S.DROP_TITLE
    QApplication.instance().processEvents()  # Qt 5 settles the bars a frame later
    assert window.drop_overlay.geometry() == window.centralWidget().rect()
    window.resize(1000, 700)
    QApplication.instance().processEvents()
    assert window.drop_overlay.geometry() == window.centralWidget().rect()
    window.dragLeaveEvent(QDragLeaveEvent())
    assert window.drop_overlay.isHidden()


def test_drop_hides_the_overlay_and_routes_the_file(window, tmp_path):
    script = tmp_path / "app.py"
    script.write_text("print(1)\n")
    window.dragEnterEvent(_drag_event(window, str(script)))
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(script))])
    event = QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime,
                       Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    window.dropEvent(event)
    assert window.drop_overlay.isHidden()
    assert window.main_tab.source_input.text() == str(script)


def test_overlay_never_takes_the_drop_itself(window):
    assert not window.drop_overlay.acceptDrops()
    assert window.drop_overlay.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)


# ── Progress label ─────────────────────────────────────────────────────────


def test_progress_label_mirrors_the_bar(window):
    assert not window.progress_label.isVisibleTo(window)
    window._set_building(True)
    window.progress_bar.setVisible(True)
    window.progress_bar.setValue(42)
    window._on_stage_changed("analyzing")
    assert Ar.STAGE_ANALYZING in window.progress_label.text()
    assert "42" in window.progress_label.text()
    assert not window.progress_bar.isTextVisible()


# ── Focus order and mnemonics ──────────────────────────────────────────────


def test_build_form_tab_order_follows_the_reading_order(window):
    tab = window.main_tab
    assert tab.source_input.nextInFocusChain() is tab.source_btn
    assert tab.output_dir.nextInFocusChain() is tab.output_dir_btn
    assert tab.icon_input.nextInFocusChain() is tab.icon_btn
    assert tab.icon_btn.nextInFocusChain() is tab.studio_btn


def test_english_menus_have_mnemonics(window):
    from py2exe_gui.strings import En

    assert all(title.startswith("&") for title in
               (En.MENU_PROJECT, En.MENU_VIEW, En.MENU_TOOLS, En.MENU_HELP))


def test_empty_log_has_a_placeholder(window):
    assert window.log_panel.log_output.placeholderText() == Ar.LOG_PANEL_EMPTY
