# Development setup

```bash
git clone https://github.com/rs-r2d2/gpum.git
cd gpum
pip install -e ".[dev]"
```

Python 3.11 or newer. No compiler, no GPU, and no vendor driver required.

## Run the checks

```bash
pytest                    # the full default suite
ruff check src tests      # lint
mypy                      # type check
```

**The default suite passes on a machine with no GPU present.** That is a deliberate property, not
a happy accident: every backend has a simulated counterpart, so the hardware matrix does not have
to exist on your desk or in CI. If `pytest` fails on a machine with no GPU, that is a bug worth
reporting.

## The suites that are deselected by default

```bash
pytest -m hardware        # needs a real NVIDIA GPU
pytest -m packaging       # needs a built AppImage
pytest -m network         # reaches the internet: link and release checks
```

They are excluded from the default run because a check that cannot pass on a contributor's
machine should never block that contributor's work. CI runs them where the prerequisites exist.

## Working on the documentation site

```bash
pip install -e ".[docs]"
mkdocs serve              # live preview on http://127.0.0.1:8000/gpum/
mkdocs build --strict     # what CI runs; warnings are failures
```

Offline, or without hitting the releases API:

```bash
GPUM_DOCS_OFFLINE=1 mkdocs serve
```

The download block on this site is generated at build time from the release list, so nothing
about it is typed by hand and no page contains a version number. `GPUM_DOCS_OFFLINE=1` exercises
the fallback path — the same one CI takes when GitHub is unreachable.

Documentation checks run as part of the ordinary suite:

```bash
pytest tests/docs
```

They read the argument parser, the scenario table, the settings dialog, and the capability matrix,
and fail when a page disagrees with any of them. So renaming a flag tells *you* that a page went
stale, rather than telling a reader months from now.

## Seeing the application without hardware

```bash
gpum --backend fake --scenario one-device-hangs
gpum --list-scenarios
```

All eight scenarios are described under [try it without a GPU](../usage/demo-mode.md).

## Next

[Quality gates](quality-gates.md) — what has to pass, and what each failure actually means.
