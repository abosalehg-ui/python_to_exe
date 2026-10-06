"""p2e_runtime: resource_path, per-user folders, the JSON config, install()."""

import json
import os
import sys

import pytest

import p2e_runtime
from p2e_runtime import config as rconfig
from p2e_runtime import paths

# ── resource_path ──────────────────────────────────────────────────────────


def test_unfrozen_resolves_against_the_main_script(monkeypatch, tmp_path):
    script = tmp_path / "proj" / "main.py"
    script.parent.mkdir()
    script.write_text("")
    main = type(sys)("__main__")
    main.__file__ = str(script)
    monkeypatch.setitem(sys.modules, "__main__", main)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert paths.resource_path("data/config.json") == os.path.join(
        str(script.parent), "data", "config.json"
    )
    assert not paths.is_frozen()


def test_frozen_onefile_and_onedir_use_meipass(monkeypatch, tmp_path):
    # One-file: the temp extraction folder; folder build: <app>/_internal.
    for bundle in (tmp_path / "_MEI12345", tmp_path / "MyApp" / "_internal"):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)
        assert paths.is_frozen()
        assert paths.resource_path("data/x.json") == os.path.join(str(bundle), "data", "x.json")


def test_frozen_without_meipass_uses_the_executable_folder(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "app" / "App.exe"))
    assert paths.bundle_dir() == str(tmp_path / "app")


def test_backslashes_and_absolute_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert paths.resource_path("data\\x.json") == os.path.join(str(tmp_path), "data", "x.json")
    absolute = str(tmp_path / "elsewhere.txt")
    assert paths.resource_path(absolute) == absolute
    assert paths.resource_path() == str(tmp_path)


def test_no_main_file_falls_back_to_argv_then_cwd(monkeypatch, tmp_path):
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setitem(sys.modules, "__main__", type(sys)("__main__"))
    script = tmp_path / "run.py"
    script.write_text("")
    monkeypatch.setattr(sys, "argv", [str(script)])
    assert paths.bundle_dir() == str(tmp_path)
    monkeypatch.setattr(sys, "argv", [""])
    monkeypatch.chdir(tmp_path)
    assert paths.bundle_dir() == os.getcwd()


@pytest.mark.parametrize("platform,env,expected", [
    ("win32", {"LOCALAPPDATA": "C:\\Users\\u\\AppData\\Local"},
     os.path.join("C:\\Users\\u\\AppData\\Local", "My App")),
    ("linux", {"XDG_STATE_HOME": "/x/state"}, os.path.join("/x/state", "My App")),
])
def test_user_state_dir(platform, env, expected):
    assert paths.user_state_dir("My App", platform=platform, env=env) == expected


def test_user_state_dir_defaults():
    home = os.path.expanduser("~")
    assert paths.user_state_dir("A", "linux", {}) == os.path.join(home, ".local", "state", "A")
    assert paths.user_state_dir("A", "darwin", {}) == os.path.join(home, "Library", "Logs", "A")
    assert paths.user_state_dir("A", "win32", {}) == os.path.join(home, "AppData", "Local", "A")


def test_safe_name_strips_path_tricks():
    assert paths.safe_name("../../etc/passwd") == "etc_passwd"
    assert paths.safe_name("My:App*?") == "My_App"
    assert paths.safe_name("") == "app"


# ── Config ─────────────────────────────────────────────────────────────────


FULL = {
    "format": 1,
    "app": {"name": "Tool", "version": "1.2.0", "build": "onedir", "rtl": True},
    "services": {
        "resource_path": {},
        "logs": {"max_bytes": 4096, "backups": 2},
        "crash_reporter": {"dialog": False, "support_url": "https://help.example"},
        "single_instance": {"message": "busy", "exit_code": 3},
        "updater": {
            "manifest_url": "https://example.com/u.json",
            "public_key": "AB" * 32,
            "installer_args": ["/SILENT"],
            "timeout": 5,
            "allow_insecure_localhost": True,
        },
    },
}


def test_parse_full_config():
    cfg = rconfig.parse_config(FULL)
    assert (cfg.app_name, cfg.app_version, cfg.build, cfg.rtl) == ("Tool", "1.2.0", "onedir", True)
    assert cfg.enabled() == ["resource_path", "logs", "crash", "single_instance", "updater"]
    assert cfg.logs.max_bytes == 4096 and cfg.logs.backups == 2
    assert cfg.crash.dialog is False
    assert cfg.single_instance.id == "Tool" and cfg.single_instance.exit_code == 3
    assert cfg.updater.public_key == "ab" * 32
    assert cfg.updater.installer_args == ["/SILENT"]
    assert cfg.updater.allow_insecure_localhost is True
    assert cfg.updater.check_on_start is False


def test_nothing_is_enabled_by_default():
    cfg = rconfig.parse_config({"app": {"name": "x"}})
    assert cfg.enabled() == []


def test_insecure_flag_needs_a_literal_true():
    data = json.loads(json.dumps(FULL))
    data["services"]["updater"]["allow_insecure_localhost"] = "yes"
    assert rconfig.parse_config(data).updater.allow_insecure_localhost is False


@pytest.mark.parametrize("mutate", [
    lambda d: d.update(format=2),
    lambda d: d["app"].update(build="sideways"),
    lambda d: d["services"].update(logs="on"),
    lambda d: d["services"]["logs"].update(max_bytes=10),
    lambda d: d["services"]["logs"].update(backups=True),
    lambda d: d["services"]["updater"].update(installer_args="/S"),
    lambda d: d["services"]["updater"].update(timeout=0),
    lambda d: d["services"]["updater"].update(manifest_url=7),
    lambda d: d.update(services=[]),
])
def test_malformed_config_is_refused(mutate):
    data = json.loads(json.dumps(FULL))
    mutate(data)
    with pytest.raises(ValueError):
        rconfig.parse_config(data)


def test_parse_rejects_non_object():
    with pytest.raises(ValueError):
        rconfig.parse_config([])


def test_true_enables_a_service_with_defaults():
    cfg = rconfig.parse_config({"services": {"logs": True, "crash_reporter": False}})
    assert cfg.logs == rconfig.LogsConfig()
    assert cfg.crash is None


def test_load_config(tmp_path, monkeypatch):
    path = tmp_path / rconfig.CONFIG_FILE_NAME
    assert rconfig.load_config(str(path)) is None
    path.write_text(json.dumps(FULL), encoding="utf-8")
    assert rconfig.load_config(str(path)).app_name == "Tool"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError):
        rconfig.load_config(str(path))
    # Without a path: the file bundled next to the app's data.
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    path.write_text(json.dumps(FULL), encoding="utf-8")
    assert rconfig.load_config().app_version == "1.2.0"


# ── install() ──────────────────────────────────────────────────────────────


@pytest.fixture
def fresh_runtime(monkeypatch):
    monkeypatch.setattr(p2e_runtime, "_installed", False)
    monkeypatch.setattr(p2e_runtime, "_config", None)
    yield


def test_install_without_config_does_nothing(fresh_runtime, tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    hook = sys.excepthook
    assert p2e_runtime.install() is None
    assert sys.excepthook is hook
    assert p2e_runtime.current_config() is None


def test_install_starts_only_enabled_services(fresh_runtime, monkeypatch):
    started = []
    for step in ("_start_logs", "_start_crash_reporter", "_start_single_instance",
                 "_start_updater"):
        original = getattr(p2e_runtime, step)

        def spy(config, _name=step, _original=original):
            started.append(_name)
            _original(config)

        monkeypatch.setattr(p2e_runtime, step, spy)
    imported = []
    monkeypatch.setattr(p2e_runtime, "_service", lambda name: imported.append(name))
    cfg = rconfig.parse_config({"app": {"name": "x"}, "services": {"resource_path": {}}})
    assert p2e_runtime.install(cfg) is cfg
    assert imported == []  # resource_path needs no service module
    assert len(started) == 4
    # Installing twice is a no-op.
    assert p2e_runtime.install(rconfig.parse_config(FULL)) is cfg
    assert p2e_runtime.current_config() is cfg


def test_a_failing_service_is_reported_not_fatal(fresh_runtime, monkeypatch, capsys):
    def boom(_name):
        raise RuntimeError("broken service")

    monkeypatch.setattr(p2e_runtime, "_service", boom)
    cfg = rconfig.parse_config({"services": {"logs": {}, "crash_reporter": {}}})
    assert p2e_runtime.install(cfg) is cfg
    err = capsys.readouterr().err
    assert "logs not started" in err and "crash_reporter not started" in err


def test_single_instance_exit_is_not_swallowed(fresh_runtime, monkeypatch):
    class Fake:
        @staticmethod
        def ensure_single_instance(*_a, **_k):
            raise SystemExit(3)

    monkeypatch.setattr(p2e_runtime, "_service", lambda name: Fake)
    cfg = rconfig.parse_config({"services": {"single_instance": {}}})
    with pytest.raises(SystemExit):
        p2e_runtime.install(cfg)


def test_install_with_invalid_file_warns(fresh_runtime, tmp_path, capsys):
    path = tmp_path / "bad.json"
    path.write_text("[]")
    assert p2e_runtime.install(str(path)) is None
    assert "invalid configuration" in capsys.readouterr().err


def test_package_imports_no_service_eagerly():
    """PyInstaller bundles only what is imported; services are opt-in."""
    import subprocess

    code = (
        "import sys, p2e_runtime; "
        "print(sorted(m for m in sys.modules if m.startswith('p2e_runtime')))"
    )
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True,
                         text=True, check=True).stdout
    assert out.strip() == "['p2e_runtime', 'p2e_runtime.config', 'p2e_runtime.paths']"
