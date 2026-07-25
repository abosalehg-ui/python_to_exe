"""Integration guard: every flag we emit must exist in PyInstaller's CLI.

This is the test that was missing when `-O2` and `--upx-level` shipped. The
unit tests asserted the builder produced the strings it was written to
produce, which says nothing about whether PyInstaller accepts them. Here we
ask PyInstaller itself.

Skipped when PyInstaller is not installed, so the core-only CI job is
unaffected.
"""

import re
import subprocess
import sys

import pytest

from py2exe_gui.core import BuildConfig, build_pyinstaller_command

pytest.importorskip("PyInstaller", reason="PyInstaller not installed")


@pytest.fixture(scope="module")
def supported_options():
    """Long options accepted by the installed PyInstaller, parsed from --help."""
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--help"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return set(re.findall(r"(--[a-zA-Z][a-zA-Z0-9-]+)", result.stdout))


@pytest.fixture
def source_file(tmp_path):
    script = tmp_path / "app.py"
    script.write_text("print('hi')\n")
    return str(script)


def _emitted_options(cmd):
    """Long options in a generated command (ignores values and the '-m' pair)."""
    return {tok.split("=", 1)[0] for tok in cmd if tok.startswith("--")}


def _maximal_config(source_file, tmp_path):
    icon = tmp_path / "app.ico"
    icon.write_bytes(b"\x00")
    version = tmp_path / "version.txt"
    version.write_text("VSVersionInfo()")
    splash = tmp_path / "splash.png"
    splash.write_bytes(b"\x89PNG\r\n")
    manifest = tmp_path / "app.manifest"
    manifest.write_text("<assembly/>")
    data = tmp_path / "data.txt"
    data.write_text("x")
    return BuildConfig(
        source=source_file,
        output_name="demo",
        output_dir=str(tmp_path / "out"),
        icon=str(icon),
        version_file=str(version),
        splash_image=str(splash),
        manifest_file=str(manifest),
        extra_files=[str(data)],
        hidden_imports=["numpy"],
        onefile=True,
        windowed=True,
        noconsole=True,
        clean=True,
        noconfirm=True,
        strip=True,
        optimize=2,
        upx=True,
        upx_dir=str(tmp_path),
    )


def test_every_emitted_flag_is_a_real_pyinstaller_option(
    source_file, tmp_path, supported_options
):
    cmd, error = build_pyinstaller_command(_maximal_config(source_file, tmp_path))
    assert error is None

    unknown = _emitted_options(cmd) - supported_options
    assert not unknown, f"PyInstaller does not accept: {sorted(unknown)}"


def test_no_short_optimize_flag_is_emitted(source_file, tmp_path):
    """`-O1`/`-O2` are Python interpreter flags, not PyInstaller options."""
    cmd, _ = build_pyinstaller_command(_maximal_config(source_file, tmp_path))
    assert not any(re.fullmatch(r"-O\d*", tok) for tok in cmd)


def test_upx_level_is_not_a_real_option(supported_options):
    """Documents why the UPX level spinbox was removed."""
    assert "--upx-level" not in supported_options


def test_optimize_is_a_real_option(supported_options):
    assert "--optimize" in supported_options


@pytest.mark.slow
def test_generated_command_actually_builds(tmp_path):
    """End-to-end: the command we generate produces a working executable."""
    script = tmp_path / "app.py"
    script.write_text("import json\nprint(json.dumps({'ok': True}))\n")
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "x.txt").write_text("data")

    cmd, error = build_pyinstaller_command(
        BuildConfig(
            source=str(script),
            output_name="demo",
            output_dir=str(tmp_path),
            optimize=2,
            extra_files=[str(assets)],
            onefile=True,
        )
    )
    assert error is None

    build = subprocess.run(cmd, capture_output=True, text=True, cwd=str(tmp_path))
    assert build.returncode == 0, build.stderr[-2000:]

    exe = tmp_path / "dist" / "demo"
    if not exe.exists():
        exe = tmp_path / "dist" / "demo.exe"
    assert exe.exists()

    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    assert '"ok": true' in run.stdout
