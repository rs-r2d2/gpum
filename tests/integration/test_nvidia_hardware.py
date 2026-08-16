"""T035, T071: tests that need real NVIDIA hardware.

Marked `hardware` and deselected by default, per constitution Principle IV: hardware-dependent
tests must never gate the default suite. Run with `pytest -m hardware`.
"""

from __future__ import annotations

import pytest

from gpum.backends.nvidia.attribution import NvmlAttributionProvider
from gpum.backends.nvidia.backend import NvidiaBackend
from gpum.core.models import BackendState

pytestmark = pytest.mark.hardware


@pytest.fixture
def backend() -> NvidiaBackend:
    b = NvidiaBackend()
    report = b.probe()
    if report.state is not BackendState.ACTIVE:
        pytest.skip(f"no active NVIDIA GPU: {report.detail}")
    yield b
    b.shutdown()


class TestRealDevices:
    def test_enumerates_at_least_one_device(self, backend: NvidiaBackend) -> None:
        assert list(backend.enumerate_devices())

    def test_memory_figures_are_plausible(self, backend: NvidiaBackend) -> None:
        for device in backend.enumerate_devices():
            if not device.supported:
                continue
            sampled = backend.sample_device(device.id)
            assert sampled.memory_total.is_measurement
            total = sampled.memory_total.value
            assert 256 * 1024**2 < total < 1024 * 1024**3, "implausible total memory"
            assert sampled.memory_used.value <= total

    def test_identity_is_a_uuid_not_an_index(self, backend: NvidiaBackend) -> None:
        for device in backend.enumerate_devices():
            assert not device.id.key.isdigit()

    def test_identity_is_stable_across_reenumeration(self, backend: NvidiaBackend) -> None:
        first = [d.id.key for d in backend.enumerate_devices()]
        second = [d.id.key for d in backend.enumerate_devices()]
        assert first == second


class TestRealAttribution:
    def test_attribution_probe_succeeds_or_explains(self, backend: NvidiaBackend) -> None:
        provider = NvmlAttributionProvider(backend)
        support = provider.probe()
        assert support.available or support.reason

    def test_every_device_gets_an_attribution_entry(self, backend: NvidiaBackend) -> None:
        provider = NvmlAttributionProvider(backend)
        devices = list(backend.enumerate_devices())
        result = provider.attribute(devices)
        assert set(result.per_device) == {d.id.key for d in devices}

    def test_process_memory_is_never_zero_when_unavailable(
        self, backend: NvidiaBackend
    ) -> None:
        """On Windows/WDDM this is the expected path; on Linux memory should be present."""
        provider = NvmlAttributionProvider(backend)
        result = provider.attribute(list(backend.enumerate_devices()))
        for process in result.processes:
            if not process.memory_used.is_measurement:
                assert process.memory_used.value is None
                assert process.memory_used.reason
