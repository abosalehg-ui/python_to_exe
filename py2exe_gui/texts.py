"""Locale text for things the core reports as codes — Qt-free.

Shared by the command line (which must never import PyQt5) and the GUI, so a
release step or a Runtime Kit message reads the same in both.
"""

from typing import Dict

from py2exe_gui.core.runtime_kit import TEXT_KEYS
from py2exe_gui.strings import LOCALE_LAYOUT, S, current_locale

_RUNTIME_TEXT_NAMES = {
    "crash_title": "KIT_RT_CRASH_TITLE",
    "crash_message": "KIT_RT_CRASH_MESSAGE",
    "support_prompt": "KIT_RT_SUPPORT_PROMPT",
    "instance_message": "KIT_RT_INSTANCE_MESSAGE",
    "update_title": "KIT_RT_UPDATE_TITLE",
    "update_message": "KIT_RT_UPDATE_MESSAGE",
}

STATUS_ICONS = {
    "pending": "○", "running": "⏳", "planned": "📋", "done": "✅", "skipped": "⏭️",
    "failed": "❌",
}


def runtime_texts() -> Dict[str, str]:
    """What the built app says (crash dialog, second copy, update prompt),
    in the language the developer is using now."""
    return {key: getattr(S, _RUNTIME_TEXT_NAMES[key]) for key in TEXT_KEYS}


def is_rtl() -> bool:
    return LOCALE_LAYOUT.get(current_locale(), "ltr") == "rtl"


def _format(template: str, params: Dict[str, str]) -> str:
    try:
        return template.format(**params)
    except (KeyError, IndexError, ValueError):
        return template


def step_title(key: str) -> str:
    return getattr(S, f"RELEASE_STEP_{key.upper()}", key)


def status_label(status: str) -> str:
    return getattr(S, f"RELEASE_STATUS_{status.upper()}", status)


def reason_text(result) -> str:
    """The translated explanation of a step result ('' when there is none)."""
    if not result.reason:
        return ""
    template = getattr(S, f"RELEASE_REASON_{result.reason.upper()}", result.reason)
    return _format(template, result.params)


def step_line(result) -> str:
    """One line per step: icon, title, explanation."""
    icon = STATUS_ICONS.get(result.status, "•")
    reason = reason_text(result)
    return f"{icon} {step_title(result.key)}" + (f" — {reason}" if reason else "")


def notes_titles() -> Dict[str, str]:
    """Section titles for drafted release notes, in the active locale."""
    keys = ("breaking", "feat", "fix", "perf", "refactor", "docs", "other", "changes",
            "no_changes")
    return {key: getattr(S, f"NOTES_{key.upper()}") for key in keys}


def project_error_text(error) -> str:
    """A ``ProjectFileError`` in the active locale."""
    template = getattr(S, f"PROJECT_ERR_{error.code.upper()}", S.PROJECT_ERR_GENERIC)
    return _format(template, {"detail": error.detail, "code": error.code})
