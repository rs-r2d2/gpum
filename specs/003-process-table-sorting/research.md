# Phase 0 Research: Process Table Column Sorting

**Feature**: 003-process-table-sorting | **Date**: 2026-08-16

---

## D-01: Where sorting happens

**Decision**: Implement `sort()` on the existing table model and enable the view's built-in
sorting, rather than intercepting header clicks and re-ordering by hand.

**Rationale**: The toolkit already provides the whole interaction — click to sort, click again
to reverse, a direction indicator in the header, and exactly one active column at a time
(FR-001 – FR-004). Hand-rolling it means reimplementing the indicator, the toggle, and the
single-column rule, each of which is a chance to get it subtly wrong.

**Consequence**: the model's existing ordering logic moves behind the standard sort entry point
rather than being replaced. The current stability guarantee and the "unmeasurable last" rule are
preserved by keeping the same comparison function (research D-03).

**Alternatives considered**: connecting to the header's click signal and calling the existing
`set_sort` — rejected because it leaves the indicator to be drawn manually and the
click-to-reverse behaviour to be tracked manually.

---

## D-02: Per-device independence comes for free

**Decision**: No coordination mechanism. Each device panel already owns its own table and its
own model instance.

**Rationale**: This is the finding that makes US3 nearly free. The global behaviour today is not
inherent — it exists only because a single toolbar control loops over every panel and pushes the
same order into each. Deleting that loop (FR-005) leaves each table independent by construction,
which is exactly FR-014 and FR-015.

**Consequence**: FR-015 ("sorting one table must not change another") cannot regress by
accident, because there is no longer any path between panels. The test asserts it anyway, since
a future "apply to all" convenience would reintroduce one.

---

## D-03: Comparison rules, and what must not regress

**Decision**: One comparison function per column, with a fixed identity tiebreak, preserving the
two behaviours the current implementation already gets right.

| Column | Comparison |
|--------|-----------|
| Process name | Case-insensitive alphabetical |
| PID | Numeric — 9 before 100, not "100" before "9" |
| User | Case-insensitive alphabetical |
| GPU memory | By byte quantity, never by formatted text |

**Two behaviours that must survive the change**:

1. **Unmeasurable values sort last in both directions** (FR-010). The existing model already
   does this for memory by keying on `(has_measurement, value)`. Sorting an unavailable figure
   as zero would rank it as though it had been measured — the same class of error as rendering
   it as `0` on screen. The rule now extends to missing names and usernames.
2. **Equal values keep a fixed relative order** (FR-012). The existing tiebreak is
   `(device_key, pid, started_at)`. At a 1 Hz refresh, a table that reshuffles equal rows every
   second is unusable — the user cannot click a row that keeps moving.

**Rationale for restating these as requirements**: both are currently emergent properties of one
function. Moving sorting behind a different entry point is exactly the kind of change that
silently drops them, so they are now tested directly rather than assumed.

---

## D-04: Persisting a per-device map

**Decision**: Store the per-GPU sort orders as a single serialized mapping from device key to
`(column, direction)`, written with the other preferences.

**Rationale**: FR-017/FR-018 require each GPU to resume its own arrangement, keyed on identity
that survives disconnection. The device key is already a stable UUID-first identifier chosen for
exactly this reason in feature 001, and device history is already keyed on it — so the same key
answers "which GPU is this" without inventing a second identity scheme.

**Growth, accepted knowingly**: the map is never pruned (spec Assumptions). One entry per GPU
the machine has ever had, retained forever. Each entry is a short column name and a boolean, so
the cost is negligible in practice — but it is monotonic, and the decision is recorded rather
than hidden.

**Robustness**: unreadable settings, a missing entry, or an entry naming a column that no longer
exists all fall back to the default order (FR-019 – FR-021) rather than failing to display a
table. A preferences file is user-editable; it must not be able to break the interface.

---

## D-05: Removing the toolbar controls

**Decision**: Delete the sort dropdown and the "Descending" checkbox outright rather than hiding
or deprecating them.

**Rationale**: FR-005. Two controls for one behaviour is the problem being solved; keeping a
disabled or hidden remnant preserves the confusion and the synchronisation burden. The persisted
`sort_column` and `sort_descending` preferences they wrote become the *default* for devices with
no saved entry (FR-019), so an existing user's chosen order is not discarded — it becomes the
starting point for every new table.

---

## No spikes required

Every mechanism here is already present in the codebase or provided by the toolkit. Nothing
needs measuring against hardware, and no behaviour depends on a driver.
