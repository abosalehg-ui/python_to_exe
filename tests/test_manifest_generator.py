"""Tests for the Windows assembly manifest generator."""

from xml.etree import ElementTree as ET

from py2exe_gui.core.manifest_generator import (
    SUPPORTED_OS_GUIDS,
    ManifestConfig,
    generate_manifest,
)


def _parse(xml: str) -> ET.Element:
    return ET.fromstring(xml)


def test_output_is_valid_xml():
    out = generate_manifest(ManifestConfig())
    root = _parse(out)
    assert root.tag.endswith("assembly")


def test_assembly_identity_has_name_and_version():
    out = generate_manifest(ManifestConfig(name="MyApp", version="2.0.0.0"))
    assert 'name="MyApp"' in out
    assert 'version="2.0.0.0"' in out


def test_description_omitted_when_blank():
    out = generate_manifest(ManifestConfig(description=""))
    assert "<description>" not in out


def test_description_included_when_set():
    out = generate_manifest(ManifestConfig(description="An app"))
    assert "<description>An app</description>" in out


def test_uac_level_default_is_asinvoker():
    out = generate_manifest(ManifestConfig(require_admin=False))
    assert 'level="asInvoker"' in out


def test_uac_level_admin_when_required():
    out = generate_manifest(ManifestConfig(require_admin=True))
    assert 'level="requireAdministrator"' in out


def test_dpi_block_absent_by_default():
    out = generate_manifest(ManifestConfig(dpi_aware=False))
    assert "dpiAware" not in out


def test_dpi_block_emits_per_monitor_v2():
    out = generate_manifest(ManifestConfig(dpi_aware=True))
    assert "PerMonitorV2" in out
    assert "true/PM" in out


def test_supported_os_emits_correct_guid():
    out = generate_manifest(ManifestConfig(supported_os=["10"]))
    assert SUPPORTED_OS_GUIDS["10"] in out


def test_unknown_os_versions_are_skipped():
    out = generate_manifest(ManifestConfig(supported_os=["10", "99"]))
    # The unknown "99" should not crash and is simply omitted.
    assert SUPPORTED_OS_GUIDS["10"] in out


def test_empty_supported_os_omits_compat_block():
    out = generate_manifest(ManifestConfig(supported_os=[]))
    assert "<compatibility" not in out


def test_special_chars_in_name_are_xml_escaped():
    out = generate_manifest(ManifestConfig(name='My&App<v2>'))
    assert "My&amp;App&lt;v2&gt;" in out
