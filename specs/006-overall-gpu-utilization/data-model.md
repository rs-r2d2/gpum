# Phase 1 Data Model: Overall GPU Utilization

**Feature**: 006-overall-gpu-utilization | **Date**: 2026-08-16

No new types. One new history series and one widget capability.

---

## `DeviceHistory` addition (`core/history.py`)

| Series | Status | Contents |
|--------|--------|----------|
| `memory_used` | existing | bytes |
| `utilization` | **existing, collected, never drawn** | percent |
| `power_draw` | existing | watts |
| `memory_utilization` | **new** | percent |

The compute-utilization series already exists and is appended on every refresh — it simply has
no consumer. This feature adds a consumer, and adds the fourth series so the memory-interface
figure gets the same bounded, gap-aware treatment.

**Unchanged behaviour, and it must stay unchanged**: capacity is derived from the retention
window and the refresh interval, resizing keeps the window constant, and every point carries its
availability so an unavailable stretch renders as a gap rather than a dip to zero.

---

## Sparkline capability (`ui/sparkline.py`)

| Property | Purpose |
|----------|---------|
| fixed maximum | Draw against a fixed 0-100 range instead of the observed peak |
| label | Name what the graph shows |

**Why a fixed maximum matters.** The memory trend scales to the device's total memory, which is
right for a quantity whose ceiling is a hardware property. A percentage already *is* a fraction
of a fixed maximum, so rescaling it to the recent peak would make an idle GPU's 0-3% noise fill
the graph and read as sustained heavy load — and would make two GPUs incomparable, each drawn
against its own peak.

---

## Panel composition (`ui/device_panel.py`)

Two activity figures, labelled by what they describe rather than by position:

| Figure | Source | Label conveys |
|--------|--------|---------------|
| Compute activity | `utilization_gpu` | how much of the time the GPU was working |
| Memory-interface activity | `utilization_memory` | how busy the path to memory was |

**The naming trap.** The memory-interface figure is *not* how full the memory is — the panel
already shows memory occupancy a few lines above. Labelling this one "MEM %" would put two
unrelated memory numbers on the same panel. The label must say it describes interface activity.

**Vertical budget**: the utilization graph takes a fixed modest height, and the process table
keeps a minimum visible area. Verified at the default window size (SC-009), not assumed.
