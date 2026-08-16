# Contract: Table sorting

**Modules**: `src/gpum/ui/process_model.py`, `src/gpum/ui/device_panel.py`,
`src/gpum/ui/preferences_store.py` | **Feature**: 003-process-table-sorting

---

## Model obligations

**MUST**:
- Sort by any of the four displayed columns, in either direction.
- Rank rows whose value is unavailable **last in both directions** — never as zero, and never as
  an empty string.
- Keep equal-valued rows in a fixed relative order across refreshes, tie-broken on process
  identity.
- Sort PID numerically and memory by quantity, never by their formatted text.
- Preserve the existing in-place update path, so a refresh does not rebuild the model and reset
  scroll position or selection.

**MUST NOT**:
- Change which rows are present. Sorting is presentation only (FR-022).
- Alter any displayed value.
- Perform any I/O or sampling.

## Panel obligations

**MUST**: own its sort state; apply the saved order for its device on first display, falling back
to the default; report changes upward for persistence.

**MUST NOT**: read or write another panel's sort state. There must be no path between panels —
that absence is what makes independence structural rather than merely tested.

## Persistence obligations

**MUST**: round-trip the per-device map; fall back to the default order for a missing entry, an
unknown column, a malformed entry, or an unreadable map; leave the rest of the preferences intact
when the map alone is corrupt.

**MUST NOT**: prune entries (an accepted, recorded decision); fail to display a table because a
saved value was unusable.

## Contract tests

| # | Assertion | Enforces |
|---|-----------|----------|
| S-01 | Each of the four columns sorts correctly in both directions | FR-006 |
| S-02 | PID sorts numerically — 9 before 100 | FR-007 |
| S-03 | Memory sorts by quantity, not formatted text | FR-008 |
| S-04 | Name and user sort case-insensitively | FR-009 |
| S-05 | **Rows with unavailable values sort last in *both* directions** | **FR-010** |
| S-06 | **Equal-valued rows never change relative order across 20 refreshes** | **FR-012** |
| S-07 | A refresh preserves the active column and direction | FR-011 |
| S-08 | Sorting one device's table leaves every other table's order untouched | **FR-015** |
| S-09 | A newly appearing device uses the default order | FR-016 |
| S-10 | Per-device orders round-trip across a restart | FR-017 |
| S-11 | A reconnected device resumes its own saved order | FR-018 |
| S-12 | Missing / unknown-column / malformed / unreadable saved state falls back to default | FR-019 – FR-021 |
| S-13 | The toolbar sort dropdown and Descending checkbox no longer exist | FR-005 |
| S-14 | Sorting changes no device total and no set of displayed processes | **FR-022** |
| S-15 | Re-sorting 500 rows stays inside the GUI-thread budget | FR-024, Principle III |

S-05 and S-06 are the two that guard behaviour the code already has and could lose silently.
