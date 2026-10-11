"""Background thread that runs ISCC.exe and streams its output to the UI.

Kept separate from ``ConversionThread`` because the lifecycle differs: the
installer step has no progress heuristics and reports a single output path.
"""

from py2exe_gui.qt import Signal
from py2exe_gui.ui.streaming_thread import OK, StreamingProcessThread


class InstallerThread(StreamingProcessThread):
    """Runs the Inno Setup compiler without blocking the UI thread."""

    #: (succeeded, the installer's path on success — an outcome code otherwise)
    finished_signal = Signal(bool, str)

    def __init__(self, command, work_dir, expected_output=""):
        super().__init__()
        self.command = command
        self.work_dir = work_dir
        self.expected_output = expected_output

    def run(self):
        def line(text: str):
            stripped = text.strip()
            if stripped:
                self.log_signal.emit(stripped)

        code = self.stream(self.command, self.work_dir or "", on_line=line)
        if code == OK:
            self.finished_signal.emit(True, self.expected_output)
        else:
            self.finished_signal.emit(False, code)
