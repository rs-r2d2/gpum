"""T044, T045: suspend/resume detection (FR-013, research D-10).

Runs with feature 001's fake clock — no suspending anything.
"""

from __future__ import annotations

import datetime as dt

import pytest

from gpum.backends.fake.backend import FakeBackend
from gpum.core.engine import SamplingEngine
from gpum.core.history import DeviceHistory
from gpum.core.models import Availability, MetricValue


class FakeClock:
    def __init__(self) -> None:
        self._now = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)

    def now(self) -> dt.datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += dt.timedelta(seconds=seconds)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def _engine(clock: FakeClock, **kw: object) -> SamplingEngine:
    return SamplingEngine(
        [FakeBackend("two-nvidia")], clock=clock.now, **kw  # type: ignore[arg-type]
    )


class TestDetection:
    def test_ordinary_cycles_are_not_resumes(self, clock: FakeClock) -> None:
        engine = _engine(clock, resume_threshold_s=30.0)
        engine.sample()
        clock.advance(1.0)
        engine.sample()
        assert engine.last_resume is None

    def test_a_long_gap_is_detected_as_a_resume(self, clock: FakeClock) -> None:
        engine = _engine(clock, resume_threshold_s=30.0)
        engine.sample()
        clock.advance(4 * 3600)  # a four-hour suspend
        engine.sample()
        assert engine.last_resume is not None
        assert engine.last_resume.gap_seconds == pytest.approx(4 * 3600)

    def test_a_degraded_backoff_is_not_mistaken_for_a_resume(self, clock: FakeClock) -> None:
        """The threshold sits above a degraded device's 10-cycle backoff so ordinary slowness
        is never misread as a suspend."""
        engine = _engine(clock, resume_threshold_s=30.0)
        engine.sample()
        clock.advance(10.0)
        engine.sample()
        assert engine.last_resume is None

    def test_resume_clears_degradation_backoff(self, clock: FakeClock) -> None:
        engine = _engine(clock, resume_threshold_s=30.0)
        engine.sample()
        for state in engine._states.values():
            state.skip_cycles = 5
        clock.advance(3600)
        engine.sample()
        assert all(s.skip_cycles == 0 for s in engine._states.values())

    def test_resume_forces_reenumeration(self, clock: FakeClock) -> None:
        backend = FakeBackend("two-nvidia")
        engine = SamplingEngine(
            [backend], clock=clock.now, reenumerate_every=1000, resume_threshold_s=30.0
        )
        engine.sample()
        before = backend.enumerate_calls
        clock.advance(3600)
        engine.sample()
        assert backend.enumerate_calls > before, "a GPU may have changed state across suspend"

    def test_resume_is_reported_once_not_every_cycle(self, clock: FakeClock) -> None:
        engine = _engine(clock, resume_threshold_s=30.0)
        engine.sample()
        clock.advance(3600)
        engine.sample()
        assert engine.last_resume is not None
        clock.advance(1.0)
        engine.sample()
        assert engine.last_resume is None


class TestHistoryGap:
    def test_a_suspend_renders_as_a_gap_not_a_line(self) -> None:
        """SC-008: drawing across a four-hour suspend asserts measurements never taken."""
        history = DeviceHistory("k", window_s=300, interval_ms=1000)
        history.append_memory(MetricValue.available(100, sampled_at=dt.datetime.now(dt.UTC)))
        history.append_gap("suspended")
        history.append_memory(MetricValue.available(200, sampled_at=dt.datetime.now(dt.UTC)))
        values = [p.value for p in history.memory_used]
        assert values == [100, None, 200]
        assert 0 not in values

    def test_the_gap_records_why(self) -> None:
        history = DeviceHistory("k", window_s=300, interval_ms=1000)
        history.append_gap("suspended")
        assert history.memory_used[-1].availability is not Availability.AVAILABLE
