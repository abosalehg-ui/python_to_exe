"""Pure logic: turn an InstallerConfig into an Inno Setup (.iss) script.

This module is deliberately UI-free and (almost) filesystem-free so it stays
testable. Actually running ISCC.exe is delegated to the UI layer, mirroring
how ``code_signer`` delegates running ``signtool``.

Reference: https://jrsoftware.org/ishelp/
"""

import os
import shutil
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ── Languages ──────────────────────────────────────────────────────────────
# Only languages that ship with Inno Setup 6 are listed here. Arabic is NOT
# bundled with Inno Setup — it exists only as an unofficial translation — so
# it is handled separately through ``arabic_isl_path``.
BUNDLED_LANGUAGES: Dict[str, str] = {
    "en": "compiler:Default.isl",
    "fr": "compiler:Languages\\French.isl",
    "de": "compiler:Languages\\German.isl",
    "es": "compiler:Languages\\Spanish.isl",
    "it": "compiler:Languages\\Italian.isl",
    "nl": "compiler:Languages\\Dutch.isl",
    "pt_br": "compiler:Languages\\BrazilianPortuguese.isl",
    "ru": "compiler:Languages\\Russian.isl",
    "tr": "compiler:Languages\\Turkish.isl",
    "he": "compiler:Languages\\Hebrew.isl",
    "ja": "compiler:Languages\\Japanese.isl",
    "pl": "compiler:Languages\\Polish.isl",
    "uk": "compiler:Languages\\Ukrainian.isl",
}

# Display names for the language picker (English identifiers keep the data
# layer locale-independent; the UI can translate them if it wants to).
LANGUAGE_LABELS: Dict[str, str] = {
    "en": "English",
    "fr": "Français",
    "de": "Deutsch",
    "es": "Español",
    "it": "Italiano",
    "nl": "Nederlands",
    "pt_br": "Português (Brasil)",
    "ru": "Русский",
    "tr": "Türkçe",
    "he": "עברית",
    "ja": "日本語",
    "pl": "Polski",
    "uk": "Українська",
}

# Namespace used to derive a stable AppId from (publisher, app name). Keeping
# the AppId stable across builds is what makes Inno Setup treat a new setup as
# an *upgrade* of an existing install rather than a second parallel install.
_APPID_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

COMPRESSION_CHOICES = ("lzma2/max", "lzma2/ultra64", "lzma2/normal", "zip/9", "none")
ARCH_CHOICES = ("x64", "x86", "any")
PRIVILEGE_CHOICES = ("admin", "lowest")


@dataclass
class InstallerConfig:
    """Everything needed to emit an Inno Setup script for a built app."""

    enabled: bool = False

    # Identity
    app_name: str = ""
    app_version: str = "1.0.0"
    publisher: str = ""
    publisher_url: str = ""
    support_url: str = ""
    app_id: str = ""  # empty → derived deterministically from name+publisher

    # Output
    output_dir: str = ""  # where Setup.exe lands; empty → alongside the app
    output_base_filename: str = ""  # empty → "<app_name>-<version>-setup"

    # Wizard assets
    license_file: str = ""
    readme_file: str = ""
    setup_icon_file: str = ""

    # Behaviour
    languages: List[str] = field(default_factory=lambda: ["en"])
    arabic_isl_path: str = ""  # unofficial Arabic.isl, supplied by the user
    privileges: str = "admin"  # "admin" | "lowest"
    architecture: str = "x64"  # "x64" | "x86" | "any"
    compression: str = "lzma2/max"

    desktop_icon: bool = True
    launch_after_install: bool = True
    allow_dir_change: bool = True
    create_uninstall_icon: bool = True

    # Optional file association, e.g. ".myapp"
    associate_extension: str = ""

    # Sign the produced Setup.exe with the same signtool command used for the
    # EXE. When True the script declares `SignTool=byparam` and ISCC must be
    # invoked with a matching /Sbyparam=... argument.
    sign_installer: bool = False

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "app_name": self.app_name,
            "app_version": self.app_version,
            "publisher": self.publisher,
            "publisher_url": self.publisher_url,
            "support_url": self.support_url,
            "app_id": self.app_id,
            "output_dir": self.output_dir,
            "output_base_filename": self.output_base_filename,
            "license_file": self.license_file,
            "readme_file": self.readme_file,
            "setup_icon_file": self.setup_icon_file,
            "languages": list(self.languages),
            "arabic_isl_path": self.arabic_isl_path,
            "privileges": self.privileges,
            "architecture": self.architecture,
            "compression": self.compression,
            "desktop_icon": self.desktop_icon,
            "launch_after_install": self.launch_after_install,
            "allow_dir_change": self.allow_dir_change,
            "create_uninstall_icon": self.create_uninstall_icon,
            "associate_extension": self.associate_extension,
            "sign_installer": self.sign_installer,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InstallerConfig":
        defaults = cls()
        languages = data.get("languages", defaults.languages)
        if isinstance(languages, str):  # tolerate hand-edited JSON
            languages = [languages]
        return cls(
            enabled=bool(data.get("enabled", defaults.enabled)),
            app_name=str(data.get("app_name", defaults.app_name)),
            app_version=str(data.get("app_version", defaults.app_version)),
            publisher=str(data.get("publisher", defaults.publisher)),
            publisher_url=str(data.get("publisher_url", defaults.publisher_url)),
            support_url=str(data.get("support_url", defaults.support_url)),
            app_id=str(data.get("app_id", defaults.app_id)),
            output_dir=str(data.get("output_dir", defaults.output_dir)),
            output_base_filename=str(
                data.get("output_base_filename", defaults.output_base_filename)
            ),
            license_file=str(data.get("license_file", defaults.license_file)),
            readme_file=str(data.get("readme_file", defaults.readme_file)),
            setup_icon_file=str(data.get("setup_icon_file", defaults.setup_icon_file)),
            languages=[str(x) for x in languages],
            arabic_isl_path=str(data.get("arabic_isl_path", defaults.arabic_isl_path)),
            privileges=str(data.get("privileges", defaults.privileges)),
            architecture=str(data.get("architecture", defaults.architecture)),
            compression=str(data.get("compression", defaults.compression)),
            desktop_icon=bool(data.get("desktop_icon", defaults.desktop_icon)),
            launch_after_install=bool(
                data.get("launch_after_install", defaults.launch_after_install)
            ),
            allow_dir_change=bool(data.get("allow_dir_change", defaults.allow_dir_change)),
            create_uninstall_icon=bool(
                data.get("create_uninstall_icon", defaults.create_uninstall_icon)
            ),
            associate_extension=str(
                data.get("associate_extension", defaults.associate_extension)
            ),
            sign_installer=bool(data.get("sign_installer", defaults.sign_installer)),
        )


# ── Helpers ────────────────────────────────────────────────────────────────


def derive_app_id(app_name: str, publisher: str = "") -> str:
    """Return a deterministic ``{GUID}`` for (publisher, app_name).

    Deterministic on purpose: the same app always gets the same AppId, so a
    newer Setup.exe upgrades the previous install in place instead of
    installing side by side.
    """
    key = f"{publisher.strip().lower()}|{app_name.strip().lower()}"
    return "{" + str(uuid.uuid5(_APPID_NAMESPACE, key)).upper() + "}"


def escape_iss(value: str) -> str:
    """Escape a string for use as an Inno Setup directive/parameter value.

    ``{`` starts a constant in Inno Setup, so a literal brace must be doubled.
    Newlines are stripped because directives are line-based.
    """
    if not value:
        return ""
    text = str(value).replace("{", "{{")
    return text.replace("\r", " ").replace("\n", " ").strip()


def normalize_version(version: str) -> str:
    """Inno Setup's AppVersion is a free-form string; just make it non-empty."""
    cleaned = escape_iss(version)
    return cleaned or "1.0.0"


def default_output_basename(config: "InstallerConfig") -> str:
    """Setup filename without extension."""
    if config.output_base_filename:
        return escape_iss(config.output_base_filename)
    name = (config.app_name or "app").replace(" ", "-")
    return escape_iss(f"{name}-{normalize_version(config.app_version)}-setup")


def resolve_languages(config: "InstallerConfig") -> Tuple[List[Tuple[str, str]], List[str]]:
    """Return (entries, warnings).

    ``entries`` is a list of (language_name, messages_file) suitable for the
    ``[Languages]`` section. ``warnings`` lists requested languages that could
    not be resolved, so the caller can surface them instead of letting ISCC
    fail with a cryptic "file not found".
    """
    entries: List[Tuple[str, str]] = []
    warnings: List[str] = []
    seen = set()

    for code in config.languages:
        key = str(code).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        if key == "ar":
            if config.arabic_isl_path:
                entries.append(("arabic", config.arabic_isl_path))
            else:
                warnings.append("ar")
            continue
        isl = BUNDLED_LANGUAGES.get(key)
        if isl:
            entries.append((key, isl))
        else:
            warnings.append(key)

    if not entries:
        # Never emit an empty [Languages] section — Inno Setup requires one.
        entries.append(("en", BUNDLED_LANGUAGES["en"]))
    return entries, warnings


def _arch_directives(architecture: str) -> List[str]:
    """Architecture directives for Inno Setup 6.

    Uses the plain ``x64`` identifier rather than ``x64compatible``: the latter
    only exists in Inno Setup 6.3+, while ``x64`` is accepted (deprecated but
    functional) across the whole 6.x line.
    """
    arch = (architecture or "x64").lower()
    if arch == "x64":
        return [
            "ArchitecturesAllowed=x64",
            "ArchitecturesInstallIn64BitMode=x64",
        ]
    if arch == "x86":
        # 32-bit setup: runs everywhere, installs into Program Files (x86).
        return []
    return []  # "any"


def validate(config: "InstallerConfig", app_path: str) -> Optional[str]:
    """Return a user-facing error message, or None when the config is usable."""
    if not config.enabled:
        return "Installer generation is disabled"
    if not config.app_name.strip():
        return "Application name is required"
    if not app_path:
        return "Built application path is required"
    if config.privileges not in PRIVILEGE_CHOICES:
        return f"Unknown privileges value: {config.privileges}"
    if config.architecture not in ARCH_CHOICES:
        return f"Unknown architecture value: {config.architecture}"
    ext = config.associate_extension.strip()
    if ext and not ext.startswith("."):
        return "File association must start with a dot (e.g. .myapp)"
    return None


# ── Script generation ──────────────────────────────────────────────────────


def generate_iss_script(
    config: "InstallerConfig",
    app_path: str,
    onefile: bool = True,
    exe_name: str = "",
) -> str:
    """Return the full contents of an Inno Setup ``.iss`` script.

    ``app_path`` is the PyInstaller output: the ``.exe`` itself when
    ``onefile`` is True, otherwise the one-dir folder containing it.
    ``exe_name`` overrides the launcher filename (defaults to the basename of
    ``app_path`` for onefile, or ``<app_name>.exe`` for onedir).
    """
    app_name = escape_iss(config.app_name or "MyApp")
    version = normalize_version(config.app_version)
    publisher = escape_iss(config.publisher)
    app_id = config.app_id.strip() or derive_app_id(config.app_name, config.publisher)

    if exe_name:
        launcher = escape_iss(exe_name)
    elif onefile:
        launcher = escape_iss(os.path.basename(app_path))
    else:
        launcher = escape_iss(f"{config.app_name or 'MyApp'}.exe")

    out_dir = config.output_dir or (
        os.path.dirname(app_path) if onefile else os.path.dirname(app_path.rstrip("\\/"))
    )

    lines: List[str] = [
        "; ─────────────────────────────────────────────────────────────",
        "; Inno Setup script generated by Python to EXE Converter",
        f"; Application: {app_name} {version}",
        "; ─────────────────────────────────────────────────────────────",
        "",
        f'#define MyAppName "{app_name}"',
        f'#define MyAppVersion "{version}"',
        f'#define MyAppExeName "{launcher}"',
        "",
        "[Setup]",
        f"AppId={app_id}",
        "AppName={#MyAppName}",
        "AppVersion={#MyAppVersion}",
        "AppVerName={#MyAppName} {#MyAppVersion}",
    ]

    if publisher:
        lines.append(f"AppPublisher={publisher}")
    if config.publisher_url:
        lines.append(f"AppPublisherURL={escape_iss(config.publisher_url)}")
    if config.support_url:
        lines.append(f"AppSupportURL={escape_iss(config.support_url)}")

    lines.extend(
        [
            "DefaultDirName={autopf}\\{#MyAppName}",
            "DefaultGroupName={#MyAppName}",
            f"OutputDir={escape_iss(out_dir)}",
            f"OutputBaseFilename={default_output_basename(config)}",
            f"Compression={escape_iss(config.compression or 'lzma2/max')}",
            "SolidCompression=yes",
            "WizardStyle=modern",
            f"PrivilegesRequired={config.privileges}",
        ]
    )

    if not config.allow_dir_change:
        lines.append("DisableDirPage=yes")
    if config.create_uninstall_icon:
        lines.append("UninstallDisplayIcon={app}\\{#MyAppExeName}")
    if config.setup_icon_file:
        lines.append(f"SetupIconFile={escape_iss(config.setup_icon_file)}")
    if config.license_file:
        lines.append(f"LicenseFile={escape_iss(config.license_file)}")
    if config.readme_file:
        lines.append(f"InfoAfterFile={escape_iss(config.readme_file)}")
    if config.sign_installer:
        # Requires ISCC to be invoked with /Sbyparam=<signtool command line>.
        lines.append("SignTool=byparam")
    lines.extend(_arch_directives(config.architecture))

    # [Languages]
    entries, _warnings = resolve_languages(config)
    lines.extend(["", "[Languages]"])
    for name, isl in entries:
        lines.append(f'Name: "{name}"; MessagesFile: "{escape_iss(isl)}"')

    # [Tasks]
    if config.desktop_icon:
        lines.extend(
            [
                "",
                "[Tasks]",
                'Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; '
                'GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked',
            ]
        )

    # [Files]
    lines.extend(["", "[Files]"])
    if onefile:
        lines.append(
            f'Source: "{escape_iss(app_path)}"; DestDir: "{{app}}"; Flags: ignoreversion'
        )
    else:
        src = escape_iss(os.path.join(app_path, "*"))
        lines.append(
            f'Source: "{src}"; DestDir: "{{app}}"; '
            "Flags: ignoreversion recursesubdirs createallsubdirs"
        )
    if config.readme_file:
        lines.append(
            f'Source: "{escape_iss(config.readme_file)}"; DestDir: "{{app}}"; '
            "Flags: ignoreversion isreadme"
        )

    # [Icons]
    lines.extend(
        [
            "",
            "[Icons]",
            'Name: "{group}\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"',
        ]
    )
    if config.create_uninstall_icon:
        lines.append(
            'Name: "{group}\\{cm:UninstallProgram,{#MyAppName}}"; '
            'Filename: "{uninstallexe}"'
        )
    if config.desktop_icon:
        lines.append(
            'Name: "{autodesktop}\\{#MyAppName}"; '
            'Filename: "{app}\\{#MyAppExeName}"; Tasks: desktopicon'
        )

    # [Registry] — optional file association
    ext = config.associate_extension.strip()
    if ext:
        prog_id = f"{(config.app_name or 'MyApp').replace(' ', '')}{ext.replace('.', '')}File"
        prog_id = escape_iss(prog_id)
        lines.extend(
            [
                "",
                "[Registry]",
                f'Root: HKA; Subkey: "Software\\Classes\\{escape_iss(ext)}"; '
                f'ValueType: string; ValueName: ""; ValueData: "{prog_id}"; '
                "Flags: uninsdeletevalue",
                f'Root: HKA; Subkey: "Software\\Classes\\{prog_id}"; '
                'ValueType: string; ValueName: ""; ValueData: "{#MyAppName}"; '
                "Flags: uninsdeletekey",
                f'Root: HKA; Subkey: "Software\\Classes\\{prog_id}\\DefaultIcon"; '
                'ValueType: string; ValueName: ""; ValueData: "{app}\\{#MyAppExeName},0"',
                f'Root: HKA; Subkey: "Software\\Classes\\{prog_id}\\shell\\open\\command"; '
                'ValueType: string; ValueName: ""; '
                'ValueData: """{app}\\{#MyAppExeName}"" ""%1"""',
            ]
        )

    # [Run]
    if config.launch_after_install:
        lines.extend(
            [
                "",
                "[Run]",
                'Filename: "{app}\\{#MyAppExeName}"; '
                'Description: "{cm:LaunchProgram,{#StringChange(MyAppName, \'&\', \'&&\')}}"; '
                "Flags: nowait postinstall skipifsilent",
            ]
        )

    return "\n".join(lines) + "\n"


# ── ISCC discovery & command ───────────────────────────────────────────────

_ISCC_SEARCH_PATHS = (
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
    r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
    r"C:\Program Files\Inno Setup 5\ISCC.exe",
)


def find_iscc(env: Optional[Dict[str, str]] = None) -> Optional[str]:
    """Locate ``ISCC.exe``.

    Order: ``INNO_SETUP_ISCC`` env var → PATH → the standard install paths.
    Returns None when Inno Setup is not installed.
    """
    environ = os.environ if env is None else env
    explicit = environ.get("INNO_SETUP_ISCC", "").strip()
    if explicit and os.path.isfile(explicit):
        return explicit

    on_path = shutil.which("ISCC") or shutil.which("iscc")
    if on_path:
        return on_path

    for candidate in _ISCC_SEARCH_PATHS:
        if os.path.isfile(candidate):
            return candidate
    return None


def build_iscc_command(
    iss_path: str,
    iscc_path: Optional[str] = None,
    output_dir: str = "",
    output_basename: str = "",
    sign_command: Optional[List[str]] = None,
    quiet: bool = True,
) -> Tuple[Optional[List[str]], Optional[str]]:
    """Construct the ISCC command line for ``iss_path``.

    Returns (command, error). ``sign_command`` — when given — is wired to the
    ``SignTool=byparam`` directive emitted by ``generate_iss_script`` for a
    signed Setup.exe.
    """
    if not iss_path:
        return None, "Script path is required"

    exe = iscc_path or find_iscc()
    if not exe:
        return None, "ISCC.exe not found — install Inno Setup or set INNO_SETUP_ISCC"

    cmd: List[str] = [exe]
    if quiet:
        cmd.append("/Q")
    if output_dir:
        cmd.append(f"/O{output_dir}")
    if output_basename:
        cmd.append(f"/F{output_basename}")
    if sign_command:
        # ISCC expects the whole signing command as one /S<name>=<command>
        # argument; $f is substituted with the file being signed.
        cmd.append("/Sbyparam=" + _format_sign_param(sign_command))
    cmd.append(iss_path)
    return cmd, None


def _format_sign_param(sign_command: List[str]) -> str:
    """Render a signtool argv as an Inno Setup ``/S`` parameter value.

    Inno Setup substitutes ``$f`` with the file to sign and ``$q`` with a
    double quote, so tokens containing spaces are wrapped in ``$q``.
    """
    parts = []
    for token in sign_command:
        if " " in token:
            parts.append(f"$q{token}$q")
        else:
            parts.append(token)
    parts.append("$f")
    return " ".join(parts)


def installer_output_path(config: "InstallerConfig", fallback_dir: str = "") -> str:
    """Absolute path of the Setup.exe that ``generate_iss_script`` will produce."""
    out_dir = config.output_dir or fallback_dir
    return os.path.join(out_dir, default_output_basename(config) + ".exe")
