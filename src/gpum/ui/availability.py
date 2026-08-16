"""The single place :class:`Availability` becomes something a user reads.

Centralising this is what makes SC-007 enforceable: there is exactly one function that turns a
metric into display text, so an unavailable value cannot leak to screen as ``0`` because
someone reached for a convenient default somewhere in a widget.
"""

from __future__ import annotations

import datetime as dt

from gpum.core.models import Availability, MetricValue
from gpum.core.units import format_bytes, format_percent, format_watt_hours, format_watts

__all__ = [
    "age_text",
    "energy_text",
    "memory_text",
    "percent_text",
    "power_text",
    "state_text",
    "tooltip_for",
]

_STATE_LABEL: dict[Availability, str] = {
    Availability.UNSUPPORTED: "Not supported",
    Availability.PERMISSION_DENIED: "Needs privileges",
    Availability.DEGRADED: "Not responding",
    Availability.NOT_APPLICABLE: "—",
    Availability.STALE: "Stale",
}


def state_text(metric: MetricValue) -> str:
    """Short label for a metric that is not a current measurement."""
    return _STATE_LABEL.get(metric.availability, "Unavailable")


def memory_text(metric: MetricValue) -> str:
    """Bytes as text, or an explicit statement that there is nothing to show.

    Deliberately never returns ``"0"`` or an empty string for a missing value: a reader must
    not be able to mistake an absence for a measurement of nothing.
    """
    if metric.availability is Availability.AVAILABLE and metric.value is not None:
        return format_bytes(metric.value)
    if metric.availability is Availability.STALE and metric.value is not None:
        return format_bytes(metric.value)
    return state_text(metric)


def percent_text(metric: MetricValue) -> str:
    if metric.availability in (Availability.AVAILABLE, Availability.STALE) and (
        metric.value is not None
    ):
        return format_percent(float(metric.value))
    return state_text(metric)


def age_text(metric: MetricValue, *, now: dt.datetime | None = None) -> str:
    """How old a stale reading is, so it is distinguishable from a current one (FR-016)."""
    if metric.sampled_at is None:
        return ""
    now = now or dt.datetime.now(dt.UTC)
    seconds = max(0, int((now - metric.sampled_at).total_seconds()))
    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    return f"{seconds // 3600}h ago"


def tooltip_for(metric: MetricValue, *, now: dt.datetime | None = None) -> str:
    """The reason a value is missing, or how fresh it is when present."""
    if metric.availability is Availability.AVAILABLE:
        return f"Measured {age_text(metric, now=now)}" if metric.sampled_at else "Measured"
    parts = [metric.reason or state_text(metric)]
    if metric.availability is Availability.STALE and metric.sampled_at:
        parts.append(f"Last measured {age_text(metric, now=now)}")
    return "\n".join(parts)


def is_dimmed(metric: MetricValue) -> bool:
    """Whether the UI should render this value muted rather than as live data."""
    return metric.availability is not Availability.AVAILABLE


def power_text(metric: MetricValue) -> str:
    """Watts as text, or an explicit statement that there is nothing to show.

    Never "0 W" for a missing value: zero watts asserts the card is drawing nothing, which is a
    far stronger claim than "we could not read it" (FR-005).
    """
    if metric.availability in (
        Availability.AVAILABLE,
        Availability.STALE,
    ) and metric.value is not None:
        return format_watts(metric.value)
    return state_text(metric)


def energy_text(metric: MetricValue) -> str:
    if metric.availability in (
        Availability.AVAILABLE,
        Availability.STALE,
    ) and metric.value is not None:
        return format_watt_hours(metric.value)
    return state_text(metric)
