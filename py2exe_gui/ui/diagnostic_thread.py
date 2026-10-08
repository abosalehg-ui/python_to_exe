"""Background thread for the doctor's diagnostic run.

A windowed EXE that crashes shows its traceback in a dialog — or nowhere —
so the smoke test cannot read it. The diagnostic run builds the same app with
the console kept on, into a side folder, runs it from a neutral directory and
hands back everything it printed.
"""

import os
import subprocess

from PyQt5.QtCore import QThread, pyqtSignal

from py2exe_gui.core.diagnostics import build_name
from py2exe_gui.core.smoke_test import locate_built_executable, run_from_neutral_folder
from py2exe_gui.strings import S


class DiagnosticThread(QThread):
    """Build a console copy of the app, run it, report its output."""

    log_signal = pyqtSignal(str)
    #: (built_ok, exe_output, build_log)
    finished_signal = pyqtSignal(bool, str, str)

    def __init__(self, command, config, timeout: float = 8.0, popen_kwargs=None):
        super().__init__()
        self.popen_kwargs = dict(popen_kwargs or {})
        self.command = command
        self.config = config
        self.timeout = timeout
        self.process = None
        self.is_cancelled = False

    def run(self):
        build_lines = []
        try:
            os.makedirs(self.config.output_dir, exist_ok=True)
            self.log_signal.emit(S.LOG_DIAG_START.format(path=self.config.output_dir))
            self.process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=self.config.output_dir,
                **self.popen_kwargs,
            )
            for line in self.process.stdout:
                if self.is_cancelled:
                    self.process.terminate()
                    break
                build_lines.append(line.rstrip("\n"))
            self.process.wait()
        except OSError as e:
            build_lines.append(str(e))
            self.finished_signal.emit(False, "", "\n".join(build_lines))
            return

        build_log = "\n".join(build_lines)
        if self.is_cancelled or self.process.returncode != 0:
            self.log_signal.emit(S.LOG_DIAG_BUILD_FAILED)
            self.finished_signal.emit(False, "", build_log)
            return

        exe = locate_built_executable(
            self.config.output_dir, build_name(self.config), self.config.onefile,
            engine=self.config.engine,
        )
        if not exe:
            self.log_signal.emit(S.LOG_SMOKE_NOT_FOUND)
            self.finished_signal.emit(False, "", build_log)
            return

        self.log_signal.emit(S.LOG_DIAG_RUN)
        # Start it from a neutral folder, as a desktop shortcut would.
        result = run_from_neutral_folder(exe, timeout=self.timeout)
        self.finished_signal.emit(True, result.output or result.error, build_log)

    def cancel(self):
        self.is_cancelled = True
        if self.process:
            self.process.terminate()
