"""Project doctor: find what will break *after* freezing, before building.

Every check here targets code that runs fine under ``python app.py`` and fails
only once PyInstaller has bundled it — the failures the command line gives no
warning about. The source is parsed, never executed.

The report is a list of ``Finding`` objects (see ``fixes.py``); most come
with fixes that can be applied to the build configuration in one click.
"""

import ast
import os
from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Optional, Set

from py2exe_gui.core.config import BuildConfig
from py2exe_gui.core.dependency_analyzer import detect_imports, filter_non_stdlib
from py2exe_gui.core.fixes import (
    FIX_ADD_DATA,
    FIX_CONSOLE,
    FIX_SET_SOURCE,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    Finding,
    Fix,
    finding_resolved,
    fix_is_applied,
    flag_fix,
    readiness_score,
    runtime_fix,
    sort_findings,
)
from py2exe_gui.core.icon_studio import read_ico_file_sizes
from py2exe_gui.core.knowledge import (
    QT_BINDINGS,
    default_is_installed,
    load_knowledge,
    pip_name_for,
)
from py2exe_gui.core.project_scan import project_imports
from py2exe_gui.core.runtime_kit import PACKAGE as RUNTIME_PACKAGE
from py2exe_gui.core.runtime_kit import validate as validate_runtime_kit

# Folder names that are never data: build output, environments, tooling.
_IGNORED_DIRS = frozenset({
    "build", "dist", "venv", ".venv", "env", ".env", "__pycache__", ".git",
    ".idea", ".vscode", "node_modules", ".mypy_cache", ".pytest_cache",
})
# Script names conventionally used as an entry point, in preference order.
_ENTRY_NAMES = ("main.py", "__main__.py", "app.py", "run.py", "start.py")
# Don't scan huge folders for entry points; the doctor must stay instant.
_MAX_ENTRY_SCAN = 60
_MAX_LITERAL_LEN = 260


@dataclass
class DoctorReport:
    """Everything the doctor found for one script."""

    source: str
    findings: List[Finding] = field(default_factory=list)
    imports: Set[str] = field(default_factory=set)
    third_party: Set[str] = field(default_factory=set)

    @property
    def score(self) -> int:
        return readiness_score(self.findings)

    def fixes(self) -> List[Fix]:
        return [fix for f in self.findings for fix in f.fixes]

    def count(self, severity: str) -> int:
        return sum(1 for f in self.findings if f.severity == severity)


def examine(
    source: str,
    config: Optional[BuildConfig] = None,
    is_installed: Callable[[str], bool] = default_is_installed,
    knowledge_path: Optional[str] = None,
) -> DoctorReport:
    """Run every check against ``source`` built with ``config``."""
    config = config or BuildConfig(source=source)
    report = DoctorReport(source=source)

    try:
        with open(source, encoding="utf-8") as f:
            code = f.read()
    except (OSError, UnicodeDecodeError) as e:
        report.findings.append(
            Finding("source_unreadable", SEVERITY_ERROR, {"error": str(e)})
        )
        return report

    try:
        tree = ast.parse(code, filename=source)
    except SyntaxError as e:
        report.findings.append(
            Finding(
                "syntax_error",
                SEVERITY_ERROR,
                {"line": str(e.lineno or 0), "error": e.msg or ""},
            )
        )
        return report

    project_dir = os.path.dirname(os.path.abspath(source))
    local = local_module_names(project_dir)
    # The script's own imports plus those of the local modules it uses: a
    # package imported only by helpers.py is just as missing from the EXE.
    report.imports = detect_imports(code) | project_imports(source)
    report.third_party = {m for m in filter_non_stdlib(report.imports) if m not in local}
    # The Runtime Kit is bundled by the converter, not installed in the build
    # environment: never report it as a missing package.
    uses_runtime = RUNTIME_PACKAGE in report.third_party
    report.third_party.discard(RUNTIME_PACKAGE)
    # An interpreter other than this one is asked in a single subprocess.
    prefetch = getattr(is_installed, "prefetch", None)
    if prefetch is not None:
        prefetch(report.third_party | set(QT_BINDINGS))
    windowed = config.windowed or config.noconsole

    findings: List[Finding] = []
    findings += _check_missing_packages(report.third_party, is_installed, knowledge_path)
    findings += _check_knowledge(
        report.third_party, config, project_dir, windowed, is_installed, knowledge_path
    )
    findings += _check_data_files(tree, code, config, project_dir, source)
    findings += _check_multiprocessing(tree, report.imports)
    if windowed:
        findings += _check_windowed(tree, config)
    findings += _check_entry_point(tree, source, project_dir)
    findings += _check_icon(config)
    findings += _check_runtime_kit(config, uses_runtime)

    report.findings = sort_findings(f for f in findings if not finding_resolved(config, f))
    return report


# ── Helpers ────────────────────────────────────────────────────────────────


def local_module_names(project_dir: str) -> Set[str]:
    """Modules and packages that live next to the script (not third-party)."""
    names: Set[str] = set()
    try:
        entries = os.listdir(project_dir)
    except OSError:
        return names
    for entry in entries:
        path = os.path.join(project_dir, entry)
        if entry.endswith((".py", ".pyw")) and os.path.isfile(path):
            names.add(os.path.splitext(entry)[0])
        elif os.path.isdir(path) and os.path.isfile(os.path.join(path, "__init__.py")):
            names.add(entry)
    return names


def _is_main_guard(node: ast.AST) -> bool:
    """``if __name__ == "__main__":`` in either operand order."""
    if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
        return False
    test = node.test
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        return False
    sides = [test.left, test.comparators[0]]
    has_name = any(isinstance(s, ast.Name) and s.id == "__name__" for s in sides)
    has_main = any(isinstance(s, ast.Constant) and s.value == "__main__" for s in sides)
    return has_name and has_main


def _names_used(tree: ast.AST) -> Set[str]:
    """Every bare name and attribute name in the tree."""
    names: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


def _sys_stream(node: ast.AST) -> str:
    """'stdout'/'stderr'/'stdin' when ``node`` is ``sys.<stream>``, else ''."""
    if (
        isinstance(node, ast.Attribute)
        and node.attr in ("stdout", "stderr", "stdin")
        and isinstance(node.value, ast.Name)
        and node.value.id == "sys"
    ):
        return node.attr
    return ""


def _covered(path: str, bundled: Iterable[str]) -> bool:
    """True when ``path`` is, or sits inside, something already bundled."""
    target = os.path.normcase(os.path.abspath(path))
    for item in bundled:
        root = os.path.normcase(os.path.abspath(item))
        if target == root or target.startswith(root.rstrip("\\/") + os.sep):
            return True
    return False


# ── Checks ─────────────────────────────────────────────────────────────────


def _check_missing_packages(third_party, is_installed, knowledge_path) -> List[Finding]:
    """An import the build interpreter can't resolve is silently left out.

    PyInstaller only warns in a file nobody reads, then the EXE dies on start
    with ModuleNotFoundError. This is the most common failure of all.
    """
    findings = []
    for module in sorted(third_party):
        if not is_installed(module):
            findings.append(
                Finding(
                    "missing_package",
                    SEVERITY_ERROR,
                    {"module": module, "pip": pip_name_for(module, knowledge_path)},
                )
            )
    return findings


def _check_knowledge(
    third_party, config, project_dir, windowed, is_installed, knowledge_path
) -> List[Finding]:
    knowledge = load_knowledge(knowledge_path)
    findings: List[Finding] = []

    for module in sorted(third_party):
        info = knowledge.get(module)
        if info is None:
            continue

        needed = tuple(f for f in info.build_fixes() if not fix_is_applied(config, f))
        if needed:
            findings.append(
                Finding("package_needs_collect", SEVERITY_WARNING, {"package": module}, needed)
            )

        for folder in info.data_dirs:
            path = os.path.join(project_dir, folder)
            if os.path.isdir(path) and not _covered(path, config.extra_files):
                findings.append(
                    Finding(
                        "package_data_dir",
                        SEVERITY_WARNING,
                        {"package": module, "folder": folder},
                        (Fix(FIX_ADD_DATA, path),),
                    )
                )

        if info.console_streams and windowed and not config.runtime_kit.log_redirect:
            findings.append(
                Finding(
                    "package_console_streams",
                    SEVERITY_ERROR,
                    {"package": module},
                    (Fix(FIX_CONSOLE),),
                    snippet="silence_streams",
                    alternatives=(runtime_fix("log_redirect"),),
                )
            )

        if info.large:
            findings.append(Finding("large_package", SEVERITY_INFO, {"package": module}))

    # Qt: PyInstaller refuses to collect more than one binding.
    used = [b for b in QT_BINDINGS if b in third_party]
    if len(used) > 1:
        findings.append(
            Finding("multiple_qt_bindings", SEVERITY_ERROR, {"bindings": ", ".join(used)})
        )
    elif len(used) == 1:
        others = tuple(
            flag_fix("--exclude-module", b)
            for b in QT_BINDINGS
            if b != used[0] and is_installed(b)
        )
        others = tuple(f for f in others if not fix_is_applied(config, f))
        if others:
            findings.append(
                Finding(
                    "other_qt_bindings_installed",
                    SEVERITY_INFO,
                    {"binding": used[0]},
                    others,
                )
            )
    return findings


def _string_literals(tree: ast.AST) -> Iterable[str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
            if 0 < len(value) <= _MAX_LITERAL_LEN and "\n" not in value:
                yield value


def _relative_data_target(literal: str, project_dir: str, source: str) -> str:
    """The top-level project item ``literal`` refers to, or '' if none.

    Only strings that name something that actually exists next to the script
    count, which keeps false positives close to zero: a string is reported
    because the file is really there, not because it looks like a path.
    """
    text = literal.strip().replace("\\", "/")
    if not text or text.startswith(("/", "http:", "https:", "~")) or ":" in text:
        return ""
    if text.startswith("./"):
        text = text[2:]
    parts = [p for p in text.split("/") if p]
    if not parts or parts[0] in (".", "..") or parts[0] in _IGNORED_DIRS:
        return ""
    if parts[-1].endswith((".py", ".pyw", ".pyc")):
        return ""

    candidate = os.path.normpath(os.path.join(project_dir, *parts))
    if not os.path.exists(candidate) or _covered(candidate, [source]):
        return ""
    top = os.path.join(project_dir, parts[0])
    if len(parts) == 1:
        if os.path.isdir(top):
            # A bare word that happens to match a folder: only count real
            # data folders, not Python packages imported by name.
            if os.path.isfile(os.path.join(top, "__init__.py")):
                return ""
        elif "." not in parts[0]:
            return ""
    return top


def _check_data_files(tree, code, config, project_dir, source) -> List[Finding]:
    targets = {}
    for literal in _string_literals(tree):
        top = _relative_data_target(literal, project_dir, source)
        if top and top not in targets:
            targets[top] = literal

    findings: List[Finding] = []
    for top, literal in sorted(targets.items()):
        if _covered(top, config.extra_files):
            continue
        findings.append(
            Finding(
                "data_not_bundled",
                SEVERITY_WARNING,
                {"path": os.path.basename(top), "literal": literal},
                (Fix(FIX_ADD_DATA, top),),
            )
        )

    # Bundling the file is half the job: a relative path is resolved against
    # the *working directory*, which is wherever the EXE was started from,
    # while the bundled copy sits in the extraction folder.
    resolves_itself = any(m in code for m in ("_MEIPASS", "__file__", "resource_path"))
    if targets and not resolves_itself:
        example = sorted(targets.values())[0]
        # With the Runtime Kit's resource_path on, the function is already in
        # the EXE: one import line instead of a function to paste.
        snippet = (
            "runtime_resource_path" if config.runtime_kit.resource_path else "resource_path"
        )
        findings.append(
            Finding(
                "relative_paths",
                SEVERITY_WARNING,
                {"example": example},
                snippet=snippet,
            )
        )
    return findings


def _check_multiprocessing(tree, imports) -> List[Finding]:
    """Without freeze_support() a frozen EXE re-launches itself endlessly."""
    names = _names_used(tree)
    uses_processes = "multiprocessing" in imports or "ProcessPoolExecutor" in names
    if uses_processes and "freeze_support" not in names:
        return [Finding("missing_freeze_support", SEVERITY_ERROR, snippet="freeze_support")]
    return []


def _check_windowed(tree, config) -> List[Finding]:
    """In a windowed EXE sys.stdin/stdout/stderr are None.

    The Runtime Kit's log redirection gives stdout/stderr a file to write to,
    which resolves the stream findings (not ``input()``: there is still no
    keyboard to read from).
    """
    findings: List[Finding] = []
    reassigned: Set[str] = set()
    used: Set[str] = set()
    calls_input = False

    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                stream = _sys_stream(target)
                if stream:
                    reassigned.add(stream)
        elif isinstance(node, ast.Attribute):
            # sys.stdout.write(...) — an attribute *of* the stream. Plain
            # print() is safe: it does nothing when sys.stdout is None.
            stream = _sys_stream(node.value)
            if stream:
                used.add(stream)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "input"
        ):
            calls_input = True

    if calls_input and "stdin" not in reassigned:
        findings.append(Finding("input_in_windowed", SEVERITY_ERROR, {}, (Fix(FIX_CONSOLE),)))
    if config.runtime_kit.log_redirect:
        return findings
    for stream in sorted(used - reassigned - {"stdin"}):
        findings.append(
            Finding(
                "stream_in_windowed",
                SEVERITY_ERROR,
                {"stream": f"sys.{stream}"},
                (Fix(FIX_CONSOLE),),
                snippet="silence_streams",
                alternatives=(runtime_fix("log_redirect"),),
            )
        )
    return findings


def has_entry_point(tree: ast.Module) -> bool:
    """Whether running the module does anything beyond defining things."""
    passive = (
        ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef,
        ast.ClassDef, ast.Assign, ast.AnnAssign, ast.Pass,
    )
    for node in tree.body:
        if _is_main_guard(node):
            return True
        if isinstance(node, passive):
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue  # docstring or a stray literal
        return True
    return False


def find_entry_candidates(project_dir: str, exclude: str = "") -> List[str]:
    """Scripts next to ``exclude`` that look like an entry point."""
    try:
        entries = sorted(os.listdir(project_dir))
    except OSError:
        return []
    scripts = [e for e in entries if e.endswith(".py")][:_MAX_ENTRY_SCAN]
    ordered = [n for n in _ENTRY_NAMES if n in scripts]
    ordered += [n for n in scripts if n not in ordered]

    excluded = os.path.normcase(os.path.abspath(exclude)) if exclude else ""
    found = []
    for name in ordered:
        path = os.path.join(project_dir, name)
        if os.path.normcase(os.path.abspath(path)) == excluded:
            continue
        try:
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except (OSError, SyntaxError, UnicodeDecodeError, ValueError):
            continue
        if any(_is_main_guard(n) for n in tree.body):
            found.append(path)
    return found


def _check_entry_point(tree, source, project_dir) -> List[Finding]:
    """A module that only defines functions builds an EXE that does nothing."""
    if has_entry_point(tree):
        return []
    candidates = find_entry_candidates(project_dir, exclude=source)
    if candidates:
        return [
            Finding(
                "no_entry_point",
                SEVERITY_WARNING,
                {"candidate": os.path.basename(candidates[0])},
                (Fix(FIX_SET_SOURCE, candidates[0]),),
                snippet="main_guard",
            )
        ]
    return [Finding("no_entry_point_alone", SEVERITY_WARNING, snippet="main_guard")]


def _check_icon(config) -> List[Finding]:
    icon = config.icon
    if not icon or not os.path.isfile(icon):
        return []
    sizes = read_ico_file_sizes(icon)
    name = os.path.basename(icon)
    if sizes is None:
        return [Finding("icon_not_ico", SEVERITY_WARNING, {"icon": name})]
    if len(sizes) == 1:
        return [Finding("icon_single_size", SEVERITY_INFO, {"icon": name, "size": str(sizes[0])})]
    return []


def _check_runtime_kit(config, uses_runtime: bool) -> List[Finding]:
    """The Runtime Kit's own settings, and code that relies on it."""
    findings = validate_runtime_kit(config.runtime_kit, config.onefile)
    if uses_runtime and not config.runtime_kit.enabled:
        # `from p2e_runtime import ...` with the kit off: the package is not
        # bundled and the EXE dies with ModuleNotFoundError.
        findings.append(
            Finding(
                "kit_imported_not_enabled",
                SEVERITY_ERROR,
                {},
                (runtime_fix("resource_path"),),
            )
        )
    return findings
