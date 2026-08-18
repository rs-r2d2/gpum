# Contract: Publishing

**Feature**: `007-github-pages-site` | **Date**: 2026-08-18

How the site gets built, checked, and deployed — and what happens when any of that fails.

## Deployment target

| Property | Value |
|---|---|
| Host | GitHub Pages, repository `rs-r2d2/gpum` |
| Pages source | GitHub Actions (not a branch) |
| URL | `https://rs-r2d2.github.io/gpum/` |
| Custom domain | None (out of scope; additive later, invalidates no content) |
| Cost | Zero (FR-001) |

## Workflow: `.github/workflows/docs.yml`

### Triggers

| Trigger | Purpose |
|---|---|
| `push` to `main`, filtered to `docs/**`, `mkdocs.yml`, `tools/gen_release_snippet.py`, `tools/mkdocs_hooks.py`, `README.md` | Publish merged documentation changes (FR-036) |
| `release: published` | A new release must reach the download page immediately, not at the next docs commit (FR-010) |
| `schedule`, weekly | Catches release state that changed without a repository event |
| `workflow_dispatch` | Manual republish |
| `pull_request` | Build and check only — **never deploys** |

### Jobs

**`build`** — runs on every trigger including pull requests.

1. Check out; set up Python 3.12; `pip install -e ".[docs,dev]"`.
2. `pytest tests/docs` — the offline drift suite (A-01…A-11).
3. `mkdocs build --strict`. The `on_pre_build` hook runs `tools/gen_release_snippet.py` first, so
   no build can proceed without a current release block. `--strict` promotes MkDocs warnings —
   unresolved links, files missing from nav — to failures.
4. `pytest tests/docs -m network` — external reachability and the generated download URL (A-12).
5. Automated accessibility audit against the built site; any critical finding fails (A-13).
6. Upload the built site as a Pages artifact.

**`deploy`** — `needs: build`, and runs only on non-pull-request triggers on `main`. Deploys the
uploaded artifact with `actions/deploy-pages`.

### Permissions

```yaml
permissions:
  contents: read
  pages: write
  id-token: write
```

Nothing more. Least privilege is the reason for the Actions-based deploy over a `gh-pages` branch
push, which would require `contents: write` for work that never needs to write to the repository
(constitution Principle V).

## Release-snippet generator

**Script**: `tools/gen_release_snippet.py`
**Invoked by**: `tools/mkdocs_hooks.py` at `on_pre_build`, so it runs for `mkdocs serve` and
`mkdocs build` alike; also runnable directly.

### Input

| Input | Source | Notes |
|---|---|---|
| Release list | `GET https://api.github.com/repos/rs-r2d2/gpum/releases` | Unauthenticated is sufficient; uses `GITHUB_TOKEN` when present, purely for rate limits |
| `GPUM_DOCS_OFFLINE` | environment | When set, skip the request and take the fallback path — this is how contributors work offline and how the fallback gets tested |

### Selection rule

The newest release that is **not a draft** and carries an asset whose name ends in `.AppImage`.
Pre-releases are eligible — this is the entire reason the generator exists, since every release
published so far is a pre-release and `/releases/latest/` skips them and returns 404.

### Output

`docs/_snippets/release.md` (gitignored), embedded via `pymdownx.snippets`.

**Resolved state** — version, asset name, the direct download command, the `chmod +x` step, and
the run command, all using values taken verbatim from the API response. The generator never
constructs a download URL from a pattern; a URL it did not receive is a URL it does not print.

**Fallback state** — when the API is unreachable, rate-limited, `GPUM_DOCS_OFFLINE` is set, or no
release carries a bundle asset: a block linking to the releases page, stating plainly that no
bundle download is currently available and directing the reader to the from-source route. The
build succeeds. A page that says "not available right now" is correct; a page with a dead link is
not.

### Guarantees

| Guarantee | Requirement |
|---|---|
| Exactly one place in the repository holds a site release version | FR-017, SC-015 |
| The download path resolves to a real asset, or says it cannot | FR-010, SC-005 |
| Pre-releases are never skipped | FR-010, SC-005 |
| No page hardcodes a version | FR-017 (asserted by A-11) |

## Failure and rollback semantics

| Failure | Behavior |
|---|---|
| Drift suite fails | `build` fails; no artifact; no deploy; previously published site unaffected (FR-037) |
| `mkdocs build --strict` fails | Same |
| Network link check or accessibility audit fails | Same — deploy is gated on the whole `build` job |
| Release API unreachable | Build **succeeds** in fallback state; the site deploys and tells the truth about the download |
| Deploy step itself fails | Previously published site remains live; the workflow run is red and visible in the Actions tab and on the commit (FR-037) |

Rollback is a revert plus the ordinary `main` push trigger. There is no separate rollback path,
and no build output lives in git history to untangle.

## Repository settings required (one-time, manual)

1. Settings → Pages → Source: **GitHub Actions**.
2. No branch protection changes; the workflow needs no write access to repository contents.

These are the only steps a maintainer performs by hand, and they are performed once. Everything
after that is FR-036's "no manual publishing step".

## Local equivalence

Every check that gates deployment is runnable locally with the commands in
[quickstart.md](../quickstart.md), including the offline fallback path. A contributor never has to
push to find out whether the site builds.
