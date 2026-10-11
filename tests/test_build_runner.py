"""The headless build runner shared by the CLI and the release pipeline."""

import os
import subprocess
import sys

import pytest

from py2exe_gui.core.build_runner import (
    PreparedBuild,
    prepare_build,
    run_build,
    stream_command,
)
from py2exe_gui.core.process_tree import group_kwargs
from py2exe_gui.core.project_file import ProjectConfig


def project_for(tmp_path, **build):
    src = tmp_path / "app.py"
    src.write_text("print(1)\n")
    project = ProjectConfig()
    project.build.source = str(src)
    project.build.output_name = "App"
    for key, value in build.items():
        setattr(project.build, key, value)
    return project


def test_prepare_writes_version_and_manifest_files_and_cleans_them(tmp_path):
    project = project_for(tmp_path)
    project.version_info.product_version = "1.2.3.0"
    project.version_info.company_name = "شركة"
    project.manifest.enabled = True
    project.manifest.require_admin = True
    prepared = prepare_build(project, "/py/python")
    assert prepared.error == "" and prepared.command[0] == "/py/python"
    version_file = prepared.command[prepared.command.index("--version-file") + 1]
    manifest = prepared.command[prepared.command.index("--manifest") + 1]
    assert "شركة" in open(version_file, encoding="utf-8").read()
    assert "requireAdministrator" in open(manifest, encoding="utf-8").read()
    assert prepared.cwd == str(tmp_path)
    prepared.cleanup()
    assert not os.path.exists(version_file) and not os.path.exists(manifest)
    # The project itself is untouched: no temp path leaks into it.
    assert project.build.version_file == "" and project.build.manifest_file == ""


def test_prepare_without_a_source(tmp_path):
    prepared = prepare_build(ProjectConfig(), sys.executable)
    assert prepared.error and prepared.command == [] and prepared.temp_files == []
    outcome = run_build(prepared, lambda _l: None)
    assert not outcome.ok and outcome.error


def test_prepare_embeds_the_runtime_kit(tmp_path):
    project = project_for(tmp_path)
    project.build.runtime_kit.crash_reporter = True
    prepared = prepare_build(project, sys.executable, texts={"crash_title": "t"})
    assert "--runtime-hook" in prepared.command
    assert prepared.services == ["crash_reporter"]
    prepared.cleanup()


def test_prepare_reports_runtime_kit_errors(tmp_path):
    project = project_for(tmp_path)
    project.build.runtime_kit.updater = True  # no URL, no key
    prepared = prepare_build(project, sys.executable)
    assert {f.code for f in prepared.kit_errors} >= {"kit_update_url_missing"}
    assert not run_build(prepared, lambda _l: None).ok


def test_stream_command_reports_lines_and_stages(tmp_path):
    lines, stages = [], []
    code = stream_command(
        [sys.executable, "-c",
         "print('INFO: Analyzing base_library.zip'); print('INFO: Building PYZ'); "
         "print('صباح الخير'); raise SystemExit(3)"],
        str(tmp_path), lines.append, lambda stage, pct: stages.append((stage, pct)),
    )
    assert code == 3
    assert lines == ["INFO: Analyzing base_library.zip", "INFO: Building PYZ", "صباح الخير"]
    assert stages == [("analyzing", 5), ("pyz", 62)]


def test_run_build_success_failure_and_missing_tool(tmp_path):
    ok = PreparedBuild(command=[sys.executable, "-c", "print('done')"], cwd=str(tmp_path))
    out = []
    assert run_build(ok, out.append).ok and out == ["done"]
    bad = PreparedBuild(command=[sys.executable, "-c", "raise SystemExit(2)"])
    outcome = run_build(bad, lambda _l: None)
    assert not outcome.ok and outcome.returncode == 2
    missing = PreparedBuild(command=[str(tmp_path / "no-such-tool")])
    outcome = run_build(missing, lambda _l: None)
    assert not outcome.ok and outcome.error


class FakeProcess:
    """A stand-in engine process: records how it is stopped.

    ``wait()`` without a timeout would block forever (``hangs``): the old
    ``terminate(); wait()`` did exactly that on an engine whose child kept
    the pipe open. No ``pid`` on purpose: ``kill_tree`` must never signal a
    group it cannot prove is the engine's own.
    """

    def __init__(self, hangs=False):
        self.stdout = iter(["one\n", "two\n"])
        self.calls = []
        self.hangs = hangs
        self.returncode = None

    def terminate(self):
        self.calls.append("terminate")

    def kill(self):
        self.calls.append("kill")
        self.returncode = -9

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.calls.append(("wait", timeout))
        if self.hangs and self.returncode is None:
            if timeout is None:
                raise AssertionError("wait() without a timeout would block forever")
            raise subprocess.TimeoutExpired("x", timeout)
        self.returncode = -15 if self.returncode is None else self.returncode
        return self.returncode


def _interrupt_on_second_line(line):
    if line == "two":
        raise KeyboardInterrupt


def test_stream_command_terminates_on_interrupt_and_waits_with_a_timeout():
    process = FakeProcess()
    with pytest.raises(KeyboardInterrupt):
        stream_command(["x"], "", _interrupt_on_second_line, popen=lambda *a, **k: process)
    assert process.calls == ["terminate", ("wait", 5.0)]


def test_stream_command_kills_an_engine_that_ignores_terminate():
    process = FakeProcess(hangs=True)
    with pytest.raises(KeyboardInterrupt):
        stream_command(["x"], "", _interrupt_on_second_line, popen=lambda *a, **k: process)
    # Polite first, then the whole tree; neither wait is unbounded.
    assert process.calls == ["terminate", ("wait", 5.0), "kill", ("wait", 5.0)]


def test_stream_command_starts_the_engine_in_its_own_group():
    seen = {}

    def popen(*args, **kwargs):
        seen.update(kwargs)
        return FakeProcess()

    stream_command(["x"], "", lambda _l: None, popen=popen)
    assert all(seen.get(k) == v for k, v in group_kwargs().items())
