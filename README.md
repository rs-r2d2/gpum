# GPUM

A live GPU monitor: memory, utilization, and the processes consuming each GPU — refreshing
every second without ever blocking its own interface.

**Read-only. No elevation required. Nothing leaves your machine.**

![GPUM monitoring an RTX 5060 Ti under load](docs/media/gpum-screenshot.png)

*A real capture, not a mockup: a CUDA kernel was started and stopped twice while the window
sampled, which is the rise and fall visible in the activity graph.*

## Features

**Per device**

- **Memory used against total**, as a bar and as a trend graph scaled to the device's capacity.
- **GPU compute activity** — the share of *time* the GPU was busy, on its own bar and its own
  trend graph. Not a fraction of cores: one small kernel can hold it at 100%, and the tooltip
  says so, because "utilization" is the number people most often read as something it isn't.
- **Memory interface activity** — how busy the path to memory was, which moves independently of
  both compute activity and memory occupancy. Labelled by what it describes so it cannot be
  confused with the memory figure a few lines above.
- **Power draw against the enforced limit**, plus energy accumulated this session.
- **The processes using the GPU**: name, PID, owner, and per-process GPU memory, sortable.

**Trend graphs** are fixed to a 0–100 scale for percentages, so an idle GPU's 0–3% noise stays
at the bottom instead of being stretched to full height by auto-scaling — and two GPUs stay
comparable. An unreadable stretch is drawn as a **break in the line**, never a drop to zero.

**Across the window**

- Adjustable refresh interval, pause, and refresh-now.
- Multiple GPUs, each in its own panel.
- Suspend and resume leave a gap in history rather than a fabricated straight line.
- Optional tray icon and autostart.

## Install

Two ways, whichever suits you.

**Self-contained download** — no Python needed:

```bash
chmod +x GPUM-0.1.0-x86_64.AppImage
./GPUM-0.1.0-x86_64.AppImage
```

50 MB, carries its own Python and Qt, runs on Ubuntu 22.04 and newer. The only prerequisite is
your NVIDIA driver.

**Python package**:

```bash
pip install -e ".[nvidia]"        # recommended
pip install -e "."                # also valid — NVIDIA support then reports as not installed
gpum --install-desktop-entry      # optional: add it to your application menu
```

Python 3.11+. No compiler needed. Both forms share the same settings file, so you can switch
between them freely.

## Run

```bash
gpum                                        # or: python -m gpum
python -m gpum --backend fake               # simulated GPUs, no hardware needed
python -m gpum --list-scenarios             # what the fake backend can simulate
```

## What it guarantees

- **It never invents a number.** Every metric is either a real measurement or is shown as
  explicitly unavailable *with a reason*. Nothing missing is rendered as `0`, and a gap in the
  trend graph is drawn as a gap, not a dip to zero.
- **It never blocks.** All sampling happens off the GUI thread with per-device timeouts. One
  wedged driver degrades one device; the rest keep updating and the window stays responsive.
- **It never mutates anything.** No process termination, no clock/power/fan changes. The only
  thing it writes is your own preferences.
- **It never phones home.** No telemetry, no network access of any kind.

## Support

See [docs/capability-matrix.md](docs/capability-matrix.md) for exactly what works on which
vendor and platform. In short: **this release covers NVIDIA on Linux and Windows**, with
per-process memory unavailable on Windows under the WDDM driver model (a driver limitation,
reported honestly). AMD and Intel are registered stubs. macOS is deferred.

## Development

```bash
pip install -e ".[dev]"
pytest                    # full suite; passes with no GPU present
pytest -m hardware        # requires a real NVIDIA GPU
ruff check src tests
```

A failing `tests/unit/test_import_boundaries.py` is a constitution violation, not a style nit:
it means the vendor or platform abstraction has been breached. Fix the import; don't relax the
test.

Design documents live in [specs/001-gpu-usage-monitor/](specs/001-gpu-usage-monitor/).
