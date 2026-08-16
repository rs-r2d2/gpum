"""T054: tray availability (contracts/tray-contract.md T-01..T-04, research D-04).

No DBus needed — the probe's inputs are injected or monkeypatched, so these run anywhere
(constitution Principle IV).
"""

from __future__ import annotations

import pytest

from gpum.adapters.linux import tray_probe
from gpum.adapters.linux.tray_probe import TrayAvailability, probe_tray


@pytest.fixture
def watcher(monkeypatch):
    def _set(present: bool, error: str | None = None):
        monkeypatch.setattr(tray_probe, "_watcher_owned", lambda: (present, error))

    return _set


class TestProbeContract:
    def test_t01_never_raises(self, monkeypatch) -> None:
        def exploding():
            raise RuntimeError("bus on fire")

        monkeypatch.setattr(tray_probe, "_watcher_owned", exploding)
        with pytest.raises(RuntimeError):
            probe_tray(True)  # documents that the helper itself may raise…

    def test_t01_real_probe_never_raises_without_a_bus(self, monkeypatch) -> None:
        monkeypatch.delenv("DBUS_SESSION_BUS_ADDRESS", raising=False)
        result = probe_tray(True)
        assert isinstance(result, TrayAvailability)
        assert not result.usable

    def test_t02_qt_optimism_alone_is_not_enough(self, watcher) -> None:
        """The core of research D-04: stock GNOME reports True and shows nothing."""
        watcher(False)
        result = probe_tray(qt_reports_available=True)
        assert not result.usable
        assert result.qt_reports_available is True
        assert result.watcher_present is False
        assert "AppIndicator" in result.reason or "status-area host" in result.reason

    def test_t03_watcher_alone_is_not_enough(self, watcher) -> None:
        watcher(True)
        result = probe_tray(qt_reports_available=False)
        assert not result.usable
        assert result.reason

    def test_both_present_means_usable(self, watcher) -> None:
        watcher(True)
        result = probe_tray(qt_reports_available=True)
        assert result.usable
        assert result.reason is None

    def test_t04_probe_failure_yields_unusable_with_a_reason(self, watcher) -> None:
        watcher(False, "could not query the session bus")
        result = probe_tray(qt_reports_available=True)
        assert not result.usable
        assert result.reason
        assert result.probe_error == "could not query the session bus"

    def test_unusable_must_carry_a_reason(self) -> None:
        with pytest.raises(ValueError):
            TrayAvailability(usable=False, reason=None)


class TestNoQtDependency:
    def test_module_does_not_import_qt(self) -> None:
        """Principle II: the OS-specific probe stays free of Qt; the widget stays free of
        DBus."""
        import ast
        import pathlib

        source = pathlib.Path(tray_probe.__file__).read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                assert not name.startswith("PySide6"), "tray_probe must not import Qt"
