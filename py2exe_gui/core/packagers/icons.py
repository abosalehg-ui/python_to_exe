"""Icons for Linux packages, with the standard library only.

A ``.desktop`` entry and an AppImage want a PNG; the project usually holds a
Windows ``.ico``. Modern ``.ico`` files carry their large sizes as embedded
PNGs, which can be copied out as they are; older ones hold 32-bit BMPs, which
are re-encoded here (BGRA rows, stored bottom-up, with the AND mask ignored
because the alpha channel already says what is transparent). Anything else
gets a plain placeholder tile, and the caller reports that it did.
"""

import struct
import zlib
from typing import List, Optional, Tuple

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PLACEHOLDER_SIZE = 256
#: A muted blue, so a missing icon is visible without pretending to be art.
PLACEHOLDER_RGB = (0x3A, 0x6E, 0xA5)


def _chunk(kind: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))


def encode_png(width: int, height: int, rows: List[bytes], alpha: bool = True) -> bytes:
    """A PNG from raw rows (RGBA, or RGB when ``alpha`` is False), top row first."""
    color_type = 6 if alpha else 2
    raw = b"".join(b"\x00" + row for row in rows)
    return (PNG_SIGNATURE
            + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0))
            + _chunk(b"IDAT", zlib.compress(raw, 9))
            + _chunk(b"IEND", b""))


def placeholder_png(size: int = PLACEHOLDER_SIZE) -> bytes:
    """A flat tile with a lighter square inside: clearly a stand-in."""
    r, g, b = PLACEHOLDER_RGB
    inner = (min(r + 70, 255), min(g + 70, 255), min(b + 70, 255))
    margin = size // 4
    rows = []
    for y in range(size):
        row = bytearray()
        for x in range(size):
            color = inner if margin <= x < size - margin and margin <= y < size - margin else (r, g, b)
            row += bytes(color)
        rows.append(bytes(row))
    return encode_png(size, size, rows, alpha=False)


def png_size(data: bytes) -> Optional[Tuple[int, int]]:
    """``(width, height)`` of a PNG, or None when ``data`` is not one."""
    if not data.startswith(PNG_SIGNATURE) or len(data) < 24 or data[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", data[16:24])


def _ico_entries(data: bytes) -> List[Tuple[int, int, int, int, int]]:
    """``(width, height, bpp, size, offset)`` per image; [] when not an ICO."""
    if len(data) < 6:
        return []
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    if reserved != 0 or kind != 1 or count == 0:
        return []
    entries = []
    for index in range(count):
        start = 6 + index * 16
        if start + 16 > len(data):
            break
        w, h, _colors, _res, _planes, bpp, size, offset = struct.unpack(
            "<BBBBHHII", data[start:start + 16])
        if offset + size <= len(data):
            entries.append((w or 256, h or 256, bpp, size, offset))
    return entries


def _bmp_entry_to_png(blob: bytes, width: int, height: int) -> Optional[bytes]:
    """A 32-bit BMP icon image (BITMAPINFOHEADER + BGRA pixels) as a PNG."""
    if len(blob) < 40:
        return None
    header_size, bi_width, bi_height, _planes, bpp, compression = struct.unpack(
        "<IiiHHI", blob[:20])
    if header_size != 40 or bpp != 32 or compression != 0 or bi_width <= 0:
        return None
    width = bi_width
    height = abs(bi_height) // 2 if abs(bi_height) == 2 * height else abs(bi_height) // 2
    if height <= 0:
        return None
    pixels = blob[40:40 + width * height * 4]
    if len(pixels) < width * height * 4:
        return None
    rows = []
    for y in range(height - 1, -1, -1):  # stored bottom-up
        src = pixels[y * width * 4:(y + 1) * width * 4]
        row = bytearray()
        for x in range(width):
            b, g, r, a = src[x * 4:x * 4 + 4]
            row += bytes((r, g, b, a))
        rows.append(bytes(row))
    return encode_png(width, height, rows, alpha=True)


def png_from_ico(data: bytes) -> Optional[bytes]:
    """The largest image of an ``.ico`` as a PNG; None when none can be read."""
    entries = sorted(_ico_entries(data), key=lambda e: (e[0] * e[1], e[2]), reverse=True)
    for width, height, _bpp, size, offset in entries:
        blob = data[offset:offset + size]
        if blob.startswith(PNG_SIGNATURE):
            return blob
        png = _bmp_entry_to_png(blob, width, height)
        if png:
            return png
    return None


def png_from_icon_file(path: str) -> Optional[bytes]:
    """PNG bytes for a ``.png`` or ``.ico`` file; None for anything else."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return None
    if data.startswith(PNG_SIGNATURE):
        return data
    return png_from_ico(data)
