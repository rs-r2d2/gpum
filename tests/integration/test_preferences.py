"""T088, T089: preferences survive a restart and throttling works (FR-015, FR-023)."""

from __future__ import annotations

from gpum.core.models import ProcessSortColumn
from gpum.core.preferences import Preferences
from gpum.ui.main_window import MainWindow
from gpum.ui.preferences_store import load_preferences, save_preferences


class TestRoundTrip:
    def test_settings_survive_a_simulated_restart(self, tmp_path, monkeypatch) -> None:

        save_preferences(
            Preferences(
                refresh_interval_ms=5000,
                sort_column=ProcessSortColumn.NAME,
                sort_descending=False,
                history_window_s=120,
                throttle_when_hidden=False,
            )
        )
        restored = load_preferences()
        assert restored.refresh_interval_ms == 5000
        assert restored.sort_column is ProcessSortColumn.NAME
        assert restored.sort_descending is False
        assert restored.history_window_s == 120
        assert restored.throttle_when_hidden is False

    def test_interval_is_clamped_on_load(self) -> None:
        assert Preferences(refresh_interval_ms=5).refresh_interval_ms == 100
        assert Preferences(refresh_interval_ms=10**9).refresh_interval_ms == 60_000


class TestWindowRestoresPreferences:
    def test_window_reflects_saved_interval(self, qtbot) -> None:
        prefs = Preferences(refresh_interval_ms=5000)
        window = MainWindow(prefs)
        qtbot.addWidget(window)
        assert window._interval_box.currentData() == 5000

    def test_toolbar_no_longer_carries_sort_controls(self, qtbot) -> None:
        """FR-005: the header is the single sort control; two controls for one behaviour was
        the problem being solved."""
        window = MainWindow(Preferences())
        qtbot.addWidget(window)
        assert not hasattr(window, "_sort_box")
        assert not hasattr(window, "_descending")

    def test_default_sort_is_still_available_for_unseen_devices(self, qtbot) -> None:
        """The old toolbar preferences are not discarded — they become the default order
        applied to any device with no saved entry (FR-019)."""
        prefs = Preferences(sort_column=ProcessSortColumn.NAME, sort_descending=False)
        column, descending = prefs.sort_for("a-device-never-sorted")
        assert column is ProcessSortColumn.NAME
        assert descending is False


class TestThrottling:
    def test_u07_hiding_the_window_requests_throttling(self, qtbot) -> None:
        window = MainWindow(Preferences(throttle_when_hidden=True))
        qtbot.addWidget(window)
        window.show()
        with qtbot.waitSignal(window.throttle_changed, timeout=1000) as blocker:
            window.hide()
        assert blocker.args == [True]

    def test_showing_the_window_clears_throttling(self, qtbot) -> None:
        window = MainWindow(Preferences(throttle_when_hidden=True))
        qtbot.addWidget(window)
        with qtbot.waitSignal(window.throttle_changed, timeout=1000) as blocker:
            window.show()
        assert blocker.args == [False]

    def test_throttling_can_be_disabled(self, qtbot) -> None:
        window = MainWindow(Preferences(throttle_when_hidden=False))
        qtbot.addWidget(window)
        window.show()
        received: list[bool] = []
        window.throttle_changed.connect(received.append)
        window.hide()
        assert True not in received


class TestWorkerThrottle:
    def test_worker_slows_its_cadence_when_throttled(self) -> None:
        from gpum.core.engine import SamplingEngine
        from gpum.registry import build_backends
        from gpum.ui.sampler_worker import HIDDEN_THROTTLE_FACTOR, SamplerWorker

        worker = SamplerWorker(SamplingEngine(build_backends("none")), interval_ms=1000)
        assert worker._effective_interval() == 1000
        worker.set_throttled(True)
        assert worker._effective_interval() == 1000 * HIDDEN_THROTTLE_FACTOR
        worker.set_throttled(False)
        assert worker._effective_interval() == 1000
