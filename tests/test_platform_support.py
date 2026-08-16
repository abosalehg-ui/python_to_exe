"""Tests for which post-build features work on which operating system."""

import pytest

from py2exe_gui.core.platform_support import (
    CODE_SIGNING,
    INSTALLER,
    MANIFEST,
    SMOKE_TEST,
    SPLASH,
    VERSION_INFO,
    WINDOWS_ONLY,
    is_supported,
    is_windows,
    platform_label,
    unsupported_features,
)


@pytest.mark.parametrize("platform", ["win32", "cygwin", "msys"])
def test_is_windows_true(platform):
    """All three are Python reporting a host that can reach the Windows SDK."""
    assert is_windows(platform) is True


@pytest.mark.parametrize("platform", ["linux", "darwin", "freebsd13"])
def test_is_windows_false(platform):
    assert is_windows(platform) is False


@pytest.mark.parametrize("feature", WINDOWS_ONLY)
def test_windows_only_features_are_supported_on_windows(feature):
    assert is_supported(feature, "win32") is True


@pytest.mark.parametrize("feature", WINDOWS_ONLY)
@pytest.mark.parametrize("platform", ["linux", "darwin"])
def test_windows_only_features_are_unsupported_elsewhere(feature, platform):
    assert is_supported(feature, platform) is False


@pytest.mark.parametrize("platform", ["win32", "linux", "darwin"])
@pytest.mark.parametrize("feature", [SPLASH, SMOKE_TEST])
def test_cross_platform_features_are_supported_everywhere(feature, platform):
    """--splash and running the produced binary work on every platform."""
    assert is_supported(feature, platform) is True


def test_unknown_feature_is_treated_as_supported():
    """Unknown keys must not silently disable a working feature."""
    assert is_supported("something_new", "linux") is True


def test_unsupported_features_lists_all_four_off_windows():
    assert set(unsupported_features("linux")) == {
        CODE_SIGNING,
        MANIFEST,
        VERSION_INFO,
        INSTALLER,
    }


def test_unsupported_features_is_empty_on_windows():
    assert unsupported_features("win32") == []


def test_unsupported_features_order_is_stable():
    assert unsupported_features("linux") == unsupported_features("darwin")


@pytest.mark.parametrize(
    "platform,label",
    [
        ("win32", "Windows"),
        ("darwin", "macOS"),
        ("linux", "Linux"),
        ("sunos5", "sunos5"),
    ],
)
def test_platform_label(platform, label):
    assert platform_label(platform) == label


def test_defaults_read_the_running_platform():
    """Called with no argument, these must not raise on any host."""
    assert isinstance(is_windows(), bool)
    assert isinstance(unsupported_features(), list)
    assert platform_label()
