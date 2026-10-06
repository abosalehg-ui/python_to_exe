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
from py2exe_gui.core.diagnostics import (
    diagnose_output,
    diagnostic_config,
    needs_diagnostic_run,
    parse_warn_file,
    read_warn_findings,
    warn_file_for,
    warn_findings,
)
from py2exe_gui.core.fixes import (
    FINDING_CODES,
    SNIPPETS,
    Finding,
    Fix,
    apply_fixes,
    dedupe_findings,
    readiness_score,
    sort_findings,
)
from py2exe_gui.core.icon_studio import ICO_SIZES, pack_ico, read_ico_sizes
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
from py2exe_gui.core.knowledge import PackageInfo, load_knowledge, lookup, pip_name_for
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
from py2exe_gui.core.project_doctor import (
    DoctorReport,
    examine,
    local_module_names,
)
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
    "FINDING_CODES",
    "ICO_SIZES",
    "LANGUAGE_LABELS",
    "PRIVILEGE_CHOICES",
    "RELEASES_PAGE_URL",
    "SNIPPETS",
    "STAGES",
    "WINDOWS_ONLY",
    "apply_fixes",
    "BatchJob",
    "BatchSummary",
    "build_iscc_command",
    "build_pyinstaller_command",
    "build_signtool_command",
    "BuildConfig",
    "BuildHistory",
    "BuildRecord",
    "BuildStageTracker",
    "check_for_update",
    "classify_line",
    "dedupe_findings",
    "derive_app_id",
    "detect_imports",
    "diagnose_output",
    "diagnostic_config",
    "DoctorReport",
    "examine",
    "filter_non_stdlib",
    "find_dangerous_args",
    "find_iscc",
    "Finding",
    "Fix",
    "format_html",
    "generate_iss_script",
    "generate_manifest",
    "generate_version_file",
    "installer_output_path",
    "InstallerConfig",
    "is_newer",
    "is_supported",
    "is_windows",
    "job_config",
    "level_color",
    "load_knowledge",
    "local_module_names",
    "locate_built_executable",
    "lookup",
    "make_jobs",
    "make_record",
    "ManifestConfig",
    "needs_diagnostic_run",
    "normalize_name",
    "pack_ico",
    "PackageInfo",
    "parse_requirements",
    "parse_version",
    "parse_warn_file",
    "pip_name_for",
    "platform_label",
    "PresetLibrary",
    "read_ico_sizes",
    "read_warn_findings",
    "readiness_score",
    "redact_password",
    "resolve_languages",
    "run_smoke_test",
    "SigningConfig",
    "SmokeResult",
    "sort_findings",
    "split_extra_args",
    "stage_keys",
    "summarize",
    "unsupported_features",
    "UpdateInfo",
    "VersionInfo",
    "warn_file_for",
    "warn_findings",
]
