"""Release files: where they go, what they are called, the portable ZIP, SHA256SUMS.

Everything is written to ``<output>/release/<version>/``. Each function can be
run again and gives the same result — the ZIP is built with fixed timestamps
and sorted entries, so rebuilding it from the same build gives the same bytes
and the same checksum.
"""

import hashlib
import os
import re
import shutil
import zipfile
from typing import Dict, List, Optional, Sequence

from py2exe_gui.core.config import BuildConfig
from py2exe_gui.core.diagnostics import build_name, build_root
from py2exe_gui.core.smoke_test import locate_built_executable

CHECKSUMS_NAME = "SHA256SUMS.txt"
NOTES_NAME = "RELEASE_NOTES.md"
#: ZIP's earliest representable time: a fixed stamp keeps the archive reproducible.
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


def safe_name(name: str) -> str:
    """An asset name GitHub keeps as is (it rewrites spaces and odd characters)."""
    cleaned = re.sub(r"[^A-Za-z0-9._+-]+", "-", name.strip()).strip("-.")
    return cleaned or "app"


def release_dir(config: BuildConfig, version: str) -> str:
    return os.path.join(build_root(config), "release", version)


def exe_asset_name(config: BuildConfig, version: str, built_path: str = "",
                   ext: str = ".exe") -> str:
    """``<name>-<version><ext>``; the extension of ``built_path`` when given."""
    if built_path:
        ext = os.path.splitext(built_path)[1]
    return f"{safe_name(build_name(config))}-{version}{ext}"


def zip_asset_name(config: BuildConfig, version: str) -> str:
    return f"{safe_name(build_name(config))}-{version}-portable.zip"


def installer_basename(config: BuildConfig, version: str) -> str:
    """Setup file name (no extension) used for a release."""
    return f"{safe_name(build_name(config))}-{version}-setup"


def built_output(config: BuildConfig) -> str:
    """The EXE (one-file) or the folder (one-dir) PyInstaller produced; '' if none."""
    exe = locate_built_executable(
        config.output_dir or os.path.dirname(config.source),
        build_name(config),
        config.onefile,
    )
    if not exe:
        return ""
    return exe if config.onefile else os.path.dirname(exe)


def copy_file(source: str, target: str) -> str:
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copy2(source, target)
    return target


def make_portable_zip(source: str, target: str) -> str:
    """Zip a one-file EXE, or a one-dir folder under its own name. Reproducible."""
    os.makedirs(os.path.dirname(target), exist_ok=True)
    entries = []
    if os.path.isdir(source):
        root_name = os.path.basename(source.rstrip("\\/"))
        for folder, dirs, files in os.walk(source):
            dirs.sort()
            for name in sorted(files):
                path = os.path.join(folder, name)
                rel = os.path.relpath(path, source).replace(os.sep, "/")
                entries.append((path, f"{root_name}/{rel}"))
    elif os.path.isfile(source):
        entries.append((source, os.path.basename(source)))
    else:
        raise FileNotFoundError(source)
    temp = target + ".tmp"
    with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, arcname in entries:
            info = zipfile.ZipInfo(arcname, date_time=_ZIP_EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            # Keep the executable bit for non-Windows builds; 0o644 otherwise.
            mode = 0o755 if os.access(path, os.X_OK) else 0o644
            info.external_attr = (0o100000 | mode) << 16
            with open(path, "rb") as f:
                archive.writestr(info, f.read())
    os.replace(temp, target)
    return target


def sha256_of(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_checksums(paths: Sequence[str]) -> str:
    """``sha256sum``-compatible text: ``<hash>  <name>``, sorted by name."""
    rows = sorted((os.path.basename(p), sha256_of(p)) for p in paths)
    return "".join(f"{digest}  {name}\n" for name, digest in rows)


def write_checksums(paths: Sequence[str], target: str) -> str:
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="ascii", newline="\n") as f:
        f.write(render_checksums(paths))
    return target


def parse_checksums(text: str) -> Dict[str, str]:
    """``{name: sha256}`` from SHA256SUMS text (``*name`` binary marker accepted)."""
    result = {}
    for line in text.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2 and re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]):
            result[parts[1].lstrip("*")] = parts[0].lower()
    return result


def verify_checksums(path: str) -> List[str]:
    """Names in ``path`` whose file (beside it) is missing or differs."""
    folder = os.path.dirname(os.path.abspath(path))
    with open(path, encoding="ascii") as f:
        expected = parse_checksums(f.read())
    bad = []
    for name, digest in expected.items():
        target = os.path.join(folder, name)
        if not os.path.isfile(target) or sha256_of(target) != digest:
            bad.append(name)
    return bad


def write_notes(text: str, target: str) -> str:
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return target


def download_url(repository: str, tag: str, name: str) -> str:
    """Where GitHub serves a release asset (before or without the API's answer)."""
    return f"https://github.com/{repository}/releases/download/{tag}/{name}"


def existing(paths: Sequence[Optional[str]]) -> List[str]:
    return [p for p in paths if p and os.path.isfile(p)]
