"""Follow a script's imports through the project's own modules.

A script that does ``import helpers`` pulls in whatever ``helpers.py``
imports too. Looking at the entry script alone misses those packages, so an
isolated build environment created from it would lack them, and the doctor
would not warn that they are missing. This module walks the local import
graph (parse only, never execute) and returns every third-party top-level
module the project needs.
"""

import os
from typing import Iterable, List, Set

from py2exe_gui.core.dependency_analyzer import detect_imports, filter_non_stdlib

# Hard caps so a huge folder (or a vendored copy of a library) cannot make the
# scan slow: the doctor runs it as the user types.
MAX_FILES = 300
_SKIP_DIRS = frozenset({
    "build", "dist", "venv", ".venv", "env", "__pycache__", ".git", "node_modules",
    "site-packages", ".tox", ".mypy_cache", ".pytest_cache",
})


def _local_targets(project_dir: str, name: str) -> List[str]:
    """Files that ``import name`` resolves to inside the project, if any."""
    module = os.path.join(project_dir, name + ".py")
    if os.path.isfile(module):
        return [module]
    package = os.path.join(project_dir, name)
    if os.path.isfile(os.path.join(package, "__init__.py")):
        files = []
        for root, dirs, names in os.walk(package):
            dirs[:] = sorted(d for d in dirs if d not in _SKIP_DIRS)
            files.extend(os.path.join(root, n) for n in sorted(names) if n.endswith(".py"))
        return files
    return []


def _read_imports(path: str) -> Set[str]:
    try:
        with open(path, encoding="utf-8") as f:
            return detect_imports(f.read())
    except (OSError, UnicodeDecodeError, ValueError):
        return set()


def project_imports(source: str, max_files: int = MAX_FILES) -> Set[str]:
    """Top-level modules imported by ``source`` and the local modules it uses.

    Local module names themselves are not in the result: only what they, in
    turn, import from outside the project (stdlib included; filter with
    ``third_party_imports``).
    """
    project_dir = os.path.dirname(os.path.abspath(source))
    seen_files: Set[str] = set()
    local_names: Set[str] = set()
    found: Set[str] = set()
    queue = [os.path.abspath(source)]

    while queue and len(seen_files) < max_files:
        path = queue.pop(0)
        if path in seen_files:
            continue
        seen_files.add(path)
        # Relative imports are skipped by detect_imports: they name modules of
        # a local package, and the whole package is queued already.
        names = _read_imports(path)
        for name in sorted(names):
            targets = _local_targets(project_dir, name)
            if targets:
                local_names.add(name)
                queue.extend(t for t in targets if t not in seen_files)
            else:
                found.add(name)
    return found - local_names


def third_party_imports(source: str, extra_local: Iterable[str] = ()) -> Set[str]:
    """``project_imports`` without the standard library."""
    return filter_non_stdlib(project_imports(source), existing=extra_local)
