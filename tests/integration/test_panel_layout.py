"""T032-T035: the cleaned-up device panel.

Feature 006 left the same percentage rendered twice and only one of three percentages given a
bar. These assert the panel presents comparable quantities comparably, and stays compact enough
that the process table survives.
"""

from __future__ import annotations

import datetime as dt

from PySide6.QtWidgets import QLabel, QProgressBar

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


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _device(key="a", **kw) -> GpuDevice:
    defaults = {
        "vendor_name": "NVIDIA",
        "memory_total": MetricValue.available(24 * 1024**3, sampled_at=_now()),
        "memory_used": MetricValue.available(6 * 1024**3, sampled_at=_now()),
        "utilization_gpu": MetricValue.available(42, sampled_at=_now()),
        "utilization_memory": MetricValue.available(88, sampled_at=_now()),
        "power_draw_avg": MetricValue.available(17.3, sampled_at=_now()),
        "power_limit": MetricValue.available(180.0, sampled_at=_now()),
        "energy_session": MetricValue.available(0.094, sampled_at=_now()),
        "attribution": Availability.AVAILABLE,
    }
    defaults.update(kw)
    return GpuDevice(id=DeviceId(Vendor.NVIDIA, key, 0), name="Test GPU", **defaults)


def _render(qtbot, device) -> MainWindow:
    window = MainWindow(Preferences())
    qtbot.addWidget(window)
    window.on_snapshot(Snapshot(taken_at=_now(), sequence=1, devices=(device,)))
    return window


def _panel_text(panel) -> str:
    return " ".join(w.text() for w in panel.findChildren(QLabel) if w.isVisibleTo(panel))


class TestThreeBars:
    def test_t032_each_percentage_has_its_own_bar(self, qtbot) -> None:
        window = _render(qtbot, _device())
        panel = window._panels["a"]
        bars = panel.findChildren(QProgressBar)
        assert len(bars) >= 3, f"expected a bar per percentage, found {len(bars)}"

    def test_t032_each_bar_is_labelled(self, qtbot) -> None:
        window = _render(qtbot, _device())
        panel = window._panels["a"]
        for attr in ("_memory_bar", "_compute_bar", "_mem_activity_bar"):
            assert hasattr(panel, attr), f"missing {attr}"

    def test_bars_reflect_their_values(self, qtbot) -> None:
        window = _render(qtbot, _device())
        panel = window._panels["a"]
        assert panel._compute_bar.value() == 42
        assert panel._mem_activity_bar.value() == 88
        assert panel._memory_bar.value() == 25  # 6 of 24 GiB


class TestNoDuplication:
    def test_t033_compute_utilization_appears_once(self, qtbot) -> None:
        """006 rendered it in both a stats row and an activity row."""
        device = _device(utilization_gpu=MetricValue.available(42, sampled_at=_now()))
        window = _render(qtbot, device)
        text = _panel_text(window._panels["a"])
        assert text.count("42%") == 1, f"compute figure appears {text.count('42%')} times"

    def test_t033_vendor_is_not_repeated(self, qtbot) -> None:
        window = _render(qtbot, _device())
        panel = window._panels["a"]
        text = _panel_text(panel)
        assert text.lower().count("nvidia") <= 1


class TestUnavailableRendering:
    def test_t034_unavailable_bar_is_empty_and_disabled(self, qtbot) -> None:
        """An unavailable percentage must not be readable as a measured 0%."""
        device = _device(utilization_gpu=MetricValue.unsupported("not reported"))
        window = _render(qtbot, device)
        panel = window._panels["a"]
        assert panel._compute_bar.value() == 0
        assert not panel._compute_bar.isEnabled()

    def test_t034_measured_zero_bar_is_empty_but_enabled(self, qtbot) -> None:
        device = _device(utilization_gpu=MetricValue.available(0, sampled_at=_now()))
        window = _render(qtbot, device)
        panel = window._panels["a"]
        assert panel._compute_bar.value() == 0
        assert panel._compute_bar.isEnabled(), "a measured 0% must not look unavailable"

    def test_t034_unavailable_shows_its_reason_in_text(self, qtbot) -> None:
        device = _device(utilization_memory=MetricValue.unsupported("not reported"))
        window = _render(qtbot, device)
        text = window._panels["a"]._mem_activity_label.text()
        assert "Not supported" in text
        assert "0%" not in text


class TestUnavailableWording:
    """Found by running quickstart V-3/V-4 against the fake backend (T030).

    The activity labels spliced the availability state into the measured sentence, producing
    "GPU compute busy  Not supported of the time" — which reads as a broken sentence before it
    reads as an unavailable metric, the opposite of what FR-011 asks for.
    """

    def test_unavailable_activity_is_not_spliced_into_the_measured_sentence(
        self, qtbot
    ) -> None:
        device = _device(
            utilization_gpu=MetricValue.unsupported("not reported by this device"),
            utilization_memory=MetricValue.unsupported("not reported by this device"),
        )
        window = _render(qtbot, device)
        panel = window._panels["a"]
        for label in (panel._compute_label, panel._mem_activity_label):
            assert "of the time" not in label.text(), (
                f"ungrammatical unavailable label: {label.text()!r}"
            )

    def test_unavailable_activity_still_names_what_it_describes(self, qtbot) -> None:
        """FR-022 does not lapse when the figure is missing: the two must still be
        distinguishable, or an unavailable panel becomes two identical lines."""
        device = _device(
            utilization_gpu=MetricValue.unsupported("not reported"),
            utilization_memory=MetricValue.unsupported("not reported"),
        )
        window = _render(qtbot, device)
        panel = window._panels["a"]
        compute, memory = panel._compute_label.text(), panel._mem_activity_label.text()
        assert compute != memory
        assert "compute" in compute.lower()
        assert "memory interface" in memory.lower()

    def test_measured_activity_keeps_the_time_wording(self, qtbot) -> None:
        """The fix must not cost the wording US2 exists to establish."""
        window = _render(qtbot, _device())
        panel = window._panels["a"]
        assert "of the time" in panel._compute_label.text()
        assert "of the time" in panel._mem_activity_label.text()

    def test_unavailable_activity_carries_its_reason(self, qtbot) -> None:
        """FR-011: unavailable, *with a reason*. The label has room for the state only."""
        device = _device(utilization_gpu=MetricValue.unsupported("driver is too old"))
        window = _render(qtbot, device)
        panel = window._panels["a"]
        assert "driver is too old" in panel._compute_label.toolTip()

    def test_available_activity_tooltip_is_just_the_explanation(self, qtbot) -> None:
        window = _render(qtbot, _device())
        panel = window._panels["a"]
        tip = panel._compute_label.toolTip().lower()
        assert "not the share of gpu cores" in tip
        assert "unsupported" not in tip


class TestCompactness:
    def test_t035_process_table_stays_visible(self, qtbot) -> None:
        window = _render(qtbot, _device())
        window.resize(880, 720)
        panel = window._panels["a"]
        assert panel._table.isVisibleTo(panel)

    def test_t035_panel_hint_leaves_room_for_the_table(self, qtbot) -> None:
        """Everything above the table must not consume the whole default window."""
        window = _render(qtbot, _device())
        window.resize(880, 720)
        panel = window._panels["a"]
        above_table = panel.sizeHint().height() - panel._table.sizeHint().height()
        assert above_table < 420, f"chrome above the table is {above_table}px"
