"""How long a built program takes to start — measured, with the method named.

"Start-up time" means different things for different programs, and a number
without its method is misleading. Every result says how it was measured:

* ``exit`` — a console program that finishes on its own: the time until the
  process has exited (start-up *and* its whole run — fine for a CLI tool,
  and labelled as such);
* ``probe`` — a program with the Runtime Kit: started with
  ``P2E_RUNTIME_PROBE=1``, the kit reports "ready" and exits *before* the
  program's own code runs, so this is the start-up cost the build adds
  (bootloader, unpacking a one-file build, the interpreter, the kit);
* ``first_output`` — anything else: the time until it first writes to
  stdout/stderr;
* ``still_running`` — it neither exited nor wrote anything within the
  timeout: no number is invented, the result says "still running after N s".

Each program runs several times from a neutral folder; the median is
reported (the first run is often slower: a cold disk cache, a one-file EXE
unpacking for the first time), and every run's time is kept.

UI-independent; runs the program with ``subprocess`` only.
"""

import os
import shutil
import statistics
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from py2exe_gui.core.process_tree import group_kwargs, kill_tree

METHOD_EXIT = "exit"
METHOD_PROBE = "probe"
METHOD_FIRST_OUTPUT = "first_output"
METHOD_STILL_RUNNING = "still_running"
METHODS = (METHOD_EXIT, METHOD_PROBE, METHOD_FIRST_OUTPUT, METHOD_STILL_RUNNING)

#: Must match ``p2e_runtime.PROBE_ENV`` / ``PROBE_EXIT_CODE`` (the runtime is
#: shipped inside users' programs and never imports the converter).
PROBE_ENV = "P2E_RUNTIME_PROBE"
PROBE_EXIT_CODE = 77
PROBE_MARKER = "P2E_RUNTIME_READY"

DEFAULT_RUNS = 5
DEFAULT_TIMEOUT = 10.0


@dataclass
class RunTiming:
    """One launch."""

    method: str
    seconds: Optional[float]  # None when still running at the timeout
    returncode: Optional[int] = None


@dataclass
class StartupResult:
    """Several launches of one program, summarised by the median."""

    method: str = ""
    runs: List[RunTiming] = field(default_factory=list)
    timeout: float = DEFAULT_TIMEOUT
    error: str = ""

    @property
    def times(self) -> List[float]:
        """The run times behind ``median``: only runs measured by ``method``."""
        return [r.seconds for r in self.runs if r.method == self.method and r.seconds is not None]

    @property
    def median(self) -> Optional[float]:
        times = self.times
        return statistics.median(times) if times else None

    @property
    def unit_runs(self) -> int:
        """How many runs the median is taken over."""
        return len(self.times)

    @property
    def ok(self) -> bool:
        return not self.error and self.median is not None


def _launch(exe: str, cwd: str, env: dict, timeout: float,
            popen=subprocess.Popen, clock=time.perf_counter) -> RunTiming:
    """Start ``exe`` once; time its exit, and its first output as a fallback.

    The exit is timed by a thread blocked in ``wait()``: ``wait(timeout=...)``
    polls with sleeps of up to 50 ms, and measured that way every result came
    out as a multiple of the polling steps.
    """
    first_output: List[float] = []
    ended: List[float] = []
    start = clock()
    process = popen([exe], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL, cwd=cwd, env=env, **group_kwargs())

    def watch_output():
        try:
            chunk = process.stdout.read(1)
        except (OSError, ValueError):
            return
        if chunk:
            first_output.append(clock())
        try:
            process.stdout.read()  # drain, so the program never blocks on a pipe
        except (OSError, ValueError):
            pass

    def watch_exit():
        process.wait()
        ended.append(clock())

    reader = threading.Thread(target=watch_output, daemon=True)
    waiter = threading.Thread(target=watch_exit, daemon=True)
    reader.start()
    waiter.start()
    waiter.join(timeout)
    if waiter.is_alive():
        # Only output seen *before* the timeout counts; then end the whole
        # group (a one-file EXE's app is a child of its bootloader).
        seen = [t for t in first_output if t - start <= timeout]
        kill_tree(process)
        waiter.join(5.0)
        reader.join(1.0)
        if seen:
            return RunTiming(METHOD_FIRST_OUTPUT, seen[0] - start)
        return RunTiming(METHOD_STILL_RUNNING, None)
    reader.join(1.0)
    returncode = process.returncode
    if returncode == PROBE_EXIT_CODE and env.get(PROBE_ENV) == "1":
        return RunTiming(METHOD_PROBE, ended[0] - start, returncode)
    return RunTiming(METHOD_EXIT, ended[0] - start, returncode)


def _summary_method(runs: List[RunTiming]) -> str:
    """The method behind the median: the one most runs were measured by."""
    measured = [r.method for r in runs if r.seconds is not None]
    if not measured:
        return METHOD_STILL_RUNNING
    return max(METHODS, key=measured.count)


def measure_startup(
    exe: str,
    runs: int = DEFAULT_RUNS,
    timeout: float = DEFAULT_TIMEOUT,
    probe: bool = False,
    popen=subprocess.Popen,
    clock: Callable[[], float] = time.perf_counter,
    on_run: Optional[Callable[[int, RunTiming], None]] = None,
) -> StartupResult:
    """Launch ``exe`` ``runs`` times from a neutral folder and time each launch.

    ``probe`` asks a Runtime Kit program to report "ready" and exit (the
    variable does nothing to a program without the kit). Runs measured by
    different methods are never mixed into one median: only the runs of the
    most common method count.
    """
    result = StartupResult(timeout=timeout)
    if not exe or not os.path.isfile(exe):
        result.error = "not_found"
        return result
    env = dict(os.environ, P2E_RUNTIME_NO_DIALOGS="1")
    if probe:
        env[PROBE_ENV] = "1"
    neutral = tempfile.mkdtemp(prefix="p2e_bench_")
    try:
        for index in range(max(1, runs)):
            try:
                timing = _launch(exe, neutral, env, timeout, popen, clock)
            except OSError as e:
                result.error = str(e)
                return result
            result.runs.append(timing)
            if on_run is not None:
                on_run(index, timing)
    finally:
        shutil.rmtree(neutral, ignore_errors=True)
    result.method = _summary_method(result.runs)
    return result
