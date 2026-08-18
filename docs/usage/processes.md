# The process table

Each device panel lists the processes using that GPU: **process**, **PID**, **user**, and
**GPU memory**.

## Sorting

Click any column header to sort by it; click again to reverse. The order you choose is remembered
per device, so it survives restarts.

**Rows whose value cannot be measured always sort to the bottom — in both directions.** This is
deliberate and it is not what most tables do. If unmeasurable rows sorted as zero, they would
lead the ascending sort and look like processes using no GPU memory at all, which is a claim GPUM
has no evidence for.

## When per-process data is unavailable

Some driver and container setups report which processes are on the GPU but not how much memory
each one holds; others report no per-process data at all. GPUM distinguishes these:

- **No processes are using this GPU** — a measured, empty result.
- **Processes: _reason_** — attribution is unavailable, and the panel says why instead of
  showing an empty list that would look like the first case.
- **A row with unavailable memory** — the process is really there; its memory figure is not
  available. It shows as unavailable rather than as `0`.

## Whose processes you see

Only what your account is allowed to see. GPUM runs unelevated, never asks for root, and never
prompts for credentials. Where elevation would reveal more, it reports reduced capability instead
of trying to acquire it.

GPUM will not terminate a process, change a clock, a power limit, or a fan curve. It observes;
it does not act.
