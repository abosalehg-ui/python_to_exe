"""Classify and format log lines for display (color + HTML)."""

from html import escape
from typing import Literal, Optional

from py2exe_gui.styles import DEFAULT_LOG_THEME, LOG_COLORS

LogLevel = Literal["info", "success", "warning", "error", "muted"]

# Tokens are matched case-insensitively, so "error:", "Error" and "ERROR" all
# classify the same way. The Arabic tokens are caseless, which is harmless.
_ERROR_TOKENS = ("❌", "error", "traceback", "فشل", "خطأ")
_WARNING_TOKENS = ("⚠️", "warning", "تنبيه")
_SUCCESS_TOKENS = ("✅", "بنجاح", "successfully", "completed")


def classify_line(line: str) -> LogLevel:
    """Heuristically determine the severity of a log line."""
    lowered = line.lower()
    # Order matters: errors before warnings, success markers before info.
    if any(token in lowered for token in _ERROR_TOKENS):
        return "error"
    if any(token in lowered for token in _WARNING_TOKENS):
        return "warning"
    if any(token in lowered for token in _SUCCESS_TOKENS):
        return "success"
    if line.startswith("─") or line.startswith("═"):
        return "muted"
    return "info"


def level_color(level: LogLevel, theme: str = DEFAULT_LOG_THEME) -> str:
    """Return the hex colour for ``level`` under ``theme``.

    Falls back to the default theme when the name is unknown, so a corrupt
    persisted preference can never crash the log.
    """
    palette = LOG_COLORS.get(theme) or LOG_COLORS[DEFAULT_LOG_THEME]
    return palette[level]


def format_html(
    line: str,
    level: Optional[LogLevel] = None,
    theme: str = DEFAULT_LOG_THEME,
) -> str:
    """Wrap ``line`` in a coloured <span> for QTextEdit.append()."""
    lvl = level or classify_line(line)
    color = level_color(lvl, theme)
    safe = escape(line).replace(" ", "&nbsp;") if line.startswith(" ") else escape(line)
    return f'<span style="color: {color};">{safe}</span>'
