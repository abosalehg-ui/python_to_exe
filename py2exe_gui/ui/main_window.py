"""Main application window."""

import json
import os
import subprocess
import sys
import tempfile
import time

from PyQt5.QtCore import Qt, QTimer
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
    QScrollArea,
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
    HISTORY_FILE,
    PYINSTALLER_REQUIREMENT,
    SETTINGS_FILE,
)
from py2exe_gui.core import (
    BuildConfig,
    BuildHistory,
    InstallerConfig,
    ManifestConfig,
    SigningConfig,
    VersionInfo,
    build_iscc_command,
    build_pyinstaller_command,
    build_signtool_command,
    detect_imports,
    find_dangerous_args,
    find_iscc,
    format_html,
    generate_iss_script,
    generate_manifest,
    generate_version_file,
    installer_output_path,
    locate_built_executable,
    make_record,
    parse_requirements,
    redact_password,
    resolve_languages,
)
from py2exe_gui.core.dependency_analyzer import filter_non_stdlib
from py2exe_gui.core.installer import (
    COMPRESSION_CHOICES,
    LANGUAGE_LABELS,
)
from py2exe_gui.core.installer import (
    validate as validate_installer,
)
from py2exe_gui.strings import (
    LOCALE_LAYOUT,
    S,
    available_locales,
    current_locale,
)
from py2exe_gui.styles import themed_stylesheet
from py2exe_gui.templates import TEMPLATES, template_description, template_name
from py2exe_gui.ui.conversion_thread import ConversionThread
from py2exe_gui.ui.dialogs import AddImportDialog, CommandPreviewDialog
from py2exe_gui.ui.installer_thread import InstallerThread
from py2exe_gui.ui.post_build_thread import PostBuildThread


def _browse_button(label: str, handler) -> QPushButton:
    """A '📂' button that screen readers and tooltips can actually describe.

    Five identical emoji-only buttons previously exposed no name at all, so
    keyboard and screen-reader users had no way to tell them apart.
    """
    button = QPushButton("📂")
    button.setToolTip(label)
    button.setAccessibleName(label)
    button.setAccessibleDescription(label)
    button.clicked.connect(handler)
    return button


class MainWindow(QMainWindow):
    """النافذة الرئيسية للتطبيق."""

    def __init__(self):
        super().__init__()
        self.conversion_thread = None
        self.installer_thread = None
        self.post_build_thread = None
        self.settings = {}
        self.current_theme = "dark"
        self._build_start_time = 0.0
        self._build_config_snapshot = {}
        self._temp_version_file = ""
        self._temp_manifest_file = ""
        self._last_built_exe = ""
        self.history = BuildHistory(HISTORY_FILE)
        self.load_settings()
        self.current_theme = self.settings.get("theme", "dark")
        self.init_ui()
        self._register_shortcuts()
        self.setAcceptDrops(True)
        self.check_dependencies()
        self._refresh_history_list()

    def init_ui(self):
        self.setWindowTitle(S.WINDOW_TITLE_FMT.format(name=APP_NAME, version=APP_VERSION))
        # A hard 800px minimum did not fit a 1366x768 laptop. Keep the
        # comfortable size as the *default*, not as a floor.
        self.setMinimumSize(900, 600)
        self.resize(1080, 800)
        direction = (
            Qt.RightToLeft
            if LOCALE_LAYOUT.get(current_locale(), "rtl") == "rtl"
            else Qt.LeftToRight
        )
        self.setLayoutDirection(direction)
        self.setStyleSheet(themed_stylesheet(self.current_theme, current_locale()))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        main_layout.addWidget(self._create_header())

        tabs = self.tabs = QTabWidget()
        tabs.addTab(self._create_main_tab(), S.TAB_MAIN)
        tabs.addTab(self._create_advanced_tab(), S.TAB_ADVANCED)
        tabs.addTab(self._create_version_info_tab(), S.TAB_VERSION_INFO)
        tabs.addTab(self._create_deploy_tab(), S.TAB_DEPLOY)
        tabs.addTab(self._create_installer_tab(), S.TAB_INSTALLER)
        tabs.addTab(self._create_templates_tab(), S.TAB_TEMPLATES)
        tabs.addTab(self._create_history_tab(), S.TAB_HISTORY)
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
        source_btn = _browse_button(S.DIALOG_CHOOSE_PY, self.browse_source)
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
        output_dir_btn = _browse_button(S.DIALOG_CHOOSE_OUT_DIR, self.browse_output_dir)
        output_layout.addWidget(self.output_dir, 1, 1)
        output_layout.addWidget(output_dir_btn, 1, 2)

        output_layout.addWidget(QLabel(S.ICON_LABEL), 2, 0)
        self.icon_input = QLineEdit()
        self.icon_input.setPlaceholderText(S.ICON_PLACEHOLDER)
        icon_btn = _browse_button(S.DIALOG_CHOOSE_ICON, self.browse_icon)
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
        # Debounced: searching on every keystroke made the cursor jump around.
        self._log_search_timer = QTimer(self)
        self._log_search_timer.setSingleShot(True)
        self._log_search_timer.setInterval(300)
        self._log_search_timer.timeout.connect(self._search_log_next)
        self.log_search.textChanged.connect(self._log_search_timer.start)
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
        import_reqs_btn = QPushButton(S.BTN_IMPORT_REQUIREMENTS)
        import_reqs_btn.clicked.connect(self.import_requirements_file)
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
        upx_dir_btn = _browse_button(S.UPX_DIR_LABEL, self.browse_upx_dir)
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
        return tab

    def _create_templates_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

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

        # Language selector (Phase 3)
        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel(S.LANGUAGE_LABEL))
        self.language_combo = QComboBox()
        current = current_locale()
        for code, native in available_locales().items():
            self.language_combo.addItem(native, code)
            if code == current:
                self.language_combo.setCurrentIndex(self.language_combo.count() - 1)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_row.addWidget(self.language_combo)
        lang_row.addStretch()
        layout.addLayout(lang_row)

        layout.addStretch()
        return tab

    def _create_version_info_tab(self):
        """Form for the optional Windows file metadata (--version-file)."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        group = QGroupBox(S.GROUP_VERSION_INFO)
        grid = QGridLayout(group)
        grid.addWidget(QLabel(S.VERSION_INFO_HINT), 0, 0, 1, 2)

        self.vi_company_name = QLineEdit()
        self.vi_file_description = QLineEdit()
        self.vi_file_version = QLineEdit()
        self.vi_file_version.setPlaceholderText(S.VI_PLACEHOLDER_VERSION)
        self.vi_internal_name = QLineEdit()
        self.vi_legal_copyright = QLineEdit()
        self.vi_original_filename = QLineEdit()
        self.vi_product_name = QLineEdit()
        self.vi_product_version = QLineEdit()
        self.vi_product_version.setPlaceholderText(S.VI_PLACEHOLDER_VERSION)

        rows = [
            (S.VI_COMPANY_NAME, self.vi_company_name),
            (S.VI_FILE_DESCRIPTION, self.vi_file_description),
            (S.VI_FILE_VERSION, self.vi_file_version),
            (S.VI_INTERNAL_NAME, self.vi_internal_name),
            (S.VI_LEGAL_COPYRIGHT, self.vi_legal_copyright),
            (S.VI_ORIGINAL_FILENAME, self.vi_original_filename),
            (S.VI_PRODUCT_NAME, self.vi_product_name),
            (S.VI_PRODUCT_VERSION, self.vi_product_version),
        ]
        for i, (label, widget) in enumerate(rows, start=1):
            grid.addWidget(QLabel(label), i, 0)
            grid.addWidget(widget, i, 1)

        layout.addWidget(group)
        layout.addStretch()
        return tab

    def _create_deploy_tab(self):
        """Splash / Manifest / Code signing / Smoke test sections."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # ── Splash ──
        splash_group = QGroupBox(S.GROUP_SPLASH)
        splash_layout = QHBoxLayout(splash_group)
        splash_layout.addWidget(QLabel(S.SPLASH_LABEL))
        self.splash_input = QLineEdit()
        self.splash_input.setPlaceholderText(S.SPLASH_PLACEHOLDER)
        splash_btn = _browse_button(S.DIALOG_CHOOSE_SPLASH, self.browse_splash_image)
        splash_layout.addWidget(self.splash_input, stretch=4)
        splash_layout.addWidget(splash_btn, stretch=1)
        layout.addWidget(splash_group)

        # ── Manifest ──
        manifest_group = QGroupBox(S.GROUP_MANIFEST)
        manifest_layout = QVBoxLayout(manifest_group)
        manifest_layout.addWidget(QLabel(S.MANIFEST_HINT))

        self.manifest_enable = QCheckBox(S.MANIFEST_ENABLE)
        manifest_layout.addWidget(self.manifest_enable)

        self.manifest_dpi = QCheckBox(S.MANIFEST_DPI)
        self.manifest_admin = QCheckBox(S.MANIFEST_ADMIN)
        manifest_layout.addWidget(self.manifest_dpi)
        manifest_layout.addWidget(self.manifest_admin)

        manifest_layout.addWidget(QLabel(S.MANIFEST_OS_LABEL))
        os_row = QHBoxLayout()
        self.manifest_os = {
            "vista": QCheckBox(S.OS_VISTA),
            "7": QCheckBox(S.OS_7),
            "8": QCheckBox(S.OS_8),
            "8.1": QCheckBox(S.OS_81),
            "10": QCheckBox(S.OS_10),
            "11": QCheckBox(S.OS_11),
        }
        # Default: modern Windows supported.
        for code in ("7", "8", "8.1", "10"):
            self.manifest_os[code].setChecked(True)
        for cb in self.manifest_os.values():
            os_row.addWidget(cb)
        manifest_layout.addLayout(os_row)
        layout.addWidget(manifest_group)

        # ── Signing ──
        signing_group = QGroupBox(S.GROUP_SIGNING)
        signing_layout = QGridLayout(signing_group)
        signing_layout.addWidget(QLabel(S.SIGNING_HINT), 0, 0, 1, 3)

        self.signing_enable = QCheckBox(S.SIGNING_ENABLE)
        signing_layout.addWidget(self.signing_enable, 1, 0, 1, 3)

        # Store mode keeps the certificate password off the command line,
        # where any process running as the same user could read it.
        self.signing_use_store = QCheckBox(S.SIGNING_USE_STORE)
        self.signing_use_store.setToolTip(S.SIGNING_USE_STORE_TIP)
        self.signing_use_store.toggled.connect(self._on_signing_mode_changed)
        signing_layout.addWidget(self.signing_use_store, 6, 0, 1, 3)

        self.signing_subject_label = QLabel(S.SIGNING_SUBJECT_LABEL)
        self.signing_subject = QLineEdit()
        self.signing_subject.setPlaceholderText(S.SIGNING_SUBJECT_PLACEHOLDER)
        signing_layout.addWidget(self.signing_subject_label, 7, 0)
        signing_layout.addWidget(self.signing_subject, 7, 1, 1, 2)

        signing_layout.addWidget(QLabel(S.SIGNING_CERT_LABEL), 2, 0)
        self.signing_cert = QLineEdit()
        self.signing_cert.setPlaceholderText(S.SIGNING_CERT_PLACEHOLDER)
        cert_btn = _browse_button(S.DIALOG_CHOOSE_CERT, self.browse_signing_cert)
        signing_layout.addWidget(self.signing_cert, 2, 1)
        signing_layout.addWidget(cert_btn, 2, 2)

        signing_layout.addWidget(QLabel(S.SIGNING_PASSWORD_LABEL), 3, 0)
        self.signing_password = QLineEdit()
        self.signing_password.setEchoMode(QLineEdit.Password)
        self.signing_password.setPlaceholderText(S.SIGNING_PASSWORD_PLACEHOLDER)
        signing_layout.addWidget(self.signing_password, 3, 1, 1, 2)

        signing_layout.addWidget(QLabel(S.SIGNING_TIMESTAMP_LABEL), 4, 0)
        self.signing_timestamp = QLineEdit("http://timestamp.digicert.com")
        signing_layout.addWidget(self.signing_timestamp, 4, 1, 1, 2)

        signing_layout.addWidget(QLabel(S.SIGNING_DESC_LABEL), 5, 0)
        self.signing_description = QLineEdit()
        self.signing_description.setPlaceholderText(S.SIGNING_DESC_PLACEHOLDER)
        signing_layout.addWidget(self.signing_description, 5, 1, 1, 2)

        layout.addWidget(signing_group)

        # ── Smoke test ──
        smoke_group = QGroupBox(S.GROUP_SMOKE)
        smoke_layout = QGridLayout(smoke_group)
        self.smoke_enable = QCheckBox(S.SMOKE_ENABLE)
        smoke_layout.addWidget(self.smoke_enable, 0, 0, 1, 2)
        smoke_layout.addWidget(QLabel(S.SMOKE_TIMEOUT_LABEL), 1, 0)
        self.smoke_timeout = QSpinBox()
        self.smoke_timeout.setRange(1, 60)
        self.smoke_timeout.setValue(5)
        smoke_layout.addWidget(self.smoke_timeout, 1, 1)
        layout.addWidget(smoke_group)

        layout.addStretch()
        return tab

    def _create_installer_tab(self):
        """Inno Setup installer configuration (Phase 7)."""
        inner = QWidget()
        layout = QVBoxLayout(inner)

        header = QGroupBox(S.GROUP_INSTALLER)
        header_layout = QVBoxLayout(header)
        hint = QLabel(S.INSTALLER_HINT)
        hint.setWordWrap(True)
        header_layout.addWidget(hint)
        self.installer_enable = QCheckBox(S.INSTALLER_ENABLE)
        header_layout.addWidget(self.installer_enable)
        layout.addWidget(header)

        # ── Identity ──
        identity = QGroupBox(S.GROUP_INSTALLER_IDENTITY)
        identity_grid = QGridLayout(identity)

        self.inst_app_name = QLineEdit()
        self.inst_app_name.setPlaceholderText(S.INST_APP_NAME_PLACEHOLDER)
        self.inst_version = QLineEdit("1.0.0")
        self.inst_version.setPlaceholderText(S.INST_VERSION_PLACEHOLDER)
        self.inst_publisher = QLineEdit()
        self.inst_publisher.setPlaceholderText(S.INST_PUBLISHER_PLACEHOLDER)
        self.inst_url = QLineEdit()
        self.inst_url.setPlaceholderText(S.INST_URL_PLACEHOLDER)
        self.inst_app_id = QLineEdit()
        self.inst_app_id.setPlaceholderText(S.INST_APPID_PLACEHOLDER)
        self.inst_app_id.setToolTip(S.INST_APPID_TIP)

        for row, (label, widget) in enumerate(
            [
                (S.INST_APP_NAME_LABEL, self.inst_app_name),
                (S.INST_VERSION_LABEL, self.inst_version),
                (S.INST_PUBLISHER_LABEL, self.inst_publisher),
                (S.INST_URL_LABEL, self.inst_url),
                (S.INST_APPID_LABEL, self.inst_app_id),
            ]
        ):
            identity_grid.addWidget(QLabel(label), row, 0)
            identity_grid.addWidget(widget, row, 1)
        layout.addWidget(identity)

        # ── Output ──
        output = QGroupBox(S.GROUP_INSTALLER_OUTPUT)
        output_grid = QGridLayout(output)

        self.inst_out_dir = QLineEdit()
        self.inst_out_dir.setPlaceholderText(S.INST_OUT_DIR_PLACEHOLDER)
        self.inst_out_name = QLineEdit()
        self.inst_out_name.setPlaceholderText(S.INST_OUT_NAME_PLACEHOLDER)
        self.inst_license = QLineEdit()
        self.inst_license.setPlaceholderText(S.INST_LICENSE_PLACEHOLDER)
        self.inst_readme = QLineEdit()
        self.inst_readme.setPlaceholderText(S.INST_README_PLACEHOLDER)
        self.inst_setup_icon = QLineEdit()
        self.inst_setup_icon.setPlaceholderText(S.INST_SETUP_ICON_PLACEHOLDER)

        browse_rows = [
            (S.INST_OUT_DIR_LABEL, self.inst_out_dir, self.browse_installer_out_dir),
            (S.INST_OUT_NAME_LABEL, self.inst_out_name, None),
            (S.INST_LICENSE_LABEL, self.inst_license, self.browse_installer_license),
            (S.INST_README_LABEL, self.inst_readme, self.browse_installer_readme),
            (S.INST_SETUP_ICON_LABEL, self.inst_setup_icon, self.browse_installer_icon),
        ]
        for row, (label, widget, handler) in enumerate(browse_rows):
            output_grid.addWidget(QLabel(label), row, 0)
            output_grid.addWidget(widget, row, 1)
            if handler is not None:
                btn = _browse_button(label, handler)
                output_grid.addWidget(btn, row, 2)
        layout.addWidget(output)

        # ── Options ──
        options = QGroupBox(S.GROUP_INSTALLER_OPTIONS)
        options_grid = QGridLayout(options)

        options_grid.addWidget(QLabel(S.INST_PRIVILEGES_LABEL), 0, 0)
        self.inst_privileges = QComboBox()
        self.inst_privileges.addItem(S.INST_PRIV_ADMIN, "admin")
        self.inst_privileges.addItem(S.INST_PRIV_LOWEST, "lowest")
        options_grid.addWidget(self.inst_privileges, 0, 1)

        options_grid.addWidget(QLabel(S.INST_ARCH_LABEL), 1, 0)
        self.inst_arch = QComboBox()
        self.inst_arch.addItem(S.INST_ARCH_X64, "x64")
        self.inst_arch.addItem(S.INST_ARCH_X86, "x86")
        self.inst_arch.addItem(S.INST_ARCH_ANY, "any")
        options_grid.addWidget(self.inst_arch, 1, 1)

        options_grid.addWidget(QLabel(S.INST_COMPRESSION_LABEL), 2, 0)
        self.inst_compression = QComboBox()
        self.inst_compression.addItems(list(COMPRESSION_CHOICES))
        options_grid.addWidget(self.inst_compression, 2, 1)

        options_grid.addWidget(QLabel(S.INST_LANGUAGES_LABEL), 3, 0)
        lang_box = QWidget()
        lang_layout = QGridLayout(lang_box)
        lang_layout.setContentsMargins(0, 0, 0, 0)
        self.inst_languages = {}
        codes = ["ar"] + list(LANGUAGE_LABELS)
        for i, code in enumerate(codes):
            label = "العربية" if code == "ar" else LANGUAGE_LABELS[code]
            checkbox = QCheckBox(label)
            if code == "en":
                checkbox.setChecked(True)
            self.inst_languages[code] = checkbox
            lang_layout.addWidget(checkbox, i // 4, i % 4)
        options_grid.addWidget(lang_box, 3, 1, 1, 2)

        options_grid.addWidget(QLabel(S.INST_ARABIC_ISL_LABEL), 4, 0)
        self.inst_arabic_isl = QLineEdit()
        self.inst_arabic_isl.setPlaceholderText(S.INST_ARABIC_ISL_PLACEHOLDER)
        self.inst_arabic_isl.setToolTip(S.INST_ARABIC_ISL_TIP)
        isl_btn = _browse_button(S.INST_ARABIC_ISL_LABEL, self.browse_arabic_isl)
        options_grid.addWidget(self.inst_arabic_isl, 4, 1)
        options_grid.addWidget(isl_btn, 4, 2)

        options_grid.addWidget(QLabel(S.INST_ASSOC_LABEL), 5, 0)
        self.inst_assoc = QLineEdit()
        self.inst_assoc.setPlaceholderText(S.INST_ASSOC_PLACEHOLDER)
        options_grid.addWidget(self.inst_assoc, 5, 1)

        self.inst_desktop_icon = QCheckBox(S.INST_DESKTOP_ICON)
        self.inst_desktop_icon.setChecked(True)
        self.inst_launch_after = QCheckBox(S.INST_LAUNCH_AFTER)
        self.inst_launch_after.setChecked(True)
        self.inst_allow_dir_change = QCheckBox(S.INST_ALLOW_DIR_CHANGE)
        self.inst_allow_dir_change.setChecked(True)
        self.inst_uninstall_icon = QCheckBox(S.INST_UNINSTALL_ICON)
        self.inst_uninstall_icon.setChecked(True)
        self.inst_sign = QCheckBox(S.INST_SIGN_INSTALLER)
        self.inst_sign.setToolTip(S.INST_SIGN_TIP)
        for i, cb in enumerate(
            [
                self.inst_desktop_icon,
                self.inst_launch_after,
                self.inst_allow_dir_change,
                self.inst_uninstall_icon,
                self.inst_sign,
            ]
        ):
            options_grid.addWidget(cb, 6 + i, 0, 1, 3)
        layout.addWidget(options)

        # ── Toolchain ──
        toolchain = QGroupBox(S.GROUP_INSTALLER_TOOLCHAIN)
        toolchain_layout = QGridLayout(toolchain)
        toolchain_layout.addWidget(QLabel(S.INST_ISCC_LABEL), 0, 0)
        self.inst_iscc_path = QLineEdit()
        self.inst_iscc_path.setPlaceholderText(S.INST_ISCC_PLACEHOLDER)
        toolchain_layout.addWidget(self.inst_iscc_path, 0, 1)
        iscc_btn = _browse_button(S.INST_ISCC_LABEL, self.browse_iscc_path)
        toolchain_layout.addWidget(iscc_btn, 0, 2)

        detect_btn = QPushButton(S.BTN_DETECT_ISCC)
        detect_btn.clicked.connect(self.detect_iscc)
        toolchain_layout.addWidget(detect_btn, 1, 0)

        gen_btn = QPushButton(S.BTN_GENERATE_ISS)
        gen_btn.clicked.connect(self.generate_iss_only)
        toolchain_layout.addWidget(gen_btn, 1, 1)

        build_btn = QPushButton(S.BTN_BUILD_INSTALLER)
        build_btn.setObjectName("successBtn")
        build_btn.clicked.connect(self.build_installer_now)
        toolchain_layout.addWidget(build_btn, 1, 2)
        layout.addWidget(toolchain)

        layout.addStretch()

        # The tab is field-dense; keep it usable on short screens.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        return scroll

    def _create_history_tab(self):
        """List of recent builds with restore + clear actions."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        group = QGroupBox(S.GROUP_HISTORY)
        group_layout = QVBoxLayout(group)

        self.history_list = QListWidget()
        self.history_list.setMinimumHeight(220)
        group_layout.addWidget(self.history_list)

        btn_row = QHBoxLayout()
        restore_btn = QPushButton(S.BTN_RESTORE_BUILD)
        restore_btn.clicked.connect(self.restore_from_history)
        clear_btn = QPushButton(S.BTN_CLEAR_HISTORY)
        clear_btn.setObjectName("dangerBtn")
        clear_btn.clicked.connect(self.clear_history)
        btn_row.addWidget(restore_btn)
        btn_row.addWidget(clear_btn)
        group_layout.addLayout(btn_row)

        layout.addWidget(group)
        return tab

    def _create_about_tab(self):
        """About page built from themed widgets.

        The previous version was one HTML blob with dark-theme colours and
        ``direction: rtl`` baked in, so the whole tab became unreadable in the
        light theme and stayed mirrored in English. Styling now lives in the
        stylesheet (``#aboutHeading`` and friends) and direction is inherited.
        """
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

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        return scroll

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

    def browse_upx_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, S.UPX_DIR_LABEL, "")
        if dir_path:
            self.upx_dir.setText(dir_path)

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
        template_key = self.templates_combo.currentData()
        if template_key and template_key in TEMPLATES:
            template = TEMPLATES[template_key]
            imports_str = (
                ", ".join(template["hidden_imports"])
                if template["hidden_imports"]
                else S.NONE
            )
            desc = S.TEMPLATE_DESC_FMT.format(
                name=template_name(template_key),
                desc=template_description(template_key),
                windowed=S.YES if template["windowed"] else S.NO,
                onefile=S.YES if template["onefile"] else S.NO,
                imports=imports_str,
            )
            self.template_desc.setHtml(desc)

    def apply_selected_template(self):
        template_key = self.templates_combo.currentData()
        if template_key and template_key in TEMPLATES:
            template = TEMPLATES[template_key]
            self.windowed_check.setChecked(template["windowed"])
            self.onefile_check.setChecked(template["onefile"])
            existing = [
                self.hidden_imports_list.item(i).text()
                for i in range(self.hidden_imports_list.count())
            ]
            for imp in template["hidden_imports"]:
                if imp not in existing:
                    self.hidden_imports_list.addItem(imp)
            name = template_name(template_key)
            self._append_log(S.LOG_TEMPLATE_APPLIED.format(name=name))
            QMessageBox.information(
                self, S.MSG_SUCCESS, S.MSG_TEMPLATE_OK_FMT.format(name=name)
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
            upx_dir=self.upx_dir.text().strip(),
            extra_args=self.extra_args.text(),
            splash_image=self.splash_input.text().strip(),
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
        self.upx_dir.setText(config.upx_dir)
        self.extra_args.setText(config.extra_args)
        if hasattr(self, "splash_input"):
            self.splash_input.setText(config.splash_image)

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
            if not isinstance(data, dict):
                raise ValueError("settings file must contain a JSON object")
            config = BuildConfig.from_dict(data)
        except (OSError, ValueError, TypeError) as e:
            QMessageBox.critical(self, S.MSG_ERROR, S.ERR_LOAD_FAIL.format(error=str(e)))
            return

        if not self._confirm_untrusted_config(config):
            self._append_log(S.LOG_SETTINGS_REJECTED.format(path=file_path))
            return

        self._apply_config(config)
        self._append_log(S.LOG_SETTINGS_LOADED.format(path=file_path))
        QMessageBox.information(self, S.MSG_SUCCESS, S.MSG_LOADED_OK)

    def _confirm_untrusted_config(self, config: BuildConfig) -> bool:
        """Ask before applying a config that would make PyInstaller run code.

        A settings file is shareable, and flags like ``--runtime-hook`` inject
        code into every EXE the build produces. The user needs to see that
        before it silently becomes part of a signed binary.
        """
        flags = find_dangerous_args(config.extra_args)
        if not flags:
            return True
        reply = QMessageBox.question(
            self,
            S.MSG_CONFIRM,
            S.MSG_DANGEROUS_ARGS_CONFIRM.format(
                flags="\n".join(f"  • {f}" for f in flags),
                args=config.extra_args,
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return reply == QMessageBox.Yes

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                self.settings = data if isinstance(data, dict) else {}
            except (OSError, ValueError):
                self.settings = {}

    def save_settings(self) -> bool:
        """Persist preferences. Reports failure instead of swallowing it."""
        try:
            directory = os.path.dirname(SETTINGS_FILE)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except (OSError, TypeError) as e:
            self._append_log(S.LOG_SETTINGS_SAVE_FAIL.format(error=str(e)))
            return False
        return True

    def _ensure_pyinstaller(self) -> bool:
        """Check for PyInstaller, offering to install it with explicit consent.

        The previous version ran ``pip install pyinstaller`` silently on the
        first build: an unattended network install, unpinned, from whatever
        index the environment happened to point at.
        """
        try:
            subprocess.run(
                [sys.executable, "-m", "PyInstaller", "--version"],
                capture_output=True,
                check=True,
            )
            return True
        except (OSError, subprocess.CalledProcessError):
            pass

        install_cmd = [sys.executable, "-m", "pip", "install", PYINSTALLER_REQUIREMENT]
        reply = QMessageBox.question(
            self,
            S.MSG_CONFIRM,
            S.MSG_INSTALL_PYINSTALLER_CONFIRM.format(cmd=" ".join(install_cmd)),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            self._append_log(S.LOG_INSTALL_PYINSTALLER_DECLINED)
            return False

        self._append_log(S.LOG_INSTALL_PYINSTALLER)
        self._append_log(" ".join(install_cmd))
        try:
            subprocess.run(install_cmd, capture_output=True, check=True, timeout=600)
        except (OSError, subprocess.SubprocessError) as e:
            QMessageBox.critical(
                self, S.MSG_ERROR, S.ERR_INSTALL_PYINSTALLER_FAIL.format(error=str(e))
            )
            return False
        self._append_log(S.LOG_INSTALL_PYINSTALLER_OK)
        return True

    def start_conversion(self):
        config = self._current_config()
        version_path = self._materialize_version_file()
        if version_path:
            config.version_file = version_path
        manifest_path = self._materialize_manifest_file()
        if manifest_path:
            config.manifest_file = manifest_path

        # Every early return below must clean up the temp files created above;
        # one path used to skip that and leak into %TEMP%.
        cmd, error = build_pyinstaller_command(config)
        if error:
            self._cleanup_temp_files()
            QMessageBox.warning(self, S.MSG_WARNING, error)
            return

        if not self._ensure_pyinstaller():
            self._cleanup_temp_files()
            return

        self._build_start_time = time.monotonic()
        self._build_config_snapshot = config.to_dict()

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
        duration = max(0.0, time.monotonic() - self._build_start_time)
        snapshot = self._build_config_snapshot
        if snapshot:
            record = make_record(
                source=snapshot.get("source", ""),
                output_name=snapshot.get("output_name", ""),
                success=success,
                duration_seconds=round(duration, 2),
                config=snapshot,
            )
            self.history.add(record)
            self._refresh_history_list()
        # Run post-build actions only on a successful build.
        if success and snapshot:
            try:
                self._run_post_build_actions(BuildConfig.from_dict(snapshot))
            except Exception as e:
                self._append_log(S.LOG_SIGNING_FAIL.format(error=str(e)))
        self._build_config_snapshot = {}
        self._cleanup_temp_files()
        if success:
            self.progress_bar.setFormat(S.PROGRESS_DONE)
            QMessageBox.information(self, S.MSG_SUCCESS, message)
        else:
            self.progress_bar.setFormat(S.PROGRESS_FAILED)
            if message != S.CONV_CANCELLED:
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
        self.log_output.append(format_html(text, theme=self.current_theme))

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
        self.setStyleSheet(themed_stylesheet(self.current_theme, current_locale()))
        self.settings["theme"] = self.current_theme

    def _on_language_changed(self, index):
        """Persist the language preference and prompt for a restart."""
        code = self.language_combo.itemData(index)
        if not code or code == self.settings.get("locale", current_locale()):
            return
        self.settings["locale"] = code
        self.save_settings()
        QMessageBox.information(self, S.MSG_SUCCESS, S.MSG_RESTART_REQUIRED)

    # ─── Phase 4: requirements / version info / history ────────────────

    def import_requirements_file(self):
        """Read a requirements.txt and merge into hidden imports."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, S.DIALOG_CHOOSE_REQS, "", S.DIALOG_FILTER_REQS
        )
        if not file_path:
            return
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            self._append_log(S.LOG_REQS_ERROR.format(error=str(e)))
            return

        packages = parse_requirements(content)
        existing = [
            self.hidden_imports_list.item(i).text()
            for i in range(self.hidden_imports_list.count())
        ]
        new_pkgs = filter_non_stdlib(packages, existing=existing)
        for pkg in sorted(new_pkgs):
            self.hidden_imports_list.addItem(pkg)
        self._append_log(
            S.LOG_REQS_IMPORTED.format(total=len(packages), added=len(new_pkgs))
        )
        if new_pkgs:
            self._append_log(S.LOG_REQS_HINT)

    def _current_version_info(self) -> VersionInfo:
        """Read the version-info form into a VersionInfo dataclass."""
        return VersionInfo(
            company_name=self.vi_company_name.text().strip(),
            file_description=self.vi_file_description.text().strip(),
            file_version=self.vi_file_version.text().strip(),
            internal_name=self.vi_internal_name.text().strip(),
            legal_copyright=self.vi_legal_copyright.text().strip(),
            original_filename=self.vi_original_filename.text().strip(),
            product_name=self.vi_product_name.text().strip(),
            product_version=self.vi_product_version.text().strip(),
        )

    def _cleanup_temp_files(self):
        """Remove every temp file created for the current build."""
        self._cleanup_temp_version_file()
        self._cleanup_temp_manifest_file()

    def _materialize_version_file(self) -> str:
        """If the version-info form has data, write a temp version.txt and return its path."""
        # Drop any file from a previous attempt first — overwriting the
        # attribute used to orphan it in %TEMP%.
        self._cleanup_temp_version_file()
        info = self._current_version_info()
        if info.is_empty():
            return ""
        content = generate_version_file(info)
        fd, path = tempfile.mkstemp(prefix="py2exe_version_", suffix=".txt", text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            return ""
        self._temp_version_file = path
        return path

    def _cleanup_temp_version_file(self):
        if self._temp_version_file and os.path.exists(self._temp_version_file):
            try:
                os.unlink(self._temp_version_file)
            except OSError:
                pass
        self._temp_version_file = ""

    # ─── History ────────────────────────────────────────────────────────

    def _refresh_history_list(self):
        """Repopulate the history list widget from BuildHistory."""
        if not hasattr(self, "history_list"):
            return
        self.history_list.clear()
        if len(self.history) == 0:
            self.history_list.addItem(S.HISTORY_EMPTY)
            return
        for record in self.history.records:
            self.history_list.addItem(record.short_label())

    def restore_from_history(self):
        """Load the selected history record's config back into the form."""
        row = self.history_list.currentRow()
        if row < 0:
            return
        record = self.history.get(row)
        if record is None:
            return
        self._apply_config(BuildConfig.from_dict(record.config))
        try:
            label_time = record.short_label().split("@", 1)[1].strip()
        except IndexError:
            label_time = record.timestamp
        self._append_log(S.LOG_RESTORED.format(time=label_time))

    def clear_history(self):
        """Wipe the build log — after confirming, since there is no undo."""
        if len(self.history) == 0:
            return
        reply = QMessageBox.question(
            self,
            S.MSG_CONFIRM,
            S.MSG_CLEAR_HISTORY_CONFIRM.format(count=len(self.history)),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        if not self.history.clear():
            self._append_log(S.LOG_HISTORY_SAVE_FAIL.format(error=self.history.last_error))
        self._refresh_history_list()
        self._append_log(S.HISTORY_CLEARED)

    # ─── Phase 5: deployment (splash / manifest / signing / smoke) ────

    def browse_splash_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, S.DIALOG_CHOOSE_SPLASH, "", S.DIALOG_FILTER_IMAGE
        )
        if file_path:
            self.splash_input.setText(file_path)

    def browse_signing_cert(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, S.DIALOG_CHOOSE_CERT, "", S.DIALOG_FILTER_CERT
        )
        if file_path:
            self.signing_cert.setText(file_path)

    def _selected_supported_os(self):
        return [code for code, cb in self.manifest_os.items() if cb.isChecked()]

    def _materialize_manifest_file(self) -> str:
        """If manifest generation is on, write a temp manifest.xml and return its path."""
        self._cleanup_temp_manifest_file()
        if not self.manifest_enable.isChecked():
            return ""
        config = ManifestConfig(
            name=self.output_name.text() or "MyApp",
            version=self.vi_product_version.text() or self.vi_file_version.text() or "1.0.0.0",
            description=self.vi_file_description.text(),
            dpi_aware=self.manifest_dpi.isChecked(),
            require_admin=self.manifest_admin.isChecked(),
            supported_os=self._selected_supported_os(),
        )
        xml = generate_manifest(config)
        fd, path = tempfile.mkstemp(prefix="py2exe_manifest_", suffix=".xml", text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(xml)
        except Exception:
            return ""
        self._temp_manifest_file = path
        return path

    def _cleanup_temp_manifest_file(self):
        if getattr(self, "_temp_manifest_file", "") and os.path.exists(
            self._temp_manifest_file
        ):
            try:
                os.unlink(self._temp_manifest_file)
            except OSError:
                pass
        self._temp_manifest_file = ""

    def _on_signing_mode_changed(self, use_store: bool):
        """Show only the fields relevant to the selected signing mode."""
        self.signing_subject.setEnabled(use_store)
        self.signing_subject_label.setEnabled(use_store)
        self.signing_cert.setEnabled(not use_store)
        self.signing_password.setEnabled(not use_store)

    def _current_signing_config(self) -> SigningConfig:
        return SigningConfig(
            enabled=self.signing_enable.isChecked(),
            use_cert_store=self.signing_use_store.isChecked(),
            cert_subject=self.signing_subject.text().strip(),
            cert_path=self.signing_cert.text().strip(),
            cert_password=self.signing_password.text(),
            timestamp_url=self.signing_timestamp.text().strip()
            or "http://timestamp.digicert.com",
            description=self.signing_description.text().strip(),
        )

    def _run_post_build_actions(self, config: BuildConfig):
        """Run signing and/or smoke test on the produced EXE."""
        exe_path = locate_built_executable(
            config.output_dir or os.path.dirname(config.source),
            config.output_name or os.path.splitext(os.path.basename(config.source))[0],
            config.onefile,
        )
        if not exe_path:
            self._last_built_exe = ""
            if (
                self.signing_enable.isChecked()
                or self.smoke_enable.isChecked()
                or self.installer_enable.isChecked()
            ):
                self._append_log(S.LOG_SMOKE_NOT_FOUND)
            return
        self._last_built_exe = exe_path

        sign_cfg = self._current_signing_config()
        smoke_enabled = self.smoke_enable.isChecked()

        if not sign_cfg.enabled and not smoke_enabled:
            self._start_installer_step(config)
            return

        # Signing waits on a timestamp server and the smoke test waits on the
        # new EXE: both used to run inline and froze the window for minutes.
        self.post_build_thread = PostBuildThread(
            exe_path,
            signing_config=sign_cfg,
            smoke_enabled=smoke_enabled,
            smoke_timeout=float(self.smoke_timeout.value()),
        )
        self.post_build_thread.log_signal.connect(self._append_log)
        self.post_build_thread.finished_signal.connect(
            lambda *_: self._start_installer_step(config)
        )
        self.post_build_thread.start()

    def _start_installer_step(self, config: BuildConfig):
        """Chain the installer build after signing/smoke-testing has finished."""
        inst_cfg = self._current_installer_config()
        if inst_cfg.enabled:
            self._run_installer(inst_cfg, config)

    # ─── Phase 7: Inno Setup installer ──────────────────────────────────

    def browse_installer_out_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, S.DIALOG_CHOOSE_OUT_DIR, "")
        if dir_path:
            self.inst_out_dir.setText(dir_path)

    def browse_installer_license(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, S.DIALOG_CHOOSE_LICENSE, "", S.DIALOG_FILTER_TEXT
        )
        if file_path:
            self.inst_license.setText(file_path)

    def browse_installer_readme(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, S.DIALOG_CHOOSE_LICENSE, "", S.DIALOG_FILTER_TEXT
        )
        if file_path:
            self.inst_readme.setText(file_path)

    def browse_installer_icon(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, S.DIALOG_CHOOSE_ICON, "", S.DIALOG_FILTER_ICON
        )
        if file_path:
            self.inst_setup_icon.setText(file_path)

    def browse_arabic_isl(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, S.DIALOG_CHOOSE_ISL, "", S.DIALOG_FILTER_ISL
        )
        if file_path:
            self.inst_arabic_isl.setText(file_path)

    def browse_iscc_path(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, S.DIALOG_CHOOSE_ISCC, "", S.DIALOG_FILTER_EXE
        )
        if file_path:
            self.inst_iscc_path.setText(file_path)

    def detect_iscc(self):
        """Locate ISCC.exe and report the result in the log."""
        path = self.inst_iscc_path.text().strip() or find_iscc()
        if path:
            self.inst_iscc_path.setText(path)
            self._append_log(S.LOG_ISCC_FOUND.format(path=path))
        else:
            self._append_log(S.LOG_ISCC_MISSING)

    def _current_installer_config(self) -> InstallerConfig:
        """Read the installer tab into an InstallerConfig dataclass."""
        languages = [code for code, cb in self.inst_languages.items() if cb.isChecked()]
        return InstallerConfig(
            enabled=self.installer_enable.isChecked(),
            app_name=self.inst_app_name.text().strip()
            or self.output_name.text().strip(),
            app_version=self.inst_version.text().strip()
            or self.vi_product_version.text().strip()
            or "1.0.0",
            publisher=self.inst_publisher.text().strip()
            or self.vi_company_name.text().strip(),
            publisher_url=self.inst_url.text().strip(),
            app_id=self.inst_app_id.text().strip(),
            output_dir=self.inst_out_dir.text().strip(),
            output_base_filename=self.inst_out_name.text().strip(),
            license_file=self.inst_license.text().strip(),
            readme_file=self.inst_readme.text().strip(),
            setup_icon_file=self.inst_setup_icon.text().strip()
            or self.icon_input.text().strip(),
            languages=languages or ["en"],
            arabic_isl_path=self.inst_arabic_isl.text().strip(),
            privileges=self.inst_privileges.currentData() or "admin",
            architecture=self.inst_arch.currentData() or "x64",
            compression=self.inst_compression.currentText(),
            desktop_icon=self.inst_desktop_icon.isChecked(),
            launch_after_install=self.inst_launch_after.isChecked(),
            allow_dir_change=self.inst_allow_dir_change.isChecked(),
            create_uninstall_icon=self.inst_uninstall_icon.isChecked(),
            associate_extension=self.inst_assoc.text().strip(),
            sign_installer=self.inst_sign.isChecked(),
        )

    def _installer_source(self, config: BuildConfig):
        """Return (app_path, onefile) describing what the installer should package.

        onefile → the produced .exe; onedir → the folder containing it.
        """
        exe_path = self._last_built_exe or locate_built_executable(
            config.output_dir or os.path.dirname(config.source),
            config.output_name or os.path.splitext(os.path.basename(config.source))[0],
            config.onefile,
        )
        if not exe_path:
            return "", config.onefile
        if config.onefile:
            return exe_path, True
        return os.path.dirname(exe_path), False

    def _write_iss_script(self, inst_cfg: InstallerConfig, build_cfg: BuildConfig):
        """Render the .iss script to disk. Returns (path, error)."""
        app_path, onefile = self._installer_source(build_cfg)
        if not app_path:
            return "", S.ERR_INSTALLER_NO_EXE

        error = validate_installer(inst_cfg, app_path)
        if error:
            return "", error

        _entries, warnings = resolve_languages(inst_cfg)
        if warnings:
            self._append_log(
                S.LOG_INSTALLER_LANG_WARN.format(langs=", ".join(warnings))
            )

        exe_name = "" if onefile else os.path.basename(self._last_built_exe or "")
        script = generate_iss_script(inst_cfg, app_path, onefile=onefile, exe_name=exe_name)

        target_dir = inst_cfg.output_dir or (
            app_path if not onefile else os.path.dirname(app_path)
        )
        iss_path = os.path.join(target_dir, f"{inst_cfg.app_name or 'setup'}.iss")
        try:
            os.makedirs(target_dir, exist_ok=True)
            with open(iss_path, "w", encoding="utf-8") as f:
                f.write(script)
        except OSError as e:
            return "", str(e)
        return iss_path, None

    def generate_iss_only(self):
        """Write the .iss script without invoking the compiler (dry run)."""
        inst_cfg = self._current_installer_config()
        inst_cfg.enabled = True  # explicit button press overrides the checkbox
        if not inst_cfg.app_name:
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_INSTALLER_NO_NAME)
            return
        iss_path, error = self._write_iss_script(inst_cfg, self._current_config())
        if error:
            self._append_log(S.LOG_ISS_FAIL.format(error=error))
            QMessageBox.warning(self, S.MSG_WARNING, error)
            return
        self._append_log(S.LOG_ISS_WRITTEN.format(path=iss_path))
        QMessageBox.information(self, S.MSG_SUCCESS, iss_path)

    def build_installer_now(self):
        """Generate the script and run ISCC on it (manual trigger)."""
        inst_cfg = self._current_installer_config()
        inst_cfg.enabled = True
        if not inst_cfg.app_name:
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_INSTALLER_NO_NAME)
            return
        self._run_installer(inst_cfg, self._current_config(), interactive=True)

    def _run_installer(self, inst_cfg: InstallerConfig, build_cfg: BuildConfig,
                       interactive: bool = False):
        """Compile the installer in a background thread."""
        if self.installer_thread and self.installer_thread.isRunning():
            return

        iss_path, error = self._write_iss_script(inst_cfg, build_cfg)
        if error:
            self._append_log(S.LOG_INSTALLER_SKIPPED.format(reason=error))
            if interactive:
                QMessageBox.warning(self, S.MSG_WARNING, error)
            return
        self._append_log(S.LOG_ISS_WRITTEN.format(path=iss_path))

        sign_command = None
        if inst_cfg.sign_installer:
            sign_cfg = self._current_signing_config()
            # The installer is signed by ISCC itself, so build the command
            # without a target file — ISCC substitutes it via $f.
            candidate, sign_error = build_signtool_command("$f", sign_cfg)
            if sign_error or candidate is None:
                self._append_log(S.LOG_SIGNING_SKIPPED.format(reason=sign_error or "unknown"))
            else:
                sign_command = candidate[:-1]  # drop the "$f" placeholder token

        cmd, error = build_iscc_command(
            iss_path,
            iscc_path=self.inst_iscc_path.text().strip() or None,
            sign_command=sign_command,
        )
        if error or cmd is None:
            self._append_log(S.LOG_INSTALLER_SKIPPED.format(reason=error or "unknown"))
            if interactive:
                QMessageBox.warning(self, S.MSG_WARNING, error or "")
            return

        app_path, onefile = self._installer_source(build_cfg)
        fallback_dir = app_path if not onefile else os.path.dirname(app_path)
        expected = installer_output_path(inst_cfg, fallback_dir)

        self._append_log(S.LOG_INSTALLER_START)
        self._append_log(" ".join(redact_password(cmd)))

        self.installer_thread = InstallerThread(
            cmd, os.path.dirname(iss_path), expected_output=expected
        )
        self.installer_thread.log_signal.connect(self._append_log)
        self.installer_thread.finished_signal.connect(
            lambda ok, msg: self._on_installer_finished(ok, msg, interactive)
        )
        self.installer_thread.start()

    def _on_installer_finished(self, success: bool, message: str, interactive: bool):
        if success:
            self._append_log(S.LOG_INSTALLER_OK.format(path=message))
            if interactive:
                QMessageBox.information(
                    self, S.MSG_SUCCESS, S.MSG_INSTALLER_OK.format(path=message)
                )
        else:
            self._append_log(S.LOG_INSTALLER_FAIL.format(error=message))
            if interactive:
                QMessageBox.critical(
                    self, S.MSG_ERROR, S.LOG_INSTALLER_FAIL.format(error=message)
                )

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
