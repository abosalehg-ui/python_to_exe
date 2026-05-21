"""Tests for log_formatter."""

from py2exe_gui.core.log_formatter import classify_line, format_html


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
    # error red ≠ success green
    assert "#d20f39" in out
