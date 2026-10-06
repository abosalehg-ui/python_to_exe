"""The size lab for Nuitka builds: its compilation report plus the output folder.

Nuitka writes no PyInstaller TOC files. It writes an XML compilation report
(``--report=<file>``, verified on Nuitka 4.2.2) that names every module, data
file, extension module and DLL it included, and which package each belongs
to. Read with ``xml.etree`` — data only — and combined with a walk of the
``<name>.dist`` folder, it attributes the bytes on disk:

* each file in the folder goes to the package the report gives it (or, for
  data and unlisted files, its top folder), symlinks counted once;
* the program binary holds the bytecode of the modules left uncompiled (the
  standard library, by Nuitka's default) — its exact size is in the report —
  and, inseparably, the compiled modules plus the Python runtime, counted
  together as ``GROUP_COMPILED``.

Why not split the compiled code per package: the report gives each compiled
module's *object file* size, and on a real build those were about four times
what linking added (PyYAML's objects: 7.9 MB; the binary grew by 1.8 MB over
the same app without it). Dividing the binary by them would invent numbers,
so the size lab shows only what it can measure.
"""

import os
import xml.etree.ElementTree as ET
from typing import Dict, Iterable, List, Optional, Tuple

#: Report entries that name a file copied into the distribution.
_FILE_TAGS = ("included_extension", "included_dll", "data_file")


class NuitkaReport:
    """What a compilation report says about one build."""

    def __init__(self) -> None:
        #: dest path (``/``-separated) → package ('' = the Python runtime).
        self.file_packages: Dict[str, str] = {}
        #: data files: dest path → (size, is the user's own)
        self.data_files: Dict[str, Tuple[int, bool]] = {}
        #: compiled modules: (dotted name, object-file size before linking)
        self.compiled: List[Tuple[str, int]] = []
        #: (dotted name, usage) of the modules kept as bytecode
        self.uncompiled: List[Tuple[str, str]] = []
        self.bytecode_bytes = 0
        self.mode = ""
        self.nuitka_version = ""
        self.ok = False


def read_report(path: str) -> NuitkaReport:
    """Parse a Nuitka compilation report; an unreadable one gives ``ok=False``."""
    report = NuitkaReport()
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return report
    if root.tag != "nuitka-compilation-report":
        return report
    report.mode = root.get("mode", "")
    report.nuitka_version = root.get("nuitka_version", "")
    for tag in _FILE_TAGS:
        for element in root.iter(tag):
            dest = (element.get("dest_path") or element.get("name") or "").replace("\\", "/")
            if not dest:
                continue
            if tag == "data_file":
                tags = (element.get("tags") or "").split(",")
                report.data_files[dest] = (_int(element.get("size")), "user" in tags)
            else:
                report.file_packages[dest] = element.get("package") or ""
    for module in root.iter("module"):
        name = module.get("name", "")
        kind = module.get("kind", "")
        if kind.startswith("Compiled") or kind == "PythonMainModule":
            obj = module.find("./c-compilation-resources/object-file")
            report.compiled.append((name, _int(obj.get("size")) if obj is not None else 0))
        elif kind.startswith("Uncompiled"):
            report.uncompiled.append((name, module.get("usage", "")))
    for data in root.iter("module_data"):
        if data.get("filename") == "__bytecode.const":
            report.bytecode_bytes = _int(data.get("blob_size"))
    report.ok = True
    return report


def _int(value: Optional[str]) -> int:
    try:
        return max(0, int(value or 0))
    except ValueError:
        return 0


def attribute_files(folder: str, report: NuitkaReport, program: str,
                    local: Iterable[str] = ()) -> Tuple[Dict[str, int], List[Tuple[str, int]]]:
    """Bytes per group for every file in ``folder``, and the files with their sizes."""
    from py2exe_gui.core.size_analyzer import (
        GROUP_RUNTIME,
        GROUP_SCRIPT,
        Entry,
        _file_size,
        group_for,
    )

    local = set(local)
    groups: Dict[str, int] = {}
    files: List[Tuple[str, int]] = []

    def add(group: str, size: int) -> None:
        if size > 0:
            groups[group] = groups.get(group, 0) + size

    for root, _dirs, names in os.walk(folder):
        for name in names:
            full = os.path.join(root, name)
            if os.path.islink(full):
                continue
            rel = os.path.relpath(full, folder).replace(os.sep, "/")
            size = _file_size(full)
            files.append((rel, size))
            if rel == program:
                add_program(groups, size, report, local)
                continue
            if rel in report.file_packages:
                package = report.file_packages[rel]
                add(package.split(".")[0] if package else GROUP_RUNTIME, size)
            elif rel in report.data_files and report.data_files[rel][1]:
                add(GROUP_SCRIPT, size)
            else:
                add(group_for(Entry(rel, "", "DATA"), local), size)
    return groups, files


def add_program(groups: Dict[str, int], size: int, report: NuitkaReport,
                local: Iterable[str] = ()) -> None:
    """Split the program binary: stdlib bytecode (exact) and the rest."""
    from py2exe_gui.core.size_analyzer import GROUP_COMPILED, GROUP_STDLIB

    bytecode = min(size, report.bytecode_bytes)
    if bytecode:
        groups[GROUP_STDLIB] = groups.get(GROUP_STDLIB, 0) + bytecode
    if size - bytecode:
        groups[GROUP_COMPILED] = groups.get(GROUP_COMPILED, 0) + size - bytecode


def analyze_nuitka_build(engine, config, top_files: int = 15, local_modules=None):
    """A ``SizeReport`` for the last Nuitka build of ``config``."""
    from py2exe_gui.core.project_doctor import local_module_names
    from py2exe_gui.core.size_analyzer import SizeReport, path_size

    if local_modules is None:
        project_dir = os.path.dirname(os.path.abspath(config.source)) if config.source else ""
        local_modules = local_module_names(project_dir) if project_dir else set()
    result = SizeReport()
    result.output_path = engine.locate_output(config)
    if result.output_path:
        result.output_bytes = path_size(result.output_path)
    report = read_report(engine.report_path(config))
    folder = engine.dist_folder(config)
    if not report.ok or not os.path.isdir(folder):
        return result
    program = engine.output_stem(config)
    for candidate in (program + ".exe", program, program + ".bin"):
        if os.path.isfile(os.path.join(folder, candidate)):
            program = candidate
            break
    groups, files = attribute_files(folder, report, program, local_modules)
    result.groups = {k: v for k, v in groups.items() if v > 0}
    result.content_bytes = sum(result.groups.values())
    result.largest_files = sorted(files, key=lambda f: -f[1])[:top_files]
    result.entries = len(files) + len(report.compiled) + len(report.uncompiled)
    return result
