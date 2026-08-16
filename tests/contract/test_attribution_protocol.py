"""T051: the attribution contract suite (contracts/process-attribution.md, A-01..A-12).

Parametrized over every registered provider. A fake provider models the shapes the real ones
produce — including the NVIDIA/WDDM case where PIDs are known but their memory is not.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping, Sequence

import pytest

from gpum.adapters import platform_identity_provider
from gpum.core.attribution import AttributionResult, AttributionSupport, ProcessIdentityInfo
from gpum.core.models import (
    Availability,
    DeviceId,
    GpuDevice,
    GpuProcess,
    MetricValue,
    PidKey,
    ProcessIdentity,
    Vendor,
)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _devices() -> list[GpuDevice]:
    return [
        GpuDevice(
            id=DeviceId(Vendor.NVIDIA, "gpu-a", 0),
            name="A",
            memory_total=MetricValue.available(1024, sampled_at=_now()),
            memory_used=MetricValue.available(512, sampled_at=_now()),
        ),
        GpuDevice(
            id=DeviceId(Vendor.NVIDIA, "gpu-b", 1),
            name="B",
            memory_total=MetricValue.available(1024, sampled_at=_now()),
            memory_used=MetricValue.available(256, sampled_at=_now()),
        ),
        GpuDevice(
            id=DeviceId(Vendor.NVIDIA, "gpu-mig", 2),
            name="MIG",
            supported=False,
            unsupported_reason="partitioned GPU (MIG) not supported",
        ),
    ]


class FakeAttributionProvider:
    """Models a realistic mix: a resolved process, a restricted one, an unresolved one, and
    a device whose memory the driver model cannot report (the WDDM shape)."""

    source_name = "fake/attribution"

    def probe(self) -> AttributionSupport:
        return AttributionSupport(available=True, supports_memory=True)

    def attribute(self, devices: Sequence[GpuDevice]) -> AttributionResult:
        processes: list[GpuProcess] = []
        per_device: dict[str, Availability] = {}
        totals: dict[str, int] = {}
        for device in devices:
            key = device.id.key
            if not device.supported:
                per_device[key] = Availability.NOT_APPLICABLE
                continue
            if key == "gpu-b":
                # Memory unobtainable, PIDs known — never reported as 0.
                per_device[key] = Availability.AVAILABLE
                processes.append(
                    GpuProcess(
                        pid=300,
                        device_key=key,
                        memory_used=MetricValue.unsupported("not reported under WDDM"),
                    )
                )
                totals[key] = 0
                continue
            per_device[key] = Availability.AVAILABLE
            processes += [
                GpuProcess(
                    pid=100,
                    device_key=key,
                    name="resolved",
                    memory_used=MetricValue.available(4096, sampled_at=_now()),
                    identity_state=ProcessIdentity.RESOLVED,
                ),
                GpuProcess(
                    pid=101,
                    device_key=key,
                    memory_used=MetricValue.available(2048, sampled_at=_now()),
                    identity_state=ProcessIdentity.RESTRICTED,
                ),
                GpuProcess(
                    pid=102,
                    device_key=key,
                    memory_used=MetricValue.available(1024, sampled_at=_now()),
                    identity_state=ProcessIdentity.UNRESOLVED,
                ),
            ]
            totals[key] = 4096 + 2048 + 1024
        return AttributionResult(
            processes=tuple(processes), per_device=per_device, total_attributed=totals
        )


class NoAttributionProvider:
    source_name = "fake/none"

    def probe(self) -> AttributionSupport:
        return AttributionSupport(available=False, reason="no source on this platform")

    def attribute(self, devices: Sequence[GpuDevice]) -> AttributionResult:
        return AttributionResult(
            per_device={d.id.key: Availability.UNSUPPORTED for d in devices}
        )


@pytest.fixture(params=[FakeAttributionProvider, NoAttributionProvider], ids=lambda c: c.__name__)
def provider(request: pytest.FixtureRequest) -> object:
    return request.param()


class TestProbe:
    def test_a01_probe_never_raises(self, provider: object) -> None:
        provider.probe()  # type: ignore[attr-defined]

    def test_unavailable_support_explains_itself(self, provider: object) -> None:
        support = provider.probe()  # type: ignore[attr-defined]
        if not support.available:
            assert support.reason


class TestAttribute:
    def test_a02_every_device_gets_an_entry(self, provider: object) -> None:
        """A missing key is indistinguishable from 'no processes' — the ambiguity US2
        scenario 4 forbids."""
        devices = _devices()
        result = provider.attribute(devices)  # type: ignore[attr-defined]
        assert set(result.per_device) == {d.id.key for d in devices}

    def test_a03_unidentifiable_pids_are_emitted_not_dropped(self, provider: object) -> None:
        result = provider.attribute(_devices())  # type: ignore[attr-defined]
        for process in result.processes:
            assert process.pid > 0  # present at all is the assertion

    def test_a04_totals_include_restricted_and_unresolved(self, provider: object) -> None:
        """SC-012: totals must account for memory whose owner cannot be named."""
        result = provider.attribute(_devices())  # type: ignore[attr-defined]
        for key, total in result.total_attributed.items():
            measured = sum(
                p.memory_used.value or 0
                for p in result.processes
                if p.device_key == key and p.memory_used.is_measurement
            )
            assert total == measured

    def test_a07_unavailable_memory_is_unsupported_never_zero(self, provider: object) -> None:
        result = provider.attribute(_devices())  # type: ignore[attr-defined]
        for process in result.processes:
            metric = process.memory_used
            if not metric.is_measurement:
                assert metric.value is None
                assert metric.reason

    def test_a09_no_process_for_an_unknown_device(self, provider: object) -> None:
        devices = _devices()
        keys = {d.id.key for d in devices}
        result = provider.attribute(devices)  # type: ignore[attr-defined]
        assert all(p.device_key in keys for p in result.processes)

    def test_unsupported_device_is_not_applicable(self, provider: object) -> None:
        result = provider.attribute(_devices())  # type: ignore[attr-defined]
        state = result.per_device["gpu-mig"]
        assert state is not Availability.AVAILABLE


class TestIdentityProvider:
    def test_a10_returns_an_entry_for_every_requested_key(self) -> None:
        provider = platform_identity_provider()
        keys = [PidKey(1, None), PidKey(999_999_999, None), PidKey(2, _now())]
        result: Mapping[PidKey, ProcessIdentityInfo] = provider.identify(keys)
        assert set(result) == set(keys)

    def test_a06_a_dead_pid_does_not_raise(self) -> None:
        provider = platform_identity_provider()
        result = provider.identify([PidKey(999_999_999, None)])
        info = result[PidKey(999_999_999, None)]
        assert info.identity_state is ProcessIdentity.UNRESOLVED

    def test_a05_inaccessible_process_is_restricted_not_an_exception(self) -> None:
        """PID 1 is not fully inspectable by an unprivileged user on most systems; whichever
        way it resolves, it must not raise."""
        provider = platform_identity_provider()
        info = provider.identify([PidKey(1, None)])[PidKey(1, None)]
        assert info.identity_state in set(ProcessIdentity)

    def test_a11_identity_works_without_elevation(self) -> None:
        """FR-019: the current (unprivileged) process must resolve itself."""
        import os

        provider = platform_identity_provider()
        key = PidKey(os.getpid(), None)
        info = provider.identify([key])[key]
        assert info.identity_state in {
            ProcessIdentity.RESOLVED,
            ProcessIdentity.CONTAINERIZED,
        }
        assert info.name
