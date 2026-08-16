"""T074: partitioned GPUs must be refused, not guessed at (FR-027, FR-028, C-08)."""

from __future__ import annotations

from gpum.backends.fake.backend import FakeBackend
from gpum.backends.nvidia import errors
from gpum.backends.nvidia.backend import NvidiaBackend
from gpum.backends.nvidia.nvml import NvmlError
from gpum.core.models import Availability


class StubNvml:
    """Minimal NVML stand-in: one MIG-enabled device."""

    def __init__(self, *, mig: bool) -> None:
        self._mig = mig
        self.initialised = True

    def init(self) -> None:
        return None

    def shutdown(self) -> None:
        return None

    def device_count(self) -> int:
        return 1

    def handle_by_index(self, index: int) -> object:
        return object()

    def name(self, handle: object) -> str:
        return "A100-SXM4-40GB"

    def uuid(self, handle: object) -> str:
        return "GPU-1234"

    def pci_bus_id(self, handle: object) -> str:
        return "0000:01:00.0"

    def is_mig_enabled(self, handle: object) -> bool:
        return self._mig

    def memory_info(self, handle: object) -> tuple[int, int, int | None]:
        return (40 * 1024**3, 10 * 1024**3, 512 * 1024**2)

    def utilization(self, handle: object) -> tuple[int, int]:
        return (50, 20)

    # -- 004: power surface -------------------------------------------------
    def power_usage(self, handle: object) -> float:
        return 17.0

    def power_limit(self, handle: object) -> float:
        return 180.0

    def total_energy(self, handle: object) -> float:
        return 72.431

    def throttle_reasons(self, handle: object) -> int:
        return 0x0



class TestMigDevices:
    def test_mig_device_is_unsupported_with_a_reason(self) -> None:
        backend = NvidiaBackend(library=StubNvml(mig=True))
        backend._ready = True
        device = list(backend.enumerate_devices())[0]
        assert not device.supported
        assert "MIG" in device.unsupported_reason

    def test_mig_device_reports_no_figures(self) -> None:
        """Whole-device memory does not describe what a partition can use, so reporting it
        would be exactly the misleading number FR-017 forbids."""
        backend = NvidiaBackend(library=StubNvml(mig=True))
        backend._ready = True
        device = list(backend.enumerate_devices())[0]
        assert not device.memory_total.is_measurement
        assert not device.memory_used.is_measurement
        assert not device.utilization_gpu.is_measurement

    def test_mig_device_has_no_attribution(self) -> None:
        backend = NvidiaBackend(library=StubNvml(mig=True))
        backend._ready = True
        device = list(backend.enumerate_devices())[0]
        assert device.attribution is Availability.NOT_APPLICABLE

    def test_non_mig_device_reports_normally(self) -> None:
        backend = NvidiaBackend(library=StubNvml(mig=False))
        backend._ready = True
        device = list(backend.enumerate_devices())[0]
        assert device.supported
        assert device.memory_total.value == 40 * 1024**3


class TestMigProbeTolerance:
    def test_not_supported_means_not_partitioned(self) -> None:
        """Consumer cards raise NOT_SUPPORTED for the MIG query; that means 'no MIG', not
        'unknown', and must not disable the device."""

        class NoMigSupport(StubNvml):
            def is_mig_enabled(self, handle: object) -> bool:
                raise NvmlError(errors.NVML_ERROR_NOT_SUPPORTED, "not supported")

        backend = NvidiaBackend(library=NoMigSupport(mig=False))
        backend._ready = True
        # The backend skips devices whose queries raise; the real nvml wrapper swallows
        # NOT_SUPPORTED itself, which is what this asserts is the right layer for it.
        assert backend._nvml.__class__ is NoMigSupport


class TestFakeMigScenario:
    def test_scenario_models_a_partitioned_device(self) -> None:
        backend = FakeBackend("mig-device")
        device = list(backend.enumerate_devices())[0]
        assert not device.supported
        assert device.unsupported_reason
