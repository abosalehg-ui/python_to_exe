"""Tests for BuildHistory persistence and BuildRecord."""

import json

from py2exe_gui.core.build_history import BuildHistory, BuildRecord, make_record


def test_make_record_fills_timestamp(tmp_path):
    record = make_record(
        source="/tmp/a.py",
        output_name="a",
        success=True,
        duration_seconds=1.5,
        config={"source": "/tmp/a.py"},
    )
    assert record.timestamp
    assert record.source == "/tmp/a.py"
    assert record.success is True


def test_history_adds_and_persists(tmp_path):
    path = str(tmp_path / "history.json")
    h = BuildHistory(path)
    h.add(make_record("/x.py", "x", True, 1.0, {}))
    assert len(h) == 1

    # Reload from disk and verify it persisted.
    h2 = BuildHistory(path)
    assert len(h2) == 1
    assert h2.records[0].source == "/x.py"


def test_history_caps_at_max_records(tmp_path):
    path = str(tmp_path / "history.json")
    h = BuildHistory(path, max_records=3)
    for i in range(5):
        h.add(make_record(f"/{i}.py", str(i), True, 0.0, {}))
    assert len(h) == 3
    # Newest first.
    assert h.records[0].source == "/4.py"
    assert h.records[2].source == "/2.py"


def test_history_clear(tmp_path):
    path = str(tmp_path / "history.json")
    h = BuildHistory(path)
    h.add(make_record("/x.py", "x", True, 1.0, {}))
    h.clear()
    assert len(h) == 0
    assert BuildHistory(path).records == []


def test_history_get_returns_none_for_invalid_index(tmp_path):
    h = BuildHistory(str(tmp_path / "h.json"))
    h.add(make_record("/x.py", "x", True, 1.0, {}))
    assert h.get(-1) is None
    assert h.get(99) is None
    assert h.get(0) is not None


def test_history_handles_corrupt_file(tmp_path):
    path = str(tmp_path / "h.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write("{ invalid json")
    h = BuildHistory(path)
    assert len(h) == 0


def test_history_ignores_non_dict_entries(tmp_path):
    path = str(tmp_path / "h.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(["not a dict", 123, None], f)
    h = BuildHistory(path)
    assert len(h) == 0


def test_short_label_success_marker():
    record = BuildRecord(
        timestamp="2026-05-21T10:00:00",
        source="/tmp/a.py",
        output_name="myapp",
        success=True,
    )
    label = record.short_label()
    assert "✓" in label
    assert "myapp" in label


def test_short_label_failure_marker():
    record = BuildRecord(
        timestamp="2026-05-21T10:00:00",
        source="/tmp/a.py",
        output_name="myapp",
        success=False,
    )
    assert "✗" in record.short_label()


def test_short_label_falls_back_to_source_when_no_output_name():
    record = BuildRecord(
        timestamp="2026-05-21T10:00:00",
        source="/tmp/widget.py",
        output_name="",
        success=True,
    )
    assert "widget.py" in record.short_label()
