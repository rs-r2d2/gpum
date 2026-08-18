# Contract: Content Accuracy

**Feature**: `007-github-pages-site` | **Date**: 2026-08-18

A documentation site fails quietly. The build stays green, the page stays beautiful, and the
sentence stops being true. This contract names the owner of every fact the site states and the
assertion that fires when a page and its owner disagree.

## Source-of-truth map

Each fact has exactly one owner. Pages restate a fact only where an assertion polices the
restatement; otherwise they link.

| Fact | Owner | How the site gets it |
|---|---|---|
| Supported platform, vendors, verified capabilities | `docs/capability-matrix.md` | The matrix *is* a site page. Other pages link to it; no page restates it |
| Command-line options, choices, defaults | `src/gpum/__main__.py` (argparse) | Restated on `/reference/cli/`, asserted |
| Demonstration scenarios and descriptions | `src/gpum/backends/fake/scenarios.SCENARIOS` | Restated on `/usage/demo-mode/`, asserted |
| Refresh-interval and history choices | `src/gpum/ui/settings_dialog.py` | Restated on `/usage/controls/`, asserted |
| Setting defaults | `src/gpum/core/preferences.Preferences` | Restated on `/usage/controls/`, asserted |
| Minimum Python version | `pyproject.toml` `requires-python` | Restated on `/download/`, asserted |
| glibc baseline for the bundle | `packaging/Dockerfile.build` | Restated on `/download/`, asserted |
| Current release version and asset URL | GitHub releases API | Generated into `docs/_snippets/release.md`; never authored |
| Backend interface obligations | `specs/001-gpu-usage-monitor/contracts/backend-interface.md` | Summarized on `/reference/backend-interface/` with a link to the contract |
| Vendor-addition procedure | `docs/adding-a-vendor.md` | Adopted as a page; the reference links to it |
| Bundle build procedure | `docs/building.md` | Adopted as a page |
| Quality gates | `.github/workflows/ci.yml`, `pyproject.toml` | Restated on `/contributing/quality-gates/`, asserted by command name |
| Governing principles | `.specify/memory/constitution.md` | Linked, never paraphrased as authority |

## Assertions

All assertions below run offline, with no GPU, in the default `pytest` invocation, except those
marked `network`. They are written before the pages they validate and must fail first
(Principle IV).

### A-01 · CLI options are fully documented
`tests/docs/test_cli_documented.py` — build the parser from `src/gpum/__main__.py`, extract every
option string and its `choices`, and assert each appears in `docs/reference/cli.md`. Fails when an
option is added, renamed, or given new choices without the page following.
*Discharges FR-015, SC-006.*

### A-02 · Scenarios are fully documented
`tests/docs/test_scenarios_documented.py` — assert every key of `SCENARIOS` appears in
`docs/usage/demo-mode.md`, and that each scenario's `description` text appears there too, so the
page cannot drift from what `--list-scenarios` prints.
*Discharges FR-021, SC-006.*

### A-03 · Settings choices and defaults are fully documented
`tests/docs/test_settings_documented.py` — assert every label in `_INTERVALS` and in the history
choice list appears in `docs/usage/controls.md`, and that the documented default for each setting
matches the corresponding field default on `Preferences` (refresh 1 s, history 5 minutes, throttle
when hidden on, tray on, start hidden off).
*Discharges FR-019, SC-006.*

### A-04 · No support claim exceeds the capability matrix
`tests/docs/test_support_claims.py` — scan every page for support-claim phrasing about Windows or
macOS, permitting only explicit non-support statements; and assert no page describes AMD or Intel
as supported or as forthcoming, since the matrix records them as registered and unimplemented.
*Discharges FR-033, FR-038, SC-011; constitution Principle II.*

### A-05 · Version facts match their owners
`tests/docs/test_support_claims.py` — assert the Python version stated on `/download/` matches
`requires-python`, and the glibc baseline stated there matches the base image pinned in
`packaging/Dockerfile.build`.
*Discharges FR-013, SC-011.*

### A-06 · Internal links and anchors resolve
`tests/docs/test_links_and_media.py` — every relative link from a page resolves to an existing
file under `docs/`; every fragment resolves to a heading in the target; every link to a repository
path (source module, spec contract, workflow) resolves in the working tree.
*Discharges FR-028, FR-039, SC-004.*

### A-07 · Every informative image has alt text
`tests/docs/test_links_and_media.py` — every image reference carries non-empty alt text, and every
referenced media file exists.
*Discharges FR-022, SC-014.*

### A-08 · Heading structure is well formed
`tests/docs/test_links_and_media.py` — exactly one top-level heading per page; no skipped levels.
*Discharges FR-005, SC-014.*

### A-09 · No third-party requests in built output
`tests/docs/test_no_third_party.py` — scan built HTML and CSS under `site/` for absolute URLs to
any host other than the site's own. Permitted: in-page hyperlinks to `github.com`, which the
reader chooses to follow. Forbidden: anything the page fetches on load — fonts, scripts, styles,
images, beacons. Skipped with a clear reason when no build output is present; the CI docs job
always builds first, so it always runs there.
*Discharges FR-006, FR-007, SC-012; constitution Principle V.*

### A-10 · README and site agree
`tests/docs/test_readme_contract.py` — assert `README.md` links to the site; assert the commands it
retains appear identically in `docs/download.md`; assert it no longer carries the long-form
sections that moved (full settings list, troubleshooting catalogue, full CLI list), so the
duplication FR-040 forbids cannot creep back.
*Discharges FR-040, SC-015.*

### A-11 · No hardcoded release version
`tests/docs/test_readme_contract.py` — assert no authored page under `docs/` contains a
release-version pattern outside the generated snippet.
*Discharges FR-017, SC-005, SC-015.*

### A-12 · External links and the download URL are reachable `network`
Marked `network`, deselected by default, run in the CI docs job — every external link responds
successfully, and the generated download URL returns a downloadable asset.
*Discharges FR-039, SC-004, SC-005.*

### A-13 · Accessibility audit *(CI job, not pytest)*
An automated audit runs against the built site; any critical finding fails the job.
*Discharges FR-005, SC-014.*

## Failure semantics

- A-01 through A-11 failing means the default test suite fails, so the disagreement blocks merge
  and is visible to the contributor who caused it — the point being that whoever renames a flag
  finds out from their own `pytest` run, not from a reader months later.
- A-12 and A-13 failing fails the docs CI job, which blocks deployment; the previously published
  site stays live (see [publishing.md](./publishing.md)).
- No assertion is satisfied by loosening it. An assertion that fails because the site is right and
  the source moved is fixed by updating the source-of-truth map above in the same change.

## Coverage of spec requirements

FR-006, FR-007, FR-013, FR-015, FR-017, FR-019, FR-021, FR-022, FR-028, FR-033, FR-038, FR-039,
FR-040 and success criteria SC-004, SC-005, SC-006, SC-011, SC-012, SC-014, SC-015 each have at
least one owning assertion above. Requirements without an assertion — the prose-quality ones such
as FR-012's "expected outcome per step" or FR-020's "state what it does not mean" — are verified by
the acceptance scenarios in [quickstart.md](../quickstart.md), because they are judgments about
whether an explanation lands, not properties a test can read.
