"""T023: behaviour proven on real hardware, kept under test on machines without it (FR-011).

These fixtures were captured from an RTX 5060 Ti on driver 580.159.03. They exist so that what
the hardware suite verifies once stays verified everywhere (constitution Principle IV).
"""

from __future__ import annotations

import json
import pathlib

import pytest

from gpum.backends.nvidia import errors

_FIXTURE_DIR = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "nvml"
FIXTURES = sorted(_FIXTURE_DIR.glob("*.json"))


@pytest.fixture(params=FIXTURES, ids=lambda p: p.stem)
def capture(request: pytest.FixtureRequest) -> dict:
    return json.loads(request.param.read_text())


class TestCapturedShape:
    def test_fixtures_exist(self) -> None:
        assert FIXTURES, "no NVML captures recorded; FR-011 requires at least one"

    def test_driver_version_recorded(self, capture: dict) -> None:
        assert capture["driver_version"]

    def test_devices_have_stable_identity(self, capture: dict) -> None:
        for device in capture["devices"]:
            assert device["uuid"].startswith("GPU-"), "UUID is the identity source (D-07)"
            assert device["pci_bus_id"]


class TestMemorySemantics:
    def test_v1_used_exceeds_v2_used_by_reserved(self, capture: dict) -> None:
        """The bug this feature caught, frozen as a fixture assertion.

        v1 `used` is total-free and folds in driver-reserved memory; v2 separates it. On this
        capture the difference is the reason our reported figure was nearly double
        nvidia-smi's before the fix.
        """
        for device in capture["devices"]:
            if "memory_v2" not in device:
                continue
            v1, v2 = device["memory_v1"], device["memory_v2"]
            assert v1["used"] > v2["used"], "expected v1 to overstate used memory"
            assert v1["used"] - v2["used"] == pytest.approx(v2["reserved"], abs=2 * 1024**2)

    def test_v2_used_plus_free_plus_reserved_equals_total(self, capture: dict) -> None:
        for device in capture["devices"]:
            if "memory_v2" not in device:
                continue
            v2 = device["memory_v2"]
            assert v2["used"] + v2["free"] + v2["reserved"] == pytest.approx(
                v2["total"], rel=0.01
            )

    def test_memory_values_are_bytes(self, capture: dict) -> None:
        for device in capture["devices"]:
            assert device["memory_v1"]["total"] > 1024**3, "totals must be bytes, not MiB"


class TestProcessCapture:
    def test_processes_carry_memory_on_linux(self, capture: dict) -> None:
        for device in capture["devices"]:
            real = [p for p in device["processes"] if "pid" in p]
            if not real:
                continue
            assert any(p["usedGpuMemory"] is not None for p in real), (
                "NVML supplies per-process memory on Linux"
            )

    def test_no_process_memory_is_zero_when_present(self, capture: dict) -> None:
        """A real GPU process holding literally zero bytes would be suspicious; the WDDM case
        reports None, not 0, which is the distinction SC-007 depends on."""
        for device in capture["devices"]:
            for process in device["processes"]:
                if process.get("usedGpuMemory") is not None:
                    assert process["usedGpuMemory"] > 0


class TestErrorSurface:
    def test_error_responses_captured(self, capture: dict) -> None:
        assert capture["error_responses"], "FR-011 requires failure responses too"

    def test_captured_error_codes_map_to_states(self, capture: dict) -> None:
        for record in capture["error_responses"].values():
            code = record.get("code")
            if code is None:
                continue
            state, detail = errors.backend_state_for(int(code))
            assert detail
            availability, reason = errors.availability_for(int(code))
            assert reason

    def test_mig_query_on_consumer_card_is_not_an_error_state(self, capture: dict) -> None:
        """Consumer cards raise NOT_SUPPORTED for the MIG query; that means "not partitioned",
        not "unknown", and must not disable the device."""
        for device in capture["devices"]:
            err = device.get("mig_mode_error")
            if err and err.get("code") is not None:
                assert int(err["code"]) in {
                    errors.NVML_ERROR_NOT_SUPPORTED,
                    errors.NVML_ERROR_INVALID_ARGUMENT,
                    errors.NVML_ERROR_FUNCTION_NOT_FOUND,
                }
