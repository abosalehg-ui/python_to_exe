"""Tests for BuildConfig serialization."""

from py2exe_gui.core.config import BuildConfig


def test_default_values():
    config = BuildConfig()
    assert config.onefile is True
    assert config.windowed is False
    assert config.clean is True
    assert config.noconfirm is True
    assert config.hidden_imports == []
    assert config.extra_files == []


def test_roundtrip_via_dict():
    original = BuildConfig(
        source="/tmp/x.py",
        output_name="MyApp",
        hidden_imports=["numpy", "pandas"],
        upx=True,
        upx_level=5,
        extra_args="--debug",
    )
    restored = BuildConfig.from_dict(original.to_dict())
    assert restored == original


def test_from_dict_with_missing_keys_uses_defaults():
    config = BuildConfig.from_dict({"source": "/tmp/a.py"})
    assert config.source == "/tmp/a.py"
    assert config.onefile is True
    assert config.hidden_imports == []


def test_to_dict_returns_independent_lists():
    config = BuildConfig(hidden_imports=["x"])
    d = config.to_dict()
    d["hidden_imports"].append("y")
    assert config.hidden_imports == ["x"]


def test_version_file_roundtrip():
    cfg = BuildConfig(version_file="/tmp/v.txt")
    assert BuildConfig.from_dict(cfg.to_dict()).version_file == "/tmp/v.txt"


def test_version_file_default_is_empty():
    assert BuildConfig().version_file == ""


def test_splash_and_manifest_roundtrip():
    cfg = BuildConfig(splash_image="/tmp/s.png", manifest_file="/tmp/m.xml")
    restored = BuildConfig.from_dict(cfg.to_dict())
    assert restored.splash_image == "/tmp/s.png"
    assert restored.manifest_file == "/tmp/m.xml"


def test_phase5_fields_default_empty():
    cfg = BuildConfig()
    assert cfg.splash_image == ""
    assert cfg.manifest_file == ""
