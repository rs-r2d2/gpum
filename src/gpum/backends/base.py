"""The vendor backend boundary (contracts/backend-interface.md).

This is the interface constitution Principle I exists to protect: adding a vendor must require
no change outside its own backend module and its registration.

Implementations MUST NOT import ``gpum.core``, ``gpum.ui``, or ``gpum.adapters`` — enforced by
``tests/unit/test_import_boundaries.py``.

Note what is absent: there is no ``get_processes()``. Per-process attribution is a separate
contract (``gpum.adapters.base``) because its source is not always the vendor — where a driver
cannot supply it, an OS-level, vendor-neutral source can, for every vendor at once. Folding it
in here would have forced platform-specific code inside a vendor module (research D-03).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from gpum.core.models import BackendCapabilities, BackendReport, DeviceId, GpuDevice, Vendor

__all__ = ["BackendError", "DeviceGoneError", "GpuBackend"]


class BackendError(Exception):
    """Base for backend failures that the sampler should surface rather than swallow."""


class DeviceGoneError(BackendError):
    """The device disappeared between enumeration and sampling.

    Raised so the sampler can re-enumerate immediately rather than reporting an error to the
    user: a removed eGPU or a restarted driver is a normal event (FR-020).
    """


@runtime_checkable
class GpuBackend(Protocol):
    """One vendor's view of the machine's GPUs."""

    vendor: Vendor
    name: str

    def probe(self) -> BackendReport:
        """Determine whether this backend can operate. MUST NOT raise, ever.

        An absent driver is an expected condition (FR-018), not an exception. Must distinguish
        ``LIBRARY_MISSING`` from ``DRIVER_MISSING`` from ``NO_DEVICES`` — SC-006 needs a
        specific message. Must complete within 2s so startup meets SC-001.
        """
        ...

    def enumerate_devices(self) -> Sequence[GpuDevice]:
        """All whole physical GPUs this backend manages; ``[]`` when none, never ``None``.

        Each device's ``DeviceId.key`` must be stable across calls, driver restarts, and
        process restarts. Partitioned devices are returned with ``supported=False`` and a
        reason (FR-027, FR-028).
        """
        ...

    def sample_device(self, device_id: DeviceId) -> GpuDevice:
        """One point-in-time reading.

        Every metric carries an accurate ``Availability`` and, when unavailable, a reason.
        Memory is in bytes — normalization belongs to ``core.units``. Must never substitute
        0, -1, or an estimate for an unobtainable value (SC-007). Must be safe to call
        concurrently for different devices. Raises ``DeviceGoneError`` if the device vanished.
        """
        ...

    def capabilities(self) -> BackendCapabilities:
        """What this backend can report on the *current platform*, not in general."""
        ...

    def shutdown(self) -> None:
        """Release vendor resources. Idempotent, and safe before any successful init."""
        ...
