# EXPLORATORY_SYSTEM_CANDIDATE: direct model versus native SLURP system

The first complete native-system comparison passes the prospectively frozen candidate condition. On primary NEW500, pooled official SLU micro F1 increases from 36.2485 to 50.6782 percent (+14.4297 percentage points; paired speaker-cluster CI90 [11.2108, 17.5903]). Joint intent accuracy increases from 72.4 to 78.6 percent (+6.2 points; CI90 [3.4114, 9.1711]).

This is one exploratory comparison on historically exposed discovery data. It is not an independent replication, a superiority/generalization claim, or a causal estimate for any individual component. Root selects same-roster replication before an added capability under OWNER-SYSTEM-VERSIONS-025.

## Registered runs

- SAEA-SLURP-DIRECT-VS-NATIVE-DIRECT-DEV1000-V1
- SAEA-SLURP-DIRECT-VS-NATIVE-SYSTEM-DEV1000-V1

## Compared systems

Both arms delivered all 1,000 registered DEV1000 answers from their own execution. Direct used one task-answer request through the same controller, FlightRuntime and OpenJiuwen executor. The native system used live Perception candidates, complete associated released slot explanations, joint Solver, Reviewer native task-contract calls, Planner acceptance or one bounded revision, and Solver-owned final delivery.

Both used frozen Q4_K_M, identical prepared query speech, the same resident decoder process, four 24,576-token slots (98,304 total), maximum 256 output tokens per request, temperature zero and seed 20260913. No GPU mmproj, encoder, Whisper, intent-boundary store or learned corrective memory was introduced. Additional calls are part of the complete-system treatment.

Each arm received one complete official SLURP score with saved per-sample sufficient counts. Root registered the source-bound read release before quality access. The shared paired analysis ran once; independent point reconciliation repeated neither scoring nor bootstrap.

## Frozen quality comparison

Values are percentages; deltas and intervals are percentage points, system minus direct. Intervals use 10,000 paired whole-speaker cluster draws. The lower fifth percentile is also the one-sided 95 percent lower endpoint. The primary seed is 20260913; row-metric seed offsets retain the frozen implementation. Scenario-stratified sensitivity results remain in the pinned complete analysis. NEW500 is primary, not unseen; OLD500 and DEV1000 are secondary.

### NEW500

| Metric | Direct | System | Delta | Speaker CI90 | Equal-scenario delta |
| --- | ---: | ---: | ---: | --- | ---: |
| Pooled official SLU micro F1 | 36.2485 | 50.6782 | +14.4297 | [+11.2108, +17.5903] | +13.1577 |
| Joint intent accuracy | 72.4000 | 78.6000 | +6.2000 | [+3.4114, +9.1711] | +4.4583 |
| Scenario accuracy | 82.0000 | 86.0000 | +4.0000 | [+1.0394, +6.9106] | +2.7018 |
| Action accuracy | 74.4000 | 80.4000 | +6.0000 | [+3.3930, +8.6393] | +4.1436 |
| Mean row exact slot F1 | 14.1076 | 20.6252 | +6.5176 | [+4.0287, +8.9074] | +7.7779 |
| Mean row official SLU F1 | 19.6389 | 34.2810 | +14.6421 | [+12.0395, +17.3547] | +14.5604 |

### OLD500

| Metric | Direct | System | Delta | Speaker CI90 | Equal-scenario delta |
| --- | ---: | ---: | ---: | --- | ---: |
| Pooled official SLU micro F1 | 34.4794 | 47.9713 | +13.4919 | [+9.8615, +17.0190] | +13.0504 |
| Joint intent accuracy | 70.2000 | 71.4000 | +1.2000 | [-1.5086, +3.7329] | +1.1831 |
| Scenario accuracy | 79.4000 | 81.2000 | +1.8000 | [-0.4415, +4.1667] | +1.7931 |
| Action accuracy | 72.8000 | 73.6000 | +0.8000 | [-1.9068, +3.3520] | +0.8083 |
| Mean row exact slot F1 | 11.7038 | 17.0271 | +5.3233 | [+2.1965, +8.5089] | +5.3515 |
| Mean row official SLU F1 | 18.0554 | 30.1942 | +12.1387 | [+9.3112, +15.0791] | +12.1920 |

### DEV1000

| Metric | Direct | System | Delta | Speaker CI90 | Equal-scenario delta |
| --- | ---: | ---: | ---: | --- | ---: |
| Pooled official SLU micro F1 | 35.3723 | 49.3358 | +13.9635 | [+11.4041, +16.4534] | +13.0713 |
| Joint intent accuracy | 71.3000 | 75.0000 | +3.7000 | [+1.7408, +5.5664] | +2.3365 |
| Scenario accuracy | 80.7000 | 83.6000 | +2.9000 | [+1.0881, +4.6858] | +2.0013 |
| Action accuracy | 73.6000 | 77.0000 | +3.4000 | [+1.5416, +5.2632] | +2.0465 |
| Mean row exact slot F1 | 12.9057 | 18.8262 | +5.9205 | [+3.9722, +7.9120] | +6.1747 |
| Mean row official SLU F1 | 18.8472 | 32.2376 | +13.3904 | [+11.3632, +15.4911] | +13.2574 |

Pooled micro uses summed official word/character TP, FP and FN. Mean row SLU F1 and mean row exact slot F1 are distinct estimands. Zero-entity rows and every malformed answer remain in the population.

NEW500 final direct-to-system intent changes comprise 59 saves and 28 harms; DEV1000 has 98 saves and 61 harms. The Perception-rank-one-to-final comparison below is a different comparison.

### Per-scenario tables

Every scenario is retained. Tables are descriptive, not subgroup gates. Other quality columns report paired deltas; the aggregate JSON preserves full points and saves/harms. Negative music and recommendation micro deltas on DEV1000 warrant analysis rather than exclusion.

#### NEW500 scenario results

| Scenario | n | Micro direct | Micro system | Micro delta | Intent delta | Scenario delta | Action delta | Exact slot mean delta | SLU row mean delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 30 | 32.960 | 52.328 | +19.368 | -6.667 | -3.333 | -6.667 | +11.556 | +17.221 |
| audio | 2 | 0.000 | 0.000 | +0.000 | +0.000 | +0.000 | +0.000 | +0.000 | +0.000 |
| calendar | 33 | 32.067 | 49.602 | +17.535 | +0.000 | -6.061 | -3.030 | +6.616 | +17.173 |
| cooking | 9 | 50.161 | 66.142 | +15.981 | -11.111 | -11.111 | -11.111 | +29.630 | +29.197 |
| datetime | 33 | 33.212 | 51.734 | +18.522 | +0.000 | -6.061 | +6.061 | +0.000 | +22.075 |
| email | 33 | 16.667 | 50.398 | +33.731 | +6.061 | +0.000 | +6.061 | +8.081 | +22.268 |
| general | 33 | 9.626 | 10.860 | +1.234 | +3.030 | -18.182 | +3.030 | +3.030 | +2.680 |
| iot | 33 | 54.384 | 59.969 | +5.585 | -3.030 | +0.000 | -3.030 | +8.081 | +9.702 |
| lists | 32 | 38.056 | 47.381 | +9.325 | +6.250 | +9.375 | +6.250 | +2.083 | +5.589 |
| music | 23 | 33.212 | 35.891 | +2.679 | -8.696 | -4.348 | -17.391 | +4.348 | +5.672 |
| news | 32 | 37.930 | 42.368 | +4.437 | +3.125 | +3.125 | +3.125 | -0.313 | +5.787 |
| play | 32 | 54.076 | 56.946 | +2.870 | +50.000 | +53.125 | +50.000 | -1.042 | +8.931 |
| qa | 32 | 54.928 | 60.428 | +5.501 | +15.625 | +12.500 | +15.625 | -1.562 | +11.300 |
| recommendation | 32 | 61.541 | 50.831 | -10.709 | +21.875 | +21.875 | +21.875 | -10.521 | -2.012 |
| social | 33 | 17.194 | 46.580 | +29.386 | +12.121 | +9.091 | +12.121 | +13.131 | +24.811 |
| takeaway | 12 | 36.571 | 59.669 | +23.097 | -8.333 | -8.333 | -8.333 | +27.778 | +23.293 |
| transport | 33 | 28.978 | 58.106 | +29.127 | -3.030 | -6.061 | -3.030 | +18.398 | +32.087 |
| weather | 33 | 17.406 | 46.577 | +29.171 | +3.030 | +3.030 | +3.030 | +20.707 | +26.314 |

#### OLD500 scenario results

| Scenario | n | Micro direct | Micro system | Micro delta | Intent delta | Scenario delta | Action delta | Exact slot mean delta | SLU row mean delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 28 | 15.012 | 63.627 | +48.614 | +0.000 | +0.000 | +3.571 | +18.333 | +32.441 |
| audio | 28 | 0.000 | 15.114 | +15.114 | -14.286 | -17.857 | -14.286 | +0.000 | +4.063 |
| calendar | 28 | 37.763 | 44.682 | +6.919 | +7.143 | +0.000 | +7.143 | -2.143 | +3.504 |
| cooking | 28 | 43.850 | 60.318 | +16.468 | -25.000 | +0.000 | -25.000 | +22.024 | +23.171 |
| datetime | 28 | 35.766 | 52.033 | +16.266 | +0.000 | +0.000 | +0.000 | -6.667 | +20.510 |
| email | 28 | 28.516 | 44.653 | +16.137 | +0.000 | +0.000 | +0.000 | +5.000 | +9.421 |
| general | 28 | 29.150 | 33.413 | +4.263 | -7.143 | -14.286 | -7.143 | +2.262 | +1.816 |
| iot | 28 | 42.819 | 56.733 | +13.914 | +3.571 | +0.000 | +0.000 | +11.905 | +14.978 |
| lists | 28 | 43.623 | 49.727 | +6.104 | +0.000 | +0.000 | -3.571 | +5.357 | +5.530 |
| music | 28 | 53.018 | 29.613 | -23.405 | -14.286 | -14.286 | -21.429 | +0.000 | -3.461 |
| news | 28 | 32.339 | 44.347 | +12.008 | +10.714 | +10.714 | +7.143 | +7.143 | +15.150 |
| play | 28 | 46.967 | 53.777 | +6.810 | +32.143 | +39.286 | +28.571 | +0.000 | +7.887 |
| qa | 28 | 50.026 | 56.990 | +6.964 | +14.286 | +14.286 | +14.286 | +7.143 | +9.918 |
| recommendation | 28 | 37.195 | 34.092 | -3.103 | +17.857 | +10.714 | +17.857 | -9.524 | -0.880 |
| social | 27 | 15.423 | 53.092 | +37.669 | +3.704 | +7.407 | +7.407 | +20.247 | +30.914 |
| takeaway | 27 | 41.299 | 45.550 | +4.250 | -7.407 | -3.704 | -3.704 | -0.617 | +7.197 |
| transport | 27 | 32.320 | 55.093 | +22.772 | +0.000 | +0.000 | +3.704 | +10.926 | +19.946 |
| weather | 27 | 8.696 | 35.836 | +27.140 | +0.000 | +0.000 | +0.000 | +4.938 | +17.351 |

#### DEV1000 scenario results

| Scenario | n | Micro direct | Micro system | Micro delta | Intent delta | Scenario delta | Action delta | Exact slot mean delta | SLU row mean delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 58 | 24.992 | 57.557 | +32.565 | -3.448 | -1.724 | -1.724 | +14.828 | +24.569 |
| audio | 30 | 0.000 | 15.114 | +15.114 | -13.333 | -16.667 | -13.333 | +0.000 | +3.792 |
| calendar | 61 | 34.217 | 47.663 | +13.445 | +3.279 | -3.279 | +1.639 | +2.596 | +10.899 |
| cooking | 37 | 45.065 | 61.676 | +16.611 | -21.622 | -2.703 | -21.622 | +23.874 | +24.637 |
| datetime | 61 | 34.357 | 51.879 | +17.522 | +0.000 | -3.279 | +3.279 | -3.060 | +21.357 |
| email | 61 | 22.658 | 47.630 | +24.972 | +3.279 | +0.000 | +3.279 | +6.667 | +16.371 |
| general | 61 | 19.342 | 20.970 | +1.628 | -1.639 | -16.393 | -1.639 | +2.678 | +2.284 |
| iot | 61 | 49.520 | 58.407 | +8.887 | +0.000 | +0.000 | -1.639 | +9.836 | +12.124 |
| lists | 60 | 41.212 | 48.643 | +7.431 | +3.333 | +5.000 | +1.667 | +3.611 | +5.561 |
| music | 51 | 42.807 | 32.451 | -10.356 | -11.765 | -9.804 | -19.608 | +1.961 | +0.658 |
| news | 60 | 35.223 | 43.335 | +8.111 | +6.667 | +6.667 | +5.000 | +3.167 | +10.156 |
| play | 60 | 50.747 | 55.467 | +4.720 | +41.667 | +46.667 | +40.000 | -0.556 | +8.444 |
| qa | 60 | 52.741 | 59.043 | +6.302 | +15.000 | +13.333 | +15.000 | +2.500 | +10.655 |
| recommendation | 60 | 49.880 | 42.927 | -6.953 | +20.000 | +16.667 | +20.000 | -10.056 | -1.484 |
| social | 60 | 16.484 | 49.124 | +32.640 | +8.333 | +8.333 | +10.000 | +16.333 | +27.557 |
| takeaway | 39 | 40.205 | 48.910 | +8.705 | -7.692 | -5.128 | -5.128 | +8.120 | +12.150 |
| transport | 60 | 30.625 | 56.696 | +26.071 | -1.667 | -3.333 | +0.000 | +15.036 | +26.624 |
| weather | 60 | 13.049 | 40.917 | +27.868 | +1.667 | +1.667 | +1.667 | +13.611 | +22.281 |

## System headroom

### Candidate coverage and joint resolution

| Population | Perception rank-one correct | Gold in up-to-three | Missing gold | Present but final incorrect | Final correct | Rank-one saves / harms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| NEW500 | 388/500 | 413/500 | 87 | 23 | 393/500 | 10 / 5 |
| OLD500 | 355/500 | 388/500 | 112 | 35 | 357/500 | 14 / 12 |
| DEV1000 | 743/1000 | 801/1000 | 199 | 58 | 750/1000 | 24 / 17 |

DEV1000 distinct candidate widths are one on 699 rows, two on 203, and three on 98. Perception generated 1,412 raw positions; first-occurrence projection retains 1,399 after 13 duplicate positions on 11 rows. Width is an output, not calibrated confidence. This comparison does not select or test a fixed Top-3 policy.

NEW500 candidate inclusion is 82.6 percent versus rank-one accuracy 77.6 percent. Of 413 covered rows, 390 finish correct and 23 do not. Three more final answers are correct outside the candidate set. DEV1000 has 25 out-of-shortlist attempts, seven correct. Preserve them as delivered behavior: this is not a perfectly enforced hard shortlist or evidence of a registered deliberate reopening policy.

| NEW500 width | n | Gold inclusion | Final intent accuracy |
| --- | ---: | ---: | ---: |
| 1 | 368 | 86.685% | 86.413% |
| 2 | 95 | 72.632% | 57.895% |
| 3 | 37 | 67.568% | 54.054% |

Candidate misses outnumber covered-but-unresolved cases, making discriminative intent knowledge a plausible extension. Slot headroom remains substantial: DEV1000 has 473 correct-intent answers with at least one exact entity FP or FN. Another 277 have correct intent and no exact entity FP/FN; 59 have incorrect intent with no entity FP/FN; 191 have both error types. These partitions use saved official counts, not another scorer.

### Reviewer, Planner and tools

Role counts are Perception 1,000, Solver 1,005, Reviewer 2,010 and Planner 1,005. Reviewer completed 1,005 model-originated task-contract tool calls, with zero failed/rejected events. Planner issued 1,000 ACCEPT and five REVISE routes: five episodes took one revision. No speech-observation tool was called.

The native framework executed its roles and tool loop. Effective error detection, calibrated selective tool choice, and a causal review benefit remain unproven. Reviewer was instructed to call the task-contract tool. Future speech tools should be selected by Reviewer/Planner for a concrete evidence gap; Solver retains answer authority.

Five final system answers lacked a parseable task intent (three NEW500, two OLD500). They remain nonrefused incorrect all-row outcomes. No system contact or final answer reached 256 tokens or reported a length stop. These format failures are not explained by output saturation.

### OBS / ORG / SUPPLY / USE

OBS: current-query prepared speech was reused across roles; zero observation-tool, ASR or encoder contacts. ORG: the released slot-contract store and associations were fixed before execution. SUPPLY: verified MODEL_REQUEST records contain 37,480 value occurrences across 5,020 contacts. USE: 9,334 lexical overlap records are marked use; they do not establish semantic or causal use.

The campaign did not preserve the original FlightReceipts candidate-to-value selection audit. Source-derived candidate projection and actual supplied-evidence requests are available, but neither is fabricated into a producer-authored selection receipt. This limits detailed selection claims, not the end-to-end comparison.

## Operational accounting

| Quantity | Direct | System |
| --- | ---: | ---: |
| Final answers | 1,000 | 1,000 |
| Generation calls | 1,000 | 5,020 |
| Reused speech seconds | 2,884.794 | 14,476.191 |
| Prompt tokens | 2,279,117 | 33,448,887 |
| Completion tokens | 25,708 | 217,695 |
| Analytical tool calls | 0 | 1,005 |
| Attached-serving window seconds | 463.967 | 8,802.729 |
| Official finalization batch seconds | 29.112 | 74.448 |

Attached-serving windows include framework work; they are not pure kernel time. Both arms reused one session, so no arm-specific model-load duration exists. Separate exact fit/seal durations are unavailable. Direct scoring overlapped system execution. The attached-window handoff separation was approximately 72 seconds; preparation/lease stages are not separately timed enough to assign it to one cause.

Sampled mean utilization was 54.51 percent direct and 87.32 percent system; mean power 60.94 W and 90.96 W. Sampled parked durations were 138.87 s and 234.40 s. Sample-mean utilization times wall is only a proxy, not a measured integral. Monitor request deltas are not reconciled model-call counts. The GPU audit observed a laptop power cap; no power, clock or serving setting was changed.

Quality remains primary. The system's 5.02-fold calls and 14.68-fold prompt tokens describe work, not a rejection rule. They can guide removal of unnecessary work after capability is established.

## Root decision and next sequence

1. Mark EXPLORATORY_SYSTEM_CANDIDATE under the frozen NEW500 micro/intent condition. Preserve all historical exposures and failed engineering records.
2. Register one same-roster direct/system replication with identical model, geometry, decoding, role programs, prompts, knowledge and projection. Reuse the resident service if exact identity remains valid. Use fresh generation and fit plans; old fit receipts are not reusable. Score each new complete arm once, and withhold quality reads until both new receipts and a new release exist.
3. After replication, select one complete-system extension. Current evidence favors better intent discrimination and coverage; correct-intent/entity errors also motivate explanatory slot values and targeted speech evidence. Do not silently combine every extension or revive an automatic knowledge/no-knowledge factorial.
4. Optimize Reviewer/Planner decisions: identify an evidence gap, select a relevant tool/knowledge view, consume its result, then accept or request Solver revision. A task-contract call alone is not the endpoint.
5. Build training-free optimization from TRAIN episodes with grouped relative feedback, bounded policy/memory edits, disjoint candidate selection, and frozen evaluation. Reuse the framework. DEV labels and error-specific corrections must not enter TRAIN knowledge/memory. Audio2Tool retains separate activation/parameter knowledge and native multi-action/dialogue/scorer contracts; later Earnings work uses its task metrics.

## Verification and custody

Independent reconciliation recomputed six metrics, scenario points, equal-scenario deltas and saves/harms from original first-score rows. Zero mismatches; maximum difference 1.51e-14 from summation order. No bootstrap/scorer repetition.

The analysis reader required two corrections: bind the canonical Perception framework envelope rather than plain phase text, and represent missing final intents without relabeling them refusals. It reuses the producer constructor. Seventy-six focused native/legacy/aggregation tests pass; engineering-base and native OpenJiuwen reuse checks pass. Independent source review found no remaining material issue. Frozen runtime 7ec4cf34, model outputs, first scores, bound configs and estimands remain unchanged. Failed reader logs are preserved; successful diagnostics ran at 780d0679.

Detailed aggregates: [verdict JSON](2026-09-13-slurp-direct-vs-native-system-verdict-v1.json). DATA is /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data; source directory analysis/SAEA-SLURP-DIRECT-VS-NATIVE-SYSTEM-PAIRED-ANALYSIS-V1.

| Artifact | SHA-256 |
| --- | --- |
| costs | 1709957a4a77fac1c86d66dd141310bb59662a03c0841fb13ba7939401f95ca0 |
| native | a9b939ceb823d8c0de3a25524f5b4fbf91bcd68f4e0498046697014818a28cfa |
| native_config | bdc5ec75c5cc1f8a35cb02208ff8a1b915df762a29d3ec7417dba1759ad9919e |
| paired | e0f1c3072e6d7347dc675c198339c239117228eab1aa836a6536113d678babc6 |
| paired_config | 0ffd7c3232d675dc7bd0035da275da5c9a80b5a32ddccc45e387662a1b6c2df9 |
| reconciliation | 10f8087d06a42fd49f47c59593c1722c9f157c048d39a10c79dd8e088e7b4506 |
| quality release | d55233d438135666f368d27898bfef3f45c7e2b3829d9f691ed95e4cb4ab8c29 |
