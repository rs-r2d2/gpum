"""T006-T009, T015-T017, T021-T023, T026-T028: utilization display (U-01 .. U-14)."""

from __future__ import annotations

import datetime as dt
import time

from PySide6.QtWidgets import QLabel

from gpum.core.models import (
    Availability,
    DeviceId,
    GpuDevice,
    MetricValue,
    Snapshot,
    Vendor,
)
from gpum.core.preferences import Preferences
from gpum.ui.main_window import MainWindow
from gpum.ui.sparkline import Sparkline


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _device(key="a", index=0, **kw) -> GpuDevice:
    defaults = {
        "memory_total": MetricValue.available(24 * 1024**3, sampled_at=_now()),
        "memory_used": MetricValue.available(6 * 1024**3, sampled_at=_now()),
        "utilization_gpu": MetricValue.available(42, sampled_at=_now()),
        "utilization_memory": MetricValue.available(88, sampled_at=_now()),
        "attribution": Availability.AVAILABLE,
    }
    defaults.update(kw)
    return GpuDevice(id=DeviceId(Vendor.NVIDIA, key, index), name="Test GPU", **defaults)


def _render(qtbot, *devices, seq=1) -> MainWindow:
    window = MainWindow(Preferences())
    qtbot.addWidget(window)
    window.on_snapshot(Snapshot(taken_at=_now(), sequence=seq, devices=tuple(devices)))
    return window


def _labels(panel) -> str:
    return " ".join(w.text() for w in panel.findChildren(QLabel))


class TestFixedScale:
    def test_u06_utilization_graph_uses_a_fixed_0_100_scale(self, qtbot) -> None:
        window = _render(qtbot, _device())
        assert window._panels["a"]._utilization_spark.fixed_maximum == 100.0

    def test_u06_memory_graph_still_auto_scales(self, qtbot) -> None:
        """Memory's ceiling is a hardware property, so auto-scaling is right for it."""
        window = _render(qtbot, _device())
        assert window._panels["a"]._sparkline.fixed_maximum is None

    def test_u07_idle_noise_does_not_fill_the_graph(self, qtbot) -> None:
        """With auto-scaling, 0-3% noise would stretch to full height and read as heavy load."""
        spark = Sparkline(fixed_maximum=100.0)
        from gpum.core.history import HistoryPoint

        noise = [HistoryPoint(_now(), v, Availability.AVAILABLE) for v in (0.0, 3.0, 1.0, 2.0)]
        spark.set_points(noise, 3.0)  # a caller passing the observed peak must be ignored
        assert spark._maximum == 100.0


class TestLabels:
    def test_u08_both_graphs_are_labelled(self, qtbot) -> None:
        window = _render(qtbot, _device())
        panel = window._panels["a"]
        assert panel._sparkline.label
        assert panel._utilization_spark.label
        assert panel._sparkline.label != panel._utilization_spark.label

    def test_utilization_label_conveys_time_not_hardware(self, qtbot) -> None:
        window = _render(qtbot, _device())
        label = window._panels["a"]._utilization_spark.label.lower()
        assert "time" in label or "busy" in label
        assert "core" not in label


class TestBothActivityFigures:
    def test_u09_both_are_displayed(self, qtbot) -> None:
        window = _render(qtbot, _device())
        text = _labels(window._panels["a"])
        assert "42%" in text
        assert "88%" in text

    def test_u09_labelled_by_what_they_describe(self, qtbot) -> None:
        window = _render(qtbot, _device())
        panel = window._panels["a"]
        # Asserts the intent — labelled by what it describes — not exact wording.
        compute = panel._compute_label.text().lower()
        memory = panel._mem_activity_label.text().lower()
        assert "compute" in compute and "busy" in compute
        assert "memory interface" in memory and "busy" in memory

    def test_u09_memory_activity_does_not_read_as_occupancy(self, qtbot) -> None:
        """The panel already shows memory occupancy; two 'memory %' figures would collide."""
        window = _render(qtbot, _device())
        panel = window._panels["a"]
        activity = panel._mem_activity_label.text().lower()
        assert "interface" in activity
        assert "used" not in activity

    def test_u10_one_available_one_not(self, qtbot) -> None:
        device = _device(utilization_memory=MetricValue.unsupported("not reported"))
        window = _render(qtbot, device)
        panel = window._panels["a"]
        assert "42%" in panel._compute_label.text()
        assert "Not supported" in panel._mem_activity_label.text()


class TestHonestReporting:
    def test_u11_no_core_count_anywhere(self, qtbot) -> None:
        """FR-009: no figure may be a count or fraction of cores."""
        window = _render(qtbot, _device())
        text = _labels(window._panels["a"]).lower()
        for forbidden in ("cores", "core count", "cuda core", "of 4608", "sm "):
            assert forbidden not in text

    def test_unavailable_utilization_is_never_zero_percent(self, qtbot) -> None:
        device = _device(utilization_gpu=MetricValue.unsupported("not reported"))
        window = _render(qtbot, device)
        text = window._panels["a"]._compute_label.text()
        assert "0%" not in text
        assert "Not supported" in text

    def test_u04_measured_zero_is_shown_as_a_measurement(self, qtbot) -> None:
        device = _device(utilization_gpu=MetricValue.available(0, sampled_at=_now()))
        window = _render(qtbot, device)
        assert "0%" in window._panels["a"]._compute_label.text()

    def test_the_explanation_is_reachable(self, qtbot) -> None:
        """FR-010: the user must be able to find out what the figure means."""
        window = _render(qtbot, _device())
        tip = window._panels["a"]._compute_label.toolTip().lower()
        assert "not the share of gpu cores" in tip


class TestLayoutAndCost:
    def test_u12_process_table_stays_visible(self, qtbot) -> None:
        """The change most likely to trade a useful table for a decorative graph."""
        window = _render(qtbot, _device())
        window.resize(880, 720)
        qtbot.waitExposed(window) if window.isVisible() else None
        panel = window._panels["a"]
        assert panel._table.isVisibleTo(panel)
        assert panel._table.minimumHeight() >= 0
        # The two graphs together must not dominate the panel.
        graphs = panel._sparkline.minimumHeight() + panel._utilization_spark.minimumHeight()
        assert graphs <= 120, f"graphs reserve {graphs}px of vertical space"

    def test_u14_eight_devices_render_within_budget(self, qtbot) -> None:
        devices = [_device(f"gpu-{i}", i) for i in range(8)]
        window = _render(qtbot, *devices, seq=1)
        start = time.perf_counter()
        window.on_snapshot(Snapshot(taken_at=_now(), sequence=2, devices=tuple(devices)))
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 16, f"render took {elapsed_ms:.1f} ms"
