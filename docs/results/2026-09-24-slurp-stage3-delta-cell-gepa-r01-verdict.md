# Cell CELL-1-GEPA verdict: the locked v2.0 plan plus the per-node stage3-deltas-gepa-v1 store (448 values: 248 curated by the decision-83 frontier rule from the sealed GEPA-R01 reflective proposer contact over 68 (scenario, node) groups of the ROLL-1 trajectories, plus the 200 iteration-1 values decision 83 retained; permitted roster = the ADV-1 disagreeing receipt, the v1r / v2 precedent; Solver 8 / Reviewer 4 / Planner 4 candidate-bound, Perception unconditional 4; label gepa-reflective-pareto-v1, operators update + selection + context_application) (Stage-3 S3-6, the GEPA family arm: the locked v2.0 plan plus the released 448-value stage3-deltas-gepa-v1 store; owner decisions 83, 99, 101, 106)

Read 2026-09-24 by the coordinator (Fable 5.1) with `scripts/analysis/plan_cell_read.py` via `scripts/flights/batch/gepacell_read.sh arm` (analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-PAIRED-ANALYSIS-V1`, score-contrasts sha256 `2a3d9e4fdecc54abb3ede4247805dddf3d0901385285f165fb38ce93970a7bf9`), and the per-node delta-consumption table with `scripts/analysis/stage3_delta_consumption_read.py`. Comparator = the sealed PLAN arm at the plan's own null (h_SLU 1.2485 / h_intent 0.9943). Model-free: zero model / tokenizer / encoder / server contacts. Development numbers (decisions 28, 86).

## 1. Verdict

| item | result |
| --- | --- |
| status | **NEUTRAL by width; NON-INFERIORITY NOT PROVEN on both metrics (no observable gain on TRAIN Fold A; the GEPA family reproduces the Training-Free GRPO family's shape: fuller reach, no pooled effect, the same strata lose)** |
| driver status | NON-INFERIORITY NOT PROVEN |
| reading | Against the sealed PLAN arm the arm reads official pooled SLU-F1 63.60 vs 63.63 (-0.04 pp, CI95 [-1.58, +1.39]) and intent 82.13 vs 82.22 (-0.09 pp, CI95 [-1.54, +1.32]); both guards fail by width only, with intervals wider than CELL-2's. The derangement twin reads 62.87 (-0.76, CI95 [-2.39, +0.76]) and 81.94 (-0.28, CI95 [-1.51, +0.89]); arm minus twin is +0.73 pp SLU and +0.19 pp intent (descriptive): the GEPA content sits slightly above its own form control, inside the noise band. Reach is far fuller than the v2 store's (299 of 448 values supplied; Solver 93 %, Reviewer 91 %, Planner 90 % of rows against 68 / 64 / 18 %) at a higher cost (prefilled tokens +14 %, GPU-h +6 %, 4.17 contacts per row), and it buys no pooled effect. The per-scenario table has the same shape as both TF-GRPO cells: general -9.4 SLU / -8.3 intent (twin -18.7 / -5.0), news -6.3, social -4.4, music -4.2 against audio +7.0 / +6.7, weather +7.8, datetime +4.7, iot +3.7. Against the Stage-2 lock B5e official the arm is +1.26 SLU [-0.22, +2.78] and +2.04 intent [+0.49, +3.54]. Two families with different authoring mechanisms (per-row advantage statements; per-group reflective proposals) reproduce one pattern: strata the store covers gain, strata it does not cover pay a form cost, the pool nets to zero -- the lever is WHERE the store is applied (iteration 3, provisional decision 110, the scenario-gated application policy now flying as CELL-3 on DEV-2000-ADDED), not which family authored it. Comparing GEPA against Training-Free GRPO head to head is a separate read with its own preregistration and is not made here. |
| cost | contacts / row 4.174 vs 4.096; GPU-h / 1,080 1.863 vs 1.758; contacts / min 38.3 vs 39.9; prefilled tokens / row 9536 vs 8353; cost lower than the base: False |
| trajectory | contacts 4508 (4.174 / row; histogram {'3': 10, '4': 1004, '7': 66}); comparator 4424 (4.096 / row; {'3': 10, '4': 1032, '7': 38}) |
| dispositions | finite stops 10, react exhaustion 0, planner-action-illegal 0, other terminal 7 |

### 1a. The decision rule, as registered (owner decision 99, the TRAIN lock)

Delta = CELL-1-GEPA minus the sealed PLAN arm (`SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`), in percentage points.

- **ADMITTED** -- the CI95 lower bound of the paired **official pooled SLU-F1** delta is **above zero** and the CI95 lower bound of the paired **intent** delta exceeds **-0.9943**. A gain is proven, not merely non-inferior.
- **NEUTRAL** -- both guards non-inferior (SLU lower bound above -1.2485, intent lower bound above -0.9943) without a proven SLU gain.
- **HARMFUL** -- a **measured** loss on either guard (owner decision 25, Method B: a CI95 upper bound below zero, or a point estimate beyond the margin). Width alone is NEUTRAL, never HARMFUL.
- **TWIN = attribution, never admission.** A gain the twin reproduces within the plan's own null is **form** -- the store's shape and token volume -- not content, and the verdict says so and claims no content effect. A gain the twin does not reproduce is attributed to the deltas' content, with the twin delta reported beside it.
- **Replication** -- an ADMITTED result is replicated on the **same roster** before any DEV, Fold B or test read. No such read is authorised by this package.

| guard | arm | comparator | delta pp | CI95 | margin | decides |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| official pooled SLU-F1 | 63.60 | 63.63 | -0.04 | [-1.58, +1.39] | 1.2485 | width only |
| intent (joint scenario+action) | 82.13 | 82.22 | -0.09 | [-1.54, +1.32] | 0.9943 | width only |

## 2. Headline contrasts (CELL-1-GEPA minus PLAN, paired, slurp-stage3-delta-cell-gepa-r01-arm-paired-analysis-v1)

| metric | PLAN | arm | delta pp | CI95 (speaker) | CI90 (speaker) | CI90 (scenario-stratified) | equal-scenario delta |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: |
| slu_f1_micro | 63.63 | 63.60 | -0.04 | [-1.58, +1.39] | [-1.33, +1.16] | [-1.41, +1.34] | -0.37 |
| scenario_action_exact | 82.22 | 82.13 | -0.09 | [-1.54, +1.32] | [-1.32, +1.08] | [-1.11, +0.93] | -0.09 |
| span_f1_micro | 53.78 | 53.60 | -0.18 | [-2.06, +1.52] | [-1.74, +1.25] | [-1.78, +1.44] | +0.05 |
| scenario_exact | 87.31 | 86.94 | -0.37 | [-1.81, +0.99] | [-1.59, +0.77] | [-1.39, +0.65] | -0.37 |
| action_exact | 83.52 | 83.33 | -0.19 | [-1.55, +1.23] | [-1.33, +0.99] | [-1.20, +0.83] | -0.19 |
| slu_f1_f1 | 42.25 | 42.78 | +0.53 | [-0.68, +1.70] | [-0.46, +1.49] | [-0.55, +1.59] | +0.53 |
| slot_f1_exact_f1 | 34.99 | 35.44 | +0.44 | [-0.83, +1.60] | [-0.62, +1.43] | [-0.71, +1.61] | +0.44 |

| metric | saves | harms | ties | two-sided McNemar p |
| --- | ---: | ---: | ---: | ---: |
| scenario_action_exact | 23 | 24 | 1033 | 1.0000 |
| scenario_exact | 21 | 25 | 1034 | 0.6587 |
| action_exact | 22 | 24 | 1034 | 0.8830 |
| slu_f1_f1 | 80 | 73 | 927 | 0.6278 |
| slot_f1_exact_f1 | 59 | 53 | 968 | 0.6368 |

Lock comparison (reported, never a gate): see `lock-comparison.json`; projection-v3 and TRAIN-symmetric companions are in `score-contrasts.json`.

## 3. The derangement twin (form control) and the content attribution

Twin analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-TWIN-PAIRED-ANALYSIS-V1`, score-contrasts sha256 `aca873af1a65060d5760ce08c7ff594b229413b03fb90d1c9dd50297b038e783`. Same comparator, same margins, same estimator, same seed: the twin read is the arm read with one input changed.

| metric | arm delta pp | arm CI95 | twin delta pp | twin CI95 | arm minus twin pp |
| --- | ---: | --- | ---: | --- | ---: |
| slu_f1_micro | -0.04 | [-1.58, +1.39] | -0.76 | [-2.39, +0.76] | +0.73 |
| scenario_action_exact | -0.09 | [-1.54, +1.32] | -0.28 | [-1.51, +0.89] | +0.19 |
| span_f1_micro | -0.18 | [-2.06, +1.52] | -0.68 | [-2.57, +1.03] | +0.50 |

**The arm-minus-twin column is DESCRIPTIVE.** It is the difference of two point estimates, each against the same sealed PLAN arm; no interval is computed for it and no test is run on it. It bounds how much of the arm's movement the store's shape and token volume alone can account for. The twin decides attribution, never admission (decision 99).

The derangement twin is a genuine FORM control on **363 of 379** rows (95.8 %): 16 of the 379 rows landed on a facet set equal to their own by arithmetic, because store revision v1r's vocabulary is 39 distinct intents over 379 rows, and the builder refuses only a twin that moved nothing at all. The twin therefore bounds the form contribution slightly from below; it is reported, not claimed away.

## 4. Per scenario (natural mixture and equal-scenario weighting; diagnostics, never gates)

- pooled_slu_f1_equal_scenario_delta_pp: -0.3722183830029145
### pooled_slu_f1_per_scenario

| scenario | delta_pp | left_pct | n | right_pct |
| --- | ---: | ---: | ---: | ---: |
| alarm | 0.266 | 76.748 | 60 | 77.014 |
| audio | 7.033 | 48.174 | 60 | 55.207 |
| calendar | 1.775 | 65.639 | 60 | 67.414 |
| cooking | -1.547 | 63.211 | 60 | 61.664 |
| datetime | 4.721 | 73.373 | 60 | 78.094 |
| email | 1.383 | 61.783 | 60 | 63.166 |
| general | -9.396 | 30.229 | 60 | 20.833 |
| iot | 3.666 | 66.368 | 60 | 70.034 |
| lists | -2.612 | 57.454 | 60 | 54.842 |
| music | -4.179 | 48.750 | 60 | 44.571 |
| news | -6.300 | 68.766 | 60 | 62.466 |
| play | -2.259 | 55.388 | 60 | 53.129 |
| qa | -0.982 | 62.649 | 60 | 61.667 |
| recommendation | -1.064 | 66.485 | 60 | 65.421 |
| social | -4.393 | 58.324 | 60 | 53.931 |
| takeaway | -1.832 | 61.793 | 60 | 59.961 |
| transport | 1.213 | 66.680 | 60 | 67.893 |
| weather | 7.806 | 70.838 | 60 | 78.644 |

### pooled_span_f1_per_scenario

| scenario | delta_pp | left_pct | n | right_pct |
| --- | ---: | ---: | ---: | ---: |
| alarm | 2.314 | 68.376 | 60 | 70.690 |
| audio | 18.590 | 23.077 | 60 | 41.667 |
| calendar | 0.647 | 52.439 | 60 | 53.086 |
| cooking | -2.101 | 52.101 | 60 | 50.000 |
| datetime | 6.024 | 59.016 | 60 | 65.041 |
| email | 0.000 | 49.524 | 60 | 49.524 |
| general | -6.618 | 27.451 | 60 | 20.833 |
| iot | 4.583 | 60.000 | 60 | 64.583 |
| lists | -2.703 | 54.054 | 60 | 51.351 |
| music | -4.049 | 46.154 | 60 | 42.105 |
| news | -9.341 | 59.341 | 60 | 50.000 |
| play | -2.339 | 41.322 | 60 | 38.983 |
| qa | -2.760 | 49.057 | 60 | 46.296 |
| recommendation | -2.711 | 59.200 | 60 | 56.489 |
| social | -6.989 | 48.322 | 60 | 41.333 |
| takeaway | -2.751 | 48.611 | 60 | 45.860 |
| transport | 2.398 | 59.627 | 60 | 62.025 |
| weather | 8.684 | 67.133 | 60 | 75.817 |

Intent band: decision-17 flagged scenarios = ['general']; scenarios losing beyond the band = [].

## 5. Frontier row (decision 75)

| cell | official SLU | official intent | GPU-h / 1,080 | contacts / row | prefilled tok / row | on GPU-h frontier | on token frontier |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| CELL-1-GEPA | 63.60 | 82.13 | 1.8628 | 4.174 | 9535.5 | False | False |
| CELL-1-GEPA twin | 62.87 | 81.94 | 1.8912 | 4.137 | 9516.1 | False | False |

## 6. Per-node delta consumption (item S3-4s)

Store `stage3-deltas`, release sha256 `53c1267169b5269bc850f75527b2c8086fd681126f9180ac4a0df9410b61fcfa`, snapshot `560d84e7e6364de5ce09635f586660d22b9a103734c51dbd64e6182599fb935c`. Rows 1080; rows that received at least one delta 1080; items supplied 19071; distinct value ids 299; skip events 348; projection events 75; inert routes none.

| node | cap | rows supplied | share | items | items / supplied row | at full cap | distinct value ids | skip events | rows skipped |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| perception | 4 | 1080 | 1.000 | 4320 | 4.000 | 1080 | 4 | 0 | 0 |
| solver | -- | 1005 | 0.931 | 6880 | 6.846 | -- | 137 | 106 | 102 |
| reviewer | 4 | 978 | 0.906 | 3871 | 3.958 | 867 | 83 | 127 | 123 |
| planner | 4 | 968 | 0.896 | 4000 | 4.132 | 902 | 75 | 115 | 111 |

| node | rows supplied | SLU saves | SLU harms | SLU neutral | SLU mean delta pp | intent saves | intent harms | intent neutral | intent mean delta pp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| perception | 1080 | 80 | 73 | 927 | +0.529 | 23 | 24 | 1033 | -0.093 |
| solver | 1005 | 77 | 70 | 858 | +0.563 | 23 | 23 | 959 | +0.000 |
| reviewer | 978 | 77 | 69 | 832 | +0.629 | 23 | 23 | 932 | +0.000 |
| planner | 968 | 75 | 69 | 824 | +0.579 | 23 | 22 | 923 | +0.103 |

### 6a. Arm versus twin supplied volume

| node | arm rows supplied | twin rows supplied | arm items | twin items | arm distinct value ids | twin distinct value ids |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| perception | 1080 | 1080 | 4320 | 4320 | 4 | 4 |
| solver | 1005 | 1008 | 6880 | 7399 | 137 | 133 |
| reviewer | 978 | 1008 | 3871 | 3910 | 83 | 87 |
| planner | 968 | 976 | 4000 | 3342 | 75 | 73 |

The derangement holds the store's TOTAL token count, not the SUPPLIED token count: a twin that supplies materially more or less than the arm is a weaker form control, and this table is where that is read rather than assumed.

The full per-value-id and per-scenario tables are in `delta-consumption.json` and `delta-consumption.md` in the analysis root. Value ids, node targets and counts only; never statement text.

## 7. Cost

| item | arm | comparator (PLAN) |
| --- | ---: | ---: |
| contacts / row | 4.174 | 4.096 |
| contacts / min | 38.3 | 39.9 |
| prefilled tokens / row | 9536 | 8353 |
| GPU-h / 1,080 rows | 1.8628 | 1.7579 |
| cache hit share | 0.7393 | 0.7545 |
| generation wall seconds | 7296.8 | 6946.0 |

## 8. Caveats

1. The derangement twin is a genuine FORM control on **363 of 379** rows (95.8 %): 16 of the 379 rows landed on a facet set equal to their own by arithmetic, because store revision v1r's vocabulary is 39 distinct intents over 379 rows, and the builder refuses only a twin that moved nothing at all. The twin therefore bounds the form contribution slightly from below; it is reported, not claimed away.
2. The registered worst-case prompt-fit bound puts the **Solver** phase at `COMPACT_REQUIRED` by 317 tokens under this cell's added block (preregistration section 5), so a non-zero compacted-row count is expected and is a caveat on the frontier row's token basis. An abstention caused by compaction would be a failure, not a caveat. Measured on this flight: contacts compacted 0, one receipt per row True, receipt dispositions {'context_compaction_contacts': 0, 'context_compaction_rows': 0, 'finite_completion_rows': 10, 'planner_action_illegal_rows': 0}.
3. **Four launch failures** preceded this flight, metering 320 contacts in total on retired attempts. None of them sealed an output or produced a score, so none of them contributes evidence beyond the harness; the plan budget is run-cumulative across every attempt of a run id, so those contacts count against this cell's registered ceiling.

| attempt | metered contacts | what failed |
| --- | ---: | --- |
| smoke v1, first launch | 0 | refused before any contact in core.flight.runtime._merge_unconditional_first_phase (an unconditional store route repeats a seeded value id); the attempt opened and metered nothing |
| smoke v1, recovery | 4 | the one allowed recovery re-registration was flown and failed; the v1 smoke run id was retired |
| smoke v2 | 12 | died at the openJiuwen vertex reviewer_0_input ('acquire must introduce at least one new value or facet'): a node-filtered candidate-bound route that selected NOTHING still returned a supply. Fixed in rails.knowledge_stores._stage3_delta_local_supply, which now supplies nothing and receipts the skip |
| arm, first attempt | 304 | aborted at solver_0_input on a Perception answer carrying duplicate candidate intent ids ('candidate intent_ids must be unique and ordered'); 73 of 75 rows completed, no output was sealed and no score was produced. Fixed by deriving both readers' parameters from rails.candidate_semantic_supply.candidate_state_read_parameters |

4. Development numbers only (owner decisions 28, 86): TRAIN Fold A is a development roster and no test, Fold B or DEV read is authorised by this verdict. An ADMITTED result is replicated on the SAME roster before any such read.

## 9. Records

Exposure-ledger rows closed (the `SAEA-SLURP-STAGE3-DELTA-CELL-*` family still open, never the retired v1 / v2 smoke rows), flight commit 194d4b42, 2026-09-24T08:16-12:43 UTC (smoke 08:16-08:18, arm 08:18-10:25; the two-step chain STOPPED cold at the step-2 GPU ramp preflight, 9.8 TFLOP/s, no twin attempt opened; twin-only relaunch SAEA-Batch-Chain-GEPACELL-TWIN: twin smoke 10:28-10:30, twin 10:30-12:42; flight commit 194d4b42); results-ledger entry; decision-99 outcome appended. Stage-3 algorithm label (owner decision 101): `tfgrpo-semantic-advantage-v1`, operators update + context_application.

Read: `docs/results/2026-09-24-slurp-stage3-delta-cell-gepa-r01-verdict.md`.
