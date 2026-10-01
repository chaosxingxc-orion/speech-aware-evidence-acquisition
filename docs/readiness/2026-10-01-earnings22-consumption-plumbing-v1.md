# Earnings-22 consumption plumbing: model-free implementation

Status: library implementation and synthetic validation only. No experiment,
model contact, dataset read, source release, own-null estimate or adoption is
created by this change. The current owner214 search registration stays SLURP-only.

## Problem and resulting behavior

Earnings-22 already had a thin whole-dev runtime adapter, but its carrier key did
not resolve a consumption-module profile. The registered Earnings transcript
hygiene also belonged only to Earnings-21. The shared framework can now resolve
an E22 all-off composition and a separately identified E22 delivery rule without
copying an executor, controller, scorer or answering model.

`rails/adapters/earnings22_module_hooks.py` exposes the existing direct-only
program through the new `earnings22` profile. Its baseline fragment contains only
`policy` and `phase_material`; it reuses the existing generic transcription
instruction bytes in `probes/e21_native_window_direct_v1.txt`. That historical
filename does not transfer E21 data, ConEC terms, snapshots, window manifests,
scorers or admissions. The fragment is a composition layer, not a runnable flight.

The E22 hooks report numeric transcript units through the shared parser, accept
no ConEC entity-term argument and expose no carrier component admission or system
lock. Every armed component is refused. The profile's `flown_programs` interface
names the already implemented shared direct program; it is not E22 flight evidence.

`saea-deliver-earnings22-text-v1` inherits the existing transcript hygiene exactly,
with a distinct carrier identity. Existing E21 identities and behavior remain
unchanged. The rule strips documented outer role markup and normalizes whitespace;
it performs no entity substitution, numeric rewriting or scoring normalization.
Only an explicitly configured native episode runs it. Empty hygiene output is
refused so the episode's finite-completion policy decides the outcome.

## Shared custody and replay corrections

Synthetic negative tests exposed two existing portability gaps:

- Delivery verification re-derived the text but did not check that the row,
  recorded delivery rule and receipt belonged to the same carrier. Verification
  now refuses a missing or mismatched carrier identity, including substitution of
  a rule with identical text behavior but the wrong carrier.
- Offline delivery replay required SLURP label/filler diagnostics. Earnings
  hygiene has no such fields. Replay now reports those diagnostics and its
  SLURP-only unparsed count as null when not applicable, while preserving the
  existing SLURP output fields and values. Unchanged transcript text is not an
  unparsed SLURP answer. Replay still writes a new destination and refuses overwrite.

These corrections apply prospectively in this source revision. No frozen worker,
old receipt, sealed output, scorer job or experiment control was modified.

## Validation and its limits

Tests were written first: the missing E22 identity failed collection; subsequent
custody/replay tests reproduced six accepted carrier substitutions and two replay
key errors. The implemented path then passed:

- 392 related tests across module composition, both Earnings adapters, native
  role execution, delivery and shared raw/feature window execution; three
  data-dependent sealed-SLURP tests skipped with `SPEECHRL_DATA_DIR` unset.
- 268 tests in the additional bundle/custody/replay suite, including the stronger
  E22 refusal tests; three data-dependent tests skipped. This suite overlaps the
  first suite; the counts are not a unique combined total.
- Engineering-base and tool-catalog checks.

Coverage is 100% for the new E22 hook file and 90% for offline delivery replay.
All 25 measured changed executable statements in the hook, delivery rule, replay
and custody verifier were executed. This is not a whole-repository coverage claim.
The synthetic native graph exercises four units per Earnings identity through
Perception, Solver, Reviewer and Planner, with immediate ACCEPT. The acquisition
node is configured but unvisited; no acquisition success is claimed. Normalizer
on/off runs issue identical requests and preserve distinct delivery receipts.
The existing synthetic E22 adapter tests separately cover whole-dev loading,
carrier mismatch and unsupported-subset refusal. No real E22 trajectory was run.

## Remaining sequence

E22 still requires its own data-use and source decisions, roster/window/packet
preparation, capacity proof, in-chain null and exact scientific registration
before any GPU experiment or benefit claim. E21 or SLURP margins and allowances
cannot supply these. Cross-carrier text-policy optimization is not yet admitted
by the SLURP-specific `SystemTextPolicyBundle` entry. Preserve current P-SV-4,
Audio2Tool and E21 holds and all closed mechanisms.

The CONTROL2 initial-family scoring-entry recovery and proposer output-budget
decisions remain pending. This implementation neither resolves nor bypasses them.
