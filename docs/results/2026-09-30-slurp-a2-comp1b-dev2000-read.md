# Cell A2 (COMP-1b on DEV-2000-ADDED) paired read: intent +4.60 pp CI95 [+2.58, +6.73], official SLU-F1 +0.53 pp [-1.04, +2.09] against the in-chain A/A; the Fold A gain replicates on the fresh roster (DESCRIPTIVE)

Read on 2026-09-30 by the records and read agent (Claude Opus 5.5, on the coordinator's brief, Fable 5.1), in
worktree `fable/a2read`. The read is model-free. `core.flight.cli` and `lease_cli` were not invoked. There were
no model, server, encoder, embedder, tokenizer, scorer or GPU contacts.

The READ row `SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-PAIRED-ANALYSIS-V1` was root countersigned on master at
`aaf4f2f93` (2026-09-30T06:09:30Z). That was after the A2 seal (`A2 DONE`, 06:06:48Z) and before any score was
opened (owner decision 198).

The recipe is `docs/readiness/2026-09-29-slurp-stage3-comp1b-dev2000-added-v1/analysis-recipe-v1.json` (recipe id
`slurp-stage3-comp1b-dev2000-added-paired-analysis-v1`, sha256 `41cc734d...0c20a`). It is a paired row bootstrap:
cluster key `utterance_id`, 10,000 draws, seed 20260929.

No utterance text, gold label, slot filler, intent name as content or model output was printed or persisted. Only
counts, rates, pp, ids and hashes appear below.

**DESCRIPTIVE.** These are development numbers on the DEV-2000-ADDED evaluation roster (owner decisions 28 and 86).
They are never a test claim. The verdict word belongs to the coordinator (decision 139).

## 1. What flew

| run | attempt | rows | contacts | GPU-h | prompt / completion tokens per row | state |
| --- | --- | ---: | ---: | ---: | --- | --- |
| A2 arm `SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1` | `attempt-slurp-native-stage3-comp1b-dev2000-added-generation-v1` | 1,000 | 4,050 | 1.6955 | 37,345.7 / 241.7 | COMPLETED at flight commit `310110be`, scored once |
| in-chain A/A `SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1` | `attempt-slurp-native-stage3-comp1-aa-dev2000-added-generation-v1` | 1,000 | 4,068 | 1.6547 | 35,815.8 / 248.8 | COMPLETED at flight commit `310110be`, scored once |

- **Seal hashes.** Arm manifest `8192451a...a5ed8`, scores `878babaa...880a9`. A/A manifest `e0aaef84...3a017`,
  scores `0543d025...1ac4c6`. The driver's stop checks PASSED (roster `f78dd8ad...`, split identity `ee6c43cd...`).
- **Contacts per row.** 4.050 (arm) vs 4.068 (A/A); the ceiling is 11. The arm had 7 finite-completion
  dispositions. Per row the arm carries +1,530 prompt tokens (the agreement and centroid supply) and -7.1
  completion tokens. The GPU-h delta is +0.041.

The registered driver `scripts/flights/read_paired_cell.sh` ran unchanged through `comp1bdev_read.sh` and exited 0.
It wrote the gating pass `vs-aa` (verdict `32b42fe0...6dd77`) and the context pass `vs-comparator` (verdict
`2b65d5b5...2282e`). No `--rescore` was needed. No `--weighting` flag was passed: this roster is not floored, so the
raw and post-stratified numbers are the same.

## 2. The gating contrast: A2 minus the in-chain A/A

| metric | A/A | A2 | delta pp | CI95 pp | CI90 pp | saves / harms |
| --- | ---: | ---: | ---: | --- | --- | --- |
| **intent (scenario_action_exact), PRIMARY** | 76.90 | 81.50 | **+4.60** | **[+2.58, +6.73]** | [+2.88, +6.41] | 79 / 33 |
| **official pooled SLU-F1 (micro), GUARD** | 65.40 | 65.93 | **+0.53** | **[-1.04, +2.09]** | [-0.79, +1.87] | -- |
| span-F1 (micro) | 57.36 | 57.40 | +0.04 | [-1.88, +1.93] | [-1.60, +1.65] | -- |
| scenario exact | 81.60 | 86.50 | +4.90 | [+3.02, +6.77] | -- | 72 / 23 |
| action exact | 79.00 | 83.10 | +4.10 | [+2.10, +6.14] | -- | 72 / 31 |
| row SLU-F1 | 47.43 | 48.16 | +0.73 | [-0.57, +2.03] | -- | 81 / 71 |

- **Reproduction.** The driver reproduces both official pooled values to within 3e-16.
- **Unrounded CI95 bounds.** Intent [+2.5768, +6.7327]; SLU-F1 [-1.0402, +2.0942]. McNemar p for intent is
  1.6e-05.

**Recording channel.**

| channel | rows | intent delta pp | saves / harms | row SLU-F1 delta pp |
| --- | ---: | ---: | --- | ---: |
| far-field | 540 | +5.74 | 48 / 17 | +1.52 |
| headset | 460 | +3.26 | 31 / 16 | -0.21 |

**Per scenario: NOT AVAILABLE on this roster.** The roster receipt withholds the per-item stratum
(`stratum_withheld_per_item: true`), so there is no model-free per-row scenario label. The official per-sample rows
carry no scenario either. The driver records this in `per-scenario-tables.json` (`a2678332...36138`), as it did for
the B6 DEV-2000-ADDED read. Neither the natural-mixture per-scenario table nor the equal-scenario weighting can be
computed without reading gold per row, which this read does not do. The Fold A per-stratum flags (takeaway intent
-10.0, general SLU -15.5) therefore cannot be checked here.

## 3. The context contrast: A2 minus the sealed DEV plan arm

This contrast is context only, never the bar. The left arm is `SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1`.

| metric | plan arm | A2 | delta pp | CI95 pp | saves / harms |
| --- | ---: | ---: | ---: | --- | --- |
| intent | 76.60 | 81.50 | +4.90 | [+2.81, +7.04] | 82 / 33 |
| official pooled SLU-F1 | 65.40 | 65.93 | +0.54 | [-1.13, +2.18] | -- |
| span-F1 (micro) | 57.05 | 57.40 | +0.35 | [-1.65, +2.29] | -- |
| row SLU-F1 | 47.35 | 48.16 | +0.81 | [-0.60, +2.24] | 85 / 70 |

The A/A sits 0.30 pp above the plan arm on intent (76.90 vs 76.60) with the same pooled SLU-F1. That is consistent
with it being the same locked plan flown again.

## 4. Entities: the COMP-1 harm-pattern check

The counts are exact-match counts summed from the sealed per-sample `slot_f1_exact_*` fields
(`supplement-v1.json`, sha256 `4202edc9...6d241`). 314 rows carry no gold entity, and that count is the same on all
three arms.

| arm | entity TP | FP | FN | emitted | FP on the 314 zero-gold rows | zero-gold rows emitting |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A/A | 608 | 485 | 419 | 1,093 | 169 | **153** |
| A2 | 607 | 481 | 420 | 1,088 | 160 | **140** |
| DEV plan arm (context) | 601 | 479 | 426 | 1,080 | 166 | 152 |

Paired row bootstraps of the summed deltas (10,000 draws, seed 20260929):

| contrast | d TP | d FP, all rows | d FP, zero-gold rows | d zero-gold rows emitting |
| --- | --- | --- | --- | --- |
| A2 - A/A | -1 [-23, +21] | -4 [-34, +25] | -9 [-27, +10] | -13 [-29, +3] |
| A2 - plan arm | +6 [-17, +29] | +2 [-26, +30] | -6 [-24, +12] | -12 [-28, +3] |

**The COMP-1 harm pattern is absent.** The cited COMP-1 arm on Fold A emitted on 252 zero-gold rows against the A/A's
162. On DEV-2000-ADDED, A2 emits on 140 zero-gold rows against the A/A's 153. The point moves the other way, and the
interval includes zero. TP and FN are flat, 607 / 420 against 608 / 419.

## 5. Delivery and conversion

The driver computes delivery with gold on the scoring side only (bank `26231b86...`, roster block `dev2000-added`).
The seal pins of both arms' `phases.json` were checked.

- **Delivery.** The row's gold intent boundary entry is delivered on 956 rows under A2 and 815 under the A/A. That is
  150 newly delivered rows and 9 newly lost. Boundary items per row: 8 on all 1,000 rows under A2, and 8 on 994
  rows under the A/A.
- **Conversion.** The A/A answered 114 of the newly delivered rows wrong, and A2 converts 40 of them to gold
  (35.1 %). On Fold A the rate was 36 of 79 (45.6 %). Three newly delivered rows go right -> wrong.
- **Transitions.**

  | delivery group | rows | wrong -> right | right -> wrong |
  | --- | ---: | ---: | ---: |
  | newly delivered | 150 | 40 | 3 |
  | delivered in both | 806 | 37 | 28 |
  | newly lost | 9 | 1 | 2 |
  | delivered in neither | 35 | 1 | 0 |

- **Gold entry use on newly delivered rows.** Used 103, ignored 47.
- **Bank class of newly delivered rows.** INTENT-UNCOVERED 107, CORRECT 21, INTENT-COVERED 10, and 4 each of
  ENTITY-FN-ONLY, ENTITY-FP-ONLY and ENTITY-MIXED.

**Attribution classes: not emitted by the driver.** The registered membership is
`docs/readiness/2026-09-27-slurp-stage3-comp-1-dev2000-added-v1/attribution-classes-v1.json` (sha256
`4f129ef4...9ef4493`, matching the recipe; 232 intent-wrong rows under the plan arm). It persists counts and
id-list hashes only, so a per-class outcome table needs `scripts/flights/comp1dev/comp1dev_attribution_classes.py`
re-run and every id-list hash reproduced. This read did not do that; it stays open for the coordinator.

## 6. Byte and structure checks

- **Recipe step 2, supply identity.** The A/A's prepared first-phase supply has output digest `d57ee9d6...fc5a19`,
  and the arm's has `ecca16a2...51b7d08`. Both equal the registered values.
- **Structure.** Both arms have 0 tool calls, and all 1,000 rows on each arm were admitted.
  - Deliver normaliser applied: 999 rows (arm), 997 (A/A).
  - Deliver normaliser changed the delivered value: 110 rows (arm), 116 (A/A).
  - Planner REVISE: 22 (arm), 30 (A/A). Revisions executed: 19 and 28.
  - Role visits per row for the arm: 4 on 974 rows, 7 on 19, 2 on 7.

## 7. Replication against the Fold A read

| read | n | intent delta | intent CI95 | SLU-F1 delta | SLU-F1 CI95 | zero-gold rows emitting (A/A -> arm) |
| --- | ---: | ---: | --- | ---: | --- | --- |
| COMP-1b, TRAIN Fold A | 1,080 | +3.80 | [+1.94, +5.65] | -0.60 | [-2.29, +1.07] | 162 -> 161 |
| A2, DEV-2000-ADDED | 1,000 | +4.60 | [+2.58, +6.73] | +0.53 | [-1.04, +2.09] | 153 -> 140 |

- **Intent replicates.** The sign is the same, the intervals overlap on [+2.58, +5.65], and the DEV point is 0.80 pp
  above the Fold A point.
- **SLU-F1 moves from -0.60 to +0.53.** Both intervals cross zero and they overlap. The Fold A width concern closes
  on DEV, where the lower bound is -1.04, inside -h_SLU = -1.2525.

## 8. The rule and the verdict

The registered rule (`protocol-registered-v1.json`, `decision_rule_fixed_here`):

- **REPLICATED** requires three things: the intent CI95 lower bound above zero, the point at or above the 2.6 pp
  cross-flight bar at n = 1,000 (the floor gate computes 2.5981), and the guard holding. The guard is official
  pooled SLU-F1, non-inferior at h_SLU 1.2525.
- **NEUTRAL** means both guards are non-inferior without a replicated gain.
- **HARMFUL** means a measured loss on either guard (decision 25).

**Verdict (read agent, for the coordinator):**

- **Intent: all three conditions hold.** The point is +4.60 and the lower bound is +2.58 > 0. The point clears both
  the 2.5981 floor and the declared 3.80.
- **SLU-F1 guard: holds by width, not just on the point.** The point is +0.53 >= -1.2525, and the CI95 lower bound
  -1.04 also lies inside -1.2525. No loss is measured.
- **Harm pattern: absent.** Zero-gold emission is 140 vs 153, with d FP on zero-gold rows -9 [-27, +10].
- **On the registered rule this reads REPLICATED**, which is **NOMINATED** on the coordinator's A2 bar (intent lower
  bound > 0, point > 2.5981, SLU point >= -1.2525). It is not HARMFUL.
- **Open items.** Per-scenario tables cannot be computed on this roster. The attribution-class outcome table was not
  produced (section 5).
- **Milestone.** A2's intent point for the milestone re-declaration is **+4.60 pp**.

Nothing is admitted by this note. The coordinator's clause and the disposition are pending, including owner decision
209.

## 9. Reproduce

```bash
# model-free; master after the READ-row countersignature (aaf4f2f93)
bash scripts/flights/comp1/comp1bdev_read.sh     # writes vs-aa and vs-comparator
python -B scripts/analysis/slurp_a2_read_supplement.py "$SPEECHRL_DATA_DIR" \
  "$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-PAIRED-ANALYSIS-V1/supplement-v1.json"
```

Outputs are under `analysis/SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-PAIRED-ANALYSIS-V1/`: `vs-aa/`, `vs-comparator/`
and `supplement-v1.json`.
