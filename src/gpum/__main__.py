"""Entry point: ``gpum`` and ``python -m gpum``."""

from __future__ import annotations

import argparse
import logging
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gpum",
        description="Live GPU memory and process monitor (read-only, no telemetry).",
    )
    parser.add_argument(
        "--backend",
        choices=["nvidia", "amd", "intel", "fake", "none"],
        default=None,
        help="restrict to one backend; 'fake' simulates GPUs, 'none' registers none",
    )
    parser.add_argument(
        "--scenario",
        default=None,
        help="fake-backend scenario name (see --list-scenarios)",
    )
    parser.add_argument(
        "--list-scenarios", action="store_true", help="list fake scenarios and exit"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="print the version and how this instance was delivered, then exit",
    )
    parser.add_argument(
        "--hidden",
        action="store_true",
        help="start minimised to the status area (used by autostart)",
    )
    parser.add_argument(
        "--install-desktop-entry",
        action="store_true",
        help="add GPUM to your application menu",
    )
    parser.add_argument(
        "--remove-desktop-entry",
        action="store_true",
        help="remove GPUM from your application menu",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.version:
        # Reported identically by both distribution forms (FR-026).
        from gpum.distribution import detect

        print(detect().describe())
        return 0

    if args.install_desktop_entry or args.remove_desktop_entry:
        from gpum.adapters.linux import desktop_entry

        if args.install_desktop_entry:
            for path in desktop_entry.install_desktop_entry():
                print(f"wrote {path}")
        else:
            removed = desktop_entry.remove_desktop_entry()
            for path in removed:
                print(f"removed {path}")
            if not removed:
                print("no desktop entry was installed")
        return 0

    if args.list_scenarios:
        from gpum.backends.fake.scenarios import SCENARIOS

        for name, scenario in SCENARIOS.items():
            print(f"{name:24} {scenario.description}")
        return 0

    missing_display = _no_graphical_session()
    if missing_display:
        print(missing_display, file=sys.stderr)
        return 3

    from gpum.ui.app import run

    return run(backend=args.backend, scenario=args.scenario, hidden=args.hidden)


def _no_graphical_session() -> str | None:
    """Explain the requirement rather than dying with an unhandled Qt error (FR-019).

    Checked here rather than by catching a Qt failure because Qt aborts the process on a
    missing display instead of raising something catchable.
    """
    import os

    if os.environ.get("QT_QPA_PLATFORM") in {"offscreen", "minimal", "vnc"}:
        return None
    if os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY"):
        return None
    return (
        "gpum needs a graphical desktop session and none was found.\n"
        "If you are connected over SSH, enable X11 forwarding (ssh -X) or run it on the "
        "machine's own desktop.\n"
        "To run headless for testing only: QT_QPA_PLATFORM=offscreen gpum"
    )


if __name__ == "__main__":
    sys.exit(main())
