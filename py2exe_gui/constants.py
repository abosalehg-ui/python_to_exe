"""Application-wide constants."""

import sys

from py2exe_gui.paths import (
    LEGACY_HISTORY_NAME,
    LEGACY_SETTINGS_NAME,
    history_path,
    presets_path,
    resolve_with_migration,
    settings_path,
)

APP_NAME = "Python to EXE Converter"
APP_VERSION = "1.2.0"
DEVELOPER = "عبدالكريم العبود"
EMAIL = "abo.saleh.g@gmail.com"
COPYRIGHT = "© 2025 [Python to EXE] - All Rights Reserved"

# Version range used when offering to install PyInstaller. Pinned rather than
# bare "pyinstaller": --optimize needs 6.0+, and an upper bound keeps a future
# major release from silently changing the CLI under us.
PYINSTALLER_REQUIREMENT = "pyinstaller>=6.0,<7"

# Per-user config paths, migrating any pre-1.1 file left in the CWD.
SETTINGS_FILE = resolve_with_migration(settings_path(), LEGACY_SETTINGS_NAME)
HISTORY_FILE = resolve_with_migration(history_path(), LEGACY_HISTORY_NAME)
# Presets are new in 1.2, so there is no legacy location to migrate from.
PRESETS_FILE = presets_path()

# Fallback for Python < 3.10, which lacks sys.stdlib_module_names. Not
# exhaustive, but it covers what a typical script imports; 3.10+ uses the
# real interpreter-provided set instead.
_FALLBACK_STDLIB = frozenset({
    "abc", "argparse", "array", "ast", "asyncio", "base64", "binascii",
    "bisect", "builtins", "bz2", "calendar", "cmath", "cmd", "codecs",
    "collections", "colorsys", "concurrent", "configparser", "contextlib",
    "copy", "csv", "ctypes", "dataclasses", "datetime", "decimal", "difflib",
    "dis", "email", "enum", "errno", "faulthandler", "filecmp", "fileinput",
    "fnmatch", "fractions", "ftplib", "functools", "gc", "getopt", "getpass",
    "gettext", "glob", "gzip", "hashlib", "heapq", "hmac", "html", "http",
    "imaplib", "importlib", "inspect", "io", "ipaddress", "itertools", "json",
    "keyword", "linecache", "locale", "logging", "lzma", "mailbox", "math",
    "mimetypes", "mmap", "multiprocessing", "netrc", "numbers", "operator",
    "os", "pathlib", "pickle", "pkgutil", "platform", "plistlib", "poplib",
    "pprint", "profile", "pstats", "pty", "queue", "quopri", "random", "re",
    "readline", "reprlib", "resource", "sched", "secrets", "select",
    "selectors", "shelve", "shlex", "shutil", "signal", "site", "smtplib",
    "socket", "socketserver", "sqlite3", "ssl", "stat", "statistics", "string",
    "stringprep", "struct", "subprocess", "symtable", "sys", "sysconfig",
    "tarfile", "tempfile", "termios", "textwrap", "threading", "time",
    "timeit", "tkinter", "token", "tokenize", "trace", "traceback",
    "tracemalloc", "tty", "types", "typing", "unicodedata", "unittest",
    "urllib", "uuid", "venv", "warnings", "wave", "weakref", "webbrowser",
    "wsgiref", "xml", "xmlrpc", "zipapp", "zipfile", "zipimport", "zlib",
    "zoneinfo",
})

# The old hand-written list held 11 names, so the auto-detector suggested
# `typing`, `collections`, `logging`, ... as hidden imports and bloated builds.
STDLIB_MODULES = frozenset(getattr(sys, "stdlib_module_names", _FALLBACK_STDLIB))
