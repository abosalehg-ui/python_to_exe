"""Read and write Windows .ico files without an imaging library.

Two jobs:

* ``pack_ico`` assembles a multi-resolution .ico from PNG images. Since
  Windows Vista an .ico entry may hold PNG data directly, so no pixel format
  conversion is needed: the UI renders each size with Qt and hands the PNG
  bytes here. That keeps Pillow out of the dependency list.
* ``read_ico_sizes`` lists the resolutions inside an .ico. It is how the
  doctor spots a PNG renamed to .ico (no ICO header at all) or an icon with a
  single size that Windows will blur when it scales it.
"""

import struct
from typing import Dict, List, Optional

# The sizes Windows asks an icon for across Explorer, the taskbar, Alt+Tab and
# high-DPI displays. 256 is stored as 0 in the directory entry.
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_HEADER = struct.Struct("<HHH")
_ENTRY = struct.Struct("<BBBBHHII")


def pack_ico(images: Dict[int, bytes]) -> bytes:
    """Build an .ico from ``{size: png_bytes}``.

    Raises ValueError for an empty mapping, a size outside 1..256, or data
    that is not PNG.
    """
    if not images:
        raise ValueError("no images to pack")
    sizes = sorted(images)
    for size in sizes:
        if not 1 <= size <= 256:
            raise ValueError(f"icon size out of range: {size}")
        if not images[size].startswith(PNG_SIGNATURE):
            raise ValueError(f"image for size {size} is not PNG data")

    header = _HEADER.pack(0, 1, len(sizes))
    offset = _HEADER.size + _ENTRY.size * len(sizes)
    directory = b""
    payload = b""
    for size in sizes:
        data = images[size]
        dim = 0 if size == 256 else size
        directory += _ENTRY.pack(dim, dim, 0, 0, 1, 32, len(data), offset)
        payload += data
        offset += len(data)
    return header + directory + payload


def read_ico_sizes(data: bytes) -> Optional[List[int]]:
    """The square sizes stored in an .ico, or None when it is not an .ico.

    Only the directory is read; the image data itself is not decoded.
    """
    if len(data) < _HEADER.size:
        return None
    reserved, kind, count = _HEADER.unpack_from(data, 0)
    if reserved != 0 or kind != 1 or count == 0:
        return None
    if len(data) < _HEADER.size + count * _ENTRY.size:
        return None
    sizes = []
    for i in range(count):
        width, _h, _c, _r, _p, _bpp, length, offset = _ENTRY.unpack_from(
            data, _HEADER.size + i * _ENTRY.size
        )
        if offset + length > len(data):
            return None
        sizes.append(256 if width == 0 else width)
    return sorted(set(sizes))


def read_ico_file_sizes(path: str) -> Optional[List[int]]:
    """``read_ico_sizes`` for a file on disk; None when unreadable."""
    try:
        with open(path, "rb") as f:
            return read_ico_sizes(f.read())
    except OSError:
        return None


def monogram(text: str) -> str:
    """The one or two characters drawn on a generated letter icon.

    Takes the first character of the first two words, so "My Tool" → "MT",
    and a single word or an emoji yields just its first character.
    """
    words = [w for w in (text or "").split() if w]
    if not words:
        return ""
    if len(words) == 1:
        return words[0][0].upper()
    return (words[0][0] + words[1][0]).upper()
