"""Command-line flags inside right-to-left strings keep their reading order.

``--onefile`` is bidi-neutral, so inside an Arabic label Qt laid it out as
"(onefile--)". Every ``--flag`` in a right-to-left locale is wrapped in a
left-to-right isolate at import time; these tests keep it that way.
"""

import re

from py2exe_gui.strings import LOCALE_LAYOUT, LOCALES, LRI, PDI, Ar, En, isolate_flags

_BARE_FLAG = re.compile(r"(?<!⁦)--[A-Za-z]")


def _strings(klass):
    for name, value in vars(klass).items():
        if name.startswith("_"):
            continue
        if isinstance(value, str):
            yield name, value
        elif isinstance(value, tuple):
            for i, item in enumerate(value):
                if isinstance(item, str):
                    yield f"{name}[{i}]", item


def test_isolate_wraps_each_flag_once():
    assert isolate_flags("ملف واحد (--onefile)") == f"ملف واحد ({LRI}--onefile{PDI})"
    once = isolate_flags("a --b c")
    assert isolate_flags(once) == once


def test_isolate_handles_a_flag_glued_to_arabic_text():
    assert isolate_flags("و--strict مفعّل") == f"و{LRI}--strict{PDI} مفعّل"


def test_isolate_leaves_text_without_flags_alone():
    assert isolate_flags("no flags here, just a-dash") == "no flags here, just a-dash"


def test_every_rtl_locale_has_no_bare_flag():
    for code, klass in LOCALES.items():
        if LOCALE_LAYOUT.get(code) != "rtl":
            continue
        bare = [name for name, text in _strings(klass) if _BARE_FLAG.search(text)]
        assert not bare, f"{code}: flags without an isolate in {bare}"


def test_isolated_flags_are_closed():
    for name, text in _strings(Ar):
        assert text.count(LRI) == text.count(PDI), name


def test_ltr_locale_is_untouched():
    assert LRI not in En.OPT_ONEFILE
    assert En.OPT_ONEFILE == "Single file (--onefile)"


def test_arabic_option_labels_read_correctly():
    assert f"{LRI}--onefile{PDI}" in Ar.OPT_ONEFILE
    assert Ar.OPT_STRIP == f"{LRI}--strip{PDI}"
