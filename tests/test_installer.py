"""Tests for the Inno Setup installer generator (core/installer.py)."""

import os

import pytest

from py2exe_gui.core.installer import (
    ARCH_CHOICES,
    BUNDLED_LANGUAGES,
    COMPRESSION_CHOICES,
    InstallerConfig,
    build_iscc_command,
    default_output_basename,
    derive_app_id,
    escape_iss,
    find_iscc,
    generate_iss_script,
    installer_output_path,
    normalize_version,
    resolve_languages,
    validate,
)


@pytest.fixture
def base_config():
    return InstallerConfig(
        enabled=True,
        app_name="My App",
        app_version="2.1.0",
        publisher="Acme Ltd",
    )


@pytest.fixture
def exe_path(tmp_path):
    exe = tmp_path / "dist" / "MyApp.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("binary")
    return str(exe)


# ── AppId ──────────────────────────────────────────────────────────────────


def test_derive_app_id_is_deterministic():
    assert derive_app_id("My App", "Acme") == derive_app_id("My App", "Acme")


def test_derive_app_id_is_case_and_space_insensitive():
    assert derive_app_id("  my app ", "ACME") == derive_app_id("My App", "acme")


def test_derive_app_id_differs_per_app():
    assert derive_app_id("App One", "Acme") != derive_app_id("App Two", "Acme")


def test_derive_app_id_is_braced_guid():
    app_id = derive_app_id("X", "Y")
    assert app_id.startswith("{") and app_id.endswith("}")
    assert len(app_id) == 38  # 36-char GUID + braces


# ── Escaping ───────────────────────────────────────────────────────────────


def test_escape_iss_doubles_braces():
    assert escape_iss("a{b}c") == "a{{b}c"


def test_escape_iss_strips_newlines():
    assert "\n" not in escape_iss("line1\nline2")
    assert escape_iss("line1\nline2") == "line1 line2"


def test_escape_iss_handles_empty():
    assert escape_iss("") == ""


def test_normalize_version_falls_back():
    assert normalize_version("") == "1.0.0"
    assert normalize_version("3.4") == "3.4"


# ── Output naming ──────────────────────────────────────────────────────────


def test_default_output_basename_uses_name_and_version(base_config):
    assert default_output_basename(base_config) == "My-App-2.1.0-setup"


def test_default_output_basename_respects_override(base_config):
    base_config.output_base_filename = "custom-setup"
    assert default_output_basename(base_config) == "custom-setup"


def test_installer_output_path_uses_fallback_dir(base_config):
    path = installer_output_path(base_config, fallback_dir=os.path.join("out", "dist"))
    assert path.endswith("My-App-2.1.0-setup.exe")
    assert "dist" in path


# ── Languages ──────────────────────────────────────────────────────────────


def test_resolve_languages_maps_bundled_codes():
    entries, warnings = resolve_languages(InstallerConfig(languages=["en", "fr"]))
    assert [name for name, _ in entries] == ["en", "fr"]
    assert entries[1][1] == BUNDLED_LANGUAGES["fr"]
    assert warnings == []


def test_resolve_languages_warns_on_arabic_without_isl():
    entries, warnings = resolve_languages(InstallerConfig(languages=["ar", "en"]))
    assert warnings == ["ar"]
    assert [name for name, _ in entries] == ["en"]


def test_resolve_languages_accepts_arabic_with_isl():
    entries, warnings = resolve_languages(
        InstallerConfig(languages=["ar"], arabic_isl_path="C:\\isl\\Arabic.isl")
    )
    assert warnings == []
    assert entries == [("arabic", "C:\\isl\\Arabic.isl")]


def test_resolve_languages_never_returns_empty():
    entries, warnings = resolve_languages(InstallerConfig(languages=["klingon"]))
    assert entries == [("en", BUNDLED_LANGUAGES["en"])]
    assert warnings == ["klingon"]


def test_resolve_languages_deduplicates():
    entries, _ = resolve_languages(InstallerConfig(languages=["en", "EN", "en"]))
    assert len(entries) == 1


# ── Validation ─────────────────────────────────────────────────────────────


def test_validate_rejects_disabled(exe_path):
    assert validate(InstallerConfig(enabled=False), exe_path) is not None


def test_validate_rejects_missing_name(exe_path):
    assert validate(InstallerConfig(enabled=True), exe_path) is not None


def test_validate_rejects_missing_app_path(base_config):
    assert validate(base_config, "") is not None


def test_validate_rejects_bad_extension(base_config, exe_path):
    base_config.associate_extension = "myapp"
    assert validate(base_config, exe_path) is not None


def test_validate_accepts_dotted_extension(base_config, exe_path):
    base_config.associate_extension = ".myapp"
    assert validate(base_config, exe_path) is None


def test_validate_rejects_unknown_privileges(base_config, exe_path):
    base_config.privileges = "root"
    assert validate(base_config, exe_path) is not None


def test_validate_accepts_good_config(base_config, exe_path):
    assert validate(base_config, exe_path) is None


# ── Script generation ──────────────────────────────────────────────────────


def test_script_contains_required_sections(base_config, exe_path):
    script = generate_iss_script(base_config, exe_path)
    for section in ("[Setup]", "[Languages]", "[Files]", "[Icons]"):
        assert section in script


def test_script_embeds_identity(base_config, exe_path):
    script = generate_iss_script(base_config, exe_path)
    assert '#define MyAppName "My App"' in script
    assert '#define MyAppVersion "2.1.0"' in script
    assert "AppPublisher=Acme Ltd" in script


def test_script_uses_derived_app_id_when_blank(base_config, exe_path):
    script = generate_iss_script(base_config, exe_path)
    assert f"AppId={derive_app_id('My App', 'Acme Ltd')}" in script


def test_script_respects_explicit_app_id(base_config, exe_path):
    base_config.app_id = "{11111111-2222-3333-4444-555555555555}"
    script = generate_iss_script(base_config, exe_path)
    assert "AppId={11111111-2222-3333-4444-555555555555}" in script


def test_onefile_packages_single_exe(base_config, exe_path):
    script = generate_iss_script(base_config, exe_path, onefile=True)
    assert f'Source: "{exe_path}"' in script
    assert "recursesubdirs" not in script


def test_onedir_packages_whole_folder(base_config, tmp_path):
    app_dir = tmp_path / "dist" / "MyApp"
    app_dir.mkdir(parents=True)
    script = generate_iss_script(base_config, str(app_dir), onefile=False)
    assert "recursesubdirs createallsubdirs" in script
    assert '#define MyAppExeName "My App.exe"' in script


def test_onedir_honours_explicit_exe_name(base_config, tmp_path):
    app_dir = tmp_path / "dist" / "MyApp"
    app_dir.mkdir(parents=True)
    script = generate_iss_script(
        base_config, str(app_dir), onefile=False, exe_name="launcher.exe"
    )
    assert '#define MyAppExeName "launcher.exe"' in script


def test_desktop_icon_adds_task_and_icon(base_config, exe_path):
    base_config.desktop_icon = True
    script = generate_iss_script(base_config, exe_path)
    assert "[Tasks]" in script
    assert "desktopicon" in script
    assert "{autodesktop}" in script


def test_desktop_icon_disabled_omits_task(base_config, exe_path):
    base_config.desktop_icon = False
    script = generate_iss_script(base_config, exe_path)
    assert "[Tasks]" not in script
    assert "{autodesktop}" not in script


def test_launch_after_install_adds_run_section(base_config, exe_path):
    script = generate_iss_script(base_config, exe_path)
    assert "[Run]" in script
    assert "postinstall" in script


def test_launch_disabled_omits_run_section(base_config, exe_path):
    base_config.launch_after_install = False
    script = generate_iss_script(base_config, exe_path)
    assert "[Run]" not in script


def test_file_association_emits_registry_section(base_config, exe_path):
    base_config.associate_extension = ".myapp"
    script = generate_iss_script(base_config, exe_path)
    assert "[Registry]" in script
    assert "Software\\Classes\\.myapp" in script
    assert "shell\\open\\command" in script


def test_no_association_omits_registry_section(base_config, exe_path):
    script = generate_iss_script(base_config, exe_path)
    assert "[Registry]" not in script


def test_x64_emits_architecture_directives(base_config, exe_path):
    base_config.architecture = "x64"
    script = generate_iss_script(base_config, exe_path)
    assert "ArchitecturesInstallIn64BitMode=x64" in script


def test_x86_omits_architecture_directives(base_config, exe_path):
    base_config.architecture = "x86"
    script = generate_iss_script(base_config, exe_path)
    assert "ArchitecturesAllowed" not in script


def test_privileges_are_emitted(base_config, exe_path):
    base_config.privileges = "lowest"
    script = generate_iss_script(base_config, exe_path)
    assert "PrivilegesRequired=lowest" in script


def test_disable_dir_page_when_change_not_allowed(base_config, exe_path):
    base_config.allow_dir_change = False
    script = generate_iss_script(base_config, exe_path)
    assert "DisableDirPage=yes" in script


def test_license_and_icon_are_wired(base_config, exe_path, tmp_path):
    lic = tmp_path / "LICENSE.txt"
    lic.write_text("x")
    ico = tmp_path / "setup.ico"
    ico.write_text("x")
    base_config.license_file = str(lic)
    base_config.setup_icon_file = str(ico)
    script = generate_iss_script(base_config, exe_path)
    assert f"LicenseFile={lic}" in script
    assert f"SetupIconFile={ico}" in script


def test_sign_installer_declares_signtool(base_config, exe_path):
    base_config.sign_installer = True
    script = generate_iss_script(base_config, exe_path)
    assert "SignTool=byparam" in script


def test_sign_disabled_omits_signtool(base_config, exe_path):
    script = generate_iss_script(base_config, exe_path)
    assert "SignTool" not in script


def test_braces_in_app_name_are_escaped(exe_path):
    config = InstallerConfig(enabled=True, app_name="App {beta}", app_version="1.0")
    script = generate_iss_script(config, exe_path)
    assert '#define MyAppName "App {{beta}"' in script


def test_script_ends_with_newline(base_config, exe_path):
    assert generate_iss_script(base_config, exe_path).endswith("\n")


def test_compression_choice_is_emitted(base_config, exe_path):
    base_config.compression = "zip/9"
    script = generate_iss_script(base_config, exe_path)
    assert "Compression=zip/9" in script


# ── ISCC command ───────────────────────────────────────────────────────────


def test_build_iscc_command_requires_script_path():
    cmd, error = build_iscc_command("", iscc_path="ISCC.exe")
    assert cmd is None
    assert error


def test_build_iscc_command_reports_missing_compiler(monkeypatch, tmp_path):
    monkeypatch.setattr("py2exe_gui.core.installer.find_iscc", lambda: None)
    cmd, error = build_iscc_command(str(tmp_path / "a.iss"))
    assert cmd is None
    assert "ISCC" in error


def test_build_iscc_command_basic(tmp_path):
    iss = str(tmp_path / "a.iss")
    cmd, error = build_iscc_command(iss, iscc_path="ISCC.exe")
    assert error is None
    assert cmd[0] == "ISCC.exe"
    assert cmd[-1] == iss
    assert "/Q" in cmd


def test_build_iscc_command_overrides_output(tmp_path):
    cmd, _ = build_iscc_command(
        str(tmp_path / "a.iss"),
        iscc_path="ISCC.exe",
        output_dir="C:\\out",
        output_basename="setup",
    )
    assert "/OC:\\out" in cmd
    assert "/Fsetup" in cmd


def test_build_iscc_command_wires_sign_parameter(tmp_path):
    cmd, _ = build_iscc_command(
        str(tmp_path / "a.iss"),
        iscc_path="ISCC.exe",
        sign_command=["signtool", "sign", "/f", "C:\\my certs\\c.pfx"],
    )
    sign_arg = next(a for a in cmd if a.startswith("/Sbyparam="))
    assert sign_arg.endswith("$f")
    assert "$qC:\\my certs\\c.pfx$q" in sign_arg


def test_build_iscc_command_quiet_can_be_disabled(tmp_path):
    cmd, _ = build_iscc_command(str(tmp_path / "a.iss"), iscc_path="ISCC.exe", quiet=False)
    assert "/Q" not in cmd


# ── Compiler discovery ─────────────────────────────────────────────────────


def test_find_iscc_prefers_env_var(tmp_path, monkeypatch):
    fake = tmp_path / "ISCC.exe"
    fake.write_text("x")
    monkeypatch.setattr("shutil.which", lambda _n: None)
    assert find_iscc({"INNO_SETUP_ISCC": str(fake)}) == str(fake)


def test_find_iscc_ignores_env_var_pointing_nowhere(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _n: None)
    monkeypatch.setattr("os.path.isfile", lambda _p: False)
    assert find_iscc({"INNO_SETUP_ISCC": "/nope/ISCC.exe"}) is None


def test_find_iscc_falls_back_to_path(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda n: "/usr/bin/iscc" if n == "ISCC" else None)
    assert find_iscc({}) == "/usr/bin/iscc"


# ── Config round-trip ──────────────────────────────────────────────────────


def test_config_round_trips(base_config):
    base_config.languages = ["en", "ar"]
    base_config.associate_extension = ".myapp"
    restored = InstallerConfig.from_dict(base_config.to_dict())
    assert restored == base_config


def test_config_from_dict_tolerates_missing_keys():
    restored = InstallerConfig.from_dict({})
    assert restored.app_version == "1.0.0"
    assert restored.languages == ["en"]


def test_config_from_dict_tolerates_scalar_languages():
    restored = InstallerConfig.from_dict({"languages": "fr"})
    assert restored.languages == ["fr"]


def test_choice_tuples_are_non_empty():
    assert COMPRESSION_CHOICES and ARCH_CHOICES
