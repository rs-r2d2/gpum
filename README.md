# GPUM

A live GPU monitor: memory, utilization, and the processes consuming each GPU — refreshing
every second without ever blocking its own interface.

**Read-only. No elevation required. Nothing leaves your machine.**

![GPUM monitoring an RTX 5060 Ti under load](docs/media/gpum-screenshot.png)

*A real capture, not a mockup: a CUDA kernel was started, stopped, and started again while the
window sampled — that is the plateau, dip, and second plateau in the activity graph, with the
kernel (`spin`) still running and holding compute at 100% at the moment of capture.*

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
comparable. An unreadable stretch is drawn as a **break in the line**, never a drop to zero. Each
graph states its own ceiling and current value, so the two are never mistaken for the same chart:
memory is scaled to the card's capacity, activity to a flat 100%. Line and label colours are
checked against the background they land on and corrected if they fall short, in light themes and
dark ones alike.

**Across the window**

- Adjustable refresh interval, pause, and refresh-now.
- Multiple GPUs, each in its own panel.
- Suspend and resume leave a gap in history rather than a fabricated straight line.
- Optional tray icon and autostart.

## Download and run

One file, 50 MB, carrying its own Python and Qt. No install step, no Python on your machine, no
compiler, no root.

**1. Download it.** Grab `GPUM-0.1.0-x86_64.AppImage` from the
[releases page](https://github.com/rs-r2d2/gpum/releases), or from a shell:

```bash
curl -L -O https://github.com/rs-r2d2/gpum/releases/download/v0.1.0-alpha.2/GPUM-0.1.0-x86_64.AppImage
```

Note the explicit version tag. Every release so far is marked *pre-release*, and GitHub's
`/releases/latest/` redirect deliberately skips pre-releases — so a `latest` URL returns **404**
here rather than the newest build. Check the releases page for the current tag.

**2. Make it executable.**

```bash
chmod +x GPUM-0.1.0-x86_64.AppImage
```

**This step is required, not a formality.** A file that arrives over HTTP has its execute bit
cleared, because a browser or `curl` has no way to know you intend to *run* what you just
fetched — so the kernel refuses to launch it until you say so. Skip this and the file is inert:
the shell answers `bash: ./GPUM-0.1.0-x86_64.AppImage: Permission denied`, and double-clicking it
in a file manager either opens an archive viewer or does nothing at all. Neither failure mentions
permissions, which is why this trips people up.

**3. Run it.**

```bash
./GPUM-0.1.0-x86_64.AppImage
```

It takes the same flags as the packaged command, so `./GPUM-0.1.0-x86_64.AppImage --backend fake`
works if you want to look around without a GPU.

**What it needs from your machine**: 64-bit x86 Linux, glibc 2.35 or newer (Ubuntu 22.04 and up),
and your NVIDIA driver already installed. The bundle deliberately does **not** carry NVIDIA's
libraries — those are version-locked to your running kernel module, so a bundled copy would
either fail to initialise or, worse, report a build machine's numbers as if they were yours.

## Install as a Python package

```bash
pip install -e ".[nvidia]"        # recommended
pip install -e "."                # also valid — NVIDIA support then reports as not installed
gpum --install-desktop-entry      # optional: add it to your application menu
```

Python 3.11+. No compiler needed. Both forms share the same settings file, so you can switch
between them freely.

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

See [docs/capability-matrix.md](docs/capability-matrix.md) for exactly what works. In short:
**Linux only, NVIDIA only.** AMD and Intel are registered stubs that report themselves as
unimplemented rather than pretending.

Windows and macOS are not supported and not planned. GPUM is vendor-agnostic by design but
single-platform by scope — the backend abstraction is real and load-bearing, the platform
ambition was dropped (constitution 2.0.0).

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
