# Implementation Plan: GPU Usage Monitor

**Branch**: `001-gpu-usage-monitor` | **Date**: 2026-08-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-gpu-usage-monitor/spec.md`

## Summary

A PySide6 desktop application that shows live GPU memory, utilization, and per-process
attribution, refreshing once per second without ever blocking its own interface.

The architecture separates three concerns that are easy to conflate: **vendor backends** answer
"what devices exist and what are their metrics", **platform adapters** answer "which local
processes are using them", and **core** merges both into immutable snapshots that the UI renders.
Phase 0 research established why attribution must be its own negotiated capability rather than
something backends always supply — NVIDIA on Windows cannot report per-process memory at all
under the WDDM driver model, so a backend-only design would have forced either a lie or a special
case (see [research.md](./research.md) D-03).

**This release ships the NVIDIA backend only**, per the user's direction. AMD and Intel are
delivered later behind the identical interface. The risk this creates — an interface
unconsciously shaped around NVML — is addressed structurally rather than by intention: the
contract test suite is written against the protocol and runs against a `FakeBackend` whose data
shapes deliberately differ from NVML's, AMD and Intel ship as registered stub backends from day
one so the registry always holds more than one implementation, and no NVML type is permitted to
cross out of `backends/nvidia/`.

## Technical Context

**Language/Version**: Python 3.11+ (3.11 minimum; validated on 3.11, 3.12, 3.13)

**Primary Dependencies**: PySide6 (Qt for Python, LGPLv3) for the interface; `psutil` for process
identity; `nvidia-ml-py` (NVML bindings) as the optional `[nvidia]` extra

**Storage**: `QSettings` for user preferences only (interval, sort order, window layout). No
database, no telemetry, no on-disk history — all sampling data is in-memory and bounded.

**Testing**: `pytest`, `pytest-qt`, `pytest-cov`; headless Qt via `QT_QPA_PLATFORM=offscreen`;
hardware-dependent tests marked `@pytest.mark.hardware` and deselected by default

**Target Platform**: Linux and Windows desktop (FR-025). macOS deferred but not architecturally
precluded (FR-026) — see Complexity Tracking.

**Project Type**: Single-project desktop application

**Performance Goals**: 1 Hz default sampling; UI interaction response under 100 ms at all times
(SC-003); no GUI-thread operation exceeding 16 ms (Principle III); full sampling cycle completing
within the interval on machines with 8+ GPUs

**Constraints**: Read-only, no elevation required (FR-019, FR-021); zero network egress (FR-022);
bounded memory across a 24-hour run (FR-024, SC-005); every displayed value carries an
availability state and no value is ever fabricated (FR-017, SC-007)

**Scale/Scope**: Up to 8+ GPUs and several hundred GPU-using processes on one local machine;
roughly 12 UI-facing screens' worth of surface in a single main window

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial evaluation (pre-research)

| Gate | Status | Basis |
|------|--------|-------|
| **I. Vendor-Agnostic Abstraction** | ⚠️ PASS WITH RISK | NVIDIA-only delivery risks an NVML-shaped interface. Mitigations below. |
| **II. Platform Parity** | ❌ VIOLATION | macOS deferred; constitution states all three platforms. Tracked below. |
| **III. Non-Blocking Live Updates** | ✅ PASS | Sampling isolated to a worker thread; per-device timeouts; signal-based delivery. |
| **IV. Test-First on Simulated Hardware** | ✅ PASS | `FakeBackend` + recorded fixtures + shared contract suite; full suite runs GPU-free. |
| **V. Read-Only, Least Privilege** | ✅ PASS | No mutating operations in scope; no elevation; no egress. |
| **Tech constraints** | ✅ PASS | Python + PySide6; one-way `backends → core → ui` layering; vendor binding optional at install. |

**Principle I mitigations** (these are binding design rules, not aspirations):

1. NVML handles, structs, and error codes MUST NOT appear outside `src/gpum/backends/nvidia/`.
   Enforced by an automated import-boundary test, not by review alone.
2. AMD and Intel backends are created in this release as registered stubs reporting
   `UNSUPPORTED` — the registry therefore never has exactly one implementation, and the "add a
   vendor" path is exercised before any vendor-specific code is written.
3. The contract suite is authored against the `GpuBackend` protocol and parametrized over all
   registered backends. `FakeBackend` deliberately models devices NVML cannot produce (a device
   with no utilization support, a device with no process attribution, a MIG device) so an
   NVML-shaped assumption fails a test rather than passing unnoticed.

### Post-design re-evaluation (after Phase 1)

| Gate | Status | Change from initial |
|------|--------|---------------------|
| **I. Vendor-Agnostic Abstraction** | ✅ PASS | Strengthened. D-03 forced attribution out of the backend interface into a separate `ProcessAttributionProvider`, which removed the largest NVML-shaped assumption before it was written. `contracts/backend-interface.md` defines the boundary; the import-boundary test enforces it. |
| **II. Platform Parity** | ❌ VIOLATION (unchanged) | Still requires resolution — see Complexity Tracking. Design work confined every OS-specific behavior to `src/gpum/adapters/`, so the deferral stayed a scope decision and not an architectural one, satisfying FR-026. |
| **III. Non-Blocking Live Updates** | ✅ PASS | `contracts/ui-update-contract.md` makes the thread boundary explicit and states the honest limitation that a timeout abandons the wait but cannot cancel a hung driver call. |
| **IV. Test-First on Simulated Hardware** | ✅ PASS | Contract suite, fake backend, and offscreen Qt confirmed in `quickstart.md`. |
| **V. Read-Only, Least Privilege** | ✅ PASS | Container resolution chosen via `/proc` rather than the Docker socket specifically to avoid a group-membership requirement (D-06). |
| **Tech constraints** | ✅ PASS | Layering holds in the structure below; `nvidia-ml-py` is an optional extra (D-13). |

**Gate result**: proceeds with one recorded violation (Principle II), which is a scope decision
already accepted by the user during `/speckit-specify` and is not marked NON-NEGOTIABLE in the
constitution. It requires a governance decision, not a design change.

## Project Structure

### Documentation (this feature)

```text
specs/001-gpu-usage-monitor/
├── plan.md              # This file
├── research.md          # Phase 0 output — 13 decisions + 4 spikes
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── backend-interface.md
│   ├── process-attribution.md
│   └── ui-update-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
src/gpum/
├── __init__.py
├── __main__.py                  # entry point; `python -m gpum` and the `gpum` script
├── core/                        # no Qt imports, no vendor imports, no OS-specific code
│   ├── models.py                # GpuDevice, GpuProcess, Sample, MetricValue, Availability
│   ├── units.py                 # single unit convention; all normalization lives here
│   ├── registry.py              # backend + adapter discovery and registration
│   ├── engine.py                # SamplingEngine: pure-Python scheduling, per-device timeouts,
│   │                            #   staleness, degradation. NO Qt — see note below.
│   ├── merge.py                 # joins device metrics with attribution into a Snapshot
│   ├── history.py               # bounded per-device ring buffers
│   └── preferences.py           # plain dataclass; no persistence logic
├── backends/                    # vendor-specific; must not import core or ui
│   ├── base.py                  # GpuBackend protocol (see contracts/backend-interface.md)
│   ├── nvidia/
│   │   ├── backend.py           # protocol implementation
│   │   ├── nvml.py              # the ONLY module permitted to touch pynvml
│   │   └── errors.py            # NVML error code → Availability reason mapping
│   ├── amd/backend.py           # registered stub reporting UNSUPPORTED
│   ├── intel/backend.py         # registered stub reporting UNSUPPORTED
│   └── fake/backend.py          # scripted simulated backend; tests and demo mode
├── adapters/                    # platform-specific; the ONLY place OS branching is allowed
│   ├── base.py                  # ProcessAttributionProvider, ProcessIdentityProvider
│   ├── linux/
│   │   ├── identity.py          # psutil-based process identity
│   │   └── containers.py        # /proc/<pid>/cgroup → container id
│   └── windows/
│       ├── identity.py
│       └── pdh.py               # GPU Engine / GPU Process Memory counters (spike S-01)
└── ui/                          # the ONLY place Qt is imported
    ├── app.py                   # QApplication setup, worker thread ownership
    ├── sampler_worker.py        # QObject/QThread/QTimer wrapper around core.engine

    ├── main_window.py
    ├── device_panel.py          # per-device memory, utilization, sparkline
    ├── process_model.py         # QAbstractTableModel with stable sort (FR-010)
    ├── sparkline.py             # bounded history rendering, gaps for unavailable
    ├── availability.py          # renders Availability states — never renders a missing value as 0
    ├── settings_dialog.py
    └── preferences_store.py     # QSettings read/write

tests/
├── contract/                    # parametrized over every registered backend
│   ├── test_backend_protocol.py
│   └── test_attribution_protocol.py
├── unit/
│   ├── test_units.py
│   ├── test_history_bounds.py
│   ├── test_merge.py
│   └── test_import_boundaries.py  # enforces the layering rules mechanically
├── integration/
│   ├── test_sampling_lifecycle.py # hot-plug, timeout, degradation, sleep/resume
│   └── test_ui_updates.py         # pytest-qt, offscreen
└── fixtures/
    └── nvml/                    # recorded NVML responses, incl. failure modes
```

**Structure Decision**: Single-project `src/` layout, chosen because this is one desktop
application with no server or client split. The package boundaries are load-bearing rather than
cosmetic — they are the physical expression of constitution Principle I and Principle II, and
`tests/unit/test_import_boundaries.py` enforces them automatically: `core` may not import
`backends`, `adapters`, `ui`, or Qt; `backends` may not import `core`, `ui`, or `adapters`; only
`backends/nvidia/nvml.py` may import `pynvml`; only `ui/` may import PySide6; and OS-conditional
logic may appear only under `adapters/`.

The `adapters/` name is deliberate — it matches the constitution's "platform adapter modules"
language, and avoids naming a package `platform`, which shadows a standard-library module.

**Sampling is split across the Qt boundary on purpose.** The scheduling, timeout, degradation,
and merge logic is a pure-Python `SamplingEngine` in `core/engine.py`; the `QObject` that owns a
`QTimer`, lives on a `QThread`, and emits signals is `ui/sampler_worker.py`. Putting the timer in
`core` would have made `core` require a Qt event loop, breaking the constitution's rule that the
core layer is importable and testable without a `QApplication`. The split also means the hardest
logic to get right — timeout and degradation state machines — is unit-testable with a fake clock
and no Qt at all.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **Principle II — macOS excluded** from this release, against "GPUM MUST run on Linux, Windows, and macOS from one codebase" | Current Mac hardware ships neither NVIDIA nor discrete AMD GPUs, so the vendor set this feature targets barely exists there. Building and testing a third platform for near-zero user reach would delay both platforms that do have the hardware. The user accepted this scope during `/speckit-specify`. | Shipping macOS anyway was rejected as effort against hardware nobody in the target audience runs. Note this is a *scope* deferral only: FR-026 keeps all OS-specific code behind `adapters/`, so adding macOS later is additive work, not a rewrite. **This still requires a governance decision** — either a MINOR constitution amendment permitting phased platform rollout, or a recorded deviation. Flagged, not silently absorbed. |
| **Two provider interfaces** (`GpuBackend` + `ProcessAttributionProvider`) instead of one | NVIDIA-on-Windows cannot supply per-process memory under WDDM, while the Windows OS itself can supply it for every vendor. The capability genuinely has two independent sources, so one interface cannot express it without lying or special-casing. | A single `GpuBackend` interface owning attribution was rejected because the NVIDIA backend would have needed Windows-specific PDH code inside it — violating both Principle I (vendor module containing platform logic) and Principle II (OS branching outside `adapters/`). The second interface is cheaper than that coupling. |
| **AMD and Intel stub backends** shipped despite being NVIDIA-only this release | Guards Principle I against the NVIDIA-only delivery risk. A registry holding exactly one implementation invites an interface shaped around it; stubs keep the plural case real and let the "unsupported vendor" UI path be tested now. | Deferring them entirely was rejected: the interface would then be validated against one real implementation plus one fake, and the first genuine second vendor would likely force an interface change — precisely the outcome Principle I exists to prevent. Stubs are a few dozen lines. |
