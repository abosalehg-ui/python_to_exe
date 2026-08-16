"""Core (UI-independent) modules: build logic, dependency analysis, config."""

from py2exe_gui.core.batch_runner import (
    BatchJob,
    BatchSummary,
    job_config,
    make_jobs,
    summarize,
)
from py2exe_gui.core.build_history import BuildHistory, BuildRecord, make_record
from py2exe_gui.core.build_stages import STAGES, BuildStageTracker, stage_keys
from py2exe_gui.core.builder import (
    DANGEROUS_FLAGS,
    build_pyinstaller_command,
    find_dangerous_args,
    split_extra_args,
)
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
from py2exe_gui.core.log_formatter import classify_line, format_html, level_color
from py2exe_gui.core.manifest_generator import ManifestConfig, generate_manifest
from py2exe_gui.core.platform_support import (
    WINDOWS_ONLY,
    is_supported,
    is_windows,
    platform_label,
    unsupported_features,
)
from py2exe_gui.core.presets import PresetLibrary, normalize_name
from py2exe_gui.core.smoke_test import (
    SmokeResult,
    locate_built_executable,
    run_smoke_test,
)
from py2exe_gui.core.update_checker import (
    RELEASES_PAGE_URL,
    UpdateInfo,
    check_for_update,
    is_newer,
    parse_version,
)
from py2exe_gui.core.version_info import VersionInfo, generate_version_file

__all__ = [
    "ARCH_CHOICES",
    "COMPRESSION_CHOICES",
    "DANGEROUS_FLAGS",
    "LANGUAGE_LABELS",
    "PRIVILEGE_CHOICES",
    "RELEASES_PAGE_URL",
    "STAGES",
    "WINDOWS_ONLY",
    "BatchJob",
    "BatchSummary",
    "BuildConfig",
    "BuildHistory",
    "BuildRecord",
    "BuildStageTracker",
    "InstallerConfig",
    "ManifestConfig",
    "PresetLibrary",
    "SigningConfig",
    "SmokeResult",
    "UpdateInfo",
    "VersionInfo",
    "build_iscc_command",
    "build_pyinstaller_command",
    "build_signtool_command",
    "check_for_update",
    "classify_line",
    "derive_app_id",
    "detect_imports",
    "filter_non_stdlib",
    "find_dangerous_args",
    "find_iscc",
    "format_html",
    "is_newer",
    "is_supported",
    "is_windows",
    "job_config",
    "level_color",
    "generate_iss_script",
    "generate_manifest",
    "generate_version_file",
    "installer_output_path",
    "locate_built_executable",
    "make_jobs",
    "make_record",
    "normalize_name",
    "parse_requirements",
    "parse_version",
    "platform_label",
    "redact_password",
    "resolve_languages",
    "run_smoke_test",
    "split_extra_args",
    "stage_keys",
    "summarize",
    "unsupported_features",
]
