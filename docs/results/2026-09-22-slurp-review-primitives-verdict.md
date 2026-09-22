# Cell R-PRIM verdict: the Reviewer verdict as a closed set of primitives (item E37, owner decision 84), one factor on the locked default-plan base

Read 2026-09-22 by the coordinator (Fable 5.1) with the repo driver `scripts/analysis/plan_cell_read.py` (analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-REVIEW-PRIMITIVES-PAIRED-ANALYSIS-V1`, score-contrasts sha256 `287796c76800a6ff2c5599a340e5265e7be088ed3c876d86b9886b576cc9afbe`) and the E37 verifier stage `scripts/analysis/slurp_verifier_measurement.py --stage primitives` (`analysis/SAEA-SLURP-REVIEW-PRIMITIVES-VERIFIER-V1/primitives.json`, sha256 `e2db4bf4777e00b5c288f5aa1198b81929fe5ddec3145ef75eb5322525086717`). Model-free: zero model / tokenizer / encoder / server contacts; five model-free scorings over copies of sealed outputs. Development numbers (decisions 28, 86).

## 1. Verdict

| item | result |
| --- | --- |
| status | **NEUTRAL (non-inferiority NOT PROVEN on intent, by width, not by loss)**: official pooled SLU-F1 +0.58 pp [-0.82, +1.80] clears the plan's own-null margin 1.2485 (non-inferior); intent -0.09 pp [-1.16, +0.94] misses the margin 0.9943 by 0.17 pp of CI width (the B1-notool precedent, decisions 25 / 61) |
| decision 97 consequence | R-PRIM is NOT HARMFUL, so the decision-85 pruning cells (P1 Reviewer 3 -> 1, P0 review-off) fly on the R-PRIM base and read the primitive distribution beside SLU / intent |
| lock | v2.0 stays on cell PLAN as flown; R-PRIM enters no plan by itself (it was registered for measurability, decision 84), it is the measurable-Reviewer base for the pruning cells only |
| cost | contacts / row 4.03 vs 4.10, GPU-h / 1,080 1.57 measured vs 1.76 (PLAN estimate), contacts / min 44.2 vs 39.9: the primitive vocabulary costs nothing |
| measurability (the purpose of E37) | parse rate **100 %** (1,091 legal Reviewer visits, 1,080 rows); tokens ACCEPT 1,073 / REVISE-INTENT 7 / REVISE-SLOT-VALUE 11 / other primitives 0; REVISE precision 0.91, recall 0.017 against 598 actually-wrong rows; Planner routed REVISE on 11 of the 18 REVISE tokens |

## 2. Headline contrasts (R-PRIM minus PLAN, paired, 10,000 draws, seed 20260915)

| metric | PLAN | R-PRIM | delta pp | CI95 |
| --- | ---: | ---: | ---: | --- |

Lock comparison (reported, never a gate): against B5e official 62.34 / 80.09 the arm reads +1.87 SLU [+0.46, +3.26] and +2.04 intent [+0.81, +3.25]; against the B5e + normaliser-node provisional lock 63.78 / 81.85, +0.43 [-1.00, +1.79] and +0.28 [-0.73, +1.30]. Projection-v3 and TRAIN-symmetric companions agree in sign (see `score-contrasts.json`).

## 3. Per-scenario tables (natural mixture and equal-scenario weighting; diagnostics, never gates)

### per_row_metrics_per_scenario

Per-scenario per-row metrics (action, scenario, intent, slot-F1, SLU-F1 by scenario, both weightings) are in `per-scenario-tables.json` under the analysis root; the pooled SLU-F1 per-scenario table follows.

- pooled_slu_f1_equal_scenario_delta_pp: 0.8861627940290652
### pooled_slu_f1_per_scenario

| scenario | delta_pp | left_pct | n | right_pct |
| --- | ---: | ---: | ---: | ---: |
| alarm | -1.842 | 76.748 | 60 | 74.905 |
| audio | 19.715 | 48.174 | 60 | 67.889 |
| calendar | 1.751 | 65.639 | 60 | 67.390 |
| cooking | 0.292 | 63.211 | 60 | 63.503 |
| datetime | 3.258 | 73.373 | 60 | 76.631 |
| email | 2.851 | 61.783 | 60 | 64.634 |
| general | -8.007 | 30.229 | 60 | 22.222 |
| iot | -1.400 | 66.368 | 60 | 64.967 |
| lists | 0.000 | 57.454 | 60 | 57.454 |
| music | -0.477 | 48.750 | 60 | 48.273 |
| news | -4.162 | 68.766 | 60 | 64.604 |
| play | 1.502 | 55.388 | 60 | 56.890 |
| qa | -2.008 | 62.649 | 60 | 60.640 |
| recommendation | 2.968 | 66.485 | 60 | 69.453 |
| social | 1.620 | 58.324 | 60 | 59.944 |
| takeaway | -7.463 | 61.793 | 60 | 54.330 |
| transport | -1.093 | 66.680 | 60 | 65.587 |
| weather | 8.447 | 70.838 | 60 | 79.285 |

### pooled_span_f1_per_scenario

| scenario | delta_pp | left_pct | n | right_pct |
| --- | ---: | ---: | ---: | ---: |
| alarm | -1.709 | 68.376 | 60 | 66.667 |
| audio | 18.590 | 23.077 | 60 | 41.667 |
| calendar | 0.977 | 52.439 | 60 | 53.416 |
| cooking | -1.253 | 52.101 | 60 | 50.847 |
| datetime | 2.522 | 59.016 | 60 | 61.538 |
| email | 2.328 | 49.524 | 60 | 51.852 |
| general | -5.229 | 27.451 | 60 | 22.222 |
| iot | -1.573 | 60.000 | 60 | 58.427 |
| lists | 0.000 | 54.054 | 60 | 54.054 |
| music | -3.846 | 46.154 | 60 | 42.308 |
| news | -3.785 | 59.341 | 60 | 55.556 |
| play | 0.417 | 41.322 | 60 | 41.739 |
| qa | -3.774 | 49.057 | 60 | 45.283 |
| recommendation | 3.703 | 59.200 | 60 | 62.903 |
| social | 1.342 | 48.322 | 60 | 49.664 |
| takeaway | -10.313 | 48.611 | 60 | 38.298 |
| transport | -1.242 | 59.627 | 60 | 58.385 |
| weather | 7.350 | 67.133 | 60 | 74.483 |

Intent band: decision-17 flagged scenarios = []; scenarios losing beyond the null band = see per-scenario-tables.json.

## 4. Structural (the tool surface, the trajectory, the dispositions)

- contacts 4353 (4.031 / row; histogram {'4': 1069, '7': 11}; reviewer contacts per row {'1': 1069, '2': 11}); comparator 4424 (4.096 / row)
- dispositions: finite stops 0, planner-action-illegal 1 (row retained), other terminal 0; E20 compaction contacts 0
- tool-free arm: every request renders the same empty tool schema (one distinct digest); knowledge-store pins identical to PLAN; the Perception request key is byte-identical to PLAN (the factor touches the Reviewer only)

## 5. The E37 primitives stage (model-free, over a copy of the sealed answers)

| statistic | value |
| --- | --- |
| total_rows | 1080 |
| armed_rows | 1080 |
| legal_visits | 1091 |
| parse_rate | 1.0 |
| multi_visit_rows | 11 |
| cross_visit_agreement_rate | 0.6363636363636364 |
| actual_wrong_rows | 598 |
| predicted_wrong_rows | 11 |
| revise_precision | 0.9090909090909091 |
| revise_recall | 0.016722408026755852 |
| token counts | {'ACCEPT': 1073, 'REVISE-INTENT': 7, 'REVISE-SLOT-VALUE': 11} |
| confusion (token x delivered correctness) | {'ACCEPT': {'correct': 481, 'incorrect': 592}, 'REVISE-INTENT': {'correct': 0, 'incorrect': 7}, 'REVISE-SLOT-VALUE': {'correct': 2, 'incorrect': 9}} |
| Planner route by token | {'ACCEPT': {'ACCEPT': 1073}, 'REVISE-INTENT': {'ACCEPT': 2, 'REVISE': 5}, 'REVISE-SLOT-VALUE': {'ACCEPT': 4, 'REVISE': 6, 'REVISE-SLOT-VALUE': 1}} |

Reading: the closed vocabulary is parseable on every visit (0 of 2,167 anchor reviews parsed before E37), but the Reviewer under the locked plan says ACCEPT on 98.4 % of visits and flags 11 of the 598 wrong rows. The review budget is now measurable, which is what decision 85 needed: the pruning cells will show what those 1.03 Reviewer contacts per row buy.

## 6. Frontier row and efficiency (decision 75)

| cell | official SLU | official intent | GPU-h / 1,080 | contacts / row | prefilled tok / row | on GPU-h frontier | on token frontier |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| R-PRIM | 64.21 | 82.13 | 1.5688 | 4.031 | 8346.5 | True | True |

Efficiency headline: cache-hit share 0.751 (comparator 0.7545), contacts / min 44.2 (comparator 39.92), cost lower than the base: True.

## 7. Records

Four exposure-ledger rows closed (SAEA-SLURP-NATIVE-REVIEW-PRIMITIVES-{SMOKE-4-,SMOKE-4-FIT-,,FIT-}V1); results-ledger entry; harness-admission entry `native_episode.reviewer_verdict` PENDING -> NEUTRAL; decision outcomes 84 / 85 / 97 appended. Pruning cells P1 / P0 registered on the R-PRIM base (`docs/readiness/2026-09-22-slurp-prune-{reviewer1,review-off}-v1/`).
