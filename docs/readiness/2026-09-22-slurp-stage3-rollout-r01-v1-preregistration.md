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
