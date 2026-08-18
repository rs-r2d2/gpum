# Contributing

Contributions are very welcome — including the small ones, and including "this page confused me".

## Just want to report something?

[Open an issue](https://github.com/rs-r2d2/gpum/issues). You do not need to read anything else on
this page first.

A useful report includes:

- **what you saw**, and what you expected instead;
- **which build** — run `gpum --version`, which prints the version *and* whether you are running
  the bundle or the package;
- **your distribution and driver version** — `nvidia-smi` prints the driver;
- **anything GPUM printed**, especially with `-v` for debug logging.

If a value showed as unavailable and you think it should not have, say which value and which
device. That distinction — unavailable versus wrong — is usually the whole diagnosis.

## Want to change something?

| | |
|---|---|
| [Development setup](development.md) | Get a working environment and a passing suite |
| [Quality gates](quality-gates.md) | What every change must pass, and what each failure means |
| [Scope and boundaries](scope.md) | What the project will not accept, before you build it |
| [Reference](../reference/index.md) | The interfaces and the rules they carry |
| [Building the bundle](../building.md) | Producing the self-contained AppImage |

## The one thing worth knowing up front

GPUM is governed by a written
[constitution](https://github.com/rs-r2d2/gpum/blob/main/.specify/memory/constitution.md), and it
is not decoration: several of the checks in this repository exist to enforce it mechanically, and
a pull request is expected to say which principles it touches. The principles are short, and
[scope and boundaries](scope.md) summarises the ones that most often decide whether a change can
be accepted.
