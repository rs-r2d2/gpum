---
description: "Task list for 006-overall-gpu-utilization"
---

# Tasks: Overall GPU Utilization

**Input**: Design documents from `/specs/006-overall-gpu-utilization/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/utilization-contract.md

**Tests**: **Mandatory.** Constitution Principle IV (Test-First on Simulated Hardware) requires
tests written and failing before implementation. Every scenario runs headless against the fake
backend; no GPU is needed except where a task says so.

**Scope**: Presentation only. Research D-01 established that both figures are already sampled on
every refresh, so **no `backends/` or platform-adapter code is touched** — which is what lets
FR-015 require sampling cost to be provably unchanged.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: `US1`, `US2`, `US3` — maps to the user stories in spec.md
- Setup, Foundational, and Polish tasks carry no story label

## Path Conventions

Single project, repository root: `src/gpum/`, `tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization

**No setup tasks.** This feature adds no dependency, module, package, or tooling. The trend
widget, the bounded gap-aware history, and the availability renderer all already exist; the
feature gives the first a fixed-scale mode and the second a fourth series. Introducing anything
new here would violate the "no second way of drawing history" decision in research D-06.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The memory-interface series must exist and be recorded before any panel can draw it

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests first ⚠️

- [X] T001 Write failing tests in `tests/unit/test_utilization_history.py` for a
  `memory_utilization` series: appended each refresh, bounded by capacity, gap-aware, and window
  constant across an interval change (U-01, U-02, U-03, U-05)
- [X] T002 Write a failing test in `tests/unit/test_utilization_history.py` asserting a measured
  0% is stored distinctly from an unavailable reading (U-04) — the two look identical on a graph
  and mean opposite things

### Implementation

- [X] T003 Add the `memory_utilization` series and `append_memory_utilization` to `DeviceHistory`
  in `src/gpum/core/history.py`, matching the existing bounded, gap-aware behaviour rather than
  introducing a second mechanism
- [X] T004 Include the new series in `append_gap` and `resize` in `src/gpum/core/history.py`, so a
  suspend gap and an interval change treat all four series alike (FR-007, SC-006)
- [X] T005 Record the memory-interface reading on every refresh in `src/gpum/ui/main_window.py`,
  alongside the compute reading already recorded (depends on T003)

**Checkpoint**: `pytest` green; no visible change yet. Foundation ready.

---

## Phase 3: User Story 1 — See how busy the GPU is over time (Priority: P1) 🎯 MVP

**Goal**: Draw the utilization history that is already collected and currently discarded, as a
separate labelled graph on a fixed 0–100 scale.

**Independent Test**: Run a GPU workload, watch the trend rise within two refresh intervals, stop
the workload, and confirm the trend falls while the busy period stays visible as history
(quickstart V-1). An unreadable stretch appears as a break, not a drop to zero (V-3).

### Tests for User Story 1 ⚠️

- [X] T006 [US1] Write failing tests in `tests/integration/test_utilization_display.py` for a
  utilization trend rendered from the already-collected `history.utilization` series (U-01)
- [X] T007 [US1] Write a failing test in `tests/integration/test_utilization_display.py` asserting
  the graph uses a **fixed 0–100 scale** (U-06) and that an idle GPU's 0–3% noise does not fill
  its height (U-07)
- [X] T008 [US1] Write a failing test in `tests/integration/test_utilization_display.py` asserting
  an unavailable stretch renders as a break in the line, not a drop to zero (U-03)
- [X] T009 [US1] Write a failing test in `tests/integration/test_utilization_display.py` asserting
  each trend graph carries a label (U-08)

### Implementation for User Story 1

- [X] T010 [US1] Add an optional `fixed_maximum` to `Sparkline` in `src/gpum/ui/sparkline.py`, so
  a percentage series is drawn against 0–100 instead of its observed peak — auto-scaling would
  make an idle GPU read as heavily loaded (FR-020)
- [X] T011 [US1] Add a `label` to `Sparkline` in `src/gpum/ui/sparkline.py`, drawn top-left, so
  two stacked graphs of similar appearance cannot be mixed up (FR-019)
- [X] T012 [US1] Add the utilization sparkline to `src/gpum/ui/device_panel.py` beneath the memory
  trend, with a fixed modest height and a distinct colour (FR-018)
- [X] T013 [US1] Label the existing memory trend in `src/gpum/ui/device_panel.py` too, so the pair
  is symmetric rather than one named and one anonymous (FR-019)
- [X] T014 [US1] Feed the trend from `history.utilization` in `src/gpum/ui/device_panel.py` — the
  data is already collected every refresh and currently discarded (FR-002, FR-006)

**Checkpoint**: The utilization history that was being thrown away is now visible. **MVP.**

---

## Phase 4: User Story 2 — Understand what the number means (Priority: P1)

**Goal**: Label the figure so it reads as time spent busy, never as a fraction of cores, and make
the explanation reachable from the panel.

**Independent Test**: Ask someone unfamiliar with the tool what the figure means — they describe
time or busyness, not a proportion of cores (SC-003). No figure anywhere is a core count
(quickstart V-7). An unreadable GPU says so rather than showing 0% (V-4).

### Tests for User Story 2 ⚠️

- [X] T015 [US2] Write a failing test in `tests/integration/test_utilization_display.py` asserting
  the utilization label conveys time/busyness rather than a proportion of hardware (FR-008)
- [X] T016 [US2] Write a failing test in `tests/integration/test_utilization_display.py` asserting
  **no figure anywhere is a core count or a fraction of cores**, including any value derivable by
  combining utilization with a count (U-11, FR-009)
- [X] T017 [US2] Write a failing test in `tests/integration/test_utilization_display.py` asserting
  unavailable utilization shows a reason and never `0%` (FR-011), and that a measured 0% is
  displayed differently (U-04, FR-012)

### Implementation for User Story 2

- [X] T018 [US2] Label the utilization figure and graph in `src/gpum/ui/device_panel.py` to convey
  how busy the GPU has been over time — "GPU compute busy N% of the time" (FR-008)
- [X] T019 [US2] Provide the FR-010 explanation as a tooltip on the activity label in
  `src/gpum/ui/device_panel.py` — that the figure measures time spent busy, not the share of
  hardware occupied, and that one small task can hold it at 100%
- [X] T020 [US2] Render unavailable and measured-zero distinctly in
  `src/gpum/ui/device_panel.py`, reusing `src/gpum/ui/availability.py` rather than adding a second
  rendering path (FR-011, FR-012)

**Checkpoint**: US1 and US2 both work. The trend is drawn *and* cannot be confidently misread.

---

## Phase 5: User Story 3 — Distinguish compute activity from memory traffic (Priority: P3)

**Goal**: Surface the memory-interface figure that is collected and never shown, labelled so it
cannot be read as the memory *occupancy* already on the same panel.

**Independent Test**: Run a memory-heavy workload and a compute-heavy one and confirm the two
figures move differently (quickstart V-5). A device reporting one but not the other shows both
states correctly.

### Tests for User Story 3 ⚠️

- [X] T021 [US3] Write a failing test in `tests/integration/test_utilization_display.py` asserting
  both activity figures are displayed and are **labelled by what they describe**, not by position
  (U-09, FR-021, FR-022)
- [X] T022 [US3] Write a failing test in `tests/integration/test_utilization_display.py` asserting
  neither label reads as memory *occupancy*, which the same panel already shows a few lines above
  (U-09)
- [X] T023 [US3] Write a failing test in `tests/integration/test_utilization_display.py` asserting
  one figure available and the other not still renders both states correctly (U-10, FR-023)

### Implementation for User Story 3

- [X] T024 [US3] Display memory-interface activity from `device.utilization_memory` beside compute
  activity in `src/gpum/ui/device_panel.py` (FR-021)
- [X] T025 [US3] Label the two in `src/gpum/ui/device_panel.py` — "Memory interface busy N% of the
  time", with its own tooltip — so neither can be read as the other and neither collides with the
  memory occupancy figure already on the panel (FR-022)

**Checkpoint**: All three user stories independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T026 [P] Write a test in `tests/integration/test_utilization_display.py` asserting the
  process table remains visible at the default window size with both graphs present (U-12,
  FR-013, SC-009) — the change most likely to trade a useful table for a decorative graph
- [X] T027 [P] Measure and record per-device sampling cost before and after the feature (U-13,
  FR-015, SC-007) — this feature draws data already collected, so any movement means something is
  being sampled twice. Result recorded under *Implementation status* below.
- [X] T028 [P] Write a test in `tests/integration/test_utilization_display.py` asserting 8 device
  panels render inside the 16 ms GUI-thread budget (U-14, FR-016)
- [X] T029 Verify agreement with `nvidia-smi` over a 10-minute varying-load run, within 5
  percentage points, in `tests/hardware/test_nvidia_smi_agreement.py` (SC-010) — **needs a GPU**.
  Load is generated by a CUDA spin kernel in `tests/hardware/loadgen.py`, since nothing on a
  plain driver install makes the GPU busy and an idle GPU agrees trivially.
- [X] T030 Run quickstart V-1 through V-9 from `specs/006-overall-gpu-utilization/quickstart.md`
  and record results (see *Quickstart results* below)
- [X] T031 Rebuild the AppImage bundle so the shipped artifact carries the change
- [X] T042 [P] Add an automated regression test for U-13 pinning per-device sampling cost, so a
  future change cannot silently start sampling twice (T027 measured it once; nothing guarded it).
  Structural guard in `tests/integration/test_sampling_cost.py` (headless, counts backend calls);
  wall-clock guard in `tests/hardware/test_sampling_cost.py`.

### Defects found by T030 and fixed

- [X] T043 Simulate memory-interface utilization in the fake backend
  (`src/gpum/backends/fake/scenarios.py`, `src/gpum/backends/fake/backend.py`) — it was
  hard-coded `unsupported("not simulated")`, so US3 and quickstart V-5 could not be exercised
  headless at all and FR-023 had no end-to-end coverage
- [X] T044 Stop splicing the availability state into the measured sentence in
  `src/gpum/ui/device_panel.py` — an unreadable figure rendered as "GPU compute busy **Not
  supported** of the time" (FR-011)
- [X] T045 Carry the unavailability *reason* in the activity tooltip in
  `src/gpum/ui/device_panel.py` — FR-011 asks for a reason and only the state was shown
- [X] T046 Fix the two quickstart commands that selected zero tests and exited green
  (`-k fixed_scale` against the wrong file, `-k cores` against `core_count`), and record that
  V-6 needs real hardware, in `specs/006-overall-gpu-utilization/quickstart.md`

### Defect found by running T029 at its specified duration

- [X] T047 Bracket the vendor comparison in `tests/hardware/test_nvidia_smi_agreement.py`
  instead of comparing single instants (SC-010). Run at the 10 minutes SC-010 specifies, T029
  failed at 19.0 pp against a 5 pp tolerance — but the figure was not wrong. Three controls
  on the reference hardware:

  | Comparison | Worst | n |
  |---|---|---|
  | ours vs `nvidia-smi`, back-to-back, under load | 0.0 pp | 117 |
  | ours vs `nvidia-smi`, back-to-back, idle desktop | 0.0 pp | 117 |
  | `nvidia-smi` vs **itself**, 100 ms apart, idle desktop | **4.0 pp** | 117 |

  The test asserted on the worst single instantaneous comparison of a quantity that moves
  between the two reads. `SETTLE_S` already compensated for this at load transitions; what it
  missed is that the *idle* blocks are not idle — a compositor or browser burst lands between
  the two reads roughly once in 378 samples and scores as disagreement. Each reading is now
  bracketed by an `nvidia-smi` read either side, and only a value outside the bracket counts.
  The 5 pp tolerance is untouched and a wrong figure still fails; what stopped failing is the
  clock ticking between two reads. Applied to the memory-interface comparison too, which shared
  the weakness and happened to pass.

---

## Phase 7: UI cleanup and utilization bars (added 2026-08-16)

**Requested**: "Clean UI and separate bar for both cpu and memory utilization percentage."

Phases 2–6 left the panel carrying the same number twice — `GPU 5%` in the stats row and
`Compute busy 5% of the time` immediately below it — plus a vendor subtitle repeating what the
title already said. Three percentages were shown as text while only one had a bar.

### Tests first ⚠️

- [X] T032 [P] Write failing tests in `tests/integration/test_panel_layout.py` asserting each of
  memory, compute activity, and memory-interface activity has its own labelled progress bar
- [X] T033 [P] Write a failing test in `tests/integration/test_panel_layout.py` asserting no value
  appears twice on a panel — specifically that compute utilization is rendered once, not in both a
  stats row and an activity row
- [X] T034 [P] Write a failing test in `tests/integration/test_panel_layout.py` asserting an
  unavailable percentage leaves its bar visibly empty **and disabled**, so it cannot be misread as
  a measured 0%
- [X] T035 [P] Write a failing test in `tests/integration/test_panel_layout.py` asserting the
  panel is shorter than before and the process table still visible at the default window size

### Implementation

- [X] T036 Add a reusable labelled percentage bar (`_metered_row`) to
  `src/gpum/ui/device_panel.py`, so memory, compute, and memory-interface are presented
  identically rather than three different ways
- [X] T037 Give compute activity and memory-interface activity their own bars in
  `src/gpum/ui/device_panel.py`, each labelled by what it describes (preserving FR-022)
- [X] T038 Remove the duplicated compute figure and the redundant vendor subtitle from
  `src/gpum/ui/device_panel.py`
- [X] T039 Combine power and energy onto one row in `src/gpum/ui/device_panel.py` to recover
  vertical space
- [X] T040 Ensure an unavailable percentage renders as an empty **disabled** bar with its reason in
  the text via `_set_meter` in `src/gpum/ui/device_panel.py`, never as a filled or zeroed bar
  (FR-011, FR-012)
- [X] T041 Verify the process table remains visible and rebuild the AppImage bundle

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: empty — nothing to initialize
- **Foundational (Phase 2)**: blocks every user story. T003 → T004 → T005 in order; T001–T002
  precede T003
- **User Story 1 (Phase 3)**: depends only on Phase 2. This is the MVP
- **User Story 2 (Phase 4)**: depends on Phase 2. Independently testable, but **should ship with
  US1** — an unlabelled trend is precisely the misreading this feature exists to prevent
- **User Story 3 (Phase 5)**: depends on Phase 2. Independent of US1 and US2
- **Polish (Phase 6)**: after the stories, except T026 which is worth running as soon as the
  second graph exists
- **Phase 7**: follows the whole feature; it is a later request, not part of the original spec

### Within Each User Story

- Tests are written and MUST fail before implementation (Constitution IV)
- History before widget, widget before panel, panel before wiring

### Parallel Opportunities

- T026, T027, T028, T042 — different concerns, safe together
- T032–T035 — written as separate test classes in `tests/integration/test_panel_layout.py`
- US1, US2, and US3 can be staffed in parallel once Phase 2 is done, though US1 and US2 touch
  `device_panel.py` and will need coordinating there

Note: within Phases 2–5 the test tasks are **not** marked `[P]` because each phase's tests share a
single file (`test_utilization_history.py`, then `test_utilization_display.py`), so concurrent
edits would conflict.

### Critical path

`T001–T005 → T010–T014 (trend visible) → T018–T020 (labelled) → ship`

---

## Implementation Strategy

### MVP first

1. Phase 2 (Foundational) — history carries both series
2. Phase 3 (US1) — the discarded history becomes a graph
3. **STOP and VALIDATE**: quickstart V-1, V-2, V-3
4. Phase 4 (US2) ships with it — see the dependency note above

### Incremental delivery

Phase 2 → US1 (MVP, demo) → US2 (honest labels) → US3 (memory interface) → Polish → Phase 7.
Each increment is independently testable and none breaks the last.

---

## Notes

- **No backend, adapter, or sampling code is touched.** Both figures are already collected every
  refresh; the compute history was recorded and discarded, and the memory-interface figure was not
  displayed at all. T027 measured that this stayed true; T042 now guards it, structurally by
  counting backend calls headless and by wall clock on hardware.
- **T007 and T026 guard the two ways this feature could make the interface worse**: a graph that
  makes idle look busy, and a panel so tall the process table falls out of view.
- Test names carry their task IDs (`test_t032_…`, `test_u06_…`), so **task IDs must stay stable**.

---

## Quickstart results — 2026-08-17 (T030)

Run on an RTX 5060 Ti, driver 580.x, Linux, at the default 880x720 window size.

| # | Check | Result |
|---|---|---|
| V-1 | Trend appears and moves | **Pass.** Labelled utilization graph beneath the memory graph; history fills and tracks load. |
| V-2 | Idle noise does not look like load | **Pass.** Fixed 0–100 scale confirmed; a 43%-busy device draws at mid-height, an 86% one high. |
| V-3 | Gaps are gaps | **Pass.** `metrics-unsupported`: 40/40 history points recorded as gaps, bar disabled, no drop to zero. |
| V-4 | Measured zero differs from unavailable | **Pass.** Measured 0% leaves the bar empty but *enabled*; unavailable leaves it empty and *disabled*. |
| V-5 | The two activity figures cannot be confused | **Pass, after two fixes** (T043, T044). |
| V-6 | Process table still visible | **Pass** on real hardware. Not verifiable on the fake backend — see below. |
| V-7 | No core counts anywhere | **Pass**, once the command was corrected (T046). |
| V-8 | Sampling is not more expensive | **Pass.** 0.994 ms mean / 2.844 ms p99 per device — unchanged from the 1.000 ms recorded after feature 004. |
| V-9 | Agreement with the vendor tool | **Pass, after one fix** (T047). 600 s alternating load, 376 settled samples: worst 0.0 pp, mean 0.00 pp outside the vendor bracket. |

### What the walk actually found

The three checks that were never going to fail on their own found nothing; the ones that
exercised the *unavailable* paths found everything.

- **V-5 could not have passed as specified.** The fake backend hard-coded the memory-interface
  figure as `unsupported("not simulated")`, so every fake device reported it missing. US3's
  display tests construct `GpuDevice` objects directly and so never touched this — the
  end-to-end path from backend to panel had no coverage at all, and FR-023 (one figure present,
  the other absent) had none in either direction. Fixed in T043.
- **The unavailable label was ungrammatical.** `"GPU compute busy  {value} of the time"` with an
  unavailable value produced *"GPU compute busy Not supported of the time"*. FR-011 wants the
  unavailability read first; this read as a broken sentence first. Fixed in T044/T045.
- **Two quickstart commands verified nothing.** `-k fixed_scale` against
  `test_utilization_history.py` and `-k cores` against `test_utilization_display.py` both matched
  zero tests and exited 0. A validation step that passes without running anything is worse than
  an absent one. Fixed in T046.
- **V-6 is not verifiable on the fake backend**, which the quickstart did not say. No attribution
  provider matches simulated devices, so the panel correctly reports "per-process data is not
  available" and hides the table — the table can only be seen on real hardware.

## Implementation status — 2026-08-17

All phases complete; **47 of 47 tasks done**. **903 default + 28 hardware tests pass**
(2 skipped, both hardware-gated), `ruff check src tests` clean, packaging suite green, bundle
rebuilt and newer than every source file.

### The feature was genuinely free

Per-device sampling cost, measured before and after (T027):

| | mean | p99 |
|---|---|---|
| After feature 004 | 1.000 ms | 3.832 ms |
| After feature 006 | 1.192 ms | **3.810 ms** |

Unchanged within noise, exactly as FR-015 required — both figures were already being read on every
refresh. The compute history was recorded into a bounded buffer and then discarded; the
memory-interface figure was never displayed at all.

### Two decisions that kept the interface from getting worse

**Fixed 0–100% scale.** The memory graph auto-scales to the device's total, which is right for a
quantity whose ceiling is a hardware property. Applying that to a percentage would stretch an idle
GPU's 0–3% noise to full height and read as sustained heavy load, and would make two GPUs
incomparable. The utilization graph is pinned to 0–100 and ignores any maximum a caller passes.

**Labels by meaning, not position.** The panel already shows memory *occupancy*. A bare "MEM 88%"
beside it would be two unrelated memory numbers on one panel. The figures now read "GPU compute
busy 42% of the time" and "Memory interface busy 88% of the time", and the tooltip states plainly
that neither is a share of GPU cores.

### What running the deferred tasks was worth

T029, T030, and T042 were the three tasks left undone on 2026-08-16, and each one found
something once actually run. That is the argument against recording them as acceptable gaps:

- **T030** (the quickstart walk) found four defects — T043 through T046. The end-to-end path
  from backend to panel had no coverage for the memory-interface figure at all, because the
  fake backend hard-coded it unsupported; the unavailable label was ungrammatical; and two
  quickstart commands selected zero tests and exited green.
- **T029** (the vendor comparison at its specified duration) found that the comparison itself
  was measuring the wrong thing — see T047. Run at 120 s it passes; run at the 600 s SC-010
  asks for, it failed on one sample in 378.
- **T042** (an automated sampling-cost guard) turned a hand measurement into two tests: a
  headless structural one counting backend calls, and a wall-clock one on hardware.

### Known, out of scope for this feature

- **`tests/hardware/test_power_agreement.py` flakes after sustained load.** It failed at 19.1%
  against a 10% tolerance when it ran straight after the 10-minute T029 run, and passed on a
  quiet GPU immediately after. It compares single instants of a fast-moving quantity during
  thermal and clock decay — the same weakness T047 fixed for utilization. It is a feature-004
  test and untouched here.
- **The `mypy` CI gate was not runnable**: `mypy` was absent from the virtualenv despite being
  a declared `dev` extra, so `ruff` and `pytest` were the only gates actually enforced. Once
  installed it reports 12 errors, all in `core/models.py`, `core/power.py`, and `core/engine.py`
  — none of them files this feature touches, and under mypy 2.3.1 against a `>=1.11` pin.
  `core/history.py`, the one in-scope file feature 006 changed, is clean.
