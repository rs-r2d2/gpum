"""T015: driver-restart recovery, driven through an NVML stub so it needs no GPU.

The failure this prevents: an NVML handle does not survive a driver restart, and a stale one
returns errors forever. Without rebuilding handles the tool looks permanently broken until the
user restarts it — which FR-014 forbids.
"""

from __future__ import annotations

from types import SimpleNamespace

from gpum.backends.nvidia import errors
from gpum.backends.nvidia.backend import NvidiaBackend
from gpum.backends.nvidia.nvml import NvmlError

MIB = 1024 * 1024


class RestartableNvml:
    """An NVML stub whose handles are invalidated by a simulated driver restart."""

    def __init__(self) -> None:
        self.initialised = False
        self._generation = 0
        self._broken = False
        self.init_calls = 0

    # -- control ----------------------------------------------------------
    def restart_driver(self) -> None:
        """Handles issued before this point become permanently invalid."""
        self._generation += 1
        self._broken = True

    def driver_back(self) -> None:
        self._broken = False

    # -- NvmlLibrary surface ----------------------------------------------
    def init(self) -> None:
        self.init_calls += 1
        if self._broken:
            raise NvmlError(errors.NVML_ERROR_DRIVER_NOT_LOADED, "driver not loaded")
        self.initialised = True

    def shutdown(self) -> None:
        self.initialised = False

    def device_count(self) -> int:
        self._check()
        return 1

    def handle_by_index(self, index: int) -> object:
        self._check()
        return SimpleNamespace(generation=self._generation)

    def name(self, handle: object) -> str:
        self._check_handle(handle)
        return "Stub GPU"

    def uuid(self, handle: object) -> str:
        self._check_handle(handle)
        return "GPU-stub-0001"

    def pci_bus_id(self, handle: object) -> str:
        return "0000:01:00.0"

    def is_mig_enabled(self, handle: object) -> bool:
        return False

    def memory_info(self, handle: object) -> tuple[int, int, int | None]:
        self._check_handle(handle)
        return (16311 * MIB, 550 * MIB, 471 * MIB)

    def utilization(self, handle: object) -> tuple[int, int]:
        self._check_handle(handle)
        return (10, 5)

    def running_processes(self, handle: object) -> list[object]:
        self._check_handle(handle)
        return []

    # -- 004: power surface -------------------------------------------------
    def power_usage(self, handle: object) -> float:
        self._check_handle(handle)
        return 17.0

    def power_limit(self, handle: object) -> float:
        self._check_handle(handle)
        return 180.0

    def total_energy(self, handle: object) -> float:
        self._check_handle(handle)
        return 72.431

    def throttle_reasons(self, handle: object) -> int:
        self._check_handle(handle)
        return 0x0

    # -- internals ---------------------------------------------------------
    def _check(self) -> None:
        if self._broken:
            raise NvmlError(errors.NVML_ERROR_UNINITIALIZED, "uninitialised")

    def _check_handle(self, handle: object) -> None:
        self._check()
        if getattr(handle, "generation", -1) != self._generation:
            raise NvmlError(errors.NVML_ERROR_GPU_IS_LOST, "stale handle after driver restart")


class TestHandleRebuild:
    def test_stale_handle_recovers_transparently(self) -> None:
        """Sampling through a driver restart succeeds without the caller doing anything: the
        backend detects the stale handle, rebuilds, and re-samples."""
        nvml = RestartableNvml()
        backend = NvidiaBackend(library=nvml)
        backend.probe()
        devices = list(backend.enumerate_devices())
        assert devices and devices[0].memory_used.is_measurement

        nvml.restart_driver()
        nvml.driver_back()
        sampled = backend.sample_device(devices[0].id)
        assert sampled.memory_used.is_measurement, "did not recover from a stale handle"

    def test_stale_handle_with_driver_still_gone_reports_device_gone(self) -> None:
        """When recovery cannot succeed, the sampler must be told to re-enumerate rather than
        being handed a silently wrong reading."""
        import pytest

        from gpum.backends.base import DeviceGoneError as _Gone

        nvml = RestartableNvml()
        backend = NvidiaBackend(library=nvml)
        backend.probe()
        devices = list(backend.enumerate_devices())
        nvml.restart_driver()  # driver stays down
        with pytest.raises(_Gone):
            backend.sample_device(devices[0].id)

    def test_recovery_rebuilds_handles_and_restores_measurements(self) -> None:
        """FR-014: full reporting returns automatically, with no restart of the tool."""
        nvml = RestartableNvml()
        backend = NvidiaBackend(library=nvml)
        backend.probe()
        first = list(backend.enumerate_devices())
        assert first[0].memory_used.is_measurement

        nvml.restart_driver()
        nvml.driver_back()
        backend.recover()

        after = list(backend.enumerate_devices())
        assert after, "device disappeared after driver restart"
        assert after[0].memory_used.is_measurement, "did not recover after handle rebuild"
        assert after[0].id.key == first[0].id.key, "identity changed across a driver restart"

    def test_recovery_is_attempted_not_assumed(self) -> None:
        nvml = RestartableNvml()
        backend = NvidiaBackend(library=nvml)
        backend.probe()
        before = nvml.init_calls
        nvml.restart_driver()
        backend.recover()
        assert nvml.init_calls > before, "recovery did not re-initialise NVML"

    def test_recovery_while_driver_still_absent_does_not_raise(self) -> None:
        nvml = RestartableNvml()
        backend = NvidiaBackend(library=nvml)
        backend.probe()
        nvml.restart_driver()
        backend.recover()
        backend.recover()

    def test_device_identity_survives_restart(self) -> None:
        """Keys are UUID-based, so history follows the same physical GPU across a restart."""
        nvml = RestartableNvml()
        backend = NvidiaBackend(library=nvml)
        backend.probe()
        before = [d.id.key for d in backend.enumerate_devices()]
        nvml.restart_driver()
        nvml.driver_back()
        backend.recover()
        assert [d.id.key for d in backend.enumerate_devices()] == before
