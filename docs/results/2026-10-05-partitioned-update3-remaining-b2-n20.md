# Partitioned update3 remaining-b2: complete exploratory cohort review

Reviewed at 2026-10-05T23:19:46.895759+00:00. All six members independently finalized20 inputs each with verified seals, one successful complete official score and zero failed jobs. Driver epoch2026-10-05T22:42:07Z ended normally23:16:19Z. Exact root READ and timing export added no model/scorer contacts. The job-specific fifteen-minute monitor is deleted.

Branches13 and16 have pooled F1 above seed but below its A/A replicate, with intent lower by5 percentage points. They reduce mean sample latency by about21-22percent. Branch14 and unchanged branch15 are slower with lower F1. Seed A/A differs by8.15 F1 percentage points. These N20 reused-input observations do not establish stable benefit or learning efficacy. Retain seed as the formal reference and preserve every candidate; qualify the complete prospective trial before a population-retention decision.

| Member | Official F1 % | Intent % | Reliable % | Mean s | Non-first s | Calls | Equal-stratum F1 % | Equal-stratum intent % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| seed | 55.3907 | 70.00 | 100.00 | 34.055 | 34.295 | 131 | 43.6196 | 70.51 |
| seed-aa | 63.5379 | 70.00 | 100.00 | 33.693 | 33.141 | 122 | 45.8208 | 70.51 |
| branch-13 | 60.7339 | 65.00 | 100.00 | 26.984 | 27.254 | 98 | 48.0261 | 66.67 |
| branch-14 | 53.6598 | 70.00 | 100.00 | 40.702 | 41.580 | 89 | 43.8860 | 70.51 |
| branch-15 | 53.7102 | 65.00 | 100.00 | 80.902 | 81.000 | 116 | 39.1343 | 66.67 |
| branch-16 | 60.7339 | 65.00 | 100.00 | 26.583 | 25.947 | 98 | 48.0261 | 62.82 |

All tool-call counts are zero. Equal-stratum metrics are descriptive arithmetic means of stratum metrics, not the official pooled endpoint.

## Complete per-stratum results

Each cell is stratum F1 % / intent %. Sparse strata are descriptive.

| Stratum | N | seed | seed-aa | branch-13 | branch-14 | branch-15 | branch-16 |
|---|---:|---:|---:|---:|---:|---:|---:|
| audio | 3 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 |
| cooking | 2 | 50.00 / 50.00 | 100.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 | 40.00 / 50.00 | 50.00 / 50.00 |
| email | 1 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 0.00 |
| general | 2 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 0.00 | 0.00 / 50.00 |
| iot | 1 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 |
| lists | 1 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 59.09 / 100.00 | 100.00 / 100.00 |
| music | 2 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 0.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 |
| news | 1 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 |
| play | 2 | 40.00 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 49.32 / 100.00 | 80.24 / 100.00 | 66.67 / 100.00 |
| qa | 2 | 58.54 / 100.00 | 62.34 / 100.00 | 62.75 / 100.00 | 62.75 / 100.00 | 62.75 / 100.00 | 62.75 / 100.00 |
| recommendation | 1 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 |
| social | 1 | 51.85 / 0.00 | 0.00 / 0.00 | 78.26 / 0.00 | 41.79 / 0.00 | 0.00 / 0.00 | 78.26 / 0.00 |
| takeaway | 1 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 |

## First-admission and subsequent timing

| Member | First sample s | Non-first mean s | First slot-count mean s | Remaining mean s | Batch wall s/sample |
|---|---:|---:|---:|---:|---:|
| seed | 29.513 | 34.295 | 29.648 | 35.157 | 8.644 |
| seed-aa | 44.184 | 33.141 | 33.630 | 33.709 | 8.848 |
| branch-13 | 21.854 | 27.254 | 25.371 | 27.387 | 6.928 |
| branch-14 | 24.017 | 41.580 | 38.661 | 41.213 | 10.672 |
| branch-15 | 79.038 | 81.000 | 86.369 | 79.535 | 21.527 |
| branch-16 | 38.670 | 25.947 | 31.190 | 25.431 | 6.905 |

Monotonic admission-to-settled-workflow wall time includes internal model/tool waits, FIT and cleanup. Pre-admission wait is separate. Roster preparation, final persistence and official scoring are excluded. Batch wall per sample measures throughput, not individual latency.

First slot-count admissions are a diagnostic group, not a proven cold wave; the remaining samples are not guaranteed warm. No slow-sample trimming.

## Measured node timing and reuse

| Member / node | Contacts | Prefill ms/contact | Decode ms/contact | Transport ms/contact | Reused input fraction |
|---|---:|---:|---:|---:|---:|
| seed / perception | 20 | 685.397 | 6535.759 | 7482.584 | 0.6309 |
| seed / planner | 37 | 336.655 | 231.678 | 678.612 | 0.9493 |
| seed / reviewer | 37 | 276.757 | 8162.309 | 8718.031 | 0.9688 |
| seed / solver | 37 | 1777.556 | 1483.026 | 3711.434 | 0.6490 |
| seed-aa / perception | 20 | 736.088 | 5966.334 | 7176.151 | 0.6309 |
| seed-aa / planner | 34 | 349.589 | 233.160 | 707.172 | 0.9496 |
| seed-aa / reviewer | 34 | 244.985 | 8310.426 | 8805.168 | 0.9686 |
| seed-aa / solver | 34 | 1988.083 | 2295.128 | 4765.651 | 0.6117 |
| branch-13 / perception | 20 | 803.221 | 4497.861 | 5630.680 | 0.6268 |
| branch-13 / planner | 26 | 573.168 | 164.870 | 1054.983 | 0.9274 |
| branch-13 / reviewer | 26 | 555.966 | 4261.437 | 5432.451 | 0.9346 |
| branch-13 / solver | 26 | 3236.986 | 3966.330 | 8292.608 | 0.4968 |
| branch-14 / perception | 20 | 1155.479 | 8878.514 | 10434.816 | 0.5954 |
| branch-14 / planner | 23 | 4794.797 | 193.670 | 5863.887 | 0.1935 |
| branch-14 / reviewer | 23 | 526.127 | 9497.532 | 10446.181 | 0.9323 |
| branch-14 / solver | 23 | 4034.506 | 3683.437 | 8471.698 | 0.3063 |
| branch-15 / perception | 20 | 1656.906 | 13269.753 | 15278.526 | 0.5954 |
| branch-15 / planner | 32 | 5778.230 | 512.177 | 7303.118 | 0.1855 |
| branch-15 / reviewer | 32 | 4748.328 | 15479.449 | 21071.800 | 0.1939 |
| branch-15 / solver | 32 | 5410.608 | 4479.733 | 11118.248 | 0.1981 |
| branch-16 / perception | 20 | 707.395 | 4412.246 | 5397.118 | 0.6268 |
| branch-16 / planner | 26 | 605.980 | 151.842 | 1310.479 | 0.8952 |
| branch-16 / reviewer | 26 | 471.632 | 4133.434 | 4894.287 | 0.9332 |
| branch-16 / solver | 26 | 2976.201 | 3819.653 | 8334.683 | 0.4852 |

Timing/reuse associations do not establish causal node credit. Preserve independent node optimization space and official quality constraints.

## Paired exploratory comparisons

| Contrast | F1 change pp | 95% CI pp | Intent change pp | Repaired / damaged whole answers |
|---|---:|---|---:|---|
| branch-13-minus-aa | -2.8040 | [-24.5657, 16.3698] | -5.00 | 0 / 3 |
| branch-13-minus-parent | 5.3432 | [-5.9194, 15.3214] | -5.00 | 1 / 1 |
| branch-14-minus-aa | -9.8781 | [-27.4223, 3.7316] | 0.00 | 0 / 3 |
| branch-14-minus-parent | -1.7309 | [-9.0193, 4.4558] | 0.00 | 1 / 1 |
| branch-15-minus-aa | -9.8277 | [-27.9493, 3.5990] | -5.00 | 0 / 4 |
| branch-15-minus-parent | -1.6805 | [-17.6353, 13.1115] | -5.00 | 2 / 3 |
| branch-16-minus-aa | -2.8040 | [-24.6439, 16.4739] | -5.00 | 0 / 3 |
| branch-16-minus-parent | 5.3432 | [-5.9051, 15.2382] | -5.00 | 1 / 1 |
| same-request-null | 8.1472 | [-8.1796, 26.4851] | 0.00 | 3 / 0 |

Whole-answer transitions compare complete systems, not within-trajectory causal repair. The complete report retains unchanged-success and unchanged-failure cases. No N20 efficacy claim.

Source: data-root analysis/SAEA-SLURP-CONTEXT-TEMPLATE-PARTITIONED-UPDATE3-N20-V1-REMAINING-B2-READ-V1/report.json and timing-summary.json. Exact root READ: SAEA-SLURP-CONTEXT-TEMPLATE-PARTITIONED-UPDATE3-N20-V1-REMAINING-B2-READ-V1.
