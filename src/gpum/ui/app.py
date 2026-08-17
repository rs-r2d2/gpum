"""Application assembly and the sampler thread's lifecycle."""

from __future__ import annotations

import logging
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from gpum.core.engine import SamplingEngine
from gpum.registry import (
    build_backends,
    present_gpu_probe,
    select_attribution_provider,
    select_identity_provider,
)
from gpum.ui.main_window import MainWindow
from gpum.ui.preferences_store import load_preferences, save_preferences
from gpum.ui.sampler_worker import SamplerThread
from gpum.ui.tray import TrayPresence

__all__ = ["run"]

_log = logging.getLogger(__name__)


def run(
    backend: str | None = None, scenario: str | None = None, hidden: bool = False
) -> int:
    app = QApplication.instance() or QApplication(sys.argv)

    preferences = load_preferences()
    backends = build_backends(backend, scenario=scenario)
    attribution = select_attribution_provider(backends)
    identity = select_identity_provider()

    engine = SamplingEngine(
        backends,
        attribution_provider=attribution,
        identity_provider=identity,
        present_gpu_probe=present_gpu_probe(),
    )

    window = MainWindow(preferences)

    availability = _probe_tray()
    window.set_tray_usable(availability.usable)
    if not availability.usable:
        _log.info("status area unavailable: %s", availability.reason)

    tray: TrayPresence | None = None
    if availability.usable and preferences.tray_enabled:
        tray = TrayPresence(_application_icon(), parent=app)
        tray.show_requested.connect(window.showNormal)
        tray.show_requested.connect(window.raise_)
        tray.quit_requested.connect(window.request_quit)
        tray.pause_toggled.connect(window._pause.setChecked)
        window.paused_changed.connect(tray.set_paused)
        window.closed_to_tray.connect(tray.notify_closed_to_tray)

    sampler = SamplerThread(engine, preferences.refresh_interval_ms)

    # Cross-thread wiring. Every connection is queued by Qt because the worker lives in
    # another thread; nothing here ever calls a backend from the GUI thread.
    sampler.worker.snapshot_ready.connect(window.on_snapshot)
    sampler.worker.discovery_changed.connect(window.on_discovery)
    sampler.worker.error_occurred.connect(window.on_error)
    window.interval_changed.connect(sampler.worker.set_interval)
    window.paused_changed.connect(sampler.worker.set_paused)
    window.throttle_changed.connect(sampler.worker.set_throttled)
    window.refresh_requested.connect(sampler.worker.refresh_now)
    window.energy_reset_requested.connect(sampler.worker.reset_energy)

    def _on_quit() -> None:
        save_preferences(window.current_preferences())
        sampler.stop()

    app.aboutToQuit.connect(_on_quit)

    def _open_settings() -> None:
        # Resolved through gpum.adapters, which holds the single OS switch. Importing
        # gpum.adapters.linux here bound the settings dialog to one platform and made the
        # autostart toggle lie on every other (research D-07).
        from gpum.adapters import platform_autostart
        from gpum.ui.settings_dialog import SettingsDialog

        autostart = platform_autostart()

        dialog = SettingsDialog(
            preferences,
            tray_usable=availability.usable,
            tray_reason=availability.reason,
            autostart_enabled=autostart.is_autostart_enabled(),
            autostart_location=str(autostart.autostart_path()),
            parent=window,
        )
        dialog.settings_changed.connect(window.apply_preferences)
        dialog.autostart_toggled.connect(
            lambda on: autostart.enable_autostart() if on else autostart.disable_autostart()
        )
        dialog.exec()

    window.settings_requested.connect(_open_settings)
    window.quit_requested.connect(app.quit)

    if (hidden or preferences.start_hidden) and tray is not None:
        # Autostarted: present in the status area without taking focus (FR-022).
        window.hide()
    else:
        window.show()
    sampler.start()
    return app.exec()


def _probe_tray():
    """Ask the platform adapter, passing Qt's own (unreliable) opinion in."""
    from gpum.adapters import tray_availability

    return tray_availability(QSystemTrayIcon.isSystemTrayAvailable())


def _application_icon() -> QIcon:
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent / "resources" / "gpum.svg"
    return QIcon(str(path))
