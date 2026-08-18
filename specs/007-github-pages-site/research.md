# Phase 0 Research: GPUM Project Website

**Feature**: `007-github-pages-site` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

Every decision below resolves a Technical Context unknown in [plan.md](./plan.md). Each records
the simpler alternative that was rejected, as the constitution's workflow gates require.

---

## D-01: Site generator — MkDocs with Material for MkDocs, built in CI

**Decision**: Author the site as Markdown under the existing `docs/` directory and build it with
MkDocs using the Material theme. Add a `docs` optional-dependency group to `pyproject.toml`.

**Rationale**:

- The repository is a Python project and `docs/` is already Markdown. Contributors get local
  preview with `pip install -e ".[docs]" && mkdocs serve` — no second language runtime.
- Material supplies, as defaults, four things FR-004/FR-005 would otherwise require hand-building
  and hand-testing: responsive layout, a navigation tree that works without JavaScript (CSS
  checkbox disclosure, not scripted), light/dark palettes honoring `prefers-color-scheme`, and
  AA-contrast text with visible keyboard focus rings.
- MkDocs is BSD-2, Material is MIT — both compatible with the project's MIT license. Neither is
  distributed with the application, so `docs/licenses.md` gains a build-tooling note only.

**Alternatives rejected**:

| Alternative | Why rejected |
|---|---|
| GitHub Pages' built-in Jekyll build | Requires a Ruby toolchain that exists nowhere else in this project, restricts plugins to an allowlist, and — decisively — offers no build step, so the release snippet (D-04) and the drift checks (D-06) would have nowhere to run. |
| Hugo | Fastest of the three, but a Go binary is as foreign to this repo as Ruby, and the speed of a ~20-page site is not a problem worth importing a toolchain to solve. |
| Hand-written HTML/CSS | Re-implements responsive navigation, theming, and contrast by hand, and duplicates the nav markup on every page. The accessibility bar in FR-005/SC-014 is much cheaper to clear with a theme that already clears it. |
| MkDocs with the stock theme | Saves one dependency and loses dark mode, the responsive nav, and the contrast work — the exact things being paid for. |

---

## D-02: Zero third-party requests — Material must be configured, not merely adopted

**Decision**: Configure `theme.font: false`, add no analytics/social/CDN plugins, and self-host
every asset. Assert it with a test that scans built HTML for absolute URLs to any host other than
the site's own, allowing only in-page links to `github.com` (which are navigation the visitor
chooses to follow, not requests the page issues).

**Rationale**: Material's default `theme.font` setting makes the *visitor's browser* fetch Google
Fonts on every page load. That is a third-party request disclosing the reader's IP and page, which
FR-006/FR-007 forbid and SC-012 measures. A tool whose headline promise is "it never phones home"
cannot have a website that does. The setting is one line; missing it silently is the risk, which
is why the check is automated rather than remembered.

**Alternatives rejected**: Leaving fonts on and disclosing them in a privacy note — the spec's
requirement is zero third-party requests, not disclosed ones. Vendoring the font files locally —
adds ~200 KB of binary assets and a licensing question for no gain over the system font stack.

---

## D-03: `docs/` becomes the site source; existing documents become pages unchanged

**Decision**: Set `docs_dir: docs`. The four existing documents — `capability-matrix.md`,
`adding-a-vendor.md`, `building.md`, `licenses.md` — stay exactly where they are and become site
pages by being listed in the navigation. No copies are made.

**Rationale**: This is the cheapest possible satisfaction of FR-038 and FR-040. The capability
matrix is not *restated* on the support page — it *is* the support page, so a constitution
Principle II amendment that updates the matrix updates the site in the same commit, with no
synchronization mechanism to build, forget, or debug. Same for the vendor-addition guide, which
the API reference links to rather than paraphrasing.

**Alternatives rejected**: A separate `site/` or `www/` tree that imports from `docs/` — creates
exactly the two-editable-copies situation FR-040 prohibits, and would need an include mechanism
and a drift test to police a problem that not copying does not have. Keeping `docs/` for
maintainers and writing user pages elsewhere — splits the audience by directory rather than by
navigation, which is where readers actually experience the split.

---

## D-04: Download links — generated at build time from the releases API, with an offline fallback

**Decision**: `tools/gen_release_snippet.py` calls `GET /repos/rs-r2d2/gpum/releases`, selects the
newest non-draft release having an `.AppImage` asset, and writes `docs/_snippets/release.md`
(gitignored) containing the version, the asset URL, and the ready-to-paste command block. Pages
embed it with `pymdownx.snippets` (already a Material dependency — no new plugin). A MkDocs
`on_pre_build` hook runs the generator, so no build can proceed with a stale or missing snippet.
Rebuild triggers include `release: published`, so a new release updates the site immediately.

**Rationale**: This is the site's single highest-stakes correctness requirement (FR-010, SC-005)
because the project's normal condition is the one that breaks the obvious approach: every release
so far is marked pre-release, and `/releases/latest/` deliberately skips pre-releases and returns
404. The README currently warns readers about this; a website that repeats the warning instead of
removing the cause has not done its job. Listing all releases and filtering ourselves is what makes
the pre-release case ordinary rather than special.

**Fallback behavior** (spec edge case: no release, or no bundle asset): the generator writes a
snippet that links to the releases page and states plainly that no bundle is currently published,
directing the reader to the from-source route. It never emits a URL it has not seen in the API
response. The build succeeds; the page tells the truth.

**Alternatives rejected**:

| Alternative | Why rejected |
|---|---|
| Link to `/releases/latest/download/...` | This is the exact known defect. It 404s for every release this project has published. |
| Fetch the release client-side with JavaScript | Breaks FR-004 (core content without scripting) and, worse, makes every visitor's browser call `api.github.com` — a third-party request, forbidden by FR-006. |
| Hand-edit the version in the pages | FR-017 forbids requiring a manual edit in more than one place per release, and hand-edited versions are how documentation goes stale. |
| Link only to the releases page, no direct download | Always correct and always one extra hop, plus the visitor must then choose among assets and pre-release labels — the friction FR-009 exists to remove. Retained as the *fallback*, not the default. |

---

## D-05: Publishing — GitHub Actions with the official Pages actions, minimal permissions

**Decision**: A `docs` workflow builds the site and deploys via `actions/configure-pages`,
`actions/upload-pages-artifact`, and `actions/deploy-pages`, with the repository's Pages source set
to "GitHub Actions". Job permissions are `contents: read`, `pages: write`, `id-token: write` and
nothing more. Triggers: push to `main` (paths-filtered to docs sources), `release: published`,
`workflow_dispatch`, and a weekly `schedule`. Pull requests build the site and run every check but
do not deploy.

**Rationale**: Deploy failure semantics come free and match FR-037 exactly — the deploy step runs
only after build and checks succeed, so a failure leaves the previously published site live and
surfaces as a red check rather than as silence. Least privilege (Principle V) is the reason for the
actions-based deploy over the branch-based one: nothing in this feature needs write access to the
repository's contents.

**Alternatives rejected**: `mkdocs gh-deploy` pushing a `gh-pages` branch — requires `contents:
write`, a strictly larger privilege than the task needs, and writes build output into git history.
Building on every push regardless of path — spends CI minutes redeploying an unchanged site;
the weekly schedule already covers "the world changed but the repo did not" (a new release
published outside the release event, for instance).

---

## D-06: Accuracy enforcement — drift tests in the default suite, link checks behind a marker

**Decision**: Add `tests/docs/`, written before the pages and failing first (Principle IV). The
suite is offline and runs with no GPU present, so it joins the default `pytest` run. External link
reachability goes behind a new `network` marker, deselected by default, matching the existing
`hardware` and `packaging` convention; CI runs it in the docs job.

**Assertions, and the requirement each discharges**:

| Assertion | Discharges |
|---|---|
| Every `argparse` option in `src/gpum/__main__.py` appears in the CLI reference page | FR-015, SC-006 |
| Every key in `backends/fake/scenarios.SCENARIOS` appears in the demo-mode page with its description | FR-021, SC-006 |
| Every `_INTERVALS` and history choice in `ui/settings_dialog.py`, and every `core.preferences.Preferences` default, appears in the settings page | FR-019, SC-006 |
| No page asserts support for Windows or macOS (phrase-level scan, allowing the explicit "not supported" statements) | FR-033, FR-038, SC-011, Principle II |
| No page claims a vendor is supported beyond what `docs/capability-matrix.md` records | FR-038, SC-011 |
| Every internal Markdown link and anchor resolves | FR-039, SC-004 |
| Every image referenced by a page has non-empty alt text | FR-022, SC-014 |
| Built HTML issues no request to a third-party host | FR-006, SC-012 |
| `README.md` links to the site, and its retained quickstart commands match the docs sources | FR-040, SC-015 |
| External links and the generated download URL respond successfully (`network` marker) | FR-039, SC-004, SC-005 |

**Rationale**: The failure mode this feature must survive is not a broken build — it is a page that
still renders beautifully while telling the reader something that stopped being true. Only the
checks that read the source of truth catch that class, and putting them in the default suite means
a contributor who renames a CLI flag learns about the stale page from their own `pytest` run.

**Alternatives rejected**: Reviewing docs by hand at release time — SC-011 and SC-015 require
verification on every publish, and human review is what produced the drift these checks exist to
prevent. An external link-checking action instead of a marker — a third-party action does the same
work while being unrunnable locally and inconsistent with how this repo already segregates
network- and hardware-dependent tests.

---

## D-07: README relationship — trim to a front door, move the depth to the site

**Decision**: `README.md` keeps its voice and its job as the repository entry point: what GPUM is,
the screenshot, the three-step quickstart, the promises, and links into the site's sections. The
long-form material — full usage reference, every CLI option, the troubleshooting catalogue, the
feature inventory — moves to the site, where it gains navigation and cross-linking. The overlap
that remains is the quickstart commands, and the drift test asserts those match the docs source.

**Rationale**: FR-040 forbids two editable copies of the same fact. Deduplication has to happen
somewhere, and README is the right side to shrink: a reader on the site can navigate, search, and
reach every neighboring page, while a reader in the README is scrolling a single wall. Nothing
written in the recent README rewrite is discarded — the explanations of `chmod +x`, of why drivers
are not bundled, and of what "100% busy" does not mean all move to pages where they can be linked
to directly from the places that need them.

**Alternatives rejected**: Leaving README untouched and accepting duplication with a fact-level
drift test — cheaper now, and it means every future edit must be made twice or silently diverge in
tone; the test can police facts but not the two descriptions drifting in emphasis. Generating
README from docs partials — GitHub renders no include mechanism, so this needs a generator plus a
committed-output check, which is more machinery than a trimmed README needs.

---

## D-08: Two install routes must be documented as they actually work

**Decision**: The site documents the bundle route as primary, and the from-source route as
`git clone` followed by `pip install -e ".[nvidia]"`. It does not present `pip install gpum`.

**Rationale**: The README's `pip install -e ".[nvidia]"` presupposes a cloned working copy without
saying so; `-e .` has no meaning to a reader who never cloned, and the command fails with an error
about the current directory that names nothing they did wrong. There is no PyPI publication to
offer instead. FR-012 requires each step to state its expected outcome, which forces this to be
fixed rather than inherited. Publishing to PyPI is a genuine improvement and explicitly out of
scope for this feature.

**Alternatives rejected**: Publishing to PyPI as part of this feature — a distribution change with
its own naming, versioning, and release-process consequences, unrelated to building a website.

---

## D-09: Dependency placement — `docs` extra, never a runtime dependency

**Decision**: `[project.optional-dependencies] docs = ["mkdocs>=1.6", "mkdocs-material>=9.5"]`.
Not added to `dev`, not added to runtime dependencies.

**Rationale**: The constitution's technology constraints require that installing GPUM pull in
nothing it does not need to run; a documentation toolchain in `dev` would also be installed by
every contributor who only wants to run tests. A separate extra keeps `pip install -e ".[dev]" &&
pytest` — the contribution path in FR-030 — as fast as it is today. The docs *checks* live in the
default test suite (D-06) and deliberately depend on nothing from this extra: they read Markdown
sources, not built HTML, except for the third-party-request scan, which is marked and skipped when
no build output is present.

---

## D-10: Site identity

**Decision**: `site_url: https://rs-r2d2.github.io/gpum/`, canonical links and sitemap enabled,
no custom domain. `site_name: GPUM`.

**Rationale**: The default project address is free, immediate, and needs no DNS ownership. A custom
domain is purely additive later — it changes one configuration line and a DNS record, and invalidates
none of the content built here, which is why the spec puts it out of scope.

---

## D-11: Accessibility verification

**Decision**: Two layers. The offline drift suite asserts the structural properties (alt text on
every informative image, heading levels descending without gaps, no meaning conveyed by color
alone in authored content). The docs CI job additionally runs an automated accessibility audit
against the built site and fails on any critical finding.

**Rationale**: SC-014 requires an automated audit, and structural assertions in pytest cannot see
computed contrast or focus order — the two things a real audit catches. Splitting them keeps the
fast, offline, always-run checks separate from the slow one that needs a built site and a browser.

**Alternatives rejected**: Audit only, no structural tests — the audit runs in CI on built output,
so a contributor writing a page with a missing alt text learns about it minutes later instead of
immediately. Structural tests only — cannot verify contrast, which is exactly where a theme
customization would break AA.

---

## Resolved Technical Context

No `NEEDS CLARIFICATION` markers remain. Language: Python 3.11+ for the build hook, generator, and
tests. Primary dependencies: MkDocs, Material for MkDocs (docs extra). Storage: none — static
files, no server component. Testing: pytest (`tests/docs/`), plus the `network` marker for
reachability and an accessibility audit in CI. Target platform: static pages served by GitHub
Pages; readers on any modern browser, desktop and mobile. Project type: documentation site inside
an existing desktop-application repository.
