"""The sampler → UI thread boundary (contracts/ui-update-contract.md).

A ``QObject`` **moved to** a ``QThread`` — never a ``QThread`` subclass with logic in
``run()`` — so its ``QTimer`` lives in the worker's own event loop. The timer is created after
the move for exactly that reason.

All scheduling logic proper lives in ``gpum.core.engine``; this class is deliberately thin.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QMetaObject, QObject, Qt, QThread, QTimer, Signal, Slot

from gpum.core.engine import SamplingEngine

__all__ = ["SamplerWorker", "SamplerThread"]

_log = logging.getLogger(__name__)

#: Multiplier applied to the interval when the window is not visible (FR-015). The tool must
#: not consume the resources it exists to measure.
HIDDEN_THROTTLE_FACTOR = 10


class SamplerWorker(QObject):
    """Owns the timer and emits snapshots. Never touches a widget."""

    snapshot_ready = Signal(object)
    discovery_changed = Signal(object)
    error_occurred = Signal(str, str)

    def __init__(self, engine: SamplingEngine, interval_ms: int = 1000) -> None:
        super().__init__()
        self._engine = engine
        self._interval_ms = interval_ms
        self._paused = False
        self._throttled = False
        self._timer: QTimer | None = None
        self._last_discovery: object | None = None

    @Slot()
    def start(self) -> None:
        """Create the timer inside the worker's thread and take the first sample at once."""
        self._timer = QTimer()
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._tick)
        self._timer.start(self._effective_interval())
        self._tick()

    @Slot()
    def stop(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        self._engine.shutdown()

    @Slot(int)
    def set_interval(self, interval_ms: int) -> None:
        """Queued from the GUI thread. Takes effect on the next cycle, never mid-cycle."""
        self._interval_ms = max(100, min(int(interval_ms), 60_000))
        # Keep the smoothing window near its target span at the new cadence (FR-026).
        self._engine.set_interval(self._interval_ms)
        self._restart_timer()

    @Slot(str)
    def reset_energy(self, device_key: str) -> None:
        """Restart energy accounting for one device (FR-012)."""
        self._engine.reset_energy(device_key or None)

    @Slot(bool)
    def set_paused(self, paused: bool) -> None:
        self._paused = bool(paused)
        if not self._paused:
            self._engine.reset_backoff()
            self._tick()

    @Slot(bool)
    def set_throttled(self, throttled: bool) -> None:
        """Slow the cadence while the display is not visible (FR-015)."""
        if self._throttled == bool(throttled):
            return
        self._throttled = bool(throttled)
        self._restart_timer()

    @Slot()
    def refresh_now(self) -> None:
        self._engine.reset_backoff()
        self._tick()

    # -- internals ------------------------------------------------------------

    def _effective_interval(self) -> int:
        if self._throttled:
            return self._interval_ms * HIDDEN_THROTTLE_FACTOR
        return self._interval_ms

    def _restart_timer(self) -> None:
        if self._timer is not None:
            self._timer.start(self._effective_interval())

    def _tick(self) -> None:
        if self._paused:
            return
        try:
            snapshot = self._engine.sample()
        except Exception as exc:  # noqa: BLE001 - a sampling failure must not kill the thread
            _log.exception("sampling cycle failed")
            # Never a modal dialog from here: a 1 Hz error would make the app unusable.
            self.error_occurred.emit("error", str(exc))
            return

        if snapshot.discovery != self._last_discovery:
            self._last_discovery = snapshot.discovery
            self.discovery_changed.emit(snapshot.discovery)
        self.snapshot_ready.emit(snapshot)


class SamplerThread:
    """Owns the ``QThread`` lifecycle so the window does not have to."""

    def __init__(self, engine: SamplingEngine, interval_ms: int = 1000) -> None:
        self.thread = QThread()
        self.thread.setObjectName("gpum-sampler")
        self.worker = SamplerWorker(engine, interval_ms)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.start)

    def start(self) -> None:
        self.thread.start()

    def stop(self, timeout_ms: int = 5000) -> None:
        """Ordered shutdown that must not block exit on a wedged driver.

        ``stop`` is invoked *in the worker's own thread* — calling it directly from the GUI
        thread would touch a QTimer owned by another thread, which is undefined behaviour.
        """
        if self.thread.isRunning():
            QMetaObject.invokeMethod(
                self.worker, "stop", Qt.ConnectionType.BlockingQueuedConnection
            )
        else:
            self.worker.stop()
        self.thread.quit()
        if not self.thread.wait(timeout_ms):
            _log.warning("sampler thread did not stop within %d ms; proceeding", timeout_ms)
