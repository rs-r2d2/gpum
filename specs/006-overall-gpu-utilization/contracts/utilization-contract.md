# Contract: Utilization display

**Modules**: `src/gpum/core/history.py`, `src/gpum/ui/sparkline.py`,
`src/gpum/ui/device_panel.py` | **Feature**: 006-overall-gpu-utilization

---

## History obligations

**MUST**: append compute and memory-interface utilization on every refresh; retain each within a
bounded capacity derived from window and interval; record availability with each point so gaps
survive; keep the window constant when the interval changes.

**MUST NOT**: store a percentage as zero when it was unavailable.

## Trend widget obligations

**MUST**: draw a percentage series against a fixed 0-100 range; break the line across gaps rather
than joining through them; carry a label naming what it shows.

**MUST NOT**: rescale a percentage series to its observed maximum — an idle GPU's noise would
fill the graph and read as heavy load; compute anything on the GUI thread beyond assignment and
repaint.

## Panel obligations

**MUST**: show both activity figures, labelled by what they describe; show a measured 0%
distinctly from an unavailable reading; show whichever figure is available when the other is not;
keep the process table visible at the default window size.

**MUST NOT**: display or allow derivation of a core count or a fraction of cores; label the
memory-interface figure in a way that reads as memory occupancy, which the panel already shows
separately.

## Contract tests

| # | Assertion | Enforces |
|---|-----------|----------|
| U-01 | Both utilization series are appended every refresh | FR-002, FR-021 |
| U-02 | Each series stays within its bounded capacity | FR-007 |
| U-03 | An unavailable reading becomes a gap, never 0 | **FR-005** |
| U-04 | A measured 0% is distinguishable from unavailable | **FR-012** |
| U-05 | Resizing the interval keeps the time window constant | FR-003, SC-006 |
| U-06 | The utilization graph uses a fixed 0-100 scale | **FR-020** |
| U-07 | An idle GPU's noise does not fill the graph | **FR-020** |
| U-08 | Each trend graph carries a label | FR-019 |
| U-09 | The two activity figures are labelled distinctly; neither reads as memory occupancy | **FR-022** |
| U-10 | One figure available and the other not still renders both states | FR-023 |
| U-11 | No core count or fraction appears anywhere | **FR-009** |
| U-12 | The process table stays visible at the default window size | **FR-013, SC-009** |
| U-13 | Per-device sampling cost is unchanged from before the feature | **FR-015, SC-007** |
| U-14 | Rendering 8 devices stays inside the GUI-thread budget | FR-016 |

U-03, U-06, U-11 and U-13 are the load-bearing ones: honesty about gaps, honesty about scale,
honesty about what is not measured, and the claim that this feature is free.
