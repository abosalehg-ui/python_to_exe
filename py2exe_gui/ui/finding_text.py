"""Turn findings and fixes into the active locale's text.

Kept free of Qt so the wording can be tested without a display: the core
hands back codes, this module is the one place that resolves them.
"""

import os
from typing import List

from py2exe_gui.core.fixes import (
    FIX_ADD_DATA,
    FIX_RUNTIME,
    FIX_SET_SOURCE,
    SNIPPETS,
    Finding,
    Fix,
)
from py2exe_gui.core.knowledge import lookup
from py2exe_gui.strings import S, current_locale

SEVERITY_ICONS = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}

# Codes whose remedy is "pip install <pip>" — the copy button copies that.
PIP_CODES = frozenset({"missing_package", "warn_missing_module"})
# Codes about one knowledge-base package: its note is appended to the detail.
PACKAGE_CODES = frozenset({
    "package_needs_collect", "package_data_dir", "package_console_streams",
    "large_package",
})


def _format(template: str, params: dict) -> str:
    try:
        return template.format(**params)
    except (KeyError, IndexError, ValueError):
        # A malformed translation must never break the panel: show it raw.
        return template


def finding_title(finding: Finding) -> str:
    template = getattr(S, f"FINDING_{finding.code.upper()}_TITLE", finding.code)
    return _format(template, finding.params)


def finding_detail(finding: Finding) -> str:
    template = getattr(S, f"FINDING_{finding.code.upper()}_DETAIL", "")
    return _format(template, finding.params)


def finding_label(finding: Finding) -> str:
    """One line for the list: severity icon + title."""
    return f"{SEVERITY_ICONS.get(finding.severity, '•')} {finding_title(finding)}"


def origin_label(origin: str) -> str:
    return getattr(S, f"ORIGIN_{origin.upper()}", origin)


def service_label(service: str) -> str:
    """A Runtime Kit service's name in the active locale."""
    return getattr(S, f"KIT_NAME_{service.upper()}", service)


def fix_label(fix: Fix) -> str:
    template = getattr(S, f"FIX_LABEL_{fix.kind.upper()}", fix.kind)
    value = fix.value
    if fix.kind in (FIX_ADD_DATA, FIX_SET_SOURCE):
        value = os.path.basename(value.rstrip("\\/")) or value
    elif fix.kind == FIX_RUNTIME:
        value = service_label(value)
    return _format(template, {"value": value})


def pip_command(finding: Finding) -> str:
    pip = finding.params.get("pip") or finding.params.get("module", "")
    return f"pip install {pip}" if pip else ""


def package_note(finding: Finding) -> str:
    if finding.code not in PACKAGE_CODES:
        return ""
    info = lookup(finding.params.get("package", ""))
    return info.note(current_locale()) if info else ""


def copy_text(finding: Finding) -> str:
    """What the copy button puts on the clipboard, or '' when nothing."""
    if finding.snippet:
        return SNIPPETS.get(finding.snippet, "")
    if finding.code in PIP_CODES:
        return pip_command(finding)
    return ""


def detail_lines(finding: Finding) -> List[str]:
    """The full explanation shown under the list for the selected finding."""
    lines = [finding_title(finding), "", finding_detail(finding)]
    note = package_note(finding)
    if note:
        lines += ["", f"{S.DOCTOR_NOTE_HEADER} {note}"]
    if finding.fixes:
        lines += ["", S.DOCTOR_FIXES_HEADER]
        lines += [f"  • {fix_label(fix)}" for fix in finding.fixes]
    if finding.alternatives:
        lines += ["", S.DOCTOR_ALT_HEADER]
        lines += [f"  • {fix_label(fix)}" for fix in finding.alternatives]
    if finding.code in PIP_CODES:
        lines += ["", S.DOCTOR_PIP_HEADER, f"  {pip_command(finding)}"]
    if finding.snippet:
        lines += ["", S.DOCTOR_MANUAL_HEADER, "", SNIPPETS.get(finding.snippet, "")]
    lines += ["", f"— {origin_label(finding.origin)}"]
    return lines
