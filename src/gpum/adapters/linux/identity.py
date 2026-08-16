"""PID → identity on Linux (contract A-05, A-06, A-10, A-12).

``psutil`` supplies name, executable, and owner; GPU memory never comes from here — only the
identity layered onto a PID some GPU source already reported.
"""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Mapping, Sequence

import psutil

from gpum.adapters.linux.containers import container_id_for_pid
from gpum.core.attribution import ProcessIdentityInfo
from gpum.core.models import PidKey, ProcessIdentity

__all__ = ["LinuxIdentityProvider"]

_log = logging.getLogger(__name__)


class LinuxIdentityProvider:
    name = "linux/psutil"

    def identify(self, pids: Sequence[PidKey]) -> Mapping[PidKey, ProcessIdentityInfo]:
        """One batch call — a per-PID call at 1 Hz across hundreds of processes would be a
        measurable load on the machine being measured."""
        out: dict[PidKey, ProcessIdentityInfo] = {}
        for key in pids:
            out[key] = self._identify_one(key)
        return out

    def _identify_one(self, key: PidKey) -> ProcessIdentityInfo:
        try:
            proc = psutil.Process(key.pid)
            with proc.oneshot():
                name = proc.name()
                started = dt.datetime.fromtimestamp(proc.create_time(), tz=dt.UTC)
                if key.started_at is not None and abs(
                    (started - key.started_at).total_seconds()
                ) > 2:
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

        container = container_id_for_pid(key.pid)
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
