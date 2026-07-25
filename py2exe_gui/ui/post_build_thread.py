"""Background thread for post-build actions (code signing + smoke test).

Both steps shell out and can block for a long time — signing waits on a
timestamp server (up to 120s) and the smoke test deliberately waits for the
new EXE. Running them inline froze the whole window with no indication that
anything was happening.
"""

import subprocess

from PyQt5.QtCore import QThread, pyqtSignal

from py2exe_gui.core import (
    build_signtool_command,
    redact_password,
    run_smoke_test,
)
from py2exe_gui.strings import S


class PostBuildThread(QThread):
    """Signs and/or smoke-tests a freshly built executable."""

    log_signal = pyqtSignal(str)
    #: (signing_attempted, signing_succeeded) — lets the caller decide whether
    #: to continue to the installer step.
    finished_signal = pyqtSignal(bool, bool)

    def __init__(
        self,
        exe_path: str,
        signing_config=None,
        smoke_enabled: bool = False,
        smoke_timeout: float = 5.0,
        sign_timeout: float = 120.0,
    ):
        super().__init__()
        self.exe_path = exe_path
        self.signing_config = signing_config
        self.smoke_enabled = smoke_enabled
        self.smoke_timeout = smoke_timeout
        self.sign_timeout = sign_timeout
        self.process = None
        self.is_cancelled = False

    def run(self):
        signed_attempted = False
        signed_ok = False

        if self.signing_config is not None and self.signing_config.enabled:
            signed_attempted = True
            signed_ok = self._sign()

        if not self.is_cancelled and self.smoke_enabled:
            self._smoke_test()

        self.finished_signal.emit(signed_attempted, signed_ok)

    # ── Steps ──────────────────────────────────────────────────────────────

    def _sign(self) -> bool:
        cmd, error = build_signtool_command(self.exe_path, self.signing_config)
        if error or cmd is None:
            self.log_signal.emit(
                S.LOG_SIGNING_SKIPPED.format(reason=error or "unknown")
            )
            return False

        self.log_signal.emit(S.LOG_SIGNING_START)
        # Log a redacted copy so the certificate password never reaches the log.
        self.log_signal.emit(" ".join(redact_password(cmd)))
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.sign_timeout
            )
        except FileNotFoundError:
            self.log_signal.emit(
                S.LOG_SIGNING_FAIL.format(error="signtool not found on PATH")
            )
            return False
        except subprocess.TimeoutExpired:
            self.log_signal.emit(S.LOG_SIGNING_FAIL.format(error="timed out"))
            return False
        except OSError as e:
            self.log_signal.emit(S.LOG_SIGNING_FAIL.format(error=str(e)))
            return False

        if result.returncode == 0:
            self.log_signal.emit(S.LOG_SIGNING_OK)
            return True
        message = (result.stderr or result.stdout or "").strip()[:300]
        self.log_signal.emit(S.LOG_SIGNING_FAIL.format(error=message))
        return False

    def _smoke_test(self) -> None:
        self.log_signal.emit(S.LOG_SMOKE_START)
        result = run_smoke_test(self.exe_path, timeout=self.smoke_timeout)
        if result.passed:
            self.log_signal.emit(S.LOG_SMOKE_OK)
        else:
            self.log_signal.emit(
                S.LOG_SMOKE_FAIL.format(
                    error=result.error or f"exit={result.returncode}"
                )
            )

    def cancel(self):
        self.is_cancelled = True
