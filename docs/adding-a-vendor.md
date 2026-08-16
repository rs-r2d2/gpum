# Adding a vendor backend

The path constitution Principle I is designed to keep short. Replacing the AMD or Intel stub
should require **no change to `core/`, `ui/`, or any other backend.** If it does, the
abstraction has failed and the interface — not the caller — needs revisiting.

## Steps

1. **Implement `GpuBackend`** in `src/gpum/backends/<vendor>/backend.py`, replacing the stub.
   The contract is `specs/001-gpu-usage-monitor/contracts/backend-interface.md`. The rules that
   matter most:
   - `probe()` **never raises** — a missing driver is expected, not exceptional.
   - Distinguish `LIBRARY_MISSING` / `DRIVER_MISSING` / `NO_DEVICES`; they produce different
     user-facing messages.
   - Device keys come from a stable UUID or PCI ID, **never** the enumeration index.
   - Memory in **bytes**. Never substitute `0` for an unobtainable value.

2. **Confine the vendor library.** Put every import of it in a single module (mirroring
   `backends/nvidia/nvml.py`) and add that path to the exemption in
   `tests/unit/test_import_boundaries.py`. Vendor types must not escape that file.

3. **Register it** in `src/gpum/registry.py` — one factory function and one dict entry.

4. **Add an attribution provider only if the vendor itself supplies attribution.** On Linux,
   AMD and Intel expose per-process data through DRM `fdinfo`, which is vendor-neutral and
   belongs in `adapters/linux/`, not in your backend. See
   `contracts/process-attribution.md`.

5. **Run `pytest tests/contract`.** The shared suite is parametrized over every registered
   backend, so your new one inherits ~13 contract tests with no test authoring.

6. **Update `docs/capability-matrix.md`** in the same change (Principle II).

## What not to do

- Don't add a method to `GpuBackend` for something only your vendor can do. Extend
  `BackendCapabilities` instead and let the UI adapt.
- Don't branch on the operating system inside a backend. That belongs in `adapters/`.
- Don't report a plausible-looking figure when the driver didn't give you one.
