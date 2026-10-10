"""The start-up benchmark and the process-group kill (2.0, milestone 3).

The programs launched here are real: tiny Python scripts made executable,
standing in for a built EXE. POSIX only where a shebang is needed.
"""

import os
import stat
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

import p2e_runtime
from py2exe_gui.core import startup_bench as sb
from py2exe_gui.core.process_tree import group_kwargs, kill_tree
from py2exe_gui.core.smoke_test import run_smoke_test

posix_only = pytest.mark.skipif(sys.platform == "win32", reason="needs a shebang script")


def gone(pid, wait=5.0):
    """True once ``pid`` no longer runs. A killed orphan can linger as a
    zombie until the container's init reaps it, so a zombie counts as gone."""
    deadline = time.monotonic() + wait
    while True:
        try:
            os.kill(pid, 0)
        except OSError:
            return True
        try:
            with open(f"/proc/{pid}/stat") as f:
                if f.read().rsplit(")", 1)[1].split()[0] == "Z":
                    return True
        except OSError:
            pass
        if time.monotonic() > deadline:
            return False
        time.sleep(0.05)


def program(tmp_path, name, body):
    path = tmp_path / name
    path.write_text(f"#!{sys.executable}\n{body}")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return str(path)


@posix_only
def test_a_program_that_exits_is_timed_until_it_exits(tmp_path):
    exe = program(tmp_path, "cli", "print('done')\n")
    result = sb.measure_startup(exe, runs=3, timeout=10)
    assert result.method == sb.METHOD_EXIT and result.ok
    assert len(result.runs) == 3 and len(result.times) == 3
    assert 0 < result.median < 10
    assert all(r.returncode == 0 for r in result.runs)


@posix_only
def test_a_server_is_timed_until_its_first_output(tmp_path):
    exe = program(tmp_path, "server",
                  "import time\nprint('listening', flush=True)\ntime.sleep(60)\n")
    result = sb.measure_startup(exe, runs=2, timeout=2)
    assert result.method == sb.METHOD_FIRST_OUTPUT
    assert all(0 < t < 2 for t in result.times)


@posix_only
def test_a_silent_program_gets_no_number(tmp_path):
    exe = program(tmp_path, "silent", "import time\ntime.sleep(60)\n")
    result = sb.measure_startup(exe, runs=2, timeout=0.8)
    assert result.method == sb.METHOD_STILL_RUNNING
    assert result.median is None and not result.ok
    assert all(r.seconds is None for r in result.runs)


@posix_only
def test_the_probe_is_recognised_only_when_asked_for(tmp_path):
    body = (
        "import os, time\n"
        f"if os.environ.get('{sb.PROBE_ENV}') == '1':\n"
        f"    os._exit({sb.PROBE_EXIT_CODE})\n"
        "time.sleep(0.3)\n"
    )
    exe = program(tmp_path, "kit", body)
    probed = sb.measure_startup(exe, runs=2, timeout=10, probe=True)
    assert probed.method == sb.METHOD_PROBE
    plain = sb.measure_startup(exe, runs=2, timeout=10)
    assert plain.method == sb.METHOD_EXIT
    # The probe skipped the program's own work (the sleep).
    assert probed.median < plain.median


@posix_only
def test_a_timeout_ends_the_whole_process_group(tmp_path):
    marker = tmp_path / "child.pid"
    body = (
        "import subprocess, sys, time\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
        f"open({str(marker)!r}, 'w').write(str(child.pid))\n"
        "time.sleep(120)\n"
    )
    exe = program(tmp_path, "parent", body)
    sb.measure_startup(exe, runs=1, timeout=1.5)
    child = int(marker.read_text())
    assert gone(child)  # no orphan left behind


@posix_only
def test_the_smoke_test_no_longer_orphans_children(tmp_path):
    marker = tmp_path / "child.pid"
    body = (
        "import subprocess, sys, time\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
        f"open({str(marker)!r}, 'w').write(str(child.pid))\n"
        "print('up', flush=True)\n"
        "time.sleep(120)\n"
    )
    exe = program(tmp_path, "gui", body)
    result = run_smoke_test(exe, timeout=1.5)
    assert result.ran and result.passed and result.returncode is None
    assert "up" in result.output
    assert gone(int(marker.read_text()))


def test_missing_program():
    result = sb.measure_startup("/no/such/program")
    assert result.error == "not_found" and not result.ok and result.runs == []


def test_output_after_the_timeout_does_not_count():
    """A line arriving after the timeout (or after the kill) is not "first output"."""
    clock_values = iter([0.0, 3.5])  # start, then the first chunk at 3.5 s

    class Pipe:
        def __init__(self):
            self.sent = False

        def read(self, n=-1):
            if n == 1 and not self.sent:
                self.sent = True
                return b"x"
            return b""

    class Process:
        pid = 1
        returncode = None

        def __init__(self):
            self.stdout = Pipe()

        def wait(self):
            time.sleep(0.4)  # longer than the timeout below
            return -9

        def poll(self):
            return None

        def kill(self):
            pass

    timing = sb._launch("x", ".", {}, 0.1, popen=lambda *a, **k: Process(),
                        clock=lambda: next(clock_values, 4.0))
    assert timing.method == sb.METHOD_STILL_RUNNING and timing.seconds is None


def test_the_median_uses_only_runs_of_the_summary_method():
    result = sb.StartupResult(method=sb.METHOD_EXIT, runs=[
        sb.RunTiming(sb.METHOD_EXIT, 0.2), sb.RunTiming(sb.METHOD_EXIT, 0.4),
        sb.RunTiming(sb.METHOD_FIRST_OUTPUT, 0.01), sb.RunTiming(sb.METHOD_EXIT, 0.3),
    ])
    assert result.times == [0.2, 0.4, 0.3] and result.median == 0.3
    assert sb._summary_method(result.runs) == sb.METHOD_EXIT
    assert sb._summary_method([sb.RunTiming(sb.METHOD_STILL_RUNNING, None)]) == (
        sb.METHOD_STILL_RUNNING)


def test_the_runtime_and_the_benchmark_agree_on_the_probe():
    assert p2e_runtime.PROBE_ENV == sb.PROBE_ENV
    assert p2e_runtime.PROBE_EXIT_CODE == sb.PROBE_EXIT_CODE
    assert p2e_runtime.PROBE_MARKER == sb.PROBE_MARKER


def test_the_runtime_kit_reports_ready_and_exits_before_the_app(tmp_path):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config = tmp_path / "p2e_runtime.json"
    config.write_text('{"app": {"name": "Probe"}, "services": {}}')
    code = (
        "import sys; sys.path.insert(0, sys.argv[1])\n"
        "import p2e_runtime\n"
        "p2e_runtime.install(sys.argv[2])\n"
        "print('the app ran')\n"
    )
    env = dict(os.environ, **{sb.PROBE_ENV: "1"})
    probed = subprocess.run([sys.executable, "-c", code, root, str(config)],
                            capture_output=True, text=True, env=env, timeout=60)
    assert probed.returncode == sb.PROBE_EXIT_CODE, probed.stderr
    assert probed.stdout.strip() == sb.PROBE_MARKER
    env.pop(sb.PROBE_ENV)
    plain = subprocess.run([sys.executable, "-c", code, root, str(config)],
                           capture_output=True, text=True, env=env, timeout=60)
    assert plain.returncode == 0 and "the app ran" in plain.stdout


def test_group_kwargs_per_platform():
    assert group_kwargs("linux") == {"start_new_session": True}
    assert "creationflags" in group_kwargs("win32")


def test_kill_tree_on_windows_uses_taskkill():
    calls = []
    process = SimpleNamespace(pid=42, poll=lambda: None, kill=lambda: calls.append("kill"))
    kill_tree(process, "win32", run=lambda cmd, **kw: calls.append(cmd))
    assert calls[0] == ["taskkill", "/F", "/T", "/PID", "42"] and calls[-1] == "kill"


def test_kill_tree_survives_a_vanished_process():
    process = SimpleNamespace(pid=2 ** 22 + 12345, poll=lambda: 0,
                              kill=lambda: (_ for _ in ()).throw(OSError("gone")))
    kill_tree(process, "linux")  # no exception
