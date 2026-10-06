"""Tests for the .ico packer and reader."""

import struct

import pytest

from py2exe_gui.core.icon_studio import (
    ICO_SIZES,
    PNG_SIGNATURE,
    monogram,
    pack_ico,
    read_ico_file_sizes,
    read_ico_sizes,
)


def fake_png(tag: bytes = b"") -> bytes:
    """Enough of a PNG for the packer, which checks only the signature."""
    return PNG_SIGNATURE + b"\x00" * 16 + tag


def test_pack_then_read_round_trips_every_size():
    data = pack_ico({size: fake_png() for size in ICO_SIZES})
    assert read_ico_sizes(data) == list(ICO_SIZES)


def test_256_is_stored_as_zero_in_the_directory():
    data = pack_ico({256: fake_png()})
    width = data[6]
    assert width == 0
    assert read_ico_sizes(data) == [256]


def test_offsets_point_at_each_png():
    images = {16: fake_png(b"a"), 32: fake_png(b"bb")}
    data = pack_ico(images)
    for i, size in enumerate(sorted(images)):
        entry = data[6 + 16 * i: 6 + 16 * (i + 1)]
        _w, _h, _c, _r, planes, bpp, length, offset = struct.unpack("<BBBBHHII", entry)
        assert (planes, bpp) == (1, 32)
        assert data[offset: offset + length] == images[size]


@pytest.mark.parametrize(
    "images",
    [{}, {0: fake_png()}, {257: fake_png()}, {16: b"GIF89a"}],
)
def test_pack_rejects_bad_input(images):
    with pytest.raises(ValueError):
        pack_ico(images)


def test_png_renamed_to_ico_is_not_an_ico():
    assert read_ico_sizes(fake_png()) is None


def test_truncated_ico_is_rejected():
    data = pack_ico({16: fake_png(), 32: fake_png()})
    assert read_ico_sizes(data[:10]) is None
    assert read_ico_sizes(data[:-5]) is None


def test_read_from_file(tmp_path):
    path = tmp_path / "a.ico"
    path.write_bytes(pack_ico({48: fake_png()}))
    assert read_ico_file_sizes(str(path)) == [48]
    assert read_ico_file_sizes(str(tmp_path / "missing.ico")) is None


@pytest.mark.parametrize(
    "text, expected",
    [("My Tool", "MT"), ("calculator", "C"), ("", ""), ("  spaced   out  ", "SO")],
)
def test_monogram(text, expected):
    assert monogram(text) == expected
