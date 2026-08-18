# Quickstart: Building and Validating the GPUM Site

**Feature**: `007-github-pages-site` | **Date**: 2026-08-18 | **Plan**: [plan.md](./plan.md)

How to build the site, preview it, and run every check that gates deployment — all locally, none
of it requiring a GPU, and most of it not requiring the network.

## Prerequisites

```bash
pip install -e ".[docs,dev]"
```

Python 3.11+. No GPU, no vendor driver, no Ruby, no Node for the offline checks.

## Build and preview

```bash
mkdocs serve                 # live preview at http://127.0.0.1:8000/gpum/
mkdocs build --strict        # one-shot build into site/; warnings are failures
```

The `on_pre_build` hook regenerates `docs/_snippets/release.md` before either command, so the
download page always shows a current release block. Working without network access:

```bash
GPUM_DOCS_OFFLINE=1 mkdocs serve
```

That takes the generator's fallback path — the same path CI takes when the releases API is
unreachable — so the fallback is exercised routinely rather than discovered in production.

## Run the checks

```bash
pytest tests/docs                  # drift suite: offline, no GPU, part of the default run
pytest                             # full suite; tests/docs is included
pytest tests/docs -m network       # external links and the live download URL
```

The drift suite reads the source of truth — the argument parser, the scenario table, the settings
dialog, the capability matrix — and fails when a page disagrees. See
[contracts/content-accuracy.md](./contracts/content-accuracy.md) for each assertion and the
requirement it discharges.

Third-party request check (needs built output):

```bash
mkdocs build --strict && pytest tests/docs/test_no_third_party.py
```

Skips with a stated reason if `site/` is absent; CI always builds first.

## Validation scenarios

Each scenario proves one user story from [spec.md](./spec.md) end to end. Run them against a local
preview or the deployed site.

### V-1 · A newcomer reaches a running window (User Story 1, P1)

1. Open `/` cold, at 1280 px and again at 360 px.
2. Confirm without scrolling past one screen: what GPUM is, the screenshot, the platform and
   hardware requirements, a visible download call to action.
3. Follow `/download/` step by step on a supported machine.

**Expected**: a running GPUM window, no question asked, no visit to the source repository. Each
step states its command and what success looks like; the executable-permission step states the
failure symptom that follows from skipping it. *(FR-009–FR-015, SC-001, SC-003)*

### V-2 · The download link is real, while every release is a pre-release (User Story 1)

```bash
python tools/gen_release_snippet.py && cat docs/_snippets/release.md
curl -sIL "$(grep -o 'https://[^ )]*\.AppImage' docs/_snippets/release.md | head -1)" | tail -2
```

**Expected**: a snippet naming the current release, and a download URL that resolves to a file —
not a 404 — even though the release is marked pre-release. *(FR-010, SC-005)*

Fallback path:

```bash
GPUM_DOCS_OFFLINE=1 python tools/gen_release_snippet.py && cat docs/_snippets/release.md
```

**Expected**: a block linking to the releases page and stating plainly that no bundle download is
currently available, pointing to the from-source route. No fabricated URL. Build still succeeds.

### V-3 · Every window element is documented (User Story 2, P2)

Open GPUM beside `/usage/`, `/usage/controls/`, and `/usage/processes/`.

**Expected**: every bar, graph, table column, control, and setting is described with what it
measures, its scale or units, and — for settings — its full choice list and default. The compute
activity entry states explicitly that 100% means the GPU was doing *something* throughout the
period, not that its cores were saturated. Unavailable values and trend-line gaps are explained as
represented absences, never as zero. *(FR-018–FR-020, SC-006)*

### V-4 · Demo mode is complete (User Story 2)

```bash
gpum --list-scenarios
```

**Expected**: every printed scenario appears on `/usage/demo-mode/` with the same description.
Eight today; adding a ninth without documenting it fails `pytest tests/docs`. *(FR-021, SC-006)*

### V-5 · Every CLI option is documented (User Story 2)

```bash
gpum --help
```

**Expected**: every option appears on `/reference/cli/` with its accepted values — including the
four the README does not currently cover (`--version`, `--hidden`, `--remove-desktop-entry`,
`-v/--verbose`) — plus the no-graphical-session message and its exit behavior. *(FR-015, SC-006)*

### V-6 · Troubleshooting is symptom-first (User Story 2)

For each of: permission denied · double-click does nothing · download 404 · nothing detected ·
distribution too old · per-process memory unavailable · no graphical session.

**Expected**: the reader finds the cause and the fix within one page, searching by what they saw
rather than by what caused it. *(FR-016, SC-007)*

### V-7 · A developer can extend from the reference alone (User Story 3, P3)

Give a developer only `/reference/`. Ask: what must a new vendor backend implement, how must it
report a value it cannot measure, and which dependencies are forbidden?

**Expected**: answers match `specs/001-gpu-usage-monitor/contracts/backend-interface.md` and
`docs/adding-a-vendor.md`, including that `probe()` never raises, that missing data is an explicit
unavailability with a reason rather than zero, and that `backends` may not import `core` or `ui`.
*(FR-024–FR-028, SC-008)*

### V-8 · A contributor gets a green suite (User Story 4, P4)

On a clean machine with no GPU, follow `/contributing/development/` only.

**Expected**: a working environment and a passing `pytest` in under 15 minutes; the reader can
state what would block their change, and that an import-boundary failure is a violated principle
to fix rather than a check to relax. *(FR-030–FR-032, SC-009)*

### V-9 · No support claim exceeds the matrix (constitution Principle II)

```bash
pytest tests/docs/test_support_claims.py
```

**Expected**: pass. No page claims Windows or macOS support; AMD and Intel are described as
registered and unimplemented rather than as forthcoming; stated Python and glibc versions match
`pyproject.toml` and `packaging/Dockerfile.build`. *(FR-033, FR-038, SC-011)*

### V-10 · The site phones home no more than the application does (Principle V)

```bash
mkdocs build --strict && pytest tests/docs/test_no_third_party.py
```

Then load any page with the browser's network panel open.

**Expected**: zero requests to any host but the site's own. In particular no font request — the
theme's default web-font fetch is disabled deliberately. Links *to* `github.com` are fine; they are
navigation the reader chooses. *(FR-006, FR-007, SC-012)*

### V-11 · Nothing breaks without JavaScript, or on a phone (FR-004, SC-013)

Disable JavaScript and reload; then view at 360 px width.

**Expected**: every page readable, full navigation usable, no horizontal scrolling of body text.
Search is the only degraded feature, and navigation covers its absence.

### V-12 · Publishing needs no manual step (User Story 5, P5)

Merge a change to a documented fact — the capability matrix is the clearest test.

**Expected**: the live site shows it within 10 minutes, with no action beyond the merge. Break the
build deliberately and confirm the previously published site stays live and the failure is red in
the Actions tab. *(FR-036, FR-037, SC-010)*

### V-13 · No fact lives in two editable places (FR-040, SC-015)

```bash
pytest tests/docs/test_readme_contract.py
```

**Expected**: README links to the site, its retained commands match `docs/download.md`, and the
long-form sections that moved have not crept back.

## What CI runs

Identical commands, in this order: `pytest tests/docs` → `mkdocs build --strict` →
`pytest tests/docs -m network` → accessibility audit → deploy. Deployment is gated on all of them;
see [contracts/publishing.md](./contracts/publishing.md).
