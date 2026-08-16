"""Tests for building and summarizing a batch of conversion jobs."""

import os

from py2exe_gui.core.batch_runner import (
    CANCELLED,
    FAILED,
    PENDING,
    SUCCESS,
    BatchJob,
    default_output_name,
    job_config,
    make_jobs,
    summarize,
)
from py2exe_gui.core.config import BuildConfig

# ── Job construction ───────────────────────────────────────────────────────


def test_default_output_name_strips_directory_and_extension():
    assert default_output_name(os.path.join("some", "dir", "app.py")) == "app"


def test_make_jobs_one_per_source():
    jobs = make_jobs(["a.py", "b.py"])
    assert [j.source for j in jobs] == ["a.py", "b.py"]
    assert [j.output_name for j in jobs] == ["a", "b"]


def test_make_jobs_preserves_order():
    jobs = make_jobs(["z.py", "a.py", "m.py"])
    assert [j.output_name for j in jobs] == ["z", "a", "m"]


def test_make_jobs_drops_duplicates():
    """The same file twice would just build over itself the second time."""
    jobs = make_jobs(["a.py", "a.py", "b.py"])
    assert [j.output_name for j in jobs] == ["a", "b"]


def test_make_jobs_drops_duplicates_that_differ_only_by_path_form():
    jobs = make_jobs(["a.py", os.path.join(".", "a.py")])
    assert len(jobs) == 1


def test_make_jobs_skips_blank_entries():
    assert make_jobs(["", "   ", "a.py"]) == make_jobs(["a.py"])


def test_new_jobs_start_pending():
    assert make_jobs(["a.py"])[0].status == PENDING


def test_job_label_marks_status():
    job = BatchJob(source="a.py", output_name="a")
    assert "a" in job.label()
    job.status = SUCCESS
    assert job.label().startswith("✓")
    job.status = FAILED
    assert job.label().startswith("✗")


def test_finished_property():
    job = BatchJob(source="a.py")
    assert job.finished is False
    job.status = SUCCESS
    assert job.finished is True


# ── Per-job configuration ──────────────────────────────────────────────────


def test_job_config_substitutes_source_and_name():
    base = BuildConfig(source="original.py", output_name="original", icon="app.ico")
    job = BatchJob(source=os.path.join("dir", "other.py"), output_name="other")
    config = job_config(job, base)
    assert config.source == os.path.join("dir", "other.py")
    assert config.output_name == "other"


def test_job_config_shares_the_rest_of_the_settings():
    base = BuildConfig(
        icon="app.ico",
        onefile=False,
        hidden_imports=["requests"],
        extra_args="--noupx",
    )
    config = job_config(BatchJob(source="a.py", output_name="a"), base)
    assert config.icon == "app.ico"
    assert config.onefile is False
    assert config.hidden_imports == ["requests"]
    assert config.extra_args == "--noupx"


def test_job_config_defaults_the_output_dir_to_the_source_folder():
    base = BuildConfig(output_dir="")
    job = BatchJob(source=os.path.join("some", "dir", "a.py"), output_name="a")
    config = job_config(job, base)
    assert config.output_dir == os.path.dirname(os.path.abspath(job.source))


def test_job_config_keeps_an_explicit_output_dir():
    base = BuildConfig(output_dir=os.path.join("chosen", "out"))
    config = job_config(BatchJob(source="a.py", output_name="a"), base)
    assert config.output_dir == os.path.join("chosen", "out")


def test_job_config_drops_per_build_temp_files():
    """A version/manifest temp path from an earlier single build is stale."""
    base = BuildConfig(version_file="/tmp/v.txt", manifest_file="/tmp/m.xml")
    config = job_config(BatchJob(source="a.py", output_name="a"), base)
    assert config.version_file == ""
    assert config.manifest_file == ""


def test_job_config_derives_a_missing_output_name():
    config = job_config(BatchJob(source="a.py", output_name=""), BuildConfig())
    assert config.output_name == "a"


def test_job_config_does_not_mutate_the_base():
    base = BuildConfig(source="original.py")
    job_config(BatchJob(source="other.py", output_name="other"), base)
    assert base.source == "original.py"


# ── Summary ────────────────────────────────────────────────────────────────


def test_summarize_counts_each_outcome():
    jobs = [
        BatchJob("a.py", "a", status=SUCCESS, duration_seconds=1.0),
        BatchJob("b.py", "b", status=FAILED, duration_seconds=2.0),
        BatchJob("c.py", "c", status=CANCELLED),
        BatchJob("d.py", "d"),
    ]
    summary = summarize(jobs)
    assert summary.total == 4
    assert summary.succeeded == 1
    assert summary.failed == 1
    assert summary.cancelled == 1
    assert summary.pending == 1


def test_summarize_totals_the_durations():
    jobs = [
        BatchJob("a.py", "a", status=SUCCESS, duration_seconds=1.5),
        BatchJob("b.py", "b", status=SUCCESS, duration_seconds=2.25),
    ]
    assert summarize(jobs).duration_seconds == 3.75


def test_summarize_names_the_failures():
    jobs = [
        BatchJob("a.py", "a", status=SUCCESS),
        BatchJob("b.py", "b", status=FAILED),
    ]
    assert summarize(jobs).failures == ["b"]


def test_summarize_of_nothing():
    summary = summarize([])
    assert summary.total == 0
    assert summary.failures == []


def test_summary_as_dict_is_json_friendly():
    summary = summarize([BatchJob("a.py", "a", status=SUCCESS, duration_seconds=1.239)])
    data = summary.as_dict()
    assert data["total"] == 1
    assert data["duration_seconds"] == 1.24
