"""Status-area presence (contracts/tray-contract.md, FR-029 – FR-034).

Cross-platform Qt only. Whether an icon will actually *appear* is a Linux-desktop question
answered by ``adapters/linux/tray_probe``; this module imports no DBus and branches on no OS
(constitution Principle II, contract T-12).

The icon is deliberately **not** a live usage indicator. Painting GPU usage into it would
require sampling continuously while hidden, contradicting the rule that sampling stops when
nothing is displayed and turning a monitor into a permanent background load (FR-032, SC-016).
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

__all__ = ["TrayPresence"]

_log = logging.getLogger(__name__)


class TrayPresence(QObject):
    """The tray icon and its menu. Owns no sampling and no window."""

    show_requested = Signal()
    pause_toggled = Signal(bool)
    quit_requested = Signal()

    def __init__(self, icon: QIcon, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setToolTip("GPUM — GPU monitor")

        menu = QMenu()
        self._show_action = QAction("Show GPUM", self)
        self._show_action.triggered.connect(self.show_requested.emit)
        menu.addAction(self._show_action)

        self._pause_action = QAction("Pause updates", self)
        self._pause_action.setCheckable(True)
        self._pause_action.toggled.connect(self.pause_toggled.emit)
        menu.addAction(self._pause_action)

        menu.addSeparator()

        self._quit_action = QAction("Quit", self)
        self._quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(self._quit_action)

        self._tray.setContextMenu(menu)
        self._menu = menu
        self._tray.activated.connect(self._on_activated)

    def show(self) -> None:
        self._tray.show()

    def hide(self) -> None:
        self._tray.hide()

    @property
    def visible(self) -> bool:
        return self._tray.isVisible()

    def set_paused(self, paused: bool) -> None:
        """Reflect state set elsewhere without re-emitting and looping."""
        was_blocked = self._pause_action.blockSignals(True)
        self._pause_action.setChecked(paused)
        self._pause_action.setText("Resume updates" if paused else "Pause updates")
        self._pause_action.blockSignals(was_blocked)

    def notify_closed_to_tray(self) -> None:
        """The one-time disclosure that closing did not quit (FR-030).

        Shown once per user rather than once per session — "close doesn't close" is disliked
        mainly because it is usually undisclosed.
        """
        if not self._tray.isVisible():
            return
        self._tray.showMessage(
            "GPUM is still running",
            "The window closed but GPUM is still in your status area. "
            "Use its menu to reopen or quit.",
            QSystemTrayIcon.MessageIcon.Information,
            5000,
        )

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_requested.emit()
