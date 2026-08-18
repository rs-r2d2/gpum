"""Shared helpers for the documentation drift suite (contracts/content-accuracy.md).

Everything here reads Markdown sources and the repository tree. Nothing imports MkDocs: the
suite must run for a contributor who installed only ``[dev]``, without the documentation
toolchain (research D-09).
"""

from __future__ import annotations

import dataclasses
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
DOCS = REPO / "docs"
MKDOCS_YML = REPO / "mkdocs.yml"

#: Where the site is published. Links to this host are internal, not third-party.
SITE_URL = "https://rs-r2d2.github.io/gpum/"

#: Repository links are written in this form so a page can link to source and the target can
#: still be verified offline, against the working tree, by stripping the prefix.
BLOB_PREFIX = "https://github.com/rs-r2d2/gpum/blob/main/"

_FENCE = re.compile(r"^(```|~~~)")
_SNIPPET_DIR = "_snippets"


def repo_root() -> pathlib.Path:
    return REPO


@dataclasses.dataclass(frozen=True)
class Page:
    """One authored or adopted Markdown page under ``docs/``."""

    path: pathlib.Path

    @property
    def rel(self) -> str:
        return self.path.relative_to(REPO).as_posix()

    @property
    def text(self) -> str:
        return self.path.read_text(encoding="utf-8")

    @property
    def prose(self) -> str:
        """The page with fenced code blocks removed.

        Links and headings inside a code sample are examples, not navigation, and checking them
        would fail on the first page that documents a command containing a URL.
        """
        out, in_fence = [], False
        for line in self.text.splitlines():
            if _FENCE.match(line.strip()):
                in_fence = not in_fence
                continue
            if not in_fence:
                out.append(line)
        return "\n".join(out)


def all_pages() -> list[Page]:
    """Every Markdown page that is part of the site, in a stable order."""
    return [
        Page(p)
        for p in sorted(DOCS.rglob("*.md"))
        if _SNIPPET_DIR not in p.relative_to(DOCS).parts
    ]


def page(rel_to_docs: str) -> Page:
    return Page(DOCS / rel_to_docs)


# --- parsing -----------------------------------------------------------------------------

_LINK = re.compile(r"(?<!!)\[(?P<text>[^\]]*)\]\((?P<target>[^)\s]+)(?:\s+\"[^\"]*\")?\)")
_IMAGE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<target>[^)\s]+)(?:\s+\"[^\"]*\")?\)")
_HEADING = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<title>.+?)\s*$")
_INLINE_CODE = re.compile(r"`([^`]+)`")


@dataclasses.dataclass(frozen=True)
class Link:
    text: str
    target: str

    @property
    def kind(self) -> str:
        if self.target.startswith(BLOB_PREFIX):
            return "repository"
        if self.target.startswith(("http://", "https://")):
            return "external"
        if self.target.startswith("#"):
            return "anchor"
        return "internal"

    @property
    def path_part(self) -> str:
        return self.target.split("#", 1)[0]

    @property
    def anchor(self) -> str:
        return self.target.split("#", 1)[1] if "#" in self.target else ""


def links(pg: Page) -> list[Link]:
    return [Link(m.group("text"), m.group("target")) for m in _LINK.finditer(pg.prose)]


def images(pg: Page) -> list[tuple[str, str]]:
    return [(m.group("alt"), m.group("target")) for m in _IMAGE.finditer(pg.text)]


def headings(pg: Page) -> list[tuple[int, str]]:
    found = []
    for line in pg.prose.splitlines():
        m = _HEADING.match(line)
        if m:
            found.append((len(m.group("hashes")), m.group("title")))
    return found


def inline_code(pg: Page) -> list[str]:
    return _INLINE_CODE.findall(pg.text)


def slugify(title: str) -> str:
    """Approximate python-markdown's ``toc`` slugify, which generates heading anchors."""
    text = re.sub(r"`([^`]*)`", r"\1", title)
    text = re.sub(r"\*\*?([^*]*)\*\*?", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


def anchors(pg: Page) -> set[str]:
    return {slugify(title) for _level, title in headings(pg)}


# --- navigation --------------------------------------------------------------------------


def nav_targets() -> list[str]:
    """Page paths listed in the ``nav:`` block of ``mkdocs.yml``.

    Parsed with a regex rather than a YAML loader so the suite keeps working without the
    documentation extra installed.
    """
    text = MKDOCS_YML.read_text(encoding="utf-8")
    nav = text.split("\nnav:", 1)[1] if "\nnav:" in text else ""
    return re.findall(r":\s*([\w./-]+\.md)\s*$", nav, flags=re.MULTILINE)


def read_source(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")
