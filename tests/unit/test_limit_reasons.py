"""T003: limiting reasons (P-13, FR-019).

The assertion that matters: "nothing is limiting this device" and "we could not determine
whether anything is" are different states. Collapsing them presents an absence of information
as information — the same error as rendering an unavailable metric as zero.
"""

from __future__ import annotations

import pytest

from gpum.core.models import LimitReason


class TestDistinctStates:
    def test_none_and_unknown_are_different(self) -> None:
        assert LimitReason.NONE is not LimitReason.UNKNOWN
        assert LimitReason.NONE != LimitReason.UNKNOWN

    def test_none_is_a_measurement(self) -> None:
        """The hardware genuinely reports 'nothing is limiting this'. That is data."""
        assert LimitReason.NONE.is_measurement is True

    def test_unknown_is_not_a_measurement(self) -> None:
        assert LimitReason.UNKNOWN.is_measurement is False

    def test_all_five_states_exist(self) -> None:
        assert {r.value for r in LimitReason} == {
            "none",
            "power",
            "thermal",
            "other",
            "unknown",
        }

    @pytest.mark.parametrize(
        ("reason", "constrained"),
        [
            (LimitReason.NONE, False),
            (LimitReason.POWER, True),
            (LimitReason.THERMAL, True),
            (LimitReason.OTHER, True),
            (LimitReason.UNKNOWN, False),
        ],
    )
    def test_is_constrained(self, reason: LimitReason, constrained: bool) -> None:
        """UNKNOWN must not claim the device is constrained — we do not know."""
        assert reason.is_constrained is constrained


class TestDisplay:
    def test_every_state_has_display_text_except_none(self) -> None:
        for reason in LimitReason:
            text = reason.display_text
            if reason is LimitReason.NONE:
                assert text == "", "an unconstrained device should show nothing"
            else:
                assert text, f"{reason} needs user-facing text"

    def test_unknown_does_not_imply_unconstrained(self) -> None:
        assert LimitReason.UNKNOWN.display_text
        assert LimitReason.UNKNOWN.display_text != LimitReason.NONE.display_text
