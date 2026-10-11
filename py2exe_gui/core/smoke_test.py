"""Post-build smoke test: briefly run the produced EXE and report the outcome."""

import os
import shutil
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from typing import List, Optional

from py2exe_gui.core.process_tree import group_kwargs, kill_tree, read_tail


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


def _capped_reader(stream, into: List[str]) -> threading.Thread:
    """A thread draining ``stream`` into ``into[0]``, keeping the tail only."""
    def run():
        into[0] = read_tail(stream, MAX_OUTPUT_CHARS)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


def run_smoke_test(
    exe_path: str, timeout: float = 5.0, cwd: Optional[str] = None,
    popen=subprocess.Popen,
) -> SmokeResult:
    """Launch ``exe_path`` and report whether it stays alive without crashing.

    For GUI apps that run indefinitely, hitting the timeout is treated as
    success (the EXE started without immediate failure).

    ``cwd`` sets the folder the EXE starts in. Running it from somewhere other
    than its own folder is what a desktop shortcut does, and it is what
    exposes relative paths that only worked because of where it was built.

    Output is read by two threads that keep only the last
    ``MAX_OUTPUT_CHARS`` of each stream: ``communicate()`` buffered everything
    a chatty app printed until the timeout, which for a server logging in a
    loop was hundreds of MB.
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
        # Its own process group: a timeout must also end what the EXE started
        # (a one-file EXE's app runs as a child of the bootloader).
        process = popen(
            [exe_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
            cwd=cwd, env=env, **group_kwargs(),
        )
    except OSError as e:
        return SmokeResult(
            ran=False, exited_cleanly=False, returncode=None,
            error=str(e),
        )
    out, err = [""], [""]
    readers = [_capped_reader(process.stdout, out), _capped_reader(process.stderr, err)]
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_tree(process)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        for reader in readers:
            reader.join(5)
        return SmokeResult(
            ran=True, exited_cleanly=False, returncode=None,
            error="", output=_combined(out[0], err[0]),
        )
    for reader in readers:
        reader.join(5)
    stdout, stderr = out[0], err[0]
    return SmokeResult(
        ran=True,
        exited_cleanly=True,
        returncode=process.returncode,
        error=(stderr or "")[:500],
        output=_combined(stdout, stderr),
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
