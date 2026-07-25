"""Main application window.

This module owns orchestration only: the build pipeline, the worker threads,
shortcuts, and the actions that span more than one tab. The tabs themselves
live in ``py2exe_gui.ui.tabs`` and own their own widgets — before that split
this file was ~1,900 lines and held every control in the application.
"""

import json
import os
import subprocess
import sys
import tempfile
import time

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QKeySequence
from PyQt5.QtWidgets import (
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QShortcut,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from py2exe_gui.constants import (
    APP_NAME,
    APP_VERSION,
    COPYRIGHT,
    DEVELOPER,
    HISTORY_FILE,
    PYINSTALLER_REQUIREMENT,
    SETTINGS_FILE,
)
from py2exe_gui.core import (
    BuildConfig,
    BuildHistory,
    InstallerConfig,
    ManifestConfig,
    build_iscc_command,
    build_pyinstaller_command,
    build_signtool_command,
    detect_imports,
    filter_non_stdlib,
    find_dangerous_args,
    find_iscc,
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
from py2exe_gui.core.installer import validate as validate_installer
from py2exe_gui.strings import (
    LOCALE_LAYOUT,
    S,
    current_locale,
    set_locale,
)
from py2exe_gui.styles import themed_stylesheet
from py2exe_gui.templates import TEMPLATES, template_name
from py2exe_gui.ui.conversion_thread import ConversionThread
from py2exe_gui.ui.dialogs import CommandPreviewDialog
from py2exe_gui.ui.installer_thread import InstallerThread
from py2exe_gui.ui.post_build_thread import PostBuildThread
from py2exe_gui.ui.tabs import (
    AboutTab,
    AdvancedTab,
    DeployTab,
    HistoryTab,
    InstallerTab,
    MainTab,
    TemplatesTab,
    VersionInfoTab,
)


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
        self._shortcuts = []
        self.history = BuildHistory(HISTORY_FILE)
        self.load_settings()
        self.current_theme = self.settings.get("theme", "dark")
        self.init_ui()
        self._register_shortcuts()
        self.setAcceptDrops(True)
        self.check_dependencies()
        self._refresh_history_list()

    # ─── Construction ───────────────────────────────────────────────────

    def init_ui(self):
        self.setWindowTitle(S.WINDOW_TITLE_FMT.format(name=APP_NAME, version=APP_VERSION))
        # A hard 800px minimum did not fit a 1366x768 laptop. Keep the
        # comfortable size as the *default*, not as a floor.
        self.setMinimumSize(900, 600)
        self.resize(1080, 800)
        self._apply_layout_direction()
        self.setStyleSheet(themed_stylesheet(self.current_theme, current_locale()))
        self.setCentralWidget(self._build_central_widget())
        self.statusBar().showMessage(f"{COPYRIGHT} | {DEVELOPER}")

    def _apply_layout_direction(self):
        self.setLayoutDirection(
            Qt.RightToLeft
            if LOCALE_LAYOUT.get(current_locale(), "rtl") == "rtl"
            else Qt.LeftToRight
        )

    def _build_central_widget(self) -> QWidget:
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(self._create_header())

        self.main_tab = MainTab(self)
        self.advanced_tab = AdvancedTab(self)
        self.version_info_tab = VersionInfoTab(self)
        self.deploy_tab = DeployTab(self)
        self.installer_tab = InstallerTab(self)
        self.templates_tab = TemplatesTab(self)
        self.history_tab = HistoryTab(self)
        self.about_tab = AboutTab(self)

        self.tabs = QTabWidget()
        for widget, title in (
            (self.main_tab, S.TAB_MAIN),
            (self.advanced_tab, S.TAB_ADVANCED),
            (self.version_info_tab, S.TAB_VERSION_INFO),
            (self.deploy_tab, S.TAB_DEPLOY),
            (self.installer_tab, S.TAB_INSTALLER),
            (self.templates_tab, S.TAB_TEMPLATES),
            (self.history_tab, S.TAB_HISTORY),
            (self.about_tab, S.TAB_ABOUT),
        ):
            self.tabs.addTab(widget, title)
        layout.addWidget(self.tabs)

        layout.addWidget(self._create_progress_group())
        layout.addLayout(self._create_action_buttons())
        return central

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

    def _create_progress_group(self):
        group = QGroupBox(S.PROGRESS_GROUP)
        group_layout = QVBoxLayout(group)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(S.PROGRESS_READY)
        group_layout.addWidget(self.progress_bar)
        return group

    def _create_action_buttons(self):
        row = QHBoxLayout()

        def action(text, handler, object_name="", primary=False):
            button = QPushButton(text)
            if object_name:
                button.setObjectName(object_name)
            button.setMinimumHeight(50)
            button.setAccessibleName(text)
            if primary:
                button.setFont(QFont("Segoe UI", 14, QFont.Bold))
            button.clicked.connect(handler)
            row.addWidget(button)
            return button

        self.convert_btn = action(
            S.BTN_CONVERT, self.start_conversion, "successBtn", primary=True
        )
        self.cancel_btn = action(S.BTN_CANCEL, self.cancel_conversion, "dangerBtn")
        self.cancel_btn.setEnabled(False)
        self.preview_btn = action(S.BTN_PREVIEW_CMD, self.preview_command)
        self.open_folder_btn = action(S.BTN_OPEN_FOLDER, self.open_output_folder)
        self.theme_btn = action(S.BTN_TOGGLE_THEME, self.toggle_theme)
        return row

    # ─── Startup checks ─────────────────────────────────────────────────

    def check_dependencies(self):
        self._append_log(S.LOG_CHECKING_DEPS)
        try:
            result = subprocess.run(
                [sys.executable, "--version"], capture_output=True, text=True
            )
            self._append_log(S.LOG_PYTHON_FOUND.format(version=result.stdout.strip()))
        except OSError:
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
        except OSError:
            self._append_log(S.LOG_PYINSTALLER_MISSING)

        self._append_log("─" * 50)
        self._append_log(S.LOG_READY)

    # ─── Dependency analysis ────────────────────────────────────────────

    def detect_imports_action(self):
        source = self.main_tab.source_input.text()
        if not source or not os.path.isfile(source):
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_NO_SOURCE)
            return

        self._append_log(S.LOG_DETECTING_IMPORTS)
        try:
            with open(source, encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            self._append_log(S.LOG_DETECT_ERROR.format(error=str(e)))
            return

        imports = detect_imports(content)
        candidates = filter_non_stdlib(
            imports, existing=self.advanced_tab.hidden_imports()
        )
        added = self.advanced_tab.merge_hidden_imports(candidates)
        self._append_log(S.LOG_DETECT_RESULT.format(total=len(imports), added=len(added)))

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
        except OSError as e:
            self._append_log(S.LOG_REQS_ERROR.format(error=str(e)))
            return

        packages = parse_requirements(content)
        candidates = filter_non_stdlib(
            packages, existing=self.advanced_tab.hidden_imports()
        )
        added = self.advanced_tab.merge_hidden_imports(candidates)
        self._append_log(S.LOG_REQS_IMPORTED.format(total=len(packages), added=len(added)))
        if added:
            self._append_log(S.LOG_REQS_HINT)

    # ─── Templates ──────────────────────────────────────────────────────

    def apply_selected_template(self):
        key = self.templates_tab.selected_template()
        if not key:
            return
        template = TEMPLATES[key]
        self.main_tab.windowed_check.setChecked(template["windowed"])
        self.main_tab.onefile_check.setChecked(template["onefile"])
        self.advanced_tab.merge_hidden_imports(template["hidden_imports"])
        name = template_name(key)
        self._append_log(S.LOG_TEMPLATE_APPLIED.format(name=name))
        QMessageBox.information(
            self, S.MSG_SUCCESS, S.MSG_TEMPLATE_OK_FMT.format(name=name)
        )

    # ─── Configuration ──────────────────────────────────────────────────

    def _current_config(self) -> BuildConfig:
        main, advanced, deploy = self.main_tab, self.advanced_tab, self.deploy_tab
        return BuildConfig(
            source=main.source_input.text(),
            output_name=main.output_name.text(),
            output_dir=main.output_dir.text(),
            icon=main.icon_input.text(),
            onefile=main.onefile_check.isChecked(),
            windowed=main.windowed_check.isChecked(),
            noconsole=main.noconsole_check.isChecked(),
            clean=main.clean_check.isChecked(),
            noconfirm=main.noconfirm_check.isChecked(),
            strip=main.strip_check.isChecked(),
            extra_files=advanced.extra_files(),
            hidden_imports=advanced.hidden_imports(),
            optimize=advanced.optimize_combo.currentIndex(),
            upx=advanced.upx_check.isChecked(),
            upx_dir=advanced.upx_dir.text().strip(),
            extra_args=advanced.extra_args.text(),
            splash_image=deploy.splash_input.text().strip(),
        )

    def _apply_config(self, config: BuildConfig):
        main, advanced, deploy = self.main_tab, self.advanced_tab, self.deploy_tab
        main.source_input.setText(config.source)
        main.output_name.setText(config.output_name)
        main.output_dir.setText(config.output_dir)
        main.icon_input.setText(config.icon)
        main.onefile_check.setChecked(config.onefile)
        main.windowed_check.setChecked(config.windowed)
        main.clean_check.setChecked(config.clean)
        main.noconsole_check.setChecked(config.noconsole)
        main.noconfirm_check.setChecked(config.noconfirm)
        main.strip_check.setChecked(config.strip)

        advanced.extra_files_list.clear()
        for path in config.extra_files:
            advanced.extra_files_list.addItem(path)
        advanced.hidden_imports_list.clear()
        for module in config.hidden_imports:
            advanced.hidden_imports_list.addItem(module)
        advanced.optimize_combo.setCurrentIndex(config.optimize)
        advanced.upx_check.setChecked(config.upx)
        advanced.upx_dir.setText(config.upx_dir)
        advanced.extra_args.setText(config.extra_args)

        deploy.splash_input.setText(config.splash_image)

    def save_current_settings(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, S.DIALOG_SAVE_SETTINGS, "py2exe_config.json", S.DIALOG_FILTER_JSON
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self._current_config().to_dict(), f, ensure_ascii=False, indent=2)
        except (OSError, TypeError) as e:
            QMessageBox.critical(self, S.MSG_ERROR, S.ERR_SAVE_FAIL.format(error=str(e)))
            return
        self._append_log(S.LOG_SETTINGS_SAVED.format(path=file_path))
        QMessageBox.information(self, S.MSG_SUCCESS, S.MSG_SAVED_OK)

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

    # ─── Preferences ────────────────────────────────────────────────────

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

    # ─── Build pipeline ─────────────────────────────────────────────────

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

        work_dir = self.main_tab.output_dir.text() or os.path.dirname(
            self.main_tab.source_input.text()
        )

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
            if not self.history.add(record):
                self._append_log(
                    S.LOG_HISTORY_SAVE_FAIL.format(error=self.history.last_error)
                )
            self._refresh_history_list()

        # Post-build actions only make sense for a successful build.
        if success and snapshot:
            try:
                self._run_post_build_actions(BuildConfig.from_dict(snapshot))
            except (OSError, ValueError) as e:
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

    def preview_command(self):
        """Show the PyInstaller command that would be executed."""
        cmd, error = build_pyinstaller_command(self._current_config())
        if error:
            QMessageBox.warning(self, S.MSG_WARNING, error)
            return
        CommandPreviewDialog(cmd, parent=self).exec_()

    def open_output_folder(self):
        output_dir = self.main_tab.output_dir.text() or os.path.dirname(
            self.main_tab.source_input.text()
        )
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

    # ─── Log / theme / locale ───────────────────────────────────────────

    def _append_log(self, line: str):
        """Append a single line to the log, coloured for the active theme."""
        self.main_tab.append_log(line, theme=self.current_theme)

    def export_log(self):
        self.main_tab.export_log()

    def toggle_theme(self):
        """Swap between dark and light themes and persist the choice."""
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.setStyleSheet(themed_stylesheet(self.current_theme, current_locale()))
        self.settings["theme"] = self.current_theme

    def _on_language_changed(self, index):
        """Switch locale and rebuild the UI in place."""
        code = self.templates_tab.language_combo.itemData(index)
        if not code or code == current_locale():
            return
        self.settings["locale"] = code
        self.save_settings()
        self.retranslate(code)

    def retranslate(self, locale_code: str):
        """Apply a new locale without restarting.

        The UI is built imperatively, so rather than teaching every widget to
        re-read its label we snapshot the state, rebuild the central widget
        under the new locale, then restore. This previously required a restart.
        """
        config = self._current_config()
        version_info = self.version_info_tab.version_info()
        log_html = self.main_tab.log_output.toHtml()

        set_locale(locale_code)
        self._apply_layout_direction()
        self.setStyleSheet(themed_stylesheet(self.current_theme, locale_code))
        self.setWindowTitle(S.WINDOW_TITLE_FMT.format(name=APP_NAME, version=APP_VERSION))
        self.setCentralWidget(self._build_central_widget())
        self.statusBar().showMessage(f"{COPYRIGHT} | {DEVELOPER}")

        self._apply_config(config)
        vi = self.version_info_tab
        vi.vi_company_name.setText(version_info.company_name)
        vi.vi_file_description.setText(version_info.file_description)
        vi.vi_file_version.setText(version_info.file_version)
        vi.vi_internal_name.setText(version_info.internal_name)
        vi.vi_legal_copyright.setText(version_info.legal_copyright)
        vi.vi_original_filename.setText(version_info.original_filename)
        vi.vi_product_name.setText(version_info.product_name)
        vi.vi_product_version.setText(version_info.product_version)

        self.main_tab.log_output.setHtml(log_html)
        self._refresh_history_list()
        self._register_shortcuts()

    # ─── Version info / manifest temp files ─────────────────────────────

    def _cleanup_temp_files(self):
        """Remove every temp file created for the current build."""
        self._cleanup_temp_version_file()
        self._cleanup_temp_manifest_file()

    def _materialize_version_file(self) -> str:
        """Write a temp version.txt when the form has data; return its path."""
        # Drop any file from a previous attempt first — overwriting the
        # attribute used to orphan it in %TEMP%.
        self._cleanup_temp_version_file()
        info = self.version_info_tab.version_info()
        if info.is_empty():
            return ""
        content = generate_version_file(info)
        fd, path = tempfile.mkstemp(prefix="py2exe_version_", suffix=".txt", text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError:
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

    def _materialize_manifest_file(self) -> str:
        """Write a temp manifest.xml when generation is on; return its path."""
        self._cleanup_temp_manifest_file()
        deploy, vi = self.deploy_tab, self.version_info_tab
        if not deploy.manifest_enable.isChecked():
            return ""
        config = ManifestConfig(
            name=self.main_tab.output_name.text() or "MyApp",
            version=vi.vi_product_version.text() or vi.vi_file_version.text() or "1.0.0.0",
            description=vi.vi_file_description.text(),
            dpi_aware=deploy.manifest_dpi.isChecked(),
            require_admin=deploy.manifest_admin.isChecked(),
            supported_os=deploy.selected_supported_os(),
        )
        xml = generate_manifest(config)
        fd, path = tempfile.mkstemp(prefix="py2exe_manifest_", suffix=".xml", text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(xml)
        except OSError:
            return ""
        self._temp_manifest_file = path
        return path

    def _cleanup_temp_manifest_file(self):
        if self._temp_manifest_file and os.path.exists(self._temp_manifest_file):
            try:
                os.unlink(self._temp_manifest_file)
            except OSError:
                pass
        self._temp_manifest_file = ""

    # ─── History ────────────────────────────────────────────────────────

    def _refresh_history_list(self):
        if not hasattr(self, "history_tab"):
            return
        self.history_tab.refresh(self.history)

    def restore_from_history(self):
        """Load the selected history record's config back into the form."""
        row = self.history_tab.selected_row()
        if row < 0:
            return
        record = self.history.get(row)
        if record is None:
            return
        config = BuildConfig.from_dict(record.config)
        if not self._confirm_untrusted_config(config):
            return
        self._apply_config(config)
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

    # ─── Post-build: signing, smoke test, installer ─────────────────────

    def _run_post_build_actions(self, config: BuildConfig):
        """Sign and/or smoke-test the produced EXE, then build the installer."""
        exe_path = locate_built_executable(
            config.output_dir or os.path.dirname(config.source),
            config.output_name or os.path.splitext(os.path.basename(config.source))[0],
            config.onefile,
        )
        if not exe_path:
            self._last_built_exe = ""
            if (
                self.deploy_tab.signing_enable.isChecked()
                or self.deploy_tab.smoke_enable.isChecked()
                or self.installer_tab.installer_enable.isChecked()
            ):
                self._append_log(S.LOG_SMOKE_NOT_FOUND)
            return
        self._last_built_exe = exe_path

        sign_cfg = self.deploy_tab.signing_config()
        smoke_enabled = self.deploy_tab.smoke_enable.isChecked()

        if not sign_cfg.enabled and not smoke_enabled:
            self._start_installer_step(config)
            return

        # Signing waits on a timestamp server and the smoke test waits on the
        # new EXE: both used to run inline and froze the window for minutes.
        self.post_build_thread = PostBuildThread(
            exe_path,
            signing_config=sign_cfg,
            smoke_enabled=smoke_enabled,
            smoke_timeout=float(self.deploy_tab.smoke_timeout.value()),
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

    # ─── Installer ──────────────────────────────────────────────────────

    def detect_iscc(self):
        """Locate ISCC.exe and report the result in the log."""
        path = self.installer_tab.inst_iscc_path.text().strip() or find_iscc()
        if path:
            self.installer_tab.inst_iscc_path.setText(path)
            self._append_log(S.LOG_ISCC_FOUND.format(path=path))
        else:
            self._append_log(S.LOG_ISCC_MISSING)

    def _current_installer_config(self) -> InstallerConfig:
        vi = self.version_info_tab
        return self.installer_tab.installer_config(
            fallback_name=self.main_tab.output_name.text().strip(),
            fallback_version=vi.vi_product_version.text().strip(),
            fallback_publisher=vi.vi_company_name.text().strip(),
            fallback_icon=self.main_tab.icon_input.text().strip(),
        )

    def _installer_source(self, config: BuildConfig):
        """Return (app_path, onefile) describing what the installer packages.

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
            self._append_log(S.LOG_INSTALLER_LANG_WARN.format(langs=", ".join(warnings)))

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
        inst_cfg.enabled = True  # an explicit button press overrides the checkbox
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

    def _run_installer(
        self, inst_cfg: InstallerConfig, build_cfg: BuildConfig, interactive: bool = False
    ):
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
            sign_cfg = self.deploy_tab.signing_config()
            # The installer is signed by ISCC itself, so build the command
            # against a placeholder that ISCC substitutes via $f.
            candidate, sign_error = build_signtool_command("$f", sign_cfg)
            if sign_error or candidate is None:
                self._append_log(
                    S.LOG_SIGNING_SKIPPED.format(reason=sign_error or "unknown")
                )
            else:
                sign_command = candidate[:-1]  # drop the "$f" placeholder token

        cmd, error = build_iscc_command(
            iss_path,
            iscc_path=self.installer_tab.inst_iscc_path.text().strip() or None,
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

    # ─── Shortcuts ──────────────────────────────────────────────────────

    def _register_shortcuts(self):
        """Bind keyboard shortcuts to common actions."""
        # Rebuilding the UI recreates the target widgets, so drop the previous
        # shortcuts rather than stacking duplicates on top of them.
        for shortcut in self._shortcuts:
            shortcut.setParent(None)
        self._shortcuts = []

        bindings = [
            ("Ctrl+O", self.main_tab.browse_source),
            ("Ctrl+B", self.start_conversion),
            ("Ctrl+Shift+B", self.cancel_conversion),
            ("Ctrl+P", self.preview_command),
            ("Ctrl+L", self.main_tab.log_output.clear),
            ("Ctrl+E", self.main_tab.export_log),
            ("Ctrl+S", self.save_current_settings),
            ("Ctrl+T", self.toggle_theme),
            ("F5", self.detect_imports_action),
            ("Ctrl+F", self.main_tab.log_search.setFocus),
        ]
        for sequence, slot in bindings:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(slot)
            self._shortcuts.append(shortcut)

    # ─── Drag & drop ────────────────────────────────────────────────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return
        for url in urls:
            path = url.toLocalFile()
            if path:
                self._handle_dropped_path(path)
        event.acceptProposedAction()

    def _handle_dropped_path(self, path: str):
        """Route a dropped path to the appropriate field based on its kind."""
        if os.path.isdir(path):
            self.advanced_tab.extra_files_list.addItem(path)
            self._append_log(S.LOG_DROPPED_EXTRA.format(path=path))
            return

        ext = os.path.splitext(path)[1].lower()
        if ext in (".py", ".pyw"):
            self.main_tab.source_input.setText(path)
            self._append_log(S.LOG_DROPPED_SOURCE.format(path=path))
        elif ext == ".ico":
            self.main_tab.icon_input.setText(path)
            self._append_log(S.LOG_DROPPED_ICON.format(path=path))
        else:
            self.advanced_tab.extra_files_list.addItem(path)
            self._append_log(S.LOG_DROPPED_EXTRA.format(path=path))

    # ─── Shutdown ───────────────────────────────────────────────────────

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
