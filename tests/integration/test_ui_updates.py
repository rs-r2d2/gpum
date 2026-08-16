"""UI contract tests (contracts/ui-update-contract.md, U-01..U-12).

Headless via QT_QPA_PLATFORM=offscreen, set in tests/conftest.py.
"""

from __future__ import annotations

import datetime as dt
import time

import pytest

from gpum.core.history import DeviceHistory
from gpum.core.models import (
    Availability,
    DeviceId,
    GpuDevice,
    GpuProcess,
    MetricValue,
    ProcessIdentity,
    ProcessSortColumn,
    Snapshot,
    Vendor,
)
from gpum.core.preferences import Preferences
from gpum.ui.main_window import MainWindow
from gpum.ui.process_model import ProcessTableModel

pytest.importorskip("PySide6")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _device(key: str, index: int = 0, **kw: object) -> GpuDevice:
    defaults = {
        "memory_total": MetricValue.available(24 * 1024**3, sampled_at=_now()),
        "memory_used": MetricValue.available(6 * 1024**3, sampled_at=_now()),
        "utilization_gpu": MetricValue.available(50, sampled_at=_now()),
        "attribution": Availability.AVAILABLE,
    }
    defaults.update(kw)
    return GpuDevice(id=DeviceId(Vendor.NVIDIA, key, index), name="Fake GPU", **defaults)  # type: ignore[arg-type]


def _snapshot(devices: tuple[GpuDevice, ...], seq: int = 1, processes=()) -> Snapshot:
    return Snapshot(taken_at=_now(), sequence=seq, devices=devices, processes=tuple(processes))


@pytest.fixture
def window(qtbot) -> MainWindow:
    w = MainWindow(Preferences())
    qtbot.addWidget(w)
    return w


class TestRenderBudget:
    def test_u01_gui_slot_stays_under_budget_with_many_devices(
        self, window: MainWindow
    ) -> None:
        """Principle III: no GUI-thread operation exceeds 16 ms."""
        devices = tuple(_device(f"gpu-{i}", i) for i in range(8))
        processes = tuple(
            GpuProcess(
                pid=1000 + n,
                device_key=f"gpu-{n % 8}",
                name=f"proc{n}",
                memory_used=MetricValue.available(1024**3, sampled_at=_now()),
                identity_state=ProcessIdentity.RESOLVED,
            )
            for n in range(200)
        )
        window.on_snapshot(_snapshot(devices, 1, processes))  # first render builds panels

        start = time.perf_counter()
        window.on_snapshot(_snapshot(devices, 2, processes))
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 16, f"render took {elapsed_ms:.1f} ms, budget is 16 ms"


class TestSnapshotOrdering:
    def test_u04_out_of_order_snapshots_are_discarded(self, window: MainWindow) -> None:
        window.on_snapshot(_snapshot((_device("a"),), seq=5))
        window.on_snapshot(_snapshot((_device("a"), _device("b", 1)), seq=3))
        assert len(window._panels) == 1, "a stale snapshot overwrote a newer one"

    def test_newer_snapshots_are_applied(self, window: MainWindow) -> None:
        window.on_snapshot(_snapshot((_device("a"),), seq=1))
        window.on_snapshot(_snapshot((_device("a"), _device("b", 1)), seq=2))
        assert len(window._panels) == 2


class TestEmptyState:
    def test_u05_empty_device_list_keeps_the_window_usable(self, window: MainWindow) -> None:
        """FR-018, SC-006: no blank window, no crash."""
        window.on_snapshot(_snapshot(()))
        assert window.isEnabled()
        assert window._discovery.isVisibleTo(window)


class TestHonestRendering:
    def test_u11_unsupported_metric_never_renders_as_zero_or_blank(
        self, window: MainWindow
    ) -> None:
        """The single most important UI assertion — this is SC-007."""
        device = _device(
            "a",
            utilization_gpu=MetricValue.unsupported("not reported by this device"),
        )
        window.on_snapshot(_snapshot((device,)))
        panel = window._panels["a"]
        text = panel._compute_label.text()
        assert "0%" not in text
        assert "Not supported" in text
        # The bar must also not read as a measured zero: empty *and* disabled.
        assert panel._compute_bar.value() == 0
        assert not panel._compute_bar.isEnabled()

    def test_unsupported_device_shows_its_reason_and_no_figures(
        self, window: MainWindow
    ) -> None:
        """FR-028: a MIG partition must not be given plausible-looking numbers."""
        device = GpuDevice(
            id=DeviceId(Vendor.NVIDIA, "mig", 0),
            name="A100",
            supported=False,
            unsupported_reason="partitioned GPU (MIG) not supported",
        )
        window.on_snapshot(_snapshot((device,)))
        panel = window._panels["mig"]
        assert "MIG" in panel._memory_label.text()
        assert not panel._memory_bar.isVisibleTo(panel)

    def test_attribution_unavailable_explains_instead_of_showing_an_empty_table(
        self, window: MainWindow
    ) -> None:
        """US2 scenario 4: an empty list would imply the GPU is idle."""
        device = _device(
            "a",
            attribution=Availability.UNSUPPORTED,
            attribution_reason="not reported under this driver model",
        )
        window.on_snapshot(_snapshot((device,)))
        panel = window._panels["a"]
        assert "not reported" in panel._process_note.text()
        assert not panel._table.isVisibleTo(panel)

    def test_u12_sparkline_gaps_are_not_zeros(self) -> None:
        history = DeviceHistory("a", window_s=10, interval_ms=1000)
        history.append_memory(MetricValue.available(100, sampled_at=_now()))
        history.append_memory(MetricValue.unsupported("gone"))
        history.append_memory(MetricValue.available(200, sampled_at=_now()))
        assert [p.value for p in history.memory_used] == [100, None, 200]


class TestDeviceLifecycle:
    def test_removed_device_panel_disappears(self, window: MainWindow) -> None:
        window.on_snapshot(_snapshot((_device("a"), _device("b", 1)), seq=1))
        assert len(window._panels) == 2
        window.on_snapshot(_snapshot((_device("a"),), seq=2))
        assert set(window._panels) == {"a"}


class TestProcessTable:
    def test_u09_sort_order_is_stable_across_refreshes(self) -> None:
        """FR-010: rows must not reshuffle under the cursor every second."""
        model = ProcessTableModel()
        rows = tuple(
            GpuProcess(
                pid=pid,
                device_key="a",
                name="same",
                memory_used=MetricValue.available(1024, sampled_at=_now()),
                identity_state=ProcessIdentity.RESOLVED,
            )
            for pid in (5, 3, 9, 1)
        )
        model.set_processes(rows)
        first = [model.data(model.index(r, 1)) for r in range(model.rowCount())]
        model.set_processes(rows)
        second = [model.data(model.index(r, 1)) for r in range(model.rowCount())]
        assert first == second

    def test_unmeasurable_memory_sorts_last_not_as_zero(self) -> None:
        model = ProcessTableModel()
        model.set_sort(ProcessSortColumn.MEMORY_USED, descending=True)
        rows = (
            GpuProcess(
                pid=1,
                device_key="a",
                name="unknown",
                memory_used=MetricValue.unsupported("WDDM"),
            ),
            GpuProcess(
                pid=2,
                device_key="a",
                name="known",
                memory_used=MetricValue.available(1024, sampled_at=_now()),
            ),
        )
        model.set_processes(rows)
        assert model.data(model.index(0, 0)) == "known"

    def test_unresolved_process_is_labelled_not_dropped(self) -> None:
        """FR-031: never omit what you cannot name."""
        model = ProcessTableModel()
        model.set_processes(
            (
                GpuProcess(
                    pid=77,
                    device_key="a",
                    memory_used=MetricValue.available(2048, sampled_at=_now()),
                    identity_state=ProcessIdentity.UNRESOLVED,
                ),
            )
        )
        assert model.rowCount() == 1
        assert "unresolved" in str(model.data(model.index(0, 0)))

    def test_restricted_process_is_labelled(self) -> None:
        model = ProcessTableModel()
        model.set_processes(
            (GpuProcess(pid=9, device_key="a", identity_state=ProcessIdentity.RESTRICTED),)
        )
        assert "restricted" in str(model.data(model.index(0, 0)))

    def test_containerized_process_shows_its_container(self) -> None:
        model = ProcessTableModel()
        model.set_processes(
            (
                GpuProcess(
                    pid=9,
                    device_key="a",
                    name="python",
                    container_id="abc123def456789",
                    identity_state=ProcessIdentity.CONTAINERIZED,
                ),
            )
        )
        assert "abc123def456" in str(model.data(model.index(0, 0)))


class TestPreferences:
    def test_u06_interval_change_is_recorded_and_emitted(
        self, window: MainWindow, qtbot
    ) -> None:
        with qtbot.waitSignal(window.interval_changed, timeout=1000) as blocker:
            window._interval_box.setCurrentIndex(window._interval_box.findData(5000))
        assert blocker.args == [5000]
        assert window.current_preferences().refresh_interval_ms == 5000

    def test_u06_pause_emits_and_records(self, window: MainWindow, qtbot) -> None:
        with qtbot.waitSignal(window.paused_changed, timeout=1000) as blocker:
            window._pause.setChecked(True)
        assert blocker.args == [True]
        assert window.current_preferences().paused is True

    def test_interval_change_resizes_history_to_keep_the_window_constant(
        self, window: MainWindow
    ) -> None:
        window.on_snapshot(_snapshot((_device("a"),)))
        before = window._histories["a"].capacity
        window._interval_box.setCurrentIndex(window._interval_box.findData(500))
        assert window._histories["a"].capacity == before * 2
