"""Platforms: Linux and macOS packages, and the GitHub Actions workflow.

The tab holds the ``[packaging]`` and ``[ci]`` sections of the project.
Building the packages and writing the workflow are the window's job (through
``core.packagers`` and ``core.ci_generator``); the tab shows what this host
can build and what the generated workflow will build elsewhere.
"""

from py2exe_gui.bidi import bidi
from py2exe_gui.core.ci_generator import DEFAULT_TOOL_REQUIREMENT, SECRET_NAMES
from py2exe_gui.core.platform_support import PACKAGE_FORMATS
from py2exe_gui.core.project_file import CiSettings, PackagingSettings
from py2exe_gui.qt import (
    QCheckBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    Qt,
)
from py2exe_gui.strings import S
from py2exe_gui.ui.tabs.base import BaseTab, platform_notice, scrolled_layout
from py2exe_gui.ui.tabs.base import muted_label as _muted
from py2exe_gui.ui.tabs.runtime_tab import _ltr_line


class PlatformsTab(BaseTab):
    """Packages for the other platforms, and a workflow that builds them all."""

    def _build(self):
        layout = scrolled_layout(self, spacing=14)

        layout.addWidget(_muted(S.PLATFORMS_HINT))
        layout.addWidget(self._build_packages_group())
        layout.addWidget(self._build_ci_group())
        layout.addStretch(1)
        self.show_packages_result("", False)

    # ── Packages ───────────────────────────────────────────────────────────

    def _build_packages_group(self) -> QGroupBox:
        group = QGroupBox(S.GROUP_PACKAGES)
        form = QFormLayout(group)
        form.addRow(_muted(S.PACKAGES_HINT))
        notice = platform_notice(*PACKAGE_FORMATS)
        if notice is not None:
            form.addRow(notice)

        formats = QGridLayout()
        self.format_checks = {}
        for column, name in enumerate(PACKAGE_FORMATS):
            check = QCheckBox(getattr(S, f"PACKAGE_{name.upper()}"))
            self.format_checks[name] = check
            formats.addWidget(check, 0, column)
        form.addRow(formats)

        self.maintainer = _ltr_line(S.PACKAGE_MAINTAINER_PLACEHOLDER)
        self.homepage = _ltr_line("https://")
        self.description = QLineEdit()
        self.description.setPlaceholderText(S.PACKAGE_DESCRIPTION_PLACEHOLDER)
        self.categories = _ltr_line(S.PACKAGE_CATEGORIES_PLACEHOLDER)
        self.identifier = _ltr_line(S.PACKAGE_IDENTIFIER_PLACEHOLDER)
        self.deb_section = _ltr_line("utils")
        self.deb_section.setMaximumWidth(160)
        self.deb_depends = _ltr_line("libc6 (>= 2.31)")
        for label, widget in (
            (S.PACKAGE_MAINTAINER_LABEL, self.maintainer),
            (S.PACKAGE_HOMEPAGE_LABEL, self.homepage),
            (S.PACKAGE_DESCRIPTION_LABEL, self.description),
            (S.PACKAGE_CATEGORIES_LABEL, self.categories),
            (S.PACKAGE_IDENTIFIER_LABEL, self.identifier),
            (S.PACKAGE_DEB_SECTION_LABEL, self.deb_section),
            (S.PACKAGE_DEB_DEPENDS_LABEL, self.deb_depends),
        ):
            widget.setAccessibleName(label)
            form.addRow(label, widget)

        row = QHBoxLayout()
        self.build_packages_btn = QPushButton(S.BTN_BUILD_PACKAGES)
        self.build_packages_btn.setObjectName("successBtn")
        self.build_packages_btn.clicked.connect(self.window_action("build_packages"))
        row.addWidget(self.build_packages_btn)
        self.open_packages_btn = QPushButton(S.BTN_OPEN_PACKAGES_FOLDER)
        self.open_packages_btn.clicked.connect(self.window_action("open_packages_folder"))
        row.addWidget(self.open_packages_btn)
        row.addStretch(1)
        form.addRow(row)
        self.packages_result = QLabel()
        self.packages_result.setWordWrap(True)
        self.packages_result.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow(self.packages_result)
        return group

    def show_packages_result(self, text: str, folder_ready: bool):
        self.packages_result.setText(bidi(text) if text else "")
        self.packages_result.setVisible(bool(text))
        self.open_packages_btn.setEnabled(folder_ready)

    def set_running(self, running: bool):
        self.build_packages_btn.setEnabled(not running)

    # ── GitHub Actions ─────────────────────────────────────────────────────

    def _build_ci_group(self) -> QGroupBox:
        group = QGroupBox(S.GROUP_CI)
        form = QFormLayout(group)
        form.addRow(_muted(S.CI_HINT))
        self.ci_python = _ltr_line("3.12")
        self.ci_python.setMaximumWidth(120)
        self.ci_python.setAccessibleName(S.CI_PYTHON_LABEL)
        form.addRow(S.CI_PYTHON_LABEL, self.ci_python)
        self.ci_tool = _ltr_line(DEFAULT_TOOL_REQUIREMENT)
        self.ci_tool.setText(DEFAULT_TOOL_REQUIREMENT)
        self.ci_tool.setAccessibleName(S.CI_TOOL_LABEL)
        form.addRow(S.CI_TOOL_LABEL, self.ci_tool)
        self.ci_sign_windows = QCheckBox(S.CI_SIGN_WINDOWS)
        self.ci_notarize_macos = QCheckBox(S.CI_NOTARIZE_MACOS)
        self.ci_allow_doctor_errors = QCheckBox(S.CI_ALLOW_DOCTOR_ERRORS)
        for check in (self.ci_sign_windows, self.ci_notarize_macos, self.ci_allow_doctor_errors):
            form.addRow(check)
        names = ", ".join(SECRET_NAMES)
        form.addRow(_muted(S.CI_SECRETS_NOTE + "\n" + names))

        row = QHBoxLayout()
        self.generate_ci_btn = QPushButton(S.BTN_GENERATE_CI)
        self.generate_ci_btn.clicked.connect(self.window_action("generate_ci_workflow"))
        row.addWidget(self.generate_ci_btn)
        row.addStretch(1)
        form.addRow(row)
        return group

    # ── The project's sections ─────────────────────────────────────────────

    def packaging_settings(self) -> PackagingSettings:
        return PackagingSettings(
            appimage=self.format_checks["appimage"].isChecked(),
            deb=self.format_checks["deb"].isChecked(),
            dmg=self.format_checks["dmg"].isChecked(),
            maintainer=self.maintainer.text().strip(),
            homepage=self.homepage.text().strip(),
            description=self.description.text().strip(),
            categories=self.categories.text().strip() or "Utility",
            identifier=self.identifier.text().strip(),
            deb_section=self.deb_section.text().strip() or "utils",
            deb_depends=self.deb_depends.text().strip(),
        )

    def ci_settings(self) -> CiSettings:
        return CiSettings(
            python_version=self.ci_python.text().strip() or "3.12",
            sign_windows=self.ci_sign_windows.isChecked(),
            notarize_macos=self.ci_notarize_macos.isChecked(),
            allow_doctor_errors=self.ci_allow_doctor_errors.isChecked(),
        )

    def tool_requirement(self) -> str:
        return self.ci_tool.text().strip() or DEFAULT_TOOL_REQUIREMENT

    def set_packaging_settings(self, packaging: PackagingSettings):
        for name, check in self.format_checks.items():
            check.setChecked(bool(getattr(packaging, name)))
        self.maintainer.setText(packaging.maintainer)
        self.homepage.setText(packaging.homepage)
        self.description.setText(packaging.description)
        self.categories.setText(packaging.categories)
        self.identifier.setText(packaging.identifier)
        self.deb_section.setText(packaging.deb_section)
        self.deb_depends.setText(packaging.deb_depends)

    def set_ci_settings(self, ci: CiSettings):
        self.ci_python.setText(ci.python_version)
        self.ci_sign_windows.setChecked(ci.sign_windows)
        self.ci_notarize_macos.setChecked(ci.notarize_macos)
        self.ci_allow_doctor_errors.setChecked(ci.allow_doctor_errors)

    def read_project(self, project):
        project.packaging = self.packaging_settings()
        project.ci = self.ci_settings()

    def apply_project(self, project, sections=()):
        if "packaging" in sections:
            self.set_packaging_settings(project.packaging)
        if "ci" in sections:
            self.set_ci_settings(project.ci)
