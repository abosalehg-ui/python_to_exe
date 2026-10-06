"""Release files (portable ZIP, SHA256SUMS, names) and the token lookup."""

import hashlib
import os
import zipfile

import pytest

from py2exe_gui.core.config import BuildConfig
from py2exe_gui.core.release import artifacts, credentials
from py2exe_gui.core.release.credentials import (
    CredentialError,
    Token,
    delete_token,
    find_token,
    redact,
    store_token,
)


def make_dist(tmp_path, onefile=True, name="MyApp"):
    src = tmp_path / "app.py"
    src.write_text("print(1)\n")
    dist = tmp_path / "dist"
    if onefile:
        dist.mkdir()
        (dist / f"{name}.exe").write_bytes(b"MZ" + b"x" * 1000)
    else:
        folder = dist / name
        (folder / "_internal" / "lib").mkdir(parents=True)
        (folder / f"{name}.exe").write_bytes(b"MZ-onedir")
        (folder / "_internal" / "base_library.zip").write_bytes(b"zip" * 50)
        (folder / "_internal" / "lib" / "x.pyd").write_bytes(b"pyd")
    return BuildConfig(source=str(src), output_name=name, onefile=onefile)


def test_names_and_folders(tmp_path):
    config = make_dist(tmp_path)
    assert artifacts.release_dir(config, "1.2.3") == str(tmp_path / "release" / "1.2.3")
    assert artifacts.exe_asset_name(config, "1.2.3", "/x/MyApp.exe") == "MyApp-1.2.3.exe"
    assert artifacts.exe_asset_name(config, "1.2.3", "/x/MyApp") == "MyApp-1.2.3"
    assert artifacts.zip_asset_name(config, "1.2.3") == "MyApp-1.2.3-portable.zip"
    assert artifacts.installer_basename(config, "1.2.3") == "MyApp-1.2.3-setup"
    assert artifacts.safe_name("My App (تجريبي)") == "My-App"
    assert artifacts.safe_name("   ") == "app"
    assert artifacts.download_url("o/r", "v1", "a.zip") == \
        "https://github.com/o/r/releases/download/v1/a.zip"


def test_built_output_onefile_and_onedir(tmp_path):
    (tmp_path / "a").mkdir()
    one = make_dist(tmp_path / "a")
    assert artifacts.built_output(one).endswith(os.path.join("dist", "MyApp.exe"))
    two_root = tmp_path / "b"
    two_root.mkdir()
    two = make_dist(two_root, onefile=False)
    assert artifacts.built_output(two) == str(two_root / "dist" / "MyApp")
    assert artifacts.built_output(BuildConfig(source=str(tmp_path / "none.py"))) == ""


def test_portable_zip_of_a_onedir_build_is_reproducible(tmp_path):
    config = make_dist(tmp_path, onefile=False)
    folder = artifacts.built_output(config)
    first = artifacts.make_portable_zip(folder, str(tmp_path / "out" / "a.zip"))
    digest = artifacts.sha256_of(first)
    os.utime(os.path.join(folder, "MyApp.exe"), (1, 1))  # timestamps must not matter
    again = artifacts.make_portable_zip(folder, first)
    assert artifacts.sha256_of(again) == digest
    with zipfile.ZipFile(first) as z:
        names = z.namelist()
        assert "MyApp/MyApp.exe" in names
        assert "MyApp/_internal/lib/x.pyd" in names
        assert z.read("MyApp/MyApp.exe") == b"MZ-onedir"
        assert all(i.date_time == (1980, 1, 1, 0, 0, 0) for i in z.infolist())


def test_portable_zip_of_a_onefile_exe(tmp_path):
    config = make_dist(tmp_path)
    target = artifacts.make_portable_zip(artifacts.built_output(config),
                                         str(tmp_path / "r" / "x.zip"))
    with zipfile.ZipFile(target) as z:
        assert z.namelist() == ["MyApp.exe"]
    with pytest.raises(FileNotFoundError):
        artifacts.make_portable_zip(str(tmp_path / "missing"), str(tmp_path / "y.zip"))


def test_checksums_match_sha256sum_format_and_verify(tmp_path):
    a = tmp_path / "b-file.exe"
    b = tmp_path / "a-file.zip"
    a.write_bytes(b"alpha")
    b.write_bytes(b"beta")
    target = artifacts.write_checksums([str(a), str(b)], str(tmp_path / "SHA256SUMS.txt"))
    text = open(target, encoding="ascii").read()
    assert text == (f"{hashlib.sha256(b'beta').hexdigest()}  a-file.zip\n"
                    f"{hashlib.sha256(b'alpha').hexdigest()}  b-file.exe\n")
    assert artifacts.verify_checksums(target) == []
    a.write_bytes(b"tampered")
    assert artifacts.verify_checksums(target) == ["b-file.exe"]
    assert artifacts.parse_checksums("nonsense\n" + "A" * 64 + " *bin.exe\n") == {
        "bin.exe": "a" * 64}


def test_notes_and_existing(tmp_path):
    path = artifacts.write_notes("## ملاحظات\n", str(tmp_path / "n" / "RELEASE_NOTES.md"))
    assert open(path, encoding="utf-8").read() == "## ملاحظات\n"
    assert artifacts.existing([path, None, "", str(tmp_path / "nope")]) == [path]


# ── Token lookup ──────────────────────────────────────────────────────────


class FakeKeyring:
    def __init__(self, value=None, broken=False):
        self.store = {}
        if value:
            self.store[(credentials.KEYRING_SERVICE, credentials.KEYRING_USERNAME)] = value
        self.broken = broken

    def get_password(self, service, user):
        if self.broken:
            raise RuntimeError("no backend")
        return self.store.get((service, user))

    def set_password(self, service, user, value):
        if self.broken:
            raise RuntimeError(f"cannot store {value}")
        self.store[(service, user)] = value

    def delete_password(self, service, user):
        if (service, user) not in self.store:
            raise KeyError("missing")
        del self.store[(service, user)]


def test_keyring_comes_first_then_the_environment():
    env = {"GITHUB_TOKEN": "env-token-value"}
    assert find_token(env, FakeKeyring("kr-token-value")) == Token("kr-token-value", "keyring")
    assert find_token(env, FakeKeyring()) == Token("env-token-value", "env")
    assert find_token(env, None) == Token("env-token-value", "env")
    assert find_token(env, FakeKeyring(broken=True)).source == "env"
    assert not find_token({}, None)
    assert find_token({}, None).source == ""


def test_token_repr_never_shows_the_value():
    token = Token("ghp_supersecretvalue", "env")
    assert "supersecret" not in repr(token) and "supersecret" not in str(token)


def test_store_and_delete(monkeypatch):
    ring = FakeKeyring()
    store_token("  new-token-123  ", ring)
    assert find_token({}, ring).value == "new-token-123"
    assert delete_token(ring) is True
    assert delete_token(ring) is False
    assert delete_token(None) is False
    with pytest.raises(CredentialError):
        store_token("", ring)
    with pytest.raises(CredentialError):
        store_token("x", None)
    with pytest.raises(CredentialError) as e:
        store_token("leaky-token-999", FakeKeyring(broken=True))
    assert "leaky-token-999" not in str(e.value)


def test_load_keyring_is_optional(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def no_keyring(name, *args, **kwargs):
        if name == "keyring":
            raise ImportError("no keyring")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_keyring)
    assert credentials.load_keyring() is None
    marker = object()
    assert credentials.load_keyring(marker) is marker


def test_redact():
    assert redact("Bearer abcdef in text abcdef", ["abcdef"]) == "Bearer *** in text ***"
    assert redact("short ab", ["ab", ""]) == "short ab"  # too short to redact safely
