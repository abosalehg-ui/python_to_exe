"""Packaging off the UI thread: ``core.packagers.run_packaging`` for the
formats this host can build, with the consent already given (or refused)
by the window before the thread starts."""

from py2exe_gui.core.packagers import run_packaging
from py2exe_gui.qt import QThread, Signal


class PackageThread(QThread):
    """Builds the packages of ``spec``; reports log lines and the results."""

    log_signal = Signal(str)
    #: list of PackageResult
    finished_signal = Signal(object)

    def __init__(self, spec, formats, allow_download: bool = False):
        super().__init__()
        self.spec = spec
        self.formats = list(formats)
        self.allow_download = allow_download

    def run(self):
        consent = (lambda _url, _dir: True) if self.allow_download else None
        results = run_packaging(self.spec, self.formats, log=self.log_signal.emit,
                                download_consent=consent)
        self.finished_signal.emit(results)
