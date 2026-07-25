"""Background thread that runs ISCC.exe and streams its output to the UI.

Kept separate from ``ConversionThread`` because the lifecycle differs: the
installer step has no progress heuristics and reports a single output path.
"""

import subprocess

from PyQt5.QtCore import QThread, pyqtSignal


class InstallerThread(QThread):
    """Runs the Inno Setup compiler without blocking the UI thread."""

    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, command, work_dir, expected_output=""):
        super().__init__()
        self.command = command
        self.work_dir = work_dir
        self.expected_output = expected_output
        self.process = None
        self.is_cancelled = False

    def run(self):
        try:
            self.process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd=self.work_dir or None,
            )
        except FileNotFoundError:
            self.finished_signal.emit(False, "ISCC.exe not found")
            return
        except OSError as e:
            self.finished_signal.emit(False, str(e))
            return

        try:
            for line in self.process.stdout:
                if self.is_cancelled:
                    self.process.terminate()
                    self.finished_signal.emit(False, "cancelled")
                    return
                stripped = line.strip()
                if stripped:
                    self.log_signal.emit(stripped)
            self.process.wait()
        except Exception as e:  # noqa: BLE001 - surfaced to the user via the log
            self.finished_signal.emit(False, str(e))
            return

        if self.process.returncode == 0:
            self.finished_signal.emit(True, self.expected_output)
        else:
            self.finished_signal.emit(
                False, f"ISCC exited with code {self.process.returncode}"
            )

    def cancel(self):
        self.is_cancelled = True
        if self.process:
            self.process.terminate()
