"""A-06, A-07, A-08: structural integrity of every site page.

A link that rots, an image nobody can describe, and a heading level that skips are three ways a
page degrades without the build ever noticing. See
``specs/007-github-pages-site/contracts/content-accuracy.md``.
"""

from __future__ import annotations

import pytest

from tests.docs.conftest import (
    BLOB_PREFIX,
    DOCS,
    all_pages,
    anchors,
    headings,
    images,
    links,
    nav_targets,
    repo_root,
)

PAGES = all_pages()
IDS = [p.rel for p in PAGES]


@pytest.mark.parametrize("pg", PAGES, ids=IDS)
def test_internal_links_resolve(pg):
    """A-06: every relative link points at a page that exists."""
    for link in links(pg):
        if link.kind != "internal":
            continue
        target = (pg.path.parent / link.path_part).resolve()
        assert target.exists(), f"{pg.rel}: link to missing target {link.target!r}"


@pytest.mark.parametrize("pg", PAGES, ids=IDS)
def test_link_anchors_resolve(pg):
    """A-06: every fragment points at a heading that exists in the target page."""
    for link in links(pg):
        if not link.anchor or link.kind in {"external", "repository"}:
            continue
        target_page = pg if link.kind == "anchor" else None
        if target_page is None:
            resolved = (pg.path.parent / link.path_part).resolve()
            if resolved.suffix != ".md" or not resolved.exists():
                continue
            target_page = type(pg)(resolved)
        assert link.anchor in anchors(target_page), (
            f"{pg.rel}: link {link.target!r} names no heading in {target_page.rel}"
        )


@pytest.mark.parametrize("pg", PAGES, ids=IDS)
def test_repository_links_exist_in_working_tree(pg):
    """A-06: a link to source is verified against the tree, not merely against a URL shape.

    This is what stops a reference to a moved module rotting silently, and it works offline.
    """
    for link in links(pg):
        if link.kind != "repository":
            continue
        rel = link.path_part[len(BLOB_PREFIX) :]
        assert (repo_root() / rel).exists(), (
            f"{pg.rel}: links to {rel!r}, which is not in the working tree"
        )


@pytest.mark.parametrize("pg", PAGES, ids=IDS)
def test_images_have_alt_text_and_exist(pg):
    """A-07: every image carries a text alternative and refers to a real file."""
    for alt, target in images(pg):
        assert alt.strip(), f"{pg.rel}: image {target!r} has no alt text"
        if target.startswith(("http://", "https://")):
            continue
        assert (pg.path.parent / target).resolve().exists(), (
            f"{pg.rel}: image file {target!r} is missing"
        )


@pytest.mark.parametrize("pg", PAGES, ids=IDS)
def test_heading_structure(pg):
    """A-08: one title per page, and no skipped levels."""
    found = headings(pg)
    tops = [t for level, t in found if level == 1]
    assert len(tops) == 1, f"{pg.rel}: expected exactly one top-level heading, found {tops}"
    previous = 1
    for level, title in found:
        assert level <= previous + 1, (
            f"{pg.rel}: heading {title!r} jumps from level {previous} to {level}"
        )
        previous = level


def test_every_page_is_reachable_from_nav():
    """A visitor arriving on any page can navigate; an orphan page has no way in."""
    listed = {t for t in nav_targets()}
    for pg in PAGES:
        rel = pg.path.relative_to(DOCS).as_posix()
        assert rel in listed, f"{pg.rel} is not listed in the mkdocs.yml nav"


def test_every_nav_entry_exists():
    for target in nav_targets():
        assert (DOCS / target).exists(), f"nav lists {target!r}, which does not exist"
