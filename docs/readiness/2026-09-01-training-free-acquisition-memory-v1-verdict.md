# Training-free acquisition memory v1 — discovery support failed

Date: 2026-09-01. Status: **DISCOVERY CONSUMED; HOLDOUT NOT READ**. Experiment:
`SAEA-SN-MF-TFRL-ACQUISITION-MEMORY-V1`. Policy artifact:
`docs/checks/speech-aware-evidence-acquisition/2026-09-01-training-free-acquisition-memory/policy.json`
(file SHA-256 `73286b10764187dfc0cb6f78b742f4dafb71b66f0e5cd9fe96907da22c29ecf9`;
self-hash `205915d0914d57333cbe3f435b8f73d9882324acaf2b1a2af115b605f3132ae5`).

## Verdict

The discovery support gate **FAILED**. No policy was selected, and the separate holdout command is
mechanically blocked. DEV-500-NEW400 rewards were not opened by this experiment.

The frozen-cell replay passed every fidelity condition before the policy table was read: 100 of 100
retain/dispatch decisions reproduced, 37 of 37 dispatched supplies matched exactly, the committed
72 of 100 score reproduced, eight vectorized recalls matched the registered recall function, and
900 cosine probes matched the scalar policy implementation. The offline guard recorded zero
connection attempts.

## Discovery numbers

The locked baseline dispatched 37 of the 100 DEV-100 round-4 trajectories. Whole utterance groups
produced 26 tuning decision points and 11 reserved discovery-gate points.

| local support | contacts suppressed on tune | correct answers lost | admissible? |
|---|---:|---:|---|
| `k = 1` | 12 of 26 | 4 | no |
| `k = 3` | 10 of 26 | 3 | no |
| `k = 5` | 0 of 26 | 0 | no — no efficiency gain |
| `k = 7` | 0 of 26 | 0 | no — no efficiency gain |

Every registered radius from 0.05 through 0.30 produced the same row at a fixed `k`. The aggressive
rules therefore did not fail because the radius was slightly misplaced; the nine-field scalar state
put successful and unsuccessful evidence acquisitions in the same local neighborhoods. Increasing
neighbor support removed the harm only by removing every stop.

## Interpretation

This is a useful falsification of the first training-free control representation. Retrieval score,
fusion margin, admitted load, supply load, and direct parse status are not sufficient statistics for
the marginal value of the second contact on this discovery surface. A training-free controller built
on those scalars cannot obtain a Pareto improvement: it trades task accuracy for contacts, or exactly
replicates the baseline.

The failure does not weaken the locked BLEND result. The controller sat on top of that baseline,
never changed its policy or knowledge bytes, and never widened dispatch. It also does not reopen the
failed E108/T500 route.

## Next admissible iteration

The next small-scale iteration must change the state representation, not relax the zero-harm gate or
expand the sample. The direct-answer query vector is already runtime-visible and is the information-
bearing object used by retrieval. A v2 episodic memory may therefore use query-vector cosine plus
the registered action return, with the same default-ACQUIRE rule, utterance-group isolation, finite
grid, and two-stage artifact boundary. It remains on DEV-100 until it produces a zero-harm discovery
gain. NEW400 stays closed to this branch until then.

No threshold from v1 may be re-read on NEW400, and the failed scalar grid is not silently extended.
Any v2 is a new registered experiment with its own policy schema and falsifier.
