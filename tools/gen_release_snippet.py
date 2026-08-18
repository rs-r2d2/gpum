"""Generate the download block for the documentation site (spec 007, contracts/publishing.md).

Why this script exists at all: every GPUM release published so far is marked *pre-release*, and
GitHub's ``/releases/latest/`` deliberately skips pre-releases and answers 404. A hand-written or
"latest"-shaped download link on the site would therefore be dead in the project's *normal*
condition, not an unusual one. So the site asks for the full release list and chooses for itself.

Two rules are load-bearing:

* a URL that did not come back from the API is never printed — no download URL is ever built
  from a pattern;
* an unreachable API is not a build failure. The page falls back to the releases page and says
  plainly that no bundle is currently offered, which is true, rather than showing a dead link.
"""

from __future__ import annotations

import dataclasses
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

API = "https://api.github.com/repos/rs-r2d2/gpum/releases"
RELEASES_PAGE = "https://github.com/rs-r2d2/gpum/releases"
BUNDLE_SUFFIX = ".AppImage"
TIMEOUT_S = 10

DEFAULT_OUTPUT = pathlib.Path(__file__).resolve().parents[1] / "docs" / "_snippets" / "release.md"


@dataclasses.dataclass(frozen=True)
class Selection:
    """The release the download instructions will point at."""

    tag: str
    version: str
    asset_name: str
    asset_url: str
    is_prerelease: bool
    html_url: str


def fetch_releases() -> list[dict]:
    """Return the repository's releases, newest first. Raises on any transport problem."""
    request = urllib.request.Request(API, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        # Only ever used to raise the anonymous rate limit; no write scope is needed.
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
        return json.loads(response.read().decode("utf-8"))


def select(releases: list[dict]) -> Selection | None:
    """Pick the newest non-draft release carrying a bundle asset.

    Pre-releases are eligible on purpose. Drafts never are: they are not published.
    """
    candidates = sorted(
        (r for r in releases if not r.get("draft")),
        key=lambda r: r.get("published_at") or r.get("created_at") or "",
        reverse=True,
    )
    for release in candidates:
        for asset in release.get("assets", []):
            name = asset.get("name", "")
            if not name.endswith(BUNDLE_SUFFIX):
                continue
            tag = release.get("tag_name", "")
            return Selection(
                tag=tag,
                version=tag[1:] if tag.startswith("v") else tag,
                asset_name=name,
                asset_url=asset["browser_download_url"],
                is_prerelease=bool(release.get("prerelease")),
                html_url=release.get("html_url", RELEASES_PAGE),
            )
    return None


def render(selection: Selection | None) -> str:
    """Render the Markdown block that pages embed with ``pymdownx.snippets``."""
    if selection is None:
        return (
            "!!! warning \"No ready-to-run bundle is published right now\"\n\n"
            "    There is currently no bundle attached to a published release. Check the\n"
            f"    [releases page]({RELEASES_PAGE}) in case that has just changed, or install\n"
            "    from source with the steps further down this page — that route needs no\n"
            "    release at all.\n"
        )

    label = "pre-release" if selection.is_prerelease else "release"
    return (
        f"**Current {label}: [{selection.version}]({selection.html_url})** — "
        f"`{selection.asset_name}`\n\n"
        "```bash\n"
        f"curl -L -O {selection.asset_url}\n"
        f"chmod +x {selection.asset_name}\n"
        f"./{selection.asset_name}\n"
        "```\n"
    )


def generate(output: pathlib.Path = DEFAULT_OUTPUT) -> pathlib.Path:
    """Write the snippet, taking the fallback path rather than failing the build."""
    selection: Selection | None = None
    if os.environ.get("GPUM_DOCS_OFFLINE") not in {"1", "true", "yes"}:
        try:
            selection = select(fetch_releases())
        except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
            print(
                f"gen_release_snippet: falling back, releases unavailable ({exc})",
                file=sys.stderr,
            )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(selection), encoding="utf-8")
    return output


def main() -> int:
    path = generate()
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
