---
description: "Task list for 007-windows-installer"
---

# Tasks: Windows Executable & Installer

**Input**: Design documents from `/specs/007-windows-installer/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md,
contracts/windows-distribution-contract.md

**Tests**: **Mandatory.** Constitution Principle IV requires tests written and failing before
implementation, and requires the default suite to pass on a machine with no GPU and no vendor
driver. Artifact checks therefore run under the existing `packaging` marker and hardware
comparison under `hardware`; neither may gate the default suite.

**Where tasks run**: this feature cannot be completed from the development machine. Each task is
marked with what it needs:

- *(any)* — runs anywhere, including Linux
- *(win)* — needs a Windows machine
- *(win+gpu)* — needs the physical Windows machine with an NVIDIA GPU

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: `US1`–`US4`, mapping to the user stories in spec.md
- Setup, Foundational, and Polish tasks carry no story label

## Path Conventions

Single project, repository root: `src/gpum/`, `packaging/`, `tests/`, `docs/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Resolve the one question that can invalidate the chosen approach

- [ ] T001 ⛔ **BLOCKED — needs a decision from the project owner** *(any)* Confirm Qt Installer
  Framework licensing and record the finding in `docs/licenses.md` (D-09). **This gates
  everything downstream**: the maintenance tool ships *inside* the artifact users receive, so
  IFW is a distributed component, not a build-time tool, and the constitution requires
  distributed dependencies to be license-compatible. If the terms do not permit it, take the
  recorded fallback in D-01 (Inno Setup) — no design work is lost, only
  `packaging/windows/installer/` changes.

  **Why it is blocked, and it is not IFW's terms.** IFW is distributed under GPL/LGPL, which
  would be assessable — except that *this project declares two different licences for itself*:
  `LICENSE` is plain MIT, while `pyproject.toml` and `docs/licenses.md` both say
  LGPL-3.0-or-later, the latter with a recorded rationale for choosing PySide6 over PyQt6
  specifically to avoid GPL. Compatibility cannot be assessed against a licence that has not
  been decided. Recorded in full in `docs/licenses.md`; this is a licensing decision, not a
  technical one, and it already affects the published AppImage.
- [X] T002 [P] *(any)* Pin the installer-framework version and document how to obtain it, in
  `docs/building.md`, so the build is reproducible rather than dependent on whatever is on the
  builder's machine (FR-020)

**Checkpoint**: the installer technology is confirmed viable and pinned.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Fix the platform-parity defect and teach the build about Windows. Both US1 and US2
depend on this — US1 because the installer offers start-at-login, US2 because the toggle
currently lies.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests first ⚠️

- [X] T003 *(any)* Add a failing rule to `tests/unit/test_import_boundaries.py` asserting that no
  module under `ui/`, `core/`, or `backends/` imports `gpum.adapters.linux.*` or
  `gpum.adapters.windows.*` (D-07). It must fail against the current `ui/app.py` — the existing
  rule catches `sys.platform` branching and missed a direct unconditional import, which is how
  this reached a release
- [X] T004 [P] *(any)* Write failing tests in `tests/unit/test_windows_autostart.py` for
  `is_autostart_enabled`, `enable_autostart`, `disable_autostart`, and `autostart_path`: the
  entry's presence is the single source of truth, enable→disable leaves the registry as found,
  and the reported location is a registry path (U-01, D-06). Fake the registry so the test runs
  on any platform, per Principle IV
- [X] T005 [P] *(any)* Write a failing test in `tests/unit/test_windows_autostart.py` asserting
  the Windows and Linux autostart modules expose the same four functions, so the settings dialog
  needs no platform knowledge (contract § Autostart obligations)

### Implementation

- [X] T006 *(any)* Add an autostart accessor to `src/gpum/adapters/__init__.py`, joining the
  single OS switch that already dispatches identity, attribution, and tray probing (D-07)
- [X] T007 *(any)* Implement `src/gpum/adapters/windows/autostart.py` writing
  `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, value `GPUM`, pointing at the installed
  executable with the existing `--hidden` flag (D-06, depends on T004)
- [X] T008 *(any)* Change `src/gpum/ui/app.py` to resolve autostart through `gpum.adapters`
  instead of importing `gpum.adapters.linux` directly — the defect itself (depends on T006)
- [X] T009 *(any)* Make the exclusion tables in `packaging/gpum.spec` platform-aware, adding the
  Windows correctness prefixes (`nvml.dll`, `nvcuda.dll`, `nvapi64.dll`, `nvfatbinaryloader`) and
  the `Qt6*.dll` size prefixes beside the existing `lib*.so` ones (D-03). Keep one spec — a
  second spec file is a build fork

### Defects found while implementing Phase 2

Both were pre-existing, both were on the platform this feature targets, and neither was in the
plan — the plan found one Windows defect by reading, and implementing the fix surfaced a worse
one next to it.

- [X] T046 *(any)* Implement `src/gpum/adapters/windows/identity.py`. `adapters/__init__.py` has
  selected `gpum.adapters.windows.identity` on Windows since feature 001 and **the module never
  existed**, so `platform_identity_provider()` raised `ModuleNotFoundError`. `ui/app.py:36`
  calls it unguarded during startup, so **GPUM could not launch on Windows at all** — which
  makes US1 acceptance scenario 2 impossible today and means the Windows column of the
  capability matrix could not have been true. Verified by import before the fix
- [X] T047 *(any)* Extract the shared `psutil` lookup into
  `src/gpum/adapters/psutil_identity.py`, used by both platforms. Copying the Linux provider
  would have duplicated the recycled-PID guard, and Principle II prohibits forked
  implementations of the same feature per platform. Container membership is a Linux cgroup
  concept and is injected rather than branched on; Windows supplies no resolver and reports
  processes as ordinary rather than containerized — a smaller claim, not a wrong one
- [X] T048 *(any)* Add `src/gpum/adapters/null_autostart.py` so platforms without an
  implementation report start-at-login as unavailable instead of raising or appearing to succeed

**Checkpoint**: `pytest` green on Linux (977 passed); the settings dialog no longer reaches into
a Linux adapter; GPUM's Windows startup path resolves; no artifact exists yet.

---

## Phase 3: User Story 1 — Install and run without being a developer (Priority: P1) 🎯 MVP

**Goal**: A Windows user with no Python downloads one file, runs it, and finds GPUM in their
Start menu showing their real GPU.

**Independent Test**: On a clean Windows machine with an NVIDIA driver, no Python, and an account
without administrator rights, run the installer and launch from the Start menu (quickstart V-1).

### Tests for User Story 1 ⚠️

- [ ] T010 [P] [US1] *(any)* Write a failing test in `tests/packaging/test_windows_artifacts.py`
  asserting the build produces both artifacts, named from the single version source rather than a
  hardcoded string (FR-017)
- [ ] T011 [P] [US1] *(any)* Write a failing test in `tests/packaging/test_windows_artifacts.py`
  asserting the installer configuration writes **only** under `%LOCALAPPDATA%` and `HKCU` — no
  `%ProgramFiles%`, no `HKLM` (FR-002, D-04). Assertable by inspecting configuration, so it needs
  no Windows machine, and it pins the property that keeps elevation off the normal path
- [ ] T012 [P] [US1] *(any)* Write a failing test in `tests/packaging/test_windows_artifacts.py`
  asserting the installer gates on Windows version and architecture before writing anything
  (FR-023, D-11)

### Implementation for User Story 1

- [ ] T013 [US1] *(win)* Create `packaging/windows/build-windows.ps1` producing the directory
  build from `packaging/gpum.spec` (D-02, depends on T009)
- [ ] T014 [US1] *(win)* Create the installer configuration under
  `packaging/windows/installer/` — per-user target, `HKCU` uninstall registration, offline
  payload (D-04, FR-005)
- [ ] T015 [US1] *(win)* Add the Start menu entry, and the desktop shortcut and start-at-login as
  user-selectable options rather than imposed defaults, in `packaging/windows/installer/`
  (FR-003, FR-004 — start-at-login uses T007)
- [ ] T016 [US1] *(win)* Add the version and architecture gate to the installer script in
  `packaging/windows/installer/`, refusing with a stated reason rather than half-installing
  (FR-023)
- [ ] T017 [US1] *(win)* Verify launch-to-data is within the 5 s budget on the installed build
  and record the measurement in `docs/building.md` (SC-003) — this is the number the packaging
  shape can break, and the reason the installed form is a directory build

**Checkpoint**: a Windows user can install and run GPUM. **MVP.**

---

## Phase 4: User Story 2 — The Windows build tells the truth (Priority: P1)

**Goal**: Every figure on Windows is a real measurement from the host's own driver or an explicit
unavailable state — and no driver library rode along inside the artifact.

**Independent Test**: Compare every reported figure against `nvidia-smi.exe` on the Windows GPU
machine, and inspect the artifact for driver components (quickstart V-2, V-11).

### Tests for User Story 2 ⚠️

- [ ] T018 [P] [US2] *(any)* Write a failing test in `tests/packaging/test_windows_artifacts.py`
  asserting the artifact contains **zero** NVIDIA driver components (FR-012, SC-008). Runs on
  Linux against a built artifact, because the failure is invisible on the machine that produced it
- [ ] T019 [P] [US2] *(any)* Write a failing test in `tests/integration/` asserting per-process GPU
  memory renders as an explicit unavailable state with a reason under a WDDM-like backend, never
  as `0` (FR-014) — exercised headless against the fake backend, per Principle IV
- [ ] T020 [P] [US2] *(win+gpu)* Write failing tests in `tests/hardware/test_windows_agreement.py`
  comparing memory and utilization against `nvidia-smi.exe`, reusing feature 006's **bracketed**
  comparison — the reason for bracketing (a metric moving between two reads) is not
  platform-specific (FR-015, D-13)

### Implementation for User Story 2

- [ ] T021 [US2] *(win)* Create `packaging/windows/verify-dist.ps1` with stable check IDs
  (`W-01`…), mirroring `packaging/verify-appdir.sh`. Every check whose failure is invisible on
  the build host MUST be build-blocking (data-model § VerificationCheck)
- [ ] T022 [US2] *(win)* Wire `verify-dist.ps1` into `packaging/windows/build-windows.ps1` so the
  build **fails rather than emits** a non-conforming artifact (FR-021)
- [ ] T023 [US2] *(win+gpu)* Run the hardware suite on the physical Windows machine and record the
  measured agreement in this file under *Verification results* (D-13, SC-005)
- [ ] T024 [US2] *(any)* Update `docs/capability-matrix.md` from what T023 actually observed,
  marking every Windows cell observed, unverified, or unavailable-with-reason — none left
  implicitly claimed (FR-016, SC-011). A green CI run marks nothing as observed; CI has no GPU

**Checkpoint**: US1 and US2 both work. The tool is installable on Windows *and* honest there.

---

## Phase 5: User Story 3 — Remove it cleanly (Priority: P2)

**Goal**: Uninstall removes everything it installed and keeps the one thing the user wants kept.

**Independent Test**: Install, change a setting, enable autostart, uninstall, and inspect what
remains (quickstart V-5, V-6, V-7).

### Tests for User Story 3 ⚠️

- [ ] T025 [P] [US3] *(any)* Write a failing test in `tests/packaging/test_windows_artifacts.py`
  asserting the uninstall configuration removes the application, Start menu entry, shortcut and
  autostart entry, and does **not** touch `HKCU\Software\gpum` (FR-008, FR-009)
- [ ] T026 [P] [US3] *(win)* Write a failing test in `tests/packaging/test_windows_install.py`
  asserting installing a higher version over an existing installation leaves exactly one
  installation and one uninstall entry (FR-010, SC-007)
- [ ] T027 [P] [US3] *(win)* Write a failing test in `tests/packaging/test_windows_install.py`
  asserting an uninstall attempted while GPUM is running is refused with a stated reason rather
  than partially completing (FR-011)

### Implementation for User Story 3

- [ ] T028 [US3] *(win)* Implement uninstall behaviour in `packaging/windows/installer/`,
  including removal of the autostart entry set via T007 (FR-008)
- [ ] T029 [US3] *(win)* Ensure the uninstall configuration in `packaging/windows/installer/`
  preserves `HKCU\Software\gpum` so a reinstall restores the user's settings (FR-009, D-05)
- [ ] T030 [US3] *(win)* Implement upgrade-over-existing handling in
  `packaging/windows/installer/` (FR-010)
- [ ] T031 [US3] *(win)* Implement running-instance detection and refusal in
  `packaging/windows/installer/` (FR-011, D-12)

**Checkpoint**: the installer is safe to try, because it is safe to remove.

---

## Phase 6: User Story 4 — Run it without installing anything (Priority: P3)

**Goal**: A single file that runs on a machine where installers are blocked by policy.

**Independent Test**: Copy only the portable file to a machine with no GPUM and run it
(quickstart V-9, V-10).

### Tests for User Story 4 ⚠️

- [ ] T032 [P] [US4] *(win)* Write a failing test in `tests/packaging/test_windows_install.py`
  asserting the portable executable runs with no installation present and no elevation (FR-006)
- [ ] T033 [P] [US4] *(any)* Write a failing test in `tests/unit/test_distribution.py` asserting
  `DistributionKind` still has exactly three values and both Windows artifacts report `BUNDLE`
  (D-10, FR-019) — the guard against the tempting change that would let behaviour branch on
  delivery form
- [ ] T034 [P] [US4] *(win)* Write a failing test in `tests/packaging/test_windows_install.py`
  asserting all three delivery forms on one machine report the same version and resolve the same
  preference store (FR-017, FR-018, D-05)

### Implementation for User Story 4

- [ ] T035 [US4] *(win)* Add the single-file target to `packaging/windows/build-windows.ps1` from
  the same spec (D-02, depends on T013)
- [ ] T036 [US4] *(any)* Document the portable form's slower startup in `docs/building.md` as the
  accepted trade of a self-extracting build, so it is not later mistaken for a defect (D-02)

**Checkpoint**: all four stories independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T037 [P] *(any)* Add a `windows-bundle` job to `.github/workflows/ci.yml` on
  `windows-latest`, mirroring the existing `bundle` job: build, run the blocking checks,
  smoke-test headless, upload the artifact (D-14, FR-020)
- [ ] T038 [P] *(any)* Add a comment to the new job in `.github/workflows/ci.yml` stating what it cannot prove — the runner
  has no GPU, so it proves the artifact builds, excludes driver libraries, and launches, and
  nothing about any number (D-14). A green badge must not be mistaken for hardware verification
- [ ] T039 [P] *(any)* Write `docs/installing-windows.md` describing the SmartScreen warning users
  will actually meet, why it appears, and how to proceed — a warning nobody was told to expect is
  indistinguishable from a compromise warning (FR-024, D-08)
- [ ] T040 [P] *(any)* Publish a SHA-256 for each Windows artifact alongside it in `dist/`, giving users an
  authenticity check that does not depend on the operating system's reputation system (FR-025, FR-007)
- [ ] T041 *(win)* Add an optional signing hook to `packaging/windows/build-windows.ps1` that is a
  no-op when unconfigured, and confirm no step assumes an unsigned artifact (FR-026, D-08)
- [ ] T042 [P] *(any)* Document the Windows build in `docs/building.md`, including why the
  installed form is a directory build and the portable form is not (D-02)
- [ ] T043 *(any)* Extend the Principle V deviation note in `src/gpum/adapters/linux/autostart.py`
  and plan.md § Complexity Tracking to cover both platforms, so the proposed amendment matches
  what the code now does
- [ ] T044 *(win+gpu)* Run quickstart V-1 through V-12 and record the results in this file under
  *Quickstart results* — including V-3, which is the check that would catch the Phase 2 defect
  surviving, and V-4, which confirms the new boundary test actually bites
- [ ] T045 *(any)* Attach the Windows artifacts and their checksums from `dist/` to the release carrying the
  existing Linux artifact (FR-022)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 gates everything — a licensing failure changes the installer
  technology, and finding that out after Phase 3 wastes all of it
- **Foundational (Phase 2)**: blocks every user story. T003 precedes T008; T004 precedes T007;
  T006 precedes T008
- **User Story 1 (Phase 3)**: depends on Phase 2 (T009 for the build, T007 for start-at-login).
  This is the MVP
- **User Story 2 (Phase 4)**: depends on Phase 2 and on T013 existing to inspect. **Should ship
  with US1** — an installable build that misreports is the outcome US2 exists to prevent
- **User Story 3 (Phase 5)**: depends on US1, since there must be an installation to remove
- **User Story 4 (Phase 6)**: depends on T013 only; otherwise independent of US2 and US3
- **Polish (Phase 7)**: after the stories, except T037/T038 which are worth landing as soon as a
  build exists

### Within Each User Story

- Tests are written and MUST fail before implementation (Constitution IV)
- Build before installer; installer before uninstall; artifacts before verification

### Parallel Opportunities

- T002 alongside T001's investigation
- T004 and T005 — same new file but separate concerns; coordinate or write sequentially
- T010, T011, T012 — one file, separate test classes
- T018, T019, T020 — different files and different markers, fully parallel
- T025, T026, T027 — separate concerns
- T037–T042 — different files, safe together
- US3 and US4 can be staffed in parallel once US1 lands

### Critical path

`T001 → T003–T009 (parity fixed, spec knows Windows) → T013–T017 (installable) → T021–T024
(honest) → ship`

---

## Implementation Strategy

### MVP first

1. Phase 1 — the licensing question, answered before it can waste anything
2. Phase 2 — the defect fixed and the build taught about Windows
3. Phase 3 (US1) — a Windows user can install and run it
4. **STOP and VALIDATE**: quickstart V-1, V-3
5. Phase 4 (US2) ships with it — see the dependency note above

### Incremental delivery

Phase 2 → US1 (MVP) → US2 (honest) → US3 (removable) → US4 (portable) → Polish. Each increment is
independently testable and none breaks the last.

### What this feature must not repeat

Feature 002 exists because feature 001 shipped unverified. T023 and T044 are the tasks that stop
this one from needing a feature 008 for the same reason — and they are the two tasks that are
easiest to mark done without actually running. They require the physical Windows machine, and no
CI result substitutes for either.

---

## Notes

- **The application barely changes.** Four files under `src/` move, and three of them exist to
  fix one pre-existing defect. Everything else is build tooling, tests, and documentation — which
  is the correct shape for a delivery feature.
- **T003 is the highest-value test in the feature.** The defect it catches shipped because the
  existing boundary rule was written against the wrong shape of the mistake. Confirm it fails
  before T008 and passes after, or it guards nothing.
- Test names should carry their task IDs (`test_t011_…`), so **task IDs must stay stable**.
