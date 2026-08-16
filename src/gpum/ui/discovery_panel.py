"""What was searched for and what was found (FR-018, SC-006).

This is what a machine with no GPU sees instead of a blank window. It names every backend that
was attempted — stubs included — so "AMD: not supported in this release" is visible rather
than being an unexplained absence.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from gpum.core.models import BackendState, DiscoveryReport

__all__ = ["DiscoveryPanel"]

_STATE_TEXT = {
    BackendState.ACTIVE: "active",
    BackendState.NO_DEVICES: "no devices found",
    BackendState.DRIVER_MISSING: "driver not loaded",
    BackendState.LIBRARY_MISSING: "support not installed",
    BackendState.NOT_IMPLEMENTED: "not supported in this release",
    BackendState.ERROR: "error",
}


class DiscoveryPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._layout = QVBoxLayout(self)

        self._heading = QLabel("Looking for GPUs…")
        font = self._heading.font()
        font.setBold(True)
        self._heading.setFont(font)
        self._layout.addWidget(self._heading)

        self._detail = QLabel()
        self._detail.setWordWrap(True)
        self._detail.setTextFormat(Qt.TextFormat.PlainText)
        self._layout.addWidget(self._detail)

        self._hint = QLabel()
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet("color: palette(mid);")
        self._layout.addWidget(self._hint)

    def update_report(self, report: DiscoveryReport) -> None:
        lines = []
        for backend in report.backends_attempted:
            label = _STATE_TEXT.get(backend.state, backend.state)
            count = f" ({backend.device_count} device(s))" if backend.device_count else ""
            lines.append(f"• {backend.vendor.upper()}: {label}{count} — {backend.detail}")

        for gpu in report.present_but_unmonitored:
            lines.append(
                f"• {gpu.vendor.upper()} GPU detected at {gpu.location} — {gpu.reason}"
            )

        if report.any_devices:
            self._heading.setText("GPUs found")
        else:
            self._heading.setText("No GPUs are available to monitor")

        self._detail.setText("\n".join(lines) or "No GPU backends were registered.")

        if report.attribution_source:
            self._hint.setText(f"Per-process data source: {report.attribution_source}")
        else:
            self._hint.setText(
                "No per-process data source is available, so processes cannot be listed."
            )
