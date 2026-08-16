"""The sampling engine (contracts/ui-update-contract.md).

Pure Python, no Qt: the ``QObject``/``QTimer`` wrapper lives in ``gpum.ui.sampler_worker``.
Splitting it this way keeps ``core`` importable without a ``QApplication`` (constitution tech
constraints) and — more usefully — makes the timeout and degradation state machines testable
with a fake clock and no event loop at all.

**Stated limitation**: a timeout here abandons the *wait*, not the *call*. A genuinely hung
driver call holds its pool thread until the driver returns; Python cannot cancel a blocking C
call. The design contains the damage rather than pretending cancellation happened: the pool is
bounded, and a device that repeatedly times out is backed off so it stops consuming a worker
every cycle.
"""

from __future__ import annotations

import concurrent.futures
import datetime as dt
import itertools
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from gpum.core.merge import merge
from gpum.core.models import (
    Availability,
    BackendReport,
    BackendState,
    DeviceId,
    DiscoveryReport,
    GpuDevice,
    MetricValue,
    PresentButUnmonitored,
    Snapshot,
    Vendor,
)
from gpum.core.power import EnergyAccumulator, PowerSmoother

__all__ = ["SamplingEngine"]

_log = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 0.1
"""Measured, not guessed (feature 002 FR-009).

Real NVIDIA hardware — RTX 5060 Ti, driver 580.159.03, 58 samples over 120 s — put a single
``sample_device()`` call at **0.031 ms mean, 0.119 ms p99**. The previous 500 ms placeholder was
roughly 4000x the observed p99, wide enough that a genuinely wedged driver would stall a device
for half a second before being noticed.

100 ms keeps ~840x headroom over the measured p99, which covers a driver that is momentarily
busy under heavy GPU load, while still detecting a wedge well inside a 1 s refresh interval.
Evidence: ``specs/002-linux-nvidia-release/verification.json``.

**Re-measured after feature 004 added power, energy, and throttle-reason reads**: 0.031 ms ->
**1.000 ms mean**, 0.119 ms -> **3.832 ms p99**. A 32x increase, because the power and energy
calls are substantially more expensive than the memory and utilization ones. 100 ms still
leaves ~26x headroom, so the budget holds — but the margin is no longer enormous, and another
metric of similar cost would be worth re-measuring rather than assuming.
"""

#: A gap larger than this means the machine slept rather than sampling being slow. Chosen to
#: sit well above a degraded device's 10-cycle backoff so ordinary slowness is never misread
#: as a suspend (data-model.md).
DEFAULT_RESUME_THRESHOLD_S = 30.0

DEFAULT_DEGRADE_AFTER = 3
DEFAULT_BACKOFF_CYCLES = 10
DEFAULT_REENUMERATE_EVERY = 10


@dataclass
class _DeviceState:
    """Per-device state carried across cycles: health, plus power smoothing and energy.

    Power state lives here rather than in the backend (which must not cache — that would make
    ``sampled_at`` a lie) or the UI (which must not compute — that would breach the GUI-thread
    budget). This object already has the right lifecycle: created on first sight of a device,
    destroyed when it disappears.
    """

    consecutive_timeouts: int = 0
    degraded: bool = False
    skip_cycles: int = 0
    last_good: GpuDevice | None = None
    smoother: PowerSmoother = field(default_factory=PowerSmoother)
    energy: EnergyAccumulator = field(default_factory=EnergyAccumulator)


@dataclass(frozen=True, slots=True)
class ResumeEvent:
    """The machine slept and came back (FR-013)."""

    detected_at: dt.datetime
    gap_seconds: float
    expected_interval_s: float


@dataclass
class _BackendState:
    backend: object
    report: BackendReport | None = None
    devices: list[GpuDevice] = field(default_factory=list)


class SamplingEngine:
    """Produces immutable :class:`Snapshot` objects on demand.

    The engine does not own a timer or a thread; the caller decides when to sample. That keeps
    scheduling policy in the UI layer where the user's interval preference lives, and keeps
    this class synchronous and testable.
    """

    def __init__(
        self,
        backends: Sequence[object],
        *,
        clock: Callable[[], dt.datetime] | None = None,
        per_device_timeout_s: float = DEFAULT_TIMEOUT_S,
        degrade_after: int = DEFAULT_DEGRADE_AFTER,
        backoff_cycles: int = DEFAULT_BACKOFF_CYCLES,
        reenumerate_every: int = DEFAULT_REENUMERATE_EVERY,
        resume_threshold_s: float = DEFAULT_RESUME_THRESHOLD_S,
        attribution_provider: object | None = None,
        identity_provider: object | None = None,
        present_gpu_probe: Callable[[], list[object]] | None = None,
        max_workers: int = 8,
    ) -> None:
        self._backends = [_BackendState(backend=b) for b in backends]
        self._clock = clock or (lambda: dt.datetime.now(dt.UTC))
        self._timeout = per_device_timeout_s
        self._degrade_after = degrade_after
        self._backoff_cycles = backoff_cycles
        self._reenumerate_every = max(1, reenumerate_every)
        self._attribution = attribution_provider
        self._identity = identity_provider
        self._present_probe = present_gpu_probe
        self._resume_threshold_s = resume_threshold_s
        self._last_cycle_at: dt.datetime | None = None
        self.last_resume: ResumeEvent | None = None
        self._sequence = itertools.count(1)
        self._cycle = 0
        self._states: dict[str, _DeviceState] = {}
        self._pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="gpum-sample"
        )
        self._probed = False

    # -- public API -----------------------------------------------------------

    def sample(self) -> Snapshot:
        """Run one full cycle and return an immutable snapshot."""
        now = self._clock()
        self.last_resume = self._detect_resume(now)
        if (
            self.last_resume is not None
            or not self._probed
            or self._cycle % self._reenumerate_every == 0
        ):
            # A GPU may have changed state across a suspend, so re-enumerate on resume.
            self._probe_and_enumerate()
        self._cycle += 1

        devices: list[GpuDevice] = []
        for state in self._backends:
            devices.extend(self._sample_backend(state))

        processes, per_device = self._attribute(devices)
        devices = [
            _with_attribution(d, per_device[d.id.key]) if d.id.key in per_device else d
            for d in devices
        ]

        return Snapshot(
            taken_at=now,
            sequence=next(self._sequence),
            devices=tuple(devices),
            processes=tuple(processes),
            discovery=self._discovery(),
            resume=self.last_resume,
        )

    def _detect_resume(self, now: dt.datetime) -> ResumeEvent | None:
        """Detect a wall-clock jump larger than sampling can explain (research D-10).

        Chosen over subscribing to logind's sleep signal: that adds a DBus dependency to a path
        that must also work where logind is absent, and cannot notice a resume logind failed to
        announce.
        """
        previous, self._last_cycle_at = self._last_cycle_at, now
        if previous is None:
            return None
        gap = (now - previous).total_seconds()
        if gap < self._resume_threshold_s:
            return None
        _log.info("resume detected after a %.0fs gap; clearing backoff", gap)
        self.reset_backoff()
        # Neither average nor accumulate across the sleep (FR-014, FR-027).
        for state in self._states.values():
            state.smoother.clear()
            state.energy.rebaseline()
        return ResumeEvent(
            detected_at=now, gap_seconds=gap, expected_interval_s=self._resume_threshold_s
        )

    def reset_backoff(self) -> None:
        """Clear degradation backoff so the next cycle retries every device.

        Used when the user explicitly asks for a refresh, and after a resume from sleep where
        a previously-degraded device is likely to be healthy again.
        """
        for state in self._states.values():
            state.skip_cycles = 0

    def shutdown(self) -> None:
        """Ordered shutdown that must not hang on a wedged driver.

        In-flight futures are abandoned rather than waited on: a monitor that cannot be closed
        because the thing it monitors is broken is precisely the failure this avoids.
        """
        self._pool.shutdown(wait=False, cancel_futures=True)
        for state in self._backends:
            try:
                state.backend.shutdown()  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001 - shutdown must never raise
                _log.debug("backend shutdown raised", exc_info=True)

    @property
    def device_keys(self) -> list[str]:
        return [d.id.key for state in self._backends for d in state.devices]

    # -- internals ------------------------------------------------------------

    def _probe_and_enumerate(self) -> None:
        self._probed = True
        for state in self._backends:
            try:
                state.report = state.backend.probe()  # type: ignore[attr-defined]
            except Exception as exc:  # noqa: BLE001 - a probe must never take the app down
                _log.warning("backend probe raised (contract C-01 violation): %s", exc)
                state.report = BackendReport(
                    vendor=getattr(state.backend, "vendor", Vendor.UNKNOWN),
                    state=BackendState.ERROR,
                    detail=f"probe failed: {exc}",
                )
                state.devices = []
                continue
            try:
                state.devices = list(state.backend.enumerate_devices())  # type: ignore[attr-defined]
            except Exception as exc:  # noqa: BLE001
                _log.warning("enumeration failed: %s", exc)
                state.devices = []

        live = {d.id.key for state in self._backends for d in state.devices}
        for key in list(self._states):
            if key not in live:
                del self._states[key]

    def _sample_backend(self, backend_state: _BackendState) -> list[GpuDevice]:
        backend = backend_state.backend
        pending: dict[concurrent.futures.Future[GpuDevice], GpuDevice] = {}
        results: dict[str, GpuDevice] = {}

        for device in backend_state.devices:
            state = self._states.setdefault(device.id.key, _DeviceState())
            if not device.supported:
                results[device.id.key] = device
                continue
            if state.skip_cycles > 0:
                state.skip_cycles -= 1
                results[device.id.key] = self._degraded_view(device, state)
                continue
            future = self._pool.submit(self._call_backend, backend, device.id)
            pending[future] = device

        deadline = self._timeout
        for future, device in pending.items():
            state = self._states[device.id.key]
            try:
                sampled = future.result(timeout=deadline)
            except concurrent.futures.TimeoutError:
                results[device.id.key] = self._on_timeout(device, state)
                continue
            except Exception as exc:  # noqa: BLE001 - includes DeviceGoneError
                _log.debug("sampling %s failed: %s", device.id.key, exc)
                self._probed = False  # trigger re-enumeration next cycle (FR-020)
                continue
            state.consecutive_timeouts = 0
            state.degraded = False
            state.skip_cycles = 0
            state.last_good = sampled
            results[device.id.key] = self._apply_power(sampled, state)

        return [results[d.id.key] for d in backend_state.devices if d.id.key in results]

    def _apply_power(self, device: GpuDevice, state: _DeviceState) -> GpuDevice:
        """Fold the raw power reading into the smoother and the energy accumulator.

        The device arrives from the backend carrying the instantaneous draw and the *raw*
        cumulative energy counter; it leaves carrying the averaged draw and the session total.
        """
        state.smoother.add(device.power_draw)
        averaged = state.smoother.average(sampled_at=device.power_draw.sampled_at)
        session = state.energy.update(device.energy_session)
        return device.with_metrics(
            power_draw_avg=averaged,
            energy_session=session,
            energy_interrupted=state.energy.interrupted,
        )

    def reset_energy(self, device_key: str | None = None) -> None:
        """Restart energy accounting without restarting the application (FR-012)."""
        for key, state in self._states.items():
            if device_key is None or key == device_key:
                state.energy.reset()

    def set_interval(self, interval_ms: int) -> None:
        """Keep the smoothing window near its target span when the cadence changes (FR-026)."""
        for state in self._states.values():
            state.smoother.resize(interval_ms=interval_ms)

    @staticmethod
    def _call_backend(backend: object, device_id: DeviceId) -> GpuDevice:
        return backend.sample_device(device_id)  # type: ignore[attr-defined]

    def _on_timeout(self, device: GpuDevice, state: _DeviceState) -> GpuDevice:
        state.consecutive_timeouts += 1
        if state.consecutive_timeouts >= self._degrade_after:
            state.degraded = True
            state.skip_cycles = self._backoff_cycles
            return self._degraded_view(device, state)
        reason = "query timed out"
        source = state.last_good or device
        return source.with_metrics(
            memory_total=source.memory_total.as_stale(reason),
            memory_used=source.memory_used.as_stale(reason),
            utilization_gpu=source.utilization_gpu.as_stale(reason),
            utilization_memory=source.utilization_memory.as_stale(reason),
        )

    @staticmethod
    def _degraded_view(device: GpuDevice, state: _DeviceState) -> GpuDevice:
        reason = "device not responding"
        source = state.last_good or device
        return source.with_metrics(
            memory_total=MetricValue.degraded(reason),
            memory_used=MetricValue.degraded(reason),
            utilization_gpu=MetricValue.degraded(reason),
            utilization_memory=MetricValue.degraded(reason),
        )

    def _attribute(
        self, devices: Sequence[GpuDevice]
    ) -> tuple[list[object], dict[str, Availability]]:
        if self._attribution is None:
            return [], {d.id.key: Availability.UNSUPPORTED for d in devices}
        try:
            result = self._attribution.attribute(devices)  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            _log.warning("attribution failed: %s", exc)
            return [], {d.id.key: Availability.UNSUPPORTED for d in devices}
        processes = merge(result, identity_provider=self._identity)
        per_device = dict(result.per_device)
        for device in devices:
            per_device.setdefault(device.id.key, Availability.UNSUPPORTED)
        return list(processes), per_device

    def _discovery(self) -> DiscoveryReport:
        reports = []
        for state in self._backends:
            if state.report is None:
                continue
            reports.append(
                BackendReport(
                    vendor=state.report.vendor,
                    state=state.report.state,
                    detail=state.report.detail,
                    device_count=len(state.devices),
                )
            )
        source = getattr(self._attribution, "source_name", None)
        return DiscoveryReport(
            backends_attempted=tuple(reports),
            attribution_source=source,
            present_but_unmonitored=self._unmonitored(),
        )

    def _unmonitored(self) -> tuple[PresentButUnmonitored, ...]:
        """GPUs the machine has that no backend produced a device for (FR-015, SC-007).

        Without this the tool tells a user with an NVIDIA + AMD machine that they have one
        GPU — a factual error about their hardware, and the same class of dishonesty as
        rendering an unavailable metric as zero.
        """
        if self._present_probe is None:
            return ()
        try:
            present = self._present_probe()
        except Exception:  # noqa: BLE001 - presence detection must never break sampling
            _log.debug("presence probe failed", exc_info=True)
            return ()

        monitored_vendors = {
            d.id.vendor for state in self._backends for d in state.devices
        }
        unmonitored = []
        for gpu in present:
            vendor = getattr(gpu, "vendor", Vendor.UNKNOWN)
            if vendor in monitored_vendors:
                continue
            unmonitored.append(
                PresentButUnmonitored(
                    vendor=vendor,
                    location=getattr(gpu, "pci_address", "unknown location"),
                    reason=f"{vendor.name} GPUs are not supported in this release",
                )
            )
        return tuple(unmonitored)


def _with_attribution(device: GpuDevice, availability: Availability) -> GpuDevice:
    if availability is Availability.AVAILABLE:
        return device.with_metrics(attribution=availability)
    reason = device.attribution_reason or "per-process data is not available for this device"
    return device.with_metrics(attribution=availability, attribution_reason=reason)
