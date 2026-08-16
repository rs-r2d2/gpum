# Contract: Tray presence and window lifecycle

**Modules**: `src/gpum/adapters/linux/tray_probe.py`, `src/gpum/ui/tray.py`,
`src/gpum/ui/main_window.py` | **Feature**: 002-linux-nvidia-release

Governs FR-029 – FR-034. The rule underneath all of it: **there must be no state in which the
tool is running and the user cannot reach it.**

---

## `TrayProbe` — will an icon actually appear?

```python
class TrayProbe(Protocol):
    def probe(self) -> TrayAvailability: ...
```

Lives in `adapters/linux/` because the question is Linux-desktop-specific. The tray *widget* is
cross-platform Qt and stays in `ui/`, so no DBus or OS branching enters the UI layer
(constitution Principle II).

**MUST**:
- Never raise. A missing session bus is an expected condition, not an exception.
- Determine `usable` as `watcher_present AND qt_reports_available`.
- Return a `reason` whenever `usable` is `False`, fit to show in settings.
- Complete within 500 ms so it cannot delay startup past SC-001's budget.

**MUST NOT**:
- Trust `QSystemTrayIcon.isSystemTrayAvailable()` alone. On stock GNOME it returns `True` while
  the icon is silently dropped — Qt reports the capability, the desktop discards it, and the user
  is left with a program they cannot see (research D-04). This is the specific failure FR-034 and
  SC-015 forbid.
- Block on DBus without a timeout.
- Assume availability when the probe itself fails. Probe failure means `usable=False` with the
  error as the reason — unavailable-and-explained, the same rule the metric model follows.

---

## Window close semantics

The decision table. Every row must be reachable and tested.

| Tray usable | `tray_enabled` pref | Close button does | Quit via |
|---|---|---|---|
| Yes | `True` | Hide to tray | Tray menu, or File→Quit |
| Yes | `False` | **Quit** | Close button |
| No | `True` | **Quit** | Close button |
| No | `False` | **Quit** | Close button |

**MUST**:
- Show a one-time notification the first time closing hides rather than quits, persisted via
  `close_notice_shown` so it appears once per user, not once per session (FR-030).
- Offer show, pause/resume, and quit from the tray menu (FR-029).
- Restore the window with a current reading within two refresh intervals of reopening (FR-033).
- Fall back to quit-on-close whenever the tray is not usable (FR-034) — the row that makes the
  unreachable state impossible.

**MUST NOT**:
- Hide the window when no tray icon will be displayed. That is the failure this contract exists
  to prevent.
- Silently ignore the user's `tray_enabled=False` preference when a tray happens to be available.

---

## Sampling while closed to tray

**MUST**: closing to the tray throttles sampling exactly as hiding the window already does.

**MUST NOT**: sample continuously to keep the tray "fresh". FR-032 and SC-016 forbid it, and
feature 001's Principle III reasoning applies unchanged — a monitor that runs permanently in the
background becomes a tax on the resource it measures.

**Implementation note**: the correct change here is *no change*. Feature 001's `hideEvent` already
signals `set_throttled(True)`, and closing to tray fires it. The temptation is to add background
polling so the window is instantly current on reopen; FR-033's two-interval budget is deliberately
loose enough that a fresh sample on reopen satisfies it.

---

## Contract tests

`tests/unit/test_tray_probe.py` and `tests/integration/test_tray_behaviour.py`, both running
against a **fake probe** with no DBus, so they pass on any machine (Principle IV).

| # | Assertion | Enforces |
|---|-----------|----------|
| T-01 | `probe()` never raises — no bus, no watcher, DBus error | — |
| T-02 | `usable` is `False` when the watcher is absent even though Qt reports `True` | **research D-04** |
| T-03 | `usable` is `False` when Qt reports `False` even though a watcher exists | conservative conjunction |
| T-04 | Probe failure yields `usable=False` with a non-empty reason | FR-017 discipline |
| T-05 | All four rows of the close-semantics table behave as specified | FR-030, FR-031, FR-034 |
| T-06 | With the tray unusable, closing the window quits the application | **SC-015** |
| T-07 | The close notice appears exactly once across sessions | FR-030 |
| T-08 | Tray menu exposes show, pause, and quit, and each works | FR-029 |
| T-09 | Reopening from tray shows a reading no older than two intervals | FR-033 |
| T-10 | Sampling rate while closed-to-tray equals the hidden-window rate | **FR-032, SC-016** |
| T-11 | Disabling the tray at runtime restores quit-on-close without a restart | FR-031 |
| T-12 | `ui/tray.py` imports no DBus library and no OS-conditional logic | Principle II |

T-06 and T-10 are the two that matter most: the first prevents an unrecoverable program, the
second prevents the tool becoming the load it is meant to measure.
