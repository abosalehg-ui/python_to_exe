"""Tests for the shared finding/fix model."""

import pytest

from py2exe_gui.core.config import BuildConfig
from py2exe_gui.core.fixes import (
    FINDING_CODES,
    FIX_ADD_DATA,
    FIX_CONSOLE,
    FIX_HIDDEN_IMPORT,
    FIX_SET_SOURCE,
    SNIPPETS,
    Finding,
    Fix,
    apply_fixes,
    dedupe_findings,
    fix_is_applied,
    flag_fix,
    has_flag,
    readiness_score,
    sort_findings,
)
from py2exe_gui.strings import Ar, En


def test_unknown_fix_kind_is_rejected():
    with pytest.raises(ValueError):
        Fix("format_disk")


def test_readiness_score_penalises_errors_and_warnings_only():
    findings = [
        Finding("a", "error"),
        Finding("b", "warning"),
        Finding("c", "info"),
    ]
    assert readiness_score(findings) == 65
    assert readiness_score([]) == 100


def test_readiness_score_never_goes_negative():
    assert readiness_score([Finding("a", "error")] * 10) == 0


def test_sort_puts_errors_first():
    ordered = sort_findings(
        [Finding("i", "info"), Finding("w", "warning"), Finding("e", "error")]
    )
    assert [f.severity for f in ordered] == ["error", "warning", "info"]


def test_dedupe_uses_code_and_params():
    a = Finding("missing_package", "error", {"module": "x"})
    b = Finding("missing_package", "error", {"module": "x"}, origin="runtime")
    c = Finding("missing_package", "error", {"module": "y"})
    assert dedupe_findings([a, b, c]) == [a, c]


@pytest.mark.parametrize(
    "extra, expected",
    [
        ("--collect-data docx", True),
        ("--collect-data=docx", True),
        ("--noupx --collect-data docx", True),
        ("--collect-data pptx", False),
        ("--collect-all docx", False),
        ("", False),
    ],
)
def test_has_flag(extra, expected):
    assert has_flag(extra, "--collect-data", "docx") is expected


def test_apply_fixes_adds_everything_and_leaves_input_untouched(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    other = tmp_path / "main.py"
    config = BuildConfig(source=str(tmp_path / "app.py"), windowed=True, noconsole=True)
    fixes = [
        Fix(FIX_HIDDEN_IMPORT, "babel.numbers"),
        Fix(FIX_ADD_DATA, str(data)),
        flag_fix("--collect-data", "docx"),
        Fix(FIX_CONSOLE),
        Fix(FIX_SET_SOURCE, str(other)),
    ]
    new, applied = apply_fixes(config, fixes)

    assert applied == fixes
    assert new.hidden_imports == ["babel.numbers"]
    assert new.extra_files == [str(data)]
    assert new.extra_args == "--collect-data docx"
    assert new.windowed is False and new.noconsole is False
    assert new.source == str(other)
    # The original config is not mutated.
    assert config.hidden_imports == [] and config.windowed is True


def test_apply_fixes_is_idempotent():
    config = BuildConfig(hidden_imports=["x"], extra_args="--copy-metadata tqdm")
    fixes = [Fix(FIX_HIDDEN_IMPORT, "x"), flag_fix("--copy-metadata", "tqdm")]
    new, applied = apply_fixes(config, fixes)
    assert applied == []
    assert new.hidden_imports == ["x"]
    assert new.extra_args == "--copy-metadata tqdm"


def test_apply_fixes_skips_duplicates_within_one_call():
    new, applied = apply_fixes(BuildConfig(), [Fix(FIX_HIDDEN_IMPORT, "a")] * 3)
    assert new.hidden_imports == ["a"]
    assert len(applied) == 1


def test_fix_is_applied_for_console_and_paths(tmp_path):
    assert fix_is_applied(BuildConfig(), Fix(FIX_CONSOLE))
    assert not fix_is_applied(BuildConfig(windowed=True), Fix(FIX_CONSOLE))
    path = str(tmp_path / "x")
    assert fix_is_applied(BuildConfig(extra_files=[path]), Fix(FIX_ADD_DATA, path))


def test_every_snippet_is_valid_python():
    for name, code in SNIPPETS.items():
        compile(code, name, "exec")


@pytest.mark.parametrize("locale", [Ar, En])
def test_every_finding_code_has_title_and_detail(locale):
    for code in FINDING_CODES:
        assert getattr(locale, f"FINDING_{code.upper()}_TITLE", "").strip(), code
        assert getattr(locale, f"FINDING_{code.upper()}_DETAIL", "").strip(), code


@pytest.mark.parametrize("locale", [Ar, En])
def test_every_fix_kind_has_a_label(locale):
    from py2exe_gui.core.fixes import FIX_KINDS

    for kind in FIX_KINDS:
        assert getattr(locale, f"FIX_LABEL_{kind.upper()}", ""), kind
