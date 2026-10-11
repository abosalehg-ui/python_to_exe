"""BuildController: Build pipeline, the temp files a build needs, post-build actions and the installer.

A mixin of MainWindow (py2exe_gui/ui/main_window.py). The window module's
constants and worker classes are read through ``_mw`` at call time so a test
that patches ``py2exe_gui.ui.main_window.X`` reaches this code too.
"""

import os
import subprocess
import sys
import tempfile
import time

from py2exe_gui.bidi import ltr
from py2exe_gui.constants import (
    PYINSTALLER_REQUIREMENT,
)
from py2exe_gui.core import (
    BuildConfig,
    InstallerConfig,
    ManifestConfig,
    build_iscc_command,
    build_signtool_command,
    find_iscc,
    generate_iss_script,
    generate_manifest,
    generate_version_file,
    installer_output_path,
    locate_built_executable,
    make_record,
    redact_password,
    resolve_languages,
)
from py2exe_gui.core.build_runner import popen_options
from py2exe_gui.core.engines import engine_for
from py2exe_gui.core.engines.base import describe_error
from py2exe_gui.core.installer import validate as validate_installer
from py2exe_gui.core.installer import write_iss_script
from py2exe_gui.core.runtime_kit import (
    preview_options,
)
from py2exe_gui.core.size_analyzer import (
    analyze,
    previous_size,
)
from py2exe_gui.core.venv_manager import (
    env_exists,
    quote_command,
)
from py2exe_gui.qt import (
    QMessageBox,
)
from py2exe_gui.strings import (
    S,
)

# The side navigation (2.1): six sections, in the order the work happens.
# Each holds one or more of the former tabs; "build" is one composed page.
from py2exe_gui.ui import main_window as _mw  # noqa: E402 - late, see docstring
from py2exe_gui.ui import streaming_thread
from py2exe_gui.ui.tabs.size_tab import size_text


class BuildController:
    # ─── Build pipeline ─────────────────────────────────────────────────

    def ask_download_consent(self, tool: str) -> bool:
        """Ask before letting the engine download a tool; True allows the next build."""
        reply = QMessageBox.question(
            self, S.MSG_CONFIRM, S.MSG_NUITKA_DOWNLOAD_CONFIRM.format(tool=tool or "?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return False
        self._allow_downloads_once = True
        self._append_log(S.LOG_NUITKA_DOWNLOAD_ALLOWED)
        return True

    def _ensure_engine(self, engine, python: str = "", then=None) -> bool:
        """The build engine is installed in ``python``, or installed with consent.

        Returns True when it is already there. Otherwise the person is asked
        (on the UI thread), pip runs on a worker, and ``then`` — the action
        that needed the engine, typically the build — is called from the
        worker's finished slot once the install succeeded; the caller returns
        right away on False.
        """
        if engine.name == "pyinstaller":
            return self._ensure_pyinstaller(python, then=then)
        python = python or sys.executable
        if engine.is_available(python):
            return True
        install_cmd = [python, "-m", "pip", "install", *engine.requirements()]
        reply = QMessageBox.question(
            self, S.MSG_CONFIRM,
            S.MSG_INSTALL_ENGINE_CONFIRM.format(engine=engine.display_name,
                                                cmd=quote_command(install_cmd)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            self._append_log(S.LOG_INSTALL_ENGINE_DECLINED.format(engine=engine.display_name))
            return False
        self._append_log(S.LOG_INSTALL_ENGINE.format(engine=engine.display_name))
        self._append_log(quote_command(install_cmd))
        self._install_tool(
            install_cmd, engine.display_name, timeout=1200, then=then,
            log_ok=S.LOG_INSTALL_ENGINE_OK.format(engine=engine.display_name),
        )
        return False

    def _ensure_pyinstaller(self, python: str = "", then=None) -> bool:
        """Check for PyInstaller, offering to install it with explicit consent.

        The previous version ran ``pip install pyinstaller`` silently on the
        first build: an unattended network install, unpinned, from whatever
        index the environment happened to point at. ``python`` is the build
        interpreter (an isolated environment's), defaulting to this one.
        See ``_ensure_engine`` for ``then``.
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
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            self._append_log(S.LOG_INSTALL_PYINSTALLER_DECLINED)
            return False

        self._append_log(S.LOG_INSTALL_PYINSTALLER)
        self._append_log(" ".join(install_cmd))
        self._install_tool(install_cmd, "PyInstaller", timeout=600, then=then,
                           log_ok=S.LOG_INSTALL_PYINSTALLER_OK)
        return False

    def _install_tool(self, install_cmd, tool: str, timeout: float, then, log_ok: str):
        """Run a consented pip install on a worker, then continue with ``then``.

        The window shows the busy bar and keeps the Build button disabled
        until pip returns; the dialog on failure is one sentence, the pip
        output goes to the log.
        """
        if self._build_in_progress():
            QMessageBox.warning(self, S.MSG_WARNING, S.MSG_DIAG_BUSY)
            return
        self._set_busy(S.BUSY_INSTALLING_FMT.format(tool=tool))
        self.convert_btn.setEnabled(False)
        self.command_thread = _mw.CommandThread(install_cmd, timeout=timeout)
        self.command_thread.finished_signal.connect(
            lambda rc, output: self._on_tool_installed(rc, output, tool, then, log_ok)
        )
        self.command_thread.start()

    def _on_tool_installed(self, returncode: int, output: str, tool: str, then, log_ok: str):
        self._clear_busy()
        self.convert_btn.setEnabled(True)
        for line in (output or "").splitlines():
            if line.strip():
                self._append_log(line.rstrip())
        if returncode != 0:
            code = getattr(self.command_thread, "code", streaming_thread.FAILED)
            self._append_log(S.ERR_INSTALL_ENGINE_FAIL.format(
                engine=tool, error=self.thread_error_text(code, "pip", self.command_thread)))
            QMessageBox.critical(self, S.MSG_ERROR, S.MSG_INSTALL_FAILED_FMT.format(tool=tool))
            self._cleanup_temp_files()
            return
        self._append_log(log_ok)
        if then is not None:
            then()

    def start_conversion(self):
        config = self._current_config()
        engine = engine_for(config)
        native = []
        if engine.version_info_mode == "options":
            native += engine.metadata_options(self._current_project().version_info)
        else:
            version_path = self._materialize_version_file()
            if version_path:
                config.version_file = version_path
        if engine.supports("manifest"):
            manifest_path = self._materialize_manifest_file()
            if manifest_path:
                config.manifest_file = manifest_path
        # Consent to downloads is given for one build at a time, by a person.
        if self._allow_downloads_once:
            self._allow_downloads_once = False
            native += engine.consent_options()

        # Every early return below must clean up the temp files created above;
        # one path used to skip that and leak into %TEMP%.
        python = self.build_python(config)
        cmd, error = engine.build_command(config, python_executable=python,
                                          extra_options=native)
        if error:
            self._cleanup_temp_files()
            QMessageBox.warning(self, S.MSG_WARNING, describe_error(error))
            return
        kit_options, kit_error = self._runtime_kit_options(config)
        if kit_error:
            self._cleanup_temp_files()
            QMessageBox.warning(self, S.MSG_WARNING, kit_error)
            return
        if kit_options:
            cmd, _error = engine.build_command(
                config, python_executable=python, extra_options=native + kit_options
            )
            self._append_log(S.LOG_KIT_EMBEDDED_FMT.format(
                services=", ".join(self._runtime_service_labels(config))
            ))

        if config.isolated_env and not env_exists(self._env_dir(config.source)):
            self._cleanup_temp_files()
            reply = QMessageBox.question(
                self, S.MSG_CONFIRM, S.MSG_ENV_NEEDED,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.create_build_env(then_build=True)
            return

        if not self._ensure_engine(engine, python, then=self.start_conversion):
            # Either declined, or pip is running on a worker and will call
            # start_conversion again once the engine is there.
            self._cleanup_temp_files()
            return
        if python != sys.executable:
            self._append_log(S.LOG_ENV_PYTHON.format(python=python))
        if engine.name != "pyinstaller":
            self._append_log(S.LOG_ENGINE_BUILD.format(engine=engine.display_name))
        try:
            engine.prepare_output(config)
        except OSError as e:
            self._cleanup_temp_files()
            self._append_log(S.LOG_OUTPUT_DIR_FAILED.format(error=str(e)))
            QMessageBox.critical(self, S.MSG_ERROR, S.MSG_OUTPUT_DIR_FAILED)
            return
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

        self._set_building(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(S.PROGRESS_CONVERTING)
        self.progress_bar.setVisible(True)
        self._refresh_progress_label()
        self.log_panel.set_expanded(True)
        self.set_status(S.STATUS_BUILDING)

        self.conversion_thread = _mw.ConversionThread(
            cmd, work_dir, engine=engine.name,
            popen_kwargs=popen_options(engine.name, engine.build_env(python)),
        )
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
        """Name the phase the engine has reached on the progress bar."""
        label = getattr(S, f"STAGE_{stage_key.upper()}", "")
        if label:
            self.progress_bar.setFormat(S.PROGRESS_STAGE_FMT.format(stage=label))
            self._refresh_progress_label()
            self.set_status(S.STATUS_BUILDING_STAGE_FMT.format(stage=label))

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

    def _set_building(self, active: bool):
        """Swap the Build and Cancel buttons; only one is ever shown."""
        self.convert_btn.setEnabled(not active)
        self.convert_btn.setVisible(not active)
        self.cancel_btn.setEnabled(active)
        self.cancel_btn.setVisible(active)

    def on_conversion_finished(self, success, message, status: str = ""):
        """``status`` is the thread's outcome code (``streaming_thread``);
        a cancelled build is told apart by it, never by its message text."""
        if not status:
            status = streaming_thread.OK if success else streaming_thread.FAILED
        cancelled = status == streaming_thread.CANCELLED
        self._set_building(False)
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
            size_report = analyze(built)

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
            self.refresh_home()

        diagnosed = []
        if snapshot and not cancelled:
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
            self._refresh_progress_label()
            self.set_status(S.STATUS_DONE_FMT.format(duration=ltr(f"{duration:.0f}s")))
            # The outcome stays until closed; the tray already pinged anyone
            # who was looking elsewhere.
            self.notify(message, "success", 0)
        else:
            self.progress_bar.setFormat(S.PROGRESS_FAILED)
            self._refresh_progress_label()
            self.set_status(S.STATUS_CANCELLED if cancelled else S.STATUS_FAILED)
            declined = [f for f in diagnosed if f.code == "nuitka_download_declined"]
            if declined:
                # The engine stopped to ask for a download; only a person says yes.
                if self.ask_download_consent(declined[0].params.get("tool", "")):
                    self.start_conversion()
            elif not cancelled:
                QMessageBox.critical(self, S.MSG_ERROR, message)

    def preview_command(self):
        """Show the command the selected engine would run."""
        config = self._current_config()
        engine = engine_for(config)
        kit = preview_options(config) if engine.supports("runtime_kit") else []
        native = engine.metadata_options(self._current_project().version_info)
        cmd, error = engine.build_command(
            config, python_executable=self.build_python(config),
            extra_options=native + kit,
        )
        if error:
            QMessageBox.warning(self, S.MSG_WARNING, describe_error(error))
            return
        _mw.CommandPreviewDialog(cmd, parent=self).exec()

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

    # ─── Post-build: signing, smoke test, installer ─────────────────────

    def _run_post_build_actions(self, config: BuildConfig):
        """Sign and/or smoke-test the produced EXE, then build the installer."""
        exe_path = locate_built_executable(
            config.output_dir or os.path.dirname(config.source),
            config.output_name or os.path.splitext(os.path.basename(config.source))[0],
            config.onefile,
            engine=config.engine,
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
        self.post_build_thread = _mw.PostBuildThread(
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
            engine=config.engine,
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

        try:
            iss_path = write_iss_script(script, inst_cfg, app_path, onefile)
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
        self.notify(S.MSG_ISS_WRITTEN_FMT.format(path=iss_path), "success", 0)

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

        self.installer_thread = _mw.InstallerThread(
            cmd, os.path.dirname(iss_path), expected_output=expected
        )
        self.installer_thread.log_signal.connect(self._append_log)
        self.installer_thread.finished_signal.connect(
            lambda ok, msg: self._on_installer_finished(ok, msg, interactive)
        )
        self.installer_thread.start()

    def _on_installer_finished(self, success: bool, message: str, interactive: bool):
        """``message`` is the installer's path on success, an outcome code otherwise."""
        if success:
            self._append_log(S.LOG_INSTALLER_OK.format(path=message))
            if interactive:
                self.notify(S.MSG_INSTALLER_OK.format(path=message), "success", 0)
        else:
            error = self.thread_error_text(message, "ISCC.exe", self.installer_thread)
            self._append_log(S.LOG_INSTALLER_FAIL.format(error=error))
            if interactive and message != streaming_thread.CANCELLED:
                QMessageBox.critical(self, S.MSG_ERROR, S.LOG_INSTALLER_FAIL.format(error=error))
