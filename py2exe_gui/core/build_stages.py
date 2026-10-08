"""Map PyInstaller's own output onto the build stage it announces.

The progress bar used to be pure heuristic: it nudged forward a few percent
whenever a line containing ``Analyzing``/``Processing``/``Building`` went past,
so it tracked how *chatty* a build was rather than how far along it was. A
project with 400 hook lines and one with 40 sat at completely different values
at the same point in the build, and neither number meant anything.

PyInstaller announces every phase it enters — ``Building PYZ``, ``Building
EXE``, ``Building COLLECT`` and so on. The phase is therefore knowable exactly,
and this module reads it off the output. Percentages are the phase boundaries;
within a phase the value creeps slowly so a long analysis still looks alive,
but it can never run past the start of the phase that has not been reached yet.

Since 2.0 the tracker is generic (``engines.base.StageTracker``) and each
engine owns its phase table; this module keeps the PyInstaller names that
existed before, as a backward-compatible shim.

UI-independent by design: ``feed()`` returns a stage *key*, and the caller
resolves it to a translated label.
"""

from typing import List, Optional, Sequence

from py2exe_gui.core.engines.base import MAX_LOG_PERCENT, Stage, StageTracker
from py2exe_gui.core.engines.pyinstaller import STAGES

__all__ = [
    "MAX_LOG_PERCENT",
    "STAGES",
    "BuildStageTracker",
    "Stage",
    "stage_for",
    "stage_keys",
]


class BuildStageTracker(StageTracker):
    """Follows build output and reports (stage, percent), monotonically.

    PyInstaller's phases unless another engine's ``stages`` are given.
    """

    def __init__(self, stages: Optional[Sequence[Stage]] = None) -> None:
        super().__init__(STAGES if stages is None else stages)


def stage_keys() -> List[str]:
    """Every stage key, in the order PyInstaller reaches them."""
    return [s.key for s in STAGES]


def stage_for(key: str) -> Optional[Stage]:
    """Look up a stage by key, or None when the key is unknown."""
    for stage in STAGES:
        if stage.key == key:
            return stage
    return None
