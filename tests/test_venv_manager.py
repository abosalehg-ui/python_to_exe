"""Tests for planning and inspecting isolated build environments."""

import json
import os
import subprocess

import pytest

from py2exe_gui.core.venv_manager import (
    LOCK_FILE_NAME,
    InstalledChecker,
    delete_env,
    env_dir_for,
    env_exists,
    env_python,
    env_status,
    format_lock,
    freeze_command,
    plan_environment,
    project_requirements,
    python_version,
    quote_command,
    read_pyvenv_version,
    single_install_command,
    write_metadata,
)

PYI = "pyinstaller>=6.0,<7"


def make_project(tmp_path, code="import yaml\n"):
    proj = tmp_path / "My Project"
    proj.mkdir()
    (proj / "main.py").write_text(code)
    return str(proj / "main.py")


def fake_env(env_dir, platform="linux", version="3.12.1"):
    os.makedirs(os.path.dirname(env_python(env_dir, platform)), exist_ok=True)
    with open(env_python(env_dir, platform), "w") as f:
        f.write("")
    with open(os.path.join(env_dir, "pyvenv.cfg"), "w") as f:
        f.write(f"home = /usr/bin\nversion = {version}\n")


# ── Locations ──────────────────────────────────────────────────────────────


def test_env_dir_is_per_project_and_stable(tmp_path):
    a = make_project(tmp_path)
    other = tmp_path / "My Project" / "tool.py"
    other.write_text("")
    root = str(tmp_path / "envs")
    assert env_dir_for(a, root) == env_dir_for(str(other), root)
    name = os.path.basename(env_dir_for(a, root))
    assert name.startswith("My_Project-") and len(name.split("-")[-1]) == 10


def test_same_folder_name_elsewhere_gets_another_env(tmp_path):
    root = str(tmp_path / "envs")
    (tmp_path / "a" / "proj").mkdir(parents=True)
    (tmp_path / "b" / "proj").mkdir(parents=True)
    assert env_dir_for(str(tmp_path / "a" / "proj" / "x.py"), root) != env_dir_for(
        str(tmp_path / "b" / "proj" / "x.py"), root
    )


def test_env_python_per_platform():
    assert env_python("E", "win32") == os.path.join("E", "Scripts", "python.exe")
    assert env_python("E", "linux") == os.path.join("E", "bin", "python")


# ── Requirements ───────────────────────────────────────────────────────────


def test_requirements_from_imports_use_pip_names(tmp_path):
    source = make_project(tmp_path, "import yaml\nimport cv2\nimport os\nimport requests\n")
    req = project_requirements(source)
    assert req.origin == "scan"
    # Ordered by import name (cv2, requests, yaml), mapped to PyPI names.
    assert req.args == ["opencv-python", "requests", "PyYAML"]
    assert req.imports == ["cv2", "requests", "yaml"]


def test_requirements_txt_wins_over_scanning(tmp_path):
    source = make_project(tmp_path)
    reqs = os.path.join(os.path.dirname(source), "requirements.txt")
    open(reqs, "w").write("PyYAML==6.0\n")
    req = project_requirements(source)
    assert (req.origin, req.args) == ("file", ["-r", reqs])


def test_lock_file_wins_over_requirements(tmp_path):
    source = make_project(tmp_path)
    folder = os.path.dirname(source)
    open(os.path.join(folder, "requirements.txt"), "w").write("x\n")
    open(os.path.join(folder, LOCK_FILE_NAME), "w").write("x==1\n")
    assert project_requirements(source).origin == "lock"


# ── Plans ──────────────────────────────────────────────────────────────────


def test_plan_without_uv(tmp_path):
    source = make_project(tmp_path)
    root = str(tmp_path / "envs")
    plan = plan_environment(source, root, "/usr/bin/python3", PYI, platform="linux")
    assert plan.setup[0] == ["/usr/bin/python3", "-m", "venv", plan.env_dir]
    assert plan.setup[1][-1] == PYI
    assert plan.setup[1][:2] == [plan.python, "-m"]
    assert plan.install[-1] == "PyYAML"


def test_plan_with_uv(tmp_path):
    source = make_project(tmp_path)
    plan = plan_environment(source, str(tmp_path / "e"), "py", PYI, uv="/bin/uv",
                            platform="linux")
    assert plan.setup[0] == ["/bin/uv", "venv", "--python", "py", plan.env_dir]
    assert plan.install[:5] == ["/bin/uv", "pip", "install", "--python", plan.python]
    assert single_install_command(plan, "x")[-1] == "x"


def test_existing_env_is_updated_not_recreated(tmp_path):
    source = make_project(tmp_path)
    root = str(tmp_path / "envs")
    fake_env(env_dir_for(source, root))
    plan = plan_environment(source, root, "py", PYI, platform="linux")
    assert not any("venv" in cmd for cmd in plan.setup)
    recreate = plan_environment(source, root, "py", PYI, recreate=True, platform="linux")
    assert recreate.setup[0][1:3] == ["-m", "venv"]


def test_project_without_packages_installs_only_pyinstaller(tmp_path):
    source = make_project(tmp_path, "import os\n")
    plan = plan_environment(source, str(tmp_path / "e"), "py", PYI)
    assert plan.install == []
    assert len(plan.all_commands()) == 2


# ── Lock files ─────────────────────────────────────────────────────────────


def test_format_lock_drops_build_tooling():
    freeze = "PyYAML==6.0.1\npyinstaller==6.22.3\npyinstaller-hooks-contrib==2026.8\n" \
             "altgraph==0.17\n# comment\nrequests==2.32.0\n"
    lock = format_lock(freeze)
    lines = [l for l in lock.splitlines() if not l.startswith("#")]  # noqa: E741
    assert lines == ["PyYAML==6.0.1", "requests==2.32.0"]


def test_freeze_command():
    assert freeze_command("py") == ["py", "-m", "pip", "freeze", "--disable-pip-version-check"]
    assert freeze_command("py", "uv") == ["uv", "pip", "freeze", "--python", "py"]


# ── Inspection ─────────────────────────────────────────────────────────────


def test_status_of_a_missing_env(tmp_path):
    status = env_status(str(tmp_path / "nope"))
    assert status.exists is False


def test_status_reads_version_and_metadata(tmp_path):
    env = str(tmp_path / "env")
    fake_env(env, platform=os.sys.platform)
    write_metadata(env, {"size_bytes": 123, "requirements": ["PyYAML"]})
    assert env_exists(env)
    status = env_status(env, with_size=False)
    assert status.exists and status.python_version == "3.12.1"
    assert status.metadata["size_bytes"] == 123


def test_uv_spells_the_version_differently(tmp_path):
    env = tmp_path / "env"
    env.mkdir()
    (env / "pyvenv.cfg").write_text("home = /x\nimplementation = CPython\nversion_info = 3.11.9\n")
    assert read_pyvenv_version(str(env)) == "3.11.9"


def test_delete_only_inside_the_root(tmp_path):
    root = tmp_path / "envs"
    env = str(root / "proj-abc")
    fake_env(env, platform=os.sys.platform)
    outside = str(tmp_path / "precious")
    fake_env(outside, platform=os.sys.platform)

    assert delete_env(outside, str(root)) is False
    assert os.path.isdir(outside)
    assert delete_env(str(root), str(root)) is False
    assert delete_env(env, str(root)) is True
    assert not os.path.exists(env)


def test_delete_refuses_a_folder_that_is_not_an_env(tmp_path):
    root = tmp_path / "envs"
    (root / "something").mkdir(parents=True)
    assert delete_env(str(root / "something"), str(root)) is False


# ── Asking another interpreter ─────────────────────────────────────────────


class FakeRun:
    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def __call__(self, cmd, **kwargs):
        self.calls.append(cmd)
        asked = cmd[3:]
        payload = {m: self.answers.get(m, False) for m in asked}
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(payload), stderr="")


def test_checker_asks_once_for_everything_prefetched():
    run = FakeRun({"yaml": True})
    check = InstalledChecker("py", runner=run)
    check.prefetch(["yaml", "numpy", "yaml.loader"])
    assert check("yaml") is True and check("numpy") is False
    assert check("yaml.constructor") is True
    assert len(run.calls) == 1


def test_checker_asks_for_unknown_modules_lazily():
    run = FakeRun({"x": True})
    check = InstalledChecker("py", runner=run)
    assert check("x") is True
    assert len(run.calls) == 1
    check.invalidate()
    check("x")
    assert len(run.calls) == 2


def test_checker_survives_a_broken_interpreter():
    def boom(*_a, **_k):
        raise OSError("no such file")

    check = InstalledChecker("missing", runner=boom)
    assert check("yaml") is False


def test_checker_against_the_real_interpreter():
    import sys

    check = InstalledChecker(sys.executable)
    check.prefetch(["json", "definitely_not_a_module_xyz"])
    assert check("json") is True
    assert check("definitely_not_a_module_xyz") is False


def test_python_version_of_this_interpreter():
    import sys

    assert python_version(sys.executable) == ".".join(map(str, sys.version_info[:3]))
    assert python_version("/no/such/python") == ""


@pytest.mark.parametrize(
    "command, expected",
    [
        (["uv", "pip", "install", "pyinstaller>=6.0,<7"], 'uv pip install "pyinstaller>=6.0,<7"'),
        (["C:\\Program Files\\py.exe", "-m", "venv"], '"C:\\Program Files\\py.exe" -m venv'),
        (["a", ""], 'a ""'),
    ],
)
def test_quote_command(command, expected):
    assert quote_command(command) == expected
