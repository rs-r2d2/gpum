"""Per-device panel: memory, utilization, trend, and the process table.

Everything here is assignment and repaint. Anything derived is computed before the snapshot
crosses the thread boundary, so no GUI-thread slot exceeds the 16 ms budget (U-01).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from gpum.core.history import DeviceHistory
from gpum.core.models import Availability, GpuDevice, Snapshot
from gpum.ui import availability as av
from gpum.ui.process_model import ProcessTableModel
from gpum.ui.sparkline import Sparkline

__all__ = ["DevicePanel"]


def _percent_value(metric) -> float | None:
    """A percentage to fill a bar with, or None when there is nothing measured."""
    if metric.is_measurement and metric.value is not None:
        return max(0.0, min(100.0, float(metric.value)))
    return None


def _activity_text(subject: str, metric) -> str:
    """``<subject> busy N% of the time``, or a plain unavailable statement.

    The two need different sentences, not one sentence with a substituted value. Splicing an
    availability state into the measured wording produced "GPU compute busy Not supported of
    the time" — which reads as a broken sentence first and an unavailable metric second, and
    FR-011 asks for the reverse.
    """
    if metric.is_measurement and metric.value is not None:
        return f"{subject} busy  {av.percent_text(metric)} of the time"
    return f"{subject} activity  {av.percent_text(metric)}"


def _activity_tooltip(explanation: str, metric) -> str:
    """The standing explanation, plus *why* the figure is missing when it is.

    FR-011 requires unavailability to carry a reason. The label has room only for the state,
    so the reason lives here rather than being dropped.
    """
    if metric.is_measurement:
        return explanation
    return f"{av.tooltip_for(metric)}\n\n{explanation}"

#: FR-010: the explanation must be reachable from the panel. The figure's common name — "core
#: utilization" — describes something the hardware does not report.
_ACTIVITY_EXPLANATION = (
    "How much of the time the GPU was working.\n\n"
    "This is not the share of GPU cores in use — the hardware does not report that. "
    "A single small task can hold this at 100%."
)

_MEMORY_ACTIVITY_EXPLANATION = (
    "How much of the time the path to GPU memory was busy.\n\n"
    "This is not how full the memory is; that is shown separately above."
)


class DevicePanel(QFrame):
    energy_reset_requested = Signal(str)
    #: (device_key, column value, descending) — for per-device persistence (FR-017).
    sort_changed = Signal(str, str, bool)

    def __init__(self, device: GpuDevice, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.device_key = device.id.key
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        self._title = QLabel()
        font = self._title.font()
        font.setBold(True)
        self._title.setFont(font)
        layout.addWidget(self._title)

        # Three comparable quantities, presented identically: a label with its value, and a bar.
        # Previously memory had a bar and the two activity figures did not, and the compute
        # figure was printed twice — once in a stats row and again in an activity row.
        self._memory_label, self._memory_bar = self._metered_row(layout)
        self._compute_label, self._compute_bar = self._metered_row(layout)
        self._mem_activity_label, self._mem_activity_bar = self._metered_row(layout)

        self._sparkline = Sparkline(label="Memory used")
        layout.addWidget(self._sparkline)

        # A second, separate graph (FR-018) on a fixed 0-100 scale (FR-020), so an idle GPU
        # reads as idle rather than having its noise stretched to fill the height.
        self._utilization_spark = Sparkline(
            label="GPU activity (% of time busy)",
            fixed_maximum=100.0,
            colour=QColor(240, 160, 72),
        )
        layout.addWidget(self._utilization_spark)

        # -- 004: power and energy share one row -----------------------------
        power_row = QHBoxLayout()
        self._power_label = QLabel()
        power_row.addWidget(self._power_label)
        self._limit_reason_label = QLabel()
        self._limit_reason_label.setStyleSheet("color: palette(mid);")
        power_row.addWidget(self._limit_reason_label)
        power_row.addStretch(1)
        self._energy_label = QLabel()
        power_row.addWidget(self._energy_label)
        self._energy_reset = QPushButton("Reset")
        self._energy_reset.setToolTip("Start measuring energy again from zero")
        self._energy_reset.setMaximumWidth(70)
        self._energy_reset.clicked.connect(
            lambda: self.energy_reset_requested.emit(self.device_key)
        )
        power_row.addWidget(self._energy_reset)
        layout.addLayout(power_row)

        self._process_note = QLabel()
        self._process_note.setWordWrap(True)
        self._process_note.setStyleSheet("color: palette(mid);")
        layout.addWidget(self._process_note)

        self._model = ProcessTableModel(self)
        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._table.setAlternatingRowColors(True)
        # The toolkit supplies click-to-sort, click-again-to-reverse, the direction indicator,
        # and the single-active-column rule (FR-001 - FR-004).
        self._table.setSortingEnabled(True)
        self._table.horizontalHeader().setSortIndicatorShown(True)
        self._model.sort_changed.connect(self._on_sort_changed)
        # The model may pick a different first-click direction than the view assumed, so the
        # indicator is re-synced from the model rather than trusted from the click.
        self._model.sort_changed.connect(self._sync_sort_indicator)
        layout.addWidget(self._table)

        self.update_device(device, None, None)

    @staticmethod
    def _metered_row(layout: QVBoxLayout) -> tuple[QLabel, QProgressBar]:
        """A label above a thin bar — the uniform presentation for every percentage."""
        label = QLabel()
        layout.addWidget(label)
        bar = QProgressBar()
        bar.setTextVisible(False)
        bar.setMaximumHeight(6)
        bar.setRange(0, 100)
        layout.addWidget(bar)
        return label, bar

    @staticmethod
    def _set_meter(bar: QProgressBar, percent: float | None) -> None:
        """Fill a bar, or leave it empty and disabled when there is nothing to show.

        Disabling is what distinguishes "unavailable" from a measured 0% — both leave the bar
        empty, and without the visual difference the two would be indistinguishable (FR-012).
        """
        bar.setValue(int(percent) if percent is not None else 0)
        bar.setEnabled(percent is not None)

    def update_device(
        self,
        device: GpuDevice,
        snapshot: Snapshot | None,
        history: DeviceHistory | None,
    ) -> None:
        self._title.setText(self._title_text(device))

        if not device.supported:
            self._render_unsupported(device)
            return

        for widget in (self._memory_bar, self._compute_bar, self._mem_activity_bar):
            widget.setVisible(True)
        self._sparkline.setVisible(True)
        self._utilization_spark.setVisible(True)
        self._table.setVisible(True)

        used_text = av.memory_text(device.memory_used)
        total_text = av.memory_text(device.memory_total)
        percent = device.memory_percent
        suffix = f"  ({percent:.0f}%)" if percent is not None else ""
        self._memory_label.setText(f"Memory {used_text} / {total_text}{suffix}")
        self._memory_label.setToolTip(av.tooltip_for(device.memory_used))
        self._set_meter(self._memory_bar, percent)

        self._render_activity(device)
        self._render_power(device)

        if history is not None:
            maximum = (
                device.memory_total.value
                if device.memory_total.is_measurement
                else max((p.value or 0) for p in history.memory_used) or 1
            )
            self._sparkline.set_points(list(history.memory_used), float(maximum))
            # Fixed scale, so the maximum passed here is ignored by the widget.
            self._utilization_spark.set_points(list(history.utilization), 100.0)

        self._render_processes(device, snapshot)

    # -- internals ------------------------------------------------------------

    def _render_activity(self, device: GpuDevice) -> None:
        """Both activity figures, labelled so neither can be read as the other (FR-021, FR-022).

        Neither is a share of hardware. Both measure how much of the sampling period the
        respective engine was busy.
        """
        compute = device.utilization_gpu
        self._compute_label.setText(_activity_text("GPU compute", compute))
        self._compute_label.setToolTip(_activity_tooltip(_ACTIVITY_EXPLANATION, compute))
        self._set_meter(self._compute_bar, _percent_value(compute))

        mem = device.utilization_memory
        self._mem_activity_label.setText(_activity_text("Memory interface", mem))
        self._mem_activity_label.setToolTip(
            _activity_tooltip(_MEMORY_ACTIVITY_EXPLANATION, mem)
        )
        self._set_meter(self._mem_activity_bar, _percent_value(mem))

    def _render_power(self, device: GpuDevice) -> None:
        """Power, energy, and limiting reason (FR-001 - FR-003, FR-011, FR-017 - FR-019)."""
        # The averaged figure is what is shown, and it says so — an average is not a
        # measurement of any instant, and the user is entitled to know that (FR-008).
        draw = device.power_draw_avg if device.power_draw_avg.is_measurement else device.power_draw
        draw_text = av.power_text(draw)
        limit_text = av.power_text(device.power_limit)
        percent = device.power_percent
        suffix = f"  ({percent:.0f}%)" if percent is not None else ""
        averaged = "  · 8s avg" if device.power_draw_avg.is_measurement else ""
        self._power_label.setText(f"Power {draw_text} / {limit_text}{suffix}{averaged}")
        self._power_label.setToolTip(av.tooltip_for(draw))

        energy = av.energy_text(device.energy_session)
        note = "  (readings were interrupted)" if device.energy_interrupted else ""
        self._energy_label.setText(f"Energy this session {energy}{note}")
        self._energy_label.setToolTip(av.tooltip_for(device.energy_session))
        self._energy_reset.setEnabled(device.energy_session.is_measurement)

        # NONE shows nothing; UNKNOWN says so. They are different states (FR-019).
        self._limit_reason_label.setText(device.limit_reason.display_text)

    def _title_text(self, device: GpuDevice) -> str:
        stale = ""
        if device.memory_used.availability is Availability.STALE:
            stale = f"  —  stale, last measured {av.age_text(device.memory_used)}"
        elif device.memory_used.availability is Availability.DEGRADED:
            stale = "  —  not responding"
        return f"{device.name}  #{device.id.index}{stale}"

    def _render_unsupported(self, device: GpuDevice) -> None:  # noqa: D401
        """FR-028: say why, and show no figures that might be wrong for a partition."""
        self._memory_label.setText(device.unsupported_reason or "Unsupported device")

        for widget in (self._memory_bar, self._compute_bar, self._mem_activity_bar):
            widget.setVisible(False)
        self._sparkline.setVisible(False)
        self._utilization_spark.setVisible(False)
        self._table.setVisible(False)
        self._power_label.setText("")
        self._energy_label.setText("")
        self._compute_label.setText("")
        self._mem_activity_label.setText("")
        self._energy_reset.setVisible(False)
        self._limit_reason_label.setText("")
        self._process_note.setText(
            "This device is not supported, so no metrics are shown for it."
        )

    def _render_processes(self, device: GpuDevice, snapshot: Snapshot | None) -> None:
        """US2 scenario 4: when attribution is unavailable, explain — never show an empty
        table, which would imply the GPU is idle."""
        if device.attribution is not Availability.AVAILABLE:
            reason = device.attribution_reason or "per-process data is unavailable"
            self._process_note.setText(f"Processes: {reason}")
            self._process_note.setVisible(True)
            self._table.setVisible(False)
            return

        processes = snapshot.processes_for(device.id.key) if snapshot else ()
        self._table.setVisible(True)
        self._model.set_processes(processes)
        if processes:
            self._process_note.setVisible(False)
        else:
            self._process_note.setText("No processes are currently using this GPU.")
            self._process_note.setVisible(True)

    def set_sort(self, column: object, descending: bool) -> None:
        """Apply a sort order without reporting it back as a user action."""
        self._model.set_sort(column, descending)  # type: ignore[arg-type]
        header = self._table.horizontalHeader()
        was_blocked = header.blockSignals(True)
        self._table.sortByColumn(
            self._model.sort_section,
            Qt.SortOrder.DescendingOrder if descending else Qt.SortOrder.AscendingOrder,
        )
        header.blockSignals(was_blocked)

    def _on_sort_changed(self, column: str, descending: bool) -> None:
        self.sort_changed.emit(self.device_key, column, descending)

    def _sync_sort_indicator(self, column: str, descending: bool) -> None:
        """Keep the header arrow matching the order actually applied."""
        header = self._table.horizontalHeader()
        was_blocked = header.blockSignals(True)
        header.setSortIndicator(
            self._model.sort_section,
            Qt.SortOrder.DescendingOrder if descending else Qt.SortOrder.AscendingOrder,
        )
        header.blockSignals(was_blocked)
