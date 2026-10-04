# TF context-diversity iteration 1: complete system trial

Root interpretation recorded 2026-10-04T17:15:13.981714+00:00. Exact READ: SAEA-SLURP-CONTEXT-TF-ITERATION1-N20-READ-V1. All six members independently finalized 20 rows with verified seals, exactly one successful complete official score each and zero failed jobs. Driver ended 2026-10-04T17:04:33Z; root countersigned at 2026-10-04T17:04:55.914570+00:00. No score replay.

## Root decision

Keep seed as the formal incumbent and remain at 20 inputs. None of the four updated complete systems exceeds the same-trial seed official SLU-F1 or lowers mean sample latency. This is a reused TRAIN optimization panel, not independent validation or evidence of stable benefit. The original TF learner rejected the update under its registered utility rule. Keep its four original optimization parents, separately from the formal seed incumbent.

Utility before -14.428366880; after -18.345750975. The original Windows wrapper exited 0 at 2026-10-04T17:07:46.0838078Z. The original 32 summarize, 8 compare, 1 experience-update, 4 propose and 1 evaluate callbacks remain spent and preserved. Nine proposed experience additions are historical only: rejection leaves zero active experience entries, so no actual experience reset is needed for this state. Provider tokens and contacts are unmetered, not zero; callback wall time includes orchestration waits and is not provider compute.

## Complete-system measurements

| Member | Official SLU-F1 (%) | Intent (%) | Reliable (%) | Contacts | Mean sample (s) | Non-first mean (s) | First 4 mean (s) | After first 4 mean (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| seed | 65.402 | 70.0 | 100.0 | 128 | 34.005 | 33.080 | 36.882 | 33.285 |
| seed-aa | 61.278 | 70.0 | 100.0 | 125 | 32.895 | 32.302 | 34.284 | 32.548 |
| speech-evidence | 56.372 | 70.0 | 100.0 | 86 | 41.659 | 41.901 | 33.895 | 43.600 |
| coverage-ledger | 54.468 | 70.0 | 100.0 | 86 | 35.428 | 35.442 | 30.500 | 36.660 |
| counterexample-check | 53.112 | 70.0 | 100.0 | 83 | 34.346 | 32.783 | 36.845 | 33.722 |
| semantic-frame | 46.091 | 75.0 | 100.0 | 104 | 50.351 | 51.796 | 29.145 | 55.652 |

Total: 120 trajectories, 612 actual generation contacts, 612 actual-request FIT receipts, 2448 FIT service endpoints and six whole-member official scores. All members have zero active knowledge-tool calls; this does not imply absence of automatic knowledge supply. Reliable completion is not correctness. Sample latency covers admission-to-settled workflow, excluding pre-admission waiting, preparation, final persistence and scoring. First/non-first groups are admission-order diagnostics, not established cold/warm cache states.

## Paired uncertainty and adverse outcomes

The registered parent contrast means the same-trial seed, not the historical TF optimization parent. Use 10000 paired utterance bootstrap draws, seed 20261001. Do not use individual strata or this small repeated panel for a formal efficacy verdict.

| Contrast | F1 delta (pp) | 95% interval (pp) | Exact-answer repairs | Exact-answer damage |
|---|---:|---|---:|---:|
| counterexample-check-minus-aa | -8.167 | [-21.902, 0.460] | 0 | 2 |
| counterexample-check-minus-parent | -12.290 | [-25.821, -2.111] | 0 | 3 |
| coverage-ledger-minus-aa | -6.810 | [-21.986, 3.811] | 1 | 1 |
| coverage-ledger-minus-parent | -10.934 | [-26.466, 2.033] | 1 | 2 |
| same-request-null | -4.124 | [-12.368, 0.000] | 0 | 1 |
| semantic-frame-minus-aa | -15.188 | [-34.633, 0.000] | 2 | 0 |
| semantic-frame-minus-parent | -19.312 | [-37.939, -2.875] | 2 | 1 |
| speech-evidence-minus-aa | -4.906 | [-21.603, 8.104] | 0 | 1 |
| speech-evidence-minus-parent | -9.030 | [-26.628, 6.138] | 0 | 2 |

These repair/damage counts compare complete system answers. They are associations, not causal credit for a node or a within-trajectory revision. A/A F1 differs by -4.124 pp despite fixed temperature and seed. Fixed decoding settings do not demonstrate bitwise repeatability; this trial does not isolate the responsible numerical or serving mechanism.

## Natural mixture and equal-stratum descriptions

The main table uses pooled official metrics. The following macro table weights the 13 observed strata equally; it is descriptive and does not replace the official pooled endpoint.

| Member | Equal-stratum F1 (%) | Equal-stratum intent (%) |
|---|---:|---:|
| seed | 47.218 | 70.513 |
| seed-aa | 45.710 | 70.513 |
| speech-evidence | 45.975 | 70.513 |
| coverage-ledger | 39.955 | 70.513 |
| counterexample-check | 40.739 | 70.513 |
| semantic-frame | 36.109 | 74.359 |

Every observed stratum follows. Cells show F1 / intent percentages.

| Stratum | n | seed | seed-aa | speech-evidence | coverage-ledger | counterexample-check | semantic-frame |
|---|---:|---:|---:|---:|---:|---:|---:|
| audio | 3 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 |
| cooking | 2 | 50.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 | 0.00 / 50.00 |
| email | 1 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 |
| general | 2 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 |
| iot | 1 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 |
| lists | 1 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 59.09 / 100.00 | 100.00 / 100.00 |
| music | 2 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 100.00 |
| news | 1 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 |
| play | 2 | 92.63 / 100.00 | 73.03 / 100.00 | 40.00 / 100.00 | 40.00 / 100.00 | 49.32 / 100.00 | 40.00 / 100.00 |
| qa | 2 | 62.75 / 100.00 | 62.75 / 100.00 | 62.75 / 100.00 | 62.75 / 100.00 | 62.75 / 100.00 | 62.75 / 100.00 |
| recommendation | 1 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 |
| social | 1 | 41.79 / 0.00 | 41.79 / 0.00 | 78.26 / 0.00 | 0.00 / 0.00 | 41.79 / 0.00 | 0.00 / 0.00 |
| takeaway | 1 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 |

## Node costs

| Member | Node | Contacts | Input reuse (%) | Mean prefill (s) | Mean generation (s) | Mean client roundtrip (s) |
|---|---|---:|---:|---:|---:|---:|
| seed | perception | 20 | 63.09 | 0.655 | 5.215 | 6.073 |
| seed | planner | 36 | 94.83 | 0.397 | 0.208 | 0.839 |
| seed | reviewer | 36 | 96.76 | 0.261 | 8.630 | 9.156 |
| seed | solver | 36 | 63.70 | 1.872 | 1.923 | 4.094 |
| seed-aa | perception | 20 | 63.09 | 0.677 | 5.335 | 6.284 |
| seed-aa | planner | 35 | 94.95 | 0.389 | 0.243 | 1.092 |
| seed-aa | reviewer | 35 | 96.80 | 0.268 | 7.249 | 7.673 |
| seed-aa | solver | 35 | 62.09 | 1.947 | 2.365 | 4.941 |
| speech-evidence | perception | 20 | 58.94 | 1.133 | 9.166 | 10.508 |
| speech-evidence | planner | 22 | 19.08 | 4.475 | 0.198 | 5.504 |
| speech-evidence | reviewer | 22 | 94.88 | 0.422 | 12.501 | 13.220 |
| speech-evidence | solver | 22 | 30.54 | 3.918 | 3.171 | 7.908 |
| coverage-ledger | perception | 20 | 58.19 | 1.196 | 6.342 | 8.047 |
| coverage-ledger | planner | 22 | 20.84 | 4.754 | 0.244 | 5.426 |
| coverage-ledger | reviewer | 22 | 93.56 | 0.569 | 8.559 | 9.484 |
| coverage-ledger | solver | 22 | 33.22 | 4.169 | 3.345 | 8.249 |
| counterexample-check | perception | 20 | 59.19 | 1.556 | 4.860 | 6.842 |
| counterexample-check | planner | 21 | 20.90 | 5.135 | 0.377 | 5.894 |
| counterexample-check | reviewer | 21 | 94.04 | 0.374 | 7.712 | 8.588 |
| counterexample-check | solver | 21 | 33.67 | 4.033 | 4.061 | 9.881 |
| semantic-frame | perception | 20 | 58.42 | 1.380 | 5.898 | 7.680 |
| semantic-frame | planner | 28 | 20.42 | 5.255 | 0.278 | 6.112 |
| semantic-frame | reviewer | 28 | 93.87 | 0.481 | 15.395 | 16.101 |
| semantic-frame | solver | 28 | 30.67 | 3.610 | 2.416 | 6.663 |

These are measured per-contact diagnostics, not independent node treatment effects or additive sample wall-time estimates. The seed Reviewer spends about 0.261 s on prefill and 8.630 s on generation per contact, with 96.76% input reuse. This particular result does not support treating all Reviewer time as prefix recomputation. Do not infer eviction causality from pooled timing.

## Consumption priorities and the next registered phase

Treat existing knowledge supply as adequate for this stage, as directed by the owner. Keep knowledge, retrieval, source rosters and construction fixed. Prioritize (1) joint Solver/Reviewer evidence use and justified corrections, (2) context organization and current-state handoffs, (3) Planner revision/stop/delivery decisions, (4) Perception presentation only when needed by downstream consumption. Complete templates may be jointly changed; component ablations are not a prerequisite.

The four candidates reduce contacts from 128 to 83--104 and increase accepted terminal counts from 6 to 18--20, yet official F1 and mean latency do not improve. Therefore neither fewer calls, shorter answers nor Planner acceptance is an adequate optimization reward by itself. Retain official quality, intent, reliable delivery and mean/non-first latency as distinct measurements. This is a prioritization inference, not a proved node-specific cause.

The measured same-cohort frontier contains seed, counterexample-check and semantic-frame. Counterexample trades lower call count and slightly lower non-first mean for lower F1; semantic-frame trades higher intent for lower F1 and higher latency. Frontier membership does not authorize adoption.

Use the prepared zero-case template profile prospectively: complete editable node templates/assembly plus automatic aggregate measurements. Do not send raw cases, knowledge contents, construction instructions or expanded source lists to semantic proposers. Full provenance stays in the backend. Preserve rejected children and adverse outcomes. Before the next iteration, explicitly register how qualified own-TF rejected-trial aggregates and attempted templates may inform the learner while its accepted parents remain unchanged. The current READ covers root analysis and the original evaluation callback only; it does not itself authorize a new optimizer export. Keep GEPA evidence separate.

Next work remains at N20/K4: prepare the exact successor protocol, parent state, feedback scope and isolated actor capsules, then admit bounded semantic calls. No new model/runtime contact, automatic scale dispatch, policy adoption or new carrier authority is granted by this report. Keep the heartbeat paused and return to the human before 8x400.

## Evidence custody

Complete data-local analysis: `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-CONTEXT-TF-ITERATION1-N20-READ-V1`. Raw traces remain outside Git. The completion receipt pins the report, timing, exact READ authorization, terminal learner decision and original Windows exit record. See `docs/receipts/continuation/2026-10-04-context-tf-iteration1-complete.json`.
