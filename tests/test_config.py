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


def test_isolated_env_round_trips_and_defaults_off():
    assert BuildConfig().isolated_env is False
    assert BuildConfig.from_dict(BuildConfig(isolated_env=True).to_dict()).isolated_env is True
    # Older settings files have no such key.
    assert BuildConfig.from_dict({"source": "a.py"}).isolated_env is False


def test_a_shared_config_cannot_name_an_interpreter():
    """The environment is a flag; its path is derived locally, never loaded."""
    data = BuildConfig(isolated_env=True).to_dict()
    assert not any("python" in key for key in data)


# ── Type-strict loading (hand-edited settings files) ──────────────────────


def test_from_dict_coerces_a_digit_string_for_an_int():
    assert BuildConfig.from_dict({"optimize": "2"}).optimize == 2


def test_from_dict_never_turns_a_string_into_a_list():
    # ``list("data")`` gave ['d', 'a', 't', 'a'] and a build that bundled
    # four one-letter files.
    config = BuildConfig.from_dict({"extra_files": "data", "hidden_imports": "x"})
    assert config.extra_files == [] and config.hidden_imports == []


def test_from_dict_keeps_the_default_for_a_string_pretending_to_be_a_bool():
    warnings = []
    config = BuildConfig.from_dict({"onefile": "yes", "windowed": 1}, warnings)
    assert config.onefile is True and config.windowed is False
    assert any("onefile" in w for w in warnings) and any("windowed" in w for w in warnings)


def test_from_dict_reports_unknown_keys_and_survives_non_dict_input():
    warnings = []
    BuildConfig.from_dict({"nope": 1}, warnings)
    assert warnings == ["build.nope: unknown setting, ignored"]
    assert BuildConfig.from_dict(None) == BuildConfig()
    assert BuildConfig.from_dict(["source"]) == BuildConfig()


def test_from_dict_still_handles_engine_and_runtime_kit():
    config = BuildConfig.from_dict({
        "engine": "unknown", "runtime_kit": {"crash_reporter": True, "app_version": 3},
    })
    assert config.engine == "pyinstaller"
    assert config.runtime_kit.crash_reporter is True and config.runtime_kit.app_version == ""
