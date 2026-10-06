"""The command line: parsing, exit codes, consent, and every command.

Runs without PyQt5 (the core CI job has none), and one test proves the CLI
never imports it.
"""

import io
import json
import os
import shutil
import subprocess
import sys

import pytest

from py2exe_gui import cli
from py2exe_gui.core.project_file import load_project, save_project
from py2exe_gui.strings import Ar, En

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = "ghp_" + "C" * 36


class Run:
    def __init__(self, code, out, err):
        self.code, self.out, self.err = code, out, err


def run(*argv, yes=False, interactive=False, answers=()):
    """Run the CLI in-process with a scripted console."""
    out, err = io.StringIO(), io.StringIO()
    replies = list(answers)
    console = cli.Console(yes=yes, interactive=interactive, out=out, err=err,
                          ask=lambda _prompt: replies.pop(0) if replies else "",
                          secret=lambda _prompt: "")
    code = cli.main(["--lang", "en", *argv], console)
    return Run(code, out.getvalue(), err.getvalue())


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "ENVS_ROOT", str(tmp_path / "envs"))
    monkeypatch.setattr(cli, "SIGNING_KEY_FILE", str(tmp_path / "key" / "k.json"))
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def script(tmp_path):
    path = tmp_path / "app.py"
    path.write_text("print('hello')\n")
    return path


@pytest.fixture
def project(script, tmp_path):
    assert run("init", str(script)).code == cli.EXIT_OK
    return tmp_path / "p2e.toml"


def edit(path, change):
    loaded = load_project(str(path))
    change(loaded.project)
    save_project(loaded.project, str(path))


# ── Parsing and exit codes ────────────────────────────────────────────────


def test_help_lists_the_commands_and_the_exit_codes(capsys):
    assert cli.main(["--lang", "en", "--help"]) == 0
    out = capsys.readouterr().out
    for command in cli.COMMANDS:
        assert command in out
    for code in ("0", "1", "2", "3", "4", "5", "130"):
        assert f"\n  {code} " in out


def test_every_command_help_shows_the_exit_codes(capsys):
    for command in cli.COMMANDS:
        argv = ["--lang", "en", command, "--help"]
        assert cli.main(argv) == 0
        assert "exit codes:" in capsys.readouterr().out


def test_exit_code_constants_match_the_documentation():
    documented = {cli.EXIT_OK: "success", cli.EXIT_FAILED: "failed",
                  cli.EXIT_USAGE: "invalid arguments", cli.EXIT_PROJECT: "project file",
                  cli.EXIT_CONSENT: "consent", cli.EXIT_TOOL: "tool",
                  cli.EXIT_INTERRUPTED: "interrupted"}
    for code, word in documented.items():
        line = next(line for line in En.CLI_EXIT_CODES.splitlines()
                    if line.strip().startswith(f"{code} "))
        assert word in line
        assert any(line.strip().startswith(f"{code} ") for line in Ar.CLI_EXIT_CODES.splitlines())
    readme = open(os.path.join(ROOT, "README_EN.md"), encoding="utf-8").read()
    assert "| 130 |" in readme and "| 4 |" in readme


def test_usage_errors(capsys):
    assert cli.main(["--lang", "en"]) == cli.EXIT_USAGE  # no command
    assert cli.main(["--lang", "en", "explode"]) == cli.EXIT_USAGE
    assert cli.main(["--lang", "en", "env", "wipe"]) == cli.EXIT_USAGE
    assert cli.main(["--lang", "en", "release", "--bump", "x"]) == cli.EXIT_USAGE
    assert cli.main(["--lang", "en", "release", "--bump", "patch",
                     "--set-version", "1.0.0"]) == cli.EXIT_USAGE
    assert cli.main(["--version"]) == 0
    assert "py2exe-gui" in capsys.readouterr().out


def test_is_cli_invocation():
    assert not cli.is_cli_invocation([])
    assert cli.is_cli_invocation(["build"])
    assert cli.is_cli_invocation(["--help"])
    assert cli.is_cli_invocation(["--lang", "ar", "doctor"])
    assert not cli.is_cli_invocation(["my_project/p2e.toml"])


def test_language_selection(monkeypatch, tmp_path):
    assert cli._requested_language(["--lang", "ar"]) == "ar"
    assert cli._requested_language(["--lang=en"]) == "en"
    monkeypatch.setenv(cli.LANG_ENV, "ar")
    assert cli._requested_language([]) == "ar"
    monkeypatch.delenv(cli.LANG_ENV)
    settings = tmp_path / "s.json"
    settings.write_text(json.dumps({"locale": "ar"}))
    monkeypatch.setattr("py2exe_gui.constants.SETTINGS_FILE", str(settings))
    assert cli._requested_language([]) == "ar"
    monkeypatch.setattr("py2exe_gui.constants.SETTINGS_FILE", str(tmp_path / "none.json"))
    assert cli._requested_language([]) == "en"


def test_arabic_output(script):
    out, err = io.StringIO(), io.StringIO()
    console = cli.Console(out=out, err=err, interactive=False)
    assert cli.main(["--lang", "ar", "init", str(script)], console) == 0
    assert "أُنشئ" in out.getvalue()


def test_the_cli_never_imports_pyqt5(tmp_path, script):
    """The headless path works where PyQt5 cannot even be imported."""
    code = (
        "import sys; sys.modules['PyQt5'] = None\n"
        "from py2exe_gui.app import main\n"
        f"rc = main(['--lang', 'en', 'init', {str(script)!r}, '--project', "
        f"{str(tmp_path / 'x.toml')!r}])\n"
        "assert not any(m == 'PyQt5' or m.startswith('PyQt5.') for m in sys.modules "
        "if sys.modules[m] is not None)\n"
        "sys.exit(rc)\n"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True,
                            text=True, env={**os.environ, "PYTHONPATH": ROOT})
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "x.toml").is_file()


# ── init ──────────────────────────────────────────────────────────────────


def test_init_creates_a_project_and_refuses_to_overwrite(script, tmp_path):
    r = run("init", str(script), "--name", "Hello", "--set-version", "0.3.0")
    assert r.code == 0 and "Created" in r.out
    loaded = load_project(str(tmp_path / "p2e.toml"))
    assert loaded.project.name == "Hello" and loaded.project.version == "0.3.0"
    assert loaded.project.build.source == str(script)
    assert run("init", str(script)).code == cli.EXIT_PROJECT
    assert run("init", str(script), "--force").code == 0
    assert load_project(str(tmp_path / "p2e.toml")).project.version == "1.0.0"


def test_init_errors(tmp_path, script):
    assert run("init", str(tmp_path / "missing.py")).code == cli.EXIT_USAGE
    (tmp_path / "notes.txt").write_text("x")
    assert run("init", str(tmp_path / "notes.txt")).code == cli.EXIT_USAGE
    assert run("init", str(script), "--set-version", "1.0").code == cli.EXIT_USAGE


def test_init_reads_the_github_remote(script, tmp_path):
    if shutil.which("git") is None:
        pytest.skip("git not installed")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "remote", "add", "origin", "git@github.com:me/tool.git"],
                   cwd=tmp_path, check=True)
    assert run("init", str(script)).code == 0
    assert load_project(str(tmp_path / "p2e.toml")).project.release.repository == "me/tool"


# ── Project file errors ───────────────────────────────────────────────────


def test_missing_and_invalid_projects(tmp_path):
    r = run("doctor")
    assert r.code == cli.EXIT_PROJECT and "No project file" in r.err
    (tmp_path / "p2e.toml").write_text('schema = 1\n[signing]\ncert_password = "x"\n')
    r = run("doctor")
    assert r.code == cli.EXIT_PROJECT and "password" in r.err.lower()
    (tmp_path / "bad.toml").write_text('schema = 1\n[build]\npython = "/usr/bin/python3"\n')
    assert run("build", "--project", "bad.toml", "--yes").code == cli.EXIT_PROJECT


def test_project_warnings_go_to_stderr(project, tmp_path):
    text = (tmp_path / "p2e.toml").read_text().replace("[build]\n", "[build]\ncolour = 1\n")
    (tmp_path / "p2e.toml").write_text(text)
    r = run("doctor")
    assert "colour" in r.err


# ── doctor ────────────────────────────────────────────────────────────────


def test_doctor_ok_and_json(project):
    r = run("doctor")
    assert r.code == 0 and "Readiness" in r.out
    r = run("doctor", "--json")
    data = json.loads(r.out)
    assert data["errors"] == 0 and data["score"] <= 100
    assert data["source"].endswith("app.py") and data["version_mismatches"] == []


def test_doctor_errors_exit_one(project, script):
    script.write_text("def broken(:\n")
    r = run("doctor")
    assert r.code == cli.EXIT_FAILED and "syntax_error" in r.out
    data = json.loads(run("doctor", "--json").out)
    assert data["errors"] == 1 and data["findings"][0]["code"] == "syntax_error"


def test_doctor_reports_version_mismatches(project):
    edit(project, lambda p: setattr(p.installer, "app_version", "9.9.9"))
    r = run("doctor")
    assert "installer.app_version" in r.out
    data = json.loads(run("doctor", "--json").out)
    assert data["version_mismatches"][0]["field"] == "installer.app_version"


def test_doctor_with_a_missing_isolated_env(project):
    edit(project, lambda p: setattr(p.build, "isolated_env", True))
    r = run("doctor")
    assert "isolated environment does not exist" in r.out


# ── build ─────────────────────────────────────────────────────────────────


class FakeProcess:
    def __init__(self, lines, code, on_finish=None):
        self.stdout = iter(lines)
        self._code = code
        self._on_finish = on_finish

    def wait(self):
        if self._on_finish:
            self._on_finish()
        return self._code

    def terminate(self):
        pass


def fake_pyinstaller(monkeypatch, tmp_path, code=0, record=None):
    lines = ["123 INFO: PyInstaller: 6.0\n", "456 INFO: Analyzing base_library.zip\n",
             "789 INFO: Building PYZ (ZlibArchive)\n", "800 INFO: Building EXE from EXE-00.toc\n",
             "900 INFO: Build complete!\n"]

    def finish():
        dist = tmp_path / "dist"
        dist.mkdir(exist_ok=True)
        (dist / "app.exe").write_bytes(b"MZ" * 2048)

    def popen(command, **kwargs):
        if record is not None:
            record.append((command, kwargs))
        return FakeProcess(lines, code, finish if code == 0 else None)

    monkeypatch.setattr("py2exe_gui.core.build_runner.subprocess.Popen", popen)
    monkeypatch.setattr(cli.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a[0], 0, "6.0", ""))


def test_build_streams_with_stage_markers(project, tmp_path, monkeypatch):
    calls = []
    fake_pyinstaller(monkeypatch, tmp_path, record=calls)
    r = run("build")
    assert r.code == 0, r.err
    assert "==> [Doctor check] 0%" in r.out
    assert "==> [Analyzing imports] 5%" in r.out
    assert "==> [Building PYZ archive] 62%" in r.out
    assert "==> [Building executable] 82%" in r.out
    assert "Build complete!" in r.out
    assert "dist" in r.out.splitlines()[-1]
    command, kwargs = calls[0]
    assert command[1:3] == ["-m", "PyInstaller"] and command[-1].endswith("app.py")
    # Version Info from the project became a --version-file, removed afterwards.
    version_file = command[command.index("--version-file") + 1]
    assert not os.path.exists(version_file)


def test_build_failure_exits_one(project, tmp_path, monkeypatch):
    fake_pyinstaller(monkeypatch, tmp_path, code=1)
    r = run("build")
    assert r.code == cli.EXIT_FAILED


def test_build_strict_stops_on_doctor_errors(project, script, tmp_path, monkeypatch):
    calls = []
    fake_pyinstaller(monkeypatch, tmp_path, record=calls)
    script.write_text("def broken(:\n")
    assert run("build", "--strict").code == cli.EXIT_FAILED
    assert calls == []
    # Without --strict the doctor reports and the build still runs.
    assert run("build").code == 0 and calls


def test_dangerous_project_settings_need_consent(project, tmp_path, monkeypatch):
    fake_pyinstaller(monkeypatch, tmp_path)
    edit(project, lambda p: setattr(p.build, "extra_args", "--runtime-hook evil.py"))
    r = run("build")
    assert r.code == cli.EXIT_CONSENT and "--yes" in r.err and "--runtime-hook" in r.out
    assert run("build", interactive=True, answers=["n"]).code == cli.EXIT_CONSENT
    assert run("build", interactive=True, answers=["y"]).code == 0
    r = run("build", yes=True)
    assert r.code == 0 and "Agreed in advance" in r.out


def test_upx_dir_counts_as_dangerous(project, tmp_path, monkeypatch):
    fake_pyinstaller(monkeypatch, tmp_path)
    edit(project, lambda p: (setattr(p.build, "upx", True), setattr(p.build, "upx_dir", "/x")))
    r = run("build")
    assert r.code == cli.EXIT_CONSENT and "--upx-dir" in r.out


def test_foreign_update_key_needs_consent(project, tmp_path, monkeypatch):
    fake_pyinstaller(monkeypatch, tmp_path)

    def foreign(p):
        p.build.runtime_kit.updater = True
        p.build.runtime_kit.update_public_key = "ab" * 32
        p.build.runtime_kit.update_url = "https://example.com/update.json"
    edit(project, foreign)
    r = run("build")
    assert r.code == cli.EXIT_CONSENT


def test_missing_pyinstaller_asks_before_installing(project, tmp_path, monkeypatch):
    fake_pyinstaller(monkeypatch, tmp_path)

    def no_pyinstaller(*_a, **_k):
        raise subprocess.CalledProcessError(1, "x")

    monkeypatch.setattr(cli.subprocess, "run", no_pyinstaller)
    r = run("build")
    assert r.code == cli.EXIT_CONSENT and "PyPI" in r.out
    installs = []
    monkeypatch.setattr(cli, "_run_streaming", lambda cmd, console, cwd="": installs.append(cmd)
                        or 0)
    assert run("build", yes=True).code == 0
    assert installs[0][1:4] == ["-m", "pip", "install"]
    monkeypatch.setattr(cli, "_run_streaming", lambda *a, **k: 1)
    assert run("build", yes=True).code == cli.EXIT_TOOL


def test_build_with_runtime_kit_errors(project, tmp_path, monkeypatch):
    fake_pyinstaller(monkeypatch, tmp_path)
    edit(project, lambda p: setattr(p.build.runtime_kit, "updater", True))
    r = run("build", yes=True)
    assert r.code == cli.EXIT_FAILED


def test_isolated_env_creation_asks_first(project, tmp_path, monkeypatch):
    fake_pyinstaller(monkeypatch, tmp_path)
    edit(project, lambda p: setattr(p.build, "isolated_env", True))
    r = run("build")
    assert r.code == cli.EXIT_CONSENT and "venv" in r.out


# ── size ──────────────────────────────────────────────────────────────────


def test_size_without_a_build(project):
    assert run("size").code == cli.EXIT_FAILED


def test_size_of_the_last_build(tmp_path):
    from tests.test_size_analyzer import make_build

    make_build(tmp_path)
    folder = tmp_path / "proj"
    target = str(folder / "p2e.toml")
    assert run("init", str(folder / "app.py"), "--project", target).code == 0
    r = run("size", "--project", target)
    assert r.code == 0, r.err
    assert "numpy" in r.out and "%" in r.out
    data = json.loads(run("size", "--project", target, "--json").out)
    assert data["output_bytes"] > 0 and "numpy" in data["groups"]
    assert data["largest_files"][0]["bytes"] > 0


# ── env ───────────────────────────────────────────────────────────────────


def fake_env(tmp_path, project_file):
    from py2exe_gui.core.venv_manager import env_dir_for, env_python

    source = load_project(str(project_file)).project.build.source
    env = env_dir_for(source, str(tmp_path / "envs"))
    os.makedirs(os.path.dirname(env_python(env)), exist_ok=True)
    open(env_python(env), "w").close()
    with open(os.path.join(env, "pyvenv.cfg"), "w") as f:
        f.write("version = 3.12.0\n")
    return env


def test_env_create_needs_consent_and_runs_the_plan(project, monkeypatch):
    r = run("env", "create")
    assert r.code == cli.EXIT_CONSENT and "venv" in r.out
    commands = []
    monkeypatch.setattr(cli, "_run_streaming",
                        lambda cmd, console, cwd="": commands.append(cmd) or 0)
    r = run("env", "create", "--yes")
    assert r.code == 0, r.err
    assert commands[0][1:3] == ["-m", "venv"] or commands[0][1] == "venv"
    assert any("pyinstaller" in " ".join(c) for c in commands)


def test_env_create_failures(project, monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "_run_streaming", lambda *a, **k: 1)
    assert run("env", "create", "--yes").code == cli.EXIT_FAILED
    r = run("env", "create", "--yes", "--base-python", str(tmp_path / "nope"))
    assert r.code == cli.EXIT_TOOL


def test_env_lock_and_delete(project, tmp_path, monkeypatch):
    assert run("env", "lock").code == cli.EXIT_FAILED  # no environment yet
    env = fake_env(tmp_path, project)
    monkeypatch.setattr(cli.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(
        a[0], 0, "PyYAML==6.0.1\npyinstaller==6.0\n", ""))
    r = run("env", "lock")
    assert r.code == 0
    lock = (tmp_path / "p2e-build.lock").read_text()
    assert "PyYAML==6.0.1" in lock and "pyinstaller" not in lock
    assert run("env", "delete").code == cli.EXIT_CONSENT
    assert os.path.isdir(env)
    assert run("env", "delete", "--yes").code == 0
    assert not os.path.exists(env)


def test_env_lock_failure(project, tmp_path, monkeypatch):
    fake_env(tmp_path, project)
    monkeypatch.setattr(cli.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(
        a[0], 1, "", "boom"))
    assert run("env", "lock").code == cli.EXIT_FAILED


# ── release ───────────────────────────────────────────────────────────────


@pytest.fixture
def repo_project(project, tmp_path, monkeypatch):
    if shutil.which("git") is None:
        pytest.skip("git not installed")
    for args in (["init", "-q", "-b", "main"], ["config", "user.name", "T"],
                 ["config", "user.email", "t@example.com"], ["config", "commit.gpgsign", "false"],
                 ["config", "tag.gpgsign", "false"]):
        subprocess.run(["git", *args], cwd=tmp_path, check=True)
    (tmp_path / ".gitignore").write_text("dist/\nbuild/\nrelease/\nenvs/\nkey/\n")
    edit(project, lambda p: setattr(p.release, "repository", "me/app"))
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "feat: first"], cwd=tmp_path, check=True)

    def fake_build(ctx):
        from py2exe_gui.core.build_runner import BuildOutcome

        dist = tmp_path / "dist"
        dist.mkdir(exist_ok=True)
        (dist / "app.exe").write_bytes(b"MZ" + ctx.version.encode() * 64)
        return BuildOutcome(True, 0)

    monkeypatch.setattr("py2exe_gui.core.release.pipeline.default_build", fake_build)
    return project


def test_release_dry_run_changes_nothing(repo_project, tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", TOKEN)
    before = repo_project.read_text()
    r = run("release", "--bump", "minor", "--dry-run")
    assert r.code == 0, r.err
    assert "Release plan for 1.1.0" in r.out and "Dry run only" in r.out
    assert "v1.1.0" in r.out and "Files uploaded" in r.out
    assert repo_project.read_text() == before
    assert not (tmp_path / "release").exists()
    tags = subprocess.run(["git", "tag"], cwd=tmp_path, capture_output=True, text=True).stdout
    assert tags == ""


def test_release_requires_consent_when_not_interactive(repo_project, tmp_path):
    os.environ["GITHUB_TOKEN"] = TOKEN
    try:
        r = run("release", "--set-version", "1.0.1", "--no-publish")
    finally:
        del os.environ["GITHUB_TOKEN"]
    assert r.code == cli.EXIT_CONSENT
    assert not (tmp_path / "release" / "1.0.1").exists()


def test_release_end_to_end_against_the_fake_api(repo_project, tmp_path, monkeypatch):
    from tests.fake_github import FakeGitHub

    monkeypatch.setattr(cli, "ALLOW_INSECURE_LOCALHOST", True)
    monkeypatch.setenv("GITHUB_TOKEN", TOKEN)
    notes = tmp_path / "notes.md"
    notes.write_text("## Hand-written notes\n", encoding="utf-8")
    with FakeGitHub(TOKEN) as fake:
        r = run("release", "--bump", "patch", "--notes", str(notes), "--api-url", fake.url,
                "--yes")
        uploads = sorted(fake.uploads)
        body = fake.releases[0]["body"] if fake.releases else ""
    assert r.code == 0, r.out + r.err
    assert uploads == ["SHA256SUMS.txt", "app-1.0.1-portable.zip", "app-1.0.1.exe"]
    assert body == "## Hand-written notes\n"
    assert TOKEN not in r.out and TOKEN not in r.err
    assert "Released 1.0.1" in r.out
    assert load_project(str(repo_project)).project.version == "1.0.1"


def test_release_errors(repo_project, tmp_path):
    assert run("release", "--set-version", "2.0", "--dry-run").code == cli.EXIT_USAGE
    assert run("release", "--notes", str(tmp_path / "missing.md"),
               "--dry-run").code == cli.EXIT_USAGE
    r = run("release", "--set-version", "1.0.1", "--dry-run")
    assert r.code == cli.EXIT_FAILED and "no GitHub token" in r.out  # publish needs a token
    assert run("release", "--set-version", "1.0.1", "--dry-run", "--no-publish").code == 0


def test_release_with_doctor_errors_is_blocked(repo_project, script):
    script.write_text("def broken(:\n")
    r = run("release", "--set-version", "1.0.1", "--dry-run", "--no-publish")
    assert r.code == cli.EXIT_FAILED and "syntax_error" in r.out
    r = run("release", "--set-version", "1.0.1", "--dry-run", "--no-publish",
            "--allow-doctor-errors")
    assert r.code == 0


def test_release_bump_needs_a_valid_current_version(project):
    edit(project, lambda p: setattr(p, "version", "not-a-version"))
    assert run("release", "--bump", "patch", "--dry-run").code == cli.EXIT_USAGE


def test_release_with_missing_isolated_env(project):
    edit(project, lambda p: setattr(p.build, "isolated_env", True))
    assert run("release", "--dry-run", "--no-publish").code == cli.EXIT_TOOL


def test_keyboard_interrupt(monkeypatch, project):
    def interrupted(*_a):
        raise KeyboardInterrupt

    monkeypatch.setitem(cli.HANDLERS, "doctor", interrupted)
    assert run("doctor").code == cli.EXIT_INTERRUPTED


def test_console_defaults():
    console = cli.Console(interactive=False)
    assert console.password("x") == ""
    assert cli.Console(interactive=True, secret=lambda _p: "pw").password("x") == "pw"


def test_sign_password_comes_from_the_environment_not_a_flag():
    parser = cli.build_parser()
    release = parser._subparsers._group_actions[0].choices["release"]
    options = {o for a in release._actions for o in a.option_strings}
    assert not any("password" in o or "token" in o for o in options)
    assert cli.SIGN_PASSWORD_ENV == "P2E_SIGN_PASSWORD"


def test_project_untouched_by_doctor(project):
    before = project.read_text()
    run("doctor")
    assert project.read_text() == before
