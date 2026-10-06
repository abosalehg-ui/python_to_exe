"""Give a windowed app somewhere to write: a rotating log file.

A PyInstaller build made with ``--windowed`` (or ``--noconsole``) starts with
``sys.stdout`` and ``sys.stderr`` set to ``None``. ``print()`` quietly does
nothing, but ``sys.stdout.write(...)`` — or any library that does it, such
as tqdm or uvicorn — crashes the app, and tracebacks vanish. Redirecting the
missing streams to a file fixes both, and keeps the output for later.

Only missing streams are replaced: an app started from a console keeps
printing to it.
"""

import io
import os
import sys
import threading
import time
from typing import Optional

from p2e_runtime.config import DEFAULT_LOG_BACKUPS, DEFAULT_LOG_MAX_BYTES
from p2e_runtime.paths import safe_name, user_state_dir


class RotatingLogStream(io.TextIOBase):
    """A text stream appending to ``path``, rotated at ``max_bytes``.

    ``app.log`` becomes ``app.log.1`` (and so on, up to ``backups``) when it
    would grow past ``max_bytes``. Writes are unbuffered, so the last lines
    before a crash are on disk. Thread-safe; never raises from ``write``.
    """

    def __init__(self, path: str, max_bytes: int = DEFAULT_LOG_MAX_BYTES,
                 backups: int = DEFAULT_LOG_BACKUPS):
        super().__init__()
        self.path = path
        self.max_bytes = max(1024, int(max_bytes))
        self.backups = max(0, int(backups))
        self._lock = threading.Lock()
        self._file = None
        self._size = 0
        self.buffer = _BinaryView(self)
        self._open()

    # ── io.TextIOBase ──────────────────────────────────────────────────────

    @property
    def encoding(self) -> str:  # type: ignore[override]
        return "utf-8"

    @property
    def errors(self) -> str:  # type: ignore[override]
        return "replace"

    def writable(self) -> bool:
        return True

    def isatty(self) -> bool:
        return False

    def write(self, text) -> int:  # type: ignore[override]
        if not isinstance(text, str):
            text = str(text)
        self.write_bytes(text.encode("utf-8", "replace"))
        return len(text)

    def flush(self) -> None:
        pass  # writes are unbuffered

    def close(self) -> None:
        with self._lock:
            if self._file is not None:
                try:
                    self._file.close()
                except OSError:
                    pass
                self._file = None
        super().close()

    # ── Internals ──────────────────────────────────────────────────────────

    def write_bytes(self, data: bytes) -> None:
        with self._lock:
            try:
                if self._file is None:
                    self._open()
                if self._file is None:
                    return
                if self._size and self._size + len(data) > self.max_bytes:
                    self._rotate()
                self._file.write(data)
                self._size += len(data)
            except (OSError, ValueError):
                pass  # a full disk must not crash the app it is logging

    def _open(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            self._file = open(self.path, "ab", buffering=0)
            self._size = self._file.tell()
        except OSError:
            self._file = None
            self._size = 0

    def _rotate(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None
        try:
            if self.backups == 0:
                os.remove(self.path)
            else:
                for index in range(self.backups - 1, 0, -1):
                    older = f"{self.path}.{index}"
                    if os.path.exists(older):
                        os.replace(older, f"{self.path}.{index + 1}")
                os.replace(self.path, f"{self.path}.1")
        except OSError:
            pass  # e.g. another instance holds the file open on Windows
        self._open()


class _BinaryView:
    """``sys.stdout.buffer`` for code that writes bytes."""

    def __init__(self, stream: RotatingLogStream):
        self._stream = stream

    def write(self, data) -> int:
        data = bytes(data)
        self._stream.write_bytes(data)
        return len(data)

    def flush(self) -> None:
        pass


def log_path(app_name: str, base_dir: Optional[str] = None) -> str:
    folder = os.path.join(base_dir or user_state_dir(app_name), "logs")
    return os.path.join(folder, f"{safe_name(app_name)}.log")


_stream: Optional[RotatingLogStream] = None


def redirect(app_name: str, app_version: str = "", max_bytes: int = DEFAULT_LOG_MAX_BYTES,
             backups: int = DEFAULT_LOG_BACKUPS, base_dir: Optional[str] = None) -> Optional[str]:
    """Send ``sys.stdout``/``sys.stderr`` to a log file *if they are missing*.

    Returns the log file's path when at least one stream was redirected,
    otherwise ``None`` (a console app keeps its console).
    """
    global _stream
    if sys.stdout is not None and sys.stderr is not None:
        return None
    if _stream is None:
        _stream = RotatingLogStream(log_path(app_name, base_dir), max_bytes, backups)
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        version = f" {app_version}" if app_version else ""
        _stream.write(f"\n=== {stamp} {app_name}{version} started (pid {os.getpid()}) ===\n")
    if sys.stdout is None:
        sys.stdout = _stream
    if sys.stderr is None:
        sys.stderr = _stream
    # The originals too, when there were none. PyInstaller's bootloader runs
    # ``sys.__stdout__.flush()`` at exit whenever sys.stdout was replaced;
    # with __stdout__ still None that raises — which the crash reporter would
    # then file as a crash on every normal exit.
    if sys.__stdout__ is None:
        sys.__stdout__ = _stream  # type: ignore[misc]
    if sys.__stderr__ is None:
        sys.__stderr__ = _stream  # type: ignore[misc]
    return _stream.path
