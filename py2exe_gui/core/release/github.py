"""Publishing a release on GitHub through the REST API.

Endpoints used (API version 2022-11-28):

* ``GET  /repos/{owner}/{repo}/releases/tags/{tag}`` — reuse an existing
  release (``GET /repos/{owner}/{repo}/releases`` as well, because the tag
  endpoint does not return drafts);
* ``POST /repos/{owner}/{repo}/releases`` — create it;
* ``POST <upload_url>?name=<asset>`` — upload each file;
* ``DELETE /repos/{owner}/{repo}/releases/assets/{id}`` — replace an asset
  of the same name whose size differs.

Publishing again after a failure therefore picks up where it stopped instead
of creating a second release or duplicate assets.

The token is sent only to the API host (and ``uploads.github.com`` for the
official API): an ``upload_url`` pointing anywhere else is refused, and
redirects are not followed, so the ``Authorization`` header can never be
carried to a third host. Every message this module produces passes through
``redact``.
"""

import json
import mimetypes
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

from py2exe_gui.core.release.credentials import redact

API_URL = "https://api.github.com"
API_VERSION = "2022-11-28"
_REPOSITORY = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9._-]{1,100}$")
_LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")


class GitHubError(Exception):
    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status


def is_repository(slug: str) -> bool:
    return bool(_REPOSITORY.match((slug or "").strip())) and ".." not in slug


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None  # urllib then raises HTTPError for the 3xx response


@dataclass
class PublishResult:
    html_url: str = ""
    release_id: int = 0
    created: bool = False
    #: asset name → browser_download_url
    assets: Dict[str, str] = field(default_factory=dict)
    uploaded: List[str] = field(default_factory=list)
    reused: List[str] = field(default_factory=list)


class GitHubClient:
    """A minimal client for the release endpoints."""

    def __init__(self, token: str, repository: str, api_url: str = API_URL,
                 user_agent: str = "py2exe-gui", timeout: float = 120,
                 allow_insecure_localhost: bool = False, opener=None):
        if not token:
            raise GitHubError("no GitHub token")
        if not is_repository(repository):
            raise GitHubError(f"not a GitHub repository (owner/name): {repository!r}")
        self._token = token
        self.repository = repository.strip()
        self.api_url = api_url.rstrip("/")
        self.allow_insecure_localhost = allow_insecure_localhost
        self._check_url(self.api_url)
        self.user_agent = user_agent
        self.timeout = timeout
        self._opener = opener or urllib.request.build_opener(_NoRedirects())
        api_host = urllib.parse.urlsplit(self.api_url).hostname or ""
        self._token_hosts = {api_host}
        if api_host == "api.github.com":
            self._token_hosts.add("uploads.github.com")

    def __repr__(self) -> str:
        return f"GitHubClient(repository={self.repository!r}, api_url={self.api_url!r})"

    # ── Plumbing ──────────────────────────────────────────────────────

    def redact(self, text: str) -> str:
        return redact(text, [self._token])

    def _check_url(self, url: str) -> None:
        parts = urllib.parse.urlsplit(url)
        host = (parts.hostname or "").lower()
        if parts.scheme == "https" and host:
            return
        if self.allow_insecure_localhost and parts.scheme == "http" and host in _LOCAL_HOSTS:
            return
        raise GitHubError(f"refusing a non-HTTPS URL: {url}")

    def _request(self, method: str, url: str, payload=None, data: Optional[bytes] = None,
                 content_type: str = "", expect=(200, 201, 204)):
        self._check_url(url)
        host = (urllib.parse.urlsplit(url).hostname or "").lower()
        if host not in self._token_hosts:
            raise GitHubError(f"refusing to send the token to {host}")
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": self.user_agent,
            "Authorization": f"Bearer {self._token}",
        }
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            content_type = "application/json"
        if content_type:
            headers["Content-Type"] = content_type
        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                status = response.status
                body = response.read()
        except urllib.error.HTTPError as e:
            status, body = e.code, e.read() or b""
        except (urllib.error.URLError, OSError) as e:
            raise GitHubError(self.redact(f"{method} {url}: {e}")) from None
        if status not in expect:
            raise GitHubError(self.redact(
                f"{method} {url}: HTTP {status} {self._message(body)}"
            ), status)
        if not body:
            return None
        try:
            return json.loads(body.decode("utf-8"))
        except ValueError:
            return None

    @staticmethod
    def _message(body: bytes) -> str:
        try:
            data = json.loads(body.decode("utf-8"))
            return str(data.get("message", ""))[:300]
        except (ValueError, AttributeError):
            return body[:200].decode("utf-8", "replace")

    def _repo_url(self, path: str) -> str:
        return f"{self.api_url}/repos/{self.repository}{path}"

    # ── Releases ──────────────────────────────────────────────────────

    def find_release(self, tag: str) -> Optional[dict]:
        """The release for ``tag`` (drafts included), or None."""
        quoted = urllib.parse.quote(tag, safe="")
        try:
            return self._request("GET", self._repo_url(f"/releases/tags/{quoted}"))
        except GitHubError as e:
            if e.status != 404:
                raise
        releases = self._request("GET", self._repo_url("/releases?per_page=100")) or []
        for release in releases:
            if isinstance(release, dict) and release.get("tag_name") == tag:
                return release
        return None

    def create_release(self, tag: str, name: str, body: str, draft: bool = False,
                       prerelease: bool = False, target_commitish: str = "") -> dict:
        payload = {"tag_name": tag, "name": name, "body": body,
                   "draft": bool(draft), "prerelease": bool(prerelease)}
        if target_commitish:
            payload["target_commitish"] = target_commitish
        return self._request("POST", self._repo_url("/releases"), payload=payload)

    def list_assets(self, release: dict) -> List[dict]:
        if isinstance(release.get("assets"), list):
            return release["assets"]
        return self._request(
            "GET", self._repo_url(f"/releases/{release['id']}/assets?per_page=100")
        ) or []

    def delete_asset(self, asset_id: int) -> None:
        self._request("DELETE", self._repo_url(f"/releases/assets/{asset_id}"))

    def upload_asset(self, release: dict, path: str, name: str = "") -> dict:
        name = name or os.path.basename(path)
        template = str(release.get("upload_url", ""))
        upload = template.split("{", 1)[0]
        if not upload:
            raise GitHubError("the release has no upload URL")
        url = f"{upload}?{urllib.parse.urlencode({'name': name})}"
        content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
        with open(path, "rb") as f:
            data = f.read()
        return self._request("POST", url, data=data, content_type=content_type)


def publish_release(client: GitHubClient, tag: str, name: str, notes: str,
                    files: Sequence[str], draft: bool = False, prerelease: bool = False,
                    target_commitish: str = "",
                    log: Callable[[str], None] = lambda _m: None) -> PublishResult:
    """Create (or reuse) the release for ``tag`` and upload ``files``. Idempotent."""
    result = PublishResult()
    release = client.find_release(tag)
    if release is None:
        release = client.create_release(tag, name, notes, draft, prerelease, target_commitish)
        result.created = True
        log(f"created release {tag}")
    else:
        log(f"reusing release {tag}")
    result.html_url = str(release.get("html_url", ""))
    result.release_id = int(release.get("id", 0) or 0)
    existing = {a.get("name"): a for a in client.list_assets(release) if isinstance(a, dict)}
    for path in files:
        asset_name = os.path.basename(path)
        current = existing.get(asset_name)
        if current is not None and int(current.get("size", -1)) == os.path.getsize(path):
            result.assets[asset_name] = str(current.get("browser_download_url", ""))
            result.reused.append(asset_name)
            log(f"already uploaded: {asset_name}")
            continue
        if current is not None:
            client.delete_asset(int(current["id"]))
        uploaded = client.upload_asset(release, path, asset_name) or {}
        result.assets[asset_name] = str(uploaded.get("browser_download_url", ""))
        result.uploaded.append(asset_name)
        log(f"uploaded: {asset_name}")
    return result
