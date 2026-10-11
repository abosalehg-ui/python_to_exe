"""Application information."""

from py2exe_gui.bidi import ltr
from py2exe_gui.constants import APP_NAME, APP_VERSION, COPYRIGHT, DEVELOPER, EMAIL
from py2exe_gui.qt import (
    QFrame,
    QLabel,
    Qt,
)
from py2exe_gui.qt import describe as qt_describe
from py2exe_gui.strings import S
from py2exe_gui.ui.tabs.base import BaseTab, scrolled_layout


class AboutTab(BaseTab):
    """About page built from themed widgets rather than an HTML blob."""

    def _build(self):
        layout = scrolled_layout(self, spacing=8)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        def add_label(text, object_name, *, bold=False):
            label = QLabel(text)
            label.setObjectName(object_name)
            label.setWordWrap(True)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            if bold:
                font = label.font()
                font.setBold(True)
                label.setFont(font)
            layout.addWidget(label)
            return label

        def add_separator():
            line = QFrame()
            line.setObjectName("aboutSeparator")
            line.setFrameShape(QFrame.Shape.HLine)
            line.setFrameShadow(QFrame.Shadow.Plain)
            layout.addWidget(line)

        add_label(f"🐍 {APP_NAME}", "aboutHeading")
        add_label(S.ABOUT_VERSION_FMT.format(version=APP_VERSION), "aboutSubheading")
        self.qt_label = add_label(S.ABOUT_QT_FMT.format(binding=ltr(qt_describe())), "aboutMuted")

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
        features.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        layout.addWidget(features)
        layout.addStretch()
