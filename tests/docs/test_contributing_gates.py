"""T039: the documented quality gates are the ones that actually run.

A contributing page describing a check that no longer exists wastes the time of exactly the
person the project most wants to keep.
"""

from __future__ import annotations

import re

import pytest

from tests.docs.conftest import DOCS, read_source

GATES_PAGE = DOCS / "contributing" / "quality-gates.md"
SETUP_PAGE = DOCS / "contributing" / "development.md"


def _ci_commands() -> str:
    return read_source(".github/workflows/ci.yml") + read_source(".github/workflows/docs.yml")


@pytest.mark.parametrize(
    "command",
    ["ruff check", "mypy", "pytest"],
    ids=["lint", "typecheck", "tests"],
)
def test_documented_gate_runs_in_ci(command):
    """Every gate the page names must appear in a workflow, and vice versa."""
    page = GATES_PAGE.read_text()
    assert command in page, f"{command!r} gates merges but is not documented"
    assert command in _ci_commands(), f"the page documents {command!r}, which CI no longer runs"


@pytest.mark.parametrize("marker", ["hardware", "packaging", "network"])
def test_declared_pytest_markers_are_documented(marker):
    """A deselected-by-default suite that nobody knows about may as well not exist."""
    declared = re.findall(r'^\s*"(\w+):', read_source("pyproject.toml"), re.MULTILINE)
    assert marker in declared, f"marker {marker!r} is no longer declared in pyproject.toml"
    text = GATES_PAGE.read_text() + SETUP_PAGE.read_text()
    assert f"-m {marker}" in text, f"marker {marker!r} is undocumented"


def test_import_boundary_failure_is_explained_as_a_principle_violation():
    """The single most misread failure in this repository."""
    page = GATES_PAGE.read_text()
    assert "test_import_boundaries" in page
    assert re.search(r"never relax|do not relax|don't relax", page, re.IGNORECASE), (
        "the page must say the response to a boundary failure is fixing the import"
    )


def test_setup_states_the_suite_passes_without_a_gpu():
    """The claim that makes contributing possible for people without the hardware."""
    page = SETUP_PAGE.read_text().lower()
    assert "no gpu" in page or "without a gpu" in page


def test_scope_page_states_the_platform_boundary():
    scope = (DOCS / "contributing" / "scope.md").read_text()
    assert "Linux" in scope
    assert re.search(r"not supported|no claim|not planned", scope, re.IGNORECASE)


def test_contributing_index_explains_how_to_report_a_problem():
    index = (DOCS / "contributing" / "index.md").read_text()
    assert "issues" in index.lower()
    assert re.search(r"include|report", index, re.IGNORECASE)
