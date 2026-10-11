"""DoctorController: Project doctor, size lab, build report, Windows Sandbox and the icon studio.

A mixin of MainWindow (py2exe_gui/ui/main_window.py). The window module's
constants and worker classes are read through ``_mw`` at call time so a test
that patches ``py2exe_gui.ui.main_window.X`` reaches this code too.
"""

import os
import time
from dataclasses import replace

from py2exe_gui.constants import (
    APP_NAME,
    APP_VERSION,
)
from py2exe_gui.core import (
    BuildConfig,
    apply_fixes,
    dedupe_findings,
    diagnose_output,
    diagnostic_config,
    examine,
    local_module_names,
    locate_built_executable,
    needs_diagnostic_run,
    readiness_score,
    sort_findings,
)
from py2exe_gui.core.build_report import (
    ReportData,
    parse_versions,
    render_html,
    report_path_for,
    sha256_file,
    write_report,
)
from py2exe_gui.core.build_runner import popen_options
from py2exe_gui.core.diagnostics import build_name, build_root
from py2exe_gui.core.engines import engine_for
from py2exe_gui.core.engines.base import describe_error
from py2exe_gui.core.fixes import (
    ORIGIN_BUILD,
    ORIGIN_RUNTIME,
    Finding,
    finding_resolved,
    fix_is_applied,
)
from py2exe_gui.core.project_scan import project_imports
from py2exe_gui.core.sandbox import generate_wsb, wsb_for_output
from py2exe_gui.core.size_analyzer import (
    analyze,
    exclude_suggestions,
    group_label_key,
    indirect_packages,
    onefile_too_big,
    output_path_for,
    previous_size,
)
from py2exe_gui.core.venv_manager import (
    env_exists,
)
from py2exe_gui.qt import (
    QDesktopServices,
    QMessageBox,
    QUrl,
)
from py2exe_gui.strings import (
    LOCALE_LAYOUT,
    S,
    current_locale,
)

# The side navigation (2.1): six sections, in the order the work happens.
# Each holds one or more of the former tabs; "build" is one composed page.
from py2exe_gui.ui import main_window as _mw  # noqa: E402 - late, see docstring
from py2exe_gui.ui.finding_text import finding_detail, finding_title, fix_label
from py2exe_gui.ui.icon_studio_dialog import IconStudioDialog
from py2exe_gui.ui.tabs.size_tab import size_text


class DoctorController:
    # ─── Project doctor ─────────────────────────────────────────────────

    def on_engine_changed(self):
        """Another engine: re-examine, and say what it cannot do here."""
        if not hasattr(self, "_doctor_timer"):
            return  # still building the window
        self._schedule_doctor()
        self.refresh_engine_status()

    def refresh_engine_status(self):
        if not hasattr(self, "main_tab"):
            return
        config = self._current_config()
        engine = engine_for(config)
        missing = engine.unsupported_features(config)
        missing += [f for f in self._current_project().features_used()
                    if not engine.supports(f) and f not in missing]
        self.main_tab.set_engine_status(missing)

    def _schedule_doctor(self, *_args):
        self._doctor_timer.start()

    def _source_path(self) -> str:
        return self.main_tab.source_input.text().strip()

    def run_doctor(self):
        """Examine the current script and settings, then refresh the views."""
        self._doctor_timer.stop()
        source = self._source_path()
        if not source or not os.path.isfile(source):
            self._doctor_findings = []
            self._source_imports = set()
            self._refresh_doctor_view()
            self.refresh_env_view()
            return
        # Findings from a build of a different script no longer apply.
        if self._build_findings and source != self._build_findings_source:
            self._build_findings = []
        config = self._current_config()
        extra = []
        if config.isolated_env and not env_exists(self._env_dir(source)):
            # Its packages will be installed when it is created; until then
            # there is nothing to ask, so don't report them all as missing.
            is_installed = lambda _module: True  # noqa: E731
            extra.append(Finding("env_not_created", "warning"))
        else:
            is_installed = self._installed_checker(config)
        report = examine(source, config, is_installed=is_installed,
                         extra_features=self._current_project().features_used())
        self._doctor_findings = sort_findings(report.findings + extra)
        self._source_imports = report.imports
        self._refresh_doctor_view()
        self.refresh_env_view()
        self.refresh_engine_status()

    def _refresh_doctor_view(self):
        source = self._source_path()
        has_source = bool(source) and os.path.isfile(source)
        self.doctor_tab.show_findings(
            self._doctor_findings, self._build_findings, has_source=has_source
        )
        self.main_tab.set_readiness(
            self.doctor_tab_score() if has_source else None
        )

    def doctor_tab_score(self) -> int:
        return readiness_score(self._doctor_findings)

    def show_doctor_tab(self):
        self.tabs.setCurrentWidget(self.doctor_tab)

    def _set_build_findings(self, findings, source: str):
        # A fix already in the settings is not a remedy any more (bundling a
        # file that is read by a relative path, say): keep the finding and its
        # advice, drop the no-op fix so it isn't offered again.
        config = self._current_config()
        findings = [
            replace(
                f,
                fixes=tuple(x for x in f.fixes if not fix_is_applied(config, x)),
                alternatives=tuple(x for x in f.alternatives if not fix_is_applied(config, x)),
            )
            for f in findings
        ]
        self._build_findings = sort_findings(dedupe_findings(findings))
        self._build_findings_source = source
        self._refresh_doctor_view()
        if self._build_findings:
            self._append_log(
                S.LOG_DOCTOR_BUILD_FINDINGS.format(count=len(self._build_findings))
            )

    def apply_doctor_fixes(self, fixes, rebuild: bool = False):
        """Apply fixes chosen on the Doctor tab, optionally rebuilding."""
        if not fixes:
            self.notify(S.DOCTOR_NOTHING_SELECTED, "warning")
            return
        if self._build_in_progress():
            QMessageBox.warning(self, S.MSG_WARNING, S.MSG_DIAG_BUSY)
            return
        new_config, applied = apply_fixes(self._current_config(), fixes)
        self._apply_config(new_config)
        for fix in applied:
            self._append_log(S.LOG_DOCTOR_FIX_APPLIED.format(fix=fix_label(fix)))

        # Build/runtime findings whose fixes (or alternative) are now all in
        # place are resolved.
        self._build_findings = [
            f for f in self._build_findings if not finding_resolved(new_config, f)
        ]
        self.run_doctor()
        self._refresh_size_view()
        if rebuild:
            self.start_conversion()

    def _diagnose_build(self, config: BuildConfig):
        """Read the build log and warn file of the build that just ended."""
        findings = diagnose_output(
            "\n".join(self._build_output),
            origin=ORIGIN_BUILD,
            source=config.source,
            source_imports=self._source_imports,
            is_installed=self._installed_checker(config),
            engine=config.engine,
        )
        findings += engine_for(config).build_findings(
            config,
            local_module_names(os.path.dirname(os.path.abspath(config.source))),
            min_mtime=self._build_wall_start,
        )
        self._set_build_findings(findings, config.source)
        return self._build_findings

    def _on_smoke_result(self, config: BuildConfig, passed: bool, output: str):
        """Turn what the built EXE printed into findings."""
        findings = []
        if output and (not passed or "Traceback" in output):
            findings = diagnose_output(
                output,
                origin=ORIGIN_RUNTIME,
                source=config.source,
                source_imports=self._source_imports,
                is_installed=self._installed_checker(config),
                engine=config.engine,
            )
        if findings:
            self._set_build_findings(self._build_findings + findings, config.source)
        if passed and needs_diagnostic_run(config):
            self._append_log(S.LOG_SMOKE_WINDOWED_HINT)

    def start_diagnostic_run(self):
        """Build a console copy of the app, run it, and diagnose its output."""
        if self._build_in_progress():
            QMessageBox.warning(self, S.MSG_WARNING, S.MSG_DIAG_BUSY)
            return
        config = self._current_config()
        if not config.source or not os.path.isfile(config.source):
            QMessageBox.warning(self, S.MSG_WARNING, S.ERR_NO_SOURCE)
            return
        if not config.output_dir:
            config.output_dir = os.path.dirname(os.path.abspath(config.source))
        if config.isolated_env and not env_exists(self._env_dir(config.source)):
            QMessageBox.warning(self, S.MSG_WARNING, S.FINDING_ENV_NOT_CREATED_DETAIL)
            return
        diag = diagnostic_config(config)
        python = self.build_python(config)
        # The same services as the real app (its code may import them), minus
        # anything that would stop on a dialog or reach the network.
        kit_options, error = self._runtime_kit_options(diag, diagnostic=True)
        engine = engine_for(diag)
        if not error:
            cmd, error = engine.build_command(
                diag, python_executable=python, extra_options=kit_options
            )
        if error:
            QMessageBox.warning(self, S.MSG_WARNING, describe_error(error))
            return
        if not self._ensure_engine(engine, python, then=self.start_diagnostic_run):
            return
        try:
            engine.prepare_output(diag)
        except OSError as e:
            self._append_log(S.LOG_OUTPUT_DIR_FAILED.format(error=str(e)))
            QMessageBox.critical(self, S.MSG_ERROR, S.MSG_OUTPUT_DIR_FAILED)
            return

        self.convert_btn.setEnabled(False)
        self.doctor_tab.diagnose_btn.setEnabled(False)
        self._set_busy(S.BUSY_DIAGNOSTIC)  # no stage tracking here

        timeout = max(8.0, float(self.deploy_tab.smoke_timeout.value()))
        self.diagnostic_thread = _mw.DiagnosticThread(
            cmd, diag, timeout=timeout,
            popen_kwargs=popen_options(engine.name, engine.build_env(python)),
        )
        self.diagnostic_thread.log_signal.connect(self._append_log)
        self.diagnostic_thread.finished_signal.connect(
            lambda built, output, build_log: self._on_diagnostic_finished(
                config, built, output, build_log
            )
        )
        self.diagnostic_thread.start()

    def _on_diagnostic_finished(self, config, built: bool, output: str, build_log: str):
        self._clear_busy()
        self.convert_btn.setEnabled(True)
        self.doctor_tab.diagnose_btn.setEnabled(True)

        imports = self._source_imports
        checker = self._installed_checker(config)
        if built:
            findings = diagnose_output(
                output, origin=ORIGIN_RUNTIME, source=config.source,
                source_imports=imports, is_installed=checker, engine=config.engine,
            )
        else:
            findings = diagnose_output(
                build_log, origin=ORIGIN_BUILD, source=config.source,
                source_imports=imports, is_installed=checker, engine=config.engine,
            )
        # The diagnostic run is the freshest evidence: it replaces, not adds to,
        # what the last build reported.
        self._set_build_findings(findings, config.source)
        if built and not findings:
            self._append_log(S.LOG_DIAG_CLEAN)
        self._append_log(S.LOG_DIAG_DONE_FMT.format(count=len(findings)))
        self.show_doctor_tab()

    # ─── Size lab and build report ──────────────────────────────────────

    def _show_size(self, config: BuildConfig, report, previous: int):
        self._size_view = (config, report, previous)
        self._refresh_size_view()

    def _refresh_size_view(self):
        """Render the size lab. Text is built here, so a language switch
        re-renders it in the new language rather than keeping the old one."""
        if self._compare_view is not None:
            self.size_tab.show_compare(*self._compare_view)
        if self._size_view is None:
            self.size_tab.show_size_report(None)
            self.size_tab.show_suggestions([])
            return
        config, report, previous = self._size_view
        imports = project_imports(config.source) if config.source else set()
        # Against the current settings: an exclusion just applied drops out.
        suggestions = exclude_suggestions(report, imports, self._current_config())
        hints = []
        indirect = indirect_packages(report, imports)
        if indirect and not config.isolated_env:
            hints.append(S.SIZE_INDIRECT_FMT.format(
                size=size_text(sum(size for _n, size in indirect)),
                names=", ".join(name for name, _s in indirect[:6]),
            ))
        if onefile_too_big(report, config):
            hints.append(S.SIZE_ONEFILE_SLOW_FMT.format(size=size_text(report.output_bytes)))
        self.size_tab.show_size_report(report, previous, hints)
        self.size_tab.show_suggestions(suggestions)

    def analyze_last_build(self):
        """Re-read the inventory of the current settings' last build."""
        config = self._current_config()
        if not config.source:
            return
        report = analyze(config)
        if not report.ok:
            self._size_view = None
            self._refresh_size_view()
            return
        previous = previous_size(
            self.history.records, config.source, config.output_name, skip=1
        )
        # Re-reading changes no settings, so hints use the settings as they are.
        self._show_size(config, report, previous)

    def _report_labels(self) -> dict:
        keys = (
            "title", "details", "result", "success", "failed", "size_on_disk",
            "contents", "duration", "previous", "app", "date", "source", "output",
            "mode", "onefile", "onedir", "environment", "python", "pyinstaller",
            "platform", "breakdown", "package", "size", "share", "largest_files", "engine",
            "findings", "options", "none", "runtime_kit",
        )
        return {key: getattr(S, f"REPORT_{key.upper()}") for key in keys}

    def _write_build_report(self, config, report, previous, duration, success):
        output = report.output_path or output_path_for(config)
        exe = output if os.path.isfile(output) else locate_built_executable(
            build_root(config), build_name(config), config.onefile, engine=config.engine
        ) or ""
        groups = []
        for group, size in report.ranked(20):
            key = group_label_key(group)
            groups.append((getattr(S, key) if key else group, size))
        versions = parse_versions("\n".join(self._build_output))
        findings = [
            (f.severity, finding_title(f), finding_detail(f))
            for f in self._build_findings + self._doctor_findings
        ]
        data = ReportData(
            app_name=build_name(config),
            source=config.source,
            output_path=output,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            success=success,
            duration_seconds=duration,
            output_bytes=report.output_bytes,
            content_bytes=report.content_bytes,
            previous_bytes=previous,
            sha256=sha256_file(exe),
            onefile=config.onefile,
            environment=S.REPORT_ENV_ISOLATED if config.isolated_env else S.REPORT_ENV_CURRENT,
            python_version=versions.get("python", ""),
            pyinstaller_version=versions.get("pyinstaller", ""),
            engine=(f"Nuitka {versions.get('nuitka', '')}".strip()
                    if config.engine == "nuitka" else ""),
            platform=versions.get("platform", ""),
            command=self._build_command,
            groups=groups,
            largest_files=report.largest_files,
            findings=findings,
            runtime_services=self._runtime_service_labels(config),
        )
        document = render_html(
            data,
            self._report_labels(),
            rtl=LOCALE_LAYOUT.get(current_locale(), "ltr") == "rtl",
            lang=current_locale(),
            generator=S.REPORT_GENERATOR_FMT.format(app=APP_NAME, version=APP_VERSION),
        )
        path = report_path_for(config)
        error = write_report(path, document)
        if error:
            self._append_log(S.LOG_REPORT_FAILED.format(error=error))
            return
        self._last_report_path = path
        self.size_tab.set_report_path(path)
        self._append_log(S.LOG_REPORT_SAVED.format(path=path))

    def open_last_report(self):
        if self._last_report_path and os.path.isfile(self._last_report_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._last_report_path))

    # ─── Windows Sandbox ────────────────────────────────────────────────

    def open_in_sandbox(self):
        """Run the last build on a clean Windows inside Windows Sandbox."""
        config = self._current_config()
        output = output_path_for(config) if config.source else ""
        if not output:
            self.notify(S.MSG_SANDBOX_NO_BUILD, "warning")
            return
        if not _mw.sandbox_available():
            self.notify(S.SANDBOX_UNAVAILABLE.format(path=output), "warning")
            return
        host, exe = wsb_for_output(output, config.onefile)
        path = os.path.join(build_root(config), f"{build_name(config)}.wsb")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(generate_wsb(host, exe))
        except OSError as e:
            self._append_log(S.LOG_SANDBOX_FAILED.format(error=str(e)))
            QMessageBox.critical(self, S.MSG_ERROR, S.MSG_SANDBOX_FILE_FAILED)
            return
        self._append_log(S.LOG_SANDBOX_WRITTEN.format(path=path))
        os.startfile(path)  # Windows only: guarded by _mw.sandbox_available() above

    # ─── Icon studio ────────────────────────────────────────────────────

    def open_icon_studio(self):
        source = self._source_path()
        name = self.main_tab.output_name.text().strip() or (
            os.path.splitext(os.path.basename(source))[0] if source else ""
        )
        start_dir = os.path.dirname(source) if source else ""
        dialog = IconStudioDialog(self, app_name=name, start_dir=start_dir)
        if dialog.exec() and dialog.saved_path:
            self.main_tab.icon_input.setText(dialog.saved_path)
            self._append_log(
                S.LOG_ICON_STUDIO_SAVED.format(sizes="16–256", path=dialog.saved_path)
            )
