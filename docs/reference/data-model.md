# Data model

The normalized types every backend produces and everything above them consumes. If you read one
page of this reference, read this one: the way absence is represented here is the single design
decision most of GPUM's behaviour follows from.

Source: [`src/gpum/core/models.py`](https://github.com/rs-r2d2/gpum/blob/main/src/gpum/core/models.py)

## `MetricValue` — a measurement and its provenance

Every quantity GPUM reports is a `MetricValue`, never a bare number:

| Field | Meaning |
|---|---|
| `value` | The measurement, or `None` when there isn't one |
| `availability` | Why this is, or is not, a real measurement |
| `reason` | Human-readable explanation, required for most non-available states |
| `sampled_at` | When the measurement was taken |

**PRINCIPLE — a non-measurement may never be presented as a measurement.** This is enforced in
the constructor, not left to discipline:

- an `AVAILABLE` metric without a value raises;
- a non-value-bearing state carrying a value raises;
- a state that owes the user an explanation without a `reason` raises.

So a backend *cannot* claim to have measured something it did not. The rule "never substitute
zero for missing data" is not a guideline here; the type refuses to be built that way.

### `Availability`

| State | Meaning |
|---|---|
| `AVAILABLE` | Measured in this sample |
| `UNSUPPORTED` | This device, driver, or platform cannot report it |
| `PERMISSION_DENIED` | Readable only with privileges GPUM deliberately does not hold |
| `STALE` | The last real measurement, shown with its original timestamp so its true age is visible |
| `DEGRADED` | The source is failing or timing out |
| `NOT_APPLICABLE` | Meaningless for this device |

There is deliberately **no `UNKNOWN`** and no default of zero. Every metric names its own state,
which is what lets the interface explain absence instead of drawing it as a value.

`STALE` is the only non-available state that carries a value: it is the last true reading, and it
travels with the timestamp that says how old it is.

## `DeviceId`

The stable identity of a GPU. Its `key` is derived from a UUID or PCI address and must survive
driver restarts, process restarts, and device reordering — history, sort order, and per-device
preferences all hang off it.

## `GpuDevice`

One GPU at one moment: identity, name, vendor, memory, compute and memory-interface activity,
power draw and enforced limit, session energy, the reason it is being limited, whether it is
supported, and its processes. Every metric on it is a `MetricValue`.

An unsupported device — a partitioned GPU, for instance — appears with `supported=False` and a
reason. It is present in the list because the user can see the card; it simply reports why its
numbers are not shown.

## `GpuProcess` and `PidKey`

A process using a GPU: name, PID, owner, and per-process GPU memory as a `MetricValue`, so
"the driver did not tell us" is distinguishable from "this process holds no memory".

`PidKey` identifies a process across samples. `ProcessIdentity` records how confidently the
process was identified, since name and owner come from the OS rather than the driver.

## `BackendCapabilities`

What a backend can report **on this platform**, right now. The UI adapts to capabilities rather
than to vendor identity — that is what keeps vendor conditionals out of `ui`.

## `BackendReport` and `BackendState`

The outcome of `probe()`: whether the backend is usable and, if not, precisely why —
`LIBRARY_MISSING`, `DRIVER_MISSING`, `NO_DEVICES` and friends are distinguished because each one
sends the reader somewhere different.

## `DiscoveryReport` and `PresentButUnmonitored`

What GPUM found and what it could not monitor. This is what fills the "No GPUs are available to
monitor" panel with a list of what was tried and why each option did not work, instead of a
shrug. A card that is physically present but has no working backend is named, not hidden.

## `Snapshot`

One complete sampling round across every backend: the devices, their processes, and the
discovery report. This is the unit the UI renders and the history stores.

## Related

- [Backend interface](backend-interface.md) — who produces these types
- [Platform adapters](adapters.md) — where process identity and attribution come from
