"""Background thread that runs PyInstaller and streams output to the UI."""

import subprocess
from datetime import datetime

from PyQt5.QtCore import QThread, pyqtSignal

from py2exe_gui.core.build_stages import BuildStageTracker
from py2exe_gui.strings import S


class ConversionThread(QThread):
    """خيط منفصل لعملية التحويل."""

    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    # Stage key from build_stages, so the window can label the progress bar.
    stage_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, command, output_dir):
        super().__init__()
        self.command = command
        self.output_dir = output_dir
        self.process = None
        self.is_cancelled = False
        self.stages = BuildStageTracker()

    def run(self):
        try:
            self.log_signal.emit("═" * 60)
            self.log_signal.emit(
                S.CONV_START.format(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            self.log_signal.emit("═" * 60)
            self.log_signal.emit(S.CONV_COMMAND.format(cmd=" ".join(self.command)))
            self.log_signal.emit("─" * 60)

            self.process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd=self.output_dir,
            )

            # Progress now follows the phase PyInstaller announces rather than
            # counting how many lines it happened to print. See build_stages.
            last_stage = self.stages.stage
            for line in self.process.stdout:
                if self.is_cancelled:
                    self.process.terminate()
                    self.finished_signal.emit(False, S.CONV_CANCELLED)
                    return

                self.log_signal.emit(line.strip())

                if self.stages.feed(line):
                    self.progress_signal.emit(self.stages.percent)
                    if self.stages.stage != last_stage:
                        last_stage = self.stages.stage
                        self.stage_signal.emit(last_stage)

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
