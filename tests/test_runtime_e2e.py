"""End to end: a real PyInstaller build with every Runtime Kit service on.

One build (minutes), then the EXE is run the way a user would run it, from a
neutral folder:

* ``resource_path`` finds bundled data;
* an uncaught exception leaves a crash report (and no environment in it);
* a second copy exits while the first runs;
* with no stdout/stderr at all (a windowed EXE), ``print`` and
  ``sys.stdout.write`` land in the log file — and a normal exit does not
  produce a crash report;
* a signed update from a local server replaces the running one-file EXE,
  restarts it, and the restarted copy removes the ``.old`` file.

POSIX only: closing descriptors 1 and 2 is how a windowed start is
reproduced here. The Windows-only pieces (renaming a running .exe,
MessageBoxW, the named mutex) are not exercised by this test.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import time

import pytest

pytest.importorskip("PyInstaller", reason="PyInstaller not installed")

from py2exe_gui.core.builder import build_pyinstaller_command  # noqa: E402
from py2exe_gui.core.config import BuildConfig, RuntimeKitConfig  # noqa: E402
from py2exe_gui.core.runtime_kit import write_kit  # noqa: E402
from py2exe_gui.core.update_signing import (  # noqa: E402
    manifest_bytes,
    new_signing_key,
    sign,
)
from tests.update_server import UpdateServer  # noqa: E402

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(sys.platform == "win32", reason="POSIX reproduction of a windowed start"),
]

APP = '''
import os
import sys
import time

from p2e_runtime import resource_path


def main():
    command, out = sys.argv[1], sys.argv[2]
    if command == "resource":
        with open(resource_path("data/hello.txt"), encoding="utf-8") as f:
            open(out, "w").write(f.read())
    elif command == "crash":
        raise RuntimeError("deliberate crash for the test")
    elif command == "hold":
        open(out, "w").write("started")
        time.sleep(float(sys.argv[3]))
    elif command == "print":
        print("hello-from-print")
        sys.stdout.write("hello-from-write\\n")
        open(out, "w").write("printed")
    elif command == "update":
        from p2e_runtime import updates

        info = updates.check()
        open(out, "w").write(f"found {info.version}")
        updates.apply(info, relaunch_args=["after-update", sys.argv[3]])
    elif command == "after-update":
        old = sys.executable + ".old"
        for _ in range(100):
            if not os.path.exists(old):
                break
            time.sleep(0.1)
        open(out, "w").write(f"relaunched old_exists={os.path.exists(old)}")


if __name__ == "__main__":
    main()
'''


@pytest.fixture(scope="module")
def server():
    saved = {k: os.environ.pop(k) for k in list(os.environ) if k.lower().endswith("_proxy")}
    with UpdateServer() as srv:
        yield srv
    os.environ.update(saved)


@pytest.fixture(scope="module")
def built(tmp_path_factory, server):
    root = tmp_path_factory.mktemp("kit_e2e")
    project = root / "proj"
    (project / "data").mkdir(parents=True)
    (project / "data" / "hello.txt").write_text("hello bundled", encoding="utf-8")
    (project / "app.py").write_text(APP, encoding="utf-8")
    key = new_signing_key()
    config = BuildConfig(
        source=str(project / "app.py"), output_name="KitApp", output_dir=str(root / "out"),
        windowed=True, extra_files=[str(project / "data")],
        runtime_kit=RuntimeKitConfig(
            resource_path=True, log_redirect=True, crash_reporter=True, single_instance=True,
            updater=True, app_version="1.0.0", update_url=server.url("/update.json"),
            update_public_key=key.public_hex,
        ),
    )
    os.makedirs(config.output_dir)
    # The test flag is the only way to accept http://127.0.0.1.
    options, errors = write_kit(config, allow_insecure_localhost=True)
    assert errors == []
    cmd, error = build_pyinstaller_command(config, extra_options=options)
    assert error is None
    result = subprocess.run(cmd, cwd=config.output_dir, capture_output=True, text=True,
                            timeout=900)
    assert result.returncode == 0, result.stderr[-3000:]
    exe = root / "out" / "dist" / "KitApp"
    assert exe.is_file()
    return exe, key, root


@pytest.fixture
def run(built, tmp_path, monkeypatch):
    exe, _key, _root = built
    neutral = tmp_path / "neutral"
    neutral.mkdir()
    state = tmp_path / "state"
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    monkeypatch.setenv("SECRET_SENTINEL", "sentinel-value-8642")

    def start(*args, closed_streams=False, wait=True, binary=None):
        kwargs = {"cwd": str(neutral), "stdout": subprocess.PIPE, "stderr": subprocess.PIPE,
                  "text": True}
        if closed_streams:
            # What a windowed EXE gets: no descriptors 1 and 2 at all, so
            # Python starts with sys.stdout and sys.stderr set to None.
            kwargs.update(stdout=None, stderr=None,
                          preexec_fn=lambda: (os.close(1), os.close(2)))
        process = subprocess.Popen([str(binary or exe), *args], **kwargs)
        if wait:
            process.out, process.err = process.communicate(timeout=120)
        return process

    start.state = state / "KitApp"
    start.tmp = tmp_path
    return start


def test_resource_path_finds_bundled_data_from_a_neutral_folder(run):
    out = run.tmp / "res.txt"
    assert run("resource", str(out)).returncode == 0
    assert out.read_text(encoding="utf-8") == "hello bundled"


def test_crash_leaves_a_report(run):
    process = run("crash", str(run.tmp / "unused"))
    assert process.returncode != 0
    reports = list((run.state / "crashes").glob("crash-*.txt"))
    assert len(reports) == 1
    text = reports[0].read_text(encoding="utf-8")
    assert "RuntimeError: deliberate crash for the test" in text
    assert "Crash report: KitApp 1.0.0" in text and "Frozen: yes" in text
    assert "sentinel-value-8642" not in text


def test_second_instance_exits(run):
    marker = run.tmp / "hold.txt"
    first = run("hold", str(marker), "20", wait=False)
    try:
        for _ in range(300):
            if marker.exists():
                break
            time.sleep(0.1)
        assert marker.exists(), "first instance never started"
        second = run("print", str(run.tmp / "second.txt"))
        assert second.returncode == 0
        assert not (run.tmp / "second.txt").exists()  # its own code never ran
        assert "KitApp is already running." in second.err
    finally:
        first.kill()
        first.wait()


def test_windowed_output_goes_to_the_log(run):
    marker = run.tmp / "printed.txt"
    process = run("print", str(marker), closed_streams=True)
    assert process.returncode == 0
    assert marker.read_text() == "printed"
    log = (run.state / "logs" / "KitApp.log").read_text(encoding="utf-8")
    assert "hello-from-print" in log and "hello-from-write" in log
    # Regression: PyInstaller flushes sys.__stdout__ at exit; with it None
    # that raised and the crash reporter filed a report on every exit.
    assert not (run.state / "crashes").exists()
    assert "Traceback" not in log


def test_signed_update_replaces_and_restarts_the_exe(run, built, server):
    exe, key, root = built
    # A copy of the build, so the original stays usable for other tests.
    installed = run.tmp / "installed" / "KitApp"
    installed.parent.mkdir()
    shutil.copy2(exe, installed)
    new_build = exe.read_bytes()  # served as "version 2.0.0"
    manifest = manifest_bytes({
        "app": "KitApp", "version": "2.0.0", "url": server.url("/dl/KitApp-2.0.0"),
        "sha256": hashlib.sha256(new_build).hexdigest(), "size": len(new_build),
        "notes": "", "min_version": "",
    })
    server.serve("/update.json", manifest)
    server.serve("/update.json.sig", sign(key.seed, manifest).hex().encode())
    server.serve("/dl/KitApp-2.0.0", new_build)
    before = os.stat(installed).st_ino

    found, relaunched = run.tmp / "found.txt", run.tmp / "relaunched.txt"
    process = run("update", str(found), str(relaunched), binary=installed)
    assert process.returncode == 0, process.err
    assert found.read_text() == "found 2.0.0"
    for _ in range(300):
        if relaunched.exists() and relaunched.read_text():
            break
        time.sleep(0.1)
    assert relaunched.read_text() == "relaunched old_exists=False"
    assert os.stat(installed).st_ino != before  # a new file, not the one that ran
    assert installed.read_bytes() == new_build
    assert os.access(installed, os.X_OK)
    assert sorted(os.listdir(installed.parent)) == ["KitApp"]
