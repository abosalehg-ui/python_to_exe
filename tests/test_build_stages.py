"""Tests for stage detection in PyInstaller output."""

import pytest

from py2exe_gui.core.build_stages import (
    MAX_LOG_PERCENT,
    STAGES,
    BuildStageTracker,
    stage_for,
    stage_keys,
)

# A trimmed but faithful slice of real PyInstaller 6.x output, in order.
REAL_OUTPUT = [
    "126 INFO: PyInstaller: 6.3.0",
    "126 INFO: Python: 3.11.5",
    "130 INFO: Platform: Windows-10-10.0.19045-SP0",
    "131 INFO: checking Analysis",
    "133 INFO: Building Analysis because Analysis-00.toc is non existent",
    "133 INFO: Initializing module dependency graph...",
    "140 INFO: Analyzing base_library.zip ...",
    "900 INFO: Processing module hooks...",
    "905 INFO: Loading module hook 'hook-encodings.py' from ...",
    "1200 INFO: Looking for ctypes DLLs",
    "1210 INFO: Looking for dynamic libraries",
    "1400 INFO: checking PYZ",
    "1405 INFO: Building PYZ (ZlibArchive) ...",
    "1500 INFO: Building PYZ ... completed successfully.",
    "1520 INFO: checking PKG",
    "1530 INFO: Building PKG (CArchive) app.pkg ...",
    "2000 INFO: Building PKG ... completed successfully.",
    "2010 INFO: Bootloader ...",
    "2020 INFO: checking EXE",
    "2030 INFO: Building EXE from EXE-00.toc",
    "2100 INFO: Copying bootloader EXE to ...",
    "2500 INFO: Building EXE from EXE-00.toc completed successfully.",
]


def test_stages_are_ordered_and_non_overlapping():
    for earlier, later in zip(STAGES, STAGES[1:]):
        assert earlier.start < earlier.end
        assert earlier.end <= later.start


def test_starts_at_zero():
    tracker = BuildStageTracker()
    assert tracker.percent == 0
    assert tracker.stage == "starting"


def test_progress_is_monotonic_across_a_real_build():
    tracker = BuildStageTracker()
    seen = [tracker.percent]
    for line in REAL_OUTPUT:
        tracker.feed(line)
        seen.append(tracker.percent)
    assert seen == sorted(seen), f"progress went backwards: {seen}"


def test_reaches_the_exe_stage_on_a_real_build():
    tracker = BuildStageTracker()
    for line in REAL_OUTPUT:
        tracker.feed(line)
    assert tracker.stage == "exe"
    assert tracker.percent >= 82


def test_stage_advances_through_the_expected_sequence():
    tracker = BuildStageTracker()
    order = []
    for line in REAL_OUTPUT:
        tracker.feed(line)
        if not order or order[-1] != tracker.stage:
            order.append(tracker.stage)
    assert order == [
        "starting",
        "analyzing",
        "hooks",
        "dependencies",
        "pyz",
        "pkg",
        "exe",
    ]


def test_never_exceeds_the_log_ceiling():
    """Only a zero exit code means done, so text alone cannot reach 100."""
    tracker = BuildStageTracker()
    for line in REAL_OUTPUT * 50:
        tracker.feed(line)
    assert tracker.percent <= MAX_LOG_PERCENT
    assert MAX_LOG_PERCENT < 100


def test_a_late_earlier_stage_marker_does_not_rewind():
    """Regression guard: output mentioning "Analyzing" after the EXE step."""
    tracker = BuildStageTracker()
    for line in REAL_OUTPUT:
        tracker.feed(line)
    high_water = tracker.percent
    tracker.feed("9000 INFO: Analyzing hidden import 'pkg_resources'")
    assert tracker.percent >= high_water
    assert tracker.stage == "exe"


def test_in_stage_chatter_creeps_but_stays_inside_the_band():
    tracker = BuildStageTracker()
    tracker.feed("INFO: Building Analysis because Analysis-00.toc is non existent")
    analyzing = stage_for("analyzing")
    for i in range(2000):
        tracker.feed(f"INFO: some analysis chatter {i}")
    assert tracker.stage == "analyzing"
    assert tracker.percent < analyzing.end


def test_empty_lines_are_ignored():
    tracker = BuildStageTracker()
    assert tracker.feed("") is False
    assert tracker.percent == 0


def test_feed_reports_whether_anything_changed():
    tracker = BuildStageTracker()
    assert tracker.feed("INFO: Building PYZ (ZlibArchive) ...") is True
    # Same marker again: already there, so nothing moved.
    assert tracker.feed("INFO: Building PYZ (ZlibArchive) ...") is False


def test_reset_returns_to_the_beginning():
    tracker = BuildStageTracker()
    for line in REAL_OUTPUT:
        tracker.feed(line)
    tracker.reset()
    assert tracker.percent == 0
    assert tracker.stage == "starting"


def test_matching_is_case_insensitive():
    tracker = BuildStageTracker()
    tracker.feed("INFO: BUILDING EXE FROM EXE-00.TOC")
    assert tracker.stage == "exe"


@pytest.mark.parametrize("key", stage_keys())
def test_every_stage_key_is_resolvable(key):
    assert stage_for(key) is not None


def test_stage_for_unknown_key_is_none():
    assert stage_for("not-a-stage") is None
