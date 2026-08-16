# Implementation Plan: GPU Power Monitoring

**Branch**: `004-gpu-power-monitoring` | **Date**: 2026-08-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-gpu-power-monitoring/spec.md`

## Summary

Add power draw, power limit, session energy, and limiting reasons to the device view.

This is the first feature since 001 to add genuinely new monitoring capability, and it fits the
existing architecture without changing it: these are device metrics on devices that already have
metrics, read through the NVML wrapper that already exists, at a cost well inside the measured
per-device query budget.

Two findings from Phase 0 shape the work:

1. **The reading is genuinely noisy.** Two reads of an *idle* card seconds apart gave 8.8 W and
   15.8 W — a 79% swing with no workload change. Hence the rolling average, bounded so it cannot
   defeat the responsiveness promise, and forbidden from averaging across gaps (research D-02).
2. **Session energy has three distinct ways to lie**: the counter can reset and go backwards,
   the machine can suspend, and readings can be interrupted. Each needs specific handling or the
   figure is worse than not showing one (research D-03).

## Technical Context

**Language/Version**: Python 3.11+ (unchanged)

**Primary Dependencies**: unchanged — PySide6, psutil, `nvidia-ml-py`. No new dependency.

**Storage**: `QSettings` as before; no new persisted state beyond an energy-reset marker held
in memory only.

**Testing**: `pytest` + `pytest-qt`; new metrics tested through the existing NVML stub pattern so
the default suite still needs no GPU. Hardware assertions extend `tests/hardware/`.

**Target Platform**: Linux + NVIDIA (unchanged). Nothing here is vendor-specific in `core`.

**Project Type**: Single-project desktop application (unchanged)

**Performance Goals**: unchanged — 1 Hz default, 16 ms GUI-thread budget. Four extra NVML calls
per device per cycle against a measured 0.119 ms p99 budget.

**Constraints**: read-only (the same interface that reports power limits can set them — this
feature never writes); no elevation; no network; every value a real measurement or explicitly
unavailable.

**Scale/Scope**: up to 8 GPUs, one machine.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial evaluation (pre-research)

| Gate | Status | Basis |
|------|--------|-------|
| **I. Vendor-Agnostic Abstraction** | ⚠️ AT RISK | New metrics could be added in NVML's shape and leak vendor specifics into `core`. |
| **II. Platform Parity** | ✅ PASS | No OS-specific code; power is a device metric, not a platform one. |
| **III. Non-Blocking Live Updates** | ⚠️ AT RISK | Four more calls per device per cycle, plus smoothing that could tempt computation onto the GUI thread. |
| **IV. Test-First on Simulated Hardware** | ⚠️ AT RISK | A feature about real electricity invites tests that need a real GPU. |
| **V. Read-Only, Least Privilege** | ⚠️ AT RISK | **The power-limit interface is read/write.** Reading it puts a setter within easy reach. |

### Post-design re-evaluation (after Phase 1)

| Gate | Status | Resolution |
|------|--------|------------|
| **I. Vendor-Agnostic Abstraction** | ✅ PASS | Power is expressed as ordinary `MetricValue`s on `GpuDevice`, identical in shape to memory and utilization. `LimitReason` is a `core` enum, not a bitmask — the NVML mask is decoded inside `backends/nvidia/` and never crosses out. Adding a vendor means populating the same fields. |
| **II. Platform Parity** | ✅ PASS | Unchanged; no adapter touched. |
| **III. Non-Blocking Live Updates** | ✅ PASS | Smoothing lives in `core/engine.py` beside existing per-device state (research D-05), so the UI still only assigns and repaints. Measured headroom confirms the extra calls fit. |
| **IV. Test-First on Simulated Hardware** | ✅ PASS | Smoothing, energy accumulation, counter reset, and suspend handling are all pure logic driven by a stub and the existing fake clock. Hardware tests assert agreement, not behaviour. |
| **V. Read-Only, Least Privilege** | ✅ PASS | Enforced structurally: the NVML wrapper exposes no setter, and an automated test asserts no module references `nvmlDeviceSetPowerManagementLimit` or its siblings. See Complexity Tracking. |

**Gate result**: passes with no new violations. Feature 002's Principle V item (autostart) and
feature 001's Principle II item (macOS) remain open and unchanged by this work.

## Project Structure

### Documentation (this feature)

```text
specs/004-gpu-power-monitoring/
├── plan.md              # This file
├── research.md          # Phase 0 — 6 decisions + 2 spikes
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── power-contract.md
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

Changes only; everything not listed is untouched.

```text
src/gpum/
├── core/
│   ├── models.py        # CHANGED: power_draw, power_draw_avg, power_limit,
│   │                    #   energy_session, limit_reason on GpuDevice; LimitReason enum
│   ├── power.py         # NEW: PowerSmoother and EnergyAccumulator — pure logic, no Qt,
│   │                    #   no vendor types, fake-clock testable
│   ├── engine.py        # CHANGED: owns per-device smoothing/energy state; clears on
│   │                    #   device loss; re-baselines on resume
│   └── units.py         # CHANGED: format_watts, format_watt_hours
├── backends/nvidia/
│   ├── nvml.py          # CHANGED: power_usage, power_limit, total_energy, throttle_reasons
│   ├── errors.py        # CHANGED: throttle bitmask -> LimitReason mapping
│   └── backend.py       # CHANGED: populate the new fields
└── ui/
    ├── device_panel.py  # CHANGED: power row, energy row with reset, limit reason
    └── availability.py  # CHANGED: watt/watt-hour rendering via the existing honest path

tests/
├── unit/
│   ├── test_power_smoothing.py   # NEW
│   ├── test_energy_accumulator.py # NEW
│   ├── test_limit_reasons.py      # NEW
│   └── test_read_only.py          # CHANGED: extend forbidden-setter list
├── integration/
│   └── test_power_display.py      # NEW
└── hardware/
    └── test_power_agreement.py    # NEW
```

**Structure Decision**: no architectural change. The one new module, `core/power.py`, exists
because smoothing and energy accumulation are stateful across cycles, and that state has to live
somewhere that is neither the backend (which must not cache — caching would make `sampled_at` a
lie) nor the UI (which must not compute — that would breach the 16 ms budget). The engine
already owns exactly this kind of per-device, cross-cycle state and already disposes of it when a
device disappears.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations. Two design decisions carry risk worth recording, since both are
places where a later change could quietly break a guarantee:

| Risk | Why it exists | How it is contained |
|------|---------------|---------------------|
| **A read-only feature reading a read/write interface.** The same NVML surface that reports the power limit can set it, and a future contributor adding "just a slider" would breach Principle V. | FR-002 requires the limit to give the draw figure meaning. | The wrapper exposes getters only, and `tests/unit/test_read_only.py` is extended to fail if any module references the setter functions by name. The prohibition is mechanical, not a comment. |
| **Smoothing can become a lie.** An averaged number is not a measurement of any instant, and a window that grows, or that spans a gap, silently reports something that never happened. | FR-025: the raw reading is unreadable (79% idle swing). | FR-026 bounds the window against the responsiveness promise; FR-027 forbids spanning gaps and the buffer clears on any unavailable reading; FR-008 requires the interface to say the figure is averaged. All three are tested. |
