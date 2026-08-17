# Implementation Plan: Linux + NVIDIA Release Readiness

**Branch**: `002-linux-nvidia-release` | **Date**: 2026-08-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-linux-nvidia-release/spec.md`

## Summary

Feature 001 built a GPU monitor and proved it against simulated devices. This feature makes it
something a stranger can install and trust: two distribution forms, a tray presence, and every
claim verified against a real NVIDIA GPU.

Three findings from Phase 0 shape the work more than anything else:

1. **The bundle must be built on Ubuntu 22.04, not on this machine.** glibc is backward- but not
   forward-compatible, so a bundle built here (glibc 2.39) fails to start on 22.04 — before any of
   the tool's careful error reporting can run. This is the most common way a Linux bundle ships
   broken (research D-02).
2. **NVIDIA driver libraries must be excluded from the bundle, not shipped in it.** NVML is
   version-locked to the host's kernel module; a bundled copy misreports against a different host
   driver. That is silent-wrong-numbers on someone else's machine — the exact failure SC-008
   exists to prevent (research D-03).
3. **`QSystemTrayIcon.isSystemTrayAvailable()` is not a reliable signal.** On stock GNOME it
   reports `True` while the icon is silently dropped, leaving a running program the user cannot
   see or recover. Availability is determined instead by a DBus owner check on
   `org.kde.StatusNotifierWatcher` (research D-04).

**No monitoring capability changes.** `core/` and `backends/` are touched only for suspend/resume
and driver-restart recovery.

## Technical Context

**Language/Version**: Python 3.11+ (unchanged). Build container pins 3.11 for the widest floor.

**Primary Dependencies**: unchanged at runtime — PySide6, psutil, `nvidia-ml-py` (optional extra).
Build-time only: PyInstaller, `appimagetool`.

**Storage**: `QSettings` at `~/.config/gpum/gpum.conf`, shared by both distribution forms
(research D-09). Plus two user-initiated files outside it: the desktop entry and, optionally, the
autostart entry.

**Testing**: `pytest` + `pytest-qt` as before, plus two new categories — `@pytest.mark.hardware`
(real GPU, already established) and `@pytest.mark.packaging` (requires a built AppImage). Both
deselected by default so the GPU-free suite stays green.

**Target Platform**: Linux desktop, glibc 2.35+ (Ubuntu 22.04 and newer, Debian 12, current
Fedora). X11 and Wayland. NVIDIA driver required for GPU data, not for launch.

**Project Type**: Single-project desktop application (unchanged) plus a build pipeline.

**Performance Goals**: unchanged from 001 — 1 Hz default, sub-100 ms interaction, 16 ms GUI-thread
budget. New: AppImage under 120 MB; cold launch to first reading under 5 seconds (SC-001).

**Constraints**: no elevation, no network egress, read-only (all unchanged and re-verified);
tray icon must add zero continuous sampling (FR-032, SC-016); both forms must be behaviourally
identical (FR-026).

**Scale/Scope**: one machine, one user, up to 8 GPUs. Verification target is the development
machine: Ubuntu 24.04, GNOME/X11, RTX 5060 Ti, driver 580.159.03.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial evaluation (pre-research)

| Gate | Status | Basis |
|------|--------|-------|
| **I. Vendor-Agnostic Abstraction** | ✅ PASS | No backend interface changes. Hardware verification strengthens it by testing the NVIDIA implementation against reality for the first time. |
| **II. Platform Parity** | ⚠️ AT RISK | An explicitly Linux-only feature. Tray detection and packaging are Linux-specific and could leak OS branching into feature code. |
| **III. Non-Blocking Live Updates** | ⚠️ AT RISK | Tray presence invites keeping the sampler running while hidden. |
| **IV. Test-First on Simulated Hardware** | ⚠️ AT RISK | A feature whose point is real hardware could easily grow tests that only pass on a GPU. |
| **V. Read-Only, Least Privilege** | ❌ VIOLATION | Autostart writes `~/.config/autostart/gpum.desktop`, outside the tool's own preference store. |

### Post-design re-evaluation (after Phase 1)

| Gate | Status | Resolution |
|------|--------|------------|
| **I. Vendor-Agnostic Abstraction** | ✅ PASS | Driver-restart recovery (D-11) lives entirely inside `backends/nvidia/`. No protocol change; the AMD/Intel stubs are unaffected. |
| **II. Platform Parity** | ✅ PASS | Tray *availability detection* is Linux-specific and lives in `adapters/linux/tray_probe.py`; the tray widget itself uses cross-platform Qt and stays in `ui/`. Packaging lives in `packaging/`, outside the application package entirely. The existing import-boundary test is extended to cover the new modules, so this is enforced rather than intended. |
| **III. Non-Blocking Live Updates** | ✅ PASS | Resolved by *adding nothing* — closing to tray fires the existing `hideEvent`, which already throttles the worker (D-06). A test asserts the sampling rate while closed-to-tray equals the hidden-window rate (SC-016). |
| **IV. Test-First on Simulated Hardware** | ✅ PASS | Tray logic is tested against a fake tray probe with no DBus. The hardware comparison harness captures fixtures (D-12, FR-011) so what it proves once stays under test on GPU-free machines. The default suite must remain green with no GPU and no AppImage. |
| **V. Read-Only, Least Privilege** | ❌ VIOLATION (accepted) | Recorded in Complexity Tracking below. Narrow, user-initiated, reversible, off by default. |

**Gate result**: proceeds with one recorded violation (Principle V, autostart). Principle II's
macOS deferral from feature 001 remains open and unchanged *(2026-08-17: since closed by constitution amendment 2.0.0)* — this feature does not worsen it, but
does not resolve it either.

## Project Structure

### Documentation (this feature)

```text
specs/002-linux-nvidia-release/
├── plan.md              # This file
├── research.md          # Phase 0 — 13 decisions + 4 spikes
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/           # Phase 1
│   ├── distribution-contract.md
│   └── tray-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

Additions and changes only; everything not listed is untouched by this feature.

```text
src/gpum/
├── core/
│   ├── engine.py                # CHANGED: wall-clock gap detection for suspend/resume (D-10)
│   └── preferences.py           # CHANGED: tray_enabled, autostart, close_notice_shown
├── backends/nvidia/
│   └── backend.py               # CHANGED: NVML re-init and handle rebuild on driver restart (D-11)
├── adapters/linux/
│   ├── tray_probe.py            # NEW: DBus StatusNotifierWatcher ownership check (D-04)
│   ├── desktop_entry.py         # NEW: XDG .desktop + icon install/remove (D-07)
│   └── autostart.py             # NEW: XDG autostart entry (D-08)
├── ui/
│   ├── tray.py                  # NEW: QSystemTrayIcon, menu, one-time close notice (D-05)
│   ├── settings_dialog.py       # NEW: interval, history, tray, autostart in one place (FR-020)
│   ├── main_window.py           # CHANGED: close-to-tray, settings dialog entry point
│   └── app.py                   # CHANGED: tray wiring, --hidden launch flag
├── resources/
│   └── gpum.svg                 # NEW: application and tray icon
└── __main__.py                  # CHANGED: --version, --hidden, --install-desktop-entry

packaging/                       # NEW — outside the application package
├── Dockerfile.build             # Ubuntu 22.04 build container (D-02)
├── build-appimage.sh            # PyInstaller -> AppDir -> appimagetool
├── gpum.spec                    # PyInstaller spec with the exclusion list (D-03)
├── AppRun
├── gpum.desktop
└── verify-appdir.sh             # asserts no NVIDIA driver library was bundled (D-03)

tools/
└── compare-with-nvidia-smi.py   # NEW: concurrent comparison harness (D-12)

tests/
├── unit/
│   ├── test_tray_probe.py       # NEW
│   ├── test_resume_detection.py # NEW: fake clock, no hardware
│   └── test_import_boundaries.py # CHANGED: cover adapters/linux/*, packaging/ exclusion
├── integration/
│   ├── test_tray_behaviour.py   # NEW: fake probe, offscreen Qt
│   ├── test_settings_dialog.py  # NEW
│   └── test_desktop_entry.py    # NEW: writes into a tmp XDG root
├── hardware/                    # NEW: @pytest.mark.hardware
│   ├── test_nvidia_smi_agreement.py
│   └── test_driver_restart.py
└── packaging/                   # NEW: @pytest.mark.packaging
    └── test_appimage_smoke.py
```

**Structure Decision**: the application package keeps its 001 layout and its one-way
`backends → core → ui` arrow. Two things are added *outside* it:

- **`packaging/`** is not importable application code. Build tooling inside `src/gpum/` would put
  PyInstaller concerns on the runtime import path and invite the application to reason about how
  it was packaged, which it must not do (FR-026 requires the two forms to be indistinguishable).
- **`tools/`** holds the verification harness, which drives the application from outside as a user
  would, rather than reaching into it.

The one genuinely new architectural element is `adapters/linux/tray_probe.py`. It exists because
the *question* "will a tray icon actually appear?" is Linux-desktop-specific while the *widget* is
cross-platform Qt. Splitting them keeps `ui/tray.py` free of DBus and OS branching, and keeps the
constitution's rule that OS-conditional logic lives only under `adapters/`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **Principle V — autostart writes `~/.config/autostart/gpum.desktop`**, a file outside the tool's own preference store, against "MUST NOT modify any system state other than its own saved user preferences" | FR-022 requires opting into starting with the desktop session, and XDG autostart is the only mechanism that does it without privileges. The write is user-initiated from a settings toggle, user-scoped, reversible by the same toggle, never performed by default, and disclosed in the settings UI. | Doing nothing was rejected because FR-022 is an accepted requirement. A "start me manually" instruction was rejected as not implementing the requirement at all. **Recommended resolution**: a PATCH constitution amendment widening Principle V from "its own saved user preferences" to "its own saved user preferences and user-initiated, user-scoped desktop-integration entries it can also remove". The current wording forbids something the spec asks for. |
| **`packaging/` and `tools/` outside `src/`**, adding two top-level directories | Build tooling and an external verification harness are not application code and must not sit on the runtime import path. FR-026 requires the app to behave identically whether frozen or installed, which is easiest to guarantee when it cannot observe the difference. | Putting them under `src/gpum/` was rejected: it ships build-time dependencies to users and creates the temptation for runtime code to branch on packaging form. A separate repository was rejected as disproportionate for a few hundred lines that must version in lockstep with the app. |
| **A second Linux-specific adapter concept** (`tray_probe`) beyond process attribution | The DBus availability check has no cross-platform meaning, but the tray widget does. Without the split, either `ui/tray.py` grows DBus and OS branching (violating Principle II) or the probe is skipped and FR-034's unreachable-tool failure becomes possible. | Trusting `QSystemTrayIcon.isSystemTrayAvailable()` was rejected on measured grounds — it is the documented false positive on stock GNOME (research D-04), and the failure it causes is a running program the user cannot recover, which SC-015 forbids outright. |
