"""AMD backend — a registered stub for this release.

Deliberately shipped before any AMD code exists. A registry holding exactly one real
implementation invites an interface shaped around it; keeping the plural case real is what
guards constitution Principle I against the NVIDIA-first delivery (plan.md § Complexity
Tracking). It also makes the "vendor not supported" UI path testable today.

Replacing this stub with a real backend must require no change outside this directory and
core/registry.py. If it does, the abstraction has failed.
"""

from __future__ import annotations

from collections.abc import Sequence

from gpum.backends.base import DeviceGoneError
from gpum.core.models import (
    BackendCapabilities,
    BackendReport,
    BackendState,
    DeviceId,
    GpuDevice,
    Vendor,
)

__all__ = ["AMDBackend"]


class AMDBackend:
    vendor = Vendor.AMD
    name = "amd"

    def probe(self) -> BackendReport:
        return BackendReport(
            vendor=self.vendor,
            state=BackendState.NOT_IMPLEMENTED,
            detail="AMD GPUs are not supported in this release",
        )

    def enumerate_devices(self) -> Sequence[GpuDevice]:
        return []

    def sample_device(self, device_id: DeviceId) -> GpuDevice:
        raise DeviceGoneError("the amd backend reports no devices")

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities()

    def shutdown(self) -> None:
        return None
