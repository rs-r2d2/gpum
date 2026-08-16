# Feature Specification: Linux + NVIDIA Release Readiness

**Feature Branch**: `002-linux-nvidia-release`

**Created**: 2026-08-16

**Status**: Draft

**Input**: User description: "Implement everything to run on linux system, nvidia gpu"

## Context

Feature 001 delivered the monitor itself: device metrics, process attribution, live updating, and
honest degradation. It was built and tested without access to a GPU, so twelve of its tasks were
deferred as unverifiable, and nothing was ever installed the way a real user would install it.

This feature closes that gap. It is not new monitoring capability — it is everything required to
say **"this works on a Linux machine with an NVIDIA GPU"** and mean it: verified against real
hardware, installable by someone who did not build it, and resilient to the things that actually
happen on a running desktop.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Install and run it without being the author (Priority: P1)

Someone with a Linux machine and an NVIDIA GPU obtains the tool, installs it with a single
documented command, and launches it from their desktop environment the way they launch anything
else. It shows their actual GPU within seconds. They never clone a repository, never activate a
virtual environment, and never read source code to get there.

**Why this priority**: Until this works, nothing else in the tool is reachable by anyone but its
author. Everything else is a refinement of something no one can start.

**Independent Test**: On a clean Linux machine with an NVIDIA GPU and no development tooling,
follow the published install instructions and launch the application. It must display real GPU
data with no additional steps.

**Acceptance Scenarios**:

1. **Given** a clean Linux machine with an NVIDIA driver installed, **When** a user follows the
   documented install command, **Then** installation completes without a compiler, without root,
   and without manual dependency resolution.
2. **Given** the tool is installed, **When** the user launches it from their desktop application
   menu, **Then** the window opens and shows their real GPU within 5 seconds.
3. **Given** the tool is installed, **When** the user runs it from a terminal by name, **Then** it
   launches identically.
4. **Given** a machine where the NVIDIA driver is present but the optional vendor support was not
   installed, **When** the user launches the tool, **Then** it opens and states exactly what to
   install to enable NVIDIA support, rather than reporting a generic failure.
5. **Given** the user wants to remove the tool, **When** they follow the documented uninstall
   step, **Then** it is removed cleanly, leaving only their saved preferences.
6. **Given** a user who has never installed a Python package, **When** they download the
   self-contained file, make it executable, and run it, **Then** the tool opens and shows their
   GPU with no other step and no administrator privileges.
7. **Given** a machine whose system language runtime is older than the tool requires, **When** the
   user runs the self-contained file, **Then** it works regardless, because it carries its own.
8. **Given** a user who has used one distribution form and switches to the other, **When** they
   launch it, **Then** their saved settings are already in effect.

---

### User Story 2 - Verified against real hardware, not assumptions (Priority: P1)

Every claim the tool makes about NVIDIA GPUs on Linux is confirmed against a physical GPU rather
than inferred: memory figures match what the vendor's own tooling reports, per-process attribution
names the right processes, and device identity survives the machine being used normally.

**Why this priority**: Feature 001's entire test suite ran without a GPU. The behaviour is
plausible but unproven, and a monitor that reports wrong numbers confidently is worse than one
that reports nothing. This is equal-priority with US1 because installation without verification
just distributes an unverified tool faster.

**Independent Test**: On a machine with a real NVIDIA GPU, compare the tool's reported figures
against the vendor's own command-line utility over several minutes and under load, and confirm
they agree within the expected sampling difference.

**Acceptance Scenarios**:

1. **Given** a real NVIDIA GPU, **When** the tool reports total and used memory, **Then** the
   figures agree with the vendor's own reporting tool within one sampling interval's drift.
2. **Given** a workload allocating a known quantity of GPU memory, **When** it starts and stops,
   **Then** the tool's reported usage rises and falls correspondingly.
3. **Given** several processes using the GPU, **When** the tool lists them, **Then** every process
   the vendor's tooling reports is present, correctly named, and attributed to the right device.
4. **Given** the machine has been running for an extended period, **When** the user compares device
   identity before and after, **Then** the same physical GPU is still identified as the same
   device with its history intact.
5. **Given** a real GPU, **When** the tool samples continuously, **Then** the measured cost of one
   sampling cycle is recorded and the timeout is set from that measurement rather than a guess.

---

### User Story 3 - Survives what a real desktop does (Priority: P2)

The machine suspends and resumes. The display driver restarts after an update. A second GPU is
present from a different vendor. A long-running session stays open for days. Through all of it the
tool keeps working, or explains itself, and never has to be restarted to recover.

**Why this priority**: These are the failures that turn a demo into a tool people keep open.
They cannot be exercised without real hardware, which is why they arrive with this feature rather
than the last one.

**Independent Test**: Suspend and resume the machine, restart the display driver, and leave the
tool running overnight; confirm it recovers unaided in each case and reports correct figures
afterwards.

**Acceptance Scenarios**:

1. **Given** the tool is running, **When** the machine suspends and resumes, **Then** sampling
   continues without duplicated, negative, or discontinuous readings, and without a restart.
2. **Given** the tool is running, **When** the GPU driver restarts or is reloaded, **Then** the
   tool reports the device as unavailable while it is gone and automatically recovers full
   reporting once it returns.
3. **Given** a machine containing both an NVIDIA GPU and a GPU from another vendor, **When** the
   user opens the tool, **Then** the NVIDIA GPU is fully monitored and the other is listed as
   present but not yet supported — never omitted silently, which would misrepresent the machine.
4. **Given** the tool has run continuously for 24 hours, **When** the user checks it, **Then** it
   is still updating at its configured cadence and its own resource use has not grown.
5. **Given** a GPU-using process is running inside a container, **When** the user views the process
   list, **Then** it is named and marked as containerised, with its memory counted in the device
   total.

---

### User Story 4 - Configure it once and forget it (Priority: P3)

The user opens a settings dialog, adjusts refresh cadence, history window, and background
behaviour in one place, and closes it. Those choices persist. If they want the tool always
available, they can have it start with their session and stay out of the way until needed.

**Why this priority**: Comfort features for people who have already adopted the tool. Valuable,
but nobody is blocked without them.

**Independent Test**: Change every available setting, restart the machine, and confirm all choices
survived and are in effect.

**Acceptance Scenarios**:

1. **Given** the tool is open, **When** the user opens settings and changes refresh interval,
   history window, and background behaviour, **Then** each change takes effect without a restart.
2. **Given** settings have been changed, **When** the machine is rebooted and the tool reopened,
   **Then** every setting is as the user left it.
3. **Given** the user has enabled starting with their session, **When** they log in, **Then** the
   tool starts automatically without stealing focus.
4. **Given** the tool is running, **When** the user closes the window, **Then** it remains
   available from the status area, and the first time this happens the tool says so.
5. **Given** the user has turned the status-area icon off, **When** they close the window,
   **Then** the tool quits.
6. **Given** the tool is closed to the status area, **When** the user reopens it, **Then** the
   window returns showing a current reading within two refresh intervals.

---

### Edge Cases

- **NVIDIA driver present but the optional vendor support package is not installed**: the tool
  opens and names the exact command that fixes it.
- **Driver version newer or older than expected**: the tool works with whatever metrics that
  driver exposes and marks the rest unavailable, rather than refusing to start.
- **A second GPU from an unsupported vendor is physically present**: listed as detected but not
  supported. Omitting it would tell the user their machine has fewer GPUs than it does.
- **The user is not in the group required to read some GPU state**: the tool runs, shows what it
  can, and labels the rest as requiring additional privileges.
- **Machine suspends mid-sampling cycle**: no duplicated or negative readings on resume.
- **Driver restarts under a running tool**: device reported unavailable, then automatically
  recovered — no restart required.
- **Display server differences between session types**: the tool opens and behaves identically.
- **A container is started or stopped while the tool is open**: its processes appear and disappear
  with the correct container label.
- **The GPU is entirely idle**: distinguishable at a glance from the GPU being unreadable.
- **Extremely long session**: the tool's own resource use stays flat across days of uptime.
- **Machine has no desktop environment** (headless or SSH): the tool reports that it needs a
  graphical session rather than crashing with an unhandled error.
- **Desktop environment does not show status-area icons**: the tool detects this and makes window
  close mean quit, so the tool can never disappear with no way to bring it back.
- **User closes the window expecting the tool to quit**: the first time it closes to the status
  area instead, the tool says so, so the behaviour is never a surprise.
- **Self-contained file downloaded but not made executable**: the documented instructions include
  the permission step, since a downloaded file is not runnable by default.
- **Self-contained file run on a machine with no NVIDIA driver**: it still opens and reports what
  it found, exactly as the installed form does.
- **Both distribution forms present on one machine**: they share saved preferences rather than
  maintaining separate, silently diverging settings.

## Requirements *(mandatory)*

### Functional Requirements

**Installation and launch**

- **FR-001**: A user MUST be able to install the tool on a Linux machine with a single documented
  command that requires no compiler and no administrator privileges.
- **FR-002**: The install MUST bring in everything needed to monitor NVIDIA GPUs, or state
  precisely what additional step enables it.
- **FR-003**: The tool MUST be launchable both by name from a terminal and from the desktop
  environment's application menu, with identical behaviour.
- **FR-004**: The tool MUST appear in the desktop environment with a name and icon that identify
  it.
- **FR-005**: The tool MUST be removable by a single documented command, leaving only saved
  preferences behind.
- **FR-006**: Installation documentation MUST state the minimum driver version required and what
  degrades on older ones.

**Hardware verification**

- **FR-007**: Reported total and used GPU memory MUST agree with the vendor's own reporting tool
  to within one sampling interval's drift, verified on real hardware.
- **FR-008**: Every GPU-using process the vendor's tooling reports MUST appear in the tool's
  process list, attributed to the correct device.
- **FR-009**: The per-device query timeout MUST be derived from measured sampling cost on real
  hardware and recorded, replacing the provisional value.
- **FR-010**: Device identity MUST remain stable across process restarts, driver restarts, and
  reboots, verified on real hardware.
- **FR-011**: The test suite MUST include recorded real-hardware responses, including failure
  responses, so that behaviour verified once stays verified on machines without a GPU.
- **FR-012**: The full automated suite MUST continue to pass on machines with no GPU present.

**Resilience**

- **FR-013**: The tool MUST resume correct sampling after the machine suspends and resumes,
  without a restart and without producing duplicated, negative, or discontinuous readings.
- **FR-014**: The tool MUST detect that the GPU driver has restarted, report the device as
  unavailable while it is absent, and restore full reporting automatically when it returns.
- **FR-015**: The tool MUST list every GPU physically present, including those from vendors it
  cannot yet monitor, marking them as detected but unsupported.
- **FR-016**: The tool MUST run for 24 continuous hours with no growth in its own resource use and
  no loss of update cadence, verified on real hardware.
- **FR-017**: The tool MUST attribute GPU-using processes running inside containers, naming them
  and marking them as containerised, verified against a real container.
- **FR-018**: The tool MUST open and remain usable regardless of which display session type the
  user's desktop runs.
- **FR-019**: When launched without a graphical session available, the tool MUST explain that it
  requires one rather than failing with an unhandled error.

**Configuration**

- **FR-020**: Users MUST be able to change refresh interval, history window, and background
  behaviour from a single settings surface, with each change taking effect without a restart.
- **FR-021**: All settings MUST persist across application restarts and machine reboots.
- **FR-022**: Users MUST be able to opt into the tool starting automatically with their desktop
  session, and it MUST NOT take focus when it does.
- **FR-023**: The tool MUST continue to require no elevated privileges for any of its
  functionality, and MUST continue to send nothing off the machine.

**Distribution**

- **FR-024**: The tool MUST be distributed in two forms: a language-package install for users
  comfortable with one, and a single self-contained downloadable file that runs on a mainstream
  Linux desktop without any prior tooling.
- **FR-025**: The self-contained file MUST run after download and a permission change, with no
  install step, no runtime prerequisite beyond the NVIDIA driver, and no administrator privileges.
- **FR-026**: Both distribution forms MUST produce identical behaviour and identical version
  reporting, so a bug report from either is reproducible against the other.
- **FR-027**: The self-contained file MUST carry its own runtime, so it works on machines whose
  system language runtime is older than the tool requires.
- **FR-028**: Both forms MUST read and write the same saved preferences, so a user moving between
  them keeps their settings.

**Background presence**

- **FR-029**: The tool MUST place an icon in the desktop's status area while running, from which
  the user can show the window, toggle pausing, and quit.
- **FR-030**: Closing the window MUST leave the tool running in the status area rather than
  quitting; quitting MUST be an explicit action.
- **FR-031**: The user MUST be able to turn the status-area icon off entirely, in which case
  closing the window quits the tool as it otherwise would.
- **FR-032**: While the window is closed to the status area, the tool MUST continue to obey its
  existing rule that sampling stops or throttles when nothing is being displayed — the status-area
  icon MUST NOT itself cause continuous sampling.
- **FR-033**: Reopening from the status area MUST restore the window with a current reading within
  two refresh intervals.
- **FR-034**: On desktop environments that do not display status-area icons, the tool MUST detect
  this and fall back to closing meaning quitting, rather than appearing to vanish with no way to
  recover it.

### Key Entities

- **Distribution Form**: One of the two ways a user obtains the tool — a language-package install
  or a self-contained downloadable file. Each carries its own prerequisites, launch method, and
  removal procedure, but both report the same version and share the same saved preferences.
- **Desktop Integration**: The tool's presence in the user's environment — its application-menu
  entry, its icon, its status-area icon, and optionally its autostart entry.
- **Status-Area Presence**: Whether the desktop displays status-area icons at all, whether the
  user has enabled the tool's icon, and what closing the window therefore means.
- **Hardware Verification Record**: The measured evidence that reported figures match the vendor's
  own tooling, including the measured sampling cost that sets the timeout.
- **Recorded Hardware Response**: A captured real-driver response, success or failure, retained so
  behaviour proven once on hardware stays under test on machines without it.
- **Resilience Event**: A disruption the tool must survive — suspend/resume, driver restart, device
  appearance or disappearance — and its expected recovery behaviour.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user who has never seen the source can go from a clean Linux machine to a running
  tool showing their real GPU in under 5 minutes, following only the published instructions.
- **SC-002**: Installation completes in a single command on 100% of tested Linux distributions,
  with zero compilation steps and zero privilege escalations.
- **SC-003**: Reported memory figures match the vendor's own tooling within 5% across a 10-minute
  observation under varying load.
- **SC-004**: 100% of GPU-using processes reported by the vendor's tooling also appear in the
  tool's process list, correctly named and attributed.
- **SC-005**: The tool recovers unaided from suspend/resume and from a driver restart in 100% of
  trials, with zero restarts required.
- **SC-006**: After 24 hours of continuous running, the tool's own memory use is within 10% of its
  use at the 1-hour mark, and its update cadence is unchanged.
- **SC-007**: On a machine containing GPUs from two vendors, the tool accounts for 100% of GPUs
  physically present — monitored or explicitly marked unsupported, never absent.
- **SC-008**: Every figure the tool displays on real hardware is either a verified measurement or
  explicitly marked unavailable; across the verification period, zero incorrect values are
  presented as measurements.
- **SC-009**: The automated suite passes on a machine with no GPU and on a machine with an NVIDIA
  GPU, with the hardware-only portion adding no failures to the GPU-free run.
- **SC-010**: A user can find and change every available setting in under 60 seconds without
  documentation, and 100% of settings survive a reboot.
- **SC-011**: The tool continues to require zero elevated privileges and produces zero bytes of
  network traffic throughout all verification.
- **SC-012**: A user with no language-runtime tooling can go from downloading the self-contained
  file to a running tool in under 2 minutes and no more than three steps.
- **SC-013**: Both distribution forms report the same version and produce identical behaviour
  across the full validation procedure — zero behavioural differences.
- **SC-014**: Closing the window and reopening from the status area returns a current reading
  within two refresh intervals in 100% of trials.
- **SC-015**: On every tested desktop environment, the tool is recoverable after the window is
  closed — either from the status area, or because closing quit it. Zero cases where the tool is
  running but unreachable.
- **SC-016**: While closed to the status area, the tool's sampling activity is no higher than its
  existing hidden-window behaviour — the status icon adds zero continuous sampling cost.

## Assumptions

- **This feature adds no new monitoring capability.** Everything about what is measured and how it
  is displayed was settled in feature 001. This is about making it installable, verified, and
  durable on one specific platform.
- **NVIDIA only.** AMD and Intel remain unimplemented and continue to appear as detected but
  unsupported. The verification machine happens to contain a second-vendor GPU, which makes
  FR-015 directly testable rather than theoretical.
- **Linux only.** Windows work from feature 001 stays deferred; nothing here should make Windows
  harder to complete later.
- **A reasonably current NVIDIA driver.** The tool works with whatever the installed driver
  exposes and degrades honestly on older ones rather than refusing to start.
- **The user has a graphical desktop session.** A headless or terminal-only mode is out of scope;
  the tool must say so clearly rather than pretending otherwise.
- **Verification happens on at least one real machine**, not in continuous integration. CI has no
  GPU, so the hardware-verified portion is a documented human procedure whose evidence is recorded
  and whose captured responses feed the automated suite afterwards.
- **Two distribution forms, no native packages.** A language-package install plus one
  self-contained file. Native distribution packages (.deb, .rpm) and store formats are explicitly
  out of scope for this release: they multiply per-distribution work and ongoing repository
  maintenance, and the self-contained file already covers the user who does not want to know what
  the tool is written in.
- **The status-area icon is presence, not a second display.** It provides show/pause/quit and
  nothing more. Deliberately *not* an at-a-glance usage indicator: rendering live GPU usage into
  the icon would require sampling continuously while hidden, contradicting the existing rule that
  sampling stops when nothing is displayed, and turning a monitor into a permanent background
  load. If that is wanted later it needs its own specification and an explicit decision about
  that trade-off.
- **Status-area support is not universal.** Some desktop environments do not show these icons
  without additional configuration. The tool detects this rather than assuming, because the
  failure mode otherwise is the worst kind: a running program the user cannot see or recover.
- **No background service.** The tool runs while the user has it running. A daemon that collects
  when the interface is closed is out of scope and would conflict with the existing rule that
  sampling stops when nothing is displayed.
