"""Bounded-history sparkline.

Unavailable stretches render as **gaps**, never as a dip to zero (U-12). A monitor that draws
a missing reading as 0% looks exactly like a monitor reporting an idle GPU, which is the
misreading SC-007 exists to prevent.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from gpum.core.history import HistoryPoint

__all__ = ["Sparkline"]


class Sparkline(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        label: str = "",
        fixed_maximum: float | None = None,
        colour: QColor | None = None,
    ) -> None:
        super().__init__(parent)
        self.setMinimumHeight(36)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self._points: list[HistoryPoint] = []
        self._maximum: float = 1.0
        self._colour = colour or QColor(72, 160, 240)
        self._label = label
        #: When set, the series is drawn against this ceiling rather than its observed peak.
        #:
        #: A percentage is already a fraction of a fixed maximum, so rescaling it to the recent
        #: peak would make an idle GPU's 0-3% noise fill the graph and read as sustained heavy
        #: load — and would make two devices incomparable, each drawn against its own peak
        #: (FR-020).
        self._fixed_maximum = fixed_maximum

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

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)

        painter.fillRect(self.rect(), QColor(0, 0, 0, 18))

        if self._label:
            painter.setPen(QColor(120, 120, 120))
            font = painter.font()
            font.setPointSizeF(max(6.5, font.pointSizeF() - 2))
            painter.setFont(font)
            painter.drawText(
                rect.adjusted(2, 0, 0, 0), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                self._label,
            )

        if len(self._points) < 2 or self._maximum <= 0:
            return

        width = rect.width()
        height = rect.height()
        step = width / max(1, len(self._points) - 1)

        path = QPainterPath()
        drawing = False
        for index, point in enumerate(self._points):
            if point.value is None:
                # A gap: end the current segment rather than plotting a zero.
                drawing = False
                continue
            x = rect.left() + index * step
            ratio = min(1.0, max(0.0, point.value / self._maximum))
            y = rect.bottom() - ratio * height
            if not drawing:
                path.moveTo(QPointF(x, y))
                drawing = True
            else:
                path.lineTo(QPointF(x, y))

        painter.setPen(QPen(self._colour, 1.6))
        painter.drawPath(path)
