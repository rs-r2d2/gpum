# Contract: `GpuBackend`

**Module**: `src/gpum/backends/base.py` | **Feature**: 001-gpu-usage-monitor

The interface every vendor backend implements. This is the boundary constitution Principle I
exists to protect: adding a vendor must require no change outside its own backend module and its
registration.

Implementations MUST NOT import `gpum.core`, `gpum.ui`, or `gpum.adapters`. Enforced by
`tests/unit/test_import_boundaries.py`.

---

## Protocol

```python
class GpuBackend(Protocol):
    vendor: Vendor
    name: str

    def probe(self) -> BackendReport: ...
    def enumerate_devices(self) -> Sequence[GpuDevice]: ...
    def sample_device(self, device_id: DeviceId) -> GpuDevice: ...
    def capabilities(self) -> BackendCapabilities: ...
    def shutdown(self) -> None: ...
```

Note what is **absent**: there is no `get_processes()`. Per-process attribution is a separate
contract ([process-attribution.md](./process-attribution.md)) because its source is not always the
vendor — NVIDIA under WDDM cannot supply it at all, while the Windows OS can supply it for every
vendor. Folding it in here would have forced platform-specific code inside a vendor module.

A backend that *can* supply attribution (NVIDIA on Linux) registers a companion
`ProcessAttributionProvider`; it does not widen this interface.

---

## Method contracts

### `probe() -> BackendReport`

Determines whether this backend can operate. Called once at startup and on re-enumeration.

**MUST**:
- Return a `BackendReport` in all cases. **Never raise.** A backend that raises during probe is a
  bug — an absent driver is an expected condition (FR-018), not an exception.
- Distinguish `LIBRARY_MISSING` (binding not installed) from `DRIVER_MISSING` (installed, no
  driver) from `NO_DEVICES` (working, zero devices). These produce different user-facing messages
  and conflating them makes SC-006's "clear, actionable message" impossible.
- Complete within 2 seconds, so startup meets SC-001's 3-second budget.
- Populate `detail` with a sentence fit to show a user.

**MUST NOT**: require elevated privileges (FR-019); write to disk; touch the network (FR-022).

### `enumerate_devices() -> Sequence[GpuDevice]`

Returns all whole physical GPUs this backend manages.

**MUST**:
- Return `[]` when none are present — never raise, never return `None`.
- Assign each device a `DeviceId.key` stable across calls, driver restarts, and process restarts
  (D-07). UUID preferred; PCI bus ID next; `vendor:index` last resort.
- Mark partitioned or virtualized devices `supported=False` with an `unsupported_reason`, and
  omit their metrics (FR-027, FR-028).
- Set each device's `attribution` field to whether per-process data can be obtained **for that
  device on this platform** — the value driving US2 scenario 4's honest message.

**MUST NOT**: return the same `key` for two devices in one call; treat enumeration index as
identity.

### `sample_device(device_id) -> GpuDevice`

One point-in-time reading.

**MUST**:
- Return every metric as a `MetricValue` with an accurate `Availability` and, when not available,
  a `reason` (FR-017).
- Map vendor error codes to specific states — not-supported → `UNSUPPORTED`, permission → 
  `PERMISSION_DENIED`. A generic catch-all defeats the purpose of the enum.
- Report memory in **bytes**. Unit normalization is `core/units.py`'s job, and a backend doing its
  own conversion is how rounding inconsistencies enter (FR-004).
- Be safe to call from a worker thread, and from a thread pool concurrently with calls for other
  devices.
- Raise `DeviceGoneError` if the device has disappeared, so the sampler can re-enumerate (FR-020).

**MUST NOT**:
- Substitute `0`, `-1`, or an estimate for an unobtainable value. **This is the single most
  important rule in the contract** — it is SC-007, and the `MetricValue` invariant
  (`value is None` iff not `AVAILABLE`) makes violating it fail construction rather than reach the
  screen.
- Block indefinitely. The sampler applies a timeout, but that abandons the *wait*, not the
  *call* — a genuinely hung call holds a pool thread until the driver returns.
- Cache across calls. Freshness is the sampler's concern, and a backend-level cache would make
  `sampled_at` a lie.

### `capabilities() -> BackendCapabilities`

Declares what this backend can report, so the UI can lay out columns without probing every device.

```python
@dataclass(frozen=True)
class BackendCapabilities:
    device_memory: bool
    device_utilization: bool
    per_process_memory: bool      # False for NVIDIA on Windows/WDDM
    per_process_utilization: bool
    supports_hotplug: bool
```

**MUST** reflect the *current platform*, not the vendor's capability in general.

### `shutdown() -> None`

Releases vendor resources. **MUST** be idempotent and **MUST NOT** raise, including when
initialization never succeeded.

---

## Contract test suite

`tests/contract/test_backend_protocol.py` is parametrized over **every** registered backend,
including `FakeBackend` and the AMD/Intel stubs. A new backend is wired into the registry and
inherits the suite — no per-vendor test authoring.

| # | Assertion | Enforces |
|---|-----------|----------|
| C-01 | `probe()` never raises, under any environment | FR-018 |
| C-02 | `probe()` returns a distinct state for missing library vs missing driver vs no devices | SC-006 |
| C-03 | `enumerate_devices()` returns `[]`, never `None`, when nothing is present | FR-018 |
| C-04 | Device keys are unique within a call and stable across calls | FR-002, D-07 |
| C-05 | Every `MetricValue` satisfies `value is None ⟺ availability != AVAILABLE` | **SC-007** |
| C-06 | Every non-`AVAILABLE` metric carries a non-empty `reason` | FR-017 |
| C-07 | Memory values are in bytes and never negative | FR-004 |
| C-08 | Devices reporting `supported=False` carry a reason and expose no metrics | FR-028 |
| C-09 | `shutdown()` is idempotent and safe before any successful init | — |
| C-10 | `capabilities()` matches what `sample_device()` actually returns | FR-017 |
| C-11 | Concurrent `sample_device()` calls for different devices are safe | Principle III |
| C-12 | No module under `backends/` imports `core`, `ui`, or `adapters` | **Principle I** |
| C-13 | No module outside `backends/nvidia/nvml.py` imports `pynvml` | **Principle I** |

C-05, C-12, and C-13 are the mechanical guards. They are why NVIDIA-first delivery does not
quietly become an NVML-shaped interface.

---

## Reference implementations this release

| Backend | State | Purpose |
|---------|-------|---------|
| `nvidia` | Full | The shipping backend (D-02) |
| `amd` | Stub — `NOT_IMPLEMENTED` | Keeps the registry plural; exercises the unsupported-vendor UI path |
| `intel` | Stub — `NOT_IMPLEMENTED` | Same |
| `fake` | Full, scripted | Tests and demo mode; deliberately models devices NVML cannot produce — no-utilization, no-attribution, MIG, timeout-on-demand — so NVML-shaped assumptions fail a test (D-12) |
