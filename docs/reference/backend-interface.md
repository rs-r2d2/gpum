# Backend interface

`GpuBackend` is one vendor's view of the machine's GPUs, and the interface constitution
Principle I exists to protect: **adding a vendor must require no change outside its own backend
module and its registration.**

Source: [`src/gpum/backends/base.py`](https://github.com/rs-r2d2/gpum/blob/main/src/gpum/backends/base.py) ·
Contract: [`contracts/backend-interface.md`](https://github.com/rs-r2d2/gpum/blob/main/specs/001-gpu-usage-monitor/contracts/backend-interface.md)

## Attributes

| Attribute | Meaning |
|---|---|
| `vendor` | The `Vendor` this backend speaks for |
| `name` | Stable short name, used by `--backend` and in messages |

## Methods

### `probe() -> BackendReport`

Determine whether this backend can operate at all.

**PRINCIPLE — this must never raise.** An absent driver is an expected condition, not an
exception. A backend that raises here turns a normal machine state into a crash.

It must distinguish `LIBRARY_MISSING` from `DRIVER_MISSING` from `NO_DEVICES`, because each
produces a different user-facing message, and a reader who is told the wrong one goes looking in
the wrong place. It must complete within 2 seconds so startup stays responsive.

### `enumerate_devices() -> Sequence[GpuDevice]`

Every whole physical GPU this backend manages. Returns `[]` when there are none — never `None`.

Each device's `DeviceId.key` must be **stable across calls, driver restarts, and process
restarts**. Derive it from a UUID or PCI address, never from the enumeration index: an index
reorders when a device is added, and history, sort order, and preferences would silently attach
to the wrong card.

Partitioned devices (MIG, for example) are returned with `supported=False` and a reason, not
omitted. A device the user can see must appear, even if its numbers cannot.

### `sample_device(device_id) -> GpuDevice`

One point-in-time reading.

**PRINCIPLE — never substitute a value you do not have.** Every metric carries an accurate
`Availability` and, where unavailable, a reason. Not `0`, not `-1`, not an interpolation. The
`MetricValue` type refuses to be constructed otherwise, so this is enforced rather than merely
requested.

Memory is in **bytes**; unit formatting belongs to `core.units`. The call must be safe to make
concurrently for different devices. Raise `DeviceGoneError` if the device vanished between
enumeration and sampling — the sampler then re-enumerates rather than showing an error, because
a removed eGPU or a restarted driver is a normal event.

### `capabilities() -> BackendCapabilities`

What this backend can report **on the current platform**, not in general. The UI adapts to this
rather than to the vendor's identity, which is what keeps vendor conditionals out of `ui`.

### `shutdown() -> None`

Release vendor resources. Must be idempotent, and safe to call before any successful
initialisation.

## Errors

| Exception | When |
|---|---|
| `BackendError` | A failure the sampler should surface rather than swallow |
| `DeviceGoneError` | The device disappeared between enumeration and sampling |

## What is deliberately absent

There is **no `get_processes()`**. Per-process attribution is a separate contract
([platform adapters](adapters.md)) because its source is not always the vendor: where a driver
cannot supply attribution, an OS-level, vendor-neutral source can — for every vendor at once.
Folding it in here would have forced platform-specific code inside a vendor module.

## Rules for implementers

- Confine every import of the vendor library to a single module, mirroring
  [`backends/nvidia/nvml.py`](https://github.com/rs-r2d2/gpum/blob/main/src/gpum/backends/nvidia/nvml.py). Vendor types must not escape
  that file.
- Do not add a method for something only your vendor can do. Extend `BackendCapabilities` and let
  the UI adapt.
- Do not branch on the operating system inside a backend. That belongs in
  [adapters](adapters.md).
- Your backend inherits roughly thirteen shared contract tests automatically — `pytest
  tests/contract` is parametrized over every registered backend, so you write none of them.

The full procedure is in [adding a vendor](../adding-a-vendor.md).
