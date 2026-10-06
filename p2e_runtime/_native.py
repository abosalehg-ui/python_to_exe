"""Native message boxes without a GUI toolkit.

On Windows this is ``MessageBoxW`` through ``ctypes``: it works whatever the
app was written with (tkinter, Qt, wx, a console tool) and before any of it
has started. Elsewhere there is no toolkit-free native dialog, so callers get
``None`` back and fall back to ``stderr``.
"""

import os
import sys
from typing import Callable, Optional

MB_OK = 0x0
MB_YESNO = 0x4
MB_ICONERROR = 0x10
MB_ICONQUESTION = 0x20
MB_ICONINFORMATION = 0x40
MB_SETFOREGROUND = 0x10000
MB_TOPMOST = 0x40000
MB_RIGHT = 0x80000
MB_RTLREADING = 0x100000
IDYES = 6

#: Set to "1" by whoever runs the app unattended (the converter's smoke test):
#: a modal dialog would otherwise keep a crashed app "alive" until the timeout.
NO_DIALOGS_ENV = "P2E_RUNTIME_NO_DIALOGS"

KIND_ERROR = "error"
KIND_INFO = "info"
KIND_QUESTION = "question"

_ICONS = {KIND_ERROR: MB_ICONERROR, KIND_INFO: MB_ICONINFORMATION, KIND_QUESTION: MB_ICONQUESTION}


def message_box_flags(kind: str, yes_no: bool, rtl: bool) -> int:
    flags = _ICONS.get(kind, MB_ICONINFORMATION) | MB_SETFOREGROUND | MB_TOPMOST
    flags |= MB_YESNO if yes_no else MB_OK
    if rtl:
        flags |= MB_RIGHT | MB_RTLREADING
    return flags


def _windows_message_box(text: str, title: str, flags: int) -> int:
    import ctypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)  # type: ignore[attr-defined]
    user32.MessageBoxW.restype = ctypes.c_int
    user32.MessageBoxW.argtypes = (
        ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint,
    )
    return int(user32.MessageBoxW(None, text, title, flags))


#: Replaced in tests. Receives (text, title, flags), returns the button id.
windows_message_box: Callable[[str, str, int], int] = _windows_message_box


def show(text: str, title: str, kind: str = KIND_INFO, yes_no: bool = False,
         rtl: bool = False, platform: Optional[str] = None) -> Optional[bool]:
    """Show a native dialog. ``True`` for Yes/OK, ``False`` for No.

    ``None`` means no native dialog exists on this platform (or it failed);
    the caller decides on a fallback. Never raises.
    """
    plat = platform if platform is not None else sys.platform
    if plat != "win32" or dialogs_disabled():
        return None
    try:
        result = windows_message_box(text, title, message_box_flags(kind, yes_no, rtl))
    except Exception:  # a dialog must never take the app down
        return None
    return result == IDYES if yes_no else True


def dialogs_disabled() -> bool:
    return os.environ.get(NO_DIALOGS_ENV) == "1"


def to_stderr(text: str) -> bool:
    """Write ``text`` to stderr if there is one. Never raises."""
    stream = sys.stderr
    if stream is None:
        return False
    try:
        stream.write(text.rstrip("\n") + "\n")
        stream.flush()
    except Exception:
        return False
    return True
