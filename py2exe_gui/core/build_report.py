"""A self-contained HTML report for one build.

Everything someone receiving the EXE might ask about — what went in, how big
each part is, which Python and PyInstaller produced it, the SHA-256 to verify
the download, what the doctor flagged — in one file that opens in any browser
and needs nothing else (no scripts, no external CSS, no network).

UI-independent: the caller passes every label already translated, the same
way the doctor's findings are resolved in the UI rather than here.
"""

import hashlib
import html
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from py2exe_gui.core.config import BuildConfig
from py2exe_gui.core.diagnostics import build_name, build_root
from py2exe_gui.core.size_analyzer import format_size

_RE_PYINSTALLER = re.compile(r"PyInstaller:\s*([\w.+-]+)")
_RE_PYTHON = re.compile(r"Python:\s*([\d.]+\w*)")
_RE_PLATFORM = re.compile(r"Platform:\s*(\S+)")


@dataclass
class ReportData:
    app_name: str
    source: str = ""
    output_path: str = ""
    timestamp: str = ""
    success: bool = True
    duration_seconds: float = 0.0
    output_bytes: int = 0
    content_bytes: int = 0
    previous_bytes: int = 0
    sha256: str = ""
    onefile: bool = True
    environment: str = ""
    python_version: str = ""
    pyinstaller_version: str = ""
    platform: str = ""
    command: List[str] = field(default_factory=list)
    #: (label, bytes) per package, biggest first.
    groups: List[Tuple[str, int]] = field(default_factory=list)
    largest_files: List[Tuple[str, int]] = field(default_factory=list)
    #: (severity, title, detail) — already translated.
    findings: List[Tuple[str, str, str]] = field(default_factory=list)
    #: Runtime Kit services embedded in the EXE — already translated.
    runtime_services: List[str] = field(default_factory=list)


def report_path_for(config: BuildConfig) -> str:
    """``<output folder>/<name>-build-report.html``, beside dist/ and build/."""
    return os.path.join(build_root(config), f"{build_name(config)}-build-report.html")


def parse_versions(build_log: str) -> Dict[str, str]:
    """PyInstaller, Python and platform as PyInstaller's first log lines state them."""
    found = {}
    for key, pattern in (
        ("pyinstaller", _RE_PYINSTALLER),
        ("python", _RE_PYTHON),
        ("platform", _RE_PLATFORM),
    ):
        match = pattern.search(build_log or "")
        if match:
            found[key] = match.group(1).rstrip(",")
    return found


def sha256_file(path: str) -> str:
    """Hex SHA-256 of a file, or '' for a folder or an unreadable path."""
    if not path or not os.path.isfile(path):
        return ""
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return ""
    return digest.hexdigest()


def options_from_command(command: Sequence[str]) -> List[str]:
    """The PyInstaller options of a build command, without interpreter or script."""
    args = list(command)
    if "PyInstaller" in args:
        args = args[args.index("PyInstaller") + 1:]
    if args and not args[-1].startswith("-"):
        args = args[:-1]  # the script
    options: List[str] = []
    for arg in args:
        if arg.startswith("-") or not options:
            options.append(arg)
        else:
            options[-1] = f"{options[-1]} {arg}"
    return options


_CSS = """
:root { --bg:#ffffff; --fg:#1f2430; --muted:#5b6475; --card:#f4f6fa; --line:#dde2ea;
        --bar:#3b82f6; --ok:#15803d; --bad:#b91c1c; --warn:#a16207; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#14161c; --fg:#e6e9ef; --muted:#9aa3b5; --card:#1d2029; --line:#2d313d;
          --bar:#60a5fa; --ok:#4ade80; --bad:#f87171; --warn:#facc15; }
}
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg);
       font: 15px/1.55 "Segoe UI", Tahoma, "Noto Sans Arabic", system-ui, sans-serif; }
main { max-width: 960px; margin: 0 auto; padding: 24px 16px 48px; }
h1 { font-size: 24px; margin: 0 0 4px; }
h2 { font-size: 17px; margin: 28px 0 10px; }
.muted { color: var(--muted); }
.cards { display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:10px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:10px 12px; }
.card b { display:block; font-size:18px; }
.ok { color: var(--ok); } .bad { color: var(--bad); } .warn { color: var(--warn); }
table { width:100%; border-collapse: collapse; }
th, td { text-align: start; padding: 6px 8px; border-bottom: 1px solid var(--line);
         vertical-align: top; }
td.num { text-align: end; white-space: nowrap; font-variant-numeric: tabular-nums; }
.bar { height: 8px; background: var(--bar); border-radius: 4px; min-width: 2px; }
code, .mono { font-family: Consolas, "Courier New", monospace; font-size: 13px;
              overflow-wrap: anywhere; direction: ltr; unicode-bidi: embed; }
ul.opts { margin: 0; padding-inline-start: 18px; }
.ltr { direction: ltr; unicode-bidi: isolate; }
footer { margin-top: 36px; font-size: 13px; }
"""


def _e(value) -> str:
    return html.escape(str(value), quote=True)


def _n(value) -> str:
    """A number or size kept in reading order ("41.6 MB", not "MB 41.6") in RTL."""
    return f'<span class="ltr">{_e(value)}</span>'


def render_html(data: ReportData, labels: Dict[str, str], rtl: bool = False,
                lang: str = "en", generator: str = "") -> str:
    """The report as one HTML document. Every dynamic value is escaped."""
    L = {k: _e(v) for k, v in labels.items()}

    def label(key: str) -> str:
        return L.get(key, _e(key))

    result_class = "ok" if data.success else "bad"
    result_text = label("success") if data.success else label("failed")

    cards = [
        (label("result"), f'<b class="{result_class}">{result_text}</b>'),
        (label("size_on_disk"), f"<b>{_n(format_size(data.output_bytes))}</b>"),
        (label("contents"), f"<b>{_n(format_size(data.content_bytes))}</b>"),
        (label("duration"), f"<b>{_n(f'{data.duration_seconds:.1f} s')}</b>"),
    ]
    if data.previous_bytes and data.output_bytes:
        change = (data.output_bytes - data.previous_bytes) * 100.0 / data.previous_bytes
        css = "ok" if change <= 0 else "warn"
        cards.append((
            label("previous"),
            f'<b class="{css}">{_n(f"{change:+.1f}%")}</b>'
            f'<span class="muted">{_n(format_size(data.previous_bytes))}</span>',
        ))
    card_html = "".join(
        f'<div class="card"><span class="muted">{title}</span>{body}</div>'
        for title, body in cards
    )

    details = [
        (label("app"), _e(data.app_name)),
        (label("date"), _e(data.timestamp)),
        (label("source"), f'<span class="mono">{_e(data.source)}</span>'),
        (label("output"), f'<span class="mono">{_e(data.output_path)}</span>'),
        (label("mode"), label("onefile") if data.onefile else label("onedir")),
        (label("environment"), _e(data.environment)),
        (label("python"), _e(data.python_version)),
        (label("pyinstaller"), _e(data.pyinstaller_version)),
        (label("platform"), _e(data.platform)),
        ("SHA-256", f'<code>{_e(data.sha256) or "—"}</code>'),
    ]
    detail_rows = "".join(
        f"<tr><th>{k}</th><td>{v or '—'}</td></tr>" for k, v in details
    )

    total = sum(size for _g, size in data.groups) or 1
    biggest = max((size for _g, size in data.groups), default=1) or 1
    group_rows = "".join(
        f"<tr><td>{_e(name)}</td>"
        f'<td style="width:40%"><div class="bar" style="width:{size * 100.0 / biggest:.1f}%"></div></td>'
        f'<td class="num">{_n(format_size(size))}</td>'
        f'<td class="num">{_n(f"{size * 100.0 / total:.1f}%")}</td></tr>'
        for name, size in data.groups
    ) or f'<tr><td colspan="4" class="muted">{label("none")}</td></tr>'

    file_rows = "".join(
        f'<tr><td class="mono">{_e(name)}</td><td class="num">{_n(format_size(size))}</td></tr>'
        for name, size in data.largest_files
    ) or f'<tr><td colspan="2" class="muted">{label("none")}</td></tr>'

    icons = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}
    finding_rows = "".join(
        f"<tr><td>{icons.get(sev, '•')}</td><td><b>{_e(title)}</b>"
        f'<div class="muted">{_e(detail)}</div></td></tr>'
        for sev, title, detail in data.findings
    ) or f'<tr><td colspan="2" class="muted">{label("none")}</td></tr>'

    service_items = "".join(f"<li>{_e(name)}</li>" for name in data.runtime_services) or (
        f'<li class="muted">{label("none")}</li>'
    )

    options = options_from_command(data.command)
    option_items = "".join(f"<li><code>{_e(o)}</code></li>" for o in options) or (
        f'<li class="muted">{label("none")}</li>'
    )

    direction = "rtl" if rtl else "ltr"
    return f"""<!doctype html>
<html lang="{_e(lang)}" dir="{direction}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{label("title")} — {_e(data.app_name)}</title>
<style>{_CSS}</style>
</head>
<body>
<main>
<h1>{label("title")}: {_e(data.app_name)}</h1>
<p class="muted">{_e(data.timestamp)}</p>
<section class="cards">{card_html}</section>

<h2>{label("details")}</h2>
<table>{detail_rows}</table>

<h2>{label("breakdown")}</h2>
<table>
<tr><th>{label("package")}</th><th></th><th>{label("size")}</th><th>{label("share")}</th></tr>
{group_rows}
</table>

<h2>{label("largest_files")}</h2>
<table>{file_rows}</table>

<h2>{label("findings")}</h2>
<table>{finding_rows}</table>

<h2>{label("runtime_kit")}</h2>
<ul class="opts">{service_items}</ul>

<h2>{label("options")}</h2>
<ul class="opts">{option_items}</ul>

<footer class="muted">{_e(generator)}</footer>
</main>
</body>
</html>
"""


def write_report(path: str, document: str) -> Optional[str]:
    """Write the report; returns an error message, or None on success."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(document)
    except OSError as e:
        return str(e)
    return None
