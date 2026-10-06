"""The package knowledge base: what popular libraries need to survive freezing.

The data lives in ``py2exe_gui/knowledge/packages.json`` rather than in code so
it can grow by pull request without anyone touching the UI or the doctor, and
so a wrong entry is a one-line data fix. This module only loads and queries it.
"""

import importlib.util
import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from py2exe_gui.core.fixes import Fix, flag_fix

KNOWLEDGE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "knowledge",
    "packages.json",
)

# PyInstaller option for each list field of an entry.
_FLAG_FIELDS = (
    ("collect_data", "--collect-data"),
    ("collect_submodules", "--collect-submodules"),
    ("collect_all", "--collect-all"),
    ("copy_metadata", "--copy-metadata"),
)

QT_BINDINGS = ("PyQt5", "PyQt6", "PySide2", "PySide6")


def default_is_installed(module: str) -> bool:
    """Whether ``module`` can be imported by the Python that runs the build.

    The builder runs PyInstaller with ``sys.executable``, so this interpreter
    is the build interpreter: a module it cannot find is left out of the EXE.
    """
    try:
        return importlib.util.find_spec(module.split(".")[0]) is not None
    except (ImportError, ValueError):
        return False


@dataclass(frozen=True)
class PackageInfo:
    """One knowledge-base entry, keyed by import name."""

    name: str
    pip: str = ""
    hidden_imports: Tuple[str, ...] = ()
    collect_data: Tuple[str, ...] = ()
    collect_submodules: Tuple[str, ...] = ()
    collect_all: Tuple[str, ...] = ()
    copy_metadata: Tuple[str, ...] = ()
    data_dirs: Tuple[str, ...] = ()
    console_streams: bool = False
    qt_binding: bool = False
    large: bool = False
    notes: Dict[str, str] = field(default_factory=dict, hash=False, compare=False)

    @property
    def pip_name(self) -> str:
        """What to ``pip install`` — the import name unless the entry says otherwise."""
        return self.pip or self.name

    def build_fixes(self) -> Tuple[Fix, ...]:
        """The config changes this package needs, as fixes."""
        fixes = [Fix("hidden_import", m) for m in self.hidden_imports]
        for attr, flag in _FLAG_FIELDS:
            fixes.extend(flag_fix(flag, arg) for arg in getattr(self, attr))
        return tuple(fixes)

    def note(self, locale: str) -> str:
        return self.notes.get(locale) or self.notes.get("en", "")


def _entry(name: str, raw: dict) -> PackageInfo:
    def strings(key):
        value = raw.get(key, [])
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise ValueError(f"{name}.{key} must be a list of strings")
        return tuple(value)

    notes = raw.get("notes", {})
    if not isinstance(notes, dict):
        raise ValueError(f"{name}.notes must be an object")
    return PackageInfo(
        name=name,
        pip=str(raw.get("pip", "")),
        hidden_imports=strings("hidden_imports"),
        collect_data=strings("collect_data"),
        collect_submodules=strings("collect_submodules"),
        collect_all=strings("collect_all"),
        copy_metadata=strings("copy_metadata"),
        data_dirs=strings("data_dirs"),
        console_streams=bool(raw.get("console_streams", False)),
        qt_binding=bool(raw.get("qt_binding", False)),
        large=bool(raw.get("large", False)),
        notes={str(k): str(v) for k, v in notes.items()},
    )


def parse_knowledge(data: dict) -> Dict[str, PackageInfo]:
    """Validate and convert the JSON document into entries."""
    packages = data.get("packages")
    if not isinstance(packages, dict):
        raise ValueError("knowledge file has no 'packages' object")
    return {name: _entry(name, raw) for name, raw in packages.items()}


@lru_cache(maxsize=None)
def _load(path: str) -> Dict[str, PackageInfo]:
    try:
        with open(path, encoding="utf-8") as f:
            return parse_knowledge(json.load(f))
    except (OSError, ValueError):
        # A missing or broken knowledge file must not take the app down: the
        # doctor simply knows less.
        return {}


def load_knowledge(path: Optional[str] = None) -> Dict[str, PackageInfo]:
    return _load(path or KNOWLEDGE_FILE)


def lookup(import_name: str, path: Optional[str] = None) -> Optional[PackageInfo]:
    """The entry for a top-level import name, or None."""
    return load_knowledge(path).get(import_name)


def pip_name_for(import_name: str, path: Optional[str] = None) -> str:
    """Best guess at the distribution to install for ``import_name``."""
    top = import_name.split(".")[0]
    info = lookup(top, path)
    return info.pip_name if info else top


def known_packages(path: Optional[str] = None) -> List[str]:
    return sorted(load_knowledge(path))
