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
    MONO_FONT_STACK,
    PALETTES,
    THEMES,
    UI_FONT_STACKS,
    base_point_size,
    clamp_scale,
    detect_system_theme,
    font_family_css,
    mono_family_css,
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
    assert "Noto Naskh Arabic" not in font_family_css("en")
    # The sheet still names it, once: as the Arabic fallback of the log font.
    assert render_theme("dark", locale="en").count("Noto Naskh Arabic") == mono_family_css_count()


def mono_family_css_count():
    return render_theme("dark", locale="en").count(mono_family_css())


def test_log_font_stack_has_an_arabic_capable_monospace_after_the_latin_ones():
    """An Arabic log line must not fall back to a proportional font."""
    names = list(MONO_FONT_STACK)
    latin = [names.index(n) for n in ("Cascadia Mono", "Consolas")]
    arabic = [i for i, n in enumerate(names) if "Arabic" in n or n == "Kawkab Mono"]
    assert arabic and max(latin) < min(arabic)
    assert mono_family_css().endswith(", monospace")


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


# ── Accessibility: field borders and the focus ring ────────────────────────


def _relative_luminance(hex_color: str) -> float:
    channels = [int(hex_color.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    la, lb = _relative_luminance(a), _relative_luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


@pytest.mark.parametrize("name", sorted(PALETTES))
def test_input_border_is_visible_against_the_field(name):
    """WCAG 1.4.11: a control's boundary needs 3:1 against what it sits on."""
    palette = PALETTES[name]
    ratio = contrast(palette["input_border"], palette["input_bg"])
    assert ratio >= 3.0, f"{name}: input_border/input_bg is only {ratio:.2f}:1"


def test_light_theme_fields_are_distinct_from_the_window():
    """A field the same colour as the window has only its 1px edge to show."""
    assert PALETTES["light"]["input_bg"] != PALETTES["light"]["window_bg"]


def test_checkbox_focus_draws_a_ring_on_the_indicator():
    sheet = render_theme("dark")
    rule = sheet.split("QCheckBox:focus::indicator")[1].split("}")[0]
    assert "border: 2px solid" in rule and PALETTES["dark"]["focus_ring"] in rule


# ── Group box title: Qt mirrors subcontrol-position itself ─────────────────


@pytest.mark.parametrize("locale", ["ar", "en"])
def test_group_title_is_not_mirrored_by_hand(locale):
    """``top right`` under RTL flipped the title back to the left."""
    sheet = render_theme("dark", locale=locale)
    assert "subcontrol-position: top left;" in sheet
    assert "subcontrol-position: top right;" not in sheet


def test_group_title_lands_on_the_right_under_rtl(qapp):
    from py2exe_gui.qt import QGroupBox, QStyle, QStyleOptionGroupBox, Qt, QWidget

    host = QWidget()
    host.setStyleSheet(render_theme("dark", locale="ar"))
    box = QGroupBox("عنوان", host)
    box.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    box.resize(400, 120)
    host.show()
    qapp.processEvents()
    option = QStyleOptionGroupBox()
    option.initFrom(box)
    option.rect = box.rect()
    option.text = box.title()
    option.subControls = QStyle.SubControl.SC_GroupBoxLabel | QStyle.SubControl.SC_GroupBoxFrame
    label = box.style().subControlRect(
        QStyle.ComplexControl.CC_GroupBox, option, QStyle.SubControl.SC_GroupBoxLabel, box
    )
    assert label.center().x() > box.width() / 2, label
    host.close()


# ── Font sizes outside the stylesheet ──────────────────────────────────────


def test_base_point_size_scales_like_the_sheet():
    assert base_point_size("primary") == 11
    assert base_point_size("score") == 16
    assert base_point_size("primary", 2.0) == 22
    assert base_point_size("log", MIN_FONT_SCALE) >= 6


def test_primary_button_and_score_are_sized_by_the_sheet():
    sheet = render_theme("dark", scale=2.0)
    assert 'QPushButton#successBtn[primary="true"]' in sheet
    assert "QLabel#doctorScore" in sheet
    assert "font-size: 22pt;" in sheet and "font-size: 32pt;" in sheet


def test_qt_font_families_come_from_the_style_table(qapp):
    """One source for the UI font: qt.application_font reads UI_FONT_STACKS."""
    from py2exe_gui import qt

    assert qt.FONT_FAMILIES == UI_FONT_STACKS["ar"]
    assert qt.font_families("en") == UI_FONT_STACKS["default"]
    font = qt.application_font(10, "en")
    if hasattr(font, "families"):
        assert list(font.families()) == list(UI_FONT_STACKS["default"])


# ── The monospace rule stays on the log ────────────────────────────────────


def test_monospace_is_scoped_to_log_and_code_views():
    sheet = render_theme("dark")
    prose = sheet.split("\nQTextEdit {")[1].split("}")[0]
    assert "font-family" not in prose
    log = sheet.split("QTextEdit#logOutput, QPlainTextEdit#logOutput {")[1].split("}")[0]
    assert mono_family_css() in log
