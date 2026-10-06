"""Update signing for the Runtime Kit: key pair, signatures, update manifests.

The app the developer ships only *verifies* (``p2e_runtime._ed25519``). The
private half lives here, on the developer's machine:

* generated from ``os.urandom`` and stored in the per-user config folder
  with owner-only permissions — never in the project, a build, a settings or
  preset file, or the log;
* used to sign ``update.json`` with Ed25519 (RFC 8032, deterministic).

Signing reuses the runtime's point arithmetic, so there is exactly one copy
of the curve code. Python integers are not constant-time; that matters only
to an attacker who can time signing operations on the developer's own
machine, which is outside what this tool can defend against.
"""

import datetime
import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from p2e_runtime import _ed25519
from p2e_runtime.updates import UpdateError, check_url, parse_manifest, parse_version

KEY_FORMAT = "p2e-ed25519-private-key-v1"
KEY_FILE_NAME = "update_signing_key.json"
MANIFEST_NAME = "update.json"
SIGNATURE_SUFFIX = ".sig"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


# ── Ed25519 signing (RFC 8032 §5.1.5–5.1.6) ────────────────────────────────


def _expand(seed: bytes) -> Tuple[int, bytes]:
    if len(seed) != 32:
        raise ValueError("an Ed25519 private key is 32 bytes")
    digest = hashlib.sha512(seed).digest()
    scalar = int.from_bytes(digest[:32], "little")
    scalar &= (1 << 254) - 8
    scalar |= 1 << 254
    return scalar, digest[32:]


def public_key_from_seed(seed: bytes) -> bytes:
    scalar, _prefix = _expand(seed)
    return _ed25519.point_compress(_ed25519.point_mul(scalar, _ed25519.BASE))


def sign(seed: bytes, message: bytes) -> bytes:
    """The 64-byte Ed25519 signature of ``message``."""
    scalar, prefix = _expand(seed)
    public = _ed25519.point_compress(_ed25519.point_mul(scalar, _ed25519.BASE))
    r = _ed25519.sha512_mod_l(prefix + message)
    r_bytes = _ed25519.point_compress(_ed25519.point_mul(r, _ed25519.BASE))
    k = _ed25519.sha512_mod_l(r_bytes + public + message)
    s = (r + k * scalar) % _ed25519.L
    return r_bytes + int.to_bytes(s, 32, "little")


def generate_seed() -> bytes:
    return os.urandom(32)


def fingerprint(public_hex: str) -> str:
    """A short, readable form of a public key for confirmation dialogs."""
    key = (public_hex or "").strip().lower()
    return " ".join(key[i:i + 4] for i in range(0, min(len(key), 16), 4))


def is_public_key(text: str) -> bool:
    return bool(_HEX64.match((text or "").strip().lower()))


# ── Key file ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SigningKey:
    seed: bytes
    public_hex: str
    created: str = ""

    def __repr__(self) -> str:  # never print the secret by accident
        return f"SigningKey(public={self.public_hex[:16]}…)"


def new_signing_key() -> SigningKey:
    seed = generate_seed()
    created = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return SigningKey(seed, public_key_from_seed(seed).hex(), created)


def key_to_json(key: SigningKey) -> str:
    return json.dumps(
        {
            "format": KEY_FORMAT,
            "warning": "PRIVATE KEY. Anyone holding this file can publish updates "
                       "that your apps will install. Never share it or commit it.",
            "private_key": key.seed.hex(),
            "public_key": key.public_hex,
            "created": key.created,
        },
        indent=2,
    ) + "\n"


def key_from_json(text: str) -> SigningKey:
    """Parse a key file, checking that its public half matches its private half."""
    try:
        data = json.loads(text)
    except ValueError as e:
        raise ValueError(f"not a key file: {e}") from e
    if not isinstance(data, dict) or data.get("format") != KEY_FORMAT:
        raise ValueError("not a Python to EXE Converter signing key")
    private = str(data.get("private_key", "")).strip().lower()
    if not _HEX64.match(private):
        raise ValueError("the private key must be 64 hex characters")
    seed = bytes.fromhex(private)
    public = public_key_from_seed(seed).hex()
    stated = str(data.get("public_key", "")).strip().lower()
    if stated and stated != public:
        raise ValueError("the public key does not belong to this private key")
    return SigningKey(seed, public, str(data.get("created", "")))


def _restrict_permissions(path: str) -> None:
    # Owner read/write only. On Windows chmod can only toggle read-only; the
    # per-user AppData folder is already private to the account by its ACL.
    if sys.platform != "win32":
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def write_key_file(path: str, key: SigningKey, overwrite: bool = False) -> None:
    """Create ``path`` with owner-only permissions from the first byte.

    Refuses to replace an existing key unless ``overwrite``: losing the key
    means apps already out there can never be updated again.
    """
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    if sys.platform != "win32":
        try:
            os.chmod(folder, stat.S_IRWXU)
        except OSError:
            pass
    flags = os.O_WRONLY | os.O_CREAT | (os.O_TRUNC if overwrite else os.O_EXCL)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(key_to_json(key))
    _restrict_permissions(path)


def read_key_file(path: str) -> SigningKey:
    with open(path, encoding="utf-8") as f:
        return key_from_json(f.read())


def read_public_key(path: str) -> str:
    """The public key of the stored pair, or '' when there is none (or it is broken)."""
    try:
        return read_key_file(path).public_hex
    except (OSError, ValueError):
        return ""


def backup_existing(path: str) -> str:
    """Rename a key about to be replaced, never delete it. Returns the new name."""
    if not os.path.exists(path):
        return ""
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = f"{path}.replaced-{stamp}"
    os.replace(path, backup)
    return backup


def is_inside(path: str, folder: str) -> bool:
    if not path or not folder:
        return False
    target = os.path.normcase(os.path.realpath(path))
    root = os.path.normcase(os.path.realpath(folder)).rstrip("\\/")
    return target == root or target.startswith(root + os.sep)


# ── Publishing an update ───────────────────────────────────────────────────


@dataclass(frozen=True)
class PublishedUpdate:
    manifest_path: str
    signature_path: str
    manifest: Dict[str, object]


def file_digest(path: str) -> Tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def manifest_bytes(manifest: Dict[str, object]) -> bytes:
    """The exact bytes that are signed and uploaded (UTF-8, stable order)."""
    return (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def build_manifest(file_path: str, version: str, url: str, notes: str = "",
                   min_version: str = "", app_name: str = "") -> Dict[str, object]:
    """Describe ``file_path`` as an update. Raises ``ValueError`` on bad input."""
    try:
        parse_version(version)
        if min_version:
            parse_version(min_version)
        check_url(url)
    except UpdateError as e:
        raise ValueError(f"the download URL must start with https:// ({e.detail})") from e
    if not os.path.isfile(file_path):
        raise ValueError(f"no such file: {file_path}")
    sha256, size = file_digest(file_path)
    if size == 0:
        raise ValueError("the file is empty")
    manifest: Dict[str, object] = {}
    if app_name:
        manifest["app"] = app_name
    manifest.update({
        "version": version.strip(),
        "url": url.strip(),
        "sha256": sha256,
        "size": size,
        "notes": notes,
        "min_version": min_version.strip(),
    })
    return manifest


def publish_update(file_path: str, version: str, url: str, key: SigningKey, notes: str = "",
                   min_version: str = "", app_name: str = "",
                   output_dir: Optional[str] = None) -> PublishedUpdate:
    """Write ``update.json`` and ``update.json.sig`` beside ``file_path``.

    Nothing is uploaded: the developer puts both files (and the new build)
    on their server. The signature is checked with the runtime's own
    verifier before anything is written.
    """
    manifest = build_manifest(file_path, version, url, notes, min_version, app_name)
    data = manifest_bytes(manifest)
    signature = sign(key.seed, data)
    if not _ed25519.verify(bytes.fromhex(key.public_hex), data, signature):
        raise ValueError("internal error: the new signature does not verify")
    parse_manifest(data, app_name)  # exactly what the runtime will accept

    folder = output_dir or os.path.dirname(os.path.abspath(file_path))
    manifest_path = os.path.join(folder, MANIFEST_NAME)
    signature_path = manifest_path + SIGNATURE_SUFFIX
    with open(manifest_path, "wb") as f:
        f.write(data)
    with open(signature_path, "w", encoding="ascii") as f:
        f.write(signature.hex() + "\n")
    return PublishedUpdate(manifest_path, signature_path, manifest)
