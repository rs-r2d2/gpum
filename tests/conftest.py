"""Shared test configuration.

Two things are set up before any test runs, both session-wide so no individual test can forget
them:

* the offscreen Qt platform, so the suite runs headless in CI with no display server
  (constitution Principle IV);
* a throwaway settings directory, so the suite can never read or write the developer's real
  preferences. Redirecting per-test proved leaky — a QSettings object constructed before the
  redirect resolves the real path — and the suite was found writing a deliberately-corrupt
  value into ``~/.config/gpum/gpum.conf``.
"""

import os
import tempfile

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

#: Kept for the whole session; QSettings resolves paths lazily and lives past a single test.
_SETTINGS_DIR = tempfile.mkdtemp(prefix="gpum-test-settings-")


@pytest.fixture(scope="session", autouse=True)
def _isolate_settings():
    """Point every QSettings lookup at a temporary directory for the whole run."""
    from PySide6.QtCore import QSettings

    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    for scope in (QSettings.Scope.UserScope, QSettings.Scope.SystemScope):
        QSettings.setPath(QSettings.Format.IniFormat, scope, _SETTINGS_DIR)
        QSettings.setPath(QSettings.Format.NativeFormat, scope, _SETTINGS_DIR)
    yield


@pytest.fixture(autouse=True)
def _clear_settings_between_tests(_isolate_settings):
    """Each test starts from empty settings, so ordering cannot leak state."""
    from PySide6.QtCore import QSettings

    yield
    settings = QSettings("gpum", "gpum")
    settings.clear()
    settings.sync()
