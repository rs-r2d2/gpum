"""Bounded per-device history (FR-005, FR-024, SC-005).

The memory bound is structural — a ``deque`` with ``maxlen`` — rather than maintained by a
cleanup routine someone could forget to call. Points retain their availability so an
unavailable stretch renders as a gap rather than a dip to zero (U-12).
"""

from __future__ import annotations

import datetime as dt
from collections import deque
from typing import NamedTuple

from gpum.core.models import Availability, MetricValue

__all__ = ["DeviceHistory", "HistoryPoint"]


class HistoryPoint(NamedTuple):
    timestamp: dt.datetime | None
    value: float | None
    availability: Availability


def _capacity(window_s: int, interval_ms: int) -> int:
    return max(1, int(window_s * 1000 / max(interval_ms, 1)))


class DeviceHistory:
    """Recent trend for one device, keyed on ``DeviceId.key`` so it survives hot-plug."""

    def __init__(self, device_key: str, *, window_s: int, interval_ms: int) -> None:
        self.device_key = device_key
        self._window_s = window_s
        self._interval_ms = interval_ms
        cap = _capacity(window_s, interval_ms)
        self.memory_used: deque[HistoryPoint] = deque(maxlen=cap)
        self.utilization: deque[HistoryPoint] = deque(maxlen=cap)
        self.power_draw: deque[HistoryPoint] = deque(maxlen=cap)
        #: Memory-*interface* activity — how busy the path to memory was. Not how full the
        #: memory is; that is a separate figure shown elsewhere.
        self.memory_utilization: deque[HistoryPoint] = deque(maxlen=cap)

    @property
    def capacity(self) -> int:
        assert self.memory_used.maxlen is not None
        return self.memory_used.maxlen

    def append_memory(self, metric: MetricValue) -> None:
        self.memory_used.append(_point(metric))

    def append_utilization(self, metric: MetricValue) -> None:
        self.utilization.append(_point(metric))

    def append_memory_utilization(self, metric: MetricValue) -> None:
        """Memory-interface activity, with unavailable stretches recorded as gaps."""
        self.memory_utilization.append(_point(metric))

    def append_power(self, metric: MetricValue) -> None:
        """Power trend, with unavailable stretches recorded as gaps (FR-010)."""
        self.power_draw.append(_point(metric))

    def append_gap(self, reason: str) -> None:
        """Record that time passed with no measurement — a suspend, most often.

        Explicitly a gap rather than a missing entry: the sparkline must show a break, because
        drawing a continuous line across a four-hour suspend would assert readings that were
        never taken (SC-008).
        """
        gap = MetricValue.unsupported(reason)
        self.memory_used.append(_point(gap))
        self.utilization.append(_point(gap))
        self.power_draw.append(_point(gap))
        self.memory_utilization.append(_point(gap))

    def resize(self, *, window_s: int, interval_ms: int) -> None:
        """Recompute capacity so the retention *window* stays constant when the interval
        changes (FR-024) — otherwise a faster interval would silently grow memory."""
        self._window_s = window_s
        self._interval_ms = interval_ms
        cap = _capacity(window_s, interval_ms)
        self.memory_used = deque(self.memory_used, maxlen=cap)
        self.utilization = deque(self.utilization, maxlen=cap)
        self.power_draw = deque(self.power_draw, maxlen=cap)
        self.memory_utilization = deque(self.memory_utilization, maxlen=cap)

    @property
    def has_any_measurement(self) -> bool:
        return any(p.availability is Availability.AVAILABLE for p in self.memory_used)


def _point(metric: MetricValue) -> HistoryPoint:
    if metric.availability is Availability.AVAILABLE and metric.value is not None:
        return HistoryPoint(metric.sampled_at, float(metric.value), metric.availability)
    # A gap, not a zero.
    return HistoryPoint(metric.sampled_at, None, metric.availability)
