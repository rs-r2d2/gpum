# Quickstart & Validation: Overall GPU Utilization

**Feature**: 006-overall-gpu-utilization | **Date**: 2026-08-16

No GPU required except where noted.

## Run

```bash
python -m gpum --backend fake --scenario two-nvidia
python -m gpum --backend fake --scenario metrics-unsupported   # utilization unavailable
python -m gpum                                                  # real hardware
```

## Scenarios

### V-1 — The trend appears and moves

**Expect**: a labelled utilization graph beneath the memory graph. Under load it rises within two
intervals; when the load stops it falls and the busy period stays visible.

### V-2 — Idle noise does not look like load *(critical)*

```bash
pytest tests/unit/test_utilization_history.py -k fixed_scale
python -m gpum   # watch an idle GPU
```

**Expect**: an idle GPU sits near the bottom of the graph. **Fail condition**: 0-3% noise filling
the height, which is what auto-scaling would produce and what FR-020 forbids.

### V-3 — Gaps are gaps *(critical)*

```bash
python -m gpum --backend fake --scenario metrics-unsupported
```

**Expect**: where utilization is unreadable the figure says so and the trend breaks. **Fail
condition**: a line dropping to zero, which asserts an idle GPU that was never measured.

### V-4 — Measured zero differs from unavailable

**Expect**: a genuinely idle GPU shows `0%` as a measurement; an unreadable one shows an explicit
unavailable state. The two must not look the same.

### V-5 — The two activity figures cannot be confused

**Expect**: compute activity and memory-interface activity are labelled by what they describe.
**Fail condition**: a bare "MEM %" that reads as memory occupancy — which the same panel already
shows a few lines above.

### V-6 — The process table is still visible *(critical)*

**Expect**: at the default window size, a device panel shows memory, both graphs, power, energy
**and** the process table without scrolling. **Fail condition**: the table pushed below the fold —
that trades something people use for something they glance at.

### V-7 — No core counts anywhere

```bash
pytest tests/integration/test_utilization_display.py -k cores
```

**Expect**: no figure anywhere represents a count or fraction of cores.

### V-8 — Sampling is not more expensive *(needs a GPU)*

**Expect**: per-device query cost unchanged from before the feature. This feature draws data
already collected; if the cost moved, something is being sampled twice.

### V-9 — Agreement with the vendor tool *(needs a GPU)*

**Expect**: reported utilization within 5 percentage points of `nvidia-smi` over 10 minutes.

## Suite

```bash
pytest                # everything for this feature
pytest -m hardware    # V-8, V-9
```
