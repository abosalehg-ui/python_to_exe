"""Per-user config locations for settings and build history.

Previously these were bare relative filenames, so they resolved against the
current working directory: launching the app from two different folders gave
two different sets of settings, and launching from a read-only folder failed
silently. Everything now lives in the platform's per-user config directory.
"""

import os
import sys
from typing import Optional

APP_DIR_NAME = "py2exe_gui"

# The filenames used before this change, still read once for migration.
LEGACY_SETTINGS_NAME = "py2exe_settings.json"
LEGACY_HISTORY_NAME = "py2exe_history.json"


def config_dir(platform: Optional[str] = None, env: Optional[dict] = None) -> str:
    """Return the per-user config directory for this application.

    Windows : %APPDATA%\\py2exe_gui
    macOS   : ~/Library/Application Support/py2exe_gui
    Linux   : $XDG_CONFIG_HOME/py2exe_gui (or ~/.config/py2exe_gui)
    """
    plat = platform if platform is not None else sys.platform
    environ = os.environ if env is None else env
    home = os.path.expanduser("~")

    if plat == "win32":
        base = environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
    elif plat == "darwin":
        base = os.path.join(home, "Library", "Application Support")
    else:
        base = environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    return os.path.join(base, APP_DIR_NAME)


def cache_dir(platform: Optional[str] = None, env: Optional[dict] = None) -> str:
    """Return the per-user cache directory, for large re-creatable data.

    Build environments run to hundreds of MB, so they must not sit in the
    Windows *roaming* profile (synced on every logon) like the settings do.

    Windows : %LOCALAPPDATA%\\py2exe_gui
    macOS   : ~/Library/Caches/py2exe_gui
    Linux   : $XDG_CACHE_HOME/py2exe_gui (or ~/.cache/py2exe_gui)
    """
    plat = platform if platform is not None else sys.platform
    environ = os.environ if env is None else env
    home = os.path.expanduser("~")

    if plat == "win32":
        base = environ.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local")
    elif plat == "darwin":
        base = os.path.join(home, "Library", "Caches")
    else:
        base = environ.get("XDG_CACHE_HOME") or os.path.join(home, ".cache")
    return os.path.join(base, APP_DIR_NAME)


def envs_dir(platform: Optional[str] = None, env: Optional[dict] = None) -> str:
    """Where isolated per-project build environments live."""
    return os.path.join(cache_dir(platform, env), "build_envs")


def ensure_config_dir() -> str:
    """Create the config directory if needed and return it.

    Returns the path even when creation fails; callers handle write errors
    where they occur rather than crashing at import time.
    """
    directory = config_dir()
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError:
        pass
    return directory


def settings_path() -> str:
    return os.path.join(config_dir(), "settings.json")


def history_path() -> str:
    return os.path.join(config_dir(), "history.json")


def presets_path() -> str:
    return os.path.join(config_dir(), "presets.json")


def signing_key_path() -> str:
    """The Runtime Kit's private update-signing key.

    In the per-user *config* folder, in a sub-folder of its own that is made
    owner-only: never in a project, a build, or a settings file.
    """
    return os.path.join(config_dir(), "signing", "update_signing_key.json")


def legacy_path(name: str) -> str:
    """Path of an old CWD-relative file, for one-time migration."""
    return os.path.abspath(name)


def resolve_with_migration(new_path: str, legacy_name: str) -> str:
    """Return ``new_path``, migrating a legacy CWD file into it once.

    Users upgrading from an earlier version keep their settings and history
    instead of silently starting from scratch. The legacy file is copied, not
    moved, so downgrading still works.
    """
    if os.path.exists(new_path):
        return new_path

    legacy = legacy_path(legacy_name)
    if not os.path.isfile(legacy):
        return new_path

    try:
        # Create the parent of new_path, not the default config dir — they
        # differ whenever the caller passes an explicit destination.
        parent = os.path.dirname(new_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(legacy, encoding="utf-8") as src:
            content = src.read()
        with open(new_path, "w", encoding="utf-8") as dst:
            dst.write(content)
    except OSError:
        # Migration is best-effort: fall back to the legacy location so the
        # user's data stays reachable rather than being lost.
        return legacy
    return new_path
