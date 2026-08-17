"""The trend graphs must read as live instruments, not as disabled widgets.

Regression cover for a shipped defect. The first sparkline washed itself with
``QColor(0, 0, 0, 18)`` and drew a 6.5pt mid-grey label *under* the series. Measured against that
wash, every foreground element failed WCAG: the label at 3.28:1 (needs 4.5:1) and the two series
lines at 2.06:1 and 1.59:1 (need 3:1), while ordinary panel text beside them ran 17:1. Two live
graphs therefore looked switched off, because a flat grey overlay is Qt's own convention for a
disabled control.

Contrast is asserted numerically rather than by screenshot comparison: the numbers are the
requirement, and a pixel baseline would break on every unrelated theme or font change.
"""

from __future__ import annotations

import datetime as dt

import pytest
from PySide6.QtGui import QColor, QPalette

from gpum.core.models import Availability
from gpum.core.units import format_bytes
from gpum.ui.sparkline import Sparkline, _contrast, _legible_rgb, _segments

pytest.importorskip("PySide6.QtWidgets")

from gpum.core.history import HistoryPoint  # noqa: E402

GIB = 1024**3

#: WCAG 2.1: 1.4.11 non-text contrast for a graphical object essential to understanding.
MIN_GRAPHIC_CONTRAST = 3.0
#: WCAG 2.1: 1.4.3 normal-size text. The labels are well below any large-text exemption.
MIN_TEXT_CONTRAST = 4.5

LIGHT_BASE = QColor(255, 255, 255)
DARK_BASE = QColor(30, 32, 36)


def _point(value: float | None) -> HistoryPoint:
    if value is None:
        return HistoryPoint(None, None, Availability.UNSUPPORTED)
    return HistoryPoint(dt.datetime.now(dt.UTC), value, Availability.AVAILABLE)


def _live_series_colours() -> dict[str, QColor]:
    """The colours the application actually passes, read off a constructed panel.

    Deliberately not a copy of the constants. A test asserting that colours *listed in the test*
    are legible would have passed throughout the entire period the shipped graphs were unreadable
    — the point is to fail when `device_panel` hands the widget something too pale.
    """
    from gpum.core.models import DeviceId, GpuDevice, Vendor
    from gpum.ui.device_panel import DevicePanel

    panel = DevicePanel(GpuDevice(id=DeviceId(Vendor.NVIDIA, "a", 0), name="Test GPU"))
    return {
        "memory": panel._sparkline._colour,
        "activity": panel._utilization_spark._colour,
    }


def _painted_series_contrast(colour: QColor, base: QColor, text: QColor) -> float:
    """Paint the widget for real and measure the boldest series pixel against its card.

    Asserted on pixels, not on the return value of `_legible_rgb`, and that distinction is the
    whole point. `_legible_rgb` guarantees its own output passes, so a test comparing its result
    against the threshold is a tautology — it stays green even if `paintEvent` never calls it.
    This measures what a user's eye receives, so removing the adjuster, or drawing with
    `self._colour` directly, fails here.
    """
    spark = Sparkline(label="Memory used", value_format=format_bytes, colour=colour)
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Base, base)
    palette.setColor(QPalette.ColorRole.Text, text)
    spark.setPalette(palette)
    spark.resize(360, 58)
    # A flat mid-height series, so the line sits clear of the frame, grid, and axis labels.
    spark.set_points([_point(12 * GIB) for _ in range(40)], float(24 * GIB))
    image = spark.grab().toImage()

    # Sample a vertical strip inside the plot, away from the header band and the right gutter.
    best = 0.0
    for x in range(60, 200, 3):
        for y in range(22, spark.height() - 6):
            best = max(best, _contrast(image.pixelColor(x, y), base))
    return best


class TestSeriesContrast:
    """The defect that made the graphs look greyed out."""

    @pytest.mark.parametrize("name", ["memory", "activity"])
    @pytest.mark.parametrize(
        ("base", "text"),
        [(LIGHT_BASE, QColor(0, 0, 0)), (DARK_BASE, QColor(228, 228, 230))],
        ids=["light", "dark"],
    )
    def test_painted_series_is_legible_on_its_own_card(
        self, name: str, base: QColor, text: QColor, qtbot
    ) -> None:
        """A series drawn below 3:1 on its own background is the whole bug, in one number."""
        colour = _live_series_colours()[name]
        ratio = _painted_series_contrast(colour, base, text)
        assert ratio >= MIN_GRAPHIC_CONTRAST, (
            f"{name} series ({colour.name()}) paints at {ratio:.2f}:1 on rgb"
            f"({base.red()},{base.green()},{base.blue()}); needs {MIN_GRAPHIC_CONTRAST}:1"
        )

    def test_a_pale_colour_is_rescued_at_paint_time(self, qtbot) -> None:
        """The original `rgb(72,160,240)` measured 2.06:1 on the slab it was drawn on.

        Handed to the widget today it must still reach the floor, because the guarantee lives in
        `paintEvent` rather than in the caller's choice of constant.
        """
        pale = QColor(72, 160, 240)
        assert _contrast(pale, LIGHT_BASE) < MIN_GRAPHIC_CONTRAST  # the input really is too pale
        ratio = _painted_series_contrast(pale, LIGHT_BASE, QColor(0, 0, 0))
        assert ratio >= MIN_GRAPHIC_CONTRAST, f"pale series painted at only {ratio:.2f}:1"

    @pytest.mark.parametrize("background", [LIGHT_BASE, DARK_BASE], ids=["light", "dark"])
    def test_the_two_series_stay_distinguishable(self, background: QColor, qtbot) -> None:
        """Two graphs sharing one colour would be worse than a pale one (FR-022)."""
        colours = _live_series_colours()
        adjusted = [
            QColor(_legible_rgb(c.rgb(), background.rgb(), 3.0)) for c in colours.values()
        ]
        assert _contrast(*adjusted) >= 1.5 or abs(adjusted[0].hue() - adjusted[1].hue()) > 30

    def test_the_original_colours_would_have_failed(self) -> None:
        """Pins the baseline, so nobody 'restores' the old palette believing it was fine.

        These are the shipped values measured against the slab they were drawn on.
        """
        slab = QColor(222, 222, 222)
        assert _contrast(QColor(72, 160, 240), slab) < MIN_GRAPHIC_CONTRAST
        assert _contrast(QColor(240, 160, 72), slab) < MIN_GRAPHIC_CONTRAST
        assert _contrast(QColor(120, 120, 120), slab) < MIN_TEXT_CONTRAST

    def test_a_colour_already_legible_is_left_alone(self) -> None:
        """The adjuster must not drift colours that already pass — it is a floor, not a filter."""
        black = QColor(0, 0, 0)
        assert _legible_rgb(black.rgb(), LIGHT_BASE.rgb(), 3.0) == black.rgb()

    def test_adjustment_preserves_hue(self, qtbot) -> None:
        """Only lightness may move. A colour that shifts hue to pass is a different design."""
        for colour in _live_series_colours().values():
            adjusted = QColor(_legible_rgb(colour.rgb(), DARK_BASE.rgb(), 3.0))
            assert abs(adjusted.hue() - colour.hue()) <= 2


class TestGapsSurviveTheRedesign:
    """U-12/SC-007. The area fill is new, and a fill is exactly how a gap gets silently bridged."""

    def test_segments_split_on_every_unavailable_reading(self) -> None:
        points = [_point(1.0), _point(2.0), _point(None), _point(3.0), _point(None), _point(4.0)]
        assert [[v for _, v in seg] for seg in _segments(points)] == [[1.0, 2.0], [3.0], [4.0]]

    def test_a_gap_is_never_represented_as_zero(self) -> None:
        """The misreading the whole rule exists to prevent: 0% looks like an idle GPU."""
        values = [v for seg in _segments([_point(5.0), _point(None), _point(6.0)]) for _, v in seg]
        assert 0.0 not in values
        assert values == [5.0, 6.0]

    def test_all_unavailable_yields_no_segments(self) -> None:
        assert _segments([_point(None)] * 5) == []

    def test_leading_and_trailing_gaps_do_not_create_empty_segments(self) -> None:
        segments = _segments([_point(None), _point(1.0), _point(None)])
        assert segments == [[(1, 1.0)]]
        assert all(seg for seg in segments)


class TestWidgetContract:
    """The public surface device_panel depends on, plus the layout budget."""

    def test_paints_without_error_in_both_palettes(self, qtbot) -> None:
        """Painting is where every one of these decisions actually lands."""
        for base, text in ((LIGHT_BASE, QColor(0, 0, 0)), (DARK_BASE, QColor(228, 228, 230))):
            spark = Sparkline(label="Memory used", value_format=format_bytes)
            palette = QPalette()
            palette.setColor(QPalette.ColorRole.Base, base)
            palette.setColor(QPalette.ColorRole.Text, text)
            spark.setPalette(palette)
            qtbot.addWidget(spark)
            spark.resize(400, 58)
            spark.set_points([_point(3 * GIB), _point(None), _point(9 * GIB)], float(24 * GIB))
            spark.grab()  # forces a real paintEvent

    def test_empty_history_paints_the_frame_not_a_crash(self, qtbot) -> None:
        spark = Sparkline(label="Memory used", value_format=format_bytes)
        qtbot.addWidget(spark)
        spark.resize(400, 58)
        spark.set_points([], None)
        spark.grab()

    def test_value_format_is_used_for_the_readout(self, qtbot) -> None:
        """Percent and bytes cannot share a formatter, so the caller supplies one (FR-020)."""
        spark = Sparkline(label="GPU activity", fixed_maximum=100.0,
                          value_format=lambda v: f"{v:.0f}%")
        qtbot.addWidget(spark)
        assert spark._value_format(42.4) == "42%"

    def test_fixed_maximum_is_not_overridden_by_the_observed_peak(self, qtbot) -> None:
        """Rescaling a percentage to its peak makes an idle GPU look pegged (FR-020)."""
        spark = Sparkline(fixed_maximum=100.0)
        qtbot.addWidget(spark)
        spark.set_points([_point(3.0), _point(4.0)], 4.0)
        assert spark._maximum == 100.0

    def test_label_is_exposed_to_assistive_technology(self, qtbot) -> None:
        """The chart is pure painting; without this it is invisible to a screen reader."""
        spark = Sparkline(label="Memory used")
        qtbot.addWidget(spark)
        assert spark.accessibleName() == "Memory used"

    def test_graph_height_stays_within_the_panel_budget(self, qtbot) -> None:
        """Two graphs must not out-argue the process table for vertical space."""
        pair = Sparkline().minimumHeight() + Sparkline(fixed_maximum=100.0).minimumHeight()
        assert pair <= 120, f"graphs reserve {pair}px"
