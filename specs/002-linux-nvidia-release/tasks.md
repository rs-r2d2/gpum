---

description: "Task list for 002-linux-nvidia-release"
---

# Tasks: Linux + NVIDIA Release Readiness

**Input**: Design documents from `/specs/002-linux-nvidia-release/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Mandatory, not optional — constitution Principle IV requires tests written and failing
before implementation. Every phase leads with its failing tests.

**Organization**: Grouped by user story. Builds on feature 001, which is already implemented and
green (457 tests).

**Scope**: Linux + NVIDIA only. No monitoring capability changes — `core/` and `backends/` are
touched only for suspend/resume and driver-restart recovery.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US4 from spec.md
- Exact file paths in every task

---

## Phase 1: Setup

- [X] T001 Add `packaging` and `hardware` pytest markers to `pyproject.toml`, both deselected by default alongside the existing `hardware` marker, so the GPU-free suite stays green
- [X] T002 [P] Create the `packaging/` and `tools/` directory skeletons per plan.md § Project Structure, outside `src/` so build tooling never reaches the runtime import path
- [X] T003 [P] Create `tests/hardware/` and `tests/packaging/` with `__init__.py` and marker-applying `conftest.py` in each
- [X] T004 [P] Add the build-time extras group `packaging = ["pyinstaller"]` to `pyproject.toml`, kept out of the runtime dependencies
- [X] T005 [P] Create the application icon at `src/gpum/resources/gpum.svg` and ensure it is included as package data

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Types and preference fields every story below depends on.

### Tests (write first, must fail)

- [X] T006 [P] Write failing tests for the three new preference fields (`tray_enabled`, `close_notice_shown`, `start_hidden`) and their defaults in `tests/integration/test_preferences.py`
- [X] T007 [P] Write failing tests for `DistributionForm` detection in `tests/unit/test_distribution.py`, covering the source, package, and simulated-bundle cases

### Implementation

- [X] T008 Add `tray_enabled`, `close_notice_shown`, and `start_hidden` to the `Preferences` dataclass in `src/gpum/core/preferences.py`, keeping it Qt-free; deliberately do **not** add `autostart_enabled` — the file's presence is the single source of truth (data-model.md)
- [X] T009 Persist the three new fields in `src/gpum/ui/preferences_store.py`
- [X] T010 Implement `DistributionForm` detection and a single version source in `src/gpum/distribution.py` per research D-13
- [X] T011 Add `--version` to `src/gpum/__main__.py`, reporting identically from both distribution forms (FR-026)
- [X] T012 Extend `tests/unit/test_import_boundaries.py` to cover the new modules: `adapters/linux/*` may branch on the OS, `ui/tray.py` may not import any DBus library, and nothing under `src/` may import `packaging/` or `tools/`

**Checkpoint**: `pytest` green with no GPU and no bundle.

---

## Phase 3: User Story 2 - Verified against real hardware (Priority: P1) 🎯 MVP

**Goal**: Every claim the tool makes about NVIDIA GPUs on Linux confirmed against a physical GPU.

**Why first**: feature 001's entire suite ran without a GPU. Packaging an unverified tool just
distributes it faster. This story also closes 001's deferred T033, T050, and T085.

**Independent Test**: run the comparison harness for 10 minutes under varying load and confirm
agreement within tolerance.

### Tests for User Story 2 (write first, must fail)

- [X] T013 [P] [US2] Write the failing agreement test in `tests/hardware/test_nvidia_smi_agreement.py` (`@pytest.mark.hardware`): memory deviation ≤ 5%, process match rate 100% (SC-003, SC-004)
- [X] T014 [P] [US2] Write the failing driver-restart test in `tests/hardware/test_driver_restart.py` asserting devices stay listed while unavailable and recover without restarting the tool (FR-014)
- [X] T015 [P] [US2] Write failing tests in `tests/unit/test_driver_recovery.py` driving the recovery state machine through an NVML stub, so the logic is testable with no GPU (Principle IV)

### Implementation for User Story 2

- [X] T016 [US2] Implement the concurrent comparison harness in `tools/compare-with-nvidia-smi.py`, sampling the tool and `nvidia-smi` **simultaneously** — sequential sampling measures the delay between them, not their agreement (research D-12)
- [X] T017 [US2] Emit a `HardwareVerificationRecord` as JSON from the harness, including `mean_cycle_cost_ms` and `p99_cycle_cost_ms` per data-model.md
- [X] T018 [US2] Run the harness for 10 minutes under varying GPU load on the reference machine and commit the result as `specs/002-linux-nvidia-release/verification.json` (FR-007, FR-008)
- [X] T019 [US2] **Closes 001-T050**: set the per-device timeout in `src/gpum/core/engine.py` from the measured p99, replacing the 500 ms placeholder, and record the measurement as its justification (FR-009)
- [X] T020 [US2] Implement `DriverRestartEvent` and the ACTIVE → RECOVERING → ACTIVE state machine in `src/gpum/backends/nvidia/backend.py`: shut down NVML, re-init, and **rebuild all handles** — a stale handle returns errors forever, leaving the tool permanently broken until restarted (research D-11)
- [X] T021 [US2] Keep devices listed with metrics marked unavailable while recovering, rather than removing them — removing would flash the whole device list away and discard history for a GPU that never left (data-model.md)
- [X] T022 [US2] **Closes 001-T085**: run spike S-02 on real hardware, capture the NVML error sequence across a driver restart, and tune T020's trigger conditions to match
- [X] T023 [US2] **Closes 001-T033**: capture real NVML responses, including the failure responses from T022, into `tests/fixtures/nvml/` so behaviour proven on hardware stays under test on GPU-free machines (FR-011)
- [X] T024 [US2] Verify FR-015/SC-007 on the reference machine: the NVIDIA GPU is fully monitored **and** the AMD GPU physically present is listed as detected but unsupported — the tool must never report fewer GPUs than the machine has
- [X] T025 [US2] Update `docs/capability-matrix.md` with the verified driver version and what was confirmed against real hardware

**Checkpoint**: the tool's numbers are proven correct. 001's three hardware tasks are closed.

---

## Phase 4: User Story 1 - Install and run it without being the author (Priority: P1)

**Goal**: two distribution forms, both installable by a stranger, behaviourally identical.

**Independent Test**: on a clean machine with no development tooling, follow the published
instructions and reach a running tool showing a real GPU.

### Tests for User Story 1 (write first, must fail)

- [X] T026 [P] [US1] Write failing tests in `tests/integration/test_desktop_entry.py` asserting that with `XDG_*` pointed at a temporary root, install writes only inside it, uninstall removes exactly what it wrote, and nothing is written without an explicit call
- [X] T027 [P] [US1] Write the failing equivalence suite in `tests/packaging/test_appimage_smoke.py` (`@pytest.mark.packaging`) covering E-01 through E-08 from contracts/distribution-contract.md
- [X] T028 [P] [US1] Write a failing test asserting no application module branches on `DistributionForm.kind` outside diagnostics (E-08) in `tests/unit/test_distribution.py`

### Implementation for User Story 1

- [X] T029 [P] [US1] Implement XDG desktop-entry and icon install/remove in `src/gpum/adapters/linux/desktop_entry.py`, writing only under the user's XDG directories (research D-07)
- [X] T030 [US1] Add `--install-desktop-entry` and `--remove-desktop-entry` to `src/gpum/__main__.py` as explicit user actions — wheels have no reliable post-install hook, and writing files as an import side-effect would be worse
- [X] T031 [US1] Create `packaging/Dockerfile.build` based on **Ubuntu 22.04** (glibc 2.35), pinning Python 3.11 (research D-02)
- [X] T032 [US1] Write `packaging/gpum.spec` for PyInstaller with the exclusion list from research D-03: exclude `QtWebEngine`, `QtQuick`, `Qt3D`, `QtMultimedia`, `QtCharts`, translations, and unused platform plugins
- [X] T033 [US1] Add explicit binary exclusions for `libnvidia-*`, `libcuda*`, `libGLX_nvidia*`, and `libglvnd` to `packaging/gpum.spec` — NVML is version-locked to the host driver, and a bundled copy misreports against a different one (research D-03)
- [X] T034 [US1] Create `packaging/AppRun` and `packaging/gpum.desktop`, ensuring no private `XDG_CONFIG_HOME` is set so both forms share `~/.config/gpum/gpum.conf` (FR-028, research D-09)
- [X] T035 [US1] Implement `packaging/verify-appdir.sh` with assertions V-01 through V-06 from contracts/distribution-contract.md
- [X] T036 [US1] Make V-01 (no driver library) and V-02 (no glibc symbol newer than 2.35) **build-blocking** in `packaging/verify-appdir.sh` — both failures are invisible on the build host and only appear on a user's machine
- [X] T037 [US1] Implement `packaging/build-appimage.sh`: PyInstaller → AppDir → `verify-appdir.sh` → `appimagetool`, stamping the version into the filename
- [X] T038 [US1] Make `packaging/build-appimage.sh` refuse to run outside the build container, so a bundle can never be produced against the host's newer glibc (research D-02)
- [X] T039 [US1] Run spike S-04: measure the produced AppImage and revisit the exclusion list if it exceeds 120 MB
- [X] T040 [US1] Run spike S-03: launch the AppImage under `ubuntu:22.04` and confirm `--version` prints, proving the glibc floor holds (quickstart V-13)
- [X] T041 [US1] Add a CI job building the AppImage in the container and running `pytest -m packaging`
- [X] T042 [US1] Rewrite the install section of `README.md` for both forms, including the `chmod +x` step, the minimum driver version, and what degrades on older drivers (FR-006)
- [X] T043 [US1] Walk quickstart V-14 manually: download, `chmod +x`, run — confirming three steps and under 2 minutes (SC-012)

**Checkpoint**: a stranger can install and run the tool by either route.

---

## Phase 5: User Story 3 - Survives what a real desktop does (Priority: P2)

**Goal**: suspend/resume, driver restarts, mixed vendors, and long uptime all handled without a
restart.

**Note**: driver-restart recovery is implemented in US2 (T020–T022) because it is inseparable from
hardware verification. This story covers the rest.

### Tests for User Story 3 (write first, must fail)

- [X] T044 [P] [US3] Write failing tests in `tests/unit/test_resume_detection.py` using feature 001's fake clock: a simulated four-hour jump is detected as a resume, backoff clears, re-enumeration is forced
- [X] T045 [P] [US3] Write a failing test asserting a resume produces an explicit **gap** in history, never an interpolated line — drawing across a suspend asserts measurements never taken (SC-008)
- [X] T046 [P] [US3] Write a failing test in `tests/integration/test_no_display.py` asserting that launching with no graphical session reports the requirement rather than raising an unhandled error (FR-019)

### Implementation for User Story 3

- [X] T047 [US3] Implement `ResumeEvent` and wall-clock gap detection in `src/gpum/core/engine.py` with the `max(10 × interval, 30 s)` threshold, chosen to sit above a degraded device's backoff so slowness is never misread as a suspend (data-model.md)
- [X] T048 [US3] On resume, clear degradation backoff, force re-enumeration, and append an explicit gap to every device history (FR-013)
- [X] T049 [US3] Detect a missing graphical session in `src/gpum/__main__.py` before constructing the application, and print an actionable message (FR-019)
- [X] T050 [US3] Verify Wayland and X11 both work by launching under each session type and recording the result (FR-018)
- [ ] T051 [US3] Run the 24-hour soak on the reference machine with real hardware and record memory footprint at the 1-hour and 24-hour marks (FR-016, SC-006)
- [ ] T052 [US3] Verify container attribution against a real Docker GPU workload per quickstart V-8 (FR-017, SC-012 of feature 001)
- [ ] T053 [US3] Verify suspend/resume for real per quickstart V-10, confirming no negative or duplicated readings and a visible gap

**Checkpoint**: the tool survives an ordinary desktop's disruptions unaided.

---

## Phase 6: User Story 4 - Configure it once and forget it (Priority: P3)

**Goal**: one settings surface, a tray presence, and autostart — with no state where the tool runs
unreachable.

### Tests for User Story 4 (write first, must fail)

- [X] T054 [P] [US4] Write the failing tray-probe suite in `tests/unit/test_tray_probe.py` covering T-01 through T-04 from contracts/tray-contract.md, including **T-02: Qt reporting `True` with no watcher present must yield `usable=False`**
- [X] T055 [P] [US4] Write the failing close-semantics suite in `tests/integration/test_tray_behaviour.py` covering all four rows of the decision table (T-05), against a **fake probe with no DBus** so it runs anywhere
- [X] T056 [P] [US4] Write the failing test for **T-06: with the tray unusable, closing the window quits** — the assertion that makes an unreachable running program impossible (SC-015)
- [X] T057 [P] [US4] Write the failing test for T-10: sampling rate while closed-to-tray equals the hidden-window rate (FR-032, SC-016)
- [X] T058 [P] [US4] Write failing tests in `tests/integration/test_settings_dialog.py` asserting every setting takes effect without a restart and survives a simulated reboot
- [X] T059 [P] [US4] Write failing tests in `tests/unit/test_autostart.py` asserting the autostart file is written only on explicit enable, removed on disable, and that the file's presence is the single source of truth

### Implementation for User Story 4

- [X] T060 [US4] Implement `TrayAvailability` and the DBus `org.kde.StatusNotifierWatcher` ownership probe in `src/gpum/adapters/linux/tray_probe.py`, with a 500 ms timeout and never raising (research D-04)
- [X] T061 [US4] Implement the conjunction rule `usable = watcher_present AND qt_reports_available` in `src/gpum/adapters/linux/tray_probe.py`; a false negative costs an icon, a false positive costs the user a program they cannot recover
- [X] T062 [US4] Treat probe failure as `usable=False` with the error as the reason — unavailable-and-explained, never assumed-working
- [X] T063 [US4] Implement the tray icon and menu (show, pause/resume, quit) in `src/gpum/ui/tray.py`, importing no DBus library and containing no OS branching (contract T-12)
- [X] T064 [US4] Implement close-to-tray in `src/gpum/ui/main_window.py` following all four rows of the decision table, **falling back to quit-on-close whenever the tray is not usable** (FR-034)
- [X] T065 [US4] Implement the one-time close notice gated on `close_notice_shown`, persisted so it appears once per user rather than once per session (FR-030)
- [X] T066 [US4] Verify that closing to tray requires **no sampler change** — feature 001's `hideEvent` already throttles the worker; resist adding background polling to keep the tray fresh (research D-06)
- [X] T067 [US4] Implement window restore from tray showing a reading no older than two intervals (FR-033)
- [X] T068 [P] [US4] Implement XDG autostart write/remove in `src/gpum/adapters/linux/autostart.py`, with the file's presence as the source of truth (research D-08)
- [X] T069 [US4] Add `--hidden` to `src/gpum/__main__.py` so an autostarted instance opens to the tray without stealing focus (FR-022)
- [X] T070 [US4] Implement `src/gpum/ui/settings_dialog.py` gathering refresh interval, history window, tray toggle, and autostart toggle into one surface (FR-020)
- [X] T071 [US4] Surface the tray-unavailable reason in the settings dialog, disabling the toggle with an explanation rather than silently ignoring it
- [X] T072 [US4] Disclose in the settings dialog that enabling autostart writes a file to the user's autostart directory, and that disabling removes it — the Principle V deviation must be visible to the user, not buried
- [X] T073 [US4] Wire the settings dialog into `src/gpum/ui/main_window.py` and ensure every change applies without a restart

**Checkpoint**: all four stories complete.

---

## Phase 7: Polish & Cross-Cutting

- [X] T074 [P] Re-verify the no-network and no-elevation guarantees against both distribution forms (FR-023, SC-011)
- [X] T075 [P] Verify both forms resolve to the same preferences path with a test, not by inspection (FR-028, E-02)
- [X] T076 [P] Update `docs/capability-matrix.md` with verified Linux/NVIDIA status and the tested driver version
- [X] T077 [P] Document the build procedure in `docs/building.md`, stating plainly why the container is mandatory
- [X] T078 Run the full quickstart V-1 through V-15 and record results
- [ ] T079 Complete the release checklist in quickstart.md
- [ ] T080 Resolve the Principle V deviation: propose the PATCH constitution amendment widening "its own saved user preferences" to include user-initiated, user-scoped desktop-integration entries the tool can also remove (plan.md § Complexity Tracking)

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (1)** → **Foundational (2)** → blocks all stories
- **US2 (3)** — no dependencies beyond Foundational. Delivers verified correctness and closes three of feature 001's deferred tasks.
- **US1 (4)** — depends on Foundational; T019's measured timeout should land before the bundle is built so the shipped artefact carries it
- **US3 (5)** — depends on Foundational; independent of US1
- **US4 (6)** — depends on Foundational; independent of US1 and US3
- **Polish (7)** — depends on the desired stories

### Critical path

`T001 → T008 → T013–T018 (verify) → T019 (timeout from data) → T031–T038 (build) → T040 (glibc proof) → shippable`

### Parallel opportunities

- T002–T005 all parallel
- T006–T007, T013–T015, T026–T028, T044–T046, T054–T059 — each story's test block
- T029 and T068 parallel (different adapter files)
- T074–T077 parallel
- With staffing, US1 / US3 / US4 proceed concurrently once Foundational is done

### Ordering risks

- **T019 before T037.** If the bundle is built before the timeout is measured, the shipped artefact
  carries feature 001's placeholder.
- **T022/T023 gate T020's tuning.** Implement recovery first, then tune from the captured error
  sequence rather than guessing.
- **T036 is build-blocking on purpose.** Do not downgrade it to a warning: both failures it catches
  are invisible on the build machine and only appear on a user's.

---

## Implementation Strategy

### MVP (US2 only)

1. Phase 1 Setup → Phase 2 Foundational
2. Phase 3 US2 — hardware verification
3. **STOP and VALIDATE**: `verification.json` shows ≤ 5% deviation and 100% process match
4. At this point the tool is *proven correct*, even though it is not yet easily installable

### Incremental delivery

1. Setup + Foundational → suite green, no behaviour change
2. + US2 → **numbers proven against reality**; 001's T033/T050/T085 closed
3. + US1 → installable by a stranger, both forms
4. + US3 → survives suspend, driver restarts, long uptime
5. + US4 → tray, settings, autostart
6. + Polish → docs, release checklist, governance

### Notes

- The default suite must stay green throughout with no GPU and no bundle. If a change makes
  hardware or a bundle mandatory for `pytest`, that change is wrong (Principle IV).
- **T080 is governance, not code**, and blocks nothing.
- Feature 001's remaining Windows tasks stay out of scope and untouched. *(2026-08-17: those tasks were subsequently dropped outright — Windows is no longer a target.)*


---

## Implementation status — 2026-08-16

75 of 80 tasks complete. **711 default + 15 hardware + 9 packaging tests pass**, lint clean.

### Delivered

- **Hardware verification (US2)**: agreement with `nvidia-smi` measured at **2.21% max
  deviation**, 100% process match over 290 samples. Evidence in `verification.json`.
- **Distribution (US1)**: a **50 MB AppImage**, built in the Ubuntu 22.04 container, verified
  to launch on 22.04 and on this machine's GNOME/X11 session, reporting the same version as the
  pip install. Plus XDG desktop-entry install/remove.
- **Resilience (US3)**: suspend/resume detection with honest history gaps, driver-restart
  recovery with handle rebuild, physical-GPU presence accounting, headless-launch message.
- **Configuration (US4)**: status-area presence with reliable availability detection, the full
  close-semantics decision table, one-time close disclosure, settings dialog, XDG autostart.

### Bugs found by actually running things

| Found by | Bug |
|---|---|
| `nvidia-smi` comparison | **Driver-reserved memory counted as used** — we reported 1021 MiB where nvidia-smi reported 550 MiB, nearly double. NVML v1's `used` is `total - free`. Fixed by preferring the v2 struct. |
| Running the bundle on a real display | **`AppRun` had the wrong library path**, so Qt's xcb plugin could not dlopen `libxcb-cursor.so.0`. Every headless test passed while the bundle was unusable for any real user. |
| Building the bundle | Five further packaging faults — see the table in `docs/building.md`. |
| Checking the discovery output | **The AMD GPU in this machine was never reported.** The tool said "AMD is unsupported" as a category but never that the user's own machine contained an unreadable AMD card. FR-015/SC-007 now satisfied via DRM sysfs presence detection. |
| Reviewing harness output | The process match rate read 100% over **zero samples** — `--query-compute-apps` lists only CUDA processes, and this desktop runs graphics ones. A vacuous pass, now impossible: the harness fails when no processes were compared. |

### Not completed, and why

| Task | Reason |
|---|---|
| T051 | 24-hour soak. Needs 24 hours of wall-clock time. The bounded-memory property is covered structurally by `tests/integration/test_soak.py`. |
| T052 | Container GPU attribution. Requires `nvidia-container-toolkit`, which is not installed on this machine — `docker run --gpus all` is unavailable. The cgroup parsing itself is unit-tested against real cgroup formats. |
| T053 | Suspend/resume on real hardware. Requires actually suspending this machine. The detection logic is tested with a fake clock. |
| T079 | Release checklist. Blocked on T051–T053. |
| T080 | Governance: the Principle V amendment. Requires a decision, not code — see below. |

### Open governance item (T080)

Autostart writes `~/.config/autostart/gpum.desktop`, outside the tool's own preference store.
Constitution Principle V says the tool "MUST NOT modify any system state other than its own
saved user preferences". The write is user-initiated, user-scoped, reversible from the same
toggle, off by default, and disclosed in the settings dialog — but the constitution's wording
forbids it as written.

**Proposed PATCH amendment**: widen Principle V to "its own saved user preferences and
user-initiated, user-scoped desktop-integration entries that it can also remove."

Feature 001's macOS deferral (Principle II) also remains open and unchanged. *(2026-08-17: closed by constitution amendment 2.0.0, which narrowed Principle II to Linux only.)*
