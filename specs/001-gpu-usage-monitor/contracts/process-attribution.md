# Contract: `ProcessAttributionProvider` and `ProcessIdentityProvider`

**Module**: `src/gpum/adapters/base.py` | **Feature**: 001-gpu-usage-monitor

Two interfaces answering two different questions:

- **`ProcessAttributionProvider`** — *which PIDs are using which GPU, and how much memory?*
- **`ProcessIdentityProvider`** — *given a PID, what is it?*

They are separate because their sources differ per platform and they fail independently. Knowing
a GPU is consuming 4 GB under PID 8321 is useful even when the process cannot be named — and
FR-031 requires that partial knowledge to reach the user rather than be discarded.

---

## Why this is not part of `GpuBackend`

Established in [research.md](../research.md) D-03. The source of attribution varies by
*platform*, not only by vendor:

| Vendor | Platform | Attribution source |
|--------|----------|--------------------|
| NVIDIA | Linux | NVML — vendor-supplied |
| NVIDIA | Windows | **Not available from NVML under WDDM.** Windows PDH counters instead |
| AMD/Intel | Linux (future) | DRM `fdinfo` — OS-supplied, vendor-neutral |
| AMD/Intel | Windows (future) | Windows PDH counters — same source as NVIDIA |

Putting attribution in `GpuBackend` would have required Windows PDH code inside the NVIDIA
backend, breaking Principle I (vendor module carrying platform logic) *and* Principle II (OS
branching outside `adapters/`) in a single stroke.

---

## `ProcessAttributionProvider`

```python
class ProcessAttributionProvider(Protocol):
    source_name: str

    def probe(self) -> AttributionSupport: ...
    def attribute(self, devices: Sequence[GpuDevice]) -> AttributionResult: ...
```

### `probe() -> AttributionSupport`

```python
@dataclass(frozen=True)
class AttributionSupport:
    available: bool
    supports_memory: bool
    supports_utilization: bool
    reason: str | None          # required when available is False
    requires_elevation: bool
```

**MUST** never raise, and **MUST** reflect the running platform and privilege level. When
`requires_elevation` is true but the process is unelevated, `available` is `False` with a reason
naming elevation — surfacing FR-019's "labeled as requiring elevated privileges" rather than
silently showing nothing.

### `attribute(devices) -> AttributionResult`

```python
@dataclass(frozen=True)
class AttributionResult:
    processes: tuple[GpuProcess, ...]
    per_device: Mapping[str, Availability]   # device_key → attribution state
    total_attributed: Mapping[str, int]      # device_key → bytes accounted for
```

**MUST**:
- Return an `Availability` for **every** device key passed in — including devices it cannot
  attribute. A device missing from `per_device` is indistinguishable from a device with no
  processes, which is exactly the ambiguity US2 scenario 4 forbids.
- Emit a `GpuProcess` with `identity_state=UNRESOLVED` for any PID it sees but cannot identify,
  counting its memory in `total_attributed` regardless (**FR-031**). Never drop it.
- Emit `identity_state=RESTRICTED` for processes visible but not inspectable at this privilege
  level (FR-009).
- Report memory in bytes, `UNSUPPORTED` where the source cannot supply it — on
  NVIDIA/Windows/WDDM, PIDs are returned with `memory_used` as `UNSUPPORTED`, not `0`.
- Tolerate a process exiting mid-call. Disappearance is expected, not an error (D-05).
- Complete within the sampler's per-cycle budget or be timed out and marked `STALE`.

**MUST NOT**:
- Infer or apportion memory. If the source doesn't say, the answer is `UNSUPPORTED` (SC-007).
- Require the Docker socket, a daemon connection, or elevation (Principle V, D-06).
- Emit a process for a `device_key` that was not in `devices`.

---

## `ProcessIdentityProvider`

```python
class ProcessIdentityProvider(Protocol):
    def identify(self, pids: Sequence[PidKey]) -> Mapping[PidKey, ProcessIdentityInfo]: ...
```

`PidKey` is `(pid, started_at)` — not a bare PID. PIDs are recycled, and a bare PID would let a
new process inherit an exited one's identity and memory attribution (D-05).

`ProcessIdentityInfo` carries `name`, `executable`, `username`, `container_id`, and
`identity_state`.

**MUST**:
- Take PIDs in **one batch call**. A per-PID call at 1 Hz across hundreds of processes is a
  measurable load on the machine being measured.
- Return an entry for every requested key — `UNRESOLVED` rather than a missing key.
- Map `psutil.AccessDenied` to `RESTRICTED`, `psutil.NoSuchProcess` to omission-with-`UNRESOLVED`,
  never to an exception reaching the sampler.
- Resolve container membership from `/proc/<pid>/cgroup` on Linux, setting `container_id` and
  `identity_state=CONTAINERIZED` (FR-029, FR-030).

**MUST NOT**: shell out per process; require elevation; contact any daemon or network service.

---

## Registration and selection

`core/registry.py` selects at startup, in order:

1. Each backend's companion provider, where it declares one (NVIDIA/Linux → NVML).
2. The platform adapter provider (Windows → PDH; Linux → DRM fdinfo, future).
3. **No provider** — every device gets `attribution=UNSUPPORTED` with a reason, and the UI shows
   the FR-006 explanation instead of an empty list.

Case 3 is a supported, tested configuration, not a failure state. It is what NVIDIA-on-Windows
looks like before the PDH adapter lands, and the tool remains fully useful for device-level
metrics in it.

---

## Contract test suite

`tests/contract/test_attribution_protocol.py`, parametrized over all registered providers
including fakes.

| # | Assertion | Enforces |
|---|-----------|----------|
| A-01 | `probe()` never raises on any platform | FR-018 |
| A-02 | `per_device` has an entry for every device passed in | US2-4 |
| A-03 | Unidentifiable PIDs yield `UNRESOLVED` processes, never omission | **FR-031, SC-012** |
| A-04 | `total_attributed` includes unresolved and restricted processes | **SC-012** |
| A-05 | Inaccessible processes yield `RESTRICTED`, not exceptions | FR-009 |
| A-06 | A process exiting mid-call does not raise | D-05 |
| A-07 | Memory unavailable ⇒ `UNSUPPORTED`, never `0` | **SC-007** |
| A-08 | Identity is keyed on `(pid, started_at)`; a recycled PID is not misattributed | FR-008 |
| A-09 | No process is emitted for an unknown `device_key` | FR-007 |
| A-10 | `identify()` returns an entry for every requested key | — |
| A-11 | No provider requires elevation to return a usable result | FR-019, Principle V |
| A-12 | Container resolution reads only `/proc`; no socket or daemon access | Principle V, D-06 |
