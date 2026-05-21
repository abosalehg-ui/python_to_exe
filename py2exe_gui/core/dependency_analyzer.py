"""Pure logic: parse Python source code to discover imported modules."""

import ast
import re
from typing import Iterable, Set

from py2exe_gui.constants import STDLIB_MODULES


def detect_imports(source_code: str) -> Set[str]:
    """Return top-level module names imported in ``source_code``.

    Uses Python's AST when the source parses, falling back to a line-based
    heuristic for unparseable input. Catches static imports
    (``import x``, ``from x import y``) and the common dynamic patterns
    ``__import__("x")`` and ``importlib.import_module("x")``.
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return _line_based_detect(source_code)

    imports: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top:
                    imports.add(top)
        elif isinstance(node, ast.ImportFrom):
            # Skip relative imports (level > 0) — they don't map to external modules.
            if node.module and node.level == 0:
                top = node.module.split(".")[0]
                if top:
                    imports.add(top)
        elif isinstance(node, ast.Call):
            dynamic = _extract_dynamic_import(node)
            if dynamic:
                imports.add(dynamic)
    return imports


def _extract_dynamic_import(call: ast.Call) -> str:
    """Return the module name from __import__/importlib.import_module calls."""
    func = call.func
    if isinstance(func, ast.Name) and func.id == "__import__":
        target = _first_string_arg(call)
        return target.split(".")[0] if target else ""
    if (
        isinstance(func, ast.Attribute)
        and func.attr == "import_module"
        and isinstance(func.value, ast.Name)
        and func.value.id == "importlib"
    ):
        target = _first_string_arg(call)
        return target.split(".")[0] if target else ""
    return ""


def _first_string_arg(call: ast.Call) -> str:
    if not call.args:
        return ""
    arg = call.args[0]
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value
    return ""


def _line_based_detect(source_code: str) -> Set[str]:
    """Fallback heuristic for source that fails to parse."""
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


# requirements.txt parsing  ────────────────────────────────────────────────

# Matches "name", "name[extra]", "name==1.0", "name>=1.0; python_version<'3.9'", etc.
_REQ_NAME = re.compile(r"^([A-Za-z_][A-Za-z0-9._-]*)")


def parse_requirements(content: str) -> Set[str]:
    """Extract package names from requirements.txt content.

    Skips comments, options (``-r``, ``--editable``), VCS URLs, and direct
    references. Returns normalized names (lower-cased, underscores).
    Note: package name ≠ import name for some packages
    (Pillow → PIL, python-dateutil → dateutil). The user can edit the
    detected entries after import.
    """
    names: Set[str] = set()
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(("-", "--")):
            continue
        if line.startswith(("http://", "https://", "git+", "hg+", "svn+", "file:")):
            continue
        if line.lower().startswith("-e ") or " @ " in line:
            continue
        match = _REQ_NAME.match(line)
        if match:
            names.add(match.group(1).lower().replace("-", "_"))
    return names
