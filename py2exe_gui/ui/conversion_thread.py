"""Background thread that runs PyInstaller and streams output to the UI."""

import subprocess
from datetime import datetime

from PyQt5.QtCore import QThread, pyqtSignal

from py2exe_gui.strings import S


class ConversionThread(QThread):
    """خيط منفصل لعملية التحويل."""

    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, command, output_dir):
        super().__init__()
        self.command = command
        self.output_dir = output_dir
        self.process = None
        self.is_cancelled = False

    def run(self):
        try:
            self.log_signal.emit("═" * 60)
            self.log_signal.emit(
                S.CONV_START.format(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            self.log_signal.emit("═" * 60)
            self.log_signal.emit(S.CONV_COMMAND.format(cmd=" ".join(self.command)))
            self.log_signal.emit("─" * 60)

            self.progress_signal.emit(10)

            self.process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd=self.output_dir,
            )

            self.progress_signal.emit(20)

            progress = 20
            for line in self.process.stdout:
                if self.is_cancelled:
                    self.process.terminate()
                    self.finished_signal.emit(False, S.CONV_CANCELLED)
                    return

                self.log_signal.emit(line.strip())

                if "Analyzing" in line:
                    progress = min(progress + 5, 50)
                elif "Processing" in line:
                    progress = min(progress + 2, 70)
                elif "Building" in line:
                    progress = min(progress + 5, 85)
                elif "Copying" in line:
                    progress = min(progress + 2, 95)

                self.progress_signal.emit(progress)

            self.process.wait()

            if self.process.returncode == 0:
                self.progress_signal.emit(100)
                self.log_signal.emit("\n" + "═" * 60)
                self.log_signal.emit(S.CONV_SUCCESS)
                self.log_signal.emit("═" * 60)
                self.finished_signal.emit(True, S.CONV_SUCCESS)
            else:
                self.log_signal.emit("\n" + "═" * 60)
                self.log_signal.emit(S.CONV_FAILED)
                self.log_signal.emit("═" * 60)
                self.finished_signal.emit(False, S.CONV_FAILED_MSG)

        except Exception as e:
            self.log_signal.emit(S.CONV_ERROR.format(error=str(e)))
            self.finished_signal.emit(False, str(e))

    def cancel(self):
        self.is_cancelled = True
        if self.process:
            self.process.terminate()
