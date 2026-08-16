"""Shared attribution vocabulary.

These types live in `core` rather than `adapters` because both sides of the attribution
boundary need them: platform adapters *and* vendor backends can supply attribution (a backend
may ship a companion provider — see research D-03), and a backend importing `adapters` would
cross a layer it must not. The protocols themselves stay in `adapters.base`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from gpum.core.models import Availability, GpuProcess, ProcessIdentity

__all__ = ["AttributionResult", "AttributionSupport", "ProcessIdentityInfo"]


@dataclass(frozen=True, slots=True)
class AttributionSupport:
    available: bool
    supports_memory: bool = False
    supports_utilization: bool = False
    reason: str | None = None
    requires_elevation: bool = False

    def __post_init__(self) -> None:
        if not self.available and not self.reason:
            raise ValueError("unavailable attribution must explain itself (FR-017)")


@dataclass(frozen=True, slots=True)
class AttributionResult:
    processes: tuple[GpuProcess, ...] = ()
    #: Must contain an entry for EVERY device passed in — a missing key is indistinguishable
    #: from "no processes", which is exactly the ambiguity US2 scenario 4 forbids.
    per_device: Mapping[str, Availability] = field(default_factory=dict)
    #: Bytes accounted for per device, including restricted and unresolved processes (SC-012).
    total_attributed: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProcessIdentityInfo:
    name: str | None = None
    executable: str | None = None
    username: str | None = None
    container_id: str | None = None
    identity_state: ProcessIdentity = ProcessIdentity.UNRESOLVED
