"""Platform adapters — the only place in the codebase permitted to branch on the OS.

Constitution Principle II: feature code contains no OS conditionals, and a platform that
cannot supply a capability degrades visibly rather than being forked around. The selection
below is the single OS switch in the application.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from gpum.adapters.base import ProcessAttributionProvider, ProcessIdentityProvider

__all__ = [
    "platform_autostart",
    "platform_attribution_provider",
    "platform_identity_provider",
    "present_gpus",
    "tray_availability",
]


def platform_autostart():
    """Start-at-login for this platform (feature 007, research D-06/D-07).

    Every implementation exposes ``is_autostart_enabled``, ``enable_autostart``,
    ``disable_autostart`` and ``autostart_path``, so the settings dialog needs no platform
    knowledge — which is the point. ``ui/app.py`` previously imported the *Linux* module
    directly and unconditionally, so on Windows the toggle disclosed a
    ``~/.config/autostart`` path, wrote a file nothing reads, and reported success. Claiming a
    capability that is absent is the same fault as rendering an unmeasured metric as zero.

    Platforms without an implementation get a null object that reports the feature as
    unavailable rather than pretending it worked.
    """
    if sys.platform.startswith("linux"):
        from gpum.adapters.linux import autostart

        return autostart
    if sys.platform.startswith("win"):
        from gpum.adapters.windows import autostart

        return autostart

    from gpum.adapters import null_autostart

    return null_autostart


def tray_availability(qt_reports_available: bool):
    """Whether a status-area icon will actually appear (FR-034).

    Platforms without an implementation fall back to trusting Qt, which is the correct default
    where Qt's answer is reliable; the override exists because it is not on Linux desktops.
    """
    if sys.platform.startswith("linux"):
        from gpum.adapters.linux.tray_probe import probe_tray

        return probe_tray(qt_reports_available)

    from gpum.adapters.linux.tray_probe import TrayAvailability

    return TrayAvailability(
        usable=qt_reports_available,
        reason=None if qt_reports_available else "no status area on this platform",
        qt_reports_available=qt_reports_available,
    )


def present_gpus() -> list[object]:
    """GPUs physically present, whether or not a backend can monitor them (FR-015).

    Returns an empty list on platforms without an implementation — the tool then reports only
    what backends found, which is a smaller claim rather than a wrong one.
    """
    if sys.platform.startswith("linux"):
        from gpum.adapters.linux.pci_devices import enumerate_present_gpus

        return list(enumerate_present_gpus())
    return []


def platform_identity_provider() -> ProcessIdentityProvider:
    """PID → name/owner/container for this platform."""
    if sys.platform.startswith("linux"):
        from gpum.adapters.linux.identity import LinuxIdentityProvider

        return LinuxIdentityProvider()
    if sys.platform.startswith("win"):
        from gpum.adapters.windows.identity import WindowsIdentityProvider

        return WindowsIdentityProvider()

    from gpum.adapters.null import NullIdentityProvider

    return NullIdentityProvider()


def platform_attribution_provider() -> ProcessAttributionProvider | None:
    """A vendor-neutral, OS-supplied attribution source, where one exists.

    Linux has DRM ``fdinfo`` and Windows has the GPU performance counters, but neither is
    implemented in this release — NVIDIA supplies attribution directly on Linux, which is this
    release's target (research D-03). Returning ``None`` is correct and supported: devices are
    then marked with an explicit reason rather than shown with an empty process list.
    """
    return None
