# Feature Specification: GPU Usage Monitor

**Feature Branch**: `001-gpu-usage-monitor`

**Created**: 2026-08-16

**Status**: Draft

**Input**: User description: "GPU monitor tool to display gpu memory usage, track process that are using gpu,  with live updates of gpu resource, for major gpu brands across NVIDIA, AMD, Intel gpus.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See live GPU memory and load at a glance (Priority: P1)

A developer or workstation user opens the monitor and immediately sees every GPU in their
machine listed with its name, how much of its memory is in use versus total, and how busy it
currently is. The numbers refresh on their own while the window stays open, so the user can
watch memory climb during a training run or a render without touching anything.

**Why this priority**: This is the smallest slice that is useful on its own. A user who only
ever gets this screen can already answer "am I about to run out of GPU memory?" — the single
most common reason people reach for a GPU monitor.

**Independent Test**: Launch the tool on a machine with at least one GPU, start a workload that
allocates GPU memory, and confirm the displayed used-memory figure rises without any user
interaction and returns to baseline when the workload ends.

**Acceptance Scenarios**:

1. **Given** a machine with one or more supported GPUs, **When** the user opens the monitor,
   **Then** each GPU is listed with its model name, used memory, total memory, percentage of
   memory used, and current utilization, within 3 seconds of launch.
2. **Given** the monitor is open and showing a GPU, **When** a workload allocates additional GPU
   memory, **Then** the displayed used-memory value reflects the change within two refresh
   intervals without the user interacting with the window.
3. **Given** the monitor is open, **When** the user watches for 60 seconds, **Then** values
   update continuously and the interface remains responsive to clicking, scrolling, and
   resizing throughout.
4. **Given** a machine with multiple GPUs, **When** the user opens the monitor, **Then** every
   detected GPU appears as a separate entry, each independently labeled and readable.

---

### User Story 2 - See which processes are consuming the GPU (Priority: P2)

The user sees a live list of the processes currently using each GPU, showing each process's
name, identifier, and how much GPU memory it holds. When memory is nearly full, the user can
tell at a glance which process is responsible — including a forgotten notebook kernel or an
orphaned job from an earlier session.

**Why this priority**: Attribution is the difference between knowing there is a problem and
knowing what to do about it. It depends on the device view existing first, so it follows P1.

**Independent Test**: Start a known process that allocates GPU memory, confirm it appears in
the process list attributed to the correct GPU with a plausible memory figure, then end the
process and confirm it disappears from the list.

**Acceptance Scenarios**:

1. **Given** at least one process is using a GPU, **When** the user views that GPU,
   **Then** a list of consuming processes is shown with each process's name, process
   identifier, and GPU memory held.
2. **Given** a process using the GPU exits, **When** the next refresh occurs, **Then** that
   process is removed from the list without error.
3. **Given** a new process begins using the GPU, **When** the next refresh occurs, **Then** it
   appears in the list attributed to the GPU it is actually using.
4. **Given** a system where per-process attribution cannot be obtained for a GPU, **When** the
   user views that GPU, **Then** the process area states plainly that per-process data is
   unavailable for this GPU and why, rather than showing an empty list that implies no GPU
   activity.
5. **Given** a process the user does not have permission to inspect, **When** it is using the
   GPU, **Then** it is still counted in device totals and shown with whatever identifying
   information is available, marked as restricted rather than omitted silently.

---

### User Story 3 - One tool across mixed vendors and platforms (Priority: P3)

A user with a laptop containing an Intel integrated GPU and a discrete NVIDIA GPU — or a
workstation with AMD cards — opens the same tool and sees all of their GPUs together, in the
same units and layout, regardless of who made them. Where a particular vendor cannot report a
particular figure, the tool says so instead of guessing.

**Why this priority**: Cross-vendor coverage is what distinguishes this tool from the vendor
utilities users already have. It is valuable but only after the single-GPU experience is solid.

**Independent Test**: On a machine with GPUs from two different vendors, confirm both appear in
one list with consistent labels and units; on a machine with no supported GPU, confirm the tool
opens and explains what it found rather than failing.

**Acceptance Scenarios**:

1. **Given** a machine with GPUs from more than one vendor, **When** the user opens the monitor,
   **Then** all detected GPUs appear in a single unified list using the same units, column
   labels, and formatting.
2. **Given** a GPU whose vendor cannot report a given metric on this platform, **When** the user
   views that GPU, **Then** the metric is shown as unavailable with a short reason, and is never
   displayed as zero or as an estimate.
3. **Given** a machine with no detectable GPU or no usable driver, **When** the user opens the
   monitor, **Then** the tool opens successfully and explains what it looked for and what it
   found, instead of crashing or showing a blank window.
4. **Given** any supported operating system, **When** the user runs the monitor without
   administrator or root privileges, **Then** it starts and displays every metric available at
   that privilege level, and labels the rest as requiring elevated privileges.

---

### User Story 4 - Tune the view to the task (Priority: P4)

The user adjusts how often data refreshes — slowing it down on a battery-powered laptop,
speeding it up while chasing a short-lived memory spike — and sorts or filters the process list
to put the heaviest consumers on top. These choices persist to the next launch.

**Why this priority**: A quality-of-life layer over a tool that is already useful. Valuable for
daily users, but nothing is blocked without it.

**Independent Test**: Change the refresh interval and confirm the observed update cadence
changes accordingly; sort the process list by memory and confirm ordering; restart the tool and
confirm both settings were remembered.

**Acceptance Scenarios**:

1. **Given** the monitor is open, **When** the user selects a different refresh interval,
   **Then** updates occur at the new cadence starting with the next refresh.
2. **Given** a process list with several entries, **When** the user sorts by GPU memory used,
   **Then** entries are ordered accordingly and the ordering is preserved across refreshes
   rather than reshuffling on every update.
3. **Given** the user has changed refresh interval and sort order, **When** they close and
   reopen the monitor, **Then** their previous choices are still in effect.

---

### Edge Cases

- **No GPU or no driver present**: the tool opens, reports what was searched for and what was
  found, and remains usable rather than exiting or showing an empty frame.
- **Metric unsupported on this vendor/platform pair**: shown as explicitly unavailable with a
  short reason; never rendered as `0`, blank, or an interpolated value.
- **Per-process attribution unavailable**: common on some vendor and operating-system
  combinations; the device totals remain correct and the process area explains the gap.
- **Process exits between sampling and display**: the entry disappears cleanly at the next
  refresh with no error dialog and no stale row.
- **Process the user cannot inspect** (owned by another user, or sandboxed): counted in totals,
  displayed as restricted, never silently dropped.
- **Process running inside a container**: resolved to the host process consuming the GPU and
  named; where the host cannot resolve it at all, its memory still counts toward device totals
  and it is shown as unresolved.
- **A partitioned or virtualized GPU is present** (MIG instance, vGPU guest): presented as an
  unsupported device with a brief reason, rather than reported with figures that may be wrong
  for a partition. Other GPUs on the machine continue to work normally.
- **A vendor query hangs or is slow**: that GPU is marked as degraded or stale after a timeout
  while every other GPU continues to update normally; the interface never freezes.
- **A GPU appears or disappears while running** (external GPU connected or removed, driver
  restarted, hybrid graphics powering the discrete GPU on or off): the device list updates and
  the tool keeps running.
- **Machine sleeps and resumes**: sampling resumes without duplicate, negative, or wildly
  discontinuous readings.
- **Very large process counts**: the list stays scrollable and responsive rather than degrading
  as entries grow.
- **Long uptime**: memory consumed by the tool itself remains bounded no matter how long the
  window stays open.
- **Two identical GPU models in one machine**: each is distinguishable from the other in the
  interface.
- **Memory reported in differing units by different vendors**: all values are normalized to one
  consistent unit convention before display.
- **The monitor is minimized or hidden**: sampling throttles or stops so a background window
  does not consume resources it is meant to measure.

## Requirements *(mandatory)*

### Functional Requirements

**Device discovery and display**

- **FR-001**: System MUST detect all GPUs present on the machine from NVIDIA, AMD, and Intel and
  present them in a single unified list.
- **FR-002**: System MUST display, for each detected GPU: an identifying model name, a
  distinguishing identifier when multiple identical models are present, the vendor, memory
  currently used, total memory capacity, and memory used as a percentage of total.
- **FR-003**: System MUST display current GPU utilization for each device where the vendor and
  platform can report it.
- **FR-004**: System MUST normalize all memory figures to a single consistent unit convention
  across vendors and state that convention in the interface.
- **FR-005**: System MUST show a short bounded history of memory usage per device so the user
  can see the recent trend, not only the instantaneous value.

**Process attribution**

- **FR-006**: System MUST display, for each GPU, the processes currently consuming that GPU,
  including each process's name, process identifier, and GPU memory held.
- **FR-007**: System MUST attribute each listed process to the specific GPU it is using on
  multi-GPU machines.
- **FR-008**: System MUST add newly started GPU-using processes and remove exited ones within
  two refresh intervals, without error and without stale entries.
- **FR-009**: System MUST include processes the user lacks permission to inspect in device
  totals, displaying them as restricted rather than omitting them.
- **FR-010**: Users MUST be able to sort the process list by GPU memory used and by process
  name, with the chosen ordering stable across refreshes.

**Live updating**

- **FR-011**: System MUST refresh all displayed values automatically at a regular interval with
  no user interaction, defaulting to once per second.
- **FR-012**: Users MUST be able to change the refresh interval, and MUST be able to pause and
  resume live updating.
- **FR-013**: System MUST remain responsive to user interaction — clicking, scrolling,
  resizing, sorting — continuously while sampling is in progress.
- **FR-014**: System MUST time out any device query that does not return promptly, mark that
  device as stale or degraded, and continue updating all other devices.
- **FR-015**: System MUST reduce or suspend sampling when its display is not visible to the
  user.
- **FR-016**: System MUST display when each value was last successfully sampled, so a frozen or
  stale reading is distinguishable from a current one.

**Honesty and degradation**

- **FR-017**: System MUST represent any metric it cannot obtain as explicitly unavailable with a
  brief reason, and MUST NOT substitute zero, a placeholder, or an estimated value.
- **FR-018**: System MUST start successfully and remain usable on machines with no GPU, no
  supported GPU, or no working driver, reporting what it searched for and what it found.
- **FR-019**: System MUST run without administrator or root privileges, displaying every metric
  available at the user's privilege level and labeling metrics that would require elevation.
- **FR-020**: System MUST detect GPUs appearing or disappearing while running and update the
  device list accordingly without restart.

**Scope and conduct**

- **FR-021**: System MUST operate as a read-only observer: it MUST NOT terminate processes,
  alter clocks, power limits, or fan settings, and MUST NOT modify any system state other than
  its own saved user preferences.
- **FR-022**: System MUST keep all collected data local to the machine and MUST NOT transmit
  usage data, process names, or system information anywhere.
- **FR-023**: System MUST persist user preferences — refresh interval, sort order, and window
  layout — across sessions.
- **FR-024**: System MUST bound its own memory consumption regardless of how long it runs or how
  much history it accumulates.

**Platform and hardware scope**

- **FR-025**: System MUST run on Linux and Windows in this release. macOS support is deferred to
  a later release and is not required here.
- **FR-026**: System MUST NOT adopt any design that precludes adding macOS later: no
  platform-specific behavior may live outside a platform adapter boundary, and no
  Linux-or-Windows assumption may be embedded in the device model, the process model, or the
  interface.
- **FR-027**: System MUST scope device coverage to whole physical GPUs. Partitioned and
  virtualized GPUs — including NVIDIA MIG instances and vGPU guests — are out of scope for this
  release.
- **FR-028**: System MUST, when it encounters a partitioned or virtualized GPU it cannot model
  correctly, present that device as unsupported with a brief reason rather than reporting
  figures that may be wrong for a partition.
- **FR-029**: System MUST attribute GPU usage by processes running inside containers to those
  processes as the host machine sees them, so container workloads appear in the process list
  rather than going unaccounted for.
- **FR-030**: System MUST display, for a containerized process, whatever identifying information
  is obtainable beyond the raw host process identifier — such as the container it belongs to —
  where the host makes that determinable.
- **FR-031**: System MUST, where a GPU-consuming process cannot be identified at all because it
  is isolated in another process namespace, still count its memory in the device totals and
  display it as an unresolved process, rather than omitting it and understating GPU use.

### Key Entities

- **GPU Device**: A single graphics processor detected on the machine. Identified by a stable
  identifier that survives refreshes, plus vendor, model name, and an index distinguishing
  identical models. Carries its current memory used, total memory, utilization, and the time of
  its last successful sample.
- **GPU Process**: A process observed to be consuming a GPU. Identified by process identifier
  and name, carries the amount of GPU memory it holds, the device it is attributed to, and an
  access state indicating whether full information was obtainable.
- **Sample**: One point-in-time reading for one device, comprising its metric values, the
  timestamp it was taken, and the availability state of each metric within it. The bounded
  recent-history trend is a sequence of these.
- **Metric Availability**: For any given metric on any given device, whether it is available,
  unavailable because the vendor or platform cannot report it, unavailable because privileges
  are insufficient, or stale because the last query timed out. Every displayed value carries one
  of these states.
- **User Preferences**: The user's persisted choices — refresh interval, process list sort
  order, paused state, and window layout.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user opening the tool on a machine with a supported GPU sees complete device
  memory figures within 3 seconds of launch, with no configuration or setup steps.
- **SC-002**: A change in GPU memory usage is visible to the user within 2 seconds of it
  occurring, at the default refresh setting.
- **SC-003**: The interface responds to user interaction within 100 milliseconds at all times,
  including while data is being collected and including on machines with 8 or more GPUs.
- **SC-004**: A user asked "which process is using the most GPU memory right now?" can answer it
  from the tool in under 15 seconds without scrolling past the first screen of content.
- **SC-005**: The tool runs continuously for 24 hours with no growth in its own memory footprint
  beyond a stated bound, and no loss of update cadence.
- **SC-006**: The tool starts successfully and reports a clear, actionable message on 100% of
  test environments lacking a GPU, lacking a driver, or lacking vendor tooling — zero crashes
  and zero blank windows.
- **SC-007**: Every displayed value is either a real measurement or explicitly marked
  unavailable; across the full vendor and platform test matrix, zero fabricated, zeroed, or
  estimated values are presented as measurements.
- **SC-008**: 100% of the tool's functionality is reachable without administrator or root
  privileges, excluding only metrics the operating system itself gates behind elevation.
- **SC-009**: On a machine with GPUs from two different vendors, a user unfamiliar with the tool
  can identify how many GPUs the machine has and which is busiest within 30 seconds.
- **SC-010**: Zero bytes of usage, process, or system data leave the machine during any
  operation.
- **SC-011**: Every success criterion above is met identically on both Linux and Windows, with
  no behavioral difference beyond metrics the platform itself cannot supply.
- **SC-012**: On a machine running a GPU workload inside a container, the user can identify the
  responsible process from the tool; device memory totals account for 100% of GPU memory in use
  even where a process cannot be named.

## Assumptions

- **Single local machine**: The tool monitors GPUs in the machine it runs on. Remote hosts,
  clusters, and network-aggregated monitoring are out of scope for this release.
- **Linux and Windows this release, macOS deferred**: macOS is dropped from this release's scope
  because current Mac hardware ships neither NVIDIA nor discrete AMD GPUs, making the named
  vendor set a poor fit. This narrows the test matrix but does **not** license platform-specific
  design: macOS remains a future target, so the platform adapter boundary required by the
  project constitution still applies in full. See the constitution note below.
- **Whole physical GPUs only**: Partitioned and virtualized GPUs (NVIDIA MIG, vGPU) are out of
  scope. The tool targets desktops and workstations, not shared datacenter hardware.
- **Containerized processes in scope, partitioned GPUs not**: The common containerized ML
  workflow is supported — a process running in Docker is resolved to the host process consuming
  the GPU and named in the list. This is deliberately narrower than full datacenter support:
  the *device* remains a whole physical GPU, so MIG partitions and vGPU guests stay out of
  scope. Where a namespace-isolated process cannot be resolved at all, its memory is still
  counted in device totals and shown as unresolved.
- **Desktop application**: The primary interface is a graphical desktop window. A headless or
  command-line output mode is not part of this release.
- **Read-only by default**: Process termination and any hardware tuning are out of scope, per
  the project constitution's read-only principle. If users later want to end a runaway process
  from the tool, that is a separate opt-in feature requiring its own specification.
- **Default refresh cadence of one second**: Chosen as the common convention for system
  monitors — fast enough to feel live, slow enough not to burden the machine being measured.
  Users can change it.
- **Bounded short history**: Recent-trend display covers a rolling window on the order of
  minutes rather than a persistent long-term record. Historical logging to disk, alerting, and
  reporting are out of scope.
- **GPU memory is the primary process metric**: Per-process GPU memory is broadly obtainable
  across vendors; per-process GPU utilization percentage is not, and is treated as a
  best-effort metric shown only where the platform supplies it.
- **No installation of vendor drivers or SDKs**: The tool works with whatever vendor tooling is
  already present and degrades to fewer metrics when it is absent; it never requires the user to
  install additional vendor software to launch.
- **Non-technical stakeholders are not the audience**: Users are developers, ML practitioners,
  and technically capable enthusiasts who understand terms like "process" and "GPU memory".
- **Single-user session**: The tool shows what the running user can see. On shared multi-user
  machines, processes belonging to other users are surfaced as restricted rather than fully
  detailed, without requiring elevation.
