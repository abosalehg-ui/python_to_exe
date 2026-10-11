"""UI-element strings carry no emoji (2.1): icons come from the icon set.

Emoji stay where they are content, not decoration: log lines, status
messages and notifications, where ✅ / ❌ / ⚠️ say what happened. They are
gone from tabs, sections, group titles, buttons and menus, whose glyphs now
come from ``py2exe_gui.icons`` and follow the theme on every platform.
"""

import re

from py2exe_gui.strings import LOCALES

EMOJI = re.compile(
    r"[\U0001F000-\U0001FAFF☀-➿⬀-⯿⌀-⏿ℹ️]"
)

#: Attribute prefixes that name a UI element rather than a message.
ELEMENT_PREFIXES = (
    "TAB_", "GROUP_", "BTN_", "MENU_", "SECTION_", "THEME_LABEL_", "KIT_NAME_",
    "BUILD_SECTION_", "LANGUAGE_LABEL", "ABOUT_DEVELOPER_LABEL", "ABOUT_FEATURES_LABEL",
    "ICON_STUDIO_TITLE", "LICENSE_DIALOG_TITLE", "COMPARE_GROUP", "DOCTOR_READINESS_BTN_FMT",
    "CLEAR_LOG", "HEADER_TITLE", "SHORTCUT_", "STATUS_",
)


def _element_strings(klass):
    for name, value in vars(klass).items():
        if isinstance(value, str) and name.startswith(ELEMENT_PREFIXES):
            yield name, value


def test_no_emoji_in_ui_element_strings():
    for code, klass in LOCALES.items():
        offenders = [name for name, text in _element_strings(klass) if EMOJI.search(text)]
        assert not offenders, f"{code}: emoji used as icons in {offenders}"


def test_emoji_still_mark_severity_in_log_lines():
    """Not a purge: ✅ / ❌ in log messages carry meaning and stay."""
    ar = LOCALES["ar"]
    assert "✅" in ar.LOG_READY
    assert "❌" in ar.CONV_FAILED


def test_element_strings_are_not_empty_except_icon_only_buttons():
    for code, klass in LOCALES.items():
        empty = [name for name, text in _element_strings(klass) if not text.strip()]
        assert empty == ["BTN_ICON_STUDIO"], f"{code}: {empty}"
