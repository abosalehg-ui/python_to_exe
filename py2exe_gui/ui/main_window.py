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
import webbrowser
from dataclasses import replace

from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtGui import QDesktopServices, QFont, QKeySequence
from PyQt5.QtWidgets import (
    QAction,
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
    PRESETS_FILE,
    PYINSTALLER_REQUIREMENT,
    SETTINGS_FILE,
)
from py2exe_gui.core import (
    RELEASES_PAGE_URL,
    BuildConfig,
    BuildHistory,
    InstallerConfig,
    ManifestConfig,
    PresetLibrary,
    apply_fixes,
    build_iscc_command,
    build_pyinstaller_command,
    build_signtool_command,
    check_for_update,
    dedupe_findings,
    detect_imports,
    diagnose_output,
    diagnostic_config,
    examine,
    filter_non_stdlib,
    find_iscc,
    generate_iss_script,
    generate_manifest,
    generate_version_file,
    installer_output_path,
    local_module_names,
    locate_built_executable,
    make_record,
    needs_diagnostic_run,
    parse_requirements,
    read_warn_findings,
    readiness_score,
    redact_password,
    resolve_languages,
    sort_findings,
    summarize,
)
from py2exe_gui.core.build_report import (
    ReportData,
    parse_versions,
    render_html,
    report_path_for,
    sha256_file,
    write_report,
)
from py2exe_gui.core.diagnostics import build_name, build_root
from py2exe_gui.core.fixes import (
    ORIGIN_BUILD,
    ORIGIN_RUNTIME,
    Finding,
    finding_resolved,
    fix_is_applied,
)
from py2exe_gui.core.installer import validate as validate_installer
from py2exe_gui.core.knowledge import default_is_installed
from py2exe_gui.core.project_file import (
    PROJECT_FILE_NAME,
    SECTIONS,
    ProjectConfig,
    ProjectFileError,
    load_project,
    new_project_for_script,
    project_path_for_script,
    save_project,
    sections_in,
    untrusted_flags,
)
from py2exe_gui.core.project_scan import project_imports
from py2exe_gui.core.release import credentials
from py2exe_gui.core.release.changelog import draft_notes
from py2exe_gui.core.release.git import remote_slug
from py2exe_gui.core.release.pipeline import (
    DONE,
    ReleaseContext,
    ReleaseOptions,
    confirmation,
    has_blocking_problems,
)
from py2exe_gui.core.release.versioning import apply_version, is_semver, version_mismatches
from py2exe_gui.core.runtime_kit import (
    preview_options,
    render_hook,
    render_runtime_config,
    untrusted_risks,
    write_kit,
)
from py2exe_gui.core.sandbox import generate_wsb, sandbox_available, wsb_for_output
from py2exe_gui.core.size_analyzer import (
    analyze_build,
    exclude_suggestions,
    format_size,
    group_label_key,
    indirect_packages,
    onefile_too_big,
    output_path_for,
    previous_size,
)
from py2exe_gui.core.update_signing import (
    backup_existing,
    fingerprint,
    is_inside,
    key_to_json,
    new_signing_key,
    publish_update,
    read_key_file,
    read_public_key,
    write_key_file,
)
from py2exe_gui.core.venv_manager import (
    InstalledChecker,
    delete_env,
    env_dir_for,
    env_exists,
    env_python,
    env_status,
    find_uv,
    folder_size,
    format_lock,
    freeze_command,
    lock_file_path,
    plan_environment,
    project_requirements,
    quote_command,
    write_metadata,
)
from py2exe_gui.paths import envs_dir, signing_key_path
from py2exe_gui.strings import (
    LOCALE_LAYOUT,
    S,
    current_locale,
    set_locale,
)
from py2exe_gui.styles import (
    DEFAULT_FONT_SCALE,
    FONT_SCALE_STEP,
    clamp_scale,
    resolve_theme,
    themed_stylesheet,
)
from py2exe_gui.templates import TEMPLATES, template_name
from py2exe_gui.texts import notes_titles, project_error_text, runtime_texts
from py2exe_gui.ui.batch_thread import BatchThread
from py2exe_gui.ui.conversion_thread import ConversionThread
from py2exe_gui.ui.diagnostic_thread import DiagnosticThread
from py2exe_gui.ui.dialogs import (
    CommandPreviewDialog,
    PresetNameDialog,
    ReleaseConfirmDialog,
    WelcomeDialog,
)
from py2exe_gui.ui.env_thread import EnvThread
from py2exe_gui.ui.finding_text import finding_detail, finding_title, fix_label, service_label
from py2exe_gui.ui.icon_studio_dialog import IconStudioDialog
from py2exe_gui.ui.installer_thread import InstallerThread
from py2exe_gui.ui.post_build_thread import PostBuildThread
from py2exe_gui.ui.release_thread import ReleaseThread
from py2exe_gui.ui.tabs import (
    AboutTab,
    AdvancedTab,
    BatchTab,
    DeployTab,
    DoctorTab,
    HistoryTab,
    InstallerTab,
    MainTab,
    ReleaseTab,
    RuntimeTab,
    SizeTab,
    TemplatesTab,
    VersionInfoTab,
)
from py2exe_gui.ui.tabs.size_tab import size_text
from py2exe_gui.ui.tray import BuildTray

# Tabs shown in simple mode. Eight tabs at once is a lot to meet when all you
# want is one .exe; the rest stay one button away.
SIMPLE_MODE_TABS = ("main", "doctor", "size", "runtime", "release", "templates", "about")

# Where isolated build environments are created. A module global so tests can
# point it at a temporary folder.
ENVS_ROOT = envs_dir()

# The Runtime Kit's private update-signing key (per-user config folder).
# A module global for the same reason.
SIGNING_KEY_FILE = signing_key_path()

# The OS keyring used for the GitHub token (``credentials.DEFAULT`` = the real
# ``keyring`` package, if installed). A module global so tests use a fake one.
KEYRING = credentials.DEFAULT

# Recent projects kept in the settings file.
RECENT_PROJECTS_MAX = 8

# Every part of a ProjectConfig a tab can apply.
ALL_SECTIONS = ("build", "project") + SECTIONS

# Wait this long after the last edit before re-examining the project, so the
# doctor does not re-parse the script on every keystroke in the path field.
DOCTOR_DEBOUNCE_MS = 500


class MainWindow(QMainWindow):
    """النافذة الرئيسية للتطبيق."""

    def __init__(self):
        super().__init__()
        self.conversion_thread = None
        self.installer_thread = None
        self.post_build_thread = None
        self.batch_thread = None
        self.diagnostic_thread = None
        self.env_thread = None
        self.settings = {}
        self.current_theme = "dark"
        self.font_scale = DEFAULT_FONT_SCALE
        self.simple_mode = True
        self._build_start_time = 0.0
        self._build_config_snapshot = {}
        self._temp_version_file = ""
        self._temp_manifest_file = ""
        self._last_built_exe = ""
        self._shortcuts = []
        self._batch_jobs = []
        # Project doctor state: what the pre-build check predicts, and what
        # the last build / run actually reported (kept until the source changes).
        self._doctor_findings = []
        self._build_findings = []
        self._build_findings_source = ""
        self._source_imports = set()
        self._build_output = []
        self._build_wall_start = 0.0
        self._build_command = []
        # One import checker per foreign interpreter (isolated environments),
        # so the doctor asks each one in a single subprocess, not per module.
        self._checkers = {}
        self._size_view = None
        self._last_report_path = ""
        # The open project file ('' = none) and the state it was saved in,
        # for the window title's unsaved-changes marker.
        self.project_path = ""
        self.project_name = ""
        self._saved_snapshot = None
        self.release_thread = None
        self._release_after_plan = False
        self._last_release_dir = ""
        self._modified_timer = QTimer(self)
        self._modified_timer.setSingleShot(True)
        self._modified_timer.setInterval(150)
        self._modified_timer.timeout.connect(self._update_modified)
        self._doctor_timer = QTimer(self)
        self._doctor_timer.setSingleShot(True)
        self._doctor_timer.setInterval(DOCTOR_DEBOUNCE_MS)
        self._doctor_timer.timeout.connect(self.run_doctor)
        self.history = BuildHistory(HISTORY_FILE)
        self.presets = PresetLibrary(PRESETS_FILE)
        self.load_settings()
        self.current_theme = self.settings.get("theme", "dark")
        self.font_scale = clamp_scale(self.settings.get("font_scale", DEFAULT_FONT_SCALE))
        self.simple_mode = bool(self.settings.get("simple_mode", True))
        self.init_ui()
        self._register_shortcuts()
        self.setAcceptDrops(True)
        self.tray = BuildTray(self, self.windowIcon())
        self.check_dependencies()
        self._refresh_history_list()
        self._refresh_presets_list()
        self._saved_snapshot = self._project_snapshot()
        self._update_title()
        # The first-run dialog and the update check are NOT started here:
        # both are modal or blocking, and a constructor that blocks cannot be
        # instantiated by a test (or shown before it finishes). ``app.main``
        # calls run_startup_tasks() once the window is on screen.

    # ─── Construction ───────────────────────────────────────────────────

    def init_ui(self):
        self._update_title()
        # A hard 800px minimum did not fit a 1366x768 laptop. Keep the
        # comfortable size as the *default*, not as a floor.
        self.setMinimumSize(900, 600)
        self.resize(1080, 800)
        self._apply_layout_direction()
        self._apply_stylesheet()
        self.setCentralWidget(self._build_central_widget())
        self._build_menu()
        self.statusBar().showMessage(f"{COPYRIGHT} | {DEVELOPER}")

    def _apply_stylesheet(self):
        """Repaint the window for the active theme, locale and font scale."""
        self.setStyleSheet(
            themed_stylesheet(self.current_theme, current_locale(), self.font_scale)
        )

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
        self.doctor_tab = DoctorTab(self)
        self.size_tab = SizeTab(self)
        self.runtime_tab = RuntimeTab(self)
        self.release_tab = ReleaseTab(self)
        self.advanced_tab = AdvancedTab(self)
        self.version_info_tab = VersionInfoTab(self)
        self.deploy_tab = DeployTab(self)
        self.installer_tab = InstallerTab(self)
        self.batch_tab = BatchTab(self)
        self.templates_tab = TemplatesTab(self)
        self.history_tab = HistoryTab(self)
        self.about_tab = AboutTab(self)

        # Keyed so simple mode can pick a subset by name rather than by index.
        self._all_tabs = (
            ("main", self.main_tab, S.TAB_MAIN),
            ("doctor", self.doctor_tab, S.TAB_DOCTOR),
            ("size", self.size_tab, S.TAB_SIZE),
            ("runtime", self.runtime_tab, S.TAB_RUNTIME),
            ("release", self.release_tab, S.TAB_RELEASE),
            ("advanced", self.advanced_tab, S.TAB_ADVANCED),
            ("version_info", self.version_info_tab, S.TAB_VERSION_INFO),
            ("deploy", self.deploy_tab, S.TAB_DEPLOY),
            ("installer", self.installer_tab, S.TAB_INSTALLER),
            ("batch", self.batch_tab, S.TAB_BATCH),
            ("templates", self.templates_tab, S.TAB_TEMPLATES),
            ("history", self.history_tab, S.TAB_HISTORY),
            ("about", self.about_tab, S.TAB_ABOUT),
        )

        # The tabs that hold a part of the project, in the order they are read.
        self._project_tabs = (
            self.main_tab, self.advanced_tab, self.deploy_tab, self.size_tab,
            self.runtime_tab, self.version_info_tab, self.installer_tab, self.release_tab,
        )

        self.tabs = QTabWidget()
        self._populate_tabs()
        layout.addWidget(self.tabs)

        self.templates_tab.set_theme(self.settings.get("theme", "dark"))

        # Re-examine whenever something the doctor's checks depend on changes.
        main = self.main_tab
        main.source_input.textChanged.connect(self._schedule_doctor)
        main.icon_input.textChanged.connect(self._schedule_doctor)
        main.windowed_check.toggled.connect(self._schedule_doctor)
        main.noconsole_check.toggled.connect(self._schedule_doctor)
        # The Runtime Kit preview names the app and its build kind.
        main.source_input.textChanged.connect(self.refresh_runtime_preview)
        main.output_name.textChanged.connect(self.refresh_runtime_preview)
        main.onefile_check.toggled.connect(self.refresh_runtime_preview)
        self.refresh_signing_key()
        self.refresh_runtime_preview()

        # Per-user preferences that live in settings, not in shared configs:
        # the interpreter path in particular must never come from a JSON file
        # someone else wrote.
        size = self.size_tab
        size.base_python.setText(str(self.settings.get("base_python", "")))
        size.base_python.textChanged.connect(
            lambda text: self.settings.__setitem__("base_python", text.strip())
        )
        size.report_auto.setChecked(bool(self.settings.get("report_auto", True)))
        size.report_auto.toggled.connect(
            lambda on: self.settings.__setitem__("report_auto", bool(on))
        )
        # The Inno Setup compiler is a program on this machine: a per-user
        # setting, never part of a project file someone else can write.
        self.installer_tab.inst_iscc_path.setText(str(self.settings.get("iscc_path", "")))
        self.installer_tab.inst_iscc_path.textChanged.connect(
            lambda text: self.settings.__setitem__("iscc_path", text.strip())
        )
        self._watch_project_fields()
        self.refresh_token_status()

        layout.addWidget(self._create_progress_group())
        layout.addLayout(self._create_action_buttons())
        return central

    def _populate_tabs(self):
        """Fill the tab bar with the set the current mode calls for.

        Tabs not shown are only detached from the bar, never destroyed — their
        widgets still hold state, so switching modes mid-setup loses nothing.
        """
        self.tabs.clear()
        for key, widget, title in self._all_tabs:
            if self.simple_mode and key not in SIMPLE_MODE_TABS:
                continue
            self.tabs.addTab(widget, title)

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
        self.mode_btn = action(self._mode_button_label(), self.toggle_mode)
        self.mode_btn.setToolTip(
            S.MODE_ADVANCED_TIP if self.simple_mode else S.MODE_SIMPLE_TIP
        )
        return row

    def _mode_button_label(self) -> str:
        """The button offers the *other* mode, so its label is the target."""
        return S.BTN_MODE_TO_ADVANCED if self.simple_mode else S.BTN_MODE_TO_SIMPLE

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

    def _current_project(self) -> ProjectConfig:
        """The whole form as one ``ProjectConfig`` — each tab reads its part."""
        project = ProjectConfig(name=self.project_name)
        for tab in self._project_tabs:
            tab.read_project(project)
        return project

    def _apply_project(self, project: ProjectConfig, sections=ALL_SECTIONS):
        """Show ``project`` in the form. Only ``sections`` are touched, so a
        pre-1.6 preset (build settings only) leaves the installer tab alone."""
        if "project" in sections:
            self.project_name = project.name
        for tab in self._project_tabs:
            tab.apply_project(project, sections)
        self.refresh_runtime_preview()
        self._schedule_modified()

    def _current_config(self) -> BuildConfig:
        return self._current_project().build

    def _apply_config(self, config: BuildConfig):
        self._apply_project(ProjectConfig(build=config), ("build",))

    @staticmethod
    def _sections_of(data: dict):
        """What a JSON settings dict (file, preset, history) actually holds."""
        present = ["build"] + sections_in(data)
        if isinstance(data.get("project"), dict):
            present.append("project")
        return tuple(present)

    def save_current_settings(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, S.DIALOG_SAVE_SETTINGS, "py2exe_config.json", S.DIALOG_FILTER_JSON
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self._current_project().to_settings_dict(), f,
                          ensure_ascii=False, indent=2)
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
            project = ProjectConfig.from_settings_dict(data)
        except (OSError, ValueError, TypeError) as e:
            QMessageBox.critical(self, S.MSG_ERROR, S.ERR_LOAD_FAIL.format(error=str(e)))
            return

        if not self._confirm_untrusted_config(project.build):
            self._append_log(S.LOG_SETTINGS_REJECTED.format(path=file_path))
            return

        self._apply_project(project, self._sections_of(data))
        self._append_log(S.LOG_SETTINGS_LOADED.format(path=file_path))
        QMessageBox.information(self, S.MSG_SUCCESS, S.MSG_LOADED_OK)

    def _confirm_untrusted_config(self, config: BuildConfig) -> bool:
        """Ask before applying a config that would make PyInstaller run code.

        A settings file is shareable, and flags like ``--runtime-hook`` inject
        code into every EXE the build produces. The user needs to see that
        before it silently becomes part of a signed binary.
        """
        flags = untrusted_flags(config)
        if flags:
            shown = config.extra_args
            if config.upx and config.upx_dir.strip():
                shown = f"{shown} --upx-dir={config.upx_dir}".strip()
            reply = QMessageBox.question(
                self,
                S.MSG_CONFIRM,
                S.MSG_DANGEROUS_ARGS_CONFIRM.format(
                    flags="\n".join(f"  • {f}" for f in flags),
                    args=shown,
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return False
        # The Runtime Kit cannot inject code (it is flags and text), but an
        # updater trusting someone else's key would install what they sign.
        risks = untrusted_risks(config.runtime_kit, read_public_key(SIGNING_KEY_FILE))
        if not risks:
            return True
        lines = [
            getattr(S, f"KIT_RISK_{risk.code.upper()}").format(**risk.params) for risk in risks
        ]
        reply = QMessageBox.question(
            self,
            S.MSG_CONFIRM,
            S.MSG_KIT_RISKS_CONFIRM.format(risks="\n\n".join(lines)),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return reply == QMessageBox.Yes

    # ─── Presets ────────────────────────────────────────────────────────

    def _refresh_presets_list(self):
        if hasattr(self, "templates_tab"):
            self.templates_tab.refresh_presets(self.presets)

    def save_current_preset(self):
        """Store the current form under a name the user chooses."""
        dialog = PresetNameDialog(self, initial=self.main_tab.output_name.text().strip())
        if not dialog.exec_():
            return
        name = dialog.get_value()
        if not name:
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_PRESET_NAME)
            return

        if self.presets.has(name):
            reply = QMessageBox.question(
                self,
                S.MSG_CONFIRM,
                S.PRESET_OVERWRITE_CONFIRM.format(name=name),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        if not self.presets.put(name, self._current_project().to_settings_dict()):
            QMessageBox.critical(
                self, S.MSG_ERROR, S.ERR_PRESET_SAVE_FAIL.format(error=self.presets.last_error)
            )
            return
        self._refresh_presets_list()
        self._append_log(S.PRESET_SAVED_FMT.format(name=name))

    def apply_selected_preset(self):
        """Load the selected preset back into the form."""
        name = self.templates_tab.selected_preset()
        if not name:
            return
        data = self.presets.get(name)
        if data is None:
            return
        project = ProjectConfig.from_settings_dict(data)
        # A preset can be imported from elsewhere, so it gets the same
        # dangerous-flag check as a settings file.
        if not self._confirm_untrusted_config(project.build):
            return
        self._apply_project(project, self._sections_of(data))
        self._append_log(S.PRESET_APPLIED_FMT.format(name=name))

    def delete_selected_preset(self):
        name = self.templates_tab.selected_preset()
        if not name:
            return
        reply = QMessageBox.question(
            self,
            S.MSG_CONFIRM,
            S.MSG_PRESET_DELETE_CONFIRM.format(name=name),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        if self.presets.delete(name):
            self._refresh_presets_list()
            self._append_log(S.PRESET_DELETED_FMT.format(name=name))

    def export_presets(self):
        if len(self.presets) == 0:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, S.DIALOG_EXPORT_PRESETS, "py2exe_presets.json", S.DIALOG_FILTER_JSON
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.presets.export_all(), f, ensure_ascii=False, indent=2)
        except (OSError, TypeError) as e:
            QMessageBox.critical(self, S.MSG_ERROR, S.ERR_SAVE_FAIL.format(error=str(e)))
            return
        self._append_log(S.LOG_SETTINGS_SAVED.format(path=file_path))

    def import_presets(self):
        """Merge a shared preset file, without overwriting the user's own."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, S.DIALOG_IMPORT_PRESETS, "", S.DIALOG_FILTER_JSON
        )
        if not file_path:
            return
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            QMessageBox.critical(self, S.MSG_ERROR, S.ERR_LOAD_FAIL.format(error=str(e)))
            return

        added = self.presets.import_all(data)
        self._refresh_presets_list()
        if added:
            self._append_log(S.LOG_PRESET_IMPORTED_FMT.format(count=len(added)))
        else:
            self._append_log(S.LOG_PRESET_IMPORT_NONE)

    # ─── Batch conversion ───────────────────────────────────────────────

    def start_batch_conversion(self):
        """Build every queued file in turn with the current settings."""
        if self._build_in_progress():
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_BATCH_BUSY)
            return

        jobs = self.batch_tab.jobs()
        if not jobs:
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_BATCH_NO_FILES)
            return

        if not self._ensure_pyinstaller():
            return

        self._batch_jobs = jobs
        self.batch_tab.set_running(True)
        self.convert_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(S.PROGRESS_CONVERTING)

        self.batch_thread = BatchThread(
            jobs, self._current_config(), python_for=self.build_python,
            options_for=self._runtime_kit_options,
        )
        self.batch_thread.log_signal.connect(self._append_log)
        self.batch_thread.progress_signal.connect(self.progress_bar.setValue)
        self.batch_thread.job_signal.connect(self._on_batch_job_update)
        self.batch_thread.finished_signal.connect(self._on_batch_finished)
        self.batch_thread.start()

    def cancel_batch_conversion(self):
        if not (self.batch_thread and self.batch_thread.isRunning()):
            return
        reply = QMessageBox.question(
            self,
            S.MSG_CONFIRM,
            S.MSG_BATCH_CANCEL_CONFIRM,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.batch_thread.cancel()

    def _on_batch_job_update(self, index, _total, _status):
        if 0 <= index < len(self._batch_jobs):
            self.batch_tab.update_row(index, self._batch_jobs[index])

    def _on_batch_finished(self, completed):
        self.batch_tab.set_running(False)
        self.convert_btn.setEnabled(True)
        self.progress_bar.setFormat(S.PROGRESS_DONE if completed else S.PROGRESS_FAILED)
        self.batch_tab.show_summary(self._batch_jobs)

        # Every batch job is a real build, so each belongs in the history.
        for job in self._batch_jobs:
            record = make_record(
                source=job.source,
                output_name=job.output_name,
                success=job.status == "success",
                duration_seconds=job.duration_seconds,
                config=self._current_project().to_settings_dict(),
            )
            self.history.add(record)
        self._refresh_history_list()

        summary = summarize(self._batch_jobs)
        self._notify_build_result(
            summary.failed == 0 and summary.cancelled == 0,
            f"{summary.succeeded}/{summary.total}",
        )

    def _build_in_progress(self) -> bool:
        for thread in (
            self.conversion_thread, self.batch_thread, self.diagnostic_thread, self.env_thread,
            self.release_thread,
        ):
            if thread and thread.isRunning():
                return True
        return False

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

    def _ensure_pyinstaller(self, python: str = "") -> bool:
        """Check for PyInstaller, offering to install it with explicit consent.

        The previous version ran ``pip install pyinstaller`` silently on the
        first build: an unattended network install, unpinned, from whatever
        index the environment happened to point at. ``python`` is the build
        interpreter (an isolated environment's), defaulting to this one.
        """
        try:
            subprocess.run(
                [python or sys.executable, "-m", "PyInstaller", "--version"],
                capture_output=True,
                check=True,
            )
            return True
        except (OSError, subprocess.CalledProcessError):
            pass

        install_cmd = [python or sys.executable, "-m", "pip", "install", PYINSTALLER_REQUIREMENT]
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
        python = self.build_python(config)
        cmd, error = build_pyinstaller_command(config, python_executable=python)
        if error:
            self._cleanup_temp_files()
            QMessageBox.warning(self, S.MSG_WARNING, error)
            return
        kit_options, kit_error = self._runtime_kit_options(config)
        if kit_error:
            self._cleanup_temp_files()
            QMessageBox.warning(self, S.MSG_WARNING, kit_error)
            return
        if kit_options:
            cmd, _error = build_pyinstaller_command(
                config, python_executable=python, extra_options=kit_options
            )
            self._append_log(S.LOG_KIT_EMBEDDED_FMT.format(
                services=", ".join(self._runtime_service_labels(config))
            ))

        if config.isolated_env and not env_exists(self._env_dir(config.source)):
            self._cleanup_temp_files()
            reply = QMessageBox.question(
                self, S.MSG_CONFIRM, S.MSG_ENV_NEEDED,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
            )
            if reply == QMessageBox.Yes:
                self.create_build_env(then_build=True)
            return

        if not self._ensure_pyinstaller(python):
            self._cleanup_temp_files()
            return
        if python != sys.executable:
            self._append_log(S.LOG_ENV_PYTHON.format(python=python))
        self._build_command = list(cmd)

        self._build_start_time = time.monotonic()
        self._build_wall_start = time.time()
        snapshot = self._current_project()
        snapshot.build = config
        self._build_config_snapshot = snapshot.to_settings_dict()
        self._build_output = []

        # A last look before building: the doctor never blocks a build, but
        # errors it can already see are worth one line in the log.
        self.run_doctor()
        errors = sum(f.severity == "error" for f in self._doctor_findings)
        if errors:
            self._append_log(S.LOG_DOCTOR_PREBUILD.format(errors=errors))

        work_dir = self.main_tab.output_dir.text() or os.path.dirname(
            self.main_tab.source_input.text()
        )

        self.convert_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(S.PROGRESS_CONVERTING)

        self.conversion_thread = ConversionThread(cmd, work_dir)
        self.conversion_thread.log_signal.connect(self._append_log)
        self.conversion_thread.log_signal.connect(self._build_output.append)
        self.conversion_thread.progress_signal.connect(self.progress_bar.setValue)
        self.conversion_thread.stage_signal.connect(self._on_stage_changed)
        self.conversion_thread.finished_signal.connect(self.on_conversion_finished)
        self.conversion_thread.start()

        # A build runs for minutes; make sure it can report from the tray even
        # if the window ends up minimised or behind something else.
        self.tray.show()

    def _on_stage_changed(self, stage_key: str):
        """Name the phase PyInstaller has reached on the progress bar."""
        label = getattr(S, f"STAGE_{stage_key.upper()}", "")
        if label:
            self.progress_bar.setFormat(S.PROGRESS_STAGE_FMT.format(stage=label))

    def _notify_build_result(self, success: bool, name: str):
        """Raise a desktop notification, unless the window is already focused."""
        if self.isActiveWindow():
            return
        if success:
            self.tray.notify(
                S.TRAY_BUILD_OK_TITLE, S.TRAY_BUILD_OK_BODY.format(name=name), True
            )
        else:
            self.tray.notify(S.TRAY_BUILD_FAIL_TITLE, S.TRAY_BUILD_FAIL_BODY, False)

    def cancel_conversion(self):
        if self.conversion_thread and self.conversion_thread.isRunning():
            self.conversion_thread.cancel()
            self._append_log(S.LOG_CANCELLING)

    def on_conversion_finished(self, success, message):
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        duration = max(0.0, time.monotonic() - self._build_start_time)
        snapshot = self._build_config_snapshot

        # Measure before recording: the record stores the size, and the
        # comparison must be against the build *before* this one.
        size_report, previous = None, 0
        if success and snapshot:
            built = BuildConfig.from_dict(snapshot)
            previous = previous_size(
                self.history.records, built.source, snapshot.get("output_name", "")
            )
            size_report = analyze_build(built)

        if snapshot:
            record = make_record(
                source=snapshot.get("source", ""),
                output_name=snapshot.get("output_name", ""),
                success=success,
                duration_seconds=round(duration, 2),
                config=snapshot,
                size_bytes=size_report.output_bytes if size_report else 0,
            )
            if not self.history.add(record):
                self._append_log(
                    S.LOG_HISTORY_SAVE_FAIL.format(error=self.history.last_error)
                )
            self._refresh_history_list()

        diagnosed = []
        if snapshot and message != S.CONV_CANCELLED:
            diagnosed = self._diagnose_build(BuildConfig.from_dict(snapshot))
            if not success and diagnosed:
                message += S.MSG_DOCTOR_FAILED_HINT.format(count=len(diagnosed))

        if size_report is not None:
            built = BuildConfig.from_dict(snapshot)
            self._show_size(built, size_report, previous)
            if size_report.output_bytes:
                self._append_log(
                    S.LOG_SIZE_SUMMARY.format(disk=size_text(size_report.output_bytes))
                )
            if self.size_tab.report_auto.isChecked():
                self._write_build_report(built, size_report, previous, duration, success)

        # Post-build actions only make sense for a successful build.
        if success and snapshot:
            try:
                self._run_post_build_actions(BuildConfig.from_dict(snapshot))
            except (OSError, ValueError) as e:
                self._append_log(S.LOG_SIGNING_FAIL.format(error=str(e)))

        output_name = snapshot.get("output_name", "") if snapshot else ""
        self._build_config_snapshot = {}
        self._cleanup_temp_files()

        # Notify before the modal box: the dialog blocks until acknowledged,
        # and the whole point is to reach a user who is looking elsewhere.
        self._notify_build_result(success, output_name)

        if success:
            self.progress_bar.setFormat(S.PROGRESS_DONE)
            QMessageBox.information(self, S.MSG_SUCCESS, message)
        else:
            self.progress_bar.setFormat(S.PROGRESS_FAILED)
            if message != S.CONV_CANCELLED:
                QMessageBox.critical(self, S.MSG_ERROR, message)

    def preview_command(self):
        """Show the PyInstaller command that would be executed."""
        config = self._current_config()
        cmd, error = build_pyinstaller_command(
            config, python_executable=self.build_python(config),
            extra_options=preview_options(config),
        )
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
        """Ctrl+T: flip between dark and light, the two most-used themes.

        The full list (including ``auto``, Nord and high contrast) lives in
        the Templates tab; this stays a two-way switch because that is what a
        single shortcut can usefully be.
        """
        stored = self.settings.get("theme", self.current_theme)
        # From auto or a named theme, flip relative to what is on screen now.
        target = "light" if resolve_theme(stored) == "dark" else "dark"
        self.apply_theme(target)

    def apply_theme(self, theme: str):
        """Set the theme preference, repaint, and persist it."""
        self.settings["theme"] = theme
        self.current_theme = resolve_theme(theme)
        self._apply_stylesheet()
        self._repaint_log()
        if hasattr(self, "templates_tab"):
            self.templates_tab.set_theme(theme)
        self._append_log(S.LOG_THEME_CHANGED.format(theme=theme))

    def _on_theme_changed(self, index=None):
        """Handler for the Templates tab's theme selector."""
        selected = self.templates_tab.selected_theme()
        if selected != self.settings.get("theme"):
            self.apply_theme(selected)

    def _repaint_log(self):
        """Re-render buffered log lines in the new theme's palette.

        Log colours are baked into the HTML at append time, so a theme change
        leaves earlier lines in the old palette — which is exactly the bug the
        light theme's log had before per-theme palettes existed.
        """
        self.main_tab._log_theme = self.current_theme
        self.main_tab._apply_log_filter()

    # ── Font zoom ───────────────────────────────────────────────────────────

    def zoom_in(self):
        self._set_font_scale(self.font_scale + FONT_SCALE_STEP)

    def zoom_out(self):
        self._set_font_scale(self.font_scale - FONT_SCALE_STEP)

    def zoom_reset(self):
        self._set_font_scale(DEFAULT_FONT_SCALE)

    def _set_font_scale(self, scale: float):
        """Rescale every font in the stylesheet, clamped to a usable range."""
        new_scale = clamp_scale(scale)
        if new_scale == self.font_scale:
            return
        self.font_scale = new_scale
        self.settings["font_scale"] = new_scale
        self._apply_stylesheet()
        self._append_log(S.LOG_ZOOM_FMT.format(percent=round(new_scale * 100)))

    # ── Simple / advanced mode ─────────────────────────────────────────────

    def toggle_mode(self):
        self.set_simple_mode(not self.simple_mode)

    def set_simple_mode(self, simple: bool):
        """Show either the essential tabs or all of them, and remember which."""
        self.simple_mode = bool(simple)
        self.settings["simple_mode"] = self.simple_mode
        self._populate_tabs()
        self.mode_btn.setText(self._mode_button_label())
        self.mode_btn.setAccessibleName(self.mode_btn.text())
        self.mode_btn.setToolTip(
            S.MODE_ADVANCED_TIP if self.simple_mode else S.MODE_SIMPLE_TIP
        )
        self._append_log(S.LOG_MODE_SIMPLE if self.simple_mode else S.LOG_MODE_ADVANCED)

    def run_startup_tasks(self):
        """Anything that blocks, run after the window is visible.

        Called by ``app.main`` rather than from ``__init__`` so that
        constructing a MainWindow stays non-blocking and testable.
        """
        self._maybe_show_welcome()
        self._maybe_check_for_updates()

    def _maybe_show_welcome(self):
        """Ask which mode to start in, once, on the very first run."""
        if self.settings.get("welcomed"):
            return
        self.settings["welcomed"] = True
        dialog = WelcomeDialog(self)
        dialog.exec_()
        self.set_simple_mode(dialog.simple_mode)
        self.save_settings()

    # ── Update check ───────────────────────────────────────────────────────

    def _maybe_check_for_updates(self):
        """Check on startup only if the user opted in — never by default.

        A packaging tool that phones home unasked is not what anyone installed;
        the setting defaults to off and the manual button is always available.
        """
        if self.settings.get("check_updates_on_start"):
            self.check_for_updates(interactive=False)

    def check_for_updates(self, interactive: bool = True):
        """Look for a newer release. Reports only — nothing is downloaded."""
        self._append_log(S.LOG_UPDATE_CHECKING)
        info = check_for_update(APP_VERSION)
        if info is None:
            self._append_log(S.LOG_UPDATE_NONE.format(version=APP_VERSION))
            if interactive:
                QMessageBox.information(self, S.MSG_SUCCESS, S.UPDATE_NONE)
            return

        self._append_log(S.LOG_UPDATE_AVAILABLE.format(version=info.version, url=info.url))
        reply = QMessageBox.question(
            self,
            S.MSG_INFO_TITLE,
            S.UPDATE_AVAILABLE_FMT.format(version=info.version, current=APP_VERSION),
            QMessageBox.Open | QMessageBox.Close,
            QMessageBox.Close,
        )
        if reply == QMessageBox.Open:
            webbrowser.open(info.url or RELEASES_PAGE_URL)

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
        project = self._current_project()
        modified = self.is_project_modified()
        # In memory only, never in the project: restored by hand below.
        password = self.deploy_tab.signing_password.text()
        notes = self.release_tab.notes_edit.toPlainText()
        # Snapshot the buffer, not the rendered HTML: the filter re-renders
        # from the buffer, so restoring HTML alone would lose the severities.
        log_lines = self.main_tab.log_lines()
        batch_sources = self.batch_tab.sources()
        publish_fields = self.runtime_tab.publish_fields()

        set_locale(locale_code)
        self._apply_layout_direction()
        self.setStyleSheet(
            themed_stylesheet(self.current_theme, locale_code, self.font_scale)
        )
        self.setCentralWidget(self._build_central_widget())
        self._build_menu()
        self.statusBar().showMessage(f"{COPYRIGHT} | {DEVELOPER}")

        # Rebuilding the widgets loses nothing: the project model carries the
        # form across (before 1.6 the deploy and installer tabs were reset).
        self._apply_project(project)
        self.deploy_tab.signing_password.setText(password)
        self.release_tab.notes_edit.setPlainText(notes)
        if not modified:
            self._saved_snapshot = self._project_snapshot()
        self._update_modified()

        self.main_tab.restore_log(log_lines)
        self.main_tab.refresh_icon_preview()
        self._refresh_doctor_view()
        self._refresh_size_view()
        self.refresh_env_view()
        self.size_tab.set_report_path(self._last_report_path)
        self.batch_tab.set_sources(batch_sources)
        self.runtime_tab.set_publish_fields(publish_fields)
        self.refresh_signing_key()
        self.refresh_runtime_preview()
        self.mode_btn.setText(self._mode_button_label())
        self._refresh_history_list()
        self._refresh_presets_list()
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
        project = ProjectConfig.from_settings_dict(record.config)
        if not self._confirm_untrusted_config(project.build):
            return
        self._apply_project(project, self._sections_of(record.config))
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

    # ─── Project doctor ─────────────────────────────────────────────────

    def _schedule_doctor(self, *_args):
        self._doctor_timer.start()

    def _source_path(self) -> str:
        return self.main_tab.source_input.text().strip()

    def run_doctor(self):
        """Examine the current script and settings, then refresh the views."""
        self._doctor_timer.stop()
        source = self._source_path()
        if not source or not os.path.isfile(source):
            self._doctor_findings = []
            self._source_imports = set()
            self._refresh_doctor_view()
            self.refresh_env_view()
            return
        # Findings from a build of a different script no longer apply.
        if self._build_findings and source != self._build_findings_source:
            self._build_findings = []
        config = self._current_config()
        extra = []
        if config.isolated_env and not env_exists(self._env_dir(source)):
            # Its packages will be installed when it is created; until then
            # there is nothing to ask, so don't report them all as missing.
            is_installed = lambda _module: True  # noqa: E731
            extra.append(Finding("env_not_created", "warning"))
        else:
            is_installed = self._installed_checker(config)
        report = examine(source, config, is_installed=is_installed)
        self._doctor_findings = sort_findings(report.findings + extra)
        self._source_imports = report.imports
        self._refresh_doctor_view()
        self.refresh_env_view()

    def _refresh_doctor_view(self):
        source = self._source_path()
        has_source = bool(source) and os.path.isfile(source)
        self.doctor_tab.show_findings(
            self._doctor_findings, self._build_findings, has_source=has_source
        )
        self.main_tab.set_readiness(
            self.doctor_tab_score() if has_source else None
        )

    def doctor_tab_score(self) -> int:
        return readiness_score(self._doctor_findings)

    def show_doctor_tab(self):
        self.tabs.setCurrentWidget(self.doctor_tab)

    def _set_build_findings(self, findings, source: str):
        # A fix already in the settings is not a remedy any more (bundling a
        # file that is read by a relative path, say): keep the finding and its
        # advice, drop the no-op fix so it isn't offered again.
        config = self._current_config()
        findings = [
            replace(
                f,
                fixes=tuple(x for x in f.fixes if not fix_is_applied(config, x)),
                alternatives=tuple(x for x in f.alternatives if not fix_is_applied(config, x)),
            )
            for f in findings
        ]
        self._build_findings = sort_findings(dedupe_findings(findings))
        self._build_findings_source = source
        self._refresh_doctor_view()
        if self._build_findings:
            self._append_log(
                S.LOG_DOCTOR_BUILD_FINDINGS.format(count=len(self._build_findings))
            )

    def apply_doctor_fixes(self, fixes, rebuild: bool = False):
        """Apply fixes chosen on the Doctor tab, optionally rebuilding."""
        if not fixes:
            QMessageBox.information(self, S.MSG_WARNING, S.DOCTOR_NOTHING_SELECTED)
            return
        if self._build_in_progress():
            QMessageBox.warning(self, S.MSG_WARNING, S.MSG_DIAG_BUSY)
            return
        new_config, applied = apply_fixes(self._current_config(), fixes)
        self._apply_config(new_config)
        for fix in applied:
            self._append_log(S.LOG_DOCTOR_FIX_APPLIED.format(fix=fix_label(fix)))

        # Build/runtime findings whose fixes (or alternative) are now all in
        # place are resolved.
        self._build_findings = [
            f for f in self._build_findings if not finding_resolved(new_config, f)
        ]
        self.run_doctor()
        self._refresh_size_view()
        if rebuild:
            self.start_conversion()

    def _diagnose_build(self, config: BuildConfig):
        """Read the build log and warn file of the build that just ended."""
        findings = diagnose_output(
            "\n".join(self._build_output),
            origin=ORIGIN_BUILD,
            source=config.source,
            source_imports=self._source_imports,
            is_installed=self._installed_checker(config),
        )
        findings += read_warn_findings(
            config,
            local_module_names(os.path.dirname(os.path.abspath(config.source))),
            min_mtime=self._build_wall_start,
        )
        self._set_build_findings(findings, config.source)
        return self._build_findings

    def _on_smoke_result(self, config: BuildConfig, passed: bool, output: str):
        """Turn what the built EXE printed into findings."""
        findings = []
        if output and (not passed or "Traceback" in output):
            findings = diagnose_output(
                output,
                origin=ORIGIN_RUNTIME,
                source=config.source,
                source_imports=self._source_imports,
                is_installed=self._installed_checker(config),
            )
        if findings:
            self._set_build_findings(self._build_findings + findings, config.source)
        if passed and needs_diagnostic_run(config):
            self._append_log(S.LOG_SMOKE_WINDOWED_HINT)

    def start_diagnostic_run(self):
        """Build a console copy of the app, run it, and diagnose its output."""
        if self._build_in_progress():
            QMessageBox.warning(self, S.MSG_WARNING, S.MSG_DIAG_BUSY)
            return
        config = self._current_config()
        if not config.source or not os.path.isfile(config.source):
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_NO_SOURCE)
            return
        if not config.output_dir:
            config.output_dir = os.path.dirname(os.path.abspath(config.source))
        if config.isolated_env and not env_exists(self._env_dir(config.source)):
            QMessageBox.warning(self, S.MSG_WARNING, S.FINDING_ENV_NOT_CREATED_DETAIL)
            return
        diag = diagnostic_config(config)
        python = self.build_python(config)
        # The same services as the real app (its code may import them), minus
        # anything that would stop on a dialog or reach the network.
        kit_options, error = self._runtime_kit_options(diag, diagnostic=True)
        if not error:
            cmd, error = build_pyinstaller_command(
                diag, python_executable=python, extra_options=kit_options
            )
        if error:
            QMessageBox.warning(self, S.MSG_WARNING, error)
            return
        if not self._ensure_pyinstaller(python):
            return

        self.convert_btn.setEnabled(False)
        self.doctor_tab.diagnose_btn.setEnabled(False)
        self.progress_bar.setRange(0, 0)  # busy: no stage tracking here

        timeout = max(8.0, float(self.deploy_tab.smoke_timeout.value()))
        self.diagnostic_thread = DiagnosticThread(cmd, diag, timeout=timeout)
        self.diagnostic_thread.log_signal.connect(self._append_log)
        self.diagnostic_thread.finished_signal.connect(
            lambda built, output, build_log: self._on_diagnostic_finished(
                config, built, output, build_log
            )
        )
        self.diagnostic_thread.start()

    def _on_diagnostic_finished(self, config, built: bool, output: str, build_log: str):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(S.PROGRESS_READY)
        self.convert_btn.setEnabled(True)
        self.doctor_tab.diagnose_btn.setEnabled(True)

        imports = self._source_imports
        checker = self._installed_checker(config)
        if built:
            findings = diagnose_output(
                output, origin=ORIGIN_RUNTIME, source=config.source,
                source_imports=imports, is_installed=checker,
            )
        else:
            findings = diagnose_output(
                build_log, origin=ORIGIN_BUILD, source=config.source,
                source_imports=imports, is_installed=checker,
            )
        # The diagnostic run is the freshest evidence: it replaces, not adds to,
        # what the last build reported.
        self._set_build_findings(findings, config.source)
        if built and not findings:
            self._append_log(S.LOG_DIAG_CLEAN)
        self._append_log(S.LOG_DIAG_DONE_FMT.format(count=len(findings)))
        self.show_doctor_tab()

    # ─── Build environment ──────────────────────────────────────────────

    def _env_dir(self, source: str) -> str:
        return env_dir_for(source, ENVS_ROOT)

    def _base_python(self) -> str:
        return self.size_tab.base_python.text().strip() or sys.executable

    def build_python(self, config: BuildConfig) -> str:
        """The interpreter that runs PyInstaller for ``config``."""
        if config.isolated_env and config.source:
            return env_python(self._env_dir(config.source))
        return sys.executable

    def _installed_checker(self, config: BuildConfig):
        """``is_installed`` answering for the build interpreter, not this one."""
        python = self.build_python(config)
        if python == sys.executable:
            return default_is_installed
        if python not in self._checkers:
            self._checkers[python] = InstalledChecker(python)
        return self._checkers[python]

    def on_env_mode_changed(self, *_args):
        self._schedule_doctor()

    def refresh_env_view(self):
        source = self._source_path()
        if not source or not os.path.isfile(source):
            self.size_tab.show_env(None, "", False, has_source=False)
            return
        status = env_status(self._env_dir(source), with_size=False)
        if status.exists and not status.metadata.get("size_bytes"):
            # An environment made outside the app (or before 1.4) has no
            # recorded size: measure it once and remember it.
            status.metadata["size_bytes"] = folder_size(status.env_dir)
            write_metadata(status.env_dir, status.metadata)
        requirements = project_requirements(source)
        if requirements.origin == "lock":
            text = S.ENV_REQ_FROM_LOCK.format(file=requirements.describe())
        elif requirements.origin == "file":
            text = S.ENV_REQ_FROM_FILE.format(file=requirements.describe())
        else:
            text = ", ".join(requirements.args) if requirements.args else S.ENV_REQ_NONE
        self.size_tab.show_env(status, text, bool(find_uv()), has_source=True)

    def create_build_env(self, recreate: bool = False, then_build: bool = False):
        """Create (or refresh) the project's environment, after explicit consent."""
        if self._build_in_progress():
            QMessageBox.warning(self, S.MSG_WARNING, S.MSG_DIAG_BUSY)
            return
        source = self._source_path()
        if not source or not os.path.isfile(source):
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_NO_SOURCE)
            return
        base = self._base_python()
        if not os.path.isfile(base):
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_ENV_PYTHON_MISSING.format(path=base))
            return

        plan = plan_environment(
            source, ENVS_ROOT, base, PYINSTALLER_REQUIREMENT,
            uv=find_uv(), recreate=recreate,
        )
        commands = "\n\n".join(quote_command(c) for c in plan.all_commands())
        reply = QMessageBox.question(
            self, S.MSG_CONFIRM, S.MSG_ENV_CONFIRM.format(commands=commands),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        if recreate and env_exists(plan.env_dir):
            delete_env(plan.env_dir, ENVS_ROOT)
        os.makedirs(ENVS_ROOT, exist_ok=True)

        self.size_tab.set_env_busy()
        self.convert_btn.setEnabled(False)
        self.progress_bar.setRange(0, 0)
        self.env_thread = EnvThread(plan, base_python=base)
        self.env_thread.log_signal.connect(self._append_log)
        self.env_thread.finished_signal.connect(
            lambda ok, failed, error: self._on_env_finished(plan, ok, failed, error, then_build)
        )
        self.env_thread.start()

    def recreate_build_env(self):
        self.create_build_env(recreate=True)

    def _on_env_finished(self, plan, ok: bool, failed, error: str, then_build: bool):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(S.PROGRESS_READY)
        self.convert_btn.setEnabled(True)
        # The environment changed: what it can import must be asked again.
        self._checkers.pop(plan.python, None)
        if ok:
            if failed:
                self._append_log(S.LOG_ENV_DONE_PARTIAL.format(names=", ".join(failed)))
            else:
                self._append_log(S.LOG_ENV_DONE)
        else:
            self._append_log(S.LOG_ENV_FAILED.format(error=error))
            QMessageBox.critical(self, S.MSG_ERROR, S.LOG_ENV_FAILED.format(error=error))
        self.run_doctor()
        if ok and then_build:
            self.start_conversion()

    def delete_build_env(self):
        source = self._source_path()
        if not source:
            return
        env_dir = self._env_dir(source)
        status = env_status(env_dir, with_size=False)
        if not status.exists:
            return
        size = format_size(int(status.metadata.get("size_bytes", 0) or 0))
        reply = QMessageBox.question(
            self, S.MSG_CONFIRM, S.MSG_ENV_DELETE_CONFIRM.format(size=size),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        if delete_env(env_dir, ENVS_ROOT):
            self._append_log(S.LOG_ENV_DELETED)
        self._checkers.pop(env_python(env_dir), None)
        self.run_doctor()

    def save_env_lock(self):
        """Pin the environment's exact versions in p2e-build.lock."""
        source = self._source_path()
        env_dir = self._env_dir(source) if source else ""
        if not env_dir or not env_exists(env_dir):
            return
        try:
            result = subprocess.run(
                freeze_command(env_python(env_dir), find_uv()),
                capture_output=True, text=True, timeout=120,
            )
        except (OSError, subprocess.SubprocessError) as e:
            self._append_log(S.LOG_ENV_LOCK_FAILED.format(error=str(e)))
            return
        if result.returncode != 0:
            self._append_log(
                S.LOG_ENV_LOCK_FAILED.format(error=(result.stderr or "").strip()[:300])
            )
            return
        path = lock_file_path(source)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(format_lock(result.stdout))
        except OSError as e:
            self._append_log(S.LOG_ENV_LOCK_FAILED.format(error=str(e)))
            return
        self._append_log(S.LOG_ENV_LOCK_SAVED.format(path=path))
        self.refresh_env_view()

    # ─── Size lab and build report ──────────────────────────────────────

    def _show_size(self, config: BuildConfig, report, previous: int):
        self._size_view = (config, report, previous)
        self._refresh_size_view()

    def _refresh_size_view(self):
        """Render the size lab. Text is built here, so a language switch
        re-renders it in the new language rather than keeping the old one."""
        if self._size_view is None:
            self.size_tab.show_size_report(None)
            self.size_tab.show_suggestions([])
            return
        config, report, previous = self._size_view
        imports = project_imports(config.source) if config.source else set()
        # Against the current settings: an exclusion just applied drops out.
        suggestions = exclude_suggestions(report, imports, self._current_config())
        hints = []
        indirect = indirect_packages(report, imports)
        if indirect and not config.isolated_env:
            hints.append(S.SIZE_INDIRECT_FMT.format(
                size=size_text(sum(size for _n, size in indirect)),
                names=", ".join(name for name, _s in indirect[:6]),
            ))
        if onefile_too_big(report, config):
            hints.append(S.SIZE_ONEFILE_SLOW_FMT.format(size=size_text(report.output_bytes)))
        self.size_tab.show_size_report(report, previous, hints)
        self.size_tab.show_suggestions(suggestions)

    def analyze_last_build(self):
        """Re-read the inventory of the current settings' last build."""
        config = self._current_config()
        if not config.source:
            return
        report = analyze_build(config)
        if not report.ok:
            self._size_view = None
            self._refresh_size_view()
            return
        previous = previous_size(
            self.history.records, config.source, config.output_name, skip=1
        )
        # Re-reading changes no settings, so hints use the settings as they are.
        self._show_size(config, report, previous)

    def _report_labels(self) -> dict:
        keys = (
            "title", "details", "result", "success", "failed", "size_on_disk",
            "contents", "duration", "previous", "app", "date", "source", "output",
            "mode", "onefile", "onedir", "environment", "python", "pyinstaller",
            "platform", "breakdown", "package", "size", "share", "largest_files",
            "findings", "options", "none", "runtime_kit",
        )
        return {key: getattr(S, f"REPORT_{key.upper()}") for key in keys}

    def _write_build_report(self, config, report, previous, duration, success):
        output = report.output_path or output_path_for(config)
        exe = output if os.path.isfile(output) else locate_built_executable(
            build_root(config), build_name(config), config.onefile
        ) or ""
        groups = []
        for group, size in report.ranked(20):
            key = group_label_key(group)
            groups.append((getattr(S, key) if key else group, size))
        versions = parse_versions("\n".join(self._build_output))
        findings = [
            (f.severity, finding_title(f), finding_detail(f))
            for f in self._build_findings + self._doctor_findings
        ]
        data = ReportData(
            app_name=build_name(config),
            source=config.source,
            output_path=output,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            success=success,
            duration_seconds=duration,
            output_bytes=report.output_bytes,
            content_bytes=report.content_bytes,
            previous_bytes=previous,
            sha256=sha256_file(exe),
            onefile=config.onefile,
            environment=S.REPORT_ENV_ISOLATED if config.isolated_env else S.REPORT_ENV_CURRENT,
            python_version=versions.get("python", ""),
            pyinstaller_version=versions.get("pyinstaller", ""),
            platform=versions.get("platform", ""),
            command=self._build_command,
            groups=groups,
            largest_files=report.largest_files,
            findings=findings,
            runtime_services=self._runtime_service_labels(config),
        )
        document = render_html(
            data,
            self._report_labels(),
            rtl=LOCALE_LAYOUT.get(current_locale(), "ltr") == "rtl",
            lang=current_locale(),
            generator=S.REPORT_GENERATOR_FMT.format(app=APP_NAME, version=APP_VERSION),
        )
        path = report_path_for(config)
        error = write_report(path, document)
        if error:
            self._append_log(S.LOG_REPORT_FAILED.format(error=error))
            return
        self._last_report_path = path
        self.size_tab.set_report_path(path)
        self._append_log(S.LOG_REPORT_SAVED.format(path=path))

    def open_last_report(self):
        if self._last_report_path and os.path.isfile(self._last_report_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._last_report_path))

    # ─── Runtime Kit ────────────────────────────────────────────────────

    def _runtime_texts(self) -> dict:
        return runtime_texts()

    def _rtl(self) -> bool:
        return LOCALE_LAYOUT.get(current_locale(), "ltr") == "rtl"

    def _runtime_service_labels(self, config: BuildConfig):
        return [service_label(name) for name in config.runtime_kit.enabled_services()]

    def _runtime_kit_options(self, config: BuildConfig, diagnostic: bool = False):
        """Write the kit for ``config``; returns (PyInstaller options, error text)."""
        try:
            options, errors = write_kit(
                config, self._runtime_texts(), rtl=self._rtl(), diagnostic=diagnostic
            )
        except OSError as e:
            return [], S.MSG_KIT_INVALID_FMT.format(problems=str(e))
        if errors:
            problems = "\n".join(f"• {finding_title(f)}" for f in errors)
            return [], S.MSG_KIT_INVALID_FMT.format(problems=problems)
        return options, None

    def on_runtime_kit_changed(self):
        self.refresh_runtime_preview()
        self._schedule_doctor()

    def refresh_runtime_preview(self, *_args):
        if not hasattr(self, "runtime_tab"):
            return
        config = self._current_config()
        if not config.runtime_kit.enabled:
            self.runtime_tab.show_preview("", "")
            return
        text = render_runtime_config(
            config.runtime_kit, build_name(config) if config.source or config.output_name
            else "app", config.onefile, self._runtime_texts(), self._rtl(),
        )
        self.runtime_tab.show_preview(render_hook(), text)

    def refresh_signing_key(self):
        self.runtime_tab.show_key(read_public_key(SIGNING_KEY_FILE), SIGNING_KEY_FILE)

    def use_my_public_key(self):
        public = read_public_key(SIGNING_KEY_FILE)
        if public:
            self.runtime_tab.public_key.setText(public)

    def generate_signing_key(self):
        """Create the developer's key pair. Replacing one needs a hard yes."""
        existing = read_public_key(SIGNING_KEY_FILE)
        if existing or os.path.exists(SIGNING_KEY_FILE):
            reply = QMessageBox.question(
                self, S.MSG_CONFIRM,
                S.MSG_KIT_KEY_REPLACE_CONFIRM.format(fingerprint=fingerprint(existing) or "?"),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        key = new_signing_key()
        try:
            backup = backup_existing(SIGNING_KEY_FILE)
            write_key_file(SIGNING_KEY_FILE, key)
        except OSError as e:
            QMessageBox.critical(self, S.MSG_ERROR, S.ERR_KIT_KEY_WRITE.format(error=str(e)))
            return
        if backup:
            self._append_log(S.LOG_KIT_KEY_REPLACED.format(path=backup))
        # Only the public half is ever shown or logged.
        self._append_log(S.LOG_KIT_KEY_GENERATED.format(fingerprint=fingerprint(key.public_hex)))
        self.refresh_signing_key()
        if self.runtime_tab.service_checks["updater"].isChecked():
            self.runtime_tab.public_key.setText(key.public_hex)

    def _forbidden_key_folders(self):
        config = self._current_config()
        folders = []
        if config.source:
            folders.append(os.path.dirname(os.path.abspath(config.source)))
        if config.output_dir:
            folders.append(config.output_dir)
        return folders

    def export_signing_key(self):
        """Back up the private key — after a warning, and never into the project."""
        try:
            key = read_key_file(SIGNING_KEY_FILE)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_KIT_KEY_READ.format(error=str(e)))
            return
        reply = QMessageBox.warning(
            self, S.MSG_CONFIRM, S.MSG_KIT_KEY_EXPORT_WARNING,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, S.DIALOG_KIT_KEY_EXPORT, "update_signing_key.json", S.DIALOG_FILTER_KEY
        )
        if not path:
            return
        if any(is_inside(path, folder) for folder in self._forbidden_key_folders()):
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_KIT_KEY_EXPORT_IN_PROJECT)
            return
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(key_to_json(key))
        except OSError as e:
            QMessageBox.critical(self, S.MSG_ERROR, S.ERR_KIT_KEY_WRITE.format(error=str(e)))
            return
        self._append_log(S.LOG_KIT_KEY_EXPORTED.format(path=path))

    def import_signing_key(self):
        path, _ = QFileDialog.getOpenFileName(
            self, S.DIALOG_KIT_KEY_IMPORT, "", S.DIALOG_FILTER_KEY
        )
        if not path:
            return
        try:
            key = read_key_file(path)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_KIT_KEY_READ.format(error=str(e)))
            return
        existing = read_public_key(SIGNING_KEY_FILE)
        if existing == key.public_hex:
            self._append_log(S.LOG_KIT_KEY_IMPORTED.format(fingerprint=fingerprint(existing)))
            return
        if existing or os.path.exists(SIGNING_KEY_FILE):
            reply = QMessageBox.question(
                self, S.MSG_CONFIRM,
                S.MSG_KIT_KEY_REPLACE_CONFIRM.format(fingerprint=fingerprint(existing) or "?"),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        try:
            backup = backup_existing(SIGNING_KEY_FILE)
            write_key_file(SIGNING_KEY_FILE, key)
        except OSError as e:
            QMessageBox.critical(self, S.MSG_ERROR, S.ERR_KIT_KEY_WRITE.format(error=str(e)))
            return
        if backup:
            self._append_log(S.LOG_KIT_KEY_REPLACED.format(path=backup))
        self._append_log(S.LOG_KIT_KEY_IMPORTED.format(fingerprint=fingerprint(key.public_hex)))
        self.refresh_signing_key()

    def publish_update(self):
        """Write and sign update.json for a new build. Uploads nothing."""
        try:
            key = read_key_file(SIGNING_KEY_FILE)
        except (OSError, ValueError):
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_KIT_NO_KEY)
            return
        fields = self.runtime_tab.publish_fields()
        config = self._current_config()
        app_name = build_name(config) if config.source or config.output_name else ""
        try:
            result = publish_update(
                fields["file"], fields["version"], fields["url"], key,
                notes=fields["notes"], min_version=fields["min_version"], app_name=app_name,
            )
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_KIT_PUBLISH_FMT.format(error=str(e)))
            return
        self._append_log(S.LOG_KIT_PUBLISHED.format(
            manifest=result.manifest_path, signature=result.signature_path
        ))
        QMessageBox.information(self, S.MSG_SUCCESS, S.MSG_KIT_PUBLISHED_FMT.format(
            manifest=result.manifest_path, signature=result.signature_path
        ))

    # ─── Windows Sandbox ────────────────────────────────────────────────

    def open_in_sandbox(self):
        """Run the last build on a clean Windows inside Windows Sandbox."""
        config = self._current_config()
        output = output_path_for(config) if config.source else ""
        if not output:
            QMessageBox.information(self, S.MSG_WARNING, S.MSG_SANDBOX_NO_BUILD)
            return
        if not sandbox_available():
            QMessageBox.information(
                self, S.MSG_WARNING, S.SANDBOX_UNAVAILABLE.format(path=output)
            )
            return
        host, exe = wsb_for_output(output, config.onefile)
        path = os.path.join(build_root(config), f"{build_name(config)}.wsb")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(generate_wsb(host, exe))
        except OSError as e:
            QMessageBox.critical(self, S.MSG_ERROR, str(e))
            return
        self._append_log(S.LOG_SANDBOX_WRITTEN.format(path=path))
        os.startfile(path)  # Windows only: guarded by sandbox_available() above

    # ─── Icon studio ────────────────────────────────────────────────────

    def open_icon_studio(self):
        source = self._source_path()
        name = self.main_tab.output_name.text().strip() or (
            os.path.splitext(os.path.basename(source))[0] if source else ""
        )
        start_dir = os.path.dirname(source) if source else ""
        dialog = IconStudioDialog(self, app_name=name, start_dir=start_dir)
        if dialog.exec_() and dialog.saved_path:
            self.main_tab.icon_input.setText(dialog.saved_path)
            self._append_log(
                S.LOG_ICON_STUDIO_SAVED.format(sizes="16–256", path=dialog.saved_path)
            )

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
        self.post_build_thread.smoke_signal.connect(
            lambda passed, output: self._on_smoke_result(config, passed, output)
        )
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

    # ─── Project file (p2e.toml) ────────────────────────────────────────

    def _build_menu(self):
        """The Project menu. Rebuilt on a language switch, like the widgets."""
        bar = self.menuBar()
        bar.clear()
        menu = bar.addMenu(S.MENU_PROJECT)

        def item(text, handler, keys=""):
            # The shortcut is shown in the menu but bound once, as a
            # QShortcut: binding it here too would make it ambiguous.
            action = QAction(f"{text}\t{keys}" if keys else text, self)
            action.triggered.connect(lambda _checked=False: handler())
            menu.addAction(action)
            return action

        self.new_project_action = item(S.MENU_NEW_PROJECT, self.new_project, "Ctrl+N")
        self.open_project_action = item(S.MENU_OPEN_PROJECT, self.open_project_dialog,
                                        "Ctrl+Shift+O")
        self.recent_menu = menu.addMenu(S.MENU_RECENT_PROJECTS)
        menu.addSeparator()
        self.save_project_action = item(S.MENU_SAVE_PROJECT, self.save_project, "Ctrl+S")
        self.save_as_action = item(S.MENU_SAVE_PROJECT_AS, self.save_project_as, "Ctrl+Shift+S")
        menu.addSeparator()
        self.init_project_action = item(S.MENU_INIT_PROJECT, self.init_project_from_script)
        self._refresh_recent_menu()

    def recent_projects(self):
        recent = self.settings.get("recent_projects", [])
        return [p for p in recent if isinstance(p, str)] if isinstance(recent, list) else []

    def _remember_project(self, path: str):
        path = os.path.abspath(path)
        recent = [p for p in self.recent_projects()
                  if os.path.normcase(p) != os.path.normcase(path)]
        self.settings["recent_projects"] = [path] + recent[: RECENT_PROJECTS_MAX - 1]
        self.save_settings()
        self._refresh_recent_menu()

    def _refresh_recent_menu(self):
        if not hasattr(self, "recent_menu"):
            return
        self.recent_menu.clear()
        recent = self.recent_projects()
        if not recent:
            empty = self.recent_menu.addAction(S.MENU_RECENT_EMPTY)
            empty.setEnabled(False)
            return
        for path in recent:
            action = self.recent_menu.addAction(path)
            action.triggered.connect(lambda _c=False, p=path: self.open_project_path(p))

    def _project_snapshot(self) -> dict:
        return self._current_project().to_settings_dict()

    def is_project_modified(self) -> bool:
        return self._saved_snapshot is not None and self._project_snapshot() != self._saved_snapshot

    def _mark_saved(self):
        self._saved_snapshot = self._project_snapshot()
        self._update_modified()

    def _watch_project_fields(self):
        """Re-check the unsaved-changes marker whenever any project field changes."""
        from PyQt5.QtWidgets import (
            QAbstractButton,
            QComboBox,
            QLineEdit,
            QListWidget,
            QPlainTextEdit,
            QSpinBox,
        )

        for tab in self._project_tabs:
            for widget in tab.findChildren(QLineEdit):
                widget.textChanged.connect(self._schedule_modified)
            for widget in tab.findChildren(QAbstractButton):
                if widget.isCheckable():
                    widget.toggled.connect(self._schedule_modified)
            for widget in tab.findChildren(QComboBox):
                widget.currentIndexChanged.connect(self._schedule_modified)
            for widget in tab.findChildren(QSpinBox):
                widget.valueChanged.connect(self._schedule_modified)
            for widget in tab.findChildren(QListWidget):
                if widget is not self.release_tab.steps_list:
                    model = widget.model()
                    model.rowsInserted.connect(self._schedule_modified)
                    model.rowsRemoved.connect(self._schedule_modified)
            for widget in tab.findChildren(QPlainTextEdit):
                if widget is not self.release_tab.notes_edit:
                    widget.textChanged.connect(self._schedule_modified)

    def _schedule_modified(self, *_args):
        if hasattr(self, "_modified_timer"):
            self._modified_timer.start()

    def _update_modified(self):
        if not hasattr(self, "release_tab"):
            return
        self.setWindowModified(bool(self.project_path) and self.is_project_modified())
        self.release_tab.show_mismatches(version_mismatches(self._current_project()))
        self._update_title()

    def _update_title(self):
        base = S.WINDOW_TITLE_FMT.format(name=APP_NAME, version=APP_VERSION)
        if self.project_path:
            name = self.project_name or (
                self._current_project().display_name() if hasattr(self, "release_tab") else ""
            ) or os.path.basename(os.path.dirname(self.project_path))
            # "[*]" is where Qt draws the unsaved-changes marker.
            self.setWindowTitle(S.WINDOW_TITLE_PROJECT_FMT.format(project=name, app=base))
        else:
            self.setWindowTitle(base)

    def _maybe_save_changes(self) -> bool:
        """Offer to save unsaved project changes. False means "cancel"."""
        if not self.project_path or not self.isVisible() or not self.is_project_modified():
            return True
        reply = QMessageBox.question(
            self, S.MSG_CONFIRM,
            S.MSG_PROJECT_UNSAVED.format(path=self.project_path),
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save,
        )
        if reply == QMessageBox.Cancel:
            return False
        if reply == QMessageBox.Save:
            return self.save_project()
        return True

    def _set_project(self, path: str, project: ProjectConfig):
        self.project_path = os.path.abspath(path) if path else ""
        self.project_name = project.name
        if path:
            self._remember_project(path)
        self._mark_saved()

    def new_project(self):
        """Start over with defaults and no project file."""
        if not self._maybe_save_changes():
            return
        password = self.deploy_tab.signing_password.text()
        self._apply_project(ProjectConfig())
        self.deploy_tab.signing_password.setText(password)
        self.release_tab.notes_edit.clear()
        self._set_project("", ProjectConfig())
        self._append_log(S.LOG_PROJECT_NEW)

    def open_project_dialog(self):
        start = os.path.dirname(self.project_path) if self.project_path else ""
        path, _ = QFileDialog.getOpenFileName(
            self, S.DIALOG_OPEN_PROJECT, start, S.DIALOG_FILTER_PROJECT
        )
        if path:
            self.open_project_path(path)

    def open_project_path(self, path: str) -> bool:
        """Open ``path`` — after the same checks as a shared settings file."""
        if not self._maybe_save_changes():
            return False
        try:
            loaded = load_project(path)
        except ProjectFileError as e:
            message = project_error_text(e)
            self._append_log(S.LOG_PROJECT_OPEN_FAIL.format(path=path, error=message))
            QMessageBox.critical(self, S.MSG_ERROR,
                                 S.ERR_PROJECT_OPEN.format(path=path, error=message))
            if e.code == "unreadable":
                self.settings["recent_projects"] = [
                    p for p in self.recent_projects() if p != path]
                self._refresh_recent_menu()
            return False
        # A project file is shared content: someone else may have written it.
        if not self._confirm_untrusted_config(loaded.project.build):
            self._append_log(S.LOG_SETTINGS_REJECTED.format(path=path))
            return False
        self._apply_project(loaded.project)
        self.release_tab.notes_edit.clear()
        self._set_project(loaded.path, loaded.project)
        for warning in loaded.warnings:
            self._append_log(S.LOG_PROJECT_WARNING.format(warning=warning))
        self._append_log(S.LOG_PROJECT_OPENED.format(path=loaded.path))
        return True

    def save_shortcut(self):
        """Ctrl+S: the project when one is open, otherwise a settings file."""
        if self.project_path:
            self.save_project()
        else:
            self.save_current_settings()

    def save_project(self) -> bool:
        if not self.project_path:
            return self.save_project_as()
        return self._write_project(self.project_path)

    def save_project_as(self) -> bool:
        source = self.main_tab.source_input.text().strip()
        start = self.project_path or (
            project_path_for_script(source) if source else PROJECT_FILE_NAME
        )
        path, _ = QFileDialog.getSaveFileName(
            self, S.DIALOG_SAVE_PROJECT, start, S.DIALOG_FILTER_PROJECT
        )
        if not path:
            return False
        return self._write_project(path)

    def _write_project(self, path: str) -> bool:
        project = self._current_project()
        try:
            written = save_project(project, path)
        except (OSError, TypeError, ValueError) as e:
            QMessageBox.critical(self, S.MSG_ERROR, S.ERR_SAVE_FAIL.format(error=str(e)))
            return False
        self._set_project(written, project)
        self._append_log(S.LOG_PROJECT_SAVED.format(path=written))
        return True

    def init_project_from_script(self):
        """Write a p2e.toml beside the script, from the current settings."""
        source = self.main_tab.source_input.text().strip()
        if not source or not os.path.isfile(source):
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_NO_SOURCE)
            return
        path = project_path_for_script(source)
        if os.path.exists(path):
            reply = QMessageBox.question(
                self, S.MSG_CONFIRM, S.MSG_PROJECT_OVERWRITE.format(path=path),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        current = self._current_project()
        version = current.version if is_semver(current.version) else ""
        project = new_project_for_script(source, current, version)
        if not project.release.repository:
            project.release.repository = remote_slug(os.path.dirname(path))
        self._apply_project(project)
        if self._write_project(path):
            self._append_log(S.LOG_PROJECT_INIT.format(path=path))

    # ─── Release ────────────────────────────────────────────────────────

    def apply_release_version(self):
        """Put the release tab's version into every tab that records one."""
        project = self._current_project()
        try:
            changes = apply_version(project, project.version)
        except ValueError:
            QMessageBox.warning(self, S.MSG_WARNING,
                                S.ERR_RELEASE_VERSION.format(version=project.version or "—"))
            return
        self._apply_project(project, ("project", "version_info", "installer", "build"))
        self._append_log(S.LOG_RELEASE_VERSION_APPLIED.format(
            version=project.version, count=len(changes)))

    def _release_cwd(self) -> str:
        if self.project_path:
            return os.path.dirname(self.project_path)
        source = self.main_tab.source_input.text().strip()
        return os.path.dirname(os.path.abspath(source)) if source else ""

    def draft_release_notes(self):
        cwd = self._release_cwd()
        notes = draft_notes(cwd, self.release_tab.tag_prefix.text().strip() or "v",
                            notes_titles()) if cwd else ""
        if not notes:
            self._append_log(S.LOG_RELEASE_NO_GIT)
            return
        self.release_tab.notes_edit.setPlainText(notes)

    def detect_release_repository(self):
        cwd = self._release_cwd()
        slug = remote_slug(cwd) if cwd else ""
        if slug:
            self.release_tab.repository.setText(slug)
        else:
            self._append_log(S.LOG_RELEASE_NO_REMOTE)

    def refresh_token_status(self):
        token = credentials.find_token(keyring_module=KEYRING)
        self.release_tab.show_token_status(token.source)

    def save_github_token(self):
        """Into the OS keyring — never the settings, the project or the log."""
        token = self.release_tab.token_input.text().strip()
        self.release_tab.token_input.clear()
        if not token:
            return
        try:
            credentials.store_token(token, KEYRING)
        except credentials.CredentialError as e:
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_TOKEN_STORE.format(error=str(e)))
            return
        self._append_log(S.LOG_TOKEN_SAVED)
        self.refresh_token_status()

    def forget_github_token(self):
        if credentials.delete_token(KEYRING):
            self._append_log(S.LOG_TOKEN_FORGOTTEN)
        self.refresh_token_status()

    def _release_context(self, project: ProjectConfig, dry_run: bool) -> ReleaseContext:
        tab = self.release_tab
        python = self.build_python(project.build)
        checker = self._installed_checker(project.build)

        def doctor(ctx):
            return examine(ctx.project.build.source, ctx.project.build, is_installed=checker)

        options = ReleaseOptions(
            version=project.version,
            notes=tab.notes_edit.toPlainText(),
            dry_run=dry_run,
            allow_doctor_errors=tab.allow_errors_check.isChecked(),
            create_tag=tab.create_tag_check.isChecked(),
            push_tag=tab.create_tag_check.isChecked() and tab.push_tag_check.isChecked(),
            publish=tab.publish_check.isChecked(),
            sign_password=self.deploy_tab.signing_password.text(),
            iscc_path=self.installer_tab.inst_iscc_path.text().strip(),
            signing_key_path=SIGNING_KEY_FILE,
            notes_titles=notes_titles(),
        )
        return ReleaseContext(
            project, options, project_path=self.project_path, python=python,
            doctor=doctor, texts=runtime_texts(), rtl=self._rtl(),
            token_provider=lambda: credentials.find_token(keyring_module=KEYRING),
        )

    def start_release(self):
        """Plan the release (a dry run); then, unless only a preview was asked
        for, confirm the full list of actions and run it."""
        if self._build_in_progress():
            QMessageBox.warning(self, S.MSG_WARNING, S.MSG_DIAG_BUSY)
            return
        project = self._current_project()
        if not is_semver(project.version):
            QMessageBox.warning(self, S.MSG_WARNING,
                                S.ERR_RELEASE_VERSION.format(version=project.version or "—"))
            return
        if not project.build.source or not os.path.isfile(project.build.source):
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_NO_SOURCE)
            return
        if project.build.isolated_env and not env_exists(self._env_dir(project.build.source)):
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_RELEASE_ENV)
            return
        self._release_after_plan = not self.release_tab.dry_run_check.isChecked()
        self._append_log(S.LOG_RELEASE_PLANNING.format(version=project.version))
        self._run_release(self._release_context(project, dry_run=True))

    def _run_release(self, context: ReleaseContext):
        self.release_tab.reset_steps()
        self.release_tab.set_running(True)
        self.release_tab.show_result("", bool(self._last_release_dir))
        self.convert_btn.setEnabled(False)
        self.release_thread = ReleaseThread(context)
        self.release_thread.log_signal.connect(self._append_log)
        self.release_thread.step_signal.connect(self.release_tab.show_step)
        self.release_thread.finished_signal.connect(self._on_release_finished)
        self.release_thread.start()

    def _on_release_finished(self, context, results):
        self.release_tab.set_running(False)
        self.convert_btn.setEnabled(True)
        if context.dry_run:
            if not self.release_tab.notes_edit.toPlainText().strip() and context.notes:
                # The drafted notes, ready to edit before anything is published.
                self.release_tab.notes_edit.setPlainText(context.notes)
            if has_blocking_problems(results):
                self.release_tab.show_result(S.RELEASE_RESULT_BLOCKED, False)
                QMessageBox.warning(self, S.MSG_WARNING, S.RELEASE_RESULT_BLOCKED)
                return
            if not self._release_after_plan:
                self.release_tab.show_result(S.RELEASE_RESULT_PLANNED, False)
                return
            dialog = ReleaseConfirmDialog(confirmation(results), context.version, self)
            if not dialog.exec_():
                self._append_log(S.LOG_RELEASE_CANCELLED)
                return
            self._append_log(S.LOG_RELEASE_STARTED.format(version=context.version))
            self._run_release(self._release_context(self._current_project(), dry_run=False))
            return

        self._last_release_dir = context.out_dir if os.path.isdir(context.out_dir) else ""
        version_step = results[0]
        if version_step.status == DONE and version_step.actions:
            # Show the bumped version everywhere; the pipeline saved the file.
            self._apply_project(context.project, ("project", "version_info", "installer",
                                                  "build"))
            if context.project_changed:
                self._mark_saved()
        if has_blocking_problems(results):
            self.release_tab.show_result(S.RELEASE_RESULT_FAILED, bool(self._last_release_dir))
            self._notify_build_result(False, context.tag)
            return
        text = S.RELEASE_RESULT_DONE.format(version=context.version, path=context.out_dir,
                                            url=context.release_url or "—")
        self.release_tab.show_result(text, bool(self._last_release_dir))
        self._append_log(text)
        self._notify_build_result(True, context.tag)

    def open_release_folder(self):
        if self._last_release_dir and os.path.isdir(self._last_release_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._last_release_dir))

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
            ("Ctrl+L", self.main_tab.clear_log),
            ("Ctrl+E", self.main_tab.export_log),
            ("Ctrl+S", self.save_shortcut),
            ("Ctrl+Shift+S", self.save_project_as),
            ("Ctrl+N", self.new_project),
            ("Ctrl+Shift+O", self.open_project_dialog),
            ("Ctrl+T", self.toggle_theme),
            ("F5", self.detect_imports_action),
            ("Ctrl+F", self.main_tab.log_search.setFocus),
            ("Ctrl+M", self.toggle_mode),
            # Zoom. Ctrl+= is bound too because reaching Ctrl++ on most
            # layouts means pressing shift, which many apps do not require.
            ("Ctrl++", self.zoom_in),
            ("Ctrl+=", self.zoom_in),
            ("Ctrl+-", self.zoom_out),
            ("Ctrl+0", self.zoom_reset),
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
        if ext == ".toml":
            self.open_project_path(path)
            return
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
        if not self._maybe_save_changes():
            event.ignore()
            return
        self.save_settings()
        if self._build_in_progress():
            reply = QMessageBox.question(
                self,
                S.MSG_CONFIRM,
                S.MSG_CLOSE_CONFIRM,
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return
            # Both threads spawn a child process; leaving either running
            # orphans a PyInstaller run after the window is gone.
            for thread in (
                self.conversion_thread, self.batch_thread, self.diagnostic_thread,
                self.env_thread,
            ):
                if thread and thread.isRunning():
                    thread.cancel()
                    thread.wait()
            if self.release_thread and self.release_thread.isRunning():
                self.release_thread.wait()

        self._cleanup_temp_files()
        self.tray.hide()
        event.accept()
