# Implementation Plan: Process Table Column Sorting

**Branch**: `003-process-table-sorting` | **Date**: 2026-08-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-process-table-sorting/spec.md`

## Summary

Replace the toolbar sort controls with click-to-sort column headers, make all four columns
sortable, give each device table its own order, and remember that order per GPU.

This is confined to the UI layer plus two small model additions. Nothing about sampling,
measurement, or vendor access changes.

The main finding from Phase 0 is that **per-device independence is free**: today's global
behaviour is not inherent, it exists only because one toolbar control loops over every panel and
pushes the same order into each. Deleting that loop leaves each table independent by
construction (research D-02).

The main risk is the opposite of new work — it is **losing behaviour that already works**. The
current model already ranks unmeasurable memory last and already keeps equal-valued rows stable
across refreshes. Moving sorting behind a different entry point is exactly the kind of change
that drops those silently, so both are now explicit requirements with their own tests
(research D-03).

## Technical Context

**Language/Version**: Python 3.11+ (unchanged)

**Primary Dependencies**: unchanged — PySide6, psutil, `nvidia-ml-py`

**Storage**: `QSettings`, extended with a serialized per-device sort map

**Testing**: `pytest` + `pytest-qt`, headless. No GPU needed for any of this feature.

**Target Platform**: unchanged

**Project Type**: Single-project desktop application (unchanged)

**Performance Goals**: re-sorting several hundred rows must stay inside the existing 16 ms
GUI-thread budget

**Constraints**: sorting is presentation only — it must not alter sampling, device totals, or
which processes are shown (FR-022, FR-023)

**Scale/Scope**: up to 8 device tables, several hundred rows each

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial evaluation (pre-research)

| Gate | Status | Basis |
|------|--------|-------|
| **I. Vendor-Agnostic Abstraction** | ✅ PASS | No backend or vendor code touched. |
| **II. Platform Parity** | ✅ PASS | No OS-specific behaviour; the toolkit provides the interaction on every platform. |
| **III. Non-Blocking Live Updates** | ⚠️ AT RISK | Re-sorting happens on the GUI thread on every refresh, against a 16 ms budget. |
| **IV. Test-First on Simulated Hardware** | ✅ PASS | Entirely testable headless with no GPU. |
| **V. Read-Only, Least Privilege** | ✅ PASS | Adds one small preference entry; changes nothing else. |

### Post-design re-evaluation (after Phase 1)

| Gate | Status | Resolution |
|------|--------|------------|
| **I. Vendor-Agnostic Abstraction** | ✅ PASS | `ProcessSortColumn` gains one value in `core`; no vendor module is touched. |
| **II. Platform Parity** | ✅ PASS | Unchanged. |
| **III. Non-Blocking Live Updates** | ✅ PASS | Sorting a few hundred rows is microseconds, and the existing in-place update path is preserved so a refresh still does not rebuild the model. A test asserts the render budget with 500 rows. |
| **IV. Test-First on Simulated Hardware** | ✅ PASS | Every scenario runs headless. |
| **V. Read-Only, Least Privilege** | ✅ PASS | The per-device map lives with existing preferences; nothing new is written outside them. |

**Gate result**: passes with no violations. The project's two open governance items (feature
002's autostart, feature 001's macOS deferral) are untouched by this work. *(2026-08-17: the macOS item has since been closed by constitution amendment 2.0.0; the Principle V autostart item remains open.)*

## Project Structure

### Documentation (this feature)

```text
specs/003-process-table-sorting/
├── plan.md              # This file
├── clarifications.md    # Pre-spec decisions from /speckit-clarify
├── research.md          # Phase 0 — 5 decisions, no spikes
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── sorting-contract.md
├── checklists/requirements.md
└── tasks.md             # Phase 2
```

### Source Code (repository root)

Changes only.

```text
src/gpum/
├── core/
│   ├── models.py             # CHANGED: ProcessSortColumn gains USER
│   └── preferences.py        # CHANGED: device_sort_orders map; existing sort_column and
│                             #   sort_descending become the default for unseen devices
└── ui/
    ├── process_model.py      # CHANGED: implement sort(); one comparison per column;
    │                         #   preserve the unmeasurable-last and stable-tiebreak rules
    ├── device_panel.py       # CHANGED: enable header sorting; expose sort changes
    ├── main_window.py        # CHANGED: remove the sort dropdown and Descending checkbox;
    │                         #   route per-device sort state
    └── preferences_store.py  # CHANGED: persist and restore the per-device map

tests/
├── unit/
│   ├── test_sort_comparisons.py   # NEW: per-column ordering and unmeasurable-last
│   └── test_sort_persistence.py   # NEW: map round-trip and malformed-input fallbacks
└── integration/
    └── test_header_sorting.py     # NEW: click behaviour, independence, stability
```

**Structure Decision**: no new modules and no architectural change. Sorting is a view concern
(FR-022), so the logic belongs in the table model that already owns row presentation. The only
`core` additions are one enum value and one preference field — both are vocabulary the UI needs
to persist, not behaviour.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations. Two risks worth recording, both about preserving existing behaviour
rather than adding new:

| Risk | Why it exists | How it is contained |
|------|---------------|---------------------|
| **Silently losing the "unmeasurable sorts last" rule.** Today this is an emergent property of one comparison function. Routing sorting through a different entry point is exactly how such a property disappears unnoticed. | FR-010 depends on it, and it is the sorting-layer expression of the project's rule that a missing value must never be treated as a measured one. | Restated as an explicit requirement, given its own tests across all four columns, and asserted in both directions rather than only descending. |
| **Silently losing stable ordering.** Equal-valued rows currently hold position across refreshes because of a fixed identity tiebreak. At 1 Hz, losing it makes the table unusable — rows move out from under the pointer. | FR-012. | The tiebreak is carried into every new comparison, and a test refreshes a table of equal-valued rows repeatedly and asserts the order never changes. |
