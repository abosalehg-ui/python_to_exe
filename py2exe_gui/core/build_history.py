"""Persistent log of recent builds so users can revisit/restore configs."""

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class BuildRecord:
    """A single build entry suitable for display and restoration."""

    timestamp: str  # ISO 8601
    source: str
    output_name: str
    success: bool
    duration_seconds: float = 0.0
    config: dict = field(default_factory=dict)

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
        self.load()

    def load(self) -> None:
        if not os.path.exists(self.path):
            self.records = []
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                raw = json.load(f)
            self.records = [BuildRecord(**r) for r in raw if isinstance(r, dict)]
        except Exception:
            self.records = []

    def save(self) -> None:
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(
                    [asdict(r) for r in self.records],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception:
            pass

    def add(self, record: BuildRecord) -> None:
        """Insert ``record`` at the top and drop entries beyond ``max_records``."""
        self.records.insert(0, record)
        if len(self.records) > self.max_records:
            self.records = self.records[: self.max_records]
        self.save()

    def clear(self) -> None:
        self.records = []
        self.save()

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
