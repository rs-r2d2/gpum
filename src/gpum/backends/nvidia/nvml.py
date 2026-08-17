"""The only module in the codebase permitted to import ``pynvml`` (contract C-13).

Everything NVML-shaped stops here: handles, structs, and error codes never cross out of this
file. That containment is what keeps the NVIDIA-first delivery from quietly shaping the vendor
abstraction around NVML (plan.md § Principle I mitigations), and it is enforced by
``tests/unit/test_import_boundaries.py``.

The binding is imported lazily. ``nvidia-ml-py`` is a pure-Python ctypes wrapper that imports
successfully with no driver present, so a missing driver surfaces at ``init()`` as a catchable
error rather than an import crash (research D-02).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gpum.backends.nvidia import errors

__all__ = ["NvmlError", "NvmlLibrary", "NvmlProcessInfo"]


class NvmlError(Exception):
    """An NVML call failed, carrying the raw return code for mapping."""

    def __init__(self, code: int, message: str = "") -> None:
        super().__init__(message or f"NVML error {code}")
        self.code = code


class NvmlUnavailable(NvmlError):
    """The binding itself is not installed."""


@dataclass(frozen=True, slots=True)
class NvmlProcessInfo:
    pid: int
    #: Bytes, or ``None`` when the driver cannot report it — NVML returns the PID but no usable
    #: memory figure. Kept nullable rather than defaulted to 0: a zero here would travel up as a
    #: measurement (research D-03).
    used_gpu_memory: int | None


class NvmlLibrary:
    """A thin, typed facade over ``pynvml``."""

    def __init__(self) -> None:
        self._nvml: Any = None
        self._initialised = False

    # -- lifecycle ------------------------------------------------------------

    def load(self) -> None:
        """Import the binding. Raises :class:`NvmlUnavailable` if it is not installed."""
        if self._nvml is not None:
            return
        try:
            import pynvml  # noqa: PLC0415 - deliberately lazy
        except ImportError as exc:
            raise NvmlUnavailable(
                errors.NVML_ERROR_LIBRARY_NOT_FOUND,
                "the nvidia-ml-py package is not installed",
            ) from exc
        self._nvml = pynvml

    def init(self) -> None:
        """Initialise NVML. Raises :class:`NvmlError` when no driver is present."""
        self.load()
        try:
            self._nvml.nvmlInit()
        except Exception as exc:  # noqa: BLE001 - normalised below
            raise self._wrap(exc) from exc
        self._initialised = True

    def shutdown(self) -> None:
        """Idempotent, and safe when init never succeeded (contract C-09)."""
        if not self._initialised or self._nvml is None:
            return
        try:
            self._nvml.nvmlShutdown()
        except Exception:  # noqa: BLE001 - shutdown must never raise
            pass
        finally:
            self._initialised = False

    @property
    def initialised(self) -> bool:
        return self._initialised

    # -- queries --------------------------------------------------------------

    def device_count(self) -> int:
        return int(self._call(self._nvml.nvmlDeviceGetCount))

    def handle_by_index(self, index: int) -> Any:
        return self._call(self._nvml.nvmlDeviceGetHandleByIndex, index)

    def name(self, handle: Any) -> str:
        value = self._call(self._nvml.nvmlDeviceGetName, handle)
        return value.decode() if isinstance(value, bytes) else str(value)

    def uuid(self, handle: Any) -> str:
        value = self._call(self._nvml.nvmlDeviceGetUUID, handle)
        return value.decode() if isinstance(value, bytes) else str(value)

    def pci_bus_id(self, handle: Any) -> str:
        info = self._call(self._nvml.nvmlDeviceGetPciInfo, handle)
        value = info.busId
        return value.decode() if isinstance(value, bytes) else str(value)

    def memory_info(self, handle: Any) -> tuple[int, int, int | None]:
        """``(total_bytes, used_bytes, reserved_bytes)``. NVML reports bytes already.

        **Version 2 is required for a correct ``used`` figure.** The v1 struct's ``used`` is
        ``total - free``, which folds in driver-reserved memory the user's processes are not
        consuming. On an idle RTX 5060 Ti that is 471 MiB of a 1021 MiB "used" reading — the
        tool would report nearly double what ``nvidia-smi`` shows for the same instant, and the
        user would rightly call it wrong. ``nvidia-smi`` reports the v2 figure.

        v2 is unavailable on older drivers. In that case ``used`` is the v1 value and
        ``reserved`` is ``None``, so callers can say the figure is approximate rather than
        quietly presenting an inflated number as exact.
        """
        v2_version = getattr(self._nvml, "nvmlMemory_v2", None)
        if v2_version is not None:
            try:
                info = self._nvml.nvmlDeviceGetMemoryInfo(handle, version=v2_version)
            except Exception:  # noqa: BLE001 - fall back to v1 below
                pass
            else:
                reserved = int(getattr(info, "reserved", 0))
                return int(info.total), int(info.used), reserved

        info = self._call(self._nvml.nvmlDeviceGetMemoryInfo, handle)
        return int(info.total), int(info.used), None

    def utilization(self, handle: Any) -> tuple[int, int]:
        """``(gpu_percent, memory_percent)``."""
        rates = self._call(self._nvml.nvmlDeviceGetUtilizationRates, handle)
        return int(rates.gpu), int(rates.memory)

    def power_usage(self, handle: Any) -> float:
        """Instantaneous draw in **watts**. NVML reports milliwatts."""
        return self._call(self._nvml.nvmlDeviceGetPowerUsage, handle) / 1000.0

    def power_limit(self, handle: Any) -> float:
        """The currently enforced limit in **watts**.

        Read only. NVML also exposes ``nvmlDeviceSetPowerManagementLimit``; this wrapper
        deliberately provides no setter, and ``tests/unit/test_read_only.py`` fails the suite
        if any module references one (constitution Principle V).
        """
        return self._call(self._nvml.nvmlDeviceGetEnforcedPowerLimit, handle) / 1000.0

    def total_energy(self, handle: Any) -> float:
        """Cumulative energy since driver load, in **watt-hours**.

        NVML reports millijoules; 1 Wh = 3.6e6 mJ. The value accumulates since the driver
        loaded, which is rarely the question a user has — converting it to a session figure is
        ``core.power.EnergyAccumulator``'s job.
        """
        millijoules = self._call(self._nvml.nvmlDeviceGetTotalEnergyConsumption, handle)
        return millijoules / 3_600_000.0

    def throttle_reasons(self, handle: Any) -> int:
        """Raw vendor bitmask. Decoded to a `core` enum in ``errors.py`` and never allowed to
        leave this package (contract P-15)."""
        return int(self._call(self._nvml.nvmlDeviceGetCurrentClocksThrottleReasons, handle))

    def is_mig_enabled(self, handle: Any) -> bool:
        """Whether this device is partitioned (research D-09, FR-028).

        A device with no MIG support at all raises ``NOT_SUPPORTED``, which simply means "not
        partitioned" — the common case on consumer hardware.
        """
        try:
            current, _pending = self._call(self._nvml.nvmlDeviceGetMigMode, handle)
        except NvmlError as exc:
            if exc.code in (
                errors.NVML_ERROR_NOT_SUPPORTED,
                errors.NVML_ERROR_FUNCTION_NOT_FOUND,
                errors.NVML_ERROR_INVALID_ARGUMENT,
            ):
                return False
            raise
        return bool(current)

    def running_processes(self, handle: Any) -> list[NvmlProcessInfo]:
        """Compute and graphics processes on this device.

        ``usedGpuMemory`` is ``None`` where the driver model cannot report it. That ``None``
        is carried through faithfully and becomes an ``UNSUPPORTED`` metric upstream — never a
        zero (SC-007).
        """
        found: dict[int, NvmlProcessInfo] = {}
        for getter_name in (
            "nvmlDeviceGetComputeRunningProcesses",
            "nvmlDeviceGetGraphicsRunningProcesses",
        ):
            getter = getattr(self._nvml, getter_name, None)
            if getter is None:
                continue
            try:
                entries = self._call(getter, handle)
            except NvmlError as exc:
                if exc.code == errors.NVML_ERROR_NOT_SUPPORTED:
                    continue
                raise
            for entry in entries:
                used = getattr(entry, "usedGpuMemory", None)
                pid = int(entry.pid)
                info = NvmlProcessInfo(pid=pid, used_gpu_memory=None if used is None else int(used))
                existing = found.get(pid)
                if existing is None or (
                    existing.used_gpu_memory is None and info.used_gpu_memory is not None
                ):
                    found[pid] = info
        return list(found.values())

    # -- internals ------------------------------------------------------------

    def _call(self, func: Any, *args: Any) -> Any:
        try:
            return func(*args)
        except Exception as exc:  # noqa: BLE001 - normalised into NvmlError
            raise self._wrap(exc) from exc

    def _wrap(self, exc: Exception) -> NvmlError:
        """Turn a ``pynvml`` exception into an :class:`NvmlError` with its numeric code."""
        code = getattr(exc, "value", None)
        if not isinstance(code, int):
            code = errors.NVML_ERROR_UNKNOWN
        return NvmlError(code, str(exc))
