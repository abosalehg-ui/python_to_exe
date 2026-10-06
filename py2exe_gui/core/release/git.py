"""The few git operations a release needs, through the ``git`` command.

Read-only queries (last tag, log, HEAD, status) are safe in a dry run. The
two that change something — ``create_tag`` and ``push_tag`` — are only called
by the pipeline after the user has confirmed them, and pushing is a separate
opt-in on top of tagging. Nothing here ever prompts: ``GIT_TERMINAL_PROMPT=0``
makes a push without credentials fail instead of hanging on a password.
"""

import os
import re
import subprocess
from dataclasses import dataclass
from typing import Callable, List, Optional

Runner = Callable[..., "subprocess.CompletedProcess"]

# Separators unlikely to appear in commit messages (ASCII unit/record separators).
_FIELD, _RECORD = "\x1f", "\x1e"


class GitError(Exception):
    """A git command failed, or git is not installed."""


@dataclass(frozen=True)
class Commit:
    sha: str
    subject: str
    body: str = ""


def run_git(args: List[str], cwd: str, runner: Optional[Runner] = None, timeout: float = 60) -> str:
    """Run ``git <args>`` in ``cwd`` and return its stdout. Raises ``GitError``."""
    run = runner or subprocess.run
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env.setdefault("LC_ALL", "C")
    try:
        result = run(
            ["git", *args], cwd=cwd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout, env=env,
        )
    except FileNotFoundError as e:
        raise GitError("git is not installed") from e
    except (OSError, subprocess.SubprocessError) as e:
        raise GitError(str(e)) from e
    if result.returncode != 0:
        raise GitError((result.stderr or result.stdout or "").strip() or f"git {args[0]} failed")
    return result.stdout


def is_repo(cwd: str, runner: Optional[Runner] = None) -> bool:
    try:
        return run_git(["rev-parse", "--is-inside-work-tree"], cwd, runner).strip() == "true"
    except GitError:
        return False


def head_sha(cwd: str, runner: Optional[Runner] = None) -> str:
    return run_git(["rev-parse", "HEAD"], cwd, runner).strip()


def last_tag(cwd: str, prefix: str = "v", runner: Optional[Runner] = None) -> str:
    """The most recent tag reachable from HEAD that starts with ``prefix``; '' if none."""
    try:
        return run_git(
            ["describe", "--tags", "--abbrev=0", "--match", f"{prefix}*"], cwd, runner
        ).strip()
    except GitError:
        return ""


def commits_since(cwd: str, tag: str = "", runner: Optional[Runner] = None) -> List[Commit]:
    """Commits in ``tag..HEAD`` (all of HEAD's history when ``tag`` is empty)."""
    revision = f"{tag}..HEAD" if tag else "HEAD"
    output = run_git(
        ["log", "--no-merges", f"--format=%H{_FIELD}%s{_FIELD}%b{_RECORD}", revision],
        cwd, runner,
    )
    commits = []
    for record in output.split(_RECORD):
        record = record.strip("\n")
        if not record.strip():
            continue
        parts = record.split(_FIELD)
        while len(parts) < 3:
            parts.append("")
        commits.append(Commit(parts[0].strip(), parts[1].strip(), parts[2].strip()))
    return commits


def tag_commit(cwd: str, tag: str, runner: Optional[Runner] = None) -> str:
    """The commit ``tag`` points to, or '' when the tag does not exist."""
    try:
        return run_git(["rev-parse", "-q", "--verify", f"refs/tags/{tag}^{{commit}}"],
                       cwd, runner).strip()
    except GitError:
        return ""


def changed_files(cwd: str, runner: Optional[Runner] = None) -> List[str]:
    """Paths with uncommitted changes (``git status --porcelain``)."""
    output = run_git(["status", "--porcelain", "--untracked-files=no"], cwd, runner)
    return [line[3:].strip() for line in output.splitlines() if len(line) > 3]


def is_tracked(cwd: str, path: str, runner: Optional[Runner] = None) -> bool:
    try:
        run_git(["ls-files", "--error-unmatch", "--", path], cwd, runner)
    except GitError:
        return False
    return True


def commit_paths(cwd: str, paths: List[str], message: str,
                 runner: Optional[Runner] = None) -> str:
    """Commit exactly ``paths`` (nothing else that happens to be staged)."""
    run_git(["add", "--", *paths], cwd, runner)
    run_git(["commit", "-m", message, "--only", "--", *paths], cwd, runner)
    return head_sha(cwd, runner)


def create_tag(cwd: str, tag: str, message: str, runner: Optional[Runner] = None) -> str:
    """Create the annotated tag ``tag`` at HEAD. Returns the commit it points to."""
    run_git(["tag", "-a", tag, "-m", message], cwd, runner)
    return tag_commit(cwd, tag, runner)


def push_tag(cwd: str, tag: str, remote: str = "origin", runner: Optional[Runner] = None) -> None:
    run_git(["push", remote, f"refs/tags/{tag}"], cwd, runner, timeout=300)


_GITHUB_REMOTE = re.compile(
    r"github\.com[:/]+(?P<owner>[A-Za-z0-9-]+)/(?P<repo>[A-Za-z0-9._-]+?)(?:\.git)?/?$"
)


def github_slug(url: str) -> str:
    """``owner/repo`` from an https or ssh GitHub remote URL; '' otherwise."""
    match = _GITHUB_REMOTE.search((url or "").strip())
    return f"{match.group('owner')}/{match.group('repo')}" if match else ""


def remote_slug(cwd: str, remote: str = "origin", runner: Optional[Runner] = None) -> str:
    try:
        return github_slug(run_git(["remote", "get-url", remote], cwd, runner))
    except GitError:
        return ""
