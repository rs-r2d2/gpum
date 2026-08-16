# Phase 0 Research: Overall GPU Utilization

**Feature**: 006-overall-gpu-utilization | **Date**: 2026-08-16

---

## D-01: Nothing new is measured

**Decision**: Use the compute and memory-interface utilization figures already collected on every
refresh. No backend change, no additional query.

**Rationale**: Inspection of the running code found both figures already sampled every cycle. The
compute figure is rendered as a bare number and its history is recorded into a bounded buffer that
is then never drawn; the memory-interface figure is not displayed anywhere. This is the rare
feature where the measurement work is already done and only presentation is missing — which is why
FR-015 can require sampling cost to be provably unchanged.

**Consequence**: the feature cannot regress sampling performance, and a test asserts the per-device
query cost is unchanged.

---

## D-02: A fixed 0-100% scale, not auto-scaling

**Decision**: Draw the utilization trend against a fixed 0 to 100 percent range.

**Rationale**: The existing memory trend auto-scales to the device's total memory, which is
correct for a quantity whose maximum is a property of the hardware. Utilization is already a
percentage of a fixed maximum, so scaling it to the recent observed maximum would be actively
misleading: on an idle GPU, noise between 0% and 3% would fill the graph and look like heavy
sustained load. It would also make two GPUs incomparable at a glance, since each would be drawn
against its own recent peak.

**Alternatives considered**: auto-scaling for consistency with the memory graph — rejected on the
grounds above. A logarithmic scale to make low values visible — rejected as harder to read and
solving a problem nobody has; low utilization *should* look low.

---

## D-03: Labelling both graphs

**Decision**: Each trend graph carries a short label naming what it shows.

**Rationale**: FR-019. Two stacked graphs of near-identical appearance, one in bytes and one in
percent, are harder to use than one graph — the reader has to remember which is which, and will
sometimes get it wrong. The label costs a few pixels and removes the ambiguity entirely.

---

## D-04: Distinguishing the two activity figures

**Decision**: Label them by what they describe — compute activity and memory-interface activity —
rather than showing two adjacent percentages.

**Rationale**: FR-022. "GPU 40%  MEM 90%" invites a reader to think the second is memory *usage*,
which is a different figure already shown elsewhere on the same panel. The distinction that
matters is compute engine versus memory interface, and the labels should say so.

**Note on terminology**: the memory-interface figure is *not* how full the memory is. It is how
busy the path to memory was. The panel already shows memory occupancy a few lines above, so the
two must not read alike.

---

## D-05: Vertical space

**Decision**: Give the trend graphs a modest fixed height and keep the process table's minimum
visible area intact.

**Rationale**: FR-013 and SC-009. The panel already carries a memory bar, a memory trend, power,
energy, and a process table; adding a second graph is the change most likely to push the process
table out of view, which would trade a useful table for a decorative graph. The existing panel
has unused vertical space below the table at the default window size, so this fits — but it must
be verified rather than assumed, which SC-009 requires.

---

## D-06: Gaps, not zeros

**Decision**: Reuse the existing history mechanism, which already records availability alongside
each point and renders unavailable stretches as gaps.

**Rationale**: FR-005. A dropped reading and a measured 0% look identical on a graph and mean
opposite things. The mechanism for this already exists and is tested; the feature adds a second
series to it rather than a second way of doing it.

---

## No spikes required

Every mechanism is already present in the codebase. Nothing depends on hardware behaviour that
has not already been measured.
