"""Pure logic: turn a BuildConfig into a PyInstaller command list."""

import os
import shlex
import sys
from typing import List, Optional, Tuple

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
) -> Tuple[Optional[List[str]], Optional[str]]:
    """Construct the PyInstaller command for the given config.

    Returns a (command, error) tuple. On success error is None; on failure
    command is None and error contains a user-facing message.
    """
    if not config.source or not os.path.isfile(config.source):
        return None, "اختر ملف المصدر أولاً!"

    py_exe = python_executable or sys.executable
    cmd: List[str] = [py_exe, "-m", "PyInstaller"]

    if config.onefile:
        cmd.append("--onefile")
    if config.windowed:
        cmd.append("--windowed")
    if config.noconsole:
        cmd.append("--noconsole")
    if config.clean:
        cmd.append("--clean")
    if config.noconfirm:
        cmd.append("--noconfirm")
    if config.strip:
        cmd.append("--strip")

    if config.output_name:
        cmd.extend(["--name", config.output_name])

    if config.icon and os.path.isfile(config.icon):
        cmd.extend(["--icon", config.icon])

    if config.version_file and os.path.isfile(config.version_file):
        cmd.extend(["--version-file", config.version_file])

    if config.splash_image and os.path.isfile(config.splash_image):
        cmd.extend(["--splash", config.splash_image])

    if config.manifest_file and os.path.isfile(config.manifest_file):
        cmd.extend(["--manifest", config.manifest_file])

    if config.output_dir:
        cmd.extend(["--distpath", os.path.join(config.output_dir, "dist")])
        cmd.extend(["--workpath", os.path.join(config.output_dir, "build")])
        cmd.extend(["--specpath", config.output_dir])

    sep = _add_data_separator(platform)
    for path in config.extra_files:
        if not os.path.exists(path):
            continue
        # PyInstaller's DEST is a *directory* inside the bundle. Files go to
        # the bundle root ("."); a directory keeps its own name as the target.
        dest = os.path.basename(path.rstrip("\\/")) if os.path.isdir(path) else "."
        cmd.extend(["--add-data", f"{path}{sep}{dest}"])

    for imp in config.hidden_imports:
        cmd.extend(["--hidden-import", imp])

    if config.optimize > 0:
        # PyInstaller has no -O flag; the bytecode level is --optimize (6.0+).
        cmd.extend(["--optimize", str(config.optimize)])

    if config.upx:
        # PyInstaller searches PATH for UPX by default; --upx-dir only narrows
        # that search. There is no --upx-level option.
        if config.upx_dir:
            cmd.append(f"--upx-dir={config.upx_dir}")
    else:
        cmd.append("--noupx")

    if config.extra_args:
        cmd.extend(split_extra_args(config.extra_args, platform))

    cmd.append(config.source)

    return cmd, None
