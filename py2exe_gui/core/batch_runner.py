"""Turn one configuration plus N source files into a queue of build jobs.

Batch builds run **sequentially**, not in parallel. PyInstaller writes into
``build/`` and ``dist/`` under the working directory, so two concurrent runs
sharing an output directory race on the same spec and cache files. The queue
here is therefore an ordered list, and the thread that consumes it runs one job
at a time.

UI-independent: this module builds the jobs and reports on them; the thread
that executes them lives in ``ui/batch_thread.py``.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Iterable, List

from py2exe_gui.core.config import BuildConfig

PENDING = "pending"
RUNNING = "running"
SUCCESS = "success"
FAILED = "failed"
CANCELLED = "cancelled"


@dataclass
class BatchJob:
    """One source file queued for conversion, plus its outcome."""

    source: str
    output_name: str = ""
    status: str = PENDING
    message: str = ""
    duration_seconds: float = 0.0

    @property
    def finished(self) -> bool:
        return self.status in (SUCCESS, FAILED, CANCELLED)

    def label(self) -> str:
        """Compact display label: '⏳ name' / '✓ name' / '✗ name'."""
        marker = {
            PENDING: "⏳",
            RUNNING: "▶",
            SUCCESS: "✓",
            FAILED: "✗",
            CANCELLED: "⊘",
        }.get(self.status, "•")
        return f"{marker} {self.output_name or os.path.basename(self.source)}"


def default_output_name(source: str) -> str:
    """The executable name PyInstaller would pick for ``source``."""
    return os.path.splitext(os.path.basename(source))[0]


def make_jobs(sources: Iterable[str]) -> List[BatchJob]:
    """One job per source path, de-duplicated, order preserved.

    The same file queued twice would build twice into the same output and the
    second run would simply overwrite the first, so duplicates are dropped.
    """
    jobs: List[BatchJob] = []
    seen = set()
    for source in sources:
        path = str(source or "").strip()
        if not path:
            continue
        key = os.path.normcase(os.path.abspath(path))
        if key in seen:
            continue
        seen.add(key)
        jobs.append(BatchJob(source=path, output_name=default_output_name(path)))
    return jobs


def job_config(job: BatchJob, base: BuildConfig) -> BuildConfig:
    """Copy ``base`` with this job's source and output name substituted.

    Everything else — icon, hidden imports, options — is shared across the
    batch, which is the point of running one. Per-file fields that only make
    sense for a single build (``version_file``, ``manifest_file``) are dropped
    so a stale temp path from an earlier single build cannot leak in.
    """
    data = base.to_dict()
    data["source"] = job.source
    data["output_name"] = job.output_name or default_output_name(job.source)
    if not data.get("output_dir"):
        data["output_dir"] = os.path.dirname(os.path.abspath(job.source))
    data["version_file"] = ""
    data["manifest_file"] = ""
    return BuildConfig.from_dict(data)


@dataclass
class BatchSummary:
    """Counts and timings for a finished (or partial) batch run."""

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    cancelled: int = 0
    pending: int = 0
    duration_seconds: float = 0.0
    failures: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, object]:
        return {
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "cancelled": self.cancelled,
            "pending": self.pending,
            "duration_seconds": round(self.duration_seconds, 2),
            "failures": list(self.failures),
        }


def summarize(jobs: Iterable[BatchJob]) -> BatchSummary:
    """Aggregate job outcomes into a report the UI can show verbatim."""
    summary = BatchSummary()
    for job in jobs:
        summary.total += 1
        summary.duration_seconds += job.duration_seconds
        if job.status == SUCCESS:
            summary.succeeded += 1
        elif job.status == FAILED:
            summary.failed += 1
            summary.failures.append(job.output_name or os.path.basename(job.source))
        elif job.status == CANCELLED:
            summary.cancelled += 1
        else:
            summary.pending += 1
    return summary
