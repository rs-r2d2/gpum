"""NVML per-process attribution (contracts/process-attribution.md).

A *companion* provider to the NVIDIA backend rather than part of the backend interface, because
attribution's source varies by driver and platform, not only by vendor — an OS-supplied,
vendor-neutral source is the right answer wherever NVML has none (research D-03).

NVML supplies per-process memory on the supported target (Linux, proprietary driver), but not
unconditionally: some driver models return the PIDs with no usable memory figure. That case is
handled honestly here — the processes are still listed, and their memory is reported
``UNSUPPORTED`` with a reason rather than ``0``. Showing zero would say "this process is using
no GPU memory", which is false.
"""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Sequence

from gpum.backends.nvidia.nvml import NvmlError, NvmlLibrary
from gpum.core.attribution import AttributionResult, AttributionSupport
from gpum.core.models import (
    Availability,
    GpuDevice,
    GpuProcess,
    MetricValue,
    ProcessIdentity,
)

__all__ = ["NvmlAttributionProvider"]

_log = logging.getLogger(__name__)

_NO_PER_PROCESS_MEMORY_REASON = (
    "per-process GPU memory is not reported by this driver; "
    "the process is listed but its memory is unknown"
)


class NvmlAttributionProvider:
    source_name = "nvidia/nvml"

    def __init__(self, backend: object) -> None:
        self._backend = backend
        self._nvml: NvmlLibrary = getattr(backend, "_nvml", None) or NvmlLibrary()

    def probe(self) -> AttributionSupport:
        """Never raises (contract A-01)."""
        try:
            if not self._nvml.initialised:
                self._nvml.init()
        except NvmlError as exc:
            return AttributionSupport(
                available=False,
                reason=f"NVIDIA per-process data is unavailable: {exc}",
            )
        except Exception as exc:  # noqa: BLE001
            return AttributionSupport(
                available=False, reason=f"NVIDIA per-process data is unavailable: {exc}"
            )
        return AttributionSupport(
            available=True,
            supports_memory=True,
            supports_utilization=False,
            requires_elevation=False,
        )

    def attribute(self, devices: Sequence[GpuDevice]) -> AttributionResult:
        processes: list[GpuProcess] = []
        per_device: dict[str, Availability] = {}
        totals: dict[str, int] = {}
        handles: dict[str, object] = getattr(self._backend, "_handles", {})
        now = dt.datetime.now(dt.UTC)

        for device in devices:
            key = device.id.key
            # Contract A-02: an entry for EVERY device, including ones we cannot attribute.
            if not device.supported:
                per_device[key] = Availability.NOT_APPLICABLE
                continue
            handle = handles.get(key)
            if handle is None:
                per_device[key] = Availability.UNSUPPORTED
                continue

            try:
                entries = self._nvml.running_processes(handle)
            except NvmlError as exc:
                _log.debug("process query failed for %s: %s", key, exc)
                per_device[key] = Availability.UNSUPPORTED
                continue

            per_device[key] = Availability.AVAILABLE
            total = 0
            for entry in entries:
                if entry.used_gpu_memory is None:
                    memory = MetricValue.unsupported(_NO_PER_PROCESS_MEMORY_REASON)
                else:
                    memory = MetricValue.available(entry.used_gpu_memory, sampled_at=now)
                    total += entry.used_gpu_memory
                processes.append(
                    GpuProcess(
                        pid=entry.pid,
                        device_key=key,
                        memory_used=memory,
                        utilization=MetricValue.unsupported(
                            "per-process utilization is not reported by NVML"
                        ),
                        # Identity is filled in later by the platform identity provider; an
                        # unresolvable PID stays in the list with its memory counted (FR-031).
                        identity_state=ProcessIdentity.UNRESOLVED,
                    )
                )
            totals[key] = total

        return AttributionResult(
            processes=tuple(processes),
            per_device=per_device,
            total_attributed=totals,
        )
