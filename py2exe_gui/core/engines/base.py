"""The build engine interface: what every freezer (PyInstaller, Nuitka...) provides.

Before 2.0 the converter knew exactly one engine, and its knowledge was spread
over ``builder.py`` (the command), ``build_stages.py`` (the progress phases),
``smoke_test.py`` (where the EXE lands) and ``diagnostics.py`` (what a failure
in its log means). An ``Engine`` gathers those answers behind one interface,
so a second engine is a new class rather than an ``if`` in every module.

UI-independent like the rest of ``core/``: an engine returns stage *keys*,
finding *codes* and feature *keys*, and the caller translates them.
"""

import os
import subprocess
from dataclasses import dataclass
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Tuple

from py2exe_gui.core.config import BuildConfig

# ── Features ───────────────────────────────────────────────────────────────
#
# Stable keys for the options an engine may or may not support. The feature
# matrix answers "can this engine do what the project asks?" before a build,
# so an option is never passed to an engine that does not have it.

FEATURE_ONEFILE = "onefile"
FEATURE_ONEDIR = "onedir"
FEATURE_WINDOWED = "windowed"
FEATURE_ICON = "icon"
FEATURE_VERSION_INFO = "version_info"
FEATURE_SPLASH = "splash"
FEATURE_MANIFEST = "manifest"
FEATURE_UPX = "upx"
FEATURE_STRIP = "strip"
FEATURE_OPTIMIZE = "optimize"
FEATURE_CLEAN = "clean"
FEATURE_DATA_FILES = "data_files"
FEATURE_HIDDEN_IMPORTS = "hidden_imports"
FEATURE_EXCLUDE_MODULES = "exclude_modules"
FEATURE_RUNTIME_KIT = "runtime_kit"
FEATURE_SIZE_REPORT = "size_report"
FEATURE_WARN_FILE = "warn_file"

#: Every feature key, in the order a comparison table lists them.
FEATURES: Tuple[str, ...] = (
    FEATURE_ONEFILE, FEATURE_ONEDIR, FEATURE_WINDOWED, FEATURE_ICON,
    FEATURE_VERSION_INFO, FEATURE_SPLASH, FEATURE_MANIFEST, FEATURE_UPX,
    FEATURE_STRIP, FEATURE_OPTIMIZE, FEATURE_CLEAN, FEATURE_DATA_FILES,
    FEATURE_HIDDEN_IMPORTS, FEATURE_EXCLUDE_MODULES, FEATURE_RUNTIME_KIT,
    FEATURE_SIZE_REPORT, FEATURE_WARN_FILE,
)


def features_used(config: BuildConfig) -> List[str]:
    """The features ``config`` actually asks for, in ``FEATURES`` order.

    Only settings that change the output count: ``clean`` is on by default
    and harmless to drop, so it is not listed as "used".
    """
    used = {
        FEATURE_ONEFILE: config.onefile,
        FEATURE_ONEDIR: not config.onefile,
        FEATURE_WINDOWED: config.windowed or config.noconsole,
        FEATURE_ICON: bool(config.icon),
        FEATURE_VERSION_INFO: bool(config.version_file),
        FEATURE_SPLASH: bool(config.splash_image),
        FEATURE_MANIFEST: bool(config.manifest_file),
        FEATURE_UPX: config.upx,
        FEATURE_STRIP: config.strip,
        FEATURE_OPTIMIZE: config.optimize > 0,
        FEATURE_DATA_FILES: bool(config.extra_files),
        FEATURE_HIDDEN_IMPORTS: bool(config.hidden_imports),
        FEATURE_RUNTIME_KIT: config.runtime_kit.enabled,
    }
    return [f for f in FEATURES if used.get(f)]


# ── Progress ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Stage:
    """One build phase and the percentage band it occupies."""

    key: str
    start: int
    end: int
    # Lowercase substrings that announce the phase in the engine's output.
    markers: Tuple[str, ...]
    # Lines of in-phase chatter per 1% of creep. Larger = slower creep, used
    # for phases that emit hundreds of lines (analysis, hooks).
    lines_per_percent: int = 4


# The bar is never driven to 100 by log text — only an exit code of 0 means
# done. A build that prints "completed successfully" for one step and then
# dies in the next must not have shown 100% on the way there.
MAX_LOG_PERCENT = 97


class StageTracker:
    """Follows an engine's output and reports (stage, percent), monotonically.

    Percentages are the phase boundaries; within a phase the value creeps
    slowly so a long phase still looks alive, but it can never run past the
    start of a phase that has not been reached yet.
    """

    def __init__(self, stages: Sequence[Stage]) -> None:
        self.stages: Tuple[Stage, ...] = tuple(stages)
        self._index = 0
        self._lines_in_stage = 0
        self.percent = 0

    @property
    def stage(self) -> str:
        """Key of the phase currently being reported."""
        return self.stages[self._index].key

    def feed(self, line: str) -> bool:
        """Consume one output line. Returns True when stage or percent moved."""
        if not line:
            return False
        lowered = line.lower()

        # Only look ahead: markers for phases already passed are ignored, so
        # output that mentions an earlier phase cannot drag the bar backwards.
        for offset in range(len(self.stages) - 1, self._index - 1, -1):
            stage = self.stages[offset]
            if stage.markers and any(m in lowered for m in stage.markers):
                if offset != self._index:
                    self._index = offset
                    self._lines_in_stage = 0
                return self._set_percent(max(self.percent, stage.start))

        # In-phase chatter: creep, but never into the next phase's band.
        current = self.stages[self._index]
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


# ── The interface ──────────────────────────────────────────────────────────


class Engine:
    """A freezer the converter can drive.

    Subclasses set the class attributes and implement ``build_command``,
    ``locate_output`` and ``log_findings``. Everything else has a working
    default built on those.
    """

    #: Stable identifier, stored in ``BuildConfig.engine`` and ``p2e.toml``.
    name: str = ""
    #: Shown to the user as is (a product name, not translated).
    display_name: str = ""
    #: The module run with ``python -m`` to build.
    module: str = ""
    #: Feature key → supported.
    feature_matrix: Dict[str, bool] = {}
    #: The phases of a build, in the order the engine reaches them.
    stages: Tuple[Stage, ...] = ()
    #: Text in a build log that means the engine is not installed.
    missing_markers: Tuple[str, ...] = ()
    #: The finding code reported when it is not installed.
    missing_code: str = ""

    # Features

    def supports(self, feature: str) -> bool:
        return bool(self.feature_matrix.get(feature, False))

    def supported_features(self) -> FrozenSet[str]:
        return frozenset(f for f, ok in self.feature_matrix.items() if ok)

    def unsupported_features(self, config: BuildConfig) -> List[str]:
        """What ``config`` asks for that this engine cannot do."""
        return [f for f in features_used(config) if not self.supports(f)]

    # Availability

    def version_command(self, python: str) -> List[str]:
        return [python, "-m", self.module, "--version"]

    def version(self, python: str, timeout: float = 60.0, run=None) -> str:
        """The installed version as the engine prints it, or '' when absent."""
        try:
            completed = (run or subprocess.run)(
                self.version_command(python), capture_output=True, text=True,
                timeout=timeout,
            )
        except (OSError, subprocess.SubprocessError):
            return ""
        if completed.returncode != 0:
            return ""
        return self.parse_version_output(completed.stdout or "")

    def parse_version_output(self, text: str) -> str:
        """The version from ``--version`` output: its first non-empty line."""
        for line in text.splitlines():
            if line.strip():
                return line.strip()
        return ""

    def is_available(self, python: str, run=None) -> bool:
        return bool(self.version(python, run=run))

    # Building

    def build_command(
        self,
        config: BuildConfig,
        python_executable: Optional[str] = None,
        platform: Optional[str] = None,
        extra_options: Sequence[str] = (),
    ) -> Tuple[Optional[List[str]], Optional[str]]:
        """``(command, None)`` or ``(None, user-facing error)``."""
        raise NotImplementedError

    def progress_tracker(self) -> StageTracker:
        return StageTracker(self.stages)

    def stage_keys(self) -> List[str]:
        return [s.key for s in self.stages]

    # Output

    def locate_output(self, config: BuildConfig) -> str:
        """The built EXE (one file) or app folder (folder mode), or ''."""
        raise NotImplementedError

    def locate_executable(self, config: BuildConfig) -> str:
        """The program to run: the one-file EXE, or the EXE inside the folder."""
        output = self.locate_output(config)
        if not output or os.path.isfile(output):
            return output
        name = self.output_stem(config)
        for candidate in (name + ".exe", name):
            path = os.path.join(output, candidate)
            if os.path.isfile(path):
                return path
        return ""

    def output_stem(self, config: BuildConfig) -> str:
        return config.output_name or os.path.splitext(os.path.basename(config.source))[0]

    # Diagnostics

    def log_findings(self, text: str, origin: str, imports: Iterable[str]) -> list:
        """Findings for failures only this engine's build log reports."""
        return []

    def build_findings(self, config: BuildConfig, local_modules: Iterable[str] = (),
                       min_mtime: float = 0.0) -> list:
        """Findings from the files a build leaves behind (PyInstaller's warn file)."""
        return []

    # Size lab

    def analyze_size(self, config: BuildConfig, local_modules=None):
        """A ``size_analyzer.SizeReport`` of the last build, or None if unsupported."""
        return None


class UnknownEngineError(ValueError):
    """``BuildConfig.engine`` names an engine this version does not know."""
