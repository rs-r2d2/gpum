"""Will a status-area icon actually appear? (research D-04, contracts/tray-contract.md)

This exists because ``QSystemTrayIcon.isSystemTrayAvailable()`` cannot be trusted. On a stock
GNOME session — no AppIndicator extension — it returns ``True`` while the desktop silently
drops the icon. Qt reports the capability, the desktop discards it, and the user is left with a
running program they can neither see nor recover. That is the specific failure FR-034 and
SC-015 forbid.

The signal that actually correlates with an icon being displayed is whether anything owns
``org.kde.StatusNotifierWatcher`` on the session bus, which is the protocol modern desktops use.
Measured on the development machine (Ubuntu 24.04, GNOME/X11): the watcher is present and the
``ubuntu-appindicators`` extension is installed, so the tray genuinely works there.

Lives under ``adapters/linux`` because the question is Linux-desktop-specific. The tray
*widget* is cross-platform Qt and stays in ``ui/`` (constitution Principle II).
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass

__all__ = ["TrayAvailability", "probe_tray"]

_log = logging.getLogger(__name__)

_WATCHER_NAME = "org.kde.StatusNotifierWatcher"

#: Must not delay startup past SC-001's 3-second budget.
_PROBE_TIMEOUT_S = 0.5


@dataclass(frozen=True, slots=True)
class TrayAvailability:
    usable: bool
    reason: str | None = None
    watcher_present: bool = False
    qt_reports_available: bool = False
    probe_error: str | None = None

    def __post_init__(self) -> None:
        if not self.usable and not self.reason:
            raise ValueError("an unusable tray must explain itself")


def probe_tray(qt_reports_available: bool) -> TrayAvailability:
    """Decide whether a tray icon will be displayed. Never raises.

    ``qt_reports_available`` is passed in rather than queried here so this module stays free of
    Qt, keeping the OS-specific check and the widget cleanly separated.

    The rule is a conjunction, deliberately conservative: a false negative costs the user an
    icon they could have had, while a false positive costs them a program they cannot recover.
    """
    watcher_present, probe_error = _watcher_owned()

    if not qt_reports_available:
        return TrayAvailability(
            usable=False,
            reason="this desktop session does not provide a status area",
            watcher_present=watcher_present,
            qt_reports_available=False,
            probe_error=probe_error,
        )

    if not watcher_present:
        return TrayAvailability(
            usable=False,
            reason=(
                "no status-area host is running on this desktop. On GNOME this usually means "
                "the AppIndicator extension is not enabled."
            ),
            watcher_present=False,
            qt_reports_available=True,
            probe_error=probe_error,
        )

    return TrayAvailability(
        usable=True,
        watcher_present=True,
        qt_reports_available=True,
        probe_error=probe_error,
    )


def _watcher_owned() -> tuple[bool, str | None]:
    """Whether anything owns the StatusNotifierWatcher name on the session bus.

    Uses ``gdbus`` rather than a DBus binding so the application takes no extra runtime
    dependency for a single startup question. A probe failure is reported, never assumed
    successful.
    """
    if not os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
        return False, "no session bus is available"

    gdbus = shutil.which("gdbus")
    if gdbus is None:
        return False, "gdbus is not installed, so the status area could not be checked"

    try:
        result = subprocess.run(
            [
                gdbus,
                "call",
                "--session",
                "--dest",
                "org.freedesktop.DBus",
                "--object-path",
                "/org/freedesktop/DBus",
                "--method",
                "org.freedesktop.DBus.NameHasOwner",
                _WATCHER_NAME,
            ],
            capture_output=True,
            text=True,
            timeout=_PROBE_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        _log.debug("tray watcher probe failed", exc_info=True)
        return False, f"could not query the session bus: {exc}"

    if result.returncode != 0:
        return False, (result.stderr or "").strip() or "session bus query failed"

    return "true" in result.stdout.lower(), None
