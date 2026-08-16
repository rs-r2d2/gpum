---

description: "Task list for 003-process-table-sorting"
---

# Tasks: Process Table Column Sorting

**Input**: Design documents from `/specs/003-process-table-sorting/`

**Tests**: Mandatory — constitution Principle IV requires tests written and failing first.

**Scope**: UI layer plus two small `core` additions. No sampling, measurement, or vendor change.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Foundational (Blocking)

### Tests first

- [X] T001 [P] Write failing tests in `tests/unit/test_sort_comparisons.py` for `ProcessSortColumn.USER` existing and for each column's comparison rule (S-01 – S-04)
- [X] T002 [P] Write failing tests in `tests/unit/test_sort_persistence.py` for the per-device map round-trip and for every malformed-input fallback (S-12)

### Implementation

- [X] T003 Add `USER` to `ProcessSortColumn` in `src/gpum/core/models.py` — the column is displayed today but absent from the enum, which is why it cannot be sorted
- [X] T004 Add `device_sort_orders` to `Preferences` in `src/gpum/core/preferences.py`, keyed on `DeviceId.key`, with `sort_column`/`sort_descending` retained as the default for unseen devices
- [X] T005 Persist and restore the map in `src/gpum/ui/preferences_store.py`, falling back to the default order on a missing entry, an unknown column, a malformed entry, or an unreadable map — a user-editable file must not be able to break the interface

**Checkpoint**: `pytest` green; no behaviour change yet.

---

## Phase 2: User Story 1 + 2 — Header sorting, all columns (Priority: P1) 🎯 MVP

### Tests first

- [X] T006 [P] [US1] Write failing tests in `tests/integration/test_header_sorting.py` for click-to-sort, click-again-to-reverse, and the indicator moving between columns (S-01)
- [X] T007 [P] [US1] Write a failing test asserting the toolbar sort dropdown and Descending checkbox no longer exist (S-13)
- [X] T008 [P] [US2] Write failing tests asserting **rows with unavailable values sort last in both directions** across all four columns (S-05) — a missing value must never rank as though it were measured
- [X] T009 [P] [US2] Write a failing test refreshing a table of equal-valued rows 20 times and asserting the order never changes (S-06)
- [X] T010 [P] [US1] Write a failing test asserting a refresh preserves the active column and direction, and does not reset scroll position (S-07)

### Implementation

- [X] T011 [US2] Implement one comparison per column in `src/gpum/ui/process_model.py`, keyed as `(has_value, value, tiebreak)` so unavailable rows rank last in both directions
- [X] T012 [US2] Sort PID numerically and memory by byte quantity, never by formatted text
- [X] T013 [US2] Carry the existing `(pid, started_at)` tiebreak into every comparison so equal-valued rows hold position across refreshes
- [X] T014 [US1] Implement the model's `sort()` entry point in `src/gpum/ui/process_model.py` so the view's built-in header sorting drives it, giving the indicator and click-to-reverse without hand-rolling them
- [X] T015 [US1] Enable header sorting on the table in `src/gpum/ui/device_panel.py` and show the direction indicator
- [X] T016 [US1] Preserve the existing in-place update path so a refresh does not rebuild the model and reset scroll position or selection
- [X] T017 [US1] Remove the sort dropdown and Descending checkbox from `src/gpum/ui/main_window.py`, along with the loop that pushed one order into every panel

**Checkpoint**: headers sort, all four columns work, nothing reshuffles. This is the MVP.

---

## Phase 3: User Story 3 — Per-device independence (Priority: P2)

### Tests first

- [X] T018 [P] [US3] Write a failing test asserting sorting one device's table leaves every other table's order and indicator untouched (S-08)
- [X] T019 [P] [US3] Write a failing test asserting a newly appearing device uses the default order rather than inheriting another's (S-09)

### Implementation

- [X] T020 [US3] Hold sort state per panel in `src/gpum/ui/device_panel.py`, with no path between panels — independence should be structural, not merely tested
- [X] T021 [US3] Apply the saved order for a device on first display, falling back to the default

---

## Phase 4: User Story 4 — Persistence (Priority: P2)

### Tests first

- [X] T022 [P] [US4] Write failing tests asserting per-device orders round-trip across a simulated restart (S-10)
- [X] T023 [P] [US4] Write a failing test asserting a device that disappears and returns resumes its own saved order (S-11)

### Implementation

- [X] T024 [US4] Emit sort changes from `src/gpum/ui/device_panel.py` up to `src/gpum/ui/main_window.py` for storage in the per-device map
- [X] T025 [US4] Save the map with the other preferences on exit and restore it on launch
- [X] T026 [US4] Retain a saved entry for a device that is not currently present, so a reconnected GPU resumes its arrangement

---

## Phase 5: Polish

- [X] T027 [P] Write a test asserting sorting changes no device total and no set of displayed processes (S-14)
- [X] T028 [P] Write a test asserting a 500-row table re-sorts inside the GUI-thread budget (S-15)
- [X] T029 Run quickstart V-1 through V-8 and record results
- [X] T030 Rebuild the bundle so the shipped artifact carries the new interaction

---

## Dependencies

- **Phase 1** blocks everything.
- **Phase 2** is the MVP; US3 and US4 build on the per-panel state it establishes.
- **Phase 3 and 4** are independent of each other.
- **Polish** last.

### Critical path

`T001–T005 → T011–T017 (headers sort) → T020–T021 (independent) → T024–T026 (persisted) → ship`

### Parallel opportunities

T001–T002, T006–T010, T018–T019, T022–T023, T027–T028.

---

## Notes

- **T008 and T009 guard behaviour the code already has.** The current model already ranks
  unmeasurable memory last and already keeps equal rows stable. Routing sorting through a new
  entry point is exactly how such properties vanish unnoticed, which is why they are tested
  directly rather than assumed.
- The whole feature runs headless. No GPU is needed for any task.


---

## Implementation status — 2026-08-16

**All 30 tasks complete. 852 default + 21 hardware tests pass, lint clean.** Bundle rebuilt.

### Verified on real hardware

Sorting the live process table on the RTX 5060 Ti:

| Sort | Result |
|---|---|
| PID ascending | 3099, 3306, 6716, 7334, 7369, 20872, 57436 — numeric, so 20872 follows 7369 |
| Name ascending | cef_server, cef_server, chrome, claude-desktop, gnome-shell, nautilus, Xorg — case-insensitive |
| Memory descending | 224, 126, 109, 46, 30, 13, 2 MiB — by quantity |

The order is saved per device and restored on the next launch. The toolbar no longer carries a
sort dropdown or a Descending checkbox.

### The bug the tests caught

Ascending sorts failed first time — the previous implementation ranked rows with **no** value
*first* when ascending, because a sentinel key flips with the sort direction. An unreadable
memory figure was sorting as though it were the smallest measured one.

Fixed by partitioning unavailable rows out and appending them, so "last" means last in both
directions rather than last-in-this-direction (FR-010).

### Per-device independence came for free

Today's global behaviour was not inherent — it existed only because one toolbar control looped
over every panel pushing the same order into each. Deleting that loop left each table
independent by construction. There is now **no path between panels**, which makes FR-015
structurally true rather than merely tested.

### Notes

- The sort indicator was checked against the model in both the user-click and restore-from-
  preferences paths. The arrow glyph points up for descending in this desktop theme; the
  underlying state is correct in both directions.
- `sort_column` / `sort_descending` were not deleted with the toolbar. They are now the default
  applied to any device with no saved entry, so an existing user's preference carries forward.
- Saved sort state accumulates one entry per GPU ever seen and is never pruned — the accepted
  decision from clarification, recorded in the spec's Assumptions.


---

## Defect fixed after implementation — 2026-08-16

**Reported**: "if i sort by gpu memory usage then process name is not changing, vice versa."

**Reproduced only against realistic data.** Six earlier checks — model logic, programmatic sort,
simulated header clicks, live refreshes, real GPU data, and the painted pixels — all passed,
because the test data happened to make different orderings coincide.

**Cause**: a newly-clicked column always started ascending, which is the toolkit default. So
clicking "GPU memory" showed the *smallest* consumers first. On a real process list that
ordering begins and ends with the same processes as the name sort:

```
Memory ascending : cef_server(2), nautilus(13), gnome-shell(34) ... chrome(147), Xorg(222)
Name   ascending : cef_server, cef_server, chrome ... nautilus, Xorg
```

Same first row, same last row. The table looked unchanged, so the click looked broken — and the
order shown was the opposite of the one anyone wants from a memory column.

**Fix**: a first click on a column now picks a sensible direction — descending for GPU memory,
ascending for the text and identifier columns. Clicking the column that is already active still
toggles, unchanged. The header indicator is re-synced from the model, so the arrow can never
claim ascending while the data is descending.

Recorded as **FR-001a**. Five regression tests added in `TestFirstClickDirection`, including one
that asserts the *first row* changes when switching columns — the user-visible symptom, which
none of the original tests checked.
