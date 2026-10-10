"""Issuing offline licence keys: the developer's side of ``p2e_runtime.license``.

The built app only *verifies* (``p2e_runtime/license.py``). Everything that
needs the private key happens here, on the developer's machine:

* the key pair is the same kind as the update-signing key (1.5) and is kept
  the same way — ``update_signing``'s file format, owner-only permissions,
  in the per-user config folder — but in a file of its own,
  ``signing/license_signing_key.json``: whoever issues licences need not be
  able to publish updates;
* a licence is a JSON payload (``name``, ``email``, ``product``, optional
  ``expiry``, ``features``) signed with Ed25519 and encoded as grouped base32.

The private key is never written into the project file, a build, a settings
file or the log; ``tests/test_licensing.py`` builds a kit and checks.

**Honesty.** A key checked inside a program the customer holds deters casual
copying — nobody can forge a key without the private half — but the check
can be patched out of any distributed app. Nothing here claims more.
"""

import datetime
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from p2e_runtime import license as runtime_license
from py2exe_gui.core.update_signing import (
    SigningKey,
    backup_existing,
    new_signing_key,
    read_key_file,
    read_public_key,
    sign,
    write_key_file,
)

KEY_FILE_NAME = "license_signing_key.json"

# One "@" with something on both sides and a dot in the domain: enough to
# catch a typo, not a validator — the address is only a label in the key.
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_FEATURE = re.compile(r"^[A-Za-z0-9_.\-]{1,64}$")
_SPLIT = re.compile(r"[,\s;]+")

ERR_NAME_MISSING = "name_missing"
ERR_PRODUCT_MISSING = "product_missing"
ERR_EMAIL_INVALID = "email_invalid"
ERR_EXPIRY_INVALID = "expiry_invalid"
ERR_EXPIRY_PAST = "expiry_past"
ERR_FEATURE_INVALID = "feature_invalid"


@dataclass
class LicenseRequest:
    """What goes into a key. ``expiry`` is ``YYYY-MM-DD`` or '' for never."""

    name: str = ""
    email: str = ""
    product: str = ""
    expiry: str = ""
    features: Tuple[str, ...] = field(default_factory=tuple)


def parse_features(text: str) -> Tuple[str, ...]:
    """``"pro, export cloud"`` → ``("pro", "export", "cloud")``, order kept, no repeats."""
    seen: List[str] = []
    for item in _SPLIT.split(text or ""):
        if item and item not in seen:
            seen.append(item)
    return tuple(seen)


def validate_request(request: LicenseRequest,
                     today: Optional[datetime.date] = None) -> List[Tuple[str, str]]:
    """``[(code, offending value), …]``; empty when the request can be issued."""
    problems: List[Tuple[str, str]] = []
    if not request.name.strip():
        problems.append((ERR_NAME_MISSING, ""))
    if not request.product.strip():
        problems.append((ERR_PRODUCT_MISSING, ""))
    email = request.email.strip()
    if email and not _EMAIL.match(email):
        problems.append((ERR_EMAIL_INVALID, email))
    expiry = request.expiry.strip()
    if expiry:
        try:
            date = datetime.date.fromisoformat(expiry)
        except ValueError:
            problems.append((ERR_EXPIRY_INVALID, expiry))
        else:
            if len(expiry) != 10:
                problems.append((ERR_EXPIRY_INVALID, expiry))
            elif date < (today or datetime.date.today()):
                problems.append((ERR_EXPIRY_PAST, expiry))
    for feature in request.features:
        if not _FEATURE.match(feature):
            problems.append((ERR_FEATURE_INVALID, feature))
    return problems


def payload_bytes(request: LicenseRequest) -> bytes:
    """The exact bytes that are signed: compact JSON, keys in a fixed order."""
    import json

    data = {
        "name": request.name.strip(),
        "email": request.email.strip(),
        "product": request.product.strip(),
        "expiry": request.expiry.strip(),
        "features": list(request.features),
    }
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def issue(request: LicenseRequest, key: SigningKey,
          today: Optional[datetime.date] = None) -> str:
    """The licence key for ``request``, checked with the runtime's own
    verifier before it is returned. ``ValueError`` on a bad request."""
    problems = validate_request(request, today)
    if problems:
        raise ValueError(", ".join(f"{code}: {value}" if value else code
                                   for code, value in problems))
    payload = payload_bytes(request)
    text = runtime_license.encode_key(payload, sign(key.seed, payload))
    info = runtime_license.verify(text, key.public_hex, request.product.strip(), today)
    if info is None or info.name != request.name.strip():
        raise ValueError("internal error: the new key does not verify")
    return text


def load_or_create_key(path: str) -> Tuple[SigningKey, bool]:
    """The licence key at ``path``, created when there is none. ``(key, created)``.

    A file that exists but is broken is *not* replaced silently: raising lets
    the caller ask, since replacing a key means every licence already sold
    stops working in new builds.
    """
    if os.path.exists(path):
        return read_key_file(path), False
    key = new_signing_key()
    write_key_file(path, key)
    return key, True


def replace_key(path: str) -> Tuple[SigningKey, str]:
    """A new key pair at ``path``; the old file is renamed, never deleted.
    Returns ``(key, backup path or '')``."""
    key = new_signing_key()
    backup = backup_existing(path)
    write_key_file(path, key)
    return key, backup


def public_key_at(path: str) -> str:
    """The public half of the stored licence key, or '' (same as the update key)."""
    return read_public_key(path)


def verify_with_key(text: str, path: str, product: str = ""):
    """``(status, info)`` for a key against the developer's own public key."""
    return runtime_license.inspect(text, public_key_at(path), product)
