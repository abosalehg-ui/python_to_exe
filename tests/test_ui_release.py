"""Headless GUI tests for the Release tab: version, token, dry run, release."""

import functools
import json
import os
import shutil
import subprocess

import pytest

pytest.importorskip("PyQt5", reason="PyQt5 not installed")

from PyQt5.QtWidgets import QMessageBox  # noqa: E402

from py2exe_gui.core.build_runner import BuildOutcome  # noqa: E402
from py2exe_gui.core.project_file import ProjectConfig, load_project, save_project  # noqa: E402
from py2exe_gui.core.release import credentials  # noqa: E402
from py2exe_gui.core.release.pipeline import Confirmation, ReleaseOptions  # noqa: E402
from py2exe_gui.strings import Ar, En, set_locale  # noqa: E402
from py2exe_gui.ui.dialogs import ReleaseConfirmDialog  # noqa: E402
from tests.conftest import MemoryKeyring  # noqa: E402
from tests.fake_github import FakeGitHub  # noqa: E402

pytestmark = pytest.mark.gui
TOKEN = "ghp_" + "G" * 36


@pytest.fixture
def keyring():
    return MemoryKeyring()


@pytest.fixture
def window(qapp, tmp_path, monkeypatch, keyring):
    monkeypatch.setattr("py2exe_gui.ui.main_window.SETTINGS_FILE", str(tmp_path / "s.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.HISTORY_FILE", str(tmp_path / "h.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.PRESETS_FILE", str(tmp_path / "p.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.ENVS_ROOT", str(tmp_path / "envs"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.SIGNING_KEY_FILE",
                        str(tmp_path / "signing" / "k.json"))
    monkeypatch.setattr("py2exe_gui.ui.main_window.KEYRING", keyring)
    from py2exe_gui.ui.main_window import MainWindow

    win = MainWindow()
    yield win
    if win.release_thread is not None:
        win.release_thread.wait(30000)
    win.close()


def answer(monkeypatch, kind, reply, record=None):
    def fake(*args, **_kwargs):
        if record is not None:
            record.append(args[2] if len(args) > 2 else "")
        return reply

    monkeypatch.setattr(QMessageBox, kind, staticmethod(fake))


def plain(text):
    """Text without the direction marks ``bidi()`` adds for right-to-left layout."""
    for mark in ("\u200e", "\u200f", "\u2066", "\u2069"):
        text = text.replace(mark, "")
    return text


def wait_release(qapp, window):
    """Let the release thread finish and deliver its queued signals."""
    for _ in range(3):
        thread = window.release_thread
        if thread is not None:
            assert thread.wait(60000)
        qapp.processEvents()
        if window.release_thread is thread:
            break


@pytest.fixture
def repo(tmp_path, monkeypatch):
    if shutil.which("git") is None:
        pytest.skip("git not installed")
    root = tmp_path / "proj"
    root.mkdir()
    (root / "app.py").write_text("print('hi')\n")
    project = ProjectConfig(name="Hi", version="1.0.0")
    project.build.source = str(root / "app.py")
    project.build.output_name = "Hi"
    project.installer.app_version = "1.0.0"
    project.release.repository = "me/app"
    save_project(project, str(root / "p2e.toml"))
    (root / ".gitignore").write_text("dist/\nbuild/\nrelease/\n")
    for args in (["init", "-q", "-b", "main"], ["config", "user.name", "T"],
                 ["config", "user.email", "t@example.com"], ["config", "commit.gpgsign", "false"],
                 ["config", "tag.gpgsign", "false"], ["add", "."],
                 ["commit", "-qm", "feat: say hi"]):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)

    def fake_build(ctx):
        dist = root / "dist"
        dist.mkdir(exist_ok=True)
        (dist / "Hi.exe").write_bytes(b"MZ" + ctx.version.encode() * 50)
        ctx.log("fake build done")
        return BuildOutcome(True, 0)

    monkeypatch.setattr("py2exe_gui.core.release.pipeline.default_build", fake_build)
    return root


def open_repo(window, repo, monkeypatch):
    answer(monkeypatch, "question", QMessageBox.Yes)
    assert window.open_project_path(str(repo / "p2e.toml"))


# ── Version ───────────────────────────────────────────────────────────────


def test_bump_buttons_and_apply_to_every_tab(window):
    tab = window.release_tab
    tab.version_input.setText("1.2.3")
    tab.bump_buttons["minor"].click()
    assert tab.version_input.text() == "1.3.0"
    tab.bump_buttons["major"].click()
    tab.bump_buttons["patch"].click()
    assert tab.version_input.text() == "2.0.1"
    tab.version_input.setText("garbage")
    tab.bump_buttons["patch"].click()
    assert tab.version_input.text() == "0.0.1"

    tab.version_input.setText("3.1.4")
    window.apply_release_version()
    assert window.version_info_tab.vi_file_version.text() == "3.1.4.0"
    assert window.version_info_tab.vi_product_version.text() == "3.1.4.0"
    assert window.installer_tab.inst_version.text() == "3.1.4"
    assert window.runtime_tab.app_version.text() == "3.1.4"


def test_apply_rejects_a_bad_version(window, monkeypatch):
    shown = []
    answer(monkeypatch, "warning", QMessageBox.Ok, shown)
    window.release_tab.version_input.setText("3.1")
    window.apply_release_version()
    assert shown and window.installer_tab.inst_version.text() == "1.0.0"


def test_mismatch_warning(window):
    window.release_tab.version_input.setText("2.0.0")
    window.installer_tab.inst_version.setText("1.9.0")
    window._update_modified()
    label = window.release_tab.mismatch_label
    assert not label.isHidden() and "installer.app_version" in label.text()
    window.apply_release_version()
    window._update_modified()
    assert label.isHidden()


# ── Token ─────────────────────────────────────────────────────────────────


def test_token_is_stored_in_the_keyring_only(window, keyring, tmp_path):
    tab = window.release_tab
    assert plain(tab.token_status.text()) == Ar.RELEASE_TOKEN_NONE
    tab.token_input.setText(TOKEN)
    window.save_github_token()
    assert tab.token_input.text() == ""
    assert keyring.get_password(credentials.KEYRING_SERVICE, credentials.KEYRING_USERNAME) == TOKEN
    assert Ar.RELEASE_TOKEN_FROM_KEYRING in plain(tab.token_status.text())
    assert tab.forget_token_btn.isEnabled()
    window.save_settings()
    assert TOKEN not in open(tmp_path / "s.json", encoding="utf-8").read()
    assert TOKEN not in window.main_tab.log_text()
    assert TOKEN not in json.dumps(window._current_project().to_settings_dict())
    window.forget_github_token()
    assert keyring.store == {}
    assert not tab.forget_token_btn.isEnabled()


def test_token_from_the_environment(window, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", TOKEN)
    window.refresh_token_status()
    assert Ar.RELEASE_TOKEN_FROM_ENV in plain(window.release_tab.token_status.text())


def test_keyring_unavailable(window, monkeypatch):
    monkeypatch.setattr("py2exe_gui.ui.main_window.KEYRING", None)
    shown = []
    answer(monkeypatch, "warning", QMessageBox.Ok, shown)
    window.release_tab.token_input.setText(TOKEN)
    window.save_github_token()
    assert shown and TOKEN not in shown[0]


# ── Notes and repository from git ─────────────────────────────────────────


def test_notes_and_repository_from_git(window, repo, monkeypatch):
    subprocess.run(["git", "remote", "add", "origin", "https://github.com/me/hi.git"],
                   cwd=repo, check=True)
    open_repo(window, repo, monkeypatch)
    window.release_tab.repository.clear()
    window.detect_release_repository()
    assert window.release_tab.repository.text() == "me/hi"
    window.draft_release_notes()
    assert "say hi" in window.release_tab.notes_edit.toPlainText()


def test_no_git_logs_instead(window, tmp_path):
    (tmp_path / "x.py").write_text("")
    window.main_tab.source_input.setText(str(tmp_path / "x.py"))
    window.draft_release_notes()
    window.detect_release_repository()
    log = window.main_tab.log_text()
    assert Ar.LOG_RELEASE_NO_GIT in log and Ar.LOG_RELEASE_NO_REMOTE in log


# ── Dry run ───────────────────────────────────────────────────────────────


def test_dry_run_from_the_tab_changes_nothing(qapp, window, repo, monkeypatch, keyring):
    keyring.set_password(credentials.KEYRING_SERVICE, credentials.KEYRING_USERNAME, TOKEN)
    open_repo(window, repo, monkeypatch)
    window.release_tab.version_input.setText("1.1.0")
    before = (repo / "p2e.toml").read_text()
    assert window.release_tab.dry_run_check.isChecked()
    window.start_release()
    wait_release(qapp, window)
    texts = window.release_tab.step_texts()
    assert all(not t.startswith("○") and not t.startswith("⏳") for t in texts), texts
    assert any("📋" in t for t in texts)
    assert plain(window.release_tab.result_label.text()) == Ar.RELEASE_RESULT_PLANNED
    assert "say hi" in window.release_tab.notes_edit.toPlainText()  # drafted, editable
    assert (repo / "p2e.toml").read_text() == before
    assert not (repo / "release").exists() and not (repo / "dist").exists()
    assert TOKEN not in window.main_tab.log_text()


def test_blocked_plan_is_reported(qapp, window, repo, monkeypatch):
    open_repo(window, repo, monkeypatch)  # no token anywhere
    window.release_tab.version_input.setText("1.1.0")
    shown = []
    answer(monkeypatch, "warning", QMessageBox.Ok, shown)
    window.start_release()
    wait_release(qapp, window)
    assert shown == [Ar.RELEASE_RESULT_BLOCKED]
    publish = window.release_tab.step_texts()[10]
    assert publish.startswith("❌") and Ar.RELEASE_REASON_NO_TOKEN in plain(publish)


def test_start_release_checks(window, tmp_path, monkeypatch):
    shown = []
    answer(monkeypatch, "warning", QMessageBox.Ok, shown)
    window.release_tab.version_input.setText("1.0")
    window.start_release()
    window.release_tab.version_input.setText("1.0.0")
    window.start_release()  # no source
    src = tmp_path / "a.py"
    src.write_text("")
    window.main_tab.source_input.setText(str(src))
    window.size_tab.isolated_radio.setChecked(True)
    window.start_release()  # isolated env missing
    assert shown[0] == Ar.ERR_RELEASE_VERSION.format(version="1.0")
    assert shown[1] == Ar.ERR_NO_SOURCE and shown[2] == Ar.ERR_RELEASE_ENV
    assert window.release_thread is None


# ── A real release, from the window ───────────────────────────────────────


def test_release_from_the_window_against_the_fake_api(qapp, window, repo, monkeypatch, keyring,
                                                      tmp_path):
    keyring.set_password(credentials.KEYRING_SERVICE, credentials.KEYRING_USERNAME, TOKEN)
    open_repo(window, repo, monkeypatch)
    window.release_tab.version_input.setText("1.1.0")
    window.release_tab.dry_run_check.setChecked(False)
    window.release_tab.notes_edit.setPlainText("## ما الجديد\n- تحية\n")
    confirmed = []

    def accept(dialog):
        confirmed.append(dialog.text_view.toPlainText())
        return 1

    monkeypatch.setattr(ReleaseConfirmDialog, "exec_", accept)
    with FakeGitHub(TOKEN) as fake:
        # The window never allows http; the fake API needs it, so only the
        # options class is wrapped here.
        monkeypatch.setattr("py2exe_gui.ui.main_window.ReleaseOptions", functools.partial(
            ReleaseOptions, api_url=fake.url, allow_insecure_localhost=True))
        window.start_release()
        wait_release(qapp, window)  # the plan, then the confirmation…
        wait_release(qapp, window)  # …then the release itself
        uploads = sorted(fake.uploads)
        release = fake.releases[0] if fake.releases else {}

    # The confirmation listed what would be created, tagged and uploaded.
    summary = confirmed[0]
    for expected in ("v1.1.0", "Hi-1.1.0.exe", "SHA256SUMS.txt", "me/app@v1.1.0",
                     str(repo / "p2e.toml")):
        assert expected in summary
    assert uploads == ["Hi-1.1.0-portable.zip", "Hi-1.1.0.exe", "SHA256SUMS.txt"]
    assert release["body"] == "## ما الجديد\n- تحية\n"
    texts = window.release_tab.step_texts()
    assert texts[0].startswith("✅") and texts[10].startswith("✅"), texts
    assert "1.1.0" in window.release_tab.result_label.text()
    assert window.release_tab.open_release_btn.isEnabled()
    # The bump reached every tab and the saved file, and nothing is pending.
    assert window.installer_tab.inst_version.text() == "1.1.0"
    assert load_project(str(repo / "p2e.toml")).project.version == "1.1.0"
    assert not window.is_project_modified()
    tags = subprocess.run(["git", "tag"], cwd=repo, capture_output=True, text=True).stdout
    assert tags.split() == ["v1.1.0"]
    # The token is nowhere but the request headers.
    window.save_settings()
    assert TOKEN not in window.main_tab.log_text()
    for name in ("s.json", "h.json", "p.json"):
        path = tmp_path / name
        if path.exists():
            assert TOKEN not in path.read_text(encoding="utf-8")
    for folder, _dirs, files in os.walk(repo):
        if ".git" in folder:
            continue
        for name in files:
            with open(os.path.join(folder, name), "rb") as f:
                assert TOKEN.encode() not in f.read()


def test_cancelling_the_confirmation_changes_nothing(qapp, window, repo, monkeypatch, keyring):
    keyring.set_password(credentials.KEYRING_SERVICE, credentials.KEYRING_USERNAME, TOKEN)
    open_repo(window, repo, monkeypatch)
    window.release_tab.version_input.setText("1.1.0")
    window.release_tab.dry_run_check.setChecked(False)
    monkeypatch.setattr(ReleaseConfirmDialog, "exec_", lambda _d: 0)
    window.start_release()
    wait_release(qapp, window)
    assert not (repo / "release").exists()
    assert Ar.LOG_RELEASE_CANCELLED in window.main_tab.log_text()


# ── The confirmation dialog ───────────────────────────────────────────────


def test_confirmation_dialog_lists_every_section_in_both_languages(qapp):
    summary = Confirmation(created=["/p/release/1.0.0/App.zip"], commands=["signtool sign /p ***"],
                           commits=["/p/p2e.toml"], tags=["v1.0.0"], pushes=["v1.0.0"],
                           releases=["me/app@v1.0.0"], uploads=["App.zip"])
    for locale, strings in (("ar", Ar), ("en", En)):
        set_locale(locale)
        text = ReleaseConfirmDialog.summary_text(summary)
        for title in ("RELEASE_CONFIRM_CREATED", "RELEASE_CONFIRM_COMMANDS",
                      "RELEASE_CONFIRM_COMMITS", "RELEASE_CONFIRM_TAGS", "RELEASE_CONFIRM_PUSHES",
                      "RELEASE_CONFIRM_RELEASES", "RELEASE_CONFIRM_UPLOADS"):
            assert getattr(strings, title) in text
        # Paths stay left-to-right inside right-to-left text.
        assert "⁦/p/release/1.0.0/App.zip⁩" in text
    assert ReleaseConfirmDialog.summary_text(Confirmation()) == En.RELEASE_CONFIRM_NOTHING
    set_locale("ar")
