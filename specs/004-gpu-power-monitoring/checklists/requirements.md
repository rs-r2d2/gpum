# Specification Quality Checklist: GPU Power Monitoring

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

**Failing item**: "No [NEEDS CLARIFICATION] markers remain" — 2 markers open:

- **FR-024** — feature scope: power alone, power + energy, or a broader sensors view.
- **FR-025** — display treatment for a genuinely noisy reading.

Both were kept rather than defaulted because each changes the size of the work and the shape of
the interface, and each has more than one defensible answer.

**Grounded in measurement, not assumption**: the power surface was probed on the reference GPU
before writing. Current draw, enforced limit, default limit, limit constraints, cumulative
energy, power-management mode, and throttle reasons are all available unprivileged. Per-process
power is **not** available at all, which is why the spec forbids implying it rather than leaving
it as an open question.

**Noise is a measured fact, not a guess**: two readings taken seconds apart on an idle card gave
8.8 W and 15.8 W — a ~79% swing with no workload change. That is what FR-007 and FR-025 exist to
address, and what SC-003 quantifies.

**Read-only boundary**: the same interface that reports power limits can set them. The spec
states explicitly that this feature reads and never writes, keeping it inside the project's
read-only principle.


### Validation iteration 2 — 2026-08-16

Both clarifications resolved. All 16 items pass.

- **Scope (Q1 → B)**: current draw, power limit, session energy, and limiting reasons.
  Temperature and fan speed are explicitly excluded as displayed metrics (FR-024) — a thermal
  limit surfaces as a *reason* without adding a temperature readout, which keeps the device
  panel from becoming a sensor dump.
- **Display (Q2 → B)**: ~5 s rolling average, labelled as averaged (FR-025).

Two consequences of Q2 were pinned down rather than left implicit, because each is a way
averaging could quietly become dishonest:

1. **FR-026** bounds the window so smoothing cannot defeat FR-004/SC-002 — a real sustained
   change must still land within two refresh intervals.
2. **FR-027** forbids averaging across a gap. Blending readings from either side of an
   interruption would manufacture a value for a period that was never measured, which is the
   same failure as rendering an unavailable metric as zero.

Grew from 25 to 27 functional requirements.
