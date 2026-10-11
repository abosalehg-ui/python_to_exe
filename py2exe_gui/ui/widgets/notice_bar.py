"""A notice above the page instead of a dialog that has to be dismissed.

"Settings saved", "Template applied", "Build finished": a message with no
decision to make is not a dialog. The bar slides in under the page bar, says
its piece, and goes away on its own (or on the close button), so the person
keeps working. Dialogs remain for questions and for errors that stop an
action.
"""

from py2exe_gui.qt import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from py2exe_gui.strings import S

LEVELS = ("info", "success", "warning")
#: How long a notice stays, per level; warnings stay until closed.
TIMEOUTS = {"info": 6000, "success": 6000, "warning": 0}


class NoticeBar(QFrame):
    """One line of text, an icon by level, and a close button."""

    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("noticeBar")
        self.setProperty("level", "info")
        self.level = "info"
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.dismiss)

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 6, 8, 6)
        row.setSpacing(10)
        self.icon_label = QLabel()
        self.icon_label.setObjectName("noticeIcon")
        self.icon_label.setFixedSize(QSize(18, 18))
        row.addWidget(self.icon_label)
        self.text_label = QLabel()
        self.text_label.setObjectName("noticeText")
        self.text_label.setWordWrap(True)
        self.text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        row.addWidget(self.text_label, 1)
        self.close_btn = QPushButton()
        self.close_btn.setObjectName("iconBtn")
        self.close_btn.setProperty("iconName", "close")
        self.close_btn.setFixedSize(QSize(32, 32))
        self.close_btn.setIconSize(QSize(14, 14))
        self.close_btn.setFlat(True)
        self.close_btn.setToolTip(S.BTN_CLOSE)
        self.close_btn.setAccessibleName(S.BTN_CLOSE)
        self.close_btn.clicked.connect(self.dismiss)
        row.addWidget(self.close_btn)
        self._icons = {}
        self.hide()

    def set_icons(self, icons: dict, close_icon=None):
        """Theme-coloured icons per level (``info``/``success``/``warning``)."""
        self._icons = dict(icons)
        if close_icon is not None:
            self.close_btn.setIcon(close_icon)
        self._show_icon()

    def _show_icon(self):
        icon = self._icons.get(self.level)
        if icon is not None:
            self.icon_label.setPixmap(icon.pixmap(QSize(18, 18)))
        else:
            self.icon_label.clear()

    def show_message(self, text: str, level: str = "info", timeout_ms=None):
        """Show ``text``; ``timeout_ms`` 0 keeps it until closed."""
        if level not in LEVELS:
            level = "info"
        self.level = level
        self.setProperty("level", level)
        # Re-polish so the objectName/property change picks up its rule.
        self.style().unpolish(self)
        self.style().polish(self)
        self.text_label.setText(text)
        self.text_label.setAccessibleName(text)
        self._show_icon()
        self.show()
        self._timer.stop()
        delay = TIMEOUTS[level] if timeout_ms is None else int(timeout_ms)
        if delay > 0:
            self._timer.start(delay)

    def dismiss(self):
        self._timer.stop()
        if self.isVisible():
            self.hide()
            self.closed.emit()

    def text(self) -> str:
        return self.text_label.text()
