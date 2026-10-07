# Same20 simple-consumption comparison: complete root business read

Recorded at 2026-10-07T15:48:56.278062+00:00.

All four members independently finalized20 trajectories, with verified seals, one unique successful complete official score and zero failed jobs each. Root read the complete family through the unchanged official-count reader. This is a manual architecture comparison on previously exposed20 inputs, not a learned L/B comparison or independent validation.

| Member | Official SLU-F1 | Intent | Reliable completion | Model/tool calls | First sample seconds | Remaining19 mean seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| seed | 62.3261% | 70.00% | 100.00% | 122/0 | 30.576 | 29.055 |
| seed-aa | 60.3123% | 70.00% | 100.00% | 125/0 | 47.860 | 32.196 |
| review-off | 55.9689% | 75.00% | 100.00% | 40/0 | 15.158 | 16.111 |
| solver-lookup | 59.1619% | 65.00% | 100.00% | 44/4 | 18.895 | 21.697 |

Individual latency is measured from admission to settled workflow, including internal waits/FIT/cleanup; pre-admission queueing, roster preparation, final persistence and scoring are separate. First admission does not prove a cold cache; remaining samples do not prove warm cache.

## Interpretation and next action

Retain seed as the current reference. Review-off reduces remaining-sample mean latency by about44.6%, while its observed official F1 is6.36percentage points below seed and4.34 below A/A. Solver-lookup is about25.3% faster than seed on this latency measure, but observed F1 is3.16points lower and intent is5points lower. Four tool calls establish actual tool use, not tool effectiveness. Neither candidate warrants quality-based adoption or automatic scale-up.

The seed/A/A F1 difference is2.01points even with fixed configuration. Preserve this observed repeat variation and do not attribute every candidate difference to architecture. Complete-system exact-answer comparisons show review-off loses one previously correct answer and gains none; lookup gains one and loses one. These are between-system associations, not causal node credit.

Stay at20 while completing the source-bound process read: initial delivered knowledge/candidate coverage, Reviewer detection and false alarms, repair/harm, raw-versus-normalized delivery, and node timing. Use those measurements to define a prospective focused revision. No data/knowledge rebuild, learner export or automatic50/100/200 admission. Return to the owner before8x400 or equivalent splitting.

## Paired official F1 differences

| Contrast | Difference pp | Registered95% paired bootstrap interval pp |
| --- | ---: | --- |
| review-off-minus-aa | -4.3434 | [-12.8577, 0.0000] |
| review-off-minus-parent | -6.3572 | [-14.5111, 0.0000] |
| same-request-null | -2.0138 | [-5.5992, 0.0000] |
| solver-lookup-minus-aa | -1.1505 | [-15.5615, 11.6801] |
| solver-lookup-minus-parent | -3.1642 | [-16.4255, 7.3566] |

Intervals are descriptive on this reused small roster; they do not establish stable benefit, generalization or feedback-learning superiority.

## Every stratum

| Stratum | N | Seed F1/intent% | A/A F1/intent% | Review-off F1/intent% | Lookup F1/intent% |
| --- | ---: | --- | --- | --- | --- |
| audio | 3 | 0.00/66.67 | 0.00/66.67 | 0.00/66.67 | 0.00/66.67 |
| cooking | 2 | 50.00/50.00 | 50.00/50.00 | 50.00/50.00 | 50.00/50.00 |
| email | 1 | 0.00/100.00 | 0.00/100.00 | 0.00/100.00 | 0.00/100.00 |
| general | 2 | 0.00/50.00 | 0.00/50.00 | 0.00/50.00 | 0.00/50.00 |
| iot | 1 | 0.00/100.00 | 0.00/100.00 | 0.00/100.00 | 0.00/100.00 |
| lists | 1 | 100.00/100.00 | 100.00/100.00 | 100.00/100.00 | 100.00/100.00 |
| music | 2 | 0.00/50.00 | 0.00/50.00 | 0.00/50.00 | 0.00/50.00 |
| news | 1 | 100.00/0.00 | 100.00/0.00 | 100.00/0.00 | 100.00/0.00 |
| play | 2 | 66.67/100.00 | 66.67/100.00 | 40.00/100.00 | 66.67/100.00 |
| qa | 2 | 62.75/100.00 | 62.75/100.00 | 62.75/100.00 | 43.24/50.00 |
| recommendation | 1 | 100.00/100.00 | 100.00/100.00 | 100.00/100.00 | 100.00/100.00 |
| social | 1 | 53.85/0.00 | 41.79/0.00 | 41.79/100.00 | 78.26/0.00 |
| takeaway | 1 | 66.67/100.00 | 66.67/100.00 | 66.67/100.00 | 66.67/100.00 |

Equal-stratum macro F1/intent percentages: seed 46.15/70.51; seed-aa 45.22/70.51; review-off 43.17/78.21; solver-lookup 46.53/66.67. This differs from the primary pooled official endpoint.

## Engineering findings and custody

The original sealed-vector loader retained whole-file bytes, decoded lines and parsed vectors concurrently. Bounded decoding removed proportional temporary buffers while preserving all vectors and exact retrieval outputs. The original source profile peaked around1.96GiB; it did not explain the historically reported20GiB host-memory decrease. The complete repaired80-trajectory campaign used at most2226.51MiB measured worker PSS, and Windows available memory stayed at least15.85GiB. The memory failure did not recur in this run.

Offline analysis exposed two metadata-contract defects: incomplete native-count projection and missing wrapper measurement_profile. Preserve both failed derivative directories. A separate corrected metadata package and independently appended signed READ row reused the same original scores. No generation, sealing or official scoring was replayed. Original signed records remain unchanged; the attempted replacement was rejected by automatic approval review and was not executed.

The15-minute experiment monitor was deleted after terminal closure and child-process exit. Frozen worker b282ed3c42231eb6366607b691d70488dfcc9502 remains unchanged.
