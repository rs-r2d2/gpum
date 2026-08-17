# Building GPUM

## Package install (works today)

```bash
pip install -e ".[nvidia,dev]"
gpum --install-desktop-entry     # optional: adds it to your application menu
```

## Self-contained bundle (AppImage)

**The bundle must be built inside the Ubuntu 22.04 container. This is not a convenience.**

glibc is backward-compatible but *not* forward-compatible. A bundle built on Ubuntu 24.04
(glibc 2.39) fails to start on Ubuntu 22.04 with a linker error — before any of GPUM's own
error reporting can run, so the user sees a cryptic crash rather than a message. Building
against 2.35 produces a bundle that runs on both.

```bash
docker build -f packaging/Dockerfile.build -t gpum-build .
docker run --rm -v "$PWD:/src" gpum-build /src/packaging/build-appimage.sh
```

`build-appimage.sh` refuses to run outside the container for this reason.

The build hands artifact ownership back to whoever owns the mounted tree, because Docker runs
as root and would otherwise leave you with a `dist/` you cannot even `chmod`. Pass `HOST_UID`
and `HOST_GID` explicitly if the fallback guesses wrong:

```bash
docker run --rm -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" \
    -v "$PWD:/src" gpum-build /src/packaging/build-appimage.sh
```

### What the build must exclude

Two separate rules, for two different reasons:

**Excluded for size** — `QtWebEngine`, `QtQuick`, `Qt3D`, `QtMultimedia`, `QtCharts`,
translations, unused platform plugins. PySide6 installs at roughly 400 MB; GPUM uses `QtCore`,
`QtGui`, and `QtWidgets` only. Budget: under 120 MB.

**Never bundled — correctness, not size** — `libnvidia-ml.so.1` and every other NVIDIA driver
library. NVML is version-locked to the host's kernel module. A bundled copy from the build
machine either fails to initialise or *misreports against a different host driver*, which is
wrong numbers presented as measurements on someone else's machine. It is silent, and it is
invisible on the build host.

`packaging/verify-appdir.sh` makes both checks build-blocking rather than advisory.

## Windows executable and installer

**Status: in progress (feature 007).** The application-side work is done and the build tooling
is not. What exists today:

- `packaging/gpum.spec` builds on Windows as well as Linux. Its exclusion tables are selected
  per platform, because the same Qt libraries are `libQt6Quick.so.6` on Linux and `Qt6Quick.dll`
  on Windows, and destination paths use different separators. A Linux-shaped table looks
  configured and excludes nothing on Windows.
- The forbidden-driver-library rule now covers `nvml`, `nvcuda`, `nvapi`, `nvfatbinaryloader`,
  `nvrtc` and `cudart`. The reason is identical to Linux: NVML is version-locked to the host's
  driver, and `nvidia-ml-py` resolves `%WINDIR%\System32\nvml.dll` by absolute path at call
  time, so excluding it is both sufficient and correct.

What does **not** exist yet: `packaging/windows/build-windows.ps1`, the installer
configuration, and `packaging/windows/verify-dist.ps1`. See
`specs/007-windows-installer/tasks.md`.

### The installer framework is not yet chosen

The requester asked for the Qt Installer Framework, and it meets the functional constraints
(per-user install without elevation, offline, an uninstall entry). **It is not yet approved**,
because it is distributed under GPL/LGPL terms and its maintenance tool ships *inside* the
artifact users receive — making it a distributed component subject to this project's licensing
rule, not merely a build tool.

That decision is blocked on a prior contradiction: this repository declares two different
licences for itself. See `docs/licenses.md`. Until that is settled, no installer framework can
be assessed for compatibility, because there is nothing definite to be compatible with. Inno
Setup is the recorded fallback (research D-01) if the terms do not work out; no design work
depends on which is chosen.

## Status

**Implemented and verified.** The pipeline produces a **50 MB** AppImage that has been confirmed
to launch on Ubuntu 22.04 (the oldest supported target) and to run on the development machine's
real GNOME/X11 session.

## Things this pipeline got wrong once, and now guards against

Each of these was found by actually building and running the bundle, not by review:

| Problem | Symptom | Guard |
|---|---|---|
| Ubuntu 22.04 ships Python 3.10, GPUM needs 3.11 | build failed outright | deadsnakes PPA in the container; the base image stays 22.04 for its *glibc*, not its Python |
| `QtQuick`/`QtQml` collected as **data**, not binaries | excluded modules shipped anyway, +27 MB | the prefix filter is applied to `a.datas` as well as `a.binaries` |
| Wayland plugin is `libqwayland.so`, not `libqwayland-generic.so` | verifier reported a missing plugin that was present | verifier accepts either name |
| Size budget checked against the **uncompressed** AppDir | build failed at 126 MB when the real download is 50 MB | AppDir gets a loose regression ceiling; the 120 MB budget is enforced on the sealed AppImage |
| Package metadata not bundled | bundle reported `0.0.0+unknown`, breaking version equivalence (FR-026) | `copy_metadata("gpum")` in the spec |
| `AppRun` pointed `LD_LIBRARY_PATH` at `usr/lib`, but PyInstaller uses `usr/bin/_internal` | **worked headless, aborted on a real display** — Qt's xcb plugin dlopens `libxcb-cursor.so.0` by name | `AppRun` covers `_internal`; the verifier asserts the library is both bundled and on that path |

The last one is the one worth remembering: every headless test passed while the bundle was
unusable for any actual user. A smoke test that never opens a window would not have caught it.
