"""T042: per-device sampling cost is structurally pinned (U-13, FR-015, SC-007).

Feature 006 claims to be free: both the compute and the memory-interface figures were already
read on every refresh, so drawing them adds presentation work and no collection work. That claim
was verified once by measuring wall-clock cost before and after, but a measurement taken by hand
guards nothing — the next change to the panel can quietly add a query and nobody finds out until
someone re-measures.

These tests guard the claim by *counting backend calls* rather than timing them, which is what
"something is being sampled twice" actually means. Counting also runs headless on a machine with
no GPU and no driver, as constitution Principle IV requires; the wall-clock companion lives in
``tests/hardware/test_sampling_cost.py`` and is skipped without hardware.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
from collections import Counter
from collections.abc import Sequence

from gpum.backends.fake.backend import FakeBackend
from gpum.core.engine import SamplingEngine
from gpum.core.models import BackendCapabilities, BackendReport, DeviceId, GpuDevice, Vendor
from gpum.core.preferences import Preferences
from gpum.ui.main_window import MainWindow


class CountingBackend:
    """A ``FakeBackend`` that records how often each part of the interface is used.

    Delegation is explicit rather than ``__getattr__``-based so that a method added to the
    backend protocol shows up as an error here instead of being silently uncounted.
    """

    def __init__(self, scenario: str = "two-nvidia") -> None:
        self._inner = FakeBackend(scenario)
        self.vendor: Vendor = self._inner.vendor
        self.name: str = self._inner.name
        self.calls: Counter[str] = Counter()
        #: Per-device tally, so "one device queried twice" cannot hide behind a correct total.
        self.per_device: Counter[str] = Counter()

    def probe(self) -> BackendReport:
        self.calls["probe"] += 1
        return self._inner.probe()

    def enumerate_devices(self) -> Sequence[GpuDevice]:
        self.calls["enumerate_devices"] += 1
        return self._inner.enumerate_devices()

    def sample_device(self, device_id: DeviceId) -> GpuDevice:
        self.calls["sample_device"] += 1
        self.per_device[device_id.key] += 1
        return self._inner.sample_device(device_id)

    def capabilities(self) -> BackendCapabilities:
        self.calls["capabilities"] += 1
        return self._inner.capabilities()

    def shutdown(self) -> None:
        self._inner.shutdown()


def _engine(backend: CountingBackend) -> SamplingEngine:
    return SamplingEngine([backend])


class TestOneQueryPerDevicePerCycle:
    def test_u13_a_cycle_queries_each_device_exactly_once(self) -> None:
        backend = CountingBackend()
        engine = _engine(backend)
        try:
            snapshot = engine.sample()
            backend.calls.clear()
            backend.per_device.clear()
            engine.sample()
        finally:
            engine.shutdown()

        assert backend.calls["sample_device"] == len(snapshot.devices)
        assert set(backend.per_device.values()) == {1}, (
            f"a device was queried more than once in a single cycle: {dict(backend.per_device)}"
        )

    def test_u13_the_count_does_not_drift_over_many_cycles(self) -> None:
        """A per-cycle leak is invisible in one cycle and obvious over twenty."""
        backend = CountingBackend()
        engine = _engine(backend)
        cycles = 20
        try:
            devices = len(engine.sample().devices)
            backend.per_device.clear()
            for _ in range(cycles):
                engine.sample()
        finally:
            engine.shutdown()

        assert devices > 0
        assert set(backend.per_device.values()) == {cycles}, (
            f"expected {cycles} queries per device, got {dict(backend.per_device)}"
        )

    def test_u13_both_activity_figures_come_from_one_query(self) -> None:
        """The heart of FR-015.

        Compute activity and memory-interface activity are two fields of one reading. If a
        future change fetches the memory-interface figure separately, this is what catches it.
        """
        backend = CountingBackend()
        engine = _engine(backend)
        try:
            backend.per_device.clear()
            snapshot = engine.sample()
        finally:
            engine.shutdown()

        reporting_both = [
            d
            for d in snapshot.devices
            if d.utilization_gpu.is_measurement and d.utilization_memory.is_measurement
        ]
        assert reporting_both, "scenario reports neither activity figure; test proves nothing"
        for device in reporting_both:
            assert backend.per_device[device.id.key] == 1, (
                "both activity figures must come from a single sample_device call"
            )


class TestDrawingCostsNothing:
    """Presentation must not reach back to the driver.

    This is the other half of "the feature was free": the panel now draws two graphs and three
    bars from the snapshot and history it is handed, and must not query anything to do it.
    """

    def test_u13_rendering_a_snapshot_issues_no_backend_call(self, qtbot) -> None:
        backend = CountingBackend()
        engine = _engine(backend)
        try:
            snapshot = engine.sample()
        finally:
            engine.shutdown()

        window = MainWindow(Preferences())
        qtbot.addWidget(window)
        backend.calls.clear()
        window.on_snapshot(snapshot)

        assert backend.calls.total() == 0, (
            f"drawing the panel reached the backend: {dict(backend.calls)}"
        )

    def test_u13_repeated_repaints_issue_no_backend_call(self, qtbot) -> None:
        backend = CountingBackend()
        engine = _engine(backend)
        try:
            snapshots = [engine.sample() for _ in range(5)]
        finally:
            engine.shutdown()

        window = MainWindow(Preferences())
        qtbot.addWidget(window)
        backend.calls.clear()
        for index, snapshot in enumerate(snapshots):
            window.on_snapshot(
                dataclasses.replace(
                    snapshot, taken_at=dt.datetime.now(dt.UTC), sequence=index + 1
                )
            )

        assert backend.calls.total() == 0, (
            f"repainting reached the backend: {dict(backend.calls)}"
        )
