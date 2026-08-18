# Reading the window

Each GPU gets its own panel, and every panel presents the same things in the same order: a title,
three bars, two trend graphs, power, and the processes using that GPU.

## The three bars

| Bar | What it measures | Scale |
|---|---|---|
| **Memory** | How much of the card's memory is in use, as `used / total` | Your card's capacity |
| **GPU compute** | How much of the *time* the GPU was working during the sampling period | 0–100% |
| **Memory interface** | How much of the time the path to GPU memory was busy | 0–100% |

The third one is labelled by what it describes precisely so it cannot be confused with the memory
figure above it. They move independently: a GPU can be nearly full of memory while doing almost
nothing, and it can be busy while holding very little.

!!! warning "What 'GPU compute 100%' does not mean"
    It means the GPU was *doing something* for the whole sampling period. It does **not** mean
    all its cores were saturated — the hardware does not report that at all. A single small
    kernel can pin this figure at 100% while most of the card sits idle. Hover the label in the
    application and it tells you exactly that, because this is the number people most often read
    as something it isn't.

## The two trend graphs

Below the bars are two graphs: **memory used** over time, and **activity** over time.

Each graph tells you its own scale, so you are never guessing: the label sits on the left, the
**current value in bold** on the right, and the ceiling and floor down the right-hand edge. The
memory graph is scaled to your card's capacity. The activity graph uses a fixed 0–100%.

That fixed scale is deliberate. An idle GPU's 0–3% noise stays near the bottom instead of being
stretched to fill the height and looking like a workload, and two GPUs stay comparable side by
side.

**How far back the graphs look** is the history window, which you can change — see
[controls and settings](controls.md).

## Power

Each panel shows **power draw against the enforced limit**, the **energy used this session**, and
— when the card is being held back — the reason it is being limited. Energy can be reset to zero
without restarting GPUM.

## When something cannot be measured

This is the part worth reading carefully, because GPUM behaves differently here from most tools.

- **A value that cannot be obtained is shown as unavailable, with a reason.** It is never shown
  as `0`. A zero would look like a real measurement of nothing happening, which is a different
  and much more misleading claim than "the driver did not tell us".
- **A gap in a trend graph is drawn as a gap** — a break in the line — not as a drop to zero.
  If your machine suspends and resumes, you get an honest hole in the history rather than a
  fabricated straight line across it.
- **A device that stops responding degrades on its own.** Queries time out per device, so one
  wedged driver marks that one device degraded while every other device keeps updating and the
  window stays responsive.
- **An unsupported device says so.** A partitioned (MIG) GPU, for example, reports that it is not
  supported instead of showing numbers that would not mean what they appear to mean.

You can see every one of these states without owning the hardware that produces them — see
[try it without a GPU](demo-mode.md).
