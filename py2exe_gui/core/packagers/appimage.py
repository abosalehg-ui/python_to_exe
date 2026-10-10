"""AppImage: one file that runs on most Linux distributions, no install.

The layout is the one ``appimagetool`` expects::

    <App>.AppDir/
      AppRun                      a shell script that execs the binary
      <app>.desktop               the launcher entry (also under usr/share)
      <app>.png  .DirIcon         the icon
      usr/bin/<app>               the one-file binary, or
      usr/lib/<app>/...           the one-dir folder

``appimagetool`` itself is an AppImage published by the AppImage project,
and every AppImage it makes starts with a small static *runtime* that the
tool would otherwise fetch from GitHub in the middle of a build. Both files
are **never downloaded without a yes**: ``find_appimagetool`` and
``find_runtime`` look for them (``APPIMAGETOOL`` / ``APPIMAGE_RUNTIME_FILE``
in the environment, the PATH for the tool, then the per-user tools folder),
``download_appimagetool`` fetches what is missing and is only called by a
caller that asked, and the tool is always run with ``--runtime-file`` so it
has no reason to go online. It is run with ``APPIMAGE_EXTRACT_AND_RUN=1`` so
it works where FUSE is unavailable (containers, CI runners).
"""

import hashlib
import os
import shutil
import urllib.request
from typing import Callable, List, Optional, Tuple

from py2exe_gui.core.fixes import SEVERITY_ERROR, Finding
from py2exe_gui.core.packagers.base import (
    Log,
    Packager,
    PackageSpec,
    desktop_entry,
    file_stem,
    install_build,
    resolve_icon_png,
    slug,
    write_bytes,
    write_text,
)

TOOL_ENV = "APPIMAGETOOL"
RUNTIME_ENV = "APPIMAGE_RUNTIME_FILE"
#: The AppImage project's own builds. "continuous" is the only channel they
#: publish; it embeds the current static runtime (no libfuse2 on the user's
#: machine), which is why it is preferred over the 2020 AppImageKit 13.
APPIMAGETOOL_URL = ("https://github.com/AppImage/appimagetool/releases/download/"
                    "continuous/appimagetool-{arch}.AppImage")
#: The static runtime every produced AppImage starts with (same project).
RUNTIME_URL = ("https://github.com/AppImage/type2-runtime/releases/download/"
               "continuous/runtime-{arch}")
APPIMAGETOOL_ARCHES = ("x86_64", "aarch64")
#: SHA-256 of the files as downloaded when this code was written (2026-10-10,
#: appimagetool "continuous build (git version 854e19e), build 313"). A newer
#: continuous build will differ: the digest is reported, never used to refuse.
KNOWN_DIGESTS = {
    "x86_64": "95cbe7cce9717fce90c484e34052ee7c7f1d7635b33c12525b4776826a7d29b6",
}
KNOWN_RUNTIME_DIGESTS = {
    "x86_64": "156f4bdbde9c52d01814600013e0a273f0118dc2de98975f3c8c63427ec79074",
}
_READ_CHUNK = 1024 * 1024


def appimage_arch(machine: str) -> str:
    """The ``ARCH`` name appimagetool uses for a ``platform.machine()``."""
    machine = (machine or "").lower()
    if machine in ("x86_64", "amd64"):
        return "x86_64"
    if machine in ("aarch64", "arm64"):
        return "aarch64"
    if machine in ("i386", "i486", "i586", "i686", "x86"):
        return "i686"
    if machine.startswith("arm"):
        return "armhf"
    return machine or "x86_64"


def appimagetool_url(machine: str) -> str:
    return APPIMAGETOOL_URL.format(arch=appimage_arch(machine))


def runtime_url(machine: str) -> str:
    return RUNTIME_URL.format(arch=appimage_arch(machine))


def appimagetool_target(tools_dir: str, machine: str) -> str:
    return os.path.join(tools_dir, f"appimagetool-{appimage_arch(machine)}.AppImage")


def runtime_target(tools_dir: str, machine: str) -> str:
    return os.path.join(tools_dir, f"runtime-{appimage_arch(machine)}")


def find_runtime(env: Optional[dict] = None, tools_dir: str = "", machine: str = "") -> str:
    """Where the AppImage runtime file is, or '' (nothing is downloaded here)."""
    environ = os.environ if env is None else env
    explicit = (environ.get(RUNTIME_ENV) or "").strip()
    if explicit and os.path.isfile(explicit):
        return explicit
    if tools_dir:
        candidate = runtime_target(tools_dir, machine)
        if os.path.isfile(candidate):
            return candidate
    return ""


def find_appimagetool(env: Optional[dict] = None, tools_dir: str = "",
                      machine: str = "") -> str:
    """Where ``appimagetool`` is, or '' (nothing is downloaded here)."""
    environ = os.environ if env is None else env
    explicit = (environ.get(TOOL_ENV) or "").strip()
    if explicit and os.path.isfile(explicit):
        return explicit
    for name in ("appimagetool", f"appimagetool-{appimage_arch(machine)}.AppImage"):
        found = shutil.which(name)
        if found:
            return found
    if tools_dir:
        candidate = appimagetool_target(tools_dir, machine)
        if os.path.isfile(candidate):
            return candidate
    return ""


def sha256_of(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_READ_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fetch(url: str, target: str, log: Log, urlopen: Callable, timeout: float) -> str:
    """Download ``url`` to ``target`` through a temporary name (a cut download
    leaves nothing that looks like a tool); returns the SHA-256."""
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    temp = target + ".part"
    log(f"GET {url}")
    with urlopen(url, timeout=timeout) as response, open(temp, "wb") as f:
        shutil.copyfileobj(response, f)
    digest = sha256_of(temp)
    os.chmod(temp, 0o755)
    os.replace(temp, target)
    log(f"sha256 {digest} ({os.path.getsize(target)} bytes) {os.path.basename(target)}")
    return digest


def download_appimagetool(tools_dir: str, log: Log = lambda _m: None,
                          machine: str = "", urlopen: Callable = urllib.request.urlopen,
                          timeout: float = 120, env: Optional[dict] = None,
                          ) -> Tuple[str, str, Optional[bool]]:
    """Fetch what is missing of ``appimagetool`` and its runtime into
    ``tools_dir``. Only ever called after the user said yes.

    Returns ``(tool_path, sha256, matches_known)`` for the tool, where
    ``matches_known`` is None when no digest is recorded for this
    architecture (or the tool was already there).
    """
    digest, matches = "", None
    tool = find_appimagetool(env, tools_dir, machine)
    if not tool:
        tool = appimagetool_target(tools_dir, machine)
        digest = _fetch(appimagetool_url(machine), tool, log, urlopen, timeout)
        known = KNOWN_DIGESTS.get(appimage_arch(machine))
        matches = None if known is None else digest == known
    if not find_runtime(env, tools_dir, machine):
        got = _fetch(runtime_url(machine), runtime_target(tools_dir, machine), log, urlopen,
                     timeout)
        known = KNOWN_RUNTIME_DIGESTS.get(appimage_arch(machine))
        if known is not None and got != known:
            log(f"runtime: sha256 differs from the one recorded when this version was "
                f"written ({known[:12]}…): a newer continuous build")
    return tool, digest, matches


class AppImagePackager(Packager):
    name = "appimage"
    display_name = "AppImage"
    extension = ".AppImage"
    tool = "appimagetool"

    def __init__(self, tools_dir: str = ""):
        self._tools_dir = tools_dir

    @property
    def tools_dir(self) -> str:
        if not self._tools_dir:
            from py2exe_gui.paths import tools_dir

            self._tools_dir = tools_dir()
        return self._tools_dir

    def tool_path(self, env: Optional[dict] = None) -> str:
        """The tool, when **both** it and the runtime file are present: the
        tool would otherwise download the runtime by itself, mid-build."""
        tool = find_appimagetool(env, self.tools_dir)
        return tool if tool and find_runtime(env, self.tools_dir) else ""

    def runtime_path(self, env: Optional[dict] = None) -> str:
        return find_runtime(env, self.tools_dir)

    def tool_missing_finding(self) -> Finding:
        return Finding("appimagetool_missing", SEVERITY_ERROR,
                       {"url": appimagetool_url(""), "path": self.tools_dir})

    def download_target(self, spec: PackageSpec) -> str:
        return appimagetool_target(self.tools_dir, spec.machine())

    def output_path(self, spec: PackageSpec) -> str:
        arch = appimage_arch(spec.machine())
        return os.path.join(spec.out_dir, f"{file_stem(spec.name)}-{spec.version}-{arch}.AppImage")

    def appdir(self, spec: PackageSpec, staging: str) -> str:
        return os.path.join(staging, f"{file_stem(spec.name)}.AppDir")

    def stage(self, spec: PackageSpec, staging: str, log: Log) -> List[Finding]:
        app = slug(spec.name)
        appdir = self.appdir(spec, staging)
        if spec.onefile:
            exe = install_build(spec, os.path.join(appdir, "usr", "bin", app))
        else:
            exe = install_build(spec, os.path.join(appdir, "usr", "lib", app))
        relative = os.path.relpath(exe, appdir).replace(os.sep, "/")
        write_text(os.path.join(appdir, "AppRun"), apprun_script(relative), 0o755)
        entry = desktop_entry(spec, exec_line=app, icon_name=app)
        write_text(os.path.join(appdir, f"{app}.desktop"), entry)
        write_text(os.path.join(appdir, "usr", "share", "applications", f"{app}.desktop"), entry)
        png, warning = resolve_icon_png(spec)
        write_bytes(os.path.join(appdir, f"{app}.png"), png)
        write_bytes(os.path.join(appdir, ".DirIcon"), png)
        write_bytes(os.path.join(appdir, "usr", "share", "icons", "hicolor", "256x256", "apps",
                                 f"{app}.png"), png)
        return [warning] if warning else []

    def commands(self, spec: PackageSpec, staging: str, tool: str,
                 env: Optional[dict] = None) -> List[List[str]]:
        runtime = self.runtime_path(env) or runtime_target(self.tools_dir, spec.machine())
        return [[tool, "--no-appstream", "--runtime-file", runtime,
                 self.appdir(spec, staging), self.output_path(spec)]]

    def environment(self, spec: PackageSpec) -> dict:
        return {
            "ARCH": appimage_arch(spec.machine()),
            "VERSION": spec.version,
            # Run the tool's own AppImage without FUSE (containers, CI).
            "APPIMAGE_EXTRACT_AND_RUN": "1",
        }


def apprun_script(relative_exe: str) -> str:
    """``AppRun``: resolve the mount point, exec the binary with the arguments."""
    return (
        "#!/bin/sh\n"
        '# Generated by Python to EXE Converter.\n'
        'HERE="$(dirname "$(readlink -f "$0")")"\n'
        f'exec "$HERE/{relative_exe}" "$@"\n'
    )
