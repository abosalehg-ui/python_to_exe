"""Pure logic: parse Python source code to discover imported modules."""

from typing import Iterable, Set

from py2exe_gui.constants import STDLIB_MODULES


def detect_imports(source_code: str) -> Set[str]:
    """Return the set of top-level module names imported in ``source_code``.

    Handles `import x`, `import x, y as z`, and `from x.y import z` forms.
    Dynamic imports (``__import__``, ``importlib``) are not detected — that
    is a Phase 4 enhancement.
    """
    imports: Set[str] = set()
    for line in source_code.split("\n"):
        line = line.strip()
        if line.startswith("import "):
            parts = line[7:].split(",")
            for part in parts:
                module = part.strip().split(" as ")[0].split(".")[0]
                if module:
                    imports.add(module)
        elif line.startswith("from "):
            module = line[5:].split(" import")[0].strip().split(".")[0]
            if module:
                imports.add(module)
    return imports


def filter_non_stdlib(
    modules: Iterable[str],
    existing: Iterable[str] = (),
    stdlib: Iterable[str] = STDLIB_MODULES,
) -> Set[str]:
    """Filter modules to those not already known and not in the stdlib list."""
    existing_set = set(existing)
    stdlib_set = set(stdlib)
    return {m for m in modules if m not in existing_set and m not in stdlib_set}
