# SLURP discriminative values: source-span bundle result

Date: September 11, 2026. Status: **NEGATIVE_COMPONENT_NOT_SELECTED**. Both generation attempts are FINALIZED from their first complete saved official scores. This is a bounded discovery component result on historically exposed data.

## Decision and interpretation

The source-span/role-frame bundle reduces the preregistered NEW500 mean per-row SLU F1 by 6.0619 percentage points; the paired speaker-cluster CI90 is [-8.6038, -3.8683]. Its interval is wholly below zero, so the prospective descriptive decision is negative. Do not select this bundle for the system or repeat this closed pair to seek a pass.

The outcome does not refute the owner principle that useful values should provide task-relevant distinctions. This experiment supplied source tokens, mention positions and roles together; it did not explicitly construct competing hypotheses, discriminating conditions or applicability boundaries. More source information was not sufficient in this implementation. No causal claim separates length, templates, source context, positions or mention multiplicity.

The named observed failure channel is increased omission at consumption. On NEW500, empty entity results rise from136 to191, with67 nonempty-to-empty transitions and12 reverse transitions. Of the67 new empty results,46 have at least one reference entity. Missing loss mass rises70 units while spurious mass falls36. Some empty results are correct; empty entity lists are not empty model responses.

## Fixed comparison and validity

Both arms use the same retained decoder-only process, frozen Qwen core/build, c65536/np4,16384 tokens per slot, max256, identical cached current-speech packets, identical sealed intent predecessor, identical shared slots-given-intent phase and OpenJiuwen executor, and the same new grounding instruction. Both retain the original KC-S1b schema examples. Top5 retrieved TRAIN value IDs and ordering match on every one of1000 rows. Only the registered value bundle and its source identities differ.

This new historical-value arm includes the common new grounding instruction. It is not an unchanged KC-S1b rerun or a no-retrieval control. No current intent improvement or full-system effect is measured. OBS and key selection are held fixed; the ORG value representation and resulting SUPPLY/USE bundle are changed jointly.

Both actual whole-roster fits pass:3001 endpoints each, minimum token margin5807 for historical and4901 for span. No result read occurred before both seals and root release. Each complete1000-row official scorer ran once with per-sample ingredients. Complete score receipts and immutable saved-score settlement were verified before analysis. No raw parent was rewritten and no rescore occurred.

## Preregistered paired results

All F1 values below are percentages; changes and intervals are percentage points. Primary uncertainty is10000 paired speaker-cluster bootstrap replicates, seed20260903, CI90. Natural mixture is primary; equal-scenario weighting and scenario-stratified row bootstrap remain separate sensitivity views. Mean per-row F1 is not pooled-count micro F1.

| Population | Speakers | Row F1 historical | Row F1 span | Change | Speaker CI90 | Improved / harmed / tied | Equal-scenario row change |
|---|---:|---:|---:|---:|---|---|---:|
| NEW500 | 115 | 39.4416 | 33.3798 | -6.0619 | [-8.6038, -3.8683] | 23 / 63 / 414 | -6.0340 |
| OLD500 | 111 | 33.6186 | 28.0018 | -5.6167 | [-7.6042, -3.8282] | 19 / 61 / 420 | -5.6486 |
| DEV1000 | 124 | 36.5301 | 30.6908 | -5.8393 | [-7.4846, -4.3530] | 42 / 124 / 834 | -5.7591 |

| Population | Micro F1 historical | Micro F1 span | Change | Speaker CI90 | Equal-scenario micro change |
|---|---:|---:|---:|---|---:|
| NEW500 | 54.5949 | 50.6868 | -3.9081 | [-6.2531, -1.7327] | -5.2593 |
| OLD500 | 49.7300 | 44.6822 | -5.0478 | [-7.4484, -2.7491] | -5.2829 |
| DEV1000 | 52.2071 | 47.7879 | -4.4192 | [-6.0610, -2.8102] | -5.0808 |

## Entity metrics and exhaustive distance-loss attribution

The shared pure attribution helper reconciles each of the six official word/character TP,FP,FN ingredients on all2000 scored rows. Four buckets exhaust FP+FN loss mass, not F1 percentage points. Type swaps use same-normalized-filler/different-type matching and are diagnostic, not evidence about an internal model cause. Surface loss can include boundary, spelling and lexical errors; it is not solely a boundary-error count.

| Population / arm | Strict entity micro F1 | Word micro F1 | Character micro F1 | Surface mass | Type-swap mass | Spurious mass | Missing mass | Predicted / reference entities | Empty entity rows |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| NEW500 / historical | 41.7582 | 51.7464 | 57.7752 | 282.7621 | 96 | 220 | 356 | 421 / 489 | 136 |
| NEW500 / span | 38.2730 | 47.6583 | 54.1263 | 290.4677 | 88 | 184 | 426 | 368 / 489 | 191 |
| OLD500 / historical | 37.2842 | 46.8184 | 53.0278 | 288.9441 | 80 | 272 | 378 | 408 / 461 | 142 |
| OLD500 / span | 32.1384 | 42.1159 | 47.5817 | 252.9895 | 84 | 236 | 462 | 348 / 461 | 191 |
| DEV1000 / historical | 39.5728 | 49.3193 | 55.4541 | 571.7062 | 176 | 492 | 734 | 829 / 950 | 278 |
| DEV1000 / span | 35.2941 | 44.9859 | 50.9621 | 543.4571 | 172 | 420 | 888 | 716 / 950 | 382 |

## Every scenario

Scenario estimates are descriptive; no stratum is selected as a new success gate. Speaker counts need not add to the population total because speakers can occur in several scenarios.

| Population | Scenario | Rows | Speakers | Historical row F1 | Span row F1 | Row change | Micro change | Improved / harmed / tied |
|---|---|---:|---:|---:|---:|---:|---:|---|
| NEW500 | alarm | 30 | 19 | 31.8853 | 29.8118 | -2.0735 | -2.4484 | 2 / 2 / 26 |
| NEW500 | audio | 2 | 2 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 / 0 / 2 |
| NEW500 | calendar | 33 | 29 | 36.3718 | 30.1721 | -6.1997 | -4.1361 | 2 / 5 / 26 |
| NEW500 | cooking | 9 | 8 | 63.0592 | 63.0592 | 0.0000 | 0.0000 | 0 / 0 / 9 |
| NEW500 | datetime | 33 | 27 | 56.9721 | 37.1390 | -19.8331 | -16.6995 | 1 / 9 / 23 |
| NEW500 | email | 33 | 25 | 26.7449 | 24.7475 | -1.9974 | 0.2202 | 1 / 3 / 29 |
| NEW500 | general | 33 | 26 | 12.6236 | 5.5529 | -7.0707 | -15.3236 | 0 / 3 / 30 |
| NEW500 | iot | 33 | 24 | 44.4891 | 44.1228 | -0.3663 | 2.0785 | 1 / 2 / 30 |
| NEW500 | lists | 32 | 26 | 17.2714 | 12.0630 | -5.2083 | -9.4807 | 0 / 2 / 30 |
| NEW500 | music | 23 | 18 | 15.9595 | 12.7283 | -3.2313 | -8.0245 | 0 / 1 / 22 |
| NEW500 | news | 32 | 29 | 41.6393 | 30.1377 | -11.5016 | -5.9214 | 0 / 5 / 27 |
| NEW500 | play | 32 | 24 | 37.5812 | 39.2136 | 1.6325 | -1.3309 | 1 / 2 / 29 |
| NEW500 | qa | 32 | 23 | 54.4930 | 49.6373 | -4.8558 | -2.5263 | 0 / 2 / 30 |
| NEW500 | recommendation | 32 | 26 | 56.1594 | 51.2356 | -4.9238 | 0.5053 | 2 / 4 / 26 |
| NEW500 | social | 33 | 28 | 52.6582 | 37.4216 | -15.2367 | -6.5289 | 4 / 9 / 20 |
| NEW500 | takeaway | 12 | 11 | 34.8984 | 11.5707 | -23.3277 | -25.6175 | 0 / 4 / 8 |
| NEW500 | transport | 33 | 30 | 45.9245 | 46.2179 | 0.2933 | 5.1184 | 7 / 5 / 21 |
| NEW500 | weather | 33 | 29 | 50.9511 | 46.2387 | -4.7124 | -4.5515 | 2 / 5 / 26 |
| OLD500 | alarm | 28 | 14 | 16.0998 | 13.9569 | -2.1429 | -6.2197 | 0 / 1 / 27 |
| OLD500 | audio | 28 | 17 | 3.6800 | 2.5210 | -1.1590 | -4.6807 | 1 / 1 / 26 |
| OLD500 | calendar | 28 | 25 | 27.4887 | 29.2745 | 1.7857 | 1.5254 | 1 / 1 / 26 |
| OLD500 | cooking | 28 | 20 | 47.3130 | 35.4813 | -11.8317 | -9.0775 | 0 / 6 / 22 |
| OLD500 | datetime | 28 | 24 | 35.1348 | 27.0720 | -8.0628 | -8.7831 | 0 / 3 / 25 |
| OLD500 | email | 28 | 21 | 30.0231 | 21.7820 | -8.2411 | -6.1156 | 1 / 4 / 23 |
| OLD500 | general | 28 | 21 | 18.2251 | 13.1918 | -5.0333 | -11.6381 | 0 / 2 / 26 |
| OLD500 | iot | 28 | 24 | 34.5346 | 33.4941 | -1.0405 | -1.0940 | 1 / 1 / 26 |
| OLD500 | lists | 28 | 23 | 25.1134 | 20.5180 | -4.5954 | -4.9608 | 0 / 2 / 26 |
| OLD500 | music | 28 | 24 | 16.0506 | 16.0506 | 0.0000 | 0.0000 | 0 / 0 / 28 |
| OLD500 | news | 28 | 24 | 45.8813 | 25.6432 | -20.2381 | -15.4095 | 1 / 7 / 20 |
| OLD500 | play | 28 | 25 | 43.3337 | 40.7884 | -2.5453 | 0.6963 | 1 / 2 / 25 |
| OLD500 | qa | 28 | 26 | 34.3813 | 32.4109 | -1.9704 | -1.2540 | 0 / 1 / 27 |
| OLD500 | recommendation | 28 | 23 | 19.5804 | 21.5035 | 1.9231 | 3.0956 | 2 / 2 / 24 |
| OLD500 | social | 27 | 19 | 66.1578 | 37.4713 | -28.6865 | -22.6481 | 1 / 12 / 14 |
| OLD500 | takeaway | 27 | 25 | 36.3237 | 36.1395 | -0.1842 | -0.8685 | 3 / 4 / 20 |
| OLD500 | transport | 27 | 21 | 46.8748 | 45.7086 | -1.1663 | -4.1638 | 4 / 6 / 17 |
| OLD500 | weather | 27 | 24 | 61.6724 | 53.1859 | -8.4865 | -3.4968 | 3 / 6 / 18 |
| DEV1000 | alarm | 58 | 27 | 24.2647 | 22.1577 | -2.1070 | -4.0207 | 2 / 3 / 53 |
| DEV1000 | audio | 30 | 18 | 3.4346 | 2.3529 | -1.0817 | -4.6807 | 1 / 1 / 28 |
| DEV1000 | calendar | 61 | 48 | 32.2943 | 29.7601 | -2.5343 | -2.2145 | 3 / 6 / 52 |
| DEV1000 | cooking | 37 | 28 | 51.1431 | 42.1894 | -8.9537 | -6.4754 | 0 / 6 / 31 |
| DEV1000 | datetime | 61 | 44 | 46.9484 | 32.5181 | -14.4303 | -12.8806 | 1 / 12 / 48 |
| DEV1000 | email | 61 | 37 | 28.2496 | 23.3863 | -4.8634 | -3.1808 | 2 / 7 / 52 |
| DEV1000 | general | 61 | 38 | 15.1948 | 9.0593 | -6.1355 | -12.8776 | 0 / 5 / 56 |
| DEV1000 | iot | 61 | 41 | 39.9198 | 39.2441 | -0.6758 | 0.5381 | 2 / 3 / 56 |
| DEV1000 | lists | 60 | 40 | 20.9310 | 16.0087 | -4.9223 | -6.7452 | 0 / 4 / 56 |
| DEV1000 | music | 51 | 33 | 16.0096 | 14.5523 | -1.4572 | -4.4405 | 0 / 1 / 50 |
| DEV1000 | news | 60 | 46 | 43.6189 | 28.0403 | -15.5786 | -10.4668 | 1 / 12 / 47 |
| DEV1000 | play | 60 | 41 | 40.2657 | 39.9485 | -0.3172 | -0.2868 | 2 / 4 / 54 |
| DEV1000 | qa | 60 | 40 | 45.1076 | 41.5983 | -3.5093 | -1.9893 | 0 / 3 / 57 |
| DEV1000 | recommendation | 60 | 42 | 39.0892 | 37.3606 | -1.7286 | 1.3041 | 4 / 6 / 50 |
| DEV1000 | social | 60 | 41 | 58.7330 | 37.4440 | -21.2891 | -13.3238 | 5 / 21 / 34 |
| DEV1000 | takeaway | 39 | 33 | 35.8851 | 28.5799 | -7.3052 | -6.6094 | 3 / 8 / 28 |
| DEV1000 | transport | 60 | 47 | 46.3522 | 45.9887 | -0.3635 | 0.9213 | 11 / 11 / 38 |
| DEV1000 | weather | 60 | 45 | 55.7757 | 49.3650 | -6.4107 | -4.0261 | 5 / 11 / 44 |

## Inputs, contacts and operational observations

| Quantity | Historical | Span |
|---|---:|---:|
| Generation calls | 1000 | 1000 |
| Separate fit endpoint calls | 3001 | 3001 |
| Current-speech seconds | 2884.7936875 | 2884.7936875 |
| Supplied value characters, full roster | 431962 | 2546681 |
| Prompt tokens | 3260548 | 3878532 |
| Completion tokens | 22980 | 23724 |
| Maximum completion tokens | 67 | 80 |
| Output-limit finishes | 0 | 0 |
| Official parser failures | 1 | 1 |
| Empty response text | 0 | 0 |
| Contact-window seconds including fit | 782.7959353923798 | 1010.2753720283508 |
| Device utilization-integral GPU hours including fit | 0.15269437059428956 | 0.22157351229853095 |
| Device energy kWh during that window | 0.016164211412982812 | 0.022324466377556983 |
| Complete official score seconds | 79.89605675099301 | 34.37884755298728 |

All2000 raw wire responses finish with stop; each arm has1000 unique requests and1000 matching responses, with no unanswered request or additional generation request. Each arm has one parsing failure, zero empty text and zero unadmitted output rows. No response reaches max256. The parsed empty-entity shift therefore cannot be explained by output-cap saturation or a large parser-failure increase. Skip/fallback counters are not separately published and are not invented; the raw model response remains available.

The pair consumes0.3742678829 utilization-integrated GPU hours including both fits, within the registered1.0 family ceiling and0.5 per arm. This is a sampled device-wide integral, not generation-only kernel time or a cost reward. Root independently recomputed the right-endpoint, max20-second covered interval method from the sealed monitor prefix; coverage gaps and server-not-ok samples are zero.

No model reload or geometry switch occurs between the arms. Historical attached work runs16:41:53.448290-16:54:56.244225 UTC; span runs16:57:55.980544-17:14:46.255916 UTC. The179.7363-second interval between those windows includes handoff/preparation before the second attached window; it is not labeled useful GPU time or claimed to meet the one-minute objective. CPU preparation and fit time inside each window are not separately identifiable from these cost receipts. Official scoring is serial,117.1483 seconds total batch time after the pair seals. Subsequent scientific analysis/review is a decision-wait interval; the service remains resident. Do not conflate current no-generation time with device failure.

## Next distinct work

1. Retain historical values as the comparator for this specific supplied phase; do not promote the negative span bundle or reopen the pair.
2. Construct compact TRAIN-grounded presence/role contrast cards: state the competing interpretations, positive and excluding evidence, applicability limits and unresolved cases. A source phrase is evidence for a distinction, not sufficient proof of it. Derive card content from permitted construction data and task contracts, never from DEV answers. Validate construction and consumption together.
3. Keep artifact/value changes separate from new review actions during attribution. Then register a complete shared agent comparison with live initial state, permitted knowledge/tool actions and Solver delivery; fixed-predecessor results do not replace this system proof.
4. Corrective memory requires a distinct admitted construction/validation result. Historical EVO-S1 TRAIN trajectories are sources for hypotheses; the rejected round supplies no admitted memory catalog. Complete the isolated runtime review, then construct and validate actual records before use.
5. In parallel, keep Audio2Tool operation/argument/state distinction cards covering all eight tiers; native first-call metrics remain primary. E21/E22 knowledge must serve native transcription/entity fidelity rather than an invented summary objective. No additional GPU contact is registered by this result note.

## Immutable evidence

Paths prefixed DATA refer to SPEECHRL_DATA_DIR. The analysis template and generation configurations remain unchanged.

| Artifact | SHA-256 |
|---|---|
| docs/readiness/2026-09-11-slurp-discriminative-values-protocol.md | 93f67338700ee37abc2fb285ed5884d9cce0ee458ea46e119ea11962188f3b92 |
| DATA/coordination/slurp-discriminative-values-postseal-score-read-release-v1.json | df4af38600b4911fb7d7312395a26ab757c77ed7a6afd86a283e07f353adcbd8 |
| DATA/analysis/SAEA-SLURP-DISCRIMINATIVE-VALUE-PAIRED-ANALYSIS-V1/bound-analysis-v1.json | f8e21598f51a20b4476641fb6c22dd4d9980f91a96717b67c7d037bc9e1c7767 |
| DATA/analysis/SAEA-SLURP-DISCRIMINATIVE-VALUE-PAIRED-ANALYSIS-V1/paired-analysis-v1.json | 787b206c36b873c89fd945e261681f0be0310c87a5b3b5d2dc7ef3ac6e795e14 |
| DATA/analysis/SAEA-SLURP-DISCRIMINATIVE-VALUE-PAIRED-ANALYSIS-V1/entity-attribution-v1.json | ee80a7cda96b022042faffb2c323b5db2bcf4696dde91a068f40f2b06e95409d |
| DATA/analysis/SAEA-SLURP-DISCRIMINATIVE-VALUE-PAIRED-ANALYSIS-V1/operational-read-v1.json | 61bfc88abea80efcab2cbc176240019b82d568fdd527fcba1ae29a11d790e62b |
| DATA/coordination/slurp-discriminative-values-cost-audit-v1.json | 26afafc1a6134f53897d2d4a3dd021d7ea74762d528f23d381071fa7d07d3b81 |
| DATA/coordination/slurp-discriminative-values-historical-score-settlement-v1.json | 0087030cb16602b6a51078e2449975f6adc5edd89e3dc56be239ea1e2aaf15f5 |
| DATA/coordination/slurp-discriminative-values-span-score-settlement-v1.json | 2fff21b9ab460730557d548f3ff30168d37009ecc77e8aaf3699dd6386175df2 |

Generation source: ae305d9b84ad1346fcf482ca3e87a1690efb3bd8. First scoring and paired analysis use the same implementation (fe21b7ca adds only the result-read ledger row). Shared attribution extraction and root ingredient-validation fix are at7941f225abfd6c495152a11fca6d39f50521beec. Focused attribution/official-adapter checks:33 passed,1 optional test skipped; Ruff and engineering-base check pass. The first offline attribution orchestration read the legacy roster under the wrong item key, produced no result and made no model/scorer contact; a source-pinned successor corrected the reader. This does not alter the frozen statistical plan.
