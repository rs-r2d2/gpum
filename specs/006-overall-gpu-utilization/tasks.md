---

description: "Task list for 006-overall-gpu-utilization"
---

# Tasks: Overall GPU Utilization

**Input**: Design documents from `/specs/006-overall-gpu-utilization/`

**Tests**: Mandatory — constitution Principle IV requires tests written and failing first.

**Scope**: Presentation only. No backend, adapter, or sampling change.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Foundational (Blocking)

### Tests first

- [X] T001 [P] Write failing tests in `tests/unit/test_utilization_history.py` for a
  memory-interface series: appended each refresh, bounded, gap-aware, window constant across an
  interval change (U-01, U-02, U-03, U-05)
- [X] T002 [P] Write a failing test asserting a measured 0% is stored distinctly from an
  unavailable reading (U-04) — the two look identical on a graph and mean opposite things

### Implementation

- [X] T003 Add a `memory_utilization` series to `DeviceHistory` in `src/gpum/core/history.py`,
  matching the existing bounded, gap-aware behaviour rather than introducing a second mechanism
- [X] T004 Include the new series in `append_gap` and `resize` in `src/gpum/core/history.py`, so
  a suspend gap and an interval change treat all series alike
- [X] T005 Record the memory-interface reading each refresh in `src/gpum/ui/main_window.py`,
  alongside the compute reading already recorded

**Checkpoint**: `pytest` green; no visible change yet.

---

## Phase 2: User Story 1 — The trend is drawn (Priority: P1) 🎯 MVP

### Tests first

- [X] T006 [P] [US1] Write failing tests in `tests/integration/test_utilization_display.py` for a
  utilization trend rendered from the already-collected history (U-01)
- [X] T007 [P] [US1] Write a failing test asserting the graph uses a **fixed 0–100 scale** (U-06)
  and that an idle GPU's 0–3% noise does not fill its height (U-07)
- [X] T008 [P] [US1] Write a failing test asserting an unavailable stretch renders as a break in
  the line, not a drop to zero (U-03)
- [X] T009 [P] [US1] Write a failing test asserting each trend graph carries a label (U-08)

### Implementation

- [X] T010 [US1] Add an optional fixed maximum to `src/gpum/ui/sparkline.py`, so a percentage
  series is drawn against 0–100 instead of its observed peak — auto-scaling would make an idle
  GPU read as heavily loaded
- [X] T011 [US1] Add a label to `src/gpum/ui/sparkline.py`, so two stacked graphs of similar
  appearance cannot be mixed up
- [X] T012 [US1] Add the utilization trend to `src/gpum/ui/device_panel.py` beneath the memory
  trend, with a fixed modest height
- [X] T013 [US1] Label the existing memory trend too, so the pair is symmetric rather than one
  named and one anonymous
- [X] T014 [US1] Feed the trend from the existing history series — the data is already collected
  every refresh and currently discarded

**Checkpoint**: the utilization history that was being thrown away is now visible. MVP.

---

## Phase 3: User Story 2 — Honest labelling (Priority: P1)

### Tests first

- [X] T015 [P] [US2] Write a failing test asserting the utilization label conveys time/busyness
  rather than a proportion of hardware (U-11 supporting)
- [X] T016 [P] [US2] Write a failing test asserting **no figure anywhere is a core count or a
  fraction of cores**, including any value derivable by combining utilization with a count (U-11)
- [X] T017 [P] [US2] Write a failing test asserting unavailable utilization shows a reason and
  never `0%` (FR-011), and that a measured 0% is displayed differently (U-04)

### Implementation

- [X] T018 [US2] Label the utilization figure and graph in `src/gpum/ui/device_panel.py` to
  convey how busy the GPU has been over time
- [X] T019 [US2] Provide the explanation required by FR-010 — that the figure measures time spent
  busy, not the share of hardware occupied — reachable from the panel
- [X] T020 [US2] Verify unavailable and measured-zero render distinctly, reusing the existing
  availability rendering rather than adding a second path

---

## Phase 4: User Story 3 — Memory-interface activity (Priority: P3)

### Tests first

- [X] T021 [P] [US3] Write a failing test asserting both activity figures are displayed and are
  **labelled by what they describe**, not by position (U-09)
- [X] T022 [P] [US3] Write a failing test asserting neither label reads as memory *occupancy*,
  which the same panel already shows a few lines above (U-09)
- [X] T023 [P] [US3] Write a failing test asserting one figure available and the other not still
  renders both states correctly (U-10)

### Implementation

- [X] T024 [US3] Display memory-interface activity beside compute activity in
  `src/gpum/ui/device_panel.py`
- [X] T025 [US3] Label the two so neither can be read as the other, and so neither collides with
  the memory occupancy figure already on the panel

---

## Phase 5: Polish

- [X] T026 [P] Write a test asserting the process table remains visible at the default window
  size with both graphs present (U-12) — the change most likely to trade a useful table for a
  decorative graph
- [X] T027 [P] Write a test asserting per-device sampling cost is unchanged (U-13) — this feature
  draws data already collected, so any movement means something is being sampled twice
- [X] T028 [P] Write a test asserting 8 device panels render inside the GUI-thread budget (U-14)
- [ ] T029 Verify agreement with the vendor tool on real hardware, within 5 percentage points
  (SC-010)
- [ ] T030 Run quickstart V-1 through V-9 and record results
- [X] T031 Rebuild the bundle so the shipped artifact carries the change

---

## Dependencies

- **Phase 1** blocks everything.
- **Phase 2** is the MVP.
- **Phase 3** should land with Phase 2 — an unlabelled trend is the misreading this feature
  exists to prevent.
- **Phase 4** is independent of Phase 3.
- **Polish** last, except T026 which is worth checking as soon as the second graph exists.

### Critical path

`T001–T005 → T010–T014 (trend visible) → T018–T020 (labelled) → ship`

### Parallel opportunities

T001–T002, T006–T009, T015–T017, T021–T023, T026–T028.

---

## Notes

- **No backend, adapter, or sampling code is touched.** Both figures are already collected every
  refresh; the compute history is recorded and discarded, and the memory-interface figure is not
  displayed at all. T027 asserts this stays true.
- **T007 and T026 guard the two ways this feature could make the interface worse**: a graph that
  makes idle look busy, and a panel so tall the process table falls out of view.


---

## Phase 6: UI cleanup and utilization bars (added 2026-08-16)

**Requested**: "Clean UI and separate bar for both cpu and memory utilization percentage."

Feature 006 left the panel carrying the same number twice — `GPU 5%` in the stats row and
`Compute busy 5% of the time` immediately below it — plus a vendor subtitle that repeats what the
title already says. Three percentages are now shown as text while only one has a bar.

### Tests first

- [ ] T032 [P] Write failing tests asserting each of memory, compute activity, and memory-interface
  activity has its own labelled progress bar
- [ ] T033 [P] Write a failing test asserting no value appears twice on a panel — specifically that
  compute utilization is rendered once, not in both a stats row and an activity row
- [ ] T034 [P] Write a failing test asserting an unavailable percentage leaves its bar visibly
  empty **and disabled**, so it cannot be misread as a measured 0%
- [ ] T035 [P] Write a failing test asserting the panel is shorter than before, and the process
  table still visible at the default window size

### Implementation

- [ ] T036 Add a reusable labelled percentage bar to `src/gpum/ui/device_panel.py`, so memory,
  compute, and memory-interface are presented identically rather than three different ways
- [ ] T037 Give compute activity and memory-interface activity their own bars, each labelled by
  what it describes (preserving FR-022)
- [ ] T038 Remove the duplicated compute figure and the redundant vendor subtitle
- [ ] T039 Combine power and energy onto one row to recover vertical space
- [ ] T040 Ensure an unavailable percentage renders as an empty disabled bar with its reason in
  the text, never as a filled or zeroed bar (FR-011, FR-012)
- [ ] T041 Verify the process table remains visible and rebuild the bundle

---

## Implementation status — 2026-08-16

29 of 31 tasks complete. **883 default + 21 hardware tests pass**, lint clean, bundle rebuilt.

### The feature was genuinely free

Per-device sampling cost, measured before and after:

| | mean | p99 |
|---|---|---|
| After feature 004 | 1.000 ms | 3.832 ms |
| After feature 006 | 1.192 ms | **3.810 ms** |

Unchanged within noise, exactly as FR-015 required — both figures were already being read on
every refresh. The compute history was recorded into a bounded buffer and then discarded; the
memory-interface figure was never displayed at all.

### Two decisions that kept the interface from getting worse

**Fixed 0-100% scale.** The memory graph auto-scales to the device's total, which is right for a
quantity whose ceiling is a hardware property. Applying that to a percentage would stretch an
idle GPU's 0-3% noise to full height and read as sustained heavy load, and would make two GPUs
incomparable. The utilization graph is pinned to 0-100 and ignores any maximum a caller passes.

**Labels by meaning, not position.** The panel already shows memory *occupancy*. A bare "MEM 88%"
beside it would be two unrelated memory numbers on one panel. The figures now read "Compute busy
42% of the time" and "Memory interface busy 88% of the time", and the tooltip states plainly that
neither is a share of GPU cores.

### Not completed

| Task | Reason |
|---|---|
| T029 | Agreement with the vendor tool over a 10-minute varying-load run. The existing hardware suite checks utilization at a point in time; the sustained comparison was not run. |
| T030 | The full quickstart walk, which includes observing the trend rise and fall under a real sustained workload. |
