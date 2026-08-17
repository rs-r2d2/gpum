# Capability Matrix

Constitution Principle II requires this table to be updated in the same change that alters
support. It is the auditable record of what actually works where.

**Platform: Linux only.** The Windows and macOS columns were removed in the same change that
dropped both as targets (constitution 2.0.0). They are not hidden pending work — no claim is
made about either. This is why the table is now a single column: it records measurements, and
Linux is the only platform GPUM is measured on.

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

| Vendor | Linux |
|---|---|
| NVIDIA — power draw | ✅ **verified vs nvidia-smi** |
| NVIDIA — power limit | ✅ **verified, exact match** |
| NVIDIA — session energy | ✅ **verified** |
| NVIDIA — limiting reason | ✅ **verified** |
| Any vendor — per-process power | ❌ **not possible** — no interface exposes it |
| Any vendor — physical presence detection | ✅ DRM sysfs (FR-015) |
| NVIDIA — memory total/used | ✅ **verified vs nvidia-smi** |
| NVIDIA — utilization | ✅ **verified** |
| NVIDIA — MIG devices | ⚠️ reported unsupported (FR-028) |
| AMD | ❌ stub |
| Intel | ❌ stub |

## Per-process attribution

| Vendor | Linux |
|---|---|
| NVIDIA — process list | ✅ **verified, 100% match** |
| NVIDIA — per-process memory | ✅ **verified** |
| NVIDIA — per-process utilization | ❌ not reported by NVML |
| Any vendor — OS-supplied fallback | ❌ DRM fdinfo not implemented |

Per-process memory is still handled as nullable end to end: where a driver returns a PID with no
memory figure, it is reported `UNSUPPORTED` with a reason rather than `0`. That path is tested
and reachable — it is not Windows-specific residue.

## Process identity

| Capability | Linux |
|---|---|
| Name, executable, owner | ✅ psutil |
| Inaccessible process → RESTRICTED | ✅ |
| Container ID | ✅ `/proc/<pid>/cgroup` |

## Known gaps in this release

1. **AMD and Intel are stubs.** They exist to keep the backend registry plural (Principle I) and
   report `NOT_IMPLEMENTED` in the discovery panel. This is now the largest functional gap.
2. **AppImage bundle: built and verified.** 50 MB, launches on Ubuntu 22.04 and on the
   development machine's GNOME/X11 session, reports the same version as the pip install.
   Container GPU attribution could not be verified here — `nvidia-container-toolkit` is not
   installed on the reference machine.
3. **No DRM fdinfo adapter.** A vendor-neutral, OS-supplied attribution source on Linux is not
   implemented. It is not needed for NVIDIA, which supplies its own, but it is what AMD and Intel
   would need before their stubs could report processes.

## Not gaps: platforms

Windows and macOS are **not supported and not planned**. They are absent from this document
rather than listed as deferred, because a deferred row is a commitment and there is none. The
adapter boundary that made them cheap to add still stands (`src/gpum/adapters/`), so this is a
scope decision, not a one-way door.
