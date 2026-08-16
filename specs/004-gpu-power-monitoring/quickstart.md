# Quickstart & Validation: GPU Power Monitoring

**Feature**: 004-gpu-power-monitoring | **Date**: 2026-08-16

## Prerequisites

V-1 … V-6 need no GPU. V-7 … V-9 need a real NVIDIA GPU (`-m hardware`).

## Validation scenarios

### V-1 — Unavailable power is never zero watts *(no GPU)* — **critical**

```bash
pytest tests/unit/test_power_smoothing.py -k unavailable
```

**Expect**: a device that cannot report power shows an explicit unavailable state with a reason.
**Fail condition**: `0 W` anywhere. Zero watts asserts the card is off, which is a different
claim from "we could not read it".

### V-2 — The average never spans a gap *(no GPU)* — **critical**

```bash
pytest tests/unit/test_power_smoothing.py -k gap
```

**Expect**: an unavailable reading clears the buffer; the next average uses only readings that
follow. **Fail condition**: an average blending values from either side of an interruption —
that manufactures a number for a period nobody measured.

### V-3 — Smoothing stays responsive *(no GPU)*

```bash
pytest tests/unit/test_power_smoothing.py -k step
```

**Expect**: a step from 20 W to 150 W is ~80% reflected within two samples. Smoothing must not
buy readability by breaking FR-004.

### V-4 — Energy survives a counter reset *(no GPU)*

```bash
pytest tests/unit/test_energy_accumulator.py
```

**Expect**: when the counter goes backwards, the accumulated total carries forward and the
figure never goes negative. Suspend re-baselines rather than banking sleep as consumption.

### V-5 — Limit reasons are five distinct states *(no GPU)*

```bash
pytest tests/unit/test_limit_reasons.py
```

**Expect**: "nothing is limiting this" and "could not determine" are different. The first is a
measurement; the second is its absence.

### V-6 — Read-only is mechanical *(no GPU)*

```bash
pytest tests/unit/test_read_only.py
```

**Expect**: no module references a power-limit setter. The same interface we read from can
write; this test is what stops that becoming a slider later.

### V-7 — Agreement with nvidia-smi *(needs a GPU)*

```bash
pytest -m hardware tests/hardware/test_power_agreement.py
```

**Expect**: reported draw within 10% of `nvidia-smi --query-gpu=power.draw`, and the limit
matching exactly. The limit is static, so any disagreement there is a unit bug.

### V-8 — Watch it under load *(needs a GPU)*

```bash
python -m gpum
```

Start a GPU workload. **Expect**: draw climbs within two intervals and falls back after; the
displayed figure is readable rather than flickering; energy increases monotonically.

### V-9 — Energy sanity *(needs a GPU)*

**Expect**: session watt-hours agree within 5% with the integral of observed draw over the same
period. The counter is the instrument; the integral is the cross-check.

## Suite

```bash
pytest                # default: no GPU. MUST stay green.
pytest -m hardware    # needs a real NVIDIA GPU
```
