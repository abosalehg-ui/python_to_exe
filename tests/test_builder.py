"""Tests for build_pyinstaller_command()."""

import os
import sys

import pytest

from py2exe_gui.core.builder import build_pyinstaller_command
from py2exe_gui.core.config import BuildConfig


@pytest.fixture
def source_file(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("print('hi')\n")
    return str(f)


def test_returns_error_when_source_missing():
    cmd, error = build_pyinstaller_command(BuildConfig(source=""))
    assert cmd is None
    assert error is not None


def test_returns_error_for_nonexistent_source(tmp_path):
    cmd, error = build_pyinstaller_command(BuildConfig(source=str(tmp_path / "nope.py")))
    assert cmd is None
    assert error is not None


def test_minimal_command_starts_with_pyinstaller(source_file):
    cmd, error = build_pyinstaller_command(BuildConfig(source=source_file))
    assert error is None
    assert cmd is not None
    assert cmd[:3] == [sys.executable, "-m", "PyInstaller"]
    assert cmd[-1] == source_file


def test_onefile_flag_included_by_default(source_file):
    cmd, _ = build_pyinstaller_command(BuildConfig(source=source_file))
    assert "--onefile" in cmd


def test_onefile_flag_omitted_when_disabled(source_file):
    cmd, _ = build_pyinstaller_command(BuildConfig(source=source_file, onefile=False))
    assert "--onefile" not in cmd


def test_windowed_flag(source_file):
    cmd, _ = build_pyinstaller_command(BuildConfig(source=source_file, windowed=True))
    assert "--windowed" in cmd


def test_strip_flag_off_by_default(source_file):
    cmd, _ = build_pyinstaller_command(BuildConfig(source=source_file))
    assert "--strip" not in cmd


def test_name_option_present(source_file):
    cmd, _ = build_pyinstaller_command(
        BuildConfig(source=source_file, output_name="MyApp")
    )
    assert "--name" in cmd
    assert cmd[cmd.index("--name") + 1] == "MyApp"


def test_icon_only_added_when_file_exists(source_file, tmp_path):
    icon = tmp_path / "icon.ico"
    icon.write_bytes(b"\x00")
    cmd, _ = build_pyinstaller_command(
        BuildConfig(source=source_file, icon=str(icon))
    )
    assert "--icon" in cmd
    assert cmd[cmd.index("--icon") + 1] == str(icon)


def test_icon_skipped_when_missing(source_file, tmp_path):
    cmd, _ = build_pyinstaller_command(
        BuildConfig(source=source_file, icon=str(tmp_path / "missing.ico"))
    )
    assert "--icon" not in cmd


def test_output_dir_adds_path_flags(source_file, tmp_path):
    out = str(tmp_path)
    cmd, _ = build_pyinstaller_command(BuildConfig(source=source_file, output_dir=out))
    assert "--distpath" in cmd
    assert "--workpath" in cmd
    assert "--specpath" in cmd
    assert cmd[cmd.index("--distpath") + 1] == os.path.join(out, "dist")


def test_hidden_imports_each_get_flag(source_file):
    cmd, _ = build_pyinstaller_command(
        BuildConfig(source=source_file, hidden_imports=["numpy", "pandas", "PIL"])
    )
    indices = [i for i, x in enumerate(cmd) if x == "--hidden-import"]
    assert len(indices) == 3
    assert cmd[indices[0] + 1] == "numpy"
    assert cmd[indices[2] + 1] == "PIL"


def test_extra_files_use_correct_separator_on_windows(source_file, tmp_path):
    extra = tmp_path / "data.txt"
    extra.write_text("x")
    cmd, _ = build_pyinstaller_command(
        BuildConfig(source=source_file, extra_files=[str(extra)]),
        platform="win32",
    )
    add_data_idx = cmd.index("--add-data")
    assert ";" in cmd[add_data_idx + 1]
    assert ":" not in cmd[add_data_idx + 1].replace(":\\", "")


def test_extra_files_use_colon_on_unix(source_file, tmp_path):
    extra = tmp_path / "data.txt"
    extra.write_text("x")
    cmd, _ = build_pyinstaller_command(
        BuildConfig(source=source_file, extra_files=[str(extra)]),
        platform="linux",
    )
    add_data_idx = cmd.index("--add-data")
    assert ":" in cmd[add_data_idx + 1]


def test_missing_extra_file_is_skipped(source_file, tmp_path):
    cmd, _ = build_pyinstaller_command(
        BuildConfig(source=source_file, extra_files=[str(tmp_path / "nope.txt")])
    )
    assert "--add-data" not in cmd


def test_optimize_level(source_file):
    cmd, _ = build_pyinstaller_command(BuildConfig(source=source_file, optimize=2))
    assert "-O2" in cmd


def test_optimize_zero_omitted(source_file):
    cmd, _ = build_pyinstaller_command(BuildConfig(source=source_file, optimize=0))
    assert not any(x.startswith("-O") for x in cmd)


def test_upx_disabled_adds_noupx(source_file):
    cmd, _ = build_pyinstaller_command(BuildConfig(source=source_file, upx=False))
    assert "--noupx" in cmd


def test_upx_enabled_adds_dir_and_level(source_file):
    cmd, _ = build_pyinstaller_command(
        BuildConfig(source=source_file, upx=True, upx_level=7)
    )
    assert "--upx-dir=upx" in cmd
    assert "--upx-level=7" in cmd
    assert "--noupx" not in cmd


def test_extra_args_appended(source_file):
    cmd, _ = build_pyinstaller_command(
        BuildConfig(source=source_file, extra_args="--debug all --log-level INFO")
    )
    assert "--debug" in cmd
    assert "all" in cmd
    assert "--log-level" in cmd
    assert "INFO" in cmd


def test_source_is_last_argument(source_file):
    cmd, _ = build_pyinstaller_command(
        BuildConfig(
            source=source_file,
            output_name="x",
            hidden_imports=["a", "b"],
            extra_args="--debug",
        )
    )
    assert cmd[-1] == source_file


def test_custom_python_executable(source_file):
    cmd, _ = build_pyinstaller_command(
        BuildConfig(source=source_file), python_executable="/usr/bin/python3.11"
    )
    assert cmd[0] == "/usr/bin/python3.11"


def test_version_file_added_when_present(source_file, tmp_path):
    vf = tmp_path / "version.txt"
    vf.write_text("VSVersionInfo(...)")
    cmd, _ = build_pyinstaller_command(
        BuildConfig(source=source_file, version_file=str(vf))
    )
    assert "--version-file" in cmd
    assert cmd[cmd.index("--version-file") + 1] == str(vf)


def test_version_file_skipped_when_missing(source_file, tmp_path):
    cmd, _ = build_pyinstaller_command(
        BuildConfig(source=source_file, version_file=str(tmp_path / "absent.txt"))
    )
    assert "--version-file" not in cmd
