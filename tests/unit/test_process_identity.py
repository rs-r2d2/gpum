"""T052: PID recycling must not misattribute memory (A-08, FR-008, research D-05)."""

from __future__ import annotations

import datetime as dt
import os

from gpum.adapters.linux.identity import LinuxIdentityProvider
from gpum.core.models import PidKey, ProcessIdentity


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class TestPidRecycling:
    def test_a_wrong_start_time_refuses_to_name_the_process(self) -> None:
        """The scenario: PID 4242 was attributed, exited, and a new process took the PID
        before identification ran. Naming it would attribute one process's GPU memory to
        another. Refusing is the only correct answer."""
        provider = LinuxIdentityProvider()
        stale_key = PidKey(os.getpid(), _now() - dt.timedelta(days=400))
        info = provider.identify([stale_key])[stale_key]
        assert info.identity_state is ProcessIdentity.UNRESOLVED
        assert info.name is None

    def test_the_matching_start_time_resolves(self) -> None:
        import psutil

        provider = LinuxIdentityProvider()
        started = dt.datetime.fromtimestamp(psutil.Process().create_time(), tz=dt.UTC)
        key = PidKey(os.getpid(), started)
        info = provider.identify([key])[key]
        assert info.identity_state in {
            ProcessIdentity.RESOLVED,
            ProcessIdentity.CONTAINERIZED,
        }
        assert info.name

    def test_no_start_time_still_resolves(self) -> None:
        """Attribution sources that cannot supply a start time are still usable."""
        provider = LinuxIdentityProvider()
        key = PidKey(os.getpid(), None)
        assert provider.identify([key])[key].name


class TestBatchContract:
    def test_a10_an_entry_for_every_key(self) -> None:
        provider = LinuxIdentityProvider()
        keys = [PidKey(os.getpid(), None), PidKey(999_999_998, None), PidKey(1, None)]
        assert set(provider.identify(keys)) == set(keys)

    def test_a06_dead_pid_does_not_raise(self) -> None:
        provider = LinuxIdentityProvider()
        key = PidKey(999_999_998, None)
        assert provider.identify([key])[key].identity_state is ProcessIdentity.UNRESOLVED
