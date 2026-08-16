"""T053: merging identity into attribution never loses a process (FR-031, SC-012)."""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping, Sequence

from gpum.core.attribution import AttributionResult, ProcessIdentityInfo
from gpum.core.merge import merge
from gpum.core.models import GpuProcess, MetricValue, PidKey, ProcessIdentity


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _result(*processes: GpuProcess) -> AttributionResult:
    return AttributionResult(processes=processes)


class Identities:
    def __init__(self, mapping: Mapping[int, ProcessIdentityInfo]) -> None:
        self._mapping = mapping

    def identify(self, pids: Sequence[PidKey]) -> Mapping[PidKey, ProcessIdentityInfo]:
        return {
            key: self._mapping.get(key.pid, ProcessIdentityInfo()) for key in pids
        }


class Exploding:
    def identify(self, pids: Sequence[PidKey]) -> Mapping[PidKey, ProcessIdentityInfo]:
        raise RuntimeError("identity service unavailable")


class TestMerge:
    def test_identity_is_attached(self) -> None:
        result = _result(GpuProcess(pid=1, device_key="a"))
        merged = merge(
            result,
            identity_provider=Identities(
                {1: ProcessIdentityInfo(name="python", identity_state=ProcessIdentity.RESOLVED)}
            ),
        )
        assert merged[0].name == "python"

    def test_unidentifiable_process_is_kept_with_its_memory(self) -> None:
        """FR-031: never drop what you cannot name."""
        result = _result(
            GpuProcess(
                pid=7,
                device_key="a",
                memory_used=MetricValue.available(4096, sampled_at=_now()),
            )
        )
        merged = merge(result, identity_provider=Identities({}))
        assert len(merged) == 1
        assert merged[0].memory_used.value == 4096
        assert merged[0].identity_state is ProcessIdentity.UNRESOLVED

    def test_identity_failure_does_not_lose_processes(self) -> None:
        """A broken identity source must degrade to unnamed processes, not to no processes —
        otherwise device totals would silently disagree with the process list."""
        result = _result(
            GpuProcess(
                pid=7,
                device_key="a",
                memory_used=MetricValue.available(4096, sampled_at=_now()),
            )
        )
        merged = merge(result, identity_provider=Exploding())
        assert len(merged) == 1
        assert merged[0].memory_used.value == 4096

    def test_no_identity_provider_returns_processes_unchanged(self) -> None:
        result = _result(GpuProcess(pid=7, device_key="a"))
        assert len(merge(result, identity_provider=None)) == 1

    def test_restricted_state_is_preserved(self) -> None:
        result = _result(GpuProcess(pid=9, device_key="a"))
        merged = merge(
            result,
            identity_provider=Identities(
                {9: ProcessIdentityInfo(identity_state=ProcessIdentity.RESTRICTED)}
            ),
        )
        assert merged[0].identity_state is ProcessIdentity.RESTRICTED

    def test_container_id_is_carried_through(self) -> None:
        result = _result(GpuProcess(pid=3, device_key="a"))
        merged = merge(
            result,
            identity_provider=Identities(
                {
                    3: ProcessIdentityInfo(
                        name="train.py",
                        container_id="abc123",
                        identity_state=ProcessIdentity.CONTAINERIZED,
                    )
                }
            ),
        )
        assert merged[0].container_id == "abc123"
        assert merged[0].identity_state is ProcessIdentity.CONTAINERIZED
