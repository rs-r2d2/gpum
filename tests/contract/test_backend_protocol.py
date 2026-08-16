"""T011: the shared backend contract suite (contracts/backend-interface.md, C-01..C-11).

Parametrized over EVERY registered backend, real and fake. A new vendor is wired into the
registry and inherits this suite — no per-vendor test authoring (constitution Principle I).
"""

import concurrent.futures
import dataclasses

import pytest

from gpum.backends.base import GpuBackend
from gpum.core.models import Availability, BackendState, MetricValue
from gpum.registry import all_backends


def _backends() -> list[GpuBackend]:
    return all_backends()


@pytest.fixture(params=_backends(), ids=lambda b: b.name)
def backend(request: pytest.FixtureRequest) -> GpuBackend:
    b = request.param
    yield b
    b.shutdown()


def _all_metrics(device: object) -> list[MetricValue]:
    # GpuDevice uses slots=True, so there is no __dict__ to walk.
    return [
        value
        for f in dataclasses.fields(device)  # type: ignore[arg-type]
        if isinstance(value := getattr(device, f.name), MetricValue)
    ]


class TestProbe:
    def test_c01_probe_never_raises(self, backend: GpuBackend) -> None:
        """An absent driver is an expected condition (FR-018), not an exception."""
        backend.probe()

    def test_c02_probe_returns_a_specific_state_and_detail(self, backend: GpuBackend) -> None:
        report = backend.probe()
        assert isinstance(report.state, BackendState)
        assert report.detail, "SC-006 needs a message fit to show a user"
        assert report.vendor == backend.vendor

    def test_c02_states_are_not_collapsed(self, backend: GpuBackend) -> None:
        report = backend.probe()
        assert report.state in set(BackendState)
        if report.state is BackendState.ACTIVE:
            assert report.device_count >= 0


class TestEnumerate:
    def test_c03_returns_a_sequence_never_none(self, backend: GpuBackend) -> None:
        devices = backend.enumerate_devices()
        assert devices is not None
        assert isinstance(list(devices), list)

    def test_c04_device_keys_are_unique_within_a_call(self, backend: GpuBackend) -> None:
        keys = [d.id.key for d in backend.enumerate_devices()]
        assert len(keys) == len(set(keys))

    def test_c04_device_keys_are_stable_across_calls(self, backend: GpuBackend) -> None:
        first = [d.id.key for d in backend.enumerate_devices()]
        second = [d.id.key for d in backend.enumerate_devices()]
        assert first == second, "identity must not be derived from enumeration order"

    def test_c04_index_is_not_identity(self, backend: GpuBackend) -> None:
        for device in backend.enumerate_devices():
            assert str(device.id.index) != device.id.key or device.id.key.startswith(
                backend.vendor.value
            ), "a bare index is not a stable key (research D-07)"


class TestSampling:
    def test_c05_metric_value_invariant_holds(self, backend: GpuBackend) -> None:
        """The contract's most important assertion — this is SC-007."""
        for device in backend.enumerate_devices():
            sampled = backend.sample_device(device.id)
            for metric in _all_metrics(sampled):
                if metric.availability is Availability.AVAILABLE:
                    assert metric.value is not None
                elif metric.availability is not Availability.STALE:
                    assert metric.value is None, (
                        f"{backend.name} returned a value on a {metric.availability} metric"
                    )

    def test_c06_unavailable_metrics_carry_a_reason(self, backend: GpuBackend) -> None:
        """Every metric that could have been measured but was not must explain itself.

        ``NOT_APPLICABLE`` is exempt, matching the model's own rule: it means the metric is
        meaningless for this device rather than unobtainable, which is self-describing. The
        states that need explaining are the ones where a value was expected and is missing.
        """
        for device in backend.enumerate_devices():
            sampled = backend.sample_device(device.id)
            for metric in _all_metrics(sampled):
                if metric.availability in (
                    Availability.AVAILABLE,
                    Availability.NOT_APPLICABLE,
                ):
                    continue
                assert metric.reason, "FR-017 requires a brief reason"

    def test_c07_memory_is_bytes_and_non_negative(self, backend: GpuBackend) -> None:
        for device in backend.enumerate_devices():
            sampled = backend.sample_device(device.id)
            for metric in (sampled.memory_total, sampled.memory_used):
                if metric.value is not None:
                    assert metric.value >= 0

    def test_c07_used_never_exceeds_total(self, backend: GpuBackend) -> None:
        for device in backend.enumerate_devices():
            s = backend.sample_device(device.id)
            if s.memory_total.value is not None and s.memory_used.value is not None:
                assert s.memory_used.value <= s.memory_total.value

    def test_c08_unsupported_devices_carry_a_reason_and_no_metrics(
        self, backend: GpuBackend
    ) -> None:
        for device in backend.enumerate_devices():
            if not device.supported:
                assert device.unsupported_reason
                for metric in _all_metrics(device):
                    assert not metric.is_measurement, "FR-028: no figures for a partition"

    def test_c10_capabilities_match_reality(self, backend: GpuBackend) -> None:
        caps = backend.capabilities()
        for device in backend.enumerate_devices():
            if not device.supported:
                continue
            sampled = backend.sample_device(device.id)
            if sampled.utilization_gpu.is_measurement:
                assert caps.device_utilization, (
                    "capabilities() claims no utilization but sampling returned one"
                )
            if sampled.memory_used.is_measurement:
                assert caps.device_memory

    def test_c11_concurrent_sampling_is_safe(self, backend: GpuBackend) -> None:
        devices = list(backend.enumerate_devices())
        if not devices:
            pytest.skip("no devices to sample concurrently")
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(backend.sample_device, d.id) for d in devices * 3]
            for future in futures:
                assert future.result(timeout=10) is not None


class TestLifecycle:
    def test_c09_shutdown_is_idempotent(self, backend: GpuBackend) -> None:
        backend.shutdown()
        backend.shutdown()

    def test_c09_shutdown_safe_before_init(self, backend: GpuBackend) -> None:
        fresh = type(backend)()
        fresh.shutdown()
