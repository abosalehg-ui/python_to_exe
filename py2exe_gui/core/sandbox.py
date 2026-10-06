"""Test a build on a clean Windows inside Windows Sandbox.

"It works on my machine" usually means the machine has Python, a DLL or a
data file the target PC lacks. Windows Sandbox (Windows 10/11 Pro, Enterprise
and Education) is a throw-away, clean Windows that starts in seconds. A
``.wsb`` file tells it which host folder to share and what to run at logon,
so double-clicking it launches the freshly built app on a pristine system.

The output folder is mapped read-only: nothing inside the sandbox can modify
the build on the host.
"""

import os
import sys
from typing import Optional
from xml.sax.saxutils import escape

SANDBOX_USER_DESKTOP = r"C:\Users\WDAGUtilityAccount\Desktop"
SANDBOX_APP_DIR = SANDBOX_USER_DESKTOP + r"\app"


def sandbox_executable(env: Optional[dict] = None) -> str:
    """Path of WindowsSandbox.exe on this system, or ''."""
    environ = os.environ if env is None else env
    root = environ.get("SystemRoot") or environ.get("SYSTEMROOT") or r"C:\Windows"
    path = os.path.join(root, "System32", "WindowsSandbox.exe")
    return path if os.path.isfile(path) else ""


def sandbox_available(platform: Optional[str] = None, env: Optional[dict] = None) -> bool:
    """True only on Windows with the Windows Sandbox feature enabled."""
    plat = platform if platform is not None else sys.platform
    return plat == "win32" and bool(sandbox_executable(env))


def generate_wsb(host_folder: str, exe_relative: str, networking: bool = True) -> str:
    """The ``.wsb`` configuration sharing ``host_folder`` and running the EXE.

    ``exe_relative`` is the EXE's path inside ``host_folder``
    (``MyApp.exe`` for a one-file build, ``MyApp.exe`` too for a folder build
    whose folder is the one shared).
    """
    command = SANDBOX_APP_DIR + "\\" + exe_relative.replace("/", "\\")
    net = "Default" if networking else "Disable"
    return (
        "<Configuration>\n"
        "  <MappedFolders>\n"
        "    <MappedFolder>\n"
        f"      <HostFolder>{escape(host_folder)}</HostFolder>\n"
        f"      <SandboxFolder>{escape(SANDBOX_APP_DIR)}</SandboxFolder>\n"
        "      <ReadOnly>true</ReadOnly>\n"
        "    </MappedFolder>\n"
        "  </MappedFolders>\n"
        f"  <Networking>{net}</Networking>\n"
        "  <LogonCommand>\n"
        f'    <Command>"{escape(command)}"</Command>\n'
        "  </LogonCommand>\n"
        "</Configuration>\n"
    )


def wsb_for_output(output_path: str, onefile: bool) -> tuple:
    """(host_folder, exe_relative) for a built one-file EXE or app folder."""
    if onefile:
        return os.path.dirname(output_path), os.path.basename(output_path)
    name = os.path.basename(output_path.rstrip("\\/"))
    exe = name + ".exe" if not name.lower().endswith(".exe") else name
    return output_path, exe
