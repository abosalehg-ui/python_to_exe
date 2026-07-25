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


class TemplatesTab(BaseTab):
    """Presets and configuration persistence."""

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
