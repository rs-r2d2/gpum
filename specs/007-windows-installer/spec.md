# Feature Specification: Windows Executable & Installer

**Feature Branch**: `007-windows-installer`

**Created**: 2026-08-17

**Status**: Draft

**Input**: User description: "Add windows exe build option with qt installer"

## Context

GPUM is delivered two ways today: a Python package, and a self-contained Linux AppImage. A
Windows user has exactly one route — install Python, install a package manager, resolve
dependencies themselves. That is the route feature 002 removed for Linux users on the grounds
that it put the tool out of reach of anyone who was not its author. On Windows it is still the
only route.

The constitution already requires this gap to be closed: the application "MUST be installable
and launchable on all three supported platforms without a compiler toolchain on the user's
machine." Windows is a supported platform, the vendor telemetry interface works there, and the
capability matrix already describes what Windows can and cannot report. What is missing is an
artifact.

This feature is not new monitoring capability. It is the delivery path that makes the existing
capability reachable on Windows, plus the verification that what it reports there is true.

**Two lessons from the Linux bundle carry over directly**, and both are correctness issues that
are invisible on the machine that builds the artifact:

- **Vendor driver libraries must never be bundled.** The vendor's management library is
  version-locked to the host's driver. A copy taken from the build machine either fails to
  initialise or — far worse — misreports against a different host driver, presenting wrong
  numbers as measurements on someone else's machine.
- **Absent capability must stay absent.** Windows cannot supply per-process GPU memory under
  its current driver model. The tool already reports that honestly; a Windows build must not
  quietly turn it into a zero.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Install and run on Windows without being a developer (Priority: P1)

Someone with a Windows machine and an NVIDIA GPU downloads a single file, runs it, and gets
GPUM in their Start menu. They launch it and see their actual GPU within seconds. They never
install Python, never open a terminal, and never read the source.

**Why this priority**: Until this exists, GPUM is unreachable on Windows by anyone who is not
willing to set up a development environment. Every other item in this feature refines something
that nobody can start.

**Independent Test**: On a clean Windows machine with an NVIDIA driver and no Python
installed, download the published artifact, run it, and launch GPUM from the Start menu. It
must display real GPU data with no additional steps.

**Acceptance Scenarios**:

1. **Given** a clean Windows machine with an NVIDIA driver installed and no Python, **When** the
   user runs the published installer, **Then** installation completes without a compiler,
   without administrator privileges, and without manual dependency resolution.
2. **Given** GPUM is installed, **When** the user launches it from the Start menu, **Then** the
   window opens and shows their real GPU within 5 seconds.
3. **Given** GPUM is installed, **When** the user launches it a second time, **Then** their saved
   preferences from the first session are already in effect.
4. **Given** a machine with no NVIDIA driver present, **When** the user launches GPUM, **Then**
   it opens and states what is missing, rather than failing to start or showing an empty window.
5. **Given** a machine where the user has no administrator rights, **When** they run the
   installer, **Then** it installs for that user alone and never prompts for elevation.
6. **Given** the machine has no network connection, **When** the user installs and launches
   GPUM, **Then** both succeed, because neither requires the network.
7. **Given** a user who already installed GPUM as a Python package on the same machine,
   **When** they install the Windows build and launch it, **Then** it reports the same version
   and shares the same saved preferences.

---

### User Story 2 - The Windows build tells the truth (Priority: P1)

Every figure GPUM shows on Windows is either a real measurement from the host's own driver or
an explicit unavailable state with a reason. Nothing is fabricated, and nothing is measured
against a library that came from the build machine rather than the user's own driver.

**Why this priority**: Equal to US1, and for the reason feature 002 exists. A delivery path that
works but reports wrong numbers is worse than no delivery path — the numbers look authoritative
precisely because the tool installed cleanly. Both failure modes named in the Context are
invisible to whoever builds the artifact and only appear on a stranger's machine.

**Independent Test**: On a Windows machine with an NVIDIA GPU, compare every figure the
installed build reports against the vendor's own tool, and confirm the artifact contains no
vendor driver library.

**Acceptance Scenarios**:

1. **Given** the built artifact, **When** its contents are inspected, **Then** it contains no
   vendor driver library, and this is enforced as a build-blocking check rather than a review
   habit.
2. **Given** GPUM running on Windows, **When** memory and utilization figures are compared with
   the vendor's own tool, **Then** they agree within the tolerance the project already applies
   on Linux.
3. **Given** Windows cannot supply per-process GPU memory under its driver model, **When** the
   process table is shown, **Then** that column reports an explicit unavailable state with a
   reason, and never `0`.
4. **Given** a machine whose driver is older than the build machine's, **When** GPUM runs,
   **Then** it works or degrades with a stated reason — it does not misreport.
5. **Given** the capability matrix, **When** this feature merges, **Then** every Windows cell
   reflects what was actually observed on Windows, with unverified claims marked as such.

---

### User Story 3 - Remove it cleanly (Priority: P2)

A user who no longer wants GPUM removes it through the ordinary Windows mechanism and it is
gone, leaving only the preferences they chose to keep.

**Why this priority**: Uninstall is what makes an installer safe to try. A tool that cannot be
cleanly removed is one users hesitate to install at all — but it is only reachable after US1.

**Independent Test**: Install, use, then uninstall through the standard Windows interface and
confirm what remains on disk and in the Start menu.

**Acceptance Scenarios**:

1. **Given** GPUM is installed, **When** the user uninstalls it through the standard Windows
   mechanism, **Then** the application, its Start menu entry, and any shortcut it created are
   removed.
2. **Given** the user uninstalls GPUM, **When** the uninstall completes, **Then** their saved
   preferences remain, so a later reinstall restores their settings.
3. **Given** GPUM is running, **When** the user starts an uninstall, **Then** they are told to
   close it first rather than left with a partially removed installation.
4. **Given** an existing installation, **When** the user installs a newer version over it,
   **Then** the result is one working installation, not two entries.

---

### User Story 4 - Run it without installing anything (Priority: P3)

A user on a managed or locked-down machine, or one who simply wants to try the tool without
committing to an installation, obtains a single executable file, runs it directly, and gets the
same application.

**Why this priority**: Valuable and genuinely distinct — a portable file reaches machines where
installers are blocked by policy — but it serves a narrower audience than US1 and is the part
of the request most likely to be dropped if effort has to be cut.

**Independent Test**: Copy the single executable to a machine with no GPUM installation, run it
directly, and confirm it behaves identically to the installed build.

**Acceptance Scenarios**:

1. **Given** the portable executable on a machine with no GPUM installed, **When** the user runs
   it directly, **Then** the application opens and shows their GPU with no installation step and
   no administrator privileges.
2. **Given** the portable executable, **When** the user runs it on a machine that also has an
   installed GPUM, **Then** both report the same version and read the same preferences.
3. **Given** the portable executable, **When** the user deletes the file, **Then** nothing of the
   application remains beyond their saved preferences.

---

### Edge Cases

- A machine with no NVIDIA GPU at all, or with only integrated graphics: the application must
  open and say so, not crash or present an empty window.
- A laptop with switchable graphics, where the discrete GPU is powered down until used: the
  device may appear, disappear, or report nothing while asleep.
- A user without administrator rights, on a machine where policy blocks unsigned installers.
- Antivirus or reputation screening quarantining or warning about a newly published artifact
  that has no download history.
- Installing over an existing installation of a different version, or of the other delivery form.
- A driver present but too old to supply some metrics.
- The machine has no network connection at install time or at run time.
- Windows on ARM hardware, where an x64 artifact may run under emulation or not at all.
- Multiple GPUs, including mixed vendors, where only some are supported.
- The user's preferences file was written by a newer version of the application.

## Requirements *(mandatory)*

### Functional Requirements

**Delivery**

- **FR-001**: The project MUST produce a Windows artifact that installs and launches on a
  machine with no Python runtime, no package manager, and no compiler toolchain.
- **FR-002**: Installation MUST complete without administrator privileges and MUST NOT prompt
  for elevation.
- **FR-003**: The installer MUST create a Start menu entry that launches the application.
- **FR-004**: The installer MUST offer, as user-selectable options rather than defaults imposed
  on the user, a desktop shortcut and starting the application when the user signs in.
- **FR-005**: Installation and launch MUST NOT require a network connection.
- **FR-006**: The project MUST also produce a single portable executable that runs directly
  without any installation step.
- **FR-007**: Every published artifact MUST be accompanied by a checksum that a user can verify
  before running it.

**Removal and upgrade**

- **FR-008**: The application MUST be removable through the standard Windows uninstall
  mechanism, removing the application, its Start menu entry, and any shortcut it created.
- **FR-009**: Uninstalling MUST leave the user's saved preferences intact.
- **FR-010**: Installing a newer version over an existing installation MUST result in exactly
  one working installation and one uninstall entry.
- **FR-011**: An uninstall or upgrade attempted while the application is running MUST tell the
  user to close it rather than leaving a partially removed installation.

**Truthfulness on Windows**

- **FR-012**: The artifact MUST NOT contain any vendor driver library. This MUST be enforced as
  a build-blocking check, because the failure is invisible on the build machine.
- **FR-013**: The application MUST resolve the host's own vendor management library at run time,
  so every measurement comes from the driver actually installed on the user's machine.
- **FR-014**: Where Windows cannot supply a metric — per-process GPU memory under its current
  driver model in particular — the application MUST report an explicit unavailable state with a
  reason and MUST NOT substitute zero.
- **FR-015**: Figures reported on Windows MUST agree with the vendor's own tool within the same
  tolerance the project already applies on Linux.
- **FR-016**: The capability matrix MUST be updated in this change to reflect what was actually
  observed on Windows, with any claim that was not observed marked as unverified.

**Consistency with the existing delivery forms**

- **FR-017**: The Windows build MUST report the same version as the Python package built from
  the same source.
- **FR-018**: All delivery forms on one machine MUST share the same saved preferences.
- **FR-019**: Application behaviour MUST NOT branch on which delivery form is running; the
  delivery form MAY be reported for diagnostics only.

**Build and release**

- **FR-020**: The Windows artifacts MUST be produced by a documented, repeatable build that a
  contributor can run, and MUST be built automatically on every change.
- **FR-021**: The build MUST fail rather than publish when any correctness check on the artifact
  does not pass.
- **FR-022**: Published Windows artifacts MUST be attached to the corresponding release
  alongside the existing Linux artifact.
- **FR-023**: The documented supported Windows versions and processor architectures MUST be
  stated, and the application MUST refuse to install on an unsupported one with a clear message
  rather than failing obscurely.
- **FR-024**: Windows artifacts ship unsigned for this release. The published documentation MUST
  therefore describe the reputation warning a user should expect to see, why it appears, and how
  to proceed past it — a warning the user was not told to expect is indistinguishable from a
  compromised download.
- **FR-025**: A user MUST be able to confirm an artifact is authentic without relying on the
  operating system's reputation check, using the published checksum.
- **FR-026**: The build MUST be arranged so that a signing step can be added later without
  reworking it, and MUST NOT bake in any assumption that artifacts are unsigned.
- **FR-027**: Windows behaviour MUST be verified on a physical Windows machine with an NVIDIA
  GPU before this feature is considered complete, and the capability matrix MUST distinguish
  what was observed there from what remains inferred.

### Key Entities

- **Installer artifact**: The file a Windows user downloads and runs to install GPUM. Carries
  the application and its runtime, but never a vendor driver library.
- **Portable artifact**: A single executable delivering the same application with no
  installation step, for machines where installers are blocked or unwanted.
- **Delivery form**: Which route delivered this instance — package, Linux bundle, Windows
  install, or portable. Diagnostic only; no behaviour may depend on it.
- **Capability matrix**: The maintained record of what works on each vendor and platform pair,
  distinguishing observed from unverified.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A Windows user with no Python installed goes from downloading the artifact to
  seeing their own GPU in under 3 minutes, in no more than 5 interactions.
- **SC-002**: Installation succeeds on an account with no administrator rights, with zero
  elevation prompts.
- **SC-003**: The application window appears and shows real GPU data within 5 seconds of launch.
- **SC-004**: Zero metrics are displayed as a fabricated value on Windows — every figure is a
  measurement or a stated unavailable state, verified across the full capability matrix.
- **SC-005**: Reported figures match the vendor's own tool within the project's existing
  tolerance, measured on real Windows hardware rather than assumed.
- **SC-006**: Uninstalling removes 100% of installed files and shortcuts, and retains 100% of
  the user's saved preferences.
- **SC-007**: Installing a newer version over an older one yields exactly one installation and
  one uninstall entry, with no user cleanup.
- **SC-008**: The published artifact contains zero vendor driver libraries, enforced by a check
  that blocks the build.
- **SC-009**: A contributor with no prior knowledge produces the same artifacts by following the
  build documentation, without assistance.
- **SC-010**: Install and first launch both succeed on a machine with no network connection.
- **SC-011**: Every Windows cell of the capability matrix is marked as observed or unverified,
  with no cell left implicitly claimed.
- **SC-012**: A user who meets the operating system's reputation warning finds it described in
  the published documentation before they meet it, together with a way to verify the download
  independently.

## Assumptions

- **The requester named the Qt Installer Framework** as the installer technology. This is
  recorded as a stated input; confirming it against the alternatives, and against the
  constraint that the tool already depends on Qt, belongs to planning rather than to this spec.
- **Per-user installation is the default**, because the constitution requires the tool to run
  without administrator privileges. A machine-wide install is out of scope unless it can be
  offered without making elevation the normal path.
- **The installer is offline.** It carries everything it installs and performs no update check,
  because the project promises that nothing leaves the user's machine. Any future updater would
  be a separate feature and would need that promise re-examined.
- **Scope is NVIDIA on Windows.** AMD and Intel remain registered stubs on Windows exactly as
  they are on Linux; this feature does not change vendor support.
- **Target is 64-bit x86 Windows 10 and Windows 11.** Windows on ARM is out of scope for this
  feature, and an unsupported platform is expected to be refused clearly rather than silently
  attempted.
- **Per-process GPU memory remains unavailable on Windows** under the current driver model.
  This is a documented platform limitation, not a defect to be fixed here.
- **No monitoring behaviour changes.** This feature adds a delivery path and the verification
  that the existing behaviour holds on Windows.
- **The existing release process is the destination.** Windows artifacts attach to the same
  releases that already carry the Linux artifact.
- **Artifacts ship unsigned for this release**, with the resulting warning documented rather
  than hidden. The build is kept arranged so a signing step can be added without rework, so the
  decision stays reversible once the project has a distributing identity. Signing is therefore
  a deferred decision, not a rejected one.
- **A physical Windows machine with an NVIDIA GPU is available** for verification. This is what
  makes US2 deliverable as written and what separates this feature from shipping an artifact
  that has been built but never run on the platform it targets.
