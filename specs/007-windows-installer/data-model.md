# Phase 1 Data Model: Windows Executable & Installer

**Feature**: 007-windows-installer | **Date**: 2026-08-17

This feature adds **no application data**. No metric, device field, preference, or history
series changes. What follows are the build- and install-time entities the feature introduces,
and the one existing type it deliberately leaves alone.

---

## Build-time entities

These exist in `packaging/windows/`. They are not importable Python and hold no runtime state.

### `WindowsTarget`

The shape being built. Two instances, one spec (D-02).

| Field | Values | Notes |
|---|---|---|
| `shape` | `directory` \| `onefile` | Directory is what the installer ships; onefile is the portable artifact |
| `artifact_name` | `GPUM-<version>-win64-setup.exe` \| `GPUM-<version>-win64-portable.exe` | Version comes from the single source of truth in `distribution.py` |
| `console` | always `false` | A console window behind a GUI application is a defect, not a diagnostic |

**Validation**: both shapes MUST be produced by one `gpum.spec` invocation path. A second spec
file is a build fork and is rejected — the same rule that kept one AppImage spec.

### `ExclusionRule`

Extends the tables already in `gpum.spec`, which are Linux-named and need Windows counterparts
(D-03).

| Field | Meaning |
|---|---|
| `reason` | `correctness` \| `size` |
| `platform` | `linux` \| `windows` |
| `prefixes` | Filename prefixes to exclude and to fail the build on if present |

**Validation**: a `correctness` rule MUST be enforced as build-blocking. A `size` rule MAY warn.
The distinction is not cosmetic — a bundled driver library produces wrong numbers on a
stranger's machine, while an oversized artifact merely annoys.

**Windows correctness prefixes**: `nvml.dll`, `nvcuda.dll`, `nvapi64.dll`, `nvfatbinaryloader`.

### `VerificationCheck`

One assertion made against a built artifact, by `verify-dist.ps1`. The Windows counterpart of
`verify-appdir.sh`.

| Field | Meaning |
|---|---|
| `id` | `W-01`, `W-02`, … — stable, referenced by tasks and failure output |
| `blocking` | Whether a failure stops the build |
| `invisible_on_build_host` | Whether this failure would go unnoticed without the check |

**Validation**: every check with `invisible_on_build_host = true` MUST be blocking. That flag is
the whole reason the script exists; a non-blocking check for an invisible failure is decoration.

---

## Install-time entities

State the installer creates on a user's machine. All per-user, all reversible (D-04).

### `InstallLocation`

| Field | Value |
|---|---|
| Application directory | `%LOCALAPPDATA%\Programs\GPUM` |
| Start menu entry | Per-user Programs folder |
| Uninstall registration | `HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\GPUM` |
| Desktop shortcut | Optional, user-selected |

**Validation**: no path under `%ProgramFiles%`, and no write under `HKLM`. Either would require
elevation and breach Principle V. This is assertable by inspecting the installer configuration,
so it is a test rather than a review note.

### `AutostartEntry`

Written only when the user enables the toggle (D-06).

| Field | Value |
|---|---|
| Location | `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` |
| Name | `GPUM` |
| Value | Path to the installed executable, plus the existing `--hidden` flag |

**State transitions**: absent → present (user enables) → absent (user disables, or uninstalls).
The entry's **presence is the single source of truth**, mirroring the rule the Linux module
already states: mirroring it into preferences would create two sources that drift the moment a
user removes it by hand.

**Validation**: enabling then disabling MUST leave the registry as it was found. Uninstalling
MUST remove it.

### `PreferenceStore` *(existing — unchanged)*

Recorded here only to state that it is deliberately untouched (D-05).

| Field | Value |
|---|---|
| Location on Windows | `HKCU\Software\gpum\gpum`, via `QSettings("gpum", "gpum")` |
| Shared by | Python package, portable executable, installed application |

**Validation**: FR-018 is already satisfied by construction. The test that pins it asserts that
all delivery forms resolve the same key — it exists to catch a future change to the org/app
strings, not to verify new work.

**Survives uninstall** (FR-009): the uninstaller MUST NOT remove this key.

---

## The type deliberately not extended

### `DistributionKind` *(existing — no new values)*

`PACKAGE` | `BUNDLE` | `SOURCE`. Both Windows artifacts report `BUNDLE` (D-10).

Adding `WINDOWS_INSTALL` and `PORTABLE` would be the natural-looking change and is the wrong
one. `distribution.py` exists to make the delivery form *unobservable to application logic* —
`tests/unit/test_distribution.py` enforces that only that module and `__main__.py` may even
mention it. New values would create precisely the affordance the module was written to remove.
`bundle_root` already distinguishes the artifacts for diagnostics.

---

## Capability matrix rows affected

Not a code entity, but the record this feature is obliged to update (FR-016) and the place its
honesty is auditable. Every Windows cell moves from inferred to one of:

| Marking | Meaning |
|---|---|
| **observed** | Checked on the physical Windows machine (D-13) |
| **unverified** | Believed from vendor documentation, not seen |
| **unavailable, with reason** | Platform cannot supply it — per-process GPU memory under WDDM |

**Validation**: no Windows cell may be left implicitly claimed (SC-011). A green CI run marks
nothing as observed — CI has no GPU, and conflating the two is the mistake this column exists to
prevent (D-14).
