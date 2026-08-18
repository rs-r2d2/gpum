# Try it without a GPU

GPUM ships simulated GPUs, so you can explore the entire interface with no hardware, no driver,
and nothing installed but GPUM itself.

```bash
gpum --backend fake                        # two healthy GPUs
gpum --backend fake --scenario mig-device   # a specific situation
gpum --list-scenarios                       # print all eight with their descriptions
```

The bundle takes these flags too:

```bash
./GPUM-*-x86_64.AppImage --backend fake --scenario no-attribution
```

## The eight scenarios

These are not decorative. Each one models a shape that real hardware or a real driver can
produce — including several that NVIDIA's own library never produces — so that the honest
handling of missing data is something you can see rather than something you have to trust.

| Scenario | What it demonstrates |
|---|---|
| `two-nvidia` | Two healthy NVIDIA GPUs — the happy path (V-1). Start here |
| `processes-churn` | Processes appearing and disappearing every cycle (V-2). Shows the table under constant change |
| `no-attribution` | Device metrics work, per-process data does not — the shape of a driver that lists no processes (V-3). The UI must explain, not show an empty list. |
| `metrics-unsupported` | A device that cannot report utilization at all (V-3). NVML always can, so this shape exists purely to break NVML-shaped assumptions. |
| `one-device-hangs` | One device blocks on query while others stay healthy (V-5). Watch the healthy devices keep updating |
| `mig-device` | A partitioned GPU, which must be reported unsupported (FR-028). |
| `multi-vendor-degraded` | Mixed vendors in one list, one of them degraded (V-1, US3). Shows how an unimplemented vendor presents itself |
| `empty` | No devices at all — the tool must stay usable (FR-018, V-4). |

## Why this exists

Two reasons, and the second is the interesting one.

The obvious one: you can evaluate GPUM before installing a driver, and you can reproduce a
screenshot without owning the card in it.

The other: these scenarios are also what the test suite runs against, which is why the full suite
passes on a machine with no GPU. A situation you can reproduce from the command line is a
situation a bug report can be written about — and a situation the project can regression-test.
See [contributing](../contributing/development.md).
