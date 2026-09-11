# SLURP program-matched live system: final decision

**SYSTEM_NOT_ADMITTED_PRIMARY_AND_INTENT_GUARD_FAILED.** The single owner-authorized follow-up is closed scientifically. The primary NEW500 interval crosses zero and intent accuracy falls by 0.2 percentage points. Keep the original G6 scenario-guard failure as a separate historical decision. Do not repeat this comparison to seek a pass.

Both independent two-stage arms used the same frozen source 21ebe2bc8f9c03469a48fe0c68e9b31f1c360dff, resident decoder-only process, c65536/np4, precomputed speech packets, max256, and shared OpenJiuwen controller. Each generated 1000 direct and 1000 slot responses, with fresh within-arm predecessor joins. Both sealed before read release; each complete joined delivery was scored once by the pinned official SLURP evaluator.

## Frozen estimates

All accuracy/F1 values are percentages and changes are percentage points. Primary uncertainty uses 10000 paired speaker-cluster bootstrap replicates, registered seed20260903 and fixed metric offsets, CI90. Mean per-row F1 and pooled-count micro F1 are different estimands. OLD500 and DEV1000 are secondary; their positive intervals cannot replace the NEW500 primary.

| Population | Metric | Control | Speech | Change | CI90 | Equal-scenario change |
|---|---|---|---|---|---|---|
| NEW500 | Mean row SLU-F1 | 31.2084 | 32.2271 | +1.0187 | [-0.9059, +2.8329] | +0.8572 |
| NEW500 | Micro SLU-F1 | 48.4421 | 49.5772 | +1.1351 | [-1.4626, +3.5620] | +1.6486 |
| NEW500 | Intent | 69.8000 | 69.6000 | -0.2000 | [-1.6771, +1.3437] | -0.1120 |
| NEW500 | Scenario | 77.0000 | 77.4000 | +0.4000 | [-0.8247, +1.6760] | +0.3815 |
| NEW500 | Action | 72.4000 | 72.6000 | +0.2000 | [-1.3410, +1.8145] | +0.2247 |
| OLD500 | Mean row SLU-F1 | 25.3800 | 28.1085 | +2.7285 | [+0.7976, +4.7293] | +2.7568 |
| OLD500 | Micro SLU-F1 | 43.4342 | 46.4696 | +3.0355 | [+0.4204, +5.6736] | +3.1659 |
| OLD500 | Intent | 68.0000 | 67.2000 | -0.8000 | [-1.9120, +0.3781] | -0.8010 |
| OLD500 | Scenario | 76.0000 | 76.0000 | +0.0000 | [-1.1859, +1.1152] | -0.0073 |
| OLD500 | Action | 71.4000 | 70.2000 | -1.2000 | [-2.3698, +0.0000] | -1.2052 |
| DEV1000 | Mean row SLU-F1 | 28.2942 | 30.1678 | +1.8736 | [+0.5657, +3.1490] | +2.0856 |
| DEV1000 | Micro SLU-F1 | 45.9991 | 48.0523 | +2.0532 | [+0.2332, +3.8801] | +3.0874 |
| DEV1000 | Intent | 68.9000 | 68.4000 | -0.5000 | [-1.4313, +0.4445] | -0.5984 |
| DEV1000 | Scenario | 76.5000 | 76.7000 | +0.2000 | [-0.5903, +0.9444] | +0.1758 |
| DEV1000 | Action | 71.9000 | 71.4000 | -0.5000 | [-1.5311, +0.5624] | -0.5984 |

## Prospective admission rule

| Requirement | Pass |
|---|---|
| primary_row_f1_lower_gt_zero | False |
| pooled_micro_gain_gt_zero | True |
| equal_scenario_row_gain_gt_zero | True |
| intent_point_nonnegative | False |
| scenario_point_nonnegative | True |
| action_point_nonnegative | True |
| malformed_final_delivery_not_increased | True |
| saturation_not_increased | True |

These protection checks are prospective descriptive point guards, not non-inferiority or equivalence tests. Historical np8/max64 null margins are inapplicable.

## All scenario strata

The following fixed strata are descriptive; no stratum is selected to rescue admission. The inherited row bootstrap remains a separately labelled sensitivity in the saved analysis.
### NEW500

| Scenario | n | Control row F1 | Speech row F1 | Row change | Micro change | Intent change | Scenario change | Action change |
|---|---|---|---|---|---|---|---|---|
| alarm | 30 | 32.1947 | 39.6631 | +7.4684 | +7.2849 | -3.3333 | -6.6667 | -3.3333 |
| audio | 2 | 0.0000 | 0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 |
| calendar | 33 | 31.6122 | 25.5184 | -6.0938 | -0.7019 | -3.0303 | +0.0000 | -3.0303 |
| cooking | 9 | 40.8369 | 44.4444 | +3.6075 | +4.2382 | +0.0000 | +0.0000 | +0.0000 |
| datetime | 33 | 33.3646 | 26.8721 | -6.4925 | -7.6841 | -6.0606 | +3.0303 | -3.0303 |
| email | 33 | 22.4387 | 28.4993 | +6.0606 | +6.4025 | -3.0303 | +0.0000 | -3.0303 |
| general | 33 | 12.7154 | 17.7659 | +5.0505 | +11.9053 | +6.0606 | +0.0000 | +6.0606 |
| iot | 33 | 47.4967 | 47.4967 | +0.0000 | -4.3661 | +0.0000 | +0.0000 | +0.0000 |
| lists | 32 | 15.5668 | 12.4418 | -3.1250 | -0.4922 | +3.1250 | +3.1250 | +3.1250 |
| music | 23 | 10.3363 | 14.6842 | +4.3478 | +10.9290 | +4.3478 | +4.3478 | +4.3478 |
| news | 32 | 25.8918 | 27.3448 | +1.4530 | +0.0004 | -3.1250 | -3.1250 | -3.1250 |
| play | 32 | 32.8341 | 27.0600 | -5.7740 | -5.7921 | +0.0000 | +0.0000 | +0.0000 |
| qa | 32 | 53.2051 | 46.9551 | -6.2500 | -4.6544 | -3.1250 | +0.0000 | -3.1250 |
| recommendation | 32 | 51.6701 | 55.9139 | +4.2438 | +0.1261 | +3.1250 | +3.1250 | +3.1250 |
| social | 33 | 29.4722 | 46.5729 | +17.1007 | +17.7581 | +3.0303 | +3.0303 | +6.0606 |
| takeaway | 12 | 26.5404 | 19.7222 | -6.8182 | -5.1616 | +0.0000 | +0.0000 | +0.0000 |
| transport | 33 | 44.5390 | 38.2047 | -6.3342 | -9.3165 | +0.0000 | +0.0000 | +0.0000 |
| weather | 33 | 20.2167 | 27.2023 | +6.9856 | +9.1997 | +0.0000 | +0.0000 | +0.0000 |

### OLD500

| Scenario | n | Control row F1 | Speech row F1 | Row change | Micro change | Intent change | Scenario change | Action change |
|---|---|---|---|---|---|---|---|---|
| alarm | 28 | 17.4065 | 17.9160 | +0.5094 | +1.1463 | +0.0000 | +0.0000 | +0.0000 |
| audio | 28 | 7.1429 | 8.3969 | +1.2541 | +7.2603 | -7.1429 | +0.0000 | -7.1429 |
| calendar | 28 | 21.7412 | 21.8871 | +0.1459 | +1.0491 | +3.5714 | +3.5714 | +0.0000 |
| cooking | 28 | 28.1568 | 37.4425 | +9.2857 | +10.5329 | +0.0000 | +0.0000 | +0.0000 |
| datetime | 28 | 38.2736 | 25.1939 | -13.0797 | -18.4690 | +0.0000 | +0.0000 | +0.0000 |
| email | 28 | 23.5408 | 23.2857 | -0.2551 | -1.6984 | +0.0000 | +0.0000 | +0.0000 |
| general | 28 | 11.0823 | 15.8442 | +4.7619 | +2.0223 | -3.5714 | +0.0000 | -3.5714 |
| iot | 28 | 30.7180 | 24.4695 | -6.2485 | -9.3028 | +0.0000 | +0.0000 | +0.0000 |
| lists | 28 | 25.2799 | 26.5931 | +1.3132 | +3.6307 | +0.0000 | +0.0000 | +0.0000 |
| music | 28 | 14.3609 | 14.9393 | +0.5783 | +6.3336 | -3.5714 | -3.5714 | -3.5714 |
| news | 28 | 20.2727 | 21.4471 | +1.1744 | +1.1919 | +0.0000 | +0.0000 | +0.0000 |
| play | 28 | 35.2023 | 40.6445 | +5.4422 | +7.5850 | +3.5714 | +3.5714 | +3.5714 |
| qa | 28 | 22.3452 | 36.8297 | +14.4845 | +14.2989 | +0.0000 | -3.5714 | +0.0000 |
| recommendation | 28 | 22.0604 | 27.1412 | +5.0808 | +8.9538 | -3.5714 | +3.5714 | -3.5714 |
| social | 27 | 44.4141 | 61.9029 | +17.4888 | +16.4044 | -7.4074 | -3.7037 | -11.1111 |
| takeaway | 27 | 24.4565 | 36.1323 | +11.6758 | +8.7254 | +3.7037 | +0.0000 | +3.7037 |
| transport | 27 | 43.1809 | 41.1978 | -1.9832 | -1.3288 | +0.0000 | +0.0000 | +0.0000 |
| weather | 27 | 28.6023 | 26.5961 | -2.0062 | -1.3490 | +0.0000 | +0.0000 | +0.0000 |

### DEV1000

| Scenario | n | Control row F1 | Speech row F1 | Row change | Micro change | Intent change | Scenario change | Action change |
|---|---|---|---|---|---|---|---|---|
| alarm | 58 | 25.0556 | 29.1645 | +4.1089 | +3.6109 | -1.7241 | -3.4483 | -1.7241 |
| audio | 30 | 6.6667 | 7.8372 | +1.1705 | +10.8966 | -6.6667 | +0.0000 | -6.6667 |
| calendar | 61 | 27.0812 | 23.8516 | -3.2297 | +0.0176 | +0.0000 | +1.6393 | -1.6393 |
| cooking | 37 | 31.2411 | 39.1456 | +7.9045 | +9.0988 | +0.0000 | +0.0000 | +0.0000 |
| datetime | 61 | 35.6179 | 26.1017 | -9.5162 | -12.8043 | -3.2787 | +1.6393 | -1.6393 |
| email | 61 | 22.9446 | 26.1062 | +3.1616 | +2.3913 | -1.6393 | +0.0000 | -1.6393 |
| general | 61 | 11.9658 | 16.8838 | +4.9180 | +7.5366 | +1.6393 | +0.0000 | +1.6393 |
| iot | 61 | 39.7950 | 36.9268 | -2.8682 | -6.1636 | +0.0000 | +0.0000 | +0.0000 |
| lists | 60 | 20.0996 | 19.0457 | -1.0538 | +2.4595 | +1.6667 | +1.6667 | +1.6667 |
| music | 51 | 12.5459 | 14.8242 | +2.2783 | +7.9532 | +0.0000 | +0.0000 | +0.0000 |
| news | 60 | 23.2696 | 24.5925 | +1.3230 | +0.8676 | -1.6667 | -1.6667 | -1.6667 |
| play | 60 | 33.9392 | 33.3994 | -0.5398 | +0.5680 | +1.6667 | +1.6667 | +1.6667 |
| qa | 60 | 38.8038 | 42.2299 | +3.4261 | +2.9492 | -1.6667 | -1.6667 | -1.6667 |
| recommendation | 60 | 37.8523 | 42.4867 | +4.6344 | +4.6574 | +0.0000 | +3.3333 | +0.0000 |
| social | 60 | 36.1961 | 53.4714 | +17.2753 | +17.8207 | -1.6667 | +0.0000 | -1.6667 |
| takeaway | 39 | 25.0977 | 31.0830 | +5.9854 | +5.5636 | +2.5641 | +0.0000 | +2.5641 |
| transport | 60 | 43.9278 | 39.5516 | -4.3762 | -5.6567 | +0.0000 | +0.0000 | +0.0000 |
| weather | 60 | 23.9902 | 26.9295 | +2.9393 | +3.8069 | +0.0000 | +0.0000 | +0.0000 |

## Integrity and attribution

All 1000 direct structured requests match after excluding only request_id and decoding_params.id_slot. Normalized direct intents match on 938/1000: NEW500 466/500 and OLD500 472/500. Raw response hashes match on 841/1000; byte equality is not semantic equality. Temperature0 and a fixed seed did not establish identical independent outputs. No stored sent HTTP-body hash exists, so structured equality must not be reported as exact transport-body equality.

Both arms have 1000 valid fresh predecessor/slot joins, zero final malformed JSON/schema rows, zero recorded refusals, zero saturation and zero fallback events. The control has one unparsed raw slot response; speech has zero. The shared join produces valid final JSON with the parsed first-stage scenario/action and fail-closed slot entities, so raw parser failure and malformed final delivery are reported separately.

OBS uses the same validated speech features. ORG retains original examples and the live predicted-intent schema. SUPPLY adds inherited speech-keyed top-five TRAIN fillers only in slots. USE remains the frozen Solver. The successful S3 fixed-predecessor component evidence is preserved, but it does not establish this live system.

## Cost and scheduling

The pair used 4000 generation calls,12004 live-fit endpoint contacts,0.4502114679422643 fit-inclusive utilization GPU hours against1.0, and0.04799783497199085 kWh. Per-arm costs were0.21377297687994107 and0.2364384910623232 GPU hours, each below0.5. Each processed5769.58737500002 speech seconds. Prompt tokens: control5466457, speech5617837; completion tokens48618 and48416. No packet was newly encoded and no mmproj was loaded into GPU memory.

Control terminal end to speech worker start was approximately420seconds, exceeding the60second handoff target. Root seal verification and coordinator dispatch delay, followed by source-bound packet validation, are retained as operational limitations; the gap is not labelled effective GPU generation. The two complete SLURP scores took124.351seconds in one sequential batch. Device utilization is a sampled device-wide integral, not exact kernel time; sampled request counters are not authoritative call counts. See STATUS-034/035 and the external cost receipts.

## Reproduction and source bindings

Use the four registered fit/generation plans and experiment fragments in docs/readiness/2026-09-11-slurp-program-matched-v1 from frozen source21ebe2bc, through the shared flight worker, registered delivery builder, complete-score batch and saved-score comparator. Existing attempts are one-shot and must never be relaunched. A future independently authorized repetition requires fresh prospective identities.

The machine-readable decision is [decision](2026-09-11-slurp-program-matched-decision.json). DATA denotes SPEECHRL_DATA_DIR.

| Root | Artifact | SHA-256 |
|---|---|---|
| DATA | analysis/SAEA-SLURP-LIVE-PROGRAM-MATCHED-PAIRED-ANALYSIS-V1/paired-contrasts.json | 109d5ca1d0d24776dc7328bdf4e0796f073a5e40b5d369cb5d7b7cc3ba3e1cd5 |
| repo | docs/readiness/2026-09-11-slurp-program-matched-v1/analysis-plan.json | 471e0d7ab6f900b5f2f31a6a7c74dd4d0d7bda22471f1db82da53141e20c5893 |
| DATA | coordination/slurp-program-matched-pair-semantic-request-identity-v1.json | 40f5e6886f8496a3914aa1d22b4138873f6ba0863bb0a60b50435e135887753c |
| DATA | runs/SAEA-SLURP-LIVE-PROGRAM-MATCHED-CONTROL-V1/derived-live-program-matched-control-delivery-v1/SAEA-SLURP-LIVE-PROGRAM-MATCHED-CONTROL-V1--delivery-live-program-matched-control-delivery-v1.run-manifest.json | ca5a6368a262d8b147efc7ed5f8ddd61e7ace74402cee65b131001163e145c75 |
| DATA | runs/SAEA-SLURP-LIVE-PROGRAM-MATCHED-CONTROL-V1/derived-live-program-matched-control-delivery-v1/SAEA-SLURP-LIVE-PROGRAM-MATCHED-CONTROL-V1--delivery-live-program-matched-control-delivery-v1.outputs.jsonl | 1a052d01046b67065f0b93092cdcd08b7a69533c93b0372ad43ba34369a89725 |
| DATA | runs/SAEA-SLURP-LIVE-PROGRAM-MATCHED-SPEECH-V1/derived-live-program-matched-speech-delivery-v1/SAEA-SLURP-LIVE-PROGRAM-MATCHED-SPEECH-V1--delivery-live-program-matched-speech-delivery-v1.run-manifest.json | 7692f280830fcb20bea8a1eeb57e4230aacce044af46026f24c011e63ca3b7b2 |
| DATA | runs/SAEA-SLURP-LIVE-PROGRAM-MATCHED-SPEECH-V1/derived-live-program-matched-speech-delivery-v1/SAEA-SLURP-LIVE-PROGRAM-MATCHED-SPEECH-V1--delivery-live-program-matched-speech-delivery-v1.outputs.jsonl | 1331a55080d0020bb49f4f59fa0ab75c0ccdda49a2bc64ebfcaea82f72fa0e6c |
| DATA | coordination/slurp-program-matched-final-delivery-shape-v1.json | c5d935b4c53f5edaed4dd44b202bc2262dfd93742dd481e61bbfe3dc2ad43628 |


## Completed custody and operational audit

Both generation attempts are FINALIZED through shared saved-score settlement. Saved receipts were independently reverified and raw manifest hashes are unchanged. No new score or model contact occurred. DATA coordination/e21-slurp-root-settlement-closure-v1.json, SHA-256 9e6fa8582c794e599707217c5055e6bab499790ec0dd460ead9991b4d90e9db9, binds all four settlements and root decisions. FINALIZED is operational completion, not scientific admission.

DATA coordination/e21-slurp-operational-timing-audit-v1.json, SHA-256 fdc8372ae28ea89b3995528a5de58e730da511586e49856be61f386f3d276b16, binds25 source records and separates timing limitations. E21 generation-contact-window device averages are53.5130%/56.9506%; SLURP fit-inclusive attached-operation averages67.8145%/70.6379%. These are not sustained full GPU utilization or exact kernel time. The419.538second SLURP handoff and119.558second speech-worker precontact period are separate. Neither pair integral includes initial model loading or between-stage idle. E21 fits and historical encoding are outside its quoted generation total.
