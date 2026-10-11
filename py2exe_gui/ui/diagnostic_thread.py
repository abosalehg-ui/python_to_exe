"""Background thread for the doctor's diagnostic run.

A windowed EXE that crashes shows its traceback in a dialog — or nowhere —
so the smoke test cannot read it. The diagnostic run builds the same app with
the console kept on, into a side folder, runs it from a neutral directory and
hands back everything it printed.
"""

import os
from typing import Dict, Optional

from py2exe_gui.core.diagnostics import build_name
from py2exe_gui.core.smoke_test import locate_built_executable, run_from_neutral_folder
from py2exe_gui.qt import Signal
from py2exe_gui.strings import S
from py2exe_gui.ui.streaming_thread import OK, StreamingProcessThread


class DiagnosticThread(StreamingProcessThread):
    """Build a console copy of the app, run it, report its output."""

    #: (built_ok, exe_output, build_log)
    finished_signal = Signal(bool, str, str)

    def __init__(self, command, config, timeout: float = 8.0,
                 popen_kwargs: Optional[Dict] = None):
        super().__init__()
        self.popen_kwargs = dict(popen_kwargs or {})
        self.command = command
        self.config = config
        self.timeout = timeout

    def run(self):
        build_lines = []
        try:
            os.makedirs(self.config.output_dir, exist_ok=True)
        except OSError as e:
            self.finished_signal.emit(False, "", str(e))
            return
        self.log_signal.emit(S.LOG_DIAG_START.format(path=self.config.output_dir))
        # The build's own output is collected, not streamed: it is evidence
        # for the doctor, and only its verdict belongs in the log.
        code = self.stream(self.command, self.config.output_dir,
                           engine=getattr(self.config, "engine", "pyinstaller"),
                           env=self.popen_kwargs.get("env"), on_line=build_lines.append)
        if self.error:
            build_lines.append(self.error)
        build_log = "\n".join(build_lines)
        if code != OK:
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
