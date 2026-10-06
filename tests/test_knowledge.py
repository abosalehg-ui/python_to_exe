"""Tests for the package knowledge base and its loader."""

import json

import pytest

from py2exe_gui.core.knowledge import (
    KNOWLEDGE_FILE,
    QT_BINDINGS,
    load_knowledge,
    lookup,
    parse_knowledge,
    pip_name_for,
)


def test_shipped_knowledge_file_loads_and_is_not_empty():
    knowledge = load_knowledge()
    assert len(knowledge) >= 30


def test_shipped_file_is_valid_json_with_schema():
    with open(KNOWLEDGE_FILE, encoding="utf-8") as f:
        data = json.load(f)
    assert data["schema"] == 1
    # parse_knowledge raises on a malformed entry, so this validates them all.
    assert parse_knowledge(data)


def test_every_note_exists_in_both_languages():
    for name, info in load_knowledge().items():
        if info.notes:
            assert info.notes.get("ar"), name
            assert info.notes.get("en"), name


def test_entries_are_keyed_by_import_name_not_pip_name():
    # The whole point of the "pip" field: the import name differs.
    assert lookup("PIL").pip_name == "Pillow"
    assert lookup("cv2").pip_name == "opencv-python"
    assert lookup("Pillow") is None


def test_pip_name_falls_back_to_import_name():
    assert pip_name_for("requests") == "requests"
    assert pip_name_for("yaml.loader") == "PyYAML"


def test_build_fixes_cover_every_list_field():
    fixes = lookup("apscheduler").build_fixes()
    values = {f.value for f in fixes}
    assert "--collect-submodules apscheduler" in values
    assert "--copy-metadata APScheduler" in values


def test_hidden_imports_become_hidden_import_fixes():
    fixes = lookup("tkcalendar").build_fixes()
    assert [(f.kind, f.value) for f in fixes] == [("hidden_import", "babel.numbers")]


def test_qt_bindings_are_all_flagged():
    for binding in QT_BINDINGS:
        assert lookup(binding).qt_binding


def test_note_falls_back_to_english():
    info = lookup("flask")
    assert info.note("fr") == info.notes["en"]


def test_missing_file_yields_empty_knowledge(tmp_path):
    assert load_knowledge(str(tmp_path / "nope.json")) == {}


def test_broken_file_yields_empty_knowledge(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{not json")
    assert load_knowledge(str(path)) == {}


@pytest.mark.parametrize(
    "packages",
    [
        {"x": {"hidden_imports": "not-a-list"}},
        {"x": {"collect_data": [1, 2]}},
        {"x": {"notes": "text"}},
    ],
)
def test_malformed_entries_are_rejected(packages):
    with pytest.raises(ValueError):
        parse_knowledge({"packages": packages})


def test_missing_packages_object_is_rejected():
    with pytest.raises(ValueError):
        parse_knowledge({})


def test_import_name_for_dist_maps_bundle_folders_back():
    from py2exe_gui.core.knowledge import import_name_for_dist

    assert import_name_for_dist("pillow") == "PIL"
    assert import_name_for_dist("opencv_python") == "cv2"
    assert import_name_for_dist("numpy") == "numpy"
