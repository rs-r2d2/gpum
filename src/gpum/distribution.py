"""How this instance was delivered — diagnostics only (research D-13, data-model.md).

**No behavioural code may branch on this.** FR-026 requires the package install and the
self-contained bundle to behave identically, and the reliable way to guarantee that is to make
the difference unobservable to application logic rather than to test every behaviour twice.
``tests/unit/test_distribution.py`` enforces it: only this module and ``__main__.py`` may
mention the packaging form, and only this module may check ``sys.frozen``.
"""

from __future__ import annotations

import enum
import sys
from dataclasses import dataclass
from functools import lru_cache

__all__ = ["DistributionForm", "DistributionKind", "detect", "version"]

_FALLBACK_VERSION = "0.0.0+unknown"


class DistributionKind(enum.StrEnum):
    PACKAGE = "package"
    BUNDLE = "bundle"
    SOURCE = "source"


@dataclass(frozen=True, slots=True)
class DistributionForm:
    kind: DistributionKind
    version: str
    bundle_root: str | None = None

    def describe(self) -> str:
        return f"gpum {self.version} ({self.kind})"


def version() -> str:
    """The single source of version truth, shared by both distribution forms (FR-026)."""
    try:
        from importlib.metadata import PackageNotFoundError
        from importlib.metadata import version as _version
    except ImportError:  # pragma: no cover - stdlib since 3.8
        return _FALLBACK_VERSION
    try:
        return _version("gpum")
    except PackageNotFoundError:
        return _FALLBACK_VERSION


@lru_cache(maxsize=1)
def detect() -> DistributionForm:
    """Determine how this instance was delivered. Never raises."""
    # The only `sys.frozen` check in the codebase, by design.
    if getattr(sys, "frozen", False):
        root = getattr(sys, "_MEIPASS", None)
        return DistributionForm(
            kind=DistributionKind.BUNDLE,
            version=version(),
            bundle_root=str(root) if root else None,
        )

    resolved = version()
    kind = (
        DistributionKind.SOURCE if resolved == _FALLBACK_VERSION else DistributionKind.PACKAGE
    )
    return DistributionForm(kind=kind, version=resolved)
