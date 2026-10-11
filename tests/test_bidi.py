"""The one bidi helper module, replacing six scattered copies.

Qt-free: the command line and ``texts.py`` use it too. The tab tests
(``test_ui_runtime``, ``test_ui_size``…) keep asserting the exact strings
the widgets show; these pin the helpers themselves.
"""

import pytest

from py2exe_gui import bidi
from py2exe_gui.bidi import (
    LRI,
    LRM,
    PDI,
    RLI,
    RLM,
    code_run,
    is_rtl,
    isolate,
    ltr,
    rlm,
    rtl,
    separator,
    strip_marks,
)
from py2exe_gui.strings import set_locale


def test_ltr_is_an_isolate_in_both_directions():
    assert ltr("41.6 MB") == f"{LRI}41.6 MB{PDI}"
    set_locale("en")
    assert ltr("x") == f"{LRI}x{PDI}"  # invisible in LTR, never a branch


def test_rtl_is_a_right_to_left_isolate():
    assert rtl("نص") == f"{RLI}نص{PDI}"


def test_isolate_follows_its_flag():
    assert isolate("0.124 s", True) == ltr("0.124 s")
    assert isolate("0.124 s", False) == "0.124 s"


def test_code_run_uses_marks_not_isolates():
    assert code_run("print()") == f"{LRM}print(){LRM}"


@pytest.mark.parametrize("locale,expected", [("ar", RLM + "✅ x"), ("en", "✅ x")])
def test_rlm_pins_a_line_only_in_a_rtl_locale(locale, expected):
    set_locale(locale)
    assert rlm("✅ x") == expected


def test_rlm_can_be_forced_either_way():
    set_locale("en")
    assert rlm("1", when=True) == RLM + "1"
    set_locale("ar")
    assert rlm("1", when=False) == "1"


def test_bidi_wraps_code_runs_and_keeps_placeholders():
    """print() must not turn into ()print inside right-to-left text."""
    set_locale("ar")
    text = bidi.bidi("يذهب print() إلى /SILENT و {app}")
    assert text.startswith(RLM)
    assert f"{LRM}print(){LRM}" in text and f"{LRM}/SILENT{LRM}" in text
    assert "{app}" in text
    set_locale("en")
    assert bidi.bidi("print() to /SILENT") == "print() to /SILENT"


def test_bidi_leaves_empty_text_alone():
    set_locale("ar")
    assert bidi.bidi("") == ""


def test_separator_is_pinned_under_rtl():
    set_locale("ar")
    assert separator() == f"{RLM} — {RLM}"
    set_locale("en")
    assert separator() == " — "


def test_is_rtl_reads_the_active_or_a_given_locale():
    set_locale("ar")
    assert is_rtl() and not is_rtl("en")
    set_locale("en")
    assert not is_rtl() and is_rtl("ar")


def test_strip_marks_removes_everything_the_module_inserts():
    set_locale("ar")
    text = rlm(ltr("a") + separator() + code_run("b") + rtl("c"))
    assert strip_marks(text) == "a — bc"


def test_the_old_copies_are_gone():
    """Every former helper now resolves to the one in ``bidi``."""
    from py2exe_gui import texts
    from py2exe_gui.ui import dialogs
    from py2exe_gui.ui.tabs import home_tab, release_tab, runtime_tab, size_tab

    assert size_tab.ltr is ltr
    assert dialogs.ltr is ltr
    assert texts._iso is isolate
    assert runtime_tab.bidi is bidi.bidi and runtime_tab.code_run is code_run
    assert release_tab._separator is separator
    assert not hasattr(home_tab, "_rlm")
    assert not hasattr(dialogs, "_ltr")
