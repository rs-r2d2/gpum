"""Scripted scenarios for the fake backend (quickstart.md V-1..V-5).

These deliberately model devices NVML *cannot* produce — a device with no utilization support,
a device with no process attribution, a MIG device, a device that hangs on demand — so that an
NVML-shaped assumption in `core` or `ui` fails a test rather than passing unnoticed
(plan.md § Principle I mitigations).
"""

from __future__ import annotations

from dataclasses import dataclass

from gpum.core.models import Availability, Vendor

__all__ = ["DeviceSpec", "Scenario", "SCENARIOS"]


@dataclass(frozen=True, slots=True)
class DeviceSpec:
    key: str
    name: str
    vendor: Vendor = Vendor.NVIDIA
    memory_total: int = 8 * 1024**3
    memory_used: int = 2 * 1024**3
    utilization: int | None = 35
    supported: bool = True
    unsupported_reason: str | None = None
    #: Availability of per-process attribution for this device.
    attribution: Availability = Availability.AVAILABLE
    attribution_reason: str | None = None
    hangs: bool = False
    process_count: int = 2


@dataclass(frozen=True, slots=True)
class Scenario:
    name: str
    devices: tuple[DeviceSpec, ...] = ()
    churn: bool = False
    description: str = ""


def _gib(n: float) -> int:
    return int(n * 1024**3)


SCENARIOS: dict[str, Scenario] = {
    "two-nvidia": Scenario(
        name="two-nvidia",
        description="Two healthy NVIDIA GPUs — the happy path (V-1).",
        devices=(
            DeviceSpec("GPU-fake-0001", "GeForce RTX 4090", memory_total=_gib(24),
                       memory_used=_gib(6), utilization=42),
            DeviceSpec("GPU-fake-0002", "GeForce RTX 4090", memory_total=_gib(24),
                       memory_used=_gib(11), utilization=88),
        ),
    ),
    "processes-churn": Scenario(
        name="processes-churn",
        description="Processes appearing and disappearing every cycle (V-2).",
        churn=True,
        devices=(
            DeviceSpec("GPU-fake-0001", "GeForce RTX 4090", memory_total=_gib(24),
                       memory_used=_gib(9), process_count=5),
        ),
    ),
    "no-attribution": Scenario(
        name="no-attribution",
        description="Device metrics work, per-process data does not — the NVIDIA/WDDM shape "
                    "(V-3). The UI must explain, not show an empty list.",
        devices=(
            DeviceSpec(
                "GPU-fake-0001",
                "GeForce RTX 4080",
                memory_total=_gib(16),
                memory_used=_gib(5),
                attribution=Availability.UNSUPPORTED,
                attribution_reason="per-process memory is not reported under this driver model",
                process_count=0,
            ),
        ),
    ),
    "metrics-unsupported": Scenario(
        name="metrics-unsupported",
        description="A device that cannot report utilization at all (V-3). NVML always can, "
                    "so this shape exists purely to break NVML-shaped assumptions.",
        devices=(
            DeviceSpec(
                "GPU-fake-0001",
                "Integrated Graphics",
                vendor=Vendor.INTEL,
                memory_total=_gib(2),
                memory_used=_gib(1),
                utilization=None,
            ),
        ),
    ),
    "one-device-hangs": Scenario(
        name="one-device-hangs",
        description="One device blocks on query while others stay healthy (V-5).",
        devices=(
            DeviceSpec("GPU-fake-0001", "GeForce RTX 4090", memory_used=_gib(3)),
            DeviceSpec("GPU-fake-hang", "GeForce RTX 3090", memory_used=_gib(7), hangs=True),
            DeviceSpec("GPU-fake-0003", "GeForce RTX 4070", memory_used=_gib(2)),
        ),
    ),
    "mig-device": Scenario(
        name="mig-device",
        description="A partitioned GPU, which must be reported unsupported (FR-028).",
        devices=(
            DeviceSpec(
                "GPU-fake-mig",
                "A100-SXM4-40GB",
                supported=False,
                unsupported_reason="partitioned GPU (MIG) not supported",
                attribution=Availability.NOT_APPLICABLE,
                process_count=0,
            ),
        ),
    ),
    "multi-vendor-degraded": Scenario(
        name="multi-vendor-degraded",
        description="Mixed vendors in one list, one of them degraded (V-1, US3).",
        devices=(
            DeviceSpec("GPU-fake-nv", "GeForce RTX 4090", vendor=Vendor.NVIDIA,
                       memory_total=_gib(24), memory_used=_gib(8)),
            DeviceSpec("GPU-fake-amd", "Radeon RX 7900 XTX", vendor=Vendor.AMD,
                       memory_total=_gib(24), memory_used=_gib(4), utilization=12),
            DeviceSpec("GPU-fake-intel", "Arc A770", vendor=Vendor.INTEL,
                       memory_total=_gib(16), memory_used=_gib(2), utilization=None,
                       hangs=True),
        ),
    ),
    "empty": Scenario(
        name="empty",
        description="No devices at all — the tool must stay usable (FR-018, V-4).",
        devices=(),
    ),
}

DEFAULT_SCENARIO = "two-nvidia"
