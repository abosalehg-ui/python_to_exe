"""Locale text for things the core reports as codes — Qt-free.

Shared by the command line (which must never import PyQt5) and the GUI, so a
release step or a Runtime Kit message reads the same in both.
"""

from typing import Dict

from py2exe_gui.core.runtime_kit import TEXT_KEYS
from py2exe_gui.strings import LOCALE_LAYOUT, S, current_locale

_RUNTIME_TEXT_NAMES = {
    "crash_title": "KIT_RT_CRASH_TITLE",
    "crash_message": "KIT_RT_CRASH_MESSAGE",
    "support_prompt": "KIT_RT_SUPPORT_PROMPT",
    "instance_message": "KIT_RT_INSTANCE_MESSAGE",
    "update_title": "KIT_RT_UPDATE_TITLE",
    "update_message": "KIT_RT_UPDATE_MESSAGE",
}

STATUS_ICONS = {
    "pending": "○", "running": "⏳", "planned": "📋", "done": "✅", "skipped": "⏭️",
    "failed": "❌",
}


def runtime_texts() -> Dict[str, str]:
    """What the built app says (crash dialog, second copy, update prompt),
    in the language the developer is using now."""
    return {key: getattr(S, _RUNTIME_TEXT_NAMES[key]) for key in TEXT_KEYS}


def is_rtl() -> bool:
    return LOCALE_LAYOUT.get(current_locale(), "ltr") == "rtl"


def _format(template: str, params: Dict[str, str]) -> str:
    try:
        return template.format(**params)
    except (KeyError, IndexError, ValueError):
        return template


def step_title(key: str) -> str:
    return getattr(S, f"RELEASE_STEP_{key.upper()}", key)


def status_label(status: str) -> str:
    return getattr(S, f"RELEASE_STATUS_{status.upper()}", status)


def reason_text(result) -> str:
    """The translated explanation of a step result ('' when there is none)."""
    if not result.reason:
        return ""
    template = getattr(S, f"RELEASE_REASON_{result.reason.upper()}", result.reason)
    return _format(template, result.params)


def step_line(result) -> str:
    """One line per step: icon, title, explanation."""
    icon = STATUS_ICONS.get(result.status, "•")
    reason = reason_text(result)
    return f"{icon} {step_title(result.key)}" + (f" — {reason}" if reason else "")


def notes_titles() -> Dict[str, str]:
    """Section titles for drafted release notes, in the active locale."""
    keys = ("breaking", "feat", "fix", "perf", "refactor", "docs", "other", "changes",
            "no_changes")
    return {key: getattr(S, f"NOTES_{key.upper()}") for key in keys}


def project_error_text(error) -> str:
    """A ``ProjectFileError`` in the active locale."""
    template = getattr(S, f"PROJECT_ERR_{error.code.upper()}", S.PROJECT_ERR_GENERIC)
    return _format(template, {"detail": error.detail, "code": error.code})


# ── Compare mode (2.0) ──────────────────────────────────────────────────

_LRI, _PDI = "⁦", "⁩"


def _iso(text: str, isolate: bool) -> str:
    """Keep "0.124 s" in reading order inside right-to-left text."""
    return f"{_LRI}{text}{_PDI}" if isolate else text


def seconds_text(seconds: float) -> str:
    """0.124 → "124 ms", 2.5 → "2.50 s", 47.3 → "47.3 s"."""
    if seconds < 1:
        return f"{seconds * 1000:.0f} ms"
    if seconds < 10:
        return f"{seconds:.2f} s"
    return f"{seconds:.1f} s"


def method_label(method: str) -> str:
    return getattr(S, f"COMPARE_METHOD_{method.upper()}", method)


def engine_label(name: str) -> str:
    from py2exe_gui.core.engines import get_engine, is_known_engine

    return get_engine(name).display_name if is_known_engine(name) else name


def startup_text(result, isolate: bool = False) -> str:
    """"124 ms (median of 5 of 5)", or "still running after 10 s — no number"."""
    from py2exe_gui.core.startup_bench import METHOD_STILL_RUNNING

    if result is None or result.error:
        return S.COMPARE_NONE
    if result.method == METHOD_STILL_RUNNING or result.median is None:
        return S.COMPARE_STILL_RUNNING_FMT.format(
            seconds=_iso(seconds_text(result.timeout), isolate))
    return S.COMPARE_MEDIAN_FMT.format(value=_iso(seconds_text(result.median), isolate),
                                       n=len(result.times), total=len(result.runs))


def compare_table(rows, isolate: bool = False):
    """(row label, [cell per engine]) for the comparison, in display order."""
    from py2exe_gui.core.size_analyzer import format_size
    from py2exe_gui.ui.finding_text import feature_label, finding_title

    def cell(row, what):
        if what == "status":
            if row.built:
                return S.COMPARE_BUILT
            why = "; ".join(finding_title(f) for f in row.findings[:2]) or row.error
            return f"{S.COMPARE_NOT_BUILT}: {why}" if why else S.COMPARE_NOT_BUILT
        if not row.built:
            return S.COMPARE_NONE if what != "unsupported" else _features(row)
        if what == "size":
            return _iso(format_size(row.size_bytes), isolate) if row.size_bytes else S.COMPARE_NONE
        if what == "build_time":
            return _iso(seconds_text(row.build_seconds), isolate)
        if what == "startup":
            return startup_text(row.startup, isolate)
        if what == "method":
            return method_label(row.startup.method) if row.startup else S.COMPARE_NONE
        if what == "runs":
            if not row.startup or not row.startup.runs:
                return S.COMPARE_NONE
            return _iso(" · ".join(seconds_text(r.seconds) if r.seconds is not None else "…"
                                   for r in row.startup.runs), isolate)
        if what == "smoke":
            if row.smoke is None:
                return S.COMPARE_NONE
            if row.smoke.passed:
                return S.COMPARE_SMOKE_PASS
            return S.COMPARE_SMOKE_FAIL.format(code=row.smoke.returncode)
        return _features(row)

    def _features(row):
        return ", ".join(feature_label(f) for f in row.unsupported) or S.COMPARE_NONE

    keys = ("status", "size", "build_time", "startup", "method", "runs", "smoke", "unsupported")
    return [(getattr(S, f"COMPARE_ROW_{k.upper()}"), [cell(r, k) for r in rows]) for k in keys]


def reason_line(reason, isolate: bool = False) -> str:
    """One reason behind a recommendation, in the active locale."""
    from py2exe_gui.core.size_analyzer import format_size
    from py2exe_gui.ui.finding_text import feature_label

    params = {}
    for key, value in reason.params.items():
        if key in ("engine", "other", "a", "b"):
            # Isolated too: a line that starts with "Nuitka" would otherwise
            # take a left-to-right direction inside Arabic text.
            params[key] = _iso(engine_label(str(value)), isolate)
        elif key in ("fast", "slow"):
            params[key] = _iso(seconds_text(float(value)), isolate)
        elif key in ("small", "big"):
            params[key] = _iso(format_size(int(value)), isolate)
        elif key == "method":
            params[key] = method_label(str(value))
        elif key == "features":
            params[key] = ", ".join(feature_label(f) for f in value)
        else:
            params[key] = str(value)
    template = getattr(S, f"COMPARE_REASON_{reason.code.upper()}", reason.code)
    return _format(template, params)


def recommendation_lines(rec, isolate: bool = False):
    """The headline and one line per reason."""
    head = (S.COMPARE_REC_FMT.format(engine=_iso(engine_label(rec.engine), isolate))
            if rec.engine else S.COMPARE_REC_NONE)
    lines = [head, S.COMPARE_WHY] + [f"• {reason_line(r, isolate)}" for r in rec.reasons]
    if isolate and is_rtl():
        # Qt 5 picks a paragraph's direction from its first strong character
        # and ignores the isolates: "• Nuitka …" would read left to right.
        lines = ["\u200f" + line for line in lines]
    return lines
