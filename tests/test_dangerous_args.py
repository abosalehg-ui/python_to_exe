"""Tests for detecting code-executing flags in an untrusted settings file."""

from py2exe_gui.core.builder import DANGEROUS_FLAGS, find_dangerous_args


def test_clean_args_report_nothing():
    assert find_dangerous_args("--debug all --log-level INFO") == []


def test_empty_args_report_nothing():
    assert find_dangerous_args("") == []
    assert find_dangerous_args("   ") == []


def test_runtime_hook_is_flagged():
    """The headline case: code injected into every produced EXE."""
    assert find_dangerous_args("--runtime-hook /tmp/evil.py") == ["--runtime-hook"]


def test_equals_form_is_flagged():
    assert find_dangerous_args("--runtime-hook=/tmp/evil.py") == ["--runtime-hook"]


def test_additional_hooks_dir_is_flagged():
    assert "--additional-hooks-dir" in find_dangerous_args("--additional-hooks-dir hooks")


def test_add_binary_is_flagged():
    assert "--add-binary" in find_dangerous_args("--add-binary evil.dll:.")


def test_runtime_tmpdir_is_flagged():
    assert "--runtime-tmpdir" in find_dangerous_args("--runtime-tmpdir C:\\temp")


def test_multiple_flags_all_reported():
    found = find_dangerous_args("--runtime-hook a.py --add-binary b.dll:. --debug all")
    assert set(found) == {"--runtime-hook", "--add-binary"}


def test_duplicates_reported_once():
    assert find_dangerous_args("--runtime-hook a.py --runtime-hook b.py") == [
        "--runtime-hook"
    ]


def test_flag_hidden_inside_quoted_path_is_not_a_false_positive():
    found = find_dangerous_args('--paths "/opt/--runtime-hook/lib"', platform="linux")
    assert found == []


def test_windows_quoting_still_detects():
    found = find_dangerous_args('--runtime-hook "C:\\my hooks\\h.py"', platform="win32")
    assert found == ["--runtime-hook"]


def test_every_declared_flag_is_detectable():
    for flag in DANGEROUS_FLAGS:
        assert find_dangerous_args(f"{flag} value") == [flag]
