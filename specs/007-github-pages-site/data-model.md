# Phase 1 Data Model: GPUM Project Website

**Feature**: `007-github-pages-site` | **Date**: 2026-08-18 | **Plan**: [plan.md](./plan.md)

This feature stores nothing at runtime. Its "data" is authored content plus one generated fact
block, and its validation rules are the assertions in `tests/docs/`. Each entity below lists its
fields, where it comes from, and the rules that must hold — the rules are the specification the
drift tests implement.

---

## Section

A top-level area of the site with a stated audience.

| Field | Type | Source |
|---|---|---|
| `title` | text | `mkdocs.yml` nav |
| `path` | URL segment | directory under `docs/` |
| `audience` | text | stated in the section's index page |
| `pages` | ordered list of Page | `mkdocs.yml` nav |

**Rules**

- Exactly five sections exist: Overview, Download, Usage, Reference, Contributing (FR-002).
- Every section appears in the global navigation on every page (FR-003).
- Section order in navigation follows the spec's user-story priority: acquisition, then usage,
  then reference, then contributing.

---

## Page

One readable unit.

| Field | Type | Source |
|---|---|---|
| `title` | text | first `#` heading |
| `path` | file path | file under `docs/` |
| `section` | Section | nav position |
| `body` | Markdown | authored, or existing document adopted unchanged |
| `links` | list of Link | parsed from body |
| `images` | list of Image | parsed from body |

**Rules**

- Every page carries the project name and full navigation, so a visitor arriving from a search
  result on a deep page can reach the download page and every other section (FR-003, edge case
  "arrives directly on a deep page").
- Heading levels descend without skipping (`#` → `##` → `###`), one `#` per page (FR-005).
- Every page is reachable from navigation; no orphan pages.
- Adopted existing documents (`capability-matrix.md`, `adding-a-vendor.md`, `building.md`,
  `licenses.md`) are edited only when their own subject changes — never to serve site layout.

---

## Link

| Field | Type | Notes |
|---|---|---|
| `target` | URL or relative path | |
| `kind` | `internal` \| `repository` \| `external` \| `download` | |
| `anchor` | text or none | fragment, if any |

**Rules**

- `internal`: the target file exists under `docs/` and, if an anchor is present, a heading
  generating that anchor exists in it (FR-039, SC-004). Checked offline, default suite.
- `repository`: the target path exists in the working tree — this is what stops a reference to a
  moved source module from rotting silently (FR-028).
- `external` and `download`: reachability checked under the `network` marker in CI (SC-004).
- No link is checked by eye. Every category above has an owning assertion.

---

## Image

| Field | Type |
|---|---|
| `path` | file under `docs/media/` |
| `alt` | text |
| `caption` | text or none |

**Rules**

- Alt text is non-empty for every image that carries information, and conveys what the image
  shows rather than naming the file (FR-022, SC-014).
- The application screenshot is a real capture of the running application, never a mockup, and
  its caption says what was happening when it was taken (spec assumption; Principle I's spirit —
  the project does not present anything it did not measure).

---

## ReleaseMetadata *(generated)*

Produced by `tools/gen_release_snippet.py` from `GET /repos/rs-r2d2/gpum/releases`, written to
`docs/_snippets/release.md`, embedded by the download page and the landing page.

| Field | Type | Derivation |
|---|---|---|
| `tag` | text | tag of the newest non-draft release having an `.AppImage` asset |
| `version` | text | version as displayed to readers |
| `asset_name` | text | the asset's filename, verbatim from the API |
| `asset_url` | URL | the asset's browser download URL, verbatim from the API |
| `is_prerelease` | boolean | from the API |
| `state` | `resolved` \| `fallback` | whether an asset was found |

**Rules**

- Pre-releases are eligible. This is the whole point: every release published so far is a
  pre-release, and the conventional "latest" link skips them and 404s (FR-010, SC-005).
- Draft releases are never eligible.
- No URL is emitted that did not appear in the API response — the generator never constructs a
  download URL by pattern.
- `state = fallback` when the API is unreachable or no release carries a bundle asset. The snippet
  then links to the releases page, states plainly that no bundle is currently published, and
  points at the from-source route. The build succeeds (spec edge case).
- Exactly one place in the repository holds a release version for the site; no page hardcodes one
  (FR-017, SC-015).

---

## RequirementStatement

A condition the visitor's machine must satisfy, presented before the download instructions.

| Field | Type | Owning source |
|---|---|---|
| `subject` | text | — |
| `value` | text | — |
| `applies_to` | `bundle` \| `from-source` \| `both` | — |

**Instances and their owners**

| Subject | Value | Owner |
|---|---|---|
| Operating system | Linux, 64-bit x86 | `docs/capability-matrix.md` |
| System library baseline | glibc 2.35+ (bundle route) | `packaging/Dockerfile.build` |
| Language runtime | Python 3.11+ (from-source route) | `pyproject.toml` `requires-python` |
| GPU and driver | NVIDIA driver installed; AMD/Intel registered but unimplemented | `docs/capability-matrix.md` |
| Disk footprint | approximately 50 MB | measured bundle size |
| Graphical session | a desktop session is required; SSH needs X11 forwarding | `src/gpum/__main__.py` |

**Rules**

- Every statement appears above the download instructions on the page, not below them (FR-013).
- No statement is authored freehand where an owning source exists; each is checked against its
  owner (FR-038, SC-011).

---

## WindowElement

A described part of the running application.

| Field | Type |
|---|---|
| `name` | text |
| `kind` | `bar` \| `graph` \| `table-column` \| `control` \| `setting` |
| `measures` | text — what it reports |
| `scale_or_units` | text |
| `default` | text or none (settings and controls) |
| `choices` | list or none (settings) |
| `misreading` | text or none — what it explicitly does not mean |

**Known instances** (the documentation must cover all of them — SC-006)

- Bars: memory used vs total; GPU compute activity; memory interface activity.
- Graphs: memory (scaled to card capacity); activity (fixed 0–100%).
- Table columns: process, PID, user, GPU memory — all sortable, unavailable values ranked last in
  both directions.
- Controls: refresh interval, pause, refresh now, settings.
- Settings: refresh every (0.5 s, 1 s, 2 s, 5 s, 10 s; default 1 s); keep history for (1 minute to
  1 hour; default 5 minutes); slow updates while hidden (default on); keep in status area when
  closed (default on); start at login (default off).

**Rules**

- `choices` and `default` are read from `src/gpum/ui/settings_dialog.py` and
  `src/gpum/core/preferences.py`; a page disagreeing with either fails the suite (FR-019, SC-006).
- At least the compute-activity element carries a `misreading` entry: busy 100% of the time means
  the GPU was doing *something* throughout the sampling period, not that its cores were saturated
  (FR-020).
- Unavailability is documented as a represented state with a reason, never as zero, and a gap in a
  trend line is documented as a gap rather than a drop (FR-020, Principle I).

---

## DemonstrationScenario

| Field | Type | Source |
|---|---|---|
| `name` | text | key in `backends/fake/scenarios.SCENARIOS` |
| `description` | text | `Scenario.description` |
| `demonstrates` | text | authored — why a reader would choose it |

**Known instances**: `two-nvidia`, `processes-churn`, `no-attribution`, `metrics-unsupported`,
`one-device-hangs`, `mig-device`, `multi-vendor-degraded`, `empty` (eight total).

**Rules**

- Every key in `SCENARIOS` is documented; adding a scenario without documenting it fails the
  default test suite (FR-021, SC-006).
- Each documented description matches the one the application prints for `--list-scenarios`.

---

## CliOption

| Field | Type | Source |
|---|---|---|
| `flag` | text | `argparse` in `src/gpum/__main__.py` |
| `choices` | list or none | parser definition |
| `default` | text or none | parser definition |
| `effect` | text | authored |

**Known instances**: `--backend` (nvidia, amd, intel, fake, none), `--scenario`,
`--list-scenarios`, `--version`, `--hidden`, `--install-desktop-entry`,
`--remove-desktop-entry`, `-v/--verbose`.

**Rules**

- Every option registered on the parser appears in `docs/reference/cli.md` with its choices
  (FR-015, SC-006). Four options undocumented in today's README are covered by this rule.
- Exit behavior is documented, including the explanatory message and non-zero exit when no
  graphical session is present.

---

## ApiEntry

| Field | Type |
|---|---|
| `name` | text |
| `purpose` | text |
| `obligations` | list — what an implementer or caller must do |
| `unavailability_behavior` | text — what happens when data cannot be obtained |
| `failure_behavior` | text — errors, timeouts, permission denial |
| `source_link` | repository path |
| `principle_backed` | boolean — is this rule a constitution principle, not a convention |

**Required entries** (FR-024): the backend interface (`GpuBackend`); the normalized data model
(`MetricValue`, `Availability`, `GpuDevice`, `GpuProcess`, `DeviceId`, `BackendReport`,
`BackendCapabilities`); the registration point (`registry`); the platform adapter boundary
(`adapters/`); the entry point and its options (`__main__`).

**Rules**

- Every entry links to its source module or its design contract under
  `specs/001-gpu-usage-monitor/contracts/` (FR-028).
- Every entry states unavailability behavior explicitly; "returns zero" is never a correct answer
  (FR-025, Principle I).
- Entries whose rules are constitution principles say so, so a reader can tell a hard rule from a
  preference (FR-026).
- The reference states its own scope: curated, not exhaustive (FR-029).

---

## QualityGate

| Field | Type |
|---|---|
| `name` | text |
| `command` | text |
| `verifies` | text |
| `failure_meaning` | text |

**Instances**: lint (`ruff check src tests`); type check (`mypy`); test suite (`pytest`, passes
with no GPU present); hardware suite (`pytest -m hardware`); packaging suite (`pytest -m
packaging`); import-boundary test — whose failure means the vendor or platform abstraction has
been breached, a principle violation to fix rather than a check to relax (FR-032).

---

## CapabilityClaim

Any statement on the site about what is supported.

| Field | Type |
|---|---|
| `subject` | platform, vendor, or capability |
| `status` | supported \| degraded \| not implemented \| not claimed |
| `evidence` | link to `docs/capability-matrix.md` |

**Rules**

- No claim exceeds what the matrix records (FR-038, SC-011).
- Linux is the only platform claimed. Windows and macOS are stated as not supported and not
  planned; no page implies otherwise (Principle II).
- NVIDIA is the only implemented vendor; AMD and Intel are registered but unimplemented and are
  described that way rather than as "coming soon" (Principle I's honesty rule).

---

## Entity relationships

```text
Section 1─* Page 1─* Link
                 └─* Image

Page ──embeds──> ReleaseMetadata        (download page, landing page)
Page ──documents──> WindowElement       (usage section)
Page ──documents──> DemonstrationScenario, CliOption
Page ──documents──> ApiEntry            (reference section)
Page ──documents──> QualityGate         (contributing section)
Page ──asserts──> CapabilityClaim ──evidenced by──> capability-matrix.md

Every documented entity has an owning source in the repository.
Every owning source has a test that fails when the page and the source disagree.
```
