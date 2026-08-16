"""Enumerate GPUs physically present, regardless of whether any backend can monitor them.

FR-015/SC-007: the tool must account for every GPU in the machine. Reporting only what a
backend can read would tell a user with an NVIDIA + AMD machine that they have one GPU, which
is a factual error about their hardware — the same class of dishonesty as rendering an
unavailable metric as zero.

Reads Linux DRM sysfs only. No privileges, no subprocess, no PCI database.
"""

from __future__ import annotations

import logging
import pathlib
from dataclasses import dataclass

from gpum.core.models import Vendor

__all__ = ["PresentGpu", "enumerate_present_gpus"]

_log = logging.getLogger(__name__)

_DRM_ROOT = "/sys/class/drm"

#: PCI SIG vendor IDs.
_VENDOR_IDS = {
    0x10DE: Vendor.NVIDIA,
    0x1002: Vendor.AMD,
    0x1022: Vendor.AMD,
    0x8086: Vendor.INTEL,
}

#: PCI class 0x03xxxx is "Display controller".
_DISPLAY_CLASS_PREFIX = 0x03


@dataclass(frozen=True, slots=True)
class PresentGpu:
    vendor: Vendor
    pci_address: str
    device_id: str

    @property
    def label(self) -> str:
        return f"{self.vendor.name} GPU at {self.pci_address}"


def enumerate_present_gpus(drm_root: str = _DRM_ROOT) -> list[PresentGpu]:
    """Every display controller the kernel knows about. Never raises."""
    root = pathlib.Path(drm_root)
    if not root.is_dir():
        return []

    found: dict[str, PresentGpu] = {}
    for card in sorted(root.glob("card[0-9]*")):
        # Skip connector entries such as card1-DP-1.
        if "-" in card.name:
            continue
        device = card / "device"
        try:
            vendor_id = _read_hex(device / "vendor")
            class_id = _read_hex(device / "class")
            device_id = _read_hex(device / "device")
        except (OSError, ValueError):
            continue
        if vendor_id is None or class_id is None:
            continue
        if (class_id >> 16) != _DISPLAY_CLASS_PREFIX:
            continue
        try:
            address = device.resolve().name
        except OSError:
            address = card.name
        found[address] = PresentGpu(
            vendor=_VENDOR_IDS.get(vendor_id, Vendor.UNKNOWN),
            pci_address=address,
            device_id=f"{device_id:04x}" if device_id is not None else "",
        )
    return list(found.values())


def _read_hex(path: pathlib.Path) -> int | None:
    try:
        text = path.read_text().strip()
    except OSError:
        return None
    if not text:
        return None
    return int(text, 16)
