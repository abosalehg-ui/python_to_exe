"""Tests for the post-build smoke test runner."""

import os
import stat
import sys

import pytest

from py2exe_gui.core.smoke_test import (
    SmokeResult,
    locate_built_executable,
    run_smoke_test,
)

# ─── locate_built_executable ────────────────────────────────────────────


def test_locate_returns_none_for_missing_inputs():
    assert locate_built_executable("", "name", True) is None
    assert locate_built_executable("/tmp", "", True) is None


def test_locate_finds_onefile_exe(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "myapp.exe").write_bytes(b"")
    found = locate_built_executable(str(tmp_path), "myapp", onefile=True)
    assert found == str(dist / "myapp.exe")


def test_locate_finds_onedir_exe(tmp_path):
    inner = tmp_path / "dist" / "myapp"
    inner.mkdir(parents=True)
    (inner / "myapp.exe").write_bytes(b"")
    found = locate_built_executable(str(tmp_path), "myapp", onefile=False)
    assert found == str(inner / "myapp.exe")


def test_locate_finds_exe_without_extension_on_unix(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "myapp").write_bytes(b"")
    found = locate_built_executable(str(tmp_path), "myapp", onefile=True)
    assert found == str(dist / "myapp")


def test_locate_returns_none_when_nothing_built(tmp_path):
    assert locate_built_executable(str(tmp_path), "missing", onefile=True) is None


# ─── run_smoke_test ─────────────────────────────────────────────────────


def test_run_smoke_test_missing_file():
    result = run_smoke_test("/no/such/file", timeout=1.0)
    assert result.ran is False
    assert result.passed is False
    assert result.error


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only shebang test")
def test_run_smoke_test_clean_exit(tmp_path):
    script = tmp_path / "ok.sh"
    script.write_text("#!/bin/sh\nexit 0\n")
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    result = run_smoke_test(str(script), timeout=2.0)
    assert result.ran is True
    assert result.passed is True
    assert result.returncode == 0


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only shebang test")
def test_run_smoke_test_nonzero_exit_fails(tmp_path):
    script = tmp_path / "fail.sh"
    script.write_text("#!/bin/sh\nexit 3\n")
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    result = run_smoke_test(str(script), timeout=2.0)
    assert result.ran is True
    assert result.passed is False
    assert result.returncode == 3


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only shebang test")
def test_run_smoke_test_timeout_treated_as_pass(tmp_path):
    # GUI-like script that stays running; hitting the timeout means "started OK".
    script = tmp_path / "loop.sh"
    script.write_text("#!/bin/sh\nsleep 30\n")
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    result = run_smoke_test(str(script), timeout=0.5)
    assert result.ran is True
    assert result.returncode is None
    assert result.passed is True


def test_smoke_result_not_ran_never_passes():
    r = SmokeResult(ran=False, exited_cleanly=False, returncode=None, error="x")
    assert r.passed is False


def test_smoke_result_clean_exit_zero_passes():
    r = SmokeResult(ran=True, exited_cleanly=True, returncode=0)
    assert r.passed is True


def test_smoke_result_clean_exit_nonzero_fails():
    r = SmokeResult(ran=True, exited_cleanly=True, returncode=1)
    assert r.passed is False


# ─── Output capture and working directory (1.3) ─────────────────────────


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only shebang test")
def test_run_smoke_test_captures_the_traceback(tmp_path):
    script = tmp_path / "crash.sh"
    script.write_text(
        "#!/bin/sh\n"
        "echo starting\n"
        "echo \"ModuleNotFoundError: No module named 'x'\" >&2\n"
        "exit 1\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    result = run_smoke_test(str(script), timeout=2.0)
    assert "starting" in result.output
    assert "No module named 'x'" in result.output


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only shebang test")
def test_run_smoke_test_keeps_output_on_timeout(tmp_path):
    script = tmp_path / "slow.sh"
    script.write_text("#!/bin/sh\necho alive\nsleep 30\n")
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    result = run_smoke_test(str(script), timeout=1.0)
    assert result.passed is True
    assert "alive" in result.output


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only shebang test")
def test_run_smoke_test_runs_in_the_given_folder(tmp_path):
    script = tmp_path / "where.sh"
    script.write_text("#!/bin/sh\npwd\n")
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    result = run_smoke_test(str(script), timeout=2.0, cwd=str(elsewhere))
    assert os.path.realpath(result.output.strip()) == os.path.realpath(str(elsewhere))


def test_combined_output_decodes_bytes_and_caps_length():
    from py2exe_gui.core.smoke_test import MAX_OUTPUT_CHARS, _combined

    assert _combined(b"out", "err") == "out\nerr"
    assert _combined(None, None) == ""
    assert len(_combined("x" * (MAX_OUTPUT_CHARS + 50), "")) == MAX_OUTPUT_CHARS


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only shebang test")
def test_run_from_neutral_folder_cleans_up(tmp_path):
    from py2exe_gui.core.smoke_test import run_from_neutral_folder

    script = tmp_path / "where.sh"
    script.write_text("#!/bin/sh\npwd\n")
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    result = run_from_neutral_folder(str(script), timeout=2.0)
    folder = result.output.strip()
    assert "p2e_run_" in folder
    assert not os.path.exists(folder)
