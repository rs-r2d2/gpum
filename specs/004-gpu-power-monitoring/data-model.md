# Phase 1 Data Model: GPU Power Monitoring

**Feature**: 004-gpu-power-monitoring | **Date**: 2026-08-16

Additions only. `MetricValue`, `Availability`, and the rule that no metric is a bare number are
unchanged and govern everything here.

---

## `GpuDevice` additions (`core/models.py`)

| Field | Type | Notes |
|-------|------|-------|
| `power_draw` | `MetricValue` | Raw instantaneous reading, watts |
| `power_draw_avg` | `MetricValue` | Rolling mean over the smoothing window, watts — what the UI shows |
| `power_limit` | `MetricValue` | Enforced limit, watts |
| `energy_session` | `MetricValue` | Watt-hours since monitoring began |
| `energy_interrupted` | `bool` | Whether readings were lost during the accumulation period |
| `limit_reason` | `LimitReason` | Why performance is constrained, if it is |

**Both raw and averaged are carried.** The UI displays the average (FR-025) and history records
it, but the instantaneous value stays available so the distinction is never lost and a future
view can show both without re-plumbing.

**Derived**: `power_percent` — draw against limit — computed only when both are real
measurements, exactly like `memory_percent`.

---

## `LimitReason` (enum, `core/models.py`)

| Value | Meaning | UI |
|-------|---------|-----|
| `NONE` | Measured, and nothing is limiting the device | Show nothing |
| `POWER` | Held at its power budget | "Power limited" |
| `THERMAL` | Held back by temperature | "Thermally limited" |
| `OTHER` | Limited by something outside the two reported causes | "Limited" |
| `UNKNOWN` | Could not be determined | "Unknown" |

**`NONE` and `UNKNOWN` are deliberately distinct** (FR-019). Collapsing them presents an absence
of information as information — the same error as rendering an unavailable metric as zero. The
hardware genuinely reports "nothing is limiting this", and that is a measurement.

**Vendor decoding stays in the backend.** The bitmask never reaches `core`; `backends/nvidia/`
maps it to this enum, so a second vendor populates the same values from whatever it has.

---

## `PowerSmoother` (`core/power.py`)

Rolling mean over a bounded window. Pure logic, no Qt, no vendor types, fake-clock testable.

| Field | Type | Notes |
|-------|------|-------|
| `window_s` | `float` | Target span, ~5 s |
| `_samples` | `deque[float]` | `maxlen` derived from window ÷ interval |

**Rules**:
- `add(metric)` appends only real measurements.
- **Any non-available reading clears the buffer** (FR-027). Averaging across a gap manufactures
  a value for a period that was never measured.
- `average()` returns `UNSUPPORTED` while the buffer is empty — never a stale figure presented
  as current.
- `resize(interval_ms)` recomputes capacity so the window stays ~5 s when the refresh rate
  changes, keeping FR-026's bound intact.

**Why bounded**: at 1 Hz this is a 5-sample mean, which reaches ~80% of a step change within two
samples — satisfying FR-004's two-interval promise. A longer window would read more smoothly and
break that guarantee.

---

## `EnergyAccumulator` (`core/power.py`)

Session energy from a monotonic hardware counter, with the three ways that counter misleads.

| Field | Type | Notes |
|-------|------|-------|
| `_baseline_wh` | `float \| None` | Counter value when the session began |
| `_last_seen_wh` | `float \| None` | Previous reading, for reset detection |
| `_carried_wh` | `float` | Energy banked from before a counter reset or re-baseline |
| `interrupted` | `bool` | A reading was lost during accumulation |

**State transitions**:

```
first reading ──> baseline set, session = 0
normal reading ──> session = carried + (current - baseline)
current < last_seen ──> counter reset: carry forward, re-baseline, continue
resume detected ──> re-baseline (suspended time is not consumption)
unavailable reading ──> interrupted = True; session figure retained, flagged
reset() ──> baseline := current, carried := 0, interrupted := False
```

**Why carry forward rather than restart**: a driver reload mid-session should not silently
discard the energy already measured. Carrying preserves the total while keeping the arithmetic
non-negative (FR-013).

**Why re-baseline on resume**: the counter does not advance while suspended, so the arithmetic
is already safe — but the session it describes would span hours of sleep. Feature 002's
wall-clock resume detection is reused rather than adding a second mechanism (FR-014).

---

## Engine state (`core/engine.py`)

`_DeviceState` gains a `PowerSmoother` and an `EnergyAccumulator`, created on first sight of a
device and destroyed with it — the same lifecycle as the existing per-device health state, which
is already cleared when a device disappears.

**On resume** (feature 002's `ResumeEvent`): every smoother is cleared and every accumulator
re-baselined, so neither averages nor accumulates across the sleep.

---

## Units (`core/units.py`)

| Function | Format | Notes |
|----------|--------|-------|
| `format_watts` | `15.8 W` | One decimal — the hardware reports milliwatts, but a tenth of a watt is already below the noise floor |
| `format_watt_hours` | `0.072 Wh` | Three decimals so short sessions do not round to zero |

Both refuse to format a non-measurement, returning the same explicit unavailable text every
other metric uses.
