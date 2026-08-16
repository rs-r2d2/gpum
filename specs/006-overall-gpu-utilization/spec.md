# Feature Specification: Overall GPU Utilization

**Feature Branch**: `006-overall-gpu-utilization`

**Created**: 2026-08-16

**Status**: Draft

**Input**: User description: "Add gpu overall core utilization"

## Context

The monitor already reads how busy each GPU is, but barely shows it. Today the figure appears as
a single number in the corner of a device panel — "GPU 3%" — with no history, no context, and no
statement of what it means.

Three gaps, established by inspecting what the tool currently does:

| Data | Collected | Shown |
|---|---|---|
| GPU engine utilization | Yes, every refresh | As a bare number only |
| Utilization history | **Yes, every refresh** | **Never drawn** — the trend graph plots memory alone |
| Memory-controller utilization | **Yes, every refresh** | **Nowhere at all** |

So most of this feature is surfacing measurements the tool already takes. The work is
presentation, not collection.

**One thing this feature must get right.** The figure is often called "core utilization", and
that name invites a specific misreading: that it reports the fraction of the GPU's cores that
are busy. It does not. It reports the fraction of the sampling period during which **at least
one** kernel was resident. A single-threaded kernel occupying one core out of thousands reports
100%. The number is genuinely useful — it answers "is this GPU working or idle?" — but it does
not answer "how much of the GPU is in use", and the interface must not imply that it does.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See how busy the GPU is over time (Priority: P1)

A user watching a workload sees not just the current utilization figure but how it has behaved
over the last few minutes. They can tell a sustained load from a burst, and see whether a job
has finished, without staring at a number and remembering what it said.

**Why this priority**: The history is already being recorded and thrown away. Drawing it is the
difference between a number and an answer.

**Independent Test**: Run a GPU workload, watch the trend rise, stop the workload, and confirm
the trend falls and the busy period stays visible as history.

**Acceptance Scenarios**:

1. **Given** a GPU that reports utilization, **When** the user views it, **Then** a trend of
   recent utilization is shown alongside the current figure.
2. **Given** a workload starts, **When** it runs, **Then** the trend rises within two refresh
   intervals.
3. **Given** the workload ends, **When** the user looks, **Then** the trend falls and the busy
   period remains visible in history.
4. **Given** a period where utilization could not be read, **When** the user views the trend,
   **Then** that period is a visible gap, not a reading of zero.
5. **Given** the refresh interval changes, **When** the user views the trend, **Then** the time
   span it covers stays consistent.

---

### User Story 2 - Understand what the number means (Priority: P1)

The user reads the label and understands they are seeing how much of the *time* the GPU was
busy, not how many of its cores were occupied. Nothing in the interface suggests a fraction of
hardware.

**Why this priority**: Equal to US1. A number that is confidently misread is worse than one that
is absent — a user who believes "40%" means "40% of my cores" will size workloads against a
quantity that was never measured.

**Independent Test**: Ask someone unfamiliar with the tool what the figure means. They should
describe time or busyness, not a proportion of cores.

**Acceptance Scenarios**:

1. **Given** the utilization figure, **When** the user reads its label, **Then** the label
   conveys that it measures how busy the GPU has been over time.
2. **Given** the user wants more detail, **When** they seek an explanation, **Then** the
   interface explains that the figure does not represent a fraction of cores in use.
3. **Given** the interface, **When** the user looks for a count or fraction of busy cores,
   **Then** no such figure is presented anywhere.
4. **Given** a GPU that cannot report utilization, **When** the user views it, **Then** the
   figure is shown as unavailable with a reason — never as 0%, which would assert the GPU is
   idle.

---

### User Story 3 - Distinguish compute activity from memory traffic (Priority: P3)

A user investigating why a workload is slower than expected can see whether the GPU's memory
interface is saturated while its compute engine is not, or the reverse — turning "it's slow"
into a direction to look.

**Why this priority**: Genuinely useful for diagnosis and the data is already collected, but it
is a second number on an already busy panel, and most users only need the first.

**Independent Test**: Run a memory-heavy workload and a compute-heavy one, and confirm the two
figures move differently.

**Acceptance Scenarios**:

1. **Given** a GPU reporting both figures, **When** the user views it, **Then** compute activity
   and memory-interface activity are separately identifiable.
2. **Given** the two figures, **When** the user reads them, **Then** each is labelled clearly
   enough that they cannot be mistaken for one another.
3. **Given** a GPU that reports one but not the other, **When** the user views it, **Then** the
   available figure is shown and the other is marked unavailable.

---

### Edge Cases

- **The GPU cannot report utilization**: shown as unavailable with a reason; every other metric
  continues working.
- **Utilization reads 0% on a GPU that is genuinely idle**: displayed as a real measurement of
  zero, and distinguishable from "could not be read".
- **A workload shorter than one sampling interval**: may not register at all; the interface must
  not imply the trend captures every event.
- **Utilization sits at 100% while the GPU is barely loaded**: this is correct behaviour for a
  time-based measure, and is exactly why US2's labelling exists.
- **A stretch of missing readings**: rendered as a gap, never as zero — the two look identical on
  a graph and mean opposite things.
- **The machine suspends and resumes**: the suspended period appears as a gap, not as idle.
- **The monitor has just opened**: the trend shows only the period actually observed, without
  padding unobserved time as measured idle.
- **Several GPUs with different capabilities**: each shows what it can; one that cannot report
  utilization says so rather than appearing idle.
- **A device panel is already dense**: adding a trend must not push the process table out of
  view or make the panel require scrolling to read the basics.

## Requirements *(mandatory)*

### Functional Requirements

**Display**

- **FR-001**: System MUST display each GPU's current utilization as a percentage.
- **FR-002**: System MUST display a trend of recent utilization alongside the current figure.
- **FR-003**: The trend MUST cover a consistent span of time regardless of the refresh interval.
- **FR-004**: The trend MUST reflect a sustained change within two refresh intervals.
- **FR-005**: Periods where utilization could not be read MUST appear as visible gaps in the
  trend, never as zero.
- **FR-006**: On first opening, the trend MUST show only the period actually observed, without
  padding unobserved time as measured idle.
- **FR-007**: System MUST retain trend history within a bounded limit, so memory does not grow
  with uptime.

**Honest labelling**

- **FR-008**: The utilization figure MUST be labelled so that it conveys how busy the GPU has
  been over time, rather than implying a proportion of cores.
- **FR-009**: System MUST NOT display, imply, or allow derivation of a count or fraction of GPU
  cores in use.
- **FR-010**: System MUST make available to the user an explanation that the figure measures
  time spent busy and not the share of hardware occupied.
- **FR-011**: System MUST show utilization as explicitly unavailable, with a reason, on any GPU
  that cannot report it — and MUST NOT show 0% in that case.
- **FR-012**: A genuine measurement of 0% MUST be visually distinguishable from an unavailable
  reading.

**Layout**

- **FR-013**: Adding the trend MUST NOT push the process table out of view or require scrolling
  to read a device's basic figures.
- **FR-014**: Utilization presentation MUST use consistent units and labels across all devices
  and vendors.

**Conduct**

- **FR-015**: The feature MUST NOT increase sampling cost, since the underlying measurements are
  already collected every refresh.
- **FR-016**: The feature MUST NOT breach the application's existing responsiveness commitments.
- **FR-017**: System MUST remain a read-only observer requiring no elevated privileges.

**Presentation**

- **FR-018**: The utilization trend MUST be a separate graph, distinct from the existing memory
  trend, so both are visible at the same time without switching views.
- **FR-019**: Each trend graph MUST be labelled with what it shows, so two graphs of similar
  appearance cannot be confused.
- **FR-020**: The utilization trend MUST be scaled against a fixed range of 0 to 100 percent, so
  its height is comparable between devices and over time rather than rescaling to whatever the
  recent maximum happens to be.
- **FR-021**: Memory-interface activity MUST be displayed alongside compute activity.
- **FR-022**: Compute activity and memory-interface activity MUST be labelled distinctly enough
  that neither can be read as the other; two bare percentages side by side are not sufficient.
- **FR-023**: Where one of the two activity figures is available and the other is not, the
  available one MUST still be shown and the other marked unavailable.

### Key Entities

- **Utilization Reading**: One measurement of how busy a GPU was during a sampling period, with
  the time it was taken and whether it is a real measurement or unavailable.
- **Utilization Trend**: The bounded sequence of readings behind the visual, covering a fixed
  span of time regardless of refresh rate, including explicit gaps where measurement failed.
- **Activity Kind**: Which aspect of the GPU a reading describes — compute engine or memory
  interface — so the two are never conflated.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can tell whether a GPU is busy, idle, or fluctuating within 5 seconds of
  looking at a device panel.
- **SC-002**: A sustained change in GPU activity appears in the trend within 2 seconds at the
  default refresh setting.
- **SC-003**: Asked what the utilization figure means, users unfamiliar with the tool describe
  time or busyness rather than a proportion of cores in at least 8 of 10 cases.
- **SC-004**: Zero figures anywhere in the interface represent a count or fraction of cores in
  use.
- **SC-005**: Periods without measurement are visually distinct from measured zero activity in
  100% of cases.
- **SC-006**: The trend's time span varies by no more than 10% when the refresh interval changes.
- **SC-007**: Sampling cost is unchanged from before the feature, measurably.
- **SC-008**: Memory used by retained trend history stays within a stated bound across a 24-hour
  run.
- **SC-009**: A device panel's basic figures remain readable without scrolling at the
  application's default window size.
- **SC-010**: Reported utilization agrees with the vendor's own reporting tool within 5
  percentage points across a 10-minute observation under varying load.

## Assumptions

- **The measurements already exist.** Both compute and memory-interface utilization are collected
  on every refresh today; the compute figure is shown as a bare number and its history is
  recorded and then discarded, and the memory-interface figure is not shown at all. This feature
  is presentation work, which is why FR-015 can require sampling cost to be unchanged.
- **Utilization is time-based, and the wording matters.** It is the fraction of the sampling
  period during which at least one kernel was resident. Every requirement here about labelling
  exists because the common name for this figure — "core utilization" — describes something else.
- **No core counts, no derived occupancy.** The hardware does not report how many cores are busy,
  and no figure may be manufactured by combining utilization with a core count, clock speed, or
  anything else. FR-009 makes this explicit; a plausible-looking invented number is worse than an
  absent one.
- **Reuses the existing trend mechanism.** The tool already draws a bounded, gap-aware trend for
  memory. This feature is expected to use the same behaviour rather than introduce a second way
  of drawing history.
- **No alerting, thresholds, or logging.** Notifying when utilization crosses a level, or writing
  it to disk for later analysis, are separate concerns.
- **Supersedes the withdrawn heatmap feature.** An earlier specification proposed a per-core
  heatmap; it was withdrawn once the underlying per-core counters proved unavailable on consumer
  hardware. This feature delivers the useful part of that idea — activity over time — using data
  that is genuinely measured.
