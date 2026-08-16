"""Tests for the named preset library."""

import json

import pytest

from py2exe_gui.core.presets import MAX_NAME_LENGTH, PresetLibrary, normalize_name


@pytest.fixture
def library(tmp_path):
    return PresetLibrary(str(tmp_path / "presets.json"))


CONFIG = {"source": "app.py", "onefile": True, "hidden_imports": ["requests"]}


# ── Name handling ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("  My Preset  ", "My Preset"),
        ("My   Preset", "My Preset"),
        ("tab\tseparated", "tab separated"),
        ("", ""),
        ("   ", ""),
    ],
)
def test_normalize_name(raw, expected):
    assert normalize_name(raw) == expected


def test_normalize_name_truncates():
    assert len(normalize_name("x" * 500)) == MAX_NAME_LENGTH


# ── Round-trip ─────────────────────────────────────────────────────────────


def test_put_then_get(library):
    assert library.put("GUI app", CONFIG) is True
    assert library.get("GUI app") == CONFIG


def test_put_persists_across_instances(library):
    library.put("GUI app", CONFIG)
    reloaded = PresetLibrary(library.path)
    assert reloaded.get("GUI app") == CONFIG


def test_put_stores_a_copy(library):
    payload = dict(CONFIG)
    library.put("GUI app", payload)
    payload["source"] = "mutated.py"
    assert library.get("GUI app")["source"] == "app.py"


def test_get_normalizes_the_lookup_name(library):
    library.put("GUI app", CONFIG)
    assert library.get("  GUI   app  ") == CONFIG


def test_put_overwrites_an_existing_name(library):
    library.put("x", CONFIG)
    library.put("x", {"source": "other.py"})
    assert library.get("x") == {"source": "other.py"}
    assert len(library) == 1


def test_put_rejects_an_empty_name(library):
    assert library.put("   ", CONFIG) is False
    assert len(library) == 0


def test_put_rejects_a_non_dict_payload(library):
    assert library.put("x", ["not", "a", "dict"]) is False


def test_delete(library):
    library.put("x", CONFIG)
    assert library.delete("x") is True
    assert library.get("x") is None


def test_delete_missing_reports_failure(library):
    assert library.delete("nope") is False
    assert library.last_error


def test_names_are_sorted_case_insensitively(library):
    for name in ("zeta", "Alpha", "beta"):
        library.put(name, CONFIG)
    assert library.names() == ["Alpha", "beta", "zeta"]


def test_has(library):
    library.put("x", CONFIG)
    assert library.has("x") is True
    assert library.has("y") is False


# ── Damaged files ──────────────────────────────────────────────────────────


def test_missing_file_loads_empty(tmp_path):
    library = PresetLibrary(str(tmp_path / "absent.json"))
    assert len(library) == 0
    assert library.last_error == ""


def test_corrupt_file_loads_empty_and_reports(tmp_path):
    path = tmp_path / "presets.json"
    path.write_text("{ not json", encoding="utf-8")
    library = PresetLibrary(str(path))
    assert len(library) == 0
    assert library.last_error


def test_non_object_file_is_rejected(tmp_path):
    path = tmp_path / "presets.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    library = PresetLibrary(str(path))
    assert len(library) == 0
    assert "object" in library.last_error


def test_one_malformed_entry_does_not_discard_the_rest(tmp_path):
    """Mirrors BuildHistory: a bad record must not wipe the whole file."""
    path = tmp_path / "presets.json"
    path.write_text(
        json.dumps({"good": CONFIG, "bad": "not-a-dict", "": CONFIG}),
        encoding="utf-8",
    )
    library = PresetLibrary(str(path))
    assert library.names() == ["good"]
    assert "skipped" in library.last_error


# ── Sharing ────────────────────────────────────────────────────────────────


def test_export_all_returns_a_detached_copy(library):
    library.put("x", CONFIG)
    exported = library.export_all()
    exported["x"]["source"] = "mutated.py"
    assert library.get("x")["source"] == "app.py"


def test_import_all_adds_new_presets(library):
    added = library.import_all({"a": CONFIG, "b": CONFIG})
    assert sorted(added) == ["a", "b"]
    assert len(library) == 2


def test_import_all_keeps_existing_names_by_default(library):
    library.put("mine", {"source": "mine.py"})
    added = library.import_all({"mine": {"source": "theirs.py"}})
    assert added == []
    assert library.get("mine")["source"] == "mine.py"


def test_import_all_can_overwrite_explicitly(library):
    library.put("mine", {"source": "mine.py"})
    added = library.import_all({"mine": {"source": "theirs.py"}}, overwrite=True)
    assert added == ["mine"]
    assert library.get("mine")["source"] == "theirs.py"


def test_import_all_rejects_a_non_dict(library):
    assert library.import_all(["nope"]) == []
    assert library.last_error


def test_import_all_skips_malformed_entries(library):
    added = library.import_all({"ok": CONFIG, "bad": 42, "": CONFIG})
    assert added == ["ok"]
