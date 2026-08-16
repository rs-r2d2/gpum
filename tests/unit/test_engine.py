"""T013: the sampling engine's timeout and degradation state machine (FR-014).

Runs with a fake clock and no Qt at all — the reason `SamplingEngine` lives in `core` and the
`QObject` wrapper lives in `ui` (plan.md § Project Structure).
"""

import dataclasses
import datetime as dt
import threading

import pytest

from gpum.backends.fake.backend import FakeBackend
from gpum.backends.fake.scenarios import SCENARIOS
from gpum.core.engine import SamplingEngine
from gpum.core.models import Availability


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


def _engine(backend: FakeBackend, clock: FakeClock, **kw: object) -> SamplingEngine:
    return SamplingEngine(backends=[backend], clock=clock.now, **kw)  # type: ignore[arg-type]


class TestSnapshots:
    def test_sequence_is_monotonic(self, clock: FakeClock) -> None:
        engine = _engine(FakeBackend(SCENARIOS["two-nvidia"]), clock)
        seqs = [engine.sample().sequence for _ in range(5)]
        assert seqs == sorted(seqs)
        assert len(set(seqs)) == 5

    def test_snapshot_emitted_even_with_no_devices(self, clock: FakeClock) -> None:
        """FR-018: an empty device list is normal, not a failure."""
        engine = _engine(FakeBackend(SCENARIOS["empty"]), clock)
        snapshot = engine.sample()
        assert snapshot.devices == ()
        assert snapshot.discovery.backends_attempted

    def test_snapshot_is_immutable(self, clock: FakeClock) -> None:
        engine = _engine(FakeBackend(SCENARIOS["two-nvidia"]), clock)
        snapshot = engine.sample()
        assert isinstance(snapshot.devices, tuple)
        with pytest.raises((AttributeError, TypeError, dataclasses.FrozenInstanceError)):
            snapshot.devices = ()  # type: ignore[misc]

    def test_taken_at_comes_from_the_injected_clock(self, clock: FakeClock) -> None:
        engine = _engine(FakeBackend(SCENARIOS["two-nvidia"]), clock)
        clock.advance(120)
        assert engine.sample().taken_at == clock.now()


class TestTimeoutAndDegradation:
    def test_timeout_marks_the_device_stale(self, clock: FakeClock) -> None:
        backend = FakeBackend(SCENARIOS["one-device-hangs"])
        engine = _engine(backend, clock, per_device_timeout_s=0.05)
        engine.sample()  # first cycle succeeds and seeds the previous value
        backend.hang(True)
        snapshot = engine.sample()
        hung = next(d for d in snapshot.devices if d.id.key == backend.hanging_key)
        assert hung.memory_used.availability is Availability.STALE

    def test_stale_keeps_the_previous_value_and_original_timestamp(
        self, clock: FakeClock
    ) -> None:
        """FR-016: a stale reading must show its true age, not the snapshot's time."""
        backend = FakeBackend(SCENARIOS["one-device-hangs"])
        engine = _engine(backend, clock, per_device_timeout_s=0.05)
        first = engine.sample()
        original = next(d for d in first.devices if d.id.key == backend.hanging_key)
        original_value = original.memory_used.value
        original_time = original.memory_used.sampled_at

        backend.hang(True)
        clock.advance(30)
        snapshot = engine.sample()
        hung = next(d for d in snapshot.devices if d.id.key == backend.hanging_key)
        assert hung.memory_used.value == original_value
        assert hung.memory_used.sampled_at == original_time

    def test_three_consecutive_timeouts_degrade_the_device(self, clock: FakeClock) -> None:
        backend = FakeBackend(SCENARIOS["one-device-hangs"])
        engine = _engine(backend, clock, per_device_timeout_s=0.05, degrade_after=3)
        engine.sample()
        backend.hang(True)
        for _ in range(3):
            engine.sample()
        snapshot = engine.sample()
        hung = next(d for d in snapshot.devices if d.id.key == backend.hanging_key)
        assert hung.memory_used.availability is Availability.DEGRADED

    def test_other_devices_keep_updating_while_one_hangs(self, clock: FakeClock) -> None:
        """U-03 / FR-014 — the whole point of a per-device timeout."""
        backend = FakeBackend(SCENARIOS["one-device-hangs"])
        engine = _engine(backend, clock, per_device_timeout_s=0.05)
        engine.sample()
        backend.hang(True)
        snapshot = engine.sample()
        healthy = [d for d in snapshot.devices if d.id.key != backend.hanging_key]
        assert healthy
        assert all(d.memory_used.availability is Availability.AVAILABLE for d in healthy)

    def test_recovery_is_immediate_on_any_success(self, clock: FakeClock) -> None:
        backend = FakeBackend(SCENARIOS["one-device-hangs"])
        engine = _engine(backend, clock, per_device_timeout_s=0.05, degrade_after=2)
        engine.sample()
        backend.hang(True)
        for _ in range(4):
            engine.sample()
        backend.hang(False)
        engine.reset_backoff()
        snapshot = engine.sample()
        recovered = next(d for d in snapshot.devices if d.id.key == backend.hanging_key)
        assert recovered.memory_used.availability is Availability.AVAILABLE

    def test_a_hanging_device_does_not_block_the_cycle(self, clock: FakeClock) -> None:
        backend = FakeBackend(SCENARIOS["one-device-hangs"])
        engine = _engine(backend, clock, per_device_timeout_s=0.05)
        engine.sample()
        backend.hang(True)
        done = threading.Event()

        def run() -> None:
            engine.sample()
            done.set()

        threading.Thread(target=run, daemon=True).start()
        assert done.wait(timeout=3), "one hung device stalled the entire sampling cycle"


class TestReEnumeration:
    def test_reenumerates_on_the_configured_cadence(self, clock: FakeClock) -> None:
        backend = FakeBackend(SCENARIOS["two-nvidia"])
        engine = _engine(backend, clock, reenumerate_every=3)
        counts = []
        for _ in range(7):
            engine.sample()
            counts.append(backend.enumerate_calls)
        assert counts[-1] < 7, "should not re-enumerate on every cycle (research D-08)"
        assert counts[-1] >= 2

    def test_new_device_appears(self, clock: FakeClock) -> None:
        backend = FakeBackend(SCENARIOS["two-nvidia"])
        engine = _engine(backend, clock, reenumerate_every=1)
        before = len(engine.sample().devices)
        backend.add_device("GPU-hotplug-1", "RTX 4090")
        after = len(engine.sample().devices)
        assert after == before + 1

    def test_removed_device_disappears(self, clock: FakeClock) -> None:
        backend = FakeBackend(SCENARIOS["two-nvidia"])
        engine = _engine(backend, clock, reenumerate_every=1)
        snapshot = engine.sample()
        victim = snapshot.devices[0].id.key
        backend.remove_device(victim)
        assert victim not in {d.id.key for d in engine.sample().devices}
