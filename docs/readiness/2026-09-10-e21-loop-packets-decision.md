# E21 LOOP decision: retain KC-E1f

Status: root reviewed and decided. This English successor replaces the malformed draft text; immutable source artifacts remain unchanged.

The judge improves PERSON errors relative to its randomized twin, but fails to retain historical KC-E1f PERSON quality. Keep KC-E1f for the next offline quality system. No new LOOP generation follows this decision.

Root decision: DATA/coordination/e21-loop-packets-root-decision-v1.json; SHA-256 a3015f10ad7251c6c2f0f816572b0b459511df08581e2cc7455aa01ea6e26b37.

All gains below use the frozen favorable direction in percentage points (error reduction, or numeric accuracy increase). The primary estimator is natural mixture; equal-call weighting is sensitivity. Bootstrap uses 10,000 call-cluster draws and seed 20260903.

| Comparison | Metric | Natural mixture gain [CI90] | Equal-call gain [CI90] |
|---|---|---:|---:|
| judge_versus_historical_comparator | PERSON | +2.022626 [+1.368053, +2.728592] | +2.432400 [+1.556625, +3.351493] |
| judge_versus_historical_comparator | WER | +0.018901 [+0.012440, +0.025899] | +0.022953 [+0.014954, +0.031438] |
| judge_versus_historical_comparator | insertion | +0.000278 [+0.000000, +0.000817] | +0.000238 [+0.000000, +0.000714] |
| judge_versus_historical_comparator | nonentity | +0.000329 [-0.001508, +0.002054] | +0.000648 [-0.000726, +0.002015] |
| judge_versus_historical_comparator | numeric | +0.000000 [+0.000000, +0.000000] | +0.000000 [+0.000000, +0.000000] |
| judge_versus_historical_kc_e1f | PERSON | -1.714090 [-2.564917, -0.886179] | -1.267347 [-2.133838, -0.388111] |
| judge_versus_historical_kc_e1f | WER | -0.026128 [-0.042751, -0.010866] | -0.022687 [-0.038620, -0.007127] |
| judge_versus_historical_kc_e1f | insertion | +0.000556 [-0.001740, +0.002882] | +0.000354 [-0.002072, +0.002724] |
| judge_versus_historical_kc_e1f | nonentity | -0.001314 [-0.006962, +0.004146] | -0.001431 [-0.007191, +0.004378] |
| judge_versus_historical_kc_e1f | numeric | -0.010273 [-0.051217, +0.021225] | -0.012661 [-0.054945, +0.016961] |
| judge_versus_twin | PERSON | +1.474117 [+0.849923, +2.136136] | +1.755367 [+1.001335, +2.525865] |
| judge_versus_twin | WER | +0.017233 [+0.010323, +0.024705] | +0.021507 [+0.013318, +0.030334] |
| judge_versus_twin | insertion | +0.001390 [+0.000535, +0.002415] | +0.001300 [+0.000476, +0.002259] |
| judge_versus_twin | nonentity | +0.002300 [-0.000318, +0.005108] | +0.003733 [+0.000932, +0.006886] |
| judge_versus_twin | numeric | +0.030820 [+0.009329, +0.062024] | +0.030596 [+0.006494, +0.063389] |
| twin_versus_historical_comparator | PERSON | +0.548509 [+0.245872, +0.897669] | +0.677033 [+0.353670, +1.039262] |
| twin_versus_historical_comparator | WER | +0.001668 [-0.001376, +0.004618] | +0.001446 [-0.001690, +0.004492] |
| twin_versus_historical_comparator | insertion | -0.001112 [-0.002079, -0.000281] | -0.001062 [-0.001997, -0.000249] |
| twin_versus_historical_comparator | nonentity | -0.001972 [-0.003977, -0.000312] | -0.003085 [-0.005860, -0.000797] |
| twin_versus_historical_comparator | numeric | -0.030820 [-0.062024, -0.009329] | -0.030596 [-0.063389, -0.006494] |
| twin_versus_historical_kc_e1f | PERSON | -3.188207 [-4.245782, -2.159683] | -3.022714 [-4.199290, -1.865167] |
| twin_versus_historical_kc_e1f | WER | -0.043362 [-0.060671, -0.026974] | -0.044193 [-0.062964, -0.025947] |
| twin_versus_historical_kc_e1f | insertion | -0.000834 [-0.003181, +0.001524] | -0.000946 [-0.003401, +0.001472] |
| twin_versus_historical_kc_e1f | nonentity | -0.003614 [-0.009334, +0.001753] | -0.005164 [-0.010884, +0.000422] |
| twin_versus_historical_kc_e1f | numeric | -0.041093 [-0.090891, +0.000000] | -0.043257 [-0.093940, -0.000161] |

## Frozen admission gates

PERSON versus historical direct and targeting versus twin pass. PERSON retention versus KC-E1f fails: lower bound -2.564917 is below -0.25009. The KC-E1f-referenced WER, numeric and insertion guards pass with respective lower bounds -0.042751, -0.051217 and -0.001740 against -0.05793, -0.15651 and -0.022178. Each arm uses 600 calls, below the 796.5 limit. Passing these guards does not repair the failed PERSON retention gate.

## Complete stratum views

These tables are descriptive, without new gates. Full precision and source hashes remain in DATA/analysis/SAEA-E21-LOOP-PACKETS-NP4-SAVED-SCORE-ANALYSIS-V1/loop-contrast-compact-tables.json (SHA-256 4e2200d863a828f665701341f9bc0ecbafbb76bbf67b7ffebab01bb489484a70).

### sample_rate

| Contrast | Stratum | n calls | PERSON | WER | Nonentity | Numeric | Insertion |
|---|---|---:|---:|---:|---:|---:|---:|
| judge_versus_historical_comparator | 11025 | 5 | +0.294985 | +0.002082 | +0.002460 | +0.000000 | +0.000000 |
| judge_versus_historical_comparator | 16000 | 6 | +5.705706 | +0.049209 | +0.002812 | +0.000000 | +0.000000 |
| judge_versus_historical_comparator | 22050 | 5 | +3.759398 | +0.028886 | +0.000000 | +0.000000 | +0.000000 |
| judge_versus_historical_comparator | 24000 | 21 | +1.844735 | +0.016870 | +0.000705 | +0.000000 | +0.000603 |
| judge_versus_historical_comparator | 44100 | 7 | +0.737463 | +0.011683 | -0.003500 | +0.000000 | +0.000000 |
| judge_versus_historical_kc_e1f | 11025 | 5 | -0.294985 | +0.000000 | +0.004919 | +0.000000 | +0.000000 |
| judge_versus_historical_kc_e1f | 16000 | 6 | -0.900901 | -0.065612 | -0.016874 | +0.068446 | -0.004687 |
| judge_versus_historical_kc_e1f | 22050 | 5 | +0.751880 | +0.025997 | +0.010261 | +0.000000 | +0.008666 |
| judge_versus_historical_kc_e1f | 24000 | 21 | -3.228286 | -0.039163 | -0.000705 | -0.048780 | +0.002410 |
| judge_versus_historical_kc_e1f | 44100 | 7 | -0.884956 | -0.014604 | -0.003500 | +0.000000 | -0.004381 |
| judge_versus_twin | 11025 | 5 | +0.294985 | +0.002082 | +0.002460 | +0.000000 | +0.000000 |
| judge_versus_twin | 16000 | 6 | +4.804805 | +0.044523 | +0.005625 | +0.000000 | +0.000000 |
| judge_versus_twin | 22050 | 5 | +2.631579 | +0.031774 | +0.003420 | +0.187617 | +0.000000 |
| judge_versus_twin | 24000 | 21 | +1.152959 | +0.015063 | +0.003527 | +0.024390 | +0.003013 |
| judge_versus_twin | 44100 | 7 | +0.589971 | +0.008762 | -0.003500 | +0.000000 | +0.000000 |
| twin_versus_historical_comparator | 11025 | 5 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 |
| twin_versus_historical_comparator | 16000 | 6 | +0.900901 | +0.004687 | -0.002812 | +0.000000 | +0.000000 |
| twin_versus_historical_comparator | 22050 | 5 | +1.127820 | -0.002889 | -0.003420 | -0.187617 | +0.000000 |
| twin_versus_historical_comparator | 24000 | 21 | +0.691776 | +0.001808 | -0.002822 | -0.024390 | -0.002410 |
| twin_versus_historical_comparator | 44100 | 7 | +0.147493 | +0.002921 | +0.000000 | +0.000000 | +0.000000 |
| twin_versus_historical_kc_e1f | 11025 | 5 | -0.589971 | -0.002082 | +0.002460 | +0.000000 | +0.000000 |
| twin_versus_historical_kc_e1f | 16000 | 6 | -5.705706 | -0.110135 | -0.022499 | +0.068446 | -0.004687 |
| twin_versus_historical_kc_e1f | 22050 | 5 | -1.879699 | -0.005777 | +0.006841 | -0.187617 | +0.008666 |
| twin_versus_historical_kc_e1f | 24000 | 21 | -4.381245 | -0.054225 | -0.004233 | -0.073171 | -0.000603 |
| twin_versus_historical_kc_e1f | 44100 | 7 | -1.474926 | -0.023367 | +0.000000 | +0.000000 | -0.004381 |

### sector

| Contrast | Stratum | n calls | PERSON | WER | Nonentity | Numeric | Insertion |
|---|---|---:|---:|---:|---:|---:|---:|
| judge_versus_historical_comparator | Basic Materials | 5 | +2.059497 | +0.025226 | +0.000000 | +0.000000 | +0.000000 |
| judge_versus_historical_comparator | Conglomerate | 4 | +1.047120 | +0.007344 | -0.002884 | +0.000000 | +0.000000 |
| judge_versus_historical_comparator | Consumer Goods | 5 | +1.400560 | +0.016009 | +0.000000 | +0.000000 | +0.000000 |
| judge_versus_historical_comparator | Financial | 5 | +1.423488 | +0.009428 | +0.000000 | +0.000000 | +0.000000 |
| judge_versus_historical_comparator | Healthcare | 5 | +0.958466 | +0.011069 | +0.003233 | +0.000000 | +0.000000 |
| judge_versus_historical_comparator | Industrial Goods | 5 | +2.295918 | +0.034196 | +0.005398 | +0.000000 | +0.002280 |
| judge_versus_historical_comparator | Services | 5 | +4.455446 | +0.029387 | -0.003524 | +0.000000 | +0.000000 |
| judge_versus_historical_comparator | Technology | 5 | +4.069767 | +0.024881 | +0.000000 | +0.000000 | +0.000000 |
| judge_versus_historical_comparator | Utilities | 5 | +2.362205 | +0.016437 | +0.000000 | +0.000000 | +0.000000 |
| judge_versus_historical_kc_e1f | Basic Materials | 5 | -0.686499 | +0.008409 | +0.003392 | +0.000000 | -0.002803 |
| judge_versus_historical_kc_e1f | Conglomerate | 4 | -3.141361 | -0.034270 | -0.008653 | +0.000000 | +0.000000 |
| judge_versus_historical_kc_e1f | Consumer Goods | 5 | -2.240896 | -0.024014 | +0.009445 | +0.000000 | +0.006003 |
| judge_versus_historical_kc_e1f | Financial | 5 | -1.779359 | -0.002357 | +0.019135 | +0.000000 | +0.000000 |
| judge_versus_historical_kc_e1f | Healthcare | 5 | -3.514377 | -0.083017 | -0.016166 | -0.217155 | -0.005534 |
| judge_versus_historical_kc_e1f | Industrial Goods | 5 | -0.255102 | -0.022797 | +0.000000 | +0.078064 | +0.002280 |
| judge_versus_historical_kc_e1f | Services | 5 | -2.475248 | -0.064651 | -0.017619 | +0.000000 | +0.000000 |
| judge_versus_historical_kc_e1f | Technology | 5 | +2.325581 | -0.007109 | -0.012794 | +0.000000 | -0.007109 |
| judge_versus_historical_kc_e1f | Utilities | 5 | -2.362205 | -0.012327 | +0.000000 | +0.000000 | +0.006164 |
| judge_versus_twin | Basic Materials | 5 | +1.372998 | +0.016817 | +0.000000 | +0.000000 | +0.000000 |
| judge_versus_twin | Conglomerate | 4 | -0.785340 | +0.002448 | +0.005769 | +0.091743 | +0.000000 |
| judge_versus_twin | Consumer Goods | 5 | +1.400560 | +0.014008 | +0.002361 | +0.000000 | +0.002001 |
| judge_versus_twin | Financial | 5 | +1.423488 | +0.014142 | +0.002734 | +0.099206 | +0.000000 |
| judge_versus_twin | Healthcare | 5 | +0.638978 | +0.011069 | +0.006466 | +0.000000 | +0.002767 |
| judge_versus_twin | Industrial Goods | 5 | +2.295918 | +0.031916 | +0.002699 | +0.000000 | +0.004559 |
| judge_versus_twin | Services | 5 | +2.970297 | +0.023509 | +0.000000 | +0.000000 | +0.000000 |
| judge_versus_twin | Technology | 5 | +3.488372 | +0.024881 | +0.004265 | +0.000000 | +0.000000 |
| judge_versus_twin | Utilities | 5 | +2.099738 | +0.018491 | -0.002413 | +0.083752 | +0.002055 |
| twin_versus_historical_comparator | Basic Materials | 5 | +0.686499 | +0.008409 | +0.000000 | +0.000000 | +0.000000 |
| twin_versus_historical_comparator | Conglomerate | 4 | +1.832461 | +0.004896 | -0.008653 | -0.091743 | +0.000000 |
| twin_versus_historical_comparator | Consumer Goods | 5 | +0.000000 | +0.002001 | -0.002361 | +0.000000 | -0.002001 |
| twin_versus_historical_comparator | Financial | 5 | +0.000000 | -0.004714 | -0.002734 | -0.099206 | +0.000000 |
| twin_versus_historical_comparator | Healthcare | 5 | +0.319489 | +0.000000 | -0.003233 | +0.000000 | -0.002767 |
| twin_versus_historical_comparator | Industrial Goods | 5 | +0.000000 | +0.002280 | +0.002699 | +0.000000 | -0.002280 |
| twin_versus_historical_comparator | Services | 5 | +1.485149 | +0.005877 | -0.003524 | +0.000000 | +0.000000 |
| twin_versus_historical_comparator | Technology | 5 | +0.581395 | +0.000000 | -0.004265 | +0.000000 | +0.000000 |
| twin_versus_historical_comparator | Utilities | 5 | +0.262467 | -0.002055 | +0.002413 | -0.083752 | -0.002055 |
| twin_versus_historical_kc_e1f | Basic Materials | 5 | -2.059497 | -0.008409 | +0.003392 | +0.000000 | -0.002803 |
| twin_versus_historical_kc_e1f | Conglomerate | 4 | -2.356021 | -0.036718 | -0.014422 | -0.091743 | +0.000000 |
| twin_versus_historical_kc_e1f | Consumer Goods | 5 | -3.641457 | -0.038022 | +0.007084 | +0.000000 | +0.004002 |
| twin_versus_historical_kc_e1f | Financial | 5 | -3.202847 | -0.016499 | +0.016402 | -0.099206 | +0.000000 |
| twin_versus_historical_kc_e1f | Healthcare | 5 | -4.153355 | -0.094086 | -0.022632 | -0.217155 | -0.008302 |
| twin_versus_historical_kc_e1f | Industrial Goods | 5 | -2.551020 | -0.054713 | -0.002699 | +0.078064 | -0.002280 |
| twin_versus_historical_kc_e1f | Services | 5 | -5.445545 | -0.088160 | -0.017619 | +0.000000 | +0.000000 |
| twin_versus_historical_kc_e1f | Technology | 5 | -1.162791 | -0.031990 | -0.017059 | +0.000000 | -0.007109 |
| twin_versus_historical_kc_e1f | Utilities | 5 | -4.461942 | -0.030819 | +0.002413 | -0.083752 | +0.004109 |

## Custody, cost and interpretation

Each arm completed 600 selected generations and kept 993 unselected predecessor windows, yielding 1,593 windows across 44 calls. No retry, skipped slice or saturation occurred. Both attempts are finalized after one complete official score each. Pair generation GPU cost is 0.3579660937786103 GPU-hours, below the registered 1.0 family cap. Full monitor and idle costs remain separately recorded.

The judge seal initially refused a stale root lease after generation. Archived custody and the subsequent seal retain those same 600 responses; no generation was replayed. Historical KC-E1f used raw audio, while these LOOP arms used formal prepared packets. This remains a provenance limitation. Saved predecessors and plans establish component behavior; they do not establish a live planner or meeting-minutes quality.

The next E21 candidate uses newly generated direct drafts followed by the existing KC-E1f constrained repair, with both stages and all costs registered before use. Root must complete its fresh-parent binding and admission; no new controller or new LOOP mechanism is implied.
