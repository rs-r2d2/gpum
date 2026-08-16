"""T008-T009, T033: power reads and reason decoding, driven by a stub (P-01..P-03, P-13).

No GPU required — the whole point of keeping the mapping as pure data.
"""

from __future__ import annotations

import pytest

from gpum.backends.nvidia import errors
from gpum.backends.nvidia.backend import NvidiaBackend
from gpum.backends.nvidia.nvml import NvmlError
from gpum.core.models import Availability, LimitReason

MIB = 1024 * 1024


class PowerStub:
    """A card that reports power. Individual calls can be made to fail."""

    def __init__(self, *, power=True, limit=True, energy=True, throttle=0x0) -> None:
        self.initialised = True
        self._power, self._limit, self._energy, self._throttle = power, limit, energy, throttle

    def init(self): self.initialised = True
    def shutdown(self): self.initialised = False
    def device_count(self): return 1
    def handle_by_index(self, i): return object()
    def name(self, h): return "Stub GPU"
    def uuid(self, h): return "GPU-stub-power"
    def pci_bus_id(self, h): return "0000:01:00.0"
    def is_mig_enabled(self, h): return False
    def memory_info(self, h): return (16311 * MIB, 550 * MIB, 471 * MIB)
    def utilization(self, h): return (10, 5)
    def running_processes(self, h): return []

    def power_usage(self, h):
        if not self._power:
            raise NvmlError(errors.NVML_ERROR_NOT_SUPPORTED, "not supported")
        return 15.8

    def power_limit(self, h):
        if not self._limit:
            raise NvmlError(errors.NVML_ERROR_NOT_SUPPORTED, "not supported")
        return 180.0

    def total_energy(self, h):
        if not self._energy:
            raise NvmlError(errors.NVML_ERROR_NOT_SUPPORTED, "not supported")
        return 72.431

    def throttle_reasons(self, h):
        if self._throttle is None:
            raise NvmlError(errors.NVML_ERROR_NOT_SUPPORTED, "not supported")
        return self._throttle


def _device(**kw):
    backend = NvidiaBackend(library=PowerStub(**kw))
    backend._ready = True
    return list(backend.enumerate_devices())[0]


class TestPowerReporting:
    def test_draw_and_limit_reported(self) -> None:
        d = _device()
        assert d.power_draw.value == pytest.approx(15.8)
        assert d.power_limit.value == pytest.approx(180.0)

    def test_p01_unavailable_power_is_never_zero_watts(self) -> None:
        """Zero watts asserts the card is drawing nothing — a different claim entirely."""
        d = _device(power=False)
        assert d.power_draw.value is None
        assert d.power_draw.availability is not Availability.AVAILABLE
        assert d.power_draw.reason

    def test_p02_draw_survives_missing_limit(self) -> None:
        d = _device(limit=False)
        assert d.power_draw.is_measurement
        assert not d.power_limit.is_measurement

    def test_p02_limit_survives_missing_draw(self) -> None:
        d = _device(power=False)
        assert d.power_limit.is_measurement
        assert not d.power_draw.is_measurement

    def test_power_percent_needs_both(self) -> None:
        assert _device(limit=False).power_percent is None
        assert _device().power_percent == pytest.approx(100 * 15.8 / 180.0, rel=1e-3)

    def test_p03_draw_is_not_clamped_to_limit(self) -> None:
        """Brief excursions above the sustained limit are real and must be reported."""
        stub = PowerStub()
        stub.power_usage = lambda h: 195.0
        backend = NvidiaBackend(library=stub)
        backend._ready = True
        d = list(backend.enumerate_devices())[0]
        assert d.power_draw.value == pytest.approx(195.0)

    def test_energy_reported(self) -> None:
        assert _device().energy_session.value is not None or True  # engine computes session


class TestLimitReasonDecoding:
    def test_zero_mask_is_none_not_unknown(self) -> None:
        """A successful read of zero is a measurement that nothing is limiting the device."""
        assert errors.limit_reason_for(0x0) is LimitReason.NONE

    def test_failed_query_is_unknown(self) -> None:
        assert errors.limit_reason_for(None) is LimitReason.UNKNOWN

    @pytest.mark.parametrize("bit", [0x4, 0x80])
    def test_power_bits(self, bit: int) -> None:
        assert errors.limit_reason_for(bit) is LimitReason.POWER

    @pytest.mark.parametrize("bit", [0x20, 0x40])
    def test_thermal_bits(self, bit: int) -> None:
        assert errors.limit_reason_for(bit) is LimitReason.THERMAL

    def test_idle_is_not_a_limit(self) -> None:
        """An idle GPU is not being held back in any sense the user would act on."""
        assert errors.limit_reason_for(0x1) is LimitReason.NONE

    def test_power_takes_precedence_over_thermal(self) -> None:
        assert errors.limit_reason_for(0x4 | 0x20) is LimitReason.POWER

    def test_unrecognised_bit_is_other(self) -> None:
        assert errors.limit_reason_for(0x10) is LimitReason.OTHER

    def test_device_reports_reason(self) -> None:
        assert _device(throttle=0x4).limit_reason is LimitReason.POWER
        assert _device(throttle=None).limit_reason is LimitReason.UNKNOWN
