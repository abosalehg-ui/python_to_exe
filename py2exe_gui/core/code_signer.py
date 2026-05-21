"""Pure logic to construct a Windows signtool.exe command.

Actually running signtool is delegated to the UI layer so this module
stays UI- and subprocess-free (and testable).
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class SigningConfig:
    """Parameters needed to sign a Windows executable."""

    enabled: bool = False
    cert_path: str = ""
    cert_password: str = ""
    timestamp_url: str = "http://timestamp.digicert.com"
    digest_algorithm: str = "sha256"
    description: str = ""
    signtool_path: str = "signtool"  # assumes signtool.exe on PATH


def build_signtool_command(
    exe_path: str,
    config: SigningConfig,
) -> Tuple[Optional[List[str]], Optional[str]]:
    """Construct the signtool ``sign`` command for ``exe_path``.

    Returns (command, error). On error, command is None.
    Validates only what we can without touching the filesystem:
    inputs being non-empty. File existence checks belong in the caller.
    """
    if not config.enabled:
        return None, "Signing is disabled"
    if not exe_path:
        return None, "Executable path is required"
    if not config.cert_path:
        return None, "Certificate path is required"

    cmd: List[str] = [config.signtool_path, "sign"]
    cmd.extend(["/f", config.cert_path])

    if config.cert_password:
        cmd.extend(["/p", config.cert_password])

    if config.timestamp_url:
        cmd.extend(["/tr", config.timestamp_url])
        cmd.extend(["/td", config.digest_algorithm])

    cmd.extend(["/fd", config.digest_algorithm])

    if config.description:
        cmd.extend(["/d", config.description])

    cmd.append(exe_path)
    return cmd, None


def redact_password(command: List[str]) -> List[str]:
    """Return a copy of ``command`` with /p values replaced by '***'.

    Use this when logging or displaying the command to avoid leaking the
    certificate password.
    """
    if not command:
        return list(command)
    redacted: List[str] = []
    skip_next = False
    for token in command:
        if skip_next:
            redacted.append("***")
            skip_next = False
            continue
        redacted.append(token)
        if token == "/p":
            skip_next = True
    return redacted
