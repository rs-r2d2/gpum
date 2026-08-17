---

description: "Task list for 001-gpu-usage-monitor"
---

# Tasks: GPU Usage Monitor

**Input**: Design documents from `/specs/001-gpu-usage-monitor/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Test tasks are **mandatory** here, not optional. Constitution Principle IV states
"Tests MUST be written and MUST fail before implementation." Every phase therefore leads with its
failing tests.

**Organization**: Grouped by user story so each is independently implementable and testable.

**Release scope**: NVIDIA backend only; Linux + Windows only. AMD and Intel ship as registered
stubs (Principle I protection, see plan.md). macOS is deferred — an open constitution violation
recorded in plan.md § Complexity Tracking.

> **Superseded 2026-08-17.** Windows and macOS are no longer targets and the constitution
> violation is closed. The scope above is Linux + NVIDIA only. See
> § Status revision — 2026-08-17 at the end of this file; task markers below are updated, this
> paragraph is left as the original record.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US4, mapping to spec.md user stories
- Exact file paths included in every task

## Path Conventions

Single project: `src/gpum/`, `tests/` at repository root, per plan.md § Project Structure.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization

- [X] T001 Create the package and test directory skeleton from plan.md § Project Structure (`src/gpum/{core,backends,adapters,ui}/`, `tests/{contract,unit,integration,fixtures}/`) with `__init__.py` in every package
- [X] T002 Create `pyproject.toml`: `requires-python = ">=3.11"`, deps `PySide6` and `psutil`, extras `nvidia = ["nvidia-ml-py"]`, `dev = ["pytest", "pytest-qt", "pytest-cov", "ruff", "mypy"]`, `all`, and the `gpum` GUI entry point per research D-13
- [X] T003 [P] Configure `ruff` (lint + format) in `pyproject.toml` with line length 100
- [X] T004 [P] Configure `mypy` in `pyproject.toml` in strict mode for `src/gpum/core/` and `src/gpum/backends/base.py`
- [X] T005 [P] Configure pytest in `pyproject.toml`: `QT_QPA_PLATFORM=offscreen` env, `hardware` marker registered and deselected by default via `addopts = "-m 'not hardware'"`
- [X] T006 [P] Create `.github/workflows/ci.yml` running lint, typecheck, and the full suite against Python 3.11/3.12/3.13, with no GPU present. Originally a Linux × Windows matrix; narrowed to Linux on 2026-08-17 with the platform scope.
- [X] T007 [P] Create `.gitignore` and a `README.md` stub stating the read-only, no-telemetry, no-elevation guarantees (FR-019, FR-021, FR-022)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The data model, backend protocol, registry, and sampling engine every story needs.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Tests (write first, must fail)

- [X] T008 [P] Write failing tests for the `MetricValue` invariant (`value is None ⟺ availability != AVAILABLE`) and for the required `reason` on non-available metrics, in `tests/unit/test_models.py` — this is the mechanical guard behind SC-007
- [X] T009 [P] Write failing tests for byte-based storage and single-convention formatting in `tests/unit/test_units.py` (FR-004)
- [X] T010 [P] Write failing import-boundary tests in `tests/unit/test_import_boundaries.py`: `core` imports no Qt/vendor/adapter module; `backends` imports no `core`/`ui`/`adapters`; only `backends/nvidia/nvml.py` imports `pynvml`; only `ui/` imports PySide6 (contract C-12, C-13)
- [X] T011 [P] Write the failing backend contract suite in `tests/contract/test_backend_protocol.py` covering C-01 through C-11, parametrized over every registered backend
- [X] T012 [P] Write failing tests for `DeviceHistory` bounded capacity and gap retention in `tests/unit/test_history_bounds.py` (FR-005, FR-024)
- [X] T013 [P] Write failing engine tests with a fake clock in `tests/unit/test_engine.py`: timeout → `STALE`, 3 consecutive timeouts → `DEGRADED`, any success → recovery, monotonic `sequence` (FR-014)

### Data model (`core/models.py` — sequential, one file)

- [X] T014 Implement `Availability`, `MetricValue` with `__post_init__` invariant enforcement, and `Vendor` in `src/gpum/core/models.py` per data-model.md
- [X] T015 Implement `DeviceId`, `GpuDevice`, and `BackendCapabilities` in `src/gpum/core/models.py`, with identity keyed on UUID → PCI ID → `vendor:index` (research D-07)
- [X] T016 Implement `ProcessIdentity`, `PidKey` as `(pid, started_at)`, and `GpuProcess` in `src/gpum/core/models.py` (research D-05)
- [X] T017 Implement `Snapshot`, `DiscoveryReport`, `BackendReport`, and `BackendState` in `src/gpum/core/models.py`, all fields as tuples so snapshots are immutable across the thread boundary

### Core infrastructure

- [X] T018 [P] Implement `src/gpum/core/units.py`: bytes-only storage, one display convention, formatting helpers that refuse to format a non-`AVAILABLE` metric
- [X] T019 [P] Implement `src/gpum/core/history.py`: `DeviceHistory` over fixed-`maxlen` deques of `(timestamp, value, availability)`, capacity derived from window ÷ interval
- [X] T020 [P] Implement the `GpuBackend` protocol and `DeviceGoneError` in `src/gpum/backends/base.py` per contracts/backend-interface.md
- [X] T021 [P] Implement the `ProcessAttributionProvider` and `ProcessIdentityProvider` protocols plus `AttributionSupport` and `AttributionResult` in `src/gpum/adapters/base.py` per contracts/process-attribution.md
- [X] T022 Implement `FakeBackend` in `src/gpum/backends/fake/backend.py` against the protocol, with no NVML-shaped assumptions
- [X] T023 Implement the named fake scenarios in `src/gpum/backends/fake/scenarios.py`: `two-nvidia`, `processes-churn`, `no-attribution`, `metrics-unsupported`, `one-device-hangs`, `mig-device`, `multi-vendor-degraded` (quickstart.md V-1 – V-5)
- [X] T024 [P] Implement the AMD stub backend in `src/gpum/backends/amd/backend.py` returning `BackendState.NOT_IMPLEMENTED` from `probe()` and no devices
- [X] T025 [P] Implement the Intel stub backend in `src/gpum/backends/intel/backend.py` returning `BackendState.NOT_IMPLEMENTED` from `probe()` and no devices
- [X] T026 Implement backend registration and probe ordering in `src/gpum/core/registry.py`, building a `DiscoveryReport` from every registered backend including stubs
- [X] T027 Implement attribution-provider selection in `src/gpum/core/registry.py` following the three-step order in contracts/process-attribution.md, with "no provider" as a supported outcome
- [X] T028 Implement `SamplingEngine` in `src/gpum/core/engine.py`: pure Python, injected clock, `ThreadPoolExecutor` with per-device timeout, producing `Snapshot` objects with monotonic `sequence`
- [X] T029 Implement the degradation state machine in `src/gpum/core/engine.py`: timeout → `STALE` preserving prior value and original `sampled_at`, 3 consecutive → `DEGRADED` with 10× backoff, any success → immediate recovery (FR-014)
- [X] T030 Implement `src/gpum/core/merge.py` joining device metrics with attribution results into a `Snapshot`, filling `per_device` availability for every device key (contract A-02)
- [X] T031 Implement the `Preferences` dataclass with defaults and `refresh_interval_ms` clamping to `[100, 60000]` in `src/gpum/core/preferences.py`, with no Qt import

**Checkpoint**: `pytest tests/unit tests/contract` passes with no GPU present. Foundation ready.

---

## Phase 3: User Story 1 - See live GPU memory and load at a glance (Priority: P1) 🎯 MVP

**Goal**: Every GPU listed with model name, used/total memory, percent used, and utilization,
refreshing every second without the UI ever blocking.

**Independent Test**: Launch against `--backend fake --scenario two-nvidia`, confirm two devices
appear within 3 s with values changing unprompted while the window stays responsive; then launch
on real NVIDIA hardware, start a CUDA workload, and watch used memory rise and fall.

### Tests for User Story 1 (write first, must fail)

- [X] T032 [P] [US1] Write failing NVML mapping tests in `tests/unit/test_nvml_mapping.py` using recorded fixtures: `NVML_ERROR_NOT_SUPPORTED` → `UNSUPPORTED`, `NVML_ERROR_NO_PERMISSION` → `PERMISSION_DENIED`, `NVML_ERROR_DRIVER_NOT_LOADED` → `DRIVER_MISSING` (contract C-02, C-06)
- [X] T033 [P] [US1] Record NVML response fixtures, including failure modes, in `tests/fixtures/nvml/` so the NVIDIA backend is testable with no driver present (Principle IV)
- [X] T034 [P] [US1] Write failing UI tests in `tests/integration/test_ui_updates.py` for U-01 (no GUI slot exceeds 16 ms with 8 devices), U-04 (out-of-order snapshots discarded), and U-11 (an `UNSUPPORTED` metric never renders as `0` or blank)
- [X] T035 [P] [US1] Write a failing hardware-marked test in `tests/integration/test_nvidia_hardware.py` (`@pytest.mark.hardware`) asserting real device enumeration and plausible memory figures

### Implementation for User Story 1

- [X] T036 [US1] Implement the NVML wrapper in `src/gpum/backends/nvidia/nvml.py` — the only module permitted to import `pynvml`; wrap init, shutdown, device handles, name, UUID, PCI info, memory info, and utilization rates
- [X] T037 [US1] Implement NVML error-code to `Availability`/`BackendState` mapping in `src/gpum/backends/nvidia/errors.py`
- [X] T038 [US1] Implement `probe()` in `src/gpum/backends/nvidia/backend.py` distinguishing `LIBRARY_MISSING`, `DRIVER_MISSING`, and `NO_DEVICES`, never raising, completing within 2 s (contract C-01, C-02)
- [X] T039 [US1] Implement `enumerate_devices()` in `src/gpum/backends/nvidia/backend.py` with UUID-first stable identity and `[]` when no devices are present (contract C-03, C-04)
- [X] T040 [US1] Implement `sample_device()` and `capabilities()` in `src/gpum/backends/nvidia/backend.py`, returning memory in bytes and raising `DeviceGoneError` when a device vanishes (contract C-05, C-07, C-10)
- [X] T041 [US1] Register the NVIDIA backend in `src/gpum/core/registry.py`
- [X] T042 [P] [US1] Implement `SamplerWorker` in `src/gpum/ui/sampler_worker.py`: `QObject` moved to a `QThread`, `QTimer` created after the move, emitting `snapshot_ready`, `discovery_changed`, and `error_occurred`
- [X] T043 [P] [US1] Implement `src/gpum/ui/availability.py` — the single place `Availability` states become display text; an unavailable metric renders its reason and never `0` or blank (SC-007)
- [X] T044 [US1] Implement `QApplication` setup and worker-thread ownership in `src/gpum/ui/app.py`, including the ordered shutdown sequence from contracts/ui-update-contract.md
- [X] T045 [US1] Implement `src/gpum/ui/main_window.py` hosting the device list and wiring `snapshot_ready` to a render slot that discards out-of-order `sequence` values
- [X] T046 [US1] Implement `src/gpum/ui/device_panel.py` showing model name, used/total memory, percent used, and utilization per device, appending `index` to disambiguate identical model names (FR-002)
- [X] T047 [US1] Implement `src/gpum/__main__.py` and the `gpum` entry point with `--backend` and `--scenario` arguments (quickstart.md)
- [X] T048 [US1] Wire `DeviceHistory` into the sampling pipeline in `src/gpum/ui/main_window.py` so each device accumulates a bounded trend (FR-005)
- [X] T049 [US1] Implement `src/gpum/ui/sparkline.py` rendering bounded history with **gaps** across unavailable stretches rather than dips to zero (U-12)
- [ ] T050 [US1] Run spike S-03: measure a full NVML sampling cycle on multi-GPU hardware and set the per-device timeout in `src/gpum/core/engine.py` from the measurement, replacing the 500 ms placeholder

**Checkpoint**: US1 is independently functional. Quickstart V-1 and V-7 pass. This is the MVP.

---

## Phase 4: User Story 2 - See which processes are consuming the GPU (Priority: P2)

**Goal**: A live per-device process list with name, PID, and GPU memory — and an honest
explanation wherever attribution is unavailable, never an empty list.

**Independent Test**: Against `--scenario processes-churn`, confirm processes appear and
disappear within two intervals with a restricted process still counted in device totals; against
`--scenario no-attribution`, confirm the explanation appears instead of an empty list.

### Tests for User Story 2 (write first, must fail)

- [X] T051 [P] [US2] Write the failing attribution contract suite in `tests/contract/test_attribution_protocol.py` covering A-01 through A-12, parametrized over every registered provider
- [X] T052 [P] [US2] Write failing tests in `tests/unit/test_process_identity.py` for PID recycling: identity keyed on `(pid, started_at)` must not misattribute a recycled PID (A-08, FR-008)
- [X] T053 [P] [US2] Write failing tests in `tests/unit/test_merge.py` asserting unresolved and restricted processes are counted in `total_attributed` and never dropped (A-03, A-04, FR-031, SC-012)
- [X] T054 [P] [US2] Write a failing UI test in `tests/integration/test_ui_updates.py` asserting a device with `attribution=UNSUPPORTED` renders an explanation, not an empty table (US2 scenario 4)
- [X] T055 [P] [US2] Write failing container-resolution tests in `tests/unit/test_containers.py` against sample `/proc/<pid>/cgroup` content for Docker, containerd, and Podman (FR-029, FR-030)

### Implementation for User Story 2

- [X] T056 [P] [US2] Implement `psutil`-based batch identity resolution in `src/gpum/adapters/linux/identity.py`, mapping `AccessDenied` → `RESTRICTED` and `NoSuchProcess` → `UNRESOLVED`, returning an entry for every requested key (A-05, A-06, A-10)
- [~] T057 [P] [US2] ~~Implement `psutil`-based batch identity resolution in `src/gpum/adapters/windows/identity.py`~~ **DROPPED — Windows is no longer a target** (constitution 2.0.0). Was implemented, then removed with the Windows adapter package. The shared lookup it introduced survives as `src/gpum/adapters/psutil_identity.py`.
- [X] T058 [P] [US2] Implement container resolution in `src/gpum/adapters/linux/containers.py` reading only `/proc/<pid>/cgroup` — no Docker socket, no daemon, no elevation (A-12, research D-06)
- [X] T059 [US2] Implement the NVML attribution provider in `src/gpum/backends/nvidia/attribution.py` using `nvmlDeviceGetComputeRunningProcesses_v3` and `nvmlDeviceGetGraphicsRunningProcesses_v3`
- [~] T060 [US2] ~~Run spike S-02 on Windows/WDDM hardware~~ **DROPPED — Windows is no longer a target** (constitution 2.0.0). The nullable-memory handling it would have confirmed is retained and tested: a `None` figure becomes `UNSUPPORTED` with a reason, never `0`.
- [X] T061 [US2] Implement the S-02 finding in `src/gpum/backends/nvidia/attribution.py`: where the driver reports no per-process memory, return PIDs with `memory_used` as `UNSUPPORTED` carrying a reason — never `0` (A-07, research D-03). The reason text was generalised when Windows was dropped; the behaviour is unchanged and still tested.
- [X] T062 [US2] Register the NVML attribution provider with the NVIDIA backend in `src/gpum/core/registry.py`
- [~] T063 [US2] ~~Run spike S-01: Windows PDH counter paths~~ **DROPPED — Windows is no longer a target** (constitution 2.0.0).
- [~] T064 [US2] ~~Implement the Windows PDH attribution provider~~ **DROPPED — Windows is no longer a target** (constitution 2.0.0). Never written.
- [~] T065 [US2] ~~Register the PDH provider as the Windows platform attribution source~~ **DROPPED — Windows is no longer a target** (constitution 2.0.0).
- [X] T066 [US2] Extend `src/gpum/core/merge.py` to attach identity and container information to attributed PIDs and emit `UNRESOLVED` entries for unidentifiable PIDs (FR-031)
- [X] T067 [US2] Implement `ProcessTableModel` in `src/gpum/ui/process_model.py` as a `QAbstractTableModel` keyed on `(device_key, pid, started_at)` so rows update in place instead of rebuilding
- [X] T068 [US2] Render `ProcessIdentity` states in `src/gpum/ui/process_model.py`: `RESTRICTED` shown as restricted, `UNRESOLVED` shown as unresolved, `CONTAINERIZED` showing the truncated container ID (FR-009, FR-030, FR-031)
- [X] T069 [US2] Wire the process table into `src/gpum/ui/device_panel.py` grouped by device (FR-007)
- [X] T070 [US2] Implement the attribution-unavailable state in `src/gpum/ui/device_panel.py`: when a device's `attribution` is not `AVAILABLE`, show the reason in place of the table (US2 scenario 4)
- [X] T071 [US2] Add a hardware-marked container test in `tests/integration/test_container_attribution.py` (`@pytest.mark.hardware`) matching quickstart V-8

**Checkpoint**: US1 and US2 both work independently. Quickstart V-2, V-3, and V-8 pass.

---

## Phase 5: User Story 3 - One tool across mixed vendors and platforms (Priority: P3)

**Goal**: One unified list regardless of vendor, honest degradation everywhere, and a usable tool
on machines with no GPU at all.

**Scope note**: real AMD and Intel backends are **not** in this release. This story delivers the
unified presentation, the discovery reporting, and the degradation paths — validated through the
stubs and fake scenarios — so that a later vendor backend is additive.

**Independent Test**: `--backend none` opens a usable window explaining what was found per
vendor; `--scenario multi-vendor-degraded` shows devices from several vendors in one list with
consistent units while one is degraded.

### Tests for User Story 3 (write first, must fail)

- [X] T072 [P] [US3] Write failing tests in `tests/integration/test_no_gpu.py` asserting the app starts, reports per-backend discovery detail, and stays usable with zero devices (FR-018, SC-006, U-05)
- [X] T073 [P] [US3] Write failing tests in `tests/integration/test_sampling_lifecycle.py` for hot-plug: a new device key appears with empty history, a vanished key is removed, a returning key resumes its prior history (FR-020, research D-08)
- [X] T074 [P] [US3] Write failing tests in `tests/unit/test_mig_detection.py` asserting a MIG-enabled device is emitted `supported=False` with a reason and no metrics (C-08, FR-028)
- [X] T075 [P] [US3] Write failing UI tests in `tests/integration/test_ui_updates.py` for U-02 (a backend blocking 5 s leaves the UI responsive) and U-03 (other devices keep updating while one is `DEGRADED`)

### Implementation for User Story 3

- [X] T076 [US3] Implement MIG detection via `nvmlDeviceGetMigMode` in `src/gpum/backends/nvidia/backend.py`, emitting the device as unsupported with reason "partitioned GPU (MIG) not supported" (FR-027, FR-028, research D-09)
- [X] T077 [US3] Implement periodic re-enumeration every 10th cycle in `src/gpum/core/engine.py`, emitting a discovery change when the device set differs (FR-020, research D-08)
- [X] T078 [US3] Handle `DeviceGoneError` in `src/gpum/core/engine.py` by triggering immediate re-enumeration rather than surfacing an error
- [X] T079 [US3] Preserve history across device disappearance and return, keyed on `DeviceId.key`, in `src/gpum/core/history.py` (research D-07)
- [X] T080 [US3] Implement `src/gpum/ui/discovery_panel.py` rendering the `DiscoveryReport` — one line per backend including stubs, e.g. "AMD: not implemented in this release" (FR-018, SC-006)
- [X] T081 [US3] Implement the empty state in `src/gpum/ui/main_window.py`: with zero devices, show the discovery panel prominently instead of a blank window (SC-006)
- [X] T082 [US3] Render unsupported devices in `src/gpum/ui/device_panel.py` with their reason and suppressed metrics (FR-028)
- [X] T083 [US3] Enforce one unified device list with consistent units and column labels across vendors in `src/gpum/ui/main_window.py`, sourcing all formatting from `core/units.py` (FR-004, US3 scenario 1)
- [X] T084 [US3] Render `STALE` and `DEGRADED` states in `src/gpum/ui/device_panel.py` with the value's true age from `sampled_at` (FR-016)
- [ ] T085 [US3] Run spike S-04: verify NVML's error surface when the driver restarts under a running process, and implement handle rebuilding in `src/gpum/backends/nvidia/backend.py` if re-init alone does not recover
- [X] T086 [US3] Create `docs/capability-matrix.md` recording every vendor × platform × metric combination and its current support state (constitution Principle II)

**Checkpoint**: All three primary stories work independently. Quickstart V-4 and V-5 pass.

---

## Phase 6: User Story 4 - Tune the view to the task (Priority: P4)

**Goal**: Adjustable refresh interval, pause, stable sorting, and preferences that survive a
restart.

**Independent Test**: Change interval and sort order, confirm the cadence and ordering change,
restart, and confirm both persist.

### Tests for User Story 4 (write first, must fail)

- [X] T087 [P] [US4] Write failing tests in `tests/integration/test_ui_updates.py` for U-06 (interval change takes effect next cycle; pause halts emissions) and U-09 (sort order stable across refreshes, no reshuffling)
- [X] T088 [P] [US4] Write failing tests in `tests/integration/test_preferences.py` asserting interval, sort order, and geometry round-trip across a simulated restart (FR-023)
- [X] T089 [P] [US4] Write failing tests in `tests/integration/test_ui_updates.py` for U-07 (hiding the window throttles sampling) (FR-015)

### Implementation for User Story 4

- [X] T090 [P] [US4] Implement `QSettings` persistence in `src/gpum/ui/preferences_store.py`, reading and writing the Qt-free `Preferences` dataclass (research D-10)
- [X] T091 [US4] Implement queued `set_interval` and `set_paused` slots in `src/gpum/ui/sampler_worker.py`, applying changes at the next cycle boundary and never mid-cycle (FR-012)
- [X] T092 [US4] Recompute `DeviceHistory` capacity when the interval changes in `src/gpum/core/history.py` so the retention window stays constant and the memory bound holds (FR-024)
- [X] T093 [US4] Implement stable multi-key sorting in `src/gpum/ui/process_model.py` with `(device_key, pid, started_at)` as tiebreaker so equal values never reshuffle between refreshes (FR-010)
- [X] T094 [US4] Implement `src/gpum/ui/settings_dialog.py` for refresh interval, history window, and hidden-window throttling
- [X] T095 [US4] Implement pause/resume control in `src/gpum/ui/main_window.py` (FR-012)
- [X] T096 [US4] Implement visibility-based throttling in `src/gpum/ui/main_window.py`, signalling the worker on hide, minimize, and deactivate (FR-015)
- [X] T097 [US4] Persist and restore window geometry and sort state in `src/gpum/ui/main_window.py` (FR-023)

**Checkpoint**: All four user stories complete. Quickstart V-6 passes.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T098 [P] Write the 24-hour soak test in `tests/integration/test_soak.py` at accelerated cadence asserting no unbounded memory growth and no cadence loss (U-10, FR-024, SC-005)
- [X] T099 [P] Write a no-egress test in `tests/integration/test_no_network.py` asserting zero socket creation during a full sampling cycle (FR-022, SC-010)
- [X] T100 [P] Write an unprivileged-run test in `tests/integration/test_no_elevation.py` asserting every code path completes without elevation (FR-019, SC-008, A-11)
- [X] T101 Add a read-only assertion test in `tests/unit/test_read_only.py` confirming no module calls process-termination or hardware-tuning APIs (FR-021, Principle V)
- [X] T102 [P] Verify the U-01 GUI-thread budget under load: 8 devices × 200 processes, no slot exceeding 16 ms, in `tests/integration/test_ui_updates.py` (SC-003, Principle III)
- [X] T103 Document the timeout limitation at the call site in `src/gpum/core/engine.py` — a timeout abandons the wait, not the call; a hung driver call holds its pool thread (contracts/ui-update-contract.md)
- [X] T104 [P] Write `docs/adding-a-vendor.md` from quickstart.md § Adding a vendor backend later
- [X] T105 [P] Expand `README.md` with install (`pip install gpum[nvidia]`), run, and the supported-platform matrix
- [X] T106 [P] Verify third-party licence compatibility and record it in `docs/licenses.md` (constitution tech constraints)
- [X] T107 Confirm packaging installs and launches **on Linux** from wheels with no compiler toolchain present (constitution tech constraints). Scope narrowed with the Windows target; the Linux half was verified.
- [X] T108 Run the full quickstart.md validation V-1 through V-6 on Linux and record results
- [~] T109 ~~Run quickstart V-1 through V-8 on Windows~~ **DROPPED — Windows is no longer a target** (constitution 2.0.0). V-1 through V-6 on Linux are recorded under T108.
- [X] T110 Resolve the open Principle II violation. **Resolved 2026-08-17 by constitution amendment 2.0.0**: Principle II was narrowed from a three-platform mandate to Linux only, so the macOS deferral is no longer a deviation — there is nothing left to deviate from. The architecture half of the principle (adapters, no OS conditionals in feature code, visible degradation) was retained deliberately.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: depends on Setup — **blocks every user story**
- **US1 (Phase 3)**: depends on Foundational
- **US2 (Phase 4)**: depends on Foundational; integrates with US1's device panel but is independently testable via fake scenarios
- **US3 (Phase 5)**: depends on Foundational; exercises US1's device rendering but its own paths (discovery, empty state, degradation) are independently testable
- **US4 (Phase 6)**: depends on Foundational; touches US1 and US2 surfaces
- **Polish (Phase 7)**: depends on the desired stories being complete

### Critical path

`T001 → T002 → T008–T013 (tests) → T014–T017 (models) → T020 (protocol) → T022 (fake) → T026 (registry) → T028–T029 (engine) → T036–T041 (NVIDIA) → T042–T047 (UI) → MVP`

### Within each user story

Tests are written first and must fail. Then models → protocols → backends/adapters → core wiring
→ UI. Spikes (T050, T060, T063, T085) gate the tasks that consume their findings.

### Parallel opportunities

- T003–T007 (Setup) all parallel
- T008–T013 (Foundational tests) all parallel — six different files
- T018–T021, T024–T025 parallel; T014–T017 are **not** (one file, `core/models.py`)
- T032–T035, T051–T055, T072–T075, T087–T089 — each story's test tasks are parallel
- T056–T058 parallel (three adapter files)
- T098–T100, T104–T106 parallel
- With staffing, US2/US3/US4 can proceed concurrently once Foundational is done

---

## Parallel Example: Foundational tests

```bash
# All six failing-test tasks touch different files — launch together:
Task: "Write failing MetricValue invariant tests in tests/unit/test_models.py"
Task: "Write failing unit-normalization tests in tests/unit/test_units.py"
Task: "Write failing import-boundary tests in tests/unit/test_import_boundaries.py"
Task: "Write failing backend contract suite in tests/contract/test_backend_protocol.py"
Task: "Write failing history-bound tests in tests/unit/test_history_bounds.py"
Task: "Write failing engine timeout/degradation tests in tests/unit/test_engine.py"
```

## Parallel Example: User Story 2 adapters

```bash
Task: "Implement Linux process identity in src/gpum/adapters/linux/identity.py"
Task: "Implement Windows process identity in src/gpum/adapters/windows/identity.py"
Task: "Implement container resolution in src/gpum/adapters/linux/containers.py"
```

---

## Implementation Strategy

### MVP (User Story 1 only)

1. Phase 1 Setup
2. Phase 2 Foundational — **critical, blocks everything**
3. Phase 3 US1
4. **STOP and VALIDATE**: quickstart V-1 (fake) and V-7 (real NVIDIA)
5. Demo — a working live GPU memory monitor

### Incremental delivery

1. Setup + Foundational → foundation ready, full suite green with no GPU
2. + US1 → **MVP**: live device memory and utilization
3. + US2 → process attribution (Linux full; Windows honestly degraded until T064)
4. + US3 → unified list, no-GPU handling, degradation, MIG
5. + US4 → preferences and view tuning
6. + Polish → soak, packaging, docs, governance

### Notes on ordering risk

- **T060 and T063 are spikes on Windows hardware.** If unavailable, US2 still ships: Linux gets
  full attribution and Windows correctly reports it unavailable (FR-017). Do not fake it to fill
  the gap — that is the exact failure SC-007 exists to prevent.
- **T050 sets the timeout from measurement.** Until it runs, 500 ms is a placeholder, not a
  decision.
- **T110 is a governance task, not code**, and does not block any implementation.

---

## Notes

- `[P]` = different files, no dependencies
- Every task names its exact file path
- Tests are mandatory per constitution Principle IV and must fail before implementation
- A failing `tests/unit/test_import_boundaries.py` is a constitution violation — fix the import,
  never relax the test
- Commit after each task or logical group; stop at any checkpoint to validate a story


---

## Implementation status — 2026-08-16

**Scope executed**: `/speckit-implement "Implement Linux application"`. 98 of 110 tasks complete.
The full suite is **457 passed, 3 skipped, 7 hardware-deselected**, lint clean.

### Not completed, and why

| Task | Reason |
|---|---|
| T033 | Recording real NVML response fixtures requires an NVIDIA machine. The error-mapping layer is fully tested with pure-data tests instead (`tests/unit/test_nvml_mapping.py`), and `tests/unit/test_mig_detection.py` uses a hand-written NVML stub. |
| T050 | Spike S-03 — measuring a real multi-GPU sampling cycle. The 500 ms per-device timeout remains a documented placeholder, not a decision. |
| T057, T063, T064, T065 | Windows adapters (identity, PDH spike, PDH provider, registration). Out of scope for "Linux application". `adapters/__init__.py` already routes to them, so they are additive. |
| T060 | Spike S-02 — confirming WDDM per-process behaviour needs a Windows NVIDIA machine. The handling is implemented (`attribution.py` maps a `None` memory figure to `UNSUPPORTED` with a WDDM-specific reason); only the empirical confirmation is outstanding. |
| T085 | Spike S-04 — driver-restart recovery needs hardware. `DeviceGoneError` handling and re-enumeration are implemented and tested against the fake backend. |
| T094 | A separate settings dialog. The toolbar covers interval, sort, pause, and refresh; a dialog would add surface without capability. Deferred deliberately. |
| T107, T109 | Cross-platform packaging and the Windows quickstart run. Linux verified; Windows unverified. |
| T110 | Governance: the open Principle II (macOS) deviation. Requires a decision, not code. |

---

## Status revision — 2026-08-17: Windows and macOS dropped as targets

The table above is superseded where it conflicts with this section. Windows and macOS are no
longer targets (constitution amended to **2.0.0**), and an audit of the tree found four
checkboxes that were stale rather than outstanding. **104 of 110 tasks are now complete, 5 are
dropped, and 1 remains genuinely outstanding.**

### Checkboxes that were wrong — the work was already done

| Task | Found in the tree |
|---|---|
| T033 | `tests/fixtures/nvml/rtx5060ti-580.159.03.json` exists, recorded from real hardware (driver 580.159.03) and including an `error_responses` section with failure modes. Consumed by `tests/unit/test_nvml_fixtures.py`. The 2026-08-16 note predates the hardware verification in feature 002. |
| T094 | `src/gpum/ui/settings_dialog.py` exists and is wired at `src/gpum/ui/app.py:86`, with coverage in `tests/integration/test_settings_dialog.py`. The "deferred deliberately" reasoning was reversed and the note was never updated. |
| T107 | The Linux half was verified; only the Windows half was not, and it is now out of scope. |
| T057 | Was implemented in the Windows adapter, then deleted with it — see below. |

### Dropped, not deferred

T057, T060, T063, T064, T065 and T109 are dropped. A deferred task implies a commitment; there
is none. The Windows adapter package (`src/gpum/adapters/windows/`) and its tests were **deleted**
rather than left in place, because partially-built platform code reads as a promise of support —
which is the same class of fault as rendering an unmeasured metric as zero.

Two things deliberately survived the deletion:

- **`src/gpum/adapters/psutil_identity.py`** — the OS-agnostic identity lookup that T057
  introduced. It is what the Linux provider now uses, and it needed no Windows to justify it.
- **The nullable per-process memory path.** `NvmlProcessInfo.used_gpu_memory` is still
  `int | None`, and a `None` still becomes `UNSUPPORTED` with a reason. Only the reason *text*
  changed, from naming WDDM to naming the driver generically. This was the honest-degradation
  guarantee, not Windows scaffolding.

### Still outstanding

| Task | Reason |
|---|---|
| T050 | Spike S-03 needs multi-GPU hardware. Note that feature 002 has since measured per-device cost on single-GPU hardware (0.119 ms p99, later 3.832 ms p99 with power) and set the timeout from it, so the "500 ms placeholder" description is itself out of date — but the multi-GPU measurement was never taken. |
| T085 | Split verdict. The **implementation half is done**: handle rebuilding after a driver restart is at `src/gpum/backends/nvidia/backend.py:159`, tested in `tests/unit/test_driver_recovery.py`. Only the empirical spike — restarting a real driver under a running process — is outstanding, and it needs hardware. |

### Resolved

**T110 is closed.** The Principle II violation is gone because the principle no longer makes the
claim that was being violated. This is worth stating plainly rather than dressing up: the
three-platform mandate was never met, from feature 001 onward, and the fix chosen was to narrow
the promise to what is actually delivered rather than to keep carrying a deviation. The
capability matrix is a single column now, and every cell in it is a measurement.

### Design corrections made during implementation

Two layering errors in `plan.md` were caught by `tests/unit/test_import_boundaries.py` and fixed:

1. **`core/registry.py` → `gpum/registry.py`.** A registry must construct backends, so leaving it
   in `core` inverted the dependency arrow. It is a composition root and now sits above `core`.
2. **Attribution types moved from `adapters/base.py` to `core/attribution.py`.** A vendor backend
   may ship a companion attribution provider (NVIDIA does), and `backends` importing `adapters`
   crosses a forbidden layer. The protocols stay in `adapters/base.py`; the data types moved.

A third was caught before coding: `core/sampler.py` was split into the Qt-free
`core/engine.py` plus `ui/sampler_worker.py`, because `core` must import without a
`QApplication`.

**Noted deviation**: the constitution states `backends` MUST NOT import `core`. Taken literally
this is unimplementable — a backend returns normalized `core` models by design. The enforced rule
is the one the layering actually needs: **`core` must not import `backends`**, and backends may
import `core.models` as shared vocabulary. Worth reconciling in the constitution's wording.
