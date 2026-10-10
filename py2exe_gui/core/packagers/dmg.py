"""A ``.dmg`` for macOS: an ``.app`` bundle plus an ``Applications`` link,
written by ``hdiutil`` — which exists on macOS only, so this packager runs
inside the generated CI workflow's macOS job, never on Linux or Windows.

Layout (``<Name>.app/Contents/``)::

    Info.plist                    name, identifier, version, executable, icon
    PkgInfo                       "APPL????"
    MacOS/<exe>                   the one-file binary, or the one-dir folder
    Resources/<name>.icns         when the project's icon is an .icns

When a ``codesign`` identity is given (``P2E_MACOS_SIGN_IDENTITY`` on the
command line, a secret in CI), the bundle is signed with the hardened
runtime before the image is made; notarization and stapling are CI steps.
"""

import os
import plistlib
import shutil
from typing import List, Optional

from py2exe_gui.core.fixes import SEVERITY_WARNING, Finding
from py2exe_gui.core.packagers.base import (
    Log,
    Packager,
    PackageSpec,
    file_stem,
    install_build,
    slug,
    write_bytes,
)


def bundle_identifier(spec: PackageSpec) -> str:
    return spec.identifier.strip() or f"local.{slug(spec.name)}"


def info_plist(spec: PackageSpec, executable: str, icon_file: str = "") -> bytes:
    info = {
        "CFBundleName": spec.name[:15] or executable,
        "CFBundleDisplayName": spec.name or executable,
        "CFBundleIdentifier": bundle_identifier(spec),
        "CFBundleVersion": spec.version or "0.0.0",
        "CFBundleShortVersionString": spec.version or "0.0.0",
        "CFBundleExecutable": executable,
        "CFBundlePackageType": "APPL",
        "CFBundleInfoDictionaryVersion": "6.0",
        "NSHighResolutionCapable": True,
    }
    if icon_file:
        info["CFBundleIconFile"] = icon_file
    if spec.homepage.strip():
        info["NSHumanReadableCopyright"] = spec.homepage.strip()
    return plistlib.dumps(info, sort_keys=True)


class DmgPackager(Packager):
    name = "dmg"
    display_name = ".dmg"
    extension = ".dmg"
    tool = "hdiutil"

    def app_dir(self, spec: PackageSpec, staging: str) -> str:
        return os.path.join(staging, f"{file_stem(spec.name)}.app")

    def output_path(self, spec: PackageSpec) -> str:
        return os.path.join(spec.out_dir, f"{file_stem(spec.name)}-{spec.version}.dmg")

    def stage(self, spec: PackageSpec, staging: str, log: Log) -> List[Finding]:
        app = self.app_dir(spec, staging)
        contents = os.path.join(app, "Contents")
        macos = os.path.join(contents, "MacOS")
        if spec.onefile:
            exe = install_build(spec, os.path.join(macos, file_stem(spec.name)))
        else:
            exe = install_build(spec, macos)
        findings: List[Finding] = []
        icon_file = ""
        if spec.icon and spec.icon.lower().endswith(".icns") and os.path.isfile(spec.icon):
            icon_file = f"{file_stem(spec.name)}.icns"
            os.makedirs(os.path.join(contents, "Resources"))
            shutil.copy2(spec.icon, os.path.join(contents, "Resources", icon_file))
        else:
            findings.append(Finding("package_icon_icns", SEVERITY_WARNING,
                                    {"icon": os.path.basename(spec.icon) or "—"}))
        write_bytes(os.path.join(contents, "Info.plist"),
                    info_plist(spec, os.path.basename(exe), icon_file))
        write_bytes(os.path.join(contents, "PkgInfo"), b"APPL????")
        os.symlink("/Applications", os.path.join(staging, "Applications"))
        return findings

    def commands(self, spec: PackageSpec, staging: str, tool: str,
                 env: Optional[dict] = None) -> List[List[str]]:
        commands = []
        if spec.sign_identity:
            commands.append(["codesign", "--force", "--deep", "--options", "runtime",
                             "--timestamp", "--sign", spec.sign_identity,
                             self.app_dir(spec, staging)])
        commands.append([tool, "create", "-volname", spec.name or file_stem(spec.name),
                         "-srcfolder", staging, "-ov", "-format", "UDZO",
                         self.output_path(spec)])
        return commands
