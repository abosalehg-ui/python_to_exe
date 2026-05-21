"""Tests for the locale registry, proxy, and string parity."""

import pytest

from py2exe_gui.strings import (
    DEFAULT_LOCALE,
    LOCALE_LAYOUT,
    LOCALES,
    Ar,
    En,
    S,
    available_locales,
    current_locale,
    set_locale,
)
from py2exe_gui.templates import TEMPLATES, template_description, template_name


@pytest.fixture(autouse=True)
def reset_locale():
    """Snapshot and restore the active locale around each test."""
    before = current_locale()
    yield
    set_locale(before)


def test_default_locale_registered():
    assert DEFAULT_LOCALE in LOCALES


def test_available_locales_includes_ar_and_en():
    locales = available_locales()
    assert "ar" in locales
    assert "en" in locales


def test_each_locale_has_a_layout_direction():
    for code in LOCALES:
        assert LOCALE_LAYOUT.get(code) in ("rtl", "ltr")


def test_proxy_delegates_to_active_locale():
    set_locale("ar")
    assert S.HEADER_TITLE == Ar.HEADER_TITLE
    set_locale("en")
    assert S.HEADER_TITLE == En.HEADER_TITLE


def test_set_locale_returns_false_for_unknown():
    assert set_locale("xyz") is False


def test_set_locale_returns_true_for_known():
    assert set_locale("en") is True
    assert current_locale() == "en"


def test_current_locale_reflects_switch():
    set_locale("ar")
    assert current_locale() == "ar"
    set_locale("en")
    assert current_locale() == "en"


def test_en_defines_every_public_attribute_of_ar():
    ar_attrs = {a for a in dir(Ar) if not a.startswith("_")}
    en_attrs = {a for a in dir(En) if not a.startswith("_")}
    missing = ar_attrs - en_attrs
    assert not missing, f"En is missing translations: {sorted(missing)}"


def test_ar_defines_every_public_attribute_of_en():
    ar_attrs = {a for a in dir(Ar) if not a.startswith("_")}
    en_attrs = {a for a in dir(En) if not a.startswith("_")}
    extra = en_attrs - ar_attrs
    assert not extra, f"En has attributes not present in Ar: {sorted(extra)}"


def test_template_helpers_track_active_locale():
    set_locale("ar")
    ar_name = template_name("gui")
    ar_desc = template_description("gui")
    set_locale("en")
    en_name = template_name("gui")
    en_desc = template_description("gui")
    assert ar_name != en_name
    assert ar_desc != en_desc


def test_all_templates_have_name_and_description_in_every_locale():
    for code in LOCALES:
        set_locale(code)
        for key in TEMPLATES:
            assert template_name(key)
            assert template_description(key)


def test_template_keys_are_stable_english_identifiers():
    # Keys must be ASCII so they survive locale switching as data values.
    for key in TEMPLATES:
        assert key.isascii()
        assert key.isidentifier()
