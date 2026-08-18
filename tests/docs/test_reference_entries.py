"""T031: the API reference covers what it must, and points at things that exist.

The reference is curated rather than generated, which buys clarity at the cost of a way to go
stale. These assertions are that cost being paid.
"""

from __future__ import annotations

import re

import pytest

from tests.docs.conftest import DOCS, Page, links, repo_root

REFERENCE = DOCS / "reference"

#: Required entries (data-model.md § ApiEntry, FR-024) and the source each must point at.
REQUIRED = {
    "index.md": None,
    "backend-interface.md": "src/gpum/backends/base.py",
    "data-model.md": "src/gpum/core/models.py",
    "registry.md": "src/gpum/registry.py",
    "adapters.md": "src/gpum/adapters/base.py",
    "cli.md": "src/gpum/__main__.py",
}


@pytest.mark.parametrize("name", sorted(REQUIRED), ids=sorted(REQUIRED))
def test_required_reference_entry_exists(name):
    assert (REFERENCE / name).exists(), f"the API reference is missing {name}"


@pytest.mark.parametrize(
    "name,source",
    [(n, s) for n, s in sorted(REQUIRED.items()) if s],
    ids=[n for n, s in sorted(REQUIRED.items()) if s],
)
def test_entry_points_at_its_authoritative_source(name, source):
    """FR-028: every entry links to source or to a design contract, and the target exists."""
    page = Page(REFERENCE / name)
    targets = [link.path_part for link in links(page) if link.kind == "repository"]
    named = [t for t in targets if source in t]
    assert named, f"{name} does not link to {source}, its authoritative source"
    assert (repo_root() / source).exists()


def test_reference_states_the_dependency_direction():
    """FR-026: the layering rule is the one thing an extender must not guess at."""
    index = (REFERENCE / "index.md").read_text()
    assert "backends" in index and "core" in index and "ui" in index
    assert re.search(r"core\b[^.\n]*must not[^.\n]*\bui\b", index, re.IGNORECASE), (
        "the reference must state that core may not import ui"
    )


def test_reference_declares_itself_curated_not_exhaustive():
    """FR-029: a reader must be able to tell this is a guide, not generated API coverage."""
    index = (REFERENCE / "index.md").read_text().lower()
    assert "not exhaustive" in index or "curated" in index


@pytest.mark.parametrize("name", sorted(REQUIRED), ids=sorted(REQUIRED))
def test_no_entry_describes_an_unavailable_metric_as_zero(name):
    """Principle I: substituting zero for a missing measurement is prohibited, and saying the
    documentation may not describe it as permitted is how that stays true."""
    text = (REFERENCE / name).read_text()
    offending = re.search(
        r"(?:return|report|use|substitut\w*|show)\w*\s+(?:a\s+)?(?:`0`|zero)\b"
        r"(?![^.\n]*(?:never|not|prohibit|must not|instead of))",
        text,
        re.IGNORECASE,
    )
    assert offending is None, f"{name}: {offending.group(0)!r} reads as permission to fake data"


def test_backend_interface_entry_covers_every_protocol_method():
    """A method an implementer must provide, absent from the page, is a trap."""
    source = (repo_root() / "src" / "gpum" / "backends" / "base.py").read_text()
    protocol = source.split("class GpuBackend", 1)[1]
    methods = set(re.findall(r"\n    def (\w+)\(", protocol))
    page = (REFERENCE / "backend-interface.md").read_text()
    for method in sorted(methods):
        assert f"{method}(" in page, f"GpuBackend.{method}() is undocumented"
