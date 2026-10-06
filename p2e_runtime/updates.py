"""Signed self-updates.

The developer publishes two files next to the new build:

* ``update.json`` — ``{version, url, sha256, size, notes, min_version}``;
* ``update.json.sig`` — an Ed25519 signature over ``update.json``'s exact
  bytes, as 128 hexadecimal characters.

``check()`` fetches both over HTTPS, verifies the signature against the public
key embedded in the app *before* reading the JSON, and returns an
``UpdateInfo`` when the version is newer. ``apply()`` downloads the file,
checks its size and SHA-256, and only then swaps it in. Anything unsigned,
tampered with, served over plain HTTP, or redirected to plain HTTP is
refused with an ``UpdateError``; nothing unverified is ever run.

Both calls are synchronous and show nothing: the app decides when to call
them and how to ask its user, from whatever toolkit it uses.

One-file builds are replaced in place: Windows refuses to overwrite a running
EXE but lets it be renamed, so the running file becomes ``<name>.old``, the
new one takes its name, the app restarts, and the next start removes the
``.old``. Folder builds are not swapped in place in this version: the
manifest points to an installer (``Setup.exe``), which is verified and then
launched with the arguments the developer configured.
"""

import hashlib
import hmac
import json
import os
import re
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from p2e_runtime import _ed25519, _native
from p2e_runtime.config import BUILD_ONEDIR, RuntimeConfig, UpdaterConfig
from p2e_runtime.paths import is_frozen

MANIFEST_MAX_BYTES = 64 * 1024
SIGNATURE_MAX_BYTES = 1024
DOWNLOAD_MAX_BYTES = 4 * 1024 ** 3
_CHUNK = 256 * 1024
_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PUBLIC_KEY = re.compile(r"^[0-9a-f]{64}$")

DEFAULT_PROMPT_TITLE = "{app} — update"
DEFAULT_PROMPT_MESSAGE = (
    "Version {version} is available (you have {current}).\n\n{notes}\n\nInstall it now?"
)


class UpdateError(Exception):
    """Why an update was refused. ``code`` is stable; ``detail`` is for logs.

    Codes: ``not_configured``, ``insecure_url``, ``network``, ``too_large``,
    ``bad_signature``, ``bad_manifest``, ``wrong_app``, ``size_mismatch``,
    ``hash_mismatch``, ``min_version``, ``not_frozen``, ``write_failed``,
    ``swap_failed``, ``launch_failed``.
    """

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


# ── Versions ───────────────────────────────────────────────────────────────

_VERSION = re.compile(
    r"^\s*v?(\d+(?:\.\d+)*)(?:[-_.]?(a|alpha|b|beta|c|rc|pre|preview|dev)[-_.]?(\d*))?\s*$",
    re.IGNORECASE,
)
_PRE_RANK = {"dev": 0, "a": 1, "alpha": 1, "b": 2, "beta": 2, "c": 3, "rc": 3, "pre": 3,
             "preview": 3}


def parse_version(text: str) -> Tuple[Tuple[int, ...], int, int]:
    """``"1.2.0rc1"`` → ``((1, 2), 3, 1)``: release, pre-release rank, number.

    A final release ranks above every pre-release of the same number
    (``1.0.0 > 1.0.0rc2 > 1.0.0b1``). Trailing zeros are ignored
    (``1.2 == 1.2.0``). Raises ``ValueError`` for anything else.
    """
    match = _VERSION.match(text or "")
    if not match:
        raise ValueError(f"not a version: {text!r}")
    release = [int(part) for part in match.group(1).split(".")]
    while len(release) > 1 and release[-1] == 0:
        release.pop()
    tag = (match.group(2) or "").lower()
    if not tag:
        return tuple(release), 99, 0
    return tuple(release), _PRE_RANK[tag], int(match.group(3) or 0)


def compare_versions(a: str, b: str) -> int:
    """-1, 0 or 1 as ``a`` is older than, equal to or newer than ``b``."""
    left, right = parse_version(a), parse_version(b)
    return (left > right) - (left < right)


def is_newer(candidate: str, current: str) -> bool:
    return compare_versions(candidate, current) > 0


# ── URLs and HTTP ──────────────────────────────────────────────────────────


def check_url(url: str, allow_insecure_localhost: bool = False) -> str:
    """Accept ``https://`` only (plus ``http://localhost`` behind the test flag)."""
    try:
        parts = urllib.parse.urlsplit(url or "")
        host = (parts.hostname or "").lower()
    except ValueError as e:
        raise UpdateError("insecure_url", str(e)) from e
    scheme = parts.scheme.lower()
    if scheme == "https" and host:
        return url
    if allow_insecure_localhost and scheme == "http" and host in _LOCAL_HOSTS:
        return url
    raise UpdateError("insecure_url", url)


def signature_url_for(manifest_url: str) -> str:
    """``.../update.json?x=1`` → ``.../update.json.sig?x=1``."""
    parts = urllib.parse.urlsplit(manifest_url)
    return urllib.parse.urlunsplit(parts._replace(path=parts.path + ".sig"))


class _SafeRedirects(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only to a URL that passes ``check_url`` itself.

    Without this, ``https://`` → ``http://`` would silently downgrade the
    connection (urllib follows such redirects by default).
    """

    def __init__(self, allow_insecure_localhost: bool):
        super().__init__()
        self.allow_insecure_localhost = allow_insecure_localhost

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl, self.allow_insecure_localhost)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def build_opener(allow_insecure_localhost: bool = False) -> urllib.request.OpenerDirector:
    """An opener that verifies certificates and refuses insecure redirects."""
    return urllib.request.build_opener(
        _SafeRedirects(allow_insecure_localhost),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
    )


def _open(opener, url: str, timeout: float):
    request = urllib.request.Request(url, headers={"User-Agent": "p2e_runtime-updater"})
    try:
        response = opener.open(request, timeout=timeout)
    except UpdateError:
        raise
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise UpdateError("network", f"{url}: {e}") from e
    # The final URL after redirects: urllib exposes it as geturl().
    return response


def _read_limited(response, limit: int, what: str) -> bytes:
    data = response.read(limit + 1)
    if len(data) > limit:
        raise UpdateError("too_large", f"{what} exceeds {limit} bytes")
    return data


# ── Manifest ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class UpdateInfo:
    """A verified update offer. Only ever built from a signed manifest."""

    version: str
    url: str
    sha256: str
    size: int
    notes: str = ""
    min_version: str = ""
    current_version: str = ""

    @property
    def applicable(self) -> bool:
        """False when the running version is older than ``min_version``.

        Such a user must install an intermediate version (or reinstall)
        instead of updating directly; ``apply()`` refuses.
        """
        if not self.min_version or not self.current_version:
            return True
        return compare_versions(self.current_version, self.min_version) >= 0


def decode_public_key(text: str) -> bytes:
    key = (text or "").strip().lower()
    if not _PUBLIC_KEY.match(key):
        raise UpdateError("not_configured", "the public key must be 64 hex characters")
    return bytes.fromhex(key)


def decode_signature(data: bytes) -> bytes:
    text = data.decode("ascii", "replace").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{128}", text):
        raise UpdateError("bad_signature", "signature file is not 128 hex characters")
    return bytes.fromhex(text)


def verify_manifest(manifest: bytes, signature: bytes, public_key: str) -> None:
    """Raise ``UpdateError('bad_signature')`` unless the signature is valid."""
    key = decode_public_key(public_key)
    if not _ed25519.verify(key, manifest, decode_signature(signature)):
        raise UpdateError("bad_signature", "the manifest is not signed by this app's key")


def parse_manifest(data: bytes, app_name: str = "", allow_insecure_localhost: bool = False
                   ) -> Dict[str, Any]:
    """Validate a manifest whose signature has *already* been verified."""
    try:
        manifest = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as e:
        raise UpdateError("bad_manifest", f"not JSON: {e}") from e
    if not isinstance(manifest, dict):
        raise UpdateError("bad_manifest", "not a JSON object")

    def text(key: str, required: bool = True) -> str:
        value = manifest.get(key, "")
        if not isinstance(value, str) or (required and not value):
            raise UpdateError("bad_manifest", f"'{key}' must be a non-empty string")
        return value

    version = text("version")
    min_version = text("min_version", required=False)
    try:
        parse_version(version)
        if min_version:
            parse_version(min_version)
    except ValueError as e:
        raise UpdateError("bad_manifest", str(e)) from e
    url = check_url(text("url"), allow_insecure_localhost)
    sha256 = text("sha256").lower()
    if not _SHA256.match(sha256):
        raise UpdateError("bad_manifest", "'sha256' must be 64 hex characters")
    size = manifest.get("size")
    if isinstance(size, bool) or not isinstance(size, int) or not 0 < size <= DOWNLOAD_MAX_BYTES:
        raise UpdateError("bad_manifest", "'size' must be a positive integer")
    notes = manifest.get("notes", "")
    if not isinstance(notes, str):
        raise UpdateError("bad_manifest", "'notes' must be a string")
    app = manifest.get("app")
    if app is not None and app_name and app != app_name:
        # A manifest signed with the same key for another of the developer's apps.
        raise UpdateError("wrong_app", f"manifest is for {app!r}")
    return {"version": version, "url": url, "sha256": sha256, "size": size,
            "notes": notes, "min_version": min_version}


# ── Configuration ──────────────────────────────────────────────────────────


def _runtime_config(config: Optional[RuntimeConfig]) -> RuntimeConfig:
    if config is None:
        import p2e_runtime

        config = p2e_runtime.current_config()
    if config is None or config.updater is None:
        raise UpdateError("not_configured", "the updater is not enabled in p2e_runtime.json")
    return config


def _updater(config: RuntimeConfig) -> UpdaterConfig:
    assert config.updater is not None
    return config.updater


# ── Check ──────────────────────────────────────────────────────────────────


def check(config: Optional[RuntimeConfig] = None, current_version: Optional[str] = None,
          opener: Optional[urllib.request.OpenerDirector] = None) -> Optional[UpdateInfo]:
    """Return the verified newer version on offer, or ``None``.

    Raises ``UpdateError`` when the offer cannot be trusted (bad signature,
    malformed manifest, insecure URL) or cannot be fetched, so that "no
    update" is never confused with "an update I had to refuse".
    """
    config = _runtime_config(config)
    updater = _updater(config)
    allow = updater.allow_insecure_localhost
    current = current_version if current_version is not None else config.app_version
    try:
        parse_version(current)
    except ValueError as e:
        raise UpdateError("not_configured", f"app version: {e}") from e
    decode_public_key(updater.public_key)  # fail early on a missing key

    manifest_url = check_url(updater.manifest_url, allow)
    signature_url = check_url(updater.signature_url or signature_url_for(manifest_url), allow)
    opener = opener or build_opener(allow)

    with _open(opener, manifest_url, updater.timeout) as response:
        manifest = _read_limited(response, MANIFEST_MAX_BYTES, "update.json")
    with _open(opener, signature_url, updater.timeout) as response:
        signature = _read_limited(response, SIGNATURE_MAX_BYTES, "update.json.sig")

    verify_manifest(manifest, signature, updater.public_key)
    fields = parse_manifest(manifest, config.app_name, allow)
    if not is_newer(fields["version"], current):
        return None
    return UpdateInfo(current_version=current, **fields)


# ── Download ───────────────────────────────────────────────────────────────


def download(info: UpdateInfo, destination: str, config: Optional[RuntimeConfig] = None,
             opener: Optional[urllib.request.OpenerDirector] = None) -> str:
    """Download ``info.url`` to ``destination`` and verify size and SHA-256.

    The file is removed again if anything does not match.
    """
    config = _runtime_config(config)
    updater = _updater(config)
    allow = updater.allow_insecure_localhost
    url = check_url(info.url, allow)
    opener = opener or build_opener(allow)
    digest = hashlib.sha256()
    received = 0
    try:
        out = open(destination, "wb")
    except OSError as e:
        raise UpdateError("write_failed", f"{destination}: {e}") from e
    try:
        with out, _open(opener, url, updater.timeout) as response:
            while True:
                try:
                    chunk = response.read(_CHUNK)
                except OSError as e:
                    raise UpdateError("network", f"{url}: {e}") from e
                if not chunk:
                    break
                received += len(chunk)
                if received > info.size:
                    raise UpdateError("size_mismatch", f"more than the {info.size} bytes promised")
                digest.update(chunk)
                try:
                    out.write(chunk)
                except OSError as e:
                    raise UpdateError("write_failed", f"{destination}: {e}") from e
        if received != info.size:
            raise UpdateError("size_mismatch", f"got {received} bytes, expected {info.size}")
        if not hmac.compare_digest(digest.hexdigest(), info.sha256.lower()):
            raise UpdateError("hash_mismatch", "SHA-256 does not match the signed manifest")
    except BaseException:
        _remove_quietly(destination)
        raise
    return destination


# ── Apply ──────────────────────────────────────────────────────────────────


class System:
    """The operations ``apply`` performs on the machine, injectable for tests."""

    def __init__(self, platform: Optional[str] = None, frozen: Optional[bool] = None,
                 executable: Optional[str] = None):
        self.platform = platform if platform is not None else sys.platform
        self.frozen = is_frozen() if frozen is None else frozen
        self.executable = executable or sys.executable
        self.pid = os.getpid()

    def exists(self, path: str) -> bool:
        return os.path.exists(path)

    def rename(self, src: str, dst: str) -> None:
        os.rename(src, dst)

    def replace(self, src: str, dst: str) -> None:
        os.replace(src, dst)

    def remove(self, path: str) -> None:
        os.remove(path)

    def make_executable(self, path: str, like: str = "") -> None:
        """POSIX only: the new file gets the old one's mode, executable."""
        mode = os.stat(like or path).st_mode & 0o777
        os.chmod(path, mode | 0o500)

    def mkdtemp(self) -> str:
        return tempfile.mkdtemp(prefix="p2e-update-")

    def spawn(self, command: List[str], env: Optional[Dict[str, str]] = None) -> None:
        kwargs: Dict[str, Any] = {"close_fds": True, "env": env}
        if self.platform == "win32":
            # Detach from the console of the process that is about to exit.
            kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED | NEW_GROUP
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen(command, **kwargs)

    def exit(self, code: int = 0) -> None:
        raise SystemExit(code)


def relaunch_environment(environ: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """The environment for starting a *new, independent* copy of the app.

    A PyInstaller one-file app passes its extraction folder to its own child
    process through ``_PYI_*`` variables. A relaunched app that inherited them
    would use the old process's folder, which is deleted when it exits.
    PyInstaller 6.9+ honours ``PYINSTALLER_RESET_ENVIRONMENT``; the variables
    are also dropped for older bootloaders.
    """
    env = dict(os.environ if environ is None else environ)
    for key in list(env):
        if key.startswith("_PYI_") or key == "_MEIPASS2":
            del env[key]
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


def _release_instance_lock() -> None:
    # Only if the single-instance guard is in use: never import it otherwise.
    guard = sys.modules.get("p2e_runtime.single_instance")
    if guard is not None:
        guard.release()


def installer_command(path: str, args: Sequence[str], platform: Optional[str] = None
                      ) -> List[str]:
    plat = platform if platform is not None else sys.platform
    if plat == "win32" and path.lower().endswith(".msi"):
        return ["msiexec", "/i", path, *args]
    return [path, *args]


def _download_name(url: str) -> str:
    name = os.path.basename(urllib.parse.urlsplit(url).path)
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return name or "update-setup.exe"


def swap_executable(target: str, new_file: str, system: System) -> str:
    """Put ``new_file`` in place of the running ``target``; returns the .old path.

    The running file is renamed, never overwritten (Windows allows the first
    and refuses the second). If moving the new file in fails, the rename is
    undone so the app is never left without its executable.
    """
    old = target + ".old"
    if system.exists(old):
        try:
            system.remove(old)
        except OSError:
            old = f"{target}.{system.pid}.old"  # a previous .old still in use
    try:
        system.rename(target, old)
    except OSError as e:
        raise UpdateError("swap_failed", f"cannot rename the running program: {e}") from e
    try:
        system.replace(new_file, target)
    except OSError as e:
        try:
            system.rename(old, target)
        except OSError:
            pass
        raise UpdateError("swap_failed", f"cannot move the new version in place: {e}") from e
    if system.platform != "win32":
        try:
            system.make_executable(target, like=old)
        except OSError:
            pass
    return old


def apply(info: UpdateInfo, config: Optional[RuntimeConfig] = None, restart: bool = True,
          relaunch_args: Optional[Sequence[str]] = None,
          opener: Optional[urllib.request.OpenerDirector] = None,
          system: Optional[System] = None) -> str:
    """Download, verify, and install ``info``.

    One-file builds: swap the executable, start the new version (with
    ``relaunch_args``, default: this run's arguments) and exit this process
    when ``restart`` is true. Folder builds: launch the verified installer
    with the configured arguments, then exit when ``restart`` is true.
    Returns the downloaded file's final path.
    """
    config = _runtime_config(config)
    updater = _updater(config)
    system = system or System()
    if not info.applicable:
        raise UpdateError("min_version", f"{info.current_version} < {info.min_version}")

    if config.build == BUILD_ONEDIR:
        folder = system.mkdtemp()
        path = download(info, os.path.join(folder, _download_name(info.url)), config, opener)
        if system.platform != "win32":
            try:
                system.make_executable(path)
            except OSError:
                pass
        _release_instance_lock()
        try:
            system.spawn(installer_command(path, updater.installer_args, system.platform))
        except OSError as e:
            raise UpdateError("launch_failed", str(e)) from e
        if restart:
            system.exit(0)
        return path

    if not system.frozen:
        raise UpdateError("not_frozen", "only a built executable can replace itself")
    target = os.path.abspath(system.executable)
    staged = target + ".new"
    download(info, staged, config, opener)
    swap_executable(target, staged, system)
    if restart:
        args = list(sys.argv[1:] if relaunch_args is None else relaunch_args)
        _release_instance_lock()
        try:
            system.spawn([target, *args], relaunch_environment())
        except OSError as e:
            raise UpdateError("launch_failed", str(e)) from e
        system.exit(0)
    return target


# ── Housekeeping ───────────────────────────────────────────────────────────


def old_files(executable: str) -> List[str]:
    folder, name = os.path.split(os.path.abspath(executable))
    try:
        entries = os.listdir(folder)
    except OSError:
        return []
    pattern = re.compile(re.escape(name) + r"(\.\d+)?\.old$")
    return [os.path.join(folder, e) for e in entries if pattern.match(e)]


def cleanup_old(executable: Optional[str] = None, attempts: int = 1, delay: float = 0.5) -> int:
    """Delete ``<exe>.old`` left by the previous update; returns how many.

    Right after a restart the old process may still be exiting and Windows
    keeps its file locked, hence the retries.
    """
    exe = executable or sys.executable
    removed = 0
    for attempt in range(max(1, attempts)):
        pending = old_files(exe)
        for path in pending:
            try:
                os.remove(path)
                removed += 1
            except OSError:
                pass
        if not old_files(exe):
            break
        if attempt + 1 < attempts:
            time.sleep(delay)
    return removed


def _remove_quietly(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def on_start(config: RuntimeConfig,
             ask: Optional[Callable[..., Optional[bool]]] = None) -> Optional[UpdateInfo]:
    """What ``p2e_runtime.install()`` does at start-up for the updater.

    Removes a previous ``.old`` (in the background, so start-up never waits),
    and — only if the developer turned on ``check_on_start`` — checks once and
    asks the user with a native Yes/No dialog. Where no native dialog exists
    nothing is asked and nothing is installed. Errors are reported on stderr
    and never stop the app.
    """
    if is_frozen() and config.build != BUILD_ONEDIR:
        threading.Thread(
            target=cleanup_old, kwargs={"attempts": 20}, name="p2e-cleanup", daemon=True
        ).start()
    updater = config.updater
    if updater is None or not updater.check_on_start:
        return None
    if ask is None and _native.dialogs_disabled():
        return None  # running unattended: nobody to ask, so don't even check
    ask = ask or _native.show
    try:
        info = check(config)
        if info is None or not info.applicable:
            return info
        fields = {"app": config.app_name, "version": info.version,
                  "current": info.current_version, "notes": info.notes}
        title = _fill(updater.prompt_title or DEFAULT_PROMPT_TITLE, fields)
        text = _fill(updater.prompt_message or DEFAULT_PROMPT_MESSAGE, fields)
        if ask(text, title, _native.KIND_QUESTION, True, config.rtl):
            apply(info, config)
        return info
    except UpdateError as e:
        _native.to_stderr(f"[p2e_runtime] update check failed: {e}")
        return None


def _fill(template: str, fields: Dict[str, str]) -> str:
    try:
        return template.format(**fields)
    except (KeyError, IndexError, ValueError):
        return template
