"""Shared command-line helpers, and the PyInstaller command (a 2.0 shim).

The PyInstaller command itself moved to ``core/engines/pyinstaller.py``;
``build_pyinstaller_command`` stays here so every existing import works.
"""

import shlex
import sys
from typing import List, Optional, Sequence, Tuple

from py2exe_gui.core.config import BuildConfig


def _add_data_separator(platform: Optional[str] = None) -> str:
    """Return the PyInstaller --add-data separator for the platform."""
    plat = platform if platform is not None else sys.platform
    return ";" if plat == "win32" else ":"


def split_extra_args(raw: str, platform: Optional[str] = None) -> List[str]:
    """Tokenize free-form extra arguments, respecting quoted paths.

    A plain ``str.split()`` breaks any argument containing spaces, which is the
    common case on Windows ("C:\\Program Files\\..."). shlex is used in
    non-POSIX mode on Windows so backslashes stay intact.
    """
    if not raw or not raw.strip():
        return []
    plat = platform if platform is not None else sys.platform
    if plat == "win32":
        tokens = shlex.split(raw, posix=False)
        # Non-POSIX mode keeps the surrounding quotes; drop them.
        return [t[1:-1] if len(t) > 1 and t[0] == t[-1] == '"' else t for t in tokens]
    return shlex.split(raw)


# PyInstaller options that cause code supplied by the config file to run —
# either during the build or inside every EXE the build produces. A settings
# JSON shared by someone else is untrusted input, so these are surfaced to the
# user for confirmation instead of being passed through silently.
DANGEROUS_FLAGS = frozenset({
    "--runtime-hook",      # code injected into every produced EXE
    "--additional-hooks-dir",  # arbitrary hook modules imported at build time
    "--add-binary",        # ships an arbitrary binary inside the bundle
    "--upx-dir",           # runs an executable from a caller-chosen directory
    "--runtime-tmpdir",    # redirects the onefile extraction directory
    # 2.0, Nuitka (checked against Nuitka 4.2.2's --help):
    "--user-plugin",                        # a Python plugin run during the build
    "--user-package-configuration-file",    # YAML that can patch module source
    "--include-plugin-directory",           # ships arbitrary code as main files
    "--include-plugin-files",
    "--force-runtime-environment-variable",  # sets e.g. PYTHONPATH in every EXE
    "--onefile-tempdir-spec",               # redirects the onefile extraction directory
    "--upx-binary",                         # runs an executable it names
    "--pgo-executable",                     # runs a command during the build
    "--python-for-scons",                   # runs another Python binary
    "--windows-nsis-path",                  # runs an installer tool it names
    "--linux-installer-appimagetool-path",
    # Consent to download and run tools is the user's to give, per build —
    # never something a shared settings file grants.
    "--assume-yes-for-downloads",
})


def find_dangerous_args(extra_args: str, platform: Optional[str] = None) -> List[str]:
    """Return the code-executing flags present in ``extra_args``.

    Matches both ``--flag value`` and ``--flag=value`` spellings. Used to warn
    before applying a settings file the user did not write themselves.
    """
    found = []
    for token in split_extra_args(extra_args, platform):
        name = token.split("=", 1)[0]
        if name in DANGEROUS_FLAGS and name not in found:
            found.append(name)
    return found


def build_pyinstaller_command(
    config: BuildConfig,
    python_executable: Optional[str] = None,
    platform: Optional[str] = None,
    extra_options: Sequence[str] = (),
) -> Tuple[Optional[List[str]], Optional[str]]:
    """Construct the PyInstaller command for the given config.

    Kept for backward compatibility: the command now lives in
    ``core/engines/pyinstaller.py``. This always builds a *PyInstaller*
    command, whatever ``config.engine`` says; use
    ``engines.engine_for(config).build_command(...)`` to honour it.

    Returns a (command, error) tuple. On success error is None; on failure
    command is None and error contains a user-facing message.
    """
    from py2exe_gui.core.engines import get_engine

    return get_engine("pyinstaller").build_command(
        config, python_executable=python_executable, platform=platform,
        extra_options=extra_options,
    )
