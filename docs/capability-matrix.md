# Capability Matrix

Constitution Principle II requires this table to be updated in the same change that alters
support. It is the auditable record of what actually works where.

**Legend**: ✅ works · ⚠️ degraded, reported honestly · ❌ not implemented · — not applicable

## Interface

| Capability | Status |
|---|---|
| Click-to-sort column headers | ✅ all four columns, per-device, persisted |
| Sort by process / PID / user / GPU memory | ✅ |
| Rows with unavailable values rank last | ✅ both directions |

## Verification status

**Verified against real hardware on 2026-08-16**: NVIDIA GeForce RTX 5060 Ti, driver
580.159.03, Ubuntu 24.04, GNOME/X11. Evidence:
`specs/002-linux-nvidia-release/verification.json`.

| Check | Result |
|---|---|
| Memory agreement with `nvidia-smi` | max deviation **2.21%**, mean 0.08% (budget 5%) |
| Process match rate | **100%** across 290 process samples |
| Total memory | exact match, 0 mismatches |
| Per-device query cost | 0.031 ms mean, **0.119 ms p99** — timeout now set from this |
| GPUs accounted for | **2 of 2** (NVIDIA monitored, AMD reported as present/unsupported) |

**Power added in feature 004**, verified against `nvidia-smi` on the same hardware: draw 9.1 W
vs 9.16 W, limit 180.0 W exact. The averaging window (8 s) was set from measurement — 30
consecutive idle reads swung 53.7% between consecutive samples, and a 5 s window failed the 10%
readability budget at 17.1%.

**Sampling cost re-measured after power was added**: per-device query went from 0.119 ms p99 to
3.832 ms p99 — a 32x increase. Still 26x inside the 100 ms timeout, but the margin is no longer
enormous.

**Bug found and fixed during verification**: NVML's v1 memory struct reports
`used = total - free`, which includes driver-reserved memory. We reported **1021 MiB** where
`nvidia-smi` reported **550 MiB** — nearly double. Fixed by preferring the v2 struct, which
separates `reserved`. Regression test: `tests/unit/test_memory_reserved.py`.

## Device metrics

| Vendor | Linux | Windows | macOS |
|---|---|---|---|
| NVIDIA — power draw | ✅ **verified vs nvidia-smi** | ✅ NVML (unverified) | ❌ deferred |
| NVIDIA — power limit | ✅ **verified, exact match** | ✅ NVML (unverified) | ❌ deferred |
| NVIDIA — session energy | ✅ **verified** | ✅ NVML (unverified) | ❌ deferred |
| NVIDIA — limiting reason | ✅ **verified** | ✅ NVML (unverified) | ❌ deferred |
| Any vendor — per-process power | ❌ **not possible** — no interface exposes it | ❌ not possible | ❌ not possible |
| Any vendor — physical presence detection | ✅ DRM sysfs (FR-015) | ❌ not implemented | ❌ deferred |
| NVIDIA — memory total/used | ✅ **verified vs nvidia-smi** | ✅ NVML (unverified) | ❌ deferred |
| NVIDIA — utilization | ✅ **verified** | ✅ NVML (unverified) | ❌ deferred |
| NVIDIA — MIG devices | ⚠️ reported unsupported (FR-028) | ⚠️ reported unsupported | ❌ deferred |
| AMD | ❌ stub | ❌ stub | ❌ deferred |
| Intel | ❌ stub | ❌ stub | ❌ deferred |

## Per-process attribution

| Vendor | Linux | Windows | macOS |
|---|---|---|---|
| NVIDIA — process list | ✅ **verified, 100% match** | ⚠️ NVML lists PIDs | ❌ deferred |
| NVIDIA — per-process memory | ✅ **verified** | ⚠️ **unavailable under WDDM** — reported as unsupported with a reason, never 0 (research D-03) | ❌ deferred |
| NVIDIA — per-process utilization | ❌ not reported by NVML | ❌ not reported by NVML | ❌ deferred |
| Any vendor — OS-supplied fallback | ❌ DRM fdinfo not implemented | ❌ PDH counters not implemented (spikes S-01/S-02) | ❌ deferred |

## Process identity

| Capability | Linux | Windows | macOS |
|---|---|---|---|
| Name, executable, owner | ✅ psutil | ✅ psutil | ❌ deferred |
| Inaccessible process → RESTRICTED | ✅ | ✅ | ❌ deferred |
| Container ID | ✅ `/proc/<pid>/cgroup` | ⚠️ no equivalent; shown unresolved | ❌ deferred |

## Known gaps in this release

1. **Windows per-process memory.** NVML cannot supply it under WDDM and the PDH adapter is not
   implemented. Windows shows the process list with memory marked unsupported. This is correct
   behaviour under FR-017, not a bug — but it is the largest functional gap.
2. **AMD and Intel are stubs.** They exist to keep the backend registry plural (Principle I) and
   report `NOT_IMPLEMENTED` in the discovery panel.
3. **AppImage bundle: built and verified.** 50 MB, launches on Ubuntu 22.04 and on the
   development machine's GNOME/X11 session, reports the same version as the pip install.
   Container GPU attribution could not be verified here — `nvidia-container-toolkit` is not
   installed on the reference machine.
4. **macOS is deferred** (FR-025). This remains an open Principle II deviation — see
   `specs/001-gpu-usage-monitor/plan.md` § Complexity Tracking.
