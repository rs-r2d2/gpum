"""T015-T017: the smoother (P-04 .. P-08).

Exists because the raw reading is unusable — two reads of an idle RTX 5060 Ti seconds apart
gave 8.8 W and 15.8 W. These tests hold the line on the two ways smoothing could become
dishonest: spanning a gap, or growing until it defeats responsiveness.
"""

from __future__ import annotations

import datetime as dt

import pytest

from gpum.core.models import Availability, MetricValue
from gpum.core.power import PowerSmoother


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _w(value: float) -> MetricValue:
    return MetricValue.available(value, sampled_at=_now())


class TestEmptyBuffer:
    def test_p04_unavailable_while_empty(self) -> None:
        """Never a stale figure presented as current."""
        s = PowerSmoother()
        result = s.average()
        assert result.availability is not Availability.AVAILABLE
        assert result.value is None
        assert result.reason

    def test_average_after_one_sample(self) -> None:
        s = PowerSmoother()
        s.add(_w(20.0))
        assert s.average().value == pytest.approx(20.0)


class TestGapHandling:
    def test_p05_unavailable_reading_clears_the_buffer(self) -> None:
        """FR-027 — the assertion that keeps averaging from inventing data."""
        s = PowerSmoother()
        for v in (100.0, 100.0, 100.0):
            s.add(_w(v))
        assert s.count == 3
        s.add(MetricValue.unsupported("driver hiccup"))
        assert s.count == 0

    def test_p05_average_does_not_span_a_gap(self) -> None:
        s = PowerSmoother()
        for _ in range(4):
            s.add(_w(150.0))
        s.add(MetricValue.unsupported("gap"))
        s.add(_w(10.0))
        # Must reflect only the post-gap reading, not a blend across the interruption.
        assert s.average().value == pytest.approx(10.0)

    def test_average_unavailable_immediately_after_a_gap(self) -> None:
        s = PowerSmoother()
        s.add(_w(50.0))
        s.add(MetricValue.unsupported("gap"))
        assert not s.average().is_measurement

    def test_stale_reading_also_clears(self) -> None:
        s = PowerSmoother()
        s.add(_w(50.0))
        s.add(MetricValue.stale(50.0, sampled_at=_now(), reason="timed out"))
        assert s.count == 0


class TestResponsiveness:
    def test_p06_step_change_is_visible_within_two_samples(self) -> None:
        """Smoothing must not buy readability by breaking FR-004.

        With the measurement-derived 8 s window an 8-sample mean travels 25% of a step in two
        samples. On a realistic 20 W -> 150 W step that is a 32 W move inside two seconds,
        which is what SC-002 asks for.
        """
        s = PowerSmoother(interval_ms=1000)
        for _ in range(s.capacity):
            s.add(_w(20.0))
        assert s.average().value == pytest.approx(20.0)

        s.add(_w(150.0))
        s.add(_w(150.0))
        after_two = s.average().value
        travelled = (after_two - 20.0) / (150.0 - 20.0)
        assert travelled >= 0.20, f"only {travelled:.0%} of the step after two samples"
        assert after_two - 20.0 >= 25.0, "step must be plainly visible within two intervals"

    def test_step_settles_fully_within_the_window(self) -> None:
        s = PowerSmoother(interval_ms=1000)
        for _ in range(s.capacity):
            s.add(_w(20.0))
        for _ in range(s.capacity):
            s.add(_w(150.0))
        assert s.average().value == pytest.approx(150.0)

    #: A noisy idle series matching the measured envelope: 30 consecutive 1 Hz reads of an
    #: idle RTX 5060 Ti spanned 9.3-21.7 W with a worst consecutive change of 53.7%. These
    #: values reproduce that envelope so the bound is tested against reality, not against a
    #: comfortable invention.
    NOISY_IDLE = [
        9.3, 21.7, 10.1, 19.8, 11.2, 20.4, 9.9, 18.6, 12.5, 21.1,
        10.8, 19.2, 13.1, 20.9, 9.6, 17.9, 14.2, 20.1, 11.7, 18.3,
    ]

    def test_p07_idle_variance_is_damped(self) -> None:
        """SC-003: the displayed figure must not swing more than 10% between refreshes.

        The window size in `power.py` was chosen from this measurement — 5 s failed at 17.1%.
        """
        s = PowerSmoother(interval_ms=1000)
        readings = self.NOISY_IDLE
        averages = []
        for value in readings:
            s.add(_w(value))
            if s.count == s.capacity:
                averages.append(s.average().value)
        # SC-003 bounds the change *between consecutive refreshes*, which is what makes a
        # number readable — not the total spread over a whole minute.
        worst = max(
            abs(b - a) / a for a, b in zip(averages, averages[1:], strict=False)
        )
        assert worst <= 0.10, f"consecutive change {worst:.1%} exceeds the 10% budget"

    def test_raw_readings_would_have_failed_that_bound(self) -> None:
        """Documents why the smoother exists at all: unsmoothed, the same measured readings
        swing far past the budget between consecutive refreshes."""
        worst = max(
            abs(b - a) / a for a, b in zip(self.NOISY_IDLE, self.NOISY_IDLE[1:], strict=False)
        )
        assert worst > 0.50, "the measured raw swing was 53.7%"


class TestWindowSizing:
    def test_capacity_derives_from_interval(self) -> None:
        assert PowerSmoother(window_s=8.0, interval_ms=1000).capacity == 8
        assert PowerSmoother(window_s=8.0, interval_ms=500).capacity == 16

    def test_default_window_meets_the_measured_requirement(self) -> None:
        """8 s was the shortest window meeting SC-003 on real data; 5 s failed at 17.1%."""
        assert PowerSmoother(interval_ms=1000).capacity >= 8

    def test_p08_resize_keeps_the_window_constant(self) -> None:
        s = PowerSmoother(window_s=8.0, interval_ms=1000)
        assert s.capacity == 8
        s.resize(interval_ms=500)
        assert s.capacity == 16

    def test_capacity_never_zero(self) -> None:
        assert PowerSmoother(window_s=0.0, interval_ms=10000).capacity >= 1

    def test_buffer_is_bounded(self) -> None:
        s = PowerSmoother(interval_ms=1000)
        for i in range(10_000):
            s.add(_w(float(i % 100)))
        assert s.count == s.capacity
