# Troubleshooting

Organised by what you saw, not by what caused it.

## "Permission denied" when I run it

You skipped the step that marks the file executable:

```bash
chmod +x GPUM-*-x86_64.AppImage
```

Downloads arrive without permission to run — see [why](../download.md#the-bundle-recommended).

## Double-clicking it does nothing, or opens an archive viewer

Same cause: the file is not marked executable yet. Some file managers also need
**Properties → Permissions → Allow executing file as program**.

## The download link gives me a 404

You are probably using a `/releases/latest/` URL. Current releases are marked *pre-release*, and
that link deliberately skips them. The command on the [download page](../download.md) always names
a real published version, because it is generated from the release list rather than typed.

## It says "No GPUs are available to monitor"

GPUM lists what it looked for and why each option did not work, right in the window. Usually the
NVIDIA driver is not installed or not loaded — check with:

```bash
nvidia-smi
```

If that fails too, it is a driver matter rather than a GPUM one. GPUM stays open and usable
either way, and you can still explore the interface with
[simulated GPUs](demo-mode.md).

## It won't start on an older distribution

The bundle needs glibc 2.35 or newer (Ubuntu 22.04 and newer). On something older, install
[from source](../download.md#from-source) instead.

## "gpum needs a graphical desktop session and none was found"

GPUM opens a window, so it needs a desktop session. Over SSH, enable X11 forwarding:

```bash
ssh -X you@machine
gpum
```

For automated testing only, `QT_QPA_PLATFORM=offscreen gpum` runs without a display.

## Per-process memory shows as unavailable

Some driver setups report the PIDs but not their memory. GPUM says so explicitly rather than
printing `0`, because `0` would look like a process using no GPU memory at all. See
[the process table](processes.md).

## A device says it is unsupported

Partitioned (MIG) GPUs report as unsupported rather than showing figures that would not mean what
they appear to mean. AMD and Intel devices are detected but not implemented, and say so — the
[capability matrix](../capability-matrix.md) records exactly what is verified.

## One GPU stopped updating while the others kept going

That is the intended behaviour. Each device is queried with its own timeout, so a driver that
wedges degrades that one device and leaves everything else — and the window itself — responsive.

## Something else

Please [open an issue](https://github.com/rs-r2d2/gpum/issues) — genuinely happy to help. What to
include is on the [contributing page](../contributing/index.md).
