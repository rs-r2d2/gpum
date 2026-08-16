"""Fallback identity provider for platforms without an adapter.

Returns UNRESOLVED for everything rather than raising: a process whose name we cannot obtain
is still counted in device totals (FR-031).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from gpum.core.attribution import ProcessIdentityInfo
from gpum.core.models import PidKey, ProcessIdentity

__all__ = ["NullIdentityProvider"]


class NullIdentityProvider:
    name = "none"

    def identify(self, pids: Sequence[PidKey]) -> Mapping[PidKey, ProcessIdentityInfo]:
        return {key: ProcessIdentityInfo(identity_state=ProcessIdentity.UNRESOLVED) for key in pids}
