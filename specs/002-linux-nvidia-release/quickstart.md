# Quickstart & Validation Guide: Linux + NVIDIA Release Readiness

**Feature**: 002-linux-nvidia-release | **Date**: 2026-08-16

How to build both distribution forms and prove this feature works. Validation splits three ways by
what each scenario needs:

- **No GPU, no bundle** — runs anywhere, including CI (V-1 … V-6)
- **Real NVIDIA GPU** — `@pytest.mark.hardware` (V-7 … V-11)
- **Built AppImage** — `@pytest.mark.packaging` (V-12 … V-15)

The default suite must stay green with none of the above (constitution Principle IV).

---

## Prerequisites

| Scenario group | Needs |
|---|---|
| V-1 … V-6 | Python 3.11+ only |
| V-7 … V-11 | NVIDIA GPU + driver + `nvidia-smi` |
| V-12 … V-15 | Docker (to build in the 22.04 container) |

Reference machine for hardware validation: Ubuntu 24.04, GNOME/X11, RTX 5060 Ti, driver 580.159.03.

---

## Build

```bash
# Form A — package install
pip install -e ".[nvidia,dev]"

# Form B — bundle. MUST build in the container (research D-02).
docker build -f packaging/Dockerfile.build -t gpum-build .
docker run --rm -v "$PWD:/src" gpum-build /src/packaging/build-appimage.sh
```

**Do not build the AppImage directly on this machine.** It has glibc 2.39; the container has 2.35.
A bundle built here dies at launch on Ubuntu 22.04 with a linker error, before any of the tool's
own error reporting can run. The build script refuses to run outside the container for this reason.

---

## Validation scenarios

### V-1 — Tray unavailable means close quits *(no GPU needed)* — **the critical one**

```bash
pytest tests/integration/test_tray_behaviour.py -k unavailable
```

**Expect**: with the probe reporting unusable, closing the window **quits**. There must be no
configuration in which the tool is running with no window and no tray icon.

**Fail condition**: the window hides when no icon will be shown. That leaves a process the user
can only kill from a terminal — the failure SC-015 forbids outright.

### V-2 — Qt's optimistic answer is not trusted *(no GPU needed)*

```bash
pytest tests/unit/test_tray_probe.py
```

**Expect**: with Qt reporting `True` and no `StatusNotifierWatcher` present, `usable` is `False`
with a reason. This is research D-04 encoded as a test.

### V-3 — Close semantics, all four rows *(no GPU needed)*

```bash
pytest tests/integration/test_tray_behaviour.py -k close_semantics
```

**Expect**: every row of the decision table in `contracts/tray-contract.md` behaves as written,
and the one-time close notice appears exactly once across simulated sessions.

### V-4 — Tray adds no sampling *(no GPU needed)*

```bash
pytest tests/integration/test_tray_behaviour.py -k sampling_rate
```

**Expect**: sampling cadence while closed-to-tray equals the hidden-window cadence. FR-032/SC-016.

### V-5 — Suspend/resume renders as a gap *(no GPU needed)*

```bash
pytest tests/unit/test_resume_detection.py
```

**Expect**: a simulated four-hour clock jump is detected as a resume; backoff clears,
re-enumeration is forced, and history contains an explicit **gap**.

**Fail condition**: a straight line drawn across the suspend. That asserts measurements never
taken — the same lie as rendering an unavailable metric as `0`.

### V-6 — Desktop integration stays inside XDG *(no GPU needed)*

```bash
pytest tests/integration/test_desktop_entry.py
```

**Expect**: with `XDG_*` pointed at a temporary root, install writes only inside it, uninstall
removes exactly what it wrote, and nothing is written without an explicit call.

### V-7 — Agreement with `nvidia-smi` *(needs a GPU)* — **the other critical one**

```bash
python tools/compare-with-nvidia-smi.py --duration 600 --out verification.json
```

**Expect**: max memory deviation ≤ 5% over 10 minutes (SC-003), 100% of processes matched
(SC-004), and a recorded mean/p99 cycle cost.

**This is the first time the tool's numbers are checked against reality.** Everything in feature
001 was verified against simulated devices.

### V-8 — Set the timeout from measurement *(needs a GPU)*

Take `mean_cycle_cost_ms` and `p99_cycle_cost_ms` from V-7 and set the per-device timeout in
`core/engine.py`, replacing feature 001's 500 ms placeholder (FR-009). Record the basis in a
comment.

### V-9 — Driver restart recovery *(needs a GPU)*

```bash
pytest -m hardware tests/hardware/test_driver_restart.py
# manual: sudo nvidia-smi -r   (or reload the kernel module) with the tool open
```

**Expect**: devices go unavailable while the driver is gone and **recover automatically** when it
returns, with handles rebuilt. No restart of the tool.

**Fail condition**: the device stays broken until the tool is restarted — FR-014's whole point.

### V-10 — Suspend and resume for real *(needs a GPU)*

Suspend the machine with the tool open; resume.

**Expect**: sampling continues, no negative or duplicated readings, a visible gap for the suspend.

### V-11 — Both vendors accounted for *(needs the reference machine)*

**Expect**: the NVIDIA GPU is fully monitored **and** the AMD GPU also present in this machine is
listed as detected but unsupported. FR-015/SC-007 — the tool must never report fewer GPUs than
the machine has.

### V-12 — Bundle carries no driver library *(needs a build)*

```bash
packaging/verify-appdir.sh build/AppDir
```

**Expect**: assertions V-01 … V-06 from `contracts/distribution-contract.md` pass. A bundled
`libnvidia-ml.so.1` fails the build.

**Why it is build-blocking**: a bundled driver library produces wrong numbers on someone else's
machine, silently. It is invisible on the build host.

### V-13 — Runs on the oldest supported distribution *(needs a build)*

```bash
docker run --rm -v "$PWD/dist:/dist" ubuntu:22.04 /dist/GPUM-x86_64.AppImage --version
```

**Expect**: the version prints. A `GLIBC_… not found` error means the build escaped the container.

### V-14 — Three steps from download to running *(needs a build)*

On a machine with no Python tooling: download, `chmod +x`, run.

**Expect**: the window opens showing the real GPU. SC-012 — under 2 minutes, at most three steps.

### V-15 — The two forms are equivalent *(needs a build)*

```bash
pytest -m packaging tests/packaging/test_appimage_smoke.py
```

**Expect**: assertions E-01 … E-08 pass — identical version, shared preferences path, identical
discovery output, no elevation, no network, and no application module branching on packaging form.

---

## Test suite

```bash
pytest                       # default: no GPU, no bundle. MUST stay green.
pytest -m hardware           # needs a real NVIDIA GPU
pytest -m packaging          # needs a built AppImage
pytest -m "not hardware and not packaging" --cov=gpum
```

---

## Release checklist

Before publishing, all of these must hold:

- [ ] Default suite green on a machine with no GPU
- [ ] `pytest -m hardware` green on the reference machine, with `verification.json` recorded
- [ ] AppImage built **in the container**, `verify-appdir.sh` passing
- [ ] `pytest -m packaging` green
- [ ] V-13 passes on Ubuntu 22.04
- [ ] V-14 walked manually by someone who did not build it
- [ ] `docs/capability-matrix.md` updated
- [ ] Feature 001's remaining hardware tasks (T033, T050, T085) closed by V-7/V-8/V-9
