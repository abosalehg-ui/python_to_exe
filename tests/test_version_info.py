"""Tests for VersionInfo dataclass and version-file generator."""

from py2exe_gui.core.version_info import (
    VersionInfo,
    generate_version_file,
    parse_version_tuple,
)


def test_parse_version_full():
    assert parse_version_tuple("1.2.3.4") == (1, 2, 3, 4)


def test_parse_version_short_pads_with_zeros():
    assert parse_version_tuple("1.2.3") == (1, 2, 3, 0)
    assert parse_version_tuple("1") == (1, 0, 0, 0)


def test_parse_version_handles_garbage():
    assert parse_version_tuple("") == (0, 0, 0, 0)
    assert parse_version_tuple("abc.def") == (0, 0, 0, 0)


def test_parse_version_accepts_comma_separated():
    assert parse_version_tuple("1, 2, 3, 4") == (1, 2, 3, 4)


def test_parse_version_truncates_extra_parts():
    assert parse_version_tuple("1.2.3.4.5.6") == (1, 2, 3, 4)


def test_is_empty_returns_true_for_blank_info():
    assert VersionInfo().is_empty() is True


def test_is_empty_returns_false_when_any_field_set():
    assert VersionInfo(company_name="Acme").is_empty() is False


def test_generate_file_contains_supplied_strings():
    info = VersionInfo(
        company_name="Acme Corp",
        product_name="Widget",
        file_version="1.2.3.4",
        legal_copyright="© 2026 Acme",
    )
    out = generate_version_file(info)
    assert "Acme Corp" in out
    assert "Widget" in out
    assert "1.2.3.4" in out
    assert "© 2026 Acme" in out


def test_generate_file_includes_version_tuple():
    info = VersionInfo(file_version="2.0.0.0")
    out = generate_version_file(info)
    assert "filevers=(2, 0, 0, 0)" in out


def test_generate_file_defaults_to_zero_when_version_blank():
    out = generate_version_file(VersionInfo(product_name="X"))
    assert "filevers=(0, 0, 0, 0)" in out
    assert "prodvers=(0, 0, 0, 0)" in out


def test_generate_file_escapes_single_quote():
    info = VersionInfo(company_name="O'Reilly Media")
    out = generate_version_file(info)
    assert "O\\'Reilly" in out


def test_generate_file_has_required_structural_blocks():
    out = generate_version_file(VersionInfo(product_name="X"))
    # Must produce a parseable PyInstaller version file with all key sections.
    assert "VSVersionInfo(" in out
    assert "FixedFileInfo(" in out
    assert "StringFileInfo(" in out
    assert "VarFileInfo(" in out
    assert "Translation" in out


def test_generate_file_uses_provided_language_id():
    info = VersionInfo(product_name="X", language_id="040704B0")
    out = generate_version_file(info)
    assert "040704B0" in out
