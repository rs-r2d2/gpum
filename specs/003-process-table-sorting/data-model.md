# Phase 1 Data Model: Process Table Column Sorting

**Feature**: 003-process-table-sorting | **Date**: 2026-08-16

Small additions. No new types beyond a preference field and one enum value.

---

## `ProcessSortColumn` (`core/models.py`)

| Value | Status | Comparison |
|-------|--------|-----------|
| `NAME` | existing | Case-insensitive alphabetical |
| `PID` | existing | Numeric |
| `MEMORY_USED` | existing | By byte quantity |
| `USER` | **new** | Case-insensitive alphabetical |

`USER` is the whole reason the enum changes: the column is displayed today but absent from the
enum, so it cannot be sorted (FR-006).

---

## `Preferences` additions (`core/preferences.py`)

| Field | Type | Notes |
|-------|------|-------|
| `device_sort_orders` | `dict[str, tuple[ProcessSortColumn, bool]]` | Device key → (column, descending) |

**Keyed on `DeviceId.key`** — the UUID-first identifier already used for device history — so a
GPU that is disconnected and reconnected resumes its own arrangement (FR-018) without a second
identity scheme.

**Existing fields change role rather than disappearing.** `sort_column` and `sort_descending`
were written by the toolbar controls being removed. They become the **default** applied to any
device with no saved entry (FR-019), so a user's existing preference carries forward instead of
being discarded.

**Never pruned**, by explicit decision (spec Assumptions). One entry per GPU ever seen, retained
indefinitely.

**Validation on load** — a preferences file is user-editable and must not be able to break the
interface:

| Input | Result |
|-------|--------|
| Missing entry for a device | Default order |
| Unparseable map | Default order for everything, rest of preferences intact |
| Entry names an unknown column | Default order for that device |
| Entry has the wrong shape | Ignored, default order |

---

## Sort state, per table

Each device panel holds the column and direction currently applied to its own table. There is
deliberately **no shared object** — the panels do not know about each other, which is what makes
FR-015 structurally true rather than merely tested (research D-02).

**Lifecycle**: on first display a panel takes its order from the saved map, or the default. On
user change it updates its own state and reports it upward for persistence. A device that
disappears keeps its saved entry.

---

## Comparison rules

Every column sorts on a key of the form `(has_value, value, tiebreak)`.

**`has_value` comes first, always.** Rows without a real value rank last in both directions
(FR-010). Sorting a missing figure as zero, or a missing name as an empty string, would rank it
as though it had been measured — the same error as rendering an unavailable metric as `0`.

**`tiebreak` is `(pid, started_at)`**, fixed and unchanging. Equal-valued rows therefore hold
position across refreshes (FR-012), which at a 1 Hz cadence is the difference between a usable
table and one whose rows move as you reach for them.
