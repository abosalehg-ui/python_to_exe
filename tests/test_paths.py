"""Tests for per-user config path resolution and legacy migration."""

import json
import os

from py2exe_gui.paths import (
    APP_DIR_NAME,
    config_dir,
    resolve_with_migration,
)


def test_windows_uses_appdata():
    path = config_dir(platform="win32", env={"APPDATA": "C:\\Users\\a\\AppData\\Roaming"})
    assert path.endswith(APP_DIR_NAME)
    assert "Roaming" in path


def test_windows_falls_back_without_appdata():
    path = config_dir(platform="win32", env={})
    assert APP_DIR_NAME in path


def test_macos_uses_application_support():
    path = config_dir(platform="darwin", env={})
    assert "Application Support" in path
    assert path.endswith(APP_DIR_NAME)


def test_linux_honours_xdg_config_home(tmp_path):
    path = config_dir(platform="linux", env={"XDG_CONFIG_HOME": str(tmp_path)})
    assert path == os.path.join(str(tmp_path), APP_DIR_NAME)


def test_linux_defaults_to_dot_config():
    path = config_dir(platform="linux", env={})
    assert os.path.join(".config", APP_DIR_NAME) in path


def test_config_dir_is_absolute():
    assert os.path.isabs(config_dir(platform="linux", env={}))


# ── Migration ──────────────────────────────────────────────────────────────


def test_migration_is_a_noop_when_target_exists(tmp_path, monkeypatch):
    target = tmp_path / "settings.json"
    target.write_text('{"theme": "light"}', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert resolve_with_migration(str(target), "legacy.json") == str(target)
    assert json.loads(target.read_text())["theme"] == "light"


def test_migration_copies_legacy_file(tmp_path, monkeypatch):
    workdir = tmp_path / "work"
    workdir.mkdir()
    (workdir / "py2exe_settings.json").write_text('{"theme": "dark"}', encoding="utf-8")
    monkeypatch.chdir(workdir)

    target = tmp_path / "config" / "settings.json"
    result = resolve_with_migration(str(target), "py2exe_settings.json")

    assert result == str(target)
    assert json.loads(target.read_text())["theme"] == "dark"


def test_migration_leaves_the_legacy_file_in_place(tmp_path, monkeypatch):
    """Copy, not move — downgrading to an older version must still work."""
    workdir = tmp_path / "work"
    workdir.mkdir()
    legacy = workdir / "py2exe_history.json"
    legacy.write_text("[]", encoding="utf-8")
    monkeypatch.chdir(workdir)

    resolve_with_migration(str(tmp_path / "cfg" / "history.json"), "py2exe_history.json")
    assert legacy.exists()


def test_migration_noop_without_legacy_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "cfg" / "settings.json"
    assert resolve_with_migration(str(target), "absent.json") == str(target)
    assert not target.exists()
