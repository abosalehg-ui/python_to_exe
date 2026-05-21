"""Tests for the built-in templates registry (Phase 6)."""

import pytest

from py2exe_gui.strings import LOCALES, set_locale
from py2exe_gui.templates import (
    _DESC_ATTR,
    _NAME_ATTR,
    TEMPLATES,
    template_description,
    template_name,
)


@pytest.fixture(autouse=True)
def reset_locale():
    before = "ar"
    set_locale(before)
    yield
    set_locale(before)


REQUIRED_KEYS = {"windowed", "onefile", "hidden_imports"}


def test_every_template_has_required_fields():
    for key, data in TEMPLATES.items():
        missing = REQUIRED_KEYS - set(data.keys())
        assert not missing, f"{key} missing fields: {missing}"
        assert isinstance(data["windowed"], bool)
        assert isinstance(data["onefile"], bool)
        assert isinstance(data["hidden_imports"], list)


def test_every_template_has_name_and_desc_keys():
    for key in TEMPLATES:
        assert key in _NAME_ATTR, f"{key} missing from _NAME_ATTR"
        assert key in _DESC_ATTR, f"{key} missing from _DESC_ATTR"


def test_every_template_resolves_in_every_locale():
    for code in LOCALES:
        set_locale(code)
        for key in TEMPLATES:
            assert template_name(key), f"empty name for {key} in {code}"
            assert template_description(key), f"empty description for {key} in {code}"


def test_phase6_templates_present():
    expected = {"fastapi", "streamlit", "kivy", "discord_bot", "click_cli"}
    assert expected.issubset(set(TEMPLATES.keys()))


def test_fastapi_template_has_fastapi_imports():
    assert "fastapi" in TEMPLATES["fastapi"]["hidden_imports"]
    assert "uvicorn" in TEMPLATES["fastapi"]["hidden_imports"]
    # FastAPI runs as a server, not a windowed app.
    assert TEMPLATES["fastapi"]["windowed"] is False


def test_streamlit_template_is_onedir():
    # Streamlit ships resources that don't bundle cleanly into onefile.
    assert TEMPLATES["streamlit"]["onefile"] is False


def test_kivy_template_is_windowed():
    assert TEMPLATES["kivy"]["windowed"] is True


def test_discord_bot_is_console_app():
    assert TEMPLATES["discord_bot"]["windowed"] is False


def test_click_cli_is_console_app():
    assert TEMPLATES["click_cli"]["windowed"] is False


def test_template_keys_are_ascii_identifiers():
    for key in TEMPLATES:
        assert key.isascii() and key.isidentifier(), key


def test_hidden_imports_are_non_empty_strings():
    for key, data in TEMPLATES.items():
        for imp in data["hidden_imports"]:
            assert isinstance(imp, str) and imp.strip(), (
                f"empty hidden_import in {key}"
            )
