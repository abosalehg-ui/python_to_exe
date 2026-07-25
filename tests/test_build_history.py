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


# ── Tolerant loading (regression: a single bad record wiped the whole file) ──


def test_unknown_keys_are_ignored(tmp_path):
    """A record written by a newer version must not destroy the history."""
    path = tmp_path / "history.json"
    path.write_text(
        json.dumps(
            [
                {
                    "timestamp": "2026-01-01T10:00:00",
                    "source": "a.py",
                    "output_name": "a",
                    "success": True,
                    "future_field": "from a newer version",
                }
            ]
        ),
        encoding="utf-8",
    )
    history = BuildHistory(str(path))
    assert len(history) == 1
    assert history.records[0].output_name == "a"


def test_missing_keys_get_defaults(tmp_path):
    path = tmp_path / "history.json"
    path.write_text(json.dumps([{"source": "a.py"}]), encoding="utf-8")
    history = BuildHistory(str(path))
    assert len(history) == 1
    assert history.records[0].success is False


def test_one_bad_record_does_not_discard_the_good_ones(tmp_path):
    path = tmp_path / "history.json"
    path.write_text(
        json.dumps([{"source": "good.py"}, "not-a-dict", {"source": "also-good.py"}]),
        encoding="utf-8",
    )
    history = BuildHistory(str(path))
    assert len(history) == 2
    assert "skipped 1" in history.last_error


def test_corrupt_json_reports_the_reason(tmp_path):
    path = tmp_path / "history.json"
    path.write_text("{not json", encoding="utf-8")
    history = BuildHistory(str(path))
    assert history.records == []
    assert history.last_error


def test_non_list_payload_is_rejected(tmp_path):
    path = tmp_path / "history.json"
    path.write_text('{"records": []}', encoding="utf-8")
    history = BuildHistory(str(path))
    assert history.records == []
    assert history.last_error


def test_save_creates_missing_parent_directory(tmp_path):
    path = tmp_path / "nested" / "deeper" / "history.json"
    history = BuildHistory(str(path))
    assert history.add(make_record("a.py", "a", True, 1.0, {})) is True
    assert path.exists()


def test_save_reports_failure_instead_of_swallowing(tmp_path):
    history = BuildHistory(str(tmp_path / "history.json"))
    history.add(make_record("a.py", "a", True, 1.0, {}))
    # A directory where the file should be makes the write fail.
    bad = tmp_path / "blocked"
    bad.mkdir()
    history.path = str(bad)
    assert history.save() is False
    assert history.last_error
