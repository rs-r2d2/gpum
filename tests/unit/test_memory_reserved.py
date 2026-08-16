"""Regression: driver-reserved memory must not be reported as used.

Found by the feature 002 comparison harness on a real RTX 5060 Ti: NVML's v1 memory struct
reports `used = total - free`, which folds in driver-reserved memory. On an idle card that was
1021 MiB "used" against nvidia-smi's 550 MiB — nearly double, and users would rightly call it
wrong. nvidia-smi reports the v2 figure, which separates `reserved`.
"""

from __future__ import annotations

from types import SimpleNamespace

from gpum.backends.nvidia.nvml import NvmlLibrary

MIB = 1024 * 1024


class _V1Only:
    """An older driver: only the v1 struct exists."""

    def nvmlDeviceGetMemoryInfo(self, handle, **kwargs):  # noqa: N802
        if kwargs:
            raise TypeError("v2 not supported by this driver")
        return SimpleNamespace(total=16311 * MIB, used=1021 * MIB, free=15290 * MIB)


class _V2Capable:
    """A current driver: v2 separates reserved from used."""

    nvmlMemory_v2 = 0x02000028

    def nvmlDeviceGetMemoryInfo(self, handle, version=None):  # noqa: N802
        if version is None:
            return SimpleNamespace(total=16311 * MIB, used=1021 * MIB, free=15290 * MIB)
        return SimpleNamespace(
            total=16311 * MIB, used=550 * MIB, free=15290 * MIB, reserved=471 * MIB
        )


def _library(stub: object) -> NvmlLibrary:
    lib = NvmlLibrary()
    lib._nvml = stub
    lib._initialised = True
    return lib


class TestReservedMemoryExcluded:
    def test_v2_used_excludes_reserved(self) -> None:
        total, used, reserved = _library(_V2Capable()).memory_info(object())
        assert used == 550 * MIB, "used must match what nvidia-smi reports"
        assert reserved == 471 * MIB
        assert total == 16311 * MIB

    def test_v2_is_preferred_over_v1(self) -> None:
        _, used, _ = _library(_V2Capable()).memory_info(object())
        assert used != 1021 * MIB, "the v1 figure was used despite v2 being available"

    def test_v1_fallback_still_works(self) -> None:
        """Older drivers must keep working, reporting reserved as unknown rather than failing."""
        total, used, reserved = _library(_V1Only()).memory_info(object())
        assert total == 16311 * MIB
        assert used == 1021 * MIB
        assert reserved is None

    def test_used_never_exceeds_total(self) -> None:
        for stub in (_V1Only(), _V2Capable()):
            total, used, _ = _library(stub).memory_info(object())
            assert used <= total
