"""Which post-build features actually work on the host operating system.

The Deploy and Installer tabs were built for Windows: ``signtool.exe`` ships
with the Windows SDK, an application manifest is a Windows PE resource, and
Inno Setup produces a Windows ``Setup.exe``. The tabs nonetheless rendered
identically on Linux and macOS, so the failure only surfaced after a build, as
a tool-not-found error in the log.

The builder itself is genuinely cross-platform (it already picks the
``--add-data`` separator from ``sys.platform``), so the answer is not to hide
the tabs but to say plainly, up front, what will not run here.
"""

import sys
from typing import List, Optional

# Feature keys, stable identifiers the UI resolves to translated labels.
CODE_SIGNING = "code_signing"
MANIFEST = "manifest"
VERSION_INFO = "version_info"
INSTALLER = "installer"
SPLASH = "splash"
SMOKE_TEST = "smoke_test"

# Features that only do anything when the build itself runs on Windows.
#
# version_info and manifest are Windows PE resources: PyInstaller accepts the
# flags on any host but they have no effect on an ELF or Mach-O binary.
# splash and smoke_test are excluded deliberately — both work everywhere.
WINDOWS_ONLY = (CODE_SIGNING, MANIFEST, VERSION_INFO, INSTALLER)


def _platform(platform: Optional[str] = None) -> str:
    return platform if platform is not None else sys.platform


def is_windows(platform: Optional[str] = None) -> bool:
    """True on Windows, including the POSIX-flavoured environments hosted on it.

    CPython reports ``win32`` natively, but under Cygwin and MSYS it reports
    those names instead — and both still reach the Windows SDK, so signtool and
    ISCC are genuinely available there.
    """
    plat = _platform(platform)
    return plat.startswith(("win", "cygwin", "msys"))


def is_supported(feature: str, platform: Optional[str] = None) -> bool:
    """True when ``feature`` has an effect on this platform."""
    if feature not in WINDOWS_ONLY:
        return True
    return is_windows(platform)


def unsupported_features(platform: Optional[str] = None) -> List[str]:
    """Every feature key that will not work on ``platform``, in stable order."""
    return [f for f in WINDOWS_ONLY if not is_supported(f, platform)]


def platform_label(platform: Optional[str] = None) -> str:
    """A human-readable OS name for use in a warning banner."""
    plat = _platform(platform)
    if plat.startswith("win"):
        return "Windows"
    if plat.startswith("darwin"):
        return "macOS"
    if plat.startswith("linux"):
        return "Linux"
    return plat
