"""T014 verification: power rendering (FR-005, FR-008, FR-019)."""

from __future__ import annotations

import datetime as dt

from gpum.core.models import (
    Availability,
    DeviceId,
    GpuDevice,
    LimitReason,
    MetricValue,
    Snapshot,
    Vendor,
)
from gpum.core.preferences import Preferences
from gpum.ui.main_window import MainWindow


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _device(**kw: object) -> GpuDevice:
    defaults: dict = {
        "memory_total": MetricValue.available(24 * 1024**3, sampled_at=_now()),
        "memory_used": MetricValue.available(6 * 1024**3, sampled_at=_now()),
        "utilization_gpu": MetricValue.available(50, sampled_at=_now()),
        "attribution": Availability.AVAILABLE,
        "power_draw": MetricValue.available(17.1, sampled_at=_now()),
        "power_draw_avg": MetricValue.available(16.8, sampled_at=_now()),
        "power_limit": MetricValue.available(180.0, sampled_at=_now()),
        "energy_session": MetricValue.available(0.523, sampled_at=_now()),
        "limit_reason": LimitReason.NONE,
    }
    defaults.update(kw)
    return GpuDevice(id=DeviceId(Vendor.NVIDIA, "gpu-a", 0), name="Test GPU", **defaults)


def _render(qtbot, device: GpuDevice) -> MainWindow:
    window = MainWindow(Preferences())
    qtbot.addWidget(window)
    window.on_snapshot(Snapshot(taken_at=_now(), sequence=1, devices=(device,)))
    return window


class TestPowerRendering:
    def test_draw_and_limit_shown(self, qtbot) -> None:
        window = _render(qtbot, _device())
        text = window._panels["gpu-a"]._power_label.text()
        assert "16.8 W" in text
        assert "180.0 W" in text

    def test_percentage_of_limit_shown(self, qtbot) -> None:
        window = _render(qtbot, _device())
        text = window._panels["gpu-a"]._power_label.text()
        assert "9%" in text or "10%" in text

    def test_averaged_figure_is_labelled(self, qtbot) -> None:
        """FR-008: an average is not a measurement of any instant; say so."""
        window = _render(qtbot, _device())
        text = window._panels["gpu-a"]._power_label.text()
        assert "avg" in text.lower()

    def test_unavailable_power_never_renders_as_zero_watts(self, qtbot) -> None:
        """FR-005 — zero watts asserts the card is off."""
        device = _device(
            power_draw=MetricValue.unsupported("not reported by this device"),
            power_draw_avg=MetricValue.unsupported("no recent power readings"),
        )
        window = _render(qtbot, device)
        text = window._panels["gpu-a"]._power_label.text()
        # Check the draw portion specifically: the limit "180.0 W" legitimately contains the
        # substring "0.0 W", so a naive whole-string check gives a false positive.
        draw_part = text.split("/")[0]
        assert "W" not in draw_part, f"draw rendered as a number: {draw_part!r}"
        assert "Not supported" in draw_part

    def test_draw_shown_when_limit_missing(self, qtbot) -> None:
        device = _device(power_limit=MetricValue.unsupported("no limit reported"))
        window = _render(qtbot, device)
        text = window._panels["gpu-a"]._power_label.text()
        assert "16.8 W" in text


class TestEnergyRendering:
    def test_session_energy_shown(self, qtbot) -> None:
        window = _render(qtbot, _device())
        text = window._panels["gpu-a"]._energy_label.text()
        assert "0.523 Wh" in text

    def test_interrupted_period_is_flagged(self, qtbot) -> None:
        """FR-015: a total covering lost readings must not read as complete."""
        device = _device(energy_interrupted=True)
        window = _render(qtbot, device)
        text = window._panels["gpu-a"]._energy_label.text()
        assert "interrupted" in text.lower()

    def test_reset_disabled_when_energy_unavailable(self, qtbot) -> None:
        device = _device(energy_session=MetricValue.unsupported("not reported"))
        window = _render(qtbot, device)
        assert not window._panels["gpu-a"]._energy_reset.isEnabled()

    def test_reset_emits_the_device_key(self, qtbot) -> None:
        window = _render(qtbot, _device())
        with qtbot.waitSignal(window.energy_reset_requested, timeout=1000) as blocker:
            window._panels["gpu-a"]._energy_reset.click()
        assert blocker.args == ["gpu-a"]


class TestLimitReasonRendering:
    """The window must stay bound to a local: an unbound MainWindow is garbage-collected
    mid-expression and its C++ widgets are destroyed before they can be read."""

    def _reason_text(self, qtbot, reason: LimitReason) -> str:
        window = _render(qtbot, _device(limit_reason=reason))
        return window._panels["gpu-a"]._limit_reason_label.text()

    def test_unconstrained_shows_nothing(self, qtbot) -> None:
        assert self._reason_text(qtbot, LimitReason.NONE) == ""

    def test_power_limited_is_stated(self, qtbot) -> None:
        assert "Power limited" in self._reason_text(qtbot, LimitReason.POWER)

    def test_thermally_limited_is_stated(self, qtbot) -> None:
        assert "Thermally limited" in self._reason_text(qtbot, LimitReason.THERMAL)

    def test_unknown_differs_from_unconstrained(self, qtbot) -> None:
        """FR-019: an absence of information must not render as information."""
        none_text = self._reason_text(qtbot, LimitReason.NONE)
        unknown_text = self._reason_text(qtbot, LimitReason.UNKNOWN)
        assert none_text != unknown_text
        assert unknown_text
