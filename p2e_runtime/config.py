"""The runtime's settings: ``p2e_runtime.json``, written by the converter.

The converter bundles this file next to the app's data; nothing about the
configuration is ever generated as Python code. A service that is absent
from ``services`` is off. Unknown keys are ignored so that a newer converter
can add options without breaking an older runtime.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from p2e_runtime.paths import resource_path, safe_name

CONFIG_FILE_NAME = "p2e_runtime.json"
FORMAT_VERSION = 1

BUILD_ONEFILE = "onefile"
BUILD_ONEDIR = "onedir"

DEFAULT_LOG_MAX_BYTES = 1024 * 1024
DEFAULT_LOG_BACKUPS = 3
DEFAULT_UPDATE_TIMEOUT = 15.0


@dataclass(frozen=True)
class LogsConfig:
    max_bytes: int = DEFAULT_LOG_MAX_BYTES
    backups: int = DEFAULT_LOG_BACKUPS


@dataclass(frozen=True)
class CrashConfig:
    dialog: bool = True
    support_url: str = ""
    title: str = ""
    message: str = ""
    support_prompt: str = ""


@dataclass(frozen=True)
class SingleInstanceConfig:
    id: str = ""
    message: str = ""
    exit_code: int = 0


@dataclass(frozen=True)
class UpdaterConfig:
    manifest_url: str = ""
    signature_url: str = ""
    public_key: str = ""
    check_on_start: bool = False
    installer_args: List[str] = field(default_factory=list)
    timeout: float = DEFAULT_UPDATE_TIMEOUT
    prompt_title: str = ""
    prompt_message: str = ""
    #: Test-only: accept plain ``http://`` to localhost. The converter never
    #: sets this from its UI or from a settings file.
    allow_insecure_localhost: bool = False


@dataclass(frozen=True)
class RuntimeConfig:
    app_name: str = "app"
    app_version: str = ""
    build: str = BUILD_ONEFILE
    rtl: bool = False
    resource_path: bool = False
    logs: Optional[LogsConfig] = None
    crash: Optional[CrashConfig] = None
    single_instance: Optional[SingleInstanceConfig] = None
    updater: Optional[UpdaterConfig] = None

    def enabled(self) -> List[str]:
        names = []
        for name in ("resource_path", "logs", "crash", "single_instance", "updater"):
            if getattr(self, name):
                names.append(name)
        return names


def _section(services: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    value = services.get(name)
    if value is None or value is False:
        return None
    if value is True:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"services.{name} must be an object")
    return value


def _str(data: Dict[str, Any], key: str, default: str = "") -> str:
    value = data.get(key, default)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value


def _int(data: Dict[str, Any], key: str, default: int, minimum: int = 0) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{key} must be an integer >= {minimum}")
    return value


def parse_config(data: Any) -> RuntimeConfig:
    """Validate the decoded JSON. Raises ``ValueError`` on anything malformed."""
    if not isinstance(data, dict):
        raise ValueError("the runtime configuration must be a JSON object")
    if data.get("format", FORMAT_VERSION) != FORMAT_VERSION:
        raise ValueError(f"unsupported configuration format: {data.get('format')!r}")
    app = data.get("app")
    services = data.get("services")
    app = {} if app is None else app
    services = {} if services is None else services
    if not isinstance(app, dict) or not isinstance(services, dict):
        raise ValueError("'app' and 'services' must be objects")

    build = _str(app, "build", BUILD_ONEFILE)
    if build not in (BUILD_ONEFILE, BUILD_ONEDIR):
        raise ValueError(f"unknown build kind: {build!r}")

    logs = crash = single = updater = None
    section = _section(services, "logs")
    if section is not None:
        logs = LogsConfig(
            max_bytes=_int(section, "max_bytes", DEFAULT_LOG_MAX_BYTES, minimum=1024),
            backups=_int(section, "backups", DEFAULT_LOG_BACKUPS),
        )
    section = _section(services, "crash_reporter")
    if section is not None:
        crash = CrashConfig(
            dialog=bool(section.get("dialog", True)),
            support_url=_str(section, "support_url"),
            title=_str(section, "title"),
            message=_str(section, "message"),
            support_prompt=_str(section, "support_prompt"),
        )
    section = _section(services, "single_instance")
    if section is not None:
        single = SingleInstanceConfig(
            id=safe_name(_str(section, "id") or _str(app, "name", "app")),
            message=_str(section, "message"),
            exit_code=_int(section, "exit_code", 0),
        )
    section = _section(services, "updater")
    if section is not None:
        args = section.get("installer_args", [])
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            raise ValueError("installer_args must be a list of strings")
        timeout = section.get("timeout", DEFAULT_UPDATE_TIMEOUT)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("timeout must be a positive number")
        updater = UpdaterConfig(
            manifest_url=_str(section, "manifest_url"),
            signature_url=_str(section, "signature_url"),
            public_key=_str(section, "public_key").strip().lower(),
            check_on_start=bool(section.get("check_on_start", False)),
            installer_args=list(args),
            timeout=float(timeout),
            prompt_title=_str(section, "prompt_title"),
            prompt_message=_str(section, "prompt_message"),
            allow_insecure_localhost=section.get("allow_insecure_localhost") is True,
        )

    return RuntimeConfig(
        app_name=_str(app, "name", "app") or "app",
        app_version=_str(app, "version"),
        build=build,
        rtl=bool(app.get("rtl", False)),
        resource_path=_section(services, "resource_path") is not None,
        logs=logs,
        crash=crash,
        single_instance=single,
        updater=updater,
    )


def default_config_path() -> str:
    return resource_path(CONFIG_FILE_NAME)


def load_config(path: Optional[str] = None) -> Optional[RuntimeConfig]:
    """Read ``p2e_runtime.json``; ``None`` when there is no such file.

    Without a path, the file bundled with the app is used. A file that exists
    but is malformed raises ``ValueError``: silently running with every
    service off would hide a broken build.
    """
    path = path or default_config_path()
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, UnicodeDecodeError) as e:
        raise ValueError(f"cannot read {path}: {e}") from e
    return parse_config(data)
