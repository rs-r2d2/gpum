"""Core data model.

Every type here is an immutable frozen dataclass: snapshots are produced on a sampler thread
and read on the GUI thread, and immutability is what makes that handoff safe without locks.

This module imports no Qt, no vendor library, and no OS-specific module. See
`specs/001-gpu-usage-monitor/data-model.md`.
"""

from __future__ import annotations

import datetime as dt
import enum
from dataclasses import dataclass, field, replace
from typing import NamedTuple, Self

__all__ = [
    "Availability",
    "BackendCapabilities",
    "BackendReport",
    "BackendState",
    "DeviceId",
    "DiscoveryReport",
    "PresentButUnmonitored",
    "GpuDevice",
    "GpuProcess",
    "LimitReason",
    "MetricValue",
    "PidKey",
    "ProcessIdentity",
    "ProcessSortColumn",
    "Snapshot",
    "Vendor",
]


class Vendor(enum.StrEnum):
    NVIDIA = "nvidia"
    AMD = "amd"
    INTEL = "intel"
    UNKNOWN = "unknown"


class Availability(enum.StrEnum):
    """Why a metric is, or is not, a real measurement.

    There is deliberately no ``UNKNOWN`` and no zero-default: FR-017 and SC-007 forbid
    presenting a non-measurement as a measurement, so every metric names its own state.
    """

    AVAILABLE = "available"
    UNSUPPORTED = "unsupported"
    PERMISSION_DENIED = "permission_denied"
    STALE = "stale"
    DEGRADED = "degraded"
    NOT_APPLICABLE = "not_applicable"


#: States that may legitimately carry a value. ``STALE`` is the sole non-available one: it
#: shows the last real measurement together with its original timestamp so the UI can display
#: the reading's true age (FR-016).
_VALUE_BEARING = frozenset({Availability.AVAILABLE, Availability.STALE})

#: States that must explain themselves to the user (FR-017).
_REASON_REQUIRED = frozenset(
    {
        Availability.UNSUPPORTED,
        Availability.PERMISSION_DENIED,
        Availability.STALE,
        Availability.DEGRADED,
    }
)


@dataclass(frozen=True, slots=True)
class MetricValue:
    """A measured quantity plus its provenance.

    The invariant enforced below is the mechanical guarantee behind SC-007: a backend cannot
    construct a metric that claims to be a measurement without actually having one.
    """

    value: int | float | None
    availability: Availability
    reason: str | None = None
    sampled_at: dt.datetime | None = None

    def __post_init__(self) -> None:
        if self.availability is Availability.AVAILABLE and self.value is None:
            raise ValueError("an AVAILABLE metric must carry a value")
        if self.availability not in _VALUE_BEARING and self.value is not None:
            raise ValueError(
                f"a {self.availability} metric must not carry a value "
                f"(got {self.value!r}); see SC-007"
            )
        if self.availability in _REASON_REQUIRED and not self.reason:
            raise ValueError(f"a {self.availability} metric requires a reason")

    @property
    def is_measurement(self) -> bool:
        """True only for a value measured in this sample."""
        return self.availability is Availability.AVAILABLE

    @classmethod
    def available(cls, value: int | float, *, sampled_at: dt.datetime) -> Self:
        return cls(value=value, availability=Availability.AVAILABLE, sampled_at=sampled_at)

    @classmethod
    def unsupported(cls, reason: str) -> Self:
        return cls(value=None, availability=Availability.UNSUPPORTED, reason=reason)

    @classmethod
    def permission_denied(cls, reason: str = "requires elevated privileges") -> Self:
        return cls(value=None, availability=Availability.PERMISSION_DENIED, reason=reason)

    @classmethod
    def not_applicable(cls) -> Self:
        return cls(value=None, availability=Availability.NOT_APPLICABLE)

    @classmethod
    def stale(
        cls, value: int | float | None, *, sampled_at: dt.datetime | None, reason: str
    ) -> Self:
        return cls(
            value=value,
            availability=Availability.STALE,
            reason=reason,
            sampled_at=sampled_at,
        )

    @classmethod
    def degraded(cls, reason: str = "device not responding") -> Self:
        return cls(value=None, availability=Availability.DEGRADED, reason=reason)

    def as_stale(self, reason: str) -> MetricValue:
        """Carry this reading forward as stale, preserving its original timestamp."""
        if self.availability is Availability.AVAILABLE:
            return MetricValue.stale(self.value, sampled_at=self.sampled_at, reason=reason)
        if self.availability is Availability.STALE:
            return self
        return MetricValue.stale(None, sampled_at=None, reason=reason)


_UNSET = MetricValue.not_applicable()


@dataclass(frozen=True, slots=True)
class DeviceId:
    """Stable device identity.

    ``index`` is display ordering only and deliberately excluded from equality and hashing: an
    enumeration index is not identity, and treating it as such would splice two devices'
    histories together after a driver restart (research D-07).
    """

    vendor: Vendor
    key: str
    index: int = field(default=0, compare=False, hash=False)

    def __str__(self) -> str:
        return f"{self.vendor}:{self.key}"


@dataclass(frozen=True, slots=True)
class BackendCapabilities:
    """What a backend can report *on the current platform*, not in general."""

    device_memory: bool = False
    device_utilization: bool = False
    per_process_memory: bool = False
    per_process_utilization: bool = False
    supports_hotplug: bool = False


class LimitReason(enum.StrEnum):
    """Why a device's performance is currently constrained.

    ``NONE`` and ``UNKNOWN`` are deliberately separate. The hardware genuinely reports
    "nothing is limiting this device", which is a measurement; failing to read that is the
    absence of one. Collapsing the two would present an absence of information as information
    — the same error as rendering an unavailable metric as zero (FR-019).
    """

    NONE = "none"
    POWER = "power"
    THERMAL = "thermal"
    OTHER = "other"
    UNKNOWN = "unknown"

    @property
    def is_measurement(self) -> bool:
        """Whether this state was actually determined."""
        return self is not LimitReason.UNKNOWN

    @property
    def is_constrained(self) -> bool:
        """Whether the device is known to be held back. ``UNKNOWN`` is not a yes."""
        return self in (LimitReason.POWER, LimitReason.THERMAL, LimitReason.OTHER)

    @property
    def display_text(self) -> str:
        return {
            LimitReason.NONE: "",
            LimitReason.POWER: "Power limited",
            LimitReason.THERMAL: "Thermally limited",
            LimitReason.OTHER: "Limited",
            LimitReason.UNKNOWN: "Limit state unknown",
        }[self]


@dataclass(frozen=True, slots=True)
class GpuDevice:
    """One whole physical GPU. Partitions are never separate devices (FR-027)."""

    id: DeviceId
    name: str
    vendor_name: str = ""
    supported: bool = True
    unsupported_reason: str | None = None
    memory_total: MetricValue = _UNSET
    memory_used: MetricValue = _UNSET
    utilization_gpu: MetricValue = _UNSET
    utilization_memory: MetricValue = _UNSET
    attribution: Availability = Availability.NOT_APPLICABLE
    attribution_reason: str | None = None
    last_sampled_at: dt.datetime | None = None

    # -- 004: power ---------------------------------------------------------
    #: Raw instantaneous draw, watts. Kept alongside the average so the distinction between
    #: "what it is drawing now" and "what it has averaged" is never lost.
    power_draw: MetricValue = _UNSET
    #: Rolling mean over the smoothing window, watts. This is what the UI shows, because the
    #: raw reading swings too sharply to read (research D-02).
    power_draw_avg: MetricValue = _UNSET
    power_limit: MetricValue = _UNSET
    #: Watt-hours since monitoring began — not since driver load, which is rarely the question.
    energy_session: MetricValue = _UNSET
    #: Whether readings were lost during accumulation, so the total is not mistaken for a
    #: complete measurement (FR-015).
    energy_interrupted: bool = False
    limit_reason: LimitReason = LimitReason.UNKNOWN

    def __post_init__(self) -> None:
        if not self.supported and not self.unsupported_reason:
            raise ValueError("an unsupported device requires an unsupported_reason")
        if not self.supported:
            for name in (
                "memory_total",
                "memory_used",
                "utilization_gpu",
                "utilization_memory",
            ):
                metric: MetricValue = getattr(self, name)
                if metric.is_measurement:
                    raise ValueError(
                        "an unsupported device must not report metrics (FR-028); "
                        f"{name} was a measurement"
                    )

    @property
    def memory_percent(self) -> float | None:
        """Computed only when both operands are real measurements."""
        total = self.memory_total
        used = self.memory_used
        if not (total.is_measurement and used.is_measurement):
            return None
        if not total.value:
            return None
        return 100.0 * float(used.value) / float(total.value)  # type: ignore[arg-type]

    @property
    def power_percent(self) -> float | None:
        """Draw against limit, computed only when both are real measurements."""
        draw = self.power_draw_avg if self.power_draw_avg.is_measurement else self.power_draw
        limit = self.power_limit
        if not (draw.is_measurement and limit.is_measurement):
            return None
        if not limit.value:
            return None
        return 100.0 * float(draw.value) / float(limit.value)  # type: ignore[arg-type]

    @property
    def display_name(self) -> str:
        return self.name

    def with_metrics(self, **metrics: object) -> GpuDevice:
        return replace(self, **metrics)


class ProcessIdentity(enum.StrEnum):
    RESOLVED = "resolved"
    RESTRICTED = "restricted"
    CONTAINERIZED = "containerized"
    UNRESOLVED = "unresolved"


class PidKey(NamedTuple):
    """Process identity for cross-sample matching.

    Includes the start time because PIDs are recycled; keying on the bare PID would let a new
    process inherit an exited one's attribution (research D-05).
    """

    pid: int
    started_at: dt.datetime | None


@dataclass(frozen=True, slots=True)
class GpuProcess:
    """One process consuming one device. A process on two GPUs yields two records."""

    pid: int
    device_key: str
    started_at: dt.datetime | None = None
    name: str | None = None
    executable: str | None = None
    username: str | None = None
    memory_used: MetricValue = _UNSET
    utilization: MetricValue = _UNSET
    identity_state: ProcessIdentity = ProcessIdentity.UNRESOLVED
    container_id: str | None = None

    @property
    def identity_key(self) -> PidKey:
        return PidKey(self.pid, self.started_at)

    @property
    def display_name(self) -> str:
        if self.name:
            return self.name
        if self.identity_state is ProcessIdentity.RESTRICTED:
            return f"<restricted> (pid {self.pid})"
        return f"<unresolved> (pid {self.pid})"


class BackendState(enum.StrEnum):
    """Why a backend is or is not producing devices.

    These must stay distinguishable: SC-006 requires a clear, actionable message, and
    collapsing "binding not installed" into "driver not loaded" makes that impossible.
    """

    ACTIVE = "active"
    NO_DEVICES = "no_devices"
    DRIVER_MISSING = "driver_missing"
    LIBRARY_MISSING = "library_missing"
    NOT_IMPLEMENTED = "not_implemented"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class BackendReport:
    vendor: Vendor
    state: BackendState
    detail: str
    device_count: int = 0

    def __post_init__(self) -> None:
        if not self.detail:
            raise ValueError("a BackendReport requires a user-facing detail message")


@dataclass(frozen=True, slots=True)
class PresentButUnmonitored:
    """A GPU the machine physically has that no backend can monitor.

    Exists so the tool never reports fewer GPUs than the machine contains (FR-015, SC-007).
    Saying "AMD is unsupported" in the abstract is not the same as telling a user that the AMD
    card in their machine is present and unreadable.
    """

    vendor: Vendor
    location: str
    reason: str


@dataclass(frozen=True, slots=True)
class DiscoveryReport:
    """What was searched for and what was found — powers FR-018 and SC-006."""

    backends_attempted: tuple[BackendReport, ...] = ()
    attribution_source: str | None = None
    present_but_unmonitored: tuple[PresentButUnmonitored, ...] = ()

    @property
    def any_devices(self) -> bool:
        return any(r.device_count for r in self.backends_attempted)

    @property
    def total_gpus_accounted(self) -> int:
        """Every GPU the tool can account for, monitored or not (SC-007)."""
        return sum(r.device_count for r in self.backends_attempted) + len(
            self.present_but_unmonitored
        )


@dataclass(frozen=True, slots=True)
class Snapshot:
    """The single immutable object crossing the sampler → UI thread boundary."""

    taken_at: dt.datetime
    sequence: int
    devices: tuple[GpuDevice, ...] = ()
    processes: tuple[GpuProcess, ...] = ()
    discovery: DiscoveryReport = field(default_factory=DiscoveryReport)
    #: Set on the first snapshot after the machine resumed from suspend (FR-013). Typed as
    #: object so `core.models` stays free of a dependency on the engine module.
    resume: object | None = None

    def processes_for(self, device_key: str) -> tuple[GpuProcess, ...]:
        return tuple(p for p in self.processes if p.device_key == device_key)


class ProcessSortColumn(enum.StrEnum):
    """The four displayed columns.

    ``USER`` was displayed but missing from this enum, which is why the column could not be
    sorted — the gap feature 003 exists to close (FR-006).
    """

    NAME = "name"
    PID = "pid"
    USER = "user"
    MEMORY_USED = "memory_used"
