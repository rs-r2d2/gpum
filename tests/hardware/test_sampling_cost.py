"""T042: per-device sampling cost measured against a recorded budget (U-13, FR-015, SC-007).

The structural half of this guard — that nothing is queried twice — lives in
``tests/integration/test_sampling_cost.py`` and runs without a GPU. This is the wall-clock half:
the same query can get more expensive without the call count moving, if a cheap NVML field is
swapped for an expensive one.

**Where the budget comes from.** Measured on this project's reference hardware (RTX 5060 Ti,
driver 580.x): 0.031 ms mean after feature 002, 1.000 ms after feature 004 added power, energy,
and throttle reasons, and 0.994 ms after feature 006 — unchanged, because feature 006 collects
nothing new. The ceiling below sits at roughly 1.8x the measured mean, which a second full set
of driver reads would breach while ordinary jitter does not.

The mean, not the p99, carries the assertion. A tail figure taken from a few hundred samples on
a desktop moves with whatever else is running, and a test that fails for unrelated reasons stops
being read. The p99 is asserted too, but loosely, and only to catch a pathological tail.
"""

from __future__ import annotations

import statistics
import time

import pytest

from gpum.core.engine import DEFAULT_TIMEOUT_S, SamplingEngine
from gpum.registry import build_backends

#: ~1.8x the 0.994 ms measured after feature 006. A doubling of query work breaches this.
MEAN_BUDGET_MS = 1.8
#: Loose: catches a pathological tail without failing because a browser started a video.
P99_BUDGET_MS = 8.0

SAMPLES = 300


@pytest.fixture
def backend_and_device():
    backends = build_backends("nvidia")
    engine = SamplingEngine(backends)
    devices = engine.sample().devices
    if not devices:
        engine.shutdown()
        pytest.skip("no NVIDIA devices present")
    yield backends[0], devices[0].id
    engine.shutdown()


def _measure(backend, device_id, samples: int = SAMPLES) -> list[float]:
    timings = []
    for _ in range(samples):
        start = time.perf_counter()
        backend.sample_device(device_id)
        timings.append((time.perf_counter() - start) * 1000)
    return sorted(timings)


class TestPerDeviceQueryCost:
    def test_u13_mean_query_cost_is_within_budget(self, backend_and_device) -> None:
        backend, device_id = backend_and_device
        timings = _measure(backend, device_id)
        mean = statistics.mean(timings)
        assert mean <= MEAN_BUDGET_MS, (
            f"per-device query cost {mean:.3f} ms exceeds the {MEAN_BUDGET_MS} ms budget — "
            "something is being sampled that was not before"
        )

    def test_u13_tail_query_cost_is_within_budget(self, backend_and_device) -> None:
        backend, device_id = backend_and_device
        timings = _measure(backend, device_id)
        p99 = timings[int(0.99 * len(timings)) - 1]
        assert p99 <= P99_BUDGET_MS, f"p99 query cost {p99:.3f} ms exceeds {P99_BUDGET_MS} ms"

    def test_query_cost_keeps_headroom_over_the_timeout(self, backend_and_device) -> None:
        """The 100 ms per-device timeout is only meaningful while a healthy query is far
        beneath it; if the two converge, healthy devices start being marked degraded."""
        backend, device_id = backend_and_device
        timings = _measure(backend, device_id, samples=100)
        p99 = timings[int(0.99 * len(timings)) - 1]
        assert p99 < DEFAULT_TIMEOUT_S * 1000 / 10, (
            f"p99 {p99:.3f} ms leaves under 10x headroom against the "
            f"{DEFAULT_TIMEOUT_S * 1000:.0f} ms timeout"
        )


class TestBothActivityFiguresAreFree:
    def test_u13_reading_both_figures_costs_one_query(self, backend_and_device) -> None:
        """FR-015 in its strongest form: on real hardware, both activity figures arrive from
        the same call, so US3 cost nothing to add."""
        backend, device_id = backend_and_device
        device = backend.sample_device(device_id)
        assert device.utilization_gpu.is_measurement
        assert device.utilization_memory.is_measurement, (
            "NVML reports memory-interface utilization; if this is unavailable the figure is "
            "not being read where it used to be"
        )
        # Both came from the single call above — no second query was made to obtain either.
        assert device.utilization_gpu.sampled_at == device.utilization_memory.sampled_at
