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


# ── Literal escaping (PyInstaller evals the generated file) ────────────────


def _company_line(value: str) -> str:
    out = generate_version_file(VersionInfo(company_name=value))
    return next(ln for ln in out.splitlines() if "CompanyName" in ln)


def test_newline_cannot_break_out_of_the_literal():
    """Regression: a raw newline used to produce an unparseable file."""
    line = _company_line("Acme\nInc")
    assert "\\n" in line
    assert line.count("u'") == 2  # name + value, both still on one line


def test_carriage_return_is_escaped():
    assert "\\r" in _company_line("Acme\rInc")


def test_tab_is_escaped():
    assert "\\t" in _company_line("Acme\tInc")


def test_quote_is_escaped():
    assert "\\'" in _company_line("Acme's")


def test_backslash_is_escaped():
    assert "\\\\" in _company_line("Acme\\Inc")


def test_control_characters_are_dropped():
    assert "\x07" not in _company_line("Acme\x07Inc")


def test_non_ascii_is_preserved_verbatim():
    """Arabic and symbols stay readable — the file is written as UTF-8."""
    assert "شركة الاختبار" in _company_line("شركة الاختبار")
    assert "©" in _company_line("© 2026")


def test_escaped_output_is_valid_python():
    """The real contract: PyInstaller must be able to eval the result."""
    import ast

    nasty = "Acme\n'; import os; os.system('calc')  #\\"
    out = generate_version_file(VersionInfo(company_name=nasty, file_version="1.0.0.0"))
    tree = ast.parse(out, mode="eval")  # raises SyntaxError if we broke out
    assert tree is not None


def test_injection_attempt_stays_inside_the_string():
    out = generate_version_file(VersionInfo(company_name="x'), StringStruct(u'Evil"))
    # The payload must remain part of the CompanyName value, not a new call.
    assert out.count("StringStruct(u'CompanyName'") == 1
