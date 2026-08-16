"""T008: the MetricValue invariant.

This is the mechanical guard behind SC-007 ("zero fabricated, zeroed, or estimated values are
presented as measurements"). If these tests pass, a backend physically cannot construct a
metric that claims to be a measurement without one.
"""

import dataclasses
import datetime as dt

import pytest

from gpum.core.models import (
    Availability,
    BackendReport,
    BackendState,
    DeviceId,
    GpuDevice,
    GpuProcess,
    MetricValue,
    PidKey,
    ProcessIdentity,
    Vendor,
)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class TestMetricValueInvariant:
    def test_available_metric_carries_a_value(self) -> None:
        m = MetricValue.available(1024, sampled_at=_now())
        assert m.value == 1024
        assert m.availability is Availability.AVAILABLE

    def test_available_metric_without_a_value_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="AVAILABLE"):
            MetricValue(value=None, availability=Availability.AVAILABLE, sampled_at=_now())

    @pytest.mark.parametrize(
        "state",
        [
            Availability.UNSUPPORTED,
            Availability.PERMISSION_DENIED,
            Availability.DEGRADED,
            Availability.NOT_APPLICABLE,
        ],
    )
    def test_unavailable_metric_must_not_carry_a_value(self, state: Availability) -> None:
        """The core of SC-007: an unavailable metric cannot smuggle a number through."""
        with pytest.raises(ValueError):
            MetricValue(value=0, availability=state, reason="nope")

    @pytest.mark.parametrize(
        "state",
        [
            Availability.UNSUPPORTED,
            Availability.PERMISSION_DENIED,
            Availability.DEGRADED,
        ],
    )
    def test_unavailable_metric_requires_a_reason(self, state: Availability) -> None:
        with pytest.raises(ValueError, match="reason"):
            MetricValue(value=None, availability=state, reason=None)

    def test_stale_metric_may_keep_its_previous_value_and_original_timestamp(self) -> None:
        """STALE is the one non-AVAILABLE state that legitimately carries a value: the last
        real measurement, shown with its true age (FR-016)."""
        then = _now() - dt.timedelta(seconds=30)
        m = MetricValue.stale(2048, sampled_at=then, reason="query timed out")
        assert m.value == 2048
        assert m.availability is Availability.STALE
        assert m.sampled_at == then

    def test_unsupported_helper_produces_no_value(self) -> None:
        m = MetricValue.unsupported("not reported under WDDM")
        assert m.value is None
        assert m.reason

    def test_is_measurement_only_true_for_available(self) -> None:
        assert MetricValue.available(1, sampled_at=_now()).is_measurement
        assert not MetricValue.unsupported("x").is_measurement
        assert not MetricValue.stale(1, sampled_at=_now(), reason="x").is_measurement

    def test_metric_is_immutable(self) -> None:
        m = MetricValue.unsupported("x")
        with pytest.raises((AttributeError, TypeError, dataclasses.FrozenInstanceError)):
            m.value = 5  # type: ignore[misc]


class TestDeviceId:
    def test_key_is_identity_not_index(self) -> None:
        a = DeviceId(vendor=Vendor.NVIDIA, key="GPU-uuid-1", index=0)
        b = DeviceId(vendor=Vendor.NVIDIA, key="GPU-uuid-1", index=3)
        assert a == b, "index must not participate in identity (research D-07)"

    def test_different_keys_are_different_devices(self) -> None:
        a = DeviceId(vendor=Vendor.NVIDIA, key="GPU-uuid-1", index=0)
        b = DeviceId(vendor=Vendor.NVIDIA, key="GPU-uuid-2", index=0)
        assert a != b


class TestGpuDevice:
    def test_unsupported_device_requires_a_reason(self) -> None:
        with pytest.raises(ValueError, match="reason"):
            GpuDevice(
                id=DeviceId(Vendor.NVIDIA, "k", 0),
                name="A100",
                supported=False,
                unsupported_reason=None,
            )

    def test_unsupported_device_exposes_no_metrics(self) -> None:
        d = GpuDevice(
            id=DeviceId(Vendor.NVIDIA, "k", 0),
            name="A100",
            supported=False,
            unsupported_reason="partitioned GPU (MIG) not supported",
        )
        assert not d.memory_total.is_measurement
        assert not d.memory_used.is_measurement

    def test_memory_percent_requires_both_operands_available(self) -> None:
        d = GpuDevice(
            id=DeviceId(Vendor.NVIDIA, "k", 0),
            name="RTX",
            memory_total=MetricValue.available(1000, sampled_at=_now()),
            memory_used=MetricValue.unsupported("nope"),
        )
        assert d.memory_percent is None

    def test_memory_percent_computed_when_both_available(self) -> None:
        d = GpuDevice(
            id=DeviceId(Vendor.NVIDIA, "k", 0),
            name="RTX",
            memory_total=MetricValue.available(1000, sampled_at=_now()),
            memory_used=MetricValue.available(250, sampled_at=_now()),
        )
        assert d.memory_percent == pytest.approx(25.0)

    def test_zero_total_does_not_divide_by_zero(self) -> None:
        d = GpuDevice(
            id=DeviceId(Vendor.NVIDIA, "k", 0),
            name="RTX",
            memory_total=MetricValue.available(0, sampled_at=_now()),
            memory_used=MetricValue.available(0, sampled_at=_now()),
        )
        assert d.memory_percent is None


class TestGpuProcess:
    def test_identity_key_includes_start_time(self) -> None:
        """PIDs are recycled; a bare PID would misattribute memory (research D-05)."""
        t = _now()
        p = GpuProcess(pid=42, started_at=t, device_key="k")
        assert p.identity_key == PidKey(42, t)

    def test_unresolved_process_still_carries_memory(self) -> None:
        """FR-031: never drop what you cannot name."""
        p = GpuProcess(
            pid=7,
            device_key="k",
            memory_used=MetricValue.available(2048, sampled_at=_now()),
            identity_state=ProcessIdentity.UNRESOLVED,
        )
        assert p.memory_used.value == 2048
        assert p.name is None


class TestBackendReport:
    def test_states_are_distinguishable(self) -> None:
        """SC-006 needs a specific message, so these must not collapse into one another."""
        assert BackendState.LIBRARY_MISSING is not BackendState.DRIVER_MISSING
        assert BackendState.DRIVER_MISSING is not BackendState.NO_DEVICES

    def test_report_requires_detail(self) -> None:
        with pytest.raises(ValueError):
            BackendReport(vendor=Vendor.AMD, state=BackendState.NOT_IMPLEMENTED, detail="")
