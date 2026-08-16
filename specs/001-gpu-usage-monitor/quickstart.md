# Quickstart & Validation Guide: GPU Usage Monitor

**Feature**: 001-gpu-usage-monitor | **Date**: 2026-08-16

How to run the application and prove the feature works. This is a validation guide — implementation
belongs in `tasks.md` and the code itself.

---

## Prerequisites

- Python 3.11+ on Linux or Windows (FR-025)
- No GPU, driver, or vendor SDK required to run the test suite (constitution Principle IV)
- An NVIDIA GPU with a working driver required only for the `hardware`-marked tests

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e ".[nvidia,dev]"     # nvidia extra per D-13; dev brings pytest + pytest-qt
```

`pip install -e ".[dev]"` alone is a valid configuration: without the `nvidia` extra the NVIDIA
backend reports `LIBRARY_MISSING` and the app still runs. That is a supported state, not an error
— it is one of the paths SC-006 requires to work.

## Run

```bash
gpum                    # installed entry point
python -m gpum          # equivalent

python -m gpum --backend fake       # simulated GPUs; no hardware needed
python -m gpum --backend fake --scenario multi-vendor-degraded
```

The `fake` backend is the primary way to demo and validate without hardware.

---

## Validation scenarios

Each maps to spec acceptance criteria. Scenarios 1–6 need **no GPU**.

### V-1 — Device view (US1, SC-001)

```bash
python -m gpum --backend fake --scenario two-nvidia
```

**Expect**: two devices listed within 3 s, each with model name, used/total memory, percent used,
and utilization. Values change every second unprompted. The window resizes and scrolls smoothly
throughout.

### V-2 — Process attribution (US2, FR-006 – FR-009)

```bash
python -m gpum --backend fake --scenario processes-churn
```

**Expect**: a process list per device with name, PID, and memory. Processes appear and disappear
within two refresh intervals, with no error dialogs and no stale rows. One process shows as
**restricted** and is still counted in the device total (FR-009).

### V-3 — Honest degradation (FR-017, SC-007) — *the critical one*

```bash
python -m gpum --backend fake --scenario no-attribution
python -m gpum --backend fake --scenario metrics-unsupported
```

**Expect**: the process area states per-process data is unavailable **and why** — it does not show
an empty list (US2 scenario 4). Unsupported metrics read "Not supported", never `0` and never
blank. The sparkline shows a **gap** across the unavailable stretch, not a dip to zero.

**Fail condition**: any zero, dash, or blank where a real measurement was not obtained. This is
the highest-value manual check in the guide; SC-007 is the requirement most easily broken by a
well-meant "just show a dash" change.

### V-4 — No GPU present (FR-018, SC-006)

```bash
python -m gpum --backend none
```

**Expect**: the window opens and states what was searched for and what was found, per backend —
e.g. "NVIDIA: driver not loaded", "AMD: not implemented in this release". No crash, no blank
window, no traceback.

### V-5 — Timeout and degradation (FR-014, U-02/U-03)

```bash
python -m gpum --backend fake --scenario one-device-hangs
```

**Expect**: the hanging device goes `STALE`, then `DEGRADED` after three cycles, showing its last
value with its true age. **Every other device keeps updating at full cadence and the UI never
freezes.** Recovery is automatic when the scenario releases the hang.

### V-6 — Preferences persist (FR-023, US4)

Change the interval to 5 s, sort by memory, close, reopen.

**Expect**: both settings still in effect. Sort order stays stable across refreshes — rows must
not reshuffle on every update (FR-010).

### V-7 — Real NVIDIA hardware (requires a GPU)

```bash
pytest -m hardware
python -m gpum
```

**Expect**: real devices with plausible figures. Start a CUDA workload and watch used memory rise
within two intervals, then fall on exit.

**On Linux**: per-process memory is populated. **On Windows (WDDM)**: per-process memory shows as
unsupported with a reason until the PDH adapter lands (D-03) — that is correct behavior, not a
bug.

### V-8 — Container attribution (Linux + Docker, FR-029/030, SC-012)

```bash
docker run --rm --gpus all -d nvidia/cuda:12.4.0-base-ubuntu22.04 \
  bash -c "sleep 600"
```

**Expect**: the containerized process appears attributed to the correct GPU, marked as
containerized with a truncated container ID. Device totals account for its memory whether or not
it can be named (SC-012).

---

## Test suite

```bash
pytest                              # full suite; MUST pass with no GPU present
pytest tests/contract               # backend + attribution contracts, all backends
pytest -m hardware                  # deselected by default; needs real hardware
pytest --cov=gpum --cov-report=term-missing
```

Qt tests run headless via `QT_QPA_PLATFORM=offscreen`, set in `pytest.ini` so CI needs no display
server.

**A failing `tests/unit/test_import_boundaries.py` is a constitution violation, not a style
nit** — it means the vendor or platform abstraction has been breached (Principle I / II). Fix the
import; do not relax the test.

---

## Layout and contracts

- Package structure and layering rules: [plan.md](./plan.md) § Project Structure
- Types and their invariants: [data-model.md](./data-model.md)
- Adding a vendor: [contracts/backend-interface.md](./contracts/backend-interface.md)
- Attribution sources: [contracts/process-attribution.md](./contracts/process-attribution.md)
- Thread boundary: [contracts/ui-update-contract.md](./contracts/ui-update-contract.md)

---

## Adding a vendor backend later (AMD/Intel)

The path Principle I is designed to keep short:

1. Implement `GpuBackend` in `src/gpum/backends/<vendor>/backend.py`, replacing the stub.
2. Register it in `core/registry.py`.
3. Add a `ProcessAttributionProvider` **only if** the vendor itself supplies attribution;
   otherwise the platform adapter already covers it.
4. Run `pytest tests/contract` — the shared suite applies automatically, no new test authoring.
5. Update the capability matrix (constitution Principle II).

**No change to `core/`, `ui/`, or any other backend should be required.** If one is, the
abstraction has failed and the interface — not the caller — needs revisiting.
