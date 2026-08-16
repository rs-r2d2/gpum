# Phase 0 Research: GPU Usage Monitor

**Feature**: 001-gpu-usage-monitor | **Date**: 2026-08-16

This document resolves the technical unknowns behind `plan.md`. Every decision below is
constrained by the project constitution — in particular Principle I (vendor abstraction),
Principle III (non-blocking live updates), and Principle IV (tests run without GPUs).

---

## D-01: Qt binding

**Decision**: PySide6.

**Rationale**: The constitution names "Qt for Python (PySide6)" directly, which settles it.
Independently it is the right call: PySide6 is the official Qt-maintained binding under LGPLv3,
so distributing a closed or differently-licensed build stays possible, and it ships manylinux
and Windows wheels requiring no compiler on the user's machine.

**Alternatives considered**: PyQt6 — mature and widely used, but GPL/commercial dual licensing
forces the whole application to GPL unless a commercial licence is bought. Rejected on
licensing, not on merit.

---

## D-02: NVIDIA data source

**Decision**: NVML through the `nvidia-ml-py` package (the official NVIDIA bindings, importable
as `pynvml`). No subprocess calls to `nvidia-smi`.

**Rationale**: NVML is the same library `nvidia-smi` itself is built on, so it is the primary
source rather than a derivative of one. It returns typed structures instead of text needing
parsing, and it reports distinct error codes (`NVML_ERROR_NOT_SUPPORTED`,
`NVML_ERROR_NO_PERMISSION`, `NVML_ERROR_DRIVER_NOT_LOADED`) that map exactly onto the
`Availability` states FR-017 demands — this is what lets the tool say *why* a value is missing
instead of showing a zero. `nvidia-ml-py` is pure Python over `ctypes`, so it installs without a
compiler and imports successfully even when no driver is present; the driver's absence surfaces
at `nvmlInit()` as a catchable error rather than an import crash.

**Alternatives considered**:
- *Parsing `nvidia-smi --query-gpu=... --format=csv` or its XML output*: spawns a process on
  every refresh — at 1 Hz that is a measurable, permanent cost on the machine being measured,
  and it fails Principle III's spirit. Output format is also unversioned and has changed between
  driver releases. Rejected.
- *GPUtil / gpustat*: convenience wrappers, both ultimately over `nvidia-smi` text. Rejected for
  the same reason, plus dependency risk.

**Calls required**: `nvmlInit_v2`, `nvmlShutdown`, `nvmlDeviceGetCount_v2`,
`nvmlDeviceGetHandleByIndex_v2`, `nvmlDeviceGetName`, `nvmlDeviceGetUUID`,
`nvmlDeviceGetPciInfo_v3`, `nvmlDeviceGetMemoryInfo` (total/used/free),
`nvmlDeviceGetUtilizationRates` (gpu/memory), `nvmlDeviceGetComputeRunningProcesses_v3`,
`nvmlDeviceGetGraphicsRunningProcesses_v3`, `nvmlDeviceGetMigMode`.

---

## D-03: Per-process attribution is a *platform* concern, not only a vendor one

**Decision**: Model process attribution as a capability that may be satisfied by **either** the
vendor backend **or** a platform adapter, and merge the results in `core`. Do not assume the
vendor backend is always the source.

**Rationale**: This is the single most consequential finding of Phase 0, and it shapes the
interfaces.

- **NVIDIA on Linux**: NVML reports per-process GPU memory directly. Vendor backend is the
  source.
- **NVIDIA on Windows**: under the WDDM driver model — which is what every consumer and most
  workstation cards use — NVML does not report per-process GPU memory. `nvidia-smi` on Windows
  lists the PIDs but prints `N/A` for their memory. Only TCC-mode cards (datacenter parts, and
  out of scope for a desktop tool) report it. So on the platform pairing that matters most for
  reach, the vendor cannot answer FR-006 at all.
- **Windows for every vendor**: Windows 10 1709+ exposes `GPU Engine` and `GPU Process Memory`
  performance counters — the exact source Task Manager's GPU column uses. These are
  vendor-neutral and give per-process GPU memory and per-engine utilization without elevation.
- **Linux for future AMD/Intel**: DRM `fdinfo` (`/proc/<pid>/fdinfo/<fd>` on DRM file
  descriptors) exposes per-process memory and engine time for `amdgpu`, `i915`, and `xe`. This
  is the mechanism `nvtop` uses. Vendor-neutral, platform-specific.

Had attribution been modelled as "backends provide processes", the NVIDIA-on-Windows case would
have forced either a lie (empty process list) or a special case bolted into the NVIDIA backend —
both violating Principle I. Treating it as a separately-negotiated capability keeps the honesty
requirement satisfiable everywhere.

**Consequence for this release**: the NVIDIA backend supplies attribution on Linux; the Windows
PDH adapter supplies it on Windows. If the PDH adapter is not delivered in the first slice,
Windows shows per-process data as explicitly unavailable per FR-017 — degraded but honest, never
an empty list implying an idle GPU.

**Confidence**: high on the WDDM limitation and the existence of the counters; the exact PDH
counter path strings need confirmation on real hardware — see **S-01**.

---

## D-04: Threading and the timeout model

**Decision**: One `QThread` hosting a sampler worker. Within it, per-device queries dispatch to a
`ThreadPoolExecutor` with a per-device wall-clock timeout. Results reach the GUI exclusively via
Qt signals carrying immutable snapshot objects.

**Rationale**: Principle III forbids any blocking I/O on the GUI thread and caps GUI-thread work
at 16 ms. Driver calls are the blocking risk: a wedged driver can make an NVML call hang for
seconds. A pool with timeouts lets one bad device be marked stale (FR-014) while the others
continue.

**Honest limitation, to be documented in code**: a `ThreadPoolExecutor` timeout abandons the
*wait*, it does not cancel the *call*. A truly hung NVML call leaves its worker thread blocked
until the driver returns. The design therefore bounds pool growth and marks a device as degraded
and stops scheduling new queries against it after repeated timeouts, rather than pretending the
call was cancelled. Threads are never killed.

**Alternatives considered**:
- *`QTimer` on the GUI thread calling NVML directly*: simplest, and the way most small Qt
  monitors are written. Directly violates Principle III — one slow driver call freezes the UI.
  Rejected outright.
- *`asyncio` with `run_in_executor`*: adds an event loop to reconcile with Qt's for no gain,
  since every underlying call is blocking C. Rejected as unjustified complexity.
- *A process per backend*: real isolation from a hung driver, and the only way to fully survive
  one. Rejected for now as disproportionate — IPC, serialization, and lifecycle cost against a
  rare failure. Revisit if hangs prove common in practice.

---

## D-05: Process metadata and identity

**Decision**: `psutil` for process name, executable path, owner, and start time. GPU memory
figures never come from `psutil` — only the process identity layered onto a PID that a GPU
source reported.

**Rationale**: PID-to-name resolution is fiddly and different on every OS; `psutil` is the
mature, well-tested answer and ships wheels for Linux and Windows on CPython, so no compiler is
needed. Start time is captured because PIDs are recycled — a PID alone is not a stable identity
across refreshes, and reusing one would misattribute memory to the wrong process (FR-008).

**Race handling**: a process can exit between the GPU query and the `psutil` lookup.
`NoSuchProcess` is expected, not exceptional; such an entry is dropped from that sample rather
than logged as an error.

---

## D-06: Container attribution

**Decision**: On Linux, resolve container membership by reading `/proc/<pid>/cgroup` and matching
the Docker/containerd/Podman ID patterns. No Docker socket access, no daemon API calls.

**Rationale**: FR-029/FR-030 need containerized workloads named. NVML on Linux already reports
host-namespace PIDs, so the process is visible; what's missing is the label saying which
container it belongs to. Reading a proc file requires no privileges, no daemon, and no network —
which matters, because talking to the Docker socket would need group membership the user may not
have and would sit awkwardly against Principle V.

**Limitation**: this yields the container *ID*. Mapping ID to human-readable container *name*
requires the daemon API and is therefore out of scope; the ID is shown truncated. Where a PID
cannot be resolved at all, FR-031 applies: count it in totals, show it as unresolved.

**Windows containers**: out of practical scope — GPU-in-container on Windows is rare and the
cgroup mechanism has no equivalent. Processes appear unresolved.

---

## D-07: Device identity across refreshes

**Decision**: Identify a device by its NVML UUID where available, falling back to PCI bus ID,
falling back to `(vendor, index)`. Identity is computed by the backend and is opaque to `core`.

**Rationale**: FR-002 requires distinguishing two identical GPU models, and the spec's edge cases
require surviving hot-plug. An enumeration index is not stable across a driver restart or an eGPU
disconnect — the same index can become a different physical card, which would splice two devices'
history together. A UUID cannot.

---

## D-08: Device re-enumeration (hot-plug)

**Decision**: Re-enumerate devices on a slow cadence (every ~10 sampling cycles) rather than
subscribing to OS device-change notifications.

**Rationale**: FR-020 requires noticing GPUs appearing and disappearing. Notification APIs are
entirely different on Linux (udev) and Windows (`WM_DEVICECHANGE`), and would put substantial
platform-specific machinery behind a rarely-exercised path. Polled re-enumeration is a few
milliseconds, uniform across platforms, and bounded in worst-case staleness. Cheap and boring
beats correct-but-forked here.

---

## D-09: MIG and virtualized devices

**Decision**: Query `nvmlDeviceGetMigMode`; when MIG is enabled on a device, emit it as a single
device marked `UNSUPPORTED` with the reason "partitioned GPU (MIG) not supported", and do not
report memory or utilization figures for it.

**Rationale**: FR-027/FR-028. Under MIG, whole-device memory figures do not describe what any
particular workload can actually use, so reporting them would be exactly the kind of misleading
number FR-017 forbids. Refusing to report is the honest option.

---

## D-10: Preferences persistence

**Decision**: `QSettings` for storage, in the UI layer only. The preferences *model* is a plain
dataclass in `core` with no Qt import.

**Rationale**: FR-023 needs persistence across sessions; `QSettings` handles the
platform-appropriate location (registry on Windows, config file on Linux) with no code of ours.
Keeping the dataclass Qt-free preserves the constitution's rule that `core` is testable without a
Qt application instance.

---

## D-11: Bounded history

**Decision**: A fixed-capacity `collections.deque` per device per metric, sized from the retention
window and current interval; entries are `(timestamp, value, availability)`.

**Rationale**: FR-005 needs a recent trend and FR-024/SC-005 require bounded memory over a 24-hour
run. A `deque` with `maxlen` makes the bound structural rather than something enforced by a
cleanup routine that could be forgotten. Storing availability alongside the value lets a gap in
the sparkline render as a gap rather than as a drop to zero.

---

## D-12: Testing without GPUs

**Decision**: `pytest` + `pytest-qt`, with a `FakeBackend` driven by scripted scenarios and
recorded NVML fixtures. Qt tests run headless under `QT_QPA_PLATFORM=offscreen`. A shared
contract suite is parametrized over every registered backend, fake ones included.

**Rationale**: Principle IV requires the full suite to pass on machines with no GPU and no
driver — which is every CI runner and most contributor laptops. The `FakeBackend` is not a test
convenience only: it doubles as a demo mode and as the mechanism for exercising failure paths
(timeouts, permission denial, hot-plug, MIG) that are otherwise impossible to trigger on demand.

**Hardware-dependent tests** are marked `@pytest.mark.hardware` and deselected by default, per
Principle IV's rule that they must not gate the default suite.

---

## D-13: Packaging and dependency policy

**Decision**: Base install carries PySide6 + psutil. `nvidia-ml-py` ships as the optional extra
`gpum[nvidia]`, with `gpum[all]` as a convenience. The backend loader treats a missing import
identically to a missing driver.

**Rationale**: The constitution requires vendor bindings to be optional at install time. This is
arguably over-strict for `nvidia-ml-py`, which is pure Python and imports fine without a driver —
but the rule is written plainly and the cost of honoring it is one extras declaration plus a
`try: import` the loader needs regardless. Installation docs lead with `pip install gpum[nvidia]`,
so the recommended path stays a single command.

---

## Spikes required before or during implementation

These are the points where confidence is lower than the rest of the document. Each is small and
each should be settled with real hardware rather than by reasoning.

- **S-01 — Windows PDH counter paths**: confirm the exact counter path strings for `GPU Engine`
  and `GPU Process Memory`, whether instance names reliably encode the PID (`pid_1234_...`), and
  whether they can be read without elevation. Blocks the Windows attribution adapter, not the
  Linux slice.
- **S-02 — WDDM per-process memory**: confirm on a Windows NVIDIA machine that
  `nvmlDeviceGetComputeRunningProcesses_v3` returns PIDs with unusable memory values, and capture
  the exact error or sentinel so it maps to the right `Availability` reason rather than a generic
  failure.
- **S-03 — NVML call latency**: measure the real cost of a full sampling cycle at 1 Hz on a
  multi-GPU machine to set the per-device timeout from data rather than from a guess.
- **S-04 — Driver-restart behavior**: verify NVML's error surface when the driver restarts under
  a running process, and whether re-`nvmlInit()` recovers cleanly or the handles must be rebuilt.

## Resolved unknowns

No `NEEDS CLARIFICATION` markers remain. Language, binding, vendor access path, threading model,
persistence, packaging, and test strategy are all settled above.
