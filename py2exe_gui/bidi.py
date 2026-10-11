"""Bidirectional text helpers, Qt-free.

Six copies of "wrap this in a left-to-right isolate" used to live in the
tabs, the dialogs and ``texts.py``, each with its own name and its own
notion of when to apply. They are collected here so the command line, the
core-facing text module and the widgets all isolate a number, a path or a
code run the same way.

Three mechanisms, for three different problems:

- :func:`ltr` wraps text in an isolate (U+2066 … U+2069). The text keeps its
  own reading order and does not affect the direction of what surrounds it:
  "41.6 MB" stays "41.6 MB" inside an Arabic sentence.
- :func:`code_run` brackets text with left-to-right *marks* (U+200E). Qt 5.15
  rendered the brackets of ``print()`` at the wrong end inside an isolate,
  while the marks held, so a run of code inside prose uses marks instead.
- :func:`rlm` prefixes a right-to-left mark (U+200F). Qt 5 takes a
  paragraph's direction from its first strong character and ignores
  isolates, so a line starting with "✅" or "123" would otherwise be laid
  out left to right with its Arabic reading backwards.
"""

import re

from py2exe_gui.strings import LOCALE_LAYOUT, current_locale

#: Left-to-right isolate … pop directional isolate.
LRI = "⁦"
PDI = "⁩"
#: Right-to-left isolate (for a run of Arabic inside English text).
RLI = "⁧"
#: Left-to-right and right-to-left marks.
LRM = "‎"
RLM = "‏"

#: Everything this module may insert, for tests and for stripping.
MARKS = (LRI, RLI, PDI, LRM, RLM)

# A run of code or a file name inside a sentence: starts with a letter, "_",
# "/" or "(", ends on a letter, digit or ")" — never on sentence punctuation.
_CODE_RUN = re.compile(r"[A-Za-z_/(][\x20-\x7a|~]*[A-Za-z0-9_)]|[A-Za-z_]")
_PLACEHOLDER = re.compile(r"(\{\w+\})")


def is_rtl(locale: str = "") -> bool:
    """Whether ``locale`` (the active one by default) lays out right to left."""
    return LOCALE_LAYOUT.get(locale or current_locale(), "ltr") == "rtl"


def ltr(text: str) -> str:
    """``text`` inside a left-to-right isolate, so "41.6 MB" or "+12.5%" or a
    path keeps its reading order inside right-to-left text.

    Always applied: an isolate is invisible in a left-to-right layout, and
    callers that build the same string for both directions should not have
    to branch.
    """
    return f"{LRI}{text}{PDI}"


def rtl(text: str) -> str:
    """``text`` inside a right-to-left isolate (Arabic inside English)."""
    return f"{RLI}{text}{PDI}"


def isolate(text: str, when: bool = True) -> str:
    """:func:`ltr` when ``when`` is true, ``text`` unchanged otherwise.

    For call sites that compute the direction once (the compare table, the
    command line) and pass it down.
    """
    return ltr(text) if when else text


def code_run(text: str) -> str:
    """A run of code, a key or a path pinned left to right with marks.

    Marks rather than an isolate: rendered offscreen, Qt 5.15 still moved
    the brackets of ``print()`` to the wrong end inside an isolate, while
    the marks held.
    """
    return f"{LRM}{text}{LRM}"


def rlm(text: str, when: bool = None) -> str:
    """``text`` behind a right-to-left mark, in a right-to-left locale.

    Pins a line that starts with a symbol ("✅", "📏") or a number to the
    paragraph direction of the UI. ``when`` overrides the locale check.
    """
    apply = is_rtl() if when is None else when
    return RLM + text if apply else text


def bidi(text: str) -> str:
    """Make mixed Arabic/code prose read correctly in a right-to-left UI.

    Each run of code (``print()``, ``/SILENT``, ``update.json``) goes through
    :func:`code_run`, otherwise its brackets and slashes migrate to the wrong
    end ("()print"); the whole line is then pinned with :func:`rlm`. In a
    left-to-right locale the text is returned unchanged. ``{placeholders}``
    are left intact for a later ``.format()``.
    """
    if not text or not is_rtl():
        return text
    parts = _PLACEHOLDER.split(text)
    for index in range(0, len(parts), 2):
        parts[index] = _CODE_RUN.sub(lambda m: code_run(m.group(0)), parts[index])
    return RLM + "".join(parts)


def separator(dash: str = " — ") -> str:
    """``dash`` between two runs, pinned so it does not merge them.

    In a right-to-left layout "SHA-256 — SHA256SUMS.txt" would otherwise
    become one left-to-right run and read backwards.
    """
    return f"{RLM}{dash}{RLM}" if is_rtl() else dash


def strip_marks(text: str) -> str:
    """``text`` without any of the characters this module inserts."""
    for mark in MARKS:
        text = text.replace(mark, "")
    return text


__all__ = [
    "LRI", "LRM", "MARKS", "PDI", "RLI", "RLM", "bidi", "code_run", "is_rtl", "isolate",
    "ltr", "rlm", "rtl", "separator", "strip_marks",
]
