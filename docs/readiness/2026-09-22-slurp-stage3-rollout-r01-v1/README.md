# Cell ROLL-1: the Stage-3 grouped-Solver rollout: launch runbook

Preregistration: [`../2026-09-22-slurp-stage3-rollout-r01-v1-preregistration.md`](../2026-09-22-slurp-stage3-rollout-r01-v1-preregistration.md).
Engineering spec: `docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md` section S3-2.
Stage-3 algorithm (owner decision 101): **`shared-rollout`**, operator `rollout` -- the algorithm-neutral
rollout every layer-A family (Training-Free GRPO, GEPA, ACE) consumes. Declared in both experiment fragments
as `stage3_algorithm` and checked by `scripts/checks/stage3_algorithm_label_check.py`.

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

## Flight registration (2026-09-23)

Registered for flight on 2026-09-23 at study commit `db3b4d6a` (worktree
`/home/chao/saea-worktrees/fable-roll1reg`, branch `fable/roll1reg`), before any contact. This
section supersedes section 1's "NOT registered here" list: the plans, the protocol, the campaign
plan and the four exposure-ledger rows now exist. The design record above (sections 0-4), the
analysis recipe and the S3-3 dry-run receipt are unchanged.

Stage-3 algorithm label (owner decision 101): **`shared-rollout`**, operator `rollout`.

| run id | plan | calls | speech seconds | GPU hours |
| --- | --- | --- | --- | --- |
| `SAEA-SLURP-STAGE3-ROLLOUT-R01-V1` | `generation-plan-registered-v1.json` | 15,200 | 66,338 | 8.0 |
| `SAEA-SLURP-STAGE3-ROLLOUT-R01-FIT-V1` | `fit-plan-registered-v1.json` | 60,800 | 66,338 | 8.0 |
| `SAEA-SLURP-STAGE3-ROLLOUT-R01-SMOKE-4-V1` | `smoke-generation-plan-registered-v1.json` | 76 | 286 | 1.0 |
| `SAEA-SLURP-STAGE3-ROLLOUT-R01-SMOKE-4-FIT-V1` | `smoke-fit-plan-registered-v1.json` | 304 | 286 | 1.0 |

Ceiling accounting (owner decision 96): 15,200 = 800 rows x 19, where 19 is the grouped-Solver
graph's own ceiling `1 + (max_revisions + 1) * (solver.max_iterations * solver.samples +
reviewer.max_iterations + planner.max_iterations) = 1 + 2 * (5 + 3 + 1)`, replacing the plan cell's
non-grouped 800 x 11 = 8,800; expected about 6,400 contacts and about 2.5 GPU hours.
60,800 = 15,200 x (1 speech packet + 3 endpoints). 66,338 = `ceil(3,491.426125 x 19)`.
286 = `ceil(15.03875 x 19)` on the four smoke rows. `native_task_contract_calls_cap = 0`: the cell
is tool-free.

No comparator: `protocol-registered-v1.json` carries `"comparator": null` with its reason. The read
is S3-3's own CLI on copies, never `plan_cell_read.py`.

Composed and protocol hashes as registered (every one of them moves at the flip, and
`scripts/flights/repin_cell.py` rewrites each document that quotes them):

| cell | composed config | protocol |
| --- | --- | --- |
| `slurp-native-stage3-rollout-r01-v1` | `1946b6fbb7b5a82cc5940d9bbd1d3c834e6902c0496c6a03e22f9e7d77ea2a6d` | `7220e87b005dae482590c565c35fbf3a7bb38d15c1b8b0349d633fd0c40f8438` |
| `slurp-native-stage3-rollout-r01-smoke-4-v1` | `78319cac32eb46a9b0250d4c683b4f17faaecc10c84cdaadc784f149b64efb09` | `6461e09d24a2c0d61812a93a3371d76fe90dda5625e5a83f961be16c3867dd7b` |

Protocol document sha256 `b5b8398f7ed7c91a264a7a9249a0fb619f488c6fc8aa7c4b4abda7e8191dc471`.

Still root's to do, in order: mint `coordination/slurp-stage3-rollout-r01-v1/root-admission-v1.json` (decision id `slurp-stage3-rollout-r01-admission-v1`), then re-pin BOTH cells in
ONE cycle with `scripts/flights/repin_cell.py --set-ready`. The re-pin builds this cell's own
model-free prepared phase supply under its own run id (item E16) -- nothing is pinned for it here,
because with no current pin the tool builds no old-value mapping and a placeholder in a plan would
never be rewritten -- pins it into the baseline fragment and into the experiment fragment's single
PENDING `preparation` readiness requirement, INSERTS the decision requirement (none is registered
here, so nothing is left behind without an `expected_decision_id`), and recomputes every dependent
hash. Then queue the smoke and the arm on the SAEA-Batch-Driver (decision 77) on the SLURP geometry.

## R01C narrowing (2026-09-23)

Cell ROLL-1 now flies **R01C**, the clean subset of the S3-1 construction roster:
`SLURP-STAGE3-CONSTRUCTION-R01C`, **625 rows** (`docs/receipts/rosters/slurp-stage3-construction-r01c.json`,
sha256 `e8abc65ba4626cccb4aae9d2eb1bd73f077a6e9a407b3dba9c18bbe4c03eeddd`). Everything else about the cell is unchanged --
same arm, same grouped-Solver factor, same knowledge stores, same geometry, same scorers,
same four run ids and attempt ids.

**Why.** `rails.runner.run_speech_native_agent_loop` refuses a run whose query samples intersect
the bound composite snapshot's own `source_sample_ids` (the union over the composed stores).
Item S3-1k removed the overlap contributed by `train-exemplars` by re-pointing it at
`size-pool-annotated-exemplars-minus-r01`. The residual intersection was **175** R01 rows whose
utterances are card sources of the two AUTHORED semantic stores (`intent-boundaries-v1`,
57 recordings; `slot-contracts-v2`, 155 recordings; union 175 utterances), and an authored card
cannot be re-pointed model-free. Those rows left the QUERY side instead (coordinator decision 102,
pending owner confirmation). A later top-up draw (R02) is a separate item.

**How.** `scripts/build_slurp_stage3_construction_clean_subset.py` -- a pure SELECTION of R01 with
zero model, tool, encoder, tokenizer, scorer, GPU and network contacts (the armed offline socket
guard recorded 0 attempts). Exclusion is by UTTERANCE, the same rule
`scripts/build_slurp_stage3_r01_excluded_exemplar_store.py` applies from the knowledge side. Every
surviving roster item, runtime-view row and query-vector line is the parent artifact's own bytes,
in the parent's order.

**New artefacts.**

| artefact | path | sha256 |
| --- | --- | --- |
| roster receipt (625 rows, 175 excluded) | `docs/receipts/rosters/slurp-stage3-construction-r01c.json` | `e8abc65ba4626cccb4aae9d2eb1bd73f077a6e9a407b3dba9c18bbe4c03eeddd` |
| dataset fragment / runtime view | `configs/dataset/slurp-speech-native-stage3-construction-r01c.json` | `36949a683739676616d4e4845fb302cad59721c8032ce4d65d18b35823a56cba` |
| intent-boundary query vectors (data root) | `vectors/slurp-stage3-construction-r01c-v1/query-vectors-speech-segments.jsonl` | `ebaa743241a67a2cb759353fa8a9f58a3f09d27c00c8c66cb3172958dcccc1b8` |
| content query vectors (data root) | `vectors/slurp-stage3-construction-r01c-v1/query-vectors-speech-content-v1.jsonl` | `dd3b2924cda10810487b2b114e61380beaf8477634c602096b875e461ae44baa` |

**Re-registered plan numbers.**

| run id | planned_model_calls | planned_speech_audio_seconds | split identity hash |
| --- | --- | --- | --- |
| `SAEA-SLURP-STAGE3-ROLLOUT-R01-V1` | 11,875 | 51,811 | `f56bc386776421aec2d8001d8697611b01c9b0562885a462759b15531e2f4515` |
| `SAEA-SLURP-STAGE3-ROLLOUT-R01-FIT-V1` | 47,500 | 51,811 | `f56bc386776421aec2d8001d8697611b01c9b0562885a462759b15531e2f4515` |
| `SAEA-SLURP-STAGE3-ROLLOUT-R01-SMOKE-4-V1` | 76 | 324 | `e9dcea536028d17737b999c65267e47645ca7b3f6f9c4f57622961cf29363ed5` |
| `SAEA-SLURP-STAGE3-ROLLOUT-R01-SMOKE-4-FIT-V1` | 304 | 324 | `e9dcea536028d17737b999c65267e47645ca7b3f6f9c4f57622961cf29363ed5` |

`planned_gpu_hours` is unchanged (8.0 arm / 1.0 smoke): a ceiling is never a target. The featcache
packet promotion receipt (800 packets) and the R01 D1 media supplement stay pinned -- both are read
BY ID and accept a superset, and all 625 R01C ids bind.

**Still root's to do.** This narrowing flips no readiness and touches no readiness state field. The
`prepared_phase_supply` artifacts pinned in both baselines were minted over the old populations and
`core.flight.runtime._phase_seed_inputs` binds a prepared artifact to the composed config, the split
identity and the packet map, so BOTH must be re-minted with `scripts/flights/repin_cell.py` before
either cell flies; that re-pin also recomputes the composed and protocol hashes once more and
rewrites every document that quotes them, including the four exposure-ledger rows above.
