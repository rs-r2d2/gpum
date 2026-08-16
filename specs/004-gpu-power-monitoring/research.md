# Phase 0 Research: GPU Power Monitoring

**Feature**: 004-gpu-power-monitoring | **Date**: 2026-08-16

Every decision below was probed on the reference GPU first — RTX 5060 Ti, driver 580.159.03 —
rather than reasoned about. The measured surface:

```
instant power draw                 15.8 W        (a prior read seconds earlier: 8.8 W)
enforced power limit              180.0 W
default power limit               180.0 W
limit constraints (min, max)      150.0, 216.0 W
total energy since driver load     72.431 Wh
power management mode                   1        (enabled)
throttle reasons                      0x0        (unconstrained)
```

---

## D-01: Where power comes from

**Decision**: Read draw, limit, cumulative energy, and throttle reasons through the existing
NVML wrapper, adding four calls to `backends/nvidia/nvml.py`. No new dependency.

**Rationale**: All four are already reachable through the binding the project installs, are
available unprivileged, and cost microseconds — the measured per-device query budget is 0.119 ms
p99, and these additions stay well inside it. Nothing about the architecture needs to change:
they are device metrics on a device that already has metrics.

**Alternatives considered**: parsing `nvidia-smi -q -d POWER` — rejected for the same reason it
was rejected in feature 001: a subprocess per refresh is a permanent cost on the machine being
measured. Reading `/sys/class/drm/*/device/hwmon/*/power1_input` — rejected as vendor-neutral in
theory but absent for NVIDIA in practice.

---

## D-02: Smoothing, and why it must be bounded

**Decision**: Display a rolling mean over a ~5 second window, sized from the current refresh
interval, labelled in the interface as an average.

**Rationale**: This is the finding that justifies the decision. Two reads of an **idle** card
seconds apart returned 8.8 W and 15.8 W — a 79% swing with no workload change at all. Power
draw is genuinely spiky at the sampling instant, so a raw reading refreshed every second is
accurate and unreadable; users would reasonably report it as a bug.

**Window size, corrected by measurement.** The initial estimate of 5 seconds was wrong. Thirty
consecutive 1 Hz reads of an idle RTX 5060 Ti spanned 9.3-21.7 W with a worst consecutive change
of **53.7%**. Smoothed:

| Window | Worst consecutive change |
|--------|--------------------------|
| raw    | 53.7% |
| 3 s    | 21.4% |
| 5 s    | **17.1% — fails SC-003** |
| 8 s    | **9.4% — passes** |
| 10 s   | 7.8% |

SC-003 budgets 10%, so **8 seconds is the shortest window that meets it**. The cost is
responsiveness: an 8-sample mean travels 25% of a step within two samples rather than 40%. On a
realistic 20 W to 150 W step that is still a 32 W move inside two seconds, which satisfies
SC-002. FR-026 makes the bound a requirement rather than an implementation detail.

A second capture during a quieter period showed only 16.9-18.3 W with ~3% consecutive change —
both are real. The window is sized for the noisy case, because that is the one that makes the
display unreadable.

**And the rule that keeps it truthful**: FR-027 forbids averaging across a gap. Blending
readings from either side of an interruption manufactures a value for a period that was never
measured — the same class of lie as rendering an unavailable metric as zero. The buffer is
cleared on any unavailable reading.

**Alternatives considered**: exponential moving average — smoother and cheaper, but its
effective window is harder to state honestly in the interface, and "labelled so the user knows
what they are looking at" (FR-008) is easier to satisfy with a plain mean over a stated window.
Median-of-N — more spike-resistant, but it *removes* genuine transients, and a brief real spike
is information a monitor should not discard.

---

## D-03: Session energy, and the three ways it can lie

**Decision**: Track session energy as `current_counter - baseline`, where the baseline is taken
when the device is first sampled, with explicit handling for counter reset, suspend, and gaps.

**Rationale**: The driver's counter accumulates since driver load (72.4 Wh on this machine),
which is almost never the question a user has. "How much did this run consume" needs a
session-scoped figure.

Three failure modes, each requiring specific handling:

1. **Counter reset** (driver reload, GPU reset): the raw value goes *backwards*. Naive
   subtraction yields a negative energy figure. Detected by `current < last_seen`; the baseline
   is re-seeded and accumulation continues from the new zero (FR-013).
2. **Suspend**: the machine sleeps for hours. The counter does not advance while suspended, so
   the arithmetic is safe — but the *session* it now describes is misleading. Feature 002
   already detects resume via wall-clock gap; that signal is reused to re-baseline (FR-014).
3. **Interrupted readings**: if power was unavailable for part of the session, the total covers
   a period it did not measure. Rather than silently under-reporting, the figure is marked as
   covering an interrupted period (FR-015).

**Alternatives considered**: integrating observed draw over time ourselves (Σ watts × interval)
— rejected as strictly worse: it inherits the sampling noise, misses everything between
samples, and would disagree with the hardware counter. The counter is the better instrument;
SC-005 checks our figure against the integral as a sanity bound, not as the source.

---

## D-04: Limiting reasons

**Decision**: Map the throttle-reason bitmask to three user-facing states — power-limited,
thermally limited, or unconstrained — plus a fourth for "cannot determine".

**Rationale**: FR-019 requires "not currently limited" and "cannot tell whether it is limited"
to be *different* states. Collapsing them is the same mistake as rendering an unavailable metric
as zero: it presents an absence of information as information. The bitmask reports 0x0 when
unconstrained, which is a genuine measurement of "nothing is limiting this", distinct from the
query failing.

Only power and thermal reasons are surfaced. The bitmask carries more (sync boost, display
clock, and others) but they are rare on desktop hardware and would add noise to a field whose
value is being immediately actionable.

---

## D-05: Where the smoothing state lives

**Decision**: In the sampling engine, keyed per device, alongside the existing per-device health
state. Not in the backend, and not in the UI.

**Rationale**: The backend contract requires each `sample_device()` call to be a fresh
point-in-time reading with no caching — a backend-level buffer would make `sampled_at` a lie.
The UI must not compute anything derived, to hold the 16 ms GUI-thread budget. The engine
already carries per-device state across cycles and already clears it when a device disappears,
which is exactly the lifecycle a smoothing buffer needs.

**Consequence**: `GpuDevice` carries both the raw reading and the averaged one. The UI displays
the average and the history records the average, but the raw value remains available so the
distinction is never lost.

---

## D-06: Units

**Decision**: Watts for draw and limit, watt-hours for energy. Fixed, not configurable.

**Rationale**: Both are how electricity is discussed and billed. Joules would be more
scientifically conventional and less useful to someone asking what a training run cost. Adding
a unit preference for two values would be configuration for its own sake.

**Precision**: one decimal place for watts (the hardware reports milliwatts, but a tenth of a
watt is already below the noise floor), three for watt-hours so short sessions are not rounded
to zero.

---

## Spikes required

- **S-01 — smoothing under real load**: confirm on hardware that a 5-sample mean tracks a real
  workload's step change within two intervals, and that idle variance falls under SC-003's 10%
  bound. The window size is derived from a two-sample noise observation and should be checked
  against a longer run.
- **S-02 — counter reset behaviour**: the reset path (D-03 case 1) is implemented defensively
  and unit-tested with a stub, but has not been observed against a real driver reload.
