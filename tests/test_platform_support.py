"""Tests for which post-build features work on which operating system."""

import pytest

from py2exe_gui.core.platform_support import (
    APPIMAGE,
    CODE_SIGNING,
    DEB,
    DMG,
    INSTALLER,
    LINUX_ONLY,
    MACOS_ONLY,
    MANIFEST,
    PACKAGE_FORMATS,
    PLATFORM_LABELS,
    SMOKE_TEST,
    SPLASH,
    VERSION_INFO,
    WINDOWS_ONLY,
    is_linux,
    is_macos,
    is_supported,
    is_windows,
    package_formats,
    platform_label,
    required_platform,
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
        DMG,
    }
    assert set(unsupported_features("darwin")) == {
        CODE_SIGNING, MANIFEST, VERSION_INFO, INSTALLER, APPIMAGE, DEB,
    }


def test_windows_cannot_build_the_linux_and_macos_packages():
    """2.0: the package formats are the one thing Windows lacks."""
    assert unsupported_features("win32") == [APPIMAGE, DEB, DMG]


def test_unsupported_features_order_is_stable():
    """Windows-only first, then Linux-only, then macOS-only — the banner order."""
    assert unsupported_features("win32") == list(LINUX_ONLY + MACOS_ONLY)
    assert unsupported_features("linux")[:4] == list(WINDOWS_ONLY)


# ── 2.0: package formats ───────────────────────────────────────────────────


def test_package_formats_per_platform():
    assert package_formats("linux") == [APPIMAGE, DEB]
    assert package_formats("darwin") == [DMG]
    assert package_formats("win32") == []
    assert PACKAGE_FORMATS == LINUX_ONLY + MACOS_ONLY


@pytest.mark.parametrize("feature,host", [
    (CODE_SIGNING, "windows"), (INSTALLER, "windows"), (APPIMAGE, "linux"), (DEB, "linux"),
    (DMG, "macos"), (SPLASH, ""), ("something_new", ""),
])
def test_required_platform(feature, host):
    assert required_platform(feature) == host
    if host:
        assert PLATFORM_LABELS[host] in ("Windows", "Linux", "macOS")


def test_is_linux_and_is_macos():
    assert is_linux("linux") and is_linux("linux2") and not is_linux("darwin")
    assert is_macos("darwin") and not is_macos("linux") and not is_macos("win32")
    assert isinstance(is_linux(), bool) and isinstance(is_macos(), bool)


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


def test_resolve_returns_the_argument_or_the_running_platform():
    import sys

    from py2exe_gui.core.platform_support import resolve

    assert resolve("win32") == "win32"
    assert resolve(None) == sys.platform
    assert resolve() == sys.platform
