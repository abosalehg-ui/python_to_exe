"""The translucent "drop it here" layer shown while a file is dragged over.

The window accepted drops since 1.x but gave no sign of it: nothing changed
on screen until the file landed. This frame covers the window's content
while a drag is over it, with a dashed border and one line saying where the
file will go.
"""

from py2exe_gui.qt import QEvent, QLabel, Qt, QVBoxLayout, QWidget


class DropOverlay(QWidget):
    """Covers its parent while visible; the parent shows and hides it."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        # A plain QWidget paints no stylesheet background unless told to.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # Drops must still reach the window underneath.
        self.setAcceptDrops(False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        self.frame = QWidget()
        self.frame.setObjectName("dropFrame")
        self.frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        frame_layout = QVBoxLayout(self.frame)
        frame_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label = QLabel()
        self.icon_label.setObjectName("dropIcon")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        frame_layout.addWidget(self.icon_label)
        self.text_label = QLabel()
        self.text_label.setObjectName("dropText")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setWordWrap(True)
        frame_layout.addWidget(self.text_label)
        self.hint_label = QLabel()
        self.hint_label.setObjectName("dropHint")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setWordWrap(True)
        frame_layout.addWidget(self.hint_label)
        layout.addWidget(self.frame)
        self.hide()
        # Follow the parent's size at all times: showing the overlay makes
        # Qt 5 relayout the central widget by a pixel *before* the overlay
        # counts as visible, so the geometry must track every resize.
        if parent is not None:
            parent.installEventFilter(self)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Resize and watched is self.parentWidget():
            self.setGeometry(watched.rect())
        return super().eventFilter(watched, event)

    def set_texts(self, title: str, hint: str):
        self.text_label.setText(title)
        self.text_label.setAccessibleName(title)
        self.hint_label.setText(hint)

    def set_icon(self, pixmap):
        self.icon_label.setPixmap(pixmap)

    def cover(self, widget: QWidget):
        """Resize to ``widget``'s geometry (called on show and on resize)."""
        self.setGeometry(widget.rect())
        self.raise_()
