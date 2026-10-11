"""Tests for the projects workspace summaries (core, no Qt)."""

import os
import time

import pytest

from py2exe_gui.core.build_history import make_record
from py2exe_gui.core.project_file import ProjectConfig, ProjectFileError, save_project
from py2exe_gui.core.workspace import (
    STATUS_MISSING,
    STATUS_OK,
    STATUS_UNREADABLE,
    ProjectSummary,
    find_releases,
    last_release,
    project_records,
    short_time,
    size_history,
    sparkline_points,
    summarize_project,
    summarize_projects,
)


@pytest.fixture
def project(tmp_path):
    folder = tmp_path / "tool"
    folder.mkdir()
    script = folder / "tool.py"
    script.write_text("print('hi')\n")
    config = ProjectConfig(name="أداتي", version="1.2.0")
    config.build.source = str(script)
    config.build.output_name = "Tool"
    config.release.repository = "me/tool"
    path = save_project(config, str(folder / "p2e.toml"))
    return {"path": path, "source": str(script), "folder": str(folder)}


def record(source, name, success, size, when):
    return make_record(source, name, success, 1.0, {}, timestamp=when, size_bytes=size)


# ── Summaries ─────────────────────────────────────────────────────────────


def test_summary_reads_name_version_and_release_settings(project):
    summary = summarize_project(project["path"])
    assert summary.ok and summary.status == STATUS_OK
    assert summary.name == "أداتي" and summary.version == "1.2.0"
    assert summary.source == project["source"] and summary.output_name == "Tool"
    assert summary.repository == "me/tool" and summary.engine == "pyinstaller"
    assert summary.display_name() == "أداتي"
    assert summary.last_build is None and summary.sizes == [] and summary.builds == 0
    assert summary.last_release is None


def test_summary_takes_the_project_builds_from_the_history(project):
    source = project["source"]
    records = [  # newest first, as BuildHistory keeps them
        record(source, "Tool", False, 0, "2026-10-11T09:00:00"),
        record(source, "Tool", True, 7_400_000, "2026-10-11T08:00:00"),
        record(source, "Other", True, 1, "2026-10-11T07:30:00"),  # another output name
        record("/elsewhere/x.py", "Tool", True, 2, "2026-10-11T07:00:00"),  # another script
        record(source, "Tool", True, 7_100_000, "2026-10-11T06:00:00"),
        record(source, "Tool", True, 0, "2026-10-11T05:00:00"),  # pre-1.4: no size
    ]
    summary = summarize_project(project["path"], records)
    assert summary.builds == 4
    assert summary.last_build is records[0] and summary.last_build.success is False
    assert summary.sizes == [7_100_000, 7_400_000]  # oldest first, successful with a size
    assert summary.size_delta() == 300_000


def test_history_match_ignores_path_spelling(project):
    source = project["source"]
    spelled = os.path.join(os.path.dirname(source), ".", os.path.basename(source))
    records = [record(spelled, "Tool", True, 5, "2026-10-11T08:00:00")]
    assert len(project_records(records, source, "Tool")) == 1
    assert project_records(records, "", "Tool") == []


def test_size_history_is_bounded_and_oldest_first():
    records = [record("a.py", "a", True, i, "t") for i in range(30, 0, -1)]
    sizes = size_history(records, limit=5)
    assert sizes == [26, 27, 28, 29, 30]
    assert size_history(records, limit=0) == list(range(1, 31))


def test_missing_file_is_reported_not_raised(tmp_path):
    summary = summarize_project(str(tmp_path / "gone" / "p2e.toml"))
    assert summary.status == STATUS_MISSING and not summary.ok
    assert summary.display_name() == "gone"
    assert summarize_project("").status == STATUS_MISSING


def test_unreadable_file_carries_the_error_code(tmp_path):
    bad = tmp_path / "p2e.toml"
    bad.write_text("this is = not [toml\n", encoding="utf-8")
    summary = summarize_project(str(bad))
    assert summary.status == STATUS_UNREADABLE
    assert summary.error_code == "syntax" and summary.error_detail


def test_refused_file_is_unreadable_with_its_reason(tmp_path):
    secret = tmp_path / "p2e.toml"
    secret.write_text('schema = 2\n[release]\ntoken = "x"\n', encoding="utf-8")
    summary = summarize_project(str(secret))
    assert summary.status == STATUS_UNREADABLE
    assert summary.error_code == "forbidden_secret" and "token" in summary.error_detail


def test_unexpected_loader_errors_never_escape(tmp_path):
    path = tmp_path / "p2e.toml"
    path.write_text("schema = 2\n", encoding="utf-8")

    def boom(_path):
        raise RuntimeError("disk on fire")

    summary = summarize_project(str(path), loader=boom)
    assert summary.status == STATUS_UNREADABLE
    assert summary.error_code == "generic" and "disk on fire" in summary.error_detail


def test_summarize_projects_keeps_order_and_isolates_failures(project, tmp_path):
    bad = tmp_path / "bad.toml"
    bad.write_text("= =\n", encoding="utf-8")
    paths = [str(bad), project["path"], str(tmp_path / "nope.toml")]
    statuses = [s.status for s in summarize_projects(paths)]
    assert statuses == [STATUS_UNREADABLE, STATUS_OK, STATUS_MISSING]


def test_loader_errors_of_the_project_kind_keep_code_and_detail(tmp_path):
    def refuse(_path):
        raise ProjectFileError("schema_newer", "9")

    path = tmp_path / "p2e.toml"
    path.write_text("schema = 9\n", encoding="utf-8")
    summary = summarize_project(str(path), loader=refuse)
    assert (summary.error_code, summary.error_detail) == ("schema_newer", "9")


# ── Releases ──────────────────────────────────────────────────────────────


def test_find_releases_lists_semver_folders_newest_last(tmp_path):
    root = tmp_path
    for name in ("1.2.0", "1.10.0", "1.2.0-rc.1", "notes", "v1.0.0"):
        (root / "release" / name).mkdir(parents=True)
    (root / "release" / "1.10.0" / "Tool-1.10.0.exe").write_bytes(b"x")
    (root / "release" / "1.10.0" / "SHA256SUMS.txt").write_text("")
    (root / "release" / "readme.txt").write_text("not a folder")
    releases = find_releases(str(root))
    assert [r.version for r in releases] == ["v1.0.0", "1.2.0-rc.1", "1.2.0", "1.10.0"]
    newest = last_release(str(root))
    assert newest.version == "1.10.0" and newest.files == 2 and newest.checksums
    assert newest.path == str(root / "release" / "1.10.0")
    assert newest.timestamp and short_time(newest.timestamp) != newest.timestamp
    assert releases[0].files == 0 and not releases[0].checksums


def test_no_release_folder_means_no_release(tmp_path):
    assert find_releases(str(tmp_path)) == []
    assert last_release(str(tmp_path)) is None
    assert last_release("") is None


def test_summary_finds_the_release_beside_the_build(project):
    folder = project["folder"]
    os.makedirs(os.path.join(folder, "release", "1.1.0"))
    os.makedirs(os.path.join(folder, "release", "1.2.0"))
    summary = summarize_project(project["path"])
    assert summary.last_release is not None and summary.last_release.version == "1.2.0"


# ── The sparkline ─────────────────────────────────────────────────────────


def test_sparkline_points_span_the_box_oldest_left():
    points = sparkline_points([10, 30, 20], 100, 40)
    assert [round(x) for x, _y in points] == [0, 50, 100]
    assert [round(y) for _x, y in points] == [40, 0, 20]  # smallest at the bottom


def test_sparkline_is_mirrored_in_rtl():
    ltr = sparkline_points([10, 30, 20], 100, 40, padding=5)
    rtl = sparkline_points([10, 30, 20], 100, 40, rtl=True, padding=5)
    assert [round(x) for x, _ in rtl] == [100 - round(x) for x, _ in ltr]
    assert [y for _, y in rtl] == [y for _, y in ltr]
    assert rtl[-1][0] == 5  # the newest build sits at the right-to-left reader's start


def test_sparkline_flat_single_and_empty():
    assert sparkline_points([], 100, 40) == []
    assert sparkline_points([5], 0, 40) == []
    assert sparkline_points([5, 5, 5], 100, 40) == [(0.0, 20.0), (50.0, 20.0), (100.0, 20.0)]
    assert sparkline_points([7], 100, 40, padding=4) == [(96.0, 20.0)]
    assert sparkline_points([7], 100, 40, padding=4, rtl=True) == [(4.0, 20.0)]
    assert sparkline_points([1, 2], 6, 40, padding=3) == []  # no room left to draw


def test_sparkline_points_stay_inside_the_padding():
    points = sparkline_points([3, 1, 4, 1, 5, 9, 2, 6], 160, 40, padding=5)
    assert len(points) == 8
    assert all(5 <= x <= 155 and 5 <= y <= 35 for x, y in points)
    assert sparkline_points([-5, 10], 100, 40)[0][1] == 40.0  # negative clamps to 0


# ── Text helpers ──────────────────────────────────────────────────────────


def test_short_time_formats_iso_and_tolerates_garbage():
    assert short_time("2026-10-11T07:33:02") == "2026-10-11 07:33"
    assert short_time("yesterday") == "yesterday"
    assert short_time("") == ""
    assert short_time(None) == ""


def test_display_name_falls_back_to_output_then_folder():
    assert ProjectSummary(path="/x/tool/p2e.toml", output_name="Tool").display_name() == "Tool"
    assert ProjectSummary(path="/x/tool/p2e.toml").display_name() == "tool"
    assert ProjectSummary(path="p2e.toml").display_name() == "p2e.toml"
    assert ProjectSummary(path="").size_delta() is None


def test_release_timestamp_follows_the_folder(tmp_path):
    folder = tmp_path / "release" / "2.0.0"
    folder.mkdir(parents=True)
    stamp = time.mktime((2026, 1, 2, 3, 4, 5, 0, 0, -1))
    os.utime(folder, (stamp, stamp))
    assert short_time(last_release(str(tmp_path)).timestamp) == "2026-01-02 03:04"
