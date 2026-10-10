"""One ``Packager`` interface for the Linux and macOS package formats.

A packager turns what the engine built (a one-file binary, or a one-dir
folder) into something a user installs: an AppImage, a ``.deb``, a ``.dmg``.
Each one stages a folder under the release directory, then runs **one**
external tool on it (``appimagetool``, ``dpkg-deb``, ``hdiutil``); the
commands are returned before anything runs, so a dry run can list them and
the confirmation can show them.

UI-independent, like the engines: findings carry codes, the caller translates.
Nothing here downloads anything — fetching ``appimagetool`` is a separate,
explicit step (``appimage.download_appimagetool``) that the caller only
reaches after a yes.
"""

import os
import platform as platform_module
import re
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence, Tuple

from py2exe_gui.core.fixes import SEVERITY_ERROR, SEVERITY_WARNING, Finding
from py2exe_gui.core.packagers.icons import placeholder_png, png_from_icon_file
from py2exe_gui.core.platform_support import is_supported, required_platform

Runner = Callable[..., "subprocess.CompletedProcess[str]"]
Log = Callable[[str], None]

#: Where a packager stages its folder, under the release directory.
STAGING_DIR = "packaging"


@dataclass
class PackageSpec:
    """Everything a package needs to know about the app. Plain data."""

    name: str  # the display name ("My App")
    version: str  # semver ("1.2.3")
    built: str  # the one-file binary, or the one-dir folder
    exe_name: str = ""  # the executable inside a one-dir folder
    icon: str = ""  # .png / .ico (Linux), .icns (macOS); '' for none
    description: str = ""
    maintainer: str = ""  # "Name <email>"
    homepage: str = ""
    categories: str = "Utility"
    identifier: str = ""  # reverse-DNS bundle id (macOS)
    license: str = ""
    windowed: bool = False  # Terminal=false in the .desktop entry
    out_dir: str = ""  # the release folder the package is written to
    arch: str = ""  # '' = this machine
    section: str = "utils"  # Debian section
    depends: str = ""  # Debian Depends line
    #: macOS: ``codesign`` identity for the .app before the .dmg ('' = unsigned).
    sign_identity: str = field(default="", repr=False)

    @property
    def onefile(self) -> bool:
        return os.path.isfile(self.built)

    def machine(self) -> str:
        return self.arch or platform_module.machine() or "x86_64"

    def executable(self) -> str:
        """The binary that runs the app, inside ``built``."""
        if self.onefile:
            return self.built
        name = self.exe_name or os.path.basename(self.built.rstrip("\\/"))
        return os.path.join(self.built, name)


@dataclass
class PackageResult:
    format: str
    ok: bool
    path: str = ""
    #: A finding code when the package was not built ("package_tool_missing"...).
    error_code: str = ""
    error: str = ""
    size_bytes: int = 0
    commands: List[List[str]] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)


class Packager:
    """A package format. Subclasses set the class attributes and implement
    ``stage``, ``output_path`` and ``commands``."""

    name = ""
    display_name = ""
    extension = ""
    #: The external tool that builds the package (its command name).
    tool = ""

    # ── What the subclass provides ───────────────────────────────────────

    def tool_path(self, env: Optional[dict] = None) -> str:
        """Where the tool is, '' when missing."""
        return shutil.which(self.tool) or ""

    def output_path(self, spec: PackageSpec) -> str:  # pragma: no cover - abstract
        raise NotImplementedError

    def stage(self, spec: PackageSpec, staging: str, log: Log) -> List[Finding]:
        """Fill ``staging`` (an empty folder) with the package layout."""
        raise NotImplementedError  # pragma: no cover - abstract

    def commands(self, spec: PackageSpec, staging: str, tool: str,
                 env: Optional[dict] = None) -> List[List[str]]:
        """The tool invocations that turn ``staging`` into the package."""
        raise NotImplementedError  # pragma: no cover - abstract

    def environment(self, spec: PackageSpec) -> dict:
        """Extra environment variables for the tool (merged over ``os.environ``)."""
        return {}

    # ── Shared behaviour ─────────────────────────────────────────────────

    def staging_dir(self, spec: PackageSpec) -> str:
        return os.path.join(spec.out_dir, STAGING_DIR, self.name)

    def check(self, spec: PackageSpec, platform: Optional[str] = None,
              env: Optional[dict] = None) -> List[Finding]:
        """Findings before building: wrong host, missing tool, missing build."""
        findings = []
        plat = platform if platform is not None else sys.platform
        if not is_supported(self.name, plat):
            findings.append(Finding("package_wrong_platform", SEVERITY_ERROR, {
                "format": self.display_name, "platform": required_platform(self.name)}))
            return findings
        if not spec.built or not os.path.exists(spec.built):
            findings.append(Finding("package_no_build", SEVERITY_ERROR,
                                    {"format": self.display_name}))
        if not self.tool_path(env):
            findings.append(self.tool_missing_finding())
        if not spec.version:
            findings.append(Finding("package_version_missing", SEVERITY_ERROR,
                                    {"format": self.display_name}))
        return findings

    def tool_missing_finding(self) -> Finding:
        return Finding("package_tool_missing", SEVERITY_ERROR,
                       {"format": self.display_name, "tool": self.tool})

    def plan(self, spec: PackageSpec, tool: str = "", env: Optional[dict] = None
             ) -> List[List[str]]:
        """The commands a build would run (for a dry run); nothing is touched."""
        return self.commands(spec, self.staging_dir(spec), tool or self.tool or "", env)

    def build(self, spec: PackageSpec, log: Log = lambda _m: None,
              runner: Runner = subprocess.run, env: Optional[dict] = None,
              timeout: float = 1800) -> PackageResult:
        """Stage, run the tool, check the output. Never raises for a tool error."""
        tool = self.tool_path(env)
        if not tool:
            missing = self.tool_missing_finding()
            return PackageResult(self.name, False, error_code=missing.code,
                                 error=self.tool, findings=[missing])
        staging = self.staging_dir(spec)
        target = self.output_path(spec)
        try:
            reset_dir(staging)
            findings = self.stage(spec, staging, log)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            if os.path.exists(target):
                os.remove(target)
        except OSError as e:
            return PackageResult(self.name, False, error_code="package_failed",
                                 error=str(e))
        commands = self.commands(spec, staging, tool, env)
        environment = dict(os.environ if env is None else env)
        environment.update(self.environment(spec))
        for command in commands:
            log("$ " + " ".join(command))
            try:
                result = runner(command, capture_output=True, text=True, timeout=timeout,
                                cwd=os.path.dirname(target) or None, env=environment)
            except (OSError, subprocess.SubprocessError) as e:
                return PackageResult(self.name, False, error_code="package_failed",
                                     error=str(e), commands=commands, findings=findings)
            for line in (result.stdout or "").splitlines() + (result.stderr or "").splitlines():
                if line.strip():
                    log(line)
            if result.returncode != 0:
                message = (result.stderr or result.stdout or "").strip()[-400:]
                return PackageResult(self.name, False, error_code="package_failed",
                                     error=message or f"exit code {result.returncode}",
                                     commands=commands, findings=findings)
        if not os.path.isfile(target):
            return PackageResult(self.name, False, error_code="package_failed",
                                 error=f"no output: {os.path.basename(target)}",
                                 commands=commands, findings=findings)
        # The staging copy is as big as the package; keep it only after a
        # failure, when it is what there is to look at.
        shutil.rmtree(staging, ignore_errors=True)
        parent = os.path.dirname(staging)
        if os.path.isdir(parent) and not os.listdir(parent):
            os.rmdir(parent)
        return PackageResult(self.name, True, path=target, size_bytes=os.path.getsize(target),
                             commands=commands, findings=findings)


# ── Shared helpers for the layouts ───────────────────────────────────────


def slug(name: str, fallback: str = "app") -> str:
    """A lowercase, ASCII, hyphenated identifier from a display name.

    Used for file names, the ``.desktop`` entry and the Debian package name
    (whose rules are the strictest: ``[a-z0-9][a-z0-9+.-]+``).
    """
    cleaned = re.sub(r"[^a-z0-9+.-]+", "-", name.strip().lower()).strip("-.")
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    if len(cleaned) < 2 or not cleaned[0].isalnum():
        cleaned = (fallback + "-" + cleaned).strip("-") if cleaned else fallback
    return cleaned


def file_stem(name: str, fallback: str = "app") -> str:
    """A file name GitHub keeps as is (mirrors ``release.artifacts.safe_name``)."""
    cleaned = re.sub(r"[^A-Za-z0-9._+-]+", "-", name.strip()).strip("-.")
    return cleaned or fallback


def desktop_categories(text: str) -> str:
    """``"Utility;Development;"`` from any separator the user typed."""
    parts = [p.strip() for p in re.split(r"[;,]", text or "") if p.strip()]
    return ";".join(parts or ["Utility"]) + ";"


def desktop_entry(spec: PackageSpec, exec_line: str, icon_name: str) -> str:
    lines = [
        "[Desktop Entry]",
        "Type=Application",
        f"Name={spec.name}",
    ]
    if spec.description:
        lines.append(f"Comment={_single_line(spec.description)}")
    lines += [
        f"Exec={exec_line}",
        f"Icon={icon_name}",
        f"Terminal={'false' if spec.windowed else 'true'}",
        f"Categories={desktop_categories(spec.categories)}",
    ]
    return "\n".join(lines) + "\n"


def _single_line(text: str) -> str:
    return " ".join(text.split())


def resolve_icon_png(spec: PackageSpec) -> Tuple[bytes, Optional[Finding]]:
    """PNG bytes for the package icon, and a warning when a placeholder is used."""
    if spec.icon:
        png = png_from_icon_file(spec.icon)
        if png:
            return png, None
    return placeholder_png(), Finding("package_icon_placeholder", SEVERITY_WARNING,
                                      {"icon": os.path.basename(spec.icon) or "—"})


def reset_dir(path: str) -> None:
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.makedirs(path)


def write_text(path: str, text: str, mode: int = 0o644) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.chmod(path, mode)
    return path


def write_bytes(path: str, data: bytes, mode: int = 0o644) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    os.chmod(path, mode)
    return path


def install_build(spec: PackageSpec, target: str) -> str:
    """Copy what was built to ``target``: the binary (one file) or the whole
    folder (one dir). Files keep their executable bit; the main binary always
    gets it. Returns the path of the executable inside ``target``."""
    if spec.onefile:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(spec.built, target)
        _make_executable(target)
        return target
    if os.path.isdir(target):
        shutil.rmtree(target)
    shutil.copytree(spec.built, target, symlinks=True)
    exe = os.path.join(target, os.path.relpath(spec.executable(), spec.built))
    if os.path.isfile(exe):
        _make_executable(exe)
    return exe


def _make_executable(path: str) -> None:
    mode = os.stat(path).st_mode
    os.chmod(path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def folder_size(path: str) -> int:
    total = 0
    for folder, _dirs, files in os.walk(path):
        for name in files:
            full = os.path.join(folder, name)
            if not os.path.islink(full):
                total += os.path.getsize(full)
    return total


def errors_in(findings: Sequence[Finding]) -> List[Finding]:
    return [f for f in findings if f.severity == SEVERITY_ERROR]
