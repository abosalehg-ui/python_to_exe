"""Semantic versions, and one bump applied everywhere at once.

Before 1.6 the version lived in three places that nothing kept in step: the
Version Info tab (``1.0.0.0``), the installer tab (``1.0.0``) and, from 1.5,
the Runtime Kit's app version that the self-updater compares against. A
release that bumped one and forgot another shipped an installer saying 1.3
around an EXE saying 1.2 — or an updater that offers the same update forever.
``apply_version`` changes all of them together.
"""

import re
from dataclasses import dataclass
from typing import List, Tuple

# semver.org 2.0.0, the official regular expression.
_SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$",
    re.ASCII,  # \d would otherwise accept Arabic-Indic digits ("١.٢.٣")
)

BUMP_PARTS = ("major", "minor", "patch")


@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int
    prerelease: str = ""
    build: str = ""

    def __str__(self) -> str:
        text = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            text += f"-{self.prerelease}"
        if self.build:
            text += f"+{self.build}"
        return text

    @property
    def core(self) -> Tuple[int, int, int]:
        return (self.major, self.minor, self.patch)


def normalize(text: str) -> str:
    """Trim, and drop a leading ``v`` (``v1.2.3`` is how tags spell it)."""
    text = (text or "").strip()
    if text[:1] in ("v", "V") and text[1:2].isdigit():
        text = text[1:]
    return text


def parse_semver(text: str) -> SemVer:
    """Parse ``1.2.3``, ``1.2.3-rc.1``, ``v1.2.3``. Raises ``ValueError``."""
    match = _SEMVER.match(normalize(text))
    if not match:
        raise ValueError(f"not a semantic version (MAJOR.MINOR.PATCH): {text!r}")
    major, minor, patch, pre, build = match.groups()
    return SemVer(int(major), int(minor), int(patch), pre or "", build or "")


def is_semver(text: str) -> bool:
    try:
        parse_semver(text)
    except ValueError:
        return False
    return True


def bump(version: str, part: str) -> str:
    """The next ``major``/``minor``/``patch`` version. A pre-release is dropped."""
    current = parse_semver(version)
    if part == "major":
        return str(SemVer(current.major + 1, 0, 0))
    if part == "minor":
        return str(SemVer(current.major, current.minor + 1, 0))
    if part == "patch":
        # 1.2.3-rc.1 → 1.2.3: finishing a pre-release is the patch bump.
        if current.prerelease:
            return str(SemVer(*current.core))
        return str(SemVer(current.major, current.minor, current.patch + 1))
    raise ValueError(f"unknown version part: {part!r} (expected one of {BUMP_PARTS})")


def windows_version(version: str) -> str:
    """The four-number form Windows file metadata needs: ``1.2.3`` → ``1.2.3.0``.

    A Windows version resource cannot carry ``-rc.1``; the pre-release still
    appears in the installer and the release, where text is allowed.
    """
    v = parse_semver(version)
    return f"{v.major}.{v.minor}.{v.patch}.0"


def tag_for(version: str, prefix: str = "v") -> str:
    return f"{prefix}{normalize(version)}"


@dataclass(frozen=True)
class VersionChange:
    field: str  # e.g. "version_info.file_version"
    old: str
    new: str


def _targets(project, version: str) -> List[Tuple[object, str, str, str]]:
    """(object, attribute, label, value it must hold) for every version field."""
    win = windows_version(version)
    plain = normalize(version)
    return [
        (project, "version", "project.version", plain),
        (project.version_info, "file_version", "version_info.file_version", win),
        (project.version_info, "product_version", "version_info.product_version", win),
        (project.installer, "app_version", "installer.app_version", plain),
        (project.build.runtime_kit, "app_version", "runtime_kit.app_version", plain),
    ]


def apply_version(project, version: str) -> List[VersionChange]:
    """Set ``version`` in every place a project records it; returns what changed.

    Idempotent: applying the current version again changes nothing.
    """
    parse_semver(version)
    changes = []
    for obj, attr, label, value in _targets(project, version):
        old = getattr(obj, attr)
        if old != value:
            setattr(obj, attr, value)
            changes.append(VersionChange(label, old, value))
    return changes


def version_mismatches(project) -> List[VersionChange]:
    """Fields that disagree with ``project.version`` (empty when consistent).

    Empty Version Info and Runtime Kit fields are not mismatches: they are
    simply unused, and a build fills nothing from them.
    """
    if not is_semver(project.version):
        return []
    found = []
    for obj, attr, label, value in _targets(project, project.version)[1:]:
        current = getattr(obj, attr)
        if current and current != value:
            found.append(VersionChange(label, current, value))
    return found
