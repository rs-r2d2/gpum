# Controls and settings

## Along the top of the window

| Control | What it does |
|---|---|
| **Refresh** | How often to sample — 0.5 s up to 10 s |
| **Pause** | Freezes the display; nothing is sampled while paused |
| **Refresh now** | Takes one sample immediately |
| **Settings…** | Everything below |

## In Settings

### Refresh every

How often GPUM samples your GPUs. Choices: **0.5 s**, **1 s**, **2 s**, **5 s**, **10 s**.
Default: **1 s**.

Faster sampling costs a little more of the resources you are trying to measure; slower sampling
makes short spikes easier to miss.

### Keep history for

How far back the trend graphs look. Choices: **1 minute**, **5 minutes**, **15 minutes**,
**1 hour**. Default: **5 minutes**.

History is bounded on purpose — memory use does not grow the longer GPUM stays open.

### Slow updates while the window is hidden

Default: **on**. When GPUM is not visible it samples less often, so it does not consume the
resources it exists to measure. Turn it off if you want an unbroken history while the window is
minimised.

### Keep GPUM in the status area when the window is closed

Default: **on**. Closing the window tucks GPUM into the system tray instead of quitting. If your
desktop has no usable status area, GPUM tells you so rather than vanishing into one that isn't
there.

### Start GPUM when I log in

Default: **off**. Adds a user-level autostart entry — nothing system-wide, and no elevated
privileges are asked for.

## Where your settings live

In your own user configuration, and nowhere else. Both the bundle and the from-source install
read and write the same file, so switching between them keeps your preferences. Sort order is
remembered per device, so a GPU you always sort by memory stays that way.

Nothing here is ever transmitted anywhere.
