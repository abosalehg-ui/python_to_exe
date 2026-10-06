"""The TOML writer: every document it writes must read back unchanged."""

import math
import sys

import pytest

from py2exe_gui.core.toml_writer import dumps, format_key, format_value, quote_string

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - depends on the interpreter
    tomllib = pytest.importorskip("tomli")


def roundtrip(data):
    return tomllib.loads(dumps(data))


def test_scalars_round_trip():
    data = {"s": "text", "t": True, "f": False, "i": -42, "big": 2**62, "x": 3.25, "z": 0}
    assert roundtrip(data) == data


def test_floats_keep_their_type():
    data = {"one": 1.0, "tiny": 1e-12, "large": 1e20, "neg": -0.5}
    loaded = roundtrip(data)
    assert loaded == data
    assert all(isinstance(v, float) for v in loaded.values())


def test_special_floats():
    loaded = roundtrip({"a": float("inf"), "b": float("-inf"), "c": float("nan")})
    assert loaded["a"] == math.inf and loaded["b"] == -math.inf and math.isnan(loaded["c"])


@pytest.mark.parametrize("text", [
    'quote " inside',
    "back\\slash",
    "C:\\Users\\me\\My Project\\app.py",
    "line1\nline2\r\nline3",
    "tab\there",
    "bell\x07 escape\x1b del\x7f nul\x00 formfeed\f backspace\b",
    "",
    "   leading and trailing   ",
    "# not a comment",
    "key = value",
    "[not.a.table]",
    "'''triple single'''",
    '"""triple double"""',
])
def test_strings_needing_escapes_round_trip(text):
    assert roundtrip({"v": text}) == {"v": text}


def test_arabic_and_other_unicode_are_written_as_themselves():
    data = {"name": "محوّل بايثون", "mixed": "تطبيق My App ١٢٣", "emoji": "🚀 إصدار",
            "rtl_marks": "\u200fنص\u200e", "cjk": "日本語"}
    text = dumps(data)
    assert "محوّل بايثون" in text and "🚀" in text
    assert "\\u" not in text.replace("\\u200F", "").replace("\\u200E", "")
    assert roundtrip(data) == data


def test_lone_surrogates_are_refused():
    with pytest.raises(ValueError):
        dumps({"bad": "\ud800"})


def test_arrays():
    data = {"empty": [], "strings": ["a", "ب", 'c"d'], "ints": [1, 2, 3],
            "nested": [[1, 2], ["x"]], "mixed": [1, "two", 3.0, True]}
    assert roundtrip(data) == data


def test_tables_and_nested_tables():
    data = {
        "schema": 1,
        "project": {"name": "App", "version": "1.2.3"},
        "release": {"repository": "o/r", "assets": {"exe": True, "zip": False},
                    "winget": {"identifier": "Me.App"}},
        "empty": {},
    }
    assert roundtrip(data) == data


def test_scalars_come_before_subtables():
    text = dumps({"t": {"a": 1, "sub": {"b": 2}, "c": 3}})
    # A key written after [t.sub] would land inside it.
    assert text.index("c = 3") < text.index("[t.sub]")
    assert roundtrip({"t": {"a": 1, "sub": {"b": 2}, "c": 3}}) == {
        "t": {"a": 1, "sub": {"b": 2}, "c": 3}}


def test_arrays_of_tables():
    data = {"jobs": [{"name": "a", "opts": {"x": 1}}, {"name": "b"}], "after": {"k": "v"}}
    text = dumps(data)
    assert "[[jobs]]" in text and "[jobs.opts]" in text
    assert roundtrip(data) == data


def test_inline_tables_inside_mixed_arrays():
    data = {"items": [{"a": 1}, "plain"], "e": [{}, 1]}
    assert roundtrip(data) == data


def test_keys_that_need_quoting():
    data = {"bare_key-1": 1, "with space": 2, "dot.ted": 3, "عربي": 4, "": 5,
            "tbl with space": {"x": 1}}
    assert format_key("bare_key-1") == "bare_key-1"
    assert format_key("dot.ted") == '"dot.ted"'
    assert roundtrip(data) == data


def test_comment_header():
    text = dumps({"a": 1}, comment="first line\nسطر ثانٍ")
    assert text.startswith("# first line\n# سطر ثانٍ\n")
    assert roundtrip({"a": 1}) == {"a": 1}
    assert tomllib.loads(text) == {"a": 1}


def test_unsupported_values_raise():
    with pytest.raises(TypeError):
        dumps({"a": None})
    with pytest.raises(TypeError):
        dumps({"a": object()})
    with pytest.raises(TypeError):
        dumps(["not", "a", "table"])
    with pytest.raises(TypeError):
        format_key(1)


def test_format_value_helpers():
    assert format_value(True) == "true"
    assert format_value(1) == "1"
    assert format_value({}) == "{}"
    assert quote_string('a"b') == '"a\\"b"'
    assert quote_string("\x01") == '"\\u0001"'


def test_output_is_deterministic():
    data = {"b": 1, "a": {"y": [1, 2], "x": "s"}}
    assert dumps(data) == dumps(dict(data))
