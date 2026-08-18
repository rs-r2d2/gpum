# Command line reference

Source: [`src/gpum/__main__.py`](https://github.com/rs-r2d2/gpum/blob/main/src/gpum/__main__.py)

```bash
gpum [--backend {nvidia,amd,intel,fake,none}] [--scenario NAME] [--list-scenarios]
     [--version] [--hidden] [--install-desktop-entry] [--remove-desktop-entry] [-v]
```

Both distribution forms accept the same options: `gpum ...` for the from-source install,
`./GPUM-*-x86_64.AppImage ...` for the bundle.

## Options

### `--backend {nvidia,amd,intel,fake,none}`

Restrict GPUM to a single backend instead of registering all of them. `fake` simulates GPUs;
`none` registers no backend at all, which is how the "nothing available" path is exercised.
Default: every backend is registered and each reports its own availability.

### `--scenario NAME`

Which simulated situation the `fake` backend should present. Only meaningful with
`--backend fake`. See [try it without a GPU](../usage/demo-mode.md) for all eight, or
`--list-scenarios`.

### `--list-scenarios`

Print every fake scenario with its description, then exit. Exit code 0.

### `--version`

Print the version *and how this copy was delivered* — bundle or package — then exit. The two
forms report identically, which is what makes a bug report unambiguous about which one you ran.

### `--hidden`

Start minimised to the status area rather than opening a window. This is what the
start-at-login entry uses, so logging in does not throw a window at you.

### `--install-desktop-entry`

Add GPUM to your applications menu, then exit, printing each file written. User-level only —
nothing system-wide, and no elevated privileges are requested.

### `--remove-desktop-entry`

Remove that entry again, then exit, printing what was removed. Says so plainly if nothing was
installed.

### `-v`, `--verbose`

Debug-level logging to standard error. Default is warnings only.

## Exit behaviour

| Situation | Result |
|---|---|
| Normal run | Exits when the window closes |
| `--version`, `--list-scenarios`, desktop-entry options | Prints and exits 0 without opening a window |
| No graphical session | Exits **3** with an explanation, including the `ssh -X` hint for remote sessions and `QT_QPA_PLATFORM=offscreen` for headless testing |

The no-display case is checked deliberately rather than left to Qt: Qt aborts the process on a
missing display instead of raising something catchable, so the check happens first and produces a
message a person can act on.

## Related

- [Backend registry](registry.md) — what `--backend` actually selects
- [Demonstration scenarios](../usage/demo-mode.md) — what `--scenario` accepts
