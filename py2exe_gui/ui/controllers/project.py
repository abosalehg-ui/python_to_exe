"""ProjectController: The project file, the projects workspace, presets, history and templates.

A mixin of MainWindow (py2exe_gui/ui/main_window.py). The window module's
constants and worker classes are read through ``_mw`` at call time so a test
that patches ``py2exe_gui.ui.main_window.X`` reaches this code too.
"""

import json
import os

from py2exe_gui.constants import (
    APP_NAME,
    APP_VERSION,
)
from py2exe_gui.core.project_file import (
    PROJECT_FILE_NAME,
    ProjectConfig,
    ProjectFileError,
    load_project,
    new_project_for_script,
    project_path_for_script,
    save_project,
)
from py2exe_gui.core.release.git import remote_slug
from py2exe_gui.core.release.versioning import is_semver, version_mismatches
from py2exe_gui.core.workspace import summarize_projects
from py2exe_gui.qt import (
    QAction,
    QActionGroup,
    QMessageBox,
)
from py2exe_gui.strings import (
    S,
    available_locales,
    current_locale,
)
from py2exe_gui.styles import (
    PALETTES,
)
from py2exe_gui.templates import TEMPLATES, template_name
from py2exe_gui.texts import project_error_text

# The side navigation (2.1): six sections, in the order the work happens.
# Each holds one or more of the former tabs; "build" is one composed page.
from py2exe_gui.ui import main_window as _mw  # noqa: E402 - late, see docstring
from py2exe_gui.ui.dialogs import (
    PresetNameDialog,
    ShortcutsDialog,
)
from py2exe_gui.ui.tabs.settings_tab import THEME_LABEL_KEYS


class ProjectController:
    # ─── Project file (p2e.toml) ────────────────────────────────────────

    def _build_menu(self):
        """Project, View, Tools and Help. Rebuilt on a language switch.

        Until 2.1 there was one menu; the theme, the language and the font
        size were reachable only from the bottom of the Templates tab or by
        shortcuts nobody could discover from the window.
        """
        bar = self.menuBar()
        bar.clear()
        # Kept on self: PySide6 6.10 hands the new menu to Python, and an
        # unreferenced one is deleted with its wrapper (6.12 and PyQt5 leave
        # it with the bar). A reference is harmless on every binding.
        self._menu_actions = []

        self._menu_icons = []

        def item(menu, text, handler, keys="", checkable=False, checked=False, icon=""):
            # The shortcut is shown in the menu but bound once, as a
            # QShortcut: binding it here too would make it ambiguous.
            action = QAction(f"{text}\t{keys}" if keys else text, self)
            if icon:
                self._menu_icons.append((action, icon))
            if checkable:
                action.setCheckable(True)
                action.setChecked(bool(checked))
                action.toggled.connect(lambda on: handler(on))
            else:
                action.triggered.connect(lambda _checked=False: handler())
            menu.addAction(action)
            self._menu_actions.append(action)
            return action

        # ── Project ──
        self.project_menu = menu = bar.addMenu(S.MENU_PROJECT)
        self.new_project_action = item(menu, S.MENU_NEW_PROJECT, self.new_project, "Ctrl+N",
                                       icon="file_text")
        self.open_project_action = item(menu, S.MENU_OPEN_PROJECT, self.open_project_dialog,
                                        "Ctrl+Shift+O", icon="open_folder")
        self.recent_menu = menu.addMenu(S.MENU_RECENT_PROJECTS)
        menu.addSeparator()
        self.save_project_action = item(menu, S.MENU_SAVE_PROJECT, self.save_project, "Ctrl+S",
                                        icon="save")
        self.save_as_action = item(menu, S.MENU_SAVE_PROJECT_AS, self.save_project_as,
                                   "Ctrl+Shift+S", icon="save")
        menu.addSeparator()
        self.init_project_action = item(menu, S.MENU_INIT_PROJECT, self.init_project_from_script)
        self._refresh_recent_menu()

        # ── View ──
        self.view_menu = view = bar.addMenu(S.MENU_VIEW)
        self.theme_menu = view.addMenu(S.MENU_THEME)
        self.theme_actions = {}
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        stored_theme = self.settings.get("theme", "dark")
        for code, label_key in THEME_LABEL_KEYS:
            action = QAction(getattr(S, label_key), self)
            action.setCheckable(True)
            action.setData(code)
            action.setChecked(code == stored_theme)
            action.triggered.connect(lambda _c=False, c=code: self.apply_theme(c))
            theme_group.addAction(action)
            self.theme_menu.addAction(action)
            self.theme_actions[code] = action
        self._menu_actions.append(theme_group)
        self.language_menu = view.addMenu(S.MENU_LANGUAGE)
        self.language_actions = {}
        language_group = QActionGroup(self)
        language_group.setExclusive(True)
        for code, native in available_locales().items():
            action = QAction(native, self)
            action.setCheckable(True)
            action.setData(code)
            action.setChecked(code == current_locale())
            action.triggered.connect(lambda _c=False, c=code: self.set_language(c))
            language_group.addAction(action)
            self.language_menu.addAction(action)
            self.language_actions[code] = action
        self._menu_actions.append(language_group)
        view.addSeparator()
        item(view, S.MENU_ZOOM_IN, self.zoom_in, "Ctrl++", icon="zoom_in")
        item(view, S.MENU_ZOOM_OUT, self.zoom_out, "Ctrl+-", icon="zoom_out")
        item(view, S.MENU_ZOOM_RESET, self.zoom_reset, "Ctrl+0")
        view.addSeparator()
        self.show_log_action = item(
            view, S.MENU_SHOW_LOG, self.log_panel.set_expanded, "Ctrl+`",
            checkable=True, checked=self.log_panel.is_expanded(), icon="log")
        self.advanced_sections_action = item(
            view, S.MENU_ADVANCED_SECTIONS, self.set_advanced_sections_open,
            checkable=True, checked=self.build_page.any_expanded())
        self.collapse_nav_action = item(
            view, S.MENU_COLLAPSE_NAV, lambda on: self._set_nav_collapsed(on),
            checkable=True, checked=self.tabs.nav.is_collapsed())
        view.addSeparator()
        item(view, S.MENU_SETTINGS,
             lambda: self.tabs.setCurrentWidget(self.settings_tab), "Ctrl+,",
             icon="section_settings")

        # ── Tools ──
        self.tools_menu = tools = bar.addMenu(S.MENU_TOOLS)
        item(tools, S.MENU_DETECT_IMPORTS, self.detect_imports_action, "F5", icon="detect")
        item(tools, S.MENU_IMPORT_REQUIREMENTS, self.import_requirements_file, icon="import")
        tools.addSeparator()
        item(tools, S.MENU_PREVIEW_COMMAND, self.preview_command, "Ctrl+P", icon="preview")
        item(tools, S.MENU_OPEN_OUTPUT, self.open_output_folder, icon="open_folder")
        item(tools, S.MENU_ICON_STUDIO, self.open_icon_studio, icon="icon_studio")
        tools.addSeparator()
        item(tools, S.MENU_BATCH, lambda: self.tabs.setCurrentWidget(self.batch_tab),
             icon="batch")
        item(tools, S.MENU_CHECK_UPDATES, self.check_for_updates, icon="update")

        # ── Help ──
        self.help_menu = help_menu = bar.addMenu(S.MENU_HELP)
        item(help_menu, S.MENU_SHORTCUTS, self.show_shortcuts, "F1", icon="keyboard")
        item(help_menu, S.MENU_ABOUT, lambda: self.tabs.setCurrentWidget(self.about_tab),
             icon="about")
        self._apply_icons()

    def _set_nav_collapsed(self, collapsed: bool):
        self.tabs.set_collapsed(bool(collapsed))
        self.settings["nav_collapsed"] = bool(collapsed)

    def shortcut_table(self):
        """(keys, description) for every binding, for the Help dialog."""
        rows = [
            ("Ctrl+O", S.SHORTCUT_OPEN_SOURCE),
            ("Ctrl+B", S.SHORTCUT_BUILD),
            ("Ctrl+Shift+B", S.SHORTCUT_CANCEL),
            ("Ctrl+P", S.SHORTCUT_PREVIEW),
            ("F5", S.SHORTCUT_DETECT),
            ("Ctrl+N", S.SHORTCUT_NEW),
            ("Ctrl+Shift+O", S.SHORTCUT_OPEN_PROJECT),
            ("Ctrl+S", S.SHORTCUT_SAVE),
            ("Ctrl+Shift+S", S.SHORTCUT_SAVE_AS),
            ("Ctrl+`", S.SHORTCUT_TOGGLE_LOG),
            ("Ctrl+F", S.SHORTCUT_FIND_LOG),
            ("Ctrl+L", S.SHORTCUT_CLEAR_LOG),
            ("Ctrl+E", S.SHORTCUT_EXPORT_LOG),
            ("Ctrl+T", S.SHORTCUT_THEME),
            ("Ctrl++ / Ctrl+=", S.SHORTCUT_ZOOM_IN),
            ("Ctrl+-", S.SHORTCUT_ZOOM_OUT),
            ("Ctrl+0", S.SHORTCUT_ZOOM_RESET),
        ]
        for number, key in enumerate(_mw.NAV_SECTIONS, start=1):
            rows.append((f"Ctrl+{number}", S.SHORTCUT_SECTION_FMT.format(
                section=self.tabs.section_title(key))))
        return rows

    def show_shortcuts(self):
        ShortcutsDialog(self.shortcut_table(), parent=self).exec()

    def recent_projects(self):
        recent = self.settings.get("recent_projects", [])
        return [p for p in recent if isinstance(p, str)] if isinstance(recent, list) else []

    def _remember_project(self, path: str):
        path = os.path.abspath(path)
        recent = [p for p in self.recent_projects()
                  if os.path.normcase(p) != os.path.normcase(path)]
        self.settings["recent_projects"] = [path] + recent[: _mw.RECENT_PROJECTS_MAX - 1]
        self.save_settings()
        self._refresh_recent_menu()
        self.refresh_home()

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

    # ─── Home: the projects workspace (2.0) ─────────────────────────────

    def refresh_home(self):
        """Rebuild the project cards from the recent list and the history.

        Cheap enough to call after every event that changes what they show:
        a project opened or saved, a build or a release finished, a theme or
        language switch (the cards are rebuilt with the new strings).
        """
        if not hasattr(self, "home_tab"):
            return
        summaries = summarize_projects(self.recent_projects(), self.history.records)
        colors = PALETTES.get(self.current_theme) or PALETTES["dark"]
        self.home_tab.show_projects(summaries, self.project_path, colors)

    def _ensure_project_open(self, path: str) -> bool:
        """Open ``path`` unless it is already the project in the form."""
        if self.project_path and os.path.normcase(os.path.normpath(path)) == os.path.normcase(
                os.path.normpath(self.project_path)):
            return True
        return self.open_project_path(path)

    def build_project(self, path: str):
        """From a card: open the project and run the Convert button's build."""
        if self._build_in_progress():
            QMessageBox.warning(self, S.MSG_WARNING, S.MSG_DIAG_BUSY)
            return
        if not self._ensure_project_open(path):
            return
        self._append_log(S.LOG_HOME_BUILD.format(path=path))
        self.tabs.setCurrentWidget(self.main_tab)
        self.start_conversion()

    def release_project(self, path: str):
        """From a card: open the project and start the Release tab's release
        (the dry run, then the confirmation, exactly as from that tab)."""
        if self._build_in_progress():
            QMessageBox.warning(self, S.MSG_WARNING, S.MSG_DIAG_BUSY)
            return
        if not self._ensure_project_open(path):
            return
        self._append_log(S.LOG_HOME_RELEASE.format(path=path))
        self.tabs.setCurrentWidget(self.release_tab)
        self.start_release()

    def forget_project(self, path: str):
        """Drop ``path`` from the recent list (the file itself is not touched)."""
        key = os.path.normcase(os.path.normpath(path))
        self.settings["recent_projects"] = [
            p for p in self.recent_projects() if os.path.normcase(os.path.normpath(p)) != key]
        self.save_settings()
        self._refresh_recent_menu()
        self.refresh_home()
        self._append_log(S.LOG_HOME_FORGOTTEN.format(path=path))

    def _project_snapshot(self) -> dict:
        return self._current_project().to_settings_dict()

    def is_project_modified(self) -> bool:
        return self._saved_snapshot is not None and self._project_snapshot() != self._saved_snapshot

    def _mark_saved(self):
        self._saved_snapshot = self._project_snapshot()
        self._update_modified()

    def _watch_project_fields(self):
        """Re-check the unsaved-changes marker whenever any project field changes."""
        from py2exe_gui.qt import (
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
        if hasattr(self, "build_page"):
            self.build_page.refresh_summaries()

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
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Save,
        )
        if reply == QMessageBox.StandardButton.Cancel:
            return False
        if reply == QMessageBox.StandardButton.Save:
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
        path, _ = _mw.QFileDialog.getOpenFileName(
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
                self.refresh_home()
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
        path, _ = _mw.QFileDialog.getSaveFileName(
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
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        current = self._current_project()
        version = current.version if is_semver(current.version) else ""
        project = new_project_for_script(source, current, version)
        if not project.release.repository:
            project.release.repository = remote_slug(os.path.dirname(path))
        self._apply_project(project)
        if self._write_project(path):
            self._append_log(S.LOG_PROJECT_INIT.format(path=path))

    # ─── Presets ────────────────────────────────────────────────────────

    def _refresh_presets_list(self):
        if hasattr(self, "templates_tab"):
            self.templates_tab.refresh_presets(self.presets)

    def save_current_preset(self):
        """Store the current form under a name the user chooses."""
        dialog = PresetNameDialog(self, initial=self.main_tab.output_name.text().strip())
        if not dialog.exec():
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
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
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
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if self.presets.delete(name):
            self._refresh_presets_list()
            self._append_log(S.PRESET_DELETED_FMT.format(name=name))

    def export_presets(self):
        if len(self.presets) == 0:
            return
        file_path, _ = _mw.QFileDialog.getSaveFileName(
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
        file_path, _ = _mw.QFileDialog.getOpenFileName(
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
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if not self.history.clear():
            self._append_log(S.LOG_HISTORY_SAVE_FAIL.format(error=self.history.last_error))
        self._refresh_history_list()
        self._append_log(S.HISTORY_CLEARED)

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
        self.notify(S.MSG_TEMPLATE_OK_FMT.format(name=name), "success")
