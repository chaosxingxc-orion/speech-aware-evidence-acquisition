# Preregistration -- Stage-3 cell ROLL-2: the sealed five-sample pool on the v2.0 lock roster

Registered before contact on 2026-09-26 at study commit `e0a8d20d`, worktree
`/home/chao/saea-worktrees/fable-roll2`, branch `fable/roll2`. Both cells are **held**. Nothing in
this note authorises a flight, a readiness flip, a scoring job or an admission entry.

## 1. What this cell is

Cell ROLL-2 is a **system-level trajectory-collection rollout** of the LOCKED v2.0 plan on TRAIN
Fold A (1,080 rows) with the Solver grouped at **samples 5, temperature 0.7** -- the same form cell
ROLL-1 flew on the 625-row construction subset R01C, moved to the roster the lock lives on.

Zero factors change in the form. `native_episode.roles.solver` keeps `samples` 5,
`decoding_overrides` {`temperature` 0.7, `seed_offset` 0} and `commit`
{`saea-commit-plurality-support-v1`, `min_support` 3, `similarity_threshold` 0.8}; the policy
program stays `phase-native-candidates-review-revise-samples5-v1` at `max_contacts` 19; there is deliberately **no** `deliver_normaliser`
node, because a grouped Solver forbids one (cell ROLL-AA's own registered reason). What moves is
the **roster**, and every roster-bound artifact takes the value the sealed Fold A lock arm
`SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1` already flew.

## 2. Why -- the measurement instrument

`docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md` establishes the law this cell answers to. An action whose effect is computable over
a **sealed sample pool** is read at about **0.67 pp at n = 625** (about **0.51 pp at n = 1,080**)
and at **zero GPU cost**. A **cross-flight** contrast at this scale carries a **measured +1.87 pp
A/A offset**: two request-identical flights of the same 625 rows differed by +1.87 pp SLU with a
CI95 that excludes zero while intent moved -1.28 pp, so such a contrast needs an in-chain A/A
replicate and about 3 pp of effect before it can see anything.

The program has a sealed pool on R01C and **none on the lock roster**. Today, therefore, no
selection, commit, verification, projection or re-ranking policy can be evaluated where the lock
lives. **ROLL-2 creates that pool.**

## 3. Status: DESCRIPTIVE

ROLL-2 is an **asset, not a comparison**, and it makes **no admission claim**. It has no
comparator, no gate number, no bar and no expected effect of its own, and it states no superiority,
transfer, generalisation, component-causal or confirmatory conclusion. Secondary products, all free
once the pool is sealed: the **within-flight sample spread on Fold A**, the **oracle best-of-5
ceiling on Fold A**, and the material for a **verifier-selection arm**. Each of those is read
offline, under its own separately registered read id, before any number is looked at.

## 4. The measurement-floor declaration

The block `scripts/checks/stage3_effect_floor_check.py` reads. It is keyed by run id because the arm
and its four-row smoke are different designs: the arm seals the pool that *is* the 0.67 pp
instrument, the smoke proves form on four rows and under `docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md` section 3 rule 5 a batch
that small can never be evidence of benefit. The canonical copy is the top-level
`stage3_measurement` object of `docs/readiness/2026-09-26-slurp-stage3-roll-2-fold-a-v1/registered-facts-v1.json`; this fence repeats it verbatim.

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "The four-row structural form smoke of ROLL-2 proves FORM and nothing else: five custodied Solver samples per row, the plurality-commit replay, zero native task-contract calls, every request fitting. It is scored by no one and read by no one, and under docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 3 rule 5 a batch of four rows can never be evidence of benefit.",
      "primary_metric": "slu_f1",
      "rows": 4
    },
    "SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "offline-sealed-pool",
      "note": "ROLL-2 makes no effectiveness claim of its own: it seals a 1,080-row x 5-sample pool on TRAIN Fold A so that commit, selection and verification rules can be read offline at the 0.67 pp floor of docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2d, on the roster where the composed policy will later be flown. Any benefit claim belongs to the read over this pool, which declares its own block.",
      "primary_metric": "slu_f1",
      "rows": 1080
    }
  }
}
```

## 5. Identities

| what | id |
|---|---|
| arm run | `SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1` |
| arm fit (spend only) | `SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-FIT-V1` |
| four-row smoke run | `SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-SMOKE-4-V1` |
| four-row smoke fit (spend only) | `SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-SMOKE-4-FIT-V1` |
| arm cell / experiment | `slurp-native-stage3-roll-2-fold-a-v1` |
| smoke cell / experiment | `slurp-native-stage3-roll-2-fold-a-smoke-4-v1` |
| arm attempt | `attempt-slurp-native-stage3-roll-2-fold-a-v1-generation` |
| arm fit attempt | `attempt-slurp-native-stage3-roll-2-fold-a-v1-fit` |
| smoke attempt | `attempt-slurp-native-stage3-roll-2-fold-a-smoke-4-v1-generation` |
| smoke fit attempt | `attempt-slurp-native-stage3-roll-2-fold-a-smoke-4-v1-fit` |
| decision receipt (root mints) | `coordination/slurp-stage3-roll-2-fold-a-v1/root-admission-v1.json` (id `slurp-stage3-roll-2-fold-a-admission-v1`) |
| campaign plan | `configs/campaign/slurp-native-stage3-roll-2-fold-a-v1.json` |
| serving session (attach only) | `serving-slurp-native-candidate-five-train-a-np4-v1` |

Composed config hash `6864487942f0da788410197f380a873f5b0b558bca215ab6f278d4532d58d962`, protocol hash `3bac1aa103b733620f4137aa5cc0d0fbdfb0604bc561c8330b013039753be1d7` (arm); `dc6f8e55bd35b330767479d2e3ceba3b7a0bbb164db29a037d823b2d4d9be9f2` / `6ba9e2cd995a75bf7c68f1b00483455d6ad2c292d144476336df7040da2bbf3f`
(smoke). Every one of these MOVES at the readiness flip, which re-pins this cell's own prepared
phase supply into the baseline fragment; `scripts/flights/batch/repin_loop_generic.sh` rewrites
each document that quotes them, including this one and the exposure-ledger rows.

## 6. Population

The unchanged TRAIN Fold A roster `docs/receipts/rosters/slurp-evo-fold-a-v2.json`
(`SLURP-EVO-FOLD-A-V2`, split identity `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`): 1,080 discovery rows, 60 in each of 18
scenarios, 3084.5284375 s of audio. It is the roster the sealed anchor, cell B1, cell B1r, the locked
plan arm PLAN and its replicate PLANr flew, disjoint by its own committed receipt from TRAIN Fold B,
the exemplar pool, DEV and the test split. Every row is preserved.

The four-row smoke flies the first four rows by roster order, split identity `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb` --
the same four rows and the same split identity the sealed lock smoke
`SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-SMOKE-4-V1` flew.

## 7. Budgets

20,520 = 1,080 TRAIN Fold A rows x 19 and 76 = 4 rows x 19, where 19 is the grouped-Solver graph's OWN ceiling at samples 5 as rails.native_episode_config.load_native_episode_config resolves it: perception.max_iterations + (max_revisions + 1) x (solver.max_iterations x solver.samples + reviewer.max_iterations + planner.max_iterations) = 1 + 2 x (1 x 5 + 3 + 1) = 19. Verified offline at registration: the composed program phase-native-candidates-review-revise-samples5-v1 declares max_contacts 19 and the loader's own graph ceiling resolves to 19 (a disagreement is refused by name). FIT: 82,080 = 20,520 x (1 speech packet + 3 endpoints) and 304 = 76 x 4 -- cell ROLL-1's own native_contact_fit mode and multiplier, rescaled to this roster.

58,607 = ceil(3084.5284375 x 19) on the 1,080 arm rows and 202 = ceil(10.5955625 x 19) on the four smoke rows. The per-row audio seconds are read from the committed Fold A roster receipt's own items[].audio_seconds (and agree with the Fold A dataset fragment's declared audio_seconds_total); no audio sample was decoded to obtain them.

About 8.5 contacts per row, so about 9,234 contacts and about 3.5 GPU hours on the arm. Basis: cell ROLL-1 MEASURED 8.5504 contacts per row on this exact grouped-Solver form (samples 5, temperature 0.7, min_support 3) over 625 R01C rows, and nothing in this registration changes the role graph, the prompt form or the number of scheduled requests -- only the roster the same form runs on. 8.5 x 1,080 = 9,180 and 8.5504 x 1,080 = 9,234, so the registered ceiling of 20,520 is about 2.2x the expectation and the 12.0 GPU-hour ceiling about 3.4x it. A ceiling is a BOUND, never a target, and budgets are run-cumulative across every attempt of a run id.

GPU-hour ceiling 12.0 (fit inclusive) on the arm and 1.0 on the smoke; `official_complete_scoring_jobs`
1 on the arm and 0 on the smoke; `native_task_contract_calls_cap` 0, `asr_calls` 0, `encoder_calls` 0.
Ceilings are bounds, never targets, and an unused budget is not attempt authority.

## 8. The Fold A re-point, key by key

Values come from `configs/baseline/slurp-native-default-plan-lock-baseline-v1.json`, the sealed Fold
A lock arm's own baseline. The checklist is the one
`docs/readiness/2026-09-24-slurp-stage3-var1-v1/` wrote down for the reverse move (the lock plan
re-pointed at R01C); this registration walks it in the opposite direction. Nothing is newly encoded,
promoted or released.

- `knowledge_stores.intent-boundaries.phase_supply.perception.query_source.relpath`
- `knowledge_stores.intent-boundaries.phase_supply.perception.query_source.sha256`
- `knowledge_stores.intent-boundaries.phase_supply.perception.query_source.tool_contact_ledger_row`
- `knowledge_stores.intent-boundaries.phase_supply.perception.query_source.embedded_signal`
- `knowledge_stores.train-exemplars.phase_supply.solver.query_source.relpath`
- `knowledge_stores.train-exemplars.phase_supply.solver.query_source.sha256`
- `knowledge_stores.train-exemplars.phase_supply.solver.query_source.tool_contact_ledger_row`
- `knowledge_stores.train-exemplars.phase_supply.solver.query_source.embedded_signal`
- `knowledge_stores.train-exemplars.release.relpath`
- `knowledge_stores.train-exemplars.release.sha256`
- `knowledge_stores.train-exemplars.snapshot.relpath`
- `knowledge_stores.train-exemplars.snapshot.sha256`
- `speech_packet_promotion_receipt`
- `speech_packet_promotion_receipt_sha256`
- `what_the_train_exemplars_store_is`
- `preparation_source_receipts`
- `native_contact_fit.run_id`
- `native_contact_fit.attempt_id`
- `native_contact_fit.contact_cap`
- `prepared_phase_supply (REMOVED, minted at the flip)`
- `population.count / population.dataset_fragment / population.roster_receipt / population.split_identity_hash`
- `populations[0].dataset_fragment / populations[0].ids`
- `split_id / cells[0].dataset_fragment`
- `family_budget.* and execution_plan.* (rows x 19 and the Fold A roster seconds x 19)`

Two things to state plainly. First, the `train-exemplars` store is the PARENT pool
`size-pool-annotated-exemplars`, not the `minus-r01` narrowing cell ROLL-1 used: that narrowing
exists only because the R01C construction roster overlapped the exemplar pool, and TRAIN Fold A is
disjoint from the exemplar pool by its own committed receipt
(`disjointness_proof.shared_utterances_fold_a_exemplars` = 0). Second, the sealed lock arm PLAN
carries `deliver_normaliser` `saea-deliver-normalise-v3` and ROLL-2 does **not**, because ROLL-2 is
cell ROLL-1's form on the lock roster and not the lock arm with a Solver group bolted on. That is a
REGISTERED DIFFERENCE from the lock arm, stated here before contact.

## 9. Structural acceptance (there is no other kind here)

A clean seal; 1,080 of 1,080 rows delivered; exactly five custodied Solver samples per row in
`solver_group` (invariant I7g) with seeds 1249110493, 1249110494, 1249110495, 1249110496, 1249110497 and temperature 0.7 on each; the plurality-commit
replay (`min_support` 3, similarity 0.8) reproducing the sealed delivered answer for every row; zero
native task-contract calls; every request fitting the 24,576-token live slot with its one-eighth
operational reserve; exactly one official complete score at finalize.

## 10. Failure policy

Stop and preserve on the first failure. No automatic restart, replay, row filtering, roster,
role-graph, prompt, knowledge, geometry or cap change. AT MOST ONE root-diagnosed recovery
re-registration for this run; a second failure closes the cell, and the fix must be proven on a
four-row dry run before another mechanism is admitted. `--allow-output-change` must never be passed
on any re-pin of this cell: it carries no committed `prepared_phase_supply` and the flip mints its
own under its own run id (harness item E16).

## 11. Prohibited

No paper-scale profile, no confirmatory split, no test-split contact, no comparator flight, no
re-scoring of a sealed arm, no admission entry from this cell, and no utterance text, gold label or
transcript printed or persisted by any read of this pool.

## 12. Context, never a comparator

TRAIN Fold A own null h_SLU 1.2485 / h_intent 0.9943 at n = 1,080; the locked plan arm PLAN 63.63
official SLU-F1 / 82.22 intent and its replicate PLANr 63.80 / 82.50 on this roster; the measured
cross-flight A/A offset +1.87 pp. None of these is this cell's comparator or bar -- ROLL-2 has no
comparator. They are recorded so the reason this cell exists stays legible.
