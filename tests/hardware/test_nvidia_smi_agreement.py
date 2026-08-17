"""T013, T029: our numbers vs nvidia-smi, on real hardware (SC-003, SC-004, SC-010).

The first check in the project against reality rather than a simulation.
"""

from __future__ import annotations

import contextlib
import os
import statistics
import subprocess
import time

import pytest

from gpum.core.engine import SamplingEngine
from gpum.registry import (
    build_backends,
    select_attribution_provider,
    select_identity_provider,
)
from tests.hardware.loadgen import gpu_load

MIB = 1024 * 1024
#: Memory moves continuously, so agreement is only meaningful for near-simultaneous reads.
TOLERANCE_PCT = 5.0


def _smi_rows() -> dict[str, dict[str, int]]:
    out = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=uuid,memory.total,memory.used",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    ).stdout
    rows = {}
    for line in out.strip().splitlines():
        uuid, total, used = (p.strip() for p in line.split(","))
        rows[uuid] = {"total": int(float(total)) * MIB, "used": int(float(used)) * MIB}
    return rows


def _smi_pids() -> set[int]:
    plain = subprocess.run(
        ["nvidia-smi"], capture_output=True, text=True, timeout=15, check=False
    ).stdout
    pids: set[int] = set()
    seen_header = False
    for line in plain.splitlines():
        if "Processes:" in line:
            seen_header = True
            continue
        if not seen_header or not line.startswith("|"):
            continue
        fields = line.strip("| \t").split()
        for index, value in enumerate(fields):
            if value in {"G", "C", "C+G"} and index >= 1:
                for candidate in fields[:index]:
                    if candidate.isdigit() and len(candidate) >= 2:
                        pids.add(int(candidate))
                break
    return pids


@pytest.fixture
def engine() -> SamplingEngine:
    backends = build_backends("nvidia")
    eng = SamplingEngine(
        backends,
        attribution_provider=select_attribution_provider(backends),
        identity_provider=select_identity_provider(),
    )
    if not eng.sample().devices:
        eng.shutdown()
        pytest.skip("no NVIDIA devices present")
    yield eng
    eng.shutdown()


class TestMemoryAgreement:
    def test_total_memory_matches_exactly(self, engine: SamplingEngine) -> None:
        """Total is static — any disagreement is a unit bug, not sampling drift."""
        theirs = _smi_rows()
        for device in engine.sample().devices:
            if device.id.key not in theirs:
                continue
            assert abs(device.memory_total.value - theirs[device.id.key]["total"]) < 2 * MIB

    def test_used_memory_within_tolerance(self, engine: SamplingEngine) -> None:
        """SC-003. This is the assertion that caught driver-reserved memory being reported as
        used — a ~90% overstatement before the v2 memory struct was adopted."""
        worst = 0.0
        for _ in range(10):
            snapshot = engine.sample()
            theirs = _smi_rows()
            for device in snapshot.devices:
                row = theirs.get(device.id.key)
                if row is None or not device.memory_used.is_measurement:
                    continue
                if not row["used"]:
                    continue
                deviation = 100.0 * abs(device.memory_used.value - row["used"]) / row["used"]
                worst = max(worst, deviation)
            time.sleep(0.5)
        assert worst <= TOLERANCE_PCT, f"worst deviation {worst:.2f}% exceeds {TOLERANCE_PCT}%"

    def test_used_never_exceeds_total(self, engine: SamplingEngine) -> None:
        for device in engine.sample().devices:
            if device.memory_used.is_measurement and device.memory_total.is_measurement:
                assert device.memory_used.value <= device.memory_total.value


class TestProcessAgreement:
    def test_every_smi_process_appears(self, engine: SamplingEngine) -> None:
        """SC-004: 100% of processes nvidia-smi reports must appear in our list."""
        theirs = _smi_pids()
        if not theirs:
            pytest.skip("no GPU processes running")
        ours = {p.pid for p in engine.sample().processes}
        missing = theirs - ours
        assert not missing, f"nvidia-smi reports GPU processes we do not: {sorted(missing)}"

    def test_processes_are_named(self, engine: SamplingEngine) -> None:
        snapshot = engine.sample()
        if not snapshot.processes:
            pytest.skip("no GPU processes running")
        named = [p for p in snapshot.processes if p.name]
        assert named, "no GPU process could be identified"

    def test_process_memory_is_measured_on_linux(self, engine: SamplingEngine) -> None:
        """NVML supplies per-process memory on the supported target. Where a driver does not, it
        is reported honestly rather than as zero."""
        snapshot = engine.sample()
        if not snapshot.processes:
            pytest.skip("no GPU processes running")
        measured = [p for p in snapshot.processes if p.memory_used.is_measurement]
        assert measured, "no per-process memory obtained on Linux"
        for process in snapshot.processes:
            if not process.memory_used.is_measurement:
                assert process.memory_used.value is None
                assert process.memory_used.reason


#: SC-010 specifies a 10-minute observation. Ten minutes in the routine suite would mean the
#: hardware suite stops being run, so the default is a short varying-load run and the full
#: duration is opted into: ``GPUM_AGREEMENT_SECONDS=600 pytest -m hardware -k utilization``.
AGREEMENT_SECONDS = float(os.environ.get("GPUM_AGREEMENT_SECONDS", "120"))
#: Load is switched on and off in blocks this long, so the run spans both states.
LOAD_BLOCK_S = 20.0
#: Readings taken within this long of a load transition are recorded but not asserted on.
#:
#: Utilization is a measure *over a window*, not at an instant: NVML reports the fraction of a
#: driver-internal sampling period during which a kernel was resident. Immediately after load
#: starts or stops, two reads a few hundred milliseconds apart legitimately differ by most of
#: the range — that is the metric moving, not the two tools disagreeing. SC-010 is about
#: agreement, so the comparison is made once the figure has settled.
SETTLE_S = 6.0
UTILIZATION_TOLERANCE_PP = 5.0


def _bracket_deviation(ours: float, before: float, after: float) -> float:
    """How far our reading falls outside the interval the vendor tool spanned around it.

    The same windowing that makes ``SETTLE_S`` necessary applies away from transitions too: an
    "idle" desktop GPU is not idle, and a compositor or browser burst between our read and the
    vendor tool's read moves the metric by tens of points. Measured on this project's reference
    hardware, ``nvidia-smi`` disagrees with *itself* by up to 4 pp across a 100 ms gap while
    agreeing with us exactly, so a single instantaneous comparison charges that movement to the
    tools rather than to the clock.

    Reading the vendor tool either side of ours turns "the metric moved" into a bracket rather
    than a disagreement: a value inside it is consistent with everything observed, and a wrong
    figure still lands outside and still fails. This measures agreement, which is what SC-010
    asks for, instead of measuring how busy the desktop was.
    """
    low, high = min(before, after), max(before, after)
    if low <= ours <= high:
        return 0.0
    return ours - high if ours > high else low - ours


def _smi_utilization() -> dict[str, tuple[float, float]]:
    out = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=uuid,utilization.gpu,utilization.memory",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    ).stdout
    rows: dict[str, tuple[float, float]] = {}
    for line in out.strip().splitlines():
        uuid, gpu, mem = (p.strip() for p in line.split(","))
        rows[uuid] = (float(gpu), float(mem))
    return rows


class TestUtilizationAgreement:
    """T029 / SC-010: reported utilization tracks nvidia-smi under varying load.

    This is the assertion feature 006 most needed and least had. Every other utilization test
    in the project runs against a simulation, where the number is whatever the fake backend was
    told to say; this is the only place the figure is checked against the hardware.
    """

    def test_t029_utilization_agrees_under_varying_load(self, engine) -> None:
        deadline = time.monotonic() + AGREEMENT_SECONDS
        block_started = time.monotonic()
        loading = True
        steady: list[tuple[float, float, float]] = []  # ours, theirs, deviation
        transitional = 0
        observed_high = observed_low = False

        while time.monotonic() < deadline:
            block_end = min(block_started + LOAD_BLOCK_S, deadline)
            context = gpu_load(LOAD_BLOCK_S + 5) if loading else contextlib.nullcontext()
            with context:
                # gpu_load() already waited for the kernel to launch; align the idle branch so
                # both states get the same settling treatment.
                transition_at = time.monotonic()
                while time.monotonic() < block_end:
                    # Bracket our reading: the vendor tool either side of it, as close together
                    # as three reads can be taken. See _bracket_deviation.
                    before = _smi_utilization()
                    snapshot = engine.sample()
                    after = _smi_utilization()
                    settled = time.monotonic() - transition_at >= SETTLE_S
                    for device in snapshot.devices:
                        first, second = before.get(device.id.key), after.get(device.id.key)
                        if first is None or second is None:
                            continue
                        if not device.utilization_gpu.is_measurement:
                            continue
                        ours = float(device.utilization_gpu.value)
                        deviation = _bracket_deviation(ours, first[0], second[0])
                        if settled:
                            steady.append((ours, second[0], deviation))
                            observed_high = observed_high or second[0] >= 50
                            observed_low = observed_low or second[0] <= 20
                        else:
                            transitional += 1
                    time.sleep(1.0)
            loading = not loading
            block_started = time.monotonic()

        assert steady, "no settled samples were collected"
        worst = max(d for _, _, d in steady)
        mean = statistics.mean(d for _, _, d in steady)
        detail = (
            f"{len(steady)} settled samples ({transitional} discarded near transitions): "
            f"worst {worst:.1f} pp, mean {mean:.2f} pp outside the vendor bracket"
        )
        # Printed, not only asserted: SC-010 is a measurement, and the recorded number is what
        # makes a later re-run comparable rather than merely also-passing.
        print(f"\nSC-010 over {AGREEMENT_SECONDS:.0f}s: {detail}")
        assert observed_high, f"the load never registered, so nothing was varied — {detail}"
        assert observed_low, f"the GPU was never idle, so nothing was varied — {detail}"
        assert worst <= UTILIZATION_TOLERANCE_PP, f"SC-010 breached — {detail}"

    def test_t029_memory_interface_utilization_agrees(self, engine) -> None:
        """The figure feature 006 surfaced for the first time. It has never been compared
        against the vendor tool before, because it was never displayed.

        Bracketed like the compute figure above: memory-interface activity moves at least as
        fast, so a single instantaneous comparison measures the gap between two reads.
        """
        worst = 0.0
        compared = 0
        with gpu_load(20):
            for _ in range(12):
                before = _smi_utilization()
                snapshot = engine.sample()
                after = _smi_utilization()
                for device in snapshot.devices:
                    first, second = before.get(device.id.key), after.get(device.id.key)
                    if first is None or second is None:
                        continue
                    if not device.utilization_memory.is_measurement:
                        continue
                    ours = float(device.utilization_memory.value)
                    worst = max(worst, _bracket_deviation(ours, first[1], second[1]))
                    compared += 1
                time.sleep(1.0)
        assert compared, "memory-interface utilization was never available to compare"
        assert worst <= UTILIZATION_TOLERANCE_PP, f"worst deviation {worst:.1f} pp over {compared}"

    def test_t029_a_measured_zero_is_a_measurement(self, engine) -> None:
        """FR-011/FR-012 against reality: an idle GPU reports 0% as a *measurement*, which is
        what makes it distinguishable from a reading that could not be taken."""
        device = engine.sample().devices[0]
        assert device.utilization_gpu.is_measurement
        assert device.utilization_gpu.value is not None
        assert device.utilization_gpu.reason is None


class TestDeviceIdentity:
    def test_uuid_matches_nvidia_smi(self, engine: SamplingEngine) -> None:
        theirs = set(_smi_rows())
        ours = {d.id.key for d in engine.sample().devices}
        assert ours & theirs, "device keys do not correspond to nvidia-smi UUIDs"

    def test_identity_is_stable_across_samples(self, engine: SamplingEngine) -> None:
        first = {d.id.key for d in engine.sample().devices}
        for _ in range(5):
            assert {d.id.key for d in engine.sample().devices} == first
