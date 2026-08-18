# Feature Specification: GPUM Project Website (GitHub Pages)

**Feature Branch**: `007-github-pages-site`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Create a gitpages website for GPUM project with user friendly download and usage details, code api description of importance, condtribution guidelines"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A newcomer downloads GPUM and gets it running (Priority: P1)

Someone hears about GPUM, lands on the project website from a search result or a link, and wants
to see their own GPU in a window as fast as possible. Within the first screen they can tell what
GPUM is, see what it looks like, confirm their machine is supported, and reach a working download
link. The download page walks them through the three steps that actually stand between them and a
running window — fetch the file, mark it executable, open it — and explains the one step that
catches almost everyone (marking it executable) rather than assuming it is obvious. The
alternative install route for people who prefer Python packaging is offered alongside, not buried.

**Why this priority**: This is the entire reason a project website exists. A visitor who cannot
get from the landing page to a running application has received no value at all, and every other
page on the site is addressed to someone who already completed this journey. It is also the
journey most damaged by the status quo, where the only instructions live in a repository README
that a non-developer visitor may never scroll to.

**Independent Test**: Give a person who has never seen GPUM only the site's URL, on a supported
Linux machine with an NVIDIA driver, and observe them reach a running GPUM window without asking
a question or opening the source repository.

**Acceptance Scenarios**:

1. **Given** a visitor arrives at the site's landing page, **When** the page finishes loading,
   **Then** they can see what GPUM does, an image of the running application, the supported
   platform and hardware requirements, and a visible path to download — without scrolling past
   more than one screen and without following a link first.
2. **Given** a visitor on the download page, **When** they follow the instructions in order,
   **Then** each step states the exact command to run, what a successful result looks like, and
   what the failure looks like if the step is skipped.
3. **Given** a visitor whose machine does not meet the requirements (non-Linux, no supported GPU,
   or an older system library baseline), **When** they read the requirements section, **Then**
   the site tells them plainly that GPUM will not run for them and what the alternative is,
   rather than letting them discover it after downloading.
4. **Given** the project publishes a new release, **When** a visitor uses the site's download
   link afterwards, **Then** the link resolves to a downloadable file for the current release and
   never to a missing-page error.

---

### User Story 2 - An existing user learns to read and configure the window (Priority: P2)

Someone already running GPUM wants to understand what they are looking at: three bars per GPU,
two trend graphs, a process table, and a settings dialog. The usage section explains each element
in the same order the window presents it, defines the metrics that are most often misread,
documents every control and setting with its available choices and default, and explains the
demonstration mode that lets anyone explore the interface with simulated GPUs and no hardware at
all.

**Why this priority**: Ranked below acquisition because it serves people who already have the
application open, but ranked above the developer-facing material because it serves the largest
audience after downloading. It also carries the project's honesty commitments — a user who
misreads "compute busy 100%" as "all cores saturated" has been misinformed by the tool, and
documentation is the only place that misreading can be corrected.

**Independent Test**: Ask a user with GPUM open to explain, using only the usage pages, what each
bar and graph shows, what a gap in a trend line means, and how to make the window refresh more
slowly — and check their answers against the application's actual behavior.

**Acceptance Scenarios**:

1. **Given** a user reading the usage section, **When** they look up any on-screen element (bar,
   trend graph, process table column, toolbar control, or setting), **Then** they find a
   description of what it measures, the units or scale it uses, and where applicable its default
   value and the full range of choices.
2. **Given** a user encountering a metric that is commonly misread, **When** they read its
   description, **Then** the description states explicitly what the metric does *not* mean.
3. **Given** a user who sees an unavailable value, a gap in a trend line, or a device reported as
   degraded, **When** they consult the site, **Then** they find an explanation of why the value is
   absent and confirmation that absence is reported rather than substituted with zero.
4. **Given** a visitor with no GPU or no supported driver, **When** they read the usage section,
   **Then** they learn how to launch the simulated-hardware demonstration mode and which
   scenarios are available.
5. **Given** a user hitting a common problem (permission denied, a download link that fails,
   nothing detected, an unsupported system), **When** they consult the troubleshooting material,
   **Then** they find the cause and the corrective action for that symptom.

---

### User Story 3 - A developer understands the code interfaces that matter (Priority: P3)

A developer evaluating GPUM, extending it, or reusing part of it wants to understand its shape
without reading every source file. The site presents a curated reference to the interfaces that
carry the design: the vendor backend interface every GPU integration implements, the normalized
data model that flows through the application, the way missing measurements are represented,
the backend registry, the platform adapter boundary, and the command-line entry point. Each entry
explains its purpose, its obligations, and the rules a correct implementation must honor —
including the ones that are non-negotiable project principles rather than style preferences.

**Why this priority**: Below the two user-facing journeys because it serves a much smaller
audience, but above general contribution mechanics because it is the material a contributor needs
*before* they can make a competent change. It is also the material least recoverable from reading
the code, since the important content is the contract and its rationale, not the signatures.

**Independent Test**: Ask a developer who has never seen the codebase to describe, from the API
reference alone, what a new vendor backend must implement, how it must report a metric it cannot
measure, and which layers it is forbidden to depend on — then verify against the existing
contract documents and boundary tests.

**Acceptance Scenarios**:

1. **Given** a developer reading the API reference, **When** they open the backend interface
   entry, **Then** they find every operation an implementation must provide, what each returns,
   which ones are forbidden to raise, and how failure and unavailability are expressed.
2. **Given** a developer reading the data model entry, **When** they look up how a metric is
   represented, **Then** they find that every metric is either a measured value or an explicit
   unavailability state with a reason, and that substituting zero or an estimate is prohibited.
3. **Given** a developer reading the reference, **When** they look for the dependency rules
   between layers, **Then** they find the permitted direction of dependencies stated explicitly
   and the consequence of breaching it.
4. **Given** a developer wanting to add support for a new GPU vendor, **When** they follow the
   reference, **Then** they can identify every file they must add or change and every file they
   must not, without inspecting the source tree first.
5. **Given** a reader of any API reference entry, **When** they want the authoritative detail,
   **Then** each entry links to the corresponding source module or design contract in the
   repository.

---

### User Story 4 - A prospective contributor knows how to contribute well (Priority: P4)

Someone wants to file an issue, fix a bug, or add a feature. The contribution section tells them
how to set up a development environment, how to run the checks that gate every change, what the
project's governing principles require of a change, how a change is expected to be described and
reviewed, and which failures signal a principle violation rather than a cosmetic problem. It also
tells them what the project will not accept, so effort is not wasted on work that cannot merge.

**Why this priority**: Valuable but addressed to the smallest audience, and dependent on the
API material above it to be actionable. A contributor arriving without this section can still
succeed by reading the repository; a user arriving without stories 1 and 2 cannot.

**Independent Test**: Have a developer follow only the contribution pages on a clean machine and
confirm they reach a working development environment with the full check suite passing, and can
correctly state what would block their change from being merged.

**Acceptance Scenarios**:

1. **Given** a new contributor, **When** they follow the environment setup instructions, **Then**
   they reach a state where the full automated check suite runs and passes on a machine with no
   GPU present.
2. **Given** a contributor preparing a change, **When** they consult the guidelines, **Then** they
   find the quality gates that must pass, the expectation to state which project principles the
   change touches, and the documentation that must be updated alongside specific kinds of change.
3. **Given** a contributor whose check run fails on an architectural boundary test, **When** they
   consult the guidelines, **Then** they learn that this indicates a violated project principle
   and that the correct response is to fix the change, never to relax the check.
4. **Given** someone who only wants to report a problem, **When** they look for how to do so,
   **Then** they find the reporting destination and what information to include, without first
   reading the development setup material.
5. **Given** a contributor considering work on an unsupported platform or a rejected direction,
   **When** they read the guidelines, **Then** the project's scope boundaries are stated
   explicitly enough that they can tell in advance the work would not be accepted.

---

### User Story 5 - The site stays accurate as the project changes (Priority: P5)

A maintainer merges a change to the project — a new release, an updated capability matrix, a
revised principle. The published site reflects it without anyone remembering to perform a
separate manual publishing step, and without the same fact having to be edited in two places and
drifting apart. Where the site restates something the repository already governs, it draws from
that source rather than keeping a second copy.

**Why this priority**: Lowest as a user-visible journey, but it determines whether the value of
all four journeys above survives the first month. Documentation that silently goes stale is worse
than none, because a confident wrong instruction costs a visitor more time than a missing one.

**Independent Test**: Merge a change that alters a documented fact (for example the capability
matrix or a supported version), then confirm the published site shows the new fact without any
manual publishing action.

**Acceptance Scenarios**:

1. **Given** a change to documented project facts is merged to the main line of development,
   **When** publishing completes, **Then** the live site reflects the change with no manual step
   beyond the merge itself.
2. **Given** a publishing attempt fails, **When** the failure occurs, **Then** the previously
   published site remains live and intact, and the failure is visibly reported to maintainers
   rather than passing silently.
3. **Given** a fact that exists both in the repository and on the site, **When** the repository
   copy changes, **Then** either the site derives from that copy or an automated check fails
   until the two agree.
4. **Given** any published page, **When** its links are checked, **Then** no link leads to a
   missing page, including links into the source repository and to release downloads.

---

### Edge Cases

- **A release is a pre-release.** The project's published releases have so far been marked as
  pre-releases, which conventional "latest release" links deliberately skip and resolve to a
  missing-page error. The site's download path must resolve to a real file under this condition,
  because it is the project's normal condition, not an exception.
- **No release exists yet, or the newest release has no downloadable bundle.** The download page
  must say so and offer the package-manager route, rather than presenting a link that fails.
- **A visitor is on Windows, macOS, or a phone.** The site must state that the application is
  Linux-only without ambiguity, and must not present a download path that cannot work for them.
  The site's own pages must still be readable on a small screen.
- **A visitor has an older system than the bundle supports.** The requirement must be stated
  before the download link, not discovered as a startup failure afterwards.
- **The screenshot cannot be seen** — images disabled, slow connection, or a screen reader. The
  meaning conveyed by the image must also exist as text.
- **A visitor arrives directly on a deep page** from a search engine, with no landing-page
  context. Every page must identify the project and offer a path to the download and to the site's
  other sections.
- **A capability is added, removed, or a principle is amended.** Any site statement about what is
  supported must be traceable to the repository's maintained record, so an amendment does not
  leave a contradicting claim published.
- **A stale page outlives its subject** — a documented setting, flag, or scenario name is renamed
  or removed. Site references to application behavior must be verifiable against the application.
- **A visitor blocks scripts, or uses only a keyboard, or has low vision.** Core content and
  navigation must remain usable.
- **A reader wants to copy a command** from a code sample that has wrapped across lines; the
  sample must remain copyable as a correct single command.

## Requirements *(mandatory)*

### Functional Requirements

#### Site foundation

- **FR-001**: The project MUST publish a public website hosted from the project's own repository,
  reachable at a stable public address, at no hosting cost to the project.
- **FR-002**: The site MUST present, at minimum, these distinct sections: an introduction and
  overview, download and installation, usage, an API reference, and contribution guidelines.
- **FR-003**: Every page MUST identify the project and provide navigation to every other top-level
  section, so that a visitor arriving on any page can reach any other.
- **FR-004**: The site MUST be readable and navigable on both desktop and small-screen widths, and
  its core content MUST remain available without client-side scripting.
- **FR-005**: The site MUST meet common accessibility expectations: meaningful text alternatives
  for images that carry information, keyboard-reachable navigation, sufficient text contrast in
  both light and dark presentations, and a logical heading structure.
- **FR-006**: The site MUST NOT include third-party analytics, tracking, advertising, or any
  mechanism that reports visitor behavior to an external party, consistent with the project's
  commitment that GPUM itself never transmits data off the user's machine.
- **FR-007**: The site MUST NOT collect personal information from visitors; it MUST NOT present
  forms, accounts, or comment systems that would do so.
- **FR-008**: The site MUST state its licensing and link to the project's license.

#### Download and installation

- **FR-009**: The site MUST present a primary, prominently placed download path that a visitor can
  reach from the landing page without prior knowledge of the project's release conventions.
- **FR-010**: The download path MUST resolve to an actual downloadable file for the project's
  current release, including when that release is marked as a pre-release.
- **FR-011**: The site MUST document the self-contained bundle route and the Python package route,
  presenting both as supported and stating what each is best suited to.
- **FR-012**: Installation instructions MUST be presented as ordered steps, each stating the exact
  command, the expected successful outcome, and — where a step is commonly skipped — the failure
  symptom that results and why the step is required.
- **FR-013**: The site MUST state the system requirements — operating system, hardware and driver
  expectations, minimum system library baseline, minimum language runtime version for the package
  route, and approximate disk footprint — before the download instructions, not after.
- **FR-014**: The site MUST explain why vendor driver libraries are not bundled with the
  application, in terms a non-expert can follow.
- **FR-015**: The site MUST document how to launch the application, how to add it to the system
  application menu, and every supported command-line option with its accepted values.
- **FR-016**: The site MUST provide troubleshooting entries for the known common failures,
  organized by the symptom the visitor observes rather than by internal cause.
- **FR-017**: Where a documented download or command references a version, the site MUST NOT
  require manual editing of that version in more than one place when a new release is published.

#### Usage documentation

- **FR-018**: The site MUST describe every element of the application window — per-device bars,
  trend graphs, the process table and its sortable columns, and toolbar controls — stating for
  each what it measures and the scale or units it uses.
- **FR-019**: The site MUST document every user-adjustable setting with its available choices and
  its default value.
- **FR-020**: The site MUST explicitly state what the most commonly misread metric does not mean,
  and MUST explain how unavailable values, gaps in trend graphs, and degraded devices are
  represented and why they are never shown as zero.
- **FR-021**: The site MUST document the simulated-hardware demonstration mode, including how to
  start it and the full list of available scenarios with what each demonstrates.
- **FR-022**: The site MUST include at least one image of the running application, accompanied by
  a text description conveying the same information for readers who cannot see it.
- **FR-023**: The site MUST state the project's behavioral guarantees — no invented values, no
  interface freezing, no modification of system or process state, no network transmission — in a
  place a prospective user encounters before downloading.

#### API reference

- **FR-024**: The site MUST present a curated reference covering the interfaces that carry the
  project's design, at minimum: the vendor backend interface, the normalized device and process
  data model including the representation of unavailable metrics, the backend registration point,
  the platform adapter boundary, and the application entry point and its options.
- **FR-025**: Each API reference entry MUST state its purpose, the obligations placed on
  implementers or callers, and the behavior required when data is unavailable or a query fails.
- **FR-026**: The API reference MUST state the permitted direction of dependencies between the
  project's layers and identify which rules are non-negotiable project principles rather than
  conventions.
- **FR-027**: The API reference MUST include a step-by-step account of adding support for a new
  GPU vendor, identifying every file that must change and the changes that must not be needed.
- **FR-028**: Every API reference entry MUST link to the corresponding source module or design
  contract in the repository as the authoritative detail.
- **FR-029**: The API reference MUST be explicitly scoped: it covers the interfaces that matter to
  an extender or integrator and does not claim to be exhaustive coverage of every symbol.

#### Contribution guidelines

- **FR-030**: The site MUST document how to set up a development environment and run the full
  automated check suite, and MUST state that the suite passes on a machine with no GPU present.
- **FR-031**: The site MUST list the quality gates every change must pass before it can be
  accepted, and the documentation that must be updated alongside specific categories of change.
- **FR-032**: The site MUST explain which check failures indicate a violated project principle
  rather than a stylistic problem, and MUST state that the correct response is to fix the change
  rather than relax the check.
- **FR-033**: The site MUST state the project's scope boundaries — including that only Linux is a
  supported platform, and that vendor support beyond what is implemented is stated honestly rather
  than implied — so a contributor can tell in advance which work would not be accepted.
- **FR-034**: The site MUST provide a path for reporting problems and asking questions that does
  not require reading the development setup material first, and MUST state what information a
  useful report contains.
- **FR-035**: The site MUST link to the project's governing principles document and its design
  documents.

#### Accuracy and publishing

- **FR-036**: The site MUST be republished automatically when changes are merged to the project's
  main line of development, with no manual publishing step.
- **FR-037**: A failed publish MUST leave the previously published site live and MUST be reported
  visibly to maintainers.
- **FR-038**: The site MUST NOT claim support for any platform, vendor, or capability beyond what
  the project's maintained capability record states; where the site restates such a fact, it MUST
  derive from that record or be automatically checked against it.
- **FR-039**: The site's internal links, links into the source repository, and download links MUST
  be automatically verified, and a broken link MUST be reported as a failure.
- **FR-040**: The repository's existing entry-point documentation MUST link to the site, and the
  site MUST NOT contradict it; content duplicated between the two MUST have a single source of
  truth.

### Key Entities

- **Site section**: One of the site's top-level areas (overview, download, usage, API reference,
  contributing). Has a title, a stated audience, and a position in navigation.
- **Page**: A single readable unit within a section. Has a title, body content, and links to
  other pages, repository sources, and external destinations.
- **Install route**: A supported way to obtain and run the application (self-contained bundle or
  Python package). Has prerequisites, ordered steps, verification of success, and known failure
  symptoms.
- **Release reference**: The current published release the download instructions point at,
  including its version identifier and downloadable asset. Must resolve correctly even when the
  release is marked as a pre-release.
- **Requirement statement**: A condition a visitor's machine must satisfy (operating system,
  hardware, driver, system library baseline, runtime version, disk space).
- **Window element**: A described part of the running application (bar, trend graph, table
  column, toolbar control, setting) with its meaning, units or scale, defaults, and available
  choices.
- **Demonstration scenario**: A named simulated-hardware situation the application can start in,
  with what it demonstrates.
- **API reference entry**: A documented interface, data type, or extension point with its purpose,
  obligations, unavailability and failure behavior, and a link to its authoritative source.
- **Quality gate**: A check a contributed change must pass, with what it verifies and what its
  failure means.
- **Capability claim**: Any statement on the site about what is supported, traceable to the
  project's maintained capability record.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time visitor on a supported machine can go from landing on the site to a
  running GPUM window in under 5 minutes, using only the site, with no questions asked.
- **SC-002**: At least 9 of 10 first-time testers complete the download-and-run journey on the
  first attempt without consulting the source repository or external help.
- **SC-003**: A visitor can identify whether their machine is supported within 30 seconds of
  arriving, without leaving the first screen of the landing page.
- **SC-004**: 100% of the site's links — internal, into the source repository, and download links
  — resolve successfully on every publish, verified automatically.
- **SC-005**: The download path resolves to a real downloadable file for the current release on
  every publish, including while all releases are marked as pre-releases; the "link is dead"
  failure occurs zero times.
- **SC-006**: 100% of the application's user-adjustable settings, toolbar controls, command-line
  options, process-table columns, and demonstration scenarios are documented with their choices
  and defaults.
- **SC-007**: Every documented common failure symptom has a corresponding troubleshooting entry;
  a user experiencing any of them finds the cause within one page.
- **SC-008**: A developer new to the codebase can, from the API reference alone, correctly state
  what a new vendor integration must implement, how it must report an unmeasurable value, and
  which dependencies are forbidden — verified against the project's design contracts.
- **SC-009**: A new contributor reaches a working development environment with the full check
  suite passing, on a machine with no GPU, in under 15 minutes using only the contribution pages.
- **SC-010**: A merged change to a documented project fact appears on the live site with no manual
  publishing action, within 10 minutes of merge.
- **SC-011**: Zero statements on the site claim support for a platform, vendor, or capability that
  the project's maintained capability record does not confirm, verified on every publish.
- **SC-012**: The site transmits no visitor data to any third party — zero tracking, analytics, or
  advertising requests, verifiable by inspecting the loaded page's outbound requests.
- **SC-013**: Every page is readable and navigable at small-screen widths, with core content and
  navigation intact when client-side scripting is unavailable.
- **SC-014**: The site's accessibility passes an automated audit with no critical findings, and
  every information-carrying image has a text alternative.
- **SC-015**: No fact is maintained in two places that can disagree; every such fact either has a
  single source or is automatically checked for agreement, with zero drift detected at publish.

## Assumptions

- The website is a documentation and distribution front door only. It does not host the
  application's downloads itself, does not require a server-side component, and adds no
  functionality to GPUM.
- The site is published from the existing project repository using its hosting platform's built-in
  static site publishing, at that platform's default project address. A custom domain is out of
  scope for this feature and can be added later without redoing the content.
- The site documents the current state of the project's main line of development. Per-release
  versioned documentation archives are out of scope for the first version.
- The API reference is a curated, hand-authored guide to the interfaces that matter to extenders
  and integrators, not exhaustive generated documentation of every symbol. This follows directly
  from the request for descriptions "of importance", and each entry links to source for detail.
- The repository README remains the entry point for people arriving via the source repository. It
  links to the site; the site is the fuller presentation. Where both describe the same fact, one
  is the source and the other derives from or is checked against it.
- Existing repository documentation — the capability matrix, the vendor-addition guide, the build
  guide, the licensing notes, and the design specifications — is reused as source material rather
  than rewritten into a second, independently maintained copy.
- The governing principles document is authoritative for every claim the site makes about
  supported platforms, vendors, privilege, and data handling. Notably: Linux is the only supported
  platform; NVIDIA is the only implemented vendor with AMD and Intel registered but unimplemented;
  the application is read-only, needs no elevated privileges, and transmits nothing off the
  machine. The site inherits these commitments and must not overstate any of them.
- The site's content is in English only; translation is out of scope.
- Search across the site, a blog or changelog feed, and community discussion features are out of
  scope for the first version.
- Screenshots are real captures of the running application, never mockups, consistent with the
  project's stance against representing anything it did not measure.
- Visitors are assumed to be on a modern browser; support for browsers without current standards
  support is out of scope, but core content must degrade gracefully.
