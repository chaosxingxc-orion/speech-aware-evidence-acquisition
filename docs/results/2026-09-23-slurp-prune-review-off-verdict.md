# Cell P0 verdict: review-off (Reviewer 0, Planner 0, no revision: Perception -> Solver -> Delivery, the item-E1 / cell-B0 form) (owner decision 85, on the measurable-Reviewer base R-PRIM, decision 97)

Read 2026-09-23 by the coordinator (Fable 5.1) with `scripts/analysis/plan_cell_read.py` via `scripts/flights/batch/prune_read.sh prune-review-off` (analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-PRUNE-REVIEW-OFF-PAIRED-ANALYSIS-V1`, score-contrasts sha256 `c726e45d52bf7516f93cf8e6d9e056769e0ae7d2b486f53c7ff032db365b0411`). Comparator = the sealed R-PRIM arm at the plan's own null (h_SLU 1.2485 / h_intent 0.9943). Model-free: zero model / tokenizer / encoder / server contacts. Development numbers (decisions 28, 86).

## 1. Verdict

| item | result |
| --- | --- |
| status | **NEUTRAL (non-inferiority NOT PROVEN on both metrics by width, not by measured loss): SLU -0.36 pp [-1.45, +0.78] vs margin 1.2485; intent -0.56 pp [-1.60, +0.52] vs margin 0.9943; no CI95 upper bound below zero, no point estimate beyond a margin (decision 25 Method B)** |
| reading | Removing the review loop halves the contacts (2.00 vs 4.03 per row, prefilled tokens 7,802 vs 8,346, GPU-h 1.26 vs 1.57) and costs at most -0.36 SLU / -0.56 intent by point estimate, unproven in either direction at this width; the locked plan keeps its Reviewer + Planner (decision 85 admits a pruning only on a proven non-inferior read), and a request-identical replicate would be needed to narrow the interval before any plan change. Together with P1 (no-op) and R-PRIM (98.4 % ACCEPT, recall 0.017), the review loop on the locked plan is a 2-contact-per-row insurance whose measurable value is within the null band. |
| cost | contacts / row 2.000 vs 4.031; GPU-h / 1,080 1.256 vs 1.569; contacts / min 26.1 vs 44.2; prefilled tokens / row 7802 vs 8346; cost lower than the base: True |
| trajectory | contacts 2160 (2.000 / row; histogram {'2': 1080}; reviewer contacts per row {'0': 1080}); comparator 4353 (4.031 / row; {'4': 1069, '7': 11}) |
| dispositions | finite stops 0, planner-action-illegal 0, other terminal 0 |

## 2. Headline contrasts (P0 minus R-PRIM, paired, 10,000 draws, seed 20260915)

| metric | R-PRIM | P0 | delta pp | CI95 |
| --- | ---: | ---: | ---: | --- |

Lock comparison (reported, never a gate): see `lock-comparison.json`; projection-v3 and TRAIN-symmetric companions are in `score-contrasts.json`.

## 3. Per-scenario (natural mixture and equal-scenario weighting; diagnostics, never gates)

- pooled_slu_f1_equal_scenario_delta_pp: -0.4774984911040734
### pooled_slu_f1_per_scenario

| scenario | delta_pp | left_pct | n | right_pct |
| --- | ---: | ---: | ---: | ---: |
| alarm | -3.060 | 74.905 | 60 | 71.846 |
| audio | -8.764 | 67.889 | 60 | 59.125 |
| calendar | -0.173 | 67.390 | 60 | 67.217 |
| cooking | 2.467 | 63.503 | 60 | 65.970 |
| datetime | 0.777 | 76.631 | 60 | 77.408 |
| email | 1.332 | 64.634 | 60 | 65.967 |
| general | 4.444 | 22.222 | 60 | 26.667 |
| iot | 0.655 | 64.967 | 60 | 65.622 |
| lists | 2.751 | 57.454 | 60 | 60.205 |
| music | 0.477 | 48.273 | 60 | 48.750 |
| news | -0.264 | 64.604 | 60 | 64.339 |
| play | -5.195 | 56.890 | 60 | 51.695 |
| qa | -0.312 | 60.640 | 60 | 60.328 |
| recommendation | -3.586 | 69.453 | 60 | 65.867 |
| social | -2.783 | 59.944 | 60 | 57.161 |
| takeaway | 4.707 | 54.330 | 60 | 59.037 |
| transport | -0.753 | 65.587 | 60 | 64.834 |
| weather | -1.316 | 79.285 | 60 | 77.970 |

### pooled_span_f1_per_scenario

| scenario | delta_pp | left_pct | n | right_pct |
| --- | ---: | ---: | ---: | ---: |
| alarm | -2.950 | 66.667 | 60 | 63.717 |
| audio | -8.333 | 41.667 | 60 | 33.333 |
| calendar | -0.586 | 53.416 | 60 | 52.830 |
| cooking | 2.934 | 50.847 | 60 | 53.782 |
| datetime | 1.173 | 61.538 | 60 | 62.712 |
| email | 1.481 | 51.852 | 60 | 53.333 |
| general | 4.444 | 22.222 | 60 | 26.667 |
| iot | 0.397 | 58.427 | 60 | 58.824 |
| lists | 1.018 | 54.054 | 60 | 55.072 |
| music | 3.846 | 42.308 | 60 | 46.154 |
| news | -0.383 | 55.556 | 60 | 55.172 |
| play | -5.703 | 41.739 | 60 | 36.036 |
| qa | 0.431 | 45.283 | 60 | 45.714 |
| recommendation | -3.074 | 62.903 | 60 | 59.829 |
| social | -2.768 | 49.664 | 60 | 46.897 |
| takeaway | 5.988 | 38.298 | 60 | 44.286 |
| transport | 0.056 | 58.385 | 60 | 58.442 |
| weather | -2.142 | 74.483 | 60 | 72.340 |

Intent band: decision-17 flagged scenarios = [].

## 4. Frontier row (decision 75)

| cell | official SLU | official intent | GPU-h / 1,080 | contacts / row | prefilled tok / row | on GPU-h frontier | on token frontier |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| P0 | 63.85 | 81.57 | 1.2565 | 2.000 | 7802.0 | True | True |

## 5. Records

Four exposure-ledger rows closed (SAEA-SLURP-NATIVE-PRUNE-REVIEW-OFF-{SMOKE-4-,SMOKE-4-FIT-,,FIT-}V1, flight commit 1e349630, 2026-09-23T00:58 to 02:28 UTC); results-ledger entry; decision-85 outcome appended. Stage-3 algorithm label: none (decision 101).
