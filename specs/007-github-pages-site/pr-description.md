# Documentation site (GitHub Pages)

Publishes a documentation site for GPUM at `https://rs-r2d2.github.io/gpum/`, built with MkDocs
and Material from the repository's existing `docs/` directory, and deployed by GitHub Actions.

Spec: `specs/007-github-pages-site/`.

## What changed

- **Site**: `mkdocs.yml`, new pages for the landing page, download, usage (5 pages), a curated
  API reference (6 pages), and contributing (4 pages). The four documents already in `docs/` —
  capability matrix, adding a vendor, building, licences — are *adopted* as pages, not copied.
- **Download block is generated** (`tools/gen_release_snippet.py` + an `on_pre_build` hook): the
  download command comes from the releases API at build time, so it resolves to a real asset even
  though every release so far is a pre-release, and no page contains a version number.
- **Drift tests** (`tests/docs/`, 8 modules): read the argument parser, scenario table, settings
  dialog, `Preferences` defaults, capability matrix, `pyproject.toml`, and the build container,
  and fail when a page disagrees with any of them.
- **README trimmed** to a front door that links into the site; the long-form usage,
  troubleshooting, and option material moved to pages that can be linked to individually.
- **CI**: new `docs` workflow; `ruff check` in the existing workflow extended to `tools`; the
  `network` marker added and deselected by default.

## Principles touched

**II — Single Target, Adapters Kept Honest.** The capability matrix *is* the site's support page
rather than a source for one, so an amendment updates the site in the same commit. A test scans
every page for positive support claims about Windows or macOS and for vendor claims exceeding the
matrix; it carries its own self-test proving the detector still catches real claims, so it cannot
be loosened into a check that passes everything.

**IV — Test-First on Simulated Hardware.** Every drift test was written before the page it
validates and observed failing. The suite is offline and hardware-free: the release generator is
tested against recorded API fixtures in `tests/fixtures/releases/`, and everything needing the
network sits behind the new `network` marker, deselected by default like `hardware` and
`packaging`.

**V — Read-Only, Least Privilege, No Telemetry.** Two concrete findings, both fixed and both now
enforced by tests rather than by memory:

1. Material's default `theme.font` setting makes the *visitor's* browser fetch Google Fonts. It
   is disabled explicitly.
2. Setting `repo_url` makes every page call `api.github.com` from the reader's browser for star
   counts. `repo_url` is therefore deliberately unset, and the repository is linked from page
   content and the footer instead.

`tests/docs/test_no_third_party.py` parses built HTML for anything the browser fetches — ignoring
`<a href>`, which is navigation the reader chooses — and fails on any third-party host. The
deploy job holds `contents: read`, `pages: write`, `id-token: write` and nothing more; the
branch-pushing deploy that needs `contents: write` was rejected on that ground.

**No deviations.** Complexity is justified against the rejected simpler alternative in
`specs/007-github-pages-site/research.md` (D-01 … D-11).

## Verification

- `pytest` — full default suite green, including 100+ new documentation assertions, offline
- `pytest tests/docs -m network` — external links and the live download URL resolve
- `mkdocs build --strict` — clean
- `ruff check src tests tools` — clean
- Drift gate proven by injection: renaming `--list-scenarios` in the parser fails the suite, and
  the deploy job cannot run because it `needs: build`

## Known gaps

- `mypy` reports 12 pre-existing errors in `src/gpum/core` (`engine.py`, `power.py`,
  `models.py`). Untouched by this change and not introduced by it.
- Repository setting required once before the first deploy: **Settings → Pages → Source: GitHub
  Actions**.
- The accessibility audit step and the release-triggered rebuild have not run yet; both need CI.
