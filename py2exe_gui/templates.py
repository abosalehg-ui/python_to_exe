"""Pre-configured build templates for common project types.

Templates are keyed by stable English identifiers; their localized display
names live in strings.py (see TPL_*_NAME / TPL_*_DESC) and are looked up
through the helpers below.
"""

from py2exe_gui.strings import S

TEMPLATES = {
    "gui": {
        "windowed": True,
        "onefile": True,
        "hidden_imports": ["PyQt5", "PyQt5.QtWidgets", "PyQt5.QtCore", "PyQt5.QtGui"],
    },
    "console": {
        "windowed": False,
        "onefile": True,
        "hidden_imports": [],
    },
    "web": {
        "windowed": False,
        "onefile": False,
        "hidden_imports": ["flask", "jinja2", "werkzeug"],
    },
    "data": {
        "windowed": False,
        "onefile": True,
        "hidden_imports": ["pandas", "numpy", "openpyxl"],
    },
    "game": {
        "windowed": True,
        "onefile": False,
        "hidden_imports": ["pygame"],
    },
    "custom": {
        "windowed": False,
        "onefile": True,
        "hidden_imports": [],
    },
}

_NAME_ATTR = {
    "gui": "TPL_GUI_NAME",
    "console": "TPL_CONSOLE_NAME",
    "web": "TPL_WEB_NAME",
    "data": "TPL_DATA_NAME",
    "game": "TPL_GAME_NAME",
    "custom": "TPL_CUSTOM_NAME",
}

_DESC_ATTR = {
    "gui": "TPL_GUI_DESC",
    "console": "TPL_CONSOLE_DESC",
    "web": "TPL_WEB_DESC",
    "data": "TPL_DATA_DESC",
    "game": "TPL_GAME_DESC",
    "custom": "TPL_CUSTOM_DESC",
}


def template_name(key: str) -> str:
    """Localized display name for a template key."""
    return getattr(S, _NAME_ATTR[key])


def template_description(key: str) -> str:
    """Localized description for a template key."""
    return getattr(S, _DESC_ATTR[key])
