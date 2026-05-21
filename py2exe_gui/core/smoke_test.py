"""Post-build smoke test: briefly run the produced EXE and report the outcome."""

import os
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class SmokeResult:
    """Outcome of a smoke test run."""

    ran: bool                       # False when the test wasn't attempted
    exited_cleanly: bool            # True when process exited within the timeout
    returncode: Optional[int]
    error: str = ""

    @property
    def passed(self) -> bool:
        """A reasonable definition of 'passed': it ran and didn't crash."""
        if not self.ran:
            return False
        if self.returncode is None:
            # Process was killed by timeout — that's OK for GUI apps that
            # would normally stay running.
            return True
        return self.returncode == 0


def locate_built_executable(
    output_dir: str,
    output_name: str,
    onefile: bool,
) -> Optional[str]:
    """Return the path to the produced EXE, or None if not found.

    Mirrors PyInstaller's layout:
      onefile  : <output_dir>/dist/<name>.exe
      onedir   : <output_dir>/dist/<name>/<name>.exe
    Also tries name-without-extension for non-Windows hosts.
    """
    if not output_dir or not output_name:
        return None

    candidates = []
    base = os.path.join(output_dir, "dist")
    for ext in (".exe", ""):
        if onefile:
            candidates.append(os.path.join(base, output_name + ext))
        else:
            candidates.append(os.path.join(base, output_name, output_name + ext))
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def run_smoke_test(exe_path: str, timeout: float = 5.0) -> SmokeResult:
    """Launch ``exe_path`` and report whether it stays alive without crashing.

    For GUI apps that run indefinitely, hitting the timeout is treated as
    success (the EXE started without immediate failure).
    """
    if not exe_path or not os.path.isfile(exe_path):
        return SmokeResult(
            ran=False, exited_cleanly=False, returncode=None,
            error="Executable not found",
        )
    try:
        completed = subprocess.run(
            [exe_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return SmokeResult(
            ran=True, exited_cleanly=False, returncode=None,
            error="",
        )
    except OSError as e:
        return SmokeResult(
            ran=False, exited_cleanly=False, returncode=None,
            error=str(e),
        )
    return SmokeResult(
        ran=True,
        exited_cleanly=True,
        returncode=completed.returncode,
        error=(completed.stderr or "")[:500],
    )
