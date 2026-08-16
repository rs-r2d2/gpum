# Feature Specification: Process Table Column Sorting

**Feature Branch**: `003-process-table-sorting`

**Created**: 2026-08-16

**Status**: Draft

**Input**: User description: "Add click-to-sort column headers to the GPU process table, per-device and persisted"

## Context

The process table can already be sorted, but not the way anyone expects. Sorting happens through
a dropdown and a separate "Descending" checkbox in the toolbar; the column headers themselves do
nothing when clicked. One of the four visible columns — **User** — cannot be sorted at all. And
the dropdown applies one order to every device's table at once, so a machine with two GPUs cannot
have them arranged differently.

This feature replaces that with the interaction every process table uses: click a header to sort
by it, click again to reverse.

The design decisions were settled in a clarification session recorded in
[clarifications.md](./clarifications.md); this specification carries no open questions.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sort by clicking a column header (Priority: P1)

A user looking at the process table clicks the "GPU memory" header and the heaviest consumer
jumps to the top. They click it again and the order reverses. An arrow in the header shows which
column is sorting and in which direction. They never look for a separate control, because there
isn't one.

**Why this priority**: This is the request, and it is how every process table the user has ever
used behaves — Task Manager, Activity Monitor, `htop`. Inert headers read as broken.

**Independent Test**: Click each of the four column headers in turn and confirm the table
reorders by that column, that clicking again reverses it, and that the arrow tracks both.

**Acceptance Scenarios**:

1. **Given** a process table with several rows, **When** the user clicks a column header,
   **Then** rows reorder by that column and an arrow appears in that header showing the
   direction.
2. **Given** a column is already sorting, **When** the user clicks the same header again,
   **Then** the direction reverses and the arrow flips.
3. **Given** one column is sorting, **When** the user clicks a different header, **Then**
   sorting moves to the new column and the previous header's arrow disappears.
4. **Given** the table is sorted, **When** the data refreshes, **Then** the chosen order is
   preserved and rows with equal values do not swap places.
5. **Given** the user has sorted a table, **When** they look at the toolbar, **Then** no sort
   dropdown or direction checkbox is present — the header is the only sort control.

---

### User Story 2 - Sort every visible column (Priority: P1)

The user can sort by any column the table shows: process name, process identifier, the user
account that owns it, and GPU memory. No column is decorative.

**Why this priority**: Equal to US1 because a table where some headers respond and others do not
is worse than one where none do — the user cannot tell which are broken.

**Independent Test**: Sort by each of the four columns and confirm the ordering is correct for
that column's data type in both directions.

**Acceptance Scenarios**:

1. **Given** the process table, **When** the user sorts by process name, **Then** rows order
   alphabetically, case-insensitively.
2. **Given** the process table, **When** the user sorts by process identifier, **Then** rows
   order numerically, not as text — so 9 comes before 100.
3. **Given** the process table, **When** the user sorts by user account, **Then** rows order
   alphabetically by owner.
4. **Given** the process table, **When** the user sorts by GPU memory, **Then** rows order by
   actual quantity, not by the formatted text.
5. **Given** rows whose value for the sorted column is unavailable, **When** the user sorts in
   either direction, **Then** those rows appear last rather than being treated as zero or as
   alphabetically first.

---

### User Story 3 - Arrange each GPU's table independently (Priority: P2)

A user with more than one GPU sorts one device's table by memory and another by process name.
Each keeps its own arrangement, and sorting one never disturbs the other.

**Why this priority**: The natural consequence of putting sorting in the headers — each table has
its own. Valuable specifically for multi-GPU machines, so it follows the single-table behaviour.

**Independent Test**: On a machine with two or more GPUs, sort each table differently and confirm
both orders hold and neither affects the other.

**Acceptance Scenarios**:

1. **Given** two or more device tables, **When** the user sorts one, **Then** the others keep
   their existing order and their own arrows.
2. **Given** tables sorted differently, **When** the data refreshes, **Then** each keeps its own
   arrangement.
3. **Given** a new GPU appears while running, **When** its table is shown, **Then** it starts
   with the default order rather than inheriting another device's.

---

### User Story 4 - Keep the arrangement (Priority: P2)

The user arranges each GPU's table, closes the application, and returns later to find every
table exactly as they left it. A GPU that was disconnected and reconnected also remembers.

**Why this priority**: Re-sorting several tables on every launch turns a convenience into a
chore.

**Independent Test**: Sort several device tables differently, restart the application, and
confirm each is restored.

**Acceptance Scenarios**:

1. **Given** the user has sorted a device's table, **When** they close and reopen the
   application, **Then** that table is sorted the same way with the same arrow.
2. **Given** several devices sorted differently, **When** the application restarts, **Then**
   each is restored to its own order.
3. **Given** a GPU is disconnected and later reconnected, **When** its table reappears, **Then**
   it resumes the order the user last chose for that specific GPU.
4. **Given** a GPU the user has never sorted, **When** its table appears, **Then** it uses the
   default order.

---

### Edge Cases

- **A row's value for the sorted column is unavailable** (unnamed process, restricted owner,
  unreadable memory): sorts last in both directions. Treating a missing value as zero or as an
  empty string would rank it as though it had been measured.
- **Two rows have identical values in the sorted column**: their relative order stays fixed
  across refreshes rather than shuffling every second.
- **A process appears or disappears** while a sort is active: the table re-sorts without losing
  the user's chosen column or direction, and without resetting scroll position.
- **The table is empty**: the header still shows the active sort, so the arrangement is clear
  before any process arrives.
- **A device's table shows an explanation instead of rows** (per-process data unavailable):
  the stored sort for that device is retained for when rows return.
- **Two GPUs of the same model**: each is remembered separately, because they are distinct
  devices.
- **A GPU is replaced by a different card in the same slot**: treated as a new device with the
  default order, since it is not the GPU whose arrangement was saved.
- **Saved settings are missing or unreadable**: every table falls back to the default order
  rather than failing to display.
- **A saved sort refers to a column that no longer exists**: falls back to the default order.

## Requirements *(mandatory)*

### Functional Requirements

**Header interaction**

- **FR-001**: Users MUST be able to sort the process table by clicking a column header.
- **FR-001a**: Clicking a column that is not currently sorting MUST apply the direction that
  answers the question that column is usually asked: descending for GPU memory, so the largest
  consumer appears first; ascending for process name, identifier, and user.
- **FR-002**: Clicking the header of the column already sorting MUST reverse the direction.
- **FR-003**: The sorting column and direction MUST be shown by an indicator in the header.
- **FR-004**: Exactly one column MUST sort at a time; sorting a new column MUST clear the
  previous column's indicator.
- **FR-005**: The existing toolbar sort dropdown and direction checkbox MUST be removed, so the
  header is the single sort control.

**Sortable columns**

- **FR-006**: All four displayed columns MUST be sortable: process name, process identifier,
  user account, and GPU memory.
- **FR-007**: Process identifier MUST sort numerically, not as text.
- **FR-008**: GPU memory MUST sort by underlying quantity, not by formatted text.
- **FR-009**: Process name and user account MUST sort alphabetically, case-insensitively.
- **FR-010**: Rows whose value for the sorted column is unavailable MUST sort last in both
  directions, never as zero or as an empty string.

**Stability**

- **FR-011**: The chosen order MUST be preserved across data refreshes.
- **FR-012**: Rows with equal values in the sorted column MUST keep a fixed relative order
  across refreshes, so the table does not reshuffle under the pointer.
- **FR-013**: Re-sorting after a refresh MUST NOT reset the table's scroll position or clear the
  user's row selection.

**Per-device independence**

- **FR-014**: Each device's process table MUST sort independently.
- **FR-015**: Sorting one device's table MUST NOT change the order or indicator of any other.
- **FR-016**: A newly appearing device MUST start with the default order rather than inheriting
  another device's.

**Persistence**

- **FR-017**: Each device's sorting column and direction MUST persist across application
  restarts.
- **FR-018**: Saved sorting MUST be associated with the specific GPU, so a device that is
  disconnected and reconnected resumes its own arrangement.
- **FR-019**: A device with no saved sorting MUST use the default order: GPU memory, descending.
- **FR-020**: Unreadable or missing saved settings MUST fall back to the default order rather
  than preventing the table from displaying.
- **FR-021**: A saved sort naming a column that no longer exists MUST fall back to the default
  order.

**Boundaries**

- **FR-022**: Sorting MUST NOT change which processes are shown, any device total, or any
  measured value — it affects presentation only.
- **FR-023**: Sorting MUST NOT alter the sampling cadence or cost.
- **FR-024**: Re-sorting MUST NOT make the interface unresponsive, including on tables with
  several hundred rows.

### Key Entities

- **Sort Order**: The column a table is sorted by and its direction. One per device table.
- **Saved Sort Orders**: The persisted association between a GPU's stable identity and the sort
  order the user last chose for it, retained across restarts.
- **Sortable Column**: A displayed column together with how its values compare — numerically,
  alphabetically, or by quantity — and where rows with unavailable values rank.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can sort the process table by any column within 2 seconds of deciding to,
  using only the table itself.
- **SC-002**: 100% of displayed columns respond to a header click; zero columns are inert.
- **SC-003**: The sorted order and indicator survive 100% of data refreshes over a 5-minute
  observation, with zero instances of equal-valued rows swapping places.
- **SC-004**: On a machine with two or more GPUs, sorting one table changes no other table's
  order in 100% of trials.
- **SC-005**: 100% of per-device sort arrangements are restored after an application restart.
- **SC-006**: A GPU disconnected and reconnected resumes its own saved arrangement in 100% of
  trials.
- **SC-007**: Rows with unavailable values appear last in both directions in 100% of cases; zero
  instances of a missing value ranking as though it were measured.
- **SC-008**: Re-sorting a table of 500 rows completes without perceptible delay and without
  breaching the application's existing responsiveness commitment.
- **SC-009**: Device totals and the set of processes shown are byte-identical before and after
  any sort operation.

## Assumptions

- **Extends existing behaviour rather than adding a capability.** Sorting already exists in a
  limited form; this changes how it is invoked, widens it to every column, makes it per-device,
  and persists it. No new data is collected.
- **The four current columns are the scope.** Process name, identifier, user account, and GPU
  memory. If columns are added later, they are expected to be sortable by the same mechanism,
  but adding columns is not part of this work.
- **No multi-column sorting.** One column at a time. Sorting by memory *then* name is a
  different feature with its own interaction cost, and no evidence suggests it is wanted.
- **No column reordering, resizing persistence, or show/hide.** Those are adjacent table
  features that were explicitly excluded during clarification to keep this focused.
- **Saved sort orders are retained indefinitely, without pruning.** This was chosen deliberately
  over an aged-out alternative. The settings file will accumulate one small entry per GPU the
  machine has ever had, including hardware long since removed, and will never self-clean. Each
  entry is a column name and a direction, so the practical cost is negligible — but it grows
  monotonically, and is worth revisiting if the settings file is ever used for something
  size-sensitive.
- **Sorting is a view concern only.** It never affects what is sampled, what is measured, or
  what is reported. A user cannot change the numbers by rearranging the table.
- **Existing stability behaviour is preserved.** The table already keeps equal-valued rows in a
  fixed order across refreshes and already ranks unmeasurable memory last; both must survive
  this change rather than being rebuilt.
