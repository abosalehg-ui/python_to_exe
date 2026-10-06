"""The release pipeline: each step, the dry run, and full runs against a
temporary git repository and the fake GitHub API."""

import json
import os
import shutil
import subprocess
import zipfile

import pytest

from py2exe_gui.core.build_runner import BuildOutcome
from py2exe_gui.core.fixes import SEVERITY_ERROR, SEVERITY_WARNING, Finding
from py2exe_gui.core.project_doctor import DoctorReport
from py2exe_gui.core.project_file import ProjectConfig, load_project, save_project
from py2exe_gui.core.release import artifacts, pipeline
from py2exe_gui.core.release.credentials import Token
from py2exe_gui.core.release.pipeline import (
    DONE,
    FAILED,
    PENDING,
    PLANNED,
    SKIPPED,
    ReleaseContext,
    ReleaseOptions,
    confirmation,
    has_blocking_problems,
    plan_release,
    run_release,
)
from py2exe_gui.core.update_signing import new_signing_key, write_key_file
from tests.fake_github import FakeGitHub

TOKEN = "ghp_" + "S" * 36
PASSWORD = "pfx-pass-9876"


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          text=True).stdout


@pytest.fixture
def repo(tmp_path):
    if shutil.which("git") is None:
        pytest.skip("git not installed")
    root = tmp_path / "proj"
    root.mkdir()
    (root / "app.py").write_text("print('hello')\n")
    project = ProjectConfig(name="MyApp")
    project.build.source = str(root / "app.py")
    project.build.output_name = "MyApp"
    project.version = "1.0.0"
    project.installer.app_version = "1.0.0"
    project.release.repository = "me/app"
    project.release.winget.enabled = True
    project.release.winget.identifier = "Me.MyApp"
    project.release.winget.publisher = "Me Inc"
    project.release.winget.license = "MIT"
    project.release.winget.short_description = "A test app"
    save_project(project, str(root / "p2e.toml"))
    (root / ".gitignore").write_text("dist/\nbuild/\nrelease/\n")
    for args in (["init", "-q", "-b", "main"], ["config", "user.name", "T"],
                 ["config", "user.email", "t@example.com"], ["config", "commit.gpgsign", "false"],
                 ["config", "tag.gpgsign", "false"], ["add", "."],
                 ["commit", "-q", "-m", "feat: first"], ["tag", "-a", "v1.0.0", "-m", "v1"]):
        git(root, *args)
    (root / "app.py").write_text("print('hello again')\n")
    git(root, "commit", "-qam", "fix: say hello again")
    return root


def fake_build(ctx):
    dist = os.path.join(os.path.dirname(ctx.project.build.source), "dist")
    os.makedirs(dist, exist_ok=True)
    if ctx.project.build.onefile:
        with open(os.path.join(dist, "MyApp.exe"), "wb") as f:
            f.write(b"MZ" + ctx.version.encode() * 100)
    else:
        folder = os.path.join(dist, "MyApp")
        os.makedirs(os.path.join(folder, "_internal"), exist_ok=True)
        with open(os.path.join(folder, "MyApp.exe"), "wb") as f:
            f.write(b"MZ-dir")
        with open(os.path.join(folder, "_internal", "lib.dll"), "wb") as f:
            f.write(b"dll")
    ctx.log("built")
    return BuildOutcome(True, 0)


def doctor_with(*findings):
    def doctor(_ctx):
        return DoctorReport(source="x", findings=list(findings))
    return doctor


def context(root, fake=None, log=None, **options):
    loaded = load_project(str(root / "p2e.toml"))
    opts = dict(version="1.1.0", platform="linux", allow_insecure_localhost=True)
    if fake is not None:
        opts["api_url"] = fake.url
    opts.update(options)
    return ReleaseContext(
        loaded.project, ReleaseOptions(**opts), project_path=loaded.path,
        log=(log.append if log is not None else (lambda _m: None)),
        build=fake_build,
        doctor=doctor_with(),
        token_provider=lambda: Token(TOKEN, "env"),
    )


def statuses(results):
    return {r.key: r.status for r in results}


def tree(path):
    found = {}
    for folder, _dirs, files in os.walk(path):
        if ".git" in folder.split(os.sep):
            continue
        for name in files:
            p = os.path.join(folder, name)
            with open(p, "rb") as f:
                found[os.path.relpath(p, path)] = f.read()
    return found


# ── Dry run ───────────────────────────────────────────────────────────────


def test_dry_run_has_no_side_effects_and_lists_everything(repo):
    before, refs = tree(repo), git(repo, "show-ref")
    with FakeGitHub(TOKEN) as fake:
        ctx = context(repo, fake, dry_run=True)
        results = plan_release(ctx)
        assert fake.requests == []  # no server contact at all
    assert tree(repo) == before and git(repo, "show-ref") == refs
    assert git(repo, "status", "--porcelain") == ""

    s = statuses(results)
    assert s["version"] == s["notes"] == s["doctor"] == s["build"] == PLANNED
    assert s["sign"] == SKIPPED and s["installer"] == SKIPPED
    assert s["portable_zip"] == s["checksums"] == s["tag"] == s["publish"] == PLANNED
    assert s["update_manifest"] == SKIPPED
    assert s["winget"] == PLANNED
    assert not has_blocking_problems(results)

    summary = confirmation(results)
    out = artifacts.release_dir(ctx.project.build, "1.1.0")
    assert os.path.join(out, "MyApp-1.1.0-portable.zip") in summary.created
    assert os.path.join(out, "SHA256SUMS.txt") in summary.created
    assert str(repo / "p2e.toml") in summary.created
    assert summary.commits == [str(repo / "p2e.toml")]
    assert summary.tags == ["v1.1.0"] and summary.pushes == []
    assert summary.releases == ["me/app@v1.1.0"]
    assert "MyApp-1.1.0-portable.zip" in summary.uploads
    assert "SHA256SUMS.txt" in summary.uploads
    assert any(c.startswith(ctx.python) for c in summary.commands)
    # Notes were drafted from git, read-only.
    assert "say hello again" in ctx.notes and "first" not in ctx.notes


def test_dry_run_requires_a_dry_context(repo):
    with pytest.raises(ValueError):
        plan_release(context(repo))


def test_dry_run_shows_every_problem_at_once(repo):
    ctx = context(repo, dry_run=True, version="2.0")
    ctx.doctor = doctor_with(Finding("syntax_error", SEVERITY_ERROR))
    ctx.token_provider = lambda: Token()
    ctx.project.release.winget.license = ""
    results = run_release(ctx)
    s = statuses(results)
    assert s["version"] == FAILED and s["doctor"] == FAILED
    assert s["publish"] == FAILED and s["winget"] == FAILED
    reasons = {r.key: r.reason for r in results}
    assert reasons["publish"] == "no_token" and reasons["winget"] == "winget_invalid"
    assert len(confirmation(results).problems) == 4


# ── A full release ────────────────────────────────────────────────────────


def test_full_release_against_git_and_the_fake_api(repo):
    log = []
    with FakeGitHub(TOKEN) as fake:
        ctx = context(repo, fake, log=log, notes="")
        results = run_release(ctx)
        requests = list(fake.requests)
        uploads = dict(fake.uploads)
        release = fake.releases[0]

    s = statuses(results)
    assert s == {"version": DONE, "notes": DONE, "doctor": DONE, "build": DONE,
                 "sign": SKIPPED, "installer": SKIPPED, "portable_zip": DONE,
                 "checksums": DONE, "update_manifest": SKIPPED, "tag": DONE,
                 "publish": DONE, "winget": DONE}, results

    # Version bumped everywhere and committed, then tagged.
    reloaded = load_project(str(repo / "p2e.toml")).project
    assert reloaded.version == "1.1.0" and reloaded.installer.app_version == "1.1.0"
    assert reloaded.version_info.file_version == "1.1.0.0"
    assert git(repo, "status", "--porcelain") == ""
    assert git(repo, "log", "-1", "--format=%s").strip() == "Release v1.1.0"
    head = git(repo, "rev-parse", "HEAD").strip()
    assert git(repo, "rev-parse", "v1.1.0^{commit}").strip() == head
    assert release["target_commitish"] == head

    # Artifacts and checksums.
    out = ctx.out_dir
    names = sorted(os.listdir(out))
    assert names == ["MyApp-1.1.0-portable.zip", "MyApp-1.1.0.exe", "RELEASE_NOTES.md",
                     "SHA256SUMS.txt", "winget"]
    assert artifacts.verify_checksums(os.path.join(out, "SHA256SUMS.txt")) == []
    assert set(artifacts.parse_checksums(open(os.path.join(out, "SHA256SUMS.txt")).read())) == {
        "MyApp-1.1.0.exe", "MyApp-1.1.0-portable.zip"}
    with zipfile.ZipFile(os.path.join(out, "MyApp-1.1.0-portable.zip")) as z:
        assert z.namelist() == ["MyApp.exe"]

    # Uploaded assets, and the notes as the release body.
    assert sorted(uploads) == ["MyApp-1.1.0-portable.zip", "MyApp-1.1.0.exe", "SHA256SUMS.txt"]
    assert "say hello again" in release["body"]
    assert release["tag_name"] == "v1.1.0" and release["name"] == "MyApp 1.1.0"

    # winget points at the real asset URL and hash.
    winget_dir = os.path.join(out, "winget")
    installer_yaml = open(os.path.join(winget_dir, "Me.MyApp.installer.yaml")).read()
    assert "InstallerType: portable" in installer_yaml
    assert '"https://github.com/me/app/releases/download/v1.1.0/MyApp-1.1.0.exe"' \
        in installer_yaml
    assert artifacts.sha256_of(os.path.join(out, "MyApp-1.1.0.exe")).upper() in installer_yaml
    assert len(os.listdir(winget_dir)) == 3

    # The token appears in no log line, no file and no request except its header.
    everything = "\n".join(log) + json.dumps([r["query"] for r in requests])
    for path in tree(repo).values():
        assert TOKEN.encode() not in path
    assert TOKEN not in everything
    assert all(r["headers"]["authorization"] == f"Bearer {TOKEN}" for r in requests)


def test_running_the_same_release_again_is_idempotent(repo):
    with FakeGitHub(TOKEN) as fake:
        first = run_release(context(repo, fake))
        assert not has_blocking_problems(first)
        fake.requests.clear()
        again = run_release(context(repo, fake))
        methods = [r["method"] for r in fake.requests]
        assert len(fake.releases) == 1
    reasons = {r.key: r.reason for r in again}
    assert reasons["version"] == "version_unchanged"
    assert reasons["tag"] == "tag_exists"
    assert statuses(again)["publish"] == DONE
    assert "POST" not in methods  # nothing created or uploaded twice


def test_push_tag_is_a_separate_opt_in(repo, tmp_path):
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    git(repo, "remote", "add", "origin", str(remote))
    results = run_release(context(repo, publish=False, push_tag=True))
    assert statuses(results)["tag"] == DONE
    assert "v1.1.0" in git(remote, "tag")
    assert any(a.kind == pipeline.PUSH for r in results for a in r.actions)


def test_without_push_the_tag_stays_local(repo, tmp_path):
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    git(repo, "remote", "add", "origin", str(remote))
    run_release(context(repo, publish=False))
    assert git(remote, "tag") == ""


# ── Gate, failures, stops ─────────────────────────────────────────────────


def test_doctor_errors_block_unless_overridden(repo):
    ctx = context(repo, publish=False)
    ctx.doctor = doctor_with(Finding("syntax_error", SEVERITY_ERROR),
                             Finding("input_in_windowed", SEVERITY_WARNING))
    results = run_release(ctx)
    s = statuses(results)
    assert s["doctor"] == FAILED and s["build"] == PENDING
    assert {r.reason for r in results if r.status == PENDING} == {"not_run"}
    assert results[2].params["codes"] == "syntax_error"
    assert not os.path.exists(repo / "dist")

    ctx = context(repo, publish=False, allow_doctor_errors=True)
    ctx.doctor = doctor_with(Finding("syntax_error", SEVERITY_ERROR))
    results = run_release(ctx)
    assert results[2].reason == "doctor_overridden" and results[2].status == DONE
    assert statuses(results)["build"] == DONE


def test_build_failures_stop_the_release(repo):
    ctx = context(repo, publish=False)
    ctx.build = lambda _ctx: BuildOutcome(False, 1, "")
    results = run_release(ctx)
    assert statuses(results)["build"] == FAILED
    assert results[3].params["error"] == "exit code 1"
    assert statuses(results)["tag"] == PENDING
    ctx = context(repo, publish=False)
    ctx.build = lambda _ctx: BuildOutcome(True, 0)  # "succeeds" but writes nothing
    assert run_release(ctx)[3].reason == "build_no_output"


def test_an_unexpected_exception_is_a_failed_step(repo):
    ctx = context(repo, publish=False)

    def explode(_ctx):
        raise RuntimeError(f"bug near {PASSWORD}")

    ctx.build = explode
    ctx.secrets.append(PASSWORD)
    results = run_release(ctx)
    assert results[3].reason == "unexpected" and PASSWORD not in results[3].params["error"]


def test_no_token_and_no_repository(repo):
    ctx = context(repo)
    ctx.token_provider = lambda: Token()
    results = run_release(ctx)
    assert {r.key: r.reason for r in results}["publish"] == "no_token"
    ctx = context(repo, version="1.2.0")
    ctx.project.release.repository = ""
    assert {r.key: r.reason for r in run_release(ctx)}["publish"] == "no_repository"


def test_publish_errors_are_reported(repo):
    with FakeGitHub("ghp_" + "X" * 36) as fake:  # the server expects another token
        results = run_release(context(repo, fake))
    publish = next(r for r in results if r.key == "publish")
    assert publish.reason == "publish_failed" and TOKEN not in publish.params["error"]


def test_tag_conflict(repo):
    git(repo, "tag", "-a", "v1.1.0", "-m", "elsewhere", "HEAD~1")
    results = run_release(context(repo, publish=False))
    tag = next(r for r in results if r.key == "tag")
    assert tag.status == FAILED and tag.reason == "tag_conflict"


def test_outside_git_the_tag_step_is_skipped(tmp_path):
    (tmp_path / "app.py").write_text("print(1)\n")
    project = ProjectConfig(version="0.1.0")
    project.build.source = str(tmp_path / "app.py")
    project.build.output_name = "MyApp"
    ctx = ReleaseContext(project, ReleaseOptions("0.2.0", publish=False, platform="linux"),
                         build=fake_build, doctor=doctor_with())
    results = run_release(ctx)
    assert {r.key: r.reason for r in results}["tag"] == "not_git"
    assert {r.key: r.reason for r in results}["notes"] == "notes_no_git"
    assert project.version == "0.2.0"  # no project file: changed in memory only


def test_versions_the_runtime_cannot_compare_are_refused(repo):
    ctx = context(repo, version="1.2.0-foo")
    ctx.project.build.runtime_kit.updater = True
    assert run_release(ctx)[0].reason == "version_runtime"
    ctx = context(repo, version="2")
    assert run_release(ctx)[0].reason == "version_invalid"


def test_toggled_off_steps_are_skipped(repo):
    ctx = context(repo, create_tag=False, publish=False)
    ctx.project.release.assets.portable_zip = False
    ctx.project.release.assets.checksums = False
    ctx.project.release.winget.enabled = False
    reasons = {r.key: r.reason for r in run_release(ctx)}
    assert reasons["portable_zip"] == "zip_off" and reasons["checksums"] == "checksums_off"
    assert reasons["tag"] == "tag_off" and reasons["publish"] == "publish_off"
    assert reasons["winget"] == "winget_off"
    assert os.path.isfile(os.path.join(ctx.out_dir, "MyApp-1.1.0.exe"))


def test_notes_given_by_the_user_are_used_verbatim(repo):
    ctx = context(repo, notes="ملاحظاتي\n", publish=False)
    results = run_release(ctx)
    assert results[1].reason == "notes_given"
    with open(os.path.join(ctx.out_dir, "RELEASE_NOTES.md"), encoding="utf-8") as f:
        assert f.read() == "ملاحظاتي\n"


# ── Update manifest (Runtime Kit 1.5) ─────────────────────────────────────


def test_update_manifest_is_signed_for_the_new_version(repo, tmp_path):
    key_path = str(tmp_path / "key" / "k.json")
    key = new_signing_key()
    write_key_file(key_path, key)
    with FakeGitHub(TOKEN) as fake:
        ctx = context(repo, fake, signing_key_path=key_path)
        ctx.project.build.runtime_kit.updater = True
        results = run_release(ctx)
        uploads = sorted(fake.uploads)
    assert statuses(results)["update_manifest"] == DONE
    manifest_path = os.path.join(ctx.out_dir, "update.json")
    data = open(manifest_path, "rb").read()
    from p2e_runtime import _ed25519
    from p2e_runtime.updates import parse_manifest

    signature = bytes.fromhex(open(manifest_path + ".sig").read().strip())
    assert _ed25519.verify(bytes.fromhex(key.public_hex), data, signature)
    info = parse_manifest(data, "MyApp")
    assert info["version"] == "1.1.0"
    assert info["url"] == "https://github.com/me/app/releases/download/v1.1.0/MyApp-1.1.0.exe"
    assert info["sha256"] == artifacts.sha256_of(os.path.join(ctx.out_dir, "MyApp-1.1.0.exe"))
    assert "update.json" in uploads and "update.json.sig" in uploads
    # The private key is never written into the release.
    for content in tree(ctx.out_dir).values():
        assert key.seed.hex().encode() not in content


def test_update_manifest_preconditions(repo, tmp_path):
    ctx = context(repo, publish=False, signing_key_path=str(tmp_path / "none.json"))
    ctx.project.build.runtime_kit.updater = True
    assert {r.key: r.reason for r in run_release(ctx)}["update_manifest"] == "no_signing_key"

    ctx = context(repo, publish=False)
    ctx.project.build.runtime_kit.updater = True
    ctx.project.release.assets.update_manifest = False
    assert {r.key: r.reason for r in run_release(ctx)}["update_manifest"] == "update_asset_off"

    # A folder build updates through its installer, which Linux cannot make.
    ctx = context(repo, publish=False, version="1.3.0")
    ctx.project.build.onefile = False
    ctx.project.build.runtime_kit.updater = True
    reasons = {r.key: r.reason for r in run_release(ctx)}
    assert reasons["update_manifest"] == "update_needs_file"

    ctx = context(repo, publish=False, dry_run=True)
    ctx.project.build.runtime_kit.updater = True
    ctx.project.release.repository = ""
    assert {r.key: r.reason for r in run_release(ctx)}["update_manifest"] == "no_repository"


def test_onedir_release_zips_the_folder(repo):
    ctx = context(repo, publish=False)
    ctx.project.build.onefile = False
    results = run_release(ctx)
    assert not has_blocking_problems(results)
    with zipfile.ZipFile(ctx.zip_target()) as z:
        assert sorted(z.namelist()) == ["MyApp/MyApp.exe", "MyApp/_internal/lib.dll"]
    winget_installer = os.path.join(ctx.out_dir, "winget", "Me.MyApp.installer.yaml")
    text = open(winget_installer).read()
    assert "InstallerType: zip" in text and "RelativeFilePath: MyApp/MyApp.exe" in text


# ── Windows-only steps, with a recording runner ───────────────────────────


class Recorder:
    """Stands in for subprocess.run: records signtool/ISCC, delegates git."""

    def __init__(self, fail=()):
        self.commands = []
        self.fail = set(fail)

    def __call__(self, command, **kwargs):
        if command[0] == "git":
            return subprocess.run(command, **kwargs)
        self.commands.append(command)
        tool = os.path.basename(command[0]).lower()
        if tool in self.fail:
            return subprocess.CompletedProcess(command, 1, "", f"{tool} broke")
        if tool.startswith("iscc"):
            iss = command[-1]
            out = os.path.dirname(iss)
            with open(iss, encoding="utf-8") as f:
                base = next(line.split("=", 1)[1] for line in f
                            if line.startswith("OutputBaseFilename="))
            with open(os.path.join(out, base.strip() + ".exe"), "wb") as f:
                f.write(b"MZ-setup")
        return subprocess.CompletedProcess(command, 0, "ok", "")


def windows_context(repo, recorder, log, **options):
    settings = dict(platform="win32", iscc_path="C:/Inno/ISCC.exe", signtool_path="signtool",
                    sign_password=PASSWORD, publish=False)
    settings.update(options)
    ctx = context(repo, log=log, **settings)
    ctx.runner = recorder
    ctx.project.signing.enabled = True
    ctx.project.signing.cert_path = str(repo / "cert.pfx")
    ctx.project.installer.enabled = True
    ctx.project.installer.sign_installer = True
    return ctx


def test_windows_release_signs_builds_installer_and_never_logs_the_password(repo):
    log, recorder = [], Recorder()
    ctx = windows_context(repo, recorder, log)
    results = run_release(ctx)
    s = statuses(results)
    assert s["sign"] == DONE and s["installer"] == DONE, results
    signtool = recorder.commands[0]
    assert signtool[:2] == ["signtool", "sign"] and PASSWORD in signtool
    iscc = recorder.commands[1]
    assert iscc[0] == "C:/Inno/ISCC.exe" and any(a.startswith("/Sbyparam=") for a in iscc)
    setup = os.path.join(ctx.out_dir, "MyApp-1.1.0-setup.exe")
    assert os.path.isfile(setup)
    sums = artifacts.parse_checksums(open(os.path.join(ctx.out_dir, "SHA256SUMS.txt")).read())
    assert "MyApp-1.1.0-setup.exe" in sums
    assert "InstallerType: inno" in open(
        os.path.join(ctx.out_dir, "winget", "Me.MyApp.installer.yaml")).read()
    # The password reached signtool, and nothing else.
    assert PASSWORD not in "\n".join(log)
    for result in results:
        assert PASSWORD not in json.dumps(result.params)
        assert all(PASSWORD not in a.target for a in result.actions)
    for content in tree(repo).values():
        assert PASSWORD.encode() not in content


def test_windows_dry_run_lists_the_tools_with_the_password_hidden(repo):
    log, recorder = [], Recorder()
    ctx = windows_context(repo, recorder, log, dry_run=True)
    results = run_release(ctx)
    assert recorder.commands == []
    summary = confirmation(results)
    assert any(c.startswith("signtool sign") and "***" in c for c in summary.commands)
    assert os.path.join(ctx.out_dir, "MyApp-1.1.0-setup.exe") in summary.created
    assert "MyApp-1.1.0-setup.exe" not in summary.uploads  # publish is off
    assert all(PASSWORD not in c for c in summary.commands)


@pytest.mark.parametrize("tool,step", [("signtool", "sign"), ("iscc.exe", "installer")])
def test_windows_tool_failures_stop_the_release(repo, tool, step):
    log = []
    ctx = windows_context(repo, Recorder(fail={tool}), log)
    results = run_release(ctx)
    assert statuses(results)[step] == FAILED
    assert statuses(results)["tag"] == PENDING
    assert PASSWORD not in "\n".join(log)


def test_missing_inno_setup(repo, monkeypatch):
    monkeypatch.setattr(pipeline, "find_iscc", lambda: None)
    ctx = windows_context(repo, Recorder(), [], iscc_path="")
    assert {r.key: r.reason for r in run_release(ctx)}["installer"] == "iscc_missing"


def test_signing_without_a_certificate(repo):
    ctx = windows_context(repo, Recorder(), [])
    ctx.project.signing.cert_path = ""
    assert {r.key: r.reason for r in run_release(ctx)}["sign"] == "sign_failed"


def test_default_build_and_doctor_wiring(repo, monkeypatch):
    """The defaults call the shared build runner and the real doctor."""
    calls = {}

    def fake_run_build(prepared, on_line, on_stage):
        calls["command"] = prepared.command
        on_stage("analyzing", 5)
        fake_build(ctx)
        return BuildOutcome(True, 0)

    monkeypatch.setattr(pipeline, "run_build", fake_run_build)
    log = []
    ctx = context(repo, log=log, publish=False)
    ctx.build = pipeline.default_build
    ctx.doctor = pipeline.default_doctor
    results = run_release(ctx)
    assert statuses(results)["build"] == DONE
    assert calls["command"][1:3] == ["-m", "PyInstaller"]
    assert "==> [analyzing] 5%" in log
    assert results[2].reason == "doctor_ok"


@pytest.mark.parametrize("platform,name", [("win32", "MyApp-1.1.0.exe"), ("linux", "MyApp-1.1.0"),
                                           ("darwin", "MyApp-1.1.0")])
def test_dry_run_predicts_the_executable_name_of_the_platform(repo, platform, name):
    ctx = context(repo, dry_run=True, publish=False, platform=platform)
    summary = confirmation(run_release(ctx))
    assert os.path.join(ctx.out_dir, name) in summary.created
