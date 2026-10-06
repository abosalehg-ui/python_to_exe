"""Post-build smoke test: briefly run the produced EXE and report the outcome."""

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Optional


@dataclass
class SmokeResult:
    """Outcome of a smoke test run."""

    ran: bool                       # False when the test wasn't attempted
    exited_cleanly: bool            # True when process exited within the timeout
    returncode: Optional[int]
    error: str = ""
    # Everything the EXE printed (stdout + stderr, capped). The diagnostics
    # read the traceback from here; ``error`` stays a short summary.
    output: str = ""

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
    engine: str = "pyinstaller",
) -> Optional[str]:
    """Return the path to the produced EXE, or None if not found.

    Mirrors PyInstaller's layout:
      onefile  : <output_dir>/dist/<name>.exe
      onedir   : <output_dir>/dist/<name>/<name>.exe
    Also tries name-without-extension for non-Windows hosts. Nuitka's folder
    builds are ``dist/<name>.dist/<name>.exe`` (it always adds ``.dist``).
    """
    if not output_dir or not output_name:
        return None

    candidates = []
    base = os.path.join(output_dir, "dist")
    folder = output_name + ".dist" if engine == "nuitka" else output_name
    for ext in (".exe", ""):
        if onefile:
            candidates.append(os.path.join(base, output_name + ext))
        else:
            candidates.append(os.path.join(base, folder, output_name + ext))
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


# Enough for any traceback; a chatty app must not balloon the UI's memory.
MAX_OUTPUT_CHARS = 20000


def _text(value) -> str:
    """Normalise captured output: TimeoutExpired hands back bytes even in text mode."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _combined(stdout, stderr) -> str:
    parts = [p for p in (_text(stdout), _text(stderr)) if p]
    return "\n".join(parts)[-MAX_OUTPUT_CHARS:]


def run_smoke_test(
    exe_path: str, timeout: float = 5.0, cwd: Optional[str] = None
) -> SmokeResult:
    """Launch ``exe_path`` and report whether it stays alive without crashing.

    For GUI apps that run indefinitely, hitting the timeout is treated as
    success (the EXE started without immediate failure).

    ``cwd`` sets the folder the EXE starts in. Running it from somewhere other
    than its own folder is what a desktop shortcut does, and it is what
    exposes relative paths that only worked because of where it was built.
    """
    if not exe_path or not os.path.isfile(exe_path):
        return SmokeResult(
            ran=False, exited_cleanly=False, returncode=None,
            error="Executable not found",
        )
    # An app built with the Runtime Kit would otherwise sit on its crash
    # dialog (Windows) and look alive until the timeout.
    env = dict(os.environ, P2E_RUNTIME_NO_DIALOGS="1")
    try:
        completed = subprocess.run(
            [exe_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env=env,
        )
    except subprocess.TimeoutExpired as e:
        return SmokeResult(
            ran=True, exited_cleanly=False, returncode=None,
            error="", output=_combined(e.stdout, e.stderr),
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
        output=_combined(completed.stdout, completed.stderr),
    )


def run_from_neutral_folder(exe_path: str, timeout: float = 5.0) -> SmokeResult:
    """``run_smoke_test`` started from a fresh temporary folder.

    The folder is removed best-effort: on Windows a one-file EXE's child
    process can outlive the timeout kill and keep the folder busy, and a
    failed cleanup must not turn a finished test into a crash.
    """
    neutral = tempfile.mkdtemp(prefix="p2e_run_")
    try:
        return run_smoke_test(exe_path, timeout=timeout, cwd=neutral)
    finally:
        shutil.rmtree(neutral, ignore_errors=True)
