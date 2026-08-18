"""A-09: the published site must not make the reader's browser talk to anyone else.

GPUM's headline promise is that it never phones home. A website for it that pulls a webfont from
a CDN, or asks an API for star counts on every page load, would quietly break that promise on the
reader's behalf — and would do it in the one place a prospective user goes to decide whether the
promise is credible.

Scope note, stated rather than hidden: Material's bundled JavaScript contains two *conditional*
fallbacks — a ResizeObserver polyfill fetched only by browsers predating 2020, and a mermaid
loader that runs only on pages containing mermaid diagrams (this site contains none). Neither is
requested by a current browser on any page here. Everything a page loads unconditionally is
checked below.
"""

from __future__ import annotations

import html.parser
import pathlib
import re
import urllib.parse

import pytest

from tests.docs.conftest import repo_root

SITE = repo_root() / "site"

#: The site's own host. Requests to it are not third-party.
OWN_HOSTS = {"rs-r2d2.github.io"}

#: Attributes whose value the browser fetches without being asked.
FETCHED = {"src", "srcset", "poster", "data-src"}

pytestmark = pytest.mark.skipif(
    not SITE.exists(),
    reason="no built site; run `mkdocs build --strict` first (CI always does)",
)


class _ResourceCollector(html.parser.HTMLParser):
    """Collects URLs the browser would fetch, ignoring links the reader chooses to follow."""

    def __init__(self) -> None:
        super().__init__()
        self.resources: list[str] = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        for name, value in values.items():
            if not value:
                continue
            if name in FETCHED:
                self.resources.extend(v.split(" ")[0] for v in value.split(","))
            elif name == "href" and tag != "a":
                # <link rel=stylesheet|preconnect|icon> is fetched; <a href> is navigation.
                self.resources.append(value)


def _third_party(urls) -> list[str]:
    offenders = []
    for url in urls:
        parsed = urllib.parse.urlparse(url.strip())
        if not parsed.netloc or parsed.netloc in OWN_HOSTS:
            continue
        offenders.append(url.strip())
    return offenders


def _html_files() -> list[pathlib.Path]:
    return sorted(SITE.rglob("*.html"))


def test_the_site_was_actually_built():
    assert _html_files(), "no HTML found under site/"


@pytest.mark.parametrize("page", _html_files(), ids=lambda p: p.name)
def test_no_page_fetches_a_third_party_resource(page):
    collector = _ResourceCollector()
    collector.feed(page.read_text(encoding="utf-8"))
    offenders = _third_party(collector.resources)
    assert not offenders, f"{page.relative_to(SITE)} loads third-party resources: {offenders}"


def test_no_stylesheet_fetches_a_third_party_resource():
    for css in sorted(SITE.rglob("*.css")):
        urls = re.findall(r"url\(\s*['\"]?([^'\")]+)", css.read_text(encoding="utf-8"))
        offenders = _third_party(urls)
        assert not offenders, f"{css.relative_to(SITE)} loads {offenders}"


def test_no_webfont_is_requested():
    """The theme's default font setting fetches Google Fonts. It must stay disabled."""
    for page in _html_files():
        text = page.read_text(encoding="utf-8")
        for host in ("fonts.googleapis.com", "fonts.gstatic.com"):
            assert host not in text, f"{page.relative_to(SITE)} references {host}"


@pytest.mark.parametrize("page", _html_files(), ids=lambda p: p.name)
def test_no_page_asks_github_for_repository_facts(page):
    """Setting `repo_url` makes the theme fetch stars and forks from api.github.com on load.

    That is a third-party request made by every visitor, so the repository is linked in ordinary
    page content instead.
    """
    text = page.read_text(encoding="utf-8")
    assert 'data-md-component="source"' not in text, (
        f"{page.relative_to(SITE)} includes the repository-facts component, which calls "
        "api.github.com from the reader's browser"
    )
