"""Main application window.

This module owns orchestration only: the build pipeline, the worker threads,
shortcuts, and the actions that span more than one tab. The tabs themselves
live in ``py2exe_gui.ui.tabs`` and own their own widgets — before that split
this file was ~1,900 lines and held every control in the application.
"""

import functools
import json
import os
import subprocess
import sys
import webbrowser

from py2exe_gui.bidi import ltr
from py2exe_gui.constants import (
    APP_VERSION,
    HISTORY_FILE,
    PRESETS_FILE,
    SETTINGS_FILE,
)
from py2exe_gui.core import (
    RELEASES_PAGE_URL,
    BuildConfig,
    BuildHistory,
    PresetLibrary,
    check_for_update,
    detect_imports,
    filter_non_stdlib,
    parse_requirements,
)
from py2exe_gui.core.project_file import (
    SECTIONS,
    ProjectConfig,
    sections_in,
    split_untrusted_flags,
    untrusted_flags,
)
from py2exe_gui.core.release import credentials

# The side navigation (2.1): six sections, in the order the work happens.
# Each holds one or more of the former tabs; "build" is one composed page.
# Worker classes, dialogs and core helpers the controller mixins
# (py2exe_gui/ui/controllers) reach through this module at call time, so one
# monkeypatch of ``py2exe_gui.ui.main_window.X`` covers every controller.
from py2exe_gui.core.release.pipeline import ReleaseOptions  # noqa: F401
from py2exe_gui.core.runtime_kit import (
    untrusted_risks,
)
from py2exe_gui.core.sandbox import sandbox_available  # noqa: F401
from py2exe_gui.core.update_signing import (
    read_public_key,
)
from py2exe_gui.core.venv_manager import find_uv  # noqa: F401
from py2exe_gui.icons import themed_icon
from py2exe_gui.paths import envs_dir, license_key_path, signing_key_path
from py2exe_gui.qt import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QKeySequence,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QShortcut,
    QSizePolicy,
    QSplitter,
    Qt,
    QTimer,
    QVBoxLayout,
    QWidget,
)
from py2exe_gui.strings import (
    LOCALE_LAYOUT,
    S,
    current_locale,
    set_locale,
)
from py2exe_gui.styles import (
    DEFAULT_FONT_SCALE,
    FONT_SCALE_STEP,
    PALETTES,
    clamp_scale,
    resolve_theme,
    themed_stylesheet,
)
from py2exe_gui.ui import streaming_thread
from py2exe_gui.ui.batch_thread import BatchThread  # noqa: F401
from py2exe_gui.ui.build_page import BuildPage
from py2exe_gui.ui.compare_thread import CompareThread  # noqa: F401
from py2exe_gui.ui.controllers.build import BuildController
from py2exe_gui.ui.controllers.doctor import DoctorController
from py2exe_gui.ui.controllers.environment import EnvironmentController
from py2exe_gui.ui.controllers.keys import KeysController
from py2exe_gui.ui.controllers.project import ProjectController
from py2exe_gui.ui.controllers.release import ReleaseController
from py2exe_gui.ui.conversion_thread import ConversionThread  # noqa: F401
from py2exe_gui.ui.diagnostic_thread import DiagnosticThread  # noqa: F401
from py2exe_gui.ui.dialogs import CommandPreviewDialog  # noqa: F401
from py2exe_gui.ui.env_thread import CommandThread, EnvThread, TaskThread  # noqa: F401
from py2exe_gui.ui.installer_thread import InstallerThread  # noqa: F401
from py2exe_gui.ui.navigation import SectionView
from py2exe_gui.ui.package_thread import PackageThread  # noqa: F401
from py2exe_gui.ui.post_build_thread import PostBuildThread  # noqa: F401
from py2exe_gui.ui.release_thread import ReleaseThread  # noqa: F401
from py2exe_gui.ui.tabs import (
    AboutTab,
    AdvancedTab,
    BatchTab,
    DeployTab,
    DoctorTab,
    HistoryTab,
    HomeTab,
    InstallerTab,
    MainTab,
    PlatformsTab,
    ReleaseTab,
    RuntimeTab,
    SettingsTab,
    SizeTab,
    TemplatesTab,
    VersionInfoTab,
)
from py2exe_gui.ui.tabs.base import em_width
from py2exe_gui.ui.tray import BuildTray
from py2exe_gui.ui.widgets import DropOverlay, NoticeBar

NAV_SECTIONS = ("projects", "build", "check", "distribute", "tools", "settings")
#: The former tabs that are sections of the Build page, with their titles.
BUILD_SECTIONS = ("advanced", "version_info", "deploy")
#: Height the log takes when it opens (the handle lets the person change it).
LOG_OPEN_HEIGHT = 220

# Where isolated build environments are created. A module global so tests can
# point it at a temporary folder.
ENVS_ROOT = envs_dir()

# The Runtime Kit's private update-signing key (per-user config folder).
# A module global for the same reason.
SIGNING_KEY_FILE = signing_key_path()
# 2.0: the private licence-signing key, kept the same way in its own file.
LICENSE_KEY_FILE = license_key_path()

# The OS keyring used for the GitHub token (``credentials.DEFAULT`` = the real
# ``keyring`` package, if installed). A module global so tests use a fake one.
KEYRING = credentials.DEFAULT
#: 2.0: the codesign identity for a macOS bundle (an environment variable, never a file).
MACOS_SIGN_ENV = "P2E_MACOS_SIGN_IDENTITY"

# Recent projects kept in the settings file.
RECENT_PROJECTS_MAX = 8

# Every part of a ProjectConfig a tab can apply.
ALL_SECTIONS = ("build", "project") + SECTIONS

# Wait this long after the last edit before re-examining the project, so the
# doctor does not re-parse the script on every keystroke in the path field.
DOCTOR_DEBOUNCE_MS = 500


class MainWindow(BuildController, EnvironmentController, ReleaseController, KeysController, ProjectController, DoctorController, QMainWindow):
    """النافذة الرئيسية للتطبيق."""

    def __init__(self):
        super().__init__()
        self.conversion_thread = None
        self.installer_thread = None
        self.post_build_thread = None
        self.batch_thread = None
        self.compare_thread = None
        self.diagnostic_thread = None
        self.env_thread = None
        # One-off commands (pip installs, pip freeze) and the update check.
        self.command_thread = None
        self.task_thread = None
        self.settings = {}
        self.current_theme = "dark"
        self.font_scale = DEFAULT_FONT_SCALE
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
        # Set by the person, for the next build only (Nuitka's downloads).
        self._allow_downloads_once = False
        self._size_view = None
        # The last comparison (rows, recommendation), re-rendered on a
        # language switch like the size lab.
        self._compare_view = None
        self._last_report_path = ""
        # The open project file ('' = none) and the state it was saved in,
        # for the window title's unsaved-changes marker.
        self.project_path = ""
        self.project_name = ""
        self._saved_snapshot = None
        self.release_thread = None
        self.package_thread = None
        self._last_packages_dir = ""
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
        self.init_ui()
        self._register_shortcuts()
        self.setAcceptDrops(True)
        self.tray = BuildTray(self, self.windowIcon())
        self.check_dependencies()
        self._refresh_history_list()
        self._refresh_presets_list()
        self.refresh_home()
        if not self.recent_projects():
            # Nothing to list yet: start where the first build is made.
            self.tabs.setCurrentWidget(self.main_tab)
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
        self._build_status_bar()

    def _apply_stylesheet(self):
        """Repaint the window for the active theme, locale and font scale."""
        self.setStyleSheet(
            themed_stylesheet(self.current_theme, current_locale(), self.font_scale)
        )
        self._apply_icons()

    # ── Icons ──────────────────────────────────────────────────────────────

    #: Former tab key → icon shown on its sub-tab.
    PAGE_ICONS = {
        "home": "home", "history": "history", "doctor": "doctor", "size": "size",
        "installer": "installer", "platforms": "platforms", "runtime": "runtime",
        "release": "release", "batch": "batch", "templates": "templates",
        "settings": "preferences", "about": "about",
    }

    def _icon(self, name: str, role: str = "text"):
        palette = PALETTES.get(self.current_theme) or PALETTES["dark"]
        rtl = LOCALE_LAYOUT.get(current_locale(), "rtl") == "rtl"
        return themed_icon(name, palette, role, rtl)

    def _apply_icons(self):
        """Colour every icon for the active theme (and mirror for RTL).

        Called after the stylesheet: icons are SVGs rendered in the palette's
        colours, so a theme change re-renders them like it recolours the CSS.
        """
        if not hasattr(self, "tabs"):
            return
        from py2exe_gui.qt import QTabWidget

        nav = self.tabs.nav
        for row, key in enumerate(self.tabs.sections()):
            nav.item(row).setIcon(self._icon(f"section_{key}"))
        for key, widget, _title in self._all_tabs:
            page = self.tabs.page_of(self._tab_sections[key])
            if isinstance(page, QTabWidget) and key in self.PAGE_ICONS:
                page.setTabIcon(page.indexOf(widget), self._icon(self.PAGE_ICONS[key]))
        self.convert_btn.setIcon(self._icon("start", "on_accent"))
        self.cancel_btn.setIcon(self._icon("stop", "on_accent"))
        self.preview_btn.setIcon(self._icon("preview"))
        self.open_folder_btn.setIcon(self._icon("open_folder"))
        for button in self.findChildren(QPushButton):
            name = button.property("iconName")
            if name:
                button.setIcon(self._icon(name, button.property("iconRole") or "text"))
        self.log_panel.set_chevrons(self._icon("chevron_down"), self._icon("chevron_up"))
        # Always "chevron_right": it is in icons.DIRECTIONAL, so _icon() already
        # mirrors it under RTL. Asking for chevron_left there mirrored twice.
        for section in self.build_page.sections.values():
            section.set_chevrons(self._icon("chevron_down"), self._icon("chevron_right"))
        for action, name in getattr(self, "_menu_icons", []):
            action.setIcon(self._icon(name))
        self.notice_bar.set_icons(
            {"info": self._icon("info", "accent"), "success": self._icon("ok", "success"),
             "warning": self._icon("warning", "warning")},
            close_icon=self._icon("close", "muted"),
        )
        from py2exe_gui.qt import QSize
        self.drop_overlay.set_icon(self._icon("import", "accent").pixmap(QSize(48, 48)))

    def _apply_layout_direction(self):
        self.setLayoutDirection(
            Qt.LayoutDirection.RightToLeft
            if LOCALE_LAYOUT.get(current_locale(), "rtl") == "rtl"
            else Qt.LayoutDirection.LeftToRight
        )

    def _build_central_widget(self) -> QWidget:
        """Side navigation | page bar, the pages, the log panel, the action bar.

        The header banner (86px repeating the title bar), the always-visible
        progress box (77px) and the row of six equal buttons are gone: what
        is left of the fixed chrome is one 40px page bar, the folded log
        (one line) and one 48px action bar.
        """
        self.home_tab = HomeTab(self)
        self.main_tab = MainTab(self, embedded=True)
        self.doctor_tab = DoctorTab(self)
        self.size_tab = SizeTab(self)
        self.runtime_tab = RuntimeTab(self)
        self.release_tab = ReleaseTab(self)
        self.platforms_tab = PlatformsTab(self)
        self.advanced_tab = AdvancedTab(self, embedded=True)
        self.version_info_tab = VersionInfoTab(self, embedded=True)
        self.deploy_tab = DeployTab(self, embedded=True)
        self.installer_tab = InstallerTab(self)
        self.batch_tab = BatchTab(self)
        self.templates_tab = TemplatesTab(self)
        self.history_tab = HistoryTab(self)
        self.settings_tab = SettingsTab(self)
        self.about_tab = AboutTab(self)
        # The log is built by the main tab (so the tab works alone) and shown
        # under every page here.
        self.log_panel = self.main_tab.log_panel

        # Every former tab, keyed, in reading order: this is the order
        # ``tabs.widget(i)`` follows, and the order the shortcuts list uses.
        self._all_tabs = (
            ("home", self.home_tab, S.TAB_HOME),
            ("history", self.history_tab, S.TAB_HISTORY),
            ("main", self.main_tab, S.TAB_MAIN),
            ("advanced", self.advanced_tab, S.BUILD_SECTION_FILES),
            ("version_info", self.version_info_tab, S.BUILD_SECTION_IDENTITY),
            ("deploy", self.deploy_tab, S.BUILD_SECTION_PRE_POST),
            ("doctor", self.doctor_tab, S.TAB_DOCTOR),
            ("size", self.size_tab, S.TAB_SIZE),
            ("installer", self.installer_tab, S.TAB_INSTALLER),
            ("platforms", self.platforms_tab, S.TAB_PLATFORMS),
            ("runtime", self.runtime_tab, S.TAB_RUNTIME),
            ("release", self.release_tab, S.TAB_RELEASE),
            ("batch", self.batch_tab, S.TAB_BATCH),
            ("templates", self.templates_tab, S.TAB_TEMPLATES),
            ("settings", self.settings_tab, S.TAB_SETTINGS),
            ("about", self.about_tab, S.TAB_ABOUT),
        )
        # Which section each former tab lives in.
        self._tab_sections = {
            "home": "projects", "history": "projects",
            "main": "build", "advanced": "build", "version_info": "build", "deploy": "build",
            "doctor": "check", "size": "check",
            "installer": "distribute", "platforms": "distribute",
            "runtime": "distribute", "release": "distribute",
            "batch": "tools", "templates": "tools",
            "settings": "settings", "about": "settings",
        }

        # The tabs that hold a part of the project, in the order they are read.
        self._project_tabs = (
            self.main_tab, self.advanced_tab, self.deploy_tab, self.size_tab,
            self.runtime_tab, self.version_info_tab, self.installer_tab, self.release_tab,
            self.platforms_tab,
        )

        self.build_page = BuildPage(
            self.main_tab,
            [
                ("advanced", S.BUILD_SECTION_FILES, self.advanced_tab, self._summary_files),
                ("version_info", S.BUILD_SECTION_IDENTITY, self.version_info_tab,
                 self._summary_identity),
                ("deploy", S.BUILD_SECTION_PRE_POST, self.deploy_tab, self._summary_pre_post),
            ],
            expanded=not bool(self.settings.get("simple_mode", True)),
        )
        self.build_page.set_expanded_keys(
            self.settings.get("build_sections", self.build_page.expanded_keys()))
        for section in self.build_page.sections.values():
            section.toggled.connect(self._remember_build_sections)

        self.tabs = SectionView()
        self._populate_tabs()
        self.tabs.sectionChanged.connect(self._on_section_changed)
        self.tabs.set_collapsed(bool(self.settings.get("nav_collapsed", False)))

        # ── The right-hand column: page bar, pages, log, actions ──
        column = QWidget()
        column_layout = QVBoxLayout(column)
        column_layout.setContentsMargins(0, 0, 0, 0)
        column_layout.setSpacing(0)
        column_layout.addWidget(self._create_page_bar())
        # A line under the page bar for "saved", "applied", "finished":
        # messages with nothing to decide are no longer modal dialogs.
        self.notice_bar = NoticeBar()
        column_layout.addWidget(self.notice_bar)
        # Pages above, log below, with a handle between them while the log is
        # open; folded, the log is one header line and the handle is locked.
        self.log_splitter = QSplitter(Qt.Orientation.Vertical)
        self.log_splitter.setObjectName("logSplitter")
        self.log_splitter.setChildrenCollapsible(False)
        self.log_splitter.addWidget(self.tabs.stack)
        self.log_panel.setParent(self.log_splitter)
        self.log_panel.setVisible(True)
        self.log_splitter.addWidget(self.log_panel)
        self.log_splitter.setStretchFactor(0, 1)
        self.log_splitter.setStretchFactor(1, 0)
        column_layout.addWidget(self.log_splitter, 1)
        self.log_panel.toggled.connect(self._on_log_toggled)
        self.log_panel.set_expanded(bool(self.settings.get("log_open", False)))
        self._on_log_toggled(self.log_panel.is_expanded())
        column_layout.addWidget(self._create_action_bar())

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.tabs.nav)
        layout.addWidget(column, 1)
        # Shown while a file is dragged over the window (see dragEnterEvent).
        self.drop_overlay = DropOverlay(central)
        self.drop_overlay.set_texts(S.DROP_TITLE, S.DROP_HINT)
        # The SectionView itself is not shown: its nav and stack are placed
        # separately so the log and action bar sit under the pages only.
        self.tabs.setParent(central)
        self.tabs.setVisible(False)

        self.settings_tab.set_theme(self.settings.get("theme", "dark"))
        self.settings_tab.set_font_scale(self.font_scale)

        # Re-examine whenever something the doctor's checks depend on changes.
        main = self.main_tab
        main.source_input.textChanged.connect(self._schedule_doctor)
        main.icon_input.textChanged.connect(self._schedule_doctor)
        main.windowed_check.toggled.connect(self._schedule_doctor)
        main.noconsole_check.toggled.connect(self._schedule_doctor)
        main.source_input.textChanged.connect(self._refresh_page_bar)
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
        self._refresh_page_bar()
        return central

    def _populate_tabs(self):
        """Register the six sections and place every former tab in one."""
        self.tabs.clear()
        titles = {
            "projects": S.SECTION_PROJECTS, "build": S.SECTION_BUILD, "check": S.SECTION_CHECK,
            "distribute": S.SECTION_DISTRIBUTE, "tools": S.SECTION_TOOLS,
            "settings": S.SECTION_SETTINGS,
        }
        for key in NAV_SECTIONS:
            if key == "build":
                self.tabs.add_section(key, titles[key], page=self.build_page)
            else:
                self.tabs.add_section(key, titles[key], tabbed=True)
        for key, widget, title in self._all_tabs:
            section = self._tab_sections[key]
            reveal = None
            if key in BUILD_SECTIONS:
                reveal = functools.partial(self.build_page.reveal, widget)
            self.tabs.add_page(section, widget, title, reveal=reveal)
        self.tabs.finish()

    def section_of(self, widget) -> str:
        """The navigation section a former tab lives in."""
        return self.tabs.section_of(widget)

    # ── Page bar ───────────────────────────────────────────────────────────

    def _create_page_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("pageBar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(16, 6, 16, 6)
        row.setSpacing(12)
        self.page_title = QLabel("")
        self.page_title.setObjectName("pageTitle")
        row.addWidget(self.page_title)
        self.page_file = QLabel("")
        self.page_file.setObjectName("pageFile")
        self.page_file.setTextFormat(Qt.TextFormat.PlainText)
        self.page_file.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        row.addWidget(self.page_file, 1)
        return bar

    def _on_section_changed(self, _key: str):
        self._refresh_page_bar()

    def _refresh_page_bar(self, *_args):
        if not hasattr(self, "page_title"):
            return
        self.page_title.setText(self.tabs.section_title(self.tabs.current_section()))
        source = self.main_tab.source_input.text().strip()
        self.page_file.setText(ltr(source) if source else S.PAGE_FILE_NONE)
        self.page_file.setToolTip(source)

    # ── Build page summaries ───────────────────────────────────────────────

    def _summary_files(self) -> str:
        files = len(self.advanced_tab.extra_files())
        imports = len(self.advanced_tab.hidden_imports())
        if not files and not imports:
            return S.BUILD_SUMMARY_NONE
        return S.BUILD_SUMMARY_FILES_FMT.format(files=ltr(str(files)), imports=ltr(str(imports)))

    def _summary_identity(self) -> str:
        info = self.version_info_tab.version_info()
        parts = [p for p in (info.product_name, info.file_version) if p]
        return ltr(" ".join(parts)) if parts else S.BUILD_SUMMARY_IDENTITY_NONE

    def _summary_pre_post(self) -> str:
        tab = self.deploy_tab
        enabled = []
        if tab.splash_input.text().strip():
            enabled.append(S.BUILD_SUMMARY_SPLASH)
        if tab.manifest_enable.isChecked():
            enabled.append(S.BUILD_SUMMARY_MANIFEST)
        if tab.signing_enable.isChecked():
            enabled.append(S.BUILD_SUMMARY_SIGNING)
        if tab.smoke_enable.isChecked():
            enabled.append(S.BUILD_SUMMARY_SMOKE)
        return S.LIST_SEPARATOR.join(enabled) if enabled else S.BUILD_SUMMARY_PRE_POST_NONE

    def _remember_build_sections(self, *_args):
        self.settings["build_sections"] = self.build_page.expanded_keys()
        if hasattr(self, "advanced_sections_action"):
            # Reflect, don't act: setChecked would otherwise fire the action's
            # handler and open every section because one opened.
            self.advanced_sections_action.blockSignals(True)
            self.advanced_sections_action.setChecked(self.build_page.any_expanded())
            self.advanced_sections_action.blockSignals(False)

    def set_advanced_sections_open(self, opened: bool):
        """Open or close every folded section of the Build page at once."""
        self.build_page.set_all_expanded(bool(opened))
        self._remember_build_sections()

    def _on_log_toggled(self, opened: bool):
        """Give the open log its share of the column; lock the handle when folded."""
        self._remember_log_open(opened)
        splitter = getattr(self, "log_splitter", None)
        if splitter is None:
            return
        handle = splitter.handle(1)
        if handle is not None:
            handle.setEnabled(bool(opened))
        total = max(splitter.height(), 1)
        if opened:
            log_height = min(max(LOG_OPEN_HEIGHT, int(total * 0.3)), max(total - 200, 120))
            splitter.setSizes([max(total - log_height, 1), log_height])
        else:
            header = self.log_panel.sizeHint().height()
            splitter.setSizes([max(total - header, 1), header])

    def _remember_log_open(self, opened: bool):
        self.settings["log_open"] = bool(opened)
        if hasattr(self, "show_log_action"):
            self.show_log_action.blockSignals(True)
            self.show_log_action.setChecked(bool(opened))
            self.show_log_action.blockSignals(False)

    def toggle_log_panel(self):
        self.log_panel.set_expanded(not self.log_panel.is_expanded())

    def toggle_nav(self):
        collapsed = not self.tabs.nav.is_collapsed()
        self.tabs.set_collapsed(collapsed)
        self.settings["nav_collapsed"] = collapsed

    # ── Action bar ─────────────────────────────────────────────────────────

    def _create_action_bar(self) -> QWidget:
        """One primary action, two quiet ones, and the progress of a build.

        Build and Cancel share one slot: only one of them is ever shown. The
        progress bar appears when a build starts and names its stage.
        """
        bar = QFrame()
        bar.setObjectName("actionBar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(12, 6, 12, 6)
        row.setSpacing(8)

        def action(text, handler, object_name="", primary=False):
            button = QPushButton(text)
            if object_name:
                button.setObjectName(object_name)
            button.setMinimumHeight(36)
            button.setAccessibleName(text)
            if primary:
                # Sized by the stylesheet (QPushButton[primary="true"]) so
                # Ctrl+= scales it with the rest of the window.
                button.setProperty("primary", "true")
                button.setMinimumWidth(em_width(button, 14))
            button.clicked.connect(handler)
            row.addWidget(button)
            return button

        self.convert_btn = action(
            S.BTN_CONVERT, self.start_conversion, "successBtn", primary=True
        )
        self.cancel_btn = action(S.BTN_CANCEL, self.cancel_conversion, "dangerBtn", primary=True)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setVisible(False)
        self.preview_btn = action(S.BTN_PREVIEW_CMD, self.preview_command, "flatBtn")
        self.open_folder_btn = action(S.BTN_OPEN_FOLDER, self.open_output_folder, "flatBtn")
        row.addStretch(1)

        # The stage reads beside the bar, not across it: text over a half
        # filled bar was two colours at once.
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("progressLabel")
        self.progress_label.setVisible(False)
        row.addWidget(self.progress_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("buildProgress")
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(S.PROGRESS_READY)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedWidth(em_width(self.progress_bar, 16))
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setAccessibleName(S.PROGRESS_READY)
        self.progress_bar.setVisible(False)
        self.progress_bar.valueChanged.connect(self._refresh_progress_label)
        row.addWidget(self.progress_bar)
        return bar

    def _refresh_progress_label(self, *_args):
        """Mirror the bar's format (stage + percentage) into the label.

        The percentage is rendered here rather than by the bar: Qt's "%p%"
        inside a right-to-left paragraph came out as "%42". The number is
        isolated so it reads "42%" in both directions.
        """
        if hasattr(self, "progress_label"):
            text = self.progress_text()
            self.progress_label.setText(text)
            self.progress_label.setVisible(self.progress_bar.isVisibleTo(self))
            self.progress_bar.setAccessibleName(text)

    def progress_text(self) -> str:
        """The bar's format with ``%p%`` replaced by an isolated percentage."""
        bar = self.progress_bar
        text = bar.format()
        if "%p%" not in text:
            return text
        span = bar.maximum() - bar.minimum()
        if span <= 0:  # busy (0, 0): no percentage to show
            return text.replace("%p%", "").rstrip(" —-–")
        percent = round((bar.value() - bar.minimum()) * 100 / span)
        return text.replace("%p%", ltr(f"{percent}%"))

    # ── Busy state ─────────────────────────────────────────────────────────

    def _set_busy(self, text: str):
        """Show an indeterminate bar labelled ``text`` while a task runs.

        The environment, the diagnostic run and the comparison used to set
        the bar's range to (0, 0) and nothing else; the bar was hidden, so
        nothing moved on screen for minutes.
        """
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat(text)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self._refresh_progress_label()
        self.set_status(text)

    def _clear_busy(self):
        """Back to the idle bar: hidden, determinate, "ready"."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(S.PROGRESS_READY)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self._refresh_progress_label()
        self.set_status(S.STATUS_READY)

    def thread_error_text(self, code: str, tool: str = "", thread=None) -> str:
        """A worker's outcome code in the active locale.

        Threads report ``streaming_thread`` codes, never sentences; ``tool``
        names the program for the sentence and ``thread`` supplies the exit
        code or the OS error it kept.
        """
        tool = tool or "?"
        if code == streaming_thread.CANCELLED:
            return S.THREAD_ERR_CANCELLED
        if code == streaming_thread.NOT_FOUND:
            return S.THREAD_ERR_NOT_FOUND_FMT.format(tool=tool)
        if code == streaming_thread.TIMED_OUT:
            return S.THREAD_ERR_TIMED_OUT_FMT.format(tool=tool)
        if code == streaming_thread.ERROR:
            return S.THREAD_ERR_ERROR_FMT.format(
                tool=tool, error=getattr(thread, "error", "") or "?")
        if code == streaming_thread.FAILED:
            return S.THREAD_ERR_FAILED_FMT.format(
                tool=tool, code=getattr(thread, "returncode", None))
        return code

    # ── Status bar ─────────────────────────────────────────────────────────

    def _build_status_bar(self):
        """What is happening now; the copyright moved to About."""
        bar = self.statusBar()
        if not hasattr(self, "status_versions"):
            self.status_versions = QLabel("")
            self.status_versions.setObjectName("statusVersions")
            bar.addPermanentWidget(self.status_versions)
        bar.showMessage(S.STATUS_READY)

    def set_status(self, text: str):
        self.statusBar().showMessage(text)

    def notify(self, text: str, level: str = "info", timeout_ms=None):
        """Say ``text`` in the notice bar (no dialog to dismiss)."""
        self.notice_bar.show_message(text, level, timeout_ms)

    # ─── Startup checks ─────────────────────────────────────────────────

    def check_dependencies(self):
        self._append_log(S.LOG_CHECKING_DEPS)
        python_version, engine_version = "", ""
        try:
            result = subprocess.run(
                [sys.executable, "--version"], capture_output=True, text=True
            )
            python_version = result.stdout.strip()
            self._append_log(S.LOG_PYTHON_FOUND.format(version=python_version))
        except OSError:
            self._append_log(S.LOG_PYTHON_MISSING)

        try:
            result = subprocess.run(
                [sys.executable, "-m", "PyInstaller", "--version"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                engine_version = result.stdout.strip()
                self._append_log(
                    S.LOG_PYINSTALLER_FOUND.format(version=engine_version)
                )
            else:
                self._append_log(S.LOG_PYINSTALLER_MISSING)
        except OSError:
            self._append_log(S.LOG_PYINSTALLER_MISSING)

        if hasattr(self, "status_versions"):
            python_short = python_version.replace("Python", "").strip()
            engine_short = f"PyInstaller {engine_version}" if engine_version else ""
            self.status_versions.setText(ltr(S.STATUS_VERSIONS_FMT.format(
                python=python_short or "?", engine=engine_short or "—")))
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
        self.notify(S.MSG_SAVED_OK, "success")

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
        self.notify(S.MSG_LOADED_OK, "success")

    def _confirm_untrusted_config(self, config: BuildConfig) -> bool:
        """Ask before applying a config that would make PyInstaller run code.

        A settings file is shareable, and flags like ``--runtime-hook`` inject
        code into every EXE the build produces. The user needs to see that
        before it silently becomes part of a signed binary.
        """
        flags, outside = split_untrusted_flags(untrusted_flags(config))
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
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return False
        if outside:
            # Paths outside the project copy this machine's files into the EXE.
            reply = QMessageBox.question(
                self,
                S.MSG_CONFIRM,
                S.MSG_UNTRUSTED_EXTRA_FILES_CONFIRM.format(
                    files="\n".join(f"  • {f}" for f in outside)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
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
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

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

    # ─── Log / theme / locale ───────────────────────────────────────────

    def _append_log(self, line: str):
        """Append a single line to the log, coloured for the active theme."""
        self.log_panel.append_log(line, theme=self.current_theme)

    def export_log(self):
        self.log_panel.export_log()

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
        if hasattr(self, "settings_tab"):
            self.settings_tab.set_theme(theme)
        self._check_theme_action(theme)
        self.refresh_home()
        self._append_log(S.LOG_THEME_CHANGED.format(theme=theme))

    def _on_theme_changed(self, index=None):
        """Handler for the Settings page's theme selector."""
        selected = self.settings_tab.selected_theme()
        if selected != self.settings.get("theme"):
            self.apply_theme(selected)

    def _check_theme_action(self, theme: str):
        for action in getattr(self, "theme_actions", {}).values():
            action.setChecked(action.data() == theme)

    def _repaint_log(self):
        """Re-render buffered log lines in the new theme's palette.

        Log colours are baked into the HTML at append time, so a theme change
        leaves earlier lines in the old palette — which is exactly the bug the
        light theme's log had before per-theme palettes existed.
        """
        self.log_panel.set_theme(self.current_theme)

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
        if hasattr(self, "settings_tab"):
            self.settings_tab.set_font_scale(new_scale)
        self._append_log(S.LOG_ZOOM_FMT.format(percent=round(new_scale * 100)))

    def run_startup_tasks(self):
        """Anything that blocks, run after the window is visible.

        Called by ``app.main`` rather than from ``__init__`` so that
        constructing a MainWindow stays non-blocking and testable. The
        first-run mode dialog is gone with the modes (2.1); the Build page's
        folded sections do its job without asking.
        """
        self.settings.setdefault("welcomed", True)
        self._maybe_check_for_updates()

    # ── Update check ───────────────────────────────────────────────────────

    def _maybe_check_for_updates(self):
        """Check on startup only if the user opted in — never by default.

        A packaging tool that phones home unasked is not what anyone installed;
        the setting defaults to off and the manual button is always available.
        """
        if self.settings.get("check_updates_on_start"):
            self.check_for_updates(interactive=False)

    def check_for_updates(self, interactive: bool = True):
        """Look for a newer release. Reports only — nothing is downloaded.

        The network call runs on a worker: a slow or absent connection used
        to freeze the window for the whole timeout.
        """
        if self.task_thread is not None and self.task_thread.isRunning():
            return
        self._append_log(S.LOG_UPDATE_CHECKING)
        self.set_status(S.BUSY_UPDATE_CHECK)
        self.task_thread = TaskThread(lambda: check_for_update(APP_VERSION))
        self.task_thread.finished_signal.connect(
            lambda info, error: self._on_update_checked(info, error, interactive)
        )
        self.task_thread.start()

    def _on_update_checked(self, info, error: str, interactive: bool):
        self.set_status(S.STATUS_READY)
        if error:
            self._append_log(error)
            info = None
        if info is None:
            self._append_log(S.LOG_UPDATE_NONE.format(version=APP_VERSION))
            if interactive:
                self.notify(S.UPDATE_NONE, "info")
            return

        self._append_log(S.LOG_UPDATE_AVAILABLE.format(version=info.version, url=info.url))
        reply = QMessageBox.question(
            self,
            S.MSG_INFO_TITLE,
            S.UPDATE_AVAILABLE_FMT.format(version=info.version, current=APP_VERSION),
            QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Close,
            QMessageBox.StandardButton.Close,
        )
        if reply == QMessageBox.StandardButton.Open:
            webbrowser.open(info.url or RELEASES_PAGE_URL)

    def _on_language_changed(self, index):
        """Switch locale and rebuild the UI in place."""
        code = self.settings_tab.language_combo.itemData(index)
        self.set_language(code)

    def set_language(self, code: str):
        """Switch the UI language (from the Settings page or the View menu)."""
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
        log_lines = self.log_panel.log_lines()
        log_open = self.log_panel.is_expanded()
        batch_sources = self.batch_tab.sources()
        publish_fields = self.runtime_tab.publish_fields()
        current = self.tabs.currentWidget()
        # The widgets are rebuilt below, so remember the page by key.
        current_key = next((k for k, w, _t in self._all_tabs if w is current), "")
        status = self.statusBar().currentMessage()
        versions = self.status_versions.text()

        set_locale(locale_code)
        self._apply_layout_direction()
        self.setStyleSheet(
            themed_stylesheet(self.current_theme, locale_code, self.font_scale)
        )
        self.setCentralWidget(self._build_central_widget())
        self._build_menu()
        self._build_status_bar()
        self.status_versions.setText(versions)
        if status and status != S.STATUS_READY:
            self.set_status(status)

        # Rebuilding the widgets loses nothing: the project model carries the
        # form across (before 1.6 the deploy and installer tabs were reset).
        self._apply_project(project)
        self.deploy_tab.signing_password.setText(password)
        self.release_tab.notes_edit.setPlainText(notes)
        if not modified:
            self._saved_snapshot = self._project_snapshot()
        self._update_modified()

        self.log_panel.restore_log(log_lines)
        self.log_panel.set_expanded(log_open)
        self.main_tab.refresh_icon_preview()
        self._refresh_doctor_view()
        self._refresh_size_view()
        self.refresh_env_view()
        self.size_tab.set_report_path(self._last_report_path)
        self.batch_tab.set_sources(batch_sources)
        self.runtime_tab.set_publish_fields(publish_fields)
        self.refresh_signing_key()
        self.refresh_runtime_preview()
        self._refresh_history_list()
        self._refresh_presets_list()
        self.refresh_home()
        self._register_shortcuts()
        for key, widget, _title in self._all_tabs:
            if key == current_key:
                self.tabs.setCurrentWidget(widget)
        self._refresh_page_bar()

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
            ("Ctrl+L", self.log_panel.clear_log),
            ("Ctrl+E", self.log_panel.export_log),
            ("Ctrl+S", self.save_shortcut),
            ("Ctrl+Shift+S", self.save_project_as),
            ("Ctrl+N", self.new_project),
            ("Ctrl+Shift+O", self.open_project_dialog),
            ("Ctrl+T", self.toggle_theme),
            ("F5", self.detect_imports_action),
            ("F1", self.show_shortcuts),
            ("Ctrl+F", self.focus_log_search),
            ("Ctrl+`", self.toggle_log_panel),
            ("Ctrl+,", lambda: self.tabs.setCurrentWidget(self.settings_tab)),
            # Zoom. Ctrl+= is bound too because reaching Ctrl++ on most
            # layouts means pressing shift, which many apps do not require.
            ("Ctrl++", self.zoom_in),
            ("Ctrl+=", self.zoom_in),
            ("Ctrl+-", self.zoom_out),
            ("Ctrl+0", self.zoom_reset),
        ]
        for number, key in enumerate(NAV_SECTIONS, start=1):
            bindings.append((f"Ctrl+{number}", lambda k=key: self.tabs.set_current_section(k)))
        for sequence, slot in bindings:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(slot)
            self._shortcuts.append(shortcut)

    def focus_log_search(self):
        """Ctrl+F: open the log if it is folded, then focus its search box."""
        self.log_panel.set_expanded(True)
        self.log_panel.log_search.setFocus()

    # ─── Drag & drop ────────────────────────────────────────────────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drop_overlay.cover(self.centralWidget())
            self.drop_overlay.show()

    def dragLeaveEvent(self, event):
        self.drop_overlay.hide()
        super().dragLeaveEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, "drop_overlay", None) is not None and self.drop_overlay.isVisible():
            self.drop_overlay.cover(self.centralWidget())

    def dropEvent(self, event):
        self.drop_overlay.hide()
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
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            # Every worker spawns a child process or writes files; leaving
            # one running orphans a PyInstaller run after the window is gone.
            for thread in self._running_threads():
                cancel = getattr(thread, "cancel", None)
                if cancel is not None:
                    cancel()
                thread.wait()

        self._cleanup_temp_files()
        self.tray.hide()
        event.accept()
