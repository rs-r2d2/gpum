"""T046: no graphical session must be explained, not crashed on (FR-019)."""

from __future__ import annotations

from gpum.__main__ import _no_graphical_session


class TestGraphicalSessionDetection:
    def test_display_present_is_accepted(self, monkeypatch) -> None:
        monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
        monkeypatch.setenv("DISPLAY", ":0")
        assert _no_graphical_session() is None

    def test_wayland_is_accepted(self, monkeypatch) -> None:
        monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        assert _no_graphical_session() is None

    def test_offscreen_is_accepted_for_testing(self, monkeypatch) -> None:
        monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        assert _no_graphical_session() is None

    def test_headless_returns_an_actionable_message(self, monkeypatch) -> None:
        monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        message = _no_graphical_session()
        assert message is not None
        assert "graphical" in message.lower()
        # Actionable, per SC-006's standard for messages.
        assert "ssh" in message.lower() or "offscreen" in message.lower()
