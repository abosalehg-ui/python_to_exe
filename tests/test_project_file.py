"""The project file: model, TOML round trip, paths, schema, and what it refuses."""

import json
import ntpath
import os
import posixpath
import sys

import pytest

from py2exe_gui.core import project_file as pf
from py2exe_gui.core.config import BuildConfig, RuntimeKitConfig
from py2exe_gui.core.installer import InstallerConfig
from py2exe_gui.core.project_file import (
    PROJECT_FILE_NAME,
    ProjectConfig,
    ProjectFileError,
    dumps_project,
    load_project,
    loads_project,
    new_project_for_script,
    project_path_for_script,
    resolve_path,
    save_project,
    sections_in,
    to_portable_path,
    untrusted_flags,
)
from py2exe_gui.core.version_info import VersionInfo

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    tomllib = pytest.importorskip("tomli")


def full_project(root: str) -> ProjectConfig:
    """A project with every section filled, Arabic text and paths included."""
    p = ProjectConfig(name="محوّل", version="2.3.4")
    p.build = BuildConfig(
        source=os.path.join(root, "src", "app.py"),
        output_name="MyApp",
        output_dir=os.path.join(root, "out"),
        icon=os.path.join(root, "assets", "icon.ico"),
        onefile=False, windowed=True, strip=True,
        extra_files=[os.path.join(root, "data"), os.path.join(root, "config.json")],
        hidden_imports=["PIL._tkinter_finder", "yaml"],
        optimize=2, upx=True, upx_dir="", extra_args='--collect-all "my pkg"',
        splash_image=os.path.join(root, "splash.png"), isolated_env=True,
        runtime_kit=RuntimeKitConfig(resource_path=True, crash_reporter=True,
                                     support_url="https://example.com/دعم",
                                     app_version="2.3.4"),
    )
    p.version_info = VersionInfo(company_name="شركة \"المثال\"", file_description="تطبيق",
                                 file_version="2.3.4.0", product_version="2.3.4.0",
                                 legal_copyright="© 2026\nكل الحقوق")
    p.manifest = pf.ManifestSettings(enabled=True, dpi_aware=True, supported_os=["10", "11"])
    p.installer = InstallerConfig(enabled=True, app_name="MyApp", app_version="2.3.4",
                                  publisher="Me", languages=["ar", "en"],
                                  license_file=os.path.join(root, "LICENSE.txt"),
                                  arabic_isl_path=os.path.join(root, "Arabic.isl"))
    p.signing = pf.SigningSettings(enabled=True, cert_path=os.path.join(root, "cert.pfx"),
                                   description="توقيع")
    p.release = pf.ReleaseSettings(repository="me/app", prerelease=True)
    p.release.assets.portable_zip = False
    p.release.winget = pf.WingetSettings(enabled=True, identifier="Me.App", license="MIT")
    return p


# ── Round trip ────────────────────────────────────────────────────────────


def test_round_trip_keeps_every_field(tmp_path):
    original = full_project(str(tmp_path))
    path = save_project(original, str(tmp_path / PROJECT_FILE_NAME))
    loaded = load_project(path)
    assert loaded.warnings == []
    # Fields deliberately not stored: generated per build.
    assert loaded.project == original


def test_saved_file_is_valid_toml_with_relative_forward_slash_paths(tmp_path):
    path = save_project(full_project(str(tmp_path)), str(tmp_path / "p2e.toml"))
    with open(path, encoding="utf-8") as f:
        text = f.read()
    data = tomllib.loads(text)
    assert data["schema"] == pf.SCHEMA_VERSION
    assert data["build"]["source"] == "src/app.py"
    assert data["build"]["extra_files"] == ["data", "config.json"]
    assert data["installer"]["license_file"] == "LICENSE.txt"
    assert data["signing"]["cert_path"] == "cert.pfx"
    assert str(tmp_path) not in text
    assert "محوّل" in text  # Arabic written as text, not escaped


def test_moving_the_project_folder_moves_the_paths(tmp_path):
    a = tmp_path / "a"
    a.mkdir()
    save_project(full_project(str(a)), str(a / "p2e.toml"))
    moved = tmp_path / "moved"
    os.rename(a, moved)
    project = load_project(str(moved / "p2e.toml")).project
    assert project.build.source == os.path.join(str(moved), "src", "app.py")
    assert project.build.icon == os.path.join(str(moved), "assets", "icon.ico")


def test_not_stored_fields_are_dropped_with_a_warning(tmp_path):
    project = ProjectConfig(build=BuildConfig(source=str(tmp_path / "a.py"),
                                              version_file="/tmp/v.txt"))
    text = dumps_project(project, str(tmp_path))
    assert "version_file" not in text and "manifest_file" not in text
    _, warnings = loads_project(text.replace("[build]\n", "[build]\nversion_file = \"x\"\n"),
                                str(tmp_path))
    assert any("version_file" in w for w in warnings)


# ── Paths ─────────────────────────────────────────────────────────────────


def test_windows_paths_relative_and_back():
    base = r"C:\Users\me\proj"
    rel = to_portable_path(r"C:\Users\me\proj\assets\icon.ico", base, ntpath)
    assert rel == "assets/icon.ico"
    assert resolve_path(rel, base, ntpath) == r"C:\Users\me\proj\assets\icon.ico"
    up = to_portable_path(r"C:\Users\me\shared\lib.dll", base, ntpath)
    assert up == "../shared/lib.dll"
    assert resolve_path(up, base, ntpath) == r"C:\Users\me\shared\lib.dll"


def test_windows_path_on_another_drive_stays_absolute():
    base = r"C:\proj"
    assert to_portable_path(r"D:\certs\me.pfx", base, ntpath) == r"D:\certs\me.pfx"
    assert resolve_path(r"D:\certs\me.pfx", base, ntpath) == r"D:\certs\me.pfx"


def test_windows_project_round_trip_through_toml():
    base = r"C:\Users\مستخدم\مشروع"
    project = ProjectConfig(build=BuildConfig(
        source=base + r"\main.py", icon=base + r"\res\app.ico",
        extra_files=[base + r"\data", r"E:\shared\fonts"]))
    text = dumps_project(project, base, ntpath)
    assert 'source = "main.py"' in text
    assert 'icon = "res/app.ico"' in text
    assert '"E:\\\\shared\\\\fonts"' in text  # backslashes escaped in TOML
    loaded, _ = loads_project(text, base, ntpath)
    assert loaded.build.source == base + r"\main.py"
    assert loaded.build.extra_files == [base + r"\data", r"E:\shared\fonts"]


def test_posix_relative_paths_and_empties():
    assert to_portable_path("", "/p") == ""
    assert resolve_path("", "/p") == ""
    assert to_portable_path("already/relative", "/p", posixpath) == "already/relative"
    assert to_portable_path("win\\style", "/p", posixpath) == "win/style"
    assert resolve_path("a/../b/c.py", "/p", posixpath) == "/p/b/c.py"
    assert resolve_path("/abs/x", "/p", posixpath) == "/abs/x"


# ── Schema and migrations ─────────────────────────────────────────────────


def test_missing_newer_and_invalid_schema(tmp_path):
    with pytest.raises(ProjectFileError) as e:
        loads_project('[project]\nname = "x"\n', str(tmp_path))
    assert e.value.code == "schema_missing"
    with pytest.raises(ProjectFileError) as e:
        loads_project(f"schema = {pf.SCHEMA_VERSION + 1}\n", str(tmp_path))
    assert e.value.code == "schema_newer"
    for bad in ('"1"', "0", "true", "1.0"):
        with pytest.raises(ProjectFileError) as e:
            loads_project(f"schema = {bad}\n", str(tmp_path))
        assert e.value.code == "schema_invalid"


def test_migration_chain_runs_in_order(tmp_path, monkeypatch):
    calls = []

    def one_to_two(data):
        calls.append(1)
        data["build"] = dict(data.get("build", {}))
        data["build"]["output_name"] = data.pop("old_name", "")
        return data

    def two_to_three(data):
        calls.append(2)
        data["project"] = {"name": "migrated", "version": "3.0.0"}
        return data

    monkeypatch.setattr(pf, "SCHEMA_VERSION", 3)
    monkeypatch.setattr(pf, "MIGRATIONS", {1: one_to_two, 2: two_to_three})
    project, warnings = loads_project('schema = 1\nold_name = "Legacy"\n', str(tmp_path))
    assert calls == [1, 2]
    assert project.build.output_name == "Legacy"
    assert project.name == "migrated" and project.version == "3.0.0"
    assert warnings == []


def test_a_gap_in_the_migration_chain_is_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(pf, "SCHEMA_VERSION", 2)
    monkeypatch.setattr(pf, "MIGRATIONS", {})
    with pytest.raises(ProjectFileError) as e:
        loads_project("schema = 1\n", str(tmp_path))
    assert e.value.code == "schema_invalid"


def test_syntax_errors_and_unreadable_files(tmp_path):
    with pytest.raises(ProjectFileError) as e:
        loads_project("schema = = 1", str(tmp_path))
    assert e.value.code == "syntax"
    with pytest.raises(ProjectFileError) as e:
        load_project(str(tmp_path / "missing.toml"))
    assert e.value.code == "unreadable"
    bad = tmp_path / "latin1.toml"
    bad.write_bytes("schema = 1\nname = \"\xe9\"\n".encode("latin-1"))
    with pytest.raises(ProjectFileError) as e:
        load_project(str(bad))
    assert e.value.code == "syntax"


# ── Strict types, unknown keys ────────────────────────────────────────────


def test_wrong_types_are_dropped_and_reported(tmp_path):
    text = (
        "schema = 1\n[build]\nonefile = \"yes\"\noptimize = true\nhidden_imports = [1, 2]\n"
        "windowed = true\n[installer]\nlanguages = \"ar\"\n[release]\nassets = 5\n"
    )
    project, warnings = loads_project(text, str(tmp_path))
    assert project.build.onefile is True  # default kept
    assert project.build.optimize == 0
    assert project.build.hidden_imports == []
    assert project.build.windowed is True
    assert project.installer.languages == ["en"]
    assert len(warnings) == 5


def test_unknown_keys_and_sections_are_reported_not_applied(tmp_path):
    project, warnings = loads_project(
        "schema = 1\nextra = 1\n[build]\nfavourite_colour = \"blue\"\n[plugins]\nx = 1\n",
        str(tmp_path))
    assert project == ProjectConfig()
    assert len(warnings) == 3


def test_non_table_sections(tmp_path):
    project, warnings = loads_project('schema = 1\nbuild = "nope"\n', str(tmp_path))
    assert project.build == BuildConfig()
    assert any("expected a table" in w for w in warnings)
    with pytest.raises(ProjectFileError) as e:
        pf.project_from_document(["not", "a", "table"], str(tmp_path))
    assert e.value.code == "not_a_table"


# ── Security: secrets and executables ─────────────────────────────────────


@pytest.mark.parametrize("snippet", [
    '[signing]\ncert_password = "hunter2"\n',
    '[signing]\npassword = "x"\n',
    '[release]\ngithub_token = "x"\n',
    '[release]\ntoken = "x"\n',
    '[release.winget]\napi_key = "x"\n',
    '[runtime_kit]\nupdate_private_key = "00"\n',
    '[secrets]\nanything = "x"\n',
    'Client-Secret = "x"\n',
])
def test_a_project_file_cannot_hold_a_password_or_token(tmp_path, snippet):
    with pytest.raises(ProjectFileError) as e:
        loads_project("schema = 1\n" + snippet, str(tmp_path))
    assert e.value.code == "forbidden_secret"


@pytest.mark.parametrize("snippet", [
    '[build]\npython = "C:/evil/python.exe"\n',
    '[build]\npython_executable = "/tmp/x"\n',
    '[build]\ninterpreter = "/tmp/x"\n',
    '[build]\nbase_python = "/tmp/x"\n',
    '[signing]\nsigntool_path = "C:/evil/signtool.exe"\n',
    '[installer]\niscc_path = "C:/evil/ISCC.exe"\n',
    'python = "/usr/bin/python3"\n',
])
def test_a_project_file_cannot_name_an_interpreter_or_tool(tmp_path, snippet):
    with pytest.raises(ProjectFileError) as e:
        loads_project("schema = 1\n" + snippet, str(tmp_path))
    assert e.value.code == "forbidden_executable"


@pytest.mark.parametrize("value", [
    "ghp_" + "a" * 36,
    "github_pat_" + "B" * 30,
    "gho_" + "1" * 36,
    "-----BEGIN OPENSSH PRIVATE KEY-----",
])
def test_token_looking_values_are_refused_anywhere(tmp_path, value):
    for snippet in (f'[release]\nrepository = "{value}"\n',
                    f'[build]\nhidden_imports = ["ok", "{value}"]\n',
                    f'[build]\nextra_args = "--x {value}"\n'):
        with pytest.raises(ProjectFileError) as e:
            loads_project("schema = 1\n" + snippet, str(tmp_path))
        assert e.value.code == "secret_value"


def test_the_model_has_no_field_for_a_secret_or_an_executable():
    doc = pf.project_to_document(full_project("/p"), "/p")
    pf.check_untrusted_content(doc)  # does not raise

    def keys(data):
        for key, value in data.items():
            yield key
            if isinstance(value, dict):
                yield from keys(value)

    assert not [k for k in keys(doc) if pf.forbidden_key(k)]


def test_saving_never_writes_the_signing_password(tmp_path):
    project = full_project(str(tmp_path))
    config = project.signing.signing_config(password="s3cret-pass", signtool_path="/x/signtool")
    assert config.cert_password == "s3cret-pass"
    project.signing = pf.SigningSettings.from_signing_config(config)
    path = save_project(project, str(tmp_path / "p2e.toml"))
    text = open(path, encoding="utf-8").read()
    assert "s3cret-pass" not in text and "/x/signtool" not in text


def test_store_mode_never_passes_a_password():
    settings = pf.SigningSettings(enabled=True, use_cert_store=True, cert_subject="Me")
    assert settings.signing_config(password="leak").cert_password == ""


def test_untrusted_flags_include_extra_args_and_upx_dir():
    assert untrusted_flags(BuildConfig()) == []
    assert untrusted_flags(BuildConfig(extra_args="--runtime-hook=x.py")) == ["--runtime-hook"]
    assert untrusted_flags(BuildConfig(upx=True, upx_dir="/tmp/evil")) == ["--upx-dir"]
    # UPX off: the folder is never used.
    assert untrusted_flags(BuildConfig(upx=False, upx_dir="/tmp/evil")) == []
    both = BuildConfig(upx=True, upx_dir="/x", extra_args="--upx-dir /y")
    assert untrusted_flags(both) == ["--upx-dir"]


# ── JSON form: settings files, presets, history ───────────────────────────


def test_settings_dict_is_a_superset_of_the_legacy_build_dict(tmp_path):
    project = full_project(str(tmp_path))
    data = project.to_settings_dict()
    legacy = project.build.to_dict()
    assert {k: data[k] for k in legacy} == legacy
    # An older app reading the new JSON still gets the build.
    assert BuildConfig.from_dict(json.loads(json.dumps(data))) == project.build
    assert ProjectConfig.from_settings_dict(json.loads(json.dumps(data))) == project


def test_pre_1_6_settings_files_still_load():
    legacy = {"source": "/p/app.py", "output_name": "Old", "onefile": False,
              "hidden_imports": ["yaml"], "upx_level": 5, "isolated_env": True,
              "runtime_kit": {"crash_reporter": True}}
    project = ProjectConfig.from_settings_dict(legacy)
    assert project.build == BuildConfig.from_dict(legacy)
    assert project.installer == InstallerConfig()
    assert sections_in(legacy) == []
    assert sections_in(project.to_settings_dict()) == list(pf.SECTIONS)
    assert sections_in("nope") == []
    with pytest.raises(ValueError):
        ProjectConfig.from_settings_dict(["not", "a", "dict"])


def test_settings_dict_ignores_secret_keys_it_does_not_model():
    data = ProjectConfig().to_settings_dict()
    data["signing"]["cert_password"] = "leak"
    data["project"] = {"name": 5, "version": "1.0.0"}
    project = ProjectConfig.from_settings_dict(data)
    assert "leak" not in json.dumps(project.to_settings_dict())
    assert project.name == "" and project.version == "1.0.0"


# ── New project from a script ─────────────────────────────────────────────


def test_new_project_for_script_aligns_every_version(tmp_path):
    script = tmp_path / "tool.py"
    script.write_text("print(1)\n")
    project = new_project_for_script(str(script))
    assert project.build.source == str(script)
    assert project.build.output_name == "tool" and project.name == "tool"
    assert project.version == "1.0.0"
    assert project.version_info.file_version == "1.0.0.0"
    assert project.installer.app_version == "1.0.0"
    assert project_path_for_script(str(script)) == str(tmp_path / "p2e.toml")


def test_new_project_keeps_the_settings_it_starts_from(tmp_path):
    base = full_project(str(tmp_path))
    project = new_project_for_script(str(tmp_path / "other.py"), base, version="5.0.0")
    assert project.build.hidden_imports == base.build.hidden_imports
    assert project.build.output_name == "MyApp" and project.name == "محوّل"
    assert project.version == "5.0.0"
    assert base.version == "2.3.4"  # the source is not modified


def test_display_name_fallbacks():
    assert ProjectConfig().display_name() == ""
    assert ProjectConfig(build=BuildConfig(source="/x/run.py")).display_name() == "run"
    assert ProjectConfig(build=BuildConfig(source="/x/run.py", output_name="R")).display_name() == "R"
    assert ProjectConfig(name="N").display_name() == "N"


def test_manifest_settings_build_a_manifest_config():
    cfg = pf.ManifestSettings(dpi_aware=True, supported_os=["10"]).manifest_config("", "", "d")
    assert cfg.name == "MyApp" and cfg.version == "1.0.0.0" and cfg.dpi_aware


def test_save_is_atomic_and_creates_folders(tmp_path):
    target = tmp_path / "deep" / "er" / "p2e.toml"
    save_project(ProjectConfig(name="x"), str(target))
    assert target.is_file()
    assert not (tmp_path / "deep" / "er" / "p2e.toml.tmp").exists()
