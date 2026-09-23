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
| `slurp-native-stage3-rollout-r01-v1` | `cf356bf34cbfb78e2f8f67f2d04ac17a0cfc00705cb2b00ffd48d3bf20e8e9b0` | `ea6ade3853d6699be3eac2fd8b8e18c77a4ad08af066f2d67fc40e9e58eb982c` |
| `slurp-native-stage3-rollout-r01-smoke-4-v1` | `bb27fcfecc4de24780a2a871237e0b29023268295055cdc561d5b6429b7ee4a7` | `b2b5f8d558ba7df6cf67e41acc4cea0caf90e403aee4321921715e09965e3597` |

Protocol document sha256 `6506203d8482fbf878135528d49f49b750c37eee7cab04bdb25476f4bc414f85`.

Still root's to do, in order: mint `coordination/slurp-stage3-rollout-r01-v1/root-admission-v1.json` (decision id `slurp-stage3-rollout-r01-admission-v1`), then re-pin BOTH cells in
ONE cycle with `scripts/flights/repin_cell.py --set-ready`. The re-pin builds this cell's own
model-free prepared phase supply under its own run id (item E16) -- nothing is pinned for it here,
because with no current pin the tool builds no old-value mapping and a placeholder in a plan would
never be rewritten -- pins it into the baseline fragment and into the experiment fragment's single
PENDING `preparation` readiness requirement, INSERTS the decision requirement (none is registered
here, so nothing is left behind without an `expected_decision_id`), and recomputes every dependent
hash. Then queue the smoke and the arm on the SAEA-Batch-Driver (decision 77) on the SLURP geometry.
