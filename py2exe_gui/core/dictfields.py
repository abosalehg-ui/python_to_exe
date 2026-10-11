"""Type-strict loading of a dataclass from a dict (a settings or project file).

Settings files are untrusted and hand-edited: ``"optimize": "2"`` or
``"extra_files": "data"`` happen. Copying such values straight into the
dataclass used to give ``list("data") == ['d', 'a', 't', 'a']`` and a
``TypeError`` much later in the build command. Here every value is checked
against the type of the field's default: a wrong type is coerced when that
is unambiguous (a digit string for an int) and otherwise dropped, keeping the
default, and the caller can collect a warning for each.

A leaf module: ``config`` and ``project_file`` both load through it.
"""

from dataclasses import fields
from typing import Any, List, Optional, Tuple


def type_ok(default: Any, value: Any) -> bool:
    """Whether ``value`` has the type ``default`` says the field holds."""
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(default, int):
        return isinstance(value, int) and not isinstance(value, bool)
    if isinstance(default, str):
        return isinstance(value, str)
    if isinstance(default, list):
        return isinstance(value, list) and all(isinstance(v, str) for v in value)
    return False


def coerce(default: Any, value: Any) -> Tuple[bool, Any]:
    """``(True, value)`` when ``value`` fits or can be made to fit ``default``.

    Only lossless conversions: an int from a digit string, an int-valued
    float, and a list of strings from a tuple. ``"yes"`` is not a bool and
    ``"data"`` is not a list — those keep the default.
    """
    if type_ok(default, value):
        return True, list(value) if isinstance(value, list) else value
    if isinstance(default, bool):
        return False, None
    if isinstance(default, int):
        if isinstance(value, str) and value.strip().lstrip("-").isdigit():
            return True, int(value.strip())
        if isinstance(value, float) and value.is_integer():
            return True, int(value)
        return False, None
    if isinstance(default, list) and isinstance(value, tuple):
        return coerce(default, list(value))
    return False, None


def section_from_dict(defaults: Any, data: Any, where: str = "",
                      warnings: Optional[List[str]] = None,
                      skip: Tuple[str, ...] = ()) -> Any:
    """A copy of ``defaults`` with the values of ``data`` that have the right type.

    Lenient on missing keys (defaults stay), strict on types (a wrong type is
    dropped or coerced and reported), unknown keys reported. Nested
    dataclasses are loaded the same way; a nested value that is not a dict is
    ignored. ``data`` that is not a dict gives the defaults back.
    """
    notes = warnings if warnings is not None else []
    if not isinstance(data, dict):
        return _copy(defaults)
    known = {f.name for f in fields(defaults)}
    result = _copy(defaults)
    for f in fields(defaults):
        if f.name in skip or f.name not in data:
            continue
        default = getattr(defaults, f.name)
        value = data[f.name]
        label = f"{where}.{f.name}" if where else f.name
        if hasattr(default, "__dataclass_fields__"):
            if isinstance(value, dict):
                setattr(result, f.name, section_from_dict(default, value, label, notes))
            else:
                notes.append(f"{label}: expected a table")
            continue
        ok, fitted = coerce(default, value)
        if ok:
            setattr(result, f.name, fitted)
        else:
            notes.append(f"{label}: wrong type ({type(value).__name__}), ignored")
    for key in data:
        if key not in known and key not in skip:
            notes.append(f"{where}.{key}: unknown setting, ignored" if where
                         else f"{key}: unknown setting, ignored")
    return result


def _copy(obj: Any) -> Any:
    """A fresh instance with the same field values (nested dataclasses copied)."""
    values = {}
    for f in fields(obj):
        value = getattr(obj, f.name)
        if hasattr(value, "__dataclass_fields__"):
            value = _copy(value)
        elif isinstance(value, list):
            value = list(value)
        values[f.name] = value
    return type(obj)(**values)
