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
    # Phase 6: new built-in templates
    "fastapi": {
        "windowed": False,
        "onefile": True,
        "hidden_imports": ["fastapi", "uvicorn", "starlette", "pydantic"],
    },
    "streamlit": {
        "windowed": False,
        "onefile": False,
        "hidden_imports": ["streamlit", "altair", "click", "tornado"],
    },
    "kivy": {
        "windowed": True,
        "onefile": True,
        "hidden_imports": ["kivy"],
    },
    "discord_bot": {
        "windowed": False,
        "onefile": True,
        "hidden_imports": ["discord", "aiohttp"],
    },
    "click_cli": {
        "windowed": False,
        "onefile": True,
        "hidden_imports": ["click"],
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
    "fastapi": "TPL_FASTAPI_NAME",
    "streamlit": "TPL_STREAMLIT_NAME",
    "kivy": "TPL_KIVY_NAME",
    "discord_bot": "TPL_DISCORD_NAME",
    "click_cli": "TPL_CLICK_NAME",
    "custom": "TPL_CUSTOM_NAME",
}

_DESC_ATTR = {
    "gui": "TPL_GUI_DESC",
    "console": "TPL_CONSOLE_DESC",
    "web": "TPL_WEB_DESC",
    "data": "TPL_DATA_DESC",
    "game": "TPL_GAME_DESC",
    "fastapi": "TPL_FASTAPI_DESC",
    "streamlit": "TPL_STREAMLIT_DESC",
    "kivy": "TPL_KIVY_DESC",
    "discord_bot": "TPL_DISCORD_DESC",
    "click_cli": "TPL_CLICK_DESC",
    "custom": "TPL_CUSTOM_DESC",
}


def template_name(key: str) -> str:
    """Localized display name for a template key."""
    return getattr(S, _NAME_ATTR[key])


def template_description(key: str) -> str:
    """Localized description for a template key."""
    return getattr(S, _DESC_ATTR[key])
