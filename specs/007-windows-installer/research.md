# Phase 0 Research: Windows Executable & Installer

**Feature**: 007-windows-installer | **Date**: 2026-08-17

Findings are numbered `D-NN` and referenced from plan.md, tasks, and code comments.

---

## D-01 — Installer technology: Qt Installer Framework

**Decision**: Qt Installer Framework (IFW), as the requester specified. Confirmed as workable
against the constraints rather than accepted on faith.

**Rationale**: It satisfies the three constraints that actually bind here. It installs per-user
without elevation, which Principle V requires. It produces a fully **offline** installer, which
the project's no-network promise requires. Its uninstaller ("maintenance tool") registers an
`HKCU` uninstall entry, so removal works through the ordinary Windows interface (FR-008). Its
install script can gate on OS version and architecture before writing anything (FR-023).

**Alternatives considered**:

| Option | Why not |
|---|---|
| **MSIX** | Requires a signed package to install at all. The requester deferred signing, so this is not merely worse — it is blocked by a decision already taken. |
| **WiX / MSI** | Per-user MSI is possible but awkward, and the ecosystem's defaults pull toward `Program Files` and elevation, which is the opposite of what Principle V wants. |
| **Inno Setup** | Genuinely a strong fit — free, mature, per-user support, smaller output. Not chosen because the requester named IFW, and IFW meets every hard constraint. Recorded because if IFW's licensing (D-09) or size proves unacceptable, this is the fallback that requires no rethinking of the design. |
| **A zip file** | No Start menu entry, no uninstall, no discoverability. This is what US4 already ships as the *portable* option; it does not satisfy US1. |

---

## D-02 — Two build shapes from one spec: directory for install, single file for portable

**Decision**: Reuse `packaging/gpum.spec` for both Windows artifacts. The **installed** form is a
directory build; the **portable** form is a single self-extracting file.

**Rationale**: A single-file build unpacks itself to a temporary directory on every launch. For
a bundle carrying Python and Qt that is seconds of startup, every time — which puts SC-003's 5 s
budget at risk for the delivery path most users take. The installed form has somewhere to live,
so it should live there. The portable form has no such luxury and pays the startup cost by
necessity, which is an acceptable trade for the audience that needs it (US4, P3).

**Consequence**: the two Windows artifacts are not byte-identical payloads and must both be
verified. The contract treats them as one behaviour with two shapes.

**Alternatives considered**: single-file for both (simpler, but taxes the common path);
directory-only (drops US4 entirely).

---

## D-03 — The driver library must come from the host, on Windows too

**Decision**: Exclude every NVIDIA driver component from the artifact and enforce it as a
**build-blocking** check, mirroring `verify-appdir.sh` on Linux.

**Rationale**: Verified directly against the binding rather than assumed. `nvidia-ml-py` is pure
Python over `ctypes` and, on Windows, loads:

1. `%WINDIR%\System32\nvml.dll` — the DCH driver location, tried first
2. `%ProgramFiles%\NVIDIA Corporation\NVSMI\nvml.dll` — the fallback

Both are **absolute paths resolved at call time**, so the binding cannot accidentally bind to a
copy sitting next to the executable. Excluding the library is therefore sufficient *and*
correct, exactly as on Linux. The risk is not the binding; it is PyInstaller's dependency
scanner sweeping a driver DLL into the bundle from the build machine, which is invisible on that
machine because the local driver matches.

**Consequence**: the existing forbidden-prefix table in `gpum.spec` is Linux-named
(`libnvidia-`, `libcuda`, …). It needs a Windows counterpart (`nvml.dll`, `nvcuda.dll`,
`nvapi64.dll`, `nvfatbinaryloader*`), and the same applies to the Qt size-exclusion lists, which
name `libQt6*.so` and must also cover `Qt6*.dll`.

---

## D-04 — Per-user install, never elevated

**Decision**: Install to `%LOCALAPPDATA%\Programs\GPUM`, register the uninstall entry under
`HKCU`, and place the Start menu entry in the per-user Programs folder. Machine-wide install is
not offered.

**Rationale**: Principle V requires the tool to run without administrator privileges, and an
installer that prompts for elevation makes elevation the normal path. A per-user install also
succeeds on managed machines where the user is not an administrator, which is a substantial part
of the Windows audience and a case US1 explicitly covers (acceptance scenario 5).

**Alternatives considered**: `Program Files` with elevation (rejected — makes the privileged
path the default); offering both (rejected — the constitution forbids speculative complexity,
and a second install mode doubles the uninstall and upgrade matrix for no demonstrated need).

---

## D-05 — Preferences already work on Windows; do not touch them

**Decision**: Change nothing. Add an equivalence test.

**Rationale**: `ui/preferences_store.py` uses `QSettings("gpum", "gpum")`, which resolves to
`HKCU\Software\gpum\gpum` on Windows without any platform code. All three delivery forms on one
machine therefore already read and write the same settings, satisfying FR-018 for free. This was
verified by reading the store rather than assumed from the docstring.

**Consequence**: FR-018 costs one test, not an implementation. The test matters anyway — it
pins a property that a future change to the org/app strings would silently break.

---

## D-06 — Windows autostart: an `HKCU` Run entry

**Decision**: Implement `adapters/windows/autostart.py` using
`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, exposing the same four functions the Linux
module does (`is_autostart_enabled`, `enable_autostart`, `disable_autostart`, `autostart_path`).

**Rationale**: User-scoped, no elevation, reversible by deleting one value, and read by Windows
itself — which is the property the current Linux-file-on-Windows behaviour lacks. Mirroring the
Linux module's function contract means the settings dialog needs no platform knowledge.

**Alternatives considered**: a shortcut in the Startup folder — equivalent in effect but requires
writing a `.lnk`, which means either a COM dependency or a shortcut library, for no benefit. The
registry value is one string.

**Deviation note**: this writes outside the tool's own preference store, the same Principle V
deviation `adapters/linux/autostart.py` already records. Recorded in plan.md § Complexity
Tracking; the amendment that module proposes should now cover both platforms.

---

## D-07 — The defect: the UI reaches into a Linux adapter

**Decision**: Move autostart behind the single OS switch in `adapters/__init__.py`, and add an
import-boundary test forbidding `ui` from importing any `gpum.adapters.<platform>` module.

**Rationale**: This is the most important finding of Phase 0 and the reason this feature is not
purely packaging. `src/gpum/ui/app.py:82` does:

```python
from gpum.adapters.linux import autostart
```

unconditionally, inside `_open_settings`. On Windows that resolves
`autostart_path()` to `C:\Users\<user>\.config\autostart\gpum.desktop`, writes a `.desktop` file
that nothing on Windows reads, and reports the toggle as enabled. The user is told a capability
is active when it is not — which Principle I forbids in the same terms it forbids substituting
zero for a missing metric.

**Why the existing tests missed it**: `test_no_os_branching_outside_adapters` looks for
`sys.platform` conditionals in non-adapter code. This file has no conditional — it imports the
Linux implementation directly and unconditionally. The rule was written against the wrong shape
of the mistake. The new test closes that: `ui` may import `gpum.adapters`, never
`gpum.adapters.linux` or `gpum.adapters.windows`.

**Scope note**: this is a pre-existing defect, not one this feature introduces. It is in scope
because US2 requires the Windows build to tell the truth, and shipping GPUM to Windows users
with a settings toggle that lies is precisely the outcome US2 exists to prevent.

---

## D-08 — Unsigned this release, signable next

**Decision**: No signing step runs, but the build exposes an optional signing hook that is a
no-op when unconfigured. Publish a SHA-256 for every artifact. Document the SmartScreen warning
before users meet it.

**Rationale**: The requester deferred signing while keeping it reversible. "Reversible" has a
concrete meaning here: nothing in the build may assume artifacts are unsigned — no hardcoded
hashes of unsigned outputs, no verification step that would break once a signature is appended,
and the installer's own payload checks must tolerate a signed executable.

**On the user-facing consequence**: Windows SmartScreen shows "Windows protected your PC" for an
artifact with no reputation. A user who was told to expect it can proceed; a user who was not
cannot distinguish it from a genuine compromise warning. That is why FR-024 makes documenting it
a requirement rather than a courtesy, and why FR-025 pairs it with a checksum — the checksum is
the authenticity answer that does not depend on Microsoft's reputation system.

---

## D-09 — Licensing check on the installer framework

**Decision**: Confirm IFW's license terms and record the result in `docs/licenses.md` **before**
the first artifact is published.

**Rationale**: The constitution requires third-party dependencies to be license-compatible with
the project's distribution license, and requires copyleft-incompatible additions to be rejected
in review. IFW is distributed under multiple licenses, and — unlike a pure build tool — part of
it (the maintenance tool) **ships inside the artifact users receive**. That makes it a
distributed component, not merely a build-time one, so the license question is real rather than
procedural.

**Consequence**: this is a gating task, not a documentation chore. If the terms are incompatible
with the project's license, D-01's recorded fallback (Inno Setup) is taken and no design work is
lost.

---

## D-10 — Do not add a distribution kind per artifact

**Decision**: Both Windows artifacts report the existing `BUNDLE` kind. `DistributionKind` keeps
its three values.

**Rationale**: `distribution.py` exists to be diagnostic only — FR-019 here, FR-026 in feature
002 — and `tests/unit/test_distribution.py` already enforces that only that module and
`__main__.py` may mention the packaging form. Adding `WINDOWS_INSTALL` and `PORTABLE` values
would create exactly the affordance the module was written to remove: a tempting way to branch
behaviour on how the user obtained the program. The `bundle_root` field already distinguishes
them for diagnostics.

**Alternatives considered**: new kinds (rejected as above); a free-text label (same problem,
less type safety).

---

## D-11 — Refuse unsupported platforms before writing anything

**Decision**: The installer checks Windows version and architecture as its first action and exits
with a stated reason if unmet: 64-bit x86, Windows 10 21H2 or later.

**Rationale**: FR-023. The failure mode being prevented is a half-installed application that
crashes at launch with a message about a missing DLL — which the user reads as "this program is
broken" rather than "this program does not support my machine". ARM64 is the live case: an x64
artifact may run under emulation with unpredictable driver-library behaviour, and claiming
support the project has not verified would violate the capability-matrix rule.

---

## D-12 — Upgrade and uninstall while running

**Decision**: Detect a running instance and instruct the user to close it, rather than proceeding.

**Rationale**: FR-011. Windows locks running executables, so a silent attempt leaves a partially
removed installation and an orphaned Start menu entry — a state that is worse than refusing,
because the user now has neither a working application nor a clean machine.

---

## D-13 — Verification on the physical Windows machine

**Decision**: Mirror the Linux hardware suite against `nvidia-smi.exe`, run it on the requester's
Windows machine, and update the capability matrix from what it observes.

**Rationale**: This is what the requester's answer to the spec's clarification bought, and it is
what separates this feature from feature 001's mistake. Three claims about Windows are currently
inferred from the vendor interface's documentation rather than observed:

- utilization and memory agree with the vendor tool
- per-process memory is genuinely unavailable under the current driver model, and is reported as
  such rather than as zero
- the process list still names processes correctly

The Linux suite already encodes the right comparison discipline — including the bracketing fix
from feature 006, which applies unchanged here, since the reason for it (a metric moving between
two reads) is not platform-specific.

**Consequence**: `present_gpus()` returns an empty list on Windows, so GPUs physically present
but unmonitorable are not reported there. That is a smaller claim rather than a wrong one, and it
belongs in the capability matrix as an observed limitation.

---

## D-14 — CI: a Windows artifact job beside the AppImage job

**Decision**: Add a `windows-bundle` job on `windows-latest`, structured like the existing
`bundle` job: build, run the build-blocking checks, smoke-test the artifact headless, upload it.

**Rationale**: The test matrix already runs on `windows-latest` across three Python versions, so
Windows CI is not new — only the artifact build is. Structuring the job as a mirror of the
AppImage one means one shape to understand.

**Note on what CI can and cannot prove**: the runner has no NVIDIA GPU, so CI proves the artifact
builds, contains no driver library, and launches. It cannot prove any number is correct. That is
D-13's job, and the distinction must stay visible in the capability matrix so a green CI badge is
never mistaken for hardware verification.
