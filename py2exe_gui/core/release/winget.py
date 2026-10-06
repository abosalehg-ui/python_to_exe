"""winget manifests for a release — generated, checked, never submitted.

Writes the three files of a multi-file manifest (version, installer,
defaultLocale) for **manifest schema 1.28.0**, the newest version in both
``microsoft/winget-cli/schemas/JSON/manifests`` and
``microsoft/winget-pkgs/doc/manifest/schema`` when this was written
(checked 2026-10-06). The required fields, enums, patterns and lengths below
are copied from those schema files:

* version:       PackageIdentifier, PackageVersion, DefaultLocale,
                 ManifestType, ManifestVersion
* installer:     PackageIdentifier, PackageVersion, Installers, ManifestType,
                 ManifestVersion; each installer: Architecture, InstallerUrl,
                 InstallerSha256 (InstallerType at the root or per installer)
* defaultLocale: PackageIdentifier, PackageVersion, PackageLocale, Publisher,
                 PackageName, License, ShortDescription, ManifestType,
                 ManifestVersion

Submitting to ``microsoft/winget-pkgs`` is left to the developer (``wingetcreate``
or a pull request); the files land in ``release/<version>/winget/``.
"""

import os
import re
from typing import Dict, List, Optional, Tuple

MANIFEST_VERSION = "1.28.0"
SCHEMA_URL = "https://aka.ms/winget-manifest.{kind}.1.28.0.schema.json"

# From manifest.*.1.28.0.json (definitions / properties).
_PACKAGE_IDENTIFIER = re.compile(
    r'^[^\.\s\\/:\*\?"<>\|\x01-\x1f]{1,32}(\.[^\.\s\\/:\*\?"<>\|\x01-\x1f]{1,32}){1,7}$'
)
_PACKAGE_VERSION = re.compile(r'^[^\\/:\*\?"<>\|\x01-\x1f]+$')
_LOCALE = re.compile(r"^([a-zA-Z]{2,3}|[iI]-[a-zA-Z]+|[xX]-[a-zA-Z]{1,8})(-[a-zA-Z]{1,8})*$")
_URL = re.compile(r"^([Hh][Tt][Tt][Pp][Ss]?)://.+$")
_SHA256 = re.compile(r"^[A-Fa-f0-9]{64}$")
ARCHITECTURES = ("x86", "x64", "arm", "arm64", "neutral")
INSTALLER_TYPES = ("msix", "msi", "appx", "exe", "zip", "inno", "nullsoft", "wix", "burn",
                   "pwa", "portable", "font")
NESTED_INSTALLER_TYPES = ("msix", "msi", "appx", "exe", "inno", "nullsoft", "wix", "burn",
                          "portable", "font")
# (min, max) string lengths.
_LENGTHS = {
    "PackageIdentifier": (1, 128), "PackageVersion": (1, 128), "PackageLocale": (1, 20),
    "DefaultLocale": (1, 20), "Publisher": (2, 256), "PackageName": (2, 256),
    "License": (3, 512), "ShortDescription": (3, 256), "InstallerUrl": (1, 2048),
    "PublisherUrl": (1, 2048), "PackageUrl": (1, 2048),
}

REQUIRED = {
    "version": ("PackageIdentifier", "PackageVersion", "DefaultLocale", "ManifestType",
                "ManifestVersion"),
    "installer": ("PackageIdentifier", "PackageVersion", "Installers", "ManifestType",
                  "ManifestVersion"),
    "defaultLocale": ("PackageIdentifier", "PackageVersion", "PackageLocale", "Publisher",
                      "PackageName", "License", "ShortDescription", "ManifestType",
                      "ManifestVersion"),
}
INSTALLER_REQUIRED = ("Architecture", "InstallerUrl", "InstallerSha256")

#: installer.architecture (Inno Setup choices) → winget Architecture.
_ARCH = {"x64": "x64", "x86": "x86", "any": "neutral"}


def architecture_for(installer_arch: str) -> str:
    return _ARCH.get((installer_arch or "x64").lower(), "x64")


def build_manifests(identifier: str, version: str, publisher: str, name: str,
                    license_text: str, short_description: str, installer_url: str,
                    sha256: str, installer_type: str, architecture: str = "x64",
                    locale: str = "en-US", publisher_url: str = "",
                    nested_path: str = "", command_alias: str = ""
                    ) -> Dict[str, Dict[str, object]]:
    """The three manifests as ordered dicts (keys in winget's usual order).

    ``installer_type`` is ``inno`` (a Setup.exe), ``portable`` (a one-file
    EXE) or ``zip`` (the portable ZIP, with ``nested_path`` the EXE inside it).
    """
    common = {"PackageIdentifier": identifier, "PackageVersion": version}
    version_doc: Dict[str, object] = dict(common)
    version_doc.update({
        "DefaultLocale": locale, "ManifestType": "version", "ManifestVersion": MANIFEST_VERSION,
    })

    installer_doc: Dict[str, object] = dict(common)
    installer_doc["InstallerType"] = installer_type
    if installer_type == "zip":
        installer_doc["NestedInstallerType"] = "portable"
        nested: Dict[str, object] = {"RelativeFilePath": nested_path}
        if command_alias:
            nested["PortableCommandAlias"] = command_alias
        installer_doc["NestedInstallerFiles"] = [nested]
    if installer_type == "inno":
        installer_doc["UpgradeBehavior"] = "install"
    installer_doc["Installers"] = [{
        "Architecture": architecture,
        "InstallerUrl": installer_url,
        # winget-pkgs writes hashes in upper case.
        "InstallerSha256": sha256.upper(),
    }]
    installer_doc.update({"ManifestType": "installer", "ManifestVersion": MANIFEST_VERSION})

    locale_doc: Dict[str, object] = dict(common)
    locale_doc.update({"PackageLocale": locale, "Publisher": publisher})
    if publisher_url:
        locale_doc["PublisherUrl"] = publisher_url
    locale_doc.update({
        "PackageName": name, "License": license_text, "ShortDescription": short_description,
        "ManifestType": "defaultLocale", "ManifestVersion": MANIFEST_VERSION,
    })
    return {"version": version_doc, "installer": installer_doc, "defaultLocale": locale_doc}


def _check_length(problems: List[str], kind: str, key: str, value: object) -> None:
    bounds = _LENGTHS.get(key)
    if bounds and isinstance(value, str) and not bounds[0] <= len(value) <= bounds[1]:
        problems.append(f"{kind}.{key}: length must be {bounds[0]}–{bounds[1]}")


def validate_manifests(docs: Dict[str, Dict[str, object]]) -> List[str]:
    """Problems against the 1.28.0 schema's required fields and formats ([] = valid)."""
    problems: List[str] = []
    for kind, required in REQUIRED.items():
        doc = docs.get(kind)
        if not isinstance(doc, dict):
            problems.append(f"{kind}: missing")
            continue
        for key in required:
            if doc.get(key) in (None, "", []):
                problems.append(f"{kind}.{key}: required")
        for key, value in doc.items():
            _check_length(problems, kind, key, value)
        if doc.get("ManifestType") != kind:
            problems.append(f"{kind}.ManifestType: must be {kind}")
        if doc.get("ManifestVersion") != MANIFEST_VERSION:
            problems.append(f"{kind}.ManifestVersion: must be {MANIFEST_VERSION}")
        identifier = str(doc.get("PackageIdentifier", ""))
        if identifier and not _PACKAGE_IDENTIFIER.match(identifier):
            problems.append(f"{kind}.PackageIdentifier: must look like Publisher.Package")
        version = str(doc.get("PackageVersion", ""))
        if version and not _PACKAGE_VERSION.match(version):
            problems.append(f"{kind}.PackageVersion: invalid characters")
        for key in ("DefaultLocale", "PackageLocale"):
            if doc.get(key) and not _LOCALE.match(str(doc[key])):
                problems.append(f"{kind}.{key}: not a locale (e.g. en-US)")
        for key in ("PublisherUrl", "PackageUrl"):
            if doc.get(key) and not _URL.match(str(doc[key])):
                problems.append(f"{kind}.{key}: must be an http(s) URL")

    installer = docs.get("installer") or {}
    root_type = installer.get("InstallerType")
    if root_type is not None and root_type not in INSTALLER_TYPES:
        problems.append("installer.InstallerType: unknown type")
    nested = installer.get("NestedInstallerType")
    if nested is not None and nested not in NESTED_INSTALLER_TYPES:
        problems.append("installer.NestedInstallerType: unknown type")
    if root_type == "zip" and not installer.get("NestedInstallerFiles"):
        problems.append("installer.NestedInstallerFiles: required for a zip")
    for index, nested_file in enumerate(installer.get("NestedInstallerFiles") or []):
        where = f"installer.NestedInstallerFiles[{index}]"
        path = nested_file.get("RelativeFilePath") if isinstance(nested_file, dict) else None
        if not isinstance(path, str) or not 1 <= len(path) <= 512:
            problems.append(f"{where}.RelativeFilePath: length must be 1–512")
        alias = nested_file.get("PortableCommandAlias") if isinstance(nested_file, dict) else None
        if alias is not None and not 1 <= len(str(alias)) <= 40:
            problems.append(f"{where}.PortableCommandAlias: length must be 1–40")
    entries = installer.get("Installers") or []
    if not isinstance(entries, list):
        entries = []
    for index, entry in enumerate(entries):
        where = f"installer.Installers[{index}]"
        for key in INSTALLER_REQUIRED:
            if not entry.get(key):
                problems.append(f"{where}.{key}: required")
        if entry.get("Architecture") and entry["Architecture"] not in ARCHITECTURES:
            problems.append(f"{where}.Architecture: unknown architecture")
        if entry.get("InstallerUrl") and not _URL.match(str(entry["InstallerUrl"])):
            problems.append(f"{where}.InstallerUrl: must be an http(s) URL")
        _check_length(problems, where, "InstallerUrl", entry.get("InstallerUrl"))
        if entry.get("InstallerSha256") and not _SHA256.match(str(entry["InstallerSha256"])):
            problems.append(f"{where}.InstallerSha256: must be 64 hex characters")
        if root_type is None and not entry.get("InstallerType"):
            problems.append(f"{where}.InstallerType: required (here or at the root)")
    return problems


# ── YAML ──────────────────────────────────────────────────────────────────

_PLAIN = re.compile(r"^[A-Za-z_][A-Za-z0-9 _.,/+()-]*$")
_YAML_WORDS = frozenset({"true", "false", "yes", "no", "on", "off", "null", "y", "n", "~"})


def yaml_scalar(value: object) -> str:
    """A YAML scalar: plain when unambiguous, double-quoted (JSON-style) otherwise."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if (_PLAIN.match(text) and text.lower() not in _YAML_WORDS
            and not text.endswith(" ") and ": " not in text and " #" not in text):
        return text
    import json

    return json.dumps(text, ensure_ascii=False)


def render_yaml(doc: Dict[str, object], kind: str) -> str:
    lines = [
        "# Created with Python to EXE Converter",
        f"# yaml-language-server: $schema={SCHEMA_URL.format(kind=kind.lower())}",
        "",
    ]
    for key, value in doc.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                first = True
                for sub_key, sub_value in item.items():
                    prefix = "- " if first else "  "
                    lines.append(f"{prefix}{sub_key}: {yaml_scalar(sub_value)}")
                    first = False
        else:
            lines.append(f"{key}: {yaml_scalar(value)}")
    return "\n".join(lines) + "\n"


def file_names(identifier: str, locale: str) -> Dict[str, str]:
    return {
        "version": f"{identifier}.yaml",
        "installer": f"{identifier}.installer.yaml",
        "defaultLocale": f"{identifier}.locale.{locale}.yaml",
    }


def write_manifests(docs: Dict[str, Dict[str, object]], folder: str) -> List[str]:
    """Write the three files into ``folder``; returns their paths."""
    identifier = str(docs["version"]["PackageIdentifier"])
    locale = str(docs["defaultLocale"]["PackageLocale"])
    os.makedirs(folder, exist_ok=True)
    paths = []
    for kind, name in file_names(identifier, locale).items():
        path = os.path.join(folder, name)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(render_yaml(docs[kind], kind))
        paths.append(path)
    return paths


def choose_installer(installer: str = "", exe: str = "", portable_zip: str = ""
                     ) -> Tuple[Optional[str], str]:
    """(file, winget InstallerType) for the best artifact a release produced."""
    if installer:
        return installer, "inno"
    if exe and exe.lower().endswith(".exe"):
        return exe, "portable"
    if portable_zip:
        return portable_zip, "zip"
    return None, ""
