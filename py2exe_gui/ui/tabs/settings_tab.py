"""Settings: appearance, language, font size and the update check.

These used to be spread over three places: the theme and language selectors
at the bottom of the Templates tab, theme and mode buttons in the action row
under every tab, and the update check in About. One page, reachable from
the side navigation and from the View menu, holds them all. Per-machine
paths (the base interpreter, the Inno Setup compiler) stay next to the
features that use them.
"""

from py2exe_gui.qt import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
from py2exe_gui.strings import S, available_locales, current_locale
from py2exe_gui.styles import DEFAULT_FONT_SCALE
from py2exe_gui.ui.tabs.base import BaseTab, scrolled_layout

# Theme value → the locale attribute holding its display name. "auto" first,
# matching styles.theme_names().
THEME_LABEL_KEYS = (
    ("auto", "THEME_LABEL_AUTO"),
    ("dark", "THEME_LABEL_DARK"),
    ("light", "THEME_LABEL_LIGHT"),
    ("nord", "THEME_LABEL_NORD"),
    ("high-contrast", "THEME_LABEL_HIGH_CONTRAST"),
)


class SettingsTab(BaseTab):
    """Preferences that live in the settings file, never in a project."""

    def _build(self):
        layout = scrolled_layout(self)
        layout.setSpacing(14)

        # ── Appearance ──
        appearance = QGroupBox(S.GROUP_APPEARANCE)
        appearance_layout = QVBoxLayout(appearance)

        theme_row = QHBoxLayout()
        theme_label = QLabel(S.THEME_SELECT_LABEL)
        theme_row.addWidget(theme_label)
        self.theme_combo = QComboBox()
        self.theme_combo.setAccessibleName(S.THEME_SELECT_LABEL)
        for code, label in THEME_LABEL_KEYS:
            self.theme_combo.addItem(getattr(S, label), code)
        theme_label.setBuddy(self.theme_combo)
        self.theme_combo.currentIndexChanged.connect(self.window_action("_on_theme_changed"))
        theme_row.addWidget(self.theme_combo, 1)
        theme_row.addStretch(1)
        appearance_layout.addLayout(theme_row)

        font_row = QHBoxLayout()
        font_label = QLabel(S.FONT_SIZE_LABEL)
        font_row.addWidget(font_label)
        self.font_smaller_btn = QPushButton(S.BTN_FONT_SMALLER)
        self.font_smaller_btn.setToolTip(S.BTN_FONT_SMALLER_TIP)
        self.font_smaller_btn.setAccessibleName(S.BTN_FONT_SMALLER_TIP)
        self.font_smaller_btn.clicked.connect(self.window_action("zoom_out"))
        self.font_value = QLabel()
        self.font_value.setObjectName("aboutMuted")
        self.font_value.setMinimumWidth(56)
        self.font_larger_btn = QPushButton(S.BTN_FONT_LARGER)
        self.font_larger_btn.setToolTip(S.BTN_FONT_LARGER_TIP)
        self.font_larger_btn.setAccessibleName(S.BTN_FONT_LARGER_TIP)
        self.font_larger_btn.clicked.connect(self.window_action("zoom_in"))
        self.font_reset_btn = QPushButton(S.BTN_FONT_RESET)
        self.font_reset_btn.setObjectName("flatBtn")
        self.font_reset_btn.setAccessibleName(S.BTN_FONT_RESET)
        self.font_reset_btn.clicked.connect(self.window_action("zoom_reset"))
        for widget in (self.font_smaller_btn, self.font_value, self.font_larger_btn,
                       self.font_reset_btn):
            font_row.addWidget(widget)
        font_row.addStretch(1)
        appearance_layout.addLayout(font_row)
        hint = QLabel(S.FONT_SIZE_HINT)
        hint.setObjectName("aboutMuted")
        hint.setWordWrap(True)
        appearance_layout.addWidget(hint)
        layout.addWidget(appearance)

        # ── Language ──
        language = QGroupBox(S.GROUP_LANGUAGE)
        language_layout = QHBoxLayout(language)
        lang_label = QLabel(S.LANGUAGE_LABEL)
        language_layout.addWidget(lang_label)
        self.language_combo = QComboBox()
        self.language_combo.setAccessibleName(S.LANGUAGE_LABEL)
        current = current_locale()
        for code, native in available_locales().items():
            self.language_combo.addItem(native, code)
            if code == current:
                self.language_combo.setCurrentIndex(self.language_combo.count() - 1)
        lang_label.setBuddy(self.language_combo)
        self.language_combo.currentIndexChanged.connect(
            self.window_action("_on_language_changed"))
        language_layout.addWidget(self.language_combo, 1)
        language_layout.addStretch(1)
        layout.addWidget(language)

        # ── Updates: report-only, and opt-in for the automatic one ──
        updates = QGroupBox(S.GROUP_UPDATES)
        updates_layout = QVBoxLayout(updates)
        update_hint = QLabel(S.UPDATES_HINT)
        update_hint.setObjectName("aboutMuted")
        update_hint.setWordWrap(True)
        updates_layout.addWidget(update_hint)
        self.update_btn = QPushButton(S.BTN_CHECK_UPDATES)
        self.update_btn.setAccessibleName(S.BTN_CHECK_UPDATES)
        self.update_btn.clicked.connect(self.window_action("check_for_updates"))
        update_row = QHBoxLayout()
        update_row.addWidget(self.update_btn)
        update_row.addStretch(1)
        updates_layout.addLayout(update_row)
        self.update_on_start = QCheckBox(S.UPDATE_CHECK_ON_START)
        self.update_on_start.setAccessibleName(S.UPDATE_CHECK_ON_START)
        if self.window is not None:
            self.update_on_start.setChecked(
                bool(self.window.settings.get("check_updates_on_start", False))
            )
        self.update_on_start.toggled.connect(self._on_update_pref_changed)
        updates_layout.addWidget(self.update_on_start)
        layout.addWidget(updates)

        layout.addStretch(1)
        self.set_font_scale(DEFAULT_FONT_SCALE)

    # ── State shown ────────────────────────────────────────────────────────

    def set_theme(self, theme: str):
        """Point the theme selector at ``theme`` without firing the handler."""
        index = self.theme_combo.findData(theme)
        if index < 0:
            return
        self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentIndex(index)
        self.theme_combo.blockSignals(False)

    def selected_theme(self) -> str:
        return self.theme_combo.currentData() or "dark"

    def set_font_scale(self, scale: float):
        self.font_value.setText(S.FONT_SIZE_FMT.format(percent=round(float(scale) * 100)))

    def selected_language(self) -> str:
        return self.language_combo.currentData() or current_locale()

    def _on_update_pref_changed(self, enabled: bool):
        if self.window is not None:
            self.window.settings["check_updates_on_start"] = bool(enabled)
