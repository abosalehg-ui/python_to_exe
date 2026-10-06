"""Background thread that creates or refreshes a project's build environment.

Runs the commands of a ``venv_manager.EnvPlan`` in order and streams their
output to the log. Packages inferred from the imports are installed together
first; if that fails (one guessed name is wrong, say), they are retried one by
one so a single bad name doesn't leave the environment empty.
"""

import subprocess
from datetime import datetime

from PyQt5.QtCore import QThread, pyqtSignal

from py2exe_gui.core.venv_manager import (
    folder_size,
    quote_command,
    single_install_command,
    write_metadata,
)
from py2exe_gui.strings import S


class EnvThread(QThread):
    """Execute an environment plan."""

    log_signal = pyqtSignal(str)
    #: (succeeded, names that could not be installed, error message)
    finished_signal = pyqtSignal(bool, list, str)

    def __init__(self, plan, base_python: str = ""):
        super().__init__()
        self.plan = plan
        self.base_python = base_python
        self.process = None
        self.is_cancelled = False

    def run(self):
        plan = self.plan
        self.log_signal.emit(S.LOG_ENV_START.format(path=plan.env_dir))
        for command in plan.setup:
            ok, error = self._run(command)
            if not ok:
                self.finished_signal.emit(False, [], error)
                return

        failed = []
        if plan.install:
            ok, error = self._run(plan.install)
            requirements = plan.requirements
            if not ok and requirements is not None and requirements.origin == "scan":
                self.log_signal.emit(S.LOG_ENV_RETRY_SINGLE)
                for name in requirements.args:
                    if self.is_cancelled:
                        break
                    single_ok, _ = self._run(single_install_command(plan, name))
                    if not single_ok:
                        failed.append(name)
                        self.log_signal.emit(S.LOG_ENV_PACKAGE_FAILED.format(name=name))
            elif not ok:
                # A requirements/lock file the user wrote: don't second-guess it.
                self.finished_signal.emit(False, [], error)
                return

        if self.is_cancelled:
            self.finished_signal.emit(False, failed, "cancelled")
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

    def _run(self, command):
        """Run one command, streaming its output. Returns (ok, last lines)."""
        if self.is_cancelled:
            return False, "cancelled"
        self.log_signal.emit(S.LOG_ENV_STEP.format(cmd=quote_command(command)))
        tail = []
        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            for line in self.process.stdout:
                line = line.rstrip()
                if line:
                    self.log_signal.emit(line)
                    tail = (tail + [line])[-5:]
            self.process.wait()
        except OSError as e:
            return False, str(e)
        if self.process.returncode != 0:
            return False, "\n".join(tail) or f"exit {self.process.returncode}"
        return True, ""

    def cancel(self):
        self.is_cancelled = True
        if self.process:
            self.process.terminate()
