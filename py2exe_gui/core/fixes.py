"""Findings and the fixes that resolve them, shared by the doctor and diagnostics.

The project doctor (before a build) and the diagnostics (after a build) both
answer the same question: "what will break, and what do I change?". They
report it in one shape so the UI can show both in one list and apply both
with one button.

UI-independent by design: a finding carries a ``code`` and ``params``, and the
UI resolves the code to translated text (``S.FINDING_<CODE>_TITLE``), the same
way ``build_stages`` hands back stage keys rather than labels.
"""

import os
from dataclasses import dataclass, field, replace
from typing import Dict, Iterable, List, Sequence, Tuple

from py2exe_gui.core.builder import split_extra_args
from py2exe_gui.core.config import BuildConfig

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"
SEVERITIES = (SEVERITY_ERROR, SEVERITY_WARNING, SEVERITY_INFO)

# Where a finding came from. Shown in the UI so the user knows whether it is a
# prediction (doctor) or something that actually happened (build, runtime).
ORIGIN_DOCTOR = "doctor"
ORIGIN_BUILD = "build"
ORIGIN_WARN = "warn"
ORIGIN_RUNTIME = "runtime"

# Fix kinds. Every kind here can be applied to a BuildConfig without touching
# the user's source code: editing someone's script behind their back is not a
# "fix", so code changes are offered as a snippet to copy instead.
FIX_HIDDEN_IMPORT = "hidden_import"
FIX_ADD_DATA = "add_data"
FIX_FLAG = "flag"
FIX_CONSOLE = "console"
FIX_SET_SOURCE = "set_source"
FIX_KINDS = (FIX_HIDDEN_IMPORT, FIX_ADD_DATA, FIX_FLAG, FIX_CONSOLE, FIX_SET_SOURCE)

# Every finding code the doctor and the diagnostics can emit. The UI looks up
# ``FINDING_<CODE>_TITLE`` / ``_DETAIL`` for each; a test keeps them in step.
FINDING_CODES = (
    # project_doctor
    "source_unreadable", "syntax_error", "missing_package", "package_needs_collect",
    "package_data_dir", "package_console_streams", "large_package",
    "multiple_qt_bindings", "other_qt_bindings_installed", "data_not_bundled",
    "relative_paths", "missing_freeze_support", "input_in_windowed",
    "stream_in_windowed", "no_entry_point", "no_entry_point_alone",
    "icon_not_ico", "icon_single_size",
    # diagnostics
    "pyinstaller_missing", "runtime_missing_module", "missing_metadata",
    "missing_data_file", "template_not_found", "streams_none", "dll_load_failed",
    "multiple_qt_bindings_build", "add_data_missing", "icon_wrong_format",
    "file_locked", "runtime_unhandled", "warn_missing_module",
    # 1.4: size lab and build environment
    "size_exclude_candidate", "env_not_created",
)

# Penalty per finding when computing the readiness score.
_SCORE_PENALTY = {SEVERITY_ERROR: 25, SEVERITY_WARNING: 10, SEVERITY_INFO: 0}


@dataclass(frozen=True)
class Fix:
    """One change to the build configuration.

    ``value`` meaning by kind:
      hidden_import → module name
      add_data      → absolute path of a file or folder to bundle
      flag          → "--flag argument" (a single PyInstaller option)
      console       → unused (turns the console back on)
      set_source    → absolute path of the script to build instead
    """

    kind: str
    value: str = ""

    def __post_init__(self):
        if self.kind not in FIX_KINDS:
            raise ValueError(f"unknown fix kind: {self.kind}")


@dataclass(frozen=True)
class Finding:
    """A problem (or a heads-up) with what to do about it."""

    code: str
    severity: str
    params: Dict[str, str] = field(default_factory=dict, hash=False, compare=False)
    fixes: Tuple[Fix, ...] = ()
    origin: str = ORIGIN_DOCTOR
    # Key into SNIPPETS when the remedy is a code change the user makes.
    snippet: str = ""

    @property
    def auto_fixable(self) -> bool:
        return bool(self.fixes)

    def key(self) -> Tuple[str, Tuple[Tuple[str, str], ...]]:
        """Identity for de-duplication across doctor/build/runtime passes."""
        return self.code, tuple(sorted(self.params.items()))


def flag_fix(flag: str, argument: str) -> Fix:
    return Fix(FIX_FLAG, f"{flag} {argument}")


def readiness_score(findings: Iterable[Finding]) -> int:
    """0–100: every error costs 25, every warning 10, info is free."""
    penalty = sum(_SCORE_PENALTY.get(f.severity, 0) for f in findings)
    return max(0, 100 - penalty)


def sort_findings(findings: Iterable[Finding]) -> List[Finding]:
    """Errors first, then warnings, then info; stable within a severity."""
    order = {s: i for i, s in enumerate(SEVERITIES)}
    return sorted(findings, key=lambda f: order.get(f.severity, len(order)))


def dedupe_findings(findings: Iterable[Finding]) -> List[Finding]:
    seen = set()
    unique = []
    for finding in findings:
        k = finding.key()
        if k in seen:
            continue
        seen.add(k)
        unique.append(finding)
    return unique


def has_flag(extra_args: str, flag: str, argument: str) -> bool:
    """True when ``--flag argument`` (or ``--flag=argument``) is already set."""
    tokens = split_extra_args(extra_args or "")
    for i, token in enumerate(tokens):
        if token == f"{flag}={argument}":
            return True
        if token == flag and i + 1 < len(tokens) and tokens[i + 1] == argument:
            return True
    return False


def fix_is_applied(config: BuildConfig, fix: Fix) -> bool:
    """Whether ``config`` already contains what ``fix`` would add."""
    if fix.kind == FIX_HIDDEN_IMPORT:
        return fix.value in config.hidden_imports
    if fix.kind == FIX_ADD_DATA:
        return any(_same_path(fix.value, p) for p in config.extra_files)
    if fix.kind == FIX_FLAG:
        flag, _, argument = fix.value.partition(" ")
        return has_flag(config.extra_args, flag, argument)
    if fix.kind == FIX_CONSOLE:
        return not config.windowed and not config.noconsole
    if fix.kind == FIX_SET_SOURCE:
        return _same_path(fix.value, config.source)
    return False


def apply_fixes(
    config: BuildConfig, fixes: Sequence[Fix]
) -> Tuple[BuildConfig, List[Fix]]:
    """Return a new config with ``fixes`` applied, and the fixes that changed it.

    The input config is left untouched. Fixes already present are skipped, so
    applying the same list twice is a no-op the second time.
    """
    hidden = list(config.hidden_imports)
    extra_files = list(config.extra_files)
    extra_args = config.extra_args or ""
    windowed, noconsole = config.windowed, config.noconsole
    source = config.source
    applied: List[Fix] = []

    for fix in fixes:
        current = replace(
            config,
            hidden_imports=hidden,
            extra_files=extra_files,
            extra_args=extra_args,
            windowed=windowed,
            noconsole=noconsole,
            source=source,
        )
        if fix_is_applied(current, fix):
            continue
        if fix.kind == FIX_HIDDEN_IMPORT:
            hidden.append(fix.value)
        elif fix.kind == FIX_ADD_DATA:
            extra_files.append(fix.value)
        elif fix.kind == FIX_FLAG:
            extra_args = f"{extra_args} {fix.value}".strip()
        elif fix.kind == FIX_CONSOLE:
            windowed = noconsole = False
        elif fix.kind == FIX_SET_SOURCE:
            source = fix.value
        applied.append(fix)

    new_config = replace(
        config,
        hidden_imports=hidden,
        extra_files=extra_files,
        extra_args=extra_args,
        windowed=windowed,
        noconsole=noconsole,
        source=source,
    )
    return new_config, applied


def _same_path(a: str, b: str) -> bool:
    if not a or not b:
        return False
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


# Code the user pastes into their own script. Language-neutral on purpose:
# the explanation around it is translated, the code is not.
SNIPPETS = {
    "resource_path": (
        "import os\n"
        "import sys\n"
        "\n"
        "\n"
        "def resource_path(relative):\n"
        '    """Absolute path to a bundled file, frozen or not."""\n'
        '    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))\n'
        "    return os.path.join(base, relative)\n"
        "\n"
        "\n"
        '# Use: open(resource_path("data/config.json"))\n'
    ),
    "freeze_support": (
        "import multiprocessing\n"
        "\n"
        'if __name__ == "__main__":\n'
        "    multiprocessing.freeze_support()  # must be the first line here\n"
        "    main()\n"
    ),
    "silence_streams": (
        "import os\n"
        "import sys\n"
        "\n"
        "# A windowed EXE has no console: sys.stdout/sys.stderr are None.\n"
        "if sys.stdout is None:\n"
        '    sys.stdout = open(os.devnull, "w")\n'
        "if sys.stderr is None:\n"
        '    sys.stderr = open(os.devnull, "w")\n'
    ),
    "main_guard": (
        "def main():\n"
        "    ...\n"
        "\n"
        "\n"
        'if __name__ == "__main__":\n'
        "    main()\n"
    ),
}
