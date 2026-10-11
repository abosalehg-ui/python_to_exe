"""Background threads for the build environment and other blocking commands.

``EnvThread`` runs the commands of a ``venv_manager.EnvPlan`` in order and
streams their output to the log. Packages inferred from the imports are
installed together first; if that fails (one guessed name is wrong, say),
they are retried one by one so a single bad name doesn't leave the
environment empty.

``CommandThread`` runs one command to completion and hands back its exit
code and output: the pip installs behind the consent dialogs, ``pip freeze``
for the lock file. Each of them used to run ``subprocess.run`` on the UI
thread, which froze the window for the duration with no sign of life.
``TaskThread`` does the same for a Python callable (the update check, which
is a network call rather than a command).
"""

import subprocess
from datetime import datetime
from typing import Callable, List, Optional

from py2exe_gui.core.venv_manager import (
    folder_size,
    quote_command,
    single_install_command,
    write_metadata,
)
from py2exe_gui.qt import QThread, Signal
from py2exe_gui.strings import S
from py2exe_gui.ui.streaming_thread import (
    CANCELLED,
    ERROR,
    FAILED,
    OK,
    TIMED_OUT,
    StreamingProcessThread,
)


class EnvThread(StreamingProcessThread):
    """Execute an environment plan."""

    #: (succeeded, names that could not be installed, outcome code — '' when ok)
    finished_signal = Signal(bool, list, str)

    def __init__(self, plan, base_python: str = ""):
        super().__init__()
        self.plan = plan
        self.base_python = base_python

    def run(self):
        plan = self.plan
        self.log_signal.emit(S.LOG_ENV_START.format(path=plan.env_dir))
        for command in plan.setup:
            code = self._run(command)
            if code != OK:
                self.finished_signal.emit(False, [], code)
                return

        failed = []
        if plan.install:
            code = self._run(plan.install)
            requirements = plan.requirements
            if code != OK and requirements is not None and requirements.origin == "scan":
                self.log_signal.emit(S.LOG_ENV_RETRY_SINGLE)
                for name in requirements.args:
                    if self.is_cancelled:
                        break
                    if self._run(single_install_command(plan, name)) != OK:
                        failed.append(name)
                        self.log_signal.emit(S.LOG_ENV_PACKAGE_FAILED.format(name=name))
            elif code != OK:
                # A requirements/lock file the user wrote: don't second-guess it.
                self.finished_signal.emit(False, [], code)
                return

        if self.is_cancelled:
            self.finished_signal.emit(False, failed, CANCELLED)
            return

        requirements = plan.requirements
        write_metadata(plan.env_dir, {
            "created": datetime.now().isoformat(timespec="seconds"),
            "base_python": self.base_python,
            "origin": requirements.origin if requirements else "",
            "requirements": list(requirements.args) if requirements else [],
            "failed": failed,
            "uv": bool(plan.uv),
            # Measured once here: walking a large environment on every refresh
            # of the tab would make it stutter.
            "size_bytes": folder_size(plan.env_dir),
        })
        self.finished_signal.emit(True, failed, "")

    def _run(self, command) -> str:
        """Run one command, streaming its output; returns an outcome code."""
        if self.is_cancelled:
            return CANCELLED
        self.log_signal.emit(S.LOG_ENV_STEP.format(cmd=quote_command(command)))

        def line(text: str):
            text = text.rstrip()
            if text:
                self.log_signal.emit(text)

        code = self.stream(command, on_line=line)
        if self.error:
            self.log_signal.emit(self.error)
        return code


class CommandThread(QThread):
    """Run one command off the UI thread; report ``(returncode, output)``.

    ``returncode`` is -1 when the command never ran or timed out, and
    ``code`` says which (an outcome code from ``streaming_thread``). The
    output is stdout and stderr together, in order, decoded leniently.
    """

    #: (returncode, combined output)
    finished_signal = Signal(int, str)

    #: How the command is run; tests swap it without touching the global
    #: ``subprocess.run`` that the window's own probes also use.
    runner = staticmethod(subprocess.run)

    def __init__(self, command: List[str], timeout: Optional[float] = None, cwd: str = ""):
        super().__init__()
        self.command = list(command)
        self.timeout = timeout
        self.cwd = cwd
        self.returncode = -1
        self.output = ""
        self.code = ""

    def run(self):
        try:
            result = self.runner(
                self.command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                encoding="utf-8", errors="replace", timeout=self.timeout,
                cwd=self.cwd or None, check=False,
            )
        except subprocess.TimeoutExpired as e:
            self.code = TIMED_OUT
            partial = e.stdout or ""
            self.output = partial.decode("utf-8", "replace") if isinstance(partial, bytes) \
                else partial
        except (OSError, subprocess.SubprocessError) as e:
            self.code = ERROR
            self.output = str(e)
        else:
            self.returncode = result.returncode
            self.output = result.stdout or ""
            self.code = OK if result.returncode == 0 else FAILED
        self.finished_signal.emit(self.returncode, self.output)


class TaskThread(QThread):
    """Run a callable off the UI thread; report what it returned.

    An exception becomes ``error`` and the result ``None``: a background task
    must never take the window down with it.
    """

    #: (result, error text — '' when the task returned normally)
    finished_signal = Signal(object, str)

    def __init__(self, task: Callable[[], object]):
        super().__init__()
        self.task = task
        self.result = None
        self.error = ""

    def run(self):
        try:
            self.result = self.task()
        except Exception as e:  # noqa: BLE001 - reported, never raised across threads
            self.error = str(e) or e.__class__.__name__
        self.finished_signal.emit(self.result, self.error)
