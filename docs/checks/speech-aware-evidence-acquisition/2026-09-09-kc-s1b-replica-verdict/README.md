# KC-S1b same-profile replication verdict

Verdict: **REPEATED_ENTITY_IMPROVEMENT_SAME_PROFILE**. The original64-token KC-S1b experiment completed1000 generation calls and one complete official scoring job, which retained per-sample statistics. No old scorer was rerun.

The prospectively primary historically exposed NEW500 sample satisfies both registered entity-side improvement tests against both historical controls. Paired speaker-cluster bootstrap uses10,000 replicates and seed20260903 (the shared helper offsets successive metrics deterministically). Scenario-stratified sensitivity agrees; natural and equal-scenario weightings remain positive.

| Comparator | Strict entity row-F1 delta / CI90 (pp) | SLU row-F1 delta / CI90 (pp) |
| --- | --- | --- |
| closed_list | +9.777 / [+7.744, +12.041] | +10.610 / [+8.476, +12.987] |
| kc_s1a | +9.687 / [+7.663, +11.978] | +10.674 / [+8.578, +13.048] |
| kc_s1b | -0.330 / [-1.482, +0.768] | -0.236 / [-1.410, +0.968] |

The historical KC-S1b comparison is descriptive: an interval spanning zero is not an equivalence result. Different-geometry and independent-roster inherited replication requirements remain open. The64 repeat is preserved; OWNER-KUS3-BUDGET-005 creates a separate256 matched control for subsequent retrieval contrasts.

The joined component view copies predecessor intent and keeps every parsed entity list unchanged for all1000 rows. It is a derived analysis artifact, not a new model run or proof of a live full-system join. Of the raw responses,507 include intent:505 match the predecessor and2 disagree;493 omit intent fields. The deterministic join restores predecessor intent for the component analysis; a live system must implement and verify that join. Three responses are unparsed. The raw scenario/action columns must not be presented as the component system intent performance.

Historical direct/KC-S1a per-row entity statistics were recovered from existing label-projection score products. Their manifests reference exactly the original output bytes; the projection function accepts only scenario/action, and all four official entity count blocks equal the original aggregate scores. Only unchanged entity metrics are reused. Projected intent correctness is excluded. Source files and hashes are frozen in configs/experiment/slurp-kc-s1b-replica-analysis-v1.json.

The complete per-population and per-stratum tables, both weightings, source hashes and join receipt are retained in summary.json. Official full-roster corpus micro SLU-F1 is44.7805%; the corresponding mean per-row SLU-F1 is28.6828%. Those are different estimators. NEW500 mean per-row SLU-F1 is31.6563%.

OBS reused the frozen speech input; ORG supplied the original TRAIN schema examples; SUPPLY used the same per-intent block; USE repeated the slot phase with a sealed intent predecessor. No new retrieval mechanism or reasoning treatment is tested by this repeat. The literal API request count is1000, with22228 completion tokens and2965694 prompt tokens; request latency sums to1909.866 seconds and is not GPU wall time. Stop reasons were not captured for this historical-compatible repeat and remain unavailable.

## NEW500 scenario table: per-row SLU-F1 (%)

| Scenario | n | Direct | KC-S1a | Historical KC-S1b | Repeat |
| --- | ---: | ---: | ---: | ---: | ---: |
| alarm | 30 | 23.98 | 27.51 | 35.42 | 36.83 |
| audio | 2 | 0.00 | 0.00 | 0.00 | 0.00 |
| calendar | 33 | 14.26 | 16.35 | 30.08 | 33.68 |
| cooking | 9 | 29.73 | 29.73 | 63.06 | 51.95 |
| datetime | 33 | 21.39 | 21.39 | 29.66 | 30.48 |
| email | 33 | 18.69 | 18.69 | 26.87 | 26.87 |
| general | 33 | 3.53 | 3.53 | 8.58 | 6.56 |
| iot | 33 | 31.81 | 30.17 | 43.56 | 45.21 |
| lists | 32 | 12.06 | 7.95 | 13.34 | 13.34 |
| music | 23 | 12.73 | 12.73 | 12.73 | 12.73 |
| news | 32 | 26.77 | 26.11 | 26.88 | 24.79 |
| play | 32 | 36.09 | 36.09 | 40.71 | 40.71 |
| qa | 32 | 34.01 | 34.01 | 46.51 | 40.26 |
| recommendation | 32 | 47.33 | 47.33 | 56.24 | 56.16 |
| social | 33 | 11.59 | 11.59 | 39.07 | 38.11 |
| takeaway | 12 | 11.57 | 11.57 | 25.46 | 19.90 |
| transport | 33 | 17.02 | 17.02 | 38.54 | 43.79 |
| weather | 33 | 6.08 | 6.08 | 21.23 | 21.23 |
