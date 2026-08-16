# Specification Quality Checklist: Process Table Column Sorting

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-16
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Items marked incomplete require spec updates before `/speckit-clarify` or `/speckit-plan`

### Validation iteration 1 — 2026-08-16

**All 16 items pass on the first iteration.** No clarification markers were needed, because the
three decisions that would have required them were already settled in a `/speckit-clarify`
session and recorded in `clarifications.md`:

1. Header-click sorting with a direction indicator; the toolbar dropdown and Descending
   checkbox are removed (FR-001 – FR-005).
2. Each device table sorts independently (FR-014 – FR-016).
3. Per-device sort persists indefinitely, keyed on the GPU's stable identity (FR-017 – FR-021).

**Written against the real starting point**, not a guess: the current `ProcessSortColumn` carries
only NAME, PID, and MEMORY_USED while the table displays four columns — so **User** is displayed
but unsortable, which FR-006 fixes. The existing stability guarantee (equal values keep a fixed
relative order) and the existing rule that unmeasurable memory sorts last are both preserved
rather than rebuilt (FR-010, FR-012, and the closing Assumption).

**Scope deliberately bounded**: no multi-column sorting, no column reordering, resizing
persistence, or show/hide. Each is an adjacent table feature that would expand this well beyond
the request.

**One consequence carried forward from clarification**: unbounded per-GPU sort storage was chosen
over a pruned alternative. The settings file will accumulate an entry per GPU the machine has
ever had and never self-clean. Recorded in Assumptions rather than re-litigated — it was an
informed choice.
