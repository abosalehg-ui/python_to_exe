"""EnvironmentController: Isolated build environments, engine comparison and batch conversion.

A mixin of MainWindow (py2exe_gui/ui/main_window.py). The window module's
constants and worker classes are read through ``_mw`` at call time so a test
that patches ``py2exe_gui.ui.main_window.X`` reaches this code too.
"""

import os
import sys

from py2exe_gui.constants import (
    PYINSTALLER_REQUIREMENT,
)
from py2exe_gui.core import (
    BuildConfig,
    make_record,
    summarize,
)
from py2exe_gui.core.compare import COMPARE_DIR
from py2exe_gui.core.diagnostics import build_root
from py2exe_gui.core.engines import engine_for, engine_names, get_engine
from py2exe_gui.core.knowledge import default_is_installed
from py2exe_gui.core.size_analyzer import (
    format_size,
)
from py2exe_gui.core.venv_manager import (
    InstalledChecker,
    delete_env,
    env_dir_for,
    env_exists,
    env_python,
    env_status,
    folder_size,
    format_lock,
    freeze_command,
    lock_file_path,
    plan_environment,
    project_requirements,
    quote_command,
    write_metadata,
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


class EnvironmentController:
    # ─── Build environment ──────────────────────────────────────────────

    def _env_dir(self, source: str) -> str:
        return env_dir_for(source, _mw.ENVS_ROOT)

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
        self.size_tab.show_env(status, text, bool(_mw.find_uv()), has_source=True)

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

        tools = engine_for(self._current_config()).requirements() or PYINSTALLER_REQUIREMENT
        plan = plan_environment(
            source, _mw.ENVS_ROOT, base, tools,
            uv=_mw.find_uv(), recreate=recreate,
        )
        commands = "\n\n".join(quote_command(c) for c in plan.all_commands())
        reply = QMessageBox.question(
            self, S.MSG_CONFIRM, S.MSG_ENV_CONFIRM.format(commands=commands),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if recreate and env_exists(plan.env_dir):
            delete_env(plan.env_dir, _mw.ENVS_ROOT)
        os.makedirs(_mw.ENVS_ROOT, exist_ok=True)

        self.size_tab.set_env_busy()
        self.convert_btn.setEnabled(False)
        self._set_busy(S.BUSY_ENV)
        self.env_thread = _mw.EnvThread(plan, base_python=base)
        self.env_thread.log_signal.connect(self._append_log)
        self.env_thread.finished_signal.connect(
            lambda ok, failed, error: self._on_env_finished(plan, ok, failed, error, then_build)
        )
        self.env_thread.start()

    def recreate_build_env(self):
        self.create_build_env(recreate=True)

    def _on_env_finished(self, plan, ok: bool, failed, error: str, then_build: bool):
        """``error`` is the thread's outcome code ('' when it succeeded)."""
        self._clear_busy()
        self.convert_btn.setEnabled(True)
        # The environment changed: what it can import must be asked again.
        self._checkers.pop(plan.python, None)
        if ok:
            if failed:
                self._append_log(S.LOG_ENV_DONE_PARTIAL.format(names=", ".join(failed)))
            else:
                self._append_log(S.LOG_ENV_DONE)
        else:
            # The pip output is already in the log line by line; the dialog
            # says what happened in one sentence and points there.
            detail = self.thread_error_text(error, "pip", self.env_thread)
            self._append_log(S.LOG_ENV_FAILED.format(error=detail))
            if error != streaming_thread.CANCELLED:
                QMessageBox.critical(self, S.MSG_ERROR, S.MSG_ENV_FAILED)
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
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if delete_env(env_dir, _mw.ENVS_ROOT):
            self._append_log(S.LOG_ENV_DELETED)
        self._checkers.pop(env_python(env_dir), None)
        self.run_doctor()

    def save_env_lock(self):
        """Pin the environment's exact versions in p2e-build.lock."""
        source = self._source_path()
        env_dir = self._env_dir(source) if source else ""
        if not env_dir or not env_exists(env_dir):
            return
        if self._build_in_progress():
            QMessageBox.warning(self, S.MSG_WARNING, S.MSG_DIAG_BUSY)
            return
        # ``pip freeze`` on a worker: it imports every distribution's metadata
        # and took seconds on a large environment, with the window frozen.
        self._set_busy(S.BUSY_FREEZING)
        self.command_thread = _mw.CommandThread(freeze_command(env_python(env_dir), _mw.find_uv()),
                                            timeout=120)
        self.command_thread.finished_signal.connect(
            lambda rc, output: self._on_env_frozen(source, rc, output)
        )
        self.command_thread.start()

    def _on_env_frozen(self, source: str, returncode: int, output: str):
        self._clear_busy()
        if returncode != 0:
            code = getattr(self.command_thread, "code", streaming_thread.FAILED)
            self._append_log(S.LOG_ENV_LOCK_FAILED.format(
                error=self.thread_error_text(code, "pip freeze", self.command_thread)))
            for line in (output or "").strip().splitlines()[-5:]:
                self._append_log(line)
            return
        path = lock_file_path(source)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(format_lock(output))
        except OSError as e:
            self._append_log(S.LOG_ENV_LOCK_FAILED.format(error=str(e)))
            return
        self._append_log(S.LOG_ENV_LOCK_SAVED.format(path=path))
        self.refresh_env_view()

    # ─── Compare engines (2.0) ──────────────────────────────────────────

    def start_compare(self, allow_downloads: bool = False):
        """Build the project with every engine into p2e_compare/, then measure."""
        if self._build_in_progress():
            QMessageBox.warning(self, S.MSG_WARNING, S.MSG_COMPARE_BUSY)
            return
        project = self._current_project()
        config = project.build
        if not config.source or not os.path.isfile(config.source):
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_NO_SOURCE)
            return
        if config.isolated_env and not env_exists(self._env_dir(config.source)):
            QMessageBox.warning(self, S.MSG_WARNING, S.FINDING_ENV_NOT_CREATED_DETAIL)
            return
        python = self.build_python(config)
        for name in engine_names():
            if not self._ensure_engine(get_engine(name), python,
                                       then=lambda: self.start_compare(allow_downloads)):
                return
        self.size_tab.show_compare([], None)
        self.size_tab.compare_btn.setEnabled(False)
        self.convert_btn.setEnabled(False)
        self._set_busy(S.BUSY_COMPARE)  # one bar for several builds
        self.compare_thread = _mw.CompareThread(
            project, python, runs=self.size_tab.compare_runs.value(),
            timeout=float(self.size_tab.compare_timeout.value()),
            texts=self._runtime_texts(), rtl=self._rtl(), allow_downloads=allow_downloads,
        )
        self.compare_thread.log_signal.connect(self._append_log)
        self.compare_thread.phase_signal.connect(self._on_compare_phase)
        self.compare_thread.finished_signal.connect(self._on_compare_finished)
        self.compare_thread.start()

    def _on_compare_phase(self, engine: str, phase: str):
        template = getattr(S, f"COMPARE_PHASE_{phase.upper()}", "{engine}")
        text = template.format(engine=get_engine(engine).display_name)
        self._set_busy(text)
        self._append_log(text)

    def _on_compare_finished(self, rows, recommendation):
        self._clear_busy()
        self.size_tab.compare_btn.setEnabled(True)
        self.convert_btn.setEnabled(True)
        self._compare_view = (rows, recommendation)
        self.size_tab.show_compare(rows, recommendation)
        config = self._current_config()
        self._append_log(S.COMPARE_DONE_LOG.format(
            folder=os.path.join(build_root(config), COMPARE_DIR)))
        self.tabs.setCurrentWidget(self.size_tab)
        declined = [f for row in rows for f in row.findings
                    if f.code == "nuitka_download_declined"]
        if declined and self.ask_download_consent(declined[0].params.get("tool", "")):
            self._allow_downloads_once = False  # the consent goes to this comparison
            self.start_compare(allow_downloads=True)

    #: Every worker the window may start. Each one spawns a child process or
    #: writes files; a build "in progress" is any of them running.
    _THREAD_ATTRS = (
        "conversion_thread", "batch_thread", "diagnostic_thread", "env_thread",
        "release_thread", "compare_thread", "package_thread", "installer_thread",
        "post_build_thread", "command_thread", "task_thread",
    )

    def _running_threads(self):
        return [t for t in (getattr(self, name, None) for name in self._THREAD_ATTRS)
                if t is not None and t.isRunning()]

    def _build_in_progress(self) -> bool:
        return bool(self._running_threads())

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

        self.batch_thread = _mw.BatchThread(
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
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
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
