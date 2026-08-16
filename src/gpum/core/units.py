"""Unit normalization (FR-004).

All memory is stored as bytes everywhere in the application. This module is the single place
that turns bytes into display text, so a rounding or convention difference cannot creep in per
vendor. It also refuses to format a metric that is not a measurement — the formatting-layer
half of SC-007.
"""

from __future__ import annotations

from gpum.core.models import Availability, MetricValue

__all__ = [
    "UNIT_CONVENTION",
    "format_bytes",
    "format_metric_bytes",
    "format_percent",
    "format_watt_hours",
    "format_watts",
    "percent",
]

#: Stated in the UI so the user knows what the numbers mean (FR-004).
UNIT_CONVENTION = "binary (MiB/GiB, 1024-based)"

_UNITS = (("TiB", 1024**4), ("GiB", 1024**3))
_MIB = 1024**2

#: Shown wherever a value does not exist. Deliberately not "0", "-", or "" — a reader must not
#: be able to mistake an absence for a measurement of nothing (SC-007).
UNAVAILABLE_TEXT = "n/a"


def format_bytes(value: int | float) -> str:
    """Format a byte count using one convention, application-wide."""
    if value < 0:
        raise ValueError(f"byte counts cannot be negative: {value!r}")
    for suffix, scale in _UNITS:
        if value >= scale:
            return f"{value / scale:.2f} {suffix}"
    # Sub-gigabyte values render as whole MiB — a fractional MiB is noise at this scale.
    return f"{round(value / _MIB)} MiB"


def format_metric_bytes(metric: MetricValue) -> str:
    """Format a metric, or say why there is nothing to format.

    A ``STALE`` metric keeps its last real value — the UI marks the staleness separately, with
    the age taken from ``sampled_at`` (FR-016).
    """
    if metric.availability is Availability.AVAILABLE and metric.value is not None:
        return format_bytes(metric.value)
    if metric.availability is Availability.STALE and metric.value is not None:
        return format_bytes(metric.value)
    return UNAVAILABLE_TEXT


def format_percent(value: float | None) -> str:
    return UNAVAILABLE_TEXT if value is None else f"{value:.0f}%"


def percent(part: MetricValue, whole: MetricValue) -> float | None:
    """Percentage, only when both operands are real measurements."""
    if not (part.is_measurement and whole.is_measurement):
        return None
    if not whole.value:
        return None
    return 100.0 * float(part.value) / float(whole.value)  # type: ignore[arg-type]


def format_watts(value: int | float) -> str:
    """Power in watts, one decimal.

    The hardware reports milliwatts, but a tenth of a watt is already well below the
    reading-to-reading noise floor, so more precision would imply accuracy that is not there.
    """
    if value < 0:
        raise ValueError(f"power cannot be negative: {value!r}")
    return f"{value:.1f} W"


def format_watt_hours(value: int | float) -> str:
    """Energy in watt-hours, three decimals so a short session does not round to zero."""
    if value < 0:
        raise ValueError(f"energy cannot be negative: {value!r}")
    if value >= 1000:
        return f"{value / 1000:.3f} kWh"
    return f"{value:.3f} Wh"


def format_metric_watts(metric: MetricValue) -> str:
    """Format a power metric, or say why there is nothing to format.

    Never returns "0 W" for a missing value: zero watts asserts the card is drawing nothing,
    which is a different and much stronger claim than "we could not read it".
    """
    if metric.availability in (
        Availability.AVAILABLE,
        Availability.STALE,
    ) and metric.value is not None:
        return format_watts(metric.value)
    return UNAVAILABLE_TEXT


def format_metric_watt_hours(metric: MetricValue) -> str:
    if metric.availability in (
        Availability.AVAILABLE,
        Availability.STALE,
    ) and metric.value is not None:
        return format_watt_hours(metric.value)
    return UNAVAILABLE_TEXT
