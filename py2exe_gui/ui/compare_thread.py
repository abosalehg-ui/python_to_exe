"""Compare mode off the UI thread: build with each engine, then measure."""

import subprocess

from PyQt5.QtCore import QThread, pyqtSignal

from py2exe_gui.core.build_runner import run_build
from py2exe_gui.core.compare import recommend, run_compare


class CompareThread(QThread):
    """Runs ``core.compare.run_compare``; reports progress and the result."""

    log_signal = pyqtSignal(str)
    #: (engine, phase) — "build", "smoke", "startup"
    phase_signal = pyqtSignal(str, str)
    #: (engine, stage key, percent) while an engine builds
    stage_signal = pyqtSignal(str, str, int)
    #: (rows, recommendation)
    finished_signal = pyqtSignal(object, object)

    def __init__(self, project, python, runs=5, timeout=10.0, texts=None, rtl=False,
                 allow_downloads=False):
        super().__init__()
        self.project = project
        self.python = python
        self.runs = runs
        self.timeout = timeout
        self.texts = texts
        self.rtl = rtl
        self.allow_downloads = allow_downloads
        self.is_cancelled = False
        self.process = None

    def _popen(self, *args, **kwargs):
        self.process = subprocess.Popen(*args, **kwargs)
        if self.is_cancelled:
            self.process.terminate()
        return self.process

    def _build(self, prepared, on_line, on_stage):
        return run_build(prepared, on_line, on_stage, popen=self._popen)

    def run(self):
        rows = run_compare(
            self.project, self.python, runs=self.runs, timeout=self.timeout,
            texts=self.texts, rtl=self.rtl, allow_downloads=self.allow_downloads,
            on_line=self.log_signal.emit,
            on_engine=self.phase_signal.emit,
            on_stage=self.stage_signal.emit,
            should_stop=lambda: self.is_cancelled,
            build=self._build,
        )
        self.finished_signal.emit(rows, recommend(rows))

    def cancel(self):
        """Stop the build that is running, and skip the rest."""
        self.is_cancelled = True
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
