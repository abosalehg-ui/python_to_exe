"""Windows file metadata embedded into the produced EXE."""

from PyQt5.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from py2exe_gui.core import VersionInfo
from py2exe_gui.core.platform_support import VERSION_INFO
from py2exe_gui.strings import S
from py2exe_gui.ui.tabs.base import BaseTab, platform_notice


class VersionInfoTab(BaseTab):
    """Form for the optional Windows file metadata (--version-file)."""

    def _build(self):
        layout = QVBoxLayout(self)

        # These fields become a Windows PE version resource. PyInstaller
        # accepts --version-file anywhere, but an ELF/Mach-O binary has
        # nowhere to put them.
        notice = platform_notice(VERSION_INFO)
        if notice is not None:
            layout.addWidget(notice)

        group = QGroupBox(S.GROUP_VERSION_INFO)
        grid = QGridLayout(group)
        grid.addWidget(QLabel(S.VERSION_INFO_HINT), 0, 0, 1, 2)

        self.vi_company_name = QLineEdit()
        self.vi_file_description = QLineEdit()
        self.vi_file_version = QLineEdit()
        self.vi_file_version.setPlaceholderText(S.VI_PLACEHOLDER_VERSION)
        self.vi_internal_name = QLineEdit()
        self.vi_legal_copyright = QLineEdit()
        self.vi_original_filename = QLineEdit()
        self.vi_product_name = QLineEdit()
        self.vi_product_version = QLineEdit()
        self.vi_product_version.setPlaceholderText(S.VI_PLACEHOLDER_VERSION)

        rows = [
            (S.VI_COMPANY_NAME, self.vi_company_name),
            (S.VI_FILE_DESCRIPTION, self.vi_file_description),
            (S.VI_FILE_VERSION, self.vi_file_version),
            (S.VI_INTERNAL_NAME, self.vi_internal_name),
            (S.VI_LEGAL_COPYRIGHT, self.vi_legal_copyright),
            (S.VI_ORIGINAL_FILENAME, self.vi_original_filename),
            (S.VI_PRODUCT_NAME, self.vi_product_name),
            (S.VI_PRODUCT_VERSION, self.vi_product_version),
        ]
        for i, (label, widget) in enumerate(rows, start=1):
            grid.addWidget(QLabel(label), i, 0)
            grid.addWidget(widget, i, 1)

        layout.addWidget(group)
        layout.addStretch()


    def version_info(self) -> VersionInfo:
        """Read the form into a VersionInfo dataclass."""
        return VersionInfo(
            company_name=self.vi_company_name.text().strip(),
            file_description=self.vi_file_description.text().strip(),
            file_version=self.vi_file_version.text().strip(),
            internal_name=self.vi_internal_name.text().strip(),
            legal_copyright=self.vi_legal_copyright.text().strip(),
            original_filename=self.vi_original_filename.text().strip(),
            product_name=self.vi_product_name.text().strip(),
            product_version=self.vi_product_version.text().strip(),
        )
