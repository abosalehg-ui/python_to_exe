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

UI-independent by design: ``feed()`` returns a stage *key*, and the caller
resolves it to a translated label.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class Stage:
    """One PyInstaller phase and the percentage band it occupies."""

    key: str
    start: int
    end: int
    # Lowercase substrings that announce the phase in PyInstaller's output.
    markers: Tuple[str, ...]
    # Lines of in-phase chatter per 1% of creep. Larger = slower creep, used
    # for phases that emit hundreds of lines (analysis, hooks).
    lines_per_percent: int = 4


# Ordered: a marker can only ever move the tracker forward, so a stray late
# mention of an earlier phase name cannot rewind the bar.
STAGES: Tuple[Stage, ...] = (
    Stage("starting", 0, 5, (), lines_per_percent=6),
    Stage(
        "analyzing",
        5,
        40,
        (
            "initializing module dependency graph",
            "analyzing base_library.zip",
            "analyzing ",
            "checking analysis",
            "building analysis",
        ),
        lines_per_percent=10,
    ),
    Stage(
        "hooks",
        40,
        55,
        ("processing module hooks", "loading module hook", "processing pre-safe import"),
        lines_per_percent=8,
    ),
    Stage("dependencies", 55, 62, ("looking for dynamic libraries", "looking for ctypes")),
    Stage("pyz", 62, 72, ("checking pyz", "building pyz")),
    Stage("pkg", 72, 82, ("checking pkg", "building pkg")),
    Stage("exe", 82, 92, ("checking exe", "building exe", "copying bootloader")),
    Stage("collect", 92, 97, ("checking collect", "building collect")),
)

# The bar is never driven to 100 by log text — only an exit code of 0 means
# done. A build that prints "completed successfully" for its PYZ and then dies
# in the EXE step must not have shown 100% on the way there.
MAX_LOG_PERCENT = 97


class BuildStageTracker:
    """Follows PyInstaller output and reports (stage, percent), monotonically."""

    def __init__(self) -> None:
        self._index = 0
        self._lines_in_stage = 0
        self.percent = 0

    @property
    def stage(self) -> str:
        """Key of the phase currently being reported."""
        return STAGES[self._index].key

    def feed(self, line: str) -> bool:
        """Consume one output line. Returns True when stage or percent moved."""
        if not line:
            return False
        lowered = line.lower()

        # Only look ahead: markers for phases already passed are ignored, so
        # output that mentions an earlier phase cannot drag the bar backwards.
        for offset in range(len(STAGES) - 1, self._index - 1, -1):
            stage = STAGES[offset]
            if stage.markers and any(m in lowered for m in stage.markers):
                if offset != self._index:
                    self._index = offset
                    self._lines_in_stage = 0
                return self._set_percent(max(self.percent, stage.start))

        # In-phase chatter: creep, but never into the next phase's band.
        current = STAGES[self._index]
        self._lines_in_stage += 1
        creep = self._lines_in_stage // current.lines_per_percent
        ceiling = max(current.start, current.end - 1)
        return self._set_percent(min(ceiling, current.start + creep))

    def _set_percent(self, value: int) -> bool:
        value = min(MAX_LOG_PERCENT, max(self.percent, value))
        if value == self.percent:
            return False
        self.percent = value
        return True

    def reset(self) -> None:
        self._index = 0
        self._lines_in_stage = 0
        self.percent = 0


def stage_keys() -> List[str]:
    """Every stage key, in the order PyInstaller reaches them."""
    return [s.key for s in STAGES]


def stage_for(key: str) -> Optional[Stage]:
    """Look up a stage by key, or None when the key is unknown."""
    for stage in STAGES:
        if stage.key == key:
            return stage
    return None
