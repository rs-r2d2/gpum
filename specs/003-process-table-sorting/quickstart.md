# Quickstart & Validation: Process Table Column Sorting

**Feature**: 003-process-table-sorting | **Date**: 2026-08-16

No GPU required for any scenario — the fake backend provides multiple devices and processes.

## Run

```bash
python -m gpum --backend fake --scenario processes-churn   # rows appearing and disappearing
python -m gpum --backend fake --scenario multi-vendor-degraded   # several device tables
python -m gpum                                             # real hardware
```

## Validation scenarios

### V-1 — Click to sort *(the request)*

Click each of the four headers in turn.

**Expect**: rows reorder by that column, an arrow shows the direction, clicking again reverses
it, and clicking a different header moves the arrow. **The toolbar has no sort dropdown and no
Descending checkbox.**

### V-2 — Every column responds

**Expect**: all four columns sort. In particular the **User** column, which is inert today.
PID must order 9 before 100 — text ordering would put 100 first.

### V-3 — Missing values rank last *(critical)*

```bash
pytest tests/unit/test_sort_comparisons.py -k unavailable
python -m gpum --backend fake --scenario no-attribution
```

**Expect**: rows with an unresolved name, restricted user, or unreadable memory appear **last in
both directions**. **Fail condition**: a missing value sorting as though it were zero or an empty
string — that ranks an absence as though it had been measured.

### V-4 — The table does not reshuffle *(critical)*

```bash
python -m gpum --backend fake --scenario processes-churn
```

Sort by user (many rows share a value) and watch for 60 seconds.

**Expect**: equal-valued rows hold position. **Fail condition**: rows swapping every refresh —
at 1 Hz that makes the table impossible to click.

### V-5 — Tables are independent

```bash
python -m gpum --backend fake --scenario multi-vendor-degraded
```

Sort one device's table by name and another by memory.

**Expect**: each keeps its own order and its own arrow; neither disturbs the other.

### V-6 — Arrangements survive a restart

Sort several tables differently, quit, relaunch.

**Expect**: every table restored, each to its own order.

### V-7 — Broken saved state degrades gracefully

Corrupt the saved sort map by hand, then launch.

**Expect**: every table shows the default order and the application starts normally. A
user-editable preferences file must not be able to break the interface.

### V-8 — Sorting changes nothing measured

**Expect**: device totals and the set of processes shown are identical before and after sorting.

## Suite

```bash
pytest                 # all of this feature is covered here; no GPU needed
```
