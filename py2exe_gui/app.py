"""Application bootstrap.

``py2exe-gui`` with no arguments opens the window; ``py2exe-gui <command>``
runs the command line (``py2exe_gui.cli``). PyQt5 is imported only on the GUI
path, so the command line works where Qt is not installed.
"""

import json
import os
import sys

from py2exe_gui.constants import SETTINGS_FILE
from py2exe_gui.strings import DEFAULT_LOCALE, LOCALE_LAYOUT, set_locale


def _load_preferred_locale() -> str:
    """Read the persisted locale preference (without depending on MainWindow)."""
    if not os.path.exists(SETTINGS_FILE):
        return DEFAULT_LOCALE
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            return json.load(f).get("locale", DEFAULT_LOCALE)
    except Exception:
        return DEFAULT_LOCALE


def run_gui(open_path: str = "") -> int:
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont
    from PyQt5.QtWidgets import QApplication

    locale = _load_preferred_locale()
    set_locale(locale)

    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv[:1])
    direction = (
        Qt.RightToLeft if LOCALE_LAYOUT.get(locale, "rtl") == "rtl" else Qt.LeftToRight
    )
    app.setLayoutDirection(direction)
    app.setFont(QFont("Segoe UI", 10))

    # Import here so it picks up the locale already set above.
    from py2exe_gui.ui.main_window import MainWindow

    window = MainWindow()
    window.show()
    # Blocking work (first-run dialog, opt-in update check) runs once the
    # window is actually on screen, not during construction.
    window.run_startup_tasks()
    if open_path:
        window.open_project_path(open_path)

    return app.exec_()


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    from py2exe_gui.cli import is_cli_invocation

    if is_cli_invocation(argv):
        from py2exe_gui.cli import main as cli_main

        return cli_main(argv)
    # "py2exe-gui path/to/p2e.toml" opens that project in the window.
    open_path = argv[0] if argv and argv[0].lower().endswith(".toml") else ""
    return run_gui(open_path)


if __name__ == "__main__":
    sys.exit(main())
