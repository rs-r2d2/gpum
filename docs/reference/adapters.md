# Platform adapters

Adapters are where operating-system-specific code lives. Nowhere else.

Source: [`src/gpum/adapters/base.py`](https://github.com/rs-r2d2/gpum/blob/main/src/gpum/adapters/base.py)

## The rule

**PRINCIPLE — OS-specific logic is confined to adapter modules.** Feature code contains no
operating-system conditionals, and the same feature is never forked per platform.

GPUM supports Linux and makes no claim about anything else, so it is worth being clear about why
this rule survives that narrowing. It is not a portability promise. It is what keeps the
degradation guarantee reachable — "no GPU", "no driver", "no status area" are all survivable
states rather than crashes — and it is what would make adding a platform later an additive change
rather than a rewrite.

## The two protocols

### `ProcessAttributionProvider`

Which processes are using which GPU.

- `probe()` — **never raises**, and reflects both the running platform *and* the current
  privilege level, since attribution is frequently a permissions question rather than a
  capability one.
- `attribute(devices)` — returns attribution for the given devices, reporting unavailability
  explicitly rather than returning an empty list that would read as "no processes".

This lives outside [the backend interface](backend-interface.md) because its source is not always
the vendor. On Linux, AMD and Intel expose per-process data through DRM `fdinfo`, which is
vendor-neutral: one implementation serves every vendor at once, and it belongs in `adapters/`
rather than in any backend.

### `ProcessIdentityProvider`

Given PIDs, what are they? A **batch** lookup — one call for many PIDs, not one call each,
because per-PID lookups on a busy machine are exactly the kind of work that would make the
sampling loop slow.

## What else lives here

Autostart entries, desktop entries, tray-availability probing, PCI device enumeration, container
detection, and process identity. All of it Linux-specific, all of it behind an interface, and all
of it with a null implementation so that a missing capability degrades instead of crashing.

## Rules

- A backend must never contain an OS conditional. If you need one, you need an adapter.
- An adapter must never import `ui`.
- A capability that cannot be supplied degrades visibly and is recorded in the
  [capability matrix](../capability-matrix.md), in the same change that alters it.
- The boundary is enforced by
  [`tests/unit/test_import_boundaries.py`](https://github.com/rs-r2d2/gpum/blob/main/tests/unit/test_import_boundaries.py).

## Related

- [Backend registry](registry.md) — how a provider is chosen at runtime
- [Data model](data-model.md) — the types attribution produces
