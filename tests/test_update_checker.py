"""Tests for the release-check logic. No test here touches the network."""

from urllib.error import URLError

import pytest

from py2exe_gui.core.update_checker import (
    RELEASES_PAGE_URL,
    check_for_update,
    fetch_latest_release,
    is_newer,
    parse_version,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1.2.3", (1, 2, 3)),
        ("v1.2.3", (1, 2, 3)),
        ("V1.2.3", (1, 2, 3)),
        ("1.2", (1, 2)),
        ("2.0.0-beta.1", (2, 0, 0)),
        ("1.0.0+build7", (1, 0, 0)),
        ("  1.4.0  ", (1, 4, 0)),
        ("", ()),
        ("not-a-version", ()),
    ],
)
def test_parse_version(text, expected):
    assert parse_version(text) == expected


@pytest.mark.parametrize(
    "candidate,current",
    [
        ("1.2.0", "1.1.0"),
        ("2.0.0", "1.9.9"),
        ("1.1.1", "1.1.0"),
        ("v1.2.0", "1.1.0"),
        ("1.10.0", "1.9.0"),  # numeric, not lexicographic
    ],
)
def test_is_newer_true(candidate, current):
    assert is_newer(candidate, current) is True


@pytest.mark.parametrize(
    "candidate,current",
    [
        ("1.1.0", "1.1.0"),
        ("1.0.0", "1.1.0"),
        ("1.2", "1.2.0"),  # equal once zero-padded
        ("1.2.0", "1.2"),
        ("", "1.1.0"),
        ("garbage", "1.1.0"),
    ],
)
def test_is_newer_false(candidate, current):
    assert is_newer(candidate, current) is False


def test_check_returns_info_for_a_newer_release():
    payload = {
        "tag_name": "v1.3.0",
        "html_url": "https://example.invalid/releases/v1.3.0",
        "name": "Phase 9",
    }
    info = check_for_update("1.2.0", fetch=lambda: payload)
    assert info is not None
    assert info.version == "1.3.0"
    assert info.url == "https://example.invalid/releases/v1.3.0"
    assert info.name == "Phase 9"


def test_check_returns_none_when_up_to_date():
    payload = {"tag_name": "v1.2.0"}
    assert check_for_update("1.2.0", fetch=lambda: payload) is None


def test_check_returns_none_when_the_fetch_fails():
    """A failed check is not worth interrupting the user for."""
    assert check_for_update("1.2.0", fetch=lambda: None) is None


def test_check_survives_a_payload_without_a_tag():
    assert check_for_update("1.2.0", fetch=lambda: {}) is None


def test_check_falls_back_to_the_name_field():
    info = check_for_update("1.2.0", fetch=lambda: {"name": "1.5.0"})
    assert info is not None
    assert info.version == "1.5.0"


def test_check_falls_back_to_the_releases_page_without_a_url():
    info = check_for_update("1.2.0", fetch=lambda: {"tag_name": "v9.0.0"})
    assert info is not None
    assert info.url == RELEASES_PAGE_URL


# ── The network call itself (mocked; no socket is opened) ──────────────────


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_fetch_parses_a_json_object(monkeypatch):
    monkeypatch.setattr(
        "py2exe_gui.core.update_checker.urlopen",
        lambda *a, **k: _FakeResponse(b'{"tag_name": "v2.0.0"}'),
    )
    assert fetch_latest_release()["tag_name"] == "v2.0.0"


def test_fetch_returns_none_on_a_network_error(monkeypatch):
    def boom(*args, **kwargs):
        raise URLError("no route to host")

    monkeypatch.setattr("py2exe_gui.core.update_checker.urlopen", boom)
    assert fetch_latest_release() is None


def test_fetch_returns_none_on_a_timeout(monkeypatch):
    def boom(*args, **kwargs):
        raise TimeoutError("timed out")

    monkeypatch.setattr("py2exe_gui.core.update_checker.urlopen", boom)
    assert fetch_latest_release() is None


def test_fetch_returns_none_on_malformed_json(monkeypatch):
    monkeypatch.setattr(
        "py2exe_gui.core.update_checker.urlopen",
        lambda *a, **k: _FakeResponse(b"<html>not json</html>"),
    )
    assert fetch_latest_release() is None


def test_fetch_rejects_a_json_array(monkeypatch):
    """The endpoint returns an object; a list means something else answered."""
    monkeypatch.setattr(
        "py2exe_gui.core.update_checker.urlopen",
        lambda *a, **k: _FakeResponse(b"[1, 2, 3]"),
    )
    assert fetch_latest_release() is None


def test_fetch_survives_undecodable_bytes(monkeypatch):
    monkeypatch.setattr(
        "py2exe_gui.core.update_checker.urlopen",
        lambda *a, **k: _FakeResponse(b"\xff\xfe\x00garbage"),
    )
    assert fetch_latest_release() is None
