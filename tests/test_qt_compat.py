"""The Qt compat layer (``py2exe_gui.qt``) behaves the same on both bindings.

Headless, skipped when no binding is installed. CI runs this file once under
PySide6 and once under PyQt5.
"""

import os
import subprocess
import sys

import pytest

pytest.importorskip("py2exe_gui.qt", reason="no Qt binding (PySide6/PyQt5) installed")

from py2exe_gui import qt  # noqa: E402
from py2exe_gui.qt import (  # noqa: E402
    QColor,
    QFontInfo,
    QFontMetrics,
    QImage,
    QPainter,
    Qt,
    QThread,
    Signal,
    application_font,
)
from tests.conftest import MemoryKeyring  # noqa: E402

pytestmark = pytest.mark.gui

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARABIC = "محوّل بايثون إلى EXE — الإصدار ٢"


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


# ── Choosing the binding ───────────────────────────────────────────────────


def test_default_order_prefers_pyside6_then_pyqt5():
    assert qt.binding_order(env={}, loaded={}) == ["PySide6", "PyQt5"]


@pytest.mark.parametrize("value,expected", [
    ("pyqt5", ["PyQt5"]), ("PySide6", ["PySide6"]), ("PYQT5", ["PyQt5"]),
    ("", ["PySide6", "PyQt5"]), ("pyqt6", ["PySide6", "PyQt5"]),
])
def test_qt_api_variable_forces_a_known_binding(value, expected):
    assert qt.binding_order(env={qt.API_VARIABLE: value}, loaded={}) == expected


def test_a_binding_already_in_the_process_wins():
    """Never load two bindings side by side."""
    assert qt.binding_order(env={}, loaded={"PyQt5": object()}) == ["PyQt5", "PySide6"]
    # A blocked module (None) does not count as loaded.
    assert qt.binding_order(env={}, loaded={"PyQt5": None}) == ["PySide6", "PyQt5"]


def test_the_chosen_binding_is_the_only_one_loaded():
    assert qt.API in qt.SUPPORTED
    other = [name for name in qt.SUPPORTED if name != qt.API][0]
    assert other not in sys.modules or sys.modules[other] is None
    assert qt.API in qt.describe() and qt.QT_VERSION in qt.describe()
    assert qt.QT_MAJOR == int(qt.QT_VERSION.split(".")[0])
    assert qt.IS_QT6 == (qt.API == "PySide6")


# ── Names that differ between the bindings ─────────────────────────────────


def test_signal_slot_property_are_the_binding_classes():
    core = qt.QtCore
    if qt.API == "PySide6":
        assert (qt.Signal, qt.Slot, qt.Property) == (core.Signal, core.Slot, core.Property)
    else:
        assert (qt.Signal, qt.Slot, qt.Property) == (
            core.pyqtSignal, core.pyqtSlot, core.pyqtProperty)


def test_qaction_and_qshortcut_come_from_the_right_module():
    expected = "QtGui" if qt.IS_QT6 else "QtWidgets"
    assert qt.QAction.__module__.endswith(expected)
    assert qt.QShortcut.__module__.endswith(expected)


def test_any_qt_class_resolves_through_the_module():
    from py2exe_gui.qt import QFileDialog, QPixmap, QTimer  # all three modules

    assert QFileDialog is qt.QtWidgets.QFileDialog
    assert QPixmap is qt.QtGui.QPixmap
    assert QTimer is qt.QtCore.QTimer
    with pytest.raises(AttributeError):
        qt.QNoSuchClass  # noqa: B018
    with pytest.raises(ImportError):
        from py2exe_gui.qt import QNoSuchClass  # noqa: F401


def test_scoped_enums_exist_on_both_bindings():
    """The code base uses fully scoped names; both bindings must accept them."""
    from py2exe_gui.qt import QDialog, QFrame, QMessageBox

    assert Qt.AlignmentFlag.AlignLeft is not None
    assert Qt.LayoutDirection.RightToLeft is not None
    assert QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    assert int(QDialog.DialogCode.Accepted) == 1
    assert QFrame.Shape.HLine is not None and QFrame.Shadow.Plain is not None
    # Roles are used arithmetically (UserRole + 1): must stay int-like.
    assert int(Qt.ItemDataRole.UserRole + 1) == int(Qt.ItemDataRole.UserRole) + 1


def test_a_signal_crosses_threads(qapp):
    class Worker(QThread):
        done = Signal(str, int)

        def run(self):
            self.done.emit("finished", 7)

    received = []
    worker = Worker()
    worker.done.connect(lambda text, n: received.append((text, n)))
    worker.start()
    assert worker.wait(10000)
    for _ in range(50):
        qapp.processEvents()
        if received:
            break
    assert received == [("finished", 7)]


# ── Fonts and Arabic rendering ─────────────────────────────────────────────


def test_application_font_lists_arabic_capable_fallbacks(qapp):
    font = application_font(10)
    assert font.pointSize() == 10
    assert qt.FONT_FAMILIES[0] == "Segoe UI"
    if hasattr(font, "families"):
        assert list(font.families()) == list(qt.FONT_FAMILIES)
    # Whatever the platform resolves it to, it is a real family.
    assert QFontInfo(font).family()


def ink_pixels(text, font, direction):
    """Render ``text`` onto a white image and count the non-white pixels."""
    image = QImage(600, 60, QImage.Format.Format_ARGB32)
    image.fill(QColor("white"))
    painter = QPainter(image)
    painter.setFont(font)
    painter.setPen(QColor("black"))
    painter.setLayoutDirection(direction)
    painter.drawText(image.rect(), Qt.AlignmentFlag.AlignVCenter, text)
    painter.end()
    count = 0
    for y in range(image.height()):
        for x in range(image.width()):
            if QColor(image.pixel(x, y)).lightness() < 128:
                count += 1
    return count


def test_arabic_text_renders_with_the_application_font(qapp):
    """Arabic has real glyphs (not .notdef boxes) and a non-zero advance."""
    font = application_font(12)
    metrics = QFontMetrics(font)
    assert metrics.horizontalAdvance(ARABIC) > metrics.horizontalAdvance("abc")
    rtl = ink_pixels(ARABIC, font, Qt.LayoutDirection.RightToLeft)
    assert rtl > 200
    # A missing-glyph box is a hollow rectangle: its ink is the same for any
    # character; shaped Arabic letters differ between strings.
    assert ink_pixels("ببب", font, Qt.LayoutDirection.RightToLeft) != ink_pixels(
        "ععع", font, Qt.LayoutDirection.RightToLeft)
    assert ink_pixels("", font, Qt.LayoutDirection.RightToLeft) == 0


def test_arabic_window_is_right_to_left_and_about_names_the_binding(window):
    window.retranslate("ar")
    assert window.layoutDirection() == Qt.LayoutDirection.RightToLeft
    label = window.about_tab.qt_label.text()
    assert qt.API in label and qt.QT_VERSION in label
    window.retranslate("en")
    assert window.layoutDirection() == Qt.LayoutDirection.LeftToRight
    assert qt.API in window.about_tab.qt_label.text()


# ── Binding health ─────────────────────────────────────────────────────────


def test_thousands_of_signal_emissions_do_not_corrupt_the_interpreter(tmp_path):
    """Why PySide6 6.12.0 is excluded below Python 3.12 (pyproject.toml).

    That release releases True/False once too often per emission; a build
    that logs a few thousand lines then aborts with "bool_dealloc". A
    subprocess, so a bad binding kills only this test.
    """
    code = (
        "from py2exe_gui.qt import QApplication, QObject, QPlainTextEdit, Signal\n"
        "app = QApplication([])\n"
        "class M(QObject):\n"
        "    text = Signal(str)\n"
        "    flag = Signal(bool)\n"
        "m = M(); box = QPlainTextEdit(); seen = []\n"
        "m.text.connect(box.appendPlainText); m.flag.connect(seen.append)\n"
        "for i in range(20000):\n"
        "    m.text.emit('line %d' % i); m.flag.emit(i % 2 == 0)\n"
        "    if i % 2000 == 0: app.processEvents()\n"
        "assert box.document().blockCount() == 20000 and len(seen) == 20000\n"
        "print('ok')\n"
    )
    env = {**os.environ, "PYTHONPATH": ROOT, "QT_QPA_PLATFORM": "offscreen",
           qt.API_VARIABLE: qt.API.lower()}
    result = subprocess.run([sys.executable, "-c", code], cwd=str(tmp_path), env=env,
                            capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, f"{qt.describe()}: {result.stderr[-2000:]}"
    assert result.stdout.strip() == "ok"


# ── High DPI ───────────────────────────────────────────────────────────────


def test_high_dpi_scaling_is_in_effect_under_a_scaled_display(tmp_path):
    """With a 150 % display, a widget's device pixel ratio follows (both Qt versions)."""
    code = (
        "from py2exe_gui.qt import QApplication, QWidget, Qt, configure_high_dpi, IS_QT6\n"
        "configure_high_dpi()\n"
        "app = QApplication([])\n"
        "w = QWidget(); w.show()\n"
        "ratio = w.devicePixelRatioF()\n"
        "assert 1.4 <= ratio <= 1.6, ratio\n"
        "if IS_QT6:\n"
        "    policy = QApplication.highDpiScaleFactorRoundingPolicy()\n"
        "    assert policy == Qt.HighDpiScaleFactorRoundingPolicy.PassThrough, policy\n"
        "else:\n"
        "    attr = Qt.ApplicationAttribute.AA_EnableHighDpiScaling\n"
        "    assert QApplication.testAttribute(attr)\n"
        "print(ratio)\n"
    )
    env = {**os.environ, "PYTHONPATH": ROOT, "QT_QPA_PLATFORM": "offscreen",
           "QT_SCALE_FACTOR": "1.5", qt.API_VARIABLE: qt.API.lower()}
    result = subprocess.run([sys.executable, "-c", code], cwd=str(tmp_path), env=env,
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr


def test_configure_high_dpi_runs_before_the_application_without_qt6_warnings(tmp_path):
    """On Qt 6 the deprecated Qt 5 attributes are not touched (they warn)."""
    code = (
        "import warnings\n"
        "warnings.simplefilter('error')\n"
        "from py2exe_gui.qt import QApplication, configure_high_dpi\n"
        "configure_high_dpi()\n"
        "app = QApplication([])\n"
        "print('ok')\n"
    )
    env = {**os.environ, "PYTHONPATH": ROOT, "QT_QPA_PLATFORM": "offscreen",
           qt.API_VARIABLE: qt.API.lower()}
    result = subprocess.run([sys.executable, "-c", code], cwd=str(tmp_path), env=env,
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
