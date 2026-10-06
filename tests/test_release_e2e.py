"""End to end with a real PyInstaller: init → build → release --dry-run →
release against the local fake GitHub API.

Drives the command line in-process, the way a CI job would run it, on a small
project in a temporary git repository, and checks what a user would check:
the EXE runs, the checksums match the files, the winget manifests satisfy the
official schema and point at the uploaded asset, the tag exists, and the
token appears nowhere.

What it cannot cover on Linux: signtool, Inno Setup, a real winget validation
and a real GitHub upload (see the PR description).
"""

import io
import os
import shutil
import subprocess
import sys

import pytest

pytest.importorskip("PyInstaller", reason="PyInstaller not installed")

from py2exe_gui import cli  # noqa: E402
from py2exe_gui.core.project_file import load_project, save_project  # noqa: E402
from py2exe_gui.core.release import artifacts  # noqa: E402
from py2exe_gui.core.release.winget import validate_manifests  # noqa: E402
from tests.fake_github import FakeGitHub  # noqa: E402

pytestmark = [pytest.mark.slow,
              pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")]

TOKEN = "ghp_" + "E" * 36
APP = "import sys\nprint('hello from', sys.argv[1:] or 'nowhere')\n"


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    console = cli.Console(interactive=False, out=out, err=err)
    code = cli.main(["--lang", "en", *argv], console)
    return code, out.getvalue(), err.getvalue()


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          text=True).stdout


def test_init_build_release(tmp_path, monkeypatch):
    project_dir = tmp_path / "hello"
    project_dir.mkdir()
    (project_dir / "hello.py").write_text(APP)
    for args in (["init", "-q", "-b", "main"], ["config", "user.name", "T"],
                 ["config", "user.email", "t@example.com"], ["config", "commit.gpgsign", "false"],
                 ["config", "tag.gpgsign", "false"]):
        git(project_dir, *args)
    monkeypatch.chdir(project_dir)
    monkeypatch.setattr(cli, "ENVS_ROOT", str(tmp_path / "envs"))
    monkeypatch.setattr(cli, "SIGNING_KEY_FILE", str(tmp_path / "key.json"))

    # init
    code, out, err = run("init", "hello.py", "--name", "Hello", "--set-version", "0.1.0")
    assert code == 0, err
    project_file = project_dir / "p2e.toml"
    loaded = load_project(str(project_file))
    loaded.project.release.repository = "me/hello"
    winget = loaded.project.release.winget
    winget.enabled, winget.identifier, winget.publisher = True, "Me.Hello", "Me Inc"
    winget.license, winget.short_description = "MIT", "Says hello"
    save_project(loaded.project, str(project_file))
    (project_dir / ".gitignore").write_text("dist/\nbuild/\nrelease/\n*.spec\n")
    git(project_dir, "add", ".")
    git(project_dir, "commit", "-qm", "feat: say hello")

    # build — a real PyInstaller run, streamed with stage markers
    code, out, err = run("build")
    assert code == 0, out + err
    assert "==> [Analyzing imports]" in out and "==> [Building PYZ archive]" in out
    built = artifacts.built_output(load_project(str(project_file)).project.build)
    result = subprocess.run([built, "x"], capture_output=True, text=True, timeout=60)
    assert "hello from ['x']" in result.stdout

    # size lab on that build
    code, out, err = run("size", "--json")
    assert code == 0 and '"output_bytes"' in out

    # release --dry-run: a plan, and nothing changes
    monkeypatch.setenv("GITHUB_TOKEN", TOKEN)
    before = project_file.read_text()
    code, out, err = run("release", "--bump", "minor", "--dry-run")
    assert code == 0, out + err
    assert "Release plan for 0.2.0" in out and "v0.2.0" in out
    assert project_file.read_text() == before
    assert not (project_dir / "release").exists() and git(project_dir, "tag") == ""

    # the real release, against the fake API
    monkeypatch.setattr(cli, "ALLOW_INSECURE_LOCALHOST", True)
    git(project_dir, "commit", "--allow-empty", "-qm", "fix: nothing really")
    with FakeGitHub(TOKEN, "me/hello") as fake:
        code, out, err = run("release", "--bump", "minor", "--api-url", fake.url, "--yes")
        uploads = dict(fake.uploads)
        release = fake.releases[0]
        requests = list(fake.requests)
    assert code == 0, out + err

    out_dir = project_dir / "release" / "0.2.0"
    exe_name = "hello-0.2.0" + (".exe" if sys.platform == "win32" else "")
    assert sorted(uploads) == sorted(["hello-0.2.0-portable.zip", exe_name, "SHA256SUMS.txt"])
    assert artifacts.verify_checksums(str(out_dir / "SHA256SUMS.txt")) == []
    for name, data in uploads.items():
        assert (out_dir / name).read_bytes() == data
    released = subprocess.run([str(out_dir / exe_name)], capture_output=True, text=True,
                              timeout=60)
    assert "hello from" in released.stdout
    assert "say hello" in release["body"] and "nothing really" in release["body"]

    # winget: three files, valid, pointing at the uploaded asset and its hash
    winget_dir = out_dir / "winget"
    assert sorted(os.listdir(winget_dir)) == ["Me.Hello.installer.yaml",
                                              "Me.Hello.locale.en-US.yaml", "Me.Hello.yaml"]
    installer_yaml = (winget_dir / "Me.Hello.installer.yaml").read_text()
    asset_url = "https://github.com/me/hello/releases/download/v0.2.0/"
    assert asset_url in installer_yaml
    sha = artifacts.sha256_of(str(out_dir / (exe_name if exe_name.endswith(".exe")
                                             else "hello-0.2.0-portable.zip")))
    assert sha.upper() in installer_yaml
    # git: the bump was committed, then tagged
    assert load_project(str(project_file)).project.version == "0.2.0"
    assert git(project_dir, "tag").split() == ["v0.2.0"]
    assert git(project_dir, "status", "--porcelain") == ""

    # the token: only ever in the Authorization header
    assert TOKEN not in out and TOKEN not in err
    assert all(TOKEN not in str(r["query"]) for r in requests)
    for folder, _dirs, files in os.walk(project_dir):
        if ".git" in folder:
            continue
        for name in files:
            with open(os.path.join(folder, name), "rb") as f:
                assert TOKEN.encode() not in f.read(), name

    from tests.test_release_winget import load_schema, schema_errors

    # Last, because it needs PyYAML (optional): parse the YAML and check it
    # against the official schema files.
    yaml = pytest.importorskip("yaml")
    for kind, name in (("version", "Me.Hello.yaml"), ("installer", "Me.Hello.installer.yaml"),
                       ("defaultLocale", "Me.Hello.locale.en-US.yaml")):
        doc = yaml.safe_load((winget_dir / name).read_text(encoding="utf-8"))
        schema = load_schema(kind)
        assert schema_errors(doc, schema, schema) == [], name
    assert validate_manifests({"version": yaml.safe_load((winget_dir / "Me.Hello.yaml").read_text()),
                               "installer": yaml.safe_load(installer_yaml),
                               "defaultLocale": yaml.safe_load(
                                   (winget_dir / "Me.Hello.locale.en-US.yaml").read_text())}) == []
