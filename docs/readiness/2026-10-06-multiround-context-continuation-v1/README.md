# Multi-round context continuation

Status: engineering verified, no real next-iteration preparation or actor admission.

The shared continuation previously accepted only the original v1 input. A further
iteration could not retain its complete rejected history and process feedback.
The existing v2 path now accepts a validated v1 or v2 immediate parent and requires
exactly the next iteration. It keeps the active evaluated population unchanged.

An actor sees the latest rejected history/process pair plus chronological abstract
`prior_continuations` for earlier pairs. Source rosters, concrete task content and
private provenance remain excluded. Cumulative exposure stays in private custody
and propagates into compiled children. All inherited content counts against the
registered byte cap; exceeded capacity fails rather than dropping adverse history.
Single-continuation actor bytes remain unchanged, verified against the real update4
input and its frozen source implementation.

Whole-trial evaluation resolves the original evaluated population through every
validated ancestor. It rechecks every intermediate registration before and after
measurement, as well as immutable packets and evidence. This preserves the existing
criterion, complete source-family reads, unique official scores and root decisions.
The negative tests cover changed intermediate registration/evidence, byte limits,
privacy and cumulative exposure through three continuations and shared compilation.

All111 relevant tests pass; both changed modules have100percent statement coverage.
The engineering-base check passes. See the exact receipt in
`docs/receipts/continuation/2026-10-06-multiround-context-continuation-prepared.json`.

This is preparation for a later prospectively registered update. It does not choose
this trial's outcome, promote policies, consume proposal slots, export partial
feedback, invoke a model/scorer or change the current frozen GPU worker. The actual
complete-trial feedback preparation and root retain/reject decision remain required.
