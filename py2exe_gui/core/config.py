"""Build configuration dataclass — decouples UI state from command construction."""

from dataclasses import dataclass, field, fields
from typing import Any, List, Optional

from py2exe_gui.core.dictfields import section_from_dict

# Runtime Kit services, in the order the UI lists them.
RUNTIME_SERVICES = (
    "resource_path", "log_redirect", "crash_reporter", "single_instance", "updater",
    "licensing",
)


#: The engine a build uses unless it names another (``core/engines``).
DEFAULT_ENGINE = "pyinstaller"
#: Engine names this version knows. Kept here, not imported from
#: ``core/engines``, so the config stays a leaf module that nothing in
#: ``core`` has to be imported before (``dictfields`` is a leaf too).
KNOWN_ENGINES = ("pyinstaller", "nuitka")


def _engine_name(value: Any) -> str:
    """A known engine name, or the default for anything else (pre-2.0 files)."""
    return value if isinstance(value, str) and value in KNOWN_ENGINES else DEFAULT_ENGINE


@dataclass
class RuntimeKitConfig:
    """Which ``p2e_runtime`` services to embed in the EXE, and their settings.

    Plain data only — booleans and strings — for the same reason
    ``isolated_env`` is a flag: a settings file shared by someone else must
    not be able to name a hook, a script or an executable. The converter
    writes the runtime hook itself at build time.
    """

    resource_path: bool = False
    log_redirect: bool = False
    crash_reporter: bool = False
    single_instance: bool = False
    updater: bool = False
    #: Offline licence keys checked with ``p2e_runtime.license``.
    licensing: bool = False

    app_version: str = ""
    support_url: str = ""
    instance_message: str = ""
    update_url: str = ""
    update_public_key: str = ""
    update_check_on_start: bool = False
    #: Arguments for a folder build's installer, e.g. "/SILENT".
    installer_args: str = ""
    #: The product name a licence must carry ('' = the app's name) and the
    #: public half of the licence key. The private half is never here.
    license_product: str = ""
    license_public_key: str = ""

    def enabled_services(self) -> List[str]:
        return [name for name in RUNTIME_SERVICES if getattr(self, name)]

    @property
    def enabled(self) -> bool:
        return bool(self.enabled_services())

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_dict(cls, data: Any) -> "RuntimeKitConfig":
        """Lenient on missing keys, strict on types: a wrong type is dropped."""
        if not isinstance(data, dict):
            return cls()
        values = {}
        for f in fields(cls):
            value = data.get(f.name)
            default = getattr(cls(), f.name)
            if isinstance(default, bool):
                values[f.name] = value if isinstance(value, bool) else default
            elif isinstance(value, str):
                values[f.name] = value
        return cls(**values)


@dataclass
class BuildConfig:
    """All parameters needed to construct a build command (PyInstaller by default)."""

    source: str = ""
    output_name: str = ""
    output_dir: str = ""
    icon: str = ""

    onefile: bool = True
    windowed: bool = False
    noconsole: bool = False
    clean: bool = True
    noconfirm: bool = True
    strip: bool = False

    extra_files: List[str] = field(default_factory=list)
    hidden_imports: List[str] = field(default_factory=list)

    optimize: int = 0
    upx: bool = False
    upx_level: int = 0  # kept for backwards-compatible config files; unused
    upx_dir: str = ""
    extra_args: str = ""

    version_file: str = ""

    # Deployment-time options: shown while the EXE unpacks, and the Windows
    # manifest to embed.
    splash_image: str = ""
    manifest_file: str = ""

    # Build in this project's isolated environment instead of the
    # interpreter running the app. A flag, never a path: a shared settings
    # file must not be able to name an executable for the build to run.
    isolated_env: bool = False

    # Runtime Kit services embedded in the EXE (see RuntimeKitConfig).
    runtime_kit: RuntimeKitConfig = field(default_factory=RuntimeKitConfig)

    # Which engine builds it (``core/engines``). A name from a fixed list,
    # never a path; an unknown name falls back to the default.
    engine: str = DEFAULT_ENGINE

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "output_name": self.output_name,
            "output_dir": self.output_dir,
            "icon": self.icon,
            "onefile": self.onefile,
            "windowed": self.windowed,
            "noconsole": self.noconsole,
            "clean": self.clean,
            "noconfirm": self.noconfirm,
            "strip": self.strip,
            "extra_files": list(self.extra_files),
            "hidden_imports": list(self.hidden_imports),
            "optimize": self.optimize,
            "upx": self.upx,
            "upx_level": self.upx_level,
            "upx_dir": self.upx_dir,
            "extra_args": self.extra_args,
            "version_file": self.version_file,
            "splash_image": self.splash_image,
            "manifest_file": self.manifest_file,
            "isolated_env": self.isolated_env,
            "runtime_kit": self.runtime_kit.to_dict(),
            "engine": self.engine,
        }

    @classmethod
    def from_dict(cls, data: Any, warnings: Optional[List[str]] = None) -> "BuildConfig":
        """Lenient on missing keys, strict on types (see ``dictfields``).

        A settings file is hand-edited and shared: ``"optimize": "2"`` is
        coerced, ``"extra_files": "data"`` and ``"onefile": "yes"`` keep the
        default instead of becoming ``['d', 'a', 't', 'a']`` or a truthy
        string the command builder trips over. ``warnings`` collects one line
        per dropped value when the caller wants to show them.
        """
        if not isinstance(data, dict):
            return cls()
        config = section_from_dict(cls(), data, "build", warnings,
                                   skip=("runtime_kit", "engine"))
        config.runtime_kit = RuntimeKitConfig.from_dict(data.get("runtime_kit"))
        config.engine = _engine_name(data.get("engine"))
        return config
