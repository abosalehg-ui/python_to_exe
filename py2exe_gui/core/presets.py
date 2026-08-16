"""A named library of saved build configurations.

The app already saves and loads a single settings file through a file dialog.
That works, but it makes every reusable setup a file the user has to find
again. A preset is the same configuration dictionary stored under a name in one
per-user file, so the common case ("build this the way I built the last one")
is a dropdown rather than a file browser.

Presets are ordinary data, not code — but a preset carries ``extra_args``, and
an *imported* preset file can therefore carry ``--runtime-hook``. Importing
routes through the same ``find_dangerous_args`` confirmation as loading a
settings file; see ``MainWindow._confirm_untrusted_config``.
"""

import json
import os
from typing import Dict, List, Optional

MAX_NAME_LENGTH = 60


def normalize_name(name: str) -> str:
    """Trim and collapse whitespace in a preset name; '' when unusable."""
    cleaned = " ".join(str(name or "").split())
    return cleaned[:MAX_NAME_LENGTH]


class PresetLibrary:
    """Named build configurations persisted to a single JSON object file."""

    def __init__(self, path: str):
        self.path = path
        self.presets: Dict[str, dict] = {}
        # Reason for the most recent load/save failure, for the caller to log.
        self.last_error: str = ""
        self.load()

    def load(self) -> bool:
        """Read the preset file. Returns False and sets ``last_error`` on failure."""
        self.last_error = ""
        if not os.path.exists(self.path):
            self.presets = {}
            return True
        try:
            with open(self.path, encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, ValueError) as e:
            self.presets = {}
            self.last_error = str(e)
            return False

        if not isinstance(raw, dict):
            self.presets = {}
            self.last_error = "preset file is not an object"
            return False

        # Drop individual malformed entries rather than discarding the file,
        # matching how BuildHistory treats a bad record.
        presets, skipped = {}, 0
        for name, config in raw.items():
            key = normalize_name(name)
            if key and isinstance(config, dict):
                presets[key] = config
            else:
                skipped += 1
        self.presets = presets
        if skipped:
            self.last_error = f"skipped {skipped} malformed preset(s)"
        return True

    def save(self) -> bool:
        """Persist the library. Returns False and sets ``last_error`` on failure."""
        self.last_error = ""
        try:
            directory = os.path.dirname(self.path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.presets, f, ensure_ascii=False, indent=2)
        except (OSError, TypeError) as e:
            self.last_error = str(e)
            return False
        return True

    # ── Access ─────────────────────────────────────────────────────────────

    def names(self) -> List[str]:
        """Preset names, sorted for a stable dropdown order."""
        return sorted(self.presets, key=str.casefold)

    def get(self, name: str) -> Optional[dict]:
        return self.presets.get(normalize_name(name))

    def has(self, name: str) -> bool:
        return normalize_name(name) in self.presets

    def put(self, name: str, config: dict) -> bool:
        """Add or overwrite a preset. False when the name is empty or I/O fails."""
        key = normalize_name(name)
        if not key or not isinstance(config, dict):
            self.last_error = "invalid preset name or payload"
            return False
        self.presets[key] = dict(config)
        return self.save()

    def delete(self, name: str) -> bool:
        key = normalize_name(name)
        if key not in self.presets:
            self.last_error = "no such preset"
            return False
        del self.presets[key]
        return self.save()

    def __len__(self) -> int:
        return len(self.presets)

    # ── Sharing ────────────────────────────────────────────────────────────

    def export_all(self) -> dict:
        """A plain dict suitable for writing to a shareable file."""
        return {name: dict(config) for name, config in self.presets.items()}

    def import_all(self, data: dict, overwrite: bool = False) -> List[str]:
        """Merge presets from ``data``; returns the names actually added.

        Existing names are kept unless ``overwrite`` is set, so importing a
        shared file cannot quietly replace the user's own setups.
        """
        if not isinstance(data, dict):
            self.last_error = "imported file is not an object"
            return []
        added = []
        for name, config in data.items():
            key = normalize_name(name)
            if not key or not isinstance(config, dict):
                continue
            if key in self.presets and not overwrite:
                continue
            self.presets[key] = dict(config)
            added.append(key)
        if added:
            self.save()
        return added
