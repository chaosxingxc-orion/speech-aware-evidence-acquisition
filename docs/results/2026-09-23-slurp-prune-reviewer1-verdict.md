# Cell P1 verdict: Reviewer 3 -> 1 (native_episode.roles.reviewer.max_iterations) (owner decision 85, on the measurable-Reviewer base R-PRIM, decision 97)

Read 2026-09-23 by the coordinator (Fable 5.1) with `scripts/analysis/plan_cell_read.py` via `scripts/flights/batch/prune_read.sh prune-reviewer1` (analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-PRUNE-REVIEWER1-PAIRED-ANALYSIS-V1`, score-contrasts sha256 `b689f98bd7424511974bb15f9a903da6683bf955da412c21bd433780efab0a03`). Comparator = the sealed R-PRIM arm at the plan's own null (h_SLU 1.2485 / h_intent 0.9943). Model-free: zero model / tokenizer / encoder / server contacts. Development numbers (decisions 28, 86).

## 1. Verdict

| item | result |
| --- | --- |
| status | **NEUTRAL (non-inferiority NOT PROVEN on SLU by width, not by loss): SLU -0.15 pp [-1.38, +1.24] misses the margin 1.2485 by 0.13 pp of CI width, intent +0.09 pp [-0.69, +0.90] non-inferior** |
| reading | The factor is nearly a no-op on this base: the R-PRIM Reviewer already used one visit per row on 1,069 of 1,080 rows (its max_iterations 3 was never drawn), so P1 removes at most the second Reviewer contact of 11 rows; contacts per row 4.017 vs 4.031, GPU-h 1.38 vs 1.57 (throughput noise, not a budget saving). The review-budget question is answered by P0 (review-off), not by P1. Decision 97 stands: not HARMFUL. |
| cost | contacts / row 4.017 vs 4.031; GPU-h / 1,080 1.383 vs 1.569; contacts / min 47.8 vs 44.2; prefilled tokens / row 8302 vs 8346; cost lower than the base: True |
| trajectory | contacts 4338 (4.017 / row; histogram {'4': 1074, '7': 6}; reviewer contacts per row {'1': 1074, '2': 6}); comparator 4353 (4.031 / row; {'4': 1069, '7': 11}) |
| dispositions | finite stops 0, planner-action-illegal 0, other terminal 0 |

## 2. Headline contrasts (P1 minus R-PRIM, paired, 10,000 draws, seed 20260915)

| metric | R-PRIM | P1 | delta pp | CI95 |
| --- | ---: | ---: | ---: | --- |

Lock comparison (reported, never a gate): see `lock-comparison.json`; projection-v3 and TRAIN-symmetric companions are in `score-contrasts.json`.

## 3. Per-scenario (natural mixture and equal-scenario weighting; diagnostics, never gates)

- pooled_slu_f1_equal_scenario_delta_pp: 0.233982234903903
### pooled_slu_f1_per_scenario

| scenario | delta_pp | left_pct | n | right_pct |
| --- | ---: | ---: | ---: | ---: |
| alarm | -1.050 | 74.905 | 60 | 73.856 |
| audio | 1.178 | 67.889 | 60 | 69.068 |
| calendar | -2.485 | 67.390 | 60 | 64.905 |
| cooking | 0.335 | 63.503 | 60 | 63.838 |
| datetime | -1.469 | 76.631 | 60 | 75.162 |
| email | -2.091 | 64.634 | 60 | 62.544 |
| general | 1.778 | 22.222 | 60 | 24.000 |
| iot | 3.385 | 64.967 | 60 | 68.352 |
| lists | 1.541 | 57.454 | 60 | 58.994 |
| music | 1.408 | 48.273 | 60 | 49.682 |
| news | 1.914 | 64.604 | 60 | 66.518 |
| play | -1.037 | 56.890 | 60 | 55.853 |
| qa | -0.811 | 60.640 | 60 | 59.829 |
| recommendation | 0.083 | 69.453 | 60 | 69.536 |
| social | -2.854 | 59.944 | 60 | 57.089 |
| takeaway | 6.356 | 54.330 | 60 | 60.686 |
| transport | 0.628 | 65.587 | 60 | 66.215 |
| weather | -2.599 | 79.285 | 60 | 76.687 |

### pooled_span_f1_per_scenario

| scenario | delta_pp | left_pct | n | right_pct |
| --- | ---: | ---: | ---: | ---: |
| alarm | -0.580 | 66.667 | 60 | 66.087 |
| audio | 1.812 | 41.667 | 60 | 43.478 |
| calendar | -0.977 | 53.416 | 60 | 52.439 |
| cooking | 1.612 | 50.847 | 60 | 52.459 |
| datetime | -1.538 | 61.538 | 60 | 60.000 |
| email | -0.908 | 51.852 | 60 | 50.943 |
| general | 1.778 | 22.222 | 60 | 24.000 |
| iot | 4.494 | 58.427 | 60 | 62.921 |
| lists | 1.502 | 54.054 | 60 | 55.556 |
| music | 4.751 | 42.308 | 60 | 47.059 |
| news | -0.611 | 55.556 | 60 | 54.945 |
| play | 2.121 | 41.739 | 60 | 43.860 |
| qa | 0.172 | 45.283 | 60 | 45.455 |
| recommendation | -0.093 | 62.903 | 60 | 62.810 |
| social | -2.685 | 49.664 | 60 | 46.980 |
| takeaway | 5.240 | 38.298 | 60 | 43.537 |
| transport | 1.009 | 58.385 | 60 | 59.394 |
| weather | -2.861 | 74.483 | 60 | 71.622 |

Intent band: decision-17 flagged scenarios = [].

## 4. Frontier row (decision 75)

| cell | official SLU | official intent | GPU-h / 1,080 | contacts / row | prefilled tok / row | on GPU-h frontier | on token frontier |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| P1 | 64.06 | 82.22 | 1.3829 | 4.017 | 8302.5 | True | True |

## 5. Records

Four exposure-ledger rows closed (SAEA-SLURP-NATIVE-PRUNE-REVIEWER1-{SMOKE-4-,SMOKE-4-FIT-,,FIT-}V1, flight commit 1e349630, 2026-09-22T23:10 to 2026-09-23T00:49 UTC); results-ledger entry; decision-85 outcome appended. Stage-3 algorithm label: none (decision 101).
