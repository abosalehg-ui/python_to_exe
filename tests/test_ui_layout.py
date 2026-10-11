"""The window must stay usable at the sizes it says it supports.

Before 2.1 the main tab laid its groups straight onto the widget; at the
default 1080x800 window (and on any 1366x768 laptop) Qt squeezed the fields
to a couple of pixels instead of scrolling. These run offscreen.
"""

import pytest

pytest.importorskip("py2exe_gui.qt", reason="no Qt binding (PySide6/PyQt5) installed")

from py2exe_gui.qt import QApplication, QLineEdit, QScrollArea  # noqa: E402
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


def _settle(window, width, height):
    window.resize(width, height)
    window.show()
    app = QApplication.instance()
    for _ in range(3):
        app.processEvents()


def test_content_fits_the_declared_minimum_size(window):
    """What the window asks for must not exceed what it promises to fit in."""
    hint = window.centralWidget().minimumSizeHint()
    assert hint.height() <= window.minimumHeight()
    assert hint.width() <= window.minimumWidth()


def test_every_tab_scrolls_instead_of_squeezing(window):
    for _key, widget, _title in window._all_tabs:
        layout = widget.layout()
        assert layout is not None and layout.count() >= 1, widget
        first = layout.itemAt(0).widget()
        assert isinstance(first, QScrollArea), f"{type(widget).__name__} is not scrollable"


@pytest.mark.parametrize("size", [(900, 600), (1080, 800), (1366, 700)])
def test_fields_keep_their_height_at_common_window_sizes(window, size):
    _settle(window, *size)
    window.tabs.setCurrentWidget(window.main_tab)
    QApplication.instance().processEvents()
    squeezed = [
        edit.objectName() or edit.placeholderText()
        for edit in window.main_tab.findChildren(QLineEdit)
        if edit.isVisible() and edit.height() < 24
    ]
    assert not squeezed, f"fields squeezed at {size}: {squeezed}"


def test_cancel_is_hidden_until_a_build_runs(window):
    assert window.convert_btn.isVisibleTo(window)
    assert not window.cancel_btn.isVisibleTo(window)
    window._set_building(True)
    assert window.cancel_btn.isVisibleTo(window)
    assert not window.convert_btn.isVisibleTo(window)
    window._set_building(False)
    assert window.convert_btn.isVisibleTo(window)
    assert not window.cancel_btn.isVisibleTo(window)
