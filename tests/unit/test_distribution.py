"""T007, T028: how the tool was delivered (data-model.md § DistributionForm).

The important assertion is E-08: no application module may branch on the packaging form.
FR-026 requires the two distribution forms to behave identically, and the reliable way to
guarantee that is to make the difference unobservable to application logic — not to test every
behaviour twice.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from gpum.distribution import DistributionForm, DistributionKind, detect

SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "gpum"

#: The only modules permitted to mention the packaging form.
_DIAGNOSTIC_MODULES = {"distribution.py", "__main__.py"}


class TestDetection:
    def test_detect_returns_a_form(self) -> None:
        form = detect()
        assert isinstance(form, DistributionForm)
        assert form.kind in set(DistributionKind)

    def test_version_is_always_present(self) -> None:
        assert detect().version

    def test_source_checkout_detected_when_not_frozen(self) -> None:
        form = detect()
        assert form.kind in {DistributionKind.SOURCE, DistributionKind.PACKAGE}
        assert form.bundle_root is None

    def test_bundle_root_only_set_for_bundles(self) -> None:
        form = detect()
        if form.kind is not DistributionKind.BUNDLE:
            assert form.bundle_root is None

    def test_detection_never_raises(self) -> None:
        for _ in range(3):
            detect()


class TestNoBehaviouralBranching:
    """E-08 — the structural guard behind FR-026."""

    @pytest.mark.parametrize(
        "path",
        [p for p in sorted(SRC.rglob("*.py")) if p.name not in _DIAGNOSTIC_MODULES],
        ids=lambda p: str(p.name),
    )
    def test_no_module_branches_on_packaging_form(self, path: pathlib.Path) -> None:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in {
                "BUNDLE",
                "PACKAGE",
                "SOURCE",
            }:
                pytest.fail(
                    f"{path.name} references DistributionKind.{node.attr}; application "
                    "behaviour must not depend on how the tool was packaged (FR-026)"
                )

    def test_frozen_marker_checked_in_exactly_one_place(self) -> None:
        """`sys.frozen` is how a bundle is recognised; scattering that check is how the two
        forms drift apart.

        Matched precisely rather than by substring — `@dataclass(frozen=True)` is everywhere
        in this codebase and has nothing to do with packaging.
        """
        offenders = []
        for path in SRC.rglob("*.py"):
            if path.name == "distribution.py":
                continue
            text = path.read_text()
            if "sys.frozen" in text or 'sys, "frozen"' in text or "sys, 'frozen'" in text:
                offenders.append(path.name)
        assert not offenders, f"sys.frozen checked outside distribution.py: {offenders}"
