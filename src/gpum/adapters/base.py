"""Process attribution and identity protocols (contracts/process-attribution.md).

Two interfaces answering two different questions:

* ``ProcessAttributionProvider`` — which PIDs are using which GPU, and how much memory?
* ``ProcessIdentityProvider``    — given a PID, what is it?

They are separate because their sources differ per platform and they fail independently.
Knowing a GPU is consuming 4 GiB under PID 8321 is useful even when the process cannot be
named — and FR-031 requires that partial knowledge to reach the user rather than be discarded.

The data types live in ``gpum.core.attribution`` so vendor backends can implement a companion
provider without importing ``adapters``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable

from gpum.core.attribution import AttributionResult, AttributionSupport, ProcessIdentityInfo
from gpum.core.models import GpuDevice, PidKey

__all__ = [
    "AttributionResult",
    "AttributionSupport",
    "ProcessAttributionProvider",
    "ProcessIdentityInfo",
    "ProcessIdentityProvider",
]


@runtime_checkable
class ProcessAttributionProvider(Protocol):
    """Which processes are using which GPU."""

    source_name: str

    def probe(self) -> AttributionSupport:
        """Never raises. Reflects the running platform *and* the current privilege level."""
        ...

    def attribute(self, devices: Sequence[GpuDevice]) -> AttributionResult:
        """Attribute GPU usage to processes.

        Must return a ``per_device`` entry for every device passed in, must emit
        ``UNRESOLVED`` processes rather than dropping unidentifiable PIDs (FR-031), and must
        never infer or apportion memory the source did not report (SC-007).
        """
        ...


@runtime_checkable
class ProcessIdentityProvider(Protocol):
    """Given PIDs, what are they?"""

    def identify(self, pids: Sequence[PidKey]) -> Mapping[PidKey, ProcessIdentityInfo]:
        """Batch lookup — one call, not one per PID.

        At 1 Hz across hundreds of processes, a per-PID call would be a measurable load on the
        machine being measured. Must return an entry for every requested key.
        """
        ...
