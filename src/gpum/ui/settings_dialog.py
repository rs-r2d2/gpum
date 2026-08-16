"""One settings surface (FR-020, FR-071, FR-072).

Two things here are deliberate rather than incidental:

* When a status-area icon cannot be displayed, the toggle is disabled **with the reason shown**
  rather than silently ignored. A preference that quietly does nothing is worse than one that
  explains itself.
* Enabling autostart discloses that it writes a file, and where. That write is the project's
  one accepted deviation from "modifies nothing but its own preferences", so it is surfaced to
  the user rather than buried (plan.md § Complexity Tracking).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from gpum.core.preferences import Preferences

__all__ = ["SettingsDialog"]

_INTERVALS = [("0.5 s", 500), ("1 s", 1000), ("2 s", 2000), ("5 s", 5000), ("10 s", 10000)]
_WINDOWS = [("1 minute", 60), ("5 minutes", 300), ("15 minutes", 900), ("1 hour", 3600)]


class SettingsDialog(QDialog):
    settings_changed = Signal()
    autostart_toggled = Signal(bool)

    def __init__(
        self,
        preferences: Preferences,
        *,
        tray_usable: bool,
        tray_reason: str | None,
        autostart_enabled: bool,
        autostart_location: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("GPUM settings")
        self._preferences = preferences

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self._interval = QComboBox()
        for label, value in _INTERVALS:
            self._interval.addItem(label, value)
        index = self._interval.findData(preferences.refresh_interval_ms)
        self._interval.setCurrentIndex(index if index >= 0 else 1)
        form.addRow("Refresh every", self._interval)

        self._history = QComboBox()
        for label, value in _WINDOWS:
            self._history.addItem(label, value)
        h_index = self._history.findData(preferences.history_window_s)
        self._history.setCurrentIndex(h_index if h_index >= 0 else 1)
        form.addRow("Keep history for", self._history)

        self._throttle = QCheckBox("Slow updates while the window is hidden")
        self._throttle.setChecked(preferences.throttle_when_hidden)
        self._throttle.setToolTip(
            "Keeps GPUM from consuming the resources it is meant to measure."
        )
        form.addRow("", self._throttle)

        self._tray = QCheckBox("Keep GPUM in the status area when the window is closed")
        self._tray.setChecked(preferences.tray_enabled and tray_usable)
        self._tray.setEnabled(tray_usable)
        form.addRow("", self._tray)

        if not tray_usable:
            # Disabled with an explanation, never silently ignored.
            note = QLabel(tray_reason or "A status area is not available in this session.")
            note.setWordWrap(True)
            note.setStyleSheet("color: palette(mid);")
            form.addRow("", note)

        self._autostart = QCheckBox("Start GPUM when I log in")
        self._autostart.setChecked(autostart_enabled)
        form.addRow("", self._autostart)

        disclosure = QLabel(
            f"Enabling this writes a startup entry to {autostart_location}. "
            "Turning it off removes that file again. GPUM changes nothing else on your system."
        )
        disclosure.setWordWrap(True)
        disclosure.setTextFormat(Qt.TextFormat.PlainText)
        disclosure.setStyleSheet("color: palette(mid);")
        form.addRow("", disclosure)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.accept)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        # Applied live — FR-020 requires each change to take effect without a restart.
        self._interval.currentIndexChanged.connect(self._apply)
        self._history.currentIndexChanged.connect(self._apply)
        self._throttle.toggled.connect(self._apply)
        self._tray.toggled.connect(self._apply)
        self._autostart.toggled.connect(self.autostart_toggled.emit)

    def _apply(self) -> None:
        self._preferences.refresh_interval_ms = int(self._interval.currentData())
        self._preferences.history_window_s = int(self._history.currentData())
        self._preferences.throttle_when_hidden = self._throttle.isChecked()
        self._preferences.tray_enabled = self._tray.isChecked()
        self.settings_changed.emit()
