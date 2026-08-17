"""PID → identity on Windows (contract A-05, A-06, A-10, A-12).

`gpum.adapters.__init__` has selected this module on Windows since feature 001, but it did not
exist — so `platform_identity_provider()` raised `ModuleNotFoundError`, and because
`ui/app.py` calls it unguarded during startup, **GPUM could not launch on Windows at all**.
Found while implementing feature 007; the Windows column of the capability matrix could not
have been true.

The lookup is the shared `psutil` one. Nothing here is Windows-specific except the absence of
container membership: Windows containers are not the cgroup concept the Linux resolver reads,
so no resolver is supplied and processes report as ordinary rather than as containerized —
a smaller claim rather than a wrong one.
"""

from __future__ import annotations

from gpum.adapters.psutil_identity import PsutilIdentityProvider

__all__ = ["WindowsIdentityProvider"]


class WindowsIdentityProvider(PsutilIdentityProvider):
    def __init__(self) -> None:
        super().__init__(name="windows/psutil")
