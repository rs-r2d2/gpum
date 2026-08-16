"""T001-T002: the utilization history series (U-01 .. U-05).

The compute series already existed and was recorded on every refresh without ever being drawn.
This adds the memory-interface series and holds both to the same bounded, gap-aware behaviour.
"""

from __future__ import annotations

import datetime as dt

from gpum.core.history import DeviceHistory
from gpum.core.models import Availability, MetricValue


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _pct(value: float) -> MetricValue:
    return MetricValue.available(value, sampled_at=_now())


class TestSeriesExist:
    def test_both_utilization_series_exist(self) -> None:
        h = DeviceHistory("k", window_s=60, interval_ms=1000)
        assert hasattr(h, "utilization")
        assert hasattr(h, "memory_utilization")

    def test_u01_both_are_appended(self) -> None:
        h = DeviceHistory("k", window_s=60, interval_ms=1000)
        h.append_utilization(_pct(40))
        h.append_memory_utilization(_pct(90))
        assert h.utilization[-1].value == 40
        assert h.memory_utilization[-1].value == 90

    def test_the_two_series_are_independent(self) -> None:
        h = DeviceHistory("k", window_s=60, interval_ms=1000)
        h.append_utilization(_pct(10))
        assert len(h.memory_utilization) == 0


class TestBounded:
    def test_u02_memory_utilization_is_bounded(self) -> None:
        h = DeviceHistory("k", window_s=10, interval_ms=1000)
        for i in range(5000):
            h.append_memory_utilization(_pct(i % 100))
        assert len(h.memory_utilization) == h.capacity == 10

    def test_u05_resize_keeps_the_window_constant(self) -> None:
        h = DeviceHistory("k", window_s=60, interval_ms=1000)
        h.append_memory_utilization(_pct(50))
        assert h.capacity == 60
        h.resize(window_s=60, interval_ms=500)
        assert h.capacity == 120
        assert h.memory_utilization.maxlen == 120

    def test_resize_preserves_recent_memory_utilization(self) -> None:
        h = DeviceHistory("k", window_s=5, interval_ms=1000)
        for i in range(5):
            h.append_memory_utilization(_pct(i))
        h.resize(window_s=3, interval_ms=1000)
        assert [p.value for p in h.memory_utilization] == [2, 3, 4]


class TestGaps:
    def test_u03_unavailable_becomes_a_gap_not_zero(self) -> None:
        """A dropped reading and a measured 0% look identical on a graph and mean opposite
        things."""
        h = DeviceHistory("k", window_s=10, interval_ms=1000)
        h.append_utilization(_pct(80))
        h.append_utilization(MetricValue.unsupported("not reported"))
        h.append_utilization(_pct(70))
        values = [p.value for p in h.utilization]
        assert values == [80, None, 70]
        assert 0 not in values

    def test_u03_applies_to_memory_utilization_too(self) -> None:
        h = DeviceHistory("k", window_s=10, interval_ms=1000)
        h.append_memory_utilization(MetricValue.unsupported("x"))
        assert h.memory_utilization[-1].value is None

    def test_u04_measured_zero_is_kept_as_a_measurement(self) -> None:
        """0% is a real reading and must not be stored as an absence."""
        h = DeviceHistory("k", window_s=10, interval_ms=1000)
        h.append_utilization(_pct(0))
        point = h.utilization[-1]
        assert point.value == 0
        assert point.availability is Availability.AVAILABLE

    def test_u04_zero_and_unavailable_are_distinguishable(self) -> None:
        h = DeviceHistory("k", window_s=10, interval_ms=1000)
        h.append_utilization(_pct(0))
        h.append_utilization(MetricValue.unsupported("unreadable"))
        measured, missing = h.utilization[-2], h.utilization[-1]
        assert measured.value == 0 and measured.availability is Availability.AVAILABLE
        assert missing.value is None and missing.availability is not Availability.AVAILABLE

    def test_a_suspend_gap_breaks_every_series(self) -> None:
        h = DeviceHistory("k", window_s=10, interval_ms=1000)
        h.append_utilization(_pct(50))
        h.append_memory_utilization(_pct(50))
        h.append_gap("machine was suspended")
        assert h.utilization[-1].value is None
        assert h.memory_utilization[-1].value is None
