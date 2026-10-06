"""Where bundled files are, and where an app may write its own files.

``resource_path`` is the one function most frozen apps need: a relative path
such as ``"data/config.json"`` resolves against the folder the program was
started from, which after freezing is rarely where the bundled copy lives.
"""

import os
import re
import sys
from typing import Mapping, Optional


def is_frozen() -> bool:
    """True inside an executable built by PyInstaller (or a similar tool)."""
    return bool(getattr(sys, "frozen", False))


def bundle_dir() -> str:
    """The folder bundled data files were placed in.

    * PyInstaller, one-file: the temporary extraction folder (``sys._MEIPASS``).
    * PyInstaller, folder build: ``<app>/_internal`` (also ``sys._MEIPASS``).
    * Another freezer: the folder holding the executable.
    * Not frozen: the folder of the main script, so the same call works while
      developing.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return str(meipass)
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    main = sys.modules.get("__main__")
    main_file = getattr(main, "__file__", None)
    if main_file:
        return os.path.dirname(os.path.abspath(main_file))
    if sys.argv and sys.argv[0] and os.path.exists(sys.argv[0]):
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.getcwd()


def resource_path(relative: str = "") -> str:
    """Absolute path of a file bundled with the app, frozen or not.

    Use it for every data file the program reads::

        from p2e_runtime import resource_path
        with open(resource_path("data/config.json")) as f:
            ...

    Forward slashes work on every platform. An absolute path is returned
    unchanged.
    """
    parts = [p for p in re.split(r"[\\/]", relative or "") if p]
    if os.path.isabs(relative or ""):
        return os.path.normpath(relative)
    return os.path.normpath(os.path.join(bundle_dir(), *parts))


def safe_name(name: str, default: str = "app") -> str:
    """``name`` reduced to characters every file system and mutex accepts."""
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "_", name or "").strip(" ._")
    return cleaned[:64] or default


def user_state_dir(
    app_name: str,
    platform: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
) -> str:
    """Per-user folder for the app's logs and crash reports.

    Windows : %LOCALAPPDATA%\\<App>          (not the roaming profile)
    macOS   : ~/Library/Logs/<App>
    Linux   : $XDG_STATE_HOME/<App>          (default ~/.local/state/<App>)
    """
    plat = platform if platform is not None else sys.platform
    environ = os.environ if env is None else env
    home = os.path.expanduser("~")
    if plat == "win32":
        base = environ.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local")
    elif plat == "darwin":
        base = os.path.join(home, "Library", "Logs")
    else:
        base = environ.get("XDG_STATE_HOME") or os.path.join(home, ".local", "state")
    return os.path.join(base, safe_name(app_name))
