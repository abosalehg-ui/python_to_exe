"""The GitHub Actions workflow generator: shape, jobs, caching, secrets.

The YAML is parsed back with PyYAML (a dev dependency), the jobs and steps
are checked by name, and one test pushes secret-looking values through every
input the generator has — the environment, the project, the keyring — and
checks that none of them reaches the output. ``actionlint`` runs when it is
installed and is skipped cleanly otherwise.
"""

import os
import re
import shlex
import shutil
import subprocess

import pytest
import yaml

from py2exe_gui import cli
from py2exe_gui.core.ci_generator import (
    ACTIONS,
    DEFAULT_PYTHON,
    DEFAULT_TOOL_REQUIREMENT,
    RUNNERS,
    SECRET_NAMES,
    WORKFLOW_RELATIVE,
    CiOptions,
    _ps,
    _sh,
    formats_by_runner,
    options_for,
    referenced_secrets,
    render_workflow,
    repo_root,
    workflow_path,
    write_workflow,
)
from py2exe_gui.core.project_file import ProjectConfig, load_project, save_project
from tests.test_cli import run

# Realistic-looking secrets. None of them may ever appear in a workflow.
SECRET_VALUES = {
    "GITHUB_TOKEN": "ghp_" + "Q" * 36,
    "P2E_SIGN_PASSWORD": "pfx-pass-Sup3rSecret!",
    "P2E_MACOS_SIGN_IDENTITY": "Developer ID Application: Example Corp (ABCDE12345)",
    "WINDOWS_CERT_BASE64": "MIIKcQIBAzCCCjcGCSqGSIb3DQEHAaCCCigEggokMIIKIDCCBNcGCSqGSIb3",
    "WINDOWS_CERT_PASSWORD": "cert-password-77",
    "MACOS_NOTARY_PASSWORD": "abcd-efgh-ijkl-mnop",
    "MACOS_NOTARY_APPLE_ID": "dev@example.com",
    "MACOS_NOTARY_TEAM_ID": "ABCDE12345",
    "MACOS_CERT_BASE64": "MIIJkQIBAzCCCVcGCSqGSIb3DQEHAaCCCUgEggl",
    "MACOS_CERT_PASSWORD": "p12-password-99",
}


def project_in(tmp_path, **kwargs):
    root = tmp_path / "repo"
    root.mkdir(exist_ok=True)
    (root / "app.py").write_text("print('hi')\n")
    project = ProjectConfig(name="My App", version="1.2.3")
    project.build.source = str(root / "app.py")
    project.build.output_name = "myapp"
    project.build.output_dir = str(root / "dist")
    project.release.repository = "me/my-app"
    for key, value in kwargs.items():
        section, name = key.split("__")
        setattr(getattr(project, section), name, value)
    path = root / "p2e.toml"
    save_project(project, str(path))
    return load_project(str(path)).project, str(path), str(root)


def full_options(**overrides):
    values = dict(app_name="My App", requirements_rel="requirements.txt", sign_windows=True,
                  cert_path_rel="certs/app.pfx", notarize_macos=True, engine="nuitka",
                  formats=["appimage", "deb", "dmg"], draft=True, prerelease=True,
                  allow_doctor_errors=True)
    values.update(overrides)
    return CiOptions(**values)


def steps_of(doc, job):
    return doc["jobs"][job]["steps"]


def step_names(doc, job):
    return [s.get("name") or s.get("uses") for s in steps_of(doc, job)]


def named(doc, job, fragment):
    """The step of ``job`` whose name holds ``fragment``."""
    return next(s for s in steps_of(doc, job) if fragment in s.get("name", ""))


# ── Shape ─────────────────────────────────────────────────────────────────


def test_workflow_parses_and_has_both_jobs():
    doc = yaml.safe_load(render_workflow(CiOptions()))
    assert doc["name"] == "p2e release"
    assert set(doc["jobs"]) == {"build", "release"}
    assert doc["on"]["push"]["tags"] == ["v*"] and doc["on"]["push"]["branches"] == ["main"]
    assert "pull_request" in doc["on"] and "workflow_dispatch" in doc["on"]
    assert doc["permissions"] == {"contents": "read"}


def test_build_matrix_covers_the_three_runners():
    doc = yaml.safe_load(render_workflow(CiOptions()))
    build = doc["jobs"]["build"]
    assert build["strategy"]["matrix"]["os"] == [r for r, _ in RUNNERS]
    assert build["strategy"]["fail-fast"] is False
    assert build["runs-on"] == "${{ matrix.os }}"


def test_build_steps_install_cache_run_and_upload():
    doc = yaml.safe_load(render_workflow(CiOptions(requirements_rel="requirements.txt")))
    names = step_names(doc, "build")
    assert names[0] == ACTIONS["checkout"]
    setup = steps_of(doc, "build")[1]
    assert setup["uses"] == ACTIONS["setup-python"]
    assert setup["with"]["python-version"] == DEFAULT_PYTHON
    assert setup["with"]["cache"] == "pip"
    assert setup["with"]["cache-dependency-path"].split() == ["p2e.toml", "requirements.txt"]
    cache = steps_of(doc, "build")[2]
    assert cache["uses"] == ACTIONS["cache"] and "build" in cache["with"]["path"].split()
    assert "hashFiles('p2e.toml', 'requirements.txt')" in cache["with"]["key"]
    install = named(doc, "build", "Install Python to EXE")
    assert f"--no-deps '{DEFAULT_TOOL_REQUIREMENT}'" in install["run"]
    assert '"pyinstaller>=6.0"' in install["run"] and "nuitka" not in install["run"]
    release = named(doc, "build", "py2exe-gui release")
    assert release["run"] == ("py2exe-gui --lang en release --project 'p2e.toml' --yes "
                              '--no-tag --no-publish --allow-downloads')
    upload = steps_of(doc, "build")[-1]
    assert upload["uses"] == ACTIONS["upload"]
    assert upload["with"]["path"] == "release"
    assert upload["with"]["name"] == "app-${{ runner.os }}"
    assert upload["with"]["if-no-files-found"] == "error"
    assert checked_out_full_history(doc)


def checked_out_full_history(doc):
    return steps_of(doc, "build")[0]["with"]["fetch-depth"] == 0


def test_nuitka_projects_install_nuitka_and_cache_its_folders():
    doc = yaml.safe_load(render_workflow(CiOptions(engine="nuitka")))
    install = named(doc, "build", "Install Python to EXE")
    assert '"nuitka[onefile]>=4.2,<5"' in install["run"]
    cache = steps_of(doc, "build")[2]
    assert "~/.cache/Nuitka" in cache["with"]["path"]
    assert doc["env"]["NUITKA_UPDATE_CHECK"] == "never"
    assert cache["with"]["key"].startswith("p2e-nuitka-")


def test_release_job_runs_on_tags_only_and_creates_the_release():
    doc = yaml.safe_load(render_workflow(full_options()))
    release = doc["jobs"]["release"]
    assert release["if"] == "startsWith(github.ref, 'refs/tags/v')"
    assert release["needs"] == "build"
    assert release["permissions"] == {"contents": "write"}
    assert steps_of(doc, "release")[0]["uses"] == ACTIONS["download"]
    create = steps_of(doc, "release")[1]
    assert create["env"]["GH_TOKEN"] == "${{ github.token }}"
    run = create["run"]
    assert 'gh release create "$GITHUB_REF_NAME"' in run
    assert "--verify-tag" in run and "--draft" in run and "--prerelease" in run
    assert 'cat artifacts/*/*/SHA256SUMS.txt' in run
    assert "RELEASE_NOTES.md" in run and "'*.iss'" in run
    plain = yaml.safe_load(render_workflow(CiOptions()))
    assert "--draft" not in steps_of(plain, "release")[1]["run"]


@pytest.mark.parametrize("text", ["$(id)", "a'b", "`id`", "$HOME x", 'say "hi"', "plain"])
def test_sh_quotes_so_the_shell_expands_nothing(text):
    """A single-quoted word comes back verbatim from a POSIX shell."""
    assert shlex.split(_sh(text)) == [text]


def test_ps_quotes_a_powershell_literal():
    assert _ps("a'b$(id)") == "'a''b$(id)'"


def test_hostile_app_name_never_reaches_a_run_line_unquoted():
    name = 'Evil" $(id) `id` $HOME'
    text = render_workflow(full_options(app_name=name))
    doc = yaml.safe_load(text)
    for job in ("build", "release"):
        for step in steps_of(doc, job):
            assert name not in step.get("run", "")
    create = steps_of(doc, "release")[1]
    assert create["env"]["APP_TITLE"] == name
    assert '--title "$APP_TITLE $GITHUB_REF_NAME"' in create["run"]
    # The hostile text is only ever inside single quotes on a run: line.
    for line in text.splitlines():
        if "$(id)" in line and "run:" in line:
            raise AssertionError(line)


def test_custom_tag_prefix_and_branch():
    doc = yaml.safe_load(render_workflow(CiOptions(tag_prefix="release-", branch="develop")))
    assert doc["on"]["push"]["tags"] == ["release-*"]
    assert doc["on"]["push"]["branches"] == ["develop"]
    assert doc["jobs"]["release"]["if"] == "startsWith(github.ref, 'refs/tags/release-')"


def test_signing_and_notarization_steps_appear_only_when_asked():
    plain = yaml.safe_load(render_workflow(CiOptions()))
    names = " ".join(step_names(plain, "build"))
    assert "certificate" not in names and "Notarize" not in names
    assert referenced_secrets(render_workflow(CiOptions())) == []

    text = render_workflow(full_options())
    doc = yaml.safe_load(text)
    names = step_names(doc, "build")
    windows = named(doc, "build", "Windows signing certificate")
    assert windows["if"] == "runner.os == 'Windows' && github.event_name != 'pull_request'"
    assert windows["shell"] == "pwsh"
    assert windows["env"] == {"CERT_BASE64": "${{ secrets.WINDOWS_CERT_BASE64 }}"}
    assert "$target = 'certs/app.pfx'" in windows["run"]
    mac = named(doc, "build", "macOS signing certificate")
    assert mac["if"] == "runner.os == 'macOS' && github.event_name != 'pull_request'"
    assert "security import" in mac["run"]
    release = named(doc, "build", "py2exe-gui release")
    assert release["env"] == {"P2E_SIGN_PASSWORD": "${{ secrets.WINDOWS_CERT_PASSWORD }}",
                              "P2E_MACOS_SIGN_IDENTITY": "${{ secrets.MACOS_SIGN_IDENTITY }}"}
    assert "--allow-doctor-errors" in release["run"]
    notarize = named(doc, "build", "Notarize")
    assert "xcrun notarytool submit" in notarize["run"] and "stapler staple" in notarize["run"]
    assert names.index(mac["name"]) < names.index(release["name"]) < names.index(notarize["name"])
    assert set(referenced_secrets(text)) == set(SECRET_NAMES)


def test_secrets_are_listed_in_the_header():
    text = render_workflow(full_options())
    header = text.split("\nname:")[0]
    for name in SECRET_NAMES:
        assert f"#   {name}" in header
    assert "(none" in render_workflow(CiOptions()).split("\nname:")[0]


# ── Secrets never reach the file ──────────────────────────────────────────


def test_secret_values_never_appear_in_the_output(tmp_path, monkeypatch):
    """Every channel a secret could arrive through is filled with a realistic
    value; the generator must not pick any of them up."""
    for name, value in SECRET_VALUES.items():
        monkeypatch.setenv(name, value)
    cert = tmp_path / "repo" / "certs" / "app.pfx"
    cert.parent.mkdir(parents=True)
    cert.write_bytes(b"\x30\x82" + SECRET_VALUES["WINDOWS_CERT_BASE64"].encode())
    project, path, root = project_in(
        tmp_path, signing__enabled=True, signing__cert_path=str(cert),
        signing__description=SECRET_VALUES["WINDOWS_CERT_PASSWORD"],  # a user mistake
        ci__sign_windows=True, ci__notarize_macos=True,
        packaging__maintainer="Me <me@example.com>",
    )
    monkeypatch.setattr(cli, "SIGNING_KEY_FILE", str(tmp_path / "key.json"))
    opts, findings = options_for(project, path, root)
    text = render_workflow(opts)
    for name, value in SECRET_VALUES.items():
        assert value not in text, name
    assert "pfx-pass" not in text and "ghp_" not in text
    # Every mention of a secret is a reference by name, nothing else.
    for match in re.finditer(r"secrets?\.[A-Za-z0-9_]+", text):
        assert re.fullmatch(r"secrets\.[A-Z0-9_]+", match.group(0)), match.group(0)
    assert set(referenced_secrets(text)) <= set(SECRET_NAMES)
    assert all(f"${{{{ secrets.{n} }}}}" in text for n in opts.secrets_used())
    assert "certs/app.pfx" in text and findings == []


def test_cli_ci_output_carries_no_secret(tmp_path, monkeypatch):
    for name, value in SECRET_VALUES.items():
        monkeypatch.setenv(name, value)
    project, path, root = project_in(tmp_path)
    monkeypatch.chdir(root)
    result = run("ci", "--print")
    assert result.code == cli.EXIT_OK
    for value in SECRET_VALUES.values():
        assert value not in result.out and value not in result.err


# ── From a project ────────────────────────────────────────────────────────


def test_options_for_a_project_in_a_subfolder(tmp_path):
    project, path, root = project_in(tmp_path)
    (tmp_path / "repo" / "requirements.txt").write_text("requests\n")
    parent = str(tmp_path)
    opts, findings = options_for(project, path, parent)
    assert opts.project_rel == "repo/p2e.toml"
    assert opts.release_root_rel == "repo/dist/release"
    assert opts.build_cache_rel == "repo/dist/build"
    assert opts.requirements_rel == "repo/requirements.txt"
    assert opts.app_name == "My App" and opts.engine == "pyinstaller"
    assert findings == []
    text = render_workflow(opts)
    assert "--project 'repo/p2e.toml'" in text and 'path: "repo/dist/release"' in text


def test_options_without_output_dir_build_next_to_the_source(tmp_path):
    project, path, root = project_in(tmp_path, build__output_dir="")
    opts, _ = options_for(project, path, root)
    assert opts.release_root_rel == "release" and opts.build_cache_rel == "build"


def test_output_outside_the_repository_is_an_error(tmp_path):
    outside = tmp_path / "elsewhere"
    project, path, root = project_in(tmp_path, build__output_dir=str(outside))
    opts, findings = options_for(project, path, root)
    assert [f.code for f in findings] == ["ci_output_outside_repo"]
    assert findings[0].severity == "error" and findings[0].params["root"] == root


def test_not_a_git_repository_is_a_warning(tmp_path):
    project, path, root = project_in(tmp_path)
    opts, findings = options_for(project, path, "")
    assert [f.code for f in findings] == ["ci_not_git"]
    assert opts.project_rel == "p2e.toml"


def test_signing_requested_but_not_configured(tmp_path):
    project, path, root = project_in(tmp_path, ci__sign_windows=True)
    opts, findings = options_for(project, path, root)
    assert [f.code for f in findings] == ["ci_signing_not_configured"]
    assert not opts.sign_windows
    project, path, root = project_in(tmp_path, ci__sign_windows=True, signing__enabled=True,
                                     signing__use_cert_store=True)
    _opts, findings = options_for(project, path, root)
    assert [f.code for f in findings] == ["ci_signing_not_configured"]


def test_project_options_flow_through(tmp_path):
    project, path, root = project_in(
        tmp_path, ci__python_version="3.11", ci__allow_doctor_errors=True,
        ci__notarize_macos=True, release__tag_prefix="r", release__draft=True,
        packaging__appimage=True, packaging__dmg=True, build__engine="nuitka",
    )
    opts, _ = options_for(project, path, root, branch="trunk")
    assert opts.python_version == "3.11" and opts.allow_doctor_errors and opts.notarize_macos
    assert opts.tag_prefix == "r" and opts.draft and not opts.prerelease
    assert opts.formats == ["appimage", "dmg"] and opts.engine == "nuitka"
    assert opts.branch == "trunk"
    assert formats_by_runner(opts) == {"windows-latest": [], "macos-latest": ["dmg"],
                                       "ubuntu-latest": ["appimage"]}
    opts, _ = options_for(project, path, root, python_version="3.9", tool_requirement="py2exe-gui==2.0.0")
    assert opts.python_version == "3.9" and opts.tool_requirement == "py2exe-gui==2.0.0"
    opts, _ = options_for(project, path, root, python_version="not-a-version")
    assert opts.python_version == DEFAULT_PYTHON


def test_rendering_is_deterministic():
    assert render_workflow(full_options()) == render_workflow(full_options())


# ── Files ─────────────────────────────────────────────────────────────────


def test_workflow_path_and_write(tmp_path):
    path = workflow_path(str(tmp_path))
    assert path == os.path.join(str(tmp_path), ".github", "workflows", "p2e-release.yml")
    assert WORKFLOW_RELATIVE == ".github/workflows/p2e-release.yml"
    write_workflow("name: x\n", path)
    assert open(path, encoding="utf-8").read() == "name: x\n"


def test_repo_root(tmp_path):
    if shutil.which("git") is None:
        pytest.skip("git not installed")
    assert repo_root(str(tmp_path)) == "" or not str(tmp_path).startswith(repo_root(str(tmp_path)) + "x")
    repo = tmp_path / "r"
    (repo / "sub").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    assert os.path.realpath(repo_root(str(repo / "sub"))) == os.path.realpath(str(repo))


# ── actionlint, when installed ────────────────────────────────────────────


@pytest.mark.parametrize("opts", [CiOptions(), full_options()], ids=["plain", "full"])
def test_actionlint_accepts_the_workflow(tmp_path, opts):
    actionlint = shutil.which("actionlint") or os.environ.get("ACTIONLINT", "")
    if not actionlint or not os.path.isfile(actionlint):
        pytest.skip("actionlint is not installed")
    path = tmp_path / ".github" / "workflows" / "p2e-release.yml"
    write_workflow(render_workflow(opts), str(path))
    result = subprocess.run([actionlint, "-no-color", str(path)], capture_output=True,
                            text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr


# ── The command line ──────────────────────────────────────────────────────


def test_cli_ci_print_writes_nothing(tmp_path, monkeypatch):
    project, path, root = project_in(tmp_path)
    monkeypatch.chdir(root)
    result = run("ci", "--print")
    assert result.code == cli.EXIT_OK
    assert "jobs:" in result.out and "windows-latest" in result.out
    assert not os.path.exists(workflow_path(root))


def test_cli_ci_needs_a_yes(tmp_path, monkeypatch):
    project, path, root = project_in(tmp_path)
    monkeypatch.chdir(root)
    result = run("ci")
    assert result.code == cli.EXIT_CONSENT
    assert not os.path.exists(workflow_path(root))
    result = run("ci", interactive=True, answers=["n"])
    assert result.code == cli.EXIT_CONSENT and not os.path.exists(workflow_path(root))


def test_cli_ci_writes_with_yes_and_asks_before_overwriting(tmp_path, monkeypatch):
    project, path, root = project_in(tmp_path)
    monkeypatch.chdir(root)
    result = run("ci", "--yes", "--python", "3.11")
    assert result.code == cli.EXIT_OK
    target = workflow_path(root)
    text = open(target, encoding="utf-8").read()
    assert 'python-version: "3.11"' in text
    assert yaml.safe_load(text)["jobs"]
    result = run("ci", interactive=True, answers=["y"])
    assert result.code == cli.EXIT_OK and "exists" in result.out.lower()


def test_cli_ci_refuses_an_output_folder_outside_the_repo(tmp_path, monkeypatch):
    project, path, root = project_in(tmp_path, build__output_dir=str(tmp_path / "out"))
    monkeypatch.chdir(root)
    result = run("ci", "--yes")
    assert result.code == cli.EXIT_PROJECT
    assert "ci_output_outside_repo" in result.err
    assert not os.path.exists(workflow_path(root))
