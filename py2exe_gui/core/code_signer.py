"""Pure logic to construct a Windows signtool.exe command.

Actually running signtool is delegated to the UI layer so this module
stays UI- and subprocess-free (and testable).
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class SigningConfig:
    """Parameters needed to sign a Windows executable.

    Two modes are supported:

    ``pfx``   — a ``.pfx`` file plus its password. Simple, but signtool takes
                the password as ``/p`` on the command line, and on Windows any
                process running as the same user can read another process's
                command line. Redaction protects the log, not the process table.
    ``store`` — the certificate is installed in the Windows certificate store
                and selected by subject name (``/n``). **No password is ever
                passed as an argument.** Prefer this on shared machines.
    """

    enabled: bool = False
    use_cert_store: bool = False
    cert_subject: str = ""  # store mode: certificate subject name for /n
    cert_path: str = ""     # pfx mode
    cert_password: str = ""  # pfx mode
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

    cmd: List[str] = [config.signtool_path, "sign"]

    if config.use_cert_store:
        if not config.cert_subject:
            return None, "Certificate subject name is required for store signing"
        # /n selects by subject from the user's certificate store — the private
        # key never leaves it and no password is placed on the command line.
        cmd.extend(["/n", config.cert_subject])
    else:
        if not config.cert_path:
            return None, "Certificate path is required"
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
