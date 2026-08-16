"""T012: bounded history (FR-005, FR-024, SC-005)."""

import datetime as dt

from gpum.core.history import DeviceHistory
from gpum.core.models import Availability, MetricValue


def _t(seconds: int) -> dt.datetime:
    return dt.datetime(2026, 1, 1, tzinfo=dt.UTC) + dt.timedelta(seconds=seconds)


class TestBounds:
    def test_capacity_derived_from_window_and_interval(self) -> None:
        h = DeviceHistory("k", window_s=300, interval_ms=1000)
        assert h.capacity == 300

    def test_capacity_is_structural_not_maintained(self) -> None:
        """The bound must hold without anyone remembering to prune (FR-024)."""
        h = DeviceHistory("k", window_s=10, interval_ms=1000)
        for i in range(10_000):
            h.append_memory(MetricValue.available(i, sampled_at=_t(i)))
        assert len(h.memory_used) == 10

    def test_resizing_the_interval_keeps_the_window_constant(self) -> None:
        h = DeviceHistory("k", window_s=60, interval_ms=1000)
        assert h.capacity == 60
        h.resize(window_s=60, interval_ms=500)
        assert h.capacity == 120

    def test_resize_preserves_the_most_recent_points(self) -> None:
        h = DeviceHistory("k", window_s=5, interval_ms=1000)
        for i in range(5):
            h.append_memory(MetricValue.available(i, sampled_at=_t(i)))
        h.resize(window_s=3, interval_ms=1000)
        assert [p.value for p in h.memory_used] == [2, 3, 4]

    def test_minimum_capacity_of_one(self) -> None:
        h = DeviceHistory("k", window_s=0, interval_ms=1000)
        assert h.capacity >= 1


class TestGapRetention:
    def test_unavailable_points_are_recorded_as_gaps_not_zeros(self) -> None:
        """U-12/SC-007: the sparkline must show a gap, never a dip to zero."""
        h = DeviceHistory("k", window_s=10, interval_ms=1000)
        h.append_memory(MetricValue.available(100, sampled_at=_t(0)))
        h.append_memory(MetricValue.unsupported("driver said no"))
        h.append_memory(MetricValue.available(200, sampled_at=_t(2)))
        values = [p.value for p in h.memory_used]
        assert values == [100, None, 200]
        assert 0 not in values

    def test_availability_travels_with_each_point(self) -> None:
        h = DeviceHistory("k", window_s=10, interval_ms=1000)
        h.append_memory(MetricValue.unsupported("x"))
        assert h.memory_used[-1].availability is Availability.UNSUPPORTED

    def test_has_any_measurement_false_when_all_gaps(self) -> None:
        h = DeviceHistory("k", window_s=5, interval_ms=1000)
        for _ in range(3):
            h.append_memory(MetricValue.unsupported("x"))
        assert not h.has_any_measurement
