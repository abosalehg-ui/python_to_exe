"""Embedding the Runtime Kit: config, validation, files, options, doctor."""

import json
import os
import sys
from dataclasses import replace

import pytest

from p2e_runtime import config as rconfig
from py2exe_gui.core import runtime_kit as rk
from py2exe_gui.core.builder import build_pyinstaller_command, find_dangerous_args
from py2exe_gui.core.config import RUNTIME_SERVICES, BuildConfig, RuntimeKitConfig
from py2exe_gui.core.diagnostics import diagnose_output
from py2exe_gui.core.fixes import (
    FIX_CONSOLE,
    FIX_RUNTIME,
    SNIPPETS,
    Finding,
    Fix,
    apply_fixes,
    finding_resolved,
    fix_is_applied,
    runtime_fix,
)
from py2exe_gui.core.project_doctor import examine

KEY = "ab" * 32
UPDATER = dict(updater=True, update_url="https://example.com/u.json",
               update_public_key=KEY, app_version="1.0.0")
ALL_ON = dict(resource_path=True, log_redirect=True, crash_reporter=True,
              single_instance=True, **UPDATER)


def make_config(tmp_path, code="print('hi')\n", **kit):
    source = tmp_path / "proj" / "app.py"
    source.parent.mkdir(exist_ok=True)
    source.write_text(code)
    return BuildConfig(source=str(source), output_name="Tool",
                       runtime_kit=RuntimeKitConfig(**kit))


# ── RuntimeKitConfig ───────────────────────────────────────────────────────


def test_nothing_is_on_by_default():
    kit = RuntimeKitConfig()
    assert kit.enabled_services() == [] and not kit.enabled
    assert BuildConfig().runtime_kit == kit


def test_round_trip_through_the_settings_dict():
    config = BuildConfig(runtime_kit=RuntimeKitConfig(**ALL_ON, support_url="https://h"))
    data = json.loads(json.dumps(config.to_dict()))
    assert BuildConfig.from_dict(data) == config
    assert data["runtime_kit"]["update_public_key"] == KEY
    assert BuildConfig.from_dict({}).runtime_kit == RuntimeKitConfig()


def test_settings_file_types_are_enforced():
    """Booleans stay booleans and text stays text: no paths, no code."""
    kit = RuntimeKitConfig.from_dict({
        "updater": "true", "log_redirect": 1, "crash_reporter": True,
        "update_url": ["https://x"], "support_url": "https://h", "hook": "/tmp/evil.py",
    })
    assert kit.enabled_services() == ["crash_reporter"]
    assert kit.update_url == "" and kit.support_url == "https://h"
    assert not hasattr(kit, "hook")
    assert RuntimeKitConfig.from_dict("nonsense") == RuntimeKitConfig()


# ── Validation ─────────────────────────────────────────────────────────────


def codes(findings):
    return [f.code for f in findings]


def test_valid_updater_has_no_findings():
    assert rk.validate(RuntimeKitConfig(**UPDATER)) == []


@pytest.mark.parametrize("change,code", [
    ({"update_url": ""}, "kit_update_url_missing"),
    ({"update_url": "http://example.com/u.json"}, "kit_update_url_insecure"),
    ({"update_url": "https://"}, "kit_update_url_insecure"),
    ({"update_public_key": ""}, "kit_update_key_missing"),
    ({"update_public_key": "abc"}, "kit_update_key_invalid"),
    ({"app_version": ""}, "kit_update_version_invalid"),
    ({"app_version": "latest"}, "kit_update_version_invalid"),
])
def test_updater_problems_block_the_build(change, code):
    findings = rk.validate(RuntimeKitConfig(**{**UPDATER, **change}))
    assert codes(findings) == [code]
    assert rk.blocking(findings) == findings


def test_folder_build_note_is_information_only():
    findings = rk.validate(RuntimeKitConfig(**UPDATER), onefile=False)
    assert codes(findings) == ["kit_update_needs_installer"]
    assert rk.blocking(findings) == []


def test_support_url_must_be_web_or_mail():
    bad = RuntimeKitConfig(crash_reporter=True, support_url="file:///etc/passwd")
    assert codes(rk.validate(bad)) == ["kit_support_url_invalid"]
    good = RuntimeKitConfig(crash_reporter=True, support_url="mailto:help@example.com")
    assert rk.validate(good) == []
    # Ignored while the crash reporter is off.
    assert rk.validate(replace(bad, crash_reporter=False)) == []


# ── p2e_runtime.json and the hook ──────────────────────────────────────────


TEXTS = {key: f"<{key}>" for key in rk.TEXT_KEYS}


def test_config_is_accepted_by_the_runtime_parser():
    kit = RuntimeKitConfig(**ALL_ON, support_url="https://help.example",
                           installer_args='/SILENT "/DIR=C:\\My App"')
    data = rk.runtime_config_dict(kit, "Tool", onefile=False, texts=TEXTS, rtl=True)
    parsed = rconfig.parse_config(json.loads(json.dumps(data)))
    assert parsed.enabled() == ["resource_path", "logs", "crash", "single_instance", "updater"]
    assert (parsed.app_name, parsed.app_version, parsed.build, parsed.rtl) == \
        ("Tool", "1.0.0", "onedir", True)
    assert parsed.crash.support_url == "https://help.example"
    assert parsed.crash.message == "<crash_message>" and parsed.crash.dialog
    assert parsed.single_instance.message == "<instance_message>"
    assert parsed.updater.public_key == KEY
    assert parsed.updater.check_on_start is False
    assert parsed.updater.allow_insecure_localhost is False
    assert parsed.updater.prompt_message == "<update_message>"


def test_only_enabled_services_are_written():
    data = rk.runtime_config_dict(RuntimeKitConfig(log_redirect=True), "Tool")
    assert list(data["services"]) == ["logs"]


def test_custom_instance_message_wins():
    kit = RuntimeKitConfig(single_instance=True, instance_message="Busy!")
    data = rk.runtime_config_dict(kit, "Tool", texts=TEXTS)
    assert data["services"]["single_instance"]["message"] == "Busy!"


def test_diagnostic_variant_never_blocks_or_reaches_the_network():
    kit = RuntimeKitConfig(**ALL_ON, update_check_on_start=True)
    normal = rk.runtime_config_dict(kit, "Tool")
    diag = rk.runtime_config_dict(kit, "Tool", diagnostic=True)
    assert normal["services"]["updater"]["check_on_start"] is True
    assert diag["services"]["updater"]["check_on_start"] is False
    assert diag["services"]["crash_reporter"]["dialog"] is False


def test_insecure_localhost_only_when_asked_for():
    kit = RuntimeKitConfig(**UPDATER)
    assert "allow_insecure_localhost" not in rk.runtime_config_dict(kit, "T")["services"]["updater"]
    data = rk.runtime_config_dict(kit, "T", allow_insecure_localhost=True)
    assert data["services"]["updater"]["allow_insecure_localhost"] is True


def test_hook_holds_no_configuration():
    hook = rk.render_hook()
    assert "import p2e_runtime" in hook and "p2e_runtime.install()" in hook
    code = [line for line in hook.splitlines() if line and not line.startswith("#")]
    assert code == ["import p2e_runtime", "p2e_runtime.install()"]


def test_rendered_json_is_unicode_text():
    text = rk.render_runtime_config(RuntimeKitConfig(crash_reporter=True), "أداة",
                                    texts={"crash_title": "خطأ"})
    assert "أداة" in text and "خطأ" in text and text.endswith("\n")


# ── Files and options ──────────────────────────────────────────────────────


def test_nothing_on_writes_nothing(tmp_path):
    config = make_config(tmp_path)
    assert rk.write_kit(config) == ([], [])
    assert not os.path.exists(rk.kit_dir_for(config))
    assert rk.preview_options(config) == []


def test_write_kit_files_and_options(tmp_path):
    config = make_config(tmp_path, **ALL_ON)
    options, errors = rk.write_kit(config, TEXTS, platform="linux")
    assert errors == []
    files = rk.kit_files(config)
    assert files.kit_dir == os.path.join(str(tmp_path / "proj"), "build", "p2e_runtime_kit",
                                         "Tool")
    assert open(files.hook_path).read() == rk.render_hook()
    parsed = rconfig.load_config(files.config_path)
    assert parsed.app_name == "Tool" and parsed.updater.manifest_url.startswith("https://")
    package = os.path.join(files.lib_dir, "p2e_runtime")
    copied = sorted(os.listdir(package))
    assert "__init__.py" in copied and "updates.py" in copied and "_ed25519.py" in copied
    assert all(name.endswith(".py") for name in copied)
    assert options == [
        "--runtime-hook", files.hook_path,
        "--add-data", f"{files.config_path}:.",
        "--paths", files.lib_dir,
        "--hidden-import", "p2e_runtime",
        "--hidden-import", "p2e_runtime.logs",
        "--hidden-import", "p2e_runtime.crash",
        "--hidden-import", "p2e_runtime.single_instance",
        "--hidden-import", "p2e_runtime.updates",
    ]
    assert rk.preview_options(config, platform="linux") == options


def test_only_enabled_service_modules_are_hidden_imports(tmp_path):
    config = make_config(tmp_path, resource_path=True)
    options, _ = rk.write_kit(config, platform="win32")
    hidden = [options[i + 1] for i, o in enumerate(options) if o == "--hidden-import"]
    assert hidden == ["p2e_runtime"]  # no updater → no urllib/ssl in the EXE
    assert f"{rk.kit_files(config).config_path};." in options  # Windows separator


def test_rewriting_replaces_a_stale_copy(tmp_path):
    config = make_config(tmp_path, log_redirect=True)
    rk.write_kit(config)
    stale = os.path.join(rk.kit_files(config).lib_dir, "p2e_runtime", "stale.py")
    open(stale, "w").close()
    rk.write_kit(config)
    assert not os.path.exists(stale)


def test_invalid_kit_writes_nothing(tmp_path):
    config = make_config(tmp_path, updater=True, update_url="http://x/u.json")
    options, errors = rk.write_kit(config)
    assert options == []
    assert set(codes(errors)) == {
        "kit_update_url_insecure", "kit_update_key_missing", "kit_update_version_invalid"}
    assert not os.path.exists(rk.kit_dir_for(config))


def test_missing_package_sources_block_the_build(tmp_path):
    config = make_config(tmp_path, log_redirect=True)
    options, errors = rk.write_kit(config, package_dir="")
    assert options == [] and codes(errors) == ["kit_source_missing"]


def test_runtime_package_dir_finds_the_sources(monkeypatch, tmp_path):
    assert os.path.isfile(os.path.join(rk.runtime_package_dir(), "updates.py"))
    # A frozen converter: the sources come as data inside its own bundle.
    import p2e_runtime

    monkeypatch.setattr(p2e_runtime, "__file__", str(tmp_path / "pyz" / "__init__.pyc"))
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert rk.runtime_package_dir() == ""
    (tmp_path / "p2e_runtime").mkdir()
    (tmp_path / "p2e_runtime" / "__init__.py").write_text("")
    assert rk.runtime_package_dir() == str(tmp_path / "p2e_runtime")


def test_kit_options_go_into_the_command_before_the_script(tmp_path):
    config = make_config(tmp_path, crash_reporter=True)
    config.extra_args = "--log-level WARN"
    options = rk.preview_options(config)
    cmd, error = build_pyinstaller_command(config, python_executable="py",
                                           extra_options=options)
    assert error is None
    assert cmd[-1] == config.source
    hook_at = cmd.index("--runtime-hook")
    assert cmd[hook_at + 1] == rk.kit_files(config).hook_path
    assert hook_at < cmd.index("--log-level")


def test_generated_hook_is_not_an_untrusted_runtime_hook(tmp_path):
    """The app's own --runtime-hook never trips the settings-file warning."""
    config = make_config(tmp_path, **ALL_ON)
    assert find_dangerous_args(config.extra_args) == []
    assert "--runtime-hook" in rk.preview_options(config)
    saved = BuildConfig.from_dict(json.loads(json.dumps(config.to_dict())))
    assert find_dangerous_args(saved.extra_args) == []
    assert "runtime-hook" not in json.dumps(saved.to_dict())


def test_runtime_hook_in_extra_args_still_trips_the_warning(tmp_path):
    config = make_config(tmp_path, **ALL_ON)
    config.extra_args = "--runtime-hook evil.py"
    assert find_dangerous_args(config.extra_args) == ["--runtime-hook"]


# ── Settings someone else wrote ────────────────────────────────────────────


def test_foreign_update_key_is_a_risk():
    kit = RuntimeKitConfig(**UPDATER)
    risks = rk.untrusted_risks(kit, own_public_key="cd" * 32)
    assert [r.code for r in risks] == ["foreign_update_key"]
    assert risks[0].params == {"key": "abab abab abab abab", "url": "https://example.com/u.json"}
    assert rk.untrusted_risks(kit, own_public_key="") != []  # no key of mine at all


def test_own_key_and_disabled_updater_are_not_risks():
    assert rk.untrusted_risks(RuntimeKitConfig(**UPDATER), own_public_key=KEY.upper()) == []
    off = RuntimeKitConfig(**{**UPDATER, "updater": False})
    assert rk.untrusted_risks(off, own_public_key="") == []


def test_support_link_is_shown_before_applying():
    kit = RuntimeKitConfig(crash_reporter=True, support_url="https://phish.example")
    assert [r.code for r in rk.untrusted_risks(kit)] == ["support_url"]


# ── Fixes ──────────────────────────────────────────────────────────────────


def test_runtime_fix_kind():
    fix = runtime_fix("log_redirect")
    assert fix == Fix(FIX_RUNTIME, "log_redirect")
    with pytest.raises(ValueError):
        Fix(FIX_RUNTIME, "keylogger")
    config = BuildConfig()
    assert not fix_is_applied(config, fix)
    new_config, applied = apply_fixes(config, [fix, fix])
    assert applied == [fix]
    assert new_config.runtime_kit.log_redirect and fix_is_applied(new_config, fix)
    assert config.runtime_kit.log_redirect is False  # input untouched


def test_every_service_can_be_a_fix():
    for service in RUNTIME_SERVICES:
        config, _ = apply_fixes(BuildConfig(), [runtime_fix(service)])
        assert config.runtime_kit.enabled_services() == [service]


def test_alternative_resolves_a_finding():
    finding = Finding("stream_in_windowed", "error", {}, (Fix(FIX_CONSOLE),),
                      alternatives=(runtime_fix("log_redirect"),))
    windowed = BuildConfig(windowed=True)
    assert not finding_resolved(windowed, finding)
    assert finding_resolved(replace(windowed, windowed=False), finding)
    assert finding_resolved(
        replace(windowed, runtime_kit=RuntimeKitConfig(log_redirect=True)), finding
    )
    assert not finding_resolved(windowed, Finding("syntax_error", "error"))


# ── Doctor integration ─────────────────────────────────────────────────────


def examine_code(tmp_path, code, **config_changes):
    config = make_config(tmp_path, code)
    config = replace(config, **config_changes)
    return examine(config.source, config, is_installed=lambda m: True)


def by_code(report, code):
    return [f for f in report.findings if f.code == code]


def test_stream_finding_offers_log_redirection_instead_of_the_console(tmp_path):
    report = examine_code(tmp_path, "import sys\nsys.stdout.write('x')\n", windowed=True)
    finding, = by_code(report, "stream_in_windowed")
    assert finding.fixes == (Fix(FIX_CONSOLE),)
    assert finding.alternatives == (runtime_fix("log_redirect"),)


def test_log_redirection_resolves_the_stream_findings(tmp_path):
    code = "import sys\nimport tqdm\nsys.stderr.write('x')\n"
    without = examine_code(tmp_path, code, windowed=True)
    assert by_code(without, "stream_in_windowed") and by_code(without, "package_console_streams")
    assert by_code(without, "package_console_streams")[0].alternatives == (
        runtime_fix("log_redirect"),
    )
    kit = RuntimeKitConfig(log_redirect=True)
    with_kit = examine_code(tmp_path, code, windowed=True, runtime_kit=kit)
    assert not by_code(with_kit, "stream_in_windowed")
    assert not by_code(with_kit, "package_console_streams")


def test_input_is_not_resolved_by_log_redirection(tmp_path):
    kit = RuntimeKitConfig(log_redirect=True)
    report = examine_code(tmp_path, "name = input()\n", windowed=True, runtime_kit=kit)
    assert by_code(report, "input_in_windowed")


def test_relative_paths_snippet_follows_the_kit(tmp_path):
    code = "open('settings.json')\n"
    (tmp_path / "proj").mkdir()
    (tmp_path / "proj" / "settings.json").write_text("{}")
    plain = examine_code(tmp_path, code)
    assert by_code(plain, "relative_paths")[0].snippet == "resource_path"
    kit = examine_code(tmp_path, code, runtime_kit=RuntimeKitConfig(resource_path=True))
    finding, = by_code(kit, "relative_paths")
    assert finding.snippet == "runtime_resource_path"
    assert SNIPPETS["runtime_resource_path"].startswith("from p2e_runtime import resource_path")


def test_code_already_using_the_kit_has_no_relative_path_finding(tmp_path):
    (tmp_path / "proj").mkdir()
    (tmp_path / "proj" / "settings.json").write_text("{}")
    code = "from p2e_runtime import resource_path\nopen(resource_path('settings.json'))\n"
    report = examine_code(tmp_path, code, runtime_kit=RuntimeKitConfig(resource_path=True))
    assert not by_code(report, "relative_paths")


def test_importing_the_kit_while_it_is_off(tmp_path):
    code = "from p2e_runtime import resource_path\n"
    report = examine(make_config(tmp_path, code).source, make_config(tmp_path, code),
                     is_installed=lambda m: False)
    assert not by_code(report, "missing_package")  # never "pip install p2e_runtime"
    finding, = by_code(report, "kit_imported_not_enabled")
    assert finding.fixes == (runtime_fix("resource_path"),)
    on = examine_code(tmp_path, code, runtime_kit=RuntimeKitConfig(resource_path=True))
    assert not by_code(on, "kit_imported_not_enabled")


def test_doctor_reports_kit_settings_problems(tmp_path):
    kit = RuntimeKitConfig(updater=True)
    report = examine_code(tmp_path, "print(1)\n", runtime_kit=kit)
    found = {f.code for f in report.findings}
    assert {"kit_update_url_missing", "kit_update_key_missing",
            "kit_update_version_invalid"} <= found


def test_runtime_streams_none_offers_the_alternative():
    findings = diagnose_output(
        "Traceback (most recent call last):\n  File \"app.py\", line 3, in <module>\n"
        "AttributeError: 'NoneType' object has no attribute 'write'\n",
        origin="runtime",
    )
    finding, = [f for f in findings if f.code == "streams_none"]
    assert finding.alternatives == (runtime_fix("log_redirect"),)
