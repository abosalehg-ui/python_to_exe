"""Application bootstrap."""

import json
import os
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

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


def main() -> int:
    locale = _load_preferred_locale()
    set_locale(locale)

    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
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

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
