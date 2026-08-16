"""The main window.

Renders snapshots and owns nothing that blocks. Every slot here is assignment and repaint:
sampling, timeouts, and merging all happen before the snapshot crosses the thread boundary.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from gpum.core.history import DeviceHistory
from gpum.core.models import DiscoveryReport, ProcessSortColumn, Snapshot
from gpum.core.preferences import Preferences
from gpum.core.units import UNIT_CONVENTION
from gpum.ui.device_panel import DevicePanel
from gpum.ui.discovery_panel import DiscoveryPanel

__all__ = ["MainWindow"]

_log = logging.getLogger(__name__)

_INTERVALS = [("0.5 s", 500), ("1 s", 1000), ("2 s", 2000), ("5 s", 5000), ("10 s", 10000)]

class MainWindow(QMainWindow):
    interval_changed = Signal(int)
    paused_changed = Signal(bool)
    throttle_changed = Signal(bool)
    refresh_requested = Signal()
    #: Emitted when the window closes and the tool should exit (contracts/tray-contract.md).
    quit_requested = Signal()
    settings_requested = Signal()
    energy_reset_requested = Signal(str)
    #: Emitted the first time closing hides rather than quits, so the notice is shown once.
    closed_to_tray = Signal()

    def __init__(self, preferences: Preferences) -> None:
        super().__init__()
        # Assigned before any Qt call that can synchronously dispatch an event back into this
        # object: setWindowTitle/resize trigger changeEvent, which reads these attributes.
        self._preferences = preferences
        self._panels: dict[str, DevicePanel] = {}
        self._histories: dict[str, DeviceHistory] = {}
        self._last_sequence = -1
        self._ready = False
        #: Whether a tray icon will actually be displayed. Set by the application after
        #: probing; until then closing quits, which is the safe default (FR-034).
        self._tray_usable = False
        self._quitting = False

        self.setWindowTitle("GPUM — GPU monitor")
        self.resize(880, 720)

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        layout.addLayout(self._build_toolbar())

        self._discovery = DiscoveryPanel()
        layout.addWidget(self._discovery)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._device_host = QWidget()
        self._device_layout = QVBoxLayout(self._device_host)
        self._device_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll.setWidget(self._device_host)
        layout.addWidget(self._scroll, 1)

        self._status = QLabel(f"Memory shown in {UNIT_CONVENTION}")
        self._status.setStyleSheet("color: palette(mid);")
        layout.addWidget(self._status)

        if preferences.window_geometry:
            self.restoreGeometry(preferences.window_geometry)
        self._ready = True

    # -- construction ---------------------------------------------------------

    def _build_toolbar(self) -> QHBoxLayout:
        bar = QHBoxLayout()

        bar.addWidget(QLabel("Refresh"))
        self._interval_box = QComboBox()
        for label, value in _INTERVALS:
            self._interval_box.addItem(label, value)
        index = self._interval_box.findData(self._preferences.refresh_interval_ms)
        self._interval_box.setCurrentIndex(index if index >= 0 else 1)
        self._interval_box.currentIndexChanged.connect(self._on_interval_changed)
        bar.addWidget(self._interval_box)

        self._pause = QPushButton("Pause")
        self._pause.setCheckable(True)
        self._pause.setChecked(self._preferences.paused)
        self._pause.toggled.connect(self._on_pause_toggled)
        bar.addWidget(self._pause)

        refresh = QPushButton("Refresh now")
        refresh.clicked.connect(self.refresh_requested.emit)
        bar.addWidget(refresh)

        settings = QPushButton("Settings…")
        settings.clicked.connect(self.settings_requested.emit)
        bar.addWidget(settings)

        bar.addStretch(1)
        return bar

    # -- tray integration -----------------------------------------------------

    def set_tray_usable(self, usable: bool) -> None:
        """Whether an icon will genuinely appear — not merely whether Qt claims one can."""
        self._tray_usable = bool(usable)

    @property
    def hides_on_close(self) -> bool:
        """The decision table from contracts/tray-contract.md, in one place.

        Closing may only hide when an icon will really be shown *and* the user wants one.
        Every other combination quits, so there is no state in which the tool is running and
        unreachable (FR-034, SC-015).
        """
        return self._tray_usable and self._preferences.tray_enabled

    def request_quit(self) -> None:
        """Quit for real, bypassing hide-on-close."""
        self._quitting = True
        self.close()

    def closeEvent(self, event: object) -> None:  # noqa: N802 - Qt naming
        if self._quitting or not self.hides_on_close:
            self.quit_requested.emit()
            super().closeEvent(event)  # type: ignore[arg-type]
            return
        event.ignore()  # type: ignore[attr-defined]
        self.hide()
        if not self._preferences.close_notice_shown:
            self._preferences.close_notice_shown = True
            self.closed_to_tray.emit()

    # -- slots ----------------------------------------------------------------

    def on_snapshot(self, snapshot: Snapshot) -> None:
        """Render one snapshot. Must stay under 16 ms (U-01)."""
        if snapshot.sequence <= self._last_sequence:
            # Queued delivery can reorder under load; a stale snapshot must not overwrite a
            # newer one (U-04).
            return
        self._last_sequence = snapshot.sequence

        resume = getattr(snapshot, "resume", None)
        if resume is not None:
            # The machine slept. Break every trend line rather than drawing across the gap —
            # a continuous line would assert readings that were never taken (SC-008).
            for history in self._histories.values():
                history.append_gap("machine was suspended")
            self._status.setText(
                f"Resumed after {resume.gap_seconds / 60:.0f} minutes suspended"
            )

        seen: set[str] = set()
        for device in snapshot.devices:
            key = device.id.key
            seen.add(key)
            history = self._histories.get(key)
            if history is None:
                history = DeviceHistory(
                    key,
                    window_s=self._preferences.history_window_s,
                    interval_ms=self._preferences.refresh_interval_ms,
                )
                self._histories[key] = history
            history.append_memory(device.memory_used)
            history.append_utilization(device.utilization_gpu)
            history.append_power(device.power_draw_avg)
            history.append_memory_utilization(device.utilization_memory)

            panel = self._panels.get(key)
            if panel is None:
                panel = DevicePanel(device)
                panel.energy_reset_requested.connect(self.energy_reset_requested.emit)
                panel.sort_changed.connect(self._on_device_sort_changed)
                # Its own saved order, or the default for a device never sorted (FR-019).
                column, descending = self._preferences.sort_for(key)
                panel.set_sort(column, descending)
                self._panels[key] = panel
                self._device_layout.addWidget(panel)
            panel.update_device(device, snapshot, history)

        for key in list(self._panels):
            if key not in seen:
                # Device removed (FR-020). Its history is deliberately retained: keys are
                # UUID-based, so a device that comes back (eGPU reconnected, driver
                # restarted) resumes its trend instead of starting from nothing.
                panel = self._panels.pop(key)
                self._device_layout.removeWidget(panel)
                panel.deleteLater()

        self._scroll.setVisible(bool(snapshot.devices))
        self._discovery.setVisible(not snapshot.devices)

    def on_discovery(self, report: DiscoveryReport) -> None:
        self._discovery.update_report(report)

    def on_error(self, severity: str, message: str) -> None:
        """Inline, never modal: a recurring error in a dialog would make the app unusable."""
        self._status.setText(f"{severity}: {message}")

    # -- events ---------------------------------------------------------------

    def hideEvent(self, event: object) -> None:  # noqa: N802 - Qt naming
        if self._ready and self._preferences.throttle_when_hidden:
            self.throttle_changed.emit(True)
        super().hideEvent(event)  # type: ignore[arg-type]

    def showEvent(self, event: object) -> None:  # noqa: N802 - Qt naming
        self._ready = True
        self.throttle_changed.emit(False)
        super().showEvent(event)  # type: ignore[arg-type]

    def changeEvent(self, event: object) -> None:  # noqa: N802 - Qt naming
        # Fires during construction too, before the window is wired up.
        if self._ready and self._preferences.throttle_when_hidden:
            self.throttle_changed.emit(self.isMinimized())
        super().changeEvent(event)  # type: ignore[arg-type]

    # -- internals ------------------------------------------------------------

    def _on_device_sort_changed(self, device_key: str, column: str, descending: bool) -> None:
        """Remember one device's order. Deliberately does not touch any other panel — there is
        no path between them, which is what makes independence structural (FR-015)."""
        try:
            self._preferences.remember_sort(
                device_key, ProcessSortColumn(column), descending
            )
        except ValueError:
            _log.debug("ignoring unknown sort column %r", column)

    def _on_interval_changed(self) -> None:
        interval = int(self._interval_box.currentData())
        self._preferences.refresh_interval_ms = interval
        for history in self._histories.values():
            history.resize(
                window_s=self._preferences.history_window_s, interval_ms=interval
            )
        self.interval_changed.emit(interval)

    def _on_pause_toggled(self, paused: bool) -> None:
        self._preferences.paused = paused
        self._pause.setText("Resume" if paused else "Pause")
        self.paused_changed.emit(paused)

    def apply_preferences(self) -> None:
        """Re-read preferences after the settings dialog changed them (FR-020)."""
        prefs = self._preferences
        index = self._interval_box.findData(prefs.refresh_interval_ms)
        if index >= 0 and index != self._interval_box.currentIndex():
            self._interval_box.setCurrentIndex(index)
        for history in self._histories.values():
            history.resize(
                window_s=prefs.history_window_s, interval_ms=prefs.refresh_interval_ms
            )
        self.interval_changed.emit(prefs.refresh_interval_ms)

    def current_preferences(self) -> Preferences:
        self._preferences.window_geometry = bytes(self.saveGeometry())
        return self._preferences
