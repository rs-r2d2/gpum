# Feature Specification: GPU Power Monitoring

**Feature Branch**: `004-gpu-power-monitoring`

**Created**: 2026-08-16

**Status**: Draft

**Input**: User description: "Add wattage usage of the gpu"

## Context

The monitor currently answers "how much GPU memory is in use, and by what". It says nothing
about how much electricity the GPU is drawing to do that work.

Power is the metric that connects GPU activity to things people actually care about: heat, fan
noise, electricity cost, laptop battery life, whether a power supply is adequate, and — for
anyone running long training jobs — how much energy a run consumed. It is also the metric that
explains *why* a GPU is slower than expected, because a card held at its power limit is being
throttled deliberately rather than malfunctioning.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See what the GPU is drawing right now (Priority: P1)

A user opens the monitor and sees, alongside memory and utilization, how many watts each GPU is
currently drawing and what its limit is. When a workload starts, the number climbs; when the
workload ends, it falls back. They can tell at a glance whether the card is idling or working
hard, without opening a terminal.

**Why this priority**: This is the request. Everything else in this feature builds on having a
trustworthy current-draw figure.

**Independent Test**: Open the monitor on a machine with a supported GPU, start a GPU workload,
and confirm the displayed wattage rises and then falls back when the workload ends.

**Acceptance Scenarios**:

1. **Given** a GPU that reports power, **When** the user opens the monitor, **Then** current
   draw and the power limit are shown for that device, in watts.
2. **Given** the monitor is open, **When** a GPU workload starts, **Then** the displayed draw
   increases within two refresh intervals, and falls back after the workload ends.
3. **Given** a GPU drawing power, **When** the user views it, **Then** draw is shown relative to
   its limit, so the number is interpretable without knowing the card's specification.
4. **Given** a GPU that cannot report power, **When** the user views it, **Then** the field is
   shown as unavailable with a brief reason — never as zero watts, which would wrongly imply the
   card is off.
5. **Given** several GPUs, **When** the user views them, **Then** each shows its own draw and
   limit independently.

---

### User Story 2 - Understand a fluctuating number (Priority: P2)

The user watches the wattage and finds it readable rather than flickering. Momentary spikes are
visible, but the display does not jump so erratically that it cannot be read. A short history
shows the recent trend, so a spike is distinguishable from a sustained load.

**Why this priority**: Power readings are inherently noisy — two readings seconds apart on an
idle card differed by nearly 80% during investigation. A raw instantaneous number refreshing
every second is technically accurate and practically unreadable.

**Independent Test**: Watch an idle GPU for 60 seconds and confirm the displayed value is
readable rather than flickering between distant values, while a real workload still registers
promptly.

**Acceptance Scenarios**:

1. **Given** an idle GPU whose raw readings fluctuate, **When** the user watches for 60 seconds,
   **Then** the displayed value is stable enough to read without appearing frozen.
2. **Given** a sudden sustained increase in load, **When** it occurs, **Then** the displayed
   value reflects it within two refresh intervals.
3. **Given** the monitor has been running for a few minutes, **When** the user views a GPU,
   **Then** a short history of power draw is visible alongside the current value.
4. **Given** a stretch where power could not be read, **When** the user views the history,
   **Then** that stretch appears as a gap rather than as a drop to zero.

---

### User Story 3 - Know what a run cost (Priority: P2)

The user runs a long GPU job and afterwards can see how much energy it consumed, expressed in
familiar units. They can reset the count to start measuring a fresh run.

**Why this priority**: This is the reason most people want watts in the first place — watts are
a rate, and the question underneath is usually total consumption. The underlying counter is
available, so this is a small addition on top of US1.

**Independent Test**: Note the energy figure, run a known GPU workload for a fixed period,
and confirm the figure increased by a plausible amount; reset it and confirm it restarts.

**Acceptance Scenarios**:

1. **Given** the monitor has been open for a period, **When** the user views a GPU, **Then**
   the energy consumed since the monitor was opened is shown in watt-hours.
2. **Given** an energy figure is displayed, **When** the user resets it, **Then** it restarts
   from zero without restarting the application.
3. **Given** a GPU that cannot report cumulative energy, **When** the user views it, **Then**
   the figure is shown as unavailable with a reason, and current draw still works.
4. **Given** the machine suspends and resumes, **When** the user views the energy figure,
   **Then** it does not jump by an implausible amount or become negative.

---

### User Story 4 - Understand why a GPU is being held back (Priority: P3)

When a GPU is running slower than expected, the user can see whether it is being limited by its
power budget, by temperature, or not at all — turning "it feels slow" into a specific,
actionable reason.

**Why this priority**: Genuinely useful diagnostics that reuse data already being collected, but
nobody is blocked without it.

**Independent Test**: On a GPU under sustained heavy load, confirm that when it reaches its
power or thermal limit the interface says so.

**Acceptance Scenarios**:

1. **Given** a GPU being limited by its power budget, **When** the user views it, **Then** the
   interface states that it is power-limited.
2. **Given** a GPU being limited by temperature, **When** the user views it, **Then** the
   interface states that it is thermally limited.
3. **Given** a GPU running unconstrained, **When** the user views it, **Then** no limiting
   reason is shown, rather than an empty or ambiguous field.
4. **Given** a GPU that cannot report limiting reasons, **When** the user views it, **Then**
   the absence is stated rather than implying the GPU is unconstrained.

---

### Edge Cases

- **GPU does not report power at all** (some integrated and older cards): shown as unavailable
  with a reason; every other metric continues working.
- **Power reported but the limit is not**: draw is shown without the relative context, rather
  than suppressing the reading entirely.
- **Reading fluctuates sharply between refreshes**: handled by the display treatment in US2;
  never presented in a way that makes the value unreadable.
- **Draw briefly exceeds the stated limit**: displayed truthfully rather than clamped, since
  brief excursions above the sustained limit are normal behaviour.
- **Cumulative energy counter resets** (driver reload, GPU reset): detected, and the session
  figure continues from the new baseline instead of going negative or spiking.
- **Machine suspends mid-session**: the energy figure does not absorb the suspended period as
  if the GPU had been drawing power throughout.
- **Power reading unavailable for part of a session**: the gap is visible in history and the
  energy figure states that it covers an interrupted period.
- **Multiple GPUs with different limits**: each is interpreted against its own limit; no
  machine-wide total is implied unless explicitly shown as a total.
- **A GPU appears or disappears mid-session**: its energy accounting starts or stops cleanly
  without corrupting other devices' figures.
- **User asks what a process is costing in watts**: not answerable — see Assumptions.

## Requirements *(mandatory)*

### Functional Requirements

**Current draw**

- **FR-001**: System MUST display the current power draw of each GPU that reports it, in watts.
- **FR-002**: System MUST display each GPU's power limit alongside its draw, so the figure is
  interpretable without knowing the card's specification.
- **FR-003**: System MUST express draw relative to the limit, so a user can judge headroom at a
  glance.
- **FR-004**: System MUST update the power reading on the same refresh cadence as existing
  metrics, and MUST reflect a sustained change within two refresh intervals.
- **FR-005**: System MUST show power as explicitly unavailable, with a brief reason, on any GPU
  that cannot report it — and MUST NOT display zero watts in that case.
- **FR-006**: System MUST continue to display draw even when the limit is unavailable, and vice
  versa, rather than suppressing both.

**Readability**

- **FR-007**: System MUST present the power figure so that normal reading-to-reading
  fluctuation does not make it unreadable, while still reflecting genuine sustained changes
  within two refresh intervals.
- **FR-008**: System MUST make clear whether the displayed figure is an instantaneous reading
  or an averaged one, so the user knows what they are looking at.
- **FR-009**: System MUST show a short recent history of power draw per GPU, consistent with
  how other metrics already display trends.
- **FR-010**: System MUST render any period where power could not be read as a gap in that
  history, never as a drop to zero.

**Energy**

- **FR-011**: System MUST display the energy consumed by each GPU since the monitor was opened,
  in watt-hours.
- **FR-012**: Users MUST be able to reset the energy figure without restarting the application.
- **FR-013**: System MUST detect a reset or discontinuity in the underlying cumulative counter
  and continue from the new baseline, never displaying a negative or implausibly large jump.
- **FR-014**: System MUST NOT attribute energy consumed while the machine was suspended to the
  session total.
- **FR-015**: System MUST indicate when an energy figure covers a period during which readings
  were interrupted, so it is not mistaken for a complete measurement.
- **FR-016**: System MUST show energy as unavailable, with a reason, on GPUs that cannot report
  it, while still showing current draw.

**Limiting reasons**

- **FR-017**: System MUST indicate when a GPU is being limited by its power budget.
- **FR-018**: System MUST indicate when a GPU is being limited by temperature.
- **FR-019**: System MUST distinguish "not currently limited" from "cannot determine whether it
  is limited", rather than showing the same empty state for both.

**Conduct**

- **FR-020**: System MUST remain a read-only observer: it MUST NOT change power limits, clocks,
  fan curves, or any other device setting.
- **FR-021**: System MUST obtain all power data without elevated privileges.
- **FR-022**: System MUST continue to send nothing off the machine.
- **FR-023**: System MUST show power data for every GPU it monitors, using consistent units and
  labels regardless of vendor.

**Scope boundary**

- **FR-024**: This feature MUST deliver current draw, power limit, session energy total, and
  limiting reasons (US1, US2, US3, US4). Temperature and fan speed MUST NOT be surfaced as
  displayed metrics in this release, even though they are obtainable — a thermal limit is
  reported as a *reason*, without adding a temperature readout.
- **FR-025**: The displayed power figure MUST be a rolling average over a short window, sized
  from measurement so that SC-003's 10% consecutive-change budget is met, and MUST be labelled
  so the user knows it is averaged rather than instantaneous. **Measured on real hardware: a
  5-second window fails at 17.1%; 8 seconds achieves 9.4%.**
- **FR-026**: The averaging window MUST be short enough that a sustained change registers
  within two refresh intervals, satisfying FR-004 and SC-002.
- **FR-027**: Averaging MUST NOT be applied across a gap in readings. Where power could not be
  read, the average MUST resume from the readings that follow rather than blending across the
  interruption.

### Key Entities

- **Power Reading**: A single measurement of a GPU's current draw, with the time it was taken
  and whether it is a real measurement or unavailable, consistent with how every other metric
  in the tool is represented.
- **Power Limit**: The wattage ceiling currently enforced on a device, used to give the draw
  figure meaning. Read-only.
- **Energy Accumulation**: Energy attributed to a GPU for the current session — a baseline
  taken when monitoring began, the latest cumulative value, whether any interruption occurred,
  and whether the underlying counter has reset.
- **Limiting Reason**: Why a GPU's performance is currently constrained — power budget,
  temperature, none, or undeterminable. The last two are distinct states.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can determine how many watts a GPU is drawing, and how close that is to its
  limit, within 5 seconds of opening the monitor.
- **SC-002**: A sustained change in GPU power draw is visible to the user within 2 seconds at
  the default refresh setting.
- **SC-003**: Displayed power on an idle GPU varies by no more than 10% between consecutive
  refreshes, while a real sustained change of 20% or more still registers within two intervals.
- **SC-004**: Reported power agrees with the vendor's own reporting tool within 10% across a
  10-minute observation under varying load.
- **SC-005**: Reported session energy agrees with the integral of observed draw over the same
  period within 5%.
- **SC-006**: Every power and energy figure displayed is either a real measurement or explicitly
  marked unavailable; across the full test matrix, zero zeroed or fabricated values appear.
- **SC-007**: Across suspend/resume and driver-restart trials, the energy figure never goes
  negative and never jumps by more than the elapsed time at maximum draw could account for —
  100% of trials.
- **SC-008**: On a GPU driven to its power limit, a user can identify that it is power-limited
  rather than faulty within 15 seconds.
- **SC-009**: All power functionality remains available without elevated privileges, and the
  tool continues to produce zero bytes of network traffic.
- **SC-010**: Adding power monitoring does not increase the tool's sampling cost enough to
  breach any existing responsiveness commitment.

## Assumptions

- **Builds on the existing monitor.** This adds metrics to the device view established
  previously. It does not change how memory, utilization, or process attribution behave.
- **Per-process power is not possible and is out of scope.** Power is measured at the device, and
  the underlying interfaces expose no per-process breakdown. A user asking "what is this process
  costing in watts" cannot be answered honestly, so the feature will not imply an answer.
  Estimating it by apportioning device power across processes by memory or utilization share
  would be a fabricated number, which the project's honesty rules forbid outright.
- **Read-only, strictly.** The interfaces that report power limits can also *set* them. This
  feature reads and never writes. Power-limit adjustment is a mutating operation and would
  require its own specification and an explicit decision.
- **Watts and watt-hours.** Familiar units, no configuration. Watt-hours rather than joules
  because electricity is billed and discussed in watt-hours.
- **Session-scoped energy.** The underlying counter accumulates since the driver loaded, which
  is rarely what a user wants to know. The figure shown is energy since monitoring began, which
  matches the question people actually ask.
- **Vendor-neutral presentation.** Where a vendor cannot supply power data, it degrades to
  unavailable with a reason, exactly as other metrics already do. Only one vendor backend is
  currently implemented, but nothing here is specific to it.
- **No alerting or budgets.** Notifying on a wattage threshold, capping consumption, or logging
  power to disk for later analysis are all out of scope.
- **No cost estimation.** Converting watt-hours to currency requires a tariff, which varies by
  region, time of day, and contract. Out of scope; the watt-hour figure is the deliverable.
