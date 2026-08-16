# Pre-Spec Clarifications: Process Table Sorting

**Captured**: 2026-08-16 via `/speckit-clarify`
**Status**: Decisions recorded; no spec written yet. Feed these into `/speckit-specify`.

## Why this is not part of feature 002

Feature 002 (Linux + NVIDIA release readiness) is complete and explicitly scoped to
installation, hardware verification, resilience, and tray presence. Its Assumptions section
states it adds no new capability. Column sorting is a user-facing behaviour change and belongs
in its own feature, extending feature 001's FR-010.

## Starting point — what already exists

Feature 001 FR-010 delivered partial sorting, implemented in
`src/gpum/ui/process_model.py` and `src/gpum/ui/main_window.py`:

- Sortable by Process name, PID, and GPU memory — via a **toolbar dropdown** plus a
  "Descending" checkbox, not by clicking column headers.
- The **User** column is displayed but is absent from `ProcessSortColumn`, so it cannot be
  sorted at all.
- Sort is **global**: the dropdown applies the same order to every device table at once.
- Ordering is already stable across refreshes, tie-broken on `(device_key, pid, started_at)`
  so equal values never reshuffle under the cursor.
- Rows whose GPU memory is not a real measurement already sort **last regardless of
  direction**, rather than being treated as zero.

## Session 2026-08-16

- Q: Should clicking a column header become the way to sort, and if so does the existing
  toolbar dropdown stay or go? → A: **B** — header-click sorting with a visible sort-direction
  arrow; remove the toolbar dropdown and the Descending checkbox.
- Q: When you have more than one GPU, should sorting a column in one device's table also
  re-sort the other tables, or should each table sort independently? → A: **B** — each table
  sorts independently.
- Q: When a GPU disappears and comes back — or the app is restarted — what sort order should
  its table use? → A: **A** — remember per-device sort indefinitely, saved per GPU UUID, with
  no pruning.

## Resolved decisions

1. **Interaction**: sorting is performed by clicking a column header. The active column shows a
   direction arrow. Clicking the active column reverses direction. The toolbar sort dropdown
   and Descending checkbox are removed — one control, not two competing ones.
2. **Sortable columns**: all four displayed columns — Process, PID, User, GPU memory. `User`
   must be added to `ProcessSortColumn`, which currently has only NAME, PID, MEMORY_USED.
3. **Scope**: each device's table sorts independently. Sorting one table must not alter any
   other table's order or arrow.
4. **Persistence**: per-device sort column and direction persist across restarts, keyed on the
   GPU's stable UUID (`DeviceId.key`), consistent with how device history is already keyed. A
   reconnected GPU resumes its previous order. No pruning — entries are retained indefinitely.

## Defaults applied without asking

- **New/unseen device**: defaults to GPU memory, descending — the current default, and the
  question users most often have.
- **Missing values sort last**, regardless of direction, extending the rule already applied to
  unmeasurable memory. Applies to unresolved process names and restricted/absent usernames, so
  rows lacking data never masquerade as alphabetically first.
- **Stability preserved**: the existing `(device_key, pid, started_at)` tiebreak stays, so rows
  do not reshuffle between refreshes at a 1 Hz cadence.
- **Sorting stays a view concern**: it must not alter sampling, device totals, or which
  processes are shown.

## Flagged consequence of decision 4

Unbounded per-GPU sort state was chosen over the pruned alternative. The saved settings file
will retain an entry for every GPU the machine has ever had, including hardware long since
removed. Each entry is small (a column name and a direction), so the practical cost is low, but
it grows monotonically and never self-cleans. Worth revisiting if the settings file is ever
used for something size-sensitive.

## Suggested next step

```
/speckit-specify Add click-to-sort column headers to the GPU process table, per-device and persisted
```
