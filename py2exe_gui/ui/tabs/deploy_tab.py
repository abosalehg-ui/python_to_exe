"""Splash screen, Windows manifest, code signing and the smoke test."""

from PyQt5.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from py2exe_gui.core import SigningConfig
from py2exe_gui.strings import S
from py2exe_gui.ui.tabs.base import BaseTab, browse_button


class DeployTab(BaseTab):
    """Everything applied to the EXE after PyInstaller produces it."""

    def _build(self):
        layout = QVBoxLayout(self)

        # ── Splash ──
        splash_group = QGroupBox(S.GROUP_SPLASH)
        splash_layout = QHBoxLayout(splash_group)
        splash_layout.addWidget(QLabel(S.SPLASH_LABEL))
        self.splash_input = QLineEdit()
        self.splash_input.setPlaceholderText(S.SPLASH_PLACEHOLDER)
        splash_btn = browse_button(S.DIALOG_CHOOSE_SPLASH, self.browse_splash_image)
        splash_layout.addWidget(self.splash_input, stretch=4)
        splash_layout.addWidget(splash_btn, stretch=1)
        layout.addWidget(splash_group)

        # ── Manifest ──
        manifest_group = QGroupBox(S.GROUP_MANIFEST)
        manifest_layout = QVBoxLayout(manifest_group)
        manifest_layout.addWidget(QLabel(S.MANIFEST_HINT))

        self.manifest_enable = QCheckBox(S.MANIFEST_ENABLE)
        manifest_layout.addWidget(self.manifest_enable)

        self.manifest_dpi = QCheckBox(S.MANIFEST_DPI)
        self.manifest_admin = QCheckBox(S.MANIFEST_ADMIN)
        manifest_layout.addWidget(self.manifest_dpi)
        manifest_layout.addWidget(self.manifest_admin)

        manifest_layout.addWidget(QLabel(S.MANIFEST_OS_LABEL))
        os_row = QHBoxLayout()
        self.manifest_os = {
            "vista": QCheckBox(S.OS_VISTA),
            "7": QCheckBox(S.OS_7),
            "8": QCheckBox(S.OS_8),
            "8.1": QCheckBox(S.OS_81),
            "10": QCheckBox(S.OS_10),
            "11": QCheckBox(S.OS_11),
        }
        # Default: modern Windows supported.
        for code in ("7", "8", "8.1", "10"):
            self.manifest_os[code].setChecked(True)
        for cb in self.manifest_os.values():
            os_row.addWidget(cb)
        manifest_layout.addLayout(os_row)
        layout.addWidget(manifest_group)

        # ── Signing ──
        signing_group = QGroupBox(S.GROUP_SIGNING)
        signing_layout = QGridLayout(signing_group)
        signing_layout.addWidget(QLabel(S.SIGNING_HINT), 0, 0, 1, 3)

        self.signing_enable = QCheckBox(S.SIGNING_ENABLE)
        signing_layout.addWidget(self.signing_enable, 1, 0, 1, 3)

        # Store mode keeps the certificate password off the command line,
        # where any process running as the same user could read it.
        self.signing_use_store = QCheckBox(S.SIGNING_USE_STORE)
        self.signing_use_store.setToolTip(S.SIGNING_USE_STORE_TIP)
        self.signing_use_store.toggled.connect(self._on_signing_mode_changed)
        signing_layout.addWidget(self.signing_use_store, 6, 0, 1, 3)

        self.signing_subject_label = QLabel(S.SIGNING_SUBJECT_LABEL)
        self.signing_subject = QLineEdit()
        self.signing_subject.setPlaceholderText(S.SIGNING_SUBJECT_PLACEHOLDER)
        signing_layout.addWidget(self.signing_subject_label, 7, 0)
        signing_layout.addWidget(self.signing_subject, 7, 1, 1, 2)

        signing_layout.addWidget(QLabel(S.SIGNING_CERT_LABEL), 2, 0)
        self.signing_cert = QLineEdit()
        self.signing_cert.setPlaceholderText(S.SIGNING_CERT_PLACEHOLDER)
        cert_btn = browse_button(S.DIALOG_CHOOSE_CERT, self.browse_signing_cert)
        signing_layout.addWidget(self.signing_cert, 2, 1)
        signing_layout.addWidget(cert_btn, 2, 2)

        signing_layout.addWidget(QLabel(S.SIGNING_PASSWORD_LABEL), 3, 0)
        self.signing_password = QLineEdit()
        self.signing_password.setEchoMode(QLineEdit.Password)
        self.signing_password.setPlaceholderText(S.SIGNING_PASSWORD_PLACEHOLDER)
        signing_layout.addWidget(self.signing_password, 3, 1, 1, 2)

        signing_layout.addWidget(QLabel(S.SIGNING_TIMESTAMP_LABEL), 4, 0)
        self.signing_timestamp = QLineEdit("http://timestamp.digicert.com")
        signing_layout.addWidget(self.signing_timestamp, 4, 1, 1, 2)

        signing_layout.addWidget(QLabel(S.SIGNING_DESC_LABEL), 5, 0)
        self.signing_description = QLineEdit()
        self.signing_description.setPlaceholderText(S.SIGNING_DESC_PLACEHOLDER)
        signing_layout.addWidget(self.signing_description, 5, 1, 1, 2)

        layout.addWidget(signing_group)

        # ── Smoke test ──
        smoke_group = QGroupBox(S.GROUP_SMOKE)
        smoke_layout = QGridLayout(smoke_group)
        self.smoke_enable = QCheckBox(S.SMOKE_ENABLE)
        smoke_layout.addWidget(self.smoke_enable, 0, 0, 1, 2)
        smoke_layout.addWidget(QLabel(S.SMOKE_TIMEOUT_LABEL), 1, 0)
        self.smoke_timeout = QSpinBox()
        self.smoke_timeout.setRange(1, 60)
        self.smoke_timeout.setValue(5)
        smoke_layout.addWidget(self.smoke_timeout, 1, 1)
        layout.addWidget(smoke_group)

        layout.addStretch()


    # ── Browsing ───────────────────────────────────────────────────────────

    def browse_splash_image(self):
        path = self._choose_file(S.DIALOG_CHOOSE_SPLASH, S.DIALOG_FILTER_IMAGE)
        if path:
            self.splash_input.setText(path)

    def browse_signing_cert(self):
        path = self._choose_file(S.DIALOG_CHOOSE_CERT, S.DIALOG_FILTER_CERT)
        if path:
            self.signing_cert.setText(path)

    # ── Signing ────────────────────────────────────────────────────────────

    def _on_signing_mode_changed(self, use_store: bool):
        """Show only the fields relevant to the selected signing mode."""
        self.signing_subject.setEnabled(use_store)
        self.signing_subject_label.setEnabled(use_store)
        self.signing_cert.setEnabled(not use_store)
        self.signing_password.setEnabled(not use_store)

    def signing_config(self) -> SigningConfig:
        return SigningConfig(
            enabled=self.signing_enable.isChecked(),
            use_cert_store=self.signing_use_store.isChecked(),
            cert_subject=self.signing_subject.text().strip(),
            cert_path=self.signing_cert.text().strip(),
            cert_password=self.signing_password.text(),
            timestamp_url=self.signing_timestamp.text().strip()
            or "http://timestamp.digicert.com",
            description=self.signing_description.text().strip(),
        )

    # ── Manifest ───────────────────────────────────────────────────────────

    def selected_supported_os(self):
        return [code for code, cb in self.manifest_os.items() if cb.isChecked()]
