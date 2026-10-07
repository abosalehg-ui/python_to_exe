"""Start a built program so that it can be stopped *with everything it started*.

A one-file PyInstaller EXE is two processes: the bootloader unpacks the app
and starts it as a child. Killing the bootloader after a timeout (what
``subprocess.run(timeout=...)`` does) left that child running — measured: four
orphaned copies of a test server per comparison on Linux, and the smoke test
did the same to every GUI app that outlived its timeout since 1.3.

So the program gets its own process group (a new session on POSIX, a new
process group on Windows) and a timeout ends the whole group.
"""

import os
import signal
import subprocess
import sys
from typing import Optional


def _windows(platform: Optional[str]) -> bool:
    return (platform if platform is not None else sys.platform).startswith("win")


def group_kwargs(platform: Optional[str] = None) -> dict:
    """``Popen`` arguments that put the program in a group of its own."""
    if _windows(platform):
        return {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200)}
    return {"start_new_session": True}


def kill_tree(process, platform: Optional[str] = None, run=subprocess.run) -> None:
    """Kill ``process`` and every process in its group; never raises."""
    if process.poll() is not None and _windows(platform):
        return
    try:
        if _windows(platform):
            # /T: the whole tree; /F: without asking. Ships with Windows.
            run(["taskkill", "/F", "/T", "/PID", str(process.pid)],
                capture_output=True, timeout=30)
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError, AttributeError):
        pass
    try:
        process.kill()
    except OSError:
        pass
