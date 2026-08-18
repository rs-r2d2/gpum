"""A-01: every command-line option is documented.

Read from the parser definition rather than from a maintained list, so that renaming a flag or
adding a choice fails the contributor's own ``pytest`` run instead of leaving a stale page for a
reader to find months later.
"""

from __future__ import annotations

import ast

import pytest

from tests.docs.conftest import DOCS, repo_root

CLI_PAGE = DOCS / "reference" / "cli.md"
ENTRY_POINT = repo_root() / "src" / "gpum" / "__main__.py"


def _parser_options() -> list[tuple[str, list[str]]]:
    """Every ``add_argument`` flag and its choices, taken from the source."""
    tree = ast.parse(ENTRY_POINT.read_text())
    options: list[tuple[str, list[str]]] = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
        ):
            continue
        flags = [
            a.value
            for a in node.args
            if isinstance(a, ast.Constant) and isinstance(a.value, str)
        ]
        choices: list[str] = []
        for kw in node.keywords:
            if kw.arg == "choices" and isinstance(kw.value, (ast.List, ast.Tuple)):
                choices = [
                    e.value for e in kw.value.elts if isinstance(e, ast.Constant)
                ]
        for flag in flags:
            options.append((flag, choices))
    return options


OPTIONS = _parser_options()


def test_the_parser_was_actually_read():
    """A guard: an empty option list would make every assertion below vacuously true."""
    assert len(OPTIONS) >= 8, f"expected the full option set, parsed {OPTIONS}"


@pytest.mark.parametrize("flag,choices", OPTIONS, ids=[f for f, _ in OPTIONS])
def test_option_is_documented(flag, choices):
    page = CLI_PAGE.read_text()
    assert flag in page, f"{flag} is accepted by gpum but absent from {CLI_PAGE.name}"
    for choice in choices:
        assert choice in page, f"{flag} accepts {choice!r}, which {CLI_PAGE.name} does not mention"


def test_missing_display_behaviour_is_documented():
    """Exit behaviour is part of the contract with anyone scripting or packaging GPUM."""
    page = CLI_PAGE.read_text().lower()
    assert "graphical" in page and ("ssh" in page or "x11" in page)
