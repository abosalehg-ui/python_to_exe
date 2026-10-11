"""Tests for the shared file-system helpers (``core/fsutil``)."""

import hashlib
import os
import sys

import pytest

from py2exe_gui.core import fsutil
from py2exe_gui.core.fsutil import file_size, folder_size, same_path, sha256_of


def test_folder_size_adds_up_files_and_skips_symlinks(tmp_path):
    folder = tmp_path / "d"
    (folder / "sub").mkdir(parents=True)
    (folder / "a.bin").write_bytes(b"x" * 600)
    (folder / "sub" / "b.bin").write_bytes(b"y" * 400)
    if sys.platform != "win32":
        # A symlink to a file inside, and one pointing outside the folder:
        # neither may be counted (shared libraries would count twice).
        os.symlink(folder / "a.bin", folder / "a-link.bin")
        outside = tmp_path / "outside.bin"
        outside.write_bytes(b"z" * 5000)
        os.symlink(outside, folder / "sub" / "out-link.bin")
    assert folder_size(str(folder)) == 1000


def test_folder_size_of_a_single_file_and_of_nothing(tmp_path):
    exe = tmp_path / "app.exe"
    exe.write_bytes(b"MZ" * 50)
    assert folder_size(str(exe)) == 100
    assert folder_size(str(tmp_path / "missing")) == 0
    assert file_size(str(tmp_path / "missing")) == 0


def test_sha256_of_matches_hashlib_across_chunk_boundaries(tmp_path):
    path = tmp_path / "blob"
    data = os.urandom(10_000) + b"tail"
    path.write_bytes(data)
    expected = hashlib.sha256(data).hexdigest()
    assert sha256_of(str(path)) == expected
    # A chunk smaller than the file exercises the loop more than once.
    assert sha256_of(str(path), chunk=1024) == expected
    assert fsutil.HASH_CHUNK == 1024 * 1024


def test_old_names_still_import_the_shared_helpers():
    from py2exe_gui.core import size_analyzer, venv_manager
    from py2exe_gui.core.packagers import appimage, base

    assert size_analyzer.path_size is folder_size
    assert venv_manager.folder_size is folder_size
    assert base.folder_size is folder_size
    assert appimage.sha256_of is sha256_of


@pytest.mark.parametrize("a,b,expected", [
    ("", "x", False),
    ("x", "", False),
    ("a/../b.py", "b.py", True),
    ("b.py", "c.py", False),
])
def test_same_path(a, b, expected):
    assert same_path(a, b) is expected


def test_same_path_is_what_fixes_and_workspace_use():
    from py2exe_gui.core import fixes, workspace

    assert fixes._same_path is same_path
    assert workspace._same_path is same_path
