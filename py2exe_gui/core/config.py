"""Build configuration dataclass — decouples UI state from command construction."""

from dataclasses import dataclass, field, fields
from typing import Any, List

# Runtime Kit services, in the order the UI lists them.
RUNTIME_SERVICES = (
    "resource_path", "log_redirect", "crash_reporter", "single_instance", "updater",
)


#: The engine a build uses unless it names another (``core/engines``).
DEFAULT_ENGINE = "pyinstaller"
#: Engine names this version knows. Kept here, not imported from
#: ``core/engines``, so the config stays a leaf module with no imports.
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

    app_version: str = ""
    support_url: str = ""
    instance_message: str = ""
    update_url: str = ""
    update_public_key: str = ""
    update_check_on_start: bool = False
    #: Arguments for a folder build's installer, e.g. "/SILENT".
    installer_args: str = ""

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

    # Phase 5: deployment-time options
    splash_image: str = ""
    manifest_file: str = ""

    # 1.4: build in this project's isolated environment instead of the
    # interpreter running the app. A flag, never a path: a shared settings
    # file must not be able to name an executable for the build to run.
    isolated_env: bool = False

    # 1.5: Runtime Kit services embedded in the EXE (see RuntimeKitConfig).
    runtime_kit: RuntimeKitConfig = field(default_factory=RuntimeKitConfig)

    # 2.0: which engine builds it (``core/engines``). A name from a fixed
    # list, never a path; an unknown name falls back to the default.
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
    def from_dict(cls, data: dict) -> "BuildConfig":
        return cls(
            source=data.get("source", ""),
            output_name=data.get("output_name", ""),
            output_dir=data.get("output_dir", ""),
            icon=data.get("icon", ""),
            onefile=data.get("onefile", True),
            windowed=data.get("windowed", False),
            noconsole=data.get("noconsole", False),
            clean=data.get("clean", True),
            noconfirm=data.get("noconfirm", True),
            strip=data.get("strip", False),
            extra_files=list(data.get("extra_files", [])),
            hidden_imports=list(data.get("hidden_imports", [])),
            optimize=data.get("optimize", 0),
            upx=data.get("upx", False),
            upx_level=data.get("upx_level", 0),
            upx_dir=data.get("upx_dir", ""),
            extra_args=data.get("extra_args", ""),
            version_file=data.get("version_file", ""),
            splash_image=data.get("splash_image", ""),
            manifest_file=data.get("manifest_file", ""),
            isolated_env=bool(data.get("isolated_env", False)),
            runtime_kit=RuntimeKitConfig.from_dict(data.get("runtime_kit")),
            engine=_engine_name(data.get("engine")),
        )
