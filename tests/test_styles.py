"""Tests for palette-driven theme rendering, font scaling and auto-detection."""

import re

import pytest

from py2exe_gui.styles import (
    AUTO_THEME,
    DEFAULT_FONT_SCALE,
    DEFAULT_LOG_THEME,
    LOG_BACKGROUND,
    LOG_COLORS,
    MAX_FONT_SCALE,
    MIN_FONT_SCALE,
    PALETTES,
    THEMES,
    clamp_scale,
    detect_system_theme,
    render_theme,
    resolve_theme,
    theme_names,
    themed_stylesheet,
)

# Every key the stylesheet template consumes from a palette.
REQUIRED_KEYS = set(PALETTES[DEFAULT_LOG_THEME])


# ── Palette completeness ───────────────────────────────────────────────────


@pytest.mark.parametrize("name", sorted(PALETTES))
def test_every_palette_defines_every_key(name):
    """A missing key would raise KeyError at render time, not at import."""
    assert set(PALETTES[name]) == REQUIRED_KEYS


@pytest.mark.parametrize("name", sorted(PALETTES))
def test_every_palette_renders(name):
    sheet = render_theme(name)
    # CSS rules legitimately contain braces; what must not survive is a
    # placeholder like "{accent}" that no palette key filled in.
    leftover = re.findall(r"\{[a-z_]+\}", sheet)
    assert not leftover, f"unsubstituted placeholders: {leftover}"
    assert "QMainWindow" in sheet


@pytest.mark.parametrize("name", sorted(PALETTES))
def test_every_palette_has_matching_log_colors(name):
    """log_formatter looks these up by theme name; a gap silently falls back."""
    assert name in LOG_COLORS
    assert name in LOG_BACKGROUND
    assert set(LOG_COLORS[name]) == {"info", "success", "warning", "error", "muted"}


@pytest.mark.parametrize("name", sorted(PALETTES))
def test_log_background_matches_the_palette(name):
    """The log colours are contrast-checked against LOG_BACKGROUND, so it has
    to be the colour the stylesheet actually paints behind them."""
    assert LOG_BACKGROUND[name] == PALETTES[name]["log_bg"]


def test_themes_covers_every_palette():
    assert set(THEMES) == set(PALETTES)


@pytest.mark.parametrize("name", sorted(PALETTES))
@pytest.mark.parametrize("key", sorted(REQUIRED_KEYS))
def test_every_colour_is_a_hex_triplet(name, key):
    value = PALETTES[name][key]
    assert value.startswith("#") and len(value) == 7
    int(value[1:], 16)


# ── Font scaling ───────────────────────────────────────────────────────────


def test_default_scale_matches_the_historic_sizes():
    sheet = render_theme("dark", scale=DEFAULT_FONT_SCALE)
    assert "font-size: 9pt;" in sheet
    assert "font-size: 18pt;" in sheet


def test_scaling_up_enlarges_the_body_size():
    assert "font-size: 18pt;" in render_theme("dark", scale=2.0)  # 9pt body doubled


def test_scaling_down_shrinks_but_never_below_six_points():
    sheet = render_theme("dark", scale=MIN_FONT_SCALE)
    sizes = [int(part.split("pt")[0]) for part in sheet.split("font-size: ")[1:]]
    assert min(sizes) >= 6


@pytest.mark.parametrize(
    "value,expected",
    [
        (1.0, 1.0),
        (0.1, MIN_FONT_SCALE),
        (99.0, MAX_FONT_SCALE),
        (MIN_FONT_SCALE, MIN_FONT_SCALE),
        (MAX_FONT_SCALE, MAX_FONT_SCALE),
    ],
)
def test_clamp_scale(value, expected):
    assert clamp_scale(value) == expected


@pytest.mark.parametrize("junk", [None, "abc", object()])
def test_clamp_scale_survives_a_corrupt_preference(junk):
    assert clamp_scale(junk) == DEFAULT_FONT_SCALE


def test_render_clamps_an_out_of_range_scale_instead_of_raising():
    assert render_theme("dark", scale=1000) == render_theme("dark", scale=MAX_FONT_SCALE)


# ── Locale font stacks ─────────────────────────────────────────────────────


def test_arabic_locale_gets_an_arabic_capable_stack():
    assert "Noto Naskh Arabic" in render_theme("dark", locale="ar")


def test_default_locale_stack_has_no_arabic_specific_face():
    assert "Noto Naskh Arabic" not in render_theme("dark", locale="en")


# ── Theme resolution ───────────────────────────────────────────────────────


def test_theme_names_lists_auto_first():
    names = theme_names()
    assert names[0] == AUTO_THEME
    assert set(names[1:]) == set(PALETTES)


@pytest.mark.parametrize("name", sorted(PALETTES))
def test_resolve_returns_a_concrete_theme_unchanged(name):
    assert resolve_theme(name) == name


def test_resolve_falls_back_for_an_unknown_name():
    """A corrupted preference must not stop the app from starting."""
    assert resolve_theme("chartreuse") == DEFAULT_LOG_THEME


def test_resolve_auto_returns_something_renderable():
    assert resolve_theme(AUTO_THEME) in PALETTES


def test_themed_stylesheet_accepts_auto():
    assert "QMainWindow" in themed_stylesheet(AUTO_THEME)


def test_themed_stylesheet_falls_back_for_garbage():
    assert themed_stylesheet("nope") == render_theme(DEFAULT_LOG_THEME)


# ── System theme detection ─────────────────────────────────────────────────


def test_macos_dark_mode():
    assert detect_system_theme("darwin", runner=lambda cmd: "Dark") == "dark"


def test_macos_light_mode_reports_no_key_at_all():
    """`defaults read` exits non-zero in light mode, which is the signal."""
    assert detect_system_theme("darwin", runner=lambda cmd: None) == "light"


def test_linux_gnome_dark():
    assert (
        detect_system_theme("linux", runner=lambda cmd: "'prefer-dark'", env={}) == "dark"
    )


def test_linux_gnome_light():
    assert (
        detect_system_theme("linux", runner=lambda cmd: "'prefer-light'", env={})
        == "light"
    )


def test_linux_gtk_theme_env_wins():
    assert (
        detect_system_theme("linux", runner=lambda cmd: None, env={"GTK_THEME": "Adwaita:dark"})
        == "dark"
    )


def test_unknown_platform_falls_back_to_the_shipped_default():
    assert detect_system_theme("sunos5", runner=lambda cmd: None, env={}) == DEFAULT_LOG_THEME


def test_detection_never_raises_on_the_real_host():
    assert detect_system_theme() in PALETTES
