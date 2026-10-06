"""p2e_runtime — optional services for apps built with Python to EXE Converter.

Pure standard library, Python 3.8+, no GUI toolkit: it works in tkinter, Qt,
wx and console apps alike. Every service is off unless ``p2e_runtime.json``
(written by the converter and bundled with the app) turns it on:

* ``resource_path()`` — paths to bundled files, frozen or not;
* log redirection — a windowed app's missing stdout/stderr go to a log file;
* crash reporter — a saved report and a dialog instead of a silent exit;
* single instance — a second copy shows a message and exits;
* signed self-updater — ``p2e_runtime.updates.check()`` / ``apply()``.

There is no telemetry, and nothing touches the network unless the developer
configured an update URL *and* the app calls the updater (or opted in to a
check at start-up).

The converter's runtime hook calls ``install()`` before the app's own code.
"""

import importlib
import sys
from typing import Optional, Union

from p2e_runtime.config import CONFIG_FILE_NAME, RuntimeConfig, load_config, parse_config
from p2e_runtime.paths import bundle_dir, is_frozen, resource_path, user_state_dir

__version__ = "1.5.0"

__all__ = [
    "CONFIG_FILE_NAME",
    "RuntimeConfig",
    "bundle_dir",
    "current_config",
    "install",
    "is_frozen",
    "load_config",
    "parse_config",
    "resource_path",
    "user_state_dir",
]

_config: Optional[RuntimeConfig] = None
_installed = False


def _service(name: str):
    # Imported by name, not with an import statement: PyInstaller only
    # bundles what it sees imported, so a service that is off (the updater
    # pulls in ssl and urllib) adds nothing to the EXE. The converter adds
    # each enabled service as a hidden import.
    return importlib.import_module(f"p2e_runtime.{name}")


def current_config() -> Optional[RuntimeConfig]:
    """The configuration ``install()`` used, or the bundled file's."""
    if _config is not None:
        return _config
    try:
        return load_config()
    except ValueError:
        return None


def _warn(message: str) -> None:
    stream = sys.stderr
    if stream is not None:
        try:
            stream.write(f"[p2e_runtime] {message}\n")
        except Exception:
            pass


def install(config: Union[RuntimeConfig, str, None] = None) -> Optional[RuntimeConfig]:
    """Turn on the services the configuration enables. Safe to call twice.

    ``config`` is a ``RuntimeConfig``, a path to ``p2e_runtime.json``, or
    ``None`` for the file bundled with the app. Without a configuration
    nothing happens. A service that fails to start is reported on stderr and
    skipped; only the single-instance guard may end the process, on purpose.
    """
    global _config, _installed
    if _installed:
        return _config
    if not isinstance(config, RuntimeConfig):
        try:
            config = load_config(config)
        except ValueError as e:
            _warn(f"ignoring an invalid configuration: {e}")
            return None
    if config is None:
        return None
    _config = config
    _installed = True

    steps = (_start_logs, _start_crash_reporter, _start_single_instance, _start_updater)
    for step in steps:
        try:
            step(config)
        except SystemExit:
            raise
        except Exception as e:
            _warn(f"{step.__name__[7:]} not started: {e!r}")
    return config


def _start_logs(config: RuntimeConfig) -> None:
    if config.logs is not None:
        _service("logs").redirect(
            config.app_name, config.app_version, config.logs.max_bytes, config.logs.backups
        )


def _start_crash_reporter(config: RuntimeConfig) -> None:
    crash = config.crash
    if crash is not None:
        _service("crash").install(
            config.app_name, config.app_version, dialog=crash.dialog,
            support_url=crash.support_url, title=crash.title, message=crash.message,
            support_prompt=crash.support_prompt, rtl=config.rtl,
        )


def _start_single_instance(config: RuntimeConfig) -> None:
    single = config.single_instance
    if single is not None:
        _service("single_instance").ensure_single_instance(
            single.id, config.app_name, single.message, single.exit_code, rtl=config.rtl,
            lock_dir=user_state_dir(config.app_name),
        )


def _start_updater(config: RuntimeConfig) -> None:
    if config.updater is not None:
        _service("updates").on_start(config)
