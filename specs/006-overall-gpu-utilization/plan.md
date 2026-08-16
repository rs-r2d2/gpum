# Implementation Plan: Overall GPU Utilization

**Branch**: `006-overall-gpu-utilization` | **Date**: 2026-08-16 | **Spec**: [spec.md](./spec.md)

## Summary

Draw the utilization history that is already being collected and discarded, surface the
memory-interface figure that is already collected and never shown, and label both so neither can
be read as a fraction of cores.

This is presentation work only. Phase 0 confirmed both measurements are already taken on every
refresh, so **no backend, adapter, or sampling code changes** and FR-015 can require sampling
cost to be provably unchanged.

The two risks are not technical. They are (a) making the panel so tall the process table falls
out of view, trading a useful table for a decorative graph, and (b) two similar-looking graphs
and two similar-looking percentages becoming harder to read than what they replaced.

## Technical Context

**Language/Version**: Python 3.11+ (unchanged)

**Primary Dependencies**: unchanged

**Storage**: unchanged — no new preference

**Testing**: `pytest` + `pytest-qt`, headless. No GPU needed.

**Target Platform**: unchanged

**Project Type**: Single-project desktop application (unchanged)

**Performance Goals**: unchanged; sampling cost must be *identical*, not merely acceptable

**Constraints**: no core count may be displayed or derivable; a measured 0% must be
distinguishable from an unreadable one; the process table must stay visible

**Scale/Scope**: up to 8 device panels

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial evaluation (pre-research)

| Gate | Status | Basis |
|------|--------|-------|
| **I. Vendor-Agnostic Abstraction** | ✅ PASS | No backend touched; both figures are existing `core` metrics. |
| **II. Platform Parity** | ✅ PASS | No OS-specific behaviour. |
| **III. Non-Blocking Live Updates** | ⚠️ AT RISK | A second graph repaints on every refresh, against a 16 ms GUI budget. |
| **IV. Test-First on Simulated Hardware** | ✅ PASS | Fully testable headless. |
| **V. Read-Only, Least Privilege** | ✅ PASS | Nothing written, nothing elevated. |

### Post-design re-evaluation (after Phase 1)

| Gate | Status | Resolution |
|------|--------|------------|
| **I. Vendor-Agnostic Abstraction** | ✅ PASS | Unchanged. The memory-interface figure was already modelled as an ordinary metric. |
| **II. Platform Parity** | ✅ PASS | Unchanged. |
| **III. Non-Blocking Live Updates** | ✅ PASS | The second graph reuses the existing widget, which does assignment and repaint only. A test asserts the GUI-thread budget with 8 devices, and another asserts per-device sampling cost is unchanged. |
| **IV. Test-First on Simulated Hardware** | ✅ PASS | Every scenario runs against the fake backend. |
| **V. Read-Only, Least Privilege** | ✅ PASS | Unchanged. |

**Gate result**: passes with no violations. The project's two open governance items are untouched.

## Project Structure

### Documentation (this feature)

```text
specs/006-overall-gpu-utilization/
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/utilization-contract.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

Changes only. Note the absence of `backends/` and `adapters/`.

```text
src/gpum/
├── core/
│   └── history.py          # CHANGED: a memory-interface series alongside the existing two
└── ui/
    ├── sparkline.py        # CHANGED: optional fixed scale and a label
    ├── device_panel.py     # CHANGED: utilization trend, both activity figures, labels
    ├── main_window.py      # CHANGED: record the memory-interface series
    └── availability.py     # unchanged — percentage rendering already exists

tests/
├── unit/test_utilization_history.py    # NEW
└── integration/test_utilization_display.py  # NEW
```

**Structure Decision**: no new modules. The trend widget already exists and already handles
bounded history with gaps; this feature gives it a fixed-scale mode and a label rather than
introducing a second way to draw history.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. Two risks recorded, both about the interface becoming worse rather than better:

| Risk | Why it exists | How it is contained |
|------|---------------|---------------------|
| **The process table gets pushed out of view.** The panel already carries a memory bar, a memory trend, power, energy, and a table. A second graph is the change most likely to make the basics require scrolling — trading a table people use for a graph they glance at. | FR-018 puts the trend in its own graph, which is the readable option but the tall one. | Fixed modest graph height, a minimum visible table area, and SC-009 measured at the default window size rather than assumed. |
| **Two graphs and two percentages become harder to read than one.** Stacked graphs of near-identical appearance, and adjacent figures reading "GPU 40% / MEM 90%", invite the reader to mix them up — and "MEM" would collide with the memory *occupancy* already shown a few lines above. | FR-021 puts both activity figures on the panel. | FR-019 requires each graph to be labelled; FR-022 requires the two figures to be distinguished by what they describe, not by position; FR-020 fixes the utilization scale so an idle GPU's noise cannot look like load. |
