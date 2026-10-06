"""What is inside a build, package by package, and what could come out.

PyInstaller writes its tables of contents (``*.toc``) into the work folder as
Python literals: every bundled module, extension, DLL and data file, with the
path it was copied from. Reading them (``ast.literal_eval``: data only, never
executed) gives an exact inventory without opening the EXE or importing
PyInstaller, so it works for one-file and folder builds alike.

Pure-Python modules are stored compressed inside one archive (``PYZ-00.pyz``);
their share of it is estimated in proportion to their source size, which
makes the per-package figures add up to what is really on disk.
"""

import ast
import glob
import os
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from py2exe_gui.constants import STDLIB_MODULES
from py2exe_gui.core.config import BuildConfig
from py2exe_gui.core.diagnostics import build_name, build_root
from py2exe_gui.core.fixes import SEVERITY_INFO, Finding, fix_is_applied, flag_fix
from py2exe_gui.core.knowledge import import_name_for_dist
from py2exe_gui.core.project_doctor import local_module_names

# Groups that are not packages the user chose.
GROUP_RUNTIME = "<python-runtime>"
GROUP_STDLIB = "<stdlib>"
GROUP_SCRIPT = "<your-code>"

_TYPECODES = frozenset({
    "PYMODULE", "PYSOURCE", "BINARY", "EXTENSION", "DATA", "DEPENDENCY",
    "SYMLINK", "SPLASH", "PYZ", "EXECUTABLE",
})
# Folder names in the bundle that belong to a package with another name.
_ALIASES = {
    "_tcl_data": "tkinter", "_tk_data": "tkinter", "tcl": "tkinter", "tk": "tkinter",
    "tcl8": "tkinter", "_tkinter": "tkinter", "tkinter": "tkinter",
    "lib-dynload": GROUP_RUNTIME, "base_library.zip": GROUP_RUNTIME,
}
_RUNTIME_FILE = re.compile(
    r"^(lib)?python\d|^vcruntime|^msvcp|^ucrtbase|^api-ms-win-|^libffi|^libssl|"
    r"^libcrypto|^libz|^libbz2|^liblzma|^libexpat|^libmpdec|^sqlite3|^libsqlite|"
    r"^libreadline|^libncurses|^libtinfo|^libuuid|^libgcc|^libstdc\+\+",
    re.IGNORECASE,
)

# Packages PyInstaller often collects although the app never uses them
# (pulled by another library's optional import). Only these are proposed for
# --exclude-module, and only when the project's own code does not import
# them: excluding something a library really needs breaks the EXE, and the
# smoke test / doctor loop is there to catch that if it happens.
EXCLUDE_CANDIDATES = (
    "tkinter", "PyQt5", "PyQt6", "PySide2", "PySide6", "matplotlib", "IPython",
    "jedi", "parso", "pytest", "_pytest", "notebook", "nbformat", "jupyter_client",
    "jupyter_core", "ipykernel", "docutils", "sphinx", "pygments", "scipy",
    "pandas", "sqlalchemy", "botocore", "boto3", "tornado", "zmq",
)
# Above this a one-file EXE takes noticeably long to start (it unpacks itself
# to a temp folder every launch); folder mode + an installer starts instantly.
ONEFILE_SLOW_BYTES = 120 * 1024 * 1024


@dataclass
class Entry:
    name: str  # destination inside the bundle, or the dotted module name
    source: str
    typecode: str
    size: int = 0


@dataclass
class SizeReport:
    """The inventory of one build."""

    output_path: str = ""
    output_bytes: int = 0          # what is really on disk in dist/
    content_bytes: int = 0         # uncompressed contents, PYZ at its real size
    groups: Dict[str, int] = field(default_factory=dict)
    largest_files: List[Tuple[str, int]] = field(default_factory=list)
    entries: int = 0

    def ranked(self, limit: int = 0) -> List[Tuple[str, int]]:
        ranked = sorted(self.groups.items(), key=lambda kv: (-kv[1], kv[0]))
        return ranked[:limit] if limit else ranked

    @property
    def ok(self) -> bool:
        return self.entries > 0


# ── Reading the TOC files ─────────────────────────────────────────────────


def _walk_entries(node) -> Iterable[Tuple[str, str, str]]:
    """Every ``(name, path, typecode)`` triple anywhere in a TOC literal."""
    if isinstance(node, (list, tuple)):
        if (
            len(node) == 3
            and all(isinstance(x, str) for x in node)
            and node[2] in _TYPECODES
        ):
            yield node[0], node[1], node[2]
            return
        for child in node:
            yield from _walk_entries(child)


def read_toc(path: str) -> List[Entry]:
    try:
        with open(path, encoding="utf-8") as f:
            data = ast.literal_eval(f.read())
    except (OSError, ValueError, SyntaxError, MemoryError, RecursionError):
        return []
    return [Entry(name, src, code) for name, src, code in _walk_entries(data)]


def work_dir_for(config: BuildConfig) -> str:
    """``<root>/build/<name>``: where PyInstaller left its TOC files."""
    return os.path.join(build_root(config), "build", build_name(config))


def _latest(work_dir: str, pattern: str) -> str:
    matches = sorted(glob.glob(os.path.join(work_dir, pattern)))
    return matches[-1] if matches else ""


def group_for(entry: Entry, local_modules: Iterable[str] = ()) -> str:
    """Which package (or runtime/stdlib bucket) an entry belongs to."""
    if entry.typecode == "PYSOURCE":
        return GROUP_SCRIPT if not entry.name.startswith("pyi_rth") else GROUP_RUNTIME
    if entry.typecode == "PYMODULE":
        top = entry.name.split(".")[0]
        if top in local_modules:          # the project's own helpers.py
            return GROUP_SCRIPT
        # PyInstaller's own bootstrap, and the interpreter's build settings.
        if top.startswith(("pyimod", "pyi_", "_sysconfigdata")):
            return GROUP_RUNTIME
        return GROUP_STDLIB if top in STDLIB_MODULES else top
    parts = [p for p in re.split(r"[\\/]", entry.name) if p]
    if not parts:
        return GROUP_RUNTIME
    head = parts[0]
    if head in _ALIASES:
        return _ALIASES[head]
    if len(parts) == 1:
        # A file at the bundle root: the interpreter, its DLLs, stdlib
        # extension modules (_ssl.pyd, unicodedata.so...).
        stem = head.split(".")[0]
        if _RUNTIME_FILE.search(head) or stem.lstrip("_") in STDLIB_MODULES or stem in STDLIB_MODULES:
            return GROUP_RUNTIME
        return stem
    if head.endswith(".libs"):          # numpy.libs, scipy.libs, pillow.libs
        head = import_name_for_dist(head[: -len(".libs")])
    if head.startswith("python3") or head == "lib":   # python3.12/lib-dynload
        return GROUP_RUNTIME
    if head.endswith((".dist-info", ".egg-info")):
        return re.split(r"-\d", head, maxsplit=1)[0].split(".")[0]
    return head


def _file_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def output_path_for(config: BuildConfig) -> str:
    """The EXE (one-file) or the app folder (folder mode) under dist/."""
    name = build_name(config)
    dist = os.path.join(build_root(config), "dist")
    if config.onefile:
        for candidate in (os.path.join(dist, name + ".exe"), os.path.join(dist, name)):
            if os.path.isfile(candidate):
                return candidate
        return ""
    folder = os.path.join(dist, name)
    return folder if os.path.isdir(folder) else ""


def path_size(path: str) -> int:
    """Bytes on disk; symlinks are skipped so shared libraries count once."""
    if os.path.isfile(path):
        return _file_size(path)
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            full = os.path.join(root, name)
            if not os.path.islink(full):
                total += _file_size(full)
    return total


def analyze_build(
    config: BuildConfig, top_files: int = 15, local_modules: Optional[Iterable[str]] = None
) -> SizeReport:
    """Inventory the most recent build of ``config``.

    ``local_modules`` (default: the modules next to the script) are counted
    as the user's own code rather than as packages.
    """
    if local_modules is None:
        project_dir = os.path.dirname(os.path.abspath(config.source)) if config.source else ""
        local_modules = local_module_names(project_dir) if project_dir else set()
    local = set(local_modules)
    report = SizeReport()
    report.output_path = output_path_for(config)
    if report.output_path:
        report.output_bytes = path_size(report.output_path)

    work = work_dir_for(config)
    bundle_toc = _latest(work, "COLLECT-*.toc") if not config.onefile else ""
    bundle_toc = bundle_toc or _latest(work, "PKG-*.toc")
    pyz_toc = _latest(work, "PYZ-*.toc")
    entries = read_toc(bundle_toc) if bundle_toc else []
    modules = [e for e in read_toc(pyz_toc) if e.typecode == "PYMODULE"] if pyz_toc else []
    if not entries and not modules:
        return report

    groups: Dict[str, int] = {}
    files: List[Tuple[str, int]] = []

    def add(group: str, size: int):
        groups[group] = groups.get(group, 0) + size

    # The module archive's real size. In folder mode it is not listed in the
    # bundle TOC (it lives inside the EXE), so read it from the work folder.
    pyz_file = _latest(work, "PYZ-*.pyz")
    pyz_real = _file_size(pyz_file) if pyz_file else 0
    for entry in entries:
        if entry.typecode in ("PYZ", "DEPENDENCY", "SYMLINK"):
            continue
        if entry.typecode == "EXECUTABLE":
            # Bootloader + embedded archive; the archive is counted per module.
            launcher = max(0, _file_size(entry.source) - pyz_real)
            add(GROUP_RUNTIME, launcher)
            files.append((entry.name, launcher))
            continue
        entry.size = _file_size(entry.source)
        add(group_for(entry, local), entry.size)
        files.append((entry.name, entry.size))

    # Spread the archive's real (compressed) size over its modules.
    for module in modules:
        module.size = _file_size(module.source)
    source_total = sum(m.size for m in modules)
    if modules and source_total:
        scale = (pyz_real / source_total) if pyz_real else 1.0
        for module in modules:
            add(group_for(module, local), int(module.size * scale))

    report.groups = {k: v for k, v in groups.items() if v > 0}
    report.content_bytes = sum(report.groups.values())
    report.largest_files = sorted(files, key=lambda f: -f[1])[:top_files]
    report.entries = len(entries) + len(modules)
    return report


# ── Advice ─────────────────────────────────────────────────────────────────


def exclude_suggestions(
    report: SizeReport,
    project_imports: Iterable[str],
    config: Optional[BuildConfig] = None,
    min_bytes: int = 512 * 1024,
) -> List[Finding]:
    """Packages in the bundle that the project's code never imports.

    Each comes as a finding with an ``--exclude-module`` fix, biggest first.
    They are suggestions, not certainties: a library may need one of them.
    """
    used = set(project_imports)
    findings = []
    for group, size in report.ranked():
        if group not in EXCLUDE_CANDIDATES or group in used or size < min_bytes:
            continue
        fix = flag_fix("--exclude-module", group)
        if config is not None and fix_is_applied(config, fix):
            continue
        findings.append(
            Finding(
                "size_exclude_candidate",
                SEVERITY_INFO,
                {"package": group, "size": format_size(size)},
                (fix,),
                origin="build",
            )
        )
    return findings


def indirect_packages(report: SizeReport, project_imports: Iterable[str],
                      min_bytes: int = 1024 * 1024) -> List[Tuple[str, int]]:
    """Third-party packages in the bundle that the project doesn't import itself.

    Many are legitimate dependencies of what it does import; the figure is a
    hint that building in an isolated environment may shed some of them.
    """
    used = set(project_imports)
    special = {GROUP_RUNTIME, GROUP_STDLIB, GROUP_SCRIPT}
    return [
        (group, size)
        for group, size in report.ranked()
        if group not in used and group not in special and size >= min_bytes
    ]


def onefile_too_big(report: SizeReport, config: BuildConfig) -> bool:
    return bool(config.onefile and report.output_bytes >= ONEFILE_SLOW_BYTES)


def size_change(previous: int, current: int) -> Optional[float]:
    """Percentage change from ``previous`` to ``current``, or None without a baseline."""
    if previous <= 0 or current <= 0:
        return None
    return (current - previous) * 100.0 / previous


def format_size(size: int) -> str:
    """Human-readable size: 812 B, 64 KB, 34.6 MB, 1.20 GB."""
    size = max(0, int(size))
    if size < 1024:
        return f"{size} B"
    if size < 1024 ** 2:
        return f"{size / 1024:.0f} KB"
    if size < 1024 ** 3:
        return f"{size / 1024 ** 2:.1f} MB"
    return f"{size / 1024 ** 3:.2f} GB"


def group_label_key(group: str) -> str:
    """Strings key for a special group, or '' for an ordinary package."""
    return {
        GROUP_RUNTIME: "SIZE_GROUP_RUNTIME",
        GROUP_STDLIB: "SIZE_GROUP_STDLIB",
        GROUP_SCRIPT: "SIZE_GROUP_SCRIPT",
    }.get(group, "")


def previous_size(records: Sequence, source: str, output_name: str, skip: int = 0) -> int:
    """Output size of the last successful build of the same script, from history.

    ``skip`` passes over that many matching records first — 1 when the newest
    record is the build being compared.
    """
    for record in records:
        if (
            getattr(record, "success", False)
            and getattr(record, "source", "") == source
            and getattr(record, "output_name", "") == output_name
            and getattr(record, "size_bytes", 0)
        ):
            if skip:
                skip -= 1
                continue
            return int(record.size_bytes)
    return 0
