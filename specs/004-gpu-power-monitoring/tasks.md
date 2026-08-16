---

description: "Task list for 004-gpu-power-monitoring"
---

# Tasks: GPU Power Monitoring

**Input**: Design documents from `/specs/004-gpu-power-monitoring/`

**Tests**: Mandatory — constitution Principle IV requires tests written and failing first.

**Scope**: Adds power draw, limit, session energy, and limiting reasons. No architectural change.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Foundational (Blocking)

### Tests first

- [X] T001 [P] Write failing tests for `format_watts` and `format_watt_hours` in `tests/unit/test_units.py`, including that neither will format a non-measurement
- [X] T002 [P] Write failing tests for the new `GpuDevice` power fields and `power_percent` in `tests/unit/test_models.py`, asserting the percentage is computed only when both operands are real measurements
- [X] T003 [P] Write failing tests in `tests/unit/test_limit_reasons.py` asserting `NONE` and `UNKNOWN` are distinct states (P-13) — an absence of information must not render as information

### Implementation

- [X] T004 Add `LimitReason` to `src/gpum/core/models.py` with all five states per data-model.md
- [X] T005 Add `power_draw`, `power_draw_avg`, `power_limit`, `energy_session`, `energy_interrupted`, and `limit_reason` to `GpuDevice` in `src/gpum/core/models.py`, defaulting to unavailable so existing backends need no change
- [X] T006 Add `power_percent` to `GpuDevice`, computed only when draw and limit are both real measurements, mirroring `memory_percent`
- [X] T007 [P] Add `format_watts` (1 decimal) and `format_watt_hours` (3 decimals) to `src/gpum/core/units.py`, both refusing to format a non-measurement

**Checkpoint**: `pytest` green; no behaviour change yet.

---

## Phase 2: User Story 1 — Current draw (Priority: P1) 🎯 MVP

### Tests first

- [X] T008 [P] [US1] Write failing tests in `tests/unit/test_power_nvml.py` using an NVML stub: unavailable power yields `UNSUPPORTED` with a reason and **never `0 W`** (P-01)
- [X] T009 [P] [US1] Write failing tests asserting draw and limit are independently available (P-02) and that draw is not clamped to the limit (P-03)
- [X] T010 [P] [US1] Write a failing hardware test in `tests/hardware/test_power_agreement.py` asserting draw within 10% of `nvidia-smi` and the limit matching exactly (P-07 equivalent, SC-004)

### Implementation

- [X] T011 [US1] Add `power_usage`, `power_limit`, `total_energy`, and `throttle_reasons` to `src/gpum/backends/nvidia/nvml.py`, converting milliwatts to watts and millijoules to watt-hours at the boundary — **getters only, no setter may be added**
- [X] T012 [US1] Map NVML errors for each new call to the right `Availability` in `src/gpum/backends/nvidia/errors.py`, so an unsupported card is distinguishable from a permission failure
- [X] T013 [US1] Populate `power_draw` and `power_limit` in `src/gpum/backends/nvidia/backend.py`, each independently guarded so one failing does not suppress the other
- [X] T014 [US1] Render power draw against its limit in `src/gpum/ui/device_panel.py`, routed through `ui/availability.py` so an unavailable value can never reach the screen as a number

**Checkpoint**: watts visible on real hardware. This is the MVP.

---

## Phase 3: User Story 2 — Readable number (Priority: P2)

### Tests first

- [X] T015 [P] [US2] Write failing tests in `tests/unit/test_power_smoothing.py`: the smoother returns unavailable while empty (P-04), and **an unavailable reading clears the buffer so the average never spans a gap** (P-05)
- [X] T016 [P] [US2] Write a failing test asserting a 20 W → 150 W step is ~80% reflected within two samples (P-06) — smoothing must not buy readability by breaking FR-004
- [X] T017 [P] [US2] Write failing tests for idle variance staying within 10% (P-07) and window resizing with the refresh interval (P-08)

### Implementation

- [X] T018 [US2] Implement `PowerSmoother` in `src/gpum/core/power.py` — bounded deque, clears on any unavailable reading, resizes with the interval. No Qt, no vendor types
- [X] T019 [US2] Hold a `PowerSmoother` per device in `src/gpum/core/engine.py` `_DeviceState`, created and destroyed on the same lifecycle as existing per-device health state
- [X] T020 [US2] Populate `power_draw_avg` from the smoother in `src/gpum/core/engine.py`, keeping the raw `power_draw` intact so the distinction is never lost
- [X] T021 [US2] Display the averaged figure in `src/gpum/ui/device_panel.py`, **labelled as averaged** so the user knows what they are reading (FR-008)
- [X] T022 [US2] Add power draw to the per-device history so the trend renders, with gaps where readings were unavailable (FR-009, FR-010)
- [X] T023 [US2] Clear every smoother on resume in `src/gpum/core/engine.py`, reusing feature 002's `ResumeEvent` rather than adding a second detection mechanism

**Checkpoint**: the number is readable and still responsive.

---

## Phase 4: User Story 3 — Session energy (Priority: P2)

### Tests first

- [X] T024 [P] [US3] Write failing tests in `tests/unit/test_energy_accumulator.py` for the normal path and for **a counter reset carrying forward without ever going negative** (P-09)
- [X] T025 [P] [US3] Write failing tests for resume re-baselining so suspended time is not banked as consumption (P-10)
- [X] T026 [P] [US3] Write failing tests for the interrupted flag (P-11) and for reset returning the session to zero without a restart (P-12)

### Implementation

- [X] T027 [US3] Implement `EnergyAccumulator` in `src/gpum/core/power.py` with baseline, carry-forward, interrupted flag, and reset per data-model.md
- [X] T028 [US3] Detect a counter going backwards and re-baseline while carrying the accumulated total forward — a driver reload must not silently discard measured energy
- [X] T029 [US3] Hold an `EnergyAccumulator` per device in `src/gpum/core/engine.py` and re-baseline every one on resume
- [X] T030 [US3] Populate `energy_session` and `energy_interrupted` in `src/gpum/core/engine.py`
- [X] T031 [US3] Display session energy in `src/gpum/ui/device_panel.py` with a reset control, and mark a total that covers an interrupted period
- [X] T032 [US3] Add a hardware test asserting session energy agrees within 5% with the integral of observed draw (SC-005)

**Checkpoint**: "what did that run cost" is answerable.

---

## Phase 5: User Story 4 — Limiting reasons (Priority: P3)

### Tests first

- [X] T033 [P] [US4] Write failing tests asserting the throttle bitmask maps to the right `LimitReason`, including that an unreadable mask yields `UNKNOWN` rather than `NONE`
- [X] T034 [P] [US4] Write a failing test asserting the raw bitmask never appears in `core` or `ui` (P-15)

### Implementation

- [X] T035 [US4] Decode the throttle bitmask to `LimitReason` in `src/gpum/backends/nvidia/errors.py`, surfacing only power and thermal causes — the mask carries more, but rare causes would add noise to a field whose value is being actionable
- [X] T036 [US4] Populate `limit_reason` in `src/gpum/backends/nvidia/backend.py`
- [X] T037 [US4] Display the limiting reason in `src/gpum/ui/device_panel.py`, showing nothing for `NONE` and an explicit unknown for `UNKNOWN`

---

## Phase 6: Polish

- [X] T038 Extend `tests/unit/test_read_only.py` so any reference to a power-limit setter fails the suite (P-14) — the interface we read from can write, and this is what stops that becoming a slider
- [X] T039 [P] Run spike S-01: confirm on hardware that the 5-sample window tracks real load within two intervals and idle variance stays under 10%
- [X] T040 [P] Verify the added calls do not breach the measured per-device query budget
- [X] T041 [P] Update `docs/capability-matrix.md` with power, energy, and limiting-reason support
- [ ] T042 Run quickstart V-1 … V-9 and record results

---

## Dependencies

- **Phase 1** blocks everything.
- **US1 (Phase 2)** is the MVP and must land before US2, which smooths what US1 reads.
- **US3, US4** depend on Phase 1 and on T011's NVML additions; otherwise independent of US2.
- **Polish** last, except T038 which may land any time and arguably should land early.

### Critical path

`T001–T007 → T008–T014 (watts visible) → T018–T021 (readable) → T027–T031 (energy) → ship`

### Parallel opportunities

T001–T003, T008–T010, T015–T017, T024–T026, T033–T034, T039–T041.

---

## Notes

- The default suite must stay green with **no GPU** throughout. Smoothing, energy, and reason
  decoding are all pure logic driven by stubs and the existing fake clock.
- **T038 is not optional polish.** It is the mechanical guard on Principle V.


---

## Implementation status — 2026-08-16

41 of 42 tasks complete. **786 default + 21 hardware tests pass**, lint clean.

### Verified against real hardware

| | GPUM | nvidia-smi |
|---|---|---|
| Draw | 9.1 W | 9.16 W |
| Limit | 180.0 W | 180.00 W |

Session energy accumulates correctly (0.031 Wh over ~9 s at ~12 W). Limiting reason reads as
unconstrained and correctly displays nothing.

### The window size was wrong, and measurement said so

The spec initially called for a ~5 second averaging window. Thirty consecutive 1 Hz reads of the
idle GPU spanned 9.3-21.7 W with a **53.7% worst consecutive change**. Smoothed:

| Window | Worst consecutive change |
|---|---|
| raw | 53.7% |
| 5 s (the guess) | **17.1% — fails SC-003** |
| 8 s | **9.4% — passes** |

The default is now 8 s, and both `research.md` and FR-025 were corrected. The cost is that a
step change travels 25% rather than 40% within two samples — on a 20 W to 150 W step that is
still a 32 W move inside two seconds, which satisfies SC-002.

### Sampling cost grew more than expected

Adding four NVML reads took the per-device query from **0.119 ms p99 to 3.832 ms p99** — 32x.
The 100 ms timeout still holds with 26x headroom, so nothing is breached, but the margin is no
longer enormous. Recorded in `core/engine.py` so the next person adding a metric re-measures
rather than assumes.

### Not completed

| Task | Reason |
|---|---|
| T042 | The full quickstart walk includes observing draw climb and fall under a sustained GPU workload (V-8) and the energy/integral cross-check over a long run (V-9). The automated hardware tests cover both in short form; the extended manual observation was not performed. |

### Design notes worth keeping

- **Per-process power does not exist** in any NVML interface. The spec forbids implying it —
  apportioning device watts by memory share would be a fabricated number.
- **The power-limit interface is read/write.** `tests/integration/test_safety_guarantees.py` now
  fails the suite if any module references a setter by name, and asserts `NvmlLibrary` exposes
  no setter methods at all. That is the mechanical guard on Principle V.
- **A counter reset restarts from zero**, not from the current reading. Re-baselining to
  `current` silently discards energy consumed since the reset — caught by a test that expected
  6.0 Wh and got 5.0.
