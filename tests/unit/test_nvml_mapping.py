"""T032: NVML error mapping (contract C-02, C-06).

Runs with no driver and no `pynvml` installed — the mapping is pure data, which is the point
of keeping it in its own module (Principle IV).
"""

import pytest

from gpum.backends.nvidia import errors
from gpum.core.models import Availability, BackendState


class TestErrorToAvailability:
    def test_not_supported_maps_to_unsupported(self) -> None:
        av, reason = errors.availability_for(errors.NVML_ERROR_NOT_SUPPORTED)
        assert av is Availability.UNSUPPORTED
        assert reason

    def test_no_permission_maps_to_permission_denied(self) -> None:
        av, reason = errors.availability_for(errors.NVML_ERROR_NO_PERMISSION)
        assert av is Availability.PERMISSION_DENIED
        assert "privile" in reason.lower()

    def test_unknown_code_still_produces_a_reason(self) -> None:
        """FR-017: never a bare failure with no explanation."""
        av, reason = errors.availability_for(999_999)
        assert av is not Availability.AVAILABLE
        assert reason

    @pytest.mark.parametrize(
        "code",
        [
            errors.NVML_ERROR_NOT_SUPPORTED,
            errors.NVML_ERROR_NO_PERMISSION,
            errors.NVML_ERROR_GPU_IS_LOST,
        ],
    )
    def test_no_mapping_ever_yields_available(self, code: int) -> None:
        """An error must never be quietly turned into a measurement (SC-007)."""
        av, _ = errors.availability_for(code)
        assert av is not Availability.AVAILABLE


class TestErrorToBackendState:
    def test_driver_not_loaded_is_distinct_from_library_missing(self) -> None:
        driver = errors.backend_state_for(errors.NVML_ERROR_DRIVER_NOT_LOADED)
        assert driver[0] is BackendState.DRIVER_MISSING
        assert driver[0] is not BackendState.LIBRARY_MISSING

    def test_uninitialized_maps_to_driver_missing(self) -> None:
        state, detail = errors.backend_state_for(errors.NVML_ERROR_UNINITIALIZED)
        assert state in {BackendState.DRIVER_MISSING, BackendState.ERROR}
        assert detail

    def test_every_state_carries_a_user_facing_detail(self) -> None:
        """SC-006 requires a clear, actionable message for each case."""
        for code in (
            errors.NVML_ERROR_DRIVER_NOT_LOADED,
            errors.NVML_ERROR_NO_PERMISSION,
            errors.NVML_ERROR_UNINITIALIZED,
            424242,
        ):
            _, detail = errors.backend_state_for(code)
            assert detail and detail[0].isupper()


class TestGoneDetection:
    def test_gpu_is_lost_is_recognised_as_gone(self) -> None:
        """FR-020: a vanished device triggers re-enumeration, not an error dialog."""
        assert errors.is_device_gone(errors.NVML_ERROR_GPU_IS_LOST)
        assert errors.is_device_gone(errors.NVML_ERROR_NOT_FOUND)
        assert not errors.is_device_gone(errors.NVML_ERROR_NOT_SUPPORTED)
