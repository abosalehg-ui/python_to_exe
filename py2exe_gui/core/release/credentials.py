"""Where the GitHub token comes from — and the places it never goes.

The token is read from the operating system's credential store through the
optional ``keyring`` package (Windows Credential Manager, macOS Keychain,
Secret Service), falling back to the ``GITHUB_TOKEN`` environment variable
that CI systems already provide. It is never written to the project file, the
settings, a preset, the build history or a log: this module is the only code
that reads it, and ``redact`` removes it from any text that is shown.
"""

import os
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Optional

KEYRING_SERVICE = "py2exe-gui"
KEYRING_USERNAME = "github-token"
ENV_VAR = "GITHUB_TOKEN"

#: Sentinel: "use the real keyring package if installed".
DEFAULT = object()


class CredentialError(Exception):
    pass


def load_keyring(module=DEFAULT):
    """The ``keyring`` module, or None when it is not installed (it is optional)."""
    if module is not DEFAULT:
        return module
    try:
        import keyring  # noqa: PLC0415 - optional dependency
    except ImportError:
        return None
    return keyring


@dataclass
class Token:
    value: str = field(default="", repr=False)
    #: "keyring", "env" or "" (none found).
    source: str = ""

    def __bool__(self) -> bool:
        return bool(self.value)

    def __repr__(self) -> str:  # never print the secret by accident
        return f"Token(source={self.source!r}, present={bool(self.value)})"


def find_token(env: Optional[Mapping[str, str]] = None, keyring_module=DEFAULT) -> Token:
    """The token from the keyring, else from ``GITHUB_TOKEN``; empty when neither."""
    keyring = load_keyring(keyring_module)
    if keyring is not None:
        try:
            value = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
        except Exception:  # noqa: BLE001 - a broken backend must not stop the env fallback
            value = None
        if value:
            return Token(value.strip(), "keyring")
    environ = os.environ if env is None else env
    value = (environ.get(ENV_VAR) or "").strip()
    if value:
        return Token(value, "env")
    return Token()


def store_token(token: str, keyring_module=DEFAULT) -> None:
    keyring = load_keyring(keyring_module)
    if keyring is None:
        raise CredentialError("keyring is not installed (pip install keyring)")
    token = (token or "").strip()
    if not token:
        raise CredentialError("empty token")
    try:
        keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, token)
    except Exception as e:  # noqa: BLE001 - backend errors vary by platform
        raise CredentialError(redact(str(e), [token])) from e


def delete_token(keyring_module=DEFAULT) -> bool:
    keyring = load_keyring(keyring_module)
    if keyring is None:
        return False
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
    except Exception:  # noqa: BLE001 - "not found" is an exception in keyring
        return False
    return True


def redact(text: str, secrets: Iterable[str]) -> str:
    """``text`` with every secret replaced by ``***``."""
    for secret in secrets:
        if secret and len(secret) >= 4:
            text = text.replace(secret, "***")
    return text
