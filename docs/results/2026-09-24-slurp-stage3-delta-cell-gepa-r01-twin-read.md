# Cell CELL-1-GEPA twin read: the derangement twin of the stage3-deltas-gepa-v1 store (form control) (the derangement form control; attribution, never admission)

Read 2026-09-24 by the coordinator (Fable 5.1) with `scripts/analysis/plan_cell_read.py` via `scripts/flights/batch/gepacell_read.sh twin` (analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-TWIN-PAIRED-ANALYSIS-V1`, score-contrasts sha256 `aca873af1a65060d5760ce08c7ff594b229413b03fb90d1c9dd50297b038e783`), and the per-node delta-consumption table with `scripts/analysis/stage3_delta_consumption_read.py`. Comparator = the sealed PLAN arm at the plan's own null (h_SLU 1.2485 / h_intent 0.9943). Model-free: zero model / tokenizer / encoder / server contacts. Development numbers (decisions 28, 86).

## 1. Verdict

| item | result |
| --- | --- |
| status | **twin read: SLU -0.76 [-2.39, +0.76], intent -0.28 [-1.51, +0.89]; arm minus twin +0.73 / +0.19 (descriptive)** |
| driver status | NON-INFERIORITY NOT PROVEN |
| reading | The twin reproduces the arm's form (the same 448 values re-attached by a within-node derangement) without its content: SLU -0.76 pp, intent -0.28 pp against the sealed PLAN; general -18.7 pp SLU on the twin against -9.4 on the arm, the form cost of carrying a supply on a stratum the store does not cover. Attribution only, never admission. |
| cost | contacts / row 4.137 vs 4.096; GPU-h / 1,080 1.891 vs 1.758; contacts / min 38.1 vs 39.9; prefilled tokens / row 9516 vs 8353; cost lower than the base: False |
| trajectory | contacts 4468 (4.137 / row; histogram {'3': 5, '4': 1024, '7': 51}); comparator 4424 (4.096 / row; {'3': 10, '4': 1032, '7': 38}) |
| dispositions | finite stops 5, react exhaustion 0, planner-action-illegal 2, other terminal 6 |

### 1a. The decision rule, as registered (owner decision 99, the TRAIN lock)

Delta = CELL-1-GEPA minus the sealed PLAN arm (`SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`), in percentage points.

- **ADMITTED** -- the CI95 lower bound of the paired **official pooled SLU-F1** delta is **above zero** and the CI95 lower bound of the paired **intent** delta exceeds **-0.9943**. A gain is proven, not merely non-inferior.
- **NEUTRAL** -- both guards non-inferior (SLU lower bound above -1.2485, intent lower bound above -0.9943) without a proven SLU gain.
- **HARMFUL** -- a **measured** loss on either guard (owner decision 25, Method B: a CI95 upper bound below zero, or a point estimate beyond the margin). Width alone is NEUTRAL, never HARMFUL.
- **TWIN = attribution, never admission.** A gain the twin reproduces within the plan's own null is **form** -- the store's shape and token volume -- not content, and the verdict says so and claims no content effect. A gain the twin does not reproduce is attributed to the deltas' content, with the twin delta reported beside it.
- **Replication** -- an ADMITTED result is replicated on the **same roster** before any DEV, Fold B or test read. No such read is authorised by this package.

| guard | arm | comparator | delta pp | CI95 | margin | decides |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| official pooled SLU-F1 | 62.87 | 63.63 | -0.76 | [-2.39, +0.76] | 1.2485 | width only |
| intent (joint scenario+action) | 81.94 | 82.22 | -0.28 | [-1.51, +0.89] | 0.9943 | width only |

## 2. Headline contrasts (CELL-1-GEPA twin minus PLAN, paired, slurp-stage3-delta-cell-gepa-r01-twin-paired-analysis-v1)

| metric | PLAN | arm | delta pp | CI95 (speaker) | CI90 (speaker) | CI90 (scenario-stratified) | equal-scenario delta |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: |
| slu_f1_micro | 63.63 | 62.87 | -0.76 | [-2.39, +0.76] | [-2.12, +0.50] | [-2.11, +0.58] | -1.65 |
| scenario_action_exact | 82.22 | 81.94 | -0.28 | [-1.51, +0.89] | [-1.31, +0.71] | [-1.20, +0.65] | -0.28 |
| span_f1_micro | 53.78 | 53.10 | -0.68 | [-2.57, +1.03] | [-2.22, +0.77] | [-2.20, +0.83] | -1.39 |
| scenario_exact | 87.31 | 86.94 | -0.37 | [-1.72, +0.96] | [-1.52, +0.75] | [-1.30, +0.56] | -0.37 |
| action_exact | 83.52 | 83.06 | -0.46 | [-1.63, +0.68] | [-1.43, +0.51] | [-1.39, +0.46] | -0.46 |
| slu_f1_f1 | 42.25 | 42.55 | +0.31 | [-1.01, +1.65] | [-0.81, +1.43] | [-0.79, +1.40] | +0.31 |
| slot_f1_exact_f1 | 34.99 | 35.31 | +0.32 | [-1.14, +1.71] | [-0.89, +1.47] | [-0.80, +1.48] | +0.32 |

| metric | saves | harms | ties | two-sided McNemar p |
| --- | ---: | ---: | ---: | ---: |
| scenario_action_exact | 18 | 21 | 1041 | 0.7493 |
| scenario_exact | 18 | 22 | 1040 | 0.6358 |
| action_exact | 17 | 22 | 1041 | 0.5224 |
| slu_f1_f1 | 70 | 73 | 937 | 0.8672 |
| slot_f1_exact_f1 | 51 | 50 | 979 | 1.0000 |

Lock comparison (reported, never a gate): see `lock-comparison.json`; projection-v3 and TRAIN-symmetric companions are in `score-contrasts.json`.

## 4. Per scenario (natural mixture and equal-scenario weighting; diagnostics, never gates)

- pooled_slu_f1_equal_scenario_delta_pp: -1.6528917924501938
### pooled_slu_f1_per_scenario

| scenario | delta_pp | left_pct | n | right_pct |
| --- | ---: | ---: | ---: | ---: |
| alarm | -1.185 | 76.748 | 60 | 75.563 |
| audio | 2.598 | 48.174 | 60 | 50.772 |
| calendar | 2.243 | 65.639 | 60 | 67.882 |
| cooking | 2.588 | 63.211 | 60 | 65.798 |
| datetime | -1.616 | 73.373 | 60 | 71.757 |
| email | 4.757 | 61.783 | 60 | 66.540 |
| general | -18.691 | 30.229 | 60 | 11.538 |
| iot | -3.935 | 66.368 | 60 | 62.432 |
| lists | -3.571 | 57.454 | 60 | 53.883 |
| music | -3.401 | 48.750 | 60 | 45.349 |
| news | -4.834 | 68.766 | 60 | 63.932 |
| play | -6.562 | 55.388 | 60 | 48.826 |
| qa | -1.148 | 62.649 | 60 | 61.501 |
| recommendation | 2.199 | 66.485 | 60 | 68.684 |
| social | -2.270 | 58.324 | 60 | 56.053 |
| takeaway | 0.965 | 61.793 | 60 | 62.758 |
| transport | -0.885 | 66.680 | 60 | 65.795 |
| weather | 2.997 | 70.838 | 60 | 73.835 |

### pooled_span_f1_per_scenario

| scenario | delta_pp | left_pct | n | right_pct |
| --- | ---: | ---: | ---: | ---: |
| alarm | 1.115 | 68.376 | 60 | 69.492 |
| audio | 4.509 | 23.077 | 60 | 27.586 |
| calendar | 2.219 | 52.439 | 60 | 54.658 |
| cooking | 1.998 | 52.101 | 60 | 54.098 |
| datetime | -0.749 | 59.016 | 60 | 58.268 |
| email | 2.813 | 49.524 | 60 | 52.336 |
| general | -15.913 | 27.451 | 60 | 11.538 |
| iot | -3.158 | 60.000 | 60 | 56.842 |
| lists | -4.054 | 54.054 | 60 | 50.000 |
| music | -3.297 | 46.154 | 60 | 42.857 |
| news | -7.794 | 59.341 | 60 | 51.546 |
| play | -6.540 | 41.322 | 60 | 34.783 |
| qa | -2.760 | 49.057 | 60 | 46.296 |
| recommendation | 3.300 | 59.200 | 60 | 62.500 |
| social | -1.426 | 48.322 | 60 | 46.897 |
| takeaway | 0.396 | 48.611 | 60 | 49.007 |
| transport | 0.750 | 59.627 | 60 | 60.377 |
| weather | 3.615 | 67.133 | 60 | 70.748 |

Intent band: decision-17 flagged scenarios = []; scenarios losing beyond the band = [].

## 5. Frontier row (decision 75)

| cell | official SLU | official intent | GPU-h / 1,080 | contacts / row | prefilled tok / row | on GPU-h frontier | on token frontier |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| CELL-1-GEPA | 62.87 | 81.94 | 1.8912 | 4.137 | 9516.1 | False | False |

## 6. Per-node delta consumption (item S3-4s)

Store `stage3-deltas`, release sha256 `fb2dad3082848f1ff794401f2ea1d9b0d53e33b0f7a459592b44364cce196fb3`, snapshot `f19671d381f82ffb07f7d186b93c45adfe129bcf934e62011abdec1744123ffe`. Rows 1080; rows that received at least one delta 1080; items supplied 18971; distinct value ids 297; skip events 298; projection events 66; inert routes none.

| node | cap | rows supplied | share | items | items / supplied row | at full cap | distinct value ids | skip events | rows skipped |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| perception | 4 | 1080 | 1.000 | 4320 | 4.000 | 1080 | 4 | 0 | 0 |
| solver | -- | 1008 | 0.933 | 7399 | 7.340 | -- | 133 | 92 | 90 |
| reviewer | 4 | 1008 | 0.933 | 3910 | 3.879 | 823 | 87 | 85 | 83 |
| planner | 4 | 976 | 0.904 | 3342 | 3.424 | 639 | 73 | 121 | 119 |

| node | rows supplied | SLU saves | SLU harms | SLU neutral | SLU mean delta pp | intent saves | intent harms | intent neutral | intent mean delta pp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| perception | 1080 | 70 | 73 | 937 | +0.307 | 18 | 21 | 1041 | -0.278 |
| solver | 1008 | 67 | 69 | 872 | +0.320 | 18 | 21 | 969 | -0.298 |
| reviewer | 1008 | 67 | 69 | 872 | +0.320 | 18 | 21 | 969 | -0.298 |
| planner | 976 | 67 | 68 | 841 | +0.433 | 18 | 21 | 937 | -0.307 |

The full per-value-id and per-scenario tables are in `delta-consumption.json` and `delta-consumption.md` in the analysis root. Value ids, node targets and counts only; never statement text.

## 7. Cost

| item | arm | comparator (PLAN) |
| --- | ---: | ---: |
| contacts / row | 4.137 | 4.096 |
| contacts / min | 38.1 | 39.9 |
| prefilled tokens / row | 9516 | 8353 |
| GPU-h / 1,080 rows | 1.8912 | 1.7579 |
| cache hit share | 0.7375 | 0.7545 |
| generation wall seconds | 7337.0 | 6946.0 |

## 8. Caveats

1. The derangement twin is a genuine FORM control on **363 of 379** rows (95.8 %): 16 of the 379 rows landed on a facet set equal to their own by arithmetic, because store revision v1r's vocabulary is 39 distinct intents over 379 rows, and the builder refuses only a twin that moved nothing at all. The twin therefore bounds the form contribution slightly from below; it is reported, not claimed away.
2. The registered worst-case prompt-fit bound puts the **Solver** phase at `COMPACT_REQUIRED` by 317 tokens under this cell's added block (preregistration section 5), so a non-zero compacted-row count is expected and is a caveat on the frontier row's token basis. An abstention caused by compaction would be a failure, not a caveat. Measured on this flight: contacts compacted 0, one receipt per row True, receipt dispositions {'context_compaction_contacts': 0, 'context_compaction_rows': 0, 'finite_completion_rows': 5, 'planner_action_illegal_rows': 2}.
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

Read: `docs/results/2026-09-24-slurp-stage3-delta-cell-gepa-r01-twin-read.md`.
