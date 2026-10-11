"""A titled section that folds away: progressive disclosure for the Build page.

Until 2.1 the less common build options lived in three more tabs and the
window had a "simple / advanced" switch that hid or showed whole tabs. A
section that opens in place does the same job without a mode: a newcomer
sees four fields, and whoever needs the splash screen or the signing
certificate opens the section that holds it. The open/closed state is the
caller's to remember (the window keeps it in the settings file).
"""

from py2exe_gui.qt import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    Qt,
    QToolButton,
    QVBoxLayout,
    QWidget,
    Signal,
)

HEADER_HEIGHT = 36


class CollapsibleSection(QWidget):
    """``title`` over ``content``; the header toggles whether content shows.

    ``subtitle`` is a short summary of what the hidden content holds ("2
    files, 3 hidden imports"), so a closed section still says something.
    """

    toggled = Signal(bool)

    def __init__(self, title: str, content: QWidget, subtitle: str = "",
                 expanded: bool = False, parent=None):
        super().__init__(parent)
        self.content = content
        self.setObjectName("collapsibleSection")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(8)
        self.header = QToolButton()
        self.header.setObjectName("sectionHeader")
        self.header.setCheckable(True)
        self.header.setChecked(bool(expanded))
        self.header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.header.setMinimumHeight(HEADER_HEIGHT)
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header.toggled.connect(self._on_toggled)
        head.addWidget(self.header, 1)

        self.subtitle = QLabel()
        self.subtitle.setObjectName("sectionSubtitle")
        self.subtitle.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        head.addWidget(self.subtitle)
        layout.addLayout(head)

        self.body = QFrame()
        self.body.setObjectName("sectionBody")
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(8, 2, 8, 8)
        body_layout.addWidget(content)
        layout.addWidget(self.body)

        self.set_title(title)
        self.set_subtitle(subtitle)
        self.body.setVisible(bool(expanded))
        self._update_arrow()

    # ── State ──────────────────────────────────────────────────────────────

    def is_expanded(self) -> bool:
        return self.header.isChecked()

    def set_expanded(self, expanded: bool):
        """Open or close without the header having been clicked."""
        if self.header.isChecked() != bool(expanded):
            self.header.setChecked(bool(expanded))

    def set_title(self, title: str):
        self.header.setText(title)
        self.header.setAccessibleName(title)

    def set_subtitle(self, subtitle: str):
        self.subtitle.setText(subtitle or "")
        self.subtitle.setVisible(bool(subtitle))

    # ── Internals ──────────────────────────────────────────────────────────

    def _on_toggled(self, checked: bool):
        self.body.setVisible(checked)
        self._update_arrow()
        self.toggled.emit(checked)

    def set_chevrons(self, open_icon, closed_icon):
        """Use these icons (theme-coloured SVGs) instead of the style's arrows."""
        self._chevrons = (open_icon, closed_icon)
        self._update_arrow()

    def _update_arrow(self):
        """Down when open; when closed, pointing into the reading direction."""
        chevrons = getattr(self, "_chevrons", None)
        if chevrons is not None:
            self.header.setArrowType(Qt.ArrowType.NoArrow)
            self.header.setIcon(chevrons[0] if self.header.isChecked() else chevrons[1])
            return
        if self.header.isChecked():
            arrow = Qt.ArrowType.DownArrow
        elif self.layoutDirection() == Qt.LayoutDirection.RightToLeft:
            arrow = Qt.ArrowType.LeftArrow
        else:
            arrow = Qt.ArrowType.RightArrow
        self.header.setArrowType(arrow)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == event.Type.LayoutDirectionChange:
            self._update_arrow()
