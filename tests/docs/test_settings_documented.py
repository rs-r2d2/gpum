"""A-03: every setting's choices and defaults are documented, and match the application."""

from __future__ import annotations

import ast

import pytest

from gpum.core.preferences import Preferences
from tests.docs.conftest import DOCS, repo_root

CONTROLS_PAGE = DOCS / "usage" / "controls.md"
DIALOG = repo_root() / "src" / "gpum" / "ui" / "settings_dialog.py"


def _labelled_choices(name: str) -> list[str]:
    """The human-readable labels of a ``[(label, value), ...]`` module constant."""
    tree = ast.parse(DIALOG.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return [
                e.elts[0].value
                for e in node.value.elts
                if isinstance(e, ast.Tuple) and isinstance(e.elts[0], ast.Constant)
            ]
    raise AssertionError(f"{name} is no longer defined in {DIALOG.name}")


INTERVALS = _labelled_choices("_INTERVALS")
WINDOWS = _labelled_choices("_WINDOWS")


@pytest.mark.parametrize("label", INTERVALS)
def test_refresh_interval_choice_is_documented(label):
    assert label in CONTROLS_PAGE.read_text(), f"refresh choice {label!r} is undocumented"


@pytest.mark.parametrize("label", WINDOWS)
def test_history_window_choice_is_documented(label):
    assert label in CONTROLS_PAGE.read_text(), f"history choice {label!r} is undocumented"


def test_documented_defaults_match_preferences():
    """Defaults are read from ``Preferences``; a page saying otherwise is simply wrong."""
    page = CONTROLS_PAGE.read_text()
    defaults = Preferences()

    seconds = defaults.refresh_interval_ms / 1000
    interval_label = f"{seconds:g} s"
    assert interval_label in page, f"the default refresh interval is {interval_label}"

    minutes = defaults.history_window_s // 60
    assert f"{minutes} minute" in page, f"the default history window is {minutes} minutes"

    for flag, phrase in (
        (defaults.throttle_when_hidden, "slow updates while the window is hidden"),
        (defaults.tray_enabled, "status area"),
    ):
        assert phrase.lower() in page.lower()
        assert flag is True, (
            f"{phrase!r} no longer defaults to on; the documented default must follow"
        )
    assert defaults.start_hidden is False


def test_every_toolbar_control_is_documented():
    page = CONTROLS_PAGE.read_text().lower()
    for control in ("refresh", "pause", "refresh now", "settings"):
        assert control in page, f"toolbar control {control!r} is undocumented"
