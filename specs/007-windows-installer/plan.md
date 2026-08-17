# Implementation Plan: Windows Executable & Installer

**Branch**: `007-windows-installer` | **Date**: 2026-08-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-windows-installer/spec.md`

## Summary

Produce two Windows artifacts — an installer and a portable executable — from the PyInstaller
build the Linux bundle already uses, and verify on real Windows hardware that what they report
is true.

Phase 0 found that this is **not purely a packaging feature**. Windows testing already runs in
CI on three Python versions, and preference storage already resolves correctly on Windows. What
does not work is the settings dialog: `ui/app.py` imports `gpum.adapters.linux.autostart`
unconditionally, so on Windows the autostart toggle would report its location as
`C:\Users\<user>\.config\autostart\gpum.desktop`, write a file nothing reads, and report
success. That is a fabricated capability claim on the platform this feature exists to serve,
and it is exactly what US2 forbids. The import-boundary tests do not catch it because they
forbid OS *branching* outside adapters, not importing a platform module by name.

So the work is three strands: **build** the artifacts, **fix** the platform-parity defect
Windows delivery exposes, and **verify** on hardware rather than inferring.

## Technical Context

**Language/Version**: Python 3.11+ (unchanged)

**Primary Dependencies**: unchanged at runtime. Build-time only: PyInstaller (already used for
the AppImage) and Qt Installer Framework.

**Storage**: unchanged — `QSettings` already resolves to `HKCU\Software\gpum\gpum` on Windows.

**Testing**: `pytest` + `pytest-qt`, headless. The default suite must stay GPU-free; Windows
artifact checks run under the existing `packaging` marker, hardware checks under `hardware`.

**Target Platform**: 64-bit x86 Windows 10 (21H2+) and Windows 11. ARM64 out of scope.

**Project Type**: Single-project desktop application (unchanged)

**Performance Goals**: window visible with real data within 5 s of launch (SC-003). This is the
one number the packaging choice can break, and it is why the installed form is a directory
build rather than a single file.

**Constraints**: no administrator privileges at any point; no network at install or run; no
vendor driver library inside the artifact; artifacts unsigned this release but the build must
stay signable.

**Scale/Scope**: two artifacts, one new platform adapter module, one CI job.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial evaluation (pre-research)

| Gate | Status | Basis |
|------|--------|-------|
| **I. Vendor-Agnostic Abstraction** | ✅ PASS | No backend is touched. |
| **II. Platform Parity by Capability** | ❌ **FAIL** | `ui/app.py` imports a Linux adapter directly; Windows would claim an autostart capability it does not have. The capability matrix also has no observed Windows column. |
| **III. Non-Blocking Live Updates** | ✅ PASS | No change to sampling or the UI update path. |
| **IV. Test-First on Simulated Hardware** | ⚠️ AT RISK | Artifact checks are inherently machine-specific; they must not gate the default GPU-free suite. |
| **V. Read-Only, Least Privilege** | ⚠️ AT RISK | An installer writes files and a startup entry — both outside "its own saved user preferences". |

**Gate result before research**: FAIL on Principle II. This is not a reason to stop; it is the
finding that shapes the feature. Proceeding to Phase 0 with the defect as a required fix.

### Post-design re-evaluation (after Phase 1)

| Gate | Status | Resolution |
|------|--------|------------|
| **I. Vendor-Agnostic Abstraction** | ✅ PASS | Unchanged. |
| **II. Platform Parity by Capability** | ✅ PASS | Autostart moves behind the single OS switch in `adapters/__init__.py` (D-07), a Windows implementation lands beside the Linux one (D-06), and a new boundary test forbids `ui` importing any `adapters.<platform>` module — closing the hole that let the defect through. The capability matrix gains an observed Windows column (D-13). |
| **III. Non-Blocking Live Updates** | ✅ PASS | Unchanged. The 5 s launch budget is met by shipping a directory build rather than a self-extracting one (D-02). |
| **IV. Test-First on Simulated Hardware** | ✅ PASS | Artifact checks run under the existing `packaging` marker and hardware comparison under `hardware`; neither gates the default suite, which stays GPU-free and passes on any machine. |
| **V. Read-Only, Least Privilege** | ⚠️ **DEVIATION RECORDED** | Per-user only, no elevation, fully reversible. See Complexity Tracking — this extends a deviation the project already recorded for Linux autostart rather than opening a new one. |

**Gate result**: passes with one recorded deviation, consistent with the precedent already set.

## Project Structure

### Documentation (this feature)

```text
specs/007-windows-installer/
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/windows-distribution-contract.md
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks output — not created here
```

### Source Code (repository root)

Changes only. Note how little of `src/` moves: the application is already cross-platform, and
the one file that is not is the defect this feature fixes.

```text
src/gpum/
├── adapters/
│   ├── __init__.py         # CHANGED: autostart joins the single OS switch
│   └── windows/
│       └── autostart.py    # NEW: HKCU Run entry, mirroring the Linux module's contract
└── ui/
    └── app.py              # CHANGED: stop reaching into adapters/linux directly

packaging/
├── gpum.spec               # CHANGED: parameterised for both targets, still one spec
└── windows/
    ├── build-windows.ps1   # NEW: PyInstaller → both artifacts → installer
    ├── verify-dist.ps1     # NEW: build-blocking checks (no driver library, no bloat)
    └── installer/          # NEW: Qt Installer Framework config and package tree

tests/
├── packaging/
│   └── test_windows_artifacts.py   # NEW: runs on Windows, no GPU required
├── hardware/
│   └── test_windows_agreement.py   # NEW: needs a Windows machine with an NVIDIA GPU
└── unit/
    └── test_import_boundaries.py   # CHANGED: ui must not import adapters.<platform>

docs/
├── building.md             # CHANGED: the Windows build, and why it is what it is
├── capability-matrix.md    # CHANGED: Windows becomes observed rather than inferred
└── installing-windows.md   # NEW: including the warning users will actually meet

.github/workflows/ci.yml    # CHANGED: a windows-bundle job beside the AppImage one
```

**Structure Decision**: no new module layer and no second build system. The Windows artifacts
come from the same PyInstaller spec as the AppImage, and Windows autostart lands as a sibling of
the Linux one behind the existing adapter switch. The only genuinely new tree is
`packaging/windows/`, which is build tooling rather than application code.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **The installer writes files and a Start menu entry outside the tool's own preference store** (Principle V) | An installer that installs nothing is not an installer. FR-001 and the constitution's own distribution clause require a Windows user to reach a working application without a toolchain. | *Portable executable only* — rejected because it leaves no Start menu entry, no uninstall path, and no discoverable application, which fails US1 for the users least able to work around it. It is shipped **as well** (US4), not instead. |
| **Windows autostart writes an `HKCU` Run entry** (Principle V) | FR-004 offers start-at-login as an option, and the setting already exists in the UI for Linux. | *Leave the toggle Linux-only* — rejected because the toggle is already visible on Windows and currently lies about what it did. Removing it silently on Windows is also acceptable, but a working implementation is the better outcome for the same effort, and it makes the two platforms honest in the same way. |

Both are **per-user, never elevated, user-initiated, and reversible** — the installer through its
uninstaller, the Run entry through the same toggle that set it. This extends the deviation
`adapters/linux/autostart.py` already records with a proposed amendment; it does not open a new
category. The proposed amendment should now cover both platforms.

**Not a deviation**: shipping unsigned. Signing is a distribution-identity decision the
requester deferred, with the build kept signable (D-08). The constitution requires license
compatibility and honest degradation, neither of which signing affects.
