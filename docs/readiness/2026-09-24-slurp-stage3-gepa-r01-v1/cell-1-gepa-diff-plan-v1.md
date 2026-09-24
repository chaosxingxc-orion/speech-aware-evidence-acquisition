# CELL-1-GEPA: the diff plan against CELL-1

Status: **DIFF PLAN, not a registration.** No fragment for `CELL-1-GEPA` is written here on
purpose: the store it pins does not exist until the GEPA proposer cell seals and the curation runs,
and a fragment that pinned a `PENDING_` store digest would have to be re-pinned in the same cycle
anyway. This note is what the coordinator turns into fragments once
`knowledge/slurp/semantic/stage3-deltas-gepa-v1/` is released.

Run id `SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-V1`; twin
`SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-TWIN-V1`; the two fit identities and the two four-row smokes
follow CELL-1's own naming.

## What changes against `docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/`

| | CELL-1 | CELL-1-GEPA |
| --- | --- | --- |
| store pinned | `stage3-deltas-v1r` | `stage3-deltas-gepa-v1` |
| twin store | `stage3-deltas-twin-v1r` | `stage3-deltas-gepa-twin-v1` |
| `stage3_algorithm` | `tfgrpo-semantic-advantage-v1` (`update`, `context_application`) | `gepa-reflective-pareto-v1` (`update`, `selection`, `context_application`) |
| everything else | -- | **identical**: the locked v2.0 PLAN fragment plus exactly one added store, the same per-node `context_supply` routes (Solver 8 / Reviewer 4 / Planner 4 candidate-bound, Perception 4 unconditional), the same TRAIN Fold A population and its split identity, the same sealed PLAN comparator, the same own null (h_SLU 1.2485 / h_intent 0.9943), the same caps, the same session and geometry, the same failure policy |

That is the point of owner decision 101: three families differ in the delta store they release and
in nothing else, so their arms are comparable by construction.

## What must be true before the fragments are written

1. The GEPA proposer cell `SAEA-SLURP-STAGE3-GEPA-R01-V1` has SEALED and its six structural items
   have been read (`analysis-recipe-v1.json`).
2. `scripts/flights/batch/gepa_to_deltas.sh` has curated and released both stores, and its
   release-pins document carries the per-node **supply reach** against the registered SLURP
   candidate-intent catalog. **An inert route is what stopped cell B9a-rec**: if a node's slice
   reaches no registered intent, that node's route must be removed from the fragment rather than
   flown empty.
3. The decision-83 retention over the CELL-1 read has been written to
   `prepared/SAEA-SLURP-STAGE3-DELTAS-GEPA-V1/retention-gepa-v1.json` and passed to the curator.
4. The four-row smoke of CELL-1-GEPA has flown and sealed. CELL-1's own three launch failures were
   all found by a smoke or by the offline dry run, and all three fixes live in shared rails modules
   that this cell inherits: the unconditional route composed exactly once, the compact Perception
   state read through the declared output contract, and a later-phase route that introduces nothing
   new supplying nothing.
5. `analysis.native_episode_dry_run` has walked **every** row of the smoke roster with the
   candidate ids a real trace recorded, including a REVISE walk -- the realistic form the third
   CELL-1 failure forced.

## The read

`scripts/flights/batch/cell1_verdict.py` with this cell's own registered facts: pooled official
SLU-F1 and intent against the sealed PLAN arm at the plan's own null, the per-scenario table in both
weightings, the frontier row (decision 75), the arm-minus-twin line, and the per-node
delta-consumption table (which deltas reached which node, per scenario, saves and harms on the rows
that received each one).

A TRAIN Fold A number is a development number (owner decisions 28 / 86). The order of reads is TRAIN
lock -> DEV confirmation -> the single test read (owner decisions 99 and 107).

## What is NOT planned here

Comparing GEPA against Training-Free GRPO. Three arms on one comparator and one own null make such a
comparison possible; making it is a separate read with its own preregistration, built from the two
arms' CI95 intervals on the same population.
