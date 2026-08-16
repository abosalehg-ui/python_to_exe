"""Runs a queue of PyInstaller builds, one after another, off the UI thread.

Sequential on purpose: PyInstaller writes into ``build/`` and ``dist/`` under
the working directory and reuses a spec cache keyed by name, so two concurrent
runs sharing an output directory corrupt each other's intermediate files. The
gain from a batch is not parallelism, it is not having to sit through N trips
through the form.
"""

import subprocess
import time

from PyQt5.QtCore import QThread, pyqtSignal

from py2exe_gui.core.batch_runner import CANCELLED, FAILED, RUNNING, SUCCESS, job_config
from py2exe_gui.core.builder import build_pyinstaller_command
from py2exe_gui.strings import S


class BatchThread(QThread):
    """Executes ``jobs`` in order, emitting progress for each one."""

    log_signal = pyqtSignal(str)
    # (index, total, status) — lets the tab repaint one row without a rebuild.
    job_signal = pyqtSignal(int, int, str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool)

    def __init__(self, jobs, base_config):
        super().__init__()
        self.jobs = jobs
        self.base_config = base_config
        self.process = None
        self.is_cancelled = False

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
        command, error = build_pyinstaller_command(config)
        if error:
            job.message = error
            self.log_signal.emit(error)
            return False

        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd=config.output_dir or None,
            )
        except (OSError, ValueError) as e:
            job.message = str(e)
            self.log_signal.emit(S.CONV_ERROR.format(error=str(e)))
            return False

        try:
            for line in self.process.stdout:
                if self.is_cancelled:
                    self.process.terminate()
                    return False
                self.log_signal.emit(line.rstrip())
            self.process.wait()
        except (OSError, ValueError) as e:
            job.message = str(e)
            self.log_signal.emit(S.CONV_ERROR.format(error=str(e)))
            return False
        finally:
            returncode = self.process.returncode if self.process else 1
            self.process = None

        return returncode == 0

    def cancel(self):
        """Stop after (or during) the current job; the rest are marked cancelled."""
        self.is_cancelled = True
        if self.process:
            self.process.terminate()
