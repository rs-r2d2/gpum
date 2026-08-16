# Contract: Sampler → UI update boundary

**Modules**: `src/gpum/core/engine.py`, `src/gpum/ui/sampler_worker.py`, `src/gpum/ui/app.py`
| **Feature**: 001-gpu-usage-monitor

**Split**: `core/engine.py` holds the pure-Python `SamplingEngine` — scheduling, per-device
timeouts, degradation state, snapshot construction — with no Qt import, so it is unit-testable
with a fake clock. `ui/sampler_worker.py` is the thin `QObject` that owns the `QTimer`, lives on
the `QThread`, and emits the signals below. Qt never appears in `core`.

The thread boundary. Constitution Principle III is NON-NEGOTIABLE, so this contract is stated as
hard rules rather than guidance.

---

## Threading model

```
┌─ GUI thread ───────────────────┐        ┌─ Sampler thread (QThread) ──────┐
│ QApplication, widgets, models  │        │ SamplerWorker                    │
│                                │        │  ├── QTimer (interval)           │
│  on_snapshot(Snapshot) ────────┼◄───────┼── snapshot_ready(Snapshot)       │
│  set_interval / pause ─────────┼───────►┼── queued slot                    │
│                                │        │  └── ThreadPoolExecutor          │
│ NEVER touches a backend        │        │       (per-device, timed out)    │
└────────────────────────────────┘        └──────────────────────────────────┘
```

The worker is a `QObject` **moved to** a `QThread` — never a `QThread` subclass with logic in
`run()`. Its `QTimer` is created after the move so it lives in the worker's event loop.

---

## Hard rules

### GUI thread

**MUST NOT**, under any circumstance:
- Call `probe()`, `enumerate_devices()`, `sample_device()`, `attribute()`, or `identify()`
- Import or touch `pynvml`, `psutil`, or any adapter module
- Perform file, socket, or subprocess I/O
- Block on a lock the sampler thread holds, or `wait()` on the sampler thread except during
  shutdown

**MUST**: complete every slot in under 16 ms (Principle III). Rendering a snapshot is assignment
and repaint — never computation over raw samples. Anything derived is computed on the sampler
side, before the signal.

### Sampler thread

**MUST NOT**: create, touch, or destroy any widget; call any Qt GUI class; emit a mutable object.

**MUST**: deliver results only via signals carrying frozen `Snapshot` objects.

---

## Signals

```python
class SamplerWorker(QObject):
    snapshot_ready = Signal(object)        # Snapshot — frozen, immutable
    discovery_changed = Signal(object)     # DiscoveryReport — on device set change
    error_occurred = Signal(str, str)      # (severity, message) — never a dialog from here
```

**Contract on `snapshot_ready`**:
- The payload is fully constructed and immutable before emission. No lazy fields, no live
  references into sampler state. This is what makes lock-free handoff safe.
- Emitted once per cycle even when nothing changed — SC-005 and FR-016 need liveness evidence,
  and a silent sampler is indistinguishable from a hung one.
- `sequence` is monotonic. The UI **MUST** discard a snapshot whose `sequence` is lower than the
  last rendered one; queued delivery can reorder under load.
- Emitted even when `devices` is empty (FR-018).

**`error_occurred` MUST NOT** trigger a modal dialog. Errors render inline in the affected
device's panel. A modal from a background sampler would block the UI on a recurring condition —
a 1 Hz error would make the app unusable.

---

## Timeout and degradation

Per FR-014, and honest about what a timeout actually does:

1. Each `sample_device` call is submitted to a `ThreadPoolExecutor` with a per-device timeout
   (default 500 ms, tuned by spike S-03).
2. On timeout the device's metrics become `STALE`, carrying the previous values with their
   original `sampled_at` so the UI can show true age. **Every other device continues normally.**
3. After 3 consecutive timeouts the device becomes `DEGRADED` and its query cadence backs off to
   every 10th cycle.
4. Any success restores `AVAILABLE` and the normal cadence immediately.

**Stated limitation**: a timeout abandons the *wait*, not the *call*. A genuinely hung driver
call holds its pool thread until the driver returns. The pool is therefore bounded and degraded
devices stop being scheduled — the design contains the damage rather than pretending
cancellation happened. Documented in code at the call site, not only here.

---

## Interval, pause, visibility

- `set_interval(ms)` and `set_paused(bool)` are **queued** slots on the worker. The GUI thread
  never mutates worker state directly.
- A new interval takes effect on the next cycle, never mid-cycle (FR-012).
- On `hide`/`minimize`/`windowDeactivate`, the UI signals the worker to throttle to a slow
  heartbeat (default 10× the interval) or stop entirely per preference (FR-015). The tool must
  not consume the resources it is meant to measure.
- Re-enumeration runs every 10th cycle (D-08); a change emits `discovery_changed` (FR-020).

---

## Shutdown

Ordered, and it must not hang on a wedged driver:

1. GUI requests stop → worker stops its timer, accepts no new cycles.
2. Worker waits up to 2 s for in-flight pool futures, then abandons them.
3. Worker calls `shutdown()` on every backend (idempotent, non-raising per the backend contract).
4. Thread quits; GUI joins with a 5 s cap, then proceeds regardless.

**MUST NOT** block application exit on a hung driver call. A monitor that cannot be closed
because the thing it monitors is broken is precisely the failure mode this design exists to
avoid.

---

## Contract tests

`tests/integration/test_ui_updates.py` (pytest-qt, `QT_QPA_PLATFORM=offscreen`).

| # | Assertion | Enforces |
|---|-----------|----------|
| U-01 | No GUI-thread slot exceeds 16 ms with 8 devices × 200 processes | **Principle III** |
| U-02 | A backend blocking 5 s leaves the GUI responsive; that device goes `STALE` | FR-013, FR-014 |
| U-03 | Other devices keep updating while one is `DEGRADED` | FR-014 |
| U-04 | Out-of-order snapshots are discarded by `sequence` | — |
| U-05 | Snapshots are emitted with an empty device list and the UI stays usable | FR-018, SC-006 |
| U-06 | Interval change takes effect next cycle; pause halts emissions | FR-012 |
| U-07 | Hiding the window throttles sampling | FR-015 |
| U-08 | Shutdown completes within 5 s even with a permanently blocked backend call | — |
| U-09 | Process table sort order is stable across refreshes; rows do not reshuffle | FR-010 |
| U-10 | 24 h simulated run at accelerated cadence shows no unbounded memory growth | FR-024, SC-005 |
| U-11 | An `UNSUPPORTED` metric never renders as `0` or blank; it renders its reason | **SC-007** |
| U-12 | Sparkline shows a gap, not a zero-dip, across an unavailable stretch | **SC-007**, FR-005 |
