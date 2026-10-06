"""GitHub publishing against a local fake API that records every request."""

import io
import logging
import urllib.error

import pytest

from py2exe_gui.core.release.github import (
    API_VERSION,
    GitHubClient,
    GitHubError,
    is_repository,
    publish_release,
)
from tests.fake_github import FakeGitHub

TOKEN = "ghp_" + "T" * 36


def client_for(fake, token=TOKEN, repo="me/app"):
    return GitHubClient(token, repo, api_url=fake.url, allow_insecure_localhost=True)


@pytest.fixture
def files(tmp_path):
    paths = []
    for name, data in (("App-1.0.0.exe", b"MZ" * 100), ("App-1.0.0-portable.zip", b"PK" * 50),
                       ("SHA256SUMS.txt", b"abc  App\n")):
        p = tmp_path / name
        p.write_bytes(data)
        paths.append(str(p))
    return paths


def test_publish_creates_the_release_and_uploads_every_asset(files, caplog):
    log = []
    with FakeGitHub(TOKEN) as fake, caplog.at_level(logging.DEBUG):
        result = publish_release(client_for(fake), "v1.0.0", "App 1.0.0", "## Notes\nملاحظات",
                                 files, draft=True, prerelease=True,
                                 target_commitish="abc123", log=log.append)
        requests = list(fake.requests)
        release = fake.releases[0]
        uploads = dict(fake.uploads)

    assert result.created and result.uploaded == [
        "App-1.0.0.exe", "App-1.0.0-portable.zip", "SHA256SUMS.txt"]
    assert result.assets["App-1.0.0.exe"].endswith("/releases/download/v1.0.0/App-1.0.0.exe")
    assert release["draft"] is True and release["prerelease"] is True
    assert release["target_commitish"] == "abc123"
    assert release["body"] == "## Notes\nملاحظات"
    assert uploads["App-1.0.0.exe"] == b"MZ" * 100

    # Endpoints, in order.
    calls = [(r["method"], r["path"]) for r in requests]
    assert calls[0] == ("GET", "/repos/me/app/releases/tags/v1.0.0")
    assert calls[1] == ("GET", "/repos/me/app/releases")
    assert calls[2] == ("POST", "/repos/me/app/releases")
    assert [c for c in calls[3:]] == [("POST", f"/uploads/repos/me/app/releases/{release['id']}"
                                               "/assets")] * 3
    assert [r["query"]["name"] for r in requests[3:]] == [
        "App-1.0.0.exe", "App-1.0.0-portable.zip", "SHA256SUMS.txt"]

    # Headers on every request.
    for r in requests:
        h = r["headers"]
        assert h["authorization"] == f"Bearer {TOKEN}"
        assert h["accept"] == "application/vnd.github+json"
        assert h["x-github-api-version"] == API_VERSION
        assert h["user-agent"].startswith("py2exe-gui")
    assert requests[3]["headers"]["content-type"] in ("application/octet-stream",
                                                     "application/x-msdownload",
                                                     "application/x-msdos-program")
    assert requests[4]["headers"]["content-type"] == "application/zip"
    assert requests[3]["body_size"] == 200

    # The token never reaches the log.
    assert TOKEN not in "\n".join(log) and TOKEN not in caplog.text


def test_publishing_again_reuses_release_and_assets(files):
    with FakeGitHub(TOKEN) as fake:
        publish_release(client_for(fake), "v1.0.0", "n", "b", files)
        fake.requests.clear()
        again = publish_release(client_for(fake), "v1.0.0", "n", "b", files)
        methods = [r["method"] for r in fake.requests]
        assert len(fake.releases) == 1
    assert not again.created and again.uploaded == [] and len(again.reused) == 3
    assert "POST" not in methods


def test_a_changed_asset_is_replaced(files):
    with FakeGitHub(TOKEN) as fake:
        publish_release(client_for(fake), "v1.0.0", "n", "b", files)
        with open(files[0], "ab") as f:
            f.write(b"more")
        fake.requests.clear()
        result = publish_release(client_for(fake), "v1.0.0", "n", "b", files)
        calls = [(r["method"], r["path"].split("/")[-2]) for r in fake.requests]
        assets = fake.releases[0]["assets"]
    assert result.uploaded == ["App-1.0.0.exe"]
    assert ("DELETE", "assets") in calls
    assert sorted(a["name"] for a in assets) == sorted(
        ["App-1.0.0.exe", "App-1.0.0-portable.zip", "SHA256SUMS.txt"])


def test_draft_releases_are_found_through_the_list(files):
    with FakeGitHub(TOKEN) as fake:
        publish_release(client_for(fake), "v2.0.0", "n", "b", files[:1], draft=True)
        result = publish_release(client_for(fake), "v2.0.0", "n", "b", files[:1], draft=True)
        assert len(fake.releases) == 1
    assert result.reused == ["App-1.0.0.exe"]


def test_bad_token_is_an_error_that_does_not_echo_the_token(files):
    with FakeGitHub(TOKEN) as fake:
        with pytest.raises(GitHubError) as e:
            publish_release(client_for(fake, token="ghp_wrongwrongwrong"), "v1", "n", "b", files)
    assert e.value.status == 401
    assert "ghp_wrongwrongwrong" not in str(e.value)


def test_upload_failure_surfaces(files):
    with FakeGitHub(TOKEN) as fake:
        fake.fail_uploads.add("SHA256SUMS.txt")
        with pytest.raises(GitHubError) as e:
            publish_release(client_for(fake), "v1", "n", "b", files)
    assert e.value.status == 500 and "upload failed" in str(e.value)


def test_http_and_foreign_hosts_are_refused():
    with pytest.raises(GitHubError):
        GitHubClient(TOKEN, "me/app", api_url="http://api.example.com")
    with pytest.raises(GitHubError):
        GitHubClient(TOKEN, "me/app", api_url="http://localhost:1")  # flag not set
    client = GitHubClient(TOKEN, "me/app")
    with pytest.raises(GitHubError, match="refusing to send the token"):
        client.upload_asset({"upload_url": "https://evil.example.com/up{?name}"}, __file__)
    with pytest.raises(GitHubError):
        client.upload_asset({"upload_url": ""}, __file__)
    # The official API also trusts its upload host.
    assert "uploads.github.com" in client._token_hosts
    assert TOKEN not in repr(client)


def test_client_rejects_missing_token_and_bad_repository():
    with pytest.raises(GitHubError):
        GitHubClient("", "me/app")
    for slug in ("", "me", "me/app/extra", "../x", "me/..", "-bad/app"):
        assert not is_repository(slug)
        with pytest.raises(GitHubError):
            GitHubClient(TOKEN, slug)
    assert is_repository("abosalehg-ui/python_to_exe")


class _Opener:
    """An opener that replays canned outcomes, for error paths a server can't easily give."""

    def __init__(self, outcome):
        self.outcome = outcome
        self.requests = []

    def open(self, request, timeout=None):
        self.requests.append(request)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


class _Response(io.BytesIO):
    def __init__(self, status, body):
        super().__init__(body)
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def test_network_errors_and_redirects_are_reported_without_the_token():
    for error in (urllib.error.URLError(f"boom {TOKEN}"), OSError("reset")):
        client = GitHubClient(TOKEN, "me/app", opener=_Opener(error))
        with pytest.raises(GitHubError) as e:
            client.find_release("v1")
        assert TOKEN not in str(e.value)
    redirect = urllib.error.HTTPError("https://api.github.com/x", 301, "Moved", {},
                                      io.BytesIO(b'{"message": "Moved Permanently"}'))
    client = GitHubClient(TOKEN, "me/app", opener=_Opener(redirect))
    with pytest.raises(GitHubError) as e:
        client.create_release("v1", "n", "b")
    assert e.value.status == 301


def test_non_json_bodies():
    client = GitHubClient(TOKEN, "me/app", opener=_Opener(_Response(200, b"not json")))
    assert client._request("GET", "https://api.github.com/x") is None
    err = urllib.error.HTTPError("u", 502, "Bad", {}, io.BytesIO(b"<html>gateway</html>"))
    client = GitHubClient(TOKEN, "me/app", opener=_Opener(err))
    with pytest.raises(GitHubError, match="gateway"):
        client._request("GET", "https://api.github.com/x")


def test_find_release_raises_other_errors_and_lists_assets_when_missing():
    err = urllib.error.HTTPError("u", 403, "Forbidden", {}, io.BytesIO(b'{"message":"rate"}'))
    client = GitHubClient(TOKEN, "me/app", opener=_Opener(err))
    with pytest.raises(GitHubError, match="rate"):
        client.find_release("v1")
    opener = _Opener(_Response(200, b'[{"name": "a", "id": 1}]'))
    client = GitHubClient(TOKEN, "me/app", opener=opener)
    assert client.list_assets({"id": 7}) == [{"name": "a", "id": 1}]
    assert opener.requests[0].full_url.endswith("/releases/7/assets?per_page=100")
