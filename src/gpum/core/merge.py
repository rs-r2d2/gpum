"""Join attribution results with process identity (contracts/process-attribution.md).

The rule this module exists to enforce: a process is never dropped for being unidentifiable.
Dropping one would understate GPU use, which is the failure FR-031 and SC-012 exist to
prevent.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import replace

from gpum.core.models import GpuProcess, PidKey, ProcessIdentity

__all__ = ["merge"]

_log = logging.getLogger(__name__)


def merge(result: object, *, identity_provider: object | None = None) -> Sequence[GpuProcess]:
    """Attach identity to attributed PIDs, leaving unresolvable ones in place."""
    processes: list[GpuProcess] = list(getattr(result, "processes", ()) or ())
    if identity_provider is None or not processes:
        return processes

    keys = [PidKey(p.pid, p.started_at) for p in processes]
    try:
        identities = identity_provider.identify(keys)  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001 - identity failure must not lose the memory figure
        _log.warning("identity resolution failed, keeping unresolved processes: %s", exc)
        return processes

    merged: list[GpuProcess] = []
    for process in processes:
        info = identities.get(PidKey(process.pid, process.started_at))
        if info is None:
            merged.append(process)
            continue
        merged.append(
            replace(
                process,
                name=info.name or process.name,
                executable=info.executable or process.executable,
                username=info.username or process.username,
                container_id=info.container_id or process.container_id,
                identity_state=_state(info, process),
            )
        )
    return merged


def _state(info: object, process: GpuProcess) -> ProcessIdentity:
    state = getattr(info, "identity_state", ProcessIdentity.UNRESOLVED)
    if state is ProcessIdentity.UNRESOLVED and process.name:
        return ProcessIdentity.RESOLVED
    return state
