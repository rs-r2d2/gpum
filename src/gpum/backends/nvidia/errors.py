"""NVML error codes mapped to availability and backend states.

Kept separate from the NVML wrapper so it is pure data: importable and testable with no
driver and no ``pynvml`` installed (constitution Principle IV).

The distinctions here are the reason FR-017 is satisfiable at all. "Not supported", "no
permission", and "driver not loaded" produce three different user-facing messages; a generic
except-and-shrug would collapse them into one useless one.
"""

from __future__ import annotations

from gpum.core.models import Availability, BackendState, LimitReason

__all__ = [
    "availability_for",
    "backend_state_for",
    "is_device_gone",
    "limit_reason_for",
]

# NVML return codes (nvml.h). Defined here rather than imported so this module stays usable
# without the binding installed.
NVML_SUCCESS = 0
NVML_ERROR_UNINITIALIZED = 1
NVML_ERROR_INVALID_ARGUMENT = 2
NVML_ERROR_NOT_SUPPORTED = 3
NVML_ERROR_NO_PERMISSION = 4
NVML_ERROR_NOT_FOUND = 6
NVML_ERROR_INSUFFICIENT_SIZE = 7
NVML_ERROR_DRIVER_NOT_LOADED = 9
NVML_ERROR_TIMEOUT = 10
NVML_ERROR_IRQ_ISSUE = 11
NVML_ERROR_LIBRARY_NOT_FOUND = 12
NVML_ERROR_FUNCTION_NOT_FOUND = 13
NVML_ERROR_GPU_IS_LOST = 15
NVML_ERROR_RESET_REQUIRED = 16
NVML_ERROR_UNKNOWN = 999

_GONE = frozenset({NVML_ERROR_GPU_IS_LOST, NVML_ERROR_NOT_FOUND, NVML_ERROR_UNINITIALIZED})

_AVAILABILITY: dict[int, tuple[Availability, str]] = {
    NVML_ERROR_NOT_SUPPORTED: (
        Availability.UNSUPPORTED,
        "not reported by this GPU or driver",
    ),
    NVML_ERROR_FUNCTION_NOT_FOUND: (
        Availability.UNSUPPORTED,
        "not supported by the installed driver version",
    ),
    NVML_ERROR_NO_PERMISSION: (
        Availability.PERMISSION_DENIED,
        "requires elevated privileges",
    ),
    NVML_ERROR_GPU_IS_LOST: (Availability.DEGRADED, "the GPU is no longer accessible"),
    NVML_ERROR_RESET_REQUIRED: (Availability.DEGRADED, "the GPU requires a reset"),
    NVML_ERROR_TIMEOUT: (Availability.DEGRADED, "the driver did not respond in time"),
    NVML_ERROR_IRQ_ISSUE: (Availability.DEGRADED, "the driver reported an interrupt issue"),
}

_BACKEND_STATE: dict[int, tuple[BackendState, str]] = {
    NVML_ERROR_DRIVER_NOT_LOADED: (
        BackendState.DRIVER_MISSING,
        "NVIDIA driver is not loaded on this machine",
    ),
    NVML_ERROR_LIBRARY_NOT_FOUND: (
        BackendState.LIBRARY_MISSING,
        "NVIDIA management library (libnvidia-ml) was not found",
    ),
    NVML_ERROR_UNINITIALIZED: (
        BackendState.DRIVER_MISSING,
        "NVIDIA management library could not be initialised",
    ),
    NVML_ERROR_NO_PERMISSION: (
        BackendState.ERROR,
        "Insufficient permission to query NVIDIA devices",
    ),
}


def availability_for(code: int) -> tuple[Availability, str]:
    """Map an NVML error to a metric availability and a short reason.

    Never returns ``AVAILABLE``: an error is never quietly turned into a measurement (SC-007).
    """
    mapped = _AVAILABILITY.get(code)
    if mapped is not None:
        return mapped
    return Availability.UNSUPPORTED, f"the driver reported error {code}"


def backend_state_for(code: int) -> tuple[BackendState, str]:
    """Map an NVML error to a backend state and a message fit to show a user (SC-006)."""
    mapped = _BACKEND_STATE.get(code)
    if mapped is not None:
        return mapped
    return BackendState.ERROR, f"NVIDIA management library reported error {code}"


def is_device_gone(code: int) -> bool:
    """Whether this error means the device vanished, so the sampler re-enumerates (FR-020)."""
    return code in _GONE


# Clock-throttle reason bits (nvml.h). Only the two that are actionable on desktop hardware are
# surfaced; the mask carries several more (sync boost, display clock, and others) that are rare
# and would add noise to a field whose whole value is being immediately useful.
NVML_CLOCKS_THROTTLE_REASON_NONE = 0x0
NVML_CLOCKS_THROTTLE_REASON_GPU_IDLE = 0x1
NVML_CLOCKS_THROTTLE_REASON_APPLICATIONS_CLOCKS_SETTING = 0x2
NVML_CLOCKS_THROTTLE_REASON_SW_POWER_CAP = 0x4
NVML_CLOCKS_THROTTLE_REASON_HW_SLOWDOWN = 0x8
NVML_CLOCKS_THROTTLE_REASON_SYNC_BOOST = 0x10
NVML_CLOCKS_THROTTLE_REASON_SW_THERMAL_SLOWDOWN = 0x20
NVML_CLOCKS_THROTTLE_REASON_HW_THERMAL_SLOWDOWN = 0x40
NVML_CLOCKS_THROTTLE_REASON_HW_POWER_BRAKE_SLOWDOWN = 0x80

_POWER_BITS = (
    NVML_CLOCKS_THROTTLE_REASON_SW_POWER_CAP
    | NVML_CLOCKS_THROTTLE_REASON_HW_POWER_BRAKE_SLOWDOWN
)
_THERMAL_BITS = (
    NVML_CLOCKS_THROTTLE_REASON_SW_THERMAL_SLOWDOWN
    | NVML_CLOCKS_THROTTLE_REASON_HW_THERMAL_SLOWDOWN
)
#: Idle and application-clock settings are not the GPU being "held back" in any sense the user
#: would act on, so they read as unconstrained.
_BENIGN_BITS = (
    NVML_CLOCKS_THROTTLE_REASON_GPU_IDLE
    | NVML_CLOCKS_THROTTLE_REASON_APPLICATIONS_CLOCKS_SETTING
)


def limit_reason_for(mask: int | None) -> LimitReason:
    """Decode a throttle bitmask into a user-facing reason (FR-017 - FR-019).

    ``None`` means the query failed, which is UNKNOWN — distinct from a successful read of
    zero, which is a genuine measurement that nothing is limiting the device.
    """
    if mask is None:
        return LimitReason.UNKNOWN
    if mask & _POWER_BITS:
        return LimitReason.POWER
    if mask & _THERMAL_BITS:
        return LimitReason.THERMAL
    remaining = mask & ~_BENIGN_BITS
    if remaining:
        return LimitReason.OTHER
    return LimitReason.NONE
