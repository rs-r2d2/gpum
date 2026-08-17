# Quickstart & Validation: Windows Executable & Installer

**Feature**: 007-windows-installer | **Date**: 2026-08-17

Unlike previous features, **most of this cannot be validated on the development machine.**
Each scenario states where it runs. Marking a Windows check as passed from Linux is the specific
mistake this guide is written to prevent.

## Build

```powershell
# On Windows, or on the CI windows runner
pip install -e ".[nvidia,dev]"
powershell -File packaging/windows/build-windows.ps1
```

Produces `dist/GPUM-<version>-win64-setup.exe` and `dist/GPUM-<version>-win64-portable.exe`.
The build runs `verify-dist.ps1` itself and fails rather than emitting an artifact that does not
pass (FR-021).

## Scenarios

### V-1 — It installs without a developer, and without an administrator *(needs Windows)*

Run the installer on a clean Windows machine with an NVIDIA driver and no Python, using an
account **without** administrator rights.

**Expect**: no elevation prompt, a Start menu entry, and the window showing the real GPU within
5 seconds of launching it. **Fail condition**: any UAC prompt — that means it is installing
somewhere it should not be (D-04).

### V-2 — No driver library rode along *(runs anywhere, including Linux CI)*

```bash
pytest -m packaging -k windows_artifact
```

**Expect**: zero NVIDIA components in the artifact. **Fail condition**: any hit. This one is
checkable off-Windows because it inspects the artifact's contents, and it is build-blocking
because the failure is invisible on the machine that produced it (D-03).

### V-3 — The autostart toggle tells the truth *(critical — needs Windows)*

Open Settings and read the disclosed location **before** enabling anything.

**Expect**: a Windows registry location. **Fail condition**: a path containing `.config` or
ending in `.desktop` — that is the pre-existing defect (D-07) still present, meaning the toggle
writes a file Windows never reads and then reports success.

Then enable it, sign out and back in, and confirm GPUM starts. Disable it and confirm the
registry is as it was found.

### V-4 — Layering is enforced, not just intended *(runs anywhere)*

```bash
pytest tests/unit/test_import_boundaries.py
```

**Expect**: a failure if any `ui`, `core`, or `backends` module imports `gpum.adapters.linux.*`
or `gpum.adapters.windows.*`. Confirm the new rule actually bites by temporarily restoring the
old import in `ui/app.py` — a boundary test that passes against the very defect it was written
for is worse than none.

### V-5 — Uninstall is clean, and keeps what it should *(needs Windows)*

Install, change a setting, enable autostart, then uninstall through Settings → Apps.

**Expect**: application, Start menu entry, shortcut and autostart entry all gone; **preferences
retained**, so a reinstall restores the changed setting (FR-009). **Fail condition**: an orphaned
Start menu entry, or settings lost.

### V-6 — Upgrade leaves one of everything *(needs Windows)*

Install, then install a build with a higher version over it.

**Expect**: one installation, one entry in Apps, settings preserved. **Fail condition**: two
entries — the state users cannot clean up themselves.

### V-7 — Running instance is refused, not half-removed *(needs Windows)*

Launch GPUM, leave it running, start an uninstall.

**Expect**: told to close it first. **Fail condition**: a partially removed installation, which
leaves neither a working application nor a clean machine (D-12).

### V-8 — Offline throughout *(needs Windows)*

Disconnect the network. Install, launch, use, uninstall.

**Expect**: all four succeed. The project promises nothing leaves the machine; an installer that
needs the network breaks that promise before the application even starts.

### V-9 — The portable file needs nothing *(needs Windows)*

Copy only `GPUM-<version>-win64-portable.exe` to a machine with no GPUM installed and run it.

**Expect**: the same application, no installation, no elevation. Startup is slower than the
installed form — that is the documented trade of a self-extracting build (D-02), not a defect.

### V-10 — All three delivery forms agree *(needs Windows)*

With the package, the installed build, and the portable file on one machine:

```powershell
gpum --version
"$env:LOCALAPPDATA\Programs\GPUM\gpum.exe" --version
.\GPUM-<version>-win64-portable.exe --version
```

**Expect**: the same version from all three, and a setting changed in one visible in the next
(FR-017, FR-018).

### V-11 — The numbers are true *(critical — needs a Windows machine with an NVIDIA GPU)*

```powershell
pytest -m hardware -k windows
```

**Expect**: memory and utilization within the project's existing tolerance of `nvidia-smi.exe`,
using the bracketed comparison from feature 006 — the reason for bracketing (a metric moving
between two reads) is not platform-specific.

**Expect** per-process GPU memory to report an explicit unavailable state with a reason under
WDDM, and never `0`.

### V-12 — The capability matrix says only what was seen *(review step)*

Read `docs/capability-matrix.md` against what V-1 to V-11 actually produced.

**Expect**: every Windows cell marked observed, unverified, or unavailable-with-reason, and none
left implicitly claimed. **Fail condition**: a cell marked observed on the strength of CI — CI has
no GPU and can prove the artifact builds and launches, nothing about any number (D-14).

## Suite

```bash
pytest                 # default: no GPU, no Windows needed
pytest -m packaging    # artifact checks
pytest -m hardware     # V-11, needs the Windows GPU machine
```

`pytest` alone deselects both marked suites, so a green run says nothing about any artifact and
nothing about any Windows number.
