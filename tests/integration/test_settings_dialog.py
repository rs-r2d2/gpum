"""T058: one settings surface, applied live (FR-020, FR-071, FR-072)."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel

from gpum.core.preferences import Preferences
from gpum.ui.settings_dialog import SettingsDialog


def _dialog(qtbot, *, tray_usable=True, tray_reason=None, autostart=False) -> SettingsDialog:
    prefs = Preferences()
    dialog = SettingsDialog(
        prefs,
        tray_usable=tray_usable,
        tray_reason=tray_reason,
        autostart_enabled=autostart,
        autostart_location="/tmp/xdg/autostart/gpum.desktop",
    )
    qtbot.addWidget(dialog)
    return dialog


class TestLiveApplication:
    def test_interval_change_applies_without_a_restart(self, qtbot) -> None:
        dialog = _dialog(qtbot)
        with qtbot.waitSignal(dialog.settings_changed, timeout=1000):
            dialog._interval.setCurrentIndex(dialog._interval.findData(5000))
        assert dialog._preferences.refresh_interval_ms == 5000

    def test_history_window_change_applies(self, qtbot) -> None:
        dialog = _dialog(qtbot)
        with qtbot.waitSignal(dialog.settings_changed, timeout=1000):
            dialog._history.setCurrentIndex(dialog._history.findData(900))
        assert dialog._preferences.history_window_s == 900

    def test_throttle_toggle_applies(self, qtbot) -> None:
        dialog = _dialog(qtbot)
        with qtbot.waitSignal(dialog.settings_changed, timeout=1000):
            dialog._throttle.setChecked(False)
        assert dialog._preferences.throttle_when_hidden is False


class TestTrayUnavailable:
    def test_toggle_is_disabled_not_silently_ignored(self, qtbot) -> None:
        dialog = _dialog(qtbot, tray_usable=False, tray_reason="AppIndicator not enabled")
        assert dialog._tray.isEnabled() is False

    def test_the_reason_is_shown_to_the_user(self, qtbot) -> None:
        reason = "no status-area host is running on this desktop"
        dialog = _dialog(qtbot, tray_usable=False, tray_reason=reason)
        shown = " ".join(label.text() for label in dialog.findChildren(QLabel))
        assert reason in shown, "the reason must be visible, not just the disabled toggle"

    def test_tray_not_enabled_when_unusable(self, qtbot) -> None:
        dialog = _dialog(qtbot, tray_usable=False, tray_reason="unavailable")
        assert dialog._tray.isChecked() is False


class TestAutostartDisclosure:
    def test_the_written_path_is_disclosed(self, qtbot) -> None:
        """The one accepted deviation from 'modifies nothing but its own preferences' must be
        visible to the user, not buried (plan.md § Complexity Tracking)."""
        dialog = _dialog(qtbot)
        text = " ".join(label.text() for label in dialog.findChildren(QLabel))
        assert "/tmp/xdg/autostart/gpum.desktop" in text
        assert "removes that file" in text

    def test_toggling_emits_rather_than_writing_directly(self, qtbot) -> None:
        """The dialog does not touch the filesystem itself; the application performs the write
        so it stays a single, testable place."""
        dialog = _dialog(qtbot)
        with qtbot.waitSignal(dialog.autostart_toggled, timeout=1000) as blocker:
            dialog._autostart.setChecked(True)
        assert blocker.args == [True]
