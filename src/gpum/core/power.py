"""Power smoothing and energy accumulation (research D-02, D-03).

Pure logic: no Qt, no vendor types, no clock of its own. Both classes hold state across
sampling cycles, which is why they live here rather than in a backend (which must not cache —
caching would make ``sampled_at`` a lie) or the UI (which must not compute — that would breach
the 16 ms GUI-thread budget).
"""

from __future__ import annotations

from collections import deque

from gpum.core.models import Availability, MetricValue

__all__ = ["EnergyAccumulator", "PowerSmoother"]

#: Target averaging span, **set from measurement rather than intuition**.
#:
#: 30 consecutive 1 Hz reads of an idle RTX 5060 Ti spanned 9.3-21.7 W, with a worst
#: consecutive change of 53.7%. Smoothed over varying windows, the worst consecutive change
#: was: 3 s -> 21.4%, 5 s -> 17.1%, 8 s -> 9.4%, 10 s -> 7.8%.
#:
#: SC-003 budgets 10% between consecutive refreshes, so 8 s is the shortest window that meets
#: it. A 5 s window — the initial guess — fails by a wide margin on real data.
#:
#: The cost is responsiveness: an 8-sample mean travels 25% of a step change within two
#: samples rather than 40%. On a realistic step (20 W -> 150 W) that is still a 32 W move
#: inside two seconds, which comfortably satisfies SC-002's "visible within 2 seconds".
DEFAULT_WINDOW_S = 8.0

#: A counter that drops by more than this is a reset, not a measurement error.
_RESET_TOLERANCE_WH = 0.001


class PowerSmoother:
    """Rolling mean over a bounded window.

    Exists because the raw reading is unusable: two reads of an *idle* RTX 5060 Ti seconds
    apart returned 8.8 W and 15.8 W — a 79% swing with no workload change (research D-02). A
    raw number refreshed every second is accurate and unreadable.

    The two rules that keep it honest:

    * the window stays short enough that smoothing cannot defeat the responsiveness promise
      (FR-026), and
    * it **never averages across a gap** (FR-027) — blending readings from either side of an
      interruption manufactures a value for a period nobody measured.
    """

    def __init__(self, *, window_s: float = DEFAULT_WINDOW_S, interval_ms: int = 1000) -> None:
        self._window_s = window_s
        self._interval_ms = interval_ms
        self._samples: deque[float] = deque(maxlen=self._capacity())

    def _capacity(self) -> int:
        return max(1, round(self._window_s * 1000 / max(self._interval_ms, 1)))

    @property
    def capacity(self) -> int:
        assert self._samples.maxlen is not None
        return self._samples.maxlen

    @property
    def count(self) -> int:
        return len(self._samples)

    def add(self, metric: MetricValue) -> None:
        """Record a reading. Any non-measurement clears the buffer."""
        if metric.availability is Availability.AVAILABLE and metric.value is not None:
            self._samples.append(float(metric.value))
            return
        # FR-027: the average must not span the gap.
        self._samples.clear()

    def average(self, *, sampled_at: object = None) -> MetricValue:
        """The mean of the buffered readings, or an explicit unavailable state.

        Returns unavailable rather than a stale figure while the buffer is empty — showing the
        last known value as though it were current is exactly the dishonesty SC-007 forbids.
        """
        if not self._samples:
            return MetricValue.unsupported("no recent power readings")
        mean = sum(self._samples) / len(self._samples)
        return MetricValue.available(round(mean, 3), sampled_at=sampled_at)  # type: ignore[arg-type]

    def resize(self, *, interval_ms: int, window_s: float | None = None) -> None:
        """Keep the window near its target span when the refresh rate changes (FR-026)."""
        self._interval_ms = interval_ms
        if window_s is not None:
            self._window_s = window_s
        self._samples = deque(self._samples, maxlen=self._capacity())

    def clear(self) -> None:
        self._samples.clear()


class EnergyAccumulator:
    """Session energy from a monotonic hardware counter.

    The counter accumulates since the driver loaded, which is rarely the question. This turns
    it into "energy since monitoring began", handling the three ways that arithmetic misleads:
    the counter can reset backwards, the machine can suspend, and readings can be interrupted.
    """

    def __init__(self) -> None:
        self._baseline_wh: float | None = None
        self._last_seen_wh: float | None = None
        self._carried_wh: float = 0.0
        self.interrupted: bool = False

    def update(self, metric: MetricValue) -> MetricValue:
        """Fold in one cumulative reading and return the session total."""
        if metric.availability is not Availability.AVAILABLE or metric.value is None:
            # A lost reading means the eventual total covers a period it did not measure.
            if self._baseline_wh is not None:
                self.interrupted = True
            return MetricValue.unsupported(metric.reason or "energy is not reported")

        current = float(metric.value)

        if self._baseline_wh is None:
            self._baseline_wh = current
            self._last_seen_wh = current
            return MetricValue.available(0.0, sampled_at=metric.sampled_at)

        if self._last_seen_wh is not None and current < self._last_seen_wh - _RESET_TOLERANCE_WH:
            # The counter reset (driver reload, GPU reset). Bank what was measured, then treat
            # the new baseline as zero rather than as `current`: a reset counter restarts from
            # zero, so a reading of 1.0 Wh means 1 Wh was already consumed after the reset.
            # Re-baselining to `current` would silently discard exactly that much.
            self._carried_wh += max(0.0, self._last_seen_wh - self._baseline_wh)
            self._baseline_wh = 0.0

        self._last_seen_wh = current
        session = self._carried_wh + max(0.0, current - self._baseline_wh)
        return MetricValue.available(round(session, 6), sampled_at=metric.sampled_at)

    def rebaseline(self) -> None:
        """Start a fresh accumulation period without discarding what was already measured.

        Used on resume: the counter does not advance while suspended, so the arithmetic is
        safe, but the session it describes would otherwise span hours of sleep (FR-014).
        """
        if self._last_seen_wh is not None and self._baseline_wh is not None:
            self._carried_wh += max(0.0, self._last_seen_wh - self._baseline_wh)
            self._baseline_wh = self._last_seen_wh

    def reset(self) -> None:
        """Return the session total to zero without restarting the application (FR-012)."""
        self._baseline_wh = self._last_seen_wh
        self._carried_wh = 0.0
        self.interrupted = False
