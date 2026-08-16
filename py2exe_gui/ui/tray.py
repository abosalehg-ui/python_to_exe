"""System tray icon and desktop notifications for long builds.

A PyInstaller run on a real project takes minutes. Until now the only way to
know it had finished was to keep the window in view, because the app had no
tray presence at all and never raised a notification.

Everything here degrades to a no-op when the platform has no system tray
(headless CI, a bare window manager), so callers never have to guard the calls.
"""

from PyQt5.QtWidgets import QAction, QMenu, QSystemTrayIcon

from py2exe_gui.strings import S


class BuildTray:
    """Thin wrapper over QSystemTrayIcon that is safe to construct anywhere.

    ``available`` reports whether a tray actually exists; when it does not,
    ``notify()`` and ``show()`` do nothing rather than raising.
    """

    def __init__(self, window, icon=None):
        self.window = window
        self.tray = None
        self._actions = []
        self.available = QSystemTrayIcon.isSystemTrayAvailable()
        if not self.available:
            return

        self.tray = QSystemTrayIcon(window)
        if icon is not None and not icon.isNull():
            self.tray.setIcon(icon)
        self.tray.setToolTip(S.TRAY_TOOLTIP)
        self.tray.activated.connect(self._on_activated)
        self.tray.setContextMenu(self._build_menu())

    def _build_menu(self) -> QMenu:
        menu = QMenu(self.window)
        for label, slot in (
            (S.TRAY_SHOW, self._restore_window),
            (S.TRAY_CANCEL, self._cancel_build),
            (S.TRAY_QUIT, self.window.close),
        ):
            action = QAction(label, self.window)
            action.triggered.connect(slot)
            menu.addAction(action)
            # Qt does not own these, so keep a reference or they are collected.
            self._actions.append(action)
        return menu

    # ── Actions ────────────────────────────────────────────────────────────

    def _on_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._restore_window()

    def _restore_window(self):
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def _cancel_build(self):
        handler = getattr(self.window, "cancel_conversion", None)
        if handler is not None:
            handler()

    # ── Public API ─────────────────────────────────────────────────────────

    def show(self):
        """Make the tray icon visible, if there is a tray."""
        if self.tray is not None:
            self.tray.show()

    def hide(self):
        if self.tray is not None:
            self.tray.hide()

    def notify(self, title: str, body: str, success: bool = True, msecs: int = 5000):
        """Raise a desktop notification. Silently ignored without a tray.

        Qt routes this through the platform's own notification service, so it
        reaches the user even when the window is minimised or buried.
        """
        if self.tray is None or not self.tray.isVisible():
            return
        icon = (
            QSystemTrayIcon.Information if success else QSystemTrayIcon.Critical
        )
        self.tray.showMessage(title, body, icon, msecs)
