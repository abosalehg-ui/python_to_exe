"""The converter's signing key and the publish helper."""

import json
import os
import stat
import sys

import pytest

from p2e_runtime import _ed25519
from py2exe_gui.core import update_signing as us


def test_new_key_is_a_valid_pair():
    key = us.new_signing_key()
    assert len(key.seed) == 32 and us.is_public_key(key.public_hex)
    assert us.public_key_from_seed(key.seed).hex() == key.public_hex
    assert key.created.endswith("Z")
    assert us.new_signing_key().seed != key.seed


def test_repr_never_shows_the_secret():
    key = us.new_signing_key()
    assert key.seed.hex() not in repr(key) and key.seed.hex() not in str(key)


def test_fingerprint_and_public_key_check():
    assert us.fingerprint("abcdef0123456789" + "0" * 48) == "abcd ef01 2345 6789"
    assert us.is_public_key("AB" * 32)
    assert not us.is_public_key("ab" * 31) and not us.is_public_key("zz" * 32)


def test_key_file_round_trip_with_owner_only_permissions(tmp_path):
    key = us.new_signing_key()
    path = tmp_path / "signing" / "key.json"
    us.write_key_file(str(path), key)
    assert us.read_key_file(str(path)) == key
    assert us.read_public_key(str(path)) == key.public_hex
    data = json.loads(path.read_text())
    assert data["format"] == us.KEY_FORMAT and "PRIVATE KEY" in data["warning"]
    if sys.platform != "win32":
        assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
        assert stat.S_IMODE(os.stat(path.parent).st_mode) == 0o700


def test_existing_key_is_never_overwritten_by_accident(tmp_path):
    path = str(tmp_path / "key.json")
    first = us.new_signing_key()
    us.write_key_file(path, first)
    with pytest.raises(FileExistsError):
        us.write_key_file(path, us.new_signing_key())
    assert us.read_key_file(path) == first
    second = us.new_signing_key()
    us.write_key_file(path, second, overwrite=True)
    assert us.read_key_file(path) == second


def test_replaced_key_is_kept_not_deleted(tmp_path):
    path = tmp_path / "key.json"
    assert us.backup_existing(str(path)) == ""
    us.write_key_file(str(path), us.new_signing_key())
    backup = us.backup_existing(str(path))
    assert os.path.isfile(backup) and not path.exists()
    assert ".replaced-" in backup


@pytest.mark.parametrize("text,message", [
    ("not json", "not a key file"),
    ("[]", "not a Python to EXE"),
    (json.dumps({"format": "other"}), "not a Python to EXE"),
    (json.dumps({"format": us.KEY_FORMAT, "private_key": "xy"}), "64 hex"),
])
def test_bad_key_files_are_refused(text, message):
    with pytest.raises(ValueError, match=message):
        us.key_from_json(text)


def test_mismatched_public_half_is_refused():
    key, other = us.new_signing_key(), us.new_signing_key()
    data = json.loads(us.key_to_json(key))
    data["public_key"] = other.public_hex
    with pytest.raises(ValueError, match="does not belong"):
        us.key_from_json(json.dumps(data))


def test_read_public_key_of_a_missing_or_broken_file(tmp_path):
    assert us.read_public_key(str(tmp_path / "none.json")) == ""
    (tmp_path / "bad.json").write_text("{")
    assert us.read_public_key(str(tmp_path / "bad.json")) == ""


def test_is_inside(tmp_path):
    project = tmp_path / "proj"
    (project / "sub").mkdir(parents=True)
    assert us.is_inside(str(project / "sub" / "key.json"), str(project))
    assert us.is_inside(str(project), str(project))
    assert not us.is_inside(str(tmp_path / "proj2" / "key.json"), str(project))
    assert not us.is_inside("", str(project)) and not us.is_inside("x", "")


# ── Publishing ─────────────────────────────────────────────────────────────


@pytest.fixture
def build(tmp_path):
    path = tmp_path / "dist" / "Tool.exe"
    path.parent.mkdir()
    path.write_bytes(b"MZ new build" * 100)
    return path


def test_publish_writes_a_signed_manifest(build):
    key = us.new_signing_key()
    result = us.publish_update(str(build), "1.3.0", "https://example.com/Tool-1.3.0.exe", key,
                               notes="Fixes", min_version="1.0", app_name="Tool")
    assert result.manifest_path == str(build.parent / "update.json")
    assert result.signature_path == str(build.parent / "update.json.sig")
    data = open(result.manifest_path, "rb").read()
    manifest = json.loads(data)
    assert manifest == {
        "app": "Tool", "version": "1.3.0", "url": "https://example.com/Tool-1.3.0.exe",
        "sha256": us.file_digest(str(build))[0], "size": 1200, "notes": "Fixes",
        "min_version": "1.0",
    }
    signature = bytes.fromhex(open(result.signature_path).read().strip())
    assert _ed25519.verify(bytes.fromhex(key.public_hex), data, signature)


def test_publish_never_writes_the_private_key(build):
    key = us.new_signing_key()
    us.publish_update(str(build), "1.3.0", "https://example.com/t.exe", key)
    for name in os.listdir(build.parent):
        content = open(build.parent / name, "rb").read()
        assert key.seed.hex().encode() not in content
        assert key.seed not in content


@pytest.mark.parametrize("version,url,min_version,message", [
    ("one", "https://example.com/t.exe", "", "not a version"),
    ("1.0", "http://example.com/t.exe", "", "https://"),
    ("1.0", "https://example.com/t.exe", "x", "not a version"),
])
def test_publish_validates_its_input(build, version, url, min_version, message):
    with pytest.raises(ValueError, match=message):
        us.publish_update(str(build), version, url, us.new_signing_key(),
                          min_version=min_version)
    assert not (build.parent / "update.json").exists()


def test_publish_refuses_missing_or_empty_files(tmp_path):
    key = us.new_signing_key()
    with pytest.raises(ValueError, match="no such file"):
        us.publish_update(str(tmp_path / "none.exe"), "1.0", "https://e.com/x", key)
    empty = tmp_path / "empty.exe"
    empty.write_bytes(b"")
    with pytest.raises(ValueError, match="empty"):
        us.publish_update(str(empty), "1.0", "https://e.com/x", key)


def test_publish_to_another_folder(build, tmp_path):
    out = tmp_path / "site"
    out.mkdir()
    result = us.publish_update(str(build), "2.0", "https://e.com/x", us.new_signing_key(),
                               output_dir=str(out))
    assert os.path.dirname(result.manifest_path) == str(out)
