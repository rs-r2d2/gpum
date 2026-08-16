# Phase 1 Data Model: Linux + NVIDIA Release Readiness

**Feature**: 002-linux-nvidia-release | **Date**: 2026-08-16

This feature adds no monitoring types. Feature 001's `MetricValue`, `GpuDevice`, `GpuProcess`,
`Snapshot`, and `Availability` are unchanged, and the rule that no metric is a bare number still
governs everything below.

What is added: types describing **how the tool was delivered**, **whether it can show a tray
icon**, and **what disrupted it**. Plus three new preference fields.

---

## `TrayAvailability` (`gpum/adapters/linux/tray_probe.py`)

The type that prevents FR-034's worst-case failure — a running program the user cannot see.

| Field | Type | Notes |
|-------|------|-------|
| `usable` | `bool` | Whether an icon will actually be displayed |
| `reason` | `str \| None` | Required when `usable` is `False`; shown in settings, not hidden |
| `watcher_present` | `bool` | A DBus owner exists for `org.kde.StatusNotifierWatcher` |
| `qt_reports_available` | `bool` | What `QSystemTrayIcon.isSystemTrayAvailable()` claims |
| `probe_error` | `str \| None` | Set when the DBus probe itself failed |

**Decision rule**: `usable = watcher_present and qt_reports_available`.

**Why both, and why the watcher dominates**: Qt's answer alone is the documented false positive on
stock GNOME — it reports `True` while the desktop silently drops the icon (research D-04). Qt's
answer is still required because a watcher can be registered while Qt's platform integration
cannot use it. The conjunction is the conservative choice, and conservative is correct here: a
false *negative* costs the user a tray icon they could have had, while a false *positive* costs
them a program they cannot recover.

**When the probe itself fails** (no session bus, DBus unreachable): `usable` is `False` with the
error as the reason. Unavailable-and-explained, never assumed-working — the same rule the metric
model follows.

---

## `DistributionForm` (`gpum/__init__.py` or equivalent)

How this running instance was delivered. Used **only** for diagnostics and bug reports.

| Field | Type | Notes |
|-------|------|-------|
| `kind` | `PACKAGE \| BUNDLE \| SOURCE` | Detected once at startup |
| `version` | `str` | Single source of truth (research D-13) |
| `bundle_root` | `str \| None` | Set only for `BUNDLE` |

**Hard rule**: no behavioural code may branch on `kind`. FR-026 requires the two forms to be
behaviourally identical, and the reliable way to guarantee that is to make the difference
unobservable to application logic. This is enforced by a test asserting `DistributionForm` is
referenced only by the diagnostics and `--version` paths — the same technique as the
import-boundary tests, for the same reason.

**Detection**: `BUNDLE` when the frozen-application marker is present; `PACKAGE` when installed
metadata exists; `SOURCE` otherwise.

---

## `DesktopIntegration` (`gpum/adapters/linux/desktop_entry.py`)

The user-initiated files the tool writes outside its preference store — the Principle V deviation,
made explicit as a type so it cannot be done casually.

| Field | Type | Notes |
|-------|------|-------|
| `desktop_entry_path` | `Path` | `~/.local/share/applications/gpum.desktop` |
| `icon_path` | `Path` | `~/.local/share/icons/hicolor/scalable/apps/gpum.svg` |
| `autostart_path` | `Path` | `~/.config/autostart/gpum.desktop` |
| `desktop_entry_installed` | `bool` | Queried, never assumed |
| `autostart_enabled` | `bool` | |

**Invariants**:
- Every path resolves under the user's XDG directories. A write outside them is a bug, and a test
  asserts it by pointing `XDG_*` at a temporary root and verifying nothing lands elsewhere.
- Every write has a matching removal. Anything the tool creates, the same toggle deletes.
- Nothing is written without an explicit user action — never at install, import, or first launch.

---

## `ResumeEvent` (`gpum/core/engine.py`)

Detected when the wall clock jumps further than sampling can explain (research D-10).

| Field | Type | Notes |
|-------|------|-------|
| `detected_at` | `datetime` | |
| `gap_seconds` | `float` | Observed clock gap |
| `expected_interval_s` | `float` | What it should have been |

**Threshold**: a gap exceeding `max(10 × interval, 30 s)` is treated as a resume rather than a slow
cycle. Chosen to sit well above a degraded device's 10-cycle backoff so ordinary slowness is never
misread as a suspend.

**On detection**: clear degradation backoff, force re-enumeration (a GPU may have changed state
across suspend), and append an explicit **gap** to every device history.

**The gap is the point.** Drawing a continuous line across a four-hour suspend would assert
measurements that were never taken — the same lie as rendering an unavailable metric as `0`.
Feature 001's `HistoryPoint` already carries `value=None` for exactly this, so the mechanism
exists; this feature just has a new reason to use it.

---

## `DriverRestartEvent` (`gpum/backends/nvidia/backend.py`)

| Field | Type | Notes |
|-------|------|-------|
| `detected_at` | `datetime` | |
| `trigger_error` | `str` | The NVML condition that revealed it |
| `recovered` | `bool` | |
| `recovery_attempts` | `int` | |

**State transitions**:

```
ACTIVE ──driver error──> RECOVERING ──re-init ok──> ACTIVE
                              │
                              └──repeated failure──> UNAVAILABLE ──(retry)──> RECOVERING
```

While `RECOVERING` or `UNAVAILABLE`, devices stay **listed** with their metrics marked
unavailable. They are not removed. Removing and re-adding would flash the entire device list away
and back, and would discard history for a GPU that never physically left.

Handles are rebuilt, never reused: an NVML handle does not survive a driver restart, and a stale
one returns errors forever, leaving the tool looking permanently broken until restarted — which
FR-014 forbids.

---

## `HardwareVerificationRecord` (`tools/compare-with-nvidia-smi.py` output)

The artefact proving FR-007/FR-008 rather than asserting them.

| Field | Type | Notes |
|-------|------|-------|
| `captured_at` | `datetime` | |
| `driver_version` | `str` | |
| `gpu_model` | `str` | |
| `duration_s` | `float` | |
| `sample_count` | `int` | |
| `max_memory_deviation_pct` | `float` | Must be ≤ 5% (SC-003) |
| `process_match_rate` | `float` | Must be 100% (SC-004) |
| `mean_cycle_cost_ms` | `float` | Feeds the timeout, replacing 001's placeholder (FR-009) |
| `p99_cycle_cost_ms` | `float` | |

**Sampling must be concurrent, not sequential.** GPU memory moves continuously; sampling the tool
and then `nvidia-smi` measures the delay between them, not their agreement.

---

## Preference additions (`gpum/core/preferences.py`)

Added to feature 001's `Preferences` dataclass, still Qt-free.

| Field | Type | Default | FR |
|-------|------|---------|-----|
| `tray_enabled` | `bool` | `True` | FR-029, FR-031 |
| `close_notice_shown` | `bool` | `False` | FR-030 — one-time notice, per user not per session |
| `start_hidden` | `bool` | `False` | FR-022 — set when launched via autostart |

`autostart_enabled` is deliberately **not** stored here: the presence of the autostart file is the
truth. Storing it separately creates two sources that drift when the user deletes the file by hand.
