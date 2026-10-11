"""One way to run a command in the background and stream its output.

Five threads (build, batch, diagnostic run, installer, environment) each had
their own copy of the same ``Popen`` loop: open the pipe, read it line by
line, check a cancel flag, terminate, wait. They differed only in what they
did with the lines and what they emitted at the end, and that is all a
subclass has to decide now. The loop itself is ``build_runner.stream_command``
— the same function the command line runs a build through — so the GUI and
the CLI cannot drift apart on how a process is started or stopped.

What a run reports is a *code*, not a sentence: ``OK``, ``FAILED``,
``CANCELLED``, ``NOT_FOUND`` (the program is not installed) or ``ERROR``
(the OS refused to start it). The window turns a code into the active
locale's text (``MainWindow.thread_error_text``); a thread never formats a
message of its own, which is how "ISCC.exe not found" used to reach an
Arabic user untranslated.
"""

import subprocess
from typing import Callable, Dict, List, Optional

from py2exe_gui.core.build_runner import stream_command
from py2exe_gui.qt import QThread, Signal

#: Outcome codes. Every ``finished_signal`` that carries a status uses one.
OK = "ok"
FAILED = "failed"
CANCELLED = "cancelled"
NOT_FOUND = "not_found"
TIMED_OUT = "timed_out"
ERROR = "error"

CODES = frozenset({OK, FAILED, CANCELLED, NOT_FOUND, TIMED_OUT, ERROR})


class StreamingProcessThread(QThread):
    """A ``QThread`` that can run commands through ``stream_command``.

    Subclasses implement ``run()`` and call :meth:`stream` once or several
    times. Lines go to ``log_signal`` unless ``on_line`` is given; stage
    changes (a build engine's phases) go to ``progress_signal`` and
    ``stage_signal``. :meth:`cancel` terminates whatever is running and makes
    the next :meth:`stream` return ``CANCELLED`` without starting anything.
    """

    log_signal = Signal(str)
    progress_signal = Signal(int)
    #: Stage key from ``core.build_stages``, so the window can label the bar.
    stage_signal = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None
        self.is_cancelled = False
        #: The last command's exit code (None if it never started).
        self.returncode: Optional[int] = None
        #: What the OS said when a command could not start ('' otherwise).
        self.error = ""

    def stream(self, command: List[str], cwd: str = "", engine: str = "pyinstaller",
               env: Optional[Dict[str, str]] = None,
               on_line: Optional[Callable[[str], None]] = None,
               track_stages: bool = False) -> str:
        """Run ``command`` to completion; returns one of the outcome codes.

        ``engine`` names the build engine whose phases are tracked (and whose
        stdin policy applies, see ``build_runner.popen_options``); for a
        command that is not a build, PyInstaller's harmless defaults do.
        """
        self.returncode = None
        self.error = ""
        if self.is_cancelled:
            return CANCELLED

        def popen(*args, **kwargs):
            self.process = subprocess.Popen(*args, **kwargs)
            return self.process

        def line(text: str):
            if on_line is not None:
                on_line(text)
            else:
                self.log_signal.emit(text)

        def stage(key: str, percent: int):
            self.progress_signal.emit(percent)
            self.stage_signal.emit(key)

        try:
            code = stream_command(command, cwd, line, stage if track_stages else None,
                                  popen=popen, engine=engine, env=env)
        except FileNotFoundError as e:
            self.error = str(e)
            return NOT_FOUND
        except (OSError, ValueError) as e:  # ValueError: a closed pipe mid-read
            self.error = str(e)
            return ERROR
        finally:
            self.process = None
        self.returncode = code
        if self.is_cancelled:
            return CANCELLED
        return OK if code == 0 else FAILED

    def cancel(self):
        """Stop the running command (if any) and refuse to start another."""
        self.is_cancelled = True
        process = self.process
        if process is not None:
            try:
                process.terminate()
            except OSError:
                pass


__all__ = [
    "CANCELLED", "CODES", "ERROR", "FAILED", "NOT_FOUND", "OK", "TIMED_OUT",
    "StreamingProcessThread",
]
