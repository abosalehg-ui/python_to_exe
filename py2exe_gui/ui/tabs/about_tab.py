"""Application information."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QFrame,
    QLabel,
    QPushButton,
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

        # Update check: report-only, and opt-in for the automatic one. Nothing
        # is ever downloaded or run on the user's behalf.
        self.update_btn = QPushButton(S.BTN_CHECK_UPDATES)
        self.update_btn.setAccessibleName(S.BTN_CHECK_UPDATES)
        self.update_btn.clicked.connect(self.window_action("check_for_updates"))
        layout.addWidget(self.update_btn)

        self.update_on_start = QCheckBox(S.UPDATE_CHECK_ON_START)
        self.update_on_start.setAccessibleName(S.UPDATE_CHECK_ON_START)
        if self.window is not None:
            self.update_on_start.setChecked(
                bool(self.window.settings.get("check_updates_on_start", False))
            )
        self.update_on_start.toggled.connect(self._on_update_pref_changed)
        layout.addWidget(self.update_on_start)

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

    def _on_update_pref_changed(self, enabled: bool):
        if self.window is not None:
            self.window.settings["check_updates_on_start"] = bool(enabled)
