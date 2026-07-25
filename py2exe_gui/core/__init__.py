"""Core (UI-independent) modules: build logic, dependency analysis, config."""

from py2exe_gui.core.build_history import BuildHistory, BuildRecord, make_record
from py2exe_gui.core.builder import build_pyinstaller_command, split_extra_args
from py2exe_gui.core.code_signer import (
    SigningConfig,
    build_signtool_command,
    redact_password,
)
from py2exe_gui.core.config import BuildConfig
from py2exe_gui.core.dependency_analyzer import (
    detect_imports,
    filter_non_stdlib,
    parse_requirements,
)
from py2exe_gui.core.installer import (
    ARCH_CHOICES,
    COMPRESSION_CHOICES,
    LANGUAGE_LABELS,
    PRIVILEGE_CHOICES,
    InstallerConfig,
    build_iscc_command,
    derive_app_id,
    find_iscc,
    generate_iss_script,
    installer_output_path,
    resolve_languages,
)
from py2exe_gui.core.log_formatter import classify_line, format_html
from py2exe_gui.core.manifest_generator import ManifestConfig, generate_manifest
from py2exe_gui.core.smoke_test import (
    SmokeResult,
    locate_built_executable,
    run_smoke_test,
)
from py2exe_gui.core.version_info import VersionInfo, generate_version_file

__all__ = [
    "ARCH_CHOICES",
    "COMPRESSION_CHOICES",
    "LANGUAGE_LABELS",
    "PRIVILEGE_CHOICES",
    "BuildConfig",
    "BuildHistory",
    "BuildRecord",
    "InstallerConfig",
    "ManifestConfig",
    "SigningConfig",
    "SmokeResult",
    "VersionInfo",
    "build_iscc_command",
    "build_pyinstaller_command",
    "build_signtool_command",
    "classify_line",
    "derive_app_id",
    "detect_imports",
    "filter_non_stdlib",
    "find_iscc",
    "format_html",
    "generate_iss_script",
    "generate_manifest",
    "generate_version_file",
    "installer_output_path",
    "locate_built_executable",
    "make_record",
    "parse_requirements",
    "redact_password",
    "resolve_languages",
    "run_smoke_test",
    "split_extra_args",
]
