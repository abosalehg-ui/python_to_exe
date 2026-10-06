"""The project file (``p2e.toml``): one settings model for the GUI, presets,
history and the command line.

Before 1.6 the settings lived in the widgets and were copied field by field
into a ``BuildConfig`` (and, separately, into a version-info form, a manifest
form, an installer form...). ``ProjectConfig`` is now the single source of
truth: everything needed to reproduce a build and a release, as data.

The file is meant to be committed and shared, so it is **untrusted input**:

* it can never hold a password, a token or a private key — the model has no
  field for one, and a file that tries (a forbidden key, or a value that looks
  like a GitHub token or a PEM key) is refused with an error;
* it can never name an interpreter or a tool to run (``python``, ``signtool``,
  ``iscc``...): ``isolated_env`` is a flag, and tool paths are per-user
  settings;
* what it *can* carry that makes the build run someone else's code
  (``--runtime-hook`` in ``extra_args``, ``--upx-dir``, an update key that is
  not yours) goes through the same confirmation as a JSON settings file — see
  ``untrusted_flags`` and ``runtime_kit.untrusted_risks``.

Paths are stored relative to the project file (with ``/``), so the project
works from any checkout, and resolved to absolute paths on load.
"""

import os
import re
from dataclasses import dataclass, field, fields
from typing import Any, Callable, Dict, List, Optional, Tuple

from py2exe_gui.core import toml_writer
from py2exe_gui.core.builder import find_dangerous_args
from py2exe_gui.core.code_signer import SigningConfig
from py2exe_gui.core.config import BuildConfig, RuntimeKitConfig
from py2exe_gui.core.installer import InstallerConfig
from py2exe_gui.core.manifest_generator import ManifestConfig
from py2exe_gui.core.version_info import VersionInfo

PROJECT_FILE_NAME = "p2e.toml"
SCHEMA_VERSION = 1
DEFAULT_TIMESTAMP_URL = "http://timestamp.digicert.com"

FILE_COMMENT = (
    "Python to EXE Converter project file.\n"
    "Everything needed to build and release this project. Safe to commit:\n"
    "it never holds a password, a token, a private key or an interpreter path."
)


# ── Sections that BuildConfig does not already model ──────────────────────


@dataclass
class ManifestSettings:
    """Windows assembly manifest options (generated at build time)."""

    enabled: bool = False
    dpi_aware: bool = False
    require_admin: bool = False
    supported_os: List[str] = field(default_factory=lambda: ["7", "8", "8.1", "10"])

    def manifest_config(self, name: str, version: str, description: str) -> ManifestConfig:
        return ManifestConfig(
            name=name or "MyApp",
            version=version or "1.0.0.0",
            description=description,
            dpi_aware=self.dpi_aware,
            require_admin=self.require_admin,
            supported_os=list(self.supported_os),
        )


@dataclass
class SigningSettings:
    """Code signing — the non-secret half only.

    The certificate password is typed at signing time (GUI field, prompt, or
    ``P2E_SIGN_PASSWORD``) and never stored; the signtool location is a
    per-user setting, never project data.
    """

    enabled: bool = False
    use_cert_store: bool = False
    cert_subject: str = ""
    cert_path: str = ""
    timestamp_url: str = DEFAULT_TIMESTAMP_URL
    description: str = ""

    def signing_config(self, password: str = "", signtool_path: str = "signtool") -> SigningConfig:
        return SigningConfig(
            enabled=self.enabled,
            use_cert_store=self.use_cert_store,
            cert_subject=self.cert_subject,
            cert_path=self.cert_path,
            cert_password="" if self.use_cert_store else password,
            timestamp_url=self.timestamp_url or DEFAULT_TIMESTAMP_URL,
            description=self.description,
            signtool_path=signtool_path or "signtool",
        )

    @classmethod
    def from_signing_config(cls, config: SigningConfig) -> "SigningSettings":
        return cls(
            enabled=config.enabled,
            use_cert_store=config.use_cert_store,
            cert_subject=config.cert_subject,
            cert_path=config.cert_path,
            timestamp_url=config.timestamp_url,
            description=config.description,
        )


@dataclass
class ReleaseAssets:
    """Which files a release uploads."""

    exe: bool = True
    installer: bool = True
    portable_zip: bool = True
    checksums: bool = True
    #: The Runtime Kit's signed update.json (only when the updater is on).
    update_manifest: bool = True


@dataclass
class WingetSettings:
    """Identifiers for the generated winget manifest (generated, never submitted)."""

    enabled: bool = False
    identifier: str = ""  # Publisher.Package
    publisher: str = ""
    license: str = ""
    short_description: str = ""
    locale: str = "en-US"


@dataclass
class ReleaseSettings:
    repository: str = ""  # "owner/repo" on GitHub
    tag_prefix: str = "v"
    draft: bool = False
    prerelease: bool = False
    assets: ReleaseAssets = field(default_factory=ReleaseAssets)
    winget: WingetSettings = field(default_factory=WingetSettings)


@dataclass
class ProjectConfig:
    """Everything that describes a project, in one place."""

    name: str = ""
    #: The version, as semver ("1.2.3"). Version Info, the installer and the
    #: Runtime Kit follow it (see ``release.versioning.apply_version``).
    version: str = ""
    build: BuildConfig = field(default_factory=BuildConfig)
    version_info: VersionInfo = field(default_factory=VersionInfo)
    manifest: ManifestSettings = field(default_factory=ManifestSettings)
    installer: InstallerConfig = field(default_factory=InstallerConfig)
    signing: SigningSettings = field(default_factory=SigningSettings)
    release: ReleaseSettings = field(default_factory=ReleaseSettings)

    def display_name(self) -> str:
        if self.name:
            return self.name
        if self.build.output_name:
            return self.build.output_name
        if self.build.source:
            return os.path.splitext(os.path.basename(self.build.source))[0]
        return ""

    # ── JSON form (settings files, presets, build history) ─────────────

    def to_settings_dict(self) -> dict:
        """The JSON form: a superset of ``BuildConfig.to_dict()``.

        Build fields stay at the top level, exactly where every earlier
        version wrote them, so an older app (or the size lab reading history)
        still finds them. The other sections are added under their own keys.
        """
        data = self.build.to_dict()
        data["project"] = {"name": self.name, "version": self.version}
        for section in SECTIONS:
            data[section] = _section_to_dict(getattr(self, section))
        return data

    @classmethod
    def from_settings_dict(cls, data: Any) -> "ProjectConfig":
        """Read the JSON form — including a pre-1.6 file, which is build only."""
        if not isinstance(data, dict):
            raise ValueError("settings must be a JSON object")
        project = cls(build=BuildConfig.from_dict(data))
        meta = data.get("project")
        if isinstance(meta, dict):
            project.name = _as_str(meta.get("name"))
            project.version = _as_str(meta.get("version"))
        warnings: List[str] = []
        for section in SECTIONS:
            raw = data.get(section)
            if isinstance(raw, dict):
                setattr(project, section, _section_from_dict(
                    getattr(project, section), raw, section, warnings
                ))
        return project


#: Sections of ProjectConfig besides ``build``, in file order.
SECTIONS = ("version_info", "manifest", "installer", "signing", "release")


def sections_in(data: Any) -> List[str]:
    """Which non-build sections a JSON settings dict actually carries.

    Applying a pre-1.6 preset must not reset the installer tab to defaults:
    only what the file holds is applied.
    """
    if not isinstance(data, dict):
        return []
    return [s for s in SECTIONS if isinstance(data.get(s), dict)]


# ── Generic, type-strict (de)serialization of the dataclasses ─────────────


def _as_str(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _section_to_dict(obj: Any) -> dict:
    out = {}
    for f in fields(obj):
        value = getattr(obj, f.name)
        if hasattr(value, "__dataclass_fields__"):
            out[f.name] = _section_to_dict(value)
        elif isinstance(value, list):
            out[f.name] = list(value)
        else:
            out[f.name] = value
    return out


def _type_ok(default: Any, value: Any) -> bool:
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(default, int):
        return isinstance(value, int) and not isinstance(value, bool)
    if isinstance(default, str):
        return isinstance(value, str)
    if isinstance(default, list):
        return isinstance(value, list) and all(isinstance(v, str) for v in value)
    return False


def _section_from_dict(defaults: Any, data: dict, where: str, warnings: List[str],
                       skip: Tuple[str, ...] = ()) -> Any:
    """A copy of ``defaults`` with the values of ``data`` that have the right type.

    Lenient on missing keys (defaults stay), strict on types (a wrong type is
    dropped and reported), unknown keys reported.
    """
    known = {f.name for f in fields(defaults)}
    values = {}
    for f in fields(defaults):
        if f.name in skip or f.name not in data:
            continue
        default = getattr(defaults, f.name)
        value = data[f.name]
        if hasattr(default, "__dataclass_fields__"):
            if isinstance(value, dict):
                values[f.name] = _section_from_dict(default, value, f"{where}.{f.name}", warnings)
            else:
                warnings.append(f"{where}.{f.name}: expected a table")
        elif _type_ok(default, value):
            values[f.name] = list(value) if isinstance(value, list) else value
        else:
            warnings.append(f"{where}.{f.name}: wrong type ({type(value).__name__}), ignored")
    for key in data:
        if key not in known:
            warnings.append(f"{where}.{key}: unknown setting, ignored")
    result = type(defaults)(**{f.name: getattr(defaults, f.name) for f in fields(defaults)})
    for name, value in values.items():
        setattr(result, name, value)
    return result


# ── Paths ─────────────────────────────────────────────────────────────────

#: Path-valued fields, per section. Lists of paths are handled the same way.
PATH_FIELDS: Dict[str, Tuple[str, ...]] = {
    "build": ("source", "output_dir", "icon", "extra_files", "upx_dir", "splash_image"),
    "installer": ("output_dir", "license_file", "readme_file", "setup_icon_file",
                  "arabic_isl_path"),
    "signing": ("cert_path",),
}


def to_portable_path(path: str, base_dir: str, pathmod=os.path) -> str:
    """``path`` relative to ``base_dir`` with ``/`` separators, when possible.

    A path on another Windows drive cannot be made relative and is kept as is.
    """
    if not path:
        return ""
    if not pathmod.isabs(path):
        return path.replace("\\", "/")
    try:
        relative = pathmod.relpath(path, base_dir)
    except ValueError:  # different drive
        return path
    return relative.replace(pathmod.sep, "/")


def resolve_path(path: str, base_dir: str, pathmod=os.path) -> str:
    """The absolute form of a path read from the project file."""
    if not path:
        return ""
    native = path.replace("/", pathmod.sep) if pathmod.sep != "/" else path
    if pathmod.isabs(native):
        return pathmod.normpath(native)
    return pathmod.normpath(pathmod.join(base_dir, native))


def _map_paths(section: dict, names: Tuple[str, ...], convert: Callable[[str], str]) -> None:
    for name in names:
        value = section.get(name)
        if isinstance(value, str):
            section[name] = convert(value)
        elif isinstance(value, list):
            section[name] = [convert(v) if isinstance(v, str) else v for v in value]


# ── Security: what a shared project file may never contain ────────────────

#: Fragments that make a key name a secret, wherever it appears.
_SECRET_KEY_PARTS = ("password", "passwd", "passphrase", "token", "secret", "private_key",
                     "privatekey", "api_key", "apikey", "credential")
#: Key names that would name a program to run.
_EXECUTABLE_KEYS = frozenset({
    "python", "python_exe", "python_executable", "python_path", "pythonpath", "interpreter",
    "base_python", "executable", "exe_path", "signtool", "signtool_path", "iscc", "iscc_path",
    "pyinstaller", "pyinstaller_path", "git", "git_path", "uv", "uv_path", "command",
})
_SECRET_VALUES = (
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),  # GitHub tokens (classic and app)
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),  # GitHub fine-grained tokens
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


class ProjectFileError(Exception):
    """A project file that cannot (or must not) be used.

    ``code`` is stable and translated by the caller; ``detail`` names the key
    or carries the parser's message.
    """

    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def forbidden_key(key: str) -> str:
    """'secret' or 'executable' when a key may not appear in a project file."""
    name = key.lower().replace("-", "_")
    if any(part in name for part in _SECRET_KEY_PARTS):
        return "secret"
    if name in _EXECUTABLE_KEYS:
        return "executable"
    return ""


def looks_like_secret(value: str) -> bool:
    return any(pattern.search(value) for pattern in _SECRET_VALUES)


def check_untrusted_content(data: Any, path: str = "") -> None:
    """Raise ``ProjectFileError`` if ``data`` holds a secret or an executable."""
    if isinstance(data, dict):
        for key, value in data.items():
            where = f"{path}.{key}" if path else str(key)
            kind = forbidden_key(str(key))
            if kind == "secret":
                raise ProjectFileError("forbidden_secret", where)
            if kind == "executable":
                raise ProjectFileError("forbidden_executable", where)
            check_untrusted_content(value, where)
    elif isinstance(data, list):
        for index, value in enumerate(data):
            check_untrusted_content(value, f"{path}[{index}]")
    elif isinstance(data, str) and looks_like_secret(data):
        raise ProjectFileError("secret_value", path)


def untrusted_flags(build: BuildConfig) -> List[str]:
    """Settings in a shared file that would make the build run its code.

    The flags inside ``extra_args``, plus ``upx_dir``: UPX is an executable,
    and that field chooses the folder it is run from.
    """
    flags = find_dangerous_args(build.extra_args)
    if build.upx and build.upx_dir.strip() and "--upx-dir" not in flags:
        flags.append("--upx-dir")
    return flags


# ── Schema versions ───────────────────────────────────────────────────────

#: ``MIGRATIONS[n]`` turns a schema-``n`` document into schema ``n + 1``.
#: Empty while there is only schema 1; the loader already runs the chain.
MIGRATIONS: Dict[int, Callable[[dict], dict]] = {}


def migrate(data: dict) -> dict:
    """Bring a parsed document up to ``SCHEMA_VERSION``."""
    schema = data.get("schema")
    if schema is None:
        raise ProjectFileError("schema_missing")
    if not isinstance(schema, int) or isinstance(schema, bool) or schema < 1:
        raise ProjectFileError("schema_invalid", repr(schema))
    if schema > SCHEMA_VERSION:
        raise ProjectFileError("schema_newer", str(schema))
    while schema < SCHEMA_VERSION:
        step = MIGRATIONS.get(schema)
        if step is None:
            raise ProjectFileError("schema_invalid", f"no migration from {schema}")
        data = step(dict(data))
        schema += 1
        data["schema"] = schema
    return data


# ── TOML form ─────────────────────────────────────────────────────────────

#: BuildConfig fields that are not project data: generated per build
#: (version/manifest files), unused (upx_level), or a section of their own.
_BUILD_NOT_STORED = ("version_file", "manifest_file", "upx_level", "runtime_kit")


def project_to_document(project: ProjectConfig, base_dir: str, pathmod=os.path) -> dict:
    """The TOML document (as a dict) for ``project``, paths made relative."""

    def portable(value: str) -> str:
        return to_portable_path(value, base_dir, pathmod)

    build = {
        f.name: _section_to_dict(project.build)[f.name]
        for f in fields(project.build) if f.name not in _BUILD_NOT_STORED
    }
    _map_paths(build, PATH_FIELDS["build"], portable)
    doc: Dict[str, Any] = {
        "schema": SCHEMA_VERSION,
        "project": {"name": project.name, "version": project.version},
        "build": build,
        "runtime_kit": _section_to_dict(project.build.runtime_kit),
    }
    for section in SECTIONS:
        values = _section_to_dict(getattr(project, section))
        _map_paths(values, PATH_FIELDS.get(section, ()), portable)
        doc[section] = values
    return doc


def project_from_document(data: dict, base_dir: str, pathmod=os.path
                          ) -> Tuple[ProjectConfig, List[str]]:
    """Parse a TOML document (already loaded) into a project.

    Raises ``ProjectFileError`` for anything that must not be used: an
    unknown or newer schema, a secret, an executable path.
    """
    if not isinstance(data, dict):
        raise ProjectFileError("not_a_table")
    check_untrusted_content(data)
    data = migrate(data)
    warnings: List[str] = []

    def resolved(section: str) -> dict:
        raw = data.get(section, {})
        if not isinstance(raw, dict):
            warnings.append(f"{section}: expected a table")
            return {}
        copy = dict(raw)
        _map_paths(copy, PATH_FIELDS.get(section, ()),
                   lambda value: resolve_path(value, base_dir, pathmod))
        return copy

    project = ProjectConfig()
    meta = data.get("project", {})
    if isinstance(meta, dict):
        meta_obj = _section_from_dict(_Meta(), meta, "project", warnings)
        project.name, project.version = meta_obj.name, meta_obj.version

    build = _section_from_dict(BuildConfig(), resolved("build"), "build", warnings,
                               skip=_BUILD_NOT_STORED)
    for name in _BUILD_NOT_STORED:
        if name in data.get("build", {}):
            warnings.append(f"build.{name}: not a project setting, ignored")
    build.runtime_kit = _section_from_dict(RuntimeKitConfig(), resolved("runtime_kit"),
                                           "runtime_kit", warnings)
    project.build = build
    for section in SECTIONS:
        setattr(project, section, _section_from_dict(
            getattr(project, section), resolved(section), section, warnings
        ))
    known = {"schema", "project", "build", "runtime_kit", *SECTIONS}
    for key in data:
        if key not in known:
            warnings.append(f"{key}: unknown section, ignored")
    return project, warnings


@dataclass
class _Meta:
    name: str = ""
    version: str = ""


# ── Files ─────────────────────────────────────────────────────────────────


def _toml_loads(text: str) -> dict:
    try:
        import tomllib  # Python 3.11+
    except ModuleNotFoundError:  # pragma: no cover - depends on the interpreter
        try:
            import tomli as tomllib  # declared for python_version < "3.11"
        except ModuleNotFoundError as e:
            raise ProjectFileError("toml_unavailable", "pip install tomli") from e
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        raise ProjectFileError("syntax", str(e)) from e


@dataclass
class LoadedProject:
    project: ProjectConfig
    path: str
    warnings: List[str] = field(default_factory=list)


def loads_project(text: str, base_dir: str, pathmod=os.path) -> Tuple[ProjectConfig, List[str]]:
    return project_from_document(_toml_loads(text), base_dir, pathmod)


def dumps_project(project: ProjectConfig, base_dir: str, pathmod=os.path) -> str:
    return toml_writer.dumps(project_to_document(project, base_dir, pathmod), FILE_COMMENT)


def load_project(path: str) -> LoadedProject:
    """Read and validate ``path``. Raises ``ProjectFileError``."""
    path = os.path.abspath(path)
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError as e:
        raise ProjectFileError("unreadable", str(e)) from e
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ProjectFileError("syntax", f"not UTF-8: {e}") from e
    project, warnings = loads_project(text, os.path.dirname(path))
    return LoadedProject(project, path, warnings)


def save_project(project: ProjectConfig, path: str) -> str:
    """Write ``path`` atomically; returns the absolute path written."""
    path = os.path.abspath(path)
    folder = os.path.dirname(path)
    text = dumps_project(project, folder)
    os.makedirs(folder, exist_ok=True)
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(temp, path)
    return path


def project_path_for_script(script: str) -> str:
    """Where "init project from this script" puts the file: beside the script."""
    return os.path.join(os.path.dirname(os.path.abspath(script)), PROJECT_FILE_NAME)


def new_project_for_script(script: str, base: Optional[ProjectConfig] = None,
                           version: str = "") -> ProjectConfig:
    """A project for ``script``, starting from ``base`` (e.g. the GUI's settings)."""
    import copy

    project = copy.deepcopy(base) if base is not None else ProjectConfig()
    project.build.source = os.path.abspath(script)
    stem = os.path.splitext(os.path.basename(script))[0]
    if not project.build.output_name:
        project.build.output_name = stem
    if not project.name:
        project.name = project.build.output_name or stem
    if version or not project.version:
        from py2exe_gui.core.release.versioning import apply_version

        apply_version(project, version or project.installer.app_version or "1.0.0")
    return project
