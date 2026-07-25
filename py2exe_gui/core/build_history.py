"""Persistent log of recent builds so users can revisit/restore configs."""

import json
import os
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from typing import List, Optional


@dataclass
class BuildRecord:
    """A single build entry suitable for display and restoration.

    Every field has a default so a record written by a different version of
    the app still loads: see ``BuildRecord.from_dict``.
    """

    timestamp: str = ""  # ISO 8601
    source: str = ""
    output_name: str = ""
    success: bool = False
    duration_seconds: float = 0.0
    config: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "BuildRecord":
        """Build a record from JSON, ignoring unknown keys.

        A plain ``BuildRecord(**data)`` raises TypeError as soon as a newer
        version adds a field, and the caller's blanket except then wiped the
        entire history file. Dropping unknown keys keeps old clients working.
        """
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def short_label(self) -> str:
        """Compact display label: '✓ name @ time' or '✗ name @ time'."""
        marker = "✓" if self.success else "✗"
        name = self.output_name or os.path.basename(self.source) or "?"
        try:
            t = datetime.fromisoformat(self.timestamp).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            t = self.timestamp
        return f"{marker} {name} @ {t}"


class BuildHistory:
    """Bounded list of recent builds, persisted to a JSON file."""

    def __init__(self, path: str, max_records: int = 20):
        self.path = path
        self.max_records = max_records
        self.records: List[BuildRecord] = []
        # Reason for the most recent load/save failure, for the caller to log.
        self.last_error: str = ""
        self.load()

    def load(self) -> bool:
        """Read the history file. Returns False and sets ``last_error`` on failure."""
        self.last_error = ""
        if not os.path.exists(self.path):
            self.records = []
            return True
        try:
            with open(self.path, encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, ValueError) as e:
            self.records = []
            self.last_error = str(e)
            return False

        if not isinstance(raw, list):
            self.records = []
            self.last_error = "history file is not a list"
            return False

        # Skip individual malformed entries rather than discarding the file.
        records, skipped = [], 0
        for item in raw:
            if not isinstance(item, dict):
                skipped += 1
                continue
            try:
                records.append(BuildRecord.from_dict(item))
            except (TypeError, ValueError):
                skipped += 1
        self.records = records
        if skipped:
            self.last_error = f"skipped {skipped} malformed record(s)"
        return True

    def save(self) -> bool:
        """Persist the history. Returns False and sets ``last_error`` on failure."""
        self.last_error = ""
        try:
            directory = os.path.dirname(self.path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(
                    [asdict(r) for r in self.records],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except (OSError, TypeError) as e:
            self.last_error = str(e)
            return False
        return True

    def add(self, record: BuildRecord) -> bool:
        """Insert ``record`` at the top and drop entries beyond ``max_records``."""
        self.records.insert(0, record)
        if len(self.records) > self.max_records:
            self.records = self.records[: self.max_records]
        return self.save()

    def clear(self) -> bool:
        self.records = []
        return self.save()

    def get(self, index: int) -> Optional[BuildRecord]:
        if 0 <= index < len(self.records):
            return self.records[index]
        return None

    def __len__(self) -> int:
        return len(self.records)


def make_record(
    source: str,
    output_name: str,
    success: bool,
    duration_seconds: float,
    config: dict,
    timestamp: Optional[str] = None,
) -> BuildRecord:
    """Factory that fills in the timestamp by default."""
    return BuildRecord(
        timestamp=timestamp or datetime.now().isoformat(timespec="seconds"),
        source=source,
        output_name=output_name,
        success=success,
        duration_seconds=duration_seconds,
        config=dict(config),
    )
