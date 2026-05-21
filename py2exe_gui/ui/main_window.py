"""Main application window."""

import json
import os
import subprocess
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QKeySequence
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QShortcut,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from py2exe_gui.constants import (
    APP_NAME,
    APP_VERSION,
    COPYRIGHT,
    DEVELOPER,
    EMAIL,
    SETTINGS_FILE,
)
from py2exe_gui.core import (
    BuildConfig,
    build_pyinstaller_command,
    detect_imports,
    format_html,
)
from py2exe_gui.core.dependency_analyzer import filter_non_stdlib
from py2exe_gui.strings import S
from py2exe_gui.styles import THEMES
from py2exe_gui.templates import TEMPLATES
from py2exe_gui.ui.conversion_thread import ConversionThread
from py2exe_gui.ui.dialogs import AddImportDialog, CommandPreviewDialog


class MainWindow(QMainWindow):
    """النافذة الرئيسية للتطبيق."""

    def __init__(self):
        super().__init__()
        self.conversion_thread = None
        self.settings = {}
        self.current_theme = "dark"
        self.load_settings()
        self.current_theme = self.settings.get("theme", "dark")
        self.init_ui()
        self._register_shortcuts()
        self.setAcceptDrops(True)
        self.check_dependencies()

    def init_ui(self):
        self.setWindowTitle(S.WINDOW_TITLE_FMT.format(name=APP_NAME, version=APP_VERSION))
        self.setMinimumSize(1080, 800)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setStyleSheet(THEMES.get(self.current_theme, THEMES["dark"]))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        main_layout.addWidget(self._create_header())

        tabs = QTabWidget()
        tabs.addTab(self._create_main_tab(), S.TAB_MAIN)
        tabs.addTab(self._create_advanced_tab(), S.TAB_ADVANCED)
        tabs.addTab(self._create_templates_tab(), S.TAB_TEMPLATES)
        tabs.addTab(self._create_about_tab(), S.TAB_ABOUT)
        main_layout.addWidget(tabs)

        progress_group = QGroupBox(S.PROGRESS_GROUP)
        progress_layout = QVBoxLayout(progress_group)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(S.PROGRESS_READY)
        progress_layout.addWidget(self.progress_bar)
        main_layout.addWidget(progress_group)

        buttons_layout = QHBoxLayout()
        self.convert_btn = QPushButton(S.BTN_CONVERT)
        self.convert_btn.setObjectName("successBtn")
        self.convert_btn.setMinimumHeight(50)
        self.convert_btn.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.convert_btn.clicked.connect(self.start_conversion)

        self.cancel_btn = QPushButton(S.BTN_CANCEL)
        self.cancel_btn.setObjectName("dangerBtn")
        self.cancel_btn.setMinimumHeight(50)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_conversion)

        self.preview_btn = QPushButton(S.BTN_PREVIEW_CMD)
        self.preview_btn.setMinimumHeight(50)
        self.preview_btn.clicked.connect(self.preview_command)

        self.open_folder_btn = QPushButton(S.BTN_OPEN_FOLDER)
        self.open_folder_btn.setMinimumHeight(50)
        self.open_folder_btn.clicked.connect(self.open_output_folder)

        self.theme_btn = QPushButton(S.BTN_TOGGLE_THEME)
        self.theme_btn.setMinimumHeight(50)
        self.theme_btn.clicked.connect(self.toggle_theme)

        buttons_layout.addWidget(self.convert_btn)
        buttons_layout.addWidget(self.cancel_btn)
        buttons_layout.addWidget(self.preview_btn)
        buttons_layout.addWidget(self.open_folder_btn)
        buttons_layout.addWidget(self.theme_btn)
        main_layout.addLayout(buttons_layout)

        self.statusBar().showMessage(f"{COPYRIGHT} | {DEVELOPER}")

    def _create_header(self):
        header = QFrame()
        header_layout = QVBoxLayout(header)
        header_layout.setAlignment(Qt.AlignCenter)

        title = QLabel(S.HEADER_TITLE)
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel(S.HEADER_SUBTITLE)
        subtitle.setObjectName("subtitleLabel")
        subtitle.setAlignment(Qt.AlignCenter)

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        return header

    def _create_main_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        source_group = QGroupBox(S.GROUP_SOURCE)
        source_layout = QHBoxLayout(source_group)
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText(S.SOURCE_PLACEHOLDER)
        self.source_input.textChanged.connect(self.on_source_changed)
        source_btn = QPushButton("📂")
        source_btn.clicked.connect(self.browse_source)
        source_layout.addWidget(self.source_input, stretch=4)
        source_layout.addWidget(source_btn, stretch=1)
        layout.addWidget(source_group)

        output_group = QGroupBox(S.GROUP_OUTPUT)
        output_layout = QGridLayout(output_group)

        output_layout.addWidget(QLabel(S.OUTPUT_NAME_LABEL), 0, 0)
        self.output_name = QLineEdit()
        self.output_name.setPlaceholderText(S.OUTPUT_NAME_PLACEHOLDER)
        output_layout.addWidget(self.output_name, 0, 1)

        output_layout.addWidget(QLabel(S.OUTPUT_DIR_LABEL), 1, 0)
        self.output_dir = QLineEdit()
        self.output_dir.setPlaceholderText(S.OUTPUT_DIR_PLACEHOLDER)
        output_dir_btn = QPushButton("📂")
        output_dir_btn.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(self.output_dir, 1, 1)
        output_layout.addWidget(output_dir_btn, 1, 2)

        output_layout.addWidget(QLabel(S.ICON_LABEL), 2, 0)
        self.icon_input = QLineEdit()
        self.icon_input.setPlaceholderText(S.ICON_PLACEHOLDER)
        icon_btn = QPushButton("📂")
        icon_btn.clicked.connect(self.browse_icon)
        output_layout.addWidget(self.icon_input, 2, 1)
        output_layout.addWidget(icon_btn, 2, 2)

        layout.addWidget(output_group)

        options_group = QGroupBox(S.GROUP_OPTIONS)
        options_layout = QVBoxLayout(options_group)

        row1 = QHBoxLayout()
        self.onefile_check = QCheckBox(S.OPT_ONEFILE)
        self.onefile_check.setChecked(True)
        self.onefile_check.setToolTip(S.OPT_ONEFILE_TIP)
        self.windowed_check = QCheckBox(S.OPT_WINDOWED)
        self.windowed_check.setToolTip(S.OPT_WINDOWED_TIP)
        self.clean_check = QCheckBox(S.OPT_CLEAN)
        self.clean_check.setChecked(True)
        self.clean_check.setToolTip(S.OPT_CLEAN_TIP)
        row1.addWidget(self.onefile_check)
        row1.addWidget(self.windowed_check)
        row1.addWidget(self.clean_check)

        row2 = QHBoxLayout()
        self.noconsole_check = QCheckBox(S.OPT_NOCONSOLE)
        self.noconsole_check.setToolTip(S.OPT_NOCONSOLE_TIP)
        self.noconfirm_check = QCheckBox(S.OPT_NOCONFIRM)
        self.noconfirm_check.setChecked(True)
        self.noconfirm_check.setToolTip(S.OPT_NOCONFIRM_TIP)
        self.strip_check = QCheckBox(S.OPT_STRIP)
        self.strip_check.setToolTip(S.OPT_STRIP_TIP)
        row2.addWidget(self.noconsole_check)
        row2.addWidget(self.noconfirm_check)
        row2.addWidget(self.strip_check)

        options_layout.addLayout(row1)
        options_layout.addLayout(row2)
        layout.addWidget(options_group)

        log_group = QGroupBox(S.GROUP_LOG)
        log_layout = QVBoxLayout(log_group)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(150)

        search_row = QHBoxLayout()
        self.log_search = QLineEdit()
        self.log_search.setPlaceholderText(S.LOG_SEARCH_PLACEHOLDER)
        self.log_search.returnPressed.connect(self._search_log_next)
        self.log_search.textChanged.connect(self._search_log_next)
        search_row.addWidget(self.log_search)

        log_btn_row = QHBoxLayout()
        clear_log_btn = QPushButton(S.CLEAR_LOG)
        clear_log_btn.clicked.connect(lambda: self.log_output.clear())
        export_log_btn = QPushButton(S.BTN_EXPORT_LOG)
        export_log_btn.clicked.connect(self.export_log)
        log_btn_row.addWidget(clear_log_btn)
        log_btn_row.addWidget(export_log_btn)

        log_layout.addLayout(search_row)
        log_layout.addWidget(self.log_output)
        log_layout.addLayout(log_btn_row)
        layout.addWidget(log_group)

        return tab

    def _create_advanced_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

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
        detect_imports_btn.clicked.connect(self.detect_imports_action)
        imports_btn_layout.addWidget(add_import_btn)
        imports_btn_layout.addWidget(remove_import_btn)
        imports_btn_layout.addWidget(detect_imports_btn)
        imports_layout.addWidget(self.hidden_imports_list)
        imports_layout.addLayout(imports_btn_layout)
        layout.addWidget(imports_group)

        extra_group = QGroupBox(S.GROUP_EXTRA_OPTS)
        extra_layout = QGridLayout(extra_group)
        extra_layout.addWidget(QLabel(S.OPT_LEVEL_LABEL), 0, 0)
        self.optimize_combo = QComboBox()
        self.optimize_combo.addItems(S.OPT_LEVELS)
        extra_layout.addWidget(self.optimize_combo, 0, 1)

        extra_layout.addWidget(QLabel(S.UPX_LEVEL_LABEL), 1, 0)
        self.upx_level = QSpinBox()
        self.upx_level.setRange(0, 9)
        self.upx_level.setValue(0)
        self.upx_level.setToolTip(S.UPX_LEVEL_TIP)
        extra_layout.addWidget(self.upx_level, 1, 1)

        self.upx_check = QCheckBox(S.UPX_USE)
        self.upx_check.setToolTip(S.UPX_USE_TIP)
        extra_layout.addWidget(self.upx_check, 2, 0, 1, 2)
        layout.addWidget(extra_group)

        cmd_group = QGroupBox(S.GROUP_EXTRA_ARGS)
        cmd_layout = QVBoxLayout(cmd_group)
        self.extra_args = QLineEdit()
        self.extra_args.setPlaceholderText(S.EXTRA_ARGS_PLACEHOLDER)
        cmd_layout.addWidget(self.extra_args)
        layout.addWidget(cmd_group)

        layout.addStretch()
        return tab

    def _create_templates_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        templates_group = QGroupBox(S.GROUP_TEMPLATES)
        templates_layout = QVBoxLayout(templates_group)
        templates_layout.addWidget(QLabel(S.TEMPLATES_HINT))

        self.templates_combo = QComboBox()
        for name, data in TEMPLATES.items():
            self.templates_combo.addItem(f"{name} - {data['description']}", name)
        self.templates_combo.currentIndexChanged.connect(self.apply_template)
        templates_layout.addWidget(self.templates_combo)

        self.template_desc = QTextEdit()
        self.template_desc.setReadOnly(True)
        self.template_desc.setMaximumHeight(100)
        templates_layout.addWidget(self.template_desc)

        apply_btn = QPushButton(S.BTN_APPLY_TEMPLATE)
        apply_btn.clicked.connect(self.apply_selected_template)
        templates_layout.addWidget(apply_btn)
        layout.addWidget(templates_group)

        save_group = QGroupBox(S.GROUP_SAVE_LOAD)
        save_layout = QVBoxLayout(save_group)
        save_layout.addWidget(QLabel(S.SAVE_LOAD_HINT))
        save_btn_layout = QHBoxLayout()
        save_settings_btn = QPushButton(S.BTN_SAVE_SETTINGS)
        save_settings_btn.clicked.connect(self.save_current_settings)
        load_settings_btn = QPushButton(S.BTN_LOAD_SETTINGS)
        load_settings_btn.clicked.connect(self.load_saved_settings)
        save_btn_layout.addWidget(save_settings_btn)
        save_btn_layout.addWidget(load_settings_btn)
        save_layout.addLayout(save_btn_layout)
        layout.addWidget(save_group)

        layout.addStretch()
        return tab

    def _create_about_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setAlignment(Qt.AlignCenter)

        features_html = "".join(f"<li>{f}</li>" for f in S.ABOUT_FEATURES)
        about_text = f"""
        <div style='text-align: center; direction: rtl;'>
            <h1 style='color: #89b4fa;'>🐍 {APP_NAME}</h1>
            <h3 style='color: #a6e3a1;'>{S.ABOUT_VERSION_FMT.format(version=APP_VERSION)}</h3>
            <hr style='border: 1px solid #45475a; margin: 20px 0;'>
            <p style='font-size: 14px; color: #cdd6f4;'>{S.ABOUT_DESC}</p>
            <hr style='border: 1px solid #45475a; margin: 20px 0;'>
            <h3 style='color: #f9e2af;'>{S.ABOUT_DEVELOPER_LABEL}</h3>
            <p style='font-size: 16px; color: #cdd6f4; font-weight: bold;'>{DEVELOPER}</p>
            <p style='color: #89b4fa;'>📧 {EMAIL}</p>
            <hr style='border: 1px solid #45475a; margin: 20px 0;'>
            <p style='color: #6c7086; font-size: 12px;'>{COPYRIGHT}</p>
            <hr style='border: 1px solid #45475a; margin: 20px 0;'>
            <h4 style='color: #cba6f7;'>{S.ABOUT_FEATURES_LABEL}</h4>
            <ul style='text-align: right; color: #cdd6f4;'>{features_html}</ul>
        </div>
        """
        about_label = QLabel(about_text)
        about_label.setWordWrap(True)
        about_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(about_label)
        return tab

    # ─── Actions ────────────────────────────────────────────────────────

    def check_dependencies(self):
        self._append_log(S.LOG_CHECKING_DEPS)
        try:
            result = subprocess.run(
                [sys.executable, "--version"], capture_output=True, text=True
            )
            self._append_log(S.LOG_PYTHON_FOUND.format(version=result.stdout.strip()))
        except Exception:
            self._append_log(S.LOG_PYTHON_MISSING)

        try:
            result = subprocess.run(
                [sys.executable, "-m", "PyInstaller", "--version"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                self._append_log(
                    S.LOG_PYINSTALLER_FOUND.format(version=result.stdout.strip())
                )
            else:
                self._append_log(S.LOG_PYINSTALLER_MISSING)
        except Exception:
            self._append_log(S.LOG_PYINSTALLER_MISSING)

        self._append_log("─" * 50)
        self._append_log(S.LOG_READY)

    def browse_source(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            S.DIALOG_CHOOSE_PY,
            self.settings.get("last_source_dir", ""),
            S.DIALOG_FILTER_PY,
        )
        if file_path:
            self.source_input.setText(file_path)
            self.settings["last_source_dir"] = os.path.dirname(file_path)

    def on_source_changed(self, text):
        if text and os.path.isfile(text):
            base_name = os.path.splitext(os.path.basename(text))[0]
            if not self.output_name.text():
                self.output_name.setText(base_name)
            if not self.output_dir.text():
                self.output_dir.setText(os.path.dirname(text))

    def browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, S.DIALOG_CHOOSE_OUT_DIR, self.settings.get("last_output_dir", "")
        )
        if dir_path:
            self.output_dir.setText(dir_path)
            self.settings["last_output_dir"] = dir_path

    def browse_icon(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, S.DIALOG_CHOOSE_ICON, "", S.DIALOG_FILTER_ICON
        )
        if file_path:
            self.icon_input.setText(file_path)

    def add_extra_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, S.DIALOG_CHOOSE_EXTRA_FILE, "", S.DIALOG_FILTER_ALL
        )
        if file_path:
            self.extra_files_list.addItem(file_path)

    def add_extra_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, S.DIALOG_CHOOSE_EXTRA_FOLDER, "")
        if dir_path:
            self.extra_files_list.addItem(dir_path)

    def remove_extra_file(self):
        current = self.extra_files_list.currentRow()
        if current >= 0:
            self.extra_files_list.takeItem(current)

    def add_hidden_import(self):
        dialog = AddImportDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            value = dialog.get_value()
            if value:
                self.hidden_imports_list.addItem(value)

    def remove_hidden_import(self):
        current = self.hidden_imports_list.currentRow()
        if current >= 0:
            self.hidden_imports_list.takeItem(current)

    def detect_imports_action(self):
        source = self.source_input.text()
        if not source or not os.path.isfile(source):
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_NO_SOURCE)
            return

        self._append_log(S.LOG_DETECTING_IMPORTS)
        try:
            with open(source, encoding="utf-8") as f:
                content = f.read()

            imports = detect_imports(content)
            existing = [
                self.hidden_imports_list.item(i).text()
                for i in range(self.hidden_imports_list.count())
            ]
            new_imports = filter_non_stdlib(imports, existing=existing)
            for imp in new_imports:
                self.hidden_imports_list.addItem(imp)

            self._append_log(
                S.LOG_DETECT_RESULT.format(total=len(imports), added=len(new_imports))
            )
        except Exception as e:
            self._append_log(S.LOG_DETECT_ERROR.format(error=str(e)))

    def apply_template(self, index):
        template_name = self.templates_combo.currentData()
        if template_name and template_name in TEMPLATES:
            template = TEMPLATES[template_name]
            imports_str = (
                ", ".join(template["hidden_imports"])
                if template["hidden_imports"]
                else S.NONE
            )
            desc = S.TEMPLATE_DESC_FMT.format(
                name=template_name,
                desc=template["description"],
                windowed=S.YES if template["windowed"] else S.NO,
                onefile=S.YES if template["onefile"] else S.NO,
                imports=imports_str,
            )
            self.template_desc.setHtml(desc)

    def apply_selected_template(self):
        template_name = self.templates_combo.currentData()
        if template_name and template_name in TEMPLATES:
            template = TEMPLATES[template_name]
            self.windowed_check.setChecked(template["windowed"])
            self.onefile_check.setChecked(template["onefile"])
            existing = [
                self.hidden_imports_list.item(i).text()
                for i in range(self.hidden_imports_list.count())
            ]
            for imp in template["hidden_imports"]:
                if imp not in existing:
                    self.hidden_imports_list.addItem(imp)
            self._append_log(S.LOG_TEMPLATE_APPLIED.format(name=template_name))
            QMessageBox.information(
                self, S.MSG_SUCCESS, S.MSG_TEMPLATE_OK_FMT.format(name=template_name)
            )

    def _current_config(self) -> BuildConfig:
        return BuildConfig(
            source=self.source_input.text(),
            output_name=self.output_name.text(),
            output_dir=self.output_dir.text(),
            icon=self.icon_input.text(),
            onefile=self.onefile_check.isChecked(),
            windowed=self.windowed_check.isChecked(),
            noconsole=self.noconsole_check.isChecked(),
            clean=self.clean_check.isChecked(),
            noconfirm=self.noconfirm_check.isChecked(),
            strip=self.strip_check.isChecked(),
            extra_files=[
                self.extra_files_list.item(i).text()
                for i in range(self.extra_files_list.count())
            ],
            hidden_imports=[
                self.hidden_imports_list.item(i).text()
                for i in range(self.hidden_imports_list.count())
            ],
            optimize=self.optimize_combo.currentIndex(),
            upx=self.upx_check.isChecked(),
            upx_level=self.upx_level.value(),
            extra_args=self.extra_args.text(),
        )

    def _apply_config(self, config: BuildConfig):
        self.source_input.setText(config.source)
        self.output_name.setText(config.output_name)
        self.output_dir.setText(config.output_dir)
        self.icon_input.setText(config.icon)
        self.onefile_check.setChecked(config.onefile)
        self.windowed_check.setChecked(config.windowed)
        self.clean_check.setChecked(config.clean)
        self.noconsole_check.setChecked(config.noconsole)
        self.noconfirm_check.setChecked(config.noconfirm)
        self.strip_check.setChecked(config.strip)
        self.extra_files_list.clear()
        for f in config.extra_files:
            self.extra_files_list.addItem(f)
        self.hidden_imports_list.clear()
        for imp in config.hidden_imports:
            self.hidden_imports_list.addItem(imp)
        self.optimize_combo.setCurrentIndex(config.optimize)
        self.upx_check.setChecked(config.upx)
        self.upx_level.setValue(config.upx_level)
        self.extra_args.setText(config.extra_args)

    def save_current_settings(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, S.DIALOG_SAVE_SETTINGS, "py2exe_config.json", S.DIALOG_FILTER_JSON
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self._current_config().to_dict(), f, ensure_ascii=False, indent=2)
            self._append_log(S.LOG_SETTINGS_SAVED.format(path=file_path))
            QMessageBox.information(self, S.MSG_SUCCESS, S.MSG_SAVED_OK)
        except Exception as e:
            QMessageBox.critical(self, S.MSG_ERROR, S.ERR_SAVE_FAIL.format(error=str(e)))

    def load_saved_settings(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, S.DIALOG_LOAD_SETTINGS, "", S.DIALOG_FILTER_JSON
        )
        if not file_path:
            return
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            self._apply_config(BuildConfig.from_dict(data))
            self._append_log(S.LOG_SETTINGS_LOADED.format(path=file_path))
            QMessageBox.information(self, S.MSG_SUCCESS, S.MSG_LOADED_OK)
        except Exception as e:
            QMessageBox.critical(self, S.MSG_ERROR, S.ERR_LOAD_FAIL.format(error=str(e)))

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, encoding="utf-8") as f:
                    self.settings = json.load(f)
            except Exception:
                self.settings = {}

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def start_conversion(self):
        cmd, error = build_pyinstaller_command(self._current_config())
        if error:
            QMessageBox.warning(self, S.MSG_WARNING, error)
            return

        try:
            subprocess.run(
                [sys.executable, "-m", "PyInstaller", "--version"],
                capture_output=True,
                check=True,
            )
        except Exception:
            self._append_log(S.LOG_INSTALL_PYINSTALLER)
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "pyinstaller"],
                    capture_output=True,
                    check=True,
                )
                self._append_log(S.LOG_INSTALL_PYINSTALLER_OK)
            except Exception as e:
                QMessageBox.critical(
                    self, S.MSG_ERROR, S.ERR_INSTALL_PYINSTALLER_FAIL.format(error=str(e))
                )
                return

        work_dir = self.output_dir.text() or os.path.dirname(self.source_input.text())

        self.convert_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(S.PROGRESS_CONVERTING)

        self.conversion_thread = ConversionThread(cmd, work_dir)
        self.conversion_thread.log_signal.connect(self._append_log)
        self.conversion_thread.progress_signal.connect(self.progress_bar.setValue)
        self.conversion_thread.finished_signal.connect(self.on_conversion_finished)
        self.conversion_thread.start()

    def cancel_conversion(self):
        if self.conversion_thread and self.conversion_thread.isRunning():
            self.conversion_thread.cancel()
            self._append_log(S.LOG_CANCELLING)

    def on_conversion_finished(self, success, message):
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        if success:
            self.progress_bar.setFormat(S.PROGRESS_DONE)
            QMessageBox.information(self, S.MSG_SUCCESS, message)
        else:
            self.progress_bar.setFormat(S.PROGRESS_FAILED)
            if "إلغاء" not in message:
                QMessageBox.critical(self, S.MSG_ERROR, message)

    def open_output_folder(self):
        output_dir = self.output_dir.text() or os.path.dirname(self.source_input.text())
        dist_dir = os.path.join(output_dir, "dist")
        if os.path.isdir(dist_dir):
            target = dist_dir
        elif os.path.isdir(output_dir):
            target = output_dir
        else:
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_OUTPUT_MISSING)
            return

        if sys.platform == "win32":
            os.startfile(target)
        elif sys.platform == "darwin":
            subprocess.run(["open", target])
        else:
            subprocess.run(["xdg-open", target])

    # ─── Phase 2: log / preview / theme / shortcuts / drag-drop ────────

    def _append_log(self, line: str):
        """Append a single line to the log, coloured by severity."""
        if line is None:
            return
        text = str(line)
        # Preserve blank lines without HTML wrapping.
        if text.strip() == "":
            self.log_output.append("")
            return
        self.log_output.append(format_html(text))

    def _search_log_next(self):
        """Find the next occurrence of the search query in the log."""
        query = self.log_search.text().strip()
        if not query:
            return
        if not self.log_output.find(query):
            # Wrap to the start and try again.
            cursor = self.log_output.textCursor()
            cursor.movePosition(cursor.Start)
            self.log_output.setTextCursor(cursor)
            self.log_output.find(query)

    def export_log(self):
        """Save the current log contents to a text file."""
        if not self.log_output.toPlainText().strip():
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            S.DIALOG_EXPORT_LOG,
            "py2exe_log.txt",
            S.DIALOG_FILTER_LOG,
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.log_output.toPlainText())
            self._append_log(S.LOG_EXPORT_OK.format(path=file_path))
        except Exception as e:
            QMessageBox.critical(
                self, S.MSG_ERROR, S.LOG_EXPORT_FAIL.format(error=str(e))
            )

    def preview_command(self):
        """Show the PyInstaller command that would be executed."""
        cmd, error = build_pyinstaller_command(self._current_config())
        if error:
            QMessageBox.warning(self, S.MSG_WARNING, error)
            return
        CommandPreviewDialog(cmd, parent=self).exec_()

    def toggle_theme(self):
        """Swap between dark and light themes and persist the choice."""
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.setStyleSheet(THEMES[self.current_theme])
        self.settings["theme"] = self.current_theme

    def _register_shortcuts(self):
        """Bind keyboard shortcuts to common actions."""
        bindings = [
            (QKeySequence("Ctrl+O"), self.browse_source),
            (QKeySequence("Ctrl+B"), self.start_conversion),
            (QKeySequence("Ctrl+Shift+B"), self.cancel_conversion),
            (QKeySequence("Ctrl+P"), self.preview_command),
            (QKeySequence("Ctrl+L"), self.log_output.clear),
            (QKeySequence("Ctrl+E"), self.export_log),
            (QKeySequence("Ctrl+S"), self.save_current_settings),
            (QKeySequence("Ctrl+T"), self.toggle_theme),
            (QKeySequence("F5"), self.detect_imports_action),
            (QKeySequence("Ctrl+F"), self.log_search.setFocus),
        ]
        for seq, slot in bindings:
            shortcut = QShortcut(seq, self)
            shortcut.activated.connect(slot)

    # ─── Drag & drop ─────────────────────────────────────────────────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return
        for url in urls:
            path = url.toLocalFile()
            if not path:
                continue
            self._handle_dropped_path(path)
        event.acceptProposedAction()

    def _handle_dropped_path(self, path: str):
        """Route a dropped path to the appropriate field based on its kind."""
        if os.path.isdir(path):
            self.extra_files_list.addItem(path)
            self._append_log(S.LOG_DROPPED_EXTRA.format(path=path))
            return

        ext = os.path.splitext(path)[1].lower()
        if ext in (".py", ".pyw"):
            self.source_input.setText(path)
            self._append_log(S.LOG_DROPPED_SOURCE.format(path=path))
        elif ext == ".ico":
            self.icon_input.setText(path)
            self._append_log(S.LOG_DROPPED_ICON.format(path=path))
        else:
            self.extra_files_list.addItem(path)
            self._append_log(S.LOG_DROPPED_EXTRA.format(path=path))

    def closeEvent(self, event):
        self.save_settings()
        if self.conversion_thread and self.conversion_thread.isRunning():
            reply = QMessageBox.question(
                self,
                S.MSG_CONFIRM,
                S.MSG_CLOSE_CONFIRM,
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.conversion_thread.cancel()
                self.conversion_thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
