# Specification Quality Checklist: Overall GPU Utilization

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

**Failing item**: "No [NEEDS CLARIFICATION] markers remain" — 2 markers open, both about
presentation on an already-dense panel:

- **FR-018** — where the utilization trend goes relative to the existing memory trend.
- **FR-019** — whether memory-interface activity is surfaced at all.

### Grounded in what the code actually does

The current behaviour was inspected rather than assumed:

| Data | Collected | Displayed |
|---|---|---|
| Compute utilization | every refresh | a bare number, "GPU 3%" |
| Utilization history | **every refresh** | **never drawn** — the trend graph plots memory only |
| Memory-interface utilization | **every refresh** | **nowhere** |

This is why FR-015 can require sampling cost to be *unchanged*: nothing new is measured. It also
sharpens FR-018 and FR-019 into real questions — the data is sitting there unused, and the only
open matter is where to put it.

### The labelling requirements are not padding

Utilization measures the fraction of the sampling period during which at least one kernel was
resident. A single-threaded kernel on one core reports 100%. The figure's common name — "core
utilization" — describes something the hardware does not report, and this project's rules forbid
presenting a value as something it is not.

FR-008 through FR-012 and SC-003, SC-004 exist for that reason: the label must convey time,
no core count may be displayed or derivable, and a measured 0% must be distinguishable from an
unreadable one.

### Relationship to the withdrawn heatmap specification

An earlier feature proposed a per-core heatmap. It was withdrawn after the per-core activity and
occupancy counters proved unsupported on consumer hardware, leaving no honest way to show cores
busy out of total. This specification delivers the useful half of that idea — activity over time
— from data that is genuinely measured, and records the supersession in its Assumptions.


### Validation iteration 2 — 2026-08-16

Both clarifications resolved. All 16 items pass.

- **Presentation (Q1 -> A)**: a separate trend graph, so memory and utilization are visible
  together without switching (FR-018).
- **Memory interface (Q2 -> A)**: displayed alongside compute activity (FR-021).

Three consequences were pinned down rather than left implicit, because each is a way these
choices could go wrong:

1. **FR-019** requires each graph to be labelled. Two unlabelled trend graphs of similar
   appearance, stacked, are a worse outcome than one graph.
2. **FR-020** fixes the utilization scale at 0-100%. Auto-scaling to the recent maximum would
   make an idle GPU's noise look like heavy load, and make two devices incomparable.
3. **FR-022** requires the two activity figures to be distinguishable by more than adjacency.
   Two bare percentages side by side is exactly the confusion Q2 risks.

FR-013 (the process table must not be pushed out of view) becomes load-bearing now that the
panel grows taller, and SC-009 measures it.

Grew from 19 to 23 functional requirements.
