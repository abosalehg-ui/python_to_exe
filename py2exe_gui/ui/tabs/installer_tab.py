"""Inno Setup installer configuration."""

from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from py2exe_gui.core import InstallerConfig
from py2exe_gui.core.installer import COMPRESSION_CHOICES, LANGUAGE_LABELS
from py2exe_gui.strings import S
from py2exe_gui.ui.tabs.base import BaseTab, browse_button


class InstallerTab(BaseTab):
    """Turns the built application into a distributable Setup.exe."""

    def _build(self):
        inner = QWidget()
        layout = QVBoxLayout(inner)

        header = QGroupBox(S.GROUP_INSTALLER)
        header_layout = QVBoxLayout(header)
        hint = QLabel(S.INSTALLER_HINT)
        hint.setWordWrap(True)
        header_layout.addWidget(hint)
        self.installer_enable = QCheckBox(S.INSTALLER_ENABLE)
        header_layout.addWidget(self.installer_enable)
        layout.addWidget(header)

        # ── Identity ──
        identity = QGroupBox(S.GROUP_INSTALLER_IDENTITY)
        identity_grid = QGridLayout(identity)

        self.inst_app_name = QLineEdit()
        self.inst_app_name.setPlaceholderText(S.INST_APP_NAME_PLACEHOLDER)
        self.inst_version = QLineEdit("1.0.0")
        self.inst_version.setPlaceholderText(S.INST_VERSION_PLACEHOLDER)
        self.inst_publisher = QLineEdit()
        self.inst_publisher.setPlaceholderText(S.INST_PUBLISHER_PLACEHOLDER)
        self.inst_url = QLineEdit()
        self.inst_url.setPlaceholderText(S.INST_URL_PLACEHOLDER)
        self.inst_app_id = QLineEdit()
        self.inst_app_id.setPlaceholderText(S.INST_APPID_PLACEHOLDER)
        self.inst_app_id.setToolTip(S.INST_APPID_TIP)

        for row, (label, widget) in enumerate(
            [
                (S.INST_APP_NAME_LABEL, self.inst_app_name),
                (S.INST_VERSION_LABEL, self.inst_version),
                (S.INST_PUBLISHER_LABEL, self.inst_publisher),
                (S.INST_URL_LABEL, self.inst_url),
                (S.INST_APPID_LABEL, self.inst_app_id),
            ]
        ):
            identity_grid.addWidget(QLabel(label), row, 0)
            identity_grid.addWidget(widget, row, 1)
        layout.addWidget(identity)

        # ── Output ──
        output = QGroupBox(S.GROUP_INSTALLER_OUTPUT)
        output_grid = QGridLayout(output)

        self.inst_out_dir = QLineEdit()
        self.inst_out_dir.setPlaceholderText(S.INST_OUT_DIR_PLACEHOLDER)
        self.inst_out_name = QLineEdit()
        self.inst_out_name.setPlaceholderText(S.INST_OUT_NAME_PLACEHOLDER)
        self.inst_license = QLineEdit()
        self.inst_license.setPlaceholderText(S.INST_LICENSE_PLACEHOLDER)
        self.inst_readme = QLineEdit()
        self.inst_readme.setPlaceholderText(S.INST_README_PLACEHOLDER)
        self.inst_setup_icon = QLineEdit()
        self.inst_setup_icon.setPlaceholderText(S.INST_SETUP_ICON_PLACEHOLDER)

        browse_rows = [
            (S.INST_OUT_DIR_LABEL, self.inst_out_dir, self.browse_installer_out_dir),
            (S.INST_OUT_NAME_LABEL, self.inst_out_name, None),
            (S.INST_LICENSE_LABEL, self.inst_license, self.browse_installer_license),
            (S.INST_README_LABEL, self.inst_readme, self.browse_installer_readme),
            (S.INST_SETUP_ICON_LABEL, self.inst_setup_icon, self.browse_installer_icon),
        ]
        for row, (label, widget, handler) in enumerate(browse_rows):
            output_grid.addWidget(QLabel(label), row, 0)
            output_grid.addWidget(widget, row, 1)
            if handler is not None:
                btn = browse_button(label, handler)
                output_grid.addWidget(btn, row, 2)
        layout.addWidget(output)

        # ── Options ──
        options = QGroupBox(S.GROUP_INSTALLER_OPTIONS)
        options_grid = QGridLayout(options)

        options_grid.addWidget(QLabel(S.INST_PRIVILEGES_LABEL), 0, 0)
        self.inst_privileges = QComboBox()
        self.inst_privileges.addItem(S.INST_PRIV_ADMIN, "admin")
        self.inst_privileges.addItem(S.INST_PRIV_LOWEST, "lowest")
        options_grid.addWidget(self.inst_privileges, 0, 1)

        options_grid.addWidget(QLabel(S.INST_ARCH_LABEL), 1, 0)
        self.inst_arch = QComboBox()
        self.inst_arch.addItem(S.INST_ARCH_X64, "x64")
        self.inst_arch.addItem(S.INST_ARCH_X86, "x86")
        self.inst_arch.addItem(S.INST_ARCH_ANY, "any")
        options_grid.addWidget(self.inst_arch, 1, 1)

        options_grid.addWidget(QLabel(S.INST_COMPRESSION_LABEL), 2, 0)
        self.inst_compression = QComboBox()
        self.inst_compression.addItems(list(COMPRESSION_CHOICES))
        options_grid.addWidget(self.inst_compression, 2, 1)

        options_grid.addWidget(QLabel(S.INST_LANGUAGES_LABEL), 3, 0)
        lang_box = QWidget()
        lang_layout = QGridLayout(lang_box)
        lang_layout.setContentsMargins(0, 0, 0, 0)
        self.inst_languages = {}
        codes = ["ar"] + list(LANGUAGE_LABELS)
        for i, code in enumerate(codes):
            label = "العربية" if code == "ar" else LANGUAGE_LABELS[code]
            checkbox = QCheckBox(label)
            if code == "en":
                checkbox.setChecked(True)
            self.inst_languages[code] = checkbox
            lang_layout.addWidget(checkbox, i // 4, i % 4)
        options_grid.addWidget(lang_box, 3, 1, 1, 2)

        options_grid.addWidget(QLabel(S.INST_ARABIC_ISL_LABEL), 4, 0)
        self.inst_arabic_isl = QLineEdit()
        self.inst_arabic_isl.setPlaceholderText(S.INST_ARABIC_ISL_PLACEHOLDER)
        self.inst_arabic_isl.setToolTip(S.INST_ARABIC_ISL_TIP)
        isl_btn = browse_button(S.INST_ARABIC_ISL_LABEL, self.browse_arabic_isl)
        options_grid.addWidget(self.inst_arabic_isl, 4, 1)
        options_grid.addWidget(isl_btn, 4, 2)

        options_grid.addWidget(QLabel(S.INST_ASSOC_LABEL), 5, 0)
        self.inst_assoc = QLineEdit()
        self.inst_assoc.setPlaceholderText(S.INST_ASSOC_PLACEHOLDER)
        options_grid.addWidget(self.inst_assoc, 5, 1)

        self.inst_desktop_icon = QCheckBox(S.INST_DESKTOP_ICON)
        self.inst_desktop_icon.setChecked(True)
        self.inst_launch_after = QCheckBox(S.INST_LAUNCH_AFTER)
        self.inst_launch_after.setChecked(True)
        self.inst_allow_dir_change = QCheckBox(S.INST_ALLOW_DIR_CHANGE)
        self.inst_allow_dir_change.setChecked(True)
        self.inst_uninstall_icon = QCheckBox(S.INST_UNINSTALL_ICON)
        self.inst_uninstall_icon.setChecked(True)
        self.inst_sign = QCheckBox(S.INST_SIGN_INSTALLER)
        self.inst_sign.setToolTip(S.INST_SIGN_TIP)
        for i, cb in enumerate(
            [
                self.inst_desktop_icon,
                self.inst_launch_after,
                self.inst_allow_dir_change,
                self.inst_uninstall_icon,
                self.inst_sign,
            ]
        ):
            options_grid.addWidget(cb, 6 + i, 0, 1, 3)
        layout.addWidget(options)

        # ── Toolchain ──
        toolchain = QGroupBox(S.GROUP_INSTALLER_TOOLCHAIN)
        toolchain_layout = QGridLayout(toolchain)
        toolchain_layout.addWidget(QLabel(S.INST_ISCC_LABEL), 0, 0)
        self.inst_iscc_path = QLineEdit()
        self.inst_iscc_path.setPlaceholderText(S.INST_ISCC_PLACEHOLDER)
        toolchain_layout.addWidget(self.inst_iscc_path, 0, 1)
        iscc_btn = browse_button(S.INST_ISCC_LABEL, self.browse_iscc_path)
        toolchain_layout.addWidget(iscc_btn, 0, 2)

        detect_btn = QPushButton(S.BTN_DETECT_ISCC)
        detect_btn.clicked.connect(self.window_action("detect_iscc"))
        toolchain_layout.addWidget(detect_btn, 1, 0)

        gen_btn = QPushButton(S.BTN_GENERATE_ISS)
        gen_btn.clicked.connect(self.window_action("generate_iss_only"))
        toolchain_layout.addWidget(gen_btn, 1, 1)

        build_btn = QPushButton(S.BTN_BUILD_INSTALLER)
        build_btn.setObjectName("successBtn")
        build_btn.clicked.connect(self.window_action("build_installer_now"))
        toolchain_layout.addWidget(build_btn, 1, 2)
        layout.addWidget(toolchain)

        layout.addStretch()

        # Field-dense: keep it usable on a short screen.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)


    # ── Browsing ───────────────────────────────────────────────────────────

    def browse_installer_out_dir(self):
        path = self._choose_dir(S.DIALOG_CHOOSE_OUT_DIR)
        if path:
            self.inst_out_dir.setText(path)

    def browse_installer_license(self):
        path = self._choose_file(S.DIALOG_CHOOSE_LICENSE, S.DIALOG_FILTER_TEXT)
        if path:
            self.inst_license.setText(path)

    def browse_installer_readme(self):
        path = self._choose_file(S.DIALOG_CHOOSE_LICENSE, S.DIALOG_FILTER_TEXT)
        if path:
            self.inst_readme.setText(path)

    def browse_installer_icon(self):
        path = self._choose_file(S.DIALOG_CHOOSE_ICON, S.DIALOG_FILTER_ICON)
        if path:
            self.inst_setup_icon.setText(path)

    def browse_arabic_isl(self):
        path = self._choose_file(S.DIALOG_CHOOSE_ISL, S.DIALOG_FILTER_ISL)
        if path:
            self.inst_arabic_isl.setText(path)

    def browse_iscc_path(self):
        path = self._choose_file(S.DIALOG_CHOOSE_ISCC, S.DIALOG_FILTER_EXE)
        if path:
            self.inst_iscc_path.setText(path)

    # ── Config ─────────────────────────────────────────────────────────────

    def selected_languages(self):
        return [code for code, cb in self.inst_languages.items() if cb.isChecked()]

    def installer_config(self, fallback_name="", fallback_version="",
                         fallback_publisher="", fallback_icon="") -> InstallerConfig:
        """Read the form, falling back to values from the other tabs."""
        return InstallerConfig(
            enabled=self.installer_enable.isChecked(),
            app_name=self.inst_app_name.text().strip() or fallback_name,
            app_version=self.inst_version.text().strip() or fallback_version or "1.0.0",
            publisher=self.inst_publisher.text().strip() or fallback_publisher,
            publisher_url=self.inst_url.text().strip(),
            app_id=self.inst_app_id.text().strip(),
            output_dir=self.inst_out_dir.text().strip(),
            output_base_filename=self.inst_out_name.text().strip(),
            license_file=self.inst_license.text().strip(),
            readme_file=self.inst_readme.text().strip(),
            setup_icon_file=self.inst_setup_icon.text().strip() or fallback_icon,
            languages=self.selected_languages() or ["en"],
            arabic_isl_path=self.inst_arabic_isl.text().strip(),
            privileges=self.inst_privileges.currentData() or "admin",
            architecture=self.inst_arch.currentData() or "x64",
            compression=self.inst_compression.currentText(),
            desktop_icon=self.inst_desktop_icon.isChecked(),
            launch_after_install=self.inst_launch_after.isChecked(),
            allow_dir_change=self.inst_allow_dir_change.isChecked(),
            create_uninstall_icon=self.inst_uninstall_icon.isChecked(),
            associate_extension=self.inst_assoc.text().strip(),
            sign_installer=self.inst_sign.isChecked(),
        )
