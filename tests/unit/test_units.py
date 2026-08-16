"""T009: unit normalization (FR-004)."""

import datetime as dt

import pytest

from gpum.core import units
from gpum.core.models import MetricValue


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class TestFormatBytes:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (0, "0 MiB"),
            (1024 * 1024, "1 MiB"),
            (1536 * 1024 * 1024, "1.50 GiB"),
            (8 * 1024**3, "8.00 GiB"),
        ],
    )
    def test_binary_convention(self, value: int, expected: str) -> None:
        assert units.format_bytes(value) == expected

    def test_convention_is_stated_for_the_ui(self) -> None:
        """FR-004 requires the UI to state the convention, so it must come from one place."""
        assert units.UNIT_CONVENTION

    def test_negative_bytes_rejected(self) -> None:
        with pytest.raises(ValueError):
            units.format_bytes(-1)


class TestFormatMetric:
    def test_available_metric_formats_its_value(self) -> None:
        m = MetricValue.available(2 * 1024**3, sampled_at=_now())
        assert units.format_metric_bytes(m) == "2.00 GiB"

    def test_unavailable_metric_never_formats_as_a_number(self) -> None:
        """SC-007 at the formatting layer: refuse rather than emit '0'."""
        m = MetricValue.unsupported("not supported here")
        out = units.format_metric_bytes(m)
        assert "0" not in out
        assert out != ""

    def test_percent_of_unavailable_is_none(self) -> None:
        whole = MetricValue.available(10, sampled_at=_now())
        assert units.percent(MetricValue.unsupported("x"), whole) is None


class TestPowerFormatting:
    """T001: watts and watt-hours (FR-005, FR-024)."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [(0, "0.0 W"), (8.8, "8.8 W"), (15.75, "15.8 W"), (180, "180.0 W")],
    )
    def test_watts_one_decimal(self, value: float, expected: str) -> None:
        assert units.format_watts(value) == expected

    def test_negative_watts_rejected(self) -> None:
        with pytest.raises(ValueError):
            units.format_watts(-1)

    @pytest.mark.parametrize(
        ("value", "expected"),
        [(0.0721, "0.072 Wh"), (72.431, "72.431 Wh"), (1500, "1.500 kWh")],
    )
    def test_watt_hours_three_decimals(self, value: float, expected: str) -> None:
        assert units.format_watt_hours(value) == expected

    def test_short_session_does_not_round_to_zero(self) -> None:
        assert units.format_watt_hours(0.004) != "0.000 Wh"

    def test_unavailable_power_never_formats_as_zero_watts(self) -> None:
        """Zero watts asserts the card is off — a different claim from 'unreadable'."""
        out = units.format_metric_watts(MetricValue.unsupported("not reported"))
        assert "0" not in out
        assert out != ""

    def test_unavailable_energy_never_formats_as_zero(self) -> None:
        out = units.format_metric_watt_hours(MetricValue.unsupported("x"))
        assert "0" not in out
