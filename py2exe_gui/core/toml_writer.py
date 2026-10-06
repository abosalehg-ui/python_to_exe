"""A small TOML writer for the project file.

The standard library reads TOML (``tomllib``, 3.11+) but cannot write it, and
the project file is the one place the app writes TOML. This covers exactly the
subset ``p2e.toml`` needs, and every value it emits reads back unchanged with
``tomllib``:

* strings (basic strings: quotes, backslashes and control characters escaped,
  every other character — Arabic included — written as itself, UTF-8);
* booleans, integers, floats (``inf``/``nan`` included);
* arrays of any of these, nested arrays, and inline tables inside arrays;
* tables (``[a.b]``) and arrays of tables (``[[a.b]]``).

``None`` and anything else TOML has no spelling for raise ``TypeError`` rather
than being silently dropped or stringified.
"""

import math
import re
from typing import Any, List, Mapping, Sequence

_BARE_KEY = re.compile(r"^[A-Za-z0-9_-]+$")

_ESCAPES = {
    "\\": "\\\\",
    '"': '\\"',
    "\b": "\\b",
    "\t": "\\t",
    "\n": "\\n",
    "\f": "\\f",
    "\r": "\\r",
}


def quote_string(value: str) -> str:
    """``value`` as a TOML basic string."""
    out = []
    for ch in value:
        if ch in _ESCAPES:
            out.append(_ESCAPES[ch])
        elif ord(ch) < 0x20 or ord(ch) == 0x7F:
            # TOML forbids raw control characters in a basic string.
            out.append(f"\\u{ord(ch):04X}")
        elif 0xD800 <= ord(ch) <= 0xDFFF:
            raise ValueError("lone surrogate characters cannot be written to TOML")
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def format_key(key: str) -> str:
    if not isinstance(key, str):
        raise TypeError(f"TOML keys must be strings, not {type(key).__name__}")
    return key if _BARE_KEY.match(key) else quote_string(key)


def _format_float(value: float) -> str:
    if math.isnan(value):
        return "nan"
    if math.isinf(value):
        return "inf" if value > 0 else "-inf"
    text = repr(value)
    # repr gives "1e+20" for large values: valid TOML, but "1.0" style needs a dot.
    if "." not in text and "e" not in text and "E" not in text:
        text += ".0"
    return text


def format_value(value: Any) -> str:
    """One TOML value on one line (inline tables for mappings)."""
    # bool before int: True is an int in Python.
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _format_float(value)
    if isinstance(value, str):
        return quote_string(value)
    if isinstance(value, Mapping):
        items = ", ".join(f"{format_key(k)} = {format_value(v)}" for k, v in value.items())
        return "{ " + items + " }" if items else "{}"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(format_value(v) for v in value) + "]"
    if value is None:
        raise TypeError("TOML has no null value")
    raise TypeError(f"cannot write {type(value).__name__} to TOML")


def _is_table_array(value: Any) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) > 0
        and all(isinstance(item, Mapping) for item in value)
    )


def _emit_table(lines: List[str], path: Sequence[str], table: Mapping, header: str) -> None:
    scalars, tables, table_arrays = [], [], []
    for key, value in table.items():
        if isinstance(value, Mapping):
            tables.append((key, value))
        elif _is_table_array(value):
            table_arrays.append((key, value))
        else:
            scalars.append((key, value))

    if header:
        if lines:
            lines.append("")
        lines.append(header)
    for key, value in scalars:
        lines.append(f"{format_key(key)} = {format_value(value)}")

    for key, value in tables:
        sub = list(path) + [key]
        _emit_table(lines, sub, value, "[" + ".".join(format_key(k) for k in sub) + "]")
    for key, items in table_arrays:
        sub = list(path) + [key]
        name = "[[" + ".".join(format_key(k) for k in sub) + "]]"
        for item in items:
            _emit_table(lines, sub, item, name)


def dumps(data: Mapping, comment: str = "") -> str:
    """Serialize ``data`` (a mapping) to a TOML document.

    ``comment`` is written first, one ``#`` line per line of text.
    """
    if not isinstance(data, Mapping):
        raise TypeError("a TOML document is a table (mapping)")
    lines: List[str] = []
    for line in comment.splitlines():
        lines.append(("# " + line).rstrip())
    body: List[str] = []
    _emit_table(body, [], data, "")
    if lines and body:
        lines.append("")
    lines.extend(body)
    return "\n".join(lines) + "\n"
