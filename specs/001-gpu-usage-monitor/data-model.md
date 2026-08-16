# Phase 1 Data Model: GPU Usage Monitor

**Feature**: 001-gpu-usage-monitor | **Date**: 2026-08-16

All types live in `src/gpum/core/models.py` unless noted. They are **immutable** frozen
dataclasses: a snapshot is produced on the sampler thread and read on the GUI thread, and
immutability is what makes that handoff safe without locks.

Nothing here imports Qt, `pynvml`, or any OS-specific module.

---

## `Availability` (enum)

The load-bearing type of the whole design. FR-017 and SC-007 forbid ever presenting a
non-measurement as a measurement, so **no metric is a bare number** — every one carries the
reason it is or isn't real.

| Value | Meaning | UI treatment |
|-------|---------|--------------|
| `AVAILABLE` | Real measurement from this sample | Show the value |
| `UNSUPPORTED` | Vendor/platform cannot report this metric at all | "Not supported" + short reason |
| `PERMISSION_DENIED` | Obtainable, but not at this privilege level (FR-019) | "Requires elevated privileges" |
| `STALE` | Last query timed out; the value shown is from an earlier sample | Last value, visibly marked stale + its age |
| `DEGRADED` | Repeated timeouts; querying has been backed off (FR-014) | "Not responding" |
| `NOT_APPLICABLE` | Metric is meaningless for this device (e.g. a MIG-partitioned card) | Suppress the field |

**Rule**: there is no `UNKNOWN` and no zero-default. A metric that cannot be measured has a state
naming *why*, and `ui/availability.py` is the single place that decides how each state renders —
so "unavailable" can never leak to screen as `0`.

---

## `MetricValue`

A single measured quantity plus its provenance.

| Field | Type | Notes |
|-------|------|-------|
| `value` | `int \| float \| None` | `None` whenever `availability != AVAILABLE` |
| `availability` | `Availability` | Required |
| `reason` | `str \| None` | Short human-readable explanation; required when not `AVAILABLE` |
| `sampled_at` | `datetime \| None` | When this value was actually measured — satisfies FR-016 and lets a `STALE` value show its true age rather than the snapshot's time |

**Validation**: `value is None` if and only if `availability != AVAILABLE`. Enforced in
`__post_init__` — this invariant is the mechanical guarantee behind SC-007.

Memory values are always **bytes** internally. Formatting to a display unit happens once, in
`core/units.py`, which also owns the single unit convention FR-004 requires the UI to state.

---

## `DeviceId`

Stable device identity that survives refreshes, driver restarts, and hot-plug (D-07).

| Field | Type | Notes |
|-------|------|-------|
| `vendor` | `Vendor` enum — `NVIDIA \| AMD \| INTEL \| UNKNOWN` | |
| `key` | `str` | UUID where available, else PCI bus ID, else `vendor:index`. Opaque to `core` |
| `index` | `int` | Enumeration position — display and ordering only, **never** identity |

**Why**: an index is not identity. After a driver restart or eGPU disconnect the same index can
denote a different physical card, which would splice two devices' histories together. History
buffers are keyed on `DeviceId.key` alone.

---

## `GpuDevice`

One whole physical GPU. Per FR-027, partitions are never separate devices.

| Field | Type | Notes |
|-------|------|-------|
| `id` | `DeviceId` | |
| `name` | `str` | Model name |
| `vendor_name` | `str` | Display string |
| `supported` | `bool` | `False` for MIG/vGPU devices (FR-028) |
| `unsupported_reason` | `str \| None` | Required when `supported` is `False` |
| `memory_total` | `MetricValue` | Bytes |
| `memory_used` | `MetricValue` | Bytes |
| `utilization_gpu` | `MetricValue` | Percent |
| `utilization_memory` | `MetricValue` | Percent |
| `attribution` | `Availability` | Whether per-process data exists **for this device** — drives the FR-006/US2-4 "unavailable, and here's why" message instead of an empty list |

**Derived, not stored**: memory-used percentage (FR-002) is computed at render time, and is only
computed when both operands are `AVAILABLE`.

**Disambiguation**: when two devices share a `name`, the UI appends `index` (FR-002, edge case
"two identical GPU models").

---

## `GpuProcess`

One process consuming one device. A process using two GPUs produces two records.

| Field | Type | Notes |
|-------|------|-------|
| `pid` | `int` | Host-namespace PID |
| `started_at` | `datetime \| None` | Part of identity — PIDs are recycled (D-05) |
| `name` | `str \| None` | `None` when unresolved |
| `executable` | `str \| None` | |
| `username` | `str \| None` | |
| `device_key` | `str` | The `DeviceId.key` this usage is attributed to (FR-007) |
| `memory_used` | `MetricValue` | Bytes; `UNSUPPORTED` on NVIDIA/WDDM (D-03) |
| `utilization` | `MetricValue` | Best-effort; frequently `UNSUPPORTED` |
| `identity_state` | `ProcessIdentity` | See below |
| `container_id` | `str \| None` | Truncated container ID where resolvable (FR-030) |

### `ProcessIdentity` (enum)

| Value | Meaning | FR |
|-------|---------|-----|
| `RESOLVED` | Full identity obtained | FR-006 |
| `RESTRICTED` | Exists, but not inspectable at this privilege level — still counted in totals | FR-009 |
| `CONTAINERIZED` | Resolved, and known to belong to a container | FR-029, FR-030 |
| `UNRESOLVED` | Cannot be identified at all; memory still counts toward device totals | FR-031 |

**Rule**: a process is *never* dropped for being unidentifiable. Dropping it would understate
GPU use, which is the failure FR-031 and SC-012 exist to prevent.

**Stable identity** for sort stability (FR-010) and add/remove correctness (FR-008) is
`(device_key, pid, started_at)` — not `pid` alone.

---

## `Snapshot`

The single immutable object crossing the thread boundary from sampler to UI.

| Field | Type | Notes |
|-------|------|-------|
| `taken_at` | `datetime` | |
| `devices` | `tuple[GpuDevice, ...]` | Empty tuple is valid and normal (FR-018) |
| `processes` | `tuple[GpuProcess, ...]` | Flat; the UI groups by `device_key` |
| `discovery` | `DiscoveryReport` | What was searched for and what was found |
| `sequence` | `int` | Monotonic; lets the UI discard an out-of-order delivery |

Tuples rather than lists so the object cannot be mutated after it crosses threads.

---

## `DiscoveryReport`

Powers FR-018 and SC-006: on a machine with no GPU the tool must explain itself rather than show
a blank window. This type is what makes that message concrete instead of generic.

| Field | Type | Notes |
|-------|------|-------|
| `backends_attempted` | `tuple[BackendReport, ...]` | One per registered backend, stubs included |
| `attribution_source` | `str \| None` | Which adapter supplied process data, if any |

### `BackendReport`

| Field | Type | Notes |
|-------|------|-------|
| `vendor` | `Vendor` | |
| `state` | `BackendState` — `ACTIVE \| NO_DEVICES \| DRIVER_MISSING \| LIBRARY_MISSING \| NOT_IMPLEMENTED \| ERROR` | `NOT_IMPLEMENTED` is what the AMD/Intel stubs return this release |
| `detail` | `str` | User-facing sentence, e.g. "NVIDIA driver not loaded" |
| `device_count` | `int` | |

---

## `DeviceHistory` (`core/history.py`)

Bounded recent trend per device (FR-005), with the memory bound structural rather than
maintained (FR-024, SC-005).

| Field | Type | Notes |
|-------|------|-------|
| `device_key` | `str` | |
| `memory_used` | `deque[HistoryPoint]` | `maxlen` fixed at construction |
| `utilization` | `deque[HistoryPoint]` | `maxlen` fixed at construction |

`HistoryPoint` is `(timestamp, value: float \| None, availability)`. Retaining availability lets
an unavailable stretch render as a **gap** in the sparkline rather than as a drop to zero — the
same honesty rule as everywhere else.

`maxlen` derives from retention window ÷ interval and is recomputed when the interval changes.
Capacity never grows unbounded regardless of uptime.

---

## `Preferences` (`core/preferences.py`)

Plain dataclass, deliberately Qt-free so `core` stays testable without a Qt application
(constitution tech constraints). Persistence is `ui/preferences_store.py`'s job via `QSettings`.

| Field | Type | Default | FR |
|-------|------|---------|-----|
| `refresh_interval_ms` | `int` | `1000` | FR-011, FR-012 |
| `paused` | `bool` | `False` | FR-012 |
| `sort_column` | `ProcessSortColumn` | `MEMORY_USED` | FR-010 |
| `sort_descending` | `bool` | `True` | FR-010 |
| `history_window_s` | `int` | `300` | FR-005 |
| `throttle_when_hidden` | `bool` | `True` | FR-015 |
| `window_geometry` | `bytes \| None` | `None` | FR-023 |

**Validation**: `refresh_interval_ms` clamped to `[100, 60000]`. The floor stops a user from
configuring the tool into consuming the resources it is meant to measure.

---

## State transitions

**Device availability**, per device per metric:

```
AVAILABLE ──timeout──> STALE ──repeated timeouts──> DEGRADED
    ^                    │                              │
    └────────────────────┴──────success─────────────────┘
```

`DEGRADED` backs off the query cadence for that device only; every other device keeps its normal
interval (FR-014). Recovery is automatic on any success — no restart, no user action.

**Process lifecycle** across samples: absent → present (FR-008, appears within two intervals);
present → absent (removed cleanly, no stale row, no error dialog); `RESOLVED` → `UNRESOLVED` is
possible mid-run when a process exits between the GPU query and the identity lookup, and is
expected rather than exceptional (D-05).

**Device set**, on re-enumeration (FR-020, every ~10 cycles per D-08): a new `DeviceId.key`
appears with empty history; a vanished key is removed along with its history buffers; a *returning*
key resumes with its prior history intact, which is exactly what keying on UUID rather than index
buys.
