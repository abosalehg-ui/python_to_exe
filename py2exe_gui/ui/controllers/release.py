"""ReleaseController: Publishing: GitHub releases, packages and the CI workflow.

A mixin of MainWindow (py2exe_gui/ui/main_window.py). The window module's
constants and worker classes are read through ``_mw`` at call time so a test
that patches ``py2exe_gui.ui.main_window.X`` reaches this code too.
"""

import os

from py2exe_gui.bidi import ltr
from py2exe_gui.core import (
    examine,
)
from py2exe_gui.core.project_file import (
    ProjectConfig,
)
from py2exe_gui.core.release import credentials
from py2exe_gui.core.release.changelog import draft_notes
from py2exe_gui.core.release.git import remote_slug
from py2exe_gui.core.release.pipeline import (
    DONE,
    ReleaseContext,
    confirmation,
    has_blocking_problems,
)
from py2exe_gui.core.release.versioning import apply_version, is_semver
from py2exe_gui.core.venv_manager import (
    env_exists,
)
from py2exe_gui.qt import (
    QDesktopServices,
    QMessageBox,
    QUrl,
)
from py2exe_gui.strings import (
    S,
)
from py2exe_gui.texts import notes_titles, runtime_texts

# The side navigation (2.1): six sections, in the order the work happens.
# Each holds one or more of the former tabs; "build" is one composed page.
from py2exe_gui.ui import main_window as _mw  # noqa: E402 - late, see docstring
from py2exe_gui.ui.dialogs import (
    CiPreviewDialog,
    ReleaseConfirmDialog,
)
from py2exe_gui.ui.finding_text import finding_title
from py2exe_gui.ui.tabs.size_tab import size_text


class ReleaseController:
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
        token = credentials.find_token(keyring_module=_mw.KEYRING)
        self.release_tab.show_token_status(token.source)

    def save_github_token(self):
        """Into the OS keyring — never the settings, the project or the log."""
        token = self.release_tab.token_input.text().strip()
        self.release_tab.token_input.clear()
        if not token:
            return
        try:
            credentials.store_token(token, _mw.KEYRING)
        except credentials.CredentialError as e:
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_TOKEN_STORE.format(error=str(e)))
            return
        self._append_log(S.LOG_TOKEN_SAVED)
        self.refresh_token_status()

    def forget_github_token(self):
        if credentials.delete_token(_mw.KEYRING):
            self._append_log(S.LOG_TOKEN_FORGOTTEN)
        self.refresh_token_status()

    def _release_context(self, project: ProjectConfig, dry_run: bool) -> ReleaseContext:
        tab = self.release_tab
        python = self.build_python(project.build)
        checker = self._installed_checker(project.build)

        def doctor(ctx):
            return examine(ctx.project.build.source, ctx.project.build, is_installed=checker,
                           extra_features=ctx.project.features_used())

        options = _mw.ReleaseOptions(
            version=project.version,
            notes=tab.notes_edit.toPlainText(),
            dry_run=dry_run,
            allow_doctor_errors=tab.allow_errors_check.isChecked(),
            create_tag=tab.create_tag_check.isChecked(),
            push_tag=tab.create_tag_check.isChecked() and tab.push_tag_check.isChecked(),
            publish=tab.publish_check.isChecked(),
            sign_password=self.deploy_tab.signing_password.text(),
            iscc_path=self.installer_tab.inst_iscc_path.text().strip(),
            signing_key_path=_mw.SIGNING_KEY_FILE,
            notes_titles=notes_titles(),
            # The plan lists "download appimagetool" as a command; the
            # confirmation dialog that shows it is the consent for the real run.
            allow_downloads=not dry_run,
            macos_sign_identity=os.environ.get(_mw.MACOS_SIGN_ENV, "").strip(),
        )
        return ReleaseContext(
            project, options, project_path=self.project_path, python=python,
            doctor=doctor, texts=runtime_texts(), rtl=self._rtl(),
            token_provider=lambda: credentials.find_token(keyring_module=_mw.KEYRING),
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
        self.release_thread = _mw.ReleaseThread(context)
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
            if not dialog.exec():
                self._append_log(S.LOG_RELEASE_CANCELLED)
                return
            self._append_log(S.LOG_RELEASE_STARTED.format(version=context.version))
            self._run_release(self._release_context(self._current_project(), dry_run=False))
            return

        self._last_release_dir = context.out_dir if os.path.isdir(context.out_dir) else ""
        self.refresh_home()
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

    # ─── Platforms: packages and the CI workflow (2.0) ──────────────────

    def build_packages(self):
        """Package the last build for this host, with consent for any download."""
        from py2exe_gui.core.packagers import get_packager, spec_from_project
        from py2exe_gui.core.packagers.appimage import appimagetool_url
        from py2exe_gui.core.platform_support import is_supported, platform_label
        from py2exe_gui.core.release import artifacts

        if self._build_in_progress():
            QMessageBox.warning(self, S.MSG_WARNING, S.MSG_COMPARE_BUSY)
            return
        project = self._current_project()
        formats = project.packaging.enabled_formats()
        if not formats:
            QMessageBox.warning(self, S.MSG_WARNING, S.MSG_PACKAGES_NONE_SELECTED)
            return
        here = [f for f in formats if is_supported(f)]
        if not here:
            QMessageBox.warning(self, S.MSG_WARNING,
                                S.MSG_PACKAGES_NONE_HERE.format(platform=platform_label()))
            return
        built = artifacts.built_output(project.build)
        if not built:
            QMessageBox.warning(self, S.MSG_WARNING, S.MSG_PACKAGES_NO_BUILD)
            return
        version = project.version if is_semver(project.version) else "0.0.0"
        out_dir = artifacts.release_dir(project.build, version)
        spec = spec_from_project(project, built, version, out_dir,
                                 sign_identity=os.environ.get(_mw.MACOS_SIGN_ENV, "").strip())
        allow_download = False
        if "appimage" in here and not get_packager("appimage").tool_path():
            packager = get_packager("appimage")
            reply = QMessageBox.question(
                self, S.MSG_CONFIRM,
                S.MSG_APPIMAGETOOL_CONFIRM.format(url=appimagetool_url(spec.machine()),
                                                  path=packager.tools_dir),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                allow_download = True
            else:
                self._append_log(S.LOG_APPIMAGETOOL_DECLINED)
                here = [f for f in here if f != "appimage"]
                if not here:
                    return
        self._append_log(S.LOG_PACKAGES_START.format(
            formats=", ".join(get_packager(f).display_name for f in here)))
        self.platforms_tab.set_running(True)
        self.platforms_tab.show_packages_result("", bool(self._last_packages_dir))
        self.convert_btn.setEnabled(False)
        self.package_thread = _mw.PackageThread(spec, here, allow_download)
        self.package_thread.log_signal.connect(self._append_log)
        self.package_thread.finished_signal.connect(self._on_packages_finished)
        self.package_thread.start()

    def _on_packages_finished(self, results):
        from py2exe_gui.core.packagers import get_packager

        self.platforms_tab.set_running(False)
        self.convert_btn.setEnabled(True)
        done = []
        for result in results:
            label = get_packager(result.format).display_name
            for finding in result.findings:
                self._append_log(f"  • [{finding.code}] {finding_title(finding)}")
            if result.ok:
                done.append(result)
                self._append_log(S.LOG_PACKAGE_DONE.format(
                    format=label, path=result.path, size=size_text(result.size_bytes)))
            else:
                self._append_log(S.LOG_PACKAGE_FAILED.format(
                    format=label, error=result.error or result.error_code))
        folder = os.path.dirname(done[0].path) if done else ""
        if folder:
            self._last_packages_dir = folder
        all_ok = bool(results) and len(done) == len(results)
        text = (S.PACKAGES_RESULT_DONE.format(count=ltr(str(len(done))), folder=ltr(folder))
                if all_ok else S.PACKAGES_RESULT_FAILED)
        self.platforms_tab.show_packages_result(text, bool(self._last_packages_dir))
        self._notify_build_result(all_ok, S.RELEASE_STEP_PACKAGES)

    def open_packages_folder(self):
        if self._last_packages_dir and os.path.isdir(self._last_packages_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._last_packages_dir))

    def generate_ci_workflow(self):
        """Preview the GitHub Actions workflow; write it only on "Write the file"."""
        from py2exe_gui.core.ci_generator import (
            options_for,
            render_workflow,
            repo_root,
            workflow_path,
            write_workflow,
        )

        if not self.project_path:
            QMessageBox.warning(self, S.MSG_WARNING, S.MSG_CI_NEEDS_PROJECT)
            return
        project = self._current_project()
        project_dir = os.path.dirname(self.project_path)
        root = repo_root(project_dir)
        opts, findings = options_for(project, self.project_path, root,
                                     tool_requirement=self.platforms_tab.tool_requirement())
        for finding in findings:
            self._append_log(f"[{finding.code}] {finding_title(finding)}")
        problems = [finding_title(f) for f in findings if f.severity == "error"]
        if problems:
            QMessageBox.warning(self, S.MSG_WARNING,
                                S.MSG_CI_BLOCKED.format(problems="\n".join(problems)))
            return
        text = render_workflow(opts)
        path = workflow_path(root or project_dir)
        dialog = CiPreviewDialog(text, path, os.path.exists(path), opts.secrets_used(), self)
        if not dialog.exec():
            self._append_log(S.LOG_CI_CANCELLED)
            return
        write_workflow(text, path)
        self._append_log(S.LOG_CI_WRITTEN.format(path=path))
