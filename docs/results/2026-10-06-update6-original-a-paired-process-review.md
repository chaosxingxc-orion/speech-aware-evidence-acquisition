# Update6 original-a: paired process supplement

Root analysis completed 2026-10-06T21:49:04.882248+00:00.

The exact original-a READ is already countersigned. This supplement uses the registered paired-process plan and all ten complete members; it adds no model/scorer contacts, reruns, selection changes or learner export. The remaining cohorts are still required before the original whole-population retention decision.

## Business interpretation

The [complete cohort report](2026-10-06-update6-original-a-complete-review.md) remains the authoritative official SLU-F1, intent, reliability, cost and per-scenario/equal-stratum presentation. None of its eight candidates exceeds the current seed F1; every candidate-minus-A/A F1 interval includes zero. The seed/A/A variation remains material. The diagnostics below add no formal efficacy verdict and do not promote any candidate.

## Clarify alarm semantics before optimizing them

The registered `false_alarm_event` and conditional `review_false_alarm` use **entity correctness of the initial draft**, not full-task correctness or semantic correctness of the critique. An entity-correct draft may still have an incorrect intent. Consequently, prior shorthand descriptions of alarms on correct drafts mean entity-correct drafts. Preserve all original pinned results; this clarification supersedes a broader interpretation, not their numerical values.

Likewise, an alarm on an entity-incorrect draft does not prove that the critique identified its actual error. Alarm quantity is insufficient as a learning objective. Inspect eventual business quality and raw-model repair/damage alongside delivered-endpoint transitions. The latter include postprocessing and cannot be assigned solely to Reviewer behavior.

## Matched-input descriptive comparisons

All differences are candidate minus comparator. Correctness and alarm values are percentage-point differences; net transition is additional repairs minus harms per100 inputs. Intervals are paired percentile bootstrap95percent with2000 replicates and fixed seed20261006. They describe the matched-known subset, without multiplicity/adaptive-search adjustment. Missing-data bounds are worst-case full-roster identification bounds, not confidence intervals. A zero-width interval does not establish zero uncertainty.

| Candidate | Comparator | Draft full correctness delta [CI] | Final full correctness delta [CI] | Full net transition delta [CI] |
| --- | --- | ---: | ---: | ---: |
| branch-01 | seed | -15.00 [-30.00, +0.00] | -15.00 [-30.00, +0.00] | +0.00 [+0.00, +0.00] |
| branch-01 | seed-aa | -10.00 [-30.00, +10.00] | -5.00 [-25.00, +15.00] | +5.00 [+0.00, +15.00] |
| branch-02 | seed | -10.00 [-30.00, +10.00] | -15.00 [-30.00, +0.00] | -5.00 [-15.00, +0.00] |
| branch-02 | seed-aa | -5.00 [-20.00, +10.00] | -5.00 [-20.00, +10.00] | +0.00 [+0.00, +0.00] |
| branch-03 | seed | -5.00 [-20.00, +10.00] | -20.00 [-40.00, -5.00] | -15.00 [-35.00, +0.00] |
| branch-03 | seed-aa | +0.00 [-20.00, +20.00] | -10.00 [-30.00, +10.00] | -10.00 [-25.00, +0.00] |
| branch-04 | seed | -5.00 [-20.00, +10.00] | -15.00 [-30.00, +0.00] | -10.00 [-30.00, +10.00] |
| branch-04 | seed-aa | +0.00 [-20.00, +20.00] | -5.00 [-25.00, +15.00] | -5.00 [-25.00, +10.00] |
| branch-05 | seed | -10.00 [-35.00, +15.00] | -15.00 [-35.00, +5.00] | -5.00 [-15.00, +0.00] |
| branch-05 | seed-aa | -5.00 [-25.00, +15.00] | -5.00 [-25.00, +15.00] | +0.00 [+0.00, +0.00] |
| branch-06 | seed | -5.00 [-20.00, +10.00] | -10.00 [-25.00, +0.00] | -5.00 [-15.00, +0.00] |
| branch-06 | seed-aa | +0.00 [-20.00, +20.00] | +0.00 [-20.00, +20.00] | +0.00 [+0.00, +0.00] |
| branch-07 | seed | +0.00 [-15.00, +15.00] | -15.00 [-30.00, +0.00] | -15.00 [-30.00, +0.00] |
| branch-07 | seed-aa | +5.00 [-10.00, +20.00] | -5.00 [-25.00, +15.00] | -10.00 [-25.00, +0.00] |
| branch-08 | seed | -5.00 [-20.00, +10.00] | -10.00 [-25.00, +0.00] | -5.00 [-15.00, +0.00] |
| branch-08 | seed-aa | +0.00 [-20.00, +20.00] | +0.00 [-20.00, +20.00] | +0.00 [+0.00, +0.00] |
| seed-aa | seed | -5.00 [-15.00, +0.00] | -10.00 [-25.00, +0.00] | -5.00 [-15.00, +0.00] |

All full-correctness and full-transition contrasts above have20 paired-known inputs and zero unknown pairs. Full-task correctness is a diagnostic binary endpoint, not the official pooled SLU-F1.

| Candidate | Comparator | Entity-correct-draft alarm event delta [CI] | Paired known / unknown | Full-roster missing bounds |
| --- | --- | ---: | ---: | ---: |
| branch-01 | seed | +0.00 [+0.00, +0.00] | 12 / 8 | [-40.00, +40.00] |
| branch-01 | seed-aa | -18.18 [-45.45, +0.00] | 11 / 9 | [-55.00, +35.00] |
| branch-02 | seed | +5.88 [+0.00, +17.65] | 17 / 3 | [-10.00, +20.00] |
| branch-02 | seed-aa | -12.50 [-37.50, +12.50] | 16 / 4 | [-30.00, +10.00] |
| branch-03 | seed | +37.50 [+12.50, +62.50] | 16 / 4 | [+10.00, +50.00] |
| branch-03 | seed-aa | +20.00 [-6.67, +46.67] | 15 / 5 | [-10.00, +40.00] |
| branch-04 | seed | +18.75 [+0.00, +37.50] | 16 / 4 | [-5.00, +35.00] |
| branch-04 | seed-aa | +0.00 [-20.00, +20.00] | 15 / 5 | [-25.00, +25.00] |
| branch-05 | seed | -6.25 [-18.75, +0.00] | 16 / 4 | [-25.00, +15.00] |
| branch-05 | seed-aa | -21.43 [-42.86, +0.00] | 14 / 6 | [-45.00, +15.00] |
| branch-06 | seed | -5.88 [-17.65, +0.00] | 17 / 3 | [-20.00, +10.00] |
| branch-06 | seed-aa | -18.75 [-37.50, +0.00] | 16 / 4 | [-35.00, +5.00] |
| branch-07 | seed | +50.00 [+25.00, +75.00] | 16 / 4 | [+20.00, +60.00] |
| branch-07 | seed-aa | +33.33 [+0.00, +66.67] | 15 / 5 | [+0.00, +50.00] |
| branch-08 | seed | +17.65 [-5.88, +41.18] | 17 / 3 | [+0.00, +30.00] |
| branch-08 | seed-aa | +6.67 [+0.00, +20.00] | 15 / 5 | [-20.00, +30.00] |
| seed-aa | seed | +20.00 [+0.00, +40.00] | 15 / 5 | [-10.00, +40.00] |

Alarm-event rates above use the same matched-known input denominator in both arms. They are not conditional false-alarm rates on each arm's own correct-draft subset.

## What changes the next algorithm question

- Branch03 and branch07 have more alarms on entity-correct drafts than seed on their16 paired-known inputs: +37.5 and+50.0 points respectively. Against A/A the differences are+20.0 and+33.3 points on15 matched-known inputs and intervals include or touch zero. Four or five unknown pairs remain explicit.
- Their final full-task correctness differences versus seed are-20 and-15 points, while their draft differences are-5 and0 points. Their draft-to-delivered net-transition differences are each-15 per100 inputs. This associates later processing with degradation in these observed systems; it does not isolate causal Reviewer contribution.
- Branch05 triggers fewer alarms and revisions but does not establish better business quality or useful model revision. Do not substitute low alarm frequency for successful error correction.
- Compare critique calibration, error-directed revision and correct-answer preservation together. A future learning rule should retain uncertainty and contradictory evidence, rather than converting this N20 diagnosis into a universal prohibition on review.

No runtime or optimizer feedback is changed here. Keep current Update6 parent retention and actor allocations unchanged. A prospective algorithm comparison can use the completed whole-population projection only after its exact source admission.

## Evidence

- Paired diagnostic SHA256: `c10c8dcc2e57b3f1e515415f35c5f395a77022a6280313795232387ec4c82fac`.
- Registered plan SHA256: `cacddc3358fa90601477b2b7241179cbbc288e92ca20b889fcb42594edbf8003`.
- External result: `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-CONTEXT-TEMPLATE-PARTITIONED-UPDATE6-DIVERSITY-N20-V1-ORIGINAL-A-READ-V1/paired-process-diagnostics-v1.json`.
- All17 contrasts remain in the source; this supplement does not select a favorable subset.
