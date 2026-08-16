"""Check GitHub Releases for a newer version of this application.

Deliberately report-only. The check returns a version number and a URL; it
never downloads, unpacks or runs anything. A packaging tool that silently
replaces its own binary is exactly the behaviour the rest of this project
refuses to do on the user's behalf (see the explicit-consent flow around
installing PyInstaller), and a self-updater is a far bigger lever than a pip
install.

The network call is isolated in ``fetch_latest_release`` and injected into
``check_for_update``, so the comparison logic is testable without a socket.
"""

import json
import re
from dataclasses import dataclass
from typing import Callable, Optional, Tuple
from urllib.error import URLError
from urllib.request import Request, urlopen

RELEASES_API_URL = (
    "https://api.github.com/repos/abosalehg-ui/python_to_exe/releases/latest"
)
RELEASES_PAGE_URL = "https://github.com/abosalehg-ui/python_to_exe/releases"

DEFAULT_TIMEOUT = 6.0

_VERSION_PART = re.compile(r"\d+")


@dataclass(frozen=True)
class UpdateInfo:
    """A release that is newer than the running version."""

    version: str
    url: str
    name: str = ""


def parse_version(text: str) -> Tuple[int, ...]:
    """Turn ``v1.2.3``/``1.2.3-beta`` into a comparable tuple of ints.

    Anything after the first non-numeric, non-dot run is discarded, so a
    pre-release suffix compares equal to its base version rather than raising.
    Unparseable input yields ``()``, which sorts below every real version.
    """
    if not text:
        return ()
    head = text.strip().lstrip("vV").split("-")[0].split("+")[0]
    parts = _VERSION_PART.findall(head)
    return tuple(int(p) for p in parts)


def is_newer(candidate: str, current: str) -> bool:
    """True when ``candidate`` is a strictly higher version than ``current``."""
    a, b = parse_version(candidate), parse_version(current)
    if not a:
        return False
    # Compare on equal length so 1.2 and 1.2.0 are the same version.
    width = max(len(a), len(b))
    return a + (0,) * (width - len(a)) > b + (0,) * (width - len(b))


def fetch_latest_release(
    url: str = RELEASES_API_URL, timeout: float = DEFAULT_TIMEOUT
) -> Optional[dict]:
    """GET the latest-release JSON. Returns None on any network/parse failure.

    A failed update check is not an error worth interrupting the user for —
    the caller logs it and moves on.
    """
    request = Request(url, headers={"Accept": "application/vnd.github+json"})
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed https URL
            payload = response.read().decode("utf-8", errors="replace")
    except (URLError, OSError, ValueError):
        return None
    try:
        data = json.loads(payload)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def check_for_update(
    current_version: str,
    fetch: Optional[Callable[[], Optional[dict]]] = None,
) -> Optional[UpdateInfo]:
    """Return an :class:`UpdateInfo` when a newer release exists, else None.

    ``fetch`` is injectable so tests (and offline runs) never touch the network.
    """
    data = (fetch or fetch_latest_release)()
    if not data:
        return None

    tag = str(data.get("tag_name") or data.get("name") or "").strip()
    if not tag or not is_newer(tag, current_version):
        return None

    return UpdateInfo(
        version=tag.lstrip("vV"),
        url=str(data.get("html_url") or RELEASES_PAGE_URL),
        name=str(data.get("name") or ""),
    )
