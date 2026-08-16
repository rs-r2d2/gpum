# Contract: Power metrics

**Modules**: `src/gpum/core/power.py`, `src/gpum/backends/nvidia/nvml.py`,
`src/gpum/core/engine.py` | **Feature**: 004-gpu-power-monitoring

---

## Backend obligations

The `GpuBackend` protocol is **unchanged**. Power arrives as additional `MetricValue` fields on
`GpuDevice`, so a backend that cannot report power simply leaves them unavailable — no interface
change, no capability negotiation, nothing for other vendors to implement before they are ready.

**MUST**:
- Report draw and limit in **watts** and energy in **watt-hours**, converting from whatever the
  vendor uses. Normalization belongs to the backend, exactly as bytes already do.
- Return `UNSUPPORTED` with a reason for any figure the device cannot provide — never `0 W`,
  which asserts the card is drawing nothing.
- Report draw and limit independently: one being unavailable must not suppress the other
  (FR-006).
- Decode any vendor-specific limiting bitmask into the `core` `LimitReason` enum. **The raw mask
  must not leave the backend.**
- Distinguish "nothing is limiting this device" (`NONE`) from "could not determine" (`UNKNOWN`).

**MUST NOT**:
- **Call any power-limit setter.** The interface that reports the limit can also change it.
  This feature reads. A test asserts no module references the setter functions by name.
- Cache readings between calls — that would make `sampled_at` false.
- Clamp draw to the limit. Brief excursions above the sustained limit are real and are reported.

## Smoothing obligations (`PowerSmoother`)

**MUST**:
- Average only over real measurements.
- **Clear the buffer on any unavailable reading.** Averaging across a gap invents a value for a
  period that was never measured (FR-027).
- Return unavailable while the buffer is empty, rather than a stale value shown as current.
- Keep the window near 5 s as the refresh interval changes (FR-026).

**MUST NOT**: grow the window enough to break the two-interval responsiveness promise; apply any
filter that discards genuine transients (a real spike is information).

## Energy obligations (`EnergyAccumulator`)

**MUST**:
- Report energy since monitoring began, not since driver load.
- Detect a counter going backwards, carry the accumulated total forward, and continue from the
  new baseline — **never emit a negative or implausible figure** (FR-013).
- Re-baseline on resume so suspended time is not counted as consumption (FR-014).
- Flag a total that covers an interrupted period (FR-015).
- Support reset without restarting the application (FR-012).

## Contract tests

| # | Assertion | Enforces |
|---|-----------|----------|
| P-01 | Unavailable power yields `UNSUPPORTED` with a reason, never `0 W` | **FR-005** |
| P-02 | Draw and limit are independently available | FR-006 |
| P-03 | Draw is not clamped to the limit | edge case |
| P-04 | Smoother returns unavailable while empty | FR-027 |
| P-05 | An unavailable reading clears the buffer; the average does not span the gap | **FR-027** |
| P-06 | A step change is ~80% reflected within two samples | **FR-026, SC-002** |
| P-07 | Idle variance under the smoother stays within 10% | SC-003 |
| P-08 | Window resizes with the refresh interval | FR-026 |
| P-09 | Counter reset carries forward; energy never goes negative | **FR-013** |
| P-10 | Resume re-baselines; suspended time is not counted | **FR-014** |
| P-11 | Interrupted readings set the flag; the total is retained | FR-015 |
| P-12 | Reset returns the session to zero without a restart | FR-012 |
| P-13 | `NONE` and `UNKNOWN` limit reasons are distinct | **FR-019** |
| P-14 | No module references any power-limit setter | **FR-020, Principle V** |
| P-15 | The raw throttle bitmask never appears in `core` or `ui` | Principle I |
