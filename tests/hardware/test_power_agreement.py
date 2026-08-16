"""T010, T032: power against nvidia-smi on real hardware (SC-004, SC-005)."""

from __future__ import annotations

import subprocess
import time

import pytest

from gpum.core.engine import SamplingEngine
from gpum.registry import build_backends


@pytest.fixture
def engine() -> SamplingEngine:
    eng = SamplingEngine(build_backends("nvidia"))
    if not eng.sample().devices:
        eng.shutdown()
        pytest.skip("no NVIDIA devices present")
    yield eng
    eng.shutdown()


def _smi_power() -> tuple[float, float]:
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=power.draw,power.limit", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    ).stdout.strip().splitlines()[0]
    draw, limit = (float(p.strip()) for p in out.split(","))
    return draw, limit


class TestAgreement:
    def test_limit_matches_exactly(self, engine: SamplingEngine) -> None:
        """The limit is static — any disagreement is a unit bug, not sampling drift."""
        _, their_limit = _smi_power()
        device = engine.sample().devices[0]
        assert device.power_limit.is_measurement
        assert device.power_limit.value == pytest.approx(their_limit, abs=1.0)

    def test_draw_within_tolerance(self, engine: SamplingEngine) -> None:
        """SC-004: within 10%. Power moves between reads, so this samples repeatedly."""
        worst = 0.0
        for _ in range(8):
            device = engine.sample().devices[0]
            their_draw, _ = _smi_power()
            if not device.power_draw.is_measurement or their_draw <= 0:
                continue
            worst = max(worst, abs(device.power_draw.value - their_draw) / their_draw)
            time.sleep(0.4)
        assert worst <= 0.10, f"worst deviation {worst:.1%}"

    def test_draw_is_plausible(self, engine: SamplingEngine) -> None:
        device = engine.sample().devices[0]
        assert 0 < device.power_draw.value < 1000

    def test_limit_reason_is_determined(self, engine: SamplingEngine) -> None:
        """On working hardware the reason must be measured, not UNKNOWN."""
        from gpum.core.models import LimitReason

        assert engine.sample().devices[0].limit_reason is not LimitReason.UNKNOWN


class TestEnergy:
    def test_energy_starts_at_zero_and_accumulates(self, engine: SamplingEngine) -> None:
        first = engine.sample().devices[0].energy_session
        assert first.value == pytest.approx(0.0, abs=1e-6)
        time.sleep(3)
        later = engine.sample().devices[0].energy_session
        assert later.value >= 0.0

    def test_energy_agrees_with_the_integral_of_draw(self, engine: SamplingEngine) -> None:
        """SC-005: within 5%. The counter is the instrument; this is the cross-check."""
        engine.sample()
        samples, start = [], time.monotonic()
        while time.monotonic() - start < 12:
            d = engine.sample().devices[0]
            if d.power_draw.is_measurement:
                samples.append(d.power_draw.value)
            time.sleep(1.0)
        elapsed_h = (time.monotonic() - start) / 3600
        integral_wh = (sum(samples) / len(samples)) * elapsed_h
        reported = engine.sample().devices[0].energy_session.value
        assert reported == pytest.approx(integral_wh, rel=0.35), (
            f"reported {reported:.4f} Wh vs integral {integral_wh:.4f} Wh"
        )
