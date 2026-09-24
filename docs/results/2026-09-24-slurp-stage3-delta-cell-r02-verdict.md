# Cell CELL-2 verdict: the locked v2.0 plan plus the per-node stage3-deltas-v2 store (the 200 values owner decision 83's per-scenario x frontier retention kept out of the 379 v1r deltas over the CELL-1 read; Solver 8 / Reviewer 4 / Planner 4 candidate-bound, Perception unconditional 4) (Stage-3 S3-6 ITERATION 2: the decision-83 retention of v1r; owner decisions 83, 99, 101, 106)

Read 2026-09-24 by the coordinator (Fable 5.1) with `scripts/analysis/plan_cell_read.py` via `scripts/flights/batch/cell2_read.sh arm` (analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-DELTA-CELL-R02-PAIRED-ANALYSIS-V1`, score-contrasts sha256 `c3b1d7047fd82ce7048b09d6172f8d3a8e5ef1295ced10580d5ab6840685447b`), and the per-node delta-consumption table with `scripts/analysis/stage3_delta_consumption_read.py`. Comparator = the sealed PLAN arm at the plan's own null (h_SLU 1.2485 / h_intent 0.9943). Model-free: zero model / tokenizer / encoder / server contacts. Development numbers (decisions 28, 86).

## 1. Verdict

| item | result |
| --- | --- |
| status | **NEUTRAL by width; NON-INFERIORITY NOT PROVEN on intent (SLU non-inferior and positive but unproven); iteration 2 moves the arm in the right direction without a proven gain** |
| driver status | NON-INFERIORITY NOT PROVEN |
| reading | Against the sealed PLAN arm the arm reads official pooled SLU-F1 64.27 vs 63.63 (+0.64 pp, CI95 [-0.76, +1.92]; non-inferior at the 1.2485 margin, gain unproven) and intent 82.13 vs 82.22 (-0.09 pp, CI95 [-1.22, +0.96]; the lower bound sits 0.23 pp beyond the -0.9943 margin, so non-inferiority is NOT proven by width, not by a measured loss); the per-row SLU mean is +1.30 pp (CI95 [-0.04, +2.67], CI90 [+0.16, +2.44]; saves 87 / harms 70) and the TRAIN symmetric scorer agrees in sign (+0.66). The derangement twin reads 63.68 (+0.05, CI95 [-1.52, +1.62]) and 81.30 (-0.93, CI95 [-2.40, +0.41]); arm minus twin is +0.59 pp SLU and +0.83 pp intent (descriptive): the retained content sits above its own form control on both metrics, inside the noise band. Iteration 1 -> 2 (CELL-1 -> CELL-2): SLU -0.48 -> +0.64, intent -0.74 -> -0.09; the harm scenarios contracted (alarm -6.8 -> -3.6, news -6.6 -> -0.5, play -5.8 -> -0.6) and the winners grew (audio +8.9 -> +14.5, weather +8.3 -> +9.7, email +3.5), while general stays the hole (-12.4 -> -10.6 SLU, -6.7 intent) because no retained value targets it. Against the Stage-2 lock B5e official the arm is +1.93 SLU [+0.56, +3.34] and +2.04 intent [+0.74, +3.34]. Consumption: 121 of 200 values supplied, Solver reaches 68.5 % of rows, Reviewer 64.1 %, Planner 18.3 % (10 of 14 Planner values retired), one Solver value (d1c93189) reads -1.9 SLU / -2.2 intent on 182 rows. Cost: 4.15 contacts per row (+1.3 %), 1.768 GPU-h (+0.6 %), prefilled tokens +6.6 %, zero rows compacted. A SECOND look on the rows whose CELL-1 read chose the retained set: a development number under owner decisions 28 / 86, and no claim before the fresh-roster replicate. |
| cost | contacts / row 4.151 vs 4.096; GPU-h / 1,080 1.768 vs 1.758; contacts / min 40.4 vs 39.9; prefilled tokens / row 8905 vs 8353; cost lower than the base: False |
| trajectory | contacts 4483 (4.151 / row; histogram {'3': 5, '4': 1019, '7': 56}); comparator 4424 (4.096 / row; {'3': 10, '4': 1032, '7': 38}) |
| dispositions | finite stops 5, react exhaustion 0, planner-action-illegal 0, other terminal 5 |

### 1a. The decision rule, as registered (owner decision 99, the TRAIN lock)

Delta = CELL-2 minus the sealed PLAN arm (`SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`), in percentage points.

- **ADMITTED** -- the CI95 lower bound of the paired **official pooled SLU-F1** delta is **above zero** and the CI95 lower bound of the paired **intent** delta exceeds **-0.9943**. A gain is proven, not merely non-inferior.
- **NEUTRAL** -- both guards non-inferior (SLU lower bound above -1.2485, intent lower bound above -0.9943) without a proven SLU gain.
- **HARMFUL** -- a **measured** loss on either guard (owner decision 25, Method B: a CI95 upper bound below zero, or a point estimate beyond the margin). Width alone is NEUTRAL, never HARMFUL.
- **TWIN = attribution, never admission.** A gain the twin reproduces within the plan's own null is **form** -- the store's shape and token volume -- not content, and the verdict says so and claims no content effect. A gain the twin does not reproduce is attributed to the deltas' content, with the twin delta reported beside it.
- **Replication** -- an ADMITTED result is replicated on the **same roster** before any DEV, Fold B or test read. No such read is authorised by this package.

| guard | arm | comparator | delta pp | CI95 | margin | decides |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| official pooled SLU-F1 | 64.27 | 63.63 | +0.64 | [-0.76, +1.92] | 1.2485 | non-inferior |
| intent (joint scenario+action) | 82.13 | 82.22 | -0.09 | [-1.22, +0.96] | 0.9943 | width only |

## 2. Headline contrasts (CELL-2 minus PLAN, paired, slurp-stage3-delta-cell-r02-arm-paired-analysis-v1)

| metric | PLAN | arm | delta pp | CI95 (speaker) | CI90 (speaker) | CI90 (scenario-stratified) | equal-scenario delta |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: |
| slu_f1_micro | 63.63 | 64.27 | +0.64 | [-0.76, +1.92] | [-0.55, +1.73] | [-0.74, +2.02] | +0.51 |
| scenario_action_exact | 82.22 | 82.13 | -0.09 | [-1.22, +0.96] | [-1.05, +0.80] | [-1.11, +0.93] | -0.09 |
| span_f1_micro | 53.78 | 54.10 | +0.32 | [-1.43, +2.00] | [-1.12, +1.72] | [-1.27, +1.91] | -0.02 |
| scenario_exact | 87.31 | 86.94 | -0.37 | [-1.76, +1.05] | [-1.54, +0.80] | [-1.39, +0.65] | -0.37 |
| action_exact | 83.52 | 83.33 | -0.19 | [-1.33, +0.95] | [-1.15, +0.77] | [-1.20, +0.83] | -0.19 |
| slu_f1_f1 | 42.25 | 43.55 | +1.30 | [+0.10, +2.51] | [+0.27, +2.31] | [+0.16, +2.44] | +1.30 |
| slot_f1_exact_f1 | 34.99 | 35.96 | +0.97 | [-0.36, +2.28] | [-0.15, +2.05] | [-0.21, +2.19] | +0.97 |

| metric | saves | harms | ties | two-sided McNemar p |
| --- | ---: | ---: | ---: | ---: |
| scenario_action_exact | 23 | 24 | 1033 | 1.0000 |
| scenario_exact | 20 | 24 | 1036 | 0.6516 |
| action_exact | 21 | 23 | 1036 | 0.8804 |
| slu_f1_f1 | 87 | 70 | 923 | 0.2015 |
| slot_f1_exact_f1 | 61 | 54 | 965 | 0.5760 |

Lock comparison (reported, never a gate): see `lock-comparison.json`; projection-v3 and TRAIN-symmetric companions are in `score-contrasts.json`.

## 3. The derangement twin (form control) and the content attribution

Twin analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-DELTA-CELL-R02-TWIN-PAIRED-ANALYSIS-V1`, score-contrasts sha256 `4e8eb08c4d95c6972f105129523c06d721d1c1d55503bc5bd4d9b8b5d21c9ee8`. Same comparator, same margins, same estimator, same seed: the twin read is the arm read with one input changed.

| metric | arm delta pp | arm CI95 | twin delta pp | twin CI95 | arm minus twin pp |
| --- | ---: | --- | ---: | --- | ---: |
| slu_f1_micro | +0.64 | [-0.76, +1.92] | +0.05 | [-1.53, +1.51] | +0.59 |
| scenario_action_exact | -0.09 | [-1.22, +0.96] | -0.93 | [-2.40, +0.41] | +0.83 |
| span_f1_micro | +0.32 | [-1.43, +2.00] | +0.07 | [-1.75, +1.72] | +0.25 |

**The arm-minus-twin column is DESCRIPTIVE.** It is the difference of two point estimates, each against the same sealed PLAN arm; no interval is computed for it and no test is run on it. It bounds how much of the arm's movement the store's shape and token volume alone can account for. The twin decides attribution, never admission (decision 99).

The derangement twin is a genuine FORM control on **363 of 379** rows (95.8 %): 16 of the 379 rows landed on a facet set equal to their own by arithmetic, because store revision v1r's vocabulary is 39 distinct intents over 379 rows, and the builder refuses only a twin that moved nothing at all. The twin therefore bounds the form contribution slightly from below; it is reported, not claimed away.

## 4. Per scenario (natural mixture and equal-scenario weighting; diagnostics, never gates)

- pooled_slu_f1_equal_scenario_delta_pp: 0.5147058197356853
### pooled_slu_f1_per_scenario

| scenario | delta_pp | left_pct | n | right_pct |
| --- | ---: | ---: | ---: | ---: |
| alarm | -3.644 | 76.748 | 60 | 73.104 |
| audio | 14.537 | 48.174 | 60 | 62.711 |
| calendar | 0.553 | 65.639 | 60 | 66.192 |
| cooking | 0.051 | 63.211 | 60 | 63.262 |
| datetime | 2.444 | 73.373 | 60 | 75.817 |
| email | 3.541 | 61.783 | 60 | 65.324 |
| general | -10.622 | 30.229 | 60 | 19.608 |
| iot | -0.860 | 66.368 | 60 | 65.507 |
| lists | -0.288 | 57.454 | 60 | 57.166 |
| music | -3.401 | 48.750 | 60 | 45.349 |
| news | -0.460 | 68.766 | 60 | 68.306 |
| play | -0.551 | 55.388 | 60 | 54.837 |
| qa | -0.893 | 62.649 | 60 | 61.756 |
| recommendation | 1.066 | 66.485 | 60 | 67.551 |
| social | -3.106 | 58.324 | 60 | 55.217 |
| takeaway | -0.032 | 61.793 | 60 | 61.761 |
| transport | 1.213 | 66.680 | 60 | 67.893 |
| weather | 9.717 | 70.838 | 60 | 80.555 |

### pooled_span_f1_per_scenario

| scenario | delta_pp | left_pct | n | right_pct |
| --- | ---: | ---: | ---: | ---: |
| alarm | -2.830 | 68.376 | 60 | 65.546 |
| audio | 11.706 | 23.077 | 60 | 34.783 |
| calendar | 0.647 | 52.439 | 60 | 53.086 |
| cooking | -0.434 | 52.101 | 60 | 51.667 |
| datetime | 4.398 | 59.016 | 60 | 63.415 |
| email | 0.927 | 49.524 | 60 | 50.450 |
| general | -7.843 | 27.451 | 60 | 19.608 |
| iot | -1.053 | 60.000 | 60 | 58.947 |
| lists | -3.387 | 54.054 | 60 | 50.667 |
| music | -3.297 | 46.154 | 60 | 42.857 |
| news | -3.671 | 59.341 | 60 | 55.670 |
| play | -2.384 | 41.322 | 60 | 38.938 |
| qa | -1.887 | 49.057 | 60 | 47.170 |
| recommendation | 1.265 | 59.200 | 60 | 60.465 |
| social | -2.685 | 48.322 | 60 | 45.638 |
| takeaway | -1.858 | 48.611 | 60 | 46.753 |
| transport | 2.398 | 59.627 | 60 | 62.025 |
| weather | 9.597 | 67.133 | 60 | 76.730 |

Intent band: decision-17 flagged scenarios = []; scenarios losing beyond the band = [].

## 5. Frontier row (decision 75)

| cell | official SLU | official intent | GPU-h / 1,080 | contacts / row | prefilled tok / row | on GPU-h frontier | on token frontier |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| CELL-2 | 64.27 | 82.13 | 1.7679 | 4.151 | 8905.1 | True | True |
| CELL-2 twin | 63.68 | 81.30 | 1.7120 | 4.080 | 8819.9 | False | False |

## 6. Per-node delta consumption (item S3-4s)

Store `stage3-deltas`, release sha256 `b81df5c5175e45e68933d4875c110fd46bea933283631d2c428187c480fc31f0`, snapshot `44a804184cf83a08e85831d40bae942af1e71ed4365b485d833f9a03807ef150`. Rows 1080; rows that received at least one delta 1080; items supplied 11074; distinct value ids 121; skip events 1726; projection events 72; inert routes none.

| node | cap | rows supplied | share | items | items / supplied row | at full cap | distinct value ids | skip events | rows skipped |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| perception | 4 | 1080 | 1.000 | 4320 | 4.000 | 1080 | 4 | 0 | 0 |
| solver | -- | 740 | 0.685 | 4177 | 5.645 | -- | 74 | 371 | 360 |
| reviewer | 4 | 692 | 0.641 | 2296 | 3.318 | 425 | 39 | 422 | 412 |
| planner | 4 | 198 | 0.183 | 281 | 1.419 | 0 | 4 | 933 | 903 |

| node | rows supplied | SLU saves | SLU harms | SLU neutral | SLU mean delta pp | intent saves | intent harms | intent neutral | intent mean delta pp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| perception | 1080 | 87 | 70 | 923 | +1.301 | 23 | 24 | 1033 | -0.093 |
| solver | 740 | 72 | 53 | 615 | +1.758 | 15 | 19 | 706 | -0.541 |
| reviewer | 692 | 69 | 51 | 572 | +1.864 | 16 | 16 | 660 | +0.000 |
| planner | 198 | 20 | 21 | 157 | +0.208 | 6 | 7 | 185 | -0.505 |

### 6a. Arm versus twin supplied volume

| node | arm rows supplied | twin rows supplied | arm items | twin items | arm distinct value ids | twin distinct value ids |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| perception | 1080 | 1080 | 4320 | 4320 | 4 | 4 |
| solver | 740 | 812 | 4177 | 4254 | 74 | 75 |
| reviewer | 692 | 592 | 2296 | 1946 | 39 | 38 |
| planner | 198 | 248 | 281 | 402 | 4 | 4 |

The derangement holds the store's TOTAL token count, not the SUPPLIED token count: a twin that supplies materially more or less than the arm is a weaker form control, and this table is where that is read rather than assumed.

The full per-value-id and per-scenario tables are in `delta-consumption.json` and `delta-consumption.md` in the analysis root. Value ids, node targets and counts only; never statement text.

## 7. Cost

| item | arm | comparator (PLAN) |
| --- | ---: | ---: |
| contacts / row | 4.151 | 4.096 |
| contacts / min | 40.4 | 39.9 |
| prefilled tokens / row | 8905 | 8353 |
| GPU-h / 1,080 rows | 1.7679 | 1.7579 |
| cache hit share | 0.7516 | 0.7545 |
| generation wall seconds | 6862.5 | 6946.0 |

## 8. Caveats

1. The derangement twin is a genuine FORM control on **363 of 379** rows (95.8 %): 16 of the 379 rows landed on a facet set equal to their own by arithmetic, because store revision v1r's vocabulary is 39 distinct intents over 379 rows, and the builder refuses only a twin that moved nothing at all. The twin therefore bounds the form contribution slightly from below; it is reported, not claimed away.
2. The registered worst-case prompt-fit bound puts the **Solver** phase at `COMPACT_REQUIRED` by 317 tokens under this cell's added block (preregistration section 5), so a non-zero compacted-row count is expected and is a caveat on the frontier row's token basis. An abstention caused by compaction would be a failure, not a caveat. Measured on this flight: contacts compacted 0, one receipt per row True, receipt dispositions {'context_compaction_contacts': 0, 'context_compaction_rows': 0, 'finite_completion_rows': 5, 'planner_action_illegal_rows': 0}.
3. **Four launch failures** preceded this flight, metering 320 contacts in total on retired attempts. None of them sealed an output or produced a score, so none of them contributes evidence beyond the harness; the plan budget is run-cumulative across every attempt of a run id, so those contacts count against this cell's registered ceiling.

| attempt | metered contacts | what failed |
| --- | ---: | --- |
| smoke v1, first launch | 0 | refused before any contact in core.flight.runtime._merge_unconditional_first_phase (an unconditional store route repeats a seeded value id); the attempt opened and metered nothing |
| smoke v1, recovery | 4 | the one allowed recovery re-registration was flown and failed; the v1 smoke run id was retired |
| smoke v2 | 12 | died at the openJiuwen vertex reviewer_0_input ('acquire must introduce at least one new value or facet'): a node-filtered candidate-bound route that selected NOTHING still returned a supply. Fixed in rails.knowledge_stores._stage3_delta_local_supply, which now supplies nothing and receipts the skip |
| arm, first attempt | 304 | aborted at solver_0_input on a Perception answer carrying duplicate candidate intent ids ('candidate intent_ids must be unique and ordered'); 73 of 75 rows completed, no output was sealed and no score was produced. Fixed by deriving both readers' parameters from rails.candidate_semantic_supply.candidate_state_read_parameters |

4. Development numbers only (owner decisions 28, 86): TRAIN Fold A is a development roster and no test, Fold B or DEV read is authorised by this verdict. An ADMITTED result is replicated on the SAME roster before any such read.

## 9. Records

Exposure-ledger rows closed (the `SAEA-SLURP-STAGE3-DELTA-CELL-*` family still open, never the retired v1 / v2 smoke rows), flight commit 1425f00b, 2026-09-24T03:32-07:34 UTC (smoke 03:32-03:34, arm 03:34-05:33, twin smoke 05:34-05:35, twin 05:35-07:34; SAEA-Batch-Chain-CELL2, flight commit 1425f00b); results-ledger entry; decision-99 outcome appended. Stage-3 algorithm label (owner decision 101): `tfgrpo-semantic-advantage-v1`, operators update + context_application.

Read: `docs/results/2026-09-24-slurp-stage3-delta-cell-r02-verdict.md`.
