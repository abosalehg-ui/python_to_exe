"""Semantic versions, bumps, and the one version applied everywhere."""

import pytest

from py2exe_gui.core.project_file import ProjectConfig
from py2exe_gui.core.release.versioning import (
    SemVer,
    apply_version,
    bump,
    is_semver,
    normalize,
    parse_semver,
    tag_for,
    version_mismatches,
    windows_version,
)


@pytest.mark.parametrize("text", ["0.0.0", "1.2.3", "10.20.30", "1.0.0-alpha", "1.0.0-rc.1",
                                  "1.0.0-0.3.7", "1.0.0-x.7.z.92", "1.0.0+20130313144700",
                                  "1.0.0-beta+exp.sha.5114f85", "v1.2.3", " 1.2.3 "])
def test_valid_versions(text):
    assert is_semver(text)


@pytest.mark.parametrize("text", ["", "1", "1.2", "1.2.3.4", "01.2.3", "1.02.3", "1.2.3-",
                                  "1.2.3-01", "1.2.3+", "a.b.c", "1.2.3 beta", "vv1.2.3",
                                  "1.2.3-ب", "١.٢.٣"])
def test_invalid_versions(text):
    assert not is_semver(text)
    with pytest.raises(ValueError):
        parse_semver(text)


def test_parse_parts_and_str():
    v = parse_semver("v1.2.3-rc.1+build.5")
    assert v == SemVer(1, 2, 3, "rc.1", "build.5")
    assert str(v) == "1.2.3-rc.1+build.5"
    assert v.core == (1, 2, 3)
    assert normalize("V2.0.0") == "2.0.0"
    assert normalize("version") == "version"


@pytest.mark.parametrize("version,part,expected", [
    ("1.2.3", "patch", "1.2.4"),
    ("1.2.3", "minor", "1.3.0"),
    ("1.2.3", "major", "2.0.0"),
    ("1.2.3-rc.1", "patch", "1.2.3"),
    ("1.2.3-rc.1", "minor", "1.3.0"),
    ("0.9.9+meta", "patch", "0.9.10"),
])
def test_bump(version, part, expected):
    assert bump(version, part) == expected


def test_bump_rejects_unknown_part_and_bad_version():
    with pytest.raises(ValueError):
        bump("1.2.3", "build")
    with pytest.raises(ValueError):
        bump("nope", "patch")


def test_windows_version_and_tag():
    assert windows_version("1.2.3") == "1.2.3.0"
    assert windows_version("1.2.3-rc.1+x") == "1.2.3.0"
    assert tag_for("1.2.3") == "v1.2.3"
    assert tag_for("v1.2.3", "release-") == "release-1.2.3"


def test_apply_version_updates_every_field_together():
    project = ProjectConfig(version="1.0.0")
    project.installer.app_version = "0.9"
    project.version_info.file_version = "0.9.0.0"
    changes = apply_version(project, "1.1.0")
    assert project.version == "1.1.0"
    assert project.version_info.file_version == "1.1.0.0"
    assert project.version_info.product_version == "1.1.0.0"
    assert project.installer.app_version == "1.1.0"
    assert project.build.runtime_kit.app_version == "1.1.0"
    assert {c.field for c in changes} == {
        "project.version", "version_info.file_version", "version_info.product_version",
        "installer.app_version", "runtime_kit.app_version"}
    assert version_mismatches(project) == []


def test_apply_version_is_idempotent():
    project = ProjectConfig()
    apply_version(project, "v2.0.0")
    assert project.version == "2.0.0"
    assert apply_version(project, "2.0.0") == []


def test_apply_version_refuses_a_bad_version_without_touching_anything():
    project = ProjectConfig(version="1.0.0")
    with pytest.raises(ValueError):
        apply_version(project, "2.0")
    assert project.version == "1.0.0"


def test_mismatches_report_the_drift_between_tabs():
    project = ProjectConfig(version="1.2.0")
    project.installer.app_version = "1.1.0"
    project.version_info.product_version = "1.2.0.0"
    found = {c.field: c.old for c in version_mismatches(project)}
    assert found == {"installer.app_version": "1.1.0"}
    # Empty Version Info / Runtime Kit fields are unused, not mismatched.
    assert "version_info.file_version" not in found
    assert version_mismatches(ProjectConfig(version="")) == []
