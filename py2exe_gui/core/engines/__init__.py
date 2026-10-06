"""Build engines: PyInstaller (the default) behind one ``Engine`` interface.

``get_engine(name)`` and ``engine_for(config)`` are the only entry points the
rest of the app needs; nothing outside this package names an engine class.
"""

from typing import Dict, List

from py2exe_gui.core.config import DEFAULT_ENGINE
from py2exe_gui.core.engines.base import (
    FEATURES,
    MAX_LOG_PERCENT,
    Engine,
    Stage,
    StageTracker,
    UnknownEngineError,
    features_used,
)
from py2exe_gui.core.engines.pyinstaller import PyInstallerEngine

_ENGINES: Dict[str, Engine] = {
    engine.name: engine for engine in (PyInstallerEngine(),)
}


def engine_names() -> List[str]:
    """Every known engine, the default first."""
    return list(_ENGINES)


def is_known_engine(name: str) -> bool:
    return name in _ENGINES


def get_engine(name: str = DEFAULT_ENGINE) -> Engine:
    """The engine called ``name``; ``UnknownEngineError`` when there is none."""
    try:
        return _ENGINES[name or DEFAULT_ENGINE]
    except KeyError:
        raise UnknownEngineError(name) from None


def engine_for(config) -> Engine:
    """The engine a ``BuildConfig`` selects."""
    return get_engine(getattr(config, "engine", "") or DEFAULT_ENGINE)


__all__ = [
    "DEFAULT_ENGINE",
    "FEATURES",
    "MAX_LOG_PERCENT",
    "Engine",
    "PyInstallerEngine",
    "Stage",
    "StageTracker",
    "UnknownEngineError",
    "engine_for",
    "engine_names",
    "features_used",
    "get_engine",
    "is_known_engine",
]
