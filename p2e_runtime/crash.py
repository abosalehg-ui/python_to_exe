"""Crash reporter: a saved report and a dialog instead of a silent exit.

When an exception escapes the app (on the main thread or any other), the
report — traceback, app version, OS, Python version, time — is written to
``<user state dir>/crashes`` and the user is told where it is. Nothing is sent
anywhere: if the developer configured a support page, it opens only when the
user clicks *Yes*. Environment variables, the user name, the machine name and
paths outside the traceback are not recorded.
"""

import os
import platform
import struct
import sys
import threading
import time
import traceback
import webbrowser
from typing import Callable, Optional

from p2e_runtime import _native
from p2e_runtime.paths import is_frozen, user_state_dir

DEFAULT_TITLE = "{app} — unexpected error"
DEFAULT_MESSAGE = (
    "{app} stopped because of an unexpected error.\n\n"
    "A report was saved to:\n{path}"
)
DEFAULT_SUPPORT_PROMPT = "Open the support page to report it?"


def format_report(exc_type, exc, tb, app_name: str, app_version: str = "",
                  thread_name: str = "", now: Optional[float] = None) -> str:
    """The text of a crash report. Holds no environment or user details."""
    moment = time.gmtime(time.time() if now is None else now)
    bits = struct.calcsize("P") * 8
    lines = [
        f"Crash report: {app_name} {app_version}".rstrip(),
        f"Time (UTC): {time.strftime('%Y-%m-%dT%H:%M:%SZ', moment)}",
        f"OS: {platform.platform()}",
        f"Python: {platform.python_version()} ({bits}-bit)",
        f"Frozen: {'yes' if is_frozen() else 'no'}",
    ]
    if thread_name:
        lines.append(f"Thread: {thread_name}")
    lines.append("")
    lines.extend(line.rstrip("\n") for line in traceback.format_exception(exc_type, exc, tb))
    return "\n".join(lines) + "\n"


def crash_dir(app_name: str, base_dir: Optional[str] = None) -> str:
    return os.path.join(base_dir or user_state_dir(app_name), "crashes")


def write_report(text: str, directory: str, now: Optional[float] = None) -> str:
    """Save ``text`` as a new file in ``directory`` and return its path."""
    os.makedirs(directory, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(time.time() if now is None else now))
    base = os.path.join(directory, f"crash-{stamp}-{os.getpid()}")
    path, counter = base + ".txt", 1
    while True:
        try:
            # "x": never overwrite an earlier report.
            with open(path, "x", encoding="utf-8") as f:
                f.write(text)
            return path
        except FileExistsError:
            counter += 1
            path = f"{base}-{counter}.txt"


def is_safe_support_url(url: str) -> bool:
    lowered = (url or "").strip().lower()
    return lowered.startswith(("https://", "http://", "mailto:"))


class CrashReporter:
    """Installed as ``sys.excepthook`` and ``threading.excepthook``."""

    def __init__(self, app_name: str, app_version: str = "", directory: Optional[str] = None,
                 dialog: bool = True, support_url: str = "", title: str = "",
                 message: str = "", support_prompt: str = "", rtl: bool = False,
                 show: Optional[Callable[..., Optional[bool]]] = None,
                 open_url: Optional[Callable[[str], object]] = None):
        self.app_name = app_name
        self.app_version = app_version
        self.directory = directory or crash_dir(app_name)
        self.dialog = dialog
        self.support_url = support_url if is_safe_support_url(support_url) else ""
        self.title = title or DEFAULT_TITLE
        self.message = message or DEFAULT_MESSAGE
        self.support_prompt = support_prompt or DEFAULT_SUPPORT_PROMPT
        self.rtl = rtl
        self._show = show or _native.show
        self._open_url = open_url or webbrowser.open
        self._previous_hook = sys.excepthook
        self._previous_thread_hook = getattr(threading, "excepthook", None)
        self._handling = threading.Lock()
        self.last_report = ""

    # ── Hooks ──────────────────────────────────────────────────────────────

    def install(self) -> None:
        sys.excepthook = self.excepthook
        if self._previous_thread_hook is not None:
            threading.excepthook = self.thread_excepthook

    def uninstall(self) -> None:
        sys.excepthook = self._previous_hook
        if self._previous_thread_hook is not None:
            threading.excepthook = self._previous_thread_hook

    def excepthook(self, exc_type, exc, tb) -> None:
        # The default hook first: with a console (or the log redirection) the
        # traceback is printed as usual, even if the dialog below blocks.
        self._call(self._previous_hook, exc_type, exc, tb)
        if issubclass(exc_type, KeyboardInterrupt):
            return
        self.report(exc_type, exc, tb, "")

    def thread_excepthook(self, args) -> None:
        self._call(self._previous_thread_hook, args)
        if args.exc_type is None or issubclass(args.exc_type, SystemExit):
            return
        thread = getattr(args.thread, "name", "") or ""
        self.report(args.exc_type, args.exc_value, args.exc_traceback, thread)

    # ── Work ───────────────────────────────────────────────────────────────

    def report(self, exc_type, exc, tb, thread_name: str = "") -> str:
        """Write the report and tell the user. Returns the report's path."""
        if not self._handling.acquire(blocking=False):
            return ""  # a crash while reporting a crash: don't recurse
        try:
            text = format_report(exc_type, exc, tb, self.app_name, self.app_version, thread_name)
            try:
                path = write_report(text, self.directory)
            except OSError as e:
                _native.to_stderr(f"[p2e_runtime] could not save the crash report: {e}")
                path = ""
            self.last_report = path
            if self.dialog:
                self._notify(path)
            return path
        finally:
            self._handling.release()

    def _notify(self, path: str) -> None:
        fields = {"app": self.app_name, "path": path or "-"}
        title = _fill(self.title, fields)
        text = _fill(self.message, fields)
        if self.support_url:
            text = f"{text}\n\n{_fill(self.support_prompt, fields)}"
        answer = self._show(text, title, _native.KIND_ERROR, bool(self.support_url), self.rtl)
        if answer is None:
            # No native dialog here: say it on stderr. A link is shown, never opened.
            note = f"\n{self.support_url}" if self.support_url else ""
            _native.to_stderr(f"{title}\n{text}{note}")
        elif answer and self.support_url:
            try:
                self._open_url(self.support_url)
            except Exception:
                pass

    @staticmethod
    def _call(hook, *args) -> None:
        if hook is None:
            return
        try:
            hook(*args)
        except Exception:
            pass


def _fill(template: str, fields) -> str:
    try:
        return template.format(**fields)
    except (KeyError, IndexError, ValueError):
        return template


_reporter: Optional[CrashReporter] = None


def install(app_name: str, app_version: str = "", **options) -> CrashReporter:
    """Install the crash reporter once; later calls return the same one."""
    global _reporter
    if _reporter is None:
        _reporter = CrashReporter(app_name, app_version, **options)
        _reporter.install()
    return _reporter
