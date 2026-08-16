"""Qt stylesheet generation: palettes, themes, font scaling, log colours.

Themes used to be two hand-written ~200-line CSS strings kept in sync by hand.
Adding a third meant a third copy, and every colour tweak had to be applied
twice without missing a selector. The stylesheet is now one template rendered
from a palette dictionary, so a theme is a table of colours and nothing else.

The rendered sheets are still exposed as ``DARK_THEME``/``LIGHT_THEME`` and
through ``THEMES``, so nothing downstream had to change.
"""

import os
import subprocess
import sys
from typing import Callable, Dict, Optional

# ── Log line colors ────────────────────────────────────────────────────────
# Single source of truth: log_formatter imports these rather than keeping a
# second copy. One palette per theme, because a single palette cannot clear
# WCAG AA (4.5:1) against backgrounds this far apart.
#
# Every value here is checked against its own theme's log background by
# tests/test_log_formatter.py, which parametrizes over LOG_COLORS — a new theme
# is contrast-tested the moment it is added.

LOG_BACKGROUND = {
    "dark": "#181825",
    "light": "#ffffff",
    "nord": "#272c36",
    "high-contrast": "#000000",
}

LOG_COLORS = {
    "dark": {
        "info": "#89b4fa",
        "success": "#a6e3a1",
        "warning": "#f9e2af",
        "error": "#f38ba8",
        "muted": "#9399b2",
    },
    "light": {
        "info": "#0969da",
        "success": "#1a7f37",
        "warning": "#9a6700",
        "error": "#cf222e",
        "muted": "#5a6169",
    },
    "nord": {
        "info": "#8fbcbb",
        "success": "#a3be8c",
        "warning": "#ebcb8b",
        "error": "#d88b94",
        "muted": "#aeb8ca",
    },
    "high-contrast": {
        "info": "#00ffff",
        "success": "#00ff00",
        "warning": "#ffff00",
        "error": "#ff8080",
        "muted": "#d0d0d0",
    },
}

DEFAULT_LOG_THEME = "dark"

# ── Fonts ──────────────────────────────────────────────────────────────────
# Segoe UI has thin Arabic coverage and falls back mid-run, which makes mixed
# Arabic/Latin lines sit at inconsistent heights. Arabic-first locales lead
# with faces that actually ship Arabic glyphs.
UI_FONT_STACKS = {
    "ar": ("Segoe UI", "Tahoma", "Dubai", "Noto Naskh Arabic", "Arial"),
    "default": ("Segoe UI", "Arial", "Helvetica"),
}

# Font scale bounds for the zoom shortcuts. Below 0.7 labels start clipping
# inside fixed-height controls; above 2.0 the tab bar no longer fits.
MIN_FONT_SCALE = 0.7
MAX_FONT_SCALE = 2.0
DEFAULT_FONT_SCALE = 1.0
FONT_SCALE_STEP = 0.1

# Point sizes at scale 1.0, named so the template reads as intent.
_BASE_SIZES = {
    "log": 8,
    "body": 9,
    "small": 9,
    "group": 10,
    "about_body": 10,
    "about_sub": 11,
    "about_head": 16,
    "title": 18,
}


def font_stack(locale: str = "default") -> tuple:
    """Ordered font family preferences for ``locale``."""
    return UI_FONT_STACKS.get(locale, UI_FONT_STACKS["default"])


def font_family_css(locale: str = "default") -> str:
    """The same stack rendered as a CSS ``font-family`` value."""
    return ", ".join(f"'{name}'" for name in font_stack(locale)) + ", sans-serif"


def clamp_scale(scale: float) -> float:
    """Hold a font scale inside the range the layout survives."""
    try:
        value = float(scale)
    except (TypeError, ValueError):
        return DEFAULT_FONT_SCALE
    return round(min(MAX_FONT_SCALE, max(MIN_FONT_SCALE, value)), 2)


def _pt(name: str, scale: float) -> str:
    """A scaled point size for the template. Never smaller than 6pt."""
    return f"{max(6, round(_BASE_SIZES[name] * scale))}pt"


# ── Palettes ───────────────────────────────────────────────────────────────
# Every key is consumed by _TEMPLATE below. A new theme is a new entry here.

PALETTES: Dict[str, Dict[str, str]] = {
    # Catppuccin Mocha
    "dark": {
        "window_bg": "#1e1e2e",
        "surface": "#313244",
        "input_bg": "#45475a",
        "border": "#45475a",
        "input_border": "#585b70",
        "text": "#cdd6f4",
        # Lightened from #6c7086: the status bar sat at 3.59:1 against its own
        # background, and the About tab's muted text at 4.45:1.
        "muted": "#a6adc8",
        "accent": "#89b4fa",
        "accent_hover": "#b4befe",
        "accent_pressed": "#74c7ec",
        "on_accent": "#1e1e2e",
        "focus_ring": "#f5e0dc",
        "disabled_bg": "#45475a",
        "disabled_text": "#a6adc8",
        "danger": "#f38ba8",
        "danger_hover": "#eba0ac",
        "success": "#a6e3a1",
        "success_hover": "#94e2d5",
        "tab_bg": "#45475a",
        "statusbar_bg": "#181825",
        "log_bg": "#181825",
        "log_text": "#a6e3a1",
        "about_sub": "#a6e3a1",
        "about_muted": "#a6adc8",
    },
    # Catppuccin Latte
    "light": {
        "window_bg": "#eff1f5",
        "surface": "#e6e9ef",
        "input_bg": "#eff1f5",
        "border": "#ccd0da",
        "input_border": "#ccd0da",
        "text": "#4c4f69",
        # The light palette was the weakest of the two on contrast: light text
        # on mid-tone Catppuccin Latte accents left the primary Build button at
        # 2.96:1. Every button colour below is darkened until white-on-colour
        # clears 4.5:1, which is why they read deeper than stock Latte.
        "muted": "#5c5f73",
        "accent": "#1052d8",
        "accent_hover": "#2a5fd0",
        "accent_pressed": "#0d47b8",
        "on_accent": "#ffffff",
        "focus_ring": "#11111b",
        "disabled_bg": "#ccd0da",
        "disabled_text": "#565a66",
        "danger": "#c00d33",
        "danger_hover": "#b82836",
        "success": "#166b2d",
        "success_hover": "#0f7278",
        "tab_bg": "#ccd0da",
        "statusbar_bg": "#dce0e8",
        "log_bg": "#ffffff",
        "log_text": "#4c4f69",
        "about_sub": "#14682c",
        "about_muted": "#5a6169",
    },
    # Nord — the most requested palette this project did not have.
    "nord": {
        "window_bg": "#2e3440",
        "surface": "#3b4252",
        "input_bg": "#434c5e",
        "border": "#4c566a",
        "input_border": "#4c566a",
        "text": "#eceff4",
        "muted": "#aeb8ca",
        "accent": "#88c0d0",
        "accent_hover": "#a3c4d8",
        "accent_pressed": "#81a1c1",
        "on_accent": "#2e3440",
        "focus_ring": "#eceff4",
        "disabled_bg": "#434c5e",
        "disabled_text": "#b4bdcd",
        # Nord's own red (#bf616a) is too dark to carry #2e3440 text (3.05:1),
        # so the button colours are lifted while keeping the hue.
        "danger": "#d88b94",
        "danger_hover": "#e3ab99",
        "success": "#a3be8c",
        "success_hover": "#b5cfa3",
        "tab_bg": "#434c5e",
        "statusbar_bg": "#272c36",
        "log_bg": "#272c36",
        "log_text": "#a3be8c",
        "about_sub": "#a3be8c",
        "about_muted": "#aeb8ca",
    },
    # Maximum contrast, for low vision and high-glare environments. Pure black
    # and white with saturated accents; nothing here is decorative.
    "high-contrast": {
        "window_bg": "#000000",
        "surface": "#0a0a0a",
        "input_bg": "#000000",
        "border": "#ffffff",
        "input_border": "#ffffff",
        "text": "#ffffff",
        "muted": "#d0d0d0",
        "accent": "#ffff00",
        "accent_hover": "#ffffa0",
        "accent_pressed": "#e0e000",
        "on_accent": "#000000",
        "focus_ring": "#00ffff",
        "disabled_bg": "#2a2a2a",
        "disabled_text": "#a0a0a0",
        "danger": "#ff8080",
        "danger_hover": "#ffb0b0",
        "success": "#00ff00",
        "success_hover": "#a0ffa0",
        "tab_bg": "#000000",
        "statusbar_bg": "#000000",
        "log_bg": "#000000",
        "log_text": "#00ff00",
        "about_sub": "#00ff00",
        "about_muted": "#d0d0d0",
    },
}


# ── Stylesheet template ────────────────────────────────────────────────────
# One copy of the rules. ``{name}`` placeholders are filled from a palette,
# ``{pt_*}`` from the scaled font sizes.

_TEMPLATE = """
QMainWindow {{
    background-color: {window_bg};
}}
QWidget {{
    font-family: {font_family};
    font-size: {pt_body};
    color: {text};
}}
QGroupBox {{
    font-weight: bold;
    font-size: {pt_group};
    border: 2px solid {border};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 10px;
    background-color: {surface};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top right;
    padding: 0 10px;
    color: {accent};
}}
QPushButton {{
    background-color: {accent};
    color: {on_accent};
    /* Transparent border keeps geometry stable when :focus adds a visible one. */
    border: 2px solid transparent;
    padding: 5px 12px;
    border-radius: 6px;
    font-weight: bold;
    min-height: 16px;
}}
QPushButton:hover {{
    background-color: {accent_hover};
}}
QPushButton:pressed {{
    background-color: {accent_pressed};
}}
/* Keyboard users could not tell which button had focus. */
QPushButton:focus {{
    border: 2px solid {focus_ring};
}}
QPushButton:disabled {{
    background-color: {disabled_bg};
    color: {disabled_text};
}}
QPushButton#dangerBtn {{
    background-color: {danger};
    color: {on_accent};
}}
QPushButton#dangerBtn:hover {{
    background-color: {danger_hover};
    color: {on_accent};
}}
QPushButton#successBtn {{
    background-color: {success};
    color: {on_accent};
}}
QPushButton#successBtn:hover {{
    background-color: {success_hover};
    color: {on_accent};
}}
QLineEdit, QComboBox, QSpinBox {{
    background-color: {input_bg};
    border: 2px solid {input_border};
    border-radius: 6px;
    padding: 8px;
    color: {text};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border-color: {accent};
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
    background-color: {disabled_bg};
    color: {disabled_text};
}}
QTextEdit {{
    background-color: {log_bg};
    border: 2px solid {border};
    border-radius: 8px;
    padding: 10px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: {pt_log};
    color: {log_text};
}}
QListWidget {{
    background-color: {input_bg};
    border: 2px solid {input_border};
    border-radius: 6px;
    padding: 5px;
}}
QListWidget::item {{
    padding: 5px;
    border-radius: 4px;
}}
QListWidget::item:selected {{
    background-color: {accent};
    color: {on_accent};
}}
QCheckBox {{
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 20px;
    height: 20px;
    border-radius: 4px;
    border: 2px solid {input_border};
    background-color: {input_bg};
}}
QCheckBox::indicator:checked {{
    background-color: {accent};
    border-color: {accent};
}}
QCheckBox:focus {{
    color: {accent};
}}
QProgressBar {{
    border: 2px solid {border};
    border-radius: 6px;
    text-align: center;
    background-color: {surface};
    color: {text};
    font-weight: bold;
}}
QProgressBar::chunk {{
    background-color: {accent};
    border-radius: 4px;
}}
QTabWidget::pane {{
    border: 2px solid {border};
    border-radius: 8px;
    background-color: {surface};
}}
QTabBar::tab {{
    background-color: {tab_bg};
    padding: 10px 20px;
    margin: 2px;
    border-radius: 6px;
    color: {text};
}}
QTabBar::tab:selected {{
    background-color: {accent};
    color: {on_accent};
}}
QTabBar::tab:focus {{
    border: 2px solid {focus_ring};
}}
QStatusBar {{
    background-color: {statusbar_bg};
    color: {muted};
}}
QLabel#titleLabel {{
    font-size: {pt_title};
    font-weight: bold;
    color: {accent};
}}
QLabel#subtitleLabel {{
    font-size: {pt_small};
    color: {muted};
}}
/* A platform or update notice above a tab's contents. Reads as a callout
   rather than another field label. */
QLabel#noticeLabel {{
    font-size: {pt_small};
    color: {on_accent};
    background-color: {accent};
    border-radius: 6px;
    padding: 8px 12px;
}}
QLabel#warningNotice {{
    font-size: {pt_small};
    color: {on_accent};
    background-color: {danger};
    border-radius: 6px;
    padding: 8px 12px;
}}
/* About tab. Previously these colours were inline in the HTML, so the tab
   stayed dark-themed (and unreadable) after switching to the light theme. */
QLabel#aboutHeading {{
    font-size: {pt_about_head};
    font-weight: bold;
    color: {accent};
}}
QLabel#aboutSubheading {{
    font-size: {pt_about_sub};
    font-weight: bold;
    color: {about_sub};
}}
QLabel#aboutBody {{
    font-size: {pt_about_body};
    color: {text};
}}
QLabel#aboutMuted {{
    font-size: {pt_small};
    color: {about_muted};
}}
QFrame#aboutSeparator {{
    background-color: {border};
    max-height: 1px;
    border: none;
}}
"""


def render_theme(
    theme: str,
    locale: str = "default",
    scale: float = DEFAULT_FONT_SCALE,
) -> str:
    """Render the stylesheet for ``theme`` at ``scale`` for ``locale``."""
    palette = PALETTES.get(theme) or PALETTES[DEFAULT_LOG_THEME]
    factor = clamp_scale(scale)
    values = dict(palette)
    values["font_family"] = font_family_css(locale)
    values.update({f"pt_{name}": _pt(name, factor) for name in _BASE_SIZES})
    return _TEMPLATE.format(**values)


def themed_stylesheet(
    theme: str,
    locale: str = "default",
    scale: float = DEFAULT_FONT_SCALE,
) -> str:
    """Return a theme stylesheet with the locale's font stack and font scale.

    ``theme`` may be ``"auto"``, which resolves against the OS setting.
    """
    return render_theme(resolve_theme(theme), locale, scale)


# ── Theme resolution ───────────────────────────────────────────────────────

AUTO_THEME = "auto"


def theme_names() -> list:
    """Selectable theme names, ``auto`` first."""
    return [AUTO_THEME] + sorted(PALETTES)


def resolve_theme(theme: str, platform: Optional[str] = None) -> str:
    """Turn a stored preference into a concrete theme name.

    ``auto`` follows the OS; an unknown name falls back to the default rather
    than raising, so a corrupted preference file cannot stop the app starting.
    """
    if theme == AUTO_THEME:
        return detect_system_theme(platform)
    return theme if theme in PALETTES else DEFAULT_LOG_THEME


def _run(command: list) -> Optional[str]:
    """Run a short command and return stdout, or None if it fails at all."""
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=2, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def detect_system_theme(
    platform: Optional[str] = None,
    runner: Optional[Callable[[list], Optional[str]]] = None,
    env: Optional[dict] = None,
) -> str:
    """Read the OS light/dark preference. Defaults to ``dark`` when unknown.

    ``dark`` is the fallback because it is what this app has always shipped;
    a machine that cannot be asked keeps the appearance it had before.
    """
    plat = platform if platform is not None else sys.platform
    run = runner or _run
    environ = os.environ if env is None else env

    if plat.startswith("win"):
        return _detect_windows_theme()
    if plat.startswith("darwin"):
        # The key is absent entirely in light mode, so a failed read is light.
        style = run(["defaults", "read", "-g", "AppleInterfaceStyle"])
        return "dark" if style and "dark" in style.lower() else "light"

    # Freedesktop: the portal setting wins, then the GNOME key.
    scheme = environ.get("GTK_THEME", "")
    if "dark" in scheme.lower():
        return "dark"
    value = run(["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"])
    if value:
        lowered = value.lower()
        if "dark" in lowered:
            return "dark"
        if "light" in lowered or "default" in lowered:
            return "light"
    return DEFAULT_LOG_THEME


def _detect_windows_theme() -> str:
    """Read AppsUseLightTheme from the registry. Import is Windows-only."""
    try:
        import winreg  # noqa: PLC0415 - absent on every other platform
    except ImportError:
        return DEFAULT_LOG_THEME
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        with key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
    except OSError:
        return DEFAULT_LOG_THEME
    return "light" if value else "dark"


# ── Backwards-compatible rendered sheets ───────────────────────────────────
# These were module constants before themes became palette-driven.

DARK_THEME = render_theme("dark")
LIGHT_THEME = render_theme("light")
NORD_THEME = render_theme("nord")
HIGH_CONTRAST_THEME = render_theme("high-contrast")

THEMES = {name: render_theme(name) for name in PALETTES}
