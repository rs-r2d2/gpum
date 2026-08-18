---

description: "Task list for the GPUM project website (GitHub Pages)"
---

# Tasks: GPUM Project Website (GitHub Pages)

**Input**: Design documents from `/specs/007-github-pages-site/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: Included and mandatory. Constitution Principle IV requires tests written before the
thing they validate, and the accuracy contract's assertions A-01…A-13 are this feature's tests:
they read the source of truth and fail when a page disagrees with it. Every test task below must
fail before its implementation tasks begin.

**Organization**: Tasks are grouped by user story so each can be implemented, tested, and shipped
independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task serves (US1…US5)
- Exact file paths are given in every task

## Path Conventions

Single project. Site source is the existing `docs/` directory (research D-03); tooling in
`tools/`; tests in `tests/docs/`. Nothing under `src/gpum/` is modified by this feature.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Configure the toolchain so the four already-existing documents build as a site.

- [X] T001 Create `mkdocs.yml` at repository root: `site_name: GPUM`, `site_url: https://rs-r2d2.github.io/gpum/`, `docs_dir: docs`, Material theme with `font: false` (research D-02 — the default fetches Google Fonts from the visitor's browser), light/dark palettes honoring the system preference, `markdown_extensions` including `pymdownx.snippets` with `base_path: docs`, and a nav listing only the adopted pages (`capability-matrix.md`, `adding-a-vendor.md`, `building.md`, `licenses.md`)
- [X] T002 [P] Add the `docs` optional-dependency group (`mkdocs>=1.6`, `mkdocs-material>=9.5`) to `pyproject.toml` under `[project.optional-dependencies]`, deliberately not in `dev` or runtime (research D-09), and register the `network` marker under `[tool.pytest.ini_options]` markers alongside `hardware` and `packaging`
- [X] T003 [P] Add `docs/_snippets/` and `site/` to `.gitignore`
- [X] T004 [P] Add a short note to `docs/licenses.md` recording that MkDocs (BSD-2) and Material for MkDocs (MIT) are build-time documentation tooling, compatible with the project's MIT license and never distributed with the application
- [X] T005 Run `pip install -e ".[docs,dev]"` then `mkdocs build --strict` and confirm the four adopted pages render with no warnings; this is the first green build and the baseline every later task builds on

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared test infrastructure, a page skeleton that lets any page be reachable, and the
minimum publishing pipeline. Deploy capability is foundational rather than deferred to US5: a
website that is not published delivers no user value, so without it even the MVP cannot be tested
by a real visitor. US5 later adds the accuracy enforcement and robustness on top of this pipeline.

**⚠️ CRITICAL**: No user story work begins until this phase is complete.

- [X] T006 Create `tests/docs/__init__.py` and `tests/docs/conftest.py` with shared helpers used by every later test: discover all Markdown pages under `docs/`, parse links (relative, repository, external), parse images with alt text, parse heading levels, and load `mkdocs.yml` nav — offline, no GPU, no network
- [X] T007 Write `tests/docs/test_links_and_media.py` implementing assertions A-06, A-07 and A-08 from [contracts/content-accuracy.md](./contracts/content-accuracy.md): internal links and anchors resolve, repository-path links exist in the working tree, every image has non-empty alt text and an existing file, exactly one top-level heading per page with no skipped levels. Confirm it passes against the adopted pages and would fail on a broken link
- [X] T008 Create a minimal `docs/index.md` (title, one-sentence description, links to the adopted pages) so the site has a homepage and every page is reachable from nav; US1 replaces its body with the real landing content
- [X] T009 Create `.github/workflows/docs.yml` per [contracts/publishing.md](./contracts/publishing.md) with a `build` job (checkout, Python 3.12, `pip install -e ".[docs,dev]"`, `pytest tests/docs`, `mkdocs build --strict`, `actions/upload-pages-artifact`) and a `deploy` job (`needs: build`, `actions/deploy-pages`, permissions exactly `contents: read` / `pages: write` / `id-token: write`, skipped on pull requests); triggers limited to `push` on `main` and `workflow_dispatch` for now
- [X] T010 One-time manual step: set repository Settings → Pages → Source to **GitHub Actions**, as recorded in [contracts/publishing.md](./contracts/publishing.md); no branch protection or token changes are needed — **done by the maintainer, 2026-08-18**
- [ ] T011 Merge to `main` and confirm the site is live at `https://rs-r2d2.github.io/gpum/` with the adopted pages reachable — **BLOCKED — needs the branch merged and pushed**

**Checkpoint**: A real, published site exists. User story work can now begin, in parallel if staffed.

---

## Phase 3: User Story 1 - A newcomer downloads GPUM and gets it running (Priority: P1) 🎯 MVP

**Goal**: A visitor who has never heard of GPUM can land on the site, confirm their machine is
supported, and reach a running window — with a download link that resolves to a real file even
though every published release is a pre-release.

**Independent Test**: Give a person only the site URL on a supported Linux machine with an NVIDIA
driver; they reach a running GPUM window without asking a question or opening the repository
(quickstart V-1, V-2).

### Tests for User Story 1 ⚠️ Write first, confirm failing

- [X] T012 [P] [US1] Write `tests/docs/test_release_snippet.py` covering the generator contract in [contracts/publishing.md](./contracts/publishing.md) against recorded API fixtures in `tests/fixtures/releases/` (no network, per Principle IV): the newest non-draft release carrying an `.AppImage` asset is selected **including when it is a pre-release**; drafts are never selected; the emitted URL is byte-identical to the asset URL in the response and is never constructed from a pattern; with no eligible release, or with `GPUM_DOCS_OFFLINE=1`, the fallback block links to the releases page, states no bundle is available, and emits no download URL
- [X] T013 [P] [US1] Write `tests/docs/test_support_claims.py` implementing assertions A-04 and A-05: no page claims Windows or macOS support (explicit non-support statements permitted), no page describes AMD or Intel as supported or forthcoming beyond what `docs/capability-matrix.md` records, the Python version stated on the download page matches `requires-python` in `pyproject.toml`, and the glibc baseline stated there matches the base image pinned in `packaging/Dockerfile.build`

### Implementation for User Story 1

- [X] T014 [US1] Implement `tools/gen_release_snippet.py`: request `GET https://api.github.com/repos/rs-r2d2/gpum/releases` (using `GITHUB_TOKEN` only for rate limits when present), apply the selection rule, and write `docs/_snippets/release.md` with the version, asset name, download command, `chmod +x` step, and run command; take the fallback path on unreachable API, rate limiting, `GPUM_DOCS_OFFLINE=1`, or no eligible asset
- [X] T015 [US1] Implement `tools/mkdocs_hooks.py` with an `on_pre_build` hook invoking the generator, and register it via `hooks:` in `mkdocs.yml`, so neither `mkdocs serve` nor `mkdocs build` can proceed with a missing or stale release block
- [X] T016 [US1] Write `docs/download.md` per [contracts/site-structure.md](./contracts/site-structure.md): system requirements **above** the instructions; the bundle route as ordered steps each stating its command and expected outcome, with the `chmod +x` step explaining the `Permission denied` symptom and why the step exists; the from-source route as `git clone` then `pip install -e ".[nvidia]"` (research D-08 — today's README presupposes a clone it never mentions, and there is no PyPI package); the embedded `--8<-- "_snippets/release.md"` block; why vendor driver libraries are not bundled; launching and `--install-desktop-entry`
- [X] T017 [US1] Replace the body of `docs/index.md` with the landing content: what GPUM is, `docs/media/gpum-screenshot.png` with alt text describing what the capture shows, platform and hardware requirements, the four behavioral promises (no invented numbers, never freezes, changes nothing, never phones home), and a download call to action visible without scrolling past one screen
- [X] T018 [US1] Add Overview and Download to the `mkdocs.yml` nav in the order fixed by [contracts/site-structure.md](./contracts/site-structure.md), and link the capability matrix from the landing page's requirements section
- [ ] T019 [US1] Run quickstart scenarios V-1 and V-2 from [quickstart.md](./quickstart.md), including the `GPUM_DOCS_OFFLINE=1` fallback path, and confirm the generated download URL resolves to a file rather than a 404 — **PARTIAL — V-2 verified against the live releases API; V-1 needs a first-time tester on NVIDIA hardware**

**Checkpoint**: The MVP is live. A stranger can download and run GPUM from the site alone.

---

## Phase 4: User Story 2 - An existing user learns to read and configure the window (Priority: P2)

**Goal**: Every element of the running window — bars, graphs, process table, controls, settings,
demo mode — is documented with what it measures, its scale, its choices, and its defaults, and the
metrics people misread are corrected explicitly.

**Independent Test**: A user with GPUM open explains every bar, graph, and column from the usage
pages alone, and their answers match the application's behavior (quickstart V-3…V-6).

### Tests for User Story 2 ⚠️ Write first, confirm failing

- [X] T020 [P] [US2] Write `tests/docs/test_cli_documented.py` (assertion A-01): build the parser from `src/gpum/__main__.py`, and assert every option string and every `choices` value appears in `docs/reference/cli.md` — this is what catches a renamed flag leaving a stale page
- [X] T021 [P] [US2] Write `tests/docs/test_scenarios_documented.py` (assertion A-02): assert every key of `src/gpum/backends/fake/scenarios.SCENARIOS` and each scenario's `description` text appears in `docs/usage/demo-mode.md`, so the page cannot drift from what `--list-scenarios` prints
- [X] T022 [P] [US2] Write `tests/docs/test_settings_documented.py` (assertion A-03): assert every label in `_INTERVALS` and the history choice list from `src/gpum/ui/settings_dialog.py` appears in `docs/usage/controls.md`, and that each documented default matches the corresponding field default on `src/gpum/core/preferences.Preferences`

### Implementation for User Story 2

- [X] T023 [P] [US2] Write `docs/usage/index.md`: the three bars and two trend graphs in the order the window presents them, each with what it measures and its scale; an explicit statement that compute activity at 100% means the GPU was doing *something* throughout the sampling period, not that its cores were saturated; and how gaps, unavailable values, and degraded devices are represented and why never as zero
- [X] T024 [P] [US2] Write `docs/usage/controls.md`: every toolbar control (refresh interval, pause, refresh now, settings) and every setting with its full choice list and default — refresh 0.5/1/2/5/10 s default 1 s, history 1 minute to 1 hour default 5 minutes, slow updates while hidden on, keep in status area on, start at login off
- [X] T025 [P] [US2] Write `docs/usage/processes.md`: the four sortable columns, sorting behavior, and why unmeasurable values rank last in both directions instead of sorting as zero
- [X] T026 [P] [US2] Write `docs/usage/demo-mode.md`: how to start simulated hardware with `--backend fake`, and all eight scenarios (`two-nvidia`, `processes-churn`, `no-attribution`, `metrics-unsupported`, `one-device-hangs`, `mig-device`, `multi-vendor-degraded`, `empty`) with what each demonstrates
- [X] T027 [P] [US2] Write `docs/usage/troubleshooting.md` organized by observed symptom: permission denied, double-click does nothing, download 404, nothing detected, distribution too old, per-process memory unavailable, no graphical session (with the SSH/X11-forwarding guidance the entry point prints)
- [X] T028 [US2] Write `docs/reference/cli.md` covering every option — `--backend`, `--scenario`, `--list-scenarios`, `--version`, `--hidden`, `--install-desktop-entry`, `--remove-desktop-entry`, `-v/--verbose` — with accepted values and effect, plus exit behavior including the no-graphical-session message; it lives under Reference but serves this journey (FR-015), which is why it ships with US2
- [X] T029 [US2] Add the Usage section and the CLI page to the `mkdocs.yml` nav, and cross-link troubleshooting from the download page
- [ ] T030 [US2] Run quickstart scenarios V-3, V-4, V-5 and V-6 against a live preview with GPUM open beside it — **PARTIAL — pages verified against the source of truth by tests; V-3/V-6 need a user with GPUM open**

**Checkpoint**: Users can read and configure the window from the site; US1 and US2 both stand alone.

---

## Phase 5: User Story 3 - A developer understands the code interfaces that matter (Priority: P3)

**Goal**: A curated reference to the interfaces that carry the design, each stating its
obligations, its unavailability behavior, and which of its rules are constitution principles
rather than conventions.

**Independent Test**: A developer who has never seen the codebase states, from the reference
alone, what a new vendor backend must implement, how it must report an unmeasurable value, and
which dependencies are forbidden — matching the design contracts (quickstart V-7).

### Tests for User Story 3 ⚠️ Write first, confirm failing

- [X] T031 [P] [US3] Write `tests/docs/test_reference_entries.py`: assert every required entry from [data-model.md](./data-model.md) exists as a page (backend interface, data model, registry, adapters, CLI), that each links to an existing source module under `src/gpum/` or a contract under `specs/001-gpu-usage-monitor/contracts/`, and that no entry describes an unavailable metric as returning zero

### Implementation for User Story 3

- [X] T032 [P] [US3] Write `docs/reference/index.md`: the scope statement (curated interfaces for extenders and integrators, explicitly not exhaustive symbol coverage), the `backends → core → ui` dependency direction with `core` never importing `ui` and `backends` never importing either, and a marker convention distinguishing constitution principles from conventions
- [X] T033 [P] [US3] Write `docs/reference/backend-interface.md` covering `GpuBackend` — `probe()`, `enumerate_devices()`, `sample_device()`, `capabilities()`, `shutdown()` — with what each returns, that `probe()` never raises because a missing driver is expected rather than exceptional, the `LIBRARY_MISSING` / `DRIVER_MISSING` / `NO_DEVICES` distinction and why it produces different user-facing messages, device keys from stable UUID or PCI ID never the enumeration index, memory in bytes, and a link to `specs/001-gpu-usage-monitor/contracts/backend-interface.md`
- [X] T034 [P] [US3] Write `docs/reference/data-model.md` covering `MetricValue`, `Availability`, `DeviceId`, `GpuDevice`, `GpuProcess`, `BackendCapabilities`, `BackendReport` and `Snapshot`, with the representation of an unavailable metric as a value-or-reason and the prohibition on substituting zero or an estimate, linking to `src/gpum/core/models.py`
- [X] T035 [P] [US3] Write `docs/reference/registry.md`: how a backend is registered as one factory and one dict entry in `src/gpum/registry.py`, how selection works, and what `--backend` does to it
- [X] T036 [P] [US3] Write `docs/reference/adapters.md`: the platform adapter boundary in `src/gpum/adapters/`, what belongs there, that OS conditionals must never appear in feature code or in a backend, and that a failure of `tests/unit/test_import_boundaries.py` means the abstraction was breached
- [X] T037 [US3] Add the Reference section to the `mkdocs.yml` nav including the adopted `docs/adding-a-vendor.md`, which the reference links to for the step-by-step vendor procedure rather than paraphrasing it
- [ ] T038 [US3] Run quickstart scenario V-7 with a developer unfamiliar with the codebase — **PARTIAL — entries verified against the contracts by tests; V-7 needs a developer new to the codebase**

**Checkpoint**: The API reference stands alone and links to authoritative sources.

---

## Phase 6: User Story 4 - A prospective contributor knows how to contribute well (Priority: P4)

**Goal**: Setup, gates, scope boundaries, and problem reporting — enough that a contributor knows
in advance what would block their change and what the project will not accept.

**Independent Test**: A developer on a clean machine with no GPU follows only the contribution
pages, reaches a passing suite, and states correctly what would block their change (V-8).

### Tests for User Story 4 ⚠️ Write first, confirm failing

- [X] T039 [P] [US4] Write `tests/docs/test_contributing_gates.py`: assert every gate command documented in `docs/contributing/quality-gates.md` appears in `.github/workflows/ci.yml` or in `pyproject.toml` markers, so a changed CI gate cannot leave the page describing a check that no longer runs

### Implementation for User Story 4

- [X] T040 [P] [US4] Write `docs/contributing/index.md`: how to report a problem or ask a question and what a useful report contains, placed so it is reachable without reading the development setup first
- [X] T041 [P] [US4] Write `docs/contributing/development.md`: `pip install -e ".[dev]"`, `pytest` passing on a machine with no GPU present, `pytest -m hardware` needing a real NVIDIA GPU, `pytest -m packaging` needing a built bundle, `ruff check src tests`, `mypy`, and `mkdocs serve` for documentation changes
- [X] T042 [P] [US4] Write `docs/contributing/quality-gates.md`: every gate, the documentation each category of change must update in the same commit (capability matrix for support changes, contract tests for interface changes, docs pages for user-visible changes), and that a failing `tests/unit/test_import_boundaries.py` is a violated principle to fix rather than a check to relax
- [X] T043 [P] [US4] Write `docs/contributing/scope.md`: Linux only and no Windows or macOS claim, AMD and Intel registered but unimplemented and described honestly rather than promised, no speculative abstraction before a second concrete case, read-only by default with no mutation of system state — linking to `.specify/memory/constitution.md` and the design documents under `specs/`
- [X] T044 [US4] Add the Contributing section to the `mkdocs.yml` nav including the adopted `docs/building.md`
- [ ] T045 [US4] Run quickstart scenario V-8 on a clean machine with no GPU — **PARTIAL — commands verified; V-8 needs a clean machine**

**Checkpoint**: All four reader-facing stories are complete and independently verifiable.

---

## Phase 7: User Story 5 - The site stays accurate as the project changes (Priority: P5)

**Goal**: Publishing needs no manual step, a failed publish leaves the previous site live, no fact
is editable in two places, and every claim is checked on every publish.

**Independent Test**: Merge a change to a documented fact and watch it reach the live site with no
manual action; break the build deliberately and confirm the previous site stays live (V-12, V-13).

### Tests for User Story 5 ⚠️ Write first, confirm failing

- [X] T046 [P] [US5] Write `tests/docs/test_readme_contract.py` (assertions A-10 and A-11): `README.md` links to the site, the commands it retains appear identically in `docs/download.md`, the long-form sections that moved are absent, and no authored page under `docs/` contains a release-version pattern outside the generated snippet
- [X] T047 [P] [US5] Write `tests/docs/test_no_third_party.py` (assertion A-09): scan built HTML and CSS under `site/` for absolute URLs to any host but the site's own, permitting in-page hyperlinks to `github.com` while forbidding anything the page fetches on load — fonts, scripts, styles, images, beacons — and skip with a stated reason when no build output is present
- [X] T048 [P] [US5] Write `tests/docs/test_external_links.py` marked `network` (assertion A-12): every external link responds successfully and the generated download URL returns a downloadable asset

### Implementation for User Story 5

- [X] T049 [US5] Trim `README.md` to a front door per research D-07: keep the introduction, screenshot, three-step quickstart, and the promises; move the full settings list, troubleshooting catalogue, full CLI list, and feature inventory to the site and link to those pages instead
- [X] T050 [US5] Extend `.github/workflows/docs.yml` triggers per [contracts/publishing.md](./contracts/publishing.md): `release: published` so a new release reaches the download page immediately, a weekly `schedule`, `workflow_dispatch`, path filters on `docs/**`, `mkdocs.yml`, the two `tools/` scripts and `README.md`, and `pull_request` building and checking without deploying
- [X] T051 [US5] Add the remaining gate steps to the `build` job — `pytest tests/docs -m network` and an automated accessibility audit against the built site failing on any critical finding — keeping `deploy` gated on the whole job so a failure leaves the previously published site live
- [ ] T052 [US5] Verify failure semantics (V-12): open a pull request that breaks a documented fact, confirm the drift suite fails, no deploy occurs, the live site is unchanged, and the failure is visible on the commit — **PARTIAL — drift gate proven by injection locally; the no-deploy half needs a real PR run**
- [ ] T053 [US5] Run quickstart scenarios V-10 and V-13, confirming zero third-party requests in a browser network panel and that README and the site agree — **PARTIAL — V-10 and V-13 verified against built output; browser network panel not run**

**Checkpoint**: The site publishes itself and defends its own accuracy.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T054 [P] Run the full quickstart validation sweep V-1…V-13 from [quickstart.md](./quickstart.md) against the deployed site — **PARTIAL — mechanical scenarios run; human-judgment scenarios pending**
- [ ] T055 [P] Verify V-11 by hand: every page readable and navigable with JavaScript disabled and at 360 px width, with no horizontal scrolling of body text — **PARTIAL — static nav and viewport verified in built HTML; visual 360px check pending**
- [X] T056 [P] Confirm `pytest` (default suite, no GPU, no network) passes with `tests/docs/` included, and extend the lint invocation in `.github/workflows/ci.yml` to cover the new `tools/` scripts so `ruff check src tests tools` is clean
- [X] T057 Confirm the complete CI sequence in order — `pytest tests/docs` → `mkdocs build --strict` → `pytest tests/docs -m network` → accessibility audit → deploy — matches [contracts/publishing.md](./contracts/publishing.md)
- [X] T058 Write the pull request description stating the principles touched (II — support claims bound to the capability matrix; IV — drift tests written first and passing with no GPU; V — no third-party requests and least-privilege deploy permissions), as the constitution's workflow gates require

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: needs Setup; blocks every user story
- **US1 (Phase 3)**: needs Foundational — the MVP
- **US2 (Phase 4)**: needs Foundational; independent of US1
- **US3 (Phase 5)**: needs Foundational; independent of US1 and US2
- **US4 (Phase 6)**: needs Foundational; independent of US1–US3
- **US5 (Phase 7)**: needs Foundational; T049 and T046 are most meaningful once US2–US4 pages exist, since the README trim moves content into them
- **Polish (Phase 8)**: needs every story intended for the release

### Within Each User Story

- Tests first, confirmed failing, then implementation (Principle IV)
- Pages before nav entries; nav before the story's verification task
- Each story's verification task closes it

### Parallel Opportunities

- Setup: T002, T003, T004 in parallel after T001
- Foundational: T006 → T007; T008 in parallel with either
- US1: T012 and T013 in parallel; T016 and T017 are separate files but share the nav change in T018
- US2: all three test tasks in parallel; then all five usage pages plus the CLI page in parallel
- US3: all five reference pages in parallel after T031
- US4: all four contributing pages in parallel after T039
- US5: T046, T047, T048 in parallel
- Across stories: once Phase 2 is done, US1–US4 can be staffed independently

---

## Parallel Example: User Story 2

```bash
# Write all three drift tests first, confirm each fails:
Task: "tests/docs/test_cli_documented.py"
Task: "tests/docs/test_scenarios_documented.py"
Task: "tests/docs/test_settings_documented.py"

# Then all six pages, one file each:
Task: "docs/usage/index.md"
Task: "docs/usage/controls.md"
Task: "docs/usage/processes.md"
Task: "docs/usage/demo-mode.md"
Task: "docs/usage/troubleshooting.md"
Task: "docs/reference/cli.md"
```

---

## Implementation Strategy

### MVP (User Story 1 only)

1. Phase 1 Setup → Phase 2 Foundational → Phase 3 US1
2. **Stop and validate**: run V-1 and V-2, including the offline fallback
3. The site is live and a stranger can download and run GPUM from it

This is a genuine shippable increment: the adopted pages (capability matrix, vendor guide, build
guide, licenses) are already published by Phase 2, and US1 adds the acquisition journey on top.

### Incremental Delivery

1. MVP (US1) → deploy
2. US2 → the largest audience after downloading → deploy
3. US3 → developers and integrators → deploy
4. US4 → contributors → deploy
5. US5 → accuracy enforcement and publishing robustness → deploy
6. Phase 8 polish

US5 last is deliberate but not risk-free: until T049 lands, the README and the site both carry the
usage and troubleshooting material. That duplication is the known, temporary cost of shipping
reader value first, and T046 is what stops it becoming permanent.

---

## Notes

- 58 tasks across 8 phases: Setup 5, Foundational 6, US1 8, US2 11, US3 8, US4 7, US5 8, Polish 5
- Nothing under `src/gpum/` is modified; the application is untouched by this feature
- Every test task must be observed failing before its implementation tasks begin
- An assertion is never satisfied by loosening it — if a test fails because the source moved, the
  source-of-truth map in [contracts/content-accuracy.md](./contracts/content-accuracy.md) is
  updated in the same change
- Commit after each task or logical group; stop at any checkpoint to validate a story on its own
