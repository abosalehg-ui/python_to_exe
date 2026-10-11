"""Runs a queue of PyInstaller builds, one after another, off the UI thread.

Sequential on purpose: PyInstaller writes into ``build/`` and ``dist/`` under
the working directory and reuses a spec cache keyed by name, so two concurrent
runs sharing an output directory corrupt each other's intermediate files. The
gain from a batch is not parallelism, it is not having to sit through N trips
through the form.
"""

import time

from py2exe_gui.core.batch_runner import CANCELLED, FAILED, RUNNING, SUCCESS, job_config
from py2exe_gui.core.engines import engine_for
from py2exe_gui.qt import Signal
from py2exe_gui.strings import S
from py2exe_gui.ui import streaming_thread
from py2exe_gui.ui.streaming_thread import StreamingProcessThread


class BatchThread(StreamingProcessThread):
    """Executes ``jobs`` in order, emitting progress for each one."""

    # (index, total, status) — lets the tab repaint one row without a rebuild.
    job_signal = Signal(int, int, str)
    finished_signal = Signal(bool)

    def __init__(self, jobs, base_config, python_for=None, options_for=None):
        super().__init__()
        self.jobs = jobs
        self.base_config = base_config
        # Resolves the interpreter for a job's config (an isolated
        # environment, or the app's own Python when None).
        self.python_for = python_for
        # Writes the Runtime Kit for a job's config and returns
        # (options, error): each job is a different app with its own name.
        self.options_for = options_for

    def run(self):
        total = len(self.jobs)
        self.log_signal.emit(S.LOG_BATCH_START.format(count=total))

        for index, job in enumerate(self.jobs, start=1):
            if self.is_cancelled:
                job.status = CANCELLED
                self.job_signal.emit(index - 1, total, CANCELLED)
                continue

            job.status = RUNNING
            self.job_signal.emit(index - 1, total, RUNNING)
            self.log_signal.emit(
                S.LOG_BATCH_JOB_START.format(index=index, total=total, name=job.output_name)
            )

            started = time.monotonic()
            ok = self._run_one(job)
            job.duration_seconds = round(max(0.0, time.monotonic() - started), 2)

            if self.is_cancelled and not ok:
                job.status = CANCELLED
            else:
                job.status = SUCCESS if ok else FAILED

            if job.status == SUCCESS:
                self.log_signal.emit(
                    S.LOG_BATCH_JOB_OK.format(
                        index=index,
                        total=total,
                        name=job.output_name,
                        duration=job.duration_seconds,
                    )
                )
            elif job.status == FAILED:
                self.log_signal.emit(
                    S.LOG_BATCH_JOB_FAIL.format(
                        index=index, total=total, name=job.output_name
                    )
                )

            self.job_signal.emit(index - 1, total, job.status)
            self.progress_signal.emit(int(index * 100 / total) if total else 100)

        if self.is_cancelled:
            self.log_signal.emit(S.LOG_BATCH_CANCELLED)
        else:
            self.log_signal.emit(S.LOG_BATCH_DONE)
        self.finished_signal.emit(not self.is_cancelled)

    def _run_one(self, job) -> bool:
        """Build a single job. Returns True on a zero exit code."""
        config = job_config(job, self.base_config)
        python = self.python_for(config) if self.python_for else None
        options, error = self.options_for(config) if self.options_for else ([], None)
        engine = engine_for(config)
        if not error:
            command, error = engine.build_command(
                config, python_executable=python, extra_options=options
            )
        if not error:
            try:
                engine.prepare_output(config)
            except OSError as e:
                error = str(e)
        if error:
            job.message = error
            self.log_signal.emit(error)
            return False

        code = self.stream(command, config.output_dir or "", engine=engine.name,
                           env=engine.build_env(python or ""))
        if self.error:
            job.message = self.error
            self.log_signal.emit(S.CONV_ERROR.format(error=self.error))
        elif code != streaming_thread.OK:
            job.message = code
        return code == streaming_thread.OK
