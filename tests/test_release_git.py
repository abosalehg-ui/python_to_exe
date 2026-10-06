"""Git operations and changelog drafts, against a real repository made in the test."""

import shutil
import subprocess

import pytest

from py2exe_gui.core.release import git
from py2exe_gui.core.release.changelog import (
    DEFAULT_TITLES,
    classify,
    draft_notes,
    group_commits,
    render_notes,
)
from py2exe_gui.core.release.git import Commit, GitError


def sh(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    if shutil.which("git") is None:
        pytest.skip("git not installed")
    path = tmp_path / "repo"
    path.mkdir()
    sh(path, "init", "-q", "-b", "main")
    sh(path, "config", "user.name", "Test")
    sh(path, "config", "user.email", "test@example.com")
    sh(path, "config", "commit.gpgsign", "false")
    sh(path, "config", "tag.gpgsign", "false")
    return path


def commit(repo, message, name="f.txt", content=None):
    (repo / name).write_text(content if content is not None else message, encoding="utf-8")
    sh(repo, "add", name)
    sh(repo, "commit", "-q", "-m", message)


# ── Changelog (pure) ──────────────────────────────────────────────────────


def test_classify_conventional_subjects():
    assert classify("feat: add release tab") == ("feat", "add release tab")
    assert classify("fix(cli): exit code") == ("fix", "**cli:** exit code")
    assert classify("refactor!: drop py3.7") == ("breaking", "drop py3.7")
    assert classify("feat: x", "BREAKING CHANGE: y") == ("breaking", "x")
    assert classify("chore: bump deps")[0] == "hidden"
    assert classify("style: fmt")[0] == "hidden"
    assert classify("weird: thing") == ("other", "thing")
    assert classify("Fix the build") is None
    assert classify("feat:") is None


def test_grouped_notes_list_groups_in_order():
    commits = [Commit("1", "fix: crash on start"), Commit("2", "feat(ui): release tab"),
               Commit("3", "chore: ci"), Commit("4", "Update README"),
               Commit("5", "perf!: faster", "")]
    groups = group_commits(commits)
    assert groups["fix"] == ["crash on start"]
    assert groups["other"] == ["Update README"]
    notes = render_notes(commits)
    assert notes.index("Breaking changes") < notes.index("Features") < notes.index("Fixes")
    assert "ci" not in notes.split("## Other changes")[0]


def test_plain_notes_when_nothing_is_conventional():
    notes = render_notes([Commit("1", "Add a button"), Commit("2", "Tidy up")])
    assert notes == "## Changes\n\n- Add a button\n- Tidy up\n"


def test_translated_titles_and_empty_cases():
    titles = {"feat": "الميزات", "no_changes": "لا تغييرات."}
    assert "## الميزات" in render_notes([Commit("1", "feat: شيء")], titles)
    assert render_notes([], titles) == "لا تغييرات.\n"
    assert render_notes([Commit("1", "chore: x")]) == DEFAULT_TITLES["no_changes"] + "\n"


# ── Git ───────────────────────────────────────────────────────────────────


def test_outside_a_repository(tmp_path):
    if shutil.which("git") is None:
        pytest.skip("git not installed")
    assert git.is_repo(str(tmp_path)) is False
    assert draft_notes(str(tmp_path)) == ""
    assert git.last_tag(str(tmp_path)) == ""
    assert git.remote_slug(str(tmp_path)) == ""
    with pytest.raises(GitError):
        git.head_sha(str(tmp_path))


def test_empty_repository_has_no_notes(repo):
    assert git.is_repo(str(repo))
    assert "No changes" in draft_notes(str(repo))


def test_notes_since_the_last_tag(repo):
    commit(repo, "feat: first feature")
    sh(repo, "tag", "-a", "v1.0.0", "-m", "v1.0.0")
    commit(repo, "fix: a bug", content="2")
    commit(repo, "feat(ui): ميزة جديدة", content="3")
    assert git.last_tag(str(repo)) == "v1.0.0"
    commits = git.commits_since(str(repo), "v1.0.0")
    assert [c.subject for c in commits] == ["feat(ui): ميزة جديدة", "fix: a bug"]
    notes = draft_notes(str(repo))
    assert "first feature" not in notes
    assert "**ui:** ميزة جديدة" in notes and "a bug" in notes


def test_all_history_without_a_tag_and_multiline_bodies(repo):
    commit(repo, "Initial import")
    (repo / "g.txt").write_text("x")
    sh(repo, "add", "g.txt")
    sh(repo, "commit", "-q", "-m", "feat: thing\n\nbody line 1\nBREAKING CHANGE: api")
    commits = git.commits_since(str(repo))
    assert len(commits) == 2
    assert commits[0].body.startswith("body line 1")
    assert "Breaking changes" in draft_notes(str(repo))


def test_tags_create_detect_and_conflict(repo):
    commit(repo, "one")
    head = git.head_sha(str(repo))
    assert git.tag_commit(str(repo), "v1.0.0") == ""
    assert git.create_tag(str(repo), "v1.0.0", "Release v1.0.0") == head
    assert git.tag_commit(str(repo), "v1.0.0") == head
    with pytest.raises(GitError):
        git.create_tag(str(repo), "v1.0.0", "again")


def test_changed_tracked_and_commit_paths(repo):
    commit(repo, "one", name="p2e.toml", content="schema = 1\n")
    (repo / "other.txt").write_text("unrelated")
    sh(repo, "add", "other.txt")
    (repo / "p2e.toml").write_text("schema = 1\n# bumped\n")
    assert "p2e.toml" in git.changed_files(str(repo))
    assert git.is_tracked(str(repo), "p2e.toml")
    assert not git.is_tracked(str(repo), "nope.txt")
    sha = git.commit_paths(str(repo), [str(repo / "p2e.toml")], "Release v1.0.1")
    assert sha == git.head_sha(str(repo))
    # Only the project file went into the commit; the other staged file did not.
    shown = subprocess.run(["git", "show", "--name-only", "--format=", "HEAD"], cwd=repo,
                           capture_output=True, text=True).stdout.split()
    assert shown == ["p2e.toml"]
    assert "other.txt" in git.changed_files(str(repo))


def test_push_tag_to_a_local_remote(repo, tmp_path):
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    sh(repo, "remote", "add", "origin", str(remote))
    commit(repo, "one")
    git.create_tag(str(repo), "v0.1.0", "x")
    git.push_tag(str(repo), "v0.1.0")
    tags = subprocess.run(["git", "tag"], cwd=remote, capture_output=True, text=True).stdout
    assert "v0.1.0" in tags


def test_push_without_a_remote_fails_instead_of_prompting(repo):
    commit(repo, "one")
    git.create_tag(str(repo), "v0.1.0", "x")
    with pytest.raises(GitError):
        git.push_tag(str(repo), "v0.1.0", remote="nowhere")


@pytest.mark.parametrize("url,slug", [
    ("https://github.com/owner/repo.git", "owner/repo"),
    ("https://github.com/owner/repo", "owner/repo"),
    ("git@github.com:owner/my.repo.git", "owner/my.repo"),
    ("ssh://git@github.com/o-1/r_2/", "o-1/r_2"),
    ("https://gitlab.com/owner/repo.git", ""),
    ("", ""),
])
def test_github_slug(url, slug):
    assert git.github_slug(url) == slug


def test_remote_slug(repo):
    sh(repo, "remote", "add", "origin", "https://github.com/me/app.git")
    assert git.remote_slug(str(repo)) == "me/app"


def test_git_missing_is_a_git_error(tmp_path):
    def runner(*_a, **_k):
        raise FileNotFoundError("git")

    with pytest.raises(GitError, match="not installed"):
        git.run_git(["status"], str(tmp_path), runner)
    assert git.is_repo(str(tmp_path), runner) is False

    def boom(*_a, **_k):
        raise subprocess.TimeoutExpired("git", 1)

    with pytest.raises(GitError):
        git.run_git(["status"], str(tmp_path), boom)


def test_git_never_prompts(tmp_path):
    seen = {}

    def runner(cmd, **kwargs):
        seen.update(kwargs["env"])
        return subprocess.CompletedProcess(cmd, 0, "true\n", "")

    assert git.is_repo(str(tmp_path), runner)
    assert seen["GIT_TERMINAL_PROMPT"] == "0"
