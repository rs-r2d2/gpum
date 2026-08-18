# Reference

A guide to the interfaces that carry GPUM's design — the ones you need if you are adding a GPU
vendor, embedding part of GPUM, or trying to understand why the code is shaped the way it is.

**This reference is curated, not exhaustive.** It does not document every symbol; it documents
the contracts, the obligations they place on you, and the rules that are not negotiable. Every
entry links to its source, which is authoritative where this page is merely helpful.

Marked **PRINCIPLE**, a rule comes from the
[project constitution](https://github.com/rs-r2d2/gpum/blob/main/.specify/memory/constitution.md)
and cannot be waived in review. Every other rule is a convention: follow it unless you have a
reason.

## The pages

| Page | What it covers |
|---|---|
| [Backend interface](backend-interface.md) | What every vendor integration must implement |
| [Data model](data-model.md) | The normalized device and process types, and how absence is represented |
| [Backend registry](registry.md) | How backends are registered and selected |
| [Platform adapters](adapters.md) | Where OS-specific code is allowed to live |
| [Command line](cli.md) | Every option the application accepts |
| [Adding a vendor](../adding-a-vendor.md) | The step-by-step procedure, start to finish |

## How GPUM is layered

```text
backends/   one module per vendor; the only place a vendor SDK may be imported
   |
   v
core/       normalized model, sampling, aggregation, history, preferences
   |
   v
ui/         Qt widgets and the sampling worker

adapters/   OS-specific code: process identity, autostart, tray probing, sysfs
```

**PRINCIPLE — dependencies point one way only.** `core` must not import `ui`. `backends` must
import neither `core.engine` nor `ui`, and must not import `adapters`. Neither `core` nor `ui`
may import a vendor SDK or branch on vendor identity.

This is enforced mechanically by
[`tests/unit/test_import_boundaries.py`](https://github.com/rs-r2d2/gpum/blob/main/tests/unit/test_import_boundaries.py).
A failure there is a constitution violation, not a style nit: it means the vendor or platform
abstraction has been breached. Fix the import; never relax the test.

**PRINCIPLE — no invented data.** Nothing anywhere in this codebase may substitute `0`, `-1`, or
an estimate for a value it could not obtain. Absence is a state with a reason, and the type
system enforces it — see [the data model](data-model.md).

**PRINCIPLE — nothing blocks the interface.** Sampling, driver queries, subprocess calls, and
sysfs reads all happen off the Qt GUI thread, which performs no blocking I/O. A slow backend
times out and is reported as degraded rather than stalling anything.

## Two things worth knowing before you read further

**Qt stays in `ui`.** `core` and `backends` are importable and testable with no Qt application
instance and no display server. That is what lets the whole suite run headless.

**Vendor libraries are optional at install time.** A missing binding is treated exactly like a
missing driver: it disables one backend, reports itself, and changes nothing else.
