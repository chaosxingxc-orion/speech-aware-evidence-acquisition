# Preregistration -- Stage-3 cell ROLL-3: the sealed five-sample pool on the evaluation roster DEV-2000-ADDED

Registered before contact on 2026-09-26 at study commit `66373032`, worktree
`/home/chao/saea-worktrees/fable-roll3`, branch `fable/roll3`. Both cells are **held**. Nothing in
this note authorises a flight, a readiness flip, a scoring job or an admission entry.

## 1. What this cell is

Cell ROLL-3 is a **system-level trajectory-collection rollout** of the LOCKED v2.0 plan on
DEV-2000-ADDED (1,000 rows) with the Solver grouped at **samples 5, temperature 0.7** -- the same
form cell ROLL-1 flew on the 625-row construction subset R01C and cell ROLL-2 flew today on TRAIN
Fold A (1,080 rows x 5 samples, 8,996 contacts, `pass: true`), moved to the evaluation roster.

Zero factors change in the form. `native_episode.roles.solver` keeps `samples` 5,
`decoding_overrides` {`temperature` 0.7, `seed_offset` 0} and `commit`
{`saea-commit-plurality-support-v1`, `min_support` 3, `similarity_threshold` 0.8}; the policy
program stays `phase-native-candidates-review-revise-samples5-v1` at `max_contacts` 19; there is
deliberately **no** `deliver_normaliser` node, because a grouped Solver forbids one (cell ROLL-AA's
own registered reason). What moves is the **roster**, and every roster-bound artifact takes the
value the sealed DEV-2000-ADDED plan arm `SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1` already
flew. ROLL-3 is ROLL-2's registration (`docs/readiness/2026-09-26-slurp-stage3-roll-2-fold-a-v1/`, pre-flip bytes at `7d49dc58`) with the
roster re-pointed and nothing else.

## 2. Why -- the measurement instrument

The measurement instrument note docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md establishes that an action whose effect is computable over a SEALED sample pool is read at about 0.67 pp at n = 625 (about 0.53 pp at n = 1,000, scaling by the square root of n) at zero GPU cost, while a cross-flight contrast at this scale carries a measured +1.87 pp A/A offset. The program has such a pool on R01C and, since cell ROLL-2 sealed today, on TRAIN Fold A -- and NONE on DEV-2000-ADDED, the evaluation roster where every admitted policy must later be replicated and where the owner names dev sampling first (owner decisions 34, 79, 139, 141). This cell creates that pool.

## 3. Status: DESCRIPTIVE

ROLL-3 is an **asset, not a comparison**, and it makes **no admission claim**. It has no
comparator, no gate number, no bar and no expected effect of its own, and it states no superiority,
transfer, generalisation, component-causal or confirmatory conclusion. Secondary products, all free
once the pool is sealed: the **within-flight sample spread on DEV-2000-ADDED**, the **oracle
best-of-5 ceiling on DEV-2000-ADDED**, and the material for a **verifier-selection arm**. Each of
those is read offline, under its own separately registered read id, before any number is looked at.

## 4. The measurement-floor declaration

The block `scripts/checks/stage3_effect_floor_check.py` reads. It is keyed by run id because the arm
and its four-row smoke are different designs: the arm seals the pool that *is* the sub-1 pp
instrument, the smoke proves form on four rows and under `docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md` section 3 rule 5 a batch that
small can never be evidence of benefit. The canonical copy is the top-level `stage3_measurement`
object of `docs/readiness/2026-09-26-slurp-stage3-roll-3-dev2000-added-v1/registered-facts-v1.json`; this fence repeats it verbatim.

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "The four-row structural form smoke of ROLL-3 proves FORM and nothing else: five custodied Solver samples per row, the plurality-commit replay, zero native task-contract calls, every request fitting. It is scored by no one and read by no one, and under docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 3 rule 5 a batch of four rows can never be evidence of benefit.",
      "primary_metric": "slu_f1",
      "rows": 4
    },
    "SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "offline-sealed-pool",
      "note": "ROLL-3 makes no effectiveness claim of its own: it seals a 1,000-row x 5-sample pool on DEV-2000-ADDED so that commit, selection and verification rules can be read offline at about the 0.67 pp floor of docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2c (about 0.53 pp at n = 1,000), on the evaluation roster where every admitted policy must later be replicated. Any benefit claim belongs to the read over this pool, which declares its own block; that read reports intent accuracy beside SLU-F1 (owner decisions 133 and 137).",
      "primary_metric": "slu_f1",
      "rows": 1000
    }
  }
}
```

## 5. Identities

| what | id |
|---|---|
| arm run | `SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-V1` |
| arm fit (spend only) | `SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-FIT-V1` |
| four-row smoke run | `SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-SMOKE-4-V1` |
| four-row smoke fit (spend only) | `SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-SMOKE-4-FIT-V1` |
| arm cell / experiment | `slurp-native-stage3-roll-3-dev2000-added-v1` |
| smoke cell / experiment | `slurp-native-stage3-roll-3-dev2000-added-smoke-4-v1` |
| arm attempt | `attempt-slurp-native-stage3-roll-3-dev2000-added-v1-generation` |
| arm fit attempt | `attempt-slurp-native-stage3-roll-3-dev2000-added-v1-fit` |
| smoke attempt | `attempt-slurp-native-stage3-roll-3-dev2000-added-smoke-4-v1-generation` |
| smoke fit attempt | `attempt-slurp-native-stage3-roll-3-dev2000-added-smoke-4-v1-fit` |
| decision receipt (root mints) | `coordination/slurp-stage3-roll-3-dev2000-added-v1/root-admission-v1.json` (id `slurp-stage3-roll-3-dev2000-added-admission-v1`) |
| campaign plan | `configs/campaign/slurp-native-stage3-roll-3-dev2000-added-v1.json` |
| serving session (attach only) | `serving-slurp-native-candidate-five-train-a-np4-v1` |

Composed config hash `c1d46e45fa74ee4a92cec4a9fb91506d19baf0b77ecebbc50fa1aa6d12549414`, protocol hash `aff61447c94cfe38247fa0944fc0c10e7498aef5f0618490e56b63233f9504c0` (arm); `5e91c6f83983da147e8d9931cbf74599499c95c6da2d9064fdfabfdafed89786` / `f61458df3365ea3313f4f12829e7c1f76e96b43fdee7e9b1b120d61c8cccd466`
(smoke). Every one of these MOVES at the readiness flip, which re-pins this cell's own prepared
phase supply into the baseline fragment; `scripts/flights/batch/repin_loop_generic.sh` rewrites
each document that quotes them, including this one and the exposure-ledger rows.

## 6. Population

The unchanged DEV-2000-ADDED roster docs/receipts/rosters/slurp-dev-2000-added-v1.json (SLURP-DEV-2000-ADDED-V1, split identity ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67, split role dev, roster role evaluation): 1,000 devel recordings -- 913 distinct utterances, 87 of them carrying two recordings; 13 scenarios in the devel mixture, the stratum withheld per item -- 2983.52725 s of audio. It is the roster cell B6's direct and plan arms, the replicate PLANr-DEV2000 and cell CELL-3's gate arm and twin flew, disjoint by its own committed receipt from DEV-1000, the test split, every TRAIN construction roster and the exemplar pool. Every row is preserved so the sealed sample pool this cell creates covers the whole evaluation roster.

The first 4 rows, by roster order, of the unchanged DEV-2000-ADDED roster docs/receipts/rosters/slurp-dev-2000-added-v1.json: slurp:devel:000017:audio-1501773854-headset, slurp:devel:000024:audio-1490195864-headset, slurp:devel:000026:audio-1502216425-headset, slurp:devel:000026:audio-1502301875 (the last two are the roster's own two recordings of one utterance), 8.1276875 s of audio, split identity fee83441e514473dc4ab798f8554882bc5753c7fc4924eda0e72c7af7ed51ef0 computed by the repository's own data.splits.split_identity_hash(data.splits.prefixed('slurp', ids)) -- the call that reproduces the committed 1,000-row identity ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67 from this receipt and cell ROLL-2's smoke identity from the Fold A receipt's first four rows. No earlier smoke on this roster used these rows: cell B6 registered no smoke and cell CELL-3's smoke took roster positions 1, 2, 8 and 14 under its own gate-defined split identity. Structural form proof only: no score and no read.

## 7. Budgets

19,000 = 1,000 DEV-2000-ADDED rows x 19 and 76 = 4 rows x 19, where 19 is the grouped-Solver graph's OWN ceiling at samples 5 as rails.native_episode_config.load_native_episode_config resolves it: perception.max_iterations + (max_revisions + 1) x (solver.max_iterations x solver.samples + reviewer.max_iterations + planner.max_iterations) = 1 + 2 x (1 x 5 + 3 + 1) = 19. Verified offline at registration by the dry run: the composed program phase-native-candidates-review-revise-samples5-v1 declares max_contacts 19 and the loader's own graph ceiling resolves to 19 (a disagreement is refused by name). FIT: 76,000 = 19,000 x (1 speech packet + 3 endpoints) and 304 = 76 x 4 -- cell ROLL-1's own native_contact_fit mode and multiplier, rescaled to this roster.

56,688 = ceil(2983.52725 x 19) on the 1,000 arm rows and 155 = ceil(8.1276875 x 19) on the four smoke rows. The per-row audio seconds are read from the committed DEV-2000-ADDED roster receipt's own items[].audio_seconds (and agree with the DEV-2000-ADDED dataset fragment's declared audio_seconds_total); no audio sample was decoded to obtain them.

About 8.5 contacts per row, so about 8,550 contacts and about 3.3 GPU hours on the arm. Basis: cell ROLL-1 MEASURED 8.5504 contacts per row on this exact grouped-Solver form (samples 5, temperature 0.7, min_support 3) over 625 R01C rows, and cell ROLL-2 flew the same form today on TRAIN Fold A at 8,996 contacts over 1,080 rows (8.33 per row); nothing in this registration changes the role graph, the prompt form or the number of scheduled requests -- only the roster the same form runs on. 8.5 x 1,000 = 8,500 and 8.5504 x 1,000 = 8,550, so the registered ceiling of 19,000 is about 2.2x the expectation and the 11.2 GPU-hour ceiling about 3.4x it (11.2 = cell ROLL-2's 12.0 x 1,000 / 1,080 = 11.11, rounded up to one decimal: ROLL-2's own cap at this roster's size). A ceiling is a BOUND, never a target, and budgets are run-cumulative across every attempt of a run id.

GPU-hour ceiling 11.2 (fit inclusive) on the arm and 1.0 on the smoke; `official_complete_scoring_jobs`
1 on the arm and 0 on the smoke; `native_task_contract_calls_cap` 0, `asr_calls` 0, `encoder_calls` 0.
Ceilings are bounds, never targets, and an unused budget is not attempt authority.

## 8. The DEV-2000-ADDED re-point, key by key

Values come from `configs/baseline/slurp-native-default-plan-dev2000-added-baseline-v1.json` and
`configs/experiment/slurp-native-default-plan-dev2000-added-v1.json`, the sealed DEV-2000-ADDED plan
arm's own fragments. The checklist is the one cell ROLL-2's `protocol-registered-v1.json` wrote down
for the R01C -> Fold A move, walked here from Fold A to DEV-2000-ADDED, plus the scorer. Nothing is
newly encoded, promoted or released.

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
- `family_budget.* and execution_plan.* (rows x 19 and the DEV-2000-ADDED roster seconds x 19)`
- `scorers[0] (slurp-slu-official-train -> slurp-slu-official: devel gold, the DEV-2000-ADDED plan arm's own scorer)`

Old -> new for the roster and its vectors: `docs/receipts/rosters/slurp-evo-fold-a-v2.json` ->
`docs/receipts/rosters/slurp-dev-2000-added-v1.json`; split identity `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6` ->
`ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67`; `split_id` `SLURP-EVO-FOLD-A-V2` -> `DEV-2000-ADDED`; `split_role` `discovery` -> `dev`;
intent-boundary query vectors `vectors/slurp-intent-boundaries-train-fold-a-1080-v1/query-vectors-speech-segments.jsonl`
-> `vectors/slurp-dev2000-added-v1/query-vectors-speech-segments.jsonl`; content query vectors
`vectors/slurp-exemplars-pool/query-vectors-speech-content-v1.jsonl` ->
`vectors/slurp-dev2000-added-v1/query-vectors-speech-content-v1.jsonl`; query-dimension alias
`prepared/SAEA-SLURP-INTENT-BOUNDARY-TRAIN-FOLD-A-ALIAS-V1/query-dimension-alias.json` ->
`prepared/SAEA-SLURP-DEV2000-ADDED-ALIAS-V1/query-dimension-alias.json`; encoding row
`SAEA-SLURP-TFRL-FOLD-A-SPEECH-QUERY-ENCODING-V1` -> `SAEA-SLURP-DEV2000-ADDED-SPEECH-QUERY-ENCODING-V1`;
packet promotion `EVO-FOLDS-V2-promotion.json` -> `DEV-2000-ADDED-promotion.json`; scorer
`slurp-slu-official-train` -> `slurp-slu-official`. Every pinned file was verified present under the
data root with its registered SHA-256 before this note was written, and both vector files carry all
1,000 roster ids.

Two things to state plainly. First, the `train-exemplars` store is the PARENT pool
`size-pool-annotated-exemplars`, the store the plan arm read on both rosters: TRAIN-built, and
disjoint from every DEV-2000-ADDED recording by the roster receipt's own `disjointness_proof`. Second,
the sealed plan arm carries `deliver_normaliser` `saea-deliver-normalise-v3` and ROLL-3 does **not**,
because ROLL-3 is cell ROLL-2's form on the evaluation roster and not the plan arm with a Solver group
bolted on. That is a REGISTERED DIFFERENCE from the plan arm, stated here before contact.

## 9. Structural acceptance (there is no other kind here)

A clean seal; 1,000 of 1,000 rows delivered; exactly five custodied Solver samples per row in
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

DEV-2000-ADDED own null h_SLU 1.2525 / h_intent 1.1520 at n = 1,000 (utterance-clustered); the plan
arm 65.40 official SLU-F1 / 76.6 intent, its replicate PLANr-DEV2000 65.15 / 76.8, and the bare core
38.09 / 61.7 on this roster; the measured cross-flight A/A offsets +1.87 pp (R01C) and -0.25 pp (this
roster's B6 pair). None of these is this cell's comparator or bar -- ROLL-3 has no comparator. They
are recorded so the reason this cell exists stays legible.
