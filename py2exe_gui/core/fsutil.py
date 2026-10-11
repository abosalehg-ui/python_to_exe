"""Small file-system helpers shared across the core.

Each of these used to live in three or four modules in slightly different
forms (one size counter skipped symlinks, another did not; one hash read the
file in 64 KiB chunks, another in 1 MiB). A leaf module with no imports from
the rest of the package, so anything can use it without a cycle.
"""

import hashlib
import os

#: Read files for hashing in 1 MiB pieces: large enough that a multi-GB
#: installer hashes at disk speed, small enough not to matter in memory.
HASH_CHUNK = 1024 * 1024


def file_size(path: str) -> int:
    """Bytes of one file; 0 when it cannot be read (gone, no permission)."""
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def folder_size(path: str) -> int:
    """Bytes on disk under ``path`` (or of the file ``path``).

    Symlinks are skipped so a shared library linked under several names
    counts once, and a link pointing outside the folder adds nothing.
    """
    if os.path.isfile(path):
        return file_size(path)
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            full = os.path.join(root, name)
            if not os.path.islink(full):
                total += file_size(full)
    return total


def sha256_of(path: str, chunk: int = HASH_CHUNK) -> str:
    """The hex SHA-256 of a file, read in pieces so its size never matters."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for piece in iter(lambda: f.read(chunk), b""):
            digest.update(piece)
    return digest.hexdigest()


def same_path(a: str, b: str) -> bool:
    """True when ``a`` and ``b`` name the same file after normalisation.

    Empty strings never match anything (a missing source is not "the same"
    as another missing source). Case is folded on Windows only.
    """
    if not a or not b:
        return False
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))
