"""Autostart fallback for platforms without an implementation (research D-07).

Linux is the only supported platform, so in practice this is what runs when GPUM is started
somewhere unsupported. It exists so that "unsupported" still means a truthful answer rather
than an exception or a silent lie.

Reports the feature as unavailable and does nothing, rather than raising or — worse — appearing
to succeed. A toggle that writes something no platform reads and then reports "enabled" is the
fault this module exists to make impossible: the settings dialog can always ask, and always
gets a truthful answer.
"""

from __future__ import annotations

import pathlib

__all__ = ["autostart_path", "disable_autostart", "enable_autostart", "is_autostart_enabled"]


def autostart_path() -> pathlib.PurePath:
    """No location, stated as such. The dialog discloses this to the user."""
    return pathlib.PurePath("(start-at-login is not supported on this platform)")


def is_autostart_enabled() -> bool:
    return False


def enable_autostart() -> pathlib.PurePath:
    """Deliberately a no-op. Returning the "location" keeps the contract shape without
    implying anything was written."""
    return autostart_path()


def disable_autostart() -> None:
    return None
