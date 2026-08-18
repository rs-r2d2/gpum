# Contract: Site Structure

**Feature**: `007-github-pages-site` | **Date**: 2026-08-18

The site's interface to its readers is its information architecture: which pages exist, at which
addresses, containing what. This contract fixes that. A page may be rewritten freely; it may not
quietly stop containing what the table says it contains, and its URL may not change without a
redirect, because published links are a promise.

## Global rules

| Rule | Requirement |
|---|---|
| Navigation on every page | Every page shows the project name and the five top-level sections; a visitor landing on any deep page can reach any other section (FR-003) |
| No scripting required | All content and all navigation work with JavaScript unavailable; search is the only scripted feature and its absence degrades to navigation (FR-004) |
| Small screens | Every page is readable and navigable at 360 px width, with no horizontal scrolling of body text (FR-004, SC-013) |
| Theme | Light and dark presentations, both meeting AA contrast; the reader's system preference is honored (FR-005) |
| Third-party requests | Zero. No fonts, no analytics, no CDN, no embeds (FR-006, SC-012) |
| Personal data | No forms, no accounts, no comments, no visitor data collected (FR-007) |
| Licensing | Every page footer links to the project license (FR-008) |
| URL stability | A published URL either keeps working or gains a redirect; this table is the record of what has been published |

## Page inventory

### Overview

| URL | Source | Must contain | Requirements |
|---|---|---|---|
| `/` | `docs/index.md` | What GPUM is, in one screen: purpose, the real screenshot with descriptive alt text, the supported platform and hardware requirements, the four behavioral promises, and a visible download call to action reachable without scrolling past one screen or following a link first | FR-009, FR-013, FR-022, FR-023, SC-003 |

### Download

| URL | Source | Must contain | Requirements |
|---|---|---|---|
| `/download/` | `docs/download.md` | System requirements *above* the instructions; the bundle route as ordered steps, each with its exact command, expected successful outcome, and — for the executable-permission step — the failure symptom that results from skipping it and why the step exists; the from-source route as clone-then-install, with its own prerequisites; the embedded generated release block; why vendor driver libraries are not bundled; how to launch and how to add to the application menu | FR-009–FR-015 |

The generated block (`docs/_snippets/release.md`) is embedded here and on `/`. No page hardcodes a
version (FR-017).

### Usage

| URL | Source | Must contain | Requirements |
|---|---|---|---|
| `/usage/` | `docs/usage/index.md` | Every per-device element in the order the window presents it — three bars, two trend graphs — each with what it measures and its scale or units; what compute activity at 100% does *not* mean; how gaps, unavailable values, and degraded devices are represented and why never as zero | FR-018, FR-020, SC-006 |
| `/usage/controls/` | `docs/usage/controls.md` | Every toolbar control, and every setting with its full choice list and default | FR-019, SC-006 |
| `/usage/processes/` | `docs/usage/processes.md` | The process table: all four sortable columns, the sort behavior, and why unmeasurable values rank last in both directions instead of sorting as zero | FR-018, FR-020 |
| `/usage/demo-mode/` | `docs/usage/demo-mode.md` | How to start simulated hardware, and all eight scenarios with what each demonstrates | FR-021, SC-006 |
| `/usage/troubleshooting/` | `docs/usage/troubleshooting.md` | Entries organized by the symptom the reader observes, covering at minimum: permission denied, double-click does nothing, download 404, nothing detected, distribution too old, per-process memory unavailable, no graphical session | FR-016, SC-007 |

### Reference

| URL | Source | Must contain | Requirements |
|---|---|---|---|
| `/reference/` | `docs/reference/index.md` | The scope statement — curated interfaces that matter to an extender or integrator, explicitly not exhaustive symbol coverage — and the dependency direction between layers, marking which rules are constitution principles | FR-026, FR-029 |
| `/reference/backend-interface/` | `docs/reference/backend-interface.md` | Every operation an implementation must provide, what each returns, which must never raise, and how unavailability and failure are expressed; links to `specs/001-gpu-usage-monitor/contracts/backend-interface.md` | FR-024, FR-025, FR-028 |
| `/reference/data-model/` | `docs/reference/data-model.md` | The normalized device and process model, and the representation of an unavailable metric with its reason — including that substituting zero or an estimate is prohibited | FR-024, FR-025 |
| `/reference/registry/` | `docs/reference/registry.md` | How a backend is registered and selected, and what `--backend` does to that selection | FR-024 |
| `/reference/adapters/` | `docs/reference/adapters.md` | The platform adapter boundary: what belongs there, what must never appear in a backend or in feature code, and the consequence of breaching it | FR-024, FR-026 |
| `/reference/cli/` | `docs/reference/cli.md` | Every command-line option with its accepted values and effect, plus exit behavior including the no-graphical-session message | FR-015, SC-006 |
| `/reference/adding-a-vendor/` | `docs/adding-a-vendor.md` *(existing, adopted)* | The step-by-step account of adding vendor support: every file to add or change, and what must *not* need changing | FR-027 |

### Contributing

| URL | Source | Must contain | Requirements |
|---|---|---|---|
| `/contributing/` | `docs/contributing/index.md` | How to report a problem or ask a question, and what a useful report contains — reachable without reading development setup first | FR-034 |
| `/contributing/development/` | `docs/contributing/development.md` | Environment setup, and running the full check suite, stating that it passes on a machine with no GPU present | FR-030 |
| `/contributing/quality-gates/` | `docs/contributing/quality-gates.md` | Every gate a change must pass; which documentation must be updated alongside which kind of change; that an import-boundary failure is a violated principle to fix, never a check to relax | FR-031, FR-032 |
| `/contributing/scope/` | `docs/contributing/scope.md` | Scope boundaries stated concretely enough to predict rejection: Linux only, unimplemented vendors described honestly rather than promised, no speculative abstraction; links to the constitution and the design documents | FR-033, FR-035 |
| `/contributing/building/` | `docs/building.md` *(existing, adopted)* | Bundle build procedure and why it must happen in the pinned container | FR-030 |

### Project

| URL | Source | Must contain | Requirements |
|---|---|---|---|
| `/capability-matrix/` | `docs/capability-matrix.md` *(existing, adopted)* | The maintained record of what works where — the site's single source for every support claim | FR-038, SC-011 |
| `/licenses/` | `docs/licenses.md` *(existing, adopted)* | Licensing of the project and its distributed dependencies, plus a note that the documentation toolchain is build-time only and not distributed | FR-008 |

## Navigation order

Acquisition before instruction, instruction before extension:

```text
Overview  ·  Download  ·  Usage  ·  Reference  ·  Contributing
                                                   └ Capability matrix, Licenses reachable from
                                                     Overview and Contributing
```

## Adopted-document rule

`capability-matrix.md`, `adding-a-vendor.md`, `building.md`, and `licenses.md` are *adopted*, not
copied. They keep their current paths and content. They may be edited when their own subject
changes; they may not be edited to suit site layout, and no page may restate their content instead
of linking to them. This is what makes a Principle II matrix update reach the site automatically.

## Verification

Structure is verified by `tests/docs/`, not by review: page existence and nav membership, heading
structure, internal link and anchor resolution, alt text presence, and absence of third-party
hosts in built output. See [content-accuracy.md](./content-accuracy.md) for content assertions.
