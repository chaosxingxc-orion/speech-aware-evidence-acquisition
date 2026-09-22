# Cell ROLL-1: the Stage-3 grouped-Solver rollout: launch runbook

Preregistration: [`../2026-09-22-slurp-stage3-rollout-r01-v1-preregistration.md`](../2026-09-22-slurp-stage3-rollout-r01-v1-preregistration.md).
Engineering spec: `docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md` section S3-2.

## 0. In one paragraph

The locked v2.0 default plan's fragment (cell PLAN) with EXACTLY the four Solver keys changed to the B2 v3
grouped-sampling form (`samples=5`, `decoding_overrides`, `commit`) and `native_episode.deliver_normaliser` removed
(a grouped Solver and the delivery normaliser cannot combine; the v3 projection moves to S3-3's offline scoring
instead), flown on the S3-1 construction roster (`SLURP-STAGE3-CONSTRUCTION-R01`, 800 rows) rather than TRAIN Fold A.
Everything else -- `knowledge_stores.slot-contracts`, `phase_material`, the task instruction template, the geometry,
`scorers` -- stays byte-identical to cell PLAN (`tests/unit/test_stage3_rollout_baseline_cell.py` is the byte proof).

## 1. What is registered here

Baselines `configs/baseline/slurp-native-stage3-rollout-baseline-v1.json` and
`-smoke-4-baseline-v1.json`, experiment fragments `configs/experiment/slurp-native-stage3-rollout-r01-v1.json` /
`slurp-native-stage3-rollout-r01-smoke-4-v1.json`, this package (README, preregistration). **NOT registered here**:
a campaign plan, exposure-ledger rows, a root-admission decision receipt, or the `generation-plan` /
`fit-plan` / `protocol-registered` / `analysis-recipe` JSON siblings the PLAN package carries -- those are minted by
`scripts/flights/repin_cell.py` from a REAL prepared phase supply and a REAL promoted-packet binding, neither of
which can exist before the roster-bound placeholders below resolve (item 3). Root registers the ledger rows; this
package does not.

## 2. What must happen before this cell can fly (in order)

1. Promote the S3-1 construction roster's featcache packets (a registered `SAEA-SN-...-PREPROCESS` preparation; the
   ENCODE step is itself a tool contact, registered before it runs -- S3-1's own docstring).
2. Register and run the intent-boundary segment-vector encoding pass against the roster's own recordings (a tool
   contact), analogous to `SAEA-SLURP-TFRL-FOLD-A-SPEECH-QUERY-ENCODING-V1`.
3. Register the train-exemplars query-vector alias export (MODEL-FREE: a subset/rename of the pool-side content
   vectors already sealed for every TRAIN utterance -- no encoder contact).
4. Re-pin the 15 `PENDING_`-prefixed fields in both baseline fragments (`stage3_pending_placeholders` documents
   each one) from the artifacts steps 1-3 produce.
5. Mint a root-admission decision receipt, then `scripts/flights/repin_cell.py --set-ready` for the smoke and the
   arm, append to the batch queue; the Windows Scheduled Task SAEA-Batch-Driver flies it (decision 77).

## 3. Smoke, arm, read

Smoke acceptance (once flown): no tools array, five raw Solver samples in `solver_group` custody per row (I7g), every
request fits. The read is S3-3's own CLI (`scripts/analysis/stage3_rollout_score.py`), not a `plan_cell_read.py`
admission read -- ROLL-1 has no gating decision rule of its own (preregistration section 4).

## 4. What this package does not authorise

No flight before every placeholder above resolves and the cell is flipped; no contact by this registration; no
ledger row (root registers); no re-flying or re-scoring of any comparator; no admission verdict (S3-6's eventual
TRAIN A cell carries that).
