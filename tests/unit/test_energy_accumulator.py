"""T024-T026: session energy (P-09 .. P-12).

The counter accumulates since driver load. Turning that into "since monitoring began" has
three failure modes, and each one produces a visibly wrong number if unhandled.
"""

from __future__ import annotations

import datetime as dt

import pytest

from gpum.core.models import MetricValue
from gpum.core.power import EnergyAccumulator


def _wh(value: float) -> MetricValue:
    return MetricValue.available(value, sampled_at=dt.datetime.now(dt.UTC))


class TestNormalAccumulation:
    def test_first_reading_is_zero(self) -> None:
        acc = EnergyAccumulator()
        assert acc.update(_wh(72.431)).value == pytest.approx(0.0)

    def test_accumulates_the_delta_not_the_counter(self) -> None:
        acc = EnergyAccumulator()
        acc.update(_wh(72.431))
        assert acc.update(_wh(72.931)).value == pytest.approx(0.5)

    def test_monotonic_across_many_readings(self) -> None:
        acc = EnergyAccumulator()
        acc.update(_wh(100.0))
        seen = [acc.update(_wh(100.0 + i * 0.25)).value for i in range(1, 10)]
        assert seen == sorted(seen)


class TestCounterReset:
    def test_p09_reset_never_produces_a_negative(self) -> None:
        """A driver reload sends the counter backwards; naive subtraction goes negative."""
        acc = EnergyAccumulator()
        acc.update(_wh(100.0))
        acc.update(_wh(105.0))
        result = acc.update(_wh(0.5))  # counter reset
        assert result.value >= 0.0

    def test_p09_measured_energy_is_carried_forward(self) -> None:
        """A reload must not silently discard what was already measured."""
        acc = EnergyAccumulator()
        acc.update(_wh(100.0))
        acc.update(_wh(105.0))  # 5 Wh measured
        after = acc.update(_wh(1.0))  # reset, then 1 Wh since
        assert after.value == pytest.approx(6.0, abs=0.01)

    def test_accumulation_continues_after_a_reset(self) -> None:
        acc = EnergyAccumulator()
        acc.update(_wh(100.0))
        acc.update(_wh(105.0))
        acc.update(_wh(1.0))
        assert acc.update(_wh(3.0)).value == pytest.approx(8.0, abs=0.01)

    def test_tiny_decrease_is_not_treated_as_a_reset(self) -> None:
        acc = EnergyAccumulator()
        acc.update(_wh(100.0))
        acc.update(_wh(100.0005))
        assert acc.update(_wh(100.0004)).value >= 0.0


class TestSuspendResume:
    def test_p10_rebaseline_does_not_lose_measured_energy(self) -> None:
        acc = EnergyAccumulator()
        acc.update(_wh(100.0))
        acc.update(_wh(102.0))
        acc.rebaseline()
        assert acc.update(_wh(102.0)).value == pytest.approx(2.0)

    def test_p10_suspended_period_is_not_counted(self) -> None:
        """The counter does not advance while asleep; re-baselining keeps the session honest."""
        acc = EnergyAccumulator()
        acc.update(_wh(100.0))
        acc.update(_wh(101.0))
        acc.rebaseline()
        after = acc.update(_wh(101.5))
        assert after.value == pytest.approx(1.5)

    def test_rebaseline_before_any_reading_is_safe(self) -> None:
        EnergyAccumulator().rebaseline()


class TestInterruption:
    def test_p11_lost_reading_sets_the_flag(self) -> None:
        acc = EnergyAccumulator()
        acc.update(_wh(100.0))
        acc.update(MetricValue.unsupported("driver hiccup"))
        assert acc.interrupted is True

    def test_p11_unavailable_returns_unavailable_not_zero(self) -> None:
        acc = EnergyAccumulator()
        acc.update(_wh(100.0))
        result = acc.update(MetricValue.unsupported("gone"))
        assert result.value is None
        assert result.reason

    def test_total_survives_an_interruption(self) -> None:
        acc = EnergyAccumulator()
        acc.update(_wh(100.0))
        acc.update(_wh(102.0))
        acc.update(MetricValue.unsupported("gap"))
        assert acc.update(_wh(103.0)).value == pytest.approx(3.0)

    def test_no_flag_before_monitoring_started(self) -> None:
        acc = EnergyAccumulator()
        acc.update(MetricValue.unsupported("never supported"))
        assert acc.interrupted is False


class TestReset:
    def test_p12_reset_returns_to_zero(self) -> None:
        acc = EnergyAccumulator()
        acc.update(_wh(100.0))
        acc.update(_wh(105.0))
        acc.reset()
        assert acc.update(_wh(105.0)).value == pytest.approx(0.0)

    def test_reset_clears_the_interrupted_flag(self) -> None:
        acc = EnergyAccumulator()
        acc.update(_wh(100.0))
        acc.update(MetricValue.unsupported("gap"))
        acc.reset()
        assert acc.interrupted is False

    def test_accumulation_resumes_after_reset(self) -> None:
        acc = EnergyAccumulator()
        acc.update(_wh(100.0))
        acc.update(_wh(105.0))
        acc.reset()
        acc.update(_wh(105.0))
        assert acc.update(_wh(107.0)).value == pytest.approx(2.0)
