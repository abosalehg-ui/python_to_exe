"""Pure logic: turn a BuildConfig into a PyInstaller command list."""

import os
import sys
from typing import List, Optional, Tuple

from py2exe_gui.core.config import BuildConfig


def _add_data_separator(platform: Optional[str] = None) -> str:
    """Return the PyInstaller --add-data separator for the platform."""
    plat = platform if platform is not None else sys.platform
    return ";" if plat == "win32" else ":"


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
        if os.path.exists(path):
            dest = os.path.basename(path)
            cmd.extend(["--add-data", f"{path}{sep}{dest}"])

    for imp in config.hidden_imports:
        cmd.extend(["--hidden-import", imp])

    if config.optimize > 0:
        cmd.append(f"-O{config.optimize}")

    if config.upx:
        cmd.append("--upx-dir=upx")
        if config.upx_level > 0:
            cmd.append(f"--upx-level={config.upx_level}")
    else:
        cmd.append("--noupx")

    if config.extra_args:
        cmd.extend(config.extra_args.split())

    cmd.append(config.source)

    return cmd, None
