# Scope and boundaries

What this project is not going to do — stated in advance, so nobody builds something that cannot
be accepted.

## Linux only

GPUM runs on Linux and makes no claim about Windows or macOS. Neither is supported, and neither
is planned. This was narrowed deliberately: the earlier three-platform ambition was never met,
which left the project's own capability record two-thirds filled with "deferred", and a governing
document that records an intention rather than a fact cannot be used to audit anything.

Partial code for an unclaimed platform will not be accepted either. A half-built adapter reads as
a promise.

What *did* survive that narrowing is the architecture rule: OS-specific code stays in
[platform adapters](../reference/adapters.md), and the same feature is never forked per platform.
That is not a portability claim — it is what keeps "no GPU", "no driver" and "no status area"
survivable rather than fatal.

## Honest about vendors

NVIDIA is implemented. AMD and Intel are registered and **not implemented**, and they say so in
the interface rather than presenting as forthcoming. A change that describes them as supported,
or as coming soon, will not be accepted; the [capability matrix](../capability-matrix.md) is the
record, and it is updated in the same change that alters support.

Implementing one of them properly is very welcome — [adding a vendor](../adding-a-vendor.md) is
the path, and it should require no change to `core/`, `ui/`, or any other backend.

## Read-only, always

GPUM observes. It will not terminate processes, change clocks, power limits, or fan curves.

That is not squeamishness: a monitoring tool is reached for during incidents, sees process names
and system topology, and earns trust by holding minimum privilege. It runs unelevated, never
prompts for credentials, and the only thing it writes is your own preferences.

Any mutation feature would need to be opt-in, individually confirmed against a named target, and
logged — and it would need a constitution amendment before the code, not after.

## Nothing leaves the machine

No telemetry, no usage data, no crash reporting, no network access of any kind. This site carries
no analytics either, and that is enforced by a test rather than a promise.

## No speculative abstraction

Complexity must be justified against the simpler alternative it replaces. An abstraction for an
anticipated second case is prohibited until the second case actually exists.

## Where the rules come from

- [The constitution](https://github.com/rs-r2d2/gpum/blob/main/.specify/memory/constitution.md) —
  the principles, and what each one is for
- [Design documents](https://github.com/rs-r2d2/gpum/blob/main/specs) — the specifications, plans,
  and contracts behind each feature
- [Capability matrix](../capability-matrix.md) — the auditable record of what actually works
