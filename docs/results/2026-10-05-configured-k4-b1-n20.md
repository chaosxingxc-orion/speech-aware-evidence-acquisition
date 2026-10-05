# Configured K4 remaining-b1: complete twenty-input comparison

All 6 registered members independently finalized with verified seals, exactly one successful complete official score each and zero failed jobs. Exact root READ: `SAEA-SLURP-CONTEXT-TEMPLATE-K4-RECOVERY1-N20-V1-REMAINING-B1-READ-V1`. The configured family contains120 trajectories and660 model contacts. No score was replayed. This is repeated-input optimization, not independent validation.

Retain the seed parent. No tested candidate improves all business objectives: branch09 trades lower SLU-F1 for higher intent and shorter latency; branch10 trades lower F1 and higher latency for higher intent. Branch11 and branch12 are descriptively dominated by seed on quality, intent and measured latency. Complete the unchanged remaining original branches13-16 before a separately qualified population learning update. N20 does not establish stable benefit or learning gain.

## Quality and latency

| Member | SLU-F1 % | Intent % | Reliable % | Calls | Mean s | First s | Non-first s | First4 mean s | Remaining16 mean s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| seed | 59.2593 | 70.00 | 100.0 | 119 | 32.021 | 63.526 | 30.363 | 38.368 | 30.434 |
| seed-aa | 58.5502 | 70.00 | 100.0 | 119 | 31.706 | 57.580 | 30.344 | 36.753 | 30.444 |
| branch-09 | 53.6587 | 75.00 | 100.0 | 95 | 27.389 | 27.850 | 27.365 | 24.780 | 28.041 |
| branch-10 | 53.1118 | 80.00 | 100.0 | 95 | 41.546 | 28.399 | 42.238 | 37.637 | 42.523 |
| branch-11 | 57.1623 | 70.00 | 100.0 | 119 | 79.614 | 70.657 | 80.085 | 71.669 | 81.600 |
| branch-12 | 54.7266 | 55.00 | 100.0 | 113 | 76.330 | 38.613 | 78.315 | 59.971 | 80.420 |

Latency is admission-to-settled-workflow, including internal model/tool waits and FIT, excluding pre-admission wait, preparation, final persistence and scoring. First4/rest16 are descriptive admission groups, not proven cold/warm batches. No slow-sample trimming. All members retain the same observed admission order.

Branch09 non-first latency falls9.87% versus seed while F1 falls5.60points and intent rises5points. All four candidate F1 intervals versus seed and A/A cross zero. Do not interpret this as proven harm or benefit. Same-request A/A differs by-0.7091F1 points with unchanged intent. Fixed temperature/seed do not establish bitwise identical outputs.

## Paired comparisons

| Contrast | F1 delta pp | F1 CI95 pp | Intent delta pp | Repaired exact answers | Damaged exact answers |
|---|---:|---|---:|---:|---:|
| branch-09-minus-aa | -4.8914 | [-15.2578, 5.1987] | 5.00 | 1 | 2 |
| branch-09-minus-parent | -5.6005 | [-16.1434, 5.5845] | 5.00 | 1 | 2 |
| branch-10-minus-aa | -5.4384 | [-16.1039, 3.7703] | 10.00 | 1 | 3 |
| branch-10-minus-parent | -6.1475 | [-17.2566, 4.6654] | 10.00 | 1 | 3 |
| branch-11-minus-aa | -1.3879 | [-14.1690, 11.2560] | 0.00 | 0 | 2 |
| branch-11-minus-parent | -2.0969 | [-12.7122, 10.1652] | 0.00 | 0 | 2 |
| branch-12-minus-aa | -3.8236 | [-18.5382, 7.4729] | -15.00 | 0 | 4 |
| branch-12-minus-parent | -4.5327 | [-20.3423, 8.5167] | -15.00 | 0 | 4 |
| same-request-null | -0.7091 | [-8.1709, 9.5934] | 0.00 | 0 | 0 |

Exact-answer changes compare complete systems; they are not node causal credit or within-trajectory repair attribution. The same-cohort measured frontier contains branch-09, branch-10, seed. Keep A/A as a null observation, not another selectable policy. No cross-cohort normalization or frontier.

## Per-node observed cost

| Member | Node | Contacts | Mean prefill s | Mean decode s | Mean transport s | Input reuse % |
|---|---|---:|---:|---:|---:|---:|
| seed | perception | 20 | 0.770 | 5.846 | 7.095 | 63.09 |
| seed | planner | 33 | 0.418 | 0.261 | 0.953 | 94.92 |
| seed | reviewer | 33 | 0.269 | 7.247 | 7.701 | 96.75 |
| seed | solver | 33 | 2.227 | 2.287 | 4.832 | 59.83 |
| seed-aa | perception | 20 | 0.657 | 5.770 | 6.598 | 63.09 |
| seed-aa | planner | 33 | 0.322 | 0.096 | 0.562 | 94.95 |
| seed-aa | reviewer | 33 | 0.344 | 8.129 | 8.799 | 96.82 |
| seed-aa | solver | 33 | 2.090 | 2.258 | 4.720 | 60.40 |
| branch-09 | perception | 20 | 0.801 | 6.187 | 7.372 | 62.67 |
| branch-09 | planner | 25 | 0.573 | 0.335 | 1.617 | 92.54 |
| branch-09 | reviewer | 25 | 0.586 | 4.000 | 4.936 | 92.76 |
| branch-09 | solver | 25 | 3.196 | 3.483 | 7.692 | 45.37 |
| branch-10 | perception | 20 | 1.298 | 7.099 | 8.961 | 59.52 |
| branch-10 | planner | 25 | 5.507 | 0.268 | 6.393 | 19.38 |
| branch-10 | reviewer | 25 | 0.592 | 6.912 | 7.890 | 92.02 |
| branch-10 | solver | 25 | 4.035 | 4.036 | 10.094 | 29.94 |
| branch-11 | perception | 20 | 1.726 | 12.243 | 15.307 | 59.52 |
| branch-11 | planner | 33 | 5.424 | 0.667 | 7.006 | 19.00 |
| branch-11 | reviewer | 33 | 4.540 | 13.661 | 19.058 | 19.86 |
| branch-11 | solver | 33 | 5.561 | 5.668 | 11.613 | 20.32 |
| branch-12 | perception | 20 | 1.165 | 10.973 | 12.490 | 62.72 |
| branch-12 | planner | 31 | 5.645 | 0.534 | 6.732 | 20.99 |
| branch-12 | reviewer | 31 | 4.463 | 13.874 | 18.976 | 21.85 |
| branch-12 | solver | 31 | 6.930 | 6.240 | 14.108 | 21.80 |

These contact-weighted timings are observations, not isolated causal effects or per-node task accuracy. Branch11 Reviewer prefill is4.540s versus seed0.269s and decode13.661s versus7.247s; Perception decode also increases. Branch09 Reviewer decode is4.000s and visits fall from33 to25, but Solver prefill/decode rises. Fewer contacts or higher cache reuse alone cannot determine whole-system business benefit. Preserve independent node templates; prioritize avoiding unnecessary generation/revision and preserving slot accuracy during future learning.

## Every stratum

Cells contain SLU-F1% / intent%; empty entities retain official counting semantics.

| Stratum | N | seed | seed-aa | branch-09 | branch-10 | branch-11 | branch-12 |
|---|---:|---:|---:|---:|---:|---:|---:|
| audio | 3 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 33.33 |
| cooking | 2 | 50.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 |
| email | 1 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 |
| general | 2 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 |
| iot | 1 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 |
| lists | 1 | 100.00 / 100.00 | 100.00 / 100.00 | 59.09 / 100.00 | 59.09 / 100.00 | 59.09 / 100.00 | 59.09 / 100.00 |
| music | 2 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 50.00 | 0.00 / 0.00 |
| news | 1 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 |
| play | 2 | 66.67 / 100.00 | 66.67 / 100.00 | 40.00 / 100.00 | 49.32 / 100.00 | 80.24 / 100.00 | 80.00 / 50.00 |
| qa | 2 | 62.75 / 100.00 | 53.73 / 100.00 | 62.75 / 100.00 | 62.75 / 100.00 | 62.34 / 100.00 | 47.76 / 50.00 |
| recommendation | 1 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 |
| social | 1 | 0.00 / 0.00 | 53.85 / 0.00 | 41.79 / 0.00 | 41.79 / 100.00 | 0.00 / 0.00 | 41.79 / 100.00 |
| takeaway | 1 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 50.00 / 100.00 | 66.67 / 100.00 |

Equal-stratum means are descriptive and do not replace official pooled quality.

| Member | Equal-stratum F1 % | Equal-stratum intent % |
|---|---:|---:|
| seed | 42.006 | 70.513 |
| seed-aa | 45.455 | 70.513 |
| branch-09 | 40.023 | 74.359 |
| branch-10 | 40.739 | 82.051 |
| branch-11 | 38.590 | 70.513 |
| branch-12 | 41.947 | 64.103 |

## Execution and disposition

Driver14:14:56Z completed14:53:52Z. All120 deliveries are reliable with zero abstention/tool calls. Six completed guards recorded413 valid Windows memory samples, minimum23.1887GiB and zero observer errors. This is historical campaign evidence, not current health or proof that smaller K caused memory savings. The15-minute monitor was deleted after terminal verification.

The zero-contact READ ledger profile was corrected from bounded-discovery-probe to model-free-check after the existing reader refused before quality access. Both original rows and root disposition are preserved. No frozen/runtime/recipe/scoring byte changed. Analysis supplements were pinned after launch and before quality read; preserve this chronology.

Root approves one complete-cohort clean-file-cache boundary with all competing work idle and before/after service/memory evidence, then unchanged remaining-b2 admission and all frozen/live checks. No current candidate adoption, extra dataset, policy edit, partial optimizer export or scale follows from this review. Other-carrier holds and human-before8x400 remain.

Analysis evidence: `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-CONTEXT-TEMPLATE-K4-RECOVERY1-N20-V1-REMAINING-B1-READ-V1`. Full official receipts, paired estimates, node/sample timing and source pins remain there.
