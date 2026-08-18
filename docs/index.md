# GPUM

**A friendly, live view of what your GPU is actually doing** — memory, activity, power, and the
processes using it, refreshing every second without ever freezing on you.

**Read-only. No root needed. Nothing ever leaves your machine.**

[Download GPUM](download.md){ .md-button .md-button--primary }
[See how to read it](usage/index.md){ .md-button }

![The GPUM window monitoring an NVIDIA RTX 5060 Ti under load: a device panel showing memory used
against total, GPU compute activity and memory interface activity as bars, two trend graphs
below them, and a table of the processes using the GPU with their names, PIDs, owners and
per-process GPU memory.](media/gpum-screenshot.png)

*A real capture, not a mockup: a CUDA kernel was started, stopped, and started again while the
window sampled — that is the plateau, dip, and second plateau in the activity graph, with the
kernel (`spin`) still running and holding compute at 100% at the moment of capture.*

## What you need

| | |
|---|---|
| **Linux, 64-bit x86** | Ubuntu 22.04 or newer, or anything with glibc 2.35+ |
| **An NVIDIA driver** | Already installed — the one you use for graphics is fine |
| **About 50 MB of disk** | That is the whole thing |

Windows and macOS are not supported and not planned. AMD and Intel are registered but not yet
implemented, and the window says so plainly rather than pretending. The
[capability matrix](capability-matrix.md) is the full record of what is verified to work.

No GPU at all? GPUM ships simulated ones, so you can
[explore the whole interface](usage/demo-mode.md) without any hardware.

## What GPUM promises you

- **It never invents a number.** Every metric is either a real measurement or is shown as
  explicitly unavailable *with a reason*. Nothing missing is rendered as `0`, and a gap in a
  trend graph is drawn as a gap, not a dip to zero.
- **It never freezes.** All sampling happens off the interface thread with per-device timeouts.
  One wedged driver degrades one device; everything else keeps updating and the window stays
  responsive.
- **It never changes anything.** No killing processes, no clock, power, or fan changes. The only
  thing it writes is your own preferences.
- **It never phones home.** No telemetry, no network access of any kind — and neither does this
  website.

## Where to go next

| If you want to… | Go to |
|---|---|
| Get it running | [Download and install](download.md) |
| Understand the window | [Reading the window](usage/index.md) |
| Fix something | [Troubleshooting](usage/troubleshooting.md) |
| Extend or integrate | [Reference](reference/index.md) |
| Contribute | [Contributing](contributing/index.md) |
