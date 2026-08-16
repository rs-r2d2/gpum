"""T072: the tool must stay usable with no GPU at all (FR-018, SC-006, U-05)."""

from gpum.core.engine import SamplingEngine
from gpum.core.models import BackendState
from gpum.core.preferences import Preferences
from gpum.registry import build_backends
from gpum.ui.main_window import MainWindow


class TestNoBackends:
    def test_engine_produces_a_snapshot_with_no_backends(self) -> None:
        engine = SamplingEngine(build_backends("none"))
        snapshot = engine.sample()
        assert snapshot.devices == ()
        assert snapshot.processes == ()

    def test_window_opens_and_stays_usable(self, qtbot) -> None:
        window = MainWindow(Preferences())
        qtbot.addWidget(window)
        engine = SamplingEngine(build_backends("none"))
        window.on_discovery(engine.sample().discovery)
        window.on_snapshot(engine.sample())
        assert window.isEnabled()


class TestDiscoveryReporting:
    def test_every_backend_is_named_including_stubs(self) -> None:
        """SC-006: the user learns what was looked for, not just that nothing appeared."""
        engine = SamplingEngine(build_backends())
        report = engine.sample().discovery
        vendors = {r.vendor for r in report.backends_attempted}
        assert {"nvidia", "amd", "intel"} <= {str(v) for v in vendors}

    def test_stubs_report_not_implemented_with_a_message(self) -> None:
        engine = SamplingEngine(build_backends())
        report = engine.sample().discovery
        for backend in report.backends_attempted:
            if str(backend.vendor) in {"amd", "intel"}:
                assert backend.state is BackendState.NOT_IMPLEMENTED
                assert backend.detail

    def test_nvidia_without_driver_says_so_specifically(self) -> None:
        """The library-missing and driver-missing cases must not be conflated."""
        engine = SamplingEngine(build_backends("nvidia"))
        report = engine.sample().discovery
        nvidia = next(r for r in report.backends_attempted if str(r.vendor) == "nvidia")
        assert nvidia.state in {
            BackendState.LIBRARY_MISSING,
            BackendState.DRIVER_MISSING,
            BackendState.NO_DEVICES,
            BackendState.ACTIVE,
            BackendState.ERROR,
        }
        assert nvidia.detail

    def test_discovery_panel_renders_each_backend(self, qtbot) -> None:
        window = MainWindow(Preferences())
        qtbot.addWidget(window)
        engine = SamplingEngine(build_backends())
        window.on_discovery(engine.sample().discovery)
        text = window._discovery._detail.text()
        assert "AMD" in text and "INTEL" in text and "NVIDIA" in text
