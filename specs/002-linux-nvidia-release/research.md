# Phase 0 Research: Linux + NVIDIA Release Readiness

**Feature**: 002-linux-nvidia-release | **Date**: 2026-08-16

Feature 001 built the monitor. This feature makes it installable, verified, and durable on Linux
with an NVIDIA GPU. The decisions below are constrained by the project constitution and by what
was measured on the development machine, which is itself a valid target: **Ubuntu 24.04, GNOME on
X11, glibc 2.39, Python 3.12, NVIDIA RTX 5060 Ti on driver 580.159.03.**

---

## D-01: Self-contained bundle format

**Decision**: PyInstaller (`--onedir`) to produce an AppDir, then `appimagetool` to seal it into a
single `.AppImage`.

**Rationale**: FR-024/FR-025 require one downloadable file that runs after a `chmod +x` with no
install step and no prerequisites beyond the NVIDIA driver. AppImage is the only mainstream Linux
format that satisfies "no install step" literally — Flatpak and Snap both require a runtime and a
system-level install, which is a prerequisite by any honest reading. PyInstaller is chosen as the
freezing step because it has maintained PySide6 hooks that already know which Qt plugins must be
collected; hand-assembling a Qt AppDir means rediscovering that list by trial and error.

**Alternatives considered**:
- *python-appimage*: builds from a manylinux Python and a pip install. Genuinely simpler and more
  reproducible, and it was close. Rejected because it gives much less control over **excluding**
  Qt modules, and PySide6's full install is large enough that exclusion is the difference between
  a ~90 MB and a ~400 MB download (see D-03).
- *Nuitka*: produces a faster, smaller binary. Rejected as disproportionate — compilation time and
  a much less familiar failure mode, for a startup-time gain that does not matter in a tool the
  user leaves open for hours.
- *Flatpak*: best desktop integration and sandboxing story. Rejected for this release because the
  sandbox actively fights the requirement: reading `/proc/<pid>/cgroup` for container attribution
  (001 FR-029) and enumerating host processes both need host access that Flatpak grants only with
  broad overrides. Worth revisiting as a *third* form later, never as a replacement.
- *Static PyInstaller `--onefile` without AppImage*: one file already, and simpler. Rejected
  because it extracts to `/tmp` on every launch, which is slow for a ~90 MB payload and leaves the
  desktop-integration story (icon, `.desktop` entry) unsolved.

---

## D-02: glibc floor — build on the oldest supported base, not this machine

**Decision**: Build the AppImage inside a container based on **Ubuntu 22.04 (glibc 2.35)**, not on
the development machine.

**Rationale**: This is the single most common way a Linux bundle ships broken. glibc is
backward-compatible but **not forward-compatible**: a binary linked against glibc 2.39 (this
machine) fails to start on Ubuntu 22.04 with a `GLIBC_2.38 not found` error, while one built
against 2.35 runs on both. Building on the newest machine available produces a bundle that works
for the developer and nobody else — and it fails at launch, before any of the tool's own careful
error reporting can run.

Ubuntu 22.04 as the floor covers 22.04, 24.04, Debian 12, and current Fedora. Ubuntu 20.04
(glibc 2.31) is excluded deliberately: it is out of standard support and would constrain the Qt
version.

**Consequence**: the build is not reproducible by running a script on a maintainer's laptop. It
requires the container, and CI must enforce that.

**Alternatives considered**: building on this machine and documenting a 24.04-or-newer
requirement. Rejected — it silently excludes the largest installed base for no gain.

---

## D-03: What must be excluded from the bundle, and what must never be bundled

**Decision**: Two separate rules, for two different reasons.

**Exclude for size**: `QtWebEngine`, `QtQuick`/QML, `Qt3D`, `QtMultimedia`, `QtCharts`,
`QtNetwork` where droppable, translations, and unused platform plugins. PySide6 installs at
roughly 400 MB; the application uses `QtCore`, `QtGui`, and `QtWidgets` only. Target: **under
120 MB** compressed.

**Never bundle — correctness, not size**: `libnvidia-ml.so.1` and every other NVIDIA driver
library **must be excluded and resolved from the host at runtime**. NVML is a driver component and
is version-locked to the running kernel module. A bundled copy from the build machine's driver
would either fail to initialise or, worse, misreport against a different host driver. The
`nvidia-ml-py` binding is pure Python over `ctypes` and loads `libnvidia-ml.so.1` by name at call
time, so excluding the library is sufficient — no special loading code is needed.

**Rationale**: PyInstaller's dependency walker will happily pull in a driver library it finds on
the build host. This must be an explicit exclusion plus an automated check on the produced
AppDir, because the failure it prevents is silent-wrong-numbers on someone else's machine, which
is the exact failure SC-008 exists to prevent.

**Also excluded**: any `libcuda.so`, `libGL` from the driver, and `libglvnd`.

---

## D-04: Detecting whether a tray icon will actually appear

**Decision**: Determine availability by checking for a **DBus owner of
`org.kde.StatusNotifierWatcher` on the session bus**, and treat `QSystemTrayIcon.
isSystemTrayAvailable()` as advisory only.

**Rationale**: This is the finding that makes FR-034 implementable, and it was measured rather
than assumed. On this machine:

```
QSystemTrayIcon.isSystemTrayAvailable() -> True
org.kde.StatusNotifierWatcher           -> present on the session bus
gnome-extensions list                   -> ubuntu-appindicators@ubuntu.com
```

Ubuntu ships the AppIndicator extension by default, so the tray genuinely works here. The trap is
that on a **stock GNOME without that extension**, `isSystemTrayAvailable()` still returns `True`
while no icon ever appears — Qt reports the capability, the desktop silently drops the icon, and
the user is left with a running program they cannot see or recover. That is precisely the
worst-case failure FR-034 and SC-015 forbid.

The `StatusNotifierWatcher` ownership check is the signal that actually correlates with an icon
being displayed, because that is the protocol modern desktops use.

**Confidence**: high that the watcher check is the right signal and that Ubuntu GNOME works.
**Lower confidence** that `isSystemTrayAvailable()` returns `True` on *stock* GNOME — that is the
documented historical behaviour but could not be verified here, since this machine has the
extension. **Spike S-01** covers it. The design is safe either way: if the optimistic report never
happens, the watcher check simply agrees with Qt and costs nothing.

**Alternatives considered**: trusting `isSystemTrayAvailable()` alone — rejected, it is the
documented false positive. Showing the icon and detecting failure afterwards — rejected, there is
no failure callback; the icon is dropped silently.

---

## D-05: Close-to-tray semantics

**Decision**: Closing the window hides it when a tray icon is present; the **first** such close
shows a notification saying so. Quit is explicit, from the tray menu or a File→Quit action. When
no tray is available, or the user disables the icon, close means quit.

**Rationale**: FR-030, FR-031, FR-034. "Close doesn't close" is a widely disliked behaviour
precisely because it is usually undisclosed; the one-time notice removes the surprise at near-zero
cost. Falling back to quit-on-close when the tray is unavailable means there is no reachable state
in which the application is running and invisible.

**Implementation note**: the "first time" flag is a persisted preference, so the notice appears
once per user, not once per session.

---

## D-06: Sampling while closed to the tray

**Decision**: Reuse feature 001's existing hidden-window throttle path unchanged. Closing to the
tray is, to the sampler, identical to hiding the window.

**Rationale**: FR-032 and SC-016 require the tray icon to add zero continuous sampling. 001
already routes `hide`/`minimize` to `set_throttled(True)` on the worker, so the correct
implementation here is *not to add anything* — the window's existing `hideEvent` already fires
when closing to tray. The risk is the opposite of the usual one: it would be easy to "helpfully"
keep sampling so the tray is fresh on reopen. FR-033's two-interval budget is deliberately loose
enough that a fresh sample on reopen satisfies it without background polling.

---

## D-07: Desktop integration for the pip install

**Decision**: Install a `.desktop` entry and icon into XDG user paths
(`~/.local/share/applications/`, `~/.local/share/icons/hicolor/…`) via a small `gpum --install-desktop-entry`
command, invoked by the user, not by the installer.

**Rationale**: FR-003/FR-004 require an application-menu entry. Python wheels have no reliable
post-install hook — `setup.py install` hooks do not run for wheels, which is what pip installs.
Writing files from a package's import side-effects would be worse. An explicit opt-in command is
honest, is documented in one line, and keeps the constitution's "modifies no state but its own
preferences" promise intact by making the write user-initiated. The AppImage does not need this:
desktop environments discover AppImage metadata themselves.

---

## D-08: Autostart

**Decision**: `~/.config/autostart/gpum.desktop`, written and removed by the settings toggle, with
`X-GNOME-Autostart-enabled` and a flag that starts the app hidden to tray.

**Rationale**: FR-022. This is the XDG standard mechanism and needs no privileges.

**Constitution note**: this writes a file outside the tool's own preference store, which brushes
against Principle V ("MUST NOT modify any system state other than its own saved user
preferences"). It is recorded in the plan's Complexity Tracking with its justification —
user-initiated, user-scoped, reversible from the same toggle, and never written by default.

---

## D-09: Shared preferences between the two distribution forms

**Decision**: Both forms use the same `QSettings` organisation and application name, resolving to
`~/.config/gpum/gpum.conf`. The AppImage sets no private `XDG_CONFIG_HOME`.

**Rationale**: FR-028. AppImages are not sandboxed, so this works by default — the requirement is
really "don't break it", and the way it breaks is a well-meant wrapper script that isolates config
per-bundle. An automated check asserts both forms resolve to the same path.

---

## D-10: Suspend/resume detection

**Decision**: Detect a wall-clock gap in the sampling engine — if more than a threshold multiple of
the interval has elapsed since the previous cycle, treat it as a resume: clear degradation backoff,
re-enumerate devices, and insert an explicit gap in history rather than a interpolated segment.

**Rationale**: FR-013. The alternative is subscribing to logind's `PrepareForSleep` DBus signal,
which is more precise but adds a DBus dependency to a code path that must also work when logind is
absent, and puts platform-specific machinery in the sampling loop. Clock-gap detection is
platform-neutral, testable with the existing fake clock, and cannot miss a resume that logind
failed to announce.

**Honesty requirement**: the gap must render as a gap. Drawing a straight line across a
four-hour suspend would assert measurements that were never taken (SC-008).

---

## D-11: Driver restart recovery

**Decision**: On an NVML error indicating the device or library is gone, shut down NVML, re-init,
and rebuild all device handles; mark devices unavailable in the interim rather than removing them
immediately.

**Rationale**: FR-014. Device handles do not survive a driver restart, and reusing a stale handle
returns errors indefinitely — the tool would appear permanently broken until restarted, which is
exactly the outcome FR-014 forbids. Keeping devices listed-but-unavailable during the gap avoids
the display flickering the whole device list away and back.

**Confidence**: the handle-rebuild requirement is well established. The precise error code
sequence a modern driver returns on restart is **spike S-02**.

---

## D-12: Hardware verification method

**Decision**: An automated comparison harness that samples the tool and `nvidia-smi` concurrently
and asserts agreement within tolerance, plus a recorded-fixture capture run.

**Rationale**: FR-007/FR-008 require agreement with the vendor's own tooling, and SC-003 sets 5%
over 10 minutes. Doing this by eye does not scale and produces no artefact. Running both sources
concurrently rather than sequentially matters — GPU memory moves, and a sequential comparison
measures the delay, not the agreement.

Captured responses feed FR-011 so behaviour proven once on hardware stays under test on GPU-free
machines, satisfying Principle IV without weakening it.

---

## D-13: Single source of version truth

**Decision**: Version read from package metadata at runtime; the AppImage build stamps the same
value into its filename and `AppStream` metadata. A `--version` flag reports it.

**Rationale**: FR-026 requires both forms to report identically so a bug report is reproducible
against either.

---

## Spikes required

- **S-01 — stock-GNOME tray false positive**: confirm on a GNOME session *without* the
  AppIndicator extension that `isSystemTrayAvailable()` returns `True` while no icon appears. This
  is the premise of D-04. If it turns out Qt reports correctly, the watcher check becomes
  redundant belt-and-braces rather than essential — harmless either way.
- **S-02 — driver restart error surface**: capture what NVML actually returns across a
  `nvidia-smi -r` or module reload, to drive D-11's recovery path.
- **S-03 — AppImage on the oldest target**: build in the 22.04 container per D-02 and launch on a
  22.04 machine or container to prove the glibc floor holds.
- **S-04 — bundle size after exclusions**: measure the produced AppImage; if it exceeds 120 MB,
  revisit the exclusion list before accepting it.

## Resolved unknowns

No `NEEDS CLARIFICATION` markers remain. Bundle format, glibc floor, exclusion policy, tray
detection, close semantics, autostart, preference sharing, resume detection, driver recovery, and
verification method are all settled above.
