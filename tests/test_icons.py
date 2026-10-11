"""The icon set (2.1): Lucide SVGs shipped in the package, coloured per theme.

Every name the application uses must resolve to a file, render with the
requested colour, mirror for right-to-left layouts, and never raise for an
unknown name. Headless (offscreen)."""

import os
import re

import pytest

pytest.importorskip("py2exe_gui.qt", reason="no Qt binding (PySide6/PyQt5) installed")

from py2exe_gui import icons  # noqa: E402
from py2exe_gui.qt import QSize  # noqa: E402
from py2exe_gui.styles import PALETTES  # noqa: E402

pytestmark = pytest.mark.gui


def _ink(image, color_test):
    return sum(
        1 for x in range(image.width()) for y in range(image.height())
        if image.pixelColor(x, y).alpha() > 0 and color_test(image.pixelColor(x, y))
    )


def test_every_name_has_a_file():
    missing = [name for name in icons.icon_names() if not os.path.isfile(icons.icon_path(name))]
    assert not missing


def test_every_file_is_a_current_color_svg_with_the_licence_header():
    for name in icons.icon_names():
        text = icons.svg_text(name)
        assert "currentColor" in text, name
        assert "@license lucide-static" in text and "ISC" in text, name
    assert os.path.isfile(os.path.join(icons.ICON_DIR, "LICENSE"))


def test_unused_files_are_not_shipped():
    """What is in the package is what the vocabulary names, nothing more."""
    used = {icons.NAMES[name] + ".svg" for name in icons.NAMES}
    shipped = {f for f in os.listdir(icons.ICON_DIR) if f.endswith(".svg")}
    assert shipped == used


def test_icon_renders_in_the_requested_colour(qapp):
    icon = icons.icon("section_build", "#ff0000")
    assert not icon.isNull()
    assert [s.width() for s in icon.availableSizes()] == list(icons.SIZES)
    image = icon.pixmap(QSize(24, 24)).toImage()
    red = _ink(image, lambda c: c.red() > 200 and c.green() < 60)
    assert red > 50


def test_unknown_name_gives_an_empty_icon_not_an_error(qapp):
    assert icons.icon("no-such-icon").isNull()
    assert icons.coloured_svg("no-such-icon", "#000") == b""


def test_icons_are_cached(qapp):
    assert icons.icon("start", "#123456") is icons.icon("start", "#123456")
    assert icons.icon("start", "#123456") is not icons.icon("start", "#654321")


def test_directional_icons_mirror_for_rtl(qapp):
    palette = PALETTES["dark"]
    ltr = icons.themed_icon("chevron_right", palette, rtl=False).pixmap(QSize(24, 24)).toImage()
    rtl = icons.themed_icon("chevron_right", palette, rtl=True).pixmap(QSize(24, 24)).toImage()
    left_ltr = sum(1 for x in range(12) for y in range(24) if ltr.pixelColor(x, y).alpha() > 0)
    left_rtl = sum(1 for x in range(12) for y in range(24) if rtl.pixelColor(x, y).alpha() > 0)
    assert left_ltr != left_rtl
    # A symmetric icon is not mirrored.
    same_a = icons.themed_icon("section_settings", palette, rtl=False)
    same_b = icons.themed_icon("section_settings", palette, rtl=True)
    assert same_a is same_b


@pytest.mark.parametrize("theme", sorted(PALETTES))
def test_themed_icon_uses_the_palette_text_colour(qapp, theme):
    palette = PALETTES[theme]
    image = icons.themed_icon("section_check", palette).pixmap(QSize(32, 32)).toImage()
    target = palette["text"].lstrip("#")
    r, g, b = (int(target[i:i + 2], 16) for i in (0, 2, 4))
    close = _ink(image, lambda c: abs(c.red() - r) < 8 and abs(c.green() - g) < 8
                 and abs(c.blue() - b) < 8)
    assert close > 20


def test_svg_sources_are_minified_single_line():
    for name in icons.icon_names():
        assert len(icons.svg_text(name).strip().splitlines()) == 1, name


def test_vocabulary_names_are_snake_case():
    assert all(re.fullmatch(r"[a-z][a-z0-9_]*", name) for name in icons.NAMES)
