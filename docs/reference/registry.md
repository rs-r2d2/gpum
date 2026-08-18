# Backend registry

The registry is the one place that knows which backends exist. It is deliberately small: adding a
vendor should touch its own module and this file, and nothing else.

Source: [`src/gpum/registry.py`](https://github.com/rs-r2d2/gpum/blob/main/src/gpum/registry.py)

## Registering a backend

Each vendor gets a factory function and one entry in the factory table. That is the entire
registration surface — one function, one dict entry.

The factories are lazy on purpose: importing a vendor binding happens only if that backend is
actually built, so a machine without the binding installed pays nothing and fails nowhere.

## Selecting backends

| Selection | Result |
|---|---|
| default | Every registered backend is built; each reports its own availability |
| `nvidia` / `amd` / `intel` | Only that backend |
| `fake` | The simulated backend, optionally with a named scenario |
| `none` | No backend at all — the "nothing available" path |

This is what the [`--backend` option](cli.md) selects.

A backend that cannot operate is not an error: it reports why through `probe()`, and the
discovery panel shows the reader what was tried. Selecting a single backend narrows what is
built; it does not turn an unavailable backend into a failure.

## Attribution and identity providers

The registry also chooses where per-process data comes from, which is a separate decision from
which vendor backend is in use:

- a **companion provider** when the vendor's own library supplies attribution — NVIDIA's does;
- otherwise a **platform provider**, which is vendor-neutral and serves every vendor at once.

Process *identity* — turning PIDs into names and owners — is chosen separately again, because it
comes from the operating system rather than from any GPU driver.

That split is why [the backend interface](backend-interface.md) has no `get_processes()`: putting
it there would have forced platform-specific code inside a vendor module.

## Related

- [Adding a vendor](../adding-a-vendor.md) — the step that registers your backend
- [Platform adapters](adapters.md) — what a platform provider is
