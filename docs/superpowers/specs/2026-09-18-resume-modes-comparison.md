# Resume modes for an aborted attempt — comparison and choice (2026-09-18)

Owner decisions 22 and 24 (2026-09-18). Decision 22 makes checkpoint resume a standing
requirement of every experiment registered from now on; decision 24 asks which resume mode that
requirement should be met with. This note compares four and records the choice. The implemented
mode is A (`core.flight.resume`, `core.bundle.outputs` invariant I7r, section 3 E10 of
`2026-09-16-slurp-v2-base-program-design.md`).

The rule every mode must satisfy, whatever its mechanism: a resume-recovery applies only when the
code and request bytes are unchanged (infrastructure failure, never a harness or config defect);
every complete row of the aborted attempt is kept without selection; every partial or unstarted row
is re-flown in full; the merged manifest declares its predecessor and scores once; and the bundle
verifies kept rows against the predecessor's recorded bytes.

## The four modes

**A — trace replay plus seal-time merge (implemented).** The recovery attempt reads the aborted
attempt's trace, replays each sample's terminal episode receipt into the in-memory result the live
runner produces, flies only the rows that are not COMPLETE, and seals the union through the one
`_canonical_output_rows` stage. The manifest declares `predecessor_attempt`; the verifier holds
each kept row against the predecessor trace.

**B — incremental canonical-row checkpoints.** The flight writes each row's canonical form to an
append-only checkpoint file as it completes; the recovery reads that file and skips the rows in it.

**C — chunked sub-attempts.** The roster is split into K chunks, each flown and sealed as its own
attempt with its own manifest; the scorer merges the K manifests. A failure loses at most one
chunk.

**D — streaming `outputs.jsonl` appends.** The seal's output file is written incrementally during
the flight instead of at the end; the recovery appends to it.

## Comparison

| Axis | A (trace replay + merge) | B (row checkpoints) | C (chunked sub-attempts) | D (streaming appends) |
| --- | --- | --- | --- | --- |
| Custody of a kept row | the predecessor trace, unchanged; the row is re-derived from the bytes the frozen core actually returned | a checkpoint file that is itself new custody: it must be hash-pinned, bound to the attempt, and proved to be a function of the trace | each chunk keeps ordinary single-attempt custody | the half-written outputs file is custody of nothing until it is hashed; a crash can leave a torn line |
| Verification complexity | one new invariant (I7r): re-hash the declared trace, re-hash the kept list, hold each row against exactly one trace | I7r plus a checkpoint-integrity invariant, plus proof that a checkpointed row equals the row the seal would have written | no new invariant per chunk; a new cross-manifest invariant for the merge (same protocol hash, disjoint rosters, one score) | I7 must accept a partially written file; the outputs artifact hash stops being a seal-time fact |
| Granularity of loss | one row (the row in flight) | one row | one chunk (roster / K rows) | one row, if the torn tail can be detected |
| Sealed-bytes invariants | unchanged: rows are still rendered once, by the same stage, and a kept row is byte identical to the row the aborted attempt would have sealed | unchanged if the checkpoint is exactly the canonical row; otherwise two writers of the same bytes | unchanged per chunk, but the paper-facing number comes from K manifests, which the "one score per complete manifest" rule forbids without a merge step | weakened: the outputs file is mutated during the flight, so its hash is not a function of a finished attempt |
| Non-native cells (E21 windows, Audio2Tool) | needs one classifier per terminal-custody form; today it covers the native role episode and refuses anything else by name (obs/window dispatch and execution-unit rosters seal per unit, not per sample) | carrier-agnostic: whatever the flight can seal, it can checkpoint | carrier-agnostic | carrier-agnostic |
| GPU cost of a recovery | zero for kept rows; only the unfinished rows are re-flown | same | same, except the chunk that died is re-flown whole | same |
| Cost during a healthy flight | zero: nothing extra is written, and an uninterrupted attempt is byte-identical to one flown before this change | one file write per row, plus its fsync discipline | K seals, K manifests, K scoring jobs | one file write per row |
| Implementation cost (this change) | one new module, one seam in the dispatch, one seam in the seal, one manifest field, one bundle invariant | the above plus a checkpoint writer, its crash semantics, and a second row-equality proof | a chunk planner, a cross-manifest merge in the scorer, and K-fold receipt/ledger plumbing | a rewrite of the seal's write path and of the outputs artifact contract |
| Works on attempts that are ALREADY aborted | yes — the B4b replicate attempt of 2026-09-17 is recoverable today, with no checkpoint it never wrote | no: only attempts flown after the checkpoint writer exists | no | no |

## Why A now

1. It recovers the attempt in front of us. The aborted B4b replicate wrote no `outputs.jsonl` (rows
   are canonicalised at seal) but it wrote its trace, and that trace already contains each
   episode's terminal receipt: 580 of its 584 started rows are COMPLETE and re-derivable, 4 lost
   their last response. A checkpoint mode recovers none of them.
2. It adds no writer to the hot path. An uninterrupted flight is byte-identical to one flown before
   this change, so the mode cannot itself become a source of defects in the 1,080-row cells.
3. Its custody is the strongest of the four: a kept row is verified against the bytes the frozen
   core returned, in the trace it returned them into — not against a derived file this repository
   wrote about them.
4. The trace is already a hash-pinned, manifest-declared artifact, so the new invariant is a
   binding between two existing artifacts rather than a new class of artifact.

## What B would add later

B is the natural successor, not a rejected alternative: it is carrier-agnostic, so it extends
resume to the cells A cannot classify today (the Earnings window/obs dispatch and execution-unit
rosters, whose terminal custody is a stitch rather than one episode receipt). The cheap form is to
write each row's ALREADY canonical form — the exact bytes `_canonical_output_rows` produces — into
an append-only per-attempt checkpoint, hash-pinned at seal, with the resume path reusing A's merge
and A's I7r custody with the checkpoint standing in for the replay. Adopt it when a non-native
carrier first needs a resume, or when a single cell's wall time makes the loss of an in-flight row
material; until then the replay covers the cells in flight, and one recovery mechanism is easier to
keep correct than two. C stays available for a genuinely long campaign (it is a scheduling
decision, not a custody one) and would need the cross-manifest merge rule before its first use. D
is not pursued: it buys the same granularity as B while weakening the invariant that an outputs
artifact's hash describes a finished attempt.

## 2026-10-14 — mode B landed (owner decision 309)

The "What B would add later" trigger fired: the NX-T R1 column died in a host restart with no trace on
disk, because nothing a flight produces is durable before its seal (design and root cause:
`2026-10-14-row-checkpoints-and-resume-mode-b-design.md`). Mode B is now implemented in the cheap form
described above, with one difference from the sketch: the checkpoint also stores the row's serialized
trace lines, so it is self-contained custody and mode A's I7r check is reused unchanged — a resume
materializes the kept rows' lines as the predecessor trace under its own attempt directory, and the
verifier re-derives that file from the pinned checkpoint.

* Every phase-program flight in the continuous form now appends one fsynced, hash-chained record per
  settled row to `<run_id>.rows.ckpt.jsonl`; the seal holds it against the sealed rows and pins its
  sha256 in the manifest (`row_checkpoint`).
* `resume_from` accepts `{"attempt_id", "checkpoint_sha256"}` (mode B) beside the mode-A form; a list may
  mix them. Mode A stays, for attempts that were flown before checkpoints existed.
* The table row "Works on attempts that are ALREADY aborted" is unchanged: mode B recovers only attempts
  flown after the writer exists. Still not covered: the per-phase barrier form, fixed and obs policies and
  execution-unit rosters (they do not checkpoint rows).
