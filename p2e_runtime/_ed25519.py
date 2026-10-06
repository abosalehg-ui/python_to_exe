"""Ed25519 signature *verification*, after the RFC 8032 reference code.

The runtime only ever checks signatures, so this module only verifies. It
follows the Python reference implementation in RFC 8032 section 6 line for
line (extended twisted Edwards coordinates, ``[S]B == R + [k]A``), plus the
checks the RFC requires of a verifier:

* ``S`` must be below the group order ``L`` (rejects malleable signatures);
* ``R`` and ``A`` must be canonical encodings of points on the curve
  (``y < p``, and a square root must exist).

The point arithmetic is shared with the converter, which signs on the
developer's machine; signing is deliberately *not* part of the runtime.
Nothing here is secret, so the lack of constant-time arithmetic does not
matter for verification.
"""

import hashlib
from typing import Optional, Tuple

Point = Tuple[int, int, int, int]

#: The field prime 2^255 - 19.
P = 2 ** 255 - 19
#: The order of the base point (often written ``L`` or ``q``).
L = 2 ** 252 + 27742317777372353535851937790883648493


def _inv(x: int) -> int:
    return pow(x, P - 2, P)


D = -121665 * _inv(121666) % P
_SQRT_M1 = pow(2, (P - 1) // 4, P)

PUBLIC_KEY_BYTES = 32
SIGNATURE_BYTES = 64


def sha512_mod_l(data: bytes) -> int:
    return int.from_bytes(hashlib.sha512(data).digest(), "little") % L


def point_add(a: Point, b: Point) -> Point:
    A = (a[1] - a[0]) * (b[1] - b[0]) % P
    B = (a[1] + a[0]) * (b[1] + b[0]) % P
    C = 2 * a[3] * b[3] * D % P
    Dd = 2 * a[2] * b[2] % P
    E, F, G, H = B - A, Dd - C, Dd + C, B + A
    return (E * F, G * H, F * G, E * H)


def point_mul(scalar: int, point: Point) -> Point:
    result: Point = (0, 1, 1, 0)  # the neutral element
    while scalar > 0:
        if scalar & 1:
            result = point_add(result, point)
        point = point_add(point, point)
        scalar >>= 1
    return result


def point_equal(a: Point, b: Point) -> bool:
    # x1/z1 == x2/z2  <=>  x1*z2 == x2*z1, and the same for y.
    if (a[0] * b[2] - b[0] * a[2]) % P != 0:
        return False
    return (a[1] * b[2] - b[1] * a[2]) % P == 0


def _recover_x(y: int, sign: int) -> Optional[int]:
    if y >= P:
        return None  # non-canonical encoding
    x2 = (y * y - 1) * _inv(D * y * y + 1)
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (P + 3) // 8, P)
    if (x * x - x2) % P != 0:
        x = x * _SQRT_M1 % P
    if (x * x - x2) % P != 0:
        return None  # not on the curve
    if (x & 1) != sign:
        x = P - x
    return x


_GY = 4 * _inv(5) % P
_GX = _recover_x(_GY, 0)
assert _GX is not None
#: The base point B.
BASE: Point = (_GX, _GY, 1, _GX * _GY % P)


def point_compress(point: Point) -> bytes:
    zinv = _inv(point[2])
    x = point[0] * zinv % P
    y = point[1] * zinv % P
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def point_decompress(data: bytes) -> Optional[Point]:
    if len(data) != 32:
        return None
    y = int.from_bytes(data, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    if x is None:
        return None
    return (x, y, 1, x * y % P)


def verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    """True only if ``signature`` is a valid Ed25519 signature of ``message``.

    Never raises for malformed input: anything that is not a well-formed,
    valid signature by ``public_key`` is simply ``False``.
    """
    if not isinstance(public_key, (bytes, bytearray)) or len(public_key) != PUBLIC_KEY_BYTES:
        return False
    if not isinstance(signature, (bytes, bytearray)) or len(signature) != SIGNATURE_BYTES:
        return False
    public_key, signature, message = bytes(public_key), bytes(signature), bytes(message)
    a = point_decompress(public_key)
    if a is None:
        return False
    r_bytes = signature[:32]
    r = point_decompress(r_bytes)
    if r is None:
        return False
    s = int.from_bytes(signature[32:], "little")
    if s >= L:
        return False
    k = sha512_mod_l(r_bytes + public_key + message)
    return point_equal(point_mul(s, BASE), point_add(r, point_mul(k, a)))
