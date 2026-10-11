"""The projects workspace (2.0 milestone 6): one summary per recent project.

The home view lists the recent ``p2e.toml`` files and, for each, what the app
already knows about the project without opening it: the name and version from
the file, the last build from the build history (``size_bytes`` and the
result, kept since 1.4), and the last release from the ``release/<version>/``
folders the 1.6 pipeline writes beside the build.

Everything here is data: this module never imports Qt, never raises for a
project it cannot read (the summary says *why* instead), and the sparkline is
a list of points the view only has to draw. The command line and the tests
use it as it is.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Optional, Sequence, Tuple

from py2exe_gui.core.build_history import BuildRecord
from py2exe_gui.core.diagnostics import build_name, build_root
from py2exe_gui.core.fsutil import same_path as _same_path
from py2exe_gui.core.project_file import LoadedProject, ProjectFileError, load_project
from py2exe_gui.core.release.artifacts import CHECKSUMS_NAME
from py2exe_gui.core.release.versioning import parse_semver

#: ``ProjectSummary.status``: the file was read; it is not there; it is there
#: but cannot be used (not TOML, refused for a secret, a newer schema...).
STATUS_OK, STATUS_MISSING, STATUS_UNREADABLE = "ok", "missing", "unreadable"

#: How many sizes a sparkline shows at most: the history keeps 20 builds for
#: every project together, so this is already more than it can hold.
SPARKLINE_POINTS = 20


@dataclass
class ReleaseInfo:
    """One ``release/<version>/`` folder the release pipeline wrote."""

    version: str
    path: str
    #: ISO 8601, from the folder's modification time.
    timestamp: str = ""
    #: Files in the folder (the EXE, the ZIP, SHA256SUMS.txt, the notes...).
    files: int = 0
    checksums: bool = False


@dataclass
class ProjectSummary:
    """What the home view shows for one recent project."""

    path: str
    status: str = STATUS_OK
    #: ``ProjectFileError.code`` (``project_error_text`` translates it) and its detail.
    error_code: str = ""
    error_detail: str = ""
    name: str = ""
    version: str = ""
    source: str = ""
    output_name: str = ""
    engine: str = ""
    repository: str = ""
    warnings: List[str] = field(default_factory=list)
    #: The newest build of this project in the history, whatever its result.
    last_build: Optional[BuildRecord] = None
    builds: int = 0
    #: Output sizes of the successful builds, oldest first (the sparkline).
    sizes: List[int] = field(default_factory=list)
    last_release: Optional[ReleaseInfo] = None

    @property
    def ok(self) -> bool:
        return self.status == STATUS_OK

    def display_name(self) -> str:
        """The project's name, or the folder's when the file has none or is gone."""
        return (self.name or self.output_name
                or os.path.basename(os.path.dirname(self.path)) or self.path)

    def size_delta(self) -> Optional[int]:
        """Newest size minus the one before it; None with fewer than two builds."""
        if len(self.sizes) < 2:
            return None
        return self.sizes[-1] - self.sizes[-2]


# ── Build history ─────────────────────────────────────────────────────────


def project_records(records: Sequence[BuildRecord], source: str,
                    output_name: str) -> List[BuildRecord]:
    """The history records of one project (same script, same output name),
    newest first as the history keeps them."""
    return [
        r for r in records
        if _same_path(getattr(r, "source", ""), source)
        and getattr(r, "output_name", "") == output_name
    ]


def size_history(records: Sequence[BuildRecord], limit: int = SPARKLINE_POINTS) -> List[int]:
    """Output sizes of the successful builds, oldest first.

    A failed build has no output and a record from before 1.4 has no size;
    neither is a point on the line.
    """
    sizes = [int(r.size_bytes) for r in records
             if getattr(r, "success", False) and int(getattr(r, "size_bytes", 0) or 0) > 0]
    sizes.reverse()
    return sizes[-limit:] if limit else sizes


# ── Releases ──────────────────────────────────────────────────────────────


def _iso_mtime(path: str) -> str:
    try:
        return datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds")
    except (OSError, OverflowError, ValueError):
        return ""


def find_releases(root: str) -> List[ReleaseInfo]:
    """Every ``release/<semver>/`` folder under ``root``, newest version last.

    A folder whose name is not a semantic version is not a release of this
    pipeline (``artifacts.release_dir`` always names one) and is skipped.
    """
    folder = os.path.join(root, "release") if root else ""
    try:
        names = os.listdir(folder) if folder else []
    except OSError:
        return []
    found = []
    for name in names:
        path = os.path.join(folder, name)
        if not os.path.isdir(path):
            continue
        try:
            semver = parse_semver(name)
        except ValueError:
            continue
        try:
            files = [n for n in os.listdir(path) if os.path.isfile(os.path.join(path, n))]
        except OSError:
            files = []
        found.append((semver, ReleaseInfo(
            version=name, path=path, timestamp=_iso_mtime(path), files=len(files),
            checksums=CHECKSUMS_NAME in files,
        )))
    # Pre-releases sort before the final version of the same core, as semver says.
    found.sort(key=lambda item: (item[0].core, item[0].prerelease == "", item[0].prerelease))
    return [info for _semver, info in found]


def last_release(root: str) -> Optional[ReleaseInfo]:
    releases = find_releases(root)
    return releases[-1] if releases else None


# ── Summaries ─────────────────────────────────────────────────────────────


def summarize_project(path: str, records: Sequence[BuildRecord] = (),
                      loader: Callable[[str], LoadedProject] = load_project) -> ProjectSummary:
    """Everything the home view shows for ``path``. Never raises.

    A file that is gone is ``missing``; one that cannot be used (bad TOML, a
    refused secret, an unknown engine, a newer schema) is ``unreadable`` with
    the error's code, so the view can say why and offer to forget it.
    """
    summary = ProjectSummary(path=path)
    if not path or not os.path.isfile(path):
        summary.status = STATUS_MISSING
        return summary
    try:
        loaded = loader(path)
    except ProjectFileError as e:
        summary.status = STATUS_UNREADABLE
        summary.error_code, summary.error_detail = e.code, e.detail
        return summary
    except Exception as e:  # noqa: BLE001 - one broken file must never take the view down
        summary.status = STATUS_UNREADABLE
        summary.error_code, summary.error_detail = "generic", f"{type(e).__name__}: {e}"
        return summary

    project = loaded.project
    summary.name = project.name
    summary.version = project.version
    summary.source = project.build.source
    summary.output_name = build_name(project.build)
    summary.engine = project.build.engine
    summary.repository = project.release.repository
    summary.warnings = list(loaded.warnings)

    mine = project_records(records, summary.source, summary.output_name)
    summary.builds = len(mine)
    summary.last_build = mine[0] if mine else None
    summary.sizes = size_history(mine)
    if project.build.source:
        summary.last_release = last_release(build_root(project.build))
    return summary


def summarize_projects(paths: Sequence[str], records: Sequence[BuildRecord] = (),
                       loader: Callable[[str], LoadedProject] = load_project
                       ) -> List[ProjectSummary]:
    """One summary per path, in the order given (most recent first)."""
    return [summarize_project(path, records, loader) for path in paths]


# ── The sparkline ─────────────────────────────────────────────────────────


def sparkline_points(sizes: Sequence[int], width: float, height: float,
                     rtl: bool = False, padding: float = 0.0) -> List[Tuple[float, float]]:
    """Where to draw ``sizes`` in a ``width`` x ``height`` box, oldest first.

    Time runs in the reading direction: left to right, or right to left when
    ``rtl`` so the newest build sits where an Arabic reader looks first. The
    smallest size is at the bottom, the largest at the top; one size, or all
    the same, is a flat line through the middle. A single build is one point
    at the newest end.
    """
    values = [max(0, int(v)) for v in sizes]
    if not values or width <= 0 or height <= 0:
        return []
    left, right = padding, width - padding
    top, bottom = padding, height - padding
    if right <= left or bottom <= top:
        return []
    low, high = min(values), max(values)
    span = high - low
    count = len(values)
    points = []
    for index, value in enumerate(values):
        if count == 1:
            x = right
        else:
            x = left + (right - left) * index / (count - 1)
        if rtl:
            x = left + right - x
        if span == 0:
            y = (top + bottom) / 2
        else:
            y = bottom - (bottom - top) * (value - low) / span
        points.append((float(x), float(y)))
    return points


# ── Text helpers (no locale: digits and ISO dates only) ───────────────────


def short_time(iso: str) -> str:
    """``2026-10-11T07:33:02`` → ``2026-10-11 07:33``; anything else unchanged."""
    try:
        return datetime.fromisoformat(iso).strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return iso or ""
