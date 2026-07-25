"""Tests for log_formatter."""

import pytest

from py2exe_gui.core.log_formatter import (
    classify_line,
    format_html,
    level_color,
)
from py2exe_gui.styles import LOG_BACKGROUND, LOG_COLORS


def test_classify_error_via_emoji():
    assert classify_line("❌ فشل التحويل!") == "error"


def test_classify_error_via_traceback():
    assert classify_line("Traceback (most recent call last):") == "error"


def test_classify_error_via_arabic_word():
    assert classify_line("خطأ في المعالجة") == "error"


def test_classify_warning_via_emoji():
    assert classify_line("⚠️ PyInstaller غير مثبت") == "warning"


def test_classify_warning_token_present():
    assert classify_line("WARNING: hidden import not found") == "warning"


def test_classify_success_via_emoji():
    assert classify_line("✅ تم التحويل بنجاح!") == "success"


def test_classify_success_via_english():
    assert classify_line("Successfully built EXE") == "success"


def test_classify_muted_separator():
    assert classify_line("─" * 50) == "muted"
    assert classify_line("═" * 60) == "muted"


def test_classify_default_is_info():
    assert classify_line("Just some output line") == "info"


def test_format_html_wraps_in_span_with_color():
    out = format_html("✅ done", level="success")
    assert "<span" in out
    assert "color:" in out
    assert "done" in out


def test_format_html_escapes_html_metacharacters():
    out = format_html("<script>evil</script>", level="info")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_format_html_auto_classifies_when_level_omitted():
    out = format_html("❌ error happened")
    assert "color:" in out
    assert level_color("error") in out
    assert level_color("success") not in out


# ── Per-theme palettes ─────────────────────────────────────────────────────


def test_level_color_differs_between_themes():
    assert level_color("error", "dark") != level_color("error", "light")


def test_level_color_falls_back_for_unknown_theme():
    assert level_color("info", "solarized") == level_color("info", "dark")


def test_format_html_honours_theme():
    dark = format_html("boom", level="error", theme="dark")
    light = format_html("boom", level="error", theme="light")
    assert level_color("error", "dark") in dark
    assert level_color("error", "light") in light


def _relative_luminance(hex_color: str) -> float:
    channels = [int(hex_color.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(a: str, b: str) -> float:
    la, lb = _relative_luminance(a), _relative_luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


@pytest.mark.parametrize("theme", sorted(LOG_COLORS))
@pytest.mark.parametrize("level", ["info", "success", "warning", "error", "muted"])
def test_every_log_color_meets_wcag_aa(theme, level):
    """Guards the fix for a palette that failed AA on both backgrounds."""
    color = level_color(level, theme)
    ratio = _contrast(color, LOG_BACKGROUND[theme])
    assert ratio >= 4.5, f"{theme}/{level} {color} is only {ratio:.2f}:1"
