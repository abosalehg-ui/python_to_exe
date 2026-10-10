"""Start a built program so that it can be stopped *with everything it started*.

A one-file PyInstaller EXE is two processes: the bootloader unpacks the app
and starts it as a child. Killing the bootloader after a timeout (what
``subprocess.run(timeout=...)`` does) left that child running — measured: four
orphaned copies of a test server per comparison on Linux, and the smoke test
did the same to every GUI app that outlived its timeout since 1.3.

So the program gets its own process group (a new session on POSIX, a new
process group on Windows) and a timeout ends the whole group.

``kill_tree`` only ever signals a group the program itself leads: a process
that was not started with ``group_kwargs`` (or a stand-in with a made-up pid)
shares *our* group, and ``killpg`` on it would take down the caller and
everything around it — a CI runner, a container's init — as happened once.
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


def leads_own_group(pid) -> bool:
    """True when ``pid`` is the leader of a process group that is not ours.

    That is exactly the process ``group_kwargs`` started: its pid is its group
    id. Anything else (a pid in our own group, pid 1, a process that is gone,
    a fake) must never be the target of ``killpg``.
    """
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 1:
        return False
    try:
        group = os.getpgid(pid)
        return group == pid and group != os.getpgid(0)
    except (OSError, AttributeError):
        return False


def kill_tree(process, platform: Optional[str] = None, run=subprocess.run) -> None:
    """Kill ``process`` and every process in its group; never raises."""
    if process.poll() is not None and _windows(platform):
        return
    try:
        if _windows(platform):
            # /T: the whole tree; /F: without asking. Ships with Windows.
            run(["taskkill", "/F", "/T", "/PID", str(process.pid)],
                capture_output=True, timeout=30)
        elif leads_own_group(getattr(process, "pid", None)):
            os.killpg(process.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError, AttributeError):
        pass
    try:
        process.kill()
    except OSError:
        pass
