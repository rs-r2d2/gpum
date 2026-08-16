"""T055-T057: close semantics and tray behaviour (contracts/tray-contract.md T-05..T-11).

Runs against injected availability rather than a real desktop, so it passes anywhere.
"""

from __future__ import annotations

import pytest

from gpum.core.preferences import Preferences
from gpum.ui.main_window import MainWindow


def _window(qtbot, *, tray_usable: bool, tray_enabled: bool) -> MainWindow:
    window = MainWindow(Preferences(tray_enabled=tray_enabled))
    qtbot.addWidget(window)
    window.set_tray_usable(tray_usable)
    return window


class TestCloseSemantics:
    """T-05: all four rows of the decision table."""

    def test_usable_and_enabled_hides(self, qtbot) -> None:
        window = _window(qtbot, tray_usable=True, tray_enabled=True)
        assert window.hides_on_close is True

    def test_usable_but_disabled_quits(self, qtbot) -> None:
        window = _window(qtbot, tray_usable=True, tray_enabled=False)
        assert window.hides_on_close is False

    def test_unusable_but_enabled_quits(self, qtbot) -> None:
        """T-06 / SC-015 — the row that prevents an unreachable running program."""
        window = _window(qtbot, tray_usable=False, tray_enabled=True)
        assert window.hides_on_close is False

    def test_unusable_and_disabled_quits(self, qtbot) -> None:
        window = _window(qtbot, tray_usable=False, tray_enabled=False)
        assert window.hides_on_close is False

    def test_default_before_probing_is_quit(self, qtbot) -> None:
        """Until availability is known, closing must quit — the safe default."""
        window = MainWindow(Preferences(tray_enabled=True))
        qtbot.addWidget(window)
        assert window.hides_on_close is False


class TestCloseBehaviour:
    def test_t06_unusable_tray_emits_quit_on_close(self, qtbot) -> None:
        window = _window(qtbot, tray_usable=False, tray_enabled=True)
        window.show()
        with qtbot.waitSignal(window.quit_requested, timeout=1000):
            window.close()

    def test_hiding_does_not_emit_quit(self, qtbot) -> None:
        window = _window(qtbot, tray_usable=True, tray_enabled=True)
        window.show()
        received: list[bool] = []
        window.quit_requested.connect(lambda: received.append(True))
        window.close()
        assert not received, "closing to tray must not quit the application"
        assert not window.isVisible()

    def test_request_quit_bypasses_hide_on_close(self, qtbot) -> None:
        window = _window(qtbot, tray_usable=True, tray_enabled=True)
        window.show()
        with qtbot.waitSignal(window.quit_requested, timeout=1000):
            window.request_quit()

    def test_t07_close_notice_appears_exactly_once(self, qtbot) -> None:
        window = _window(qtbot, tray_usable=True, tray_enabled=True)
        window.show()
        notices: list[bool] = []
        window.closed_to_tray.connect(lambda: notices.append(True))

        window.close()
        window.show()
        window.close()
        window.show()
        window.close()
        assert len(notices) == 1, "the disclosure must appear once per user, not per close"

    def test_close_notice_state_persists_into_preferences(self, qtbot) -> None:
        window = _window(qtbot, tray_usable=True, tray_enabled=True)
        window.show()
        window.close()
        assert window.current_preferences().close_notice_shown is True

    def test_t11_disabling_the_tray_restores_quit_on_close(self, qtbot) -> None:
        window = _window(qtbot, tray_usable=True, tray_enabled=True)
        assert window.hides_on_close is True
        window.current_preferences().tray_enabled = False
        assert window.hides_on_close is False, "must take effect without a restart"


class TestSamplingUnaffected:
    def test_t10_closing_to_tray_throttles_like_hiding(self, qtbot) -> None:
        """FR-032 / SC-016: the tray icon must add zero continuous sampling.

        The correct implementation is *no change* — closing to tray fires hideEvent, which
        already throttles the worker.
        """
        window = _window(qtbot, tray_usable=True, tray_enabled=True)
        window.show()
        with qtbot.waitSignal(window.throttle_changed, timeout=1000) as blocker:
            window.close()
        assert blocker.args == [True]

    def test_reopening_clears_throttle(self, qtbot) -> None:
        window = _window(qtbot, tray_usable=True, tray_enabled=True)
        window.show()
        window.close()
        with qtbot.waitSignal(window.throttle_changed, timeout=1000) as blocker:
            window.showNormal()
        assert blocker.args == [False]


class TestTrayWidget:
    def test_t08_menu_offers_show_pause_and_quit(self, qtbot) -> None:
        pytest.importorskip("PySide6.QtWidgets")
        from PySide6.QtGui import QIcon

        from gpum.ui.tray import TrayPresence

        tray = TrayPresence(QIcon())
        labels = [a.text().lower() for a in tray._menu.actions() if a.text()]
        assert any("show" in x for x in labels)
        assert any("pause" in x or "resume" in x for x in labels)
        assert any("quit" in x for x in labels)

    def test_pause_state_reflects_without_looping(self, qtbot) -> None:
        from PySide6.QtGui import QIcon

        from gpum.ui.tray import TrayPresence

        tray = TrayPresence(QIcon())
        emitted: list[bool] = []
        tray.pause_toggled.connect(emitted.append)
        tray.set_paused(True)
        assert emitted == [], "reflecting external state must not re-emit"
        assert "Resume" in tray._pause_action.text()
