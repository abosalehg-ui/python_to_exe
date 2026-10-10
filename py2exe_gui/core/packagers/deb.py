"""A ``.deb`` for Debian and Ubuntu, built with ``dpkg-deb``.

Layout (``<pkg>_<version>_<arch>/``)::

    DEBIAN/control
    usr/bin/<pkg>                              one-file binary, or
    opt/<pkg>/...  +  usr/bin/<pkg> -> /opt/<pkg>/<exe>   one-dir folder
    usr/share/applications/<pkg>.desktop
    usr/share/icons/hicolor/256x256/apps/<pkg>.png

The package name and version follow Debian policy (lowercase name; a
pre-release ``1.0.0-beta.1`` becomes ``1.0.0~beta.1`` so it sorts before
``1.0.0``). ``dpkg-deb --root-owner-group`` makes every file root-owned
without ``fakeroot``.
"""

import os
import re
from typing import List, Optional

from py2exe_gui.core.fixes import SEVERITY_WARNING, Finding
from py2exe_gui.core.packagers.base import (
    Log,
    Packager,
    PackageSpec,
    desktop_entry,
    folder_size,
    install_build,
    resolve_icon_png,
    slug,
    write_bytes,
    write_text,
)

#: ``platform.machine()`` → Debian architecture.
_ARCHES = {
    "x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64",
    "i386": "i386", "i486": "i386", "i586": "i386", "i686": "i386", "x86": "i386",
    "armv7l": "armhf", "armv6l": "armhf", "ppc64le": "ppc64el", "s390x": "s390x",
    "riscv64": "riscv64",
}


def deb_arch(machine: str) -> str:
    machine = (machine or "").lower()
    return _ARCHES.get(machine, machine or "amd64")


def deb_version(version: str) -> str:
    """A Debian upstream version: ``1.2.3``, ``1.0.0~beta.1``, ``0.0.0`` for none."""
    text = (version or "").strip()
    text = re.sub(r"-", "~", text)  # a pre-release sorts before the release
    text = re.sub(r"[^A-Za-z0-9.+~]", ".", text)
    text = text.strip(".~")
    if not text or not text[0].isdigit():
        text = "0.0.0" + (("+" + text) if text else "")
    return text


def control_text(spec: PackageSpec, installed_kb: int) -> str:
    """``DEBIAN/control``: the required fields, then the optional ones."""
    synopsis, *rest = (spec.description or spec.name).strip().splitlines() or [spec.name]
    lines = [
        f"Package: {slug(spec.name)}",
        f"Version: {deb_version(spec.version)}",
        f"Section: {spec.section or 'utils'}",
        "Priority: optional",
        f"Architecture: {deb_arch(spec.machine())}",
        f"Maintainer: {spec.maintainer or spec.name + ' <unknown@localhost>'}",
        f"Installed-Size: {max(installed_kb, 1)}",
    ]
    if spec.depends.strip():
        lines.append(f"Depends: {spec.depends.strip()}")
    if spec.homepage.strip():
        lines.append(f"Homepage: {spec.homepage.strip()}")
    lines.append(f"Description: {' '.join(synopsis.split()) or spec.name}")
    for line in rest:
        line = line.rstrip()
        lines.append(" " + line if line.strip() else " .")
    return "\n".join(lines) + "\n"


class DebPackager(Packager):
    name = "deb"
    display_name = ".deb"
    extension = ".deb"
    tool = "dpkg-deb"

    def package_dir(self, spec: PackageSpec, staging: str) -> str:
        return os.path.join(staging, f"{slug(spec.name)}_{deb_version(spec.version)}"
                                     f"_{deb_arch(spec.machine())}")

    def output_path(self, spec: PackageSpec) -> str:
        return os.path.join(spec.out_dir, os.path.basename(self.package_dir(spec, "")) + ".deb")

    def check(self, spec, platform=None, env=None) -> List[Finding]:
        findings = super().check(spec, platform, env)
        if not spec.maintainer.strip() and not any(f.severity == "error" for f in findings):
            findings.append(Finding("package_maintainer_missing", SEVERITY_WARNING,
                                    {"format": self.display_name}))
        return findings

    def stage(self, spec: PackageSpec, staging: str, log: Log) -> List[Finding]:
        pkg = slug(spec.name)
        root = self.package_dir(spec, staging)
        os.makedirs(os.path.join(root, "DEBIAN"), mode=0o755)
        if spec.onefile:
            install_build(spec, os.path.join(root, "usr", "bin", pkg))
        else:
            exe = install_build(spec, os.path.join(root, "opt", pkg))
            os.makedirs(os.path.join(root, "usr", "bin"))
            os.symlink("/" + os.path.relpath(exe, root).replace(os.sep, "/"),
                       os.path.join(root, "usr", "bin", pkg))
        write_text(os.path.join(root, "usr", "share", "applications", f"{pkg}.desktop"),
                   desktop_entry(spec, exec_line=pkg, icon_name=pkg))
        png, warning = resolve_icon_png(spec)
        write_bytes(os.path.join(root, "usr", "share", "icons", "hicolor", "256x256", "apps",
                                 f"{pkg}.png"), png)
        for folder, dirs, _files in os.walk(root):
            for name in dirs:
                os.chmod(os.path.join(folder, name), 0o755)
        installed_kb = (folder_size(root) + 1023) // 1024
        write_text(os.path.join(root, "DEBIAN", "control"), control_text(spec, installed_kb))
        return [warning] if warning else []

    def commands(self, spec: PackageSpec, staging: str, tool: str,
                 env: Optional[dict] = None) -> List[List[str]]:
        return [[tool, "--build", "--root-owner-group", self.package_dir(spec, staging),
                 self.output_path(spec)]]
