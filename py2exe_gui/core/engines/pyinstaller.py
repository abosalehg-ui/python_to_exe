"""PyInstaller, the default engine: the command, its phases, its output, its log.

Moved here from ``builder.py`` (the command) and ``build_stages.py`` (the
phases) in 2.0. Both modules keep their public names as thin shims, so every
existing import still works and still behaves exactly as before.
"""

import os
import re
import sys
from typing import Iterable, List, Optional, Sequence, Tuple

from py2exe_gui.core.builder import _add_data_separator as add_data_separator
from py2exe_gui.core.builder import split_extra_args
from py2exe_gui.core.config import BuildConfig
from py2exe_gui.core.engines import base
from py2exe_gui.core.engines.base import Engine, Stage
from py2exe_gui.core.fixes import SEVERITY_ERROR, Finding, flag_fix
from py2exe_gui.core.knowledge import QT_BINDINGS

NAME = "pyinstaller"


# ── Phases ─────────────────────────────────────────────────────────────────
#
# PyInstaller announces every phase it enters — ``Building PYZ``, ``Building
# EXE``, ``Building COLLECT`` and so on — so the phase is knowable exactly.
# Ordered: a marker can only ever move the tracker forward, so a stray late
# mention of an earlier phase name cannot rewind the bar.
STAGES: Tuple[Stage, ...] = (
    Stage("starting", 0, 5, (), lines_per_percent=6),
    Stage(
        "analyzing",
        5,
        40,
        (
            "initializing module dependency graph",
            "analyzing base_library.zip",
            "analyzing ",
            "checking analysis",
            "building analysis",
        ),
        lines_per_percent=10,
    ),
    Stage(
        "hooks",
        40,
        55,
        ("processing module hooks", "loading module hook", "processing pre-safe import"),
        lines_per_percent=8,
    ),
    Stage("dependencies", 55, 62, ("looking for dynamic libraries", "looking for ctypes")),
    Stage("pyz", 62, 72, ("checking pyz", "building pyz")),
    Stage("pkg", 72, 82, ("checking pkg", "building pkg")),
    Stage("exe", 82, 92, ("checking exe", "building exe", "copying bootloader")),
    Stage("collect", 92, 97, ("checking collect", "building collect")),
)


# ── Build-log patterns ─────────────────────────────────────────────────────

_RE_QT = re.compile(
    r"attempting to run hook for '(\w+)', while hook for '(\w+)' has already been run"
)
_RE_UNABLE_TO_FIND = re.compile(r'Unable to find "(.+?)" when adding binary and data files')
_RE_ICON_FORMAT = re.compile(
    r"Received icon image '(.+?)' which exists but is not in the correct format"
)


#: Options PyInstaller fixes use; anything another engine names is not one.
_OWN_FLAGS = frozenset({
    "--collect-data", "--collect-submodules", "--collect-all", "--copy-metadata",
    "--exclude-module", "--collect-binaries", "--hidden-import",
})


class PyInstallerEngine(Engine):
    name = NAME
    display_name = "PyInstaller"
    module = "PyInstaller"
    feature_matrix = {f: True for f in base.FEATURES}
    stages = STAGES
    missing_markers = ("No module named PyInstaller", "No module named 'PyInstaller'")
    missing_code = "pyinstaller_missing"

    def build_command(
        self,
        config: BuildConfig,
        python_executable: Optional[str] = None,
        platform: Optional[str] = None,
        extra_options: Sequence[str] = (),
    ) -> Tuple[Optional[List[str]], Optional[str]]:
        """Construct the PyInstaller command for the given config.

        ``extra_options`` are options the app generated itself at build time —
        the Runtime Kit's ``--runtime-hook`` and friends. They are passed here
        rather than stored in the config, so no settings file can supply them.

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

        sep = add_data_separator(platform)
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

        cmd.extend(extra_options)

        if config.extra_args:
            cmd.extend(split_extra_args(config.extra_args, platform))

        cmd.append(config.source)

        return cmd, None

    def requirements(self, platform: Optional[str] = None) -> Tuple[str, ...]:
        from py2exe_gui.constants import PYINSTALLER_REQUIREMENT

        return (PYINSTALLER_REQUIREMENT,)

    def translate_flag(self, flag: str, argument: str) -> Optional[List[Tuple[str, str]]]:
        """PyInstaller's own options pass; another engine's (Nuitka plugins) do not."""
        return [(flag, argument)] if flag in _OWN_FLAGS else None

    def locate_output(self, config: BuildConfig) -> str:
        """The EXE (one-file) or the app folder (folder mode) under dist/."""
        name = self.output_stem(config)
        root = config.output_dir or os.path.dirname(config.source)
        dist = os.path.join(root, "dist")
        if config.onefile:
            for candidate in (os.path.join(dist, name + ".exe"), os.path.join(dist, name)):
                if os.path.isfile(candidate):
                    return candidate
            return ""
        folder = os.path.join(dist, name)
        return folder if os.path.isdir(folder) else ""

    def log_findings(self, text: str, origin: str, imports: Iterable[str]) -> List[Finding]:
        """Build-time failures PyInstaller reports in its own words."""
        imports = set(imports)
        findings: List[Finding] = []
        for running, already in _RE_QT.findall(text):
            drop = running if running not in imports or already in imports else already
            if drop not in QT_BINDINGS:
                continue
            findings.append(
                Finding("multiple_qt_bindings_build", SEVERITY_ERROR,
                        {"bindings": f"{already}, {running}", "drop": drop},
                        (flag_fix("--exclude-module", drop),), origin=origin)
            )

        for path in _RE_UNABLE_TO_FIND.findall(text):
            findings.append(
                Finding("add_data_missing", SEVERITY_ERROR, {"path": path}, origin=origin)
            )

        for path in _RE_ICON_FORMAT.findall(text):
            findings.append(
                Finding("icon_wrong_format", SEVERITY_ERROR, {"icon": os.path.basename(path)},
                        origin=origin)
            )
        return findings

    def build_findings(self, config: BuildConfig, local_modules: Iterable[str] = (),
                       min_mtime: float = 0.0) -> List[Finding]:
        """The user's own missing imports, from ``warn-<name>.txt``."""
        from py2exe_gui.core.diagnostics import read_warn_findings

        return read_warn_findings(config, local_modules, min_mtime=min_mtime)

    def analyze_size(self, config: BuildConfig, local_modules=None):
        """Inventory the build from PyInstaller's TOC files."""
        from py2exe_gui.core.size_analyzer import analyze_build

        return analyze_build(config, local_modules=local_modules)
