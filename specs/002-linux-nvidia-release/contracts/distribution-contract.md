# Contract: Distribution

**Artefacts**: `packaging/`, `pyproject.toml` | **Feature**: 002-linux-nvidia-release

Two delivery forms that must be indistinguishable in behaviour (FR-026).

---

## Form A — package install

```bash
pip install gpum[nvidia]
gpum                              # or: python -m gpum
gpum --install-desktop-entry      # opt-in menu entry (research D-07)
pip uninstall gpum
```

**MUST**:
- Install with no compiler, no elevation, no manual dependency resolution (FR-001, SC-002).
- Work without the `[nvidia]` extra, reporting exactly what to install to enable NVIDIA support
  (FR-002, feature 001 SC-006).
- Provide a `gpum` console entry point identical in behaviour to `python -m gpum` (FR-003).
- Never write outside the user's XDG directories, and never write anything at install time.

**MUST NOT**: require root; require a system Qt; trigger a source build of any dependency.

---

## Form B — self-contained bundle

```bash
chmod +x GPUM-x86_64.AppImage
./GPUM-x86_64.AppImage
```

**MUST**:
- Run after download and a permission change, with no install step and no prerequisite beyond the
  NVIDIA driver (FR-025, SC-012 — three steps maximum).
- Carry its own Python and Qt so it runs where the system runtime is older (FR-027).
- **Be built on Ubuntu 22.04 (glibc 2.35), never on a newer host.** glibc is backward- but not
  forward-compatible: a bundle built on 24.04 dies at launch on 22.04 with a linker error, before
  any of the tool's own error handling can run (research D-02).
- Launch and remain usable on a machine with no NVIDIA driver, reporting what it found — exactly
  as the installed form does.
- Read and write `~/.config/gpum/gpum.conf`, the same file Form A uses (FR-028).
- Report the same version string as Form A (FR-026, research D-13).

**MUST NOT**:
- **Bundle `libnvidia-ml.so.1` or any NVIDIA driver library.** This is the most important rule in
  this contract. NVML is version-locked to the host's kernel module; a bundled copy from the build
  machine either fails to initialise or misreports against a different host driver. That is
  wrong numbers presented as measurements on someone else's machine — the failure SC-008 exists to
  prevent, and it is silent (research D-03).
- Bundle `libcuda.so`, driver `libGL`, or `libglvnd`.
- Set a private `XDG_CONFIG_HOME`, which would silently fork the user's settings (FR-028).
- Require FUSE to be installed beyond what the AppImage runtime already needs.

---

## Build pipeline contract

`packaging/build-appimage.sh`, run inside `packaging/Dockerfile.build`:

1. Freeze with PyInstaller using `packaging/gpum.spec`.
2. Assemble the AppDir with `AppRun`, `gpum.desktop`, and the icon.
3. **Run `packaging/verify-appdir.sh` — the build fails if it does not pass.**
4. Seal with `appimagetool`, stamping the version into the filename.

### `verify-appdir.sh` assertions

| # | Assertion | Enforces |
|---|-----------|----------|
| V-01 | No `libnvidia-*`, `libcuda*`, or `libGLX_nvidia*` anywhere in the AppDir | **research D-03** — the silent-wrong-numbers failure |
| V-02 | No object requires a glibc symbol newer than 2.35 | research D-02 — launch failure on the oldest target |
| V-03 | `QtCore`, `QtGui`, `QtWidgets` present; `QtWebEngine`, `QtQuick`, `Qt3D`, `QtMultimedia` absent | size budget (SC via S-04) |
| V-04 | The Qt `xcb` and `wayland` platform plugins are both present | FR-018 — both session types |
| V-05 | Total size under 120 MB | research S-04 |
| V-06 | `AppRun` is executable and the desktop entry validates | launchability |

V-01 and V-02 are build-blocking rather than advisory, because both failures are invisible on the
build machine and only appear on a user's.

---

## Equivalence contract

Automated, in `tests/packaging/test_appimage_smoke.py` (`@pytest.mark.packaging`).

| # | Assertion | Enforces |
|---|-----------|----------|
| E-01 | Both forms report an identical `--version` string | FR-026 |
| E-02 | Both forms resolve to the same preferences path | FR-028 |
| E-03 | Both launch and produce a first reading within 5 s | SC-001 |
| E-04 | Both open successfully with the NVIDIA driver absent | feature 001 FR-018 |
| E-05 | Both produce identical discovery output on the same machine | FR-026 |
| E-06 | Neither requires elevation for any operation | FR-023, SC-011 |
| E-07 | Neither emits network traffic during a full sampling cycle | FR-023, SC-011 |
| E-08 | No application module branches on `DistributionForm.kind` outside diagnostics | FR-026 |

E-08 is the structural guard: FR-026's "identical behaviour" is guaranteed most reliably by making
the packaging form unobservable to application logic, not by testing every behaviour twice.
