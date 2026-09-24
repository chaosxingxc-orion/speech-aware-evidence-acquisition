# Cell CELL-2 twin read: the derangement twin of the stage3-deltas-v2 store (form control) (the derangement form control; attribution, never admission)

Read 2026-09-24 by the coordinator (Fable 5.1) with `scripts/analysis/plan_cell_read.py` via `scripts/flights/batch/cell2_read.sh twin` (analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-DELTA-CELL-R02-TWIN-PAIRED-ANALYSIS-V1`, score-contrasts sha256 `4e8eb08c4d95c6972f105129523c06d721d1c1d55503bc5bd4d9b8b5d21c9ee8`), and the per-node delta-consumption table with `scripts/analysis/stage3_delta_consumption_read.py`. Comparator = the sealed PLAN arm at the plan's own null (h_SLU 1.2485 / h_intent 0.9943). Model-free: zero model / tokenizer / encoder / server contacts. Development numbers (decisions 28, 86).

## 1. Verdict

| item | result |
| --- | --- |
| status | **twin read: SLU +0.05 [-1.52, +1.62], intent -0.93 [-2.40, +0.41]; arm minus twin +0.59 / +0.83 (descriptive)** |
| driver status | NON-INFERIORITY NOT PROVEN |
| reading | The twin reproduces the arm's form (same 200 values re-attached by a within-node derangement) without its content: SLU +0.05 pp, intent -0.93 pp against the sealed PLAN; the arm sits +0.59 / +0.83 above it, inside the noise band. Attribution only, never admission. |
| cost | contacts / row 4.080 vs 4.096; GPU-h / 1,080 1.712 vs 1.758; contacts / min 40.1 vs 39.9; prefilled tokens / row 8820 vs 8353; cost lower than the base: True |
| trajectory | contacts 4406 (4.080 / row; histogram {'3': 4, '4': 1046, '7': 30}); comparator 4424 (4.096 / row; {'3': 10, '4': 1032, '7': 38}) |
| dispositions | finite stops 4, react exhaustion 0, planner-action-illegal 1, other terminal 3 |

### 1a. The decision rule, as registered (owner decision 99, the TRAIN lock)

Delta = CELL-2 minus the sealed PLAN arm (`SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`), in percentage points.

- **ADMITTED** -- the CI95 lower bound of the paired **official pooled SLU-F1** delta is **above zero** and the CI95 lower bound of the paired **intent** delta exceeds **-0.9943**. A gain is proven, not merely non-inferior.
- **NEUTRAL** -- both guards non-inferior (SLU lower bound above -1.2485, intent lower bound above -0.9943) without a proven SLU gain.
- **HARMFUL** -- a **measured** loss on either guard (owner decision 25, Method B: a CI95 upper bound below zero, or a point estimate beyond the margin). Width alone is NEUTRAL, never HARMFUL.
- **TWIN = attribution, never admission.** A gain the twin reproduces within the plan's own null is **form** -- the store's shape and token volume -- not content, and the verdict says so and claims no content effect. A gain the twin does not reproduce is attributed to the deltas' content, with the twin delta reported beside it.
- **Replication** -- an ADMITTED result is replicated on the **same roster** before any DEV, Fold B or test read. No such read is authorised by this package.

| guard | arm | comparator | delta pp | CI95 | margin | decides |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| official pooled SLU-F1 | 63.68 | 63.63 | +0.05 | [-1.53, +1.51] | 1.2485 | width only |
| intent (joint scenario+action) | 81.30 | 82.22 | -0.93 | [-2.40, +0.41] | 0.9943 | width only |

## 2. Headline contrasts (CELL-2 twin minus PLAN, paired, slurp-stage3-delta-cell-r02-twin-paired-analysis-v1)

| metric | PLAN | arm | delta pp | CI95 (speaker) | CI90 (speaker) | CI90 (scenario-stratified) | equal-scenario delta |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: |
| slu_f1_micro | 63.63 | 63.68 | +0.05 | [-1.53, +1.51] | [-1.28, +1.28] | [-1.31, +1.40] | +0.19 |
| scenario_action_exact | 82.22 | 81.30 | -0.93 | [-2.40, +0.41] | [-2.16, +0.19] | [-1.94, +0.19] | -0.93 |
| span_f1_micro | 53.78 | 53.85 | +0.07 | [-1.75, +1.72] | [-1.44, +1.47] | [-1.40, +1.56] | +0.11 |
| scenario_exact | 87.31 | 85.74 | -1.57 | [-3.25, +0.08] | [-3.00, -0.20] | [-2.69, -0.46] | -1.57 |
| action_exact | 83.52 | 82.50 | -1.02 | [-2.32, +0.25] | [-2.12, +0.00] | [-2.04, +0.00] | -1.02 |
| slu_f1_f1 | 42.25 | 43.25 | +1.01 | [-0.30, +2.25] | [-0.09, +2.07] | [-0.06, +2.10] | +1.01 |
| slot_f1_exact_f1 | 34.99 | 35.83 | +0.84 | [-0.49, +2.05] | [-0.26, +1.86] | [-0.25, +1.96] | +0.84 |

| metric | saves | harms | ties | two-sided McNemar p |
| --- | ---: | ---: | ---: | ---: |
| scenario_action_exact | 20 | 30 | 1030 | 0.2026 |
| scenario_exact | 17 | 34 | 1029 | 0.0241 |
| action_exact | 19 | 30 | 1031 | 0.1524 |
| slu_f1_f1 | 80 | 62 | 938 | 0.1534 |
| slot_f1_exact_f1 | 54 | 46 | 980 | 0.4841 |

Lock comparison (reported, never a gate): see `lock-comparison.json`; projection-v3 and TRAIN-symmetric companions are in `score-contrasts.json`.

## 4. Per scenario (natural mixture and equal-scenario weighting; diagnostics, never gates)

- pooled_slu_f1_equal_scenario_delta_pp: 0.186697118852492
### pooled_slu_f1_per_scenario

| scenario | delta_pp | left_pct | n | right_pct |
| --- | ---: | ---: | ---: | ---: |
| alarm | -7.834 | 76.748 | 60 | 68.913 |
| audio | 17.248 | 48.174 | 60 | 65.422 |
| calendar | 1.536 | 65.639 | 60 | 67.175 |
| cooking | -1.499 | 63.211 | 60 | 61.711 |
| datetime | 5.166 | 73.373 | 60 | 78.540 |
| email | 5.967 | 61.783 | 60 | 67.751 |
| general | -10.229 | 30.229 | 60 | 20.000 |
| iot | -0.864 | 66.368 | 60 | 65.503 |
| lists | 2.745 | 57.454 | 60 | 60.199 |
| music | -2.596 | 48.750 | 60 | 46.154 |
| news | -7.815 | 68.766 | 60 | 60.951 |
| play | -1.684 | 55.388 | 60 | 53.704 |
| qa | -5.096 | 62.649 | 60 | 57.552 |
| recommendation | 3.054 | 66.485 | 60 | 69.540 |
| social | -2.701 | 58.324 | 60 | 55.623 |
| takeaway | 0.969 | 61.793 | 60 | 62.762 |
| transport | 1.359 | 66.680 | 60 | 68.039 |
| weather | 5.635 | 70.838 | 60 | 76.473 |

### pooled_span_f1_per_scenario

| scenario | delta_pp | left_pct | n | right_pct |
| --- | ---: | ---: | ---: | ---: |
| alarm | -5.566 | 68.376 | 60 | 62.810 |
| audio | 16.923 | 23.077 | 60 | 40.000 |
| calendar | 2.106 | 52.439 | 60 | 54.545 |
| cooking | -2.921 | 52.101 | 60 | 49.180 |
| datetime | 6.557 | 59.016 | 60 | 65.574 |
| email | 4.180 | 49.524 | 60 | 53.704 |
| general | -7.451 | 27.451 | 60 | 20.000 |
| iot | -0.426 | 60.000 | 60 | 59.574 |
| lists | 1.502 | 54.054 | 60 | 55.556 |
| music | -2.517 | 46.154 | 60 | 43.636 |
| news | -11.918 | 59.341 | 60 | 47.423 |
| play | -1.667 | 41.322 | 60 | 39.655 |
| qa | -6.464 | 49.057 | 60 | 42.593 |
| recommendation | 2.816 | 59.200 | 60 | 62.016 |
| social | -2.270 | 48.322 | 60 | 46.053 |
| takeaway | -0.559 | 48.611 | 60 | 48.052 |
| transport | 2.101 | 59.627 | 60 | 61.728 |
| weather | 7.534 | 67.133 | 60 | 74.667 |

Intent band: decision-17 flagged scenarios = ['general']; scenarios losing beyond the band = ['general'].

## 5. Frontier row (decision 75)

| cell | official SLU | official intent | GPU-h / 1,080 | contacts / row | prefilled tok / row | on GPU-h frontier | on token frontier |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| CELL-2 | 63.68 | 81.30 | 1.7120 | 4.080 | 8819.9 | False | False |

## 6. Per-node delta consumption (item S3-4s)

Store `stage3-deltas`, release sha256 `b18b141f67dae4b413391d22dd787a3b85480d2b4fab24db0848e547e7aa1a9a`, snapshot `131809122d23ccdaac86c9a9426c5e045a9544fc3059c1b46f80a3365151d614`. Rows 1080; rows that received at least one delta 1080; items supplied 10922; distinct value ids 121; skip events 1652; projection events 60; inert routes none.

| node | cap | rows supplied | share | items | items / supplied row | at full cap | distinct value ids | skip events | rows skipped |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| perception | 4 | 1080 | 1.000 | 4320 | 4.000 | 1080 | 4 | 0 | 0 |
| solver | -- | 812 | 0.752 | 4254 | 5.239 | -- | 75 | 287 | 281 |
| reviewer | 4 | 592 | 0.548 | 1946 | 3.287 | 370 | 38 | 507 | 494 |
| planner | 4 | 248 | 0.230 | 402 | 1.621 | 0 | 4 | 858 | 838 |

| node | rows supplied | SLU saves | SLU harms | SLU neutral | SLU mean delta pp | intent saves | intent harms | intent neutral | intent mean delta pp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| perception | 1080 | 80 | 62 | 938 | +1.008 | 20 | 30 | 1030 | -0.926 |
| solver | 812 | 69 | 43 | 700 | +1.718 | 17 | 27 | 768 | -1.232 |
| reviewer | 592 | 60 | 37 | 495 | +2.141 | 10 | 15 | 567 | -0.845 |
| planner | 248 | 28 | 17 | 203 | +3.322 | 4 | 9 | 235 | -2.016 |

The full per-value-id and per-scenario tables are in `delta-consumption.json` and `delta-consumption.md` in the analysis root. Value ids, node targets and counts only; never statement text.

## 7. Cost

| item | arm | comparator (PLAN) |
| --- | ---: | ---: |
| contacts / row | 4.080 | 4.096 |
| contacts / min | 40.1 | 39.9 |
| prefilled tokens / row | 8820 | 8353 |
| GPU-h / 1,080 rows | 1.7120 | 1.7579 |
| cache hit share | 0.7471 | 0.7545 |
| generation wall seconds | 6805.4 | 6946.0 |

## 8. Caveats

1. The derangement twin is a genuine FORM control on **363 of 379** rows (95.8 %): 16 of the 379 rows landed on a facet set equal to their own by arithmetic, because store revision v1r's vocabulary is 39 distinct intents over 379 rows, and the builder refuses only a twin that moved nothing at all. The twin therefore bounds the form contribution slightly from below; it is reported, not claimed away.
2. The registered worst-case prompt-fit bound puts the **Solver** phase at `COMPACT_REQUIRED` by 317 tokens under this cell's added block (preregistration section 5), so a non-zero compacted-row count is expected and is a caveat on the frontier row's token basis. An abstention caused by compaction would be a failure, not a caveat. Measured on this flight: contacts compacted 0, one receipt per row True, receipt dispositions {'context_compaction_contacts': 0, 'context_compaction_rows': 0, 'finite_completion_rows': 4, 'planner_action_illegal_rows': 1}.
3. **Four launch failures** preceded this flight, metering 320 contacts in total on retired attempts. None of them sealed an output or produced a score, so none of them contributes evidence beyond the harness; the plan budget is run-cumulative across every attempt of a run id, so those contacts count against this cell's registered ceiling.

| attempt | metered contacts | what failed |
| --- | ---: | --- |
| smoke v1, first launch | 0 | refused before any contact in core.flight.runtime._merge_unconditional_first_phase (an unconditional store route repeats a seeded value id); the attempt opened and metered nothing |
| smoke v1, recovery | 4 | the one allowed recovery re-registration was flown and failed; the v1 smoke run id was retired |
| smoke v2 | 12 | died at the openJiuwen vertex reviewer_0_input ('acquire must introduce at least one new value or facet'): a node-filtered candidate-bound route that selected NOTHING still returned a supply. Fixed in rails.knowledge_stores._stage3_delta_local_supply, which now supplies nothing and receipts the skip |
| arm, first attempt | 304 | aborted at solver_0_input on a Perception answer carrying duplicate candidate intent ids ('candidate intent_ids must be unique and ordered'); 73 of 75 rows completed, no output was sealed and no score was produced. Fixed by deriving both readers' parameters from rails.candidate_semantic_supply.candidate_state_read_parameters |

4. Development numbers only (owner decisions 28, 86): TRAIN Fold A is a development roster and no test, Fold B or DEV read is authorised by this verdict. An ADMITTED result is replicated on the SAME roster before any such read.

## 9. Records

No record is closed by the twin read: the twin decides attribution, not admission, and the family's exposure-ledger rows, results-ledger entry and decision-99 outcome are written exactly once, by the arm verdict.

Read: `docs/results/2026-09-24-slurp-stage3-delta-cell-r02-twin-read.md`.
