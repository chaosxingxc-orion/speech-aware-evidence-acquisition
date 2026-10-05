# Complete original-a cost decomposition

Root-only diagnostic at 2026-10-05T21:59:40.070250+00:00. All sources belong to the already qualified complete original-a family. No active-family quality was read; no learner export or policy change.

The speed/quality tradeoff is not explained by a single cache metric. Branch-01 has fewer role visits and shorter Reviewer decoding, while its Solver input reuse is lower than the seed. Branch-04 and branch-07 show both low reuse in text roles and higher measured prefill burden. Reviewer decode remains large even when reuse is high. These observations identify costs to examine after the full population completes; they do not attribute causal contribution to a node.

| Member | Role | Calls/sample | Prefill seconds/sample | Decode seconds/sample | Mean output tokens/call | Input reuse fraction |
|---|---|---:|---:|---:|---:|---:|
| branch-01 | perception | 1.00 | 0.772 | 4.305 | 83.55 | 0.6250 |
| branch-01 | planner | 1.20 | 0.663 | 0.275 | 2.21 | 0.9241 |
| branch-01 | reviewer | 1.20 | 0.572 | 3.908 | 64.42 | 0.9324 |
| branch-01 | solver | 1.20 | 3.861 | 3.967 | 28.25 | 0.4637 |
| branch-02 | perception | 1.00 | 1.219 | 8.114 | 87.40 | 0.5934 |
| branch-02 | planner | 1.25 | 6.730 | 0.318 | 2.20 | 0.1896 |
| branch-02 | reviewer | 1.25 | 0.539 | 11.759 | 84.84 | 0.9330 |
| branch-02 | solver | 1.25 | 4.863 | 5.401 | 24.20 | 0.2927 |
| branch-03 | perception | 1.00 | 1.568 | 6.981 | 83.50 | 0.5934 |
| branch-03 | planner | 1.35 | 6.854 | 0.425 | 2.26 | 0.1883 |
| branch-03 | reviewer | 1.35 | 0.580 | 15.810 | 95.52 | 0.9333 |
| branch-03 | solver | 1.35 | 6.530 | 5.783 | 25.63 | 0.2840 |
| branch-04 | perception | 1.00 | 1.134 | 10.940 | 81.10 | 0.6256 |
| branch-04 | planner | 1.25 | 5.623 | 0.422 | 2.28 | 0.2204 |
| branch-04 | reviewer | 1.25 | 5.695 | 20.648 | 111.28 | 0.2306 |
| branch-04 | solver | 1.25 | 6.995 | 5.400 | 24.56 | 0.2296 |
| branch-05 | perception | 1.00 | 0.675 | 5.179 | 88.80 | 0.6248 |
| branch-05 | planner | 1.35 | 0.613 | 0.210 | 2.26 | 0.9255 |
| branch-05 | reviewer | 1.35 | 0.660 | 6.786 | 78.15 | 0.9342 |
| branch-05 | solver | 1.35 | 4.081 | 3.788 | 28.15 | 0.5157 |
| branch-06 | perception | 1.00 | 1.270 | 8.422 | 90.50 | 0.5949 |
| branch-06 | planner | 1.10 | 5.181 | 0.389 | 2.09 | 0.1900 |
| branch-06 | reviewer | 1.10 | 0.822 | 10.832 | 72.82 | 0.9342 |
| branch-06 | solver | 1.10 | 4.212 | 2.956 | 23.50 | 0.3054 |
| branch-07 | perception | 1.00 | 1.393 | 8.122 | 81.10 | 0.5944 |
| branch-07 | planner | 1.60 | 8.401 | 0.877 | 2.69 | 0.2036 |
| branch-07 | reviewer | 1.60 | 7.425 | 23.712 | 116.84 | 0.2218 |
| branch-07 | solver | 1.60 | 7.759 | 7.841 | 26.00 | 0.2196 |
| branch-08 | perception | 1.00 | 1.235 | 11.503 | 87.25 | 0.6269 |
| branch-08 | planner | 1.25 | 5.353 | 0.527 | 2.24 | 0.2272 |
| branch-08 | reviewer | 1.25 | 5.320 | 17.908 | 100.44 | 0.2360 |
| branch-08 | solver | 1.25 | 6.369 | 4.690 | 23.36 | 0.2366 |
| seed | perception | 1.00 | 0.786 | 5.835 | 125.05 | 0.6309 |
| seed | planner | 1.90 | 0.689 | 0.263 | 2.87 | 0.9484 |
| seed | reviewer | 1.90 | 0.423 | 16.052 | 159.18 | 0.9685 |
| seed | solver | 1.90 | 3.644 | 2.920 | 24.89 | 0.6535 |
| seed-aa | perception | 1.00 | 0.661 | 6.576 | 128.80 | 0.6309 |
| seed-aa | planner | 1.80 | 0.654 | 0.282 | 2.81 | 0.9516 |
| seed-aa | reviewer | 1.80 | 0.503 | 15.453 | 156.67 | 0.9697 |
| seed-aa | solver | 1.80 | 3.619 | 3.566 | 31.89 | 0.6325 |

Each value divides observed role contact totals by the actual completed sample count in the pinned timing report. Repeated visits are retained. Per-sample service sums differ from concurrent batch wall time and client workflow latency. No slow samples are trimmed.

Seed Reviewer: high input reuse does not remove output generation cost. Branch-01: lower Reviewer visit/output burden accompanies faster execution but reduced official pooled F1. Branch-04/07: weaker reuse accompanies greater prefill cost; a causal claim would need a separately registered controlled comparison. Do not reinstate fixed shared prefixes solely from these observations.

Keep role-specific template freedom and evaluate business quality jointly with mean/non-first latency. Complete the current registered population before any new learner update.

Data-root numeric evidence: coordination/partitioned-update3-scientific-preparation-v1/original-a-cost-diagnostic-v1.json
SHA256: f1ff2103172e215ff116b07e35acb6e4a3e904ed56b2c15318405d9328c212c2
