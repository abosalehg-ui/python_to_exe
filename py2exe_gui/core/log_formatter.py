"""Classify and format log lines for display (color + HTML)."""

from html import escape
from typing import Literal

LogLevel = Literal["info", "success", "warning", "error", "muted"]


def classify_line(line: str) -> LogLevel:
    """Heuristically determine the severity of a log line."""
    lowered = line.lower()
    # Order matters: success markers before generic info, errors before warnings.
    if any(token in line for token in ("❌", "ERROR", "Traceback", "فشل", "خطأ")):
        return "error"
    if any(token in line for token in ("⚠️", "WARNING", "تنبيه")):
        return "warning"
    if any(token in line for token in ("✅", "بنجاح", "Successfully", "completed")):
        return "success"
    if line.startswith("─") or line.startswith("═"):
        return "muted"
    if "info" in lowered or line.startswith("INFO"):
        return "info"
    return "info"


_LEVEL_COLORS = {
    "info": "#89b4fa",
    "success": "#40a02b",
    "warning": "#df8e1d",
    "error": "#d20f39",
    "muted": "#6c7086",
}


def format_html(line: str, level: LogLevel = None) -> str:
    """Wrap ``line`` in a coloured <span> for QTextEdit.append()."""
    lvl = level or classify_line(line)
    color = _LEVEL_COLORS[lvl]
    safe = escape(line).replace(" ", "&nbsp;") if line.startswith(" ") else escape(line)
    return f'<span style="color: {color};">{safe}</span>'
