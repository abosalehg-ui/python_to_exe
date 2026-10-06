"""Nuitka: compiles the program to C, then to a native executable.

Every option below was mapped from the installed Nuitka's own ``--help`` (and
``--help-plugins`` for the UPX plugin), not from memory. Verified against
**Nuitka 4.2.2** on Python 3.12 (Linux, gcc 13); the help text is kept as a
test fixture (``tests/data/nuitka/help-4.2.2.txt``) and a test checks that
every option this module can emit appears in it.

What Nuitka gives, stated without promises: the program's own modules become
compiled C code rather than bytecode in an archive, which typically draws
fewer antivirus false positives and makes extracting the source harder —
harder, not impossible: the logic is still in the binary and can be reverse
engineered. Builds are much slower than PyInstaller's (a C compiler runs).

Layout, chosen to match PyInstaller's so the rest of the app (smoke test,
installer, release) finds the result where it already looks:

* one file  → ``<root>/dist/<name>[.exe]``; Nuitka's intermediate folders
  (``<name>.build``, ``<name>.dist``, ``<name>.onefile-build``) stay in
  ``<root>/build/nuitka`` — like PyInstaller's ``build/`` — and the size lab
  reads ``<name>.dist`` from there;
* a folder  → ``<root>/dist/<name>.dist/<name>[.exe]``: Nuitka always adds
  the ``.dist`` suffix and ``--output-folder-name`` takes no directory part
  (both checked on a real build); its C build folder is removed afterwards;
* the compilation report (``--report``) → ``<root>/build/<name>-nuitka-report.xml``.
  Nuitka does not create the report's folder (a real build failed to write
  it), so ``prepare_output`` creates it first.

Never passed unless the caller has the user's consent: ``--assume-yes-for-
downloads`` (``consent_options``). Without it the build runs with stdin
closed, so Nuitka's own download prompt answers "no" by itself.
"""

import os
import re
import sys
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from py2exe_gui.core.builder import split_extra_args
from py2exe_gui.core.config import BuildConfig
from py2exe_gui.core.engines import base
from py2exe_gui.core.engines.base import Engine, Stage
from py2exe_gui.core.fixes import (
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    Finding,
    flag_fix,
)
from py2exe_gui.core.version_info import VersionInfo, parse_version_tuple

NAME = "nuitka"
#: The Nuitka release this module was verified against.
VERIFIED_VERSION = "4.2.2"
#: Offered when Nuitka is missing (installed only with the user's consent).
#: The "onefile" extra is upstream's: it adds zstandard, which compresses the
#: one-file payload (27% of its size on the sample build).
REQUIREMENT = "nuitka[onefile]>=4.2,<5"

#: Python versions Nuitka 4.2.2 supports (``nuitka.PythonVersions``), from
#: 3.8, the oldest this app supports; and those it only runs experimentally
#: (a real 3.15 build printed "only experimentally supported").
SUPPORTED_PYTHONS = ("3.8", "3.9", "3.10", "3.11", "3.12", "3.13", "3.14")
EXPERIMENTAL_PYTHONS = ("3.15",)

BUILD_SUBDIR = "nuitka"


# ── Phases (read off real Nuitka 4.2.2 builds, see tests/data/nuitka) ──────
#
# Nuitka prints one line per step when its progress bar is off
# (``--progress-bar=none``); there is no line per module, so the bar moves in
# steps and creeps a little on warnings.
STAGES: Tuple[Stage, ...] = (
    Stage("starting", 0, 5, ("nuitka-options: used command line options",)),
    Stage("nuitka_python", 5, 45, ("starting python compilation",)),
    Stage(
        "nuitka_c_source",
        45,
        55,
        ("completed python level compilation", "generating source code for c backend",
         "running data composer tool"),
    ),
    Stage("nuitka_c_compile", 55, 85, ("running c compilation via scons",
                                       "backend c compiler:")),
    Stage("nuitka_c_link", 85, 90, ("backend c linking",)),
    Stage(
        "nuitka_onefile",
        90,
        97,
        ("creating single file from dist folder", "running bootstrap binary compilation"),
    ),
)


# ── Fix vocabulary ─────────────────────────────────────────────────────────
#
# Fixes are written in PyInstaller's vocabulary (the knowledge base and the
# diagnostics predate Nuitka). Each translates to Nuitka's option, or to
# nothing when Nuitka has no equivalent — it is then reported as unsupported,
# never passed through.

#: PyInstaller option → the Nuitka options that do the same, () if none.
FROM_PYINSTALLER: Dict[str, Tuple[str, ...]] = {
    "--collect-data": ("--include-package-data",),
    "--collect-submodules": ("--include-package",),
    # --collect-all also copies the distribution's metadata, but that takes a
    # distribution name, which is not always the import name given here.
    "--collect-all": ("--include-package", "--include-package-data"),
    "--copy-metadata": ("--include-distribution-metadata",),
    "--exclude-module": ("--nofollow-import-to",),
    "--hidden-import": ("--include-module",),
    # Nuitka finds a package's DLLs through its own package configuration;
    # there is no command-line option that collects them.
    "--collect-binaries": (),
}

#: Options a Nuitka fix may use as they are.
NATIVE_FLAGS = frozenset({
    "--enable-plugins", "--include-package", "--include-package-data",
    "--include-distribution-metadata", "--nofollow-import-to", "--include-module",
})


# ── Build-log patterns (from real runs; see tests/data/nuitka) ─────────────

_RE_PLUGIN = re.compile(r"Use '--enable-plugins?=([\w.-]+)' for: (.+)")
_RE_DOWNLOAD = re.compile(r"Nuitka will download (.+?) from")
_RE_DOWNLOAD_REJECT = re.compile(r"FATAL: (.*?(?:download|required).*)$", re.MULTILINE)
_RE_COMPILER = re.compile(
    r"failed to detect GCC version of backend compiler '([^']+)'"
    r"|Failed unexpectedly in Scons C backend compilation"
)
_RE_TOOL_REQUIRED = re.compile(
    r"requires '(patchelf)' to be installed|The '(readelf)' is used to analyse dependencies"
)
_RE_SYNTAX = re.compile(r'File "([^"]+)", line (\d+)\n(?:.*\n){0,3}?SyntaxError: (.+)')
_RE_EXPERIMENTAL = re.compile(
    r"The Python version '([\d.]+)' is only experimentally supported by Nuitka '([^']+)'"
)
#: Where a frozen Nuitka program runs from: ``<name>.dist/`` (folder) or the
#: onefile extraction folder ``onefile_<pid>_<time>_<random>/``.
BUNDLE_PREFIX = re.compile(r"^.*?(?:[\\/][^\\/]+\.dist|[\\/]onefile_\d+_\d+_\w+)[\\/]")


def _is_windows(platform: Optional[str]) -> bool:
    return (platform if platform is not None else sys.platform).startswith("win")


def _numeric_version(version: str) -> str:
    """Nuitka accepts "up to 4 numbers, no strings": 1.2.3-beta → 1.2.3.0."""
    return ".".join(str(n) for n in parse_version_tuple(version))


class NuitkaEngine(Engine):
    name = NAME
    display_name = "Nuitka"
    module = "nuitka"
    feature_matrix = {
        base.FEATURE_ONEFILE: True,           # --mode=onefile
        base.FEATURE_ONEDIR: True,            # --mode=standalone
        base.FEATURE_WINDOWED: True,          # --windows-console-mode=disable
        base.FEATURE_ICON: True,              # --windows-icon-from-ico
        base.FEATURE_VERSION_INFO: True,      # --company-name, --file-version...
        base.FEATURE_SPLASH: True,            # --onefile-windows-splash-screen-image
        base.FEATURE_MANIFEST: False,         # no option for a custom manifest
        base.FEATURE_UPX: True,               # --enable-plugins=upx
        base.FEATURE_STRIP: True,             # stripped unless --unstripped
        base.FEATURE_OPTIMIZE: True,          # --python-flag=no_asserts/no_docstrings
        base.FEATURE_CLEAN: False,            # nothing like PyInstaller's --clean
        base.FEATURE_DATA_FILES: True,        # --include-data-files/-dir
        base.FEATURE_HIDDEN_IMPORTS: True,    # --include-module
        base.FEATURE_EXCLUDE_MODULES: True,   # --nofollow-import-to
        base.FEATURE_RUNTIME_KIT: False,      # needs PyInstaller's --runtime-hook
        base.FEATURE_SIZE_REPORT: True,       # --report + the output folder
        base.FEATURE_WARN_FILE: False,
    }
    stages = STAGES
    missing_markers = ("No module named nuitka", "No module named 'nuitka'")
    missing_code = "nuitka_missing"
    version_info_mode = "options"
    interactive_stdin = False
    bundle_prefix = BUNDLE_PREFIX
    flag_style = "equals"

    # ── Availability ──

    def requirements(self, platform: Optional[str] = None) -> Tuple[str, ...]:
        # patchelf is on PyPI as a wheel carrying the binary; a real Linux
        # build failed without it.
        plat = platform if platform is not None else sys.platform
        return (REQUIREMENT, "patchelf") if plat.startswith("linux") else (REQUIREMENT,)

    def version_env(self) -> Dict[str, str]:
        # ``--version`` checks for a newer release online unless told not to.
        return {"NUITKA_UPDATE_CHECK": "never"}

    def consent_options(self) -> List[str]:
        return ["--assume-yes-for-downloads"]

    def build_env(self, python: str, base_env: Optional[Dict[str, str]] = None
                  ) -> Optional[Dict[str, str]]:
        """The app's environment, with the build interpreter's folder first on PATH.

        Nuitka runs ``patchelf`` (and the compiler) from PATH; this is what an
        activated venv does, so tools installed into the isolated environment
        are found. Also no update check, like ``--update-check=never``.
        """
        env = dict(os.environ if base_env is None else base_env)
        folder = os.path.dirname(python or sys.executable)
        if folder:
            env["PATH"] = folder + os.pathsep + env.get("PATH", "")
        env["NUITKA_UPDATE_CHECK"] = "never"
        return env

    # ── Features ──

    def unsupported_features(self, config: BuildConfig) -> List[str]:
        missing = super().unsupported_features(config)
        # The splash screen exists for one-file builds only.
        if config.splash_image and not config.onefile and base.FEATURE_SPLASH not in missing:
            missing.append(base.FEATURE_SPLASH)
        return [f for f in base.FEATURES if f in missing]

    # ── Layout ──

    def _root(self, config: BuildConfig) -> str:
        return config.output_dir or os.path.dirname(config.source)

    def _exe_name(self, config: BuildConfig, platform: Optional[str]) -> str:
        name = self.output_stem(config)
        return name + ".exe" if _is_windows(platform) else name

    def work_dir(self, config: BuildConfig) -> str:
        """Nuitka's intermediate folders (one-file builds)."""
        return os.path.join(self._root(config), "build", BUILD_SUBDIR)

    def report_path(self, config: BuildConfig) -> str:
        return os.path.join(self._root(config), "build",
                            f"{self.output_stem(config)}-nuitka-report.xml")

    def dist_folder(self, config: BuildConfig) -> str:
        """The ``<name>.dist`` folder: the result (folder mode) or its contents."""
        stem = self.output_stem(config) + ".dist"
        if config.onefile:
            return os.path.join(self.work_dir(config), stem)
        return os.path.join(self._root(config), "dist", stem)

    def prepare_output(self, config: BuildConfig) -> None:
        for folder in (os.path.dirname(self.report_path(config)),
                       os.path.join(self._root(config), "dist")):
            os.makedirs(folder, exist_ok=True)

    def locate_output(self, config: BuildConfig) -> str:
        if config.onefile:
            dist = os.path.join(self._root(config), "dist")
            name = self.output_stem(config)
            for candidate in (os.path.join(dist, name + ".exe"), os.path.join(dist, name)):
                if os.path.isfile(candidate):
                    return candidate
            return ""
        folder = self.dist_folder(config)
        return folder if os.path.isdir(folder) else ""

    # ── The command ──

    def build_command(
        self,
        config: BuildConfig,
        python_executable: Optional[str] = None,
        platform: Optional[str] = None,
        extra_options: Sequence[str] = (),
    ) -> Tuple[Optional[List[str]], Optional[str]]:
        """The Nuitka command for ``config``.

        Options for features Nuitka lacks (a custom manifest, the Runtime
        Kit's hook) are left out: ``unsupported_features`` reports them.
        """
        if not config.source or not os.path.isfile(config.source):
            return None, "اختر ملف المصدر أولاً!"

        windows = _is_windows(platform)
        root = self._root(config)
        stem = self.output_stem(config)
        cmd: List[str] = [python_executable or sys.executable, "-m", "nuitka"]

        if config.onefile:
            cmd += [
                "--mode=onefile",
                f"--output-dir={self.work_dir(config)}",
                f"--output-filename={os.path.join(root, 'dist', self._exe_name(config, platform))}",
            ]
        else:
            cmd += [
                "--mode=standalone",
                f"--output-dir={os.path.join(root, 'dist')}",
                f"--output-filename={self._exe_name(config, platform)}",
                "--remove-output",
            ]
        cmd += [
            f"--output-folder-name={stem}",
            f"--report={self.report_path(config)}",
            # No network unless the user asked for it, and one line per step.
            "--update-check=never",
            "--progress-bar=none",
        ]

        if windows and (config.windowed or config.noconsole):
            cmd.append("--windows-console-mode=disable")
        if windows and config.icon and os.path.isfile(config.icon):
            cmd.append(f"--windows-icon-from-ico={config.icon}")
        if (windows and config.onefile and config.splash_image
                and os.path.isfile(config.splash_image)):
            cmd.append(f"--onefile-windows-splash-screen-image={config.splash_image}")

        for path in config.extra_files:
            if not os.path.exists(path):
                continue
            target = os.path.basename(path.rstrip("\\/"))
            if os.path.isdir(path):
                cmd.append(f"--include-data-dir={path}={target}")
            else:
                cmd.append(f"--include-data-files={path}={target}")

        for module in config.hidden_imports:
            cmd.append(f"--include-module={module}")

        if config.optimize >= 1:
            cmd.append("--python-flag=no_asserts")
        if config.optimize >= 2:
            cmd.append("--python-flag=no_docstrings")

        if config.upx:
            cmd.append("--enable-plugins=upx")
            if config.upx_dir:
                cmd.append(f"--upx-binary={config.upx_dir}")

        cmd.extend(extra_options)
        if config.extra_args:
            cmd.extend(split_extra_args(config.extra_args, platform))
        cmd.append(config.source)
        return cmd, None

    def metadata_options(self, info: VersionInfo, platform: Optional[str] = None) -> List[str]:
        """Version Info as Nuitka options (a Windows PE resource, like PyInstaller's)."""
        if not _is_windows(platform) or info.is_empty():
            return []
        options = []
        for flag, value in (
            ("--company-name", info.company_name),
            ("--product-name", info.product_name),
            ("--file-description", info.file_description),
            ("--copyright", info.legal_copyright),
        ):
            if value:
                options.append(f"{flag}={value}")
        if info.file_version:
            options.append(f"--file-version={_numeric_version(info.file_version)}")
        if info.product_version:
            options.append(f"--product-version={_numeric_version(info.product_version)}")
        return options

    # ── Fixes ──

    def translate_flag(self, flag: str, argument: str) -> Optional[List[Tuple[str, str]]]:
        if flag in NATIVE_FLAGS:
            return [(flag, argument)]
        targets = FROM_PYINSTALLER.get(flag)
        if not targets:
            return None
        return [(target, argument) for target in targets]

    # ── Diagnostics ──

    def log_findings(self, text: str, origin: str, imports: Iterable[str]) -> List[Finding]:
        findings: List[Finding] = []
        for plugin, reason in _RE_PLUGIN.findall(text):
            findings.append(
                Finding("nuitka_plugin_needed", SEVERITY_WARNING,
                        {"plugin": plugin, "reason": reason.strip()},
                        (flag_fix("--enable-plugins", plugin),), origin=origin)
            )
        if "Is it OK to download" in text and "default non-interactive" in text:
            tools = _RE_DOWNLOAD.findall(text)
            reject = _RE_DOWNLOAD_REJECT.findall(text)
            findings.append(
                Finding("nuitka_download_declined", SEVERITY_ERROR,
                        {"tool": tools[0] if tools else "",
                         "reason": reject[-1].strip() if reject else ""},
                        origin=origin)
            )
        for match in _RE_TOOL_REQUIRED.finditer(text):
            tool = match.group(1) or match.group(2)
            findings.append(
                Finding("nuitka_tool_missing", SEVERITY_ERROR, {"tool": tool}, origin=origin)
            )
        match = _RE_COMPILER.search(text)
        if match:
            findings.append(
                Finding("nuitka_compiler_failed", SEVERITY_ERROR,
                        {"compiler": match.group(1) or ""}, origin=origin)
            )
        match = _RE_SYNTAX.search(text)
        if match:
            findings.append(
                Finding("syntax_error", SEVERITY_ERROR,
                        {"line": match.group(2), "error": match.group(3).strip()},
                        origin=origin)
            )
        for version, nuitka in _RE_EXPERIMENTAL.findall(text):
            findings.append(
                Finding("nuitka_python_experimental", SEVERITY_WARNING,
                        {"version": version, "nuitka": nuitka}, origin=origin)
            )
        return findings

    # ── Size lab ──

    def analyze_size(self, config: BuildConfig, local_modules=None):
        from py2exe_gui.core.engines.nuitka_report import analyze_nuitka_build

        return analyze_nuitka_build(self, config, local_modules=local_modules)
