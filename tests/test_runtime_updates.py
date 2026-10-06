"""The signed self-updater: policy, verification, swap, and a full local flow.

The integration tests run a real ``http.server`` on 127.0.0.1 and use the
test-only ``allow_insecure_localhost`` flag; everything else (signature,
manifest, size and hash checks, redirects, the swap) is the production path.
The Windows-only parts (renaming a *running* EXE, process creation flags)
are exercised through the injectable ``System``; they are not run on Windows
here.
"""

import hashlib
import os
import sys
import threading

import pytest

from p2e_runtime import config as rconfig
from p2e_runtime import updates
from p2e_runtime.updates import UpdateError, UpdateInfo
from py2exe_gui.core.update_signing import (
    manifest_bytes,
    new_signing_key,
    publish_update,
    sign,
)
from tests.update_server import UpdateServer

KEY = new_signing_key()
OTHER_KEY = new_signing_key()
NEW_BINARY = b"\x7fELF-pretend-new-version" * 200


@pytest.fixture(autouse=True)
def no_proxy(monkeypatch):
    # The local server must be reached directly, whatever the environment says.
    for name in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy",
                 "ALL_PROXY"):
        monkeypatch.delenv(name, raising=False)


def runtime_config(manifest_url, key=KEY, build="onefile", allow=True, version="1.0.0",
                   **updater):
    data = {
        "app": {"name": "Tool", "version": version, "build": build},
        "services": {"updater": {
            "manifest_url": manifest_url,
            "public_key": key.public_hex,
            "allow_insecure_localhost": allow,
            "timeout": 5,
            **updater,
        }},
    }
    return rconfig.parse_config(data)


def signed(manifest, key=KEY):
    data = manifest_bytes(manifest)
    return data, sign(key.seed, data).hex().encode() + b"\n"


def offer(server, version="2.0.0", body=NEW_BINARY, key=KEY, **fields):
    """Publish a signed update for ``body`` on ``server``; returns the manifest URL."""
    manifest = {
        "app": "Tool",
        "version": version,
        "url": server.serve("/dl/Tool-new", body),
        "sha256": hashlib.sha256(NEW_BINARY).hexdigest(),
        "size": len(NEW_BINARY),
        "notes": "Faster.",
        "min_version": "",
    }
    manifest.update(fields)
    data, signature = signed(manifest, key)
    server.serve("/update.json.sig", signature)
    return server.serve("/update.json", data)


class FakeSystem(updates.System):
    """Real file operations; process start and exit are recorded instead."""

    def __init__(self, executable, platform=None, frozen=True):
        super().__init__(platform=platform, frozen=frozen, executable=executable)
        self.spawned, self.exited = [], []

    def spawn(self, command, env=None):
        self.spawned.append((command, env))

    def exit(self, code=0):
        self.exited.append(code)


# ── URL policy ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("url", [
    "https://example.com/u.json", "HTTPS://Example.com/u.json", "https://localhost:8443/u",
])
def test_https_is_accepted(url):
    assert updates.check_url(url) == url


@pytest.mark.parametrize("url", [
    "http://example.com/u.json", "http://localhost/u.json", "ftp://example.com/u",
    "file:///etc/passwd", "https:///nohost", "", "javascript:alert(1)",
])
def test_everything_else_is_refused(url):
    with pytest.raises(UpdateError) as e:
        updates.check_url(url)
    assert e.value.code == "insecure_url"


def test_localhost_http_only_behind_the_test_flag():
    for url in ("http://localhost:8000/u", "http://127.0.0.1/u", "http://[::1]:9/u"):
        assert updates.check_url(url, allow_insecure_localhost=True) == url
    for url in ("http://example.com/u", "http://127.0.0.1.evil.example/u",
                "http://localhost.evil.example/u"):
        with pytest.raises(UpdateError):
            updates.check_url(url, allow_insecure_localhost=True)


def test_signature_url_keeps_the_query():
    assert updates.signature_url_for("https://h/a/update.json?v=2") == \
        "https://h/a/update.json.sig?v=2"


# ── Versions ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize("older,newer", [
    ("1.0.0", "1.0.1"), ("1.9", "1.10"), ("1.2", "2"), ("v1.0", "1.0.1"),
    ("1.0.0rc1", "1.0.0"), ("1.0.0b2", "1.0.0rc1"), ("1.0.0a1", "1.0.0b1"),
    ("1.0.0.dev1", "1.0.0a1"), ("1.0.0-beta.2", "1.0.0-beta.10"), ("0.9.9", "1.0.0rc1"),
])
def test_version_order(older, newer):
    assert updates.compare_versions(older, newer) == -1
    assert updates.compare_versions(newer, older) == 1
    assert updates.is_newer(newer, older) and not updates.is_newer(older, newer)


@pytest.mark.parametrize("a,b", [("1.2", "1.2.0"), ("v2.0", "2.0.0.0"), ("1.0RC1", "1.0rc1")])
def test_equal_versions(a, b):
    assert updates.compare_versions(a, b) == 0
    assert not updates.is_newer(a, b)


@pytest.mark.parametrize("text", ["", "abc", "1..2", "1.0-final", "1.0 beta", None])
def test_invalid_versions_raise(text):
    with pytest.raises(ValueError):
        updates.parse_version(text)


# ── Manifest checks ────────────────────────────────────────────────────────


def good_manifest(**overrides):
    manifest = {"version": "2.0.0", "url": "https://example.com/Tool.exe",
                "sha256": "ab" * 32, "size": 10, "notes": "", "min_version": "1.0.0"}
    manifest.update(overrides)
    return manifest


def test_valid_signature_passes():
    data, signature = signed(good_manifest())
    updates.verify_manifest(data, signature, KEY.public_hex)


@pytest.mark.parametrize("case", ["manifest", "signature", "key", "truncated", "garbage"])
def test_signature_failures(case):
    data, signature = signed(good_manifest())
    key = KEY.public_hex
    if case == "manifest":
        data = data.replace(b"2.0.0", b"9.0.0")
    elif case == "signature":
        signature = (b"0" if signature[:1] != b"0" else b"1") + signature[1:]
    elif case == "key":
        key = OTHER_KEY.public_hex
    elif case == "truncated":
        signature = signature[:100]
    else:
        signature = b"<html>404</html>"
    with pytest.raises(UpdateError) as e:
        updates.verify_manifest(data, signature, key)
    assert e.value.code == "bad_signature"


def test_whitespace_change_breaks_the_signature():
    """The signature covers the exact bytes, not the parsed JSON."""
    data, signature = signed(good_manifest())
    with pytest.raises(UpdateError):
        updates.verify_manifest(data.replace(b"\n", b"\r\n"), signature, KEY.public_hex)


@pytest.mark.parametrize("key", ["", "abc", "zz" * 32])
def test_unusable_public_key(key):
    data, signature = signed(good_manifest())
    with pytest.raises(UpdateError) as e:
        updates.verify_manifest(data, signature, key)
    assert e.value.code == "not_configured"


@pytest.mark.parametrize("overrides,code", [
    ({"version": ""}, "bad_manifest"),
    ({"version": "two"}, "bad_manifest"),
    ({"min_version": "x.y"}, "bad_manifest"),
    ({"url": "http://example.com/Tool.exe"}, "insecure_url"),
    ({"sha256": "12"}, "bad_manifest"),
    ({"size": 0}, "bad_manifest"),
    ({"size": True}, "bad_manifest"),
    ({"size": "10"}, "bad_manifest"),
    ({"notes": 5}, "bad_manifest"),
    ({"app": "SomeOtherApp"}, "wrong_app"),
])
def test_manifest_fields_are_validated(overrides, code):
    data, _sig = signed(good_manifest(**overrides))
    with pytest.raises(UpdateError) as e:
        updates.parse_manifest(data, app_name="Tool")
    assert e.value.code == code


@pytest.mark.parametrize("data", [b"not json", b"[1, 2]", b"\xff\xfe"])
def test_manifest_must_be_a_json_object(data):
    with pytest.raises(UpdateError) as e:
        updates.parse_manifest(data)
    assert e.value.code == "bad_manifest"


def test_update_info_applicability():
    assert UpdateInfo("2.0", "u", "a" * 64, 1).applicable
    assert UpdateInfo("2.0", "u", "a" * 64, 1, min_version="1.5", current_version="1.5").applicable
    assert not UpdateInfo("2.0", "u", "a" * 64, 1, min_version="1.5",
                          current_version="1.4.9").applicable


def test_check_requires_configuration(monkeypatch):
    import p2e_runtime

    monkeypatch.setattr(p2e_runtime, "_config", None)
    monkeypatch.setattr(p2e_runtime, "current_config", lambda: None)
    with pytest.raises(UpdateError) as e:
        updates.check()
    assert e.value.code == "not_configured"
    with pytest.raises(UpdateError):
        updates.check(rconfig.parse_config({"services": {}}))
    with pytest.raises(UpdateError):  # unusable app version
        updates.check(runtime_config("https://example.com/u.json", version="dev"))


# ── Full flow against a local server ───────────────────────────────────────


def test_check_and_apply_onefile(tmp_path):
    target = tmp_path / "Tool"
    target.write_bytes(b"old version")
    os.chmod(target, 0o755)
    with UpdateServer() as server:
        cfg = runtime_config(offer(server))
        info = updates.check(cfg)
        assert info == UpdateInfo(
            version="2.0.0", url=server.url("/dl/Tool-new"),
            sha256=hashlib.sha256(NEW_BINARY).hexdigest(), size=len(NEW_BINARY),
            notes="Faster.", min_version="", current_version="1.0.0",
        )
        system = FakeSystem(str(target))
        updates.apply(info, cfg, relaunch_args=["--after-update"], system=system)

    assert target.read_bytes() == NEW_BINARY
    assert (tmp_path / "Tool.old").read_bytes() == b"old version"
    assert not (tmp_path / "Tool.new").exists()
    if sys.platform != "win32":
        assert os.stat(target).st_mode & 0o111
    (command, env), = system.spawned
    assert command == [str(target), "--after-update"]
    assert env["PYINSTALLER_RESET_ENVIRONMENT"] == "1"
    assert system.exited == [0]
    assert server.requests == ["/update.json", "/update.json.sig", "/dl/Tool-new"]


def test_publish_helper_output_is_accepted_by_the_runtime(tmp_path):
    """Converter side and runtime side agree byte for byte."""
    build = tmp_path / "Tool.exe"
    build.write_bytes(NEW_BINARY)
    result = publish_update(str(build), "2.0.0", "https://example.com/Tool.exe", KEY,
                            notes="ملاحظات", app_name="Tool")
    data = open(result.manifest_path, "rb").read()
    signature = open(result.signature_path, "rb").read()
    updates.verify_manifest(data, signature, KEY.public_hex)
    fields = updates.parse_manifest(data, app_name="Tool")
    assert fields["sha256"] == hashlib.sha256(NEW_BINARY).hexdigest()
    assert fields["size"] == len(NEW_BINARY) and fields["notes"] == "ملاحظات"


def test_no_update_when_not_newer():
    with UpdateServer() as server:
        cfg = runtime_config(offer(server, version="1.0.0"))
        assert updates.check(cfg) is None
        cfg = runtime_config(offer(server, version="0.9"))
        assert updates.check(cfg) is None


@pytest.mark.parametrize("case", ["tampered", "wrong_key", "no_signature", "html_signature"])
def test_check_refuses_unverified_manifests(case):
    with UpdateServer() as server:
        url = offer(server)
        cfg = runtime_config(url)
        if case == "tampered":
            data = server.routes["/update.json"][2].replace(b"Faster.", b"Evil.")
            server.serve("/update.json", data)
        elif case == "wrong_key":
            cfg = runtime_config(url, key=OTHER_KEY)
        elif case == "no_signature":
            del server.routes["/update.json.sig"]
        else:
            server.serve("/update.json.sig", b"<html>hello</html>")
        with pytest.raises(UpdateError) as e:
            updates.check(cfg)
    expected = "network" if case == "no_signature" else "bad_signature"
    assert e.value.code == expected


@pytest.mark.parametrize("body,code", [
    (b"X" * len(NEW_BINARY), "hash_mismatch"),
    (NEW_BINARY + b"extra", "size_mismatch"),
    (NEW_BINARY[:-10], "size_mismatch"),
], ids=["different-bytes", "longer", "shorter"])
def test_apply_refuses_a_file_that_does_not_match(tmp_path, body, code):
    target = tmp_path / "Tool"
    target.write_bytes(b"old version")
    with UpdateServer() as server:
        cfg = runtime_config(offer(server))
        info = updates.check(cfg)
        server.serve("/dl/Tool-new", body)  # swapped after the manifest was signed
        system = FakeSystem(str(target))
        with pytest.raises(UpdateError) as e:
            updates.apply(info, cfg, system=system)
    assert e.value.code == code
    assert target.read_bytes() == b"old version"  # untouched
    assert sorted(os.listdir(tmp_path)) == ["Tool"]  # no .new or .old left behind
    assert system.spawned == [] and system.exited == []


def test_plain_http_is_refused_without_contacting_the_server():
    with UpdateServer() as server:
        url = offer(server)
        with pytest.raises(UpdateError) as e:
            updates.check(runtime_config(url, allow=False))
    assert e.value.code == "insecure_url"
    assert server.requests == []


def test_redirect_to_plain_http_is_refused():
    with UpdateServer() as server:
        offer(server)
        url = server.redirect("/latest/update.json", "http://downgrade.example/update.json")
        with pytest.raises(UpdateError) as e:
            updates.check(runtime_config(url))
    assert e.value.code == "insecure_url"
    assert server.requests == ["/latest/update.json"]


def test_redirect_handler_refuses_https_to_http():
    """The production case: an HTTPS response redirecting to plain HTTP."""
    import urllib.request

    handler = updates._SafeRedirects(allow_insecure_localhost=False)
    request = urllib.request.Request("https://example.com/update.json")
    with pytest.raises(UpdateError) as e:
        handler.redirect_request(request, None, 302, "Found", {},
                                 "http://example.com/update.json")
    assert e.value.code == "insecure_url"
    allowed = handler.redirect_request(request, None, 302, "Found", {},
                                       "https://cdn.example.com/update.json")
    assert allowed.full_url == "https://cdn.example.com/update.json"


def test_secure_redirect_is_followed():
    with UpdateServer() as server:
        offer(server)
        url = server.redirect("/latest/update.json", server.url("/update.json"))
        cfg = runtime_config(url, signature_url=server.url("/update.json.sig"))
        assert updates.check(cfg).version == "2.0.0"


def test_oversized_manifest_is_refused():
    with UpdateServer() as server:
        url = server.serve("/update.json", b" " * (updates.MANIFEST_MAX_BYTES + 1))
        server.serve("/update.json.sig", b"0" * 128)
        with pytest.raises(UpdateError) as e:
            updates.check(runtime_config(url))
    assert e.value.code == "too_large"


def test_unreachable_server_is_a_network_error():
    with UpdateServer() as server:
        url = server.url("/update.json")
    with pytest.raises(UpdateError) as e:  # server is shut down now
        updates.check(runtime_config(url))
    assert e.value.code == "network"


def test_min_version_blocks_apply(tmp_path):
    with UpdateServer() as server:
        cfg = runtime_config(offer(server, min_version="1.5.0"))
        info = updates.check(cfg)
    assert info is not None and not info.applicable
    with pytest.raises(UpdateError) as e:
        updates.apply(info, cfg, system=FakeSystem(str(tmp_path / "Tool")))
    assert e.value.code == "min_version"


def test_unfrozen_app_cannot_swap_itself(tmp_path):
    with UpdateServer() as server:
        cfg = runtime_config(offer(server))
        info = updates.check(cfg)
        with pytest.raises(UpdateError) as e:
            updates.apply(info, cfg, system=FakeSystem(str(tmp_path / "x"), frozen=False))
    assert e.value.code == "not_frozen"


def test_unwritable_folder_is_reported(tmp_path):
    with UpdateServer() as server:
        cfg = runtime_config(offer(server))
        info = updates.check(cfg)
        missing = tmp_path / "no-such-folder" / "Tool"
        with pytest.raises(UpdateError) as e:
            updates.apply(info, cfg, system=FakeSystem(str(missing)))
    assert e.value.code == "write_failed"


def test_onedir_downloads_verifies_and_launches_the_installer(tmp_path):
    with UpdateServer() as server:
        url = offer(server, url=server.serve("/dl/Tool-2.0.0-Setup.exe", NEW_BINARY))
        cfg = runtime_config(url, build="onedir", installer_args=["/SILENT", "/NORESTART"])
        info = updates.check(cfg)
        system = FakeSystem(str(tmp_path / "Tool" / "Tool.exe"))
        system.mkdtemp = lambda: str(tmp_path)
        path = updates.apply(info, cfg, system=system)
    assert path == str(tmp_path / "Tool-2.0.0-Setup.exe")
    assert open(path, "rb").read() == NEW_BINARY
    assert system.spawned == [([path, "/SILENT", "/NORESTART"], None)]
    assert system.exited == [0]


# ── Swap logic on this OS, and the Windows branches by injection ───────────


def test_swap_replaces_and_keeps_the_old_file(tmp_path):
    target, new = tmp_path / "App", tmp_path / "App.new"
    target.write_bytes(b"old")
    new.write_bytes(b"new")
    (tmp_path / "App.old").write_bytes(b"stale")  # from an earlier update
    os.chmod(target, 0o750)
    old = updates.swap_executable(str(target), str(new), updates.System())
    assert old == str(tmp_path / "App.old")
    assert target.read_bytes() == b"new" and (tmp_path / "App.old").read_bytes() == b"old"
    if sys.platform != "win32":
        assert os.stat(target).st_mode & 0o777 == 0o750


def test_swap_uses_a_unique_name_when_the_old_file_is_locked(tmp_path):
    target, new = tmp_path / "App.exe", tmp_path / "App.exe.new"
    target.write_bytes(b"old")
    new.write_bytes(b"new")
    (tmp_path / "App.exe.old").write_bytes(b"still running")

    class Locked(FakeSystem):
        def remove(self, path):
            raise PermissionError("in use")  # Windows: the old process still runs

    system = Locked(str(target), platform="win32")
    old = updates.swap_executable(str(target), str(new), system)
    assert old == f"{target}.{system.pid}.old"
    assert target.read_bytes() == b"new"


def test_swap_rolls_back_when_the_new_file_cannot_be_moved_in(tmp_path):
    target = tmp_path / "App.exe"
    target.write_bytes(b"old")

    class Broken(FakeSystem):
        def replace(self, src, dst):
            raise PermissionError("antivirus has it open")

    with pytest.raises(UpdateError) as e:
        updates.swap_executable(str(target), str(tmp_path / "App.exe.new"),
                                Broken(str(target), platform="win32"))
    assert e.value.code == "swap_failed"
    assert target.read_bytes() == b"old"  # back where it was
    assert not (tmp_path / "App.exe.old").exists()


def test_swap_reports_a_rename_failure(tmp_path):
    class NoRename(FakeSystem):
        def rename(self, src, dst):
            raise PermissionError("denied")

    with pytest.raises(UpdateError) as e:
        updates.swap_executable(str(tmp_path / "a"), str(tmp_path / "b"),
                                NoRename(str(tmp_path / "a")))
    assert e.value.code == "swap_failed"


def test_windows_apply_branch(tmp_path, monkeypatch):
    """platform=win32: no chmod; the relaunch is detached from the old console."""
    target = tmp_path / "Tool.exe"
    target.write_bytes(b"old version")
    launched = []
    monkeypatch.setattr(updates.subprocess, "Popen",
                        lambda command, **kwargs: launched.append((command, kwargs)))

    class Windows(updates.System):
        made_executable = False

        def make_executable(self, path, like=""):
            self.made_executable = True

        def exit(self, code=0):
            self.exit_code = code

    with UpdateServer() as server:
        cfg = runtime_config(offer(server))
        system = Windows(platform="win32", frozen=True, executable=str(target))
        updates.apply(updates.check(cfg), cfg, relaunch_args=[], system=system)
    assert target.read_bytes() == NEW_BINARY
    assert system.made_executable is False
    (command, kwargs), = launched
    assert command == [str(target)]
    assert kwargs["creationflags"] == 0x00000008 | 0x00000200
    assert kwargs["env"]["PYINSTALLER_RESET_ENVIRONMENT"] == "1"
    assert system.exit_code == 0


def test_posix_spawn_starts_a_new_session(monkeypatch):
    launched = []
    monkeypatch.setattr(updates.subprocess, "Popen",
                        lambda command, **kwargs: launched.append(kwargs))
    updates.System(platform="linux").spawn(["x"])
    assert launched[0]["start_new_session"] is True and "creationflags" not in launched[0]


def test_system_exit_raises_system_exit():
    with pytest.raises(SystemExit):
        updates.System().exit(0)


def test_installer_command():
    assert updates.installer_command("C:\\t\\Setup.msi", ["/qn"], "win32") == \
        ["msiexec", "/i", "C:\\t\\Setup.msi", "/qn"]
    assert updates.installer_command("C:\\t\\Setup.exe", ["/S"], "win32") == \
        ["C:\\t\\Setup.exe", "/S"]
    assert updates.installer_command("/t/setup.run", [], "linux") == ["/t/setup.run"]


def test_download_name_is_sanitised():
    assert updates._download_name("https://h/x/My%20Setup.exe") == "My_20Setup.exe"
    assert updates._download_name("https://h/") == "update-setup.exe"
    assert updates._download_name("https://h/../..") == "update-setup.exe"


def test_relaunch_environment_drops_pyinstaller_state():
    env = updates.relaunch_environment({
        "PATH": "/bin", "_PYI_APPLICATION_HOME_DIR": "/tmp/_MEI1", "_PYI_ARCHIVE_FILE": "x",
        "_MEIPASS2": "/tmp/_MEI1", "_PYI_PARENT_PROCESS_LEVEL": "1",
    })
    assert env == {"PATH": "/bin", "PYINSTALLER_RESET_ENVIRONMENT": "1"}


def test_cleanup_removes_only_this_programs_old_files(tmp_path):
    exe = tmp_path / "Tool.exe"
    for name in ("Tool.exe", "Tool.exe.old", "Tool.exe.4242.old", "Other.exe.old",
                 "Tool.exe.oldish"):
        (tmp_path / name).write_text("x")
    assert updates.cleanup_old(str(exe)) == 2
    assert sorted(os.listdir(tmp_path)) == ["Other.exe.old", "Tool.exe", "Tool.exe.oldish"]
    assert updates.cleanup_old(str(tmp_path / "missing" / "x")) == 0


def test_cleanup_retries_a_locked_file(tmp_path, monkeypatch):
    exe = tmp_path / "Tool.exe"
    (tmp_path / "Tool.exe.old").write_text("x")
    real_remove, attempts = os.remove, []

    def flaky(path):
        attempts.append(path)
        if len(attempts) < 3:
            raise PermissionError("still in use")
        real_remove(path)

    monkeypatch.setattr(updates.os, "remove", flaky)
    assert updates.cleanup_old(str(exe), attempts=5, delay=0) == 1
    assert len(attempts) == 3


# ── Start-up behaviour ─────────────────────────────────────────────────────


def test_on_start_does_nothing_unless_asked(monkeypatch):
    monkeypatch.setattr(updates, "check", lambda *a, **k: pytest.fail("network used"))
    assert updates.on_start(runtime_config("https://example.com/u.json")) is None


def test_on_start_asks_and_applies_only_on_yes(monkeypatch):
    cfg = runtime_config("https://example.com/u.json", check_on_start=True)
    info = UpdateInfo("2.0.0", "https://example.com/t", "a" * 64, 1, notes="n",
                      current_version="1.0.0")
    monkeypatch.setattr(updates, "check", lambda config: info)
    applied, asked = [], []
    monkeypatch.setattr(updates, "apply", lambda i, config: applied.append(i))

    def ask(text, title, kind, yes_no, rtl):
        asked.append((text, title, yes_no))
        return answer

    answer = False
    assert updates.on_start(cfg, ask=ask) is info and applied == []
    answer = True
    updates.on_start(cfg, ask=ask)
    assert applied == [info]
    text, title, yes_no = asked[0]
    assert "2.0.0" in text and "1.0.0" in text and "Tool" in title and yes_no


def test_on_start_never_installs_without_a_native_dialog(monkeypatch):
    cfg = runtime_config("https://example.com/u.json", check_on_start=True)
    info = UpdateInfo("2.0.0", "https://example.com/t", "a" * 64, 1, current_version="1.0.0")
    monkeypatch.setattr(updates, "check", lambda config: info)
    monkeypatch.setattr(updates, "apply", lambda *a: pytest.fail("installed without asking"))
    updates.on_start(cfg, ask=lambda *a: None)  # None = no dialog on this platform


def test_on_start_reports_failures_and_carries_on(monkeypatch, capsys):
    cfg = runtime_config("https://example.com/u.json", check_on_start=True)

    def refuse(config):
        raise UpdateError("bad_signature", "nope")

    monkeypatch.setattr(updates, "check", refuse)
    assert updates.on_start(cfg) is None
    assert "update check failed: bad_signature" in capsys.readouterr().err


def test_on_start_cleans_up_in_the_background_when_frozen(monkeypatch, tmp_path):
    (tmp_path / "Tool.old").write_text("x")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "Tool"))
    done = threading.Event()
    real = updates.cleanup_old

    def tracked(**kwargs):
        try:
            return real(**kwargs)
        finally:
            done.set()

    monkeypatch.setattr(updates, "cleanup_old", tracked)
    updates.on_start(runtime_config("https://example.com/u.json"))
    assert done.wait(5)
    assert not (tmp_path / "Tool.old").exists()


def test_relaunch_releases_the_single_instance_lock_first(tmp_path, monkeypatch):
    """Else the new copy could find the lock taken and quit as 'already running'."""
    from p2e_runtime import single_instance

    api = type("Api", (), {"closed": [],
                           "create_mutex": lambda self, name: (7, 0),
                           "close": lambda self, h: self.closed.append(h)})()
    monkeypatch.setattr(single_instance, "_lock", None)
    single_instance.ensure_single_instance("Tool", platform="win32", api=api)
    target = tmp_path / "Tool"
    target.write_bytes(b"old")
    order = []

    class Recording(FakeSystem):
        def spawn(self, command, env=None):
            order.append(("spawn", list(api.closed)))

    with UpdateServer() as server:
        cfg = runtime_config(offer(server))
        updates.apply(updates.check(cfg), cfg, system=Recording(str(target)))
    assert order == [("spawn", [7])]  # the lock was already released
    assert single_instance._lock is None
    single_instance.release()  # a second release is harmless


def test_on_start_skips_the_check_when_unattended(monkeypatch):
    from p2e_runtime import _native

    monkeypatch.setenv(_native.NO_DIALOGS_ENV, "1")
    monkeypatch.setattr(updates, "check", lambda *a, **k: pytest.fail("network used"))
    cfg = runtime_config("https://example.com/u.json", check_on_start=True)
    assert updates.on_start(cfg) is None
