# Implementation Plan: GPUM Project Website (GitHub Pages)

**Branch**: `007-github-pages-site` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-github-pages-site/spec.md`

## Summary

Publish a public documentation site for GPUM at `https://rs-r2d2.github.io/gpum/` covering four
audiences in priority order: a newcomer who needs a working window (P1), a user learning to read
it (P2), a developer who needs the interfaces that carry the design (P3), and a contributor who
needs the rules a change must satisfy (P4).

The approach is deliberately small. The existing `docs/` directory becomes the site source, so the
capability matrix, the vendor-addition guide, the build guide, and the licensing notes become site
pages without being copied. New Markdown pages are added alongside them for download, usage, the
curated API reference, and contribution guidelines. MkDocs with the Material theme renders it;
GitHub Actions builds and deploys it on merge and on release publication.

Two mechanisms carry the weight. First, the download link is generated at build time from the
releases API rather than hardcoded, because every release this project has published is a
pre-release and the conventional "latest release" link returns 404 for exactly that reason.
Second, a set of drift tests in the default `pytest` suite reads the source of truth — the argument
parser, the scenario table, the settings dialog, the capability matrix — and fails when a page
disagrees with it. The failure this feature must survive is not a broken build; it is a page that
renders perfectly while saying something that stopped being true.

## Technical Context

**Language/Version**: Python 3.11+ (build hook, release-snippet generator, drift tests). Site
content is Markdown; no application code changes.

**Primary Dependencies**: MkDocs ≥1.6 and Material for MkDocs ≥9.5, in a new `docs` optional
dependency group. `pymdownx.snippets` (ships with Material) embeds the generated release block.
No new runtime dependency; no new dependency in `dev`.

**Storage**: None. Static files only, no server component, no database, no visitor state.

**Testing**: `pytest` — `tests/docs/` in the default suite (offline, no GPU); a new `network`
marker for external link reachability, deselected by default like `hardware` and `packaging`;
an automated accessibility audit against the built site in CI.

**Target Platform**: Static pages served by GitHub Pages. Readers on any modern browser, desktop
and small screen, with core content and navigation intact when scripting is unavailable.

**Project Type**: Documentation site inside an existing single-project desktop application repo.

**Performance Goals**: Landing page usable on first paint with no blocking third-party request
(there are none); page weight dominated by the one screenshot; full site build under 30 s so a
contributor's `mkdocs serve` loop stays tight.

**Constraints**: Zero third-party network requests from any published page (constitution
Principle V, extended to the site). Core content readable without JavaScript. WCAG AA contrast in
both light and dark. No fact editable in two places. Download link must resolve to a real asset
while all releases are pre-releases.

**Scale/Scope**: ~20 pages across five sections; four existing documents adopted unchanged; one
new CI workflow; one generator script; one test package; a trimmed README.

## Constitution Check

*GATE: evaluated before Phase 0 and re-evaluated after Phase 1 design. Constitution 2.0.0.*

| Principle | Applies? | Assessment |
|---|---|---|
| **I. Vendor-Agnostic Abstraction** | As a documentation obligation | PASS. The API reference presents the backend interface as the single extension point and documents unavailability as a first-class state (FR-025). It links to `specs/001-gpu-usage-monitor/contracts/backend-interface.md` and `docs/adding-a-vendor.md` rather than paraphrasing them, so the contract cannot drift from its documentation. No site page suggests a vendor-specific escape hatch. |
| **II. Single Target, Adapters Kept Honest** | Yes — directly | PASS, enforced. `docs/capability-matrix.md` *is* the site's support page rather than a source for one, so a change that amends the matrix amends the site in the same commit, as the principle requires. A drift test scans every page for support claims about Windows or macOS and for vendor claims exceeding the matrix, failing the default test suite if either appears (FR-033, FR-038). AMD and Intel are documented as registered but unimplemented. |
| **III. Non-Blocking Live Updates** | No | N/A. This feature adds no sampling, no threading, and no Qt code. Nothing in it executes inside the running application; `src/gpum/` is not modified. |
| **IV. Test-First on Simulated Hardware** | Yes | PASS. `tests/docs/` is written before the pages it validates and must fail first. The suite is offline and hardware-free, so it runs in the default `pytest` invocation on a machine with no GPU. Everything requiring the network sits behind the new `network` marker, following the existing `hardware`/`packaging` precedent. |
| **V. Read-Only, Least Privilege, No Telemetry** | Yes — directly | PASS, enforced. No analytics, no tracking, no advertising, no forms, no accounts (FR-006, FR-007). Material's default Google Fonts fetch is disabled explicitly and asserted by a test that scans built HTML for third-party hosts — the promise "it never phones home" would be hollow if the project's own website did. The deploy job holds `contents: read`, `pages: write`, `id-token: write` and nothing more; the branch-pushing deploy that would need `contents: write` was rejected on this ground. |

**Technology and architecture constraints**:

- Python-only tooling; no second language runtime introduced for contributors (research D-01).
- Docs dependencies are an optional `docs` extra: installing GPUM, or installing `dev` to run
  tests, pulls in none of them (research D-09).
- Layering is untouched — no file under `src/gpum/` changes. `backends → core → ui` is unaffected.
- Licensing: MkDocs (BSD-2) and Material (MIT) are compatible with the project's MIT license and
  are build-time only, never distributed with the application. `docs/licenses.md` gains a note
  recording that distinction.

**Workflow and quality gates**:

- Capability-matrix obligation satisfied structurally rather than procedurally (Principle II).
- Existing CI gates unchanged; docs checks join the default `pytest` run, so no change can pass CI
  while leaving a page contradicting the code.
- The one deliberate deletion in this feature — trimming README's long-form sections — is a
  deduplication required by FR-040, with the content relocated, not discarded (research D-07).

**Result**: PASS, no violations, before Phase 0 and again after Phase 1. Complexity Tracking is
therefore empty; the justification for each added mechanism against its simpler alternative is
recorded in [research.md](./research.md) as the workflow gates require.

## Project Structure

### Documentation (this feature)

```text
specs/007-github-pages-site/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output — D-01..D-11
├── data-model.md        # Phase 1 output — content model and validation rules
├── quickstart.md        # Phase 1 output — build, preview, and validate
├── contracts/
│   ├── site-structure.md      # Page inventory, URLs, required content, navigation
│   ├── content-accuracy.md    # Source-of-truth map and the assertions that police it
│   └── publishing.md          # Build/deploy triggers, permissions, failure semantics
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
mkdocs.yml                       # NEW — site config, nav, theme, no third-party assets

docs/                            # becomes the MkDocs docs_dir; existing files stay put
├── index.md                     # NEW — landing: what it is, screenshot, requirements, download
├── download.md                  # NEW — bundle route, from-source route, requirements, verify
├── usage/
│   ├── index.md                 # NEW — reading the window: bars, trend graphs
│   ├── controls.md              # NEW — toolbar controls and every setting with defaults
│   ├── processes.md             # NEW — the process table, sorting, unavailable values
│   ├── demo-mode.md             # NEW — simulated hardware, all eight scenarios
│   └── troubleshooting.md       # NEW — organized by observed symptom
├── reference/
│   ├── index.md                 # NEW — scope note: curated, not exhaustive
│   ├── backend-interface.md     # NEW — GpuBackend: operations, obligations, failure states
│   ├── data-model.md            # NEW — MetricValue, GpuDevice, GpuProcess, Availability
│   ├── registry.md              # NEW — registration and backend selection
│   ├── adapters.md              # NEW — platform adapter boundary and dependency direction
│   └── cli.md                   # NEW — every command-line option and exit behavior
├── contributing/
│   ├── index.md                 # NEW — reporting problems; contributing at a glance
│   ├── development.md           # NEW — environment setup, running the suite with no GPU
│   ├── quality-gates.md         # NEW — gates, what a boundary-test failure means
│   └── scope.md                 # NEW — what the project will not accept, and why
├── capability-matrix.md         # EXISTING — unchanged, becomes the support page
├── adding-a-vendor.md           # EXISTING — unchanged, linked from reference/
├── building.md                  # EXISTING — unchanged, linked from contributing/
├── licenses.md                  # EXISTING — note added for build-time docs tooling
├── _snippets/
│   └── release.md               # GENERATED, gitignored — version, asset URL, commands
└── media/
    └── gpum-screenshot.png      # EXISTING

tools/
├── gen_release_snippet.py       # NEW — releases API → _snippets/release.md, offline fallback
└── mkdocs_hooks.py              # NEW — on_pre_build hook; no build proceeds without the snippet

tests/docs/                      # NEW — offline drift suite, default pytest run
├── __init__.py
├── test_cli_documented.py       # every argparse option appears in reference/cli.md
├── test_settings_documented.py  # intervals, history choices, Preferences defaults
├── test_scenarios_documented.py # every SCENARIOS key with its description
├── test_support_claims.py       # no Windows/macOS claim; vendors within the matrix
├── test_links_and_media.py      # internal links/anchors resolve; alt text present
├── test_readme_contract.py      # README links to the site; retained commands agree
└── test_no_third_party.py       # built HTML issues no third-party request

.github/workflows/docs.yml       # NEW — build, check, audit, deploy
pyproject.toml                   # docs extra; network marker
README.md                        # trimmed to a front door, links into the site
.gitignore                       # docs/_snippets/, site/
```

**Structure Decision**: Single project, documentation-only addition. The site source is the
existing `docs/` directory rather than a new top-level tree — the decisive reason (research D-03)
is that it makes the capability matrix and the vendor guide *be* site pages instead of having
copies of them, which is what satisfies FR-038 and FR-040 with no synchronization machinery. New
tooling lives in the existing `tools/` directory and new tests in `tests/docs/`, alongside the
conventions already in use. Nothing under `src/gpum/` is touched.

## Phase 1 Design Artifacts

| Artifact | What it fixes |
|---|---|
| [data-model.md](./data-model.md) | The content model — page, section, release metadata, documented-element entries — and the validation rules each drift test enforces. |
| [contracts/site-structure.md](./contracts/site-structure.md) | Page inventory with URLs, required content per page, navigation rules, and traceability to the spec's functional requirements. |
| [contracts/content-accuracy.md](./contracts/content-accuracy.md) | Which fact is owned by which source, and the exact assertion that catches a page disagreeing with it. |
| [contracts/publishing.md](./contracts/publishing.md) | Build and deploy triggers, token permissions, the release-snippet generator's input/output contract, and failure and rollback semantics. |
| [quickstart.md](./quickstart.md) | How to build, preview, and validate the site locally and in CI, including how to exercise the offline fallback and verify zero third-party requests. |

## Complexity Tracking

No constitution violations; this section is intentionally empty. Each added mechanism — the CI
workflow, the release-snippet generator, the drift suite, the accessibility audit — is justified
against the simpler alternative it replaces in [research.md](./research.md) (D-04, D-05, D-06,
D-11), as the workflow gates require.
