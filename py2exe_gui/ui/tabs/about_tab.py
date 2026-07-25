"""Application information."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from py2exe_gui.constants import APP_NAME, APP_VERSION, COPYRIGHT, DEVELOPER, EMAIL
from py2exe_gui.strings import S
from py2exe_gui.ui.tabs.base import BaseTab


class AboutTab(BaseTab):
    """About page built from themed widgets rather than an HTML blob."""

    def _build(self):
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setAlignment(Qt.AlignTop)
        layout.setSpacing(8)

        def add_label(text, object_name, *, bold=False):
            label = QLabel(text)
            label.setObjectName(object_name)
            label.setWordWrap(True)
            label.setAlignment(Qt.AlignCenter)
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            if bold:
                font = label.font()
                font.setBold(True)
                label.setFont(font)
            layout.addWidget(label)
            return label

        def add_separator():
            line = QFrame()
            line.setObjectName("aboutSeparator")
            line.setFrameShape(QFrame.HLine)
            line.setFrameShadow(QFrame.Plain)
            layout.addWidget(line)

        add_label(f"🐍 {APP_NAME}", "aboutHeading")
        add_label(S.ABOUT_VERSION_FMT.format(version=APP_VERSION), "aboutSubheading")
        add_separator()
        add_label(S.ABOUT_DESC_PLAIN, "aboutBody")
        add_separator()
        add_label(S.ABOUT_DEVELOPER_LABEL, "aboutSubheading")
        add_label(DEVELOPER, "aboutBody", bold=True)
        add_label(f"📧 {EMAIL}", "aboutBody")
        add_separator()
        add_label(COPYRIGHT, "aboutMuted")
        add_separator()
        add_label(S.ABOUT_FEATURES_LABEL, "aboutSubheading")

        features = QLabel("\n".join(f"•  {f}" for f in S.ABOUT_FEATURES))
        features.setObjectName("aboutBody")
        features.setWordWrap(True)
        # Feature bullets read as a block; centring a list looks wrong in both
        # directions, so follow the inherited layout direction instead.
        features.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        layout.addWidget(features)
        layout.addStretch()

        # Field-dense: keep it usable on a short screen.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
