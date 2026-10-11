"""The icon set: Lucide SVGs shipped in the package, coloured from the theme.

Until 2.1 every tab, group and button started with an emoji. An emoji is a
glyph of the system's colour-emoji font, so the same window looked different
on Windows, Linux and macOS, and nothing about its colour or weight followed
the theme. The icons here are ~80 files from Lucide (ISC licence, see
``icons/LICENSE``), 24px line icons drawn with ``currentColor``; ``icon()``
substitutes the theme's colour for it and renders a ``QIcon`` with pixmaps
at the sizes the widgets ask for. Directional icons are mirrored for a
right-to-left layout.

``NAMES`` maps the application's own vocabulary ("start", "browse_folder",
"section_build") to Lucide file names, so a change of glyph is one line
here and the rest of the code never names a file.
"""

import os
from typing import Dict, Optional

from py2exe_gui.qt import (
    QByteArray,
    QIcon,
    QPainter,
    QPixmap,
    QSize,
    Qt,
    QtCore,
    QTransform,
)

ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")

#: Application vocabulary → Lucide file name (without ``.svg``).
NAMES: Dict[str, str] = {
    # Side navigation
    "section_projects": "folder-open",
    "section_build": "hammer",
    "section_check": "stethoscope",
    "section_distribute": "package",
    "section_tools": "wrench",
    "section_settings": "settings",
    # Pages
    "home": "house",
    "history": "history",
    "doctor": "stethoscope",
    "size": "gauge",
    "installer": "box",
    "platforms": "globe",
    "runtime": "layers",
    "release": "rocket",
    "batch": "list",
    "templates": "layout-template",
    "about": "info",
    "preferences": "sliders-horizontal",
    # Actions
    "start": "play",
    "stop": "square",
    "preview": "terminal",
    "open_folder": "folder",
    "browse_file": "file-search",
    "browse_folder": "folder-search",
    "icon_studio": "palette",
    "image": "image",
    "search": "search",
    "add": "plus",
    "add_file": "file-plus",
    "add_folder": "folder-plus",
    "remove": "trash-2",
    "clear": "eraser",
    "copy": "copy",
    "save": "save",
    "export": "upload",
    "import": "download",
    "refresh": "refresh-cw",
    "log": "scroll-text",
    "detect": "search",
    "apply": "check",
    "rebuild": "rotate-ccw",
    "diagnose": "flask-conical",
    "sandbox": "monitor",
    "ci": "bot",
    "git": "git-branch",
    "tag": "tag",
    "star": "star",
    "pencil": "pencil",
    "eye": "eye",
    "update": "cloud-download",
    "filter": "filter",
    "close": "x",
    "key": "key",
    "shield": "shield-check",
    "external": "external-link",
    "archive": "archive",
    "timer": "timer",
    "bug": "bug",
    "list_checks": "list-checks",
    "file_code": "file-code",
    "file_text": "file-text",
    "file_cog": "file-cog",
    "hard_drive": "hard-drive",
    "power": "power",
    "sparkles": "sparkles",
    "badge": "badge-check",
    "flag": "flag",
    "cpu": "cpu",
    # Chrome
    "chevron_down": "chevron-down",
    "chevron_up": "chevron-up",
    "chevron_left": "chevron-left",
    "chevron_right": "chevron-right",
    "collapse_nav": "panel-left-close",
    "expand_nav": "panel-left-open",
    "panel_bottom": "panel-bottom",
    "help": "circle-help",
    "keyboard": "keyboard",
    "theme_light": "sun",
    "theme_dark": "moon",
    "language": "languages",
    "zoom_in": "zoom-in",
    "zoom_out": "zoom-out",
    # Status
    "ok": "circle-check",
    "warning": "triangle-alert",
    "error": "circle-x",
    "info": "info",
    "alert": "circle-alert",
    "loader": "loader",
}

#: Icons whose meaning points along the reading direction: mirrored in RTL.
#: (Play, lists and documents are not: a play triangle points right in every
#: script, and Arabic readers expect it so.)
DIRECTIONAL = frozenset({
    "chevron_left", "chevron_right", "collapse_nav", "expand_nav", "external",
})

#: Pixmap sizes rendered into every QIcon (the widgets ask for 16–32px; the
#: larger ones serve high-DPI screens).
SIZES = (16, 20, 24, 32, 48, 64)

DEFAULT_COLOR = "#cdd6f4"
DEFAULT_DISABLED = "#a6adc8"

_cache: Dict[tuple, QIcon] = {}
_svg_cache: Dict[str, str] = {}


def icon_names():
    """Every name ``icon()`` accepts, sorted."""
    return sorted(NAMES)


def icon_path(name: str) -> str:
    """The SVG file behind ``name`` (a vocabulary name or a Lucide file name)."""
    return os.path.join(ICON_DIR, NAMES.get(name, name) + ".svg")


def svg_text(name: str) -> str:
    """The SVG source for ``name``, or ``""`` when there is no such file."""
    path = icon_path(name)
    if path in _svg_cache:
        return _svg_cache[path]
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        text = ""
    _svg_cache[path] = text
    return text


def coloured_svg(name: str, color: str) -> bytes:
    """The SVG with the theme colour in place of ``currentColor``."""
    text = svg_text(name)
    if not text:
        return b""
    return text.replace("currentColor", color).encode("utf-8")


def _render(svg: bytes, size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    if not svg:
        return pixmap
    try:
        from py2exe_gui.qt import QSvgRenderer  # QtSvg, looked up lazily
    except (ImportError, AttributeError):
        QSvgRenderer = None
    if QSvgRenderer is not None:
        renderer = QSvgRenderer(QByteArray(svg))
        if renderer.isValid():
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            renderer.render(painter)
            painter.end()
            return pixmap
    # Without QtSvg: the image plugin, if present, decodes it the same way.
    loaded = QPixmap()
    if loaded.loadFromData(svg, "SVG"):
        return loaded.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
    return pixmap


def icon(name: str, color: str = DEFAULT_COLOR, disabled: Optional[str] = None,
         mirror: bool = False, selected: Optional[str] = None) -> QIcon:
    """A ``QIcon`` for ``name`` in ``color``; empty (not an error) if unknown.

    ``disabled`` colours the icon's disabled state, ``selected`` its
    selected state (a list row on the accent background), and ``mirror``
    flips it horizontally (for a right-to-left layout, see
    :func:`themed_icon`).
    """
    key = (name, color, disabled, bool(mirror), selected)
    cached = _cache.get(key)
    if cached is not None:
        return cached
    result = QIcon()
    normal = coloured_svg(name, color)
    if normal:
        flip = QTransform().scale(-1, 1) if mirror else None
        variants = [(QIcon.Mode.Normal, normal)]
        if disabled:
            variants.append((QIcon.Mode.Disabled, coloured_svg(name, disabled)))
        if selected:
            variants.append((QIcon.Mode.Selected, coloured_svg(name, selected)))
        for size in SIZES:
            for mode, svg in variants:
                pixmap = _render(svg, size)
                if flip is not None:
                    pixmap = pixmap.transformed(flip)
                result.addPixmap(pixmap, mode)
    _cache[key] = result
    return result


def themed_icon(name: str, palette: Optional[dict] = None, role: str = "text",
                rtl: bool = False) -> QIcon:
    """``icon()`` coloured from a theme palette (``styles.PALETTES`` entry).

    ``role`` names the palette colour: ``"text"``, ``"accent"``,
    ``"on_accent"``, ``"muted"``, ``"danger"``… Directional icons are
    mirrored when ``rtl`` is true.
    """
    palette = palette or {}
    color = palette.get(role, DEFAULT_COLOR)
    disabled = palette.get("disabled_text", DEFAULT_DISABLED)
    selected = palette.get("on_accent")
    return icon(name, color, disabled=disabled, mirror=rtl and name in DIRECTIONAL,
                selected=selected)


def pixmap(name: str, size: int = 16, color: str = DEFAULT_COLOR) -> QPixmap:
    """One rendered pixmap, for labels that show an icon rather than a button."""
    return icon(name, color).pixmap(QSize(size, size))


def clear_cache():
    _cache.clear()


__all__ = [
    "DIRECTIONAL", "ICON_DIR", "NAMES", "SIZES", "clear_cache", "coloured_svg", "icon",
    "icon_names", "icon_path", "pixmap", "svg_text", "themed_icon",
]

# QtCore is imported so the module fails loudly if the binding is missing,
# like every other UI module, rather than at the first icon.
_ = QtCore
