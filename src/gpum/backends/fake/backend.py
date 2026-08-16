"""A simulated backend (research D-12).

Not merely a test convenience: it doubles as the application's demo mode and is the only way
to exercise failure paths — timeouts, permission denial, hot-plug, MIG — on demand. It is
written against the protocol with no NVML-shaped assumptions.
"""

from __future__ import annotations

import datetime as dt
import itertools
import random
import threading
import time
from collections.abc import Sequence

from gpum.backends.base import DeviceGoneError
from gpum.backends.fake.scenarios import DEFAULT_SCENARIO, SCENARIOS, DeviceSpec, Scenario
from gpum.core.models import (
    Availability,
    BackendCapabilities,
    BackendReport,
    BackendState,
    DeviceId,
    GpuDevice,
    MetricValue,
    Vendor,
)

__all__ = ["FakeBackend"]

_HANG_SECONDS = 30.0


class FakeBackend:
    """Scripted GPUs driven by a :class:`Scenario`."""

    vendor = Vendor.UNKNOWN
    name = "fake"

    def __init__(self, scenario: Scenario | str | None = None) -> None:
        if scenario is None:
            scenario = DEFAULT_SCENARIO
        if isinstance(scenario, str):
            scenario = SCENARIOS[scenario]
        self._scenario = scenario
        self._specs: dict[str, DeviceSpec] = {d.key: d for d in scenario.devices}
        self._order: list[str] = [d.key for d in scenario.devices]
        self._hanging = any(d.hangs for d in scenario.devices)
        self._hang_enabled = False
        self._rng = random.Random(1234)
        self._cycle = itertools.count()
        self._lock = threading.Lock()
        self.enumerate_calls = 0

    # -- test / demo controls -------------------------------------------------

    @property
    def hanging_key(self) -> str:
        return next((k for k, s in self._specs.items() if s.hangs), "")

    def hang(self, enabled: bool) -> None:
        """Turn the scripted hang on or off, so timeout paths can be exercised."""
        self._hang_enabled = enabled

    def add_device(self, key: str, name: str) -> None:
        with self._lock:
            self._specs[key] = DeviceSpec(key, name)
            self._order.append(key)

    def remove_device(self, key: str) -> None:
        with self._lock:
            self._specs.pop(key, None)
            if key in self._order:
                self._order.remove(key)

    # -- GpuBackend -----------------------------------------------------------

    def probe(self) -> BackendReport:
        if not self._specs:
            return BackendReport(
                vendor=self.vendor,
                state=BackendState.NO_DEVICES,
                detail="Simulated backend: no devices in this scenario",
            )
        return BackendReport(
            vendor=self.vendor,
            state=BackendState.ACTIVE,
            detail=f"Simulated backend running scenario '{self._scenario.name}'",
            device_count=len(self._specs),
        )

    def enumerate_devices(self) -> Sequence[GpuDevice]:
        self.enumerate_calls += 1
        with self._lock:
            order = list(self._order)
            specs = dict(self._specs)
        return [self._device(specs[k], i) for i, k in enumerate(order) if k in specs]

    def sample_device(self, device_id: DeviceId) -> GpuDevice:
        spec = self._specs.get(device_id.key)
        if spec is None:
            raise DeviceGoneError(f"device {device_id.key} is gone")
        if spec.hangs and self._hang_enabled:
            time.sleep(_HANG_SECONDS)
        index = self._order.index(spec.key) if spec.key in self._order else 0
        return self._device(spec, index, jitter=True)

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            device_memory=True,
            device_utilization=any(s.utilization is not None for s in self._specs.values()),
            per_process_memory=any(
                s.attribution is Availability.AVAILABLE for s in self._specs.values()
            ),
            per_process_utilization=False,
            supports_hotplug=True,
        )

    def shutdown(self) -> None:
        """Idempotent and safe before any init (contract C-09)."""
        self._hang_enabled = False

    # -- internals ------------------------------------------------------------

    def _device(self, spec: DeviceSpec, index: int, *, jitter: bool = False) -> GpuDevice:
        now = dt.datetime.now(dt.UTC)
        if not spec.supported:
            return GpuDevice(
                id=DeviceId(spec.vendor, spec.key, index),
                name=spec.name,
                vendor_name=spec.vendor.name,
                supported=False,
                unsupported_reason=spec.unsupported_reason,
                attribution=Availability.NOT_APPLICABLE,
                last_sampled_at=now,
            )

        used = spec.memory_used
        util = spec.utilization
        if jitter:
            wobble = self._rng.uniform(-0.05, 0.05)
            used = max(0, min(spec.memory_total, int(used * (1 + wobble))))
            if util is not None:
                util = max(0, min(100, util + self._rng.randint(-8, 8)))

        utilization = (
            MetricValue.available(util, sampled_at=now)
            if util is not None
            else MetricValue.unsupported("utilization is not reported by this device")
        )
        return GpuDevice(
            id=DeviceId(spec.vendor, spec.key, index),
            name=spec.name,
            vendor_name=spec.vendor.name,
            memory_total=MetricValue.available(spec.memory_total, sampled_at=now),
            memory_used=MetricValue.available(used, sampled_at=now),
            utilization_gpu=utilization,
            utilization_memory=MetricValue.unsupported("not simulated"),
            attribution=spec.attribution,
            attribution_reason=spec.attribution_reason,
            last_sampled_at=now,
        )

    @property
    def scenario(self) -> Scenario:
        return self._scenario

    @property
    def specs(self) -> dict[str, DeviceSpec]:
        return dict(self._specs)
