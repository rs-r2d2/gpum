"""PID → identity on Linux (contract A-05, A-06, A-10, A-12).

``psutil`` supplies name, executable, and owner; GPU memory never comes from here — only the
identity layered onto a PID some GPU source already reported.

The lookup itself lives in `gpum.adapters.psutil_identity`, which needs no OS knowledge. What is
Linux about identity is container membership, which is supplied here as the resolver.
"""

from __future__ import annotations

from gpum.adapters.linux.containers import container_id_for_pid
from gpum.adapters.psutil_identity import PsutilIdentityProvider

__all__ = ["LinuxIdentityProvider"]


class LinuxIdentityProvider(PsutilIdentityProvider):
    def __init__(self) -> None:
        super().__init__(name="linux/psutil", container_resolver=container_id_for_pid)
