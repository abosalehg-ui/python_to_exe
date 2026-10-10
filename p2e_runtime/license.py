"""Offline licence keys: Ed25519-signed, base32, checked without a network.

A licence is a small JSON payload — who it is for (``name``, ``email``),
which ``product`` it unlocks, an optional ``expiry`` date and a list of
``features`` — signed on the developer's machine with the private half of a
key pair the converter keeps for them. The app ships only the *public* half
(in ``p2e_runtime.json``) and calls :func:`verify` or :func:`check`::

    from p2e_runtime import license

    info = license.check(key_typed_by_the_user)
    if info is None:
        ...  # not a licence for this app, tampered, or expired
    elif info.has_feature("pro"):
        ...

**What this does and does not protect.** The signature makes it impossible
to *forge* a key without the private key, so a key generator cannot be
written by someone who only has the app. It does nothing against someone who
edits the distributed app itself: a client-side check can always be patched
out of any program a user holds, and the expiry relies on the user's own
clock. Treat it as a deterrent against casual copying, not as a guarantee.

Standard library only (plus the kit's own Ed25519 verifier). Nothing here
raises on user input: a malformed key is simply ``None``.
"""

import base64
import datetime
import json
import re
from dataclasses import dataclass
from typing import Any, Optional, Tuple, Union

from p2e_runtime import _ed25519

__all__ = [
    "GROUP_SIZE",
    "STATUS_EXPIRED",
    "STATUS_INVALID",
    "STATUS_VALID",
    "STATUS_WRONG_PRODUCT",
    "LicenseInfo",
    "check",
    "decode_key",
    "encode_key",
    "format_key",
    "inspect",
    "normalize_key",
    "verify",
]

#: The first byte of every key: lets the layout change without old keys
#: being mistaken for new ones.
FORMAT_VERSION = 1
#: Letters per group in the copy-and-paste form (``XXXXX-XXXXX-…``).
GROUP_SIZE = 5
#: The payload is UTF-8 JSON; a key longer than this is not one of ours.
MAX_KEY_BYTES = 4096

STATUS_VALID = "valid"
STATUS_INVALID = "invalid"
STATUS_WRONG_PRODUCT = "wrong_product"
STATUS_EXPIRED = "expired"

# The base32 alphabet (RFC 4648) has no 0, 1 or 8: someone reading a key
# aloud or off paper mixes them up with O, I and B, so they are accepted.
_LOOKALIKES = str.maketrans("018", "OIB")
_NOT_ALPHABET = re.compile(r"[^A-Z2-7]")
_PUBLIC_HEX = re.compile(r"^[0-9a-fA-F]{64}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_FEATURE = re.compile(r"^[A-Za-z0-9_.\-]{1,64}$")


@dataclass(frozen=True)
class LicenseInfo:
    """A licence whose signature was checked. Everything in it is trusted
    as far as the signature goes — not further (see the module note)."""

    name: str
    email: str
    product: str
    #: ``YYYY-MM-DD`` (the last day the licence is valid), or '' for never.
    expiry: str = ""
    features: Tuple[str, ...] = ()

    def has_feature(self, feature: str) -> bool:
        return feature in self.features

    @property
    def expires(self) -> bool:
        return bool(self.expiry)

    def expiry_date(self) -> Optional[datetime.date]:
        return _parse_date(self.expiry) if self.expiry else None

    def is_expired(self, today: Optional[datetime.date] = None) -> bool:
        """True from the day *after* ``expiry``: the expiry day itself counts."""
        date = self.expiry_date()
        if date is None:
            return False
        return (today or datetime.date.today()) > date

    def days_left(self, today: Optional[datetime.date] = None) -> Optional[int]:
        """Days until expiry (0 on the last day, negative after), or ``None``."""
        date = self.expiry_date()
        if date is None:
            return None
        return (date - (today or datetime.date.today())).days


# ── Text form ──────────────────────────────────────────────────────────────


def normalize_key(text: str) -> str:
    """The bare base32 letters of a typed key: case, spaces, dashes and
    line breaks do not matter, nor do O/0, I/1 and B/8 mix-ups."""
    if not isinstance(text, str):
        return ""
    return _NOT_ALPHABET.sub("", text.upper().translate(_LOOKALIKES))


def format_key(letters: str) -> str:
    """``XXXXX-XXXXX-…`` from bare letters, for display and copying."""
    letters = normalize_key(letters)
    return "-".join(letters[i:i + GROUP_SIZE] for i in range(0, len(letters), GROUP_SIZE))


def encode_key(payload: bytes, signature: bytes) -> str:
    """The grouped text form of a signed payload (the converter calls this)."""
    if len(signature) != _ed25519.SIGNATURE_BYTES:
        raise ValueError("an Ed25519 signature is 64 bytes")
    raw = bytes([FORMAT_VERSION]) + signature + payload
    return format_key(base64.b32encode(raw).decode("ascii").rstrip("="))


def decode_key(text: str) -> Optional[Tuple[bytes, bytes]]:
    """``(payload, signature)`` from a typed key, or ``None`` for garbage."""
    letters = normalize_key(text)
    if not letters or len(letters) > MAX_KEY_BYTES * 2:
        return None
    padded = letters + "=" * (-len(letters) % 8)
    try:
        raw = base64.b32decode(padded)
    except (ValueError, TypeError):
        return None
    if len(raw) < 1 + _ed25519.SIGNATURE_BYTES + 2 or raw[0] != FORMAT_VERSION:
        return None
    signature = raw[1:1 + _ed25519.SIGNATURE_BYTES]
    return raw[1 + _ed25519.SIGNATURE_BYTES:], signature


# ── Verification ───────────────────────────────────────────────────────────


def _parse_date(text: str) -> Optional[datetime.date]:
    if not isinstance(text, str) or not _DATE.match(text):
        return None
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        return None


def _public_key_bytes(public_key: Union[str, bytes, None]) -> Optional[bytes]:
    if isinstance(public_key, (bytes, bytearray)):
        return bytes(public_key) if len(public_key) == _ed25519.PUBLIC_KEY_BYTES else None
    if isinstance(public_key, str) and _PUBLIC_HEX.match(public_key.strip()):
        return bytes.fromhex(public_key.strip())
    return None


def _info_from_payload(payload: bytes) -> Optional[LicenseInfo]:
    try:
        data: Any = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    name, email, product = data.get("name"), data.get("email", ""), data.get("product")
    expiry = data.get("expiry") or ""
    features = data.get("features") or []
    if not isinstance(name, str) or not isinstance(product, str) or not product.strip():
        return None
    if not isinstance(email, str) or not isinstance(expiry, str):
        return None
    if expiry and _parse_date(expiry) is None:
        return None
    if not isinstance(features, list) or not all(
        isinstance(f, str) and _FEATURE.match(f) for f in features
    ):
        return None
    return LicenseInfo(name, email, product, expiry, tuple(features))


def inspect(key: str, public_key: Union[str, bytes, None], product: str = "",
            today: Optional[datetime.date] = None) -> Tuple[str, Optional[LicenseInfo]]:
    """``(status, info)``: like :func:`verify`, but says *why* a key fails.

    ``info`` is filled for :data:`STATUS_EXPIRED` and
    :data:`STATUS_WRONG_PRODUCT` too, so an app can say "expired on …"; it is
    ``None`` only for :data:`STATUS_INVALID`, when nothing in the key can be
    trusted. Never raises on its inputs.
    """
    try:
        key_bytes = _public_key_bytes(public_key)
        decoded = decode_key(key)
        if key_bytes is None or decoded is None:
            return STATUS_INVALID, None
        payload, signature = decoded
        if not _ed25519.verify(key_bytes, payload, signature):
            return STATUS_INVALID, None
        info = _info_from_payload(payload)
        if info is None:
            return STATUS_INVALID, None
        if product and info.product.strip() != str(product).strip():
            return STATUS_WRONG_PRODUCT, info
        if info.is_expired(today):
            return STATUS_EXPIRED, info
        return STATUS_VALID, info
    except Exception:  # a bug here must never take the app down
        return STATUS_INVALID, None


def verify(key: str, public_key: Union[str, bytes, None], product: str = "",
           today: Optional[datetime.date] = None) -> Optional[LicenseInfo]:
    """The licence in ``key`` if it is genuine, for ``product`` (when given)
    and not expired; otherwise ``None``. Never raises on its inputs."""
    status, info = inspect(key, public_key, product, today)
    return info if status == STATUS_VALID else None


def check(key: str, config=None, today: Optional[datetime.date] = None) -> Optional[LicenseInfo]:
    """:func:`verify` against the public key and product bundled with the app.

    ``None`` when the build has no licensing section (the converter's
    *Licensing* service was off), as well as for a bad key.
    """
    try:
        if config is None:
            from p2e_runtime import current_config

            config = current_config()
        licensing = getattr(config, "licensing", None)
        if licensing is None:
            return None
        return verify(key, licensing.public_key, licensing.product, today)
    except Exception:
        return None
