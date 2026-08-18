"""A-12: external links and the live download URL actually resolve.

Marked ``network`` and deselected by default, following the repository's existing convention for
checks that cannot pass on an arbitrary machine (``hardware``, ``packaging``). CI runs it.
"""

from __future__ import annotations

import urllib.error
import urllib.request

import pytest

from tests.docs.conftest import all_pages, links
from tools import gen_release_snippet as gen

pytestmark = pytest.mark.network

TIMEOUT_S = 20


def _external_targets() -> list[tuple[str, str]]:
    seen: dict[str, str] = {}
    for pg in all_pages():
        for link in links(pg):
            if link.kind in {"external", "repository"}:
                seen.setdefault(link.path_part, pg.rel)
    return sorted((url, page) for url, page in seen.items())


def _head(url: str) -> int:
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": "gpum-docs-check"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
        return response.status


@pytest.mark.parametrize("url,page", _external_targets(), ids=[u for u, _ in _external_targets()])
def test_external_link_resolves(url, page):
    try:
        status = _head(url)
    except urllib.error.HTTPError as exc:  # pragma: no cover - network dependent
        pytest.fail(f"{page} links to {url}, which answered {exc.code}")
    except urllib.error.URLError as exc:  # pragma: no cover - network dependent
        pytest.fail(f"{page} links to {url}, which could not be reached ({exc.reason})")
    assert status < 400


def test_the_generated_download_url_is_downloadable():
    """SC-005: the one link whose failure costs a first-time visitor the whole product."""
    selection = gen.select(gen.fetch_releases())
    if selection is None:
        pytest.skip("no published release currently carries a bundle asset")
    request = urllib.request.Request(
        selection.asset_url, method="GET", headers={"User-Agent": "gpum-docs-check"}
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
        assert response.status == 200
        assert response.read(4), "the download URL resolved but returned no content"
