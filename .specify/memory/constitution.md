<!--
SYNC IMPACT REPORT
==================
Version change: none (unfilled template scaffold) → 1.0.0
Bump rationale: Initial ratification. All template placeholders replaced with concrete,
project-specific governance for the GPUM cross-vendor GPU monitor.

Modified principles:
  - [PRINCIPLE_1_NAME] → I. Vendor-Agnostic Abstraction (NON-NEGOTIABLE)
  - [PRINCIPLE_2_NAME] → II. Platform Parity by Capability, Not by Fork
  - [PRINCIPLE_3_NAME] → III. Non-Blocking Live Updates (NON-NEGOTIABLE)
  - [PRINCIPLE_4_NAME] → IV. Test-First on Simulated Hardware
  - [PRINCIPLE_5_NAME] → V. Read-Only by Default, Least Privilege

Added sections:
  - Technology & Architecture Constraints (was [SECTION_2_NAME])
  - Development Workflow & Quality Gates (was [SECTION_3_NAME])
  - Governance (populated)

Removed sections: none

Deferred TODOs: none
-->

# GPUM Constitution

GPUM is a platform-agnostic desktop tool that reports live GPU utilization and the processes
consuming GPU resources across NVIDIA, AMD, and Intel hardware.

## Core Principles

### I. Vendor-Agnostic Abstraction (NON-NEGOTIABLE)

Every vendor integration MUST sit behind a single, stable backend interface that returns a
normalized device and process model. Application, aggregation, and UI code MUST NOT import a
vendor SDK, shell out to a vendor tool, or branch on vendor identity; only backend
implementations may do so. Adding a new vendor MUST require no change outside its own backend
module and its registration.

Metrics differ in availability by vendor, driver, and platform. Backends MUST report each
metric as either a value or an explicit "unsupported/unavailable" state, and MUST NOT
substitute zero, a guess, or an interpolation for missing data. Per-process GPU attribution in
particular is unavailable on some vendor/OS combinations; the UI MUST render that absence
honestly rather than implying idle usage.

*Rationale: Vendor telemetry surfaces are unstable and unevenly capable. Isolating them is the
only way a three-vendor tool stays maintainable and truthful.*

### II. Platform Parity by Capability, Not by Fork

GPUM MUST run on Linux, Windows, and macOS from one codebase. OS-specific logic MUST be
confined to platform adapter modules; feature code MUST NOT contain OS conditionals. Forked
implementations of the same feature per platform are prohibited.

Where a platform cannot supply a capability, the capability MUST degrade visibly and be
recorded in a maintained capability matrix covering every supported vendor × platform pair.
The matrix MUST be updated in the same change that alters support. Absence of a GPU, of a
driver, or of any supported backend MUST leave the application running and usable, not crashed.

*Rationale: "Platform agnostic" is a promise about behavior, not a build target. A capability
matrix makes the promise auditable and prevents silent regressions on untested platforms.*

### III. Non-Blocking Live Updates (NON-NEGOTIABLE)

All GPU sampling, driver queries, subprocess calls, and file/sysfs reads MUST execute off the
Qt GUI thread. The GUI thread MUST NOT perform blocking I/O, and no single GUI-thread operation
may exceed 16 ms under a nominal device count. Cross-thread communication MUST use Qt signals
or an equivalent thread-safe channel.

Sampling MUST run on a user-configurable interval with a documented default, and a slow or hung
backend MUST time out and be reported as degraded rather than stalling the sampling loop or the
UI. Retained history MUST be bounded so that memory does not grow with uptime. Sampling MUST
stop or throttle when its output is not visible.

*Rationale: A monitor that freezes is worse than no monitor. Live updating is the product, so
UI responsiveness and sampler isolation are correctness requirements, not polish.*

### IV. Test-First on Simulated Hardware

Tests MUST be written and MUST fail before implementation. Every backend MUST have a fake or
recorded-fixture implementation, and the full test suite MUST pass on machines with no GPU and
no vendor drivers installed. A test that can only run on specific hardware MUST be marked as
such and MUST NOT gate the default suite.

Each backend MUST pass a shared contract test suite proving it satisfies the common interface,
including its behavior for unavailable metrics, absent devices, permission denial, and query
timeouts. Every fixed defect MUST gain a regression test reproducing it.

*Rationale: The hardware matrix cannot be present in CI or on most contributor machines.
Simulated backends and a shared contract suite are what make the abstraction verifiable.*

### V. Read-Only by Default, Least Privilege

GPUM MUST function as a read-only observer in its default configuration and MUST NOT require
root or administrator privileges to run. Where elevation would unlock additional metrics, the
tool MUST run unelevated with reduced capability and MUST NOT prompt for or retain elevated
credentials on its own.

Any operation that mutates system or process state — terminating a process, altering clocks,
power limits, or fan curves — MUST be opt-in, MUST require explicit per-action user
confirmation identifying the exact target, and MUST be logged. GPUM MUST NOT transmit
telemetry, usage data, process names, or system information off the machine. All data
collection MUST stay local.

*Rationale: A monitoring tool sees process names and system topology and is often reached for
during incidents. It earns trust by holding minimum privilege and keeping what it sees local.*

## Technology & Architecture Constraints

- **Language**: Python. The minimum supported Python version MUST be declared in project
  metadata and enforced in CI.
- **UI framework**: Qt for Python (PySide6). Qt widgets/QML MUST NOT appear outside the UI
  layer, and the core sampling and aggregation layers MUST be importable and testable without
  a Qt application instance or a display server.
- **Layering**: `backends` (vendor-specific) → `core` (normalized model, sampling, aggregation)
  → `ui` (Qt). Dependencies MUST point in one direction only; `core` MUST NOT import `ui`, and
  `backends` MUST NOT import `core` or `ui`.
- **Dependencies**: Vendor SDKs, bindings, and CLI tools MUST be optional at install time and
  resolved at runtime. Installing GPUM MUST NOT require any vendor driver or SDK to be present.
  A missing optional dependency disables one backend and nothing else.
- **Licensing**: Third-party dependencies MUST be license-compatible with the project's chosen
  distribution license; copyleft-incompatible additions MUST be rejected in review.
- **Distribution**: The application MUST be installable and launchable on all three supported
  platforms without a compiler toolchain on the user's machine.

## Development Workflow & Quality Gates

- Every change MUST pass automated linting, type checking, and the full test suite before
  merge; these gates MUST run in CI on Linux, Windows, and macOS.
- Every pull request MUST state which principles it touches and MUST justify any deviation in
  the change description. Unjustified deviations MUST block merge.
- Changes to the backend interface MUST update every backend and the shared contract tests in
  the same change. Interface drift across backends MUST NOT be merged.
- Changes affecting vendor or platform support MUST update the capability matrix in the same
  change.
- Changes to the sampling loop, threading model, or UI update path MUST include evidence that
  the GUI thread remains non-blocking under load.
- Complexity MUST be justified against the simpler alternative that was rejected. Speculative
  abstraction for anticipated vendors or features is prohibited until a second concrete case
  exists.

## Governance

This constitution supersedes all other development practices, conventions, and preferences for
this project. Where a tool default, a style guide, or an agent instruction conflicts with a
principle here, this document wins.

**Amendment procedure**: Amendments MUST be proposed as a written change to this file stating
the motivation, the affected principles, the version bump and its rationale, and a migration
plan for any code or process already relying on the superseded rule. An amendment takes effect
when merged; the merged change MUST carry the updated version line and Sync Impact Report.

**Versioning policy**: This constitution is versioned as MAJOR.MINOR.PATCH.
- MAJOR: a principle is removed or redefined in a backward-incompatible way, or governance
  changes in a way that invalidates prior compliance.
- MINOR: a principle or section is added, or existing guidance is materially expanded.
- PATCH: clarifications, rewording, and typo fixes that do not change obligations.

**Compliance review**: Every pull request review MUST verify compliance with these principles;
the reviewer, not the author, is accountable for that verification. Principles marked
NON-NEGOTIABLE admit no exception and MUST NOT be waived in review — a change that cannot
satisfy them requires an amendment first. All other deviations MUST be recorded in the change
description with their justification. The constitution MUST be reviewed for accuracy whenever
a new vendor or platform is added.

**Version**: 1.0.0 | **Ratified**: 2026-08-16 | **Last Amended**: 2026-08-16
