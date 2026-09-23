# Cell ROLL-1: the Stage-3 grouped-Solver rollout on the S3-1 construction roster: preregistration

Registered 2026-09-22 by the coordinator (Fable 5.1), from the sealed cell PLAN fragment plus the B2 v3 grouped-Solver
form, per `docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md` section S3-2. Before any contact.
READINESS HELD: this registration authorises no flight, no readiness flip and no contact (see section 5).

## 1. Why this cell exists

Stage 3's owner-decided base loop (decisions 80-83; `docs/superpowers/specs/2026-09-21-slurp-stage3-training-free-rl-
design.md`) needs, for iteration 1, N = 5 grouped-Solver rollouts per row of an about-800-row semantic-diversity
construction roster, so that S3-3 can score the disagreeing samples and S3-4 can ask the frozen core what distinguished
the best answer from the worst. ROLL-1 is that rollout: the locked plan's fragment with exactly the grouped-Solver
factor, flown on the S3-1 roster instead of TRAIN Fold A.

## 2. The cell

| item | value |
| --- | --- |
| base | the locked plan cell PLAN (`configs/baseline/slurp-native-default-plan-lock-baseline-v1.json`) |
| factor | native_episode.roles.solver.samples=5, decoding_overrides={temperature:0.7,seed_offset:0}, commit={policy:saea-commit-plurality-support-v1,min_support:3,similarity_threshold:0.8} (the B2 v3 form); native_episode.deliver_normaliser REMOVED (forbidden with a grouped Solver) |
| not factors | knowledge_stores.slot-contracts, phase_material, the task instruction template, the geometry (np4 x 24,576), scorers -- byte-identical to cell PLAN |
| roster | SLURP-STAGE3-CONSTRUCTION-R01 (800 rows, `docs/receipts/rosters/slurp-stage3-construction-r01.json`), NOT TRAIN Fold A |
| contacts per row | ceiling 19 (1 + (max_revisions+1)*(5+3+1), the B2 v3 graph formula); expected about 8 |
| comparator | none yet -- this is a rollout for S3-3/S3-4 curation, not an admission read; the eventual TRAIN A cell (S3-6) reads against the sealed PLAN arm at the plan's own null |
| smoke | four rows of the same roster, structural acceptance |
| runs | `SAEA-SLURP-STAGE3-ROLLOUT-R01-V1` / `-FIT-V1`; smoke `SAEA-SLURP-STAGE3-ROLLOUT-R01-SMOKE-4-V1` / `-SMOKE-4-FIT-V1` |

## 3. What this registration does NOT authorise (readiness held)

The roster-bound identity pins cannot exist yet: the S3-1 construction roster's featcache packets are not promoted (the
ENCODE step is itself a tool contact and must be separately registered before it runs, per S3-1's own docstring), and
neither the intent-boundary query-vector encoding pass nor the train-exemplars query-vector alias export has been
built. Every field that depends on either is a `PENDING_`-prefixed placeholder in both baseline fragments
(`stage3_pending_placeholders` block, 15 entries, documented one for one). `readiness.state` here is `"held"`, not
`"ready"`: no decision id is minted, no `scripts/flights/repin_cell.py --set-ready` has run, and the cell is not on the
batch queue. Filling the placeholders and flipping readiness is root's own follow-up.

## 4. Decision rule

This cell has no gating decision rule of its own -- it produces raw samples for S3-3 (score on copies) and S3-4 (the
semantic-advantage contact), not an admission verdict. The eventual delta-store cell (S3-6) carries the gating rule
(the plan's own null, decision 38).

## 5. Budgets (execution_plan; owner-specified planning numbers, see the README's own note on the ceiling)

`execution_plan.planned_model_calls = 8,800` (800 rows x 11, the coordinator's own S3-2 deliverable line -- NOTE this
reuses cell PLAN's non-grouped per-row ceiling (11) as the planning number, not the grouped-Solver graph's own
ceiling (19, section 2); `execution_plan.planned_speech_audio_seconds = audio_seconds_total(roster) x 11` (repeated
speech accounting, the same convention); `execution_plan.planned_gpu_hours = 8.0`. `family_budget` mirrors these.
First failure stops and preserves; no automatic recovery is pre-authorised here.

## Flight registration (2026-09-23)

The three S3-1 preparations of section 3 are now SEALED and pinned by hash in both baseline
fragments (`stage3_placeholders_filled` records all 18 fills): the featcache packet promotion
`SAEA-SN-STAGE3-CONSTRUCTION-R01-PREPROCESS-RECOVERY-V1` (receipt sha256 `a1664e34...`), the
intent-boundary speech-query encoding `SAEA-SLURP-STAGE3-CONSTRUCTION-R01-SPEECH-QUERY-ENCODING-V1`
(alias sha256 `41b47b3f...`) and the model-free content derivative
`SAEA-SLURP-STAGE3-CONSTRUCTION-R01-QUERY-VECTOR-EXPORT-V1` (sha256 `651ddfbb...`). The cell is
therefore registered for flight on 2026-09-23 at study commit `db3b4d6a`, before any contact, and
`readiness.state` stays `"held"`.

Stage-3 algorithm label (owner decision 101): **`shared-rollout`**, operator `rollout` -- the
algorithm-neutral rollout operator every layer-A family (Training-Free GRPO, GEPA, ACE) consumes.

### Section 5 superseded: the registered budgets (owner decision 96)

Section 5 above registered `planned_model_calls = 8,800` (800 x 11, cell PLAN's non-grouped
ceiling). Owner decision 96 replaces that at the readiness flip with the grouped-Solver graph's OWN
ceiling:

| quantity | arm | smoke |
| --- | --- | --- |
| `planned_model_calls` | 15,200 = 800 x 19 | 76 = 4 x 19 |
| `fit_endpoint_calls_cap` | 60,800 = 15,200 x 4 | 304 = 76 x 4 |
| `planned_speech_audio_seconds` | 66,338 = `ceil(3,491.426125 x 19)` | 286 = `ceil(15.03875 x 19)` |
| `planned_gpu_hours` | 8.0 (unchanged) | 1.0 |
| `native_task_contract_calls_cap` | 0 (tool-free) | 0 (tool-free) |

19 = `1 + (max_revisions + 1) * (solver.max_iterations * solver.samples + reviewer.max_iterations +
planner.max_iterations) = 1 + 2 * (5 + 3 + 1)`, as
`rails.native_episode_config.load_native_episode_config` resolves it. Expected spend: about 6,400
contacts (about 8 per row, spec S3-2) and about 2.5 GPU hours. Ceilings are bounds, never targets,
and budgets are run-cumulative across every attempt of a run id.

`service_session` is now `serving-slurp-native-candidate-five-train-a-np4-v1` in both fragments
(the resident SLURP session; attach only, never spawn or stop).

### What is registered

Package `docs/readiness/2026-09-22-slurp-stage3-rollout-r01-v1/` (the four plans fresh and
registered, `protocol-registered-v1.json`, plus the pre-existing README, analysis recipe and S3-3
dry-run receipt), campaign plan `configs/campaign/slurp-native-stage3-rollout-r01-v1.json`, and four
unconsumed exposure-ledger rows (`SAEA-SLURP-STAGE3-ROLLOUT-R01-V1` / `-FIT-V1` /
`-SMOKE-4-V1` / `-SMOKE-4-FIT-V1`, `consumed = no`).

Section 4's decision rule is unchanged and the protocol states it machine-readably:
`"comparator": null`, because ROLL-1 is a rollout for curation read by
`scripts/analysis/stage3_rollout_score.py`, never by `scripts/analysis/plan_cell_read.py`.

Nothing here authorises a flight. Root mints
`coordination/slurp-stage3-rollout-r01-v1/root-admission-v1.json` (decision id
`slurp-stage3-rollout-r01-admission-v1`) and flips both cells with
`scripts/flights/repin_cell.py --set-ready`, which also mints this cell's own prepared phase supply.
