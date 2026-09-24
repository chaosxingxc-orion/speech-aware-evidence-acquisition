# Cell CELL-1 verdict: the locked v2.0 plan plus the per-node stage3-deltas-v1r store (379 node-targeted deltas curated from the sealed ADV-1 statements; Solver 8 / Reviewer 4 / Planner 4 candidate-bound, Perception unconditional 4) (Stage-3 S3-6 / S3-4s, owner decisions 83, 99, 101, 106)

Read 2026-09-23 by the coordinator (Fable 5.1) with `scripts/analysis/plan_cell_read.py` via `scripts/flights/batch/cell1_read.sh arm` (analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-DELTA-CELL-R01-PAIRED-ANALYSIS-V1`, score-contrasts sha256 `6fd8f734fd68ec129becda4f8a452d7c984dd9743e1d949344551de8c5670d8c`), and the per-node delta-consumption table with `scripts/analysis/stage3_delta_consumption_read.py`. Comparator = the sealed PLAN arm at the plan's own null (h_SLU 1.2485 / h_intent 0.9943). Model-free: zero model / tokenizer / encoder / server contacts. Development numbers (decisions 28, 86).

## 1. Verdict

| item | result |
| --- | --- |
| status | **NEUTRAL by width; NON-INFERIORITY NOT PROVEN on either metric (no observable positive gain on TRAIN Fold A; the twin reproduces the arm within noise, so the delta store's content moves nothing at the pooled level)** |
| driver status | NON-INFERIORITY NOT PROVEN |
| reading | Against the sealed PLAN arm the arm reads official pooled SLU-F1 63.15 vs 63.63 (-0.48 pp, CI95 [-2.18, +1.24]) and intent 81.48 vs 82.22 (-0.74 pp, CI95 [-2.17, +0.57]); the derangement twin reads 63.19 (-0.44, CI95 [-1.94, +0.99]) and 82.31 (+0.09, CI95 [-1.19, +1.30]); arm minus twin is -0.04 pp SLU and -0.83 pp intent (descriptive): the pooled effect is neither content nor form. Every row received deltas (256 of 379 distinct values supplied; Planner reaches 59 % of rows), the per-delta paired outcomes are strongly heterogeneous (Solver deltas +5 to +6.5 pp SLU on 100+ rows beside -4 to -5 pp), and the per-scenario table swings from audio +8.9 / weather +8.3 / datetime +4.2 to general -12.4 / alarm -6.8 / news -6.6 / play -5.8 pp -- the pattern decision 83's retention rule was preregistered for (iteration 2: 200 kept / 179 retired, iteration-2-retention-v1.md). Cost: contacts +2.9 %, GPU-h +2.5 %, prefilled tokens +10.9 %; off both frontiers. The loop itself (rollout -> scoring -> advantage -> curation -> release -> cell -> read) closed end to end under the contracts; the four launch defects of 2026-09-23 were mechanism-wiring defects fixed before any generation contact was wasted beyond 320 metered calls. |
| cost | contacts / row 4.216 vs 4.096; GPU-h / 1,080 1.802 vs 1.758; contacts / min 39.8 vs 39.9; prefilled tokens / row 9265 vs 8353; cost lower than the base: False |
| trajectory | contacts 4553 (4.216 / row; histogram {'3': 7, '4': 993, '7': 80}); comparator 4424 (4.096 / row; {'3': 10, '4': 1032, '7': 38}) |
| dispositions | finite stops 7, react exhaustion 0, planner-action-illegal 1, other terminal 5 |

### 1a. The decision rule, as registered (owner decision 99, the TRAIN lock)

Delta = CELL-1 minus the sealed PLAN arm (`SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`), in percentage points.

- **ADMITTED** -- the CI95 lower bound of the paired **official pooled SLU-F1** delta is **above zero** and the CI95 lower bound of the paired **intent** delta exceeds **-0.9943**. A gain is proven, not merely non-inferior.
- **NEUTRAL** -- both guards non-inferior (SLU lower bound above -1.2485, intent lower bound above -0.9943) without a proven SLU gain.
- **HARMFUL** -- a **measured** loss on either guard (owner decision 25, Method B: a CI95 upper bound below zero, or a point estimate beyond the margin). Width alone is NEUTRAL, never HARMFUL.
- **TWIN = attribution, never admission.** A gain the twin reproduces within the plan's own null is **form** -- the store's shape and token volume -- not content, and the verdict says so and claims no content effect. A gain the twin does not reproduce is attributed to the deltas' content, with the twin delta reported beside it.
- **Replication** -- an ADMITTED result is replicated on the **same roster** before any DEV, Fold B or test read. No such read is authorised by this package.

| guard | arm | comparator | delta pp | CI95 | margin | decides |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| official pooled SLU-F1 | 63.15 | 63.63 | -0.48 | [-2.18, +1.24] | 1.2485 | width only |
| intent (joint scenario+action) | 81.48 | 82.22 | -0.74 | [-2.17, +0.57] | 0.9943 | width only |

## 2. Headline contrasts (CELL-1 minus PLAN, paired, slurp-stage3-delta-cell-arm-paired-analysis-v1)

| metric | PLAN | arm | delta pp | CI95 (speaker) | CI90 (speaker) | CI90 (scenario-stratified) | equal-scenario delta |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: |
| slu_f1_micro | 63.63 | 63.15 | -0.48 | [-2.18, +1.24] | [-1.91, +0.94] | [-1.91, +0.94] | -0.83 |
| scenario_action_exact | 82.22 | 81.48 | -0.74 | [-2.17, +0.57] | [-1.91, +0.35] | [-1.76, +0.28] | -0.74 |
| span_f1_micro | 53.78 | 53.60 | -0.18 | [-2.19, +1.87] | [-1.84, +1.50] | [-1.76, +1.41] | -0.49 |
| scenario_exact | 87.31 | 86.39 | -0.93 | [-2.42, +0.45] | [-2.19, +0.25] | [-1.85, +0.00] | -0.93 |
| action_exact | 83.52 | 82.50 | -1.02 | [-2.31, +0.18] | [-2.07, +0.00] | [-2.04, -0.09] | -1.02 |
| slu_f1_f1 | 42.25 | 42.78 | +0.54 | [-0.71, +1.83] | [-0.52, +1.64] | [-0.61, +1.68] | +0.54 |
| slot_f1_exact_f1 | 34.99 | 35.57 | +0.57 | [-0.85, +1.98] | [-0.63, +1.74] | [-0.61, +1.79] | +0.57 |

| metric | saves | harms | ties | two-sided McNemar p |
| --- | ---: | ---: | ---: | ---: |
| scenario_action_exact | 19 | 27 | 1034 | 0.3020 |
| scenario_exact | 15 | 25 | 1040 | 0.1539 |
| action_exact | 16 | 27 | 1037 | 0.1263 |
| slu_f1_f1 | 86 | 81 | 913 | 0.7570 |
| slot_f1_exact_f1 | 66 | 61 | 953 | 0.7228 |

Lock comparison (reported, never a gate): see `lock-comparison.json`; projection-v3 and TRAIN-symmetric companions are in `score-contrasts.json`.

## 3. The derangement twin (form control) and the content attribution

Twin analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-DELTA-CELL-TWIN-PAIRED-ANALYSIS-V1`, score-contrasts sha256 `03b0c98a7432f3be6144bd786f48249f463e204b11c6acd08fe4b5993722bdc6`. Same comparator, same margins, same estimator, same seed: the twin read is the arm read with one input changed.

| metric | arm delta pp | arm CI95 | twin delta pp | twin CI95 | arm minus twin pp |
| --- | ---: | --- | ---: | --- | ---: |
| slu_f1_micro | -0.48 | [-2.18, +1.24] | -0.44 | [-1.94, +0.99] | -0.04 |
| scenario_action_exact | -0.74 | [-2.17, +0.57] | +0.09 | [-1.19, +1.30] | -0.83 |
| span_f1_micro | -0.18 | [-2.19, +1.87] | -0.30 | [-2.20, +1.63] | +0.12 |

**The arm-minus-twin column is DESCRIPTIVE.** It is the difference of two point estimates, each against the same sealed PLAN arm; no interval is computed for it and no test is run on it. It bounds how much of the arm's movement the store's shape and token volume alone can account for. The twin decides attribution, never admission (decision 99).

The derangement twin is a genuine FORM control on **363 of 379** rows (95.8 %): 16 of the 379 rows landed on a facet set equal to their own by arithmetic, because store revision v1r's vocabulary is 39 distinct intents over 379 rows, and the builder refuses only a twin that moved nothing at all. The twin therefore bounds the form contribution slightly from below; it is reported, not claimed away.

## 4. Per scenario (natural mixture and equal-scenario weighting; diagnostics, never gates)

- pooled_slu_f1_equal_scenario_delta_pp: -0.8256825868487585
### pooled_slu_f1_per_scenario

| scenario | delta_pp | left_pct | n | right_pct |
| --- | ---: | ---: | ---: | ---: |
| alarm | -6.782 | 76.748 | 60 | 69.966 |
| audio | 8.944 | 48.174 | 60 | 57.118 |
| calendar | 0.239 | 65.639 | 60 | 65.879 |
| cooking | -1.064 | 63.211 | 60 | 62.146 |
| datetime | 4.150 | 73.373 | 60 | 77.523 |
| email | 2.160 | 61.783 | 60 | 63.943 |
| general | -12.372 | 30.229 | 60 | 17.857 |
| iot | -3.424 | 66.368 | 60 | 62.944 |
| lists | -1.816 | 57.454 | 60 | 55.638 |
| music | -2.754 | 48.750 | 60 | 45.996 |
| news | -6.563 | 68.766 | 60 | 62.203 |
| play | -5.779 | 55.388 | 60 | 49.610 |
| qa | 0.657 | 62.649 | 60 | 63.306 |
| recommendation | 1.817 | 66.485 | 60 | 68.303 |
| social | -2.120 | 58.324 | 60 | 56.204 |
| takeaway | -0.023 | 61.793 | 60 | 61.770 |
| transport | 1.529 | 66.680 | 60 | 68.209 |
| weather | 8.339 | 70.838 | 60 | 79.177 |

### pooled_span_f1_per_scenario

| scenario | delta_pp | left_pct | n | right_pct |
| --- | ---: | ---: | ---: | ---: |
| alarm | -5.043 | 68.376 | 60 | 63.333 |
| audio | 11.406 | 23.077 | 60 | 34.483 |
| calendar | -0.265 | 52.439 | 60 | 52.174 |
| cooking | -0.434 | 52.101 | 60 | 51.667 |
| datetime | 5.500 | 59.016 | 60 | 64.516 |
| email | -0.467 | 49.524 | 60 | 49.057 |
| general | -9.594 | 27.451 | 60 | 17.857 |
| iot | -1.053 | 60.000 | 60 | 58.947 |
| lists | -3.387 | 54.054 | 60 | 50.667 |
| music | -3.297 | 46.154 | 60 | 42.857 |
| news | -8.320 | 59.341 | 60 | 51.020 |
| play | -5.115 | 41.322 | 60 | 36.207 |
| qa | 0.000 | 49.057 | 60 | 49.057 |
| recommendation | 0.950 | 59.200 | 60 | 60.150 |
| social | -2.168 | 48.322 | 60 | 46.154 |
| takeaway | -1.406 | 48.611 | 60 | 47.205 |
| transport | 4.123 | 59.627 | 60 | 63.750 |
| weather | 9.790 | 67.133 | 60 | 76.923 |

Intent band: decision-17 flagged scenarios = ['general']; scenarios losing beyond the band = ['general'].

## 5. Frontier row (decision 75)

| cell | official SLU | official intent | GPU-h / 1,080 | contacts / row | prefilled tok / row | on GPU-h frontier | on token frontier |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| CELL-1 | 63.15 | 81.48 | 1.8021 | 4.216 | 9264.9 | False | False |
| CELL-1 twin | 63.19 | 82.31 | 1.7879 | 4.142 | 9194.6 | False | False |

## 6. Per-node delta consumption (item S3-4s)

Store `stage3-deltas`, release sha256 `02505ba2e548a008cc6c16ffda6f7b9bff505061863026a3d7e1396c26d6c2e0`, snapshot `e2552666ebe6dcd87e4239bfddb3a02d62e8965280b9f52c40acf9cbf4b2f27d`. Rows 1080; rows that received at least one delta 1080; items supplied 15235; distinct value ids 256; skip events 831; projection events 75; inert routes none.

| node | cap | rows supplied | share | items | items / supplied row | at full cap | distinct value ids | skip events | rows skipped |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| perception | 4 | 1080 | 1.000 | 4320 | 4.000 | 1080 | 4 | 0 | 0 |
| solver | 8 | 937 | 0.868 | 6386 | 6.815 | 536 | 147 | 189 | 176 |
| reviewer | 4 | 982 | 0.909 | 3722 | 3.790 | 727 | 91 | 130 | 123 |
| planner | 4 | 641 | 0.594 | 807 | 1.259 | 0 | 14 | 512 | 488 |

| node | rows supplied | SLU saves | SLU harms | SLU neutral | SLU mean delta pp | intent saves | intent harms | intent neutral | intent mean delta pp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| perception | 1080 | 86 | 81 | 913 | +0.537 | 19 | 27 | 1034 | -0.741 |
| solver | 937 | 81 | 78 | 778 | +0.340 | 17 | 24 | 896 | -0.747 |
| reviewer | 982 | 81 | 76 | 825 | +0.404 | 18 | 24 | 940 | -0.611 |
| planner | 641 | 47 | 51 | 543 | -0.127 | 10 | 17 | 614 | -1.092 |

### 6a. Arm versus twin supplied volume

| node | arm rows supplied | twin rows supplied | arm items | twin items | arm distinct value ids | twin distinct value ids |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| perception | 1080 | 1080 | 4320 | 4320 | 4 | 4 |
| solver | 937 | 902 | 6386 | 6344 | 147 | 149 |
| reviewer | 982 | 980 | 3722 | 3571 | 91 | 89 |
| planner | 641 | 471 | 807 | 827 | 14 | 14 |

The derangement holds the store's TOTAL token count, not the SUPPLIED token count: a twin that supplies materially more or less than the arm is a weaker form control, and this table is where that is read rather than assumed.

The full per-value-id and per-scenario tables are in `delta-consumption.json` and `delta-consumption.md` in the analysis root. Value ids, node targets and counts only; never statement text.

## 7. Cost

| item | arm | comparator (PLAN) |
| --- | ---: | ---: |
| contacts / row | 4.216 | 4.096 |
| contacts / min | 39.8 | 39.9 |
| prefilled tokens / row | 9265 | 8353 |
| GPU-h / 1,080 rows | 1.8021 | 1.7579 |
| cache hit share | 0.7486 | 0.7545 |
| generation wall seconds | 7089.7 | 6946.0 |

## 8. Caveats

1. The derangement twin is a genuine FORM control on **363 of 379** rows (95.8 %): 16 of the 379 rows landed on a facet set equal to their own by arithmetic, because store revision v1r's vocabulary is 39 distinct intents over 379 rows, and the builder refuses only a twin that moved nothing at all. The twin therefore bounds the form contribution slightly from below; it is reported, not claimed away.
2. The registered worst-case prompt-fit bound puts the **Solver** phase at `COMPACT_REQUIRED` by 317 tokens under this cell's added block (preregistration section 5), so a non-zero compacted-row count is expected and is a caveat on the frontier row's token basis. An abstention caused by compaction would be a failure, not a caveat. Measured on this flight: contacts compacted 0, one receipt per row True, receipt dispositions {'context_compaction_contacts': 0, 'context_compaction_rows': 0, 'finite_completion_rows': 7, 'planner_action_illegal_rows': 1}.
3. **Four launch failures** preceded this flight, metering 320 contacts in total on retired attempts. None of them sealed an output or produced a score, so none of them contributes evidence beyond the harness; the plan budget is run-cumulative across every attempt of a run id, so those contacts count against this cell's registered ceiling.

| attempt | metered contacts | what failed |
| --- | ---: | --- |
| smoke v1, first launch | 0 | refused before any contact in core.flight.runtime._merge_unconditional_first_phase (an unconditional store route repeats a seeded value id); the attempt opened and metered nothing |
| smoke v1, recovery | 4 | the one allowed recovery re-registration was flown and failed; the v1 smoke run id was retired |
| smoke v2 | 12 | died at the openJiuwen vertex reviewer_0_input ('acquire must introduce at least one new value or facet'): a node-filtered candidate-bound route that selected NOTHING still returned a supply. Fixed in rails.knowledge_stores._stage3_delta_local_supply, which now supplies nothing and receipts the skip |
| arm, first attempt | 304 | aborted at solver_0_input on a Perception answer carrying duplicate candidate intent ids ('candidate intent_ids must be unique and ordered'); 73 of 75 rows completed, no output was sealed and no score was produced. Fixed by deriving both readers' parameters from rails.candidate_semantic_supply.candidate_state_read_parameters |

4. Development numbers only (owner decisions 28, 86): TRAIN Fold A is a development roster and no test, Fold B or DEV read is authorised by this verdict. An ADMITTED result is replicated on the SAME roster before any such read.

## 9. Records

Exposure-ledger rows closed (the `SAEA-SLURP-STAGE3-DELTA-CELL-*` family still open, never the retired v1 / v2 smoke rows), flight commit 00c313c3, 2026-09-23T20:35-2026-09-24T00:46 UTC (arm 20:35-22:42, twin smoke 22:43, twin 22:44-00:46); results-ledger entry; decision-99 outcome appended. Stage-3 algorithm label (owner decision 101): `tfgrpo-semantic-advantage-v1`, operators update + context_application.

Read: `docs/results/2026-09-23-slurp-stage3-delta-cell-r01-verdict.md`.
