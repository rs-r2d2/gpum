"""T098: bounded memory over a long run (FR-024, SC-005, U-10).

Runs at accelerated cadence rather than for 24 real hours: the property under test is that
retention is structural, so a few thousand cycles prove it as well as a day would.
"""

from __future__ import annotations

import gc

from gpum.core.engine import SamplingEngine
from gpum.core.history import DeviceHistory
from gpum.core.models import MetricValue
from gpum.registry import build_backends


class TestBoundedMemory:
    def test_history_never_exceeds_capacity_over_many_cycles(self) -> None:
        history = DeviceHistory("k", window_s=300, interval_ms=1000)
        import datetime as dt

        now = dt.datetime.now(dt.UTC)
        for i in range(86_400):  # a simulated day at 1 Hz
            history.append_memory(MetricValue.available(i, sampled_at=now))
        assert len(history.memory_used) == history.capacity == 300

    def test_engine_state_does_not_grow_with_cycles(self) -> None:
        engine = SamplingEngine(
            build_backends("fake", scenario="two-nvidia"), reenumerate_every=5
        )
        for _ in range(50):
            engine.sample()
        gc.collect()
        baseline = len(engine._states)
        for _ in range(500):
            engine.sample()
        gc.collect()
        assert len(engine._states) == baseline, "per-device state grew with cycle count"
        engine.shutdown()

    def test_snapshots_are_not_retained_by_the_engine(self) -> None:
        """Snapshots use slots and are not weak-referenceable, so this checks referrers
        instead: nothing owned by the engine may still point at an emitted snapshot."""
        engine = SamplingEngine(build_backends("fake", scenario="two-nvidia"))
        snapshot = engine.sample()
        gc.collect()
        referrers = gc.get_referrers(snapshot)
        assert engine not in referrers
        assert engine.__dict__ not in referrers, "the engine retained an emitted snapshot"
        engine.shutdown()
