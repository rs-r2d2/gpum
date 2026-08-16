"""The NVIDIA backend (contracts/backend-interface.md).

Speaks only in `core` types. All NVML specifics live in ``nvml.py`` and ``errors.py``, so
nothing NVML-shaped reaches `core` or `ui` (contract C-13).
"""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Sequence

from gpum.backends.base import DeviceGoneError
from gpum.backends.nvidia import errors
from gpum.backends.nvidia.nvml import NvmlError, NvmlLibrary, NvmlUnavailable
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

__all__ = ["NvidiaBackend"]

_log = logging.getLogger(__name__)

_MIG_REASON = "partitioned GPU (MIG) not supported"


class NvidiaBackend:
    vendor = Vendor.NVIDIA
    name = "nvidia"

    def __init__(self, library: NvmlLibrary | None = None) -> None:
        self._nvml = library or NvmlLibrary()
        self._handles: dict[str, object] = {}
        self._mig: set[str] = set()
        self._ready = False
        self._recovery_attempts = 0

    # -- GpuBackend -----------------------------------------------------------

    def probe(self) -> BackendReport:
        """Never raises — an absent driver is expected, not exceptional (contract C-01)."""
        try:
            self._nvml.init()
        except NvmlUnavailable:
            return BackendReport(
                vendor=self.vendor,
                state=BackendState.LIBRARY_MISSING,
                detail=(
                    "NVIDIA support is not installed. Install it with: pip install 'gpum[nvidia]'"
                ),
            )
        except NvmlError as exc:
            state, detail = errors.backend_state_for(exc.code)
            return BackendReport(vendor=self.vendor, state=state, detail=detail)
        except Exception as exc:  # noqa: BLE001 - contract C-01 is absolute
            _log.debug("unexpected NVML probe failure", exc_info=True)
            return BackendReport(
                vendor=self.vendor,
                state=BackendState.ERROR,
                detail=f"NVIDIA support failed unexpectedly: {exc}",
            )

        self._ready = True
        try:
            count = self._nvml.device_count()
        except NvmlError as exc:
            state, detail = errors.backend_state_for(exc.code)
            return BackendReport(vendor=self.vendor, state=state, detail=detail)

        if count == 0:
            return BackendReport(
                vendor=self.vendor,
                state=BackendState.NO_DEVICES,
                detail="NVIDIA driver is present but reports no GPUs",
            )
        return BackendReport(
            vendor=self.vendor,
            state=BackendState.ACTIVE,
            detail=f"NVIDIA driver active, {count} GPU(s) found",
            device_count=count,
        )

    def enumerate_devices(self) -> Sequence[GpuDevice]:
        if not self._ready and not self._ensure_ready():
            return []
        try:
            count = self._nvml.device_count()
        except NvmlError:
            return []

        devices: list[GpuDevice] = []
        self._handles.clear()
        self._mig.clear()
        for index in range(count):
            try:
                handle = self._nvml.handle_by_index(index)
                key = self._identity(handle, index)
                self._handles[key] = handle
                if self._nvml.is_mig_enabled(handle):
                    self._mig.add(key)
                    devices.append(
                        GpuDevice(
                            id=DeviceId(self.vendor, key, index),
                            name=self._safe_name(handle),
                            vendor_name="NVIDIA",
                            supported=False,
                            unsupported_reason=_MIG_REASON,
                            attribution=Availability.NOT_APPLICABLE,
                        )
                    )
                    continue
                devices.append(self._sample_handle(key, handle, index))
            except NvmlError as exc:
                _log.debug("skipping device %d: %s", index, exc)
                continue
        return devices

    def sample_device(self, device_id: DeviceId) -> GpuDevice:
        if device_id.key in self._mig:
            return GpuDevice(
                id=device_id,
                name="NVIDIA GPU",
                vendor_name="NVIDIA",
                supported=False,
                unsupported_reason=_MIG_REASON,
                attribution=Availability.NOT_APPLICABLE,
            )
        handle = self._handles.get(device_id.key)
        if handle is None:
            raise DeviceGoneError(f"device {device_id.key} is no longer enumerated")
        try:
            return self._sample_handle(device_id.key, handle, device_id.index)
        except (DeviceGoneError, NvmlError) as exc:
            # `_sample_handle` already converts a lost-device NVML error into DeviceGoneError,
            # so both types arrive here.
            gone = isinstance(exc, DeviceGoneError) or errors.is_device_gone(
                getattr(exc, "code", -1)
            )
            if not gone:
                raise
            # A lost handle usually means the driver restarted rather than the card being
            # physically removed. Attempt recovery once and re-sample with a fresh handle; if
            # that fails, report it gone so the sampler re-enumerates.
            if self.recover():
                self.enumerate_devices()
                fresh = self._handles.get(device_id.key)
                if fresh is not None:
                    return self._sample_handle(device_id.key, fresh, device_id.index)
            raise DeviceGoneError(str(exc)) from exc

    def recover(self) -> bool:
        """Rebuild NVML state after a driver restart (FR-014, research D-11).

        An NVML handle does not survive a driver restart, and a stale one returns errors
        indefinitely — without this the tool looks permanently broken until the user restarts
        it. Shutting down and re-initialising is the only way to obtain valid handles.

        Never raises: a driver that is still absent is an expected condition, and the caller
        simply tries again on a later cycle.
        """
        self._recovery_attempts += 1
        self._handles.clear()
        self._mig.clear()
        self._ready = False
        try:
            self._nvml.shutdown()
        except Exception:  # noqa: BLE001 - shutdown must never raise
            _log.debug("NVML shutdown during recovery raised", exc_info=True)
        try:
            self._nvml.init()
        except Exception as exc:  # noqa: BLE001
            _log.debug("NVML recovery attempt %d failed: %s", self._recovery_attempts, exc)
            return False
        self._ready = True
        _log.info("NVML recovered after %d attempt(s)", self._recovery_attempts)
        self._recovery_attempts = 0
        return True

    @property
    def recovery_attempts(self) -> int:
        return self._recovery_attempts

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            device_memory=True,
            device_utilization=True,
            # NVML reports per-process memory on Linux. On Windows under WDDM it does not, and
            # the attribution provider reports that honestly instead (research D-03).
            per_process_memory=True,
            per_process_utilization=False,
            supports_hotplug=True,
        )

    def shutdown(self) -> None:
        self._handles.clear()
        self._mig.clear()
        self._ready = False
        self._nvml.shutdown()

    # -- internals ------------------------------------------------------------

    def _ensure_ready(self) -> bool:
        try:
            self._nvml.init()
        except (NvmlError, Exception):  # noqa: BLE001
            return False
        self._ready = True
        return True

    def _identity(self, handle: object, index: int) -> str:
        """UUID, then PCI bus ID, then a last-resort composite (research D-07).

        Never the bare index: after a driver restart the same index can denote a different
        physical card, which would splice two devices' histories together.
        """
        for getter in (self._nvml.uuid, self._nvml.pci_bus_id):
            try:
                value = getter(handle)
            except NvmlError:
                continue
            if value:
                return value
        return f"{self.vendor}:{index}"

    def _safe_name(self, handle: object) -> str:
        try:
            return self._nvml.name(handle)
        except NvmlError:
            return "NVIDIA GPU"

    def _sample_handle(self, key: str, handle: object, index: int) -> GpuDevice:
        now = dt.datetime.now(dt.UTC)

        try:
            total_bytes, used_bytes, reserved_bytes = self._nvml.memory_info(handle)
            memory_total = MetricValue.available(total_bytes, sampled_at=now)
            memory_used = MetricValue.available(used_bytes, sampled_at=now)
            if reserved_bytes is None:
                # v1 only: `used` includes driver-reserved memory, so it reads high compared
                # with nvidia-smi. Verified at ~471 MiB of overstatement on a 16 GiB card.
                _log.debug("NVML v2 memory unavailable; used includes reserved memory")
        except NvmlError as exc:
            if errors.is_device_gone(exc.code):
                raise DeviceGoneError(str(exc)) from exc
            availability, reason = errors.availability_for(exc.code)
            memory_total = MetricValue(value=None, availability=availability, reason=reason)
            memory_used = MetricValue(value=None, availability=availability, reason=reason)

        try:
            gpu_pct, mem_pct = self._nvml.utilization(handle)
            utilization_gpu = MetricValue.available(gpu_pct, sampled_at=now)
            utilization_memory = MetricValue.available(mem_pct, sampled_at=now)
        except NvmlError as exc:
            availability, reason = errors.availability_for(exc.code)
            utilization_gpu = MetricValue(value=None, availability=availability, reason=reason)
            utilization_memory = MetricValue(value=None, availability=availability, reason=reason)

        # Power fields are read independently: FR-006 requires one being unavailable not to
        # suppress the others.
        power_draw = self._metric(lambda: self._nvml.power_usage(handle), now)
        power_limit = self._metric(lambda: self._nvml.power_limit(handle), now)
        energy_total = self._metric(lambda: self._nvml.total_energy(handle), now)

        try:
            mask: int | None = self._nvml.throttle_reasons(handle)
        except NvmlError:
            mask = None
        limit_reason = errors.limit_reason_for(mask)

        return GpuDevice(
            id=DeviceId(self.vendor, key, index),
            name=self._safe_name(handle),
            vendor_name="NVIDIA",
            memory_total=memory_total,
            memory_used=memory_used,
            utilization_gpu=utilization_gpu,
            utilization_memory=utilization_memory,
            attribution=Availability.NOT_APPLICABLE,
            power_draw=power_draw,
            power_limit=power_limit,
            # The raw cumulative counter. `core.power.EnergyAccumulator` turns it into a
            # session figure; the backend does not keep state across calls.
            energy_session=energy_total,
            limit_reason=limit_reason,
            last_sampled_at=now,
        )

    def _metric(self, read: object, now: dt.datetime) -> MetricValue:
        """Read one optional metric, mapping failure to an explicit unavailable state.

        Never substitutes a number: an unreadable power figure becomes UNSUPPORTED with a
        reason, never 0 W, which would assert the card is drawing nothing (FR-005).
        """
        try:
            value = read()  # type: ignore[operator]
        except NvmlError as exc:
            availability, reason = errors.availability_for(exc.code)
            return MetricValue(value=None, availability=availability, reason=reason)
        except Exception as exc:  # noqa: BLE001
            return MetricValue.unsupported(f"could not be read: {exc}")
        return MetricValue.available(value, sampled_at=now)
