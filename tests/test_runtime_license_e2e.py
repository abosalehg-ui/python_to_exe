"""End to end: a real PyInstaller build with the Runtime Kit's licensing on.

One build (a minute or two), then the program is run from a neutral folder
with a valid key, a tampered key, a key for another product and an expired
key, the way a customer's machine would run it: no network, no converter,
nothing but the bundled ``p2e_runtime.json`` and ``p2e_runtime.license``.
The private key is checked to be absent from every file PyInstaller wrote.
"""

import datetime
import os
import subprocess
import sys
import time

import pytest

pytest.importorskip("PyInstaller", reason="PyInstaller not installed")

from py2exe_gui.core.builder import build_pyinstaller_command  # noqa: E402
from py2exe_gui.core.config import BuildConfig, RuntimeKitConfig  # noqa: E402
from py2exe_gui.core.licensing import LicenseRequest, issue, load_or_create_key  # noqa: E402
from py2exe_gui.core.runtime_kit import write_kit  # noqa: E402

pytestmark = pytest.mark.slow

APP = '''
import sys
import time

from p2e_runtime import current_config, license

key = sys.argv[1] if len(sys.argv) > 1 else ""
licensing = current_config().licensing
started = time.perf_counter()
status, info = license.inspect(key, licensing.public_key, licensing.product)
elapsed_ms = (time.perf_counter() - started) * 1000
checked = license.check(key)
print(f"status={status} check={'ok' if checked else 'none'} ms={elapsed_ms:.1f}")
if info is not None:
    print(f"name={info.name} product={info.product} expiry={info.expiry or '-'} "
          f"features={','.join(info.features)}")
sys.exit(0 if checked else 3)
'''


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    root = tmp_path_factory.mktemp("license_e2e")
    project = root / "proj"
    project.mkdir()
    (project / "app.py").write_text(APP, encoding="utf-8")
    key_path = str(root / "config" / "signing" / "license_signing_key.json")
    key, _ = load_or_create_key(key_path)
    config = BuildConfig(
        source=str(project / "app.py"), output_name="LicensedApp",
        output_dir=str(root / "out"),
        runtime_kit=RuntimeKitConfig(licensing=True, license_product="LicensedApp",
                                     license_public_key=key.public_hex),
    )
    os.makedirs(config.output_dir)
    options, errors = write_kit(config)
    assert errors == []
    cmd, error = build_pyinstaller_command(config, extra_options=options)
    assert error is None
    started = time.perf_counter()
    result = subprocess.run(cmd, cwd=config.output_dir, capture_output=True, text=True,
                            timeout=900)
    build_seconds = time.perf_counter() - started
    assert result.returncode == 0, result.stderr[-3000:]
    exe = root / "out" / "dist" / ("LicensedApp.exe" if sys.platform == "win32" else "LicensedApp")
    assert exe.is_file()
    return {"exe": exe, "key": key, "root": root, "build_seconds": build_seconds,
            "config": config}


@pytest.fixture
def run(built, tmp_path):
    neutral = tmp_path / "neutral"
    neutral.mkdir()

    def start(*args):
        env = {k: v for k, v in os.environ.items() if not k.lower().endswith("_proxy")}
        process = subprocess.run([str(built["exe"]), *args], cwd=str(neutral),
                                 capture_output=True, text=True, timeout=120, env=env)
        return process

    return start


def valid_key(built, **fields):
    request = LicenseRequest(name="Sara", email="sara@example.com", product="LicensedApp",
                             features=("pro",))
    for name, value in fields.items():
        setattr(request, name, value)
    return issue(request, built["key"], today=datetime.date(2000, 1, 1))


def test_valid_key_is_accepted(run, built):
    process = run(valid_key(built))
    assert process.returncode == 0, process.stderr
    assert "status=valid check=ok" in process.stdout
    assert "name=Sara product=LicensedApp expiry=- features=pro" in process.stdout
    ms = float(process.stdout.split("ms=")[1].split()[0])
    built["verify_ms"] = ms
    assert ms < 2000  # pure-Python Ed25519 in a frozen app


def test_valid_key_typed_sloppily(run, built):
    key = valid_key(built).lower().replace("-", " ")
    assert run(key).returncode == 0


def test_tampered_key_is_refused(run, built):
    key = valid_key(built)
    letters = list(key.replace("-", ""))
    letters[-3] = "A" if letters[-3] != "A" else "B"
    process = run("".join(letters))
    assert process.returncode == 3
    assert "status=invalid check=none" in process.stdout


def test_garbage_is_refused_without_a_traceback(run):
    for garbage in ("", "not-a-key", "ABCDE-FGHIJ-KLMNO"):
        process = run(garbage)
        assert process.returncode == 3 and "Traceback" not in process.stderr
        assert "status=invalid" in process.stdout


def test_other_products_key_is_refused(run, built):
    process = run(valid_key(built, product="OtherApp"))
    assert process.returncode == 3
    assert "status=wrong_product check=none" in process.stdout
    assert "product=OtherApp" in process.stdout


def test_expired_key_is_refused(run, built):
    process = run(valid_key(built, expiry="2001-01-01"))
    assert process.returncode == 3
    assert "status=expired check=none" in process.stdout and "expiry=2001-01-01" in process.stdout


def test_another_developers_key_is_refused(run, built, tmp_path):
    other, _ = load_or_create_key(str(tmp_path / "other.json"))
    request = LicenseRequest(name="Sara", product="LicensedApp")
    process = run(issue(request, other))
    assert process.returncode == 3 and "status=invalid" in process.stdout


def test_private_key_is_in_no_file_pyinstaller_wrote(built):
    private_hex = built["key"].seed.hex().encode()
    seed = built["key"].seed
    public = built["key"].public_hex.encode()
    found_public = False
    scanned = 0
    for folder in (built["root"] / "out" / "dist", built["root"] / "out" / "build"):
        for dirpath, _dirs, names in os.walk(folder):
            for name in names:
                path = os.path.join(dirpath, name)
                if os.path.islink(path):
                    continue
                with open(path, "rb") as f:
                    blob = f.read()
                scanned += 1
                assert private_hex not in blob and seed not in blob, path
                if public in blob:
                    found_public = True
    assert scanned > 0 and found_public  # the public key *is* embedded


def test_report_measurements(built, capsys):
    """Not an assertion: prints the numbers the PR description quotes."""
    size = built["exe"].stat().st_size
    key = valid_key(built)
    with capsys.disabled():
        print(f"\n[license e2e] build {built['build_seconds']:.1f}s, "
              f"exe {size / 1e6:.1f} MB, key {len(key)} chars "
              f"({len(key.replace('-', ''))} letters), verify in app "
              f"{built.get('verify_ms', float('nan')):.1f} ms")
