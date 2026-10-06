"""Draft release notes from the commits since the last tag.

Commits that follow Conventional Commits (``feat: …``, ``fix(ui): …``,
``refactor!: …``) are grouped by type; when none of them do, the notes are a
plain list of commit subjects. Either way the result is a *draft*: the GUI
shows it in an editor and the CLI takes ``--notes FILE`` instead.
"""

import re
from typing import Dict, List, Optional, Sequence

from py2exe_gui.core.release.git import (
    Commit,
    GitError,
    Runner,
    commits_since,
    is_repo,
    last_tag,
)

_CONVENTIONAL = re.compile(
    r"^(?P<type>[A-Za-z]+)(?:\((?P<scope>[^)]*)\))?(?P<breaking>!)?:\s*(?P<desc>\S.*)$"
)

#: Group key for each conventional type, in the order the notes list them.
GROUP_ORDER = ("breaking", "feat", "fix", "perf", "refactor", "docs", "other")
_TYPE_GROUP = {
    "feat": "feat", "feature": "feat",
    "fix": "fix", "bugfix": "fix",
    "perf": "perf",
    "refactor": "refactor",
    "docs": "docs", "doc": "docs",
}
#: Types that are noise in user-facing notes.
_HIDDEN_TYPES = frozenset({"chore", "ci", "build", "test", "tests", "style"})

DEFAULT_TITLES = {
    "breaking": "Breaking changes",
    "feat": "Features",
    "fix": "Fixes",
    "perf": "Performance",
    "refactor": "Refactoring",
    "docs": "Documentation",
    "other": "Other changes",
    "changes": "Changes",
    "no_changes": "No changes since the last release.",
}


def classify(subject: str, body: str = "") -> Optional[tuple]:
    """``(group, text)`` for a conventional subject; None when not conventional."""
    match = _CONVENTIONAL.match(subject.strip())
    if not match:
        return None
    kind = match.group("type").lower()
    text = match.group("desc").strip()
    if match.group("scope"):
        text = f"**{match.group('scope').strip()}:** {text}"
    if match.group("breaking") or "BREAKING CHANGE" in body:
        return "breaking", text
    if kind in _HIDDEN_TYPES:
        return "hidden", text
    return _TYPE_GROUP.get(kind, "other"), text


def group_commits(commits: Sequence[Commit]) -> Dict[str, List[str]]:
    """Commit texts per group. Only conventional commits are grouped."""
    groups: Dict[str, List[str]] = {key: [] for key in GROUP_ORDER}
    for commit in commits:
        found = classify(commit.subject, commit.body)
        if found is None:
            groups["other"].append(commit.subject.strip())
        elif found[0] != "hidden":
            groups[found[0]].append(found[1])
    return groups


def render_notes(commits: Sequence[Commit], titles: Optional[Dict[str, str]] = None) -> str:
    """Markdown notes for ``commits`` (newest first, as git log lists them)."""
    t = dict(DEFAULT_TITLES)
    t.update(titles or {})
    if not commits:
        return t["no_changes"] + "\n"
    conventional = any(classify(c.subject, c.body) is not None for c in commits)
    if not conventional:
        lines = [f"## {t['changes']}", ""]
        lines += [f"- {c.subject.strip()}" for c in commits if c.subject.strip()]
        return "\n".join(lines) + "\n"
    groups = group_commits(commits)
    sections = []
    for key in GROUP_ORDER:
        if groups[key]:
            sections.append("\n".join([f"## {t[key]}", ""] + [f"- {x}" for x in groups[key]]))
    if not sections:
        return t["no_changes"] + "\n"
    return "\n\n".join(sections) + "\n"


def draft_notes(cwd: str, tag_prefix: str = "v", titles: Optional[Dict[str, str]] = None,
                runner: Optional[Runner] = None) -> str:
    """Notes for ``git log <last-tag>..HEAD`` in ``cwd``; '' outside a repository."""
    if not is_repo(cwd, runner):
        return ""
    tag = last_tag(cwd, tag_prefix, runner)
    try:
        commits = commits_since(cwd, tag, runner)
    except GitError:  # a repository without commits yet
        commits = []
    return render_notes(commits, titles)
