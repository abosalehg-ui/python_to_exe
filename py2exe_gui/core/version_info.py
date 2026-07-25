"""Generate a PyInstaller --version-file payload from a metadata dataclass."""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class VersionInfo:
    """Windows file metadata embedded into the produced EXE."""

    company_name: str = ""
    file_description: str = ""
    file_version: str = ""  # "1.0.0.0" or empty
    internal_name: str = ""
    legal_copyright: str = ""
    original_filename: str = ""
    product_name: str = ""
    product_version: str = ""  # "1.0.0.0" or empty
    language_id: str = "040904B0"  # US English / Unicode

    def is_empty(self) -> bool:
        """True when no user-facing field is filled."""
        return not any(
            (
                self.company_name,
                self.file_description,
                self.file_version,
                self.internal_name,
                self.legal_copyright,
                self.original_filename,
                self.product_name,
                self.product_version,
            )
        )


def parse_version_tuple(version: str) -> Tuple[int, int, int, int]:
    """Parse '1.2.3' or '1.2.3.4' → (1, 2, 3, 0) / (1, 2, 3, 4). Empty → zeros."""
    if not version:
        return (0, 0, 0, 0)
    parts = version.replace(",", ".").split(".")
    nums = []
    for p in parts[:4]:
        try:
            nums.append(int(p.strip()))
        except ValueError:
            nums.append(0)
    while len(nums) < 4:
        nums.append(0)
    return tuple(nums[:4])  # type: ignore[return-value]


# Characters that would terminate or corrupt a single-quoted Python literal.
_LITERAL_ESCAPES = (
    ("\\", "\\\\"),  # must come first
    ("'", "\\'"),
    ("\n", "\\n"),
    ("\r", "\\r"),
    ("\t", "\\t"),
)


def _escape(value: str) -> str:
    """Escape a user string for a single-quoted Python literal.

    PyInstaller ``eval``s the generated file, so anything able to terminate
    the literal early must be neutralised. The previous version escaped only
    the backslash and the quote, so a pasted multi-line value broke out of the
    string and produced an unparseable file.

    Non-ASCII text is deliberately left as-is rather than run through
    ``unicode_escape``: the file is written as UTF-8 and PyInstaller reads it
    as UTF-8, so an Arabic company name stays readable in the generated file
    instead of becoming a wall of ``\\uXXXX``.
    """
    if not value:
        return ""
    for char, replacement in _LITERAL_ESCAPES:
        value = value.replace(char, replacement)
    # Drop any remaining C0 control characters, which have no legitimate use
    # in file metadata and would otherwise land raw inside the literal.
    return "".join(ch for ch in value if ch >= " " or ch == "\\")


def generate_version_file(info: VersionInfo) -> str:
    """Return the contents of a PyInstaller-compatible version.txt file.

    Format reference: https://pyinstaller.org/en/stable/spec-files.html
    """
    file_vers = parse_version_tuple(info.file_version)
    prod_vers = parse_version_tuple(info.product_version)
    file_version_str = info.file_version or "0.0.0.0"
    product_version_str = info.product_version or "0.0.0.0"

    return (
        "VSVersionInfo(\n"
        "  ffi=FixedFileInfo(\n"
        f"    filevers={file_vers},\n"
        f"    prodvers={prod_vers},\n"
        "    mask=0x3f,\n"
        "    flags=0x0,\n"
        "    OS=0x40004,\n"
        "    fileType=0x1,\n"
        "    subtype=0x0,\n"
        "    date=(0, 0)\n"
        "  ),\n"
        "  kids=[\n"
        "    StringFileInfo(\n"
        "      [\n"
        "      StringTable(\n"
        f"        u'{info.language_id}',\n"
        "        [\n"
        f"        StringStruct(u'CompanyName', u'{_escape(info.company_name)}'),\n"
        f"        StringStruct(u'FileDescription', u'{_escape(info.file_description)}'),\n"
        f"        StringStruct(u'FileVersion', u'{_escape(file_version_str)}'),\n"
        f"        StringStruct(u'InternalName', u'{_escape(info.internal_name)}'),\n"
        f"        StringStruct(u'LegalCopyright', u'{_escape(info.legal_copyright)}'),\n"
        f"        StringStruct(u'OriginalFilename', u'{_escape(info.original_filename)}'),\n"
        f"        StringStruct(u'ProductName', u'{_escape(info.product_name)}'),\n"
        f"        StringStruct(u'ProductVersion', u'{_escape(product_version_str)}')\n"
        "        ]\n"
        "      )\n"
        "      ]\n"
        "    ),\n"
        "    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])\n"
        "  ]\n"
        ")\n"
    )
