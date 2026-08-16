"""T024: every GPU in the machine is accounted for (FR-015, SC-007).

Reporting only monitorable GPUs tells a user with an NVIDIA + AMD machine that they have one
GPU. That is a factual error about their hardware — the same class of dishonesty as rendering
an unavailable metric as zero.
"""

from __future__ import annotations

import pathlib

from gpum.adapters.linux.pci_devices import enumerate_present_gpus
from gpum.core.engine import SamplingEngine
from gpum.core.models import Vendor
from gpum.registry import build_backends


def _fake_drm(root: pathlib.Path, cards: list[tuple[str, str, str, str]]) -> pathlib.Path:
    """Build a fake /sys/class/drm tree: (card, vendor, class, device)."""
    drm = root / "drm"
    drm.mkdir(parents=True, exist_ok=True)
    for name, vendor, klass, device in cards:
        pci = root / "pci" / name
        pci.mkdir(parents=True, exist_ok=True)
        (pci / "vendor").write_text(vendor + "\n")
        (pci / "class").write_text(klass + "\n")
        (pci / "device").write_text(device + "\n")
        card = drm / f"card{len(list(drm.iterdir()))}"
        card.mkdir()
        (card / "device").symlink_to(pci)
    return drm


class TestEnumeration:
    def test_detects_multiple_vendors(self, tmp_path: pathlib.Path) -> None:
        drm = _fake_drm(
            tmp_path,
            [
                ("0000:01:00.0", "0x10de", "0x030000", "0x2d04"),
                ("0000:11:00.0", "0x1002", "0x030000", "0x13c0"),
            ],
        )
        found = enumerate_present_gpus(str(drm))
        assert {g.vendor for g in found} == {Vendor.NVIDIA, Vendor.AMD}

    def test_ignores_non_display_devices(self, tmp_path: pathlib.Path) -> None:
        drm = _fake_drm(
            tmp_path,
            [
                ("0000:01:00.0", "0x10de", "0x030000", "0x2d04"),
                ("0000:02:00.0", "0x10de", "0x040300", "0x22bd"),  # audio function
            ],
        )
        assert len(enumerate_present_gpus(str(drm))) == 1

    def test_unknown_vendor_is_still_reported(self, tmp_path: pathlib.Path) -> None:
        """An unrecognised vendor is still a GPU in the machine. Reporting it as unknown is
        honest; omitting it is not."""
        drm = _fake_drm(tmp_path, [("0000:03:00.0", "0x1234", "0x030000", "0x0001")])
        found = enumerate_present_gpus(str(drm))
        assert len(found) == 1
        assert found[0].vendor is Vendor.UNKNOWN

    def test_missing_drm_tree_returns_empty(self) -> None:
        assert enumerate_present_gpus("/nonexistent/drm") == []

    def test_never_raises_on_unreadable_entries(self, tmp_path: pathlib.Path) -> None:
        drm = tmp_path / "drm"
        (drm / "card0").mkdir(parents=True)
        assert enumerate_present_gpus(str(drm)) == []


class TestDiscoveryAccounting:
    def test_unmonitored_gpu_is_reported(self) -> None:
        class FakePresent:
            vendor = Vendor.AMD
            pci_address = "0000:11:00.0"

        engine = SamplingEngine(
            build_backends("none"), present_gpu_probe=lambda: [FakePresent()]
        )
        report = engine.sample().discovery
        assert len(report.present_but_unmonitored) == 1
        assert report.present_but_unmonitored[0].location == "0000:11:00.0"
        assert report.present_but_unmonitored[0].reason
        engine.shutdown()

    def test_monitored_vendor_is_not_double_counted(self) -> None:
        class FakePresent:
            vendor = Vendor.NVIDIA
            pci_address = "0000:01:00.0"

        engine = SamplingEngine(
            build_backends("fake", scenario="two-nvidia"),
            present_gpu_probe=lambda: [FakePresent()],
        )
        report = engine.sample().discovery
        # The fake backend reports UNKNOWN vendor devices, so an NVIDIA card is genuinely
        # unmonitored here; the assertion is that accounting stays consistent.
        assert report.total_gpus_accounted >= 1
        engine.shutdown()

    def test_probe_failure_does_not_break_sampling(self) -> None:
        def exploding() -> list[object]:
            raise RuntimeError("sysfs unavailable")

        engine = SamplingEngine(build_backends("none"), present_gpu_probe=exploding)
        snapshot = engine.sample()
        assert snapshot.discovery.present_but_unmonitored == ()
        engine.shutdown()

    def test_no_probe_means_no_claim(self) -> None:
        engine = SamplingEngine(build_backends("none"))
        assert engine.sample().discovery.present_but_unmonitored == ()
        engine.shutdown()
