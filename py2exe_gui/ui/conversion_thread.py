"""Background thread that runs the build engine and streams output to the UI."""

from datetime import datetime
from typing import Dict, Optional

from py2exe_gui.qt import Signal
from py2exe_gui.strings import S
from py2exe_gui.ui.streaming_thread import CANCELLED, OK, StreamingProcessThread


class ConversionThread(StreamingProcessThread):
    """خيط منفصل لعملية التحويل."""

    #: (succeeded, message for the notice, outcome code — see streaming_thread)
    finished_signal = Signal(bool, str, str)

    def __init__(self, command, output_dir, engine: str = "pyinstaller",
                 popen_kwargs: Optional[Dict] = None):
        super().__init__()
        self.command = command
        self.output_dir = output_dir
        # The engine's phases label the progress bar; ``popen_kwargs`` is
        # what ``build_runner.popen_options`` returned for it (the build
        # interpreter's environment; stdin policy is re-derived from the name).
        self.engine = engine
        self.popen_kwargs = dict(popen_kwargs or {})

    def run(self):
        self.log_signal.emit("═" * 60)
        self.log_signal.emit(
            S.CONV_START.format(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        self.log_signal.emit("═" * 60)
        self.log_signal.emit(S.CONV_COMMAND.format(cmd=" ".join(self.command)))
        self.log_signal.emit("─" * 60)

        # Progress follows the phase the engine announces rather than counting
        # how many lines it happened to print. See build_stages.
        code = self.stream(self.command, self.output_dir, engine=self.engine,
                           env=self.popen_kwargs.get("env"), track_stages=True)

        if code == CANCELLED:
            self.finished_signal.emit(False, S.CONV_CANCELLED, code)
            return
        if code == OK:
            self.progress_signal.emit(100)
            self.log_signal.emit("\n" + "═" * 60)
            self.log_signal.emit(S.CONV_SUCCESS)
            self.log_signal.emit("═" * 60)
            self.finished_signal.emit(True, S.CONV_SUCCESS, code)
            return
        if self.error:
            # The engine could not be started at all (missing interpreter…).
            self.log_signal.emit(S.CONV_ERROR.format(error=self.error))
        self.log_signal.emit("\n" + "═" * 60)
        self.log_signal.emit(S.CONV_FAILED)
        self.log_signal.emit("═" * 60)
        self.finished_signal.emit(False, S.CONV_FAILED_MSG, code)
