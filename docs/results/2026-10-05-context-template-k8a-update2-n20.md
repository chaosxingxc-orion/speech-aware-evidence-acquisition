# K8A update-two: complete twenty-input template panel

Ten independently finalized members produced200 trajectories with one unique successful official score per member and zero failures. Exact root READ: `SAEA-SLURP-CONTEXT-TEMPLATE-K8A-UPDATE2-N20-POST-OBSERVER-READ-V1`. All original template policies were preserved. This is the first partition of the original sixteen-candidate update-two population,not an independent search replicate. It is same-input optimization;N20 does not establish stable benefit or generalization.

The execution base completed this panel. No candidate is formally adopted: branch08 increases entity/SLU-F1 on this small cohort but reduces intent and approximately doubles non-first latency. Branch01 is faster but reduces both quality metrics. Keep the seed as formal parent and execute the original unchanged K8B population before any future separately registered learning decision.

## Complete quality and sample timing

| Member | SLU-F1 % | Intent % | Reliable % | Calls | Mean s | First s | Non-first mean s | First4 mean s | Rest16 mean s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| seed | 55.4795 | 70.00 | 100.0 | 125 | 33.851 | 46.696 | 33.175 | 34.616 | 33.660 |
| seed-aa | 59.5867 | 70.00 | 100.0 | 131 | 34.341 | 31.940 | 34.467 | 28.445 | 35.815 |
| branch-01 | 51.3422 | 65.00 | 100.0 | 98 | 27.203 | 43.635 | 26.338 | 32.791 | 25.806 |
| branch-02 | 50.6396 | 70.00 | 100.0 | 98 | 44.880 | 27.365 | 45.802 | 37.565 | 46.709 |
| branch-03 | 53.6290 | 70.00 | 100.0 | 107 | 73.256 | 61.924 | 73.852 | 63.105 | 75.793 |
| branch-04 | 52.0163 | 55.00 | 100.0 | 107 | 72.399 | 100.344 | 70.929 | 68.106 | 73.473 |
| branch-05 | 51.2215 | 60.00 | 100.0 | 104 | 28.645 | 55.931 | 27.209 | 35.549 | 26.919 |
| branch-06 | 51.7378 | 65.00 | 100.0 | 95 | 42.789 | 24.600 | 43.747 | 37.497 | 44.112 |
| branch-07 | 55.1924 | 65.00 | 100.0 | 110 | 75.789 | 43.658 | 77.480 | 53.705 | 81.310 |
| branch-08 | 63.8668 | 55.00 | 100.0 | 104 | 67.134 | 101.477 | 65.326 | 69.650 | 66.505 |

All members retain the same observed admission order. Mean latency spans admission to settled workflow,including internal model/tool waits and FIT;it excludes pre-admission wait,preparation,persistence and official scoring. First4/rest16 are descriptive groups,not proven cold/warm batches. Do not trim slow samples or confuse batch throughput with individual latency.

Branch08 minus seed F1: 8.3874 percentage points,95% clustered interval [-5.3830,24.6515]. Versus A/A: 4.2801 points,interval [-10.6763,17.8211]. Both intervals cross zero. Intent falls15points. The same-request A/A F1 spread is4.1072points despite fixed temperature0 and seed;do not claim bitwise deterministic outputs. Its cause is not established here.

The latency-aware same-panel frontier contains branch-01, branch-08, seed. The duplicate seed/A/A bundle is retained as two descriptive measurements in the table,not two policies. The older call-count frontier in report.json is a separate diagnostic;it does not replace measured sample latency. No cross-panel frontier or half-population optimizer export.

## Per-node observed cost

| Member | Node | Contacts | Mean prefill s | Mean decode s | Mean transport s | Input reuse % |
|---|---|---:|---:|---:|---:|---:|
| seed | perception | 20 | 0.720 | 5.095 | 6.209 | 63.09 |
| seed | planner | 35 | 0.335 | 0.129 | 0.604 | 94.88 |
| seed | reviewer | 35 | 0.234 | 9.126 | 9.448 | 96.78 |
| seed | solver | 35 | 1.766 | 2.244 | 4.444 | 63.54 |
| seed-aa | perception | 20 | 0.692 | 6.274 | 7.183 | 63.09 |
| seed-aa | planner | 37 | 0.378 | 0.207 | 0.714 | 94.82 |
| seed-aa | reviewer | 37 | 0.273 | 8.217 | 8.800 | 96.82 |
| seed-aa | solver | 37 | 1.792 | 1.645 | 3.817 | 64.58 |
| branch-01 | perception | 20 | 0.830 | 5.361 | 6.792 | 62.50 |
| branch-01 | planner | 26 | 0.603 | 0.383 | 1.211 | 92.04 |
| branch-01 | reviewer | 26 | 0.481 | 5.085 | 5.750 | 92.23 |
| branch-01 | solver | 26 | 2.740 | 3.311 | 6.774 | 48.59 |
| branch-02 | perception | 20 | 1.073 | 9.369 | 10.761 | 59.34 |
| branch-02 | planner | 26 | 4.562 | 0.233 | 5.313 | 19.00 |
| branch-02 | reviewer | 26 | 0.691 | 9.683 | 11.110 | 92.14 |
| branch-02 | solver | 26 | 4.315 | 3.490 | 8.422 | 28.94 |
| branch-03 | perception | 20 | 1.617 | 10.914 | 12.851 | 59.34 |
| branch-03 | planner | 29 | 5.704 | 0.602 | 7.902 | 18.84 |
| branch-03 | reviewer | 29 | 5.016 | 15.425 | 21.135 | 19.72 |
| branch-03 | solver | 29 | 5.709 | 4.498 | 11.017 | 20.14 |
| branch-04 | perception | 20 | 1.252 | 11.307 | 13.029 | 62.55 |
| branch-04 | planner | 29 | 5.244 | 0.457 | 6.373 | 21.51 |
| branch-04 | reviewer | 29 | 4.904 | 13.940 | 19.695 | 22.36 |
| branch-04 | solver | 29 | 6.901 | 5.189 | 13.217 | 22.34 |
| branch-05 | perception | 20 | 0.679 | 4.728 | 5.701 | 62.65 |
| branch-05 | planner | 28 | 0.492 | 0.308 | 1.063 | 92.19 |
| branch-05 | reviewer | 28 | 0.612 | 5.302 | 6.280 | 92.47 |
| branch-05 | solver | 28 | 2.941 | 3.244 | 7.394 | 51.95 |
| branch-06 | perception | 20 | 1.229 | 8.263 | 9.727 | 59.50 |
| branch-06 | planner | 25 | 5.056 | 0.209 | 5.570 | 19.12 |
| branch-06 | reviewer | 25 | 0.646 | 8.305 | 9.482 | 92.13 |
| branch-06 | solver | 25 | 4.364 | 4.139 | 9.777 | 29.48 |
| branch-07 | perception | 20 | 1.609 | 12.866 | 14.845 | 59.50 |
| branch-07 | planner | 30 | 5.094 | 0.392 | 5.919 | 18.43 |
| branch-07 | reviewer | 30 | 5.967 | 15.123 | 22.371 | 19.23 |
| branch-07 | solver | 30 | 5.869 | 4.409 | 10.824 | 19.67 |
| branch-08 | perception | 20 | 1.186 | 12.776 | 14.401 | 62.70 |
| branch-08 | planner | 28 | 4.543 | 0.379 | 5.482 | 21.89 |
| branch-08 | reviewer | 28 | 4.588 | 13.305 | 18.851 | 22.78 |
| branch-08 | solver | 28 | 5.477 | 5.061 | 11.699 | 22.76 |

These are contact-weighted means,not isolated causal effects or per-node accuracy. Server and client timing boundaries differ;do not subtract them to invent queue time or sum concurrent contacts as experiment wall time.

Branch08 Reviewer prefill rises from0.234s to4.588s per contact and decode from9.126s to13.305s;its input reuse falls from96.78% to22.78%. Perception decode also rises from5.095s to12.776s. Both prompt processing and generation contribute observed cost;cache misses alone are not a complete explanation. Fewer model calls (104 versus125) do not guarantee lower end-to-end latency. Keep independent node optimization space;these measurements do not justify restoring mandatory common-prefix text.

## Every stratum

Cells contain SLU-F1% / intent%. Small strata and empty-entity counting can produce zero entity F1 without zero intent;retain the official counting semantics. Equal-stratum numbers below are descriptive macros and do not replace official pooled F1.

| Stratum | N | seed | seed-aa | branch-01 | branch-02 | branch-03 | branch-04 | branch-05 | branch-06 | branch-07 | branch-08 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| audio | 3 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 |
| cooking | 2 | 50.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 | 40.00 / 50.00 | 50.00 / 50.00 | 0.00 / 50.00 | 50.00 / 50.00 | 40.00 / 50.00 | 50.00 / 50.00 |
| email | 1 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 |
| general | 2 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| iot | 1 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 |
| lists | 1 | 100.00 / 100.00 | 100.00 / 100.00 | 59.09 / 100.00 | 59.09 / 100.00 | 59.09 / 100.00 | 59.09 / 100.00 | 59.09 / 100.00 | 59.09 / 100.00 | 59.09 / 100.00 | 59.09 / 100.00 |
| music | 2 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 |
| news | 1 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 |
| play | 2 | 66.67 / 100.00 | 62.46 / 100.00 | 62.46 / 100.00 | 40.00 / 100.00 | 80.24 / 100.00 | 50.00 / 50.00 | 73.03 / 100.00 | 49.32 / 100.00 | 80.24 / 100.00 | 80.00 / 50.00 |
| qa | 2 | 53.73 / 100.00 | 62.75 / 100.00 | 37.21 / 50.00 | 62.75 / 100.00 | 62.75 / 100.00 | 62.75 / 100.00 | 62.75 / 100.00 | 62.75 / 100.00 | 62.75 / 100.00 | 62.75 / 100.00 |
| recommendation | 1 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 |
| social | 1 | 0.00 / 0.00 | 41.79 / 0.00 | 0.00 / 0.00 | 41.79 / 0.00 | 41.79 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 41.79 / 0.00 | 0.00 / 0.00 | 78.26 / 0.00 |
| takeaway | 1 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 0.00 |

| Member | Equal-stratum F1 % | Equal-stratum intent % |
|---|---:|---:|
| seed | 41.313 | 70.513 |
| seed-aa | 44.897 | 70.513 |
| branch-01 | 36.571 | 66.667 |
| branch-02 | 40.023 | 70.513 |
| branch-03 | 42.349 | 70.513 |
| branch-04 | 37.577 | 55.128 |
| branch-05 | 35.502 | 58.974 |
| branch-06 | 40.739 | 66.667 |
| branch-07 | 39.134 | 66.667 |
| branch-08 | 45.905 | 55.128 |

## Execution and resource disposition

All200 deliveries are reliable under the registered definition;no abstentions or knowledge-tool contacts. 1079 model contacts were charged. Ten completed resource guards contain757 physical Windows samples,minimum25.2829GiB,zero guard failures. This is historical campaign evidence,not current health. No causal K16-to-K8 memory benefit is established;the original system also executed members sequentially.

Driver epoch10:36:59Z completed11:47:12Z. Root confirmed no admitted driver/worker/scorer remains,no STOP,and deleted slurp-k8a-post-observer-15m. Preserve all controls and frozen sources. Official scoring-worker totals remain separate from sample latency;the earlier slow first finalizer remains unattributed.

Root approves prospective unchanged K8B admission after this complete review. This is engineering/stage progression,not benefit adoption or scale. No updates between panels. Preserve failed old attempts and other-carrier holds;return to human before8x400.

## Source evidence

Data-root analysis directory: `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-CONTEXT-TEMPLATE-K8A-UPDATE2-N20-POST-OBSERVER-READ-V1`. It contains complete report.json,per-member saved official score links,source-bound node/sample timing,and all pairwise confidence intervals/repair-damage counts. No scorer was replayed. The repository continuation receipt pins these sources.
