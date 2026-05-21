"""Generate a Windows assembly manifest XML for PyInstaller --manifest."""

from dataclasses import dataclass, field
from typing import List
from xml.sax.saxutils import escape

# GUIDs for supportedOS entries (Windows assembly manifests).
SUPPORTED_OS_GUIDS = {
    "vista": "{e2011457-1546-43c5-a5fe-008deee3d3f0}",
    "7": "{35138b9a-5d96-4fbd-8e2d-a2440225f93a}",
    "8": "{4a2f28e3-53b9-4441-ba9c-d69d4a4a6e38}",
    "8.1": "{1f676c76-80e1-4239-95bb-83d0f6d0da78}",
    "10": "{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}",
    "11": "{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}",  # shares 10's GUID
}


@dataclass
class ManifestConfig:
    """User-configurable Windows manifest options."""

    name: str = "MyApp"
    version: str = "1.0.0.0"
    description: str = ""

    # DPI awareness: True → perMonitorV2 (modern), False → omit.
    dpi_aware: bool = False

    # UAC level: asInvoker (default user) vs requireAdministrator.
    require_admin: bool = False

    # Compatibility list — each entry is a key in SUPPORTED_OS_GUIDS.
    supported_os: List[str] = field(
        default_factory=lambda: ["7", "8", "8.1", "10"]
    )


def _supported_os_block(versions: List[str]) -> str:
    if not versions:
        return ""
    lines = ["    <compatibility xmlns=\"urn:schemas-microsoft-com:compatibility.v1\">",
            "      <application>"]
    for v in versions:
        guid = SUPPORTED_OS_GUIDS.get(v)
        if guid:
            lines.append(f"        <supportedOS Id=\"{guid}\"/>")
    lines.append("      </application>")
    lines.append("    </compatibility>")
    return "\n".join(lines)


def _dpi_block(enabled: bool) -> str:
    if not enabled:
        return ""
    return (
        "  <application xmlns=\"urn:schemas-microsoft-com:asm.v3\">\n"
        "    <windowsSettings>\n"
        "      <dpiAware xmlns=\"http://schemas.microsoft.com/SMI/2005/WindowsSettings\">true/PM</dpiAware>\n"
        "      <dpiAwareness xmlns=\"http://schemas.microsoft.com/SMI/2016/WindowsSettings\">PerMonitorV2</dpiAwareness>\n"
        "    </windowsSettings>\n"
        "  </application>"
    )


def _uac_level(require_admin: bool) -> str:
    return "requireAdministrator" if require_admin else "asInvoker"


def generate_manifest(config: ManifestConfig) -> str:
    """Return the XML body of a Windows assembly manifest."""
    name = escape(config.name or "MyApp")
    version = escape(config.version or "1.0.0.0")
    description = escape(config.description or "")
    uac = _uac_level(config.require_admin)
    dpi = _dpi_block(config.dpi_aware)
    os_block = _supported_os_block(config.supported_os)

    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">',
        f'  <assemblyIdentity type="win32" name="{name}" version="{version}" processorArchitecture="*"/>',
    ]
    if description:
        parts.append(f"  <description>{description}</description>")
    parts.append(
        "  <trustInfo xmlns=\"urn:schemas-microsoft-com:asm.v3\">\n"
        "    <security>\n"
        "      <requestedPrivileges>\n"
        f"        <requestedExecutionLevel level=\"{uac}\" uiAccess=\"false\"/>\n"
        "      </requestedPrivileges>\n"
        "    </security>\n"
        "  </trustInfo>"
    )
    if dpi:
        parts.append(dpi)
    if os_block:
        parts.append(os_block)
    parts.append("</assembly>")
    return "\n".join(parts) + "\n"
