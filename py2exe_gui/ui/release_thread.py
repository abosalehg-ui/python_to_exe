"""Background thread that runs (or plans) a release.

The pipeline itself is UI-free (``core.release.pipeline``); this only moves
it off the UI thread and turns its callbacks into signals, so the checklist
updates live while PyInstaller, signtool or an upload is running.
"""

from PyQt5.QtCore import QThread, pyqtSignal

from py2exe_gui.core.release.pipeline import run_release


class ReleaseThread(QThread):
    log_signal = pyqtSignal(str)
    #: A ``StepResult`` (running, then its final status).
    step_signal = pyqtSignal(object)
    #: (context, list of StepResult)
    finished_signal = pyqtSignal(object, object)

    def __init__(self, context):
        super().__init__()
        self.context = context
        # The pipeline logs from this thread; signals cross to the UI safely.
        context._log = self.log_signal.emit

    def run(self):
        results = run_release(self.context, self.step_signal.emit)
        self.finished_signal.emit(self.context, results)
