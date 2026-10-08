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

#: 2.0: optional per-engine hints, under ``"engines": {"<engine>": {...}}``.
#: PyInstaller's needs stay in the top-level fields (every entry predates
#: the other engines), so only the other engines have a section.
ENGINE_HINT_ENGINES = ("nuitka",)
#: Allowed keys of an engine section: ``plugins`` (Nuitka plugins the package
#: needs, ``--enable-plugins``) and ``notes`` ({ar, en}).
ENGINE_HINT_KEYS = ("plugins", "notes")


@dataclass(frozen=True)
class EngineHints:
    """What one package needs from one engine beyond the common fields."""

    plugins: Tuple[str, ...] = ()
    notes: Dict[str, str] = field(default_factory=dict, hash=False, compare=False)


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
    engines: Dict[str, EngineHints] = field(default_factory=dict, hash=False, compare=False)

    @property
    def pip_name(self) -> str:
        """What to ``pip install`` — the import name unless the entry says otherwise."""
        return self.pip or self.name

    def build_fixes(self, engine: str = "pyinstaller") -> Tuple[Fix, ...]:
        """The config changes this package needs, as fixes.

        In PyInstaller's vocabulary (``fixes.localize_fixes`` translates them
        for another engine), plus that engine's own needs (Nuitka plugins).
        """
        fixes = [Fix("hidden_import", m) for m in self.hidden_imports]
        for attr, flag in _FLAG_FIELDS:
            fixes.extend(flag_fix(flag, arg) for arg in getattr(self, attr))
        fixes.extend(self.engine_fixes(engine))
        return tuple(fixes)

    def engine_fixes(self, engine: str) -> Tuple[Fix, ...]:
        """Only what ``engine`` needs on top of the common fields."""
        hints = self.engines.get(engine)
        if hints is None:
            return ()
        return tuple(flag_fix("--enable-plugins", p) for p in hints.plugins)

    def note(self, locale: str, engine: str = "") -> str:
        text = self.notes.get(locale) or self.notes.get("en", "")
        hints = self.engines.get(engine)
        if hints is not None and hints.notes:
            extra = hints.notes.get(locale) or hints.notes.get("en", "")
            text = f"{text} {extra}".strip()
        return text


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
        engines=_engine_hints(name, raw.get("engines", {})),
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


def _engine_hints(name: str, raw) -> Dict[str, EngineHints]:
    if not isinstance(raw, dict):
        raise ValueError(f"{name}.engines must be an object")
    hints = {}
    for engine, section in raw.items():
        where = f"{name}.engines.{engine}"
        if engine not in ENGINE_HINT_ENGINES:
            raise ValueError(f"{where}: unknown engine")
        if not isinstance(section, dict):
            raise ValueError(f"{where} must be an object")
        unknown = set(section) - set(ENGINE_HINT_KEYS)
        if unknown:
            raise ValueError(f"{where}: unknown keys {sorted(unknown)}")
        plugins = section.get("plugins", [])
        if not isinstance(plugins, list) or not all(isinstance(p, str) and p for p in plugins):
            raise ValueError(f"{where}.plugins must be a list of strings")
        notes = section.get("notes", {})
        if not isinstance(notes, dict):
            raise ValueError(f"{where}.notes must be an object")
        hints[engine] = EngineHints(tuple(plugins), {str(k): str(v) for k, v in notes.items()})
    return hints


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


def _normalize_dist(name: str) -> str:
    return name.lower().replace("-", "_").replace(".", "_")


def import_name_for_dist(dist: str, path: Optional[str] = None) -> str:
    """The import name for a distribution name (``Pillow`` → ``PIL``), if known.

    Folders such as ``pillow.libs`` or ``opencv_python.libs`` in a bundle are
    named after the distribution; this maps them back so they are counted
    with the package they belong to.
    """
    wanted = _normalize_dist(dist)
    for name, info in load_knowledge(path).items():
        if info.pip and _normalize_dist(info.pip) == wanted:
            return name
    return dist


def known_packages(path: Optional[str] = None) -> List[str]:
    return sorted(load_knowledge(path))
