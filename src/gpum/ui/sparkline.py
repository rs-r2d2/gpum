"""Bounded-history sparkline.

Unavailable stretches render as **gaps**, never as a dip to zero (U-12). A monitor that draws
a missing reading as 0% looks exactly like a monitor reporting an idle GPU, which is the
misreading SC-007 exists to prevent. The area fill honours the same rule: it is built per
contiguous segment, so it never spans a gap and never implies data across one.

**Why this is drawn as a framed chart rather than a bare line.** The first version washed the
whole widget with ``QColor(0, 0, 0, 18)`` and drew a 6.5pt mid-grey label under the series. Every
foreground element failed WCAG contrast against that wash — the label at 3.28:1 against a 4.5:1
requirement, and the two series lines at 2.06:1 and 1.59:1 against a 3:1 requirement — while the
ordinary panel text beside them ran 17:1. A flat grey overlay is also Qt's own convention for a
*disabled* widget, so two live graphs read as switched off, and the series was drawn over the
label rather than around it. The frame, the grid, and the value readout replace that: the widget
now looks like an instrument, and every element is measurably legible in both palettes.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from functools import lru_cache

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPalette,
    QPen,
)
from PySide6.QtWidgets import QWidget

from gpum.core.history import HistoryPoint

__all__ = ["Sparkline"]

#: Gridlines as fractions of the ceiling. Enough to read a value off the curve, few enough not
#: to compete with the series.
_GRID_FRACTIONS = (0.25, 0.5, 0.75)

#: Series line width. Wide enough that antialiasing leaves a fully saturated core pixel — at
#: 1.6px every pixel of the line is a blend, so the colour a user actually sees is paler than the
#: colour chosen, which is half of how the original graphs ended up unreadable.
_SERIES_WIDTH = 2.0

#: Contrast the series is corrected to before painting.
#:
#: Higher than the 3:1 that WCAG 1.4.11 requires, because 3:1 is the figure that must survive
#: *rasterisation*. Antialiasing blends the curve's edge pixels toward the background, so
#: correcting to exactly 3.0 paints something below it — measured at 2.91:1 on the very colour
#: this widget shipped with. The margin is the cost of the curve being smooth.
_SERIES_MIN_CONTRAST = 4.0

#: The widget's whole vertical budget: one header row plus the plot card.
#:
#: Deliberately tight. `test_u12_process_table_stays_visible` caps both graphs at 120px combined,
#: because the process table is the feature and the graphs are context — a taller chart would win
#: the layout argument against the thing users actually came for.
_HEIGHT = 58
_HEADER_H = 15


def _relative_luminance(colour: QColor) -> float:
    def channel(value: int) -> float:
        srgb = value / 255
        return srgb / 12.92 if srgb <= 0.03928 else ((srgb + 0.055) / 1.055) ** 2.4

    return (
        0.2126 * channel(colour.red())
        + 0.7152 * channel(colour.green())
        + 0.0722 * channel(colour.blue())
    )


def _contrast(a: QColor, b: QColor) -> float:
    high, low = sorted((_relative_luminance(a), _relative_luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


@lru_cache(maxsize=32)
def _legible_rgb(colour_rgb: int, background_rgb: int, minimum: float) -> int:
    """Nudge a series colour until it clears ``minimum`` contrast on this background.

    A single hard-coded palette cannot serve both themes: the original light blue was chosen to
    sit on a dark chart and scored 2.06:1 once the chart turned out to be light. Rather than pick
    a compromise that is mediocre on both, the hue is kept and only lightness moves, away from
    the background until the ratio is met. Cached because the answer depends solely on the two
    colours, and `paintEvent` must stay cheap (U-01).
    """
    colour, background = QColor(colour_rgb), QColor(background_rgb)
    if _contrast(colour, background) >= minimum:
        return colour.rgb()

    # Move away from the background: darken on a light ground, lighten on a dark one.
    darken = _relative_luminance(background) > 0.5
    hue, saturation, lightness, alpha = colour.getHsl()
    for _ in range(64):
        lightness = max(0, lightness - 4) if darken else min(255, lightness + 4)
        candidate = QColor.fromHsl(hue, saturation, lightness, alpha)
        if _contrast(candidate, background) >= minimum:
            return candidate.rgb()
        if lightness in (0, 255):
            break
    return candidate.rgb()


def _segments(points: Sequence[HistoryPoint]) -> list[list[tuple[int, float]]]:
    """Contiguous runs of real readings, as ``(index, value)`` pairs.

    The single mechanism behind U-12. Splitting first means neither the line nor the fill can
    bridge an unavailable stretch, because a gap is simply not inside any segment.
    """
    runs: list[list[tuple[int, float]]] = []
    current: list[tuple[int, float]] = []
    for index, point in enumerate(points):
        if point.value is None:
            if current:
                runs.append(current)
                current = []
            continue
        current.append((index, point.value))
    if current:
        runs.append(current)
    return runs


class Sparkline(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        label: str = "",
        fixed_maximum: float | None = None,
        colour: QColor | None = None,
        value_format: Callable[[float], str] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setMinimumHeight(_HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self._points: list[HistoryPoint] = []
        self._maximum: float = 1.0
        self._colour = colour or QColor(21, 101, 192)
        self._label = label
        #: Renders the current value and the ceiling. The widget holds raw floats and has no
        #: business knowing whether they are bytes or percent, so the caller supplies this.
        self._value_format = value_format or (lambda value: f"{value:.0f}")
        #: When set, the series is drawn against this ceiling rather than its observed peak.
        #:
        #: A percentage is already a fraction of a fixed maximum, so rescaling it to the recent
        #: peak would make an idle GPU's 0-3% noise fill the graph and read as sustained heavy
        #: load — and would make two devices incomparable, each drawn against its own peak
        #: (FR-020).
        self._fixed_maximum = fixed_maximum
        if label:
            # The chart is pure painting, so without this it is invisible to a screen reader.
            self.setAccessibleName(label)

    def set_points(self, points: list[HistoryPoint], maximum: float | None) -> None:
        """Assignment plus a repaint request — no computation on the GUI thread (U-01)."""
        self._points = points
        if self._fixed_maximum is not None:
            self._maximum = self._fixed_maximum
        else:
            self._maximum = float(maximum) if maximum else 1.0
        self.update()

    @property
    def label(self) -> str:
        return self._label

    @property
    def fixed_maximum(self) -> float | None:
        return self._fixed_maximum

    # -- painting -------------------------------------------------------------

    def _series_pen_colour(self, background: QColor) -> QColor:
        return QColor(_legible_rgb(self._colour.rgb(), background.rgb(), _SERIES_MIN_CONTRAST))

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        palette = self.palette()
        card_bg = palette.color(QPalette.ColorRole.Base)
        text = palette.color(QPalette.ColorRole.Text)
        muted = QColor(text)
        muted.setAlpha(165)
        border = QColor(text)
        border.setAlpha(70)

        font = painter.font()
        font.setPointSizeF(max(7.5, font.pointSizeF() - 1))
        painter.setFont(font)

        # The axis labels get their own gutter outside the plot. Drawing the ceiling *inside* the
        # plot is the trap this widget already fell into once: at 96% activity the series runs
        # straight through a top-right "100%", which is the same collision the header band was
        # introduced to fix.
        ceiling_text = self._value_format(self._maximum)
        metrics = QFontMetricsF(font)
        gutter = metrics.horizontalAdvance(ceiling_text) + 8

        header = QRectF(1, 0, self.width() - 2, _HEADER_H)
        card = QRectF(
            1.5,
            _HEADER_H + 0.5,
            max(8.0, self.width() - gutter - 3),
            self.height() - _HEADER_H - 2,
        )

        # -- header: label left, current value right ---------------------------
        # Drawn in its own band rather than over the plot. The series used to be painted on top
        # of the label, which is how "GPU activity (% of time busy)" ended up with a line
        # through it.
        if self._label:
            painter.setPen(muted)
            painter.drawText(
                header,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                self._label,
            )

        segments = _segments(self._points)
        bold = QFont(font)
        bold.setBold(True)
        painter.setFont(bold)
        painter.setPen(text)
        painter.drawText(
            header,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            self._value_format(segments[-1][-1][1]) if segments else "—",
        )
        painter.setFont(font)

        # -- the plot card -----------------------------------------------------
        painter.setBrush(card_bg)
        painter.setPen(QPen(border, 1))
        painter.drawRoundedRect(card, 3, 3)

        plot = card.adjusted(3, 3, -3, -3)
        grid = QColor(text)
        grid.setAlpha(28)
        painter.setPen(QPen(grid, 1))
        for fraction in _GRID_FRACTIONS:
            y = plot.bottom() - fraction * plot.height()
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))

        # The ceiling and the floor, stated in the gutter. Without them the two graphs look like
        # the same chart while one is scaled to installed memory and the other to a fixed 100%
        # (FR-020).
        # Each label is centred on the gridline it names, so the pair reads as an axis rather
        # than as two captions that happen to sit near the corners.
        painter.setPen(muted)
        for text_value, y in ((ceiling_text, plot.top()), ("0", plot.bottom())):
            painter.drawText(
                QRectF(card.right() + 4, y - 6, gutter, 12),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                text_value,
            )

        if not segments or self._maximum <= 0:
            return

        series = self._series_pen_colour(card_bg)
        fill = QColor(series)
        fill.setAlpha(48)
        step = plot.width() / max(1, len(self._points) - 1)

        def coords(index: int, value: float) -> QPointF:
            ratio = min(1.0, max(0.0, value / self._maximum))
            return QPointF(plot.left() + index * step, plot.bottom() - ratio * plot.height())

        peak = max(value for segment in segments for _, value in segment)

        for segment in segments:
            line = QPainterPath()
            area = QPainterPath()
            first = coords(*segment[0])
            area.moveTo(QPointF(first.x(), plot.bottom()))
            area.lineTo(first)
            line.moveTo(first)
            for index, value in segment[1:]:
                point = coords(index, value)
                line.lineTo(point)
                area.lineTo(point)
            area.lineTo(QPointF(coords(*segment[-1]).x(), plot.bottom()))
            area.closeSubpath()

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill)
            painter.drawPath(area)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(series, _SERIES_WIDTH))
            painter.drawPath(line)

        # -- peak marker -------------------------------------------------------
        # The window's high-water mark, which a 1.8px line at this height otherwise hides.
        if peak > 0:
            for segment in segments:
                for index, value in segment:
                    if value == peak:
                        painter.setPen(QPen(series, 1))
                        painter.setBrush(card_bg)
                        painter.drawEllipse(coords(index, value), 2.4, 2.4)
                        return
