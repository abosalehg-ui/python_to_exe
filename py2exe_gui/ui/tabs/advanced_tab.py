"""Extra data files, hidden imports, optimisation and raw arguments."""

from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)

from py2exe_gui.strings import S
from py2exe_gui.ui.dialogs import AddImportDialog
from py2exe_gui.ui.tabs.base import BaseTab, browse_button


class AdvancedTab(BaseTab):
    """Options that map to the less common PyInstaller flags."""

    def _build(self):
        layout = QVBoxLayout(self)

        files_group = QGroupBox(S.GROUP_EXTRA_FILES)
        files_layout = QVBoxLayout(files_group)
        self.extra_files_list = QListWidget()
        self.extra_files_list.setMinimumHeight(100)

        files_btn_layout = QHBoxLayout()
        add_file_btn = QPushButton(S.BTN_ADD_FILE)
        add_file_btn.clicked.connect(self.add_extra_file)
        add_folder_btn = QPushButton(S.BTN_ADD_FOLDER)
        add_folder_btn.clicked.connect(self.add_extra_folder)
        remove_file_btn = QPushButton(S.BTN_REMOVE_SELECTED)
        remove_file_btn.clicked.connect(self.remove_extra_file)
        files_btn_layout.addWidget(add_file_btn)
        files_btn_layout.addWidget(add_folder_btn)
        files_btn_layout.addWidget(remove_file_btn)
        files_layout.addWidget(self.extra_files_list)
        files_layout.addLayout(files_btn_layout)
        layout.addWidget(files_group)

        imports_group = QGroupBox(S.GROUP_HIDDEN_IMPORTS)
        imports_layout = QVBoxLayout(imports_group)
        self.hidden_imports_list = QListWidget()
        self.hidden_imports_list.setMinimumHeight(80)

        imports_btn_layout = QHBoxLayout()
        add_import_btn = QPushButton(S.BTN_ADD_IMPORT)
        add_import_btn.clicked.connect(self.add_hidden_import)
        remove_import_btn = QPushButton(S.BTN_REMOVE_SELECTED)
        remove_import_btn.clicked.connect(self.remove_hidden_import)
        detect_imports_btn = QPushButton(S.BTN_AUTO_DETECT)
        detect_imports_btn.clicked.connect(self.window_action("detect_imports_action"))
        import_reqs_btn = QPushButton(S.BTN_IMPORT_REQUIREMENTS)
        import_reqs_btn.clicked.connect(self.window_action("import_requirements_file"))
        imports_btn_layout.addWidget(add_import_btn)
        imports_btn_layout.addWidget(remove_import_btn)
        imports_btn_layout.addWidget(detect_imports_btn)
        imports_btn_layout.addWidget(import_reqs_btn)
        imports_layout.addWidget(self.hidden_imports_list)
        imports_layout.addLayout(imports_btn_layout)
        layout.addWidget(imports_group)

        extra_group = QGroupBox(S.GROUP_EXTRA_OPTS)
        extra_layout = QGridLayout(extra_group)
        extra_layout.addWidget(QLabel(S.OPT_LEVEL_LABEL), 0, 0)
        self.optimize_combo = QComboBox()
        self.optimize_combo.addItems(S.OPT_LEVELS)
        extra_layout.addWidget(self.optimize_combo, 0, 1)

        extra_layout.addWidget(QLabel(S.UPX_DIR_LABEL), 1, 0)
        self.upx_dir = QLineEdit()
        self.upx_dir.setPlaceholderText(S.UPX_DIR_PLACEHOLDER)
        upx_dir_btn = browse_button(S.UPX_DIR_LABEL, self.browse_upx_dir)
        extra_layout.addWidget(self.upx_dir, 1, 1)
        extra_layout.addWidget(upx_dir_btn, 1, 2)

        self.upx_check = QCheckBox(S.UPX_USE)
        self.upx_check.setToolTip(S.UPX_USE_TIP)
        extra_layout.addWidget(self.upx_check, 2, 0, 1, 3)
        layout.addWidget(extra_group)

        cmd_group = QGroupBox(S.GROUP_EXTRA_ARGS)
        cmd_layout = QVBoxLayout(cmd_group)
        self.extra_args = QLineEdit()
        self.extra_args.setPlaceholderText(S.EXTRA_ARGS_PLACEHOLDER)
        cmd_layout.addWidget(self.extra_args)
        layout.addWidget(cmd_group)

        layout.addStretch()


    # ── Extra data files ───────────────────────────────────────────────────

    def add_extra_file(self):
        path = self._choose_file(S.DIALOG_CHOOSE_EXTRA_FILE, S.DIALOG_FILTER_ALL)
        if path:
            self.extra_files_list.addItem(path)

    def add_extra_folder(self):
        path = self._choose_dir(S.DIALOG_CHOOSE_EXTRA_FOLDER)
        if path:
            self.extra_files_list.addItem(path)

    def remove_extra_file(self):
        row = self.extra_files_list.currentRow()
        if row >= 0:
            self.extra_files_list.takeItem(row)

    # ── Hidden imports ─────────────────────────────────────────────────────

    def add_hidden_import(self):
        dialog = AddImportDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            value = dialog.get_value()
            if value:
                self.hidden_imports_list.addItem(value)

    def remove_hidden_import(self):
        row = self.hidden_imports_list.currentRow()
        if row >= 0:
            self.hidden_imports_list.takeItem(row)

    def hidden_imports(self):
        """Current hidden-import entries as a plain list."""
        return [
            self.hidden_imports_list.item(i).text()
            for i in range(self.hidden_imports_list.count())
        ]

    def extra_files(self):
        """Current extra-file entries as a plain list."""
        return [
            self.extra_files_list.item(i).text()
            for i in range(self.extra_files_list.count())
        ]

    def merge_hidden_imports(self, modules):
        """Add modules that are not already listed. Returns the ones added."""
        existing = set(self.hidden_imports())
        added = [m for m in sorted(modules) if m not in existing]
        for module in added:
            self.hidden_imports_list.addItem(module)
        return added

    def browse_upx_dir(self):
        path = self._choose_dir(S.UPX_DIR_LABEL)
        if path:
            self.upx_dir.setText(path)
