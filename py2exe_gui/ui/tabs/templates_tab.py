"""Project templates, settings save/load and the language selector."""

from PyQt5.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from py2exe_gui.strings import S, available_locales, current_locale
from py2exe_gui.templates import TEMPLATES, template_description, template_name
from py2exe_gui.ui.tabs.base import BaseTab

# Theme value → the locale attribute holding its display name. "auto" first,
# matching styles.theme_names().
THEME_LABEL_KEYS = (
    ("auto", "THEME_LABEL_AUTO"),
    ("dark", "THEME_LABEL_DARK"),
    ("light", "THEME_LABEL_LIGHT"),
    ("nord", "THEME_LABEL_NORD"),
    ("high-contrast", "THEME_LABEL_HIGH_CONTRAST"),
)


class TemplatesTab(BaseTab):
    """Templates, saved presets, appearance and language."""

    def _build(self):
        layout = QVBoxLayout(self)

        templates_group = QGroupBox(S.GROUP_TEMPLATES)
        templates_layout = QVBoxLayout(templates_group)
        templates_layout.addWidget(QLabel(S.TEMPLATES_HINT))

        self.templates_combo = QComboBox()
        for key in TEMPLATES:
            label = f"{template_name(key)} - {template_description(key)}"
            self.templates_combo.addItem(label, key)
        self.templates_combo.currentIndexChanged.connect(self.apply_template)
        templates_layout.addWidget(self.templates_combo)

        self.template_desc = QTextEdit()
        self.template_desc.setReadOnly(True)
        self.template_desc.setMaximumHeight(100)
        templates_layout.addWidget(self.template_desc)

        apply_btn = QPushButton(S.BTN_APPLY_TEMPLATE)
        apply_btn.clicked.connect(self.window_action("apply_selected_template"))
        templates_layout.addWidget(apply_btn)
        layout.addWidget(templates_group)

        # ── Named presets ──
        # The save/load buttons below write a JSON file the user then has to
        # find again. A preset is the same payload under a name, in one place.
        presets_group = QGroupBox(S.GROUP_PRESETS)
        presets_layout = QVBoxLayout(presets_group)
        presets_hint = QLabel(S.PRESETS_HINT)
        presets_hint.setWordWrap(True)
        presets_layout.addWidget(presets_hint)

        self.presets_combo = QComboBox()
        self.presets_combo.setAccessibleName(S.GROUP_PRESETS)
        presets_layout.addWidget(self.presets_combo)

        preset_row = QHBoxLayout()
        for label, action in (
            (S.BTN_PRESET_APPLY, "apply_selected_preset"),
            (S.BTN_PRESET_SAVE, "save_current_preset"),
            (S.BTN_PRESET_DELETE, "delete_selected_preset"),
        ):
            button = QPushButton(label)
            button.setAccessibleName(label)
            button.clicked.connect(self.window_action(action))
            preset_row.addWidget(button)
        presets_layout.addLayout(preset_row)

        share_row = QHBoxLayout()
        for label, action in (
            (S.BTN_PRESET_EXPORT, "export_presets"),
            (S.BTN_PRESET_IMPORT, "import_presets"),
        ):
            button = QPushButton(label)
            button.setAccessibleName(label)
            button.clicked.connect(self.window_action(action))
            share_row.addWidget(button)
        presets_layout.addLayout(share_row)
        layout.addWidget(presets_group)

        save_group = QGroupBox(S.GROUP_SAVE_LOAD)
        save_layout = QVBoxLayout(save_group)
        save_layout.addWidget(QLabel(S.SAVE_LOAD_HINT))
        save_btn_layout = QHBoxLayout()
        save_settings_btn = QPushButton(S.BTN_SAVE_SETTINGS)
        save_settings_btn.clicked.connect(self.window_action("save_current_settings"))
        load_settings_btn = QPushButton(S.BTN_LOAD_SETTINGS)
        load_settings_btn.clicked.connect(self.window_action("load_saved_settings"))
        save_btn_layout.addWidget(save_settings_btn)
        save_btn_layout.addWidget(load_settings_btn)
        save_layout.addLayout(save_btn_layout)
        layout.addWidget(save_group)

        # ── Appearance ──
        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel(S.THEME_SELECT_LABEL))
        self.theme_combo = QComboBox()
        self.theme_combo.setAccessibleName(S.THEME_SELECT_LABEL)
        for code, label in THEME_LABEL_KEYS:
            self.theme_combo.addItem(getattr(S, label), code)
        self.theme_combo.currentIndexChanged.connect(self.window_action("_on_theme_changed"))
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch()
        layout.addLayout(theme_row)

        # Language selector (Phase 3)
        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel(S.LANGUAGE_LABEL))
        self.language_combo = QComboBox()
        current = current_locale()
        for code, native in available_locales().items():
            self.language_combo.addItem(native, code)
            if code == current:
                self.language_combo.setCurrentIndex(self.language_combo.count() - 1)
        self.language_combo.currentIndexChanged.connect(self.window_action("_on_language_changed"))
        lang_row.addWidget(self.language_combo)
        lang_row.addStretch()
        layout.addLayout(lang_row)

        layout.addStretch()


    def apply_template(self, index=None):
        """Refresh the description panel for the highlighted template."""
        key = self.templates_combo.currentData()
        if not key or key not in TEMPLATES:
            return
        template = TEMPLATES[key]
        imports = ", ".join(template["hidden_imports"]) or S.NONE
        self.template_desc.setHtml(
            S.TEMPLATE_DESC_FMT.format(
                name=template_name(key),
                desc=template_description(key),
                windowed=S.YES if template["windowed"] else S.NO,
                onefile=S.YES if template["onefile"] else S.NO,
                imports=imports,
            )
        )

    def selected_template(self):
        """The highlighted template key, or None."""
        key = self.templates_combo.currentData()
        return key if key in TEMPLATES else None

    # ── Presets ────────────────────────────────────────────────────────────

    def refresh_presets(self, library):
        """Repopulate the preset dropdown from ``library``, keeping selection."""
        previous = self.selected_preset()
        self.presets_combo.clear()
        names = library.names()
        if not names:
            self.presets_combo.addItem(S.PRESET_NONE, "")
            return
        for name in names:
            self.presets_combo.addItem(name, name)
        if previous in names:
            self.presets_combo.setCurrentIndex(names.index(previous))

    def selected_preset(self) -> str:
        """The highlighted preset name, or '' when the list is empty."""
        return self.presets_combo.currentData() or ""

    # ── Appearance ─────────────────────────────────────────────────────────

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
