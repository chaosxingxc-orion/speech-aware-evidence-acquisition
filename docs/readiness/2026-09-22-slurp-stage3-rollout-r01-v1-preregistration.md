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
