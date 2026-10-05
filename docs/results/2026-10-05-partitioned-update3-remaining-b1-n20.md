# Partitioned update3 remaining-b1: complete exploratory cohort review

Reviewed at 2026-10-05T22:36:06.002736+00:00. All 6 members independently finalized 20 inputs each, with verified seals, exactly one successful complete official score and zero failed jobs. Root READ and timing export completed without new model/scorer contacts.

No candidate exceeds the seed on official pooled SLU-F1. Branch09 reduces mean latency by about21percent but loses F1 and intent accuracy. Branch10 raises intent by5percentage points but loses F1 and increases latency. Branch11 exceeds A/A F1 but is slower than both controls and below seed F1. Seed A/A differs by about5.01 F1 percentage points. These are exploratory tradeoffs on reused N20 inputs, not stable benefit, formal adoption or proof of learning gain.

Continue unchanged adjacent remaining-b2, retaining all registered candidates and no-change positions. Full successor optimizer export remains held until every configured cohort completes.

| Member | Official F1 % | Intent % | Reliable % | Mean s | Non-first s | Calls | Equal-stratum F1 % | Equal-stratum intent % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| seed | 59.2878 | 70.00 | 100.00 | 33.628 | 33.879 | 128 | 45.6709 | 70.51 |
| seed-aa | 54.2811 | 70.00 | 100.00 | 32.655 | 33.072 | 128 | 42.6566 | 70.51 |
| branch-09 | 54.6766 | 55.00 | 100.00 | 26.517 | 26.808 | 98 | 42.1656 | 58.97 |
| branch-10 | 54.2811 | 75.00 | 100.00 | 47.700 | 47.250 | 104 | 44.0186 | 78.21 |
| branch-11 | 57.8603 | 65.00 | 100.00 | 79.582 | 79.714 | 122 | 43.1182 | 66.67 |
| branch-12 | 49.2539 | 60.00 | 100.00 | 60.332 | 61.624 | 92 | 40.1096 | 62.82 |

All tool-call counts are zero. Equal-stratum values are arithmetic means of within-stratum pooled metrics, descriptive rather than the official pooled endpoint.

## Complete per-stratum results

Each cell is stratum F1 % / intent %. Sparse strata are descriptive.

| Stratum | N | seed | seed-aa | branch-09 | branch-10 | branch-11 | branch-12 |
|---|---:|---:|---:|---:|---:|---:|---:|
| audio | 3 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 |
| cooking | 2 | 50.00 / 50.00 | 50.00 / 50.00 | 66.67 / 0.00 | 50.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 |
| email | 1 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 |
| general | 2 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| iot | 1 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 |
| lists | 1 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 59.09 / 100.00 | 59.09 / 100.00 |
| music | 2 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 |
| news | 1 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 |
| play | 2 | 66.67 / 100.00 | 33.33 / 100.00 | 73.03 / 100.00 | 40.00 / 100.00 | 80.24 / 100.00 | 66.67 / 100.00 |
| qa | 2 | 58.54 / 100.00 | 62.75 / 100.00 | 0.00 / 0.00 | 62.75 / 100.00 | 62.75 / 100.00 | 37.21 / 50.00 |
| recommendation | 1 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 |
| social | 1 | 51.85 / 0.00 | 41.79 / 0.00 | 41.79 / 0.00 | 52.83 / 100.00 | 41.79 / 0.00 | 41.79 / 0.00 |
| takeaway | 1 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 |

## First-admission and subsequent timing

| Member | First sample s | Non-first mean s | First slot-count mean s | Remaining mean s | Batch wall s/sample |
|---|---:|---:|---:|---:|---:|
| seed | 28.876 | 33.879 | 30.189 | 34.488 | 8.829 |
| seed-aa | 24.737 | 33.072 | 30.360 | 33.229 | 8.634 |
| branch-09 | 20.986 | 26.808 | 25.641 | 26.736 | 7.120 |
| branch-10 | 56.253 | 47.250 | 41.005 | 49.373 | 12.711 |
| branch-11 | 77.057 | 79.714 | 68.383 | 82.381 | 21.010 |
| branch-12 | 35.791 | 61.624 | 39.123 | 65.635 | 16.100 |

Monotonic admission-to-settled-workflow wall time includes internal model/tool waits, FIT and cleanup. Pre-admission wait is separate. Roster preparation, final persistence and official scoring are excluded. Batch wall per sample measures throughput, not individual latency.

First slot-count admissions are a diagnostic group, not a proven cold wave; the remaining samples are not guaranteed warm. No slow-sample trimming.

## Measured node timing and reuse

| Member / node | Contacts | Prefill ms/contact | Decode ms/contact | Transport ms/contact | Reused input fraction |
|---|---:|---:|---:|---:|---:|
| seed / perception | 20 | 676.356 | 6129.129 | 6993.740 | 0.6309 |
| seed / planner | 36 | 386.170 | 232.064 | 740.883 | 0.9507 |
| seed / reviewer | 36 | 272.550 | 8328.496 | 8784.596 | 0.9694 |
| seed / solver | 36 | 1856.373 | 1779.837 | 4051.750 | 0.6342 |
| seed-aa / perception | 20 | 659.512 | 5846.237 | 6689.463 | 0.6309 |
| seed-aa / planner | 36 | 361.631 | 168.274 | 846.866 | 0.9487 |
| seed-aa / reviewer | 36 | 308.945 | 7561.893 | 8167.981 | 0.9676 |
| seed-aa / solver | 36 | 1853.511 | 1970.432 | 4198.621 | 0.6434 |
| branch-09 / perception | 20 | 784.676 | 5037.530 | 6343.509 | 0.6270 |
| branch-09 / planner | 26 | 492.997 | 161.912 | 889.439 | 0.9261 |
| branch-09 / reviewer | 26 | 481.946 | 5267.134 | 6405.021 | 0.9339 |
| branch-09 / solver | 26 | 2598.260 | 3362.378 | 6729.350 | 0.4960 |
| branch-10 / perception | 20 | 1132.588 | 9273.166 | 10907.771 | 0.5966 |
| branch-10 / planner | 28 | 4906.408 | 395.395 | 5571.984 | 0.1955 |
| branch-10 / reviewer | 28 | 581.184 | 10049.529 | 11383.631 | 0.9313 |
| branch-10 / solver | 28 | 4293.679 | 3070.572 | 7900.197 | 0.2921 |
| branch-11 / perception | 20 | 1385.592 | 13032.289 | 14707.649 | 0.5952 |
| branch-11 / planner | 34 | 4836.110 | 328.439 | 5525.140 | 0.1952 |
| branch-11 / reviewer | 34 | 3949.589 | 16857.447 | 21532.657 | 0.2121 |
| branch-11 / solver | 34 | 5545.984 | 3877.984 | 9867.277 | 0.2095 |
| branch-12 / perception | 20 | 1177.936 | 11550.163 | 13183.016 | 0.6267 |
| branch-12 / planner | 24 | 5027.728 | 483.725 | 5944.870 | 0.2102 |
| branch-12 / reviewer | 24 | 5930.517 | 14545.682 | 21252.808 | 0.2191 |
| branch-12 / solver | 24 | 5885.416 | 4434.473 | 10567.275 | 0.2184 |

Timing/reuse associations do not establish causal node credit. Preserve independent node optimization space and official quality constraints.

## Paired exploratory comparisons

All registered confidence intervals are retained in the complete source report; no N20 efficacy claim.

| Contrast | F1 change pp | 95% CI pp | Intent change pp | Repaired / damaged whole answers |
|---|---:|---|---:|---|
| branch-09-minus-aa | 0.3955 | [-18.5910, 19.3245] | -15.00 | 0 / 2 |
| branch-09-minus-parent | -4.6112 | [-21.4195, 13.7030] | -15.00 | 1 / 3 |
| branch-10-minus-aa | 0.0000 | [-8.5865, 5.1918] | 5.00 | 0 / 1 |
| branch-10-minus-parent | -5.0067 | [-14.5455, 1.2000] | 5.00 | 0 / 1 |
| branch-11-minus-aa | 3.5792 | [-10.5859, 17.1426] | -5.00 | 1 / 4 |
| branch-11-minus-parent | -1.4275 | [-10.7770, 7.8414] | -5.00 | 0 / 3 |
| branch-12-minus-aa | -5.0272 | [-22.1598, 7.5396] | -10.00 | 1 / 4 |
| branch-12-minus-parent | -10.0339 | [-23.1002, -1.9994] | -10.00 | 0 / 3 |
| same-request-null | -5.0067 | [-14.0001, 4.2665] | 0.00 | 1 / 1 |

Whole-answer transitions compare complete systems, not within-trajectory repair causality. The complete source report retains unchanged-success and unchanged-failure cases.

Source: data-root analysis/SAEA-SLURP-CONTEXT-TEMPLATE-PARTITIONED-UPDATE3-N20-V1-REMAINING-B1-READ-V1/report.json and timing-summary.json. Exact root READ: SAEA-SLURP-CONTEXT-TEMPLATE-PARTITIONED-UPDATE3-N20-V1-REMAINING-B1-READ-V1.
