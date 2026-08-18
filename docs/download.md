# Download and install

Two supported ways to get GPUM. The **bundle** is one self-contained file with Python and Qt
already inside — nothing to install, nothing to uninstall. **From source** is just as supported
and handy if you already live in Python. Both share the same settings file, so you can switch
between them whenever you like and your preferences follow you.

## Before you start

Check these first — it is quicker than finding out after the download.

| What you need | Details |
|---|---|
| **Linux, 64-bit x86** | Ubuntu 22.04 or newer, or anything with glibc 2.35+. Windows and macOS are not supported and not planned — see [scope](contributing/scope.md) |
| **An NVIDIA driver** | Already installed; the one you use for graphics is fine. Check with `nvidia-smi`. AMD and Intel are registered but not implemented — see the [capability matrix](capability-matrix.md) |
| **A desktop session** | GPUM opens a window. Over SSH you need X11 forwarding (`ssh -X`) |
| **About 50 MB of disk** | That is the whole bundle |
| **Python 3.11 or newer** | Only for the from-source route. The bundle carries its own |

No GPU to hand? You can still explore the whole interface — see
[try it without a GPU](usage/demo-mode.md).

## The bundle (recommended)

--8<-- "_snippets/release.md"

Three lines, and your GPUs should appear straight away.

### What those three lines do

**1. Download it.** `curl -L -O` saves the file into your current directory. You can equally
click the link on the [releases page](https://github.com/rs-r2d2/gpum/releases) — the result is
the same file.

!!! tip "Use the version tag, not `latest`"
    Releases so far are marked *pre-release*, and GitHub's `/releases/latest/` link deliberately
    skips those — a `latest` URL gives you a **404** rather than a download. The command above
    always names a real published version, which is why it is generated rather than typed.

**2. Allow it to run.**

```bash
chmod +x GPUM-*-x86_64.AppImage
```

Anything you download arrives *without* permission to run: your browser and `curl` cannot know
whether you meant to save a file or execute a program, so Linux waits for you to say so. This is
you saying so.

Skip it and nothing helpful happens. The terminal says
`bash: ./GPUM-…-x86_64.AppImage: Permission denied`, and double-clicking in a file manager
either opens an archive viewer or does nothing at all. Neither mentions permissions, which is why
this catches almost everybody once.

**3. Open it.**

```bash
./GPUM-*-x86_64.AppImage
```

A window appears listing your GPUs. If it does not, the window itself will say what it looked for
and why each option did not work — and [troubleshooting](usage/troubleshooting.md) covers the
common cases.

### Put it in your applications menu

Either pin the bundle to your dock, or install the package below and run
`gpum --install-desktop-entry`.

## From source

```bash
git clone https://github.com/rs-r2d2/gpum.git
cd gpum
pip install -e ".[nvidia]"
```

Then:

```bash
gpum                              # launch it
gpum --install-desktop-entry      # add it to your applications menu
gpum --version                    # prints the version and how this copy was delivered
```

`pip install -e "."` without the `[nvidia]` extra also works — NVIDIA support then reports itself
as not installed rather than failing. Python 3.11 or newer, and no compiler is required.

There is no `pip install gpum` from PyPI yet; the from-source route above is the supported one.

Every command-line option is documented in the [command line reference](reference/cli.md).

## Why the NVIDIA driver is not bundled

NVIDIA's libraries are locked to your running kernel module. A copy shipped inside the bundle
would either refuse to load or — much worse — quietly report *the build machine's* numbers as if
they were yours. So GPUM asks your system for them instead. Honest beats convenient.

This is the same reason installing GPUM never requires a vendor driver or SDK to be present: a
missing one disables a backend and reports itself, and nothing else changes.

## If something goes wrong

[Troubleshooting](usage/troubleshooting.md) is organised by what you saw, not by what caused it.
