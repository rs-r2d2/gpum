# GPUM(GPU monitor) 📊

**A friendly, live view of what your GPU is actually doing** — memory, activity, power, and the
processes using it, refreshing every second without ever freezing on you.

🔒 **Read-only. No root needed. Nothing ever leaves your machine.**

📖 **Full documentation: [rs-r2d2.github.io/gpum](https://rs-r2d2.github.io/gpum/)**

![GPUM monitoring an RTX 5060 Ti under load](docs/media/gpum-screenshot.png)

*A real capture, not a mockup: a CUDA kernel was started, stopped, and started again while the
window sampled — that is the plateau, dip, and second plateau in the activity graph, with the
kernel (`spin`) still running and holding compute at 100% at the moment of capture.*

---

## 🚀 Get started

The easiest way is the **AppImage**: one self-contained file with Python and Qt already inside.
Nothing to install, nothing to uninstall — delete the file and it's gone. 🎉

**1.** Grab it from the [**download page**](https://rs-r2d2.github.io/gpum/download/), which
always shows the command for the current release. 📥

**2.** Allow it to run:

```bash
chmod +x GPUM-*-x86_64.AppImage
```

> ⚠️ **Don't skip this one!** Anything you download arrives *without* permission to run, so
> Linux waits for you to say so. Skip it and you get `Permission denied` — or a double-click that
> silently does nothing. It catches almost everybody once.

**3.** Open it:

```bash
./GPUM-*-x86_64.AppImage
```

That's it — your GPUs should appear straight away. ✨

**Prefer pip?** Just as supported:

```bash
git clone https://github.com/rs-r2d2/gpum.git
cd gpum
pip install -e ".[nvidia]"
gpum
```

Python 3.11+, no compiler required. Both forms share the same settings file, so switch between
them whenever you like — your preferences follow you. 👍

### ✅ What you'll need

| | |
|---|---|
| 🐧 **Linux, 64-bit x86** | Ubuntu 22.04 or newer, or anything with glibc 2.35+ |
| 🎮 **An NVIDIA driver** | already installed — the one you already use for graphics is fine |
| 💾 **~50 MB of disk** | that's the whole thing |

Full requirements, the from-source route, and why the driver isn't bundled:
**[Download and install](https://rs-r2d2.github.io/gpum/download/)**.

---

## ✨ What you get

**For every GPU**

- 💾 **Memory used vs total** — as a bar and as a trend graph scaled to the card's capacity.
- ⚡ **GPU compute activity** — the share of *time* the GPU was busy, with its own bar and graph.
- 🔀 **Memory interface activity** — how busy the path to memory was, which moves independently
  of both compute activity and memory occupancy.
- 🔌 **Power draw vs the enforced limit**, plus energy used this session.
- 📋 **The processes using the GPU** — name, PID, owner, and per-process memory, all sortable.

**Across the window** — adjustable refresh interval, pause and refresh-now, one panel per GPU, an
optional tray icon, and start-at-login. Suspend and resume leave an honest gap in history, never
a fabricated straight line.

📘 [**How to read the window**](https://rs-r2d2.github.io/gpum/usage/) explains every bar, graph,
and column — including the one number people most often read as something it isn't.

🧪 No GPU? GPUM ships simulated ones:
[**try it without hardware**](https://rs-r2d2.github.io/gpum/usage/demo-mode/).

---

## 🤝 What GPUM promises you

- 🚫 **It never invents a number.** Every metric is either a real measurement or is shown as
  explicitly unavailable *with a reason*. Nothing missing is rendered as `0`, and a gap in a
  trend graph is drawn as a gap, not a dip to zero.
- 🧊 **It never freezes.** All sampling happens off the interface thread with per-device timeouts.
  One wedged driver degrades one device; everything else keeps updating and the window stays
  responsive.
- ✋ **It never changes anything.** No killing processes, no clock, power, or fan changes. The
  only thing it writes is your own preferences.
- 🔐 **It never phones home.** No telemetry, no network access of any kind — and neither does the
  documentation site.

---

## 💻 Supported hardware

**Linux and NVIDIA.** 🐧🟩 AMD and Intel are registered but not implemented — they say so plainly
in the window rather than pretending. See
[docs/capability-matrix.md](docs/capability-matrix.md) for the full picture of what's verified.

Windows and macOS aren't supported or planned. GPUM is vendor-agnostic by design but
single-platform by scope — the backend abstraction is real and load-bearing; the platform
ambition was dropped (constitution 2.0.0).

---

## 🧯 Something not working?

The [**troubleshooting guide**](https://rs-r2d2.github.io/gpum/usage/troubleshooting/) is
organised by what you saw, not by what caused it. If it isn't there, please
[open an issue](https://github.com/rs-r2d2/gpum/issues) — genuinely happy to help. 💬

---

## 🛠️ Contributing

Contributions are very welcome. 💚

```bash
pip install -e ".[dev]"
pytest
ruff check src tests
```

The suite passes with no GPU present. A failing `tests/unit/test_import_boundaries.py` is a
constitution violation, not a style nit: it means the vendor or platform abstraction has been
breached. Fix the import; don't relax the test.

📗 [**Contributing guide**](https://rs-r2d2.github.io/gpum/contributing/) — development setup,
quality gates, and what the project won't accept. Design documents live in
[specs/](specs/), and the principles the code is held to are in
[.specify/memory/constitution.md](.specify/memory/constitution.md).
