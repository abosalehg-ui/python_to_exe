"""Shared fixtures. Makes the project importable from any working directory."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Qt must be told to run headless before any QApplication is created, or
# importing the UI on a machine without a display aborts the process.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    """A single QApplication for the whole session.

    Qt permits only one instance per process, so this is session-scoped and
    reused; individual tests create and close their own windows.
    """
    pytest.importorskip("PyQt5", reason="PyQt5 not installed")
    from PyQt5.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app
    app.processEvents()


@pytest.fixture(autouse=True)
def _restore_locale():
    """Keep locale changes from leaking between tests."""
    from py2exe_gui.strings import current_locale, set_locale

    before = current_locale()
    yield
    set_locale(before)


@pytest.fixture(autouse=True)
def _isolate_credentials(monkeypatch):
    """No test may read the developer's real token, keyring or password.

    The keyring package (optional) is pointed at a backend that refuses
    everything; tests that need a keyring pass an in-memory one.
    """
    for name in ("GITHUB_TOKEN", "P2E_SIGN_PASSWORD", "P2E_LANG"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PYTHON_KEYRING_BACKEND", "keyring.backends.fail.Keyring")


class MemoryKeyring:
    """An in-memory stand-in for the ``keyring`` module."""

    def __init__(self):
        self.store = {}

    def get_password(self, service, user):
        return self.store.get((service, user))

    def set_password(self, service, user, value):
        self.store[(service, user)] = value

    def delete_password(self, service, user):
        if (service, user) not in self.store:
            raise KeyError(user)
        del self.store[(service, user)]
