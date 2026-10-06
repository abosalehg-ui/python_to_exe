"""Allow only one running copy of the app per user session.

Windows uses a named mutex (``CreateMutexW`` + ``ERROR_ALREADY_EXISTS``),
released by the system when the process ends, however it ends. POSIX systems
use an ``fcntl`` lock on a file in the user's state folder, likewise released
when the process dies. A second copy shows a message and exits; bringing the
first copy's window to the front is not attempted.
"""

import os
import sys
from typing import Any, Optional, Tuple

from p2e_runtime import _native
from p2e_runtime.paths import safe_name, user_state_dir

ERROR_ALREADY_EXISTS = 183
DEFAULT_MESSAGE = "{app} is already running."


class WindowsMutexApi:
    """The two kernel32 calls the guard needs, behind a seam for tests."""

    def __init__(self):
        import ctypes
        from ctypes import wintypes

        self._ctypes = ctypes
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
        self._kernel32.CreateMutexW.restype = wintypes.HANDLE
        self._kernel32.CreateMutexW.argtypes = (
            ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR,
        )
        self._kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)

    def create_mutex(self, name: str) -> Tuple[Any, int]:
        handle = self._kernel32.CreateMutexW(None, False, name)
        return handle, self._ctypes.get_last_error()

    def close(self, handle: Any) -> None:
        self._kernel32.CloseHandle(handle)


class InstanceLock:
    """Held for the life of the process. ``release()`` is only for tests."""

    def __init__(self, kind: str, handle: Any, api: Any = None, path: str = ""):
        self.kind = kind
        self.handle = handle
        self.path = path
        self._api = api

    def release(self) -> None:
        if self.handle is None:
            return
        if self.kind == "mutex":
            self._api.close(self.handle)
        else:
            try:
                os.close(self.handle)
            except OSError:
                pass
        self.handle = None


def mutex_name(instance_id: str) -> str:
    # "Local\" scopes the name to the user's session: two people logged in
    # to the same machine can each run the app.
    return "Local\\p2e-" + safe_name(instance_id)


def _acquire_mutex(instance_id: str, api: Any) -> Optional[InstanceLock]:
    api = api or WindowsMutexApi()
    handle, error = api.create_mutex(mutex_name(instance_id))
    if not handle:
        raise OSError(error, "CreateMutexW failed")
    if error == ERROR_ALREADY_EXISTS:
        api.close(handle)
        return None
    return InstanceLock("mutex", handle, api)


def lock_file_path(instance_id: str, lock_dir: Optional[str] = None) -> str:
    folder = lock_dir or user_state_dir(instance_id)
    return os.path.join(folder, f"{safe_name(instance_id)}.lock")


def _acquire_file_lock(instance_id: str, lock_dir: Optional[str]) -> Optional[InstanceLock]:
    import fcntl

    path = lock_file_path(instance_id, lock_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return None
    try:
        os.ftruncate(fd, 0)
        os.write(fd, str(os.getpid()).encode("ascii"))
    except OSError:
        pass
    return InstanceLock("file", fd, path=path)


def acquire(instance_id: str, platform: Optional[str] = None, api: Any = None,
            lock_dir: Optional[str] = None) -> Optional[InstanceLock]:
    """Take the instance lock; ``None`` if another copy already holds it."""
    plat = platform if platform is not None else sys.platform
    if plat == "win32":
        return _acquire_mutex(instance_id, api)
    return _acquire_file_lock(instance_id, lock_dir)


_lock: Optional[InstanceLock] = None


def ensure_single_instance(instance_id: str, app_name: str = "", message: str = "",
                           exit_code: int = 0, rtl: bool = False,
                           platform: Optional[str] = None, api: Any = None,
                           lock_dir: Optional[str] = None) -> InstanceLock:
    """Exit with ``exit_code`` (after showing ``message``) if already running."""
    global _lock
    if _lock is not None and _lock.handle is not None:
        return _lock
    lock = acquire(instance_id, platform=platform, api=api, lock_dir=lock_dir)
    if lock is None:
        name = app_name or instance_id
        try:
            text = (message or DEFAULT_MESSAGE).format(app=name)
        except (KeyError, IndexError, ValueError):
            text = message
        if _native.show(text, name, _native.KIND_INFO, rtl=rtl, platform=platform) is None:
            _native.to_stderr(text)
        raise SystemExit(exit_code)
    _lock = lock
    return lock


def release() -> None:
    """Give up the lock early — before starting the updated copy of the app.

    Otherwise the new copy can start while this one is still exiting, find
    the lock taken, and quit as "already running".
    """
    global _lock
    if _lock is not None:
        _lock.release()
        _lock = None
