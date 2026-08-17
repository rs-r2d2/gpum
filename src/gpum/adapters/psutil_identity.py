"""PID → identity via ``psutil``, shared by every platform that has it (contract A-05, A-06,
A-10, A-12).

**Why this is a separate module rather than part of the Linux adapter**: everything identity
needs — name, executable, owner, start time — ``psutil`` supplies without any OS knowledge. The
only genuinely platform-specific part is container membership, a Linux cgroup concept, so it is
injected rather than branched on. Linux is currently the only caller; keeping the split means a
future platform reuses the recycled-PID guard below instead of growing a second copy of it,
which is what Principle II's ban on per-platform forks exists to prevent.

GPU memory never comes from here — only the identity layered onto a PID some GPU source already
reported.
"""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Callable, Mapping, Sequence

import psutil

from gpum.core.attribution import ProcessIdentityInfo
from gpum.core.models import PidKey, ProcessIdentity

__all__ = ["PsutilIdentityProvider"]

_log = logging.getLogger(__name__)

#: How far a process's observed start time may differ from the one recorded at attribution
#: before the PID is treated as recycled.
_RECYCLE_TOLERANCE_S = 2


class PsutilIdentityProvider:
    """Identity for a batch of PIDs.

    ``container_resolver`` maps a PID to a container id, or is ``None`` on platforms where the
    concept does not apply.
    """

    def __init__(
        self,
        name: str,
        container_resolver: Callable[[int], str | None] | None = None,
    ) -> None:
        self.name = name
        self._container_for = container_resolver

    def identify(self, pids: Sequence[PidKey]) -> Mapping[PidKey, ProcessIdentityInfo]:
        """One batch call — a per-PID call at 1 Hz across hundreds of processes would be a
        measurable load on the machine being measured."""
        return {key: self._identify_one(key) for key in pids}

    def _identify_one(self, key: PidKey) -> ProcessIdentityInfo:
        try:
            proc = psutil.Process(key.pid)
            with proc.oneshot():
                name = proc.name()
                started = dt.datetime.fromtimestamp(proc.create_time(), tz=dt.UTC)
                if (
                    key.started_at is not None
                    and abs((started - key.started_at).total_seconds()) > _RECYCLE_TOLERANCE_S
                ):
                    # The PID was recycled between attribution and identification; naming it
                    # would attribute one process's memory to another (research D-05).
                    return ProcessIdentityInfo(identity_state=ProcessIdentity.UNRESOLVED)
                executable = _try(proc.exe)
                username = _try(proc.username)
        except psutil.NoSuchProcess:
            # Expected: processes exit between the GPU query and this lookup.
            return ProcessIdentityInfo(identity_state=ProcessIdentity.UNRESOLVED)
        except psutil.AccessDenied:
            return ProcessIdentityInfo(identity_state=ProcessIdentity.RESTRICTED)
        except Exception:  # noqa: BLE001 - identity failure must never lose the memory figure
            _log.debug("identity lookup failed for pid %s", key.pid, exc_info=True)
            return ProcessIdentityInfo(identity_state=ProcessIdentity.UNRESOLVED)

        container = self._container_for(key.pid) if self._container_for else None
        return ProcessIdentityInfo(
            name=name,
            executable=executable,
            username=username,
            container_id=container,
            identity_state=(
                ProcessIdentity.CONTAINERIZED if container else ProcessIdentity.RESOLVED
            ),
        )


def _try(getter: object) -> str | None:
    try:
        return str(getter())  # type: ignore[operator]
    except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
        return None
