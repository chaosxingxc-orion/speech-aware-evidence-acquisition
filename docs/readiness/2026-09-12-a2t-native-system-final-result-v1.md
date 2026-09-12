# Audio2Tool native system: final recovery result

Snapshot: September 12, 2026. All three arms are FINALIZED and COMPLETED, with one hash-bound first complete official score each. Root decided the unchanged frozen rules at 18:54:16 UTC. This report reads sealed registered analysis; it adds no model or scorer contact.

## Decision and scientific meaning

- promising_system: NOT_ADMITTED. Knowledge minus direct official exact match is -0.300 percentage points, primary 97.5% interval [-1.122450, 0.513876]; the frozen threshold is +1.0 point. Tool accuracy also declines by 3.475 points.
- knowledge_contribution: NOT_ESTABLISHED. Knowledge minus matched stage control exact match is +0.650 points, primary 97.5% interval [-0.102700, 1.429677]; the frozen threshold is +1.0 point. Do not add the whole-system tool/F1 guards to this separate label.
- Equal-tier primary intervals lead to the same two decisions. The eight tiers each contain 500 rows, so natural-mixture and equal-tier points coincide.
- Close this configuration without additional generation. This is a negative or unresolved result for this system package, not proof that external tools, knowledge or training-free system optimization cannot help.

The 4000-row roster contains 2097 query_idx clusters, including 677 that cross tiers. The registered analysis uses 10000 whole-query cluster bootstrap draws and frozen seeds. Primary intervals are 97.5%; secondary intervals are 90%. The positive secondary interval for knowledge minus stage control must not replace the failed primary declaration.

## Complete-arm overview

| Metric | Direct | Stage control | Knowledge | Published equal-tier reference |
|---|---:|---:|---:|---:|
| Exact match, percent | 18.900 | 17.950 | 18.600 | 29.675 |
| Tool accuracy, percent | 62.025 | 60.525 | 58.550 | 69.1875 |
| Macro parameter F1, percent | 30.290774 | 29.117917 | 30.719464 | Not in pinned row |
| Parse failures | 24 | 22 | 77 | Not in pinned row |
| Generation contacts | 4000 | 8000 | 8000 | Not a matched run |

Published values come from the frozen a2t_v2_rescore.PAPER_TIER_ROW, described as Table 3 in the pinned scorer provenance. They are a contextual reference, not a matched model, population or mathematical ceiling. The very large Tier 1 gap remains a reproduction/interface question; do not attribute it to one component from this comparison.

## Complete strata

The following are descriptive points. Do not infer per-stratum significance from them. Exact intervals, all secondary metrics, signs and both weighting schemes remain in the pinned full analysis.

### official_exact_match

| Stratum | n | Direct % | Stage control % | Knowledge % | Published reference % |
|---|---:|---:|---:|---:|---:|
| tier1_direct | 500 | 16.600000 | 15.400000 | 10.800000 | 92.4 |
| tier2_parametric | 500 | 28.200000 | 27.400000 | 30.200000 | 15.6 |
| tier3_multi_intent | 500 | 20.400000 | 18.800000 | 19.600000 | 28.6 |
| tier4_implicit | 500 | 6.600000 | 6.200000 | 6.600000 | 11.3 |
| tier5_needle | 500 | 21.200000 | 20.600000 | 22.600000 | 36.0 |
| tier6_correction | 500 | 25.000000 | 24.000000 | 26.600000 | 24.8 |
| tier7_multiturn | 500 | 10.600000 | 9.800000 | 9.800000 | 16.3 |
| tier8_intent_blending | 500 | 22.600000 | 21.400000 | 22.600000 | 12.4 |
| smart_car | 351 | 47.008547 | 45.014245 | 46.153846 | Not in pinned row |
| smart_home | 2792 | 9.598854 | 9.204871 | 8.810888 | Not in pinned row |
| wearables | 857 | 37.689615 | 35.355893 | 39.206534 | Not in pinned row |

### official_tool_accuracy

| Stratum | n | Direct % | Stage control % | Knowledge % | Published reference % |
|---|---:|---:|---:|---:|---:|
| tier1_direct | 500 | 67.000000 | 66.400000 | 63.400000 | 92.4 |
| tier2_parametric | 500 | 77.600000 | 77.600000 | 75.800000 | 84.6 |
| tier3_multi_intent | 500 | 68.200000 | 63.000000 | 59.800000 | 74.7 |
| tier4_implicit | 500 | 29.000000 | 27.800000 | 26.400000 | 33.4 |
| tier5_needle | 500 | 80.000000 | 80.600000 | 77.200000 | 90.6 |
| tier6_correction | 500 | 76.400000 | 75.400000 | 74.600000 | 81.5 |
| tier7_multiturn | 500 | 48.600000 | 47.200000 | 45.200000 | 54.6 |
| tier8_intent_blending | 500 | 49.400000 | 46.200000 | 46.000000 | 41.7 |
| smart_car | 351 | 72.649573 | 71.794872 | 69.800570 | Not in pinned row |
| smart_home | 2792 | 55.372493 | 54.297994 | 51.540115 | Not in pinned row |
| wearables | 857 | 79.346558 | 76.196033 | 76.779463 | Not in pinned row |

### official_macro_parameter_f1

| Stratum | n | Direct % | Stage control % | Knowledge % | Published reference % |
|---|---:|---:|---:|---:|---:|
| tier1_direct | 500 | 22.600000 | 22.200000 | 20.600000 | Not in pinned row |
| tier2_parametric | 500 | 45.303333 | 43.756667 | 46.356667 | Not in pinned row |
| tier3_multi_intent | 500 | 35.427619 | 32.453333 | 33.117619 | Not in pinned row |
| tier4_implicit | 500 | 15.953333 | 15.973333 | 16.860000 | Not in pinned row |
| tier5_needle | 500 | 34.360952 | 33.229048 | 36.033333 | Not in pinned row |
| tier6_correction | 500 | 38.390000 | 38.279524 | 42.826190 | Not in pinned row |
| tier7_multiturn | 500 | 18.546667 | 17.903810 | 18.563810 | Not in pinned row |
| tier8_intent_blending | 500 | 31.744286 | 29.147619 | 31.398095 | Not in pinned row |
| smart_car | 351 | 56.362773 | 54.767331 | 56.904084 | Not in pinned row |
| smart_home | 2792 | 22.669447 | 22.088706 | 22.800092 | Not in pinned row |
| wearables | 857 | 44.441851 | 41.513030 | 45.795410 | Not in pinned row |

## Component diagnostics and limits

- The staged control loses 0.950 exact-match points versus direct; its exploratory CI90 is entirely below zero. The added stage and own-draft reuse are a harmful package in this run. This does not isolate the exact prompt or state mechanism.
- Every knowledge final request contains eight supplied values. Supply records average 12951.606 characters; final prompt tokens average 7247.13 versus 3774.555 for stage control. These are observed input increases, not causal proof that length causes the harm.
- Knowledge has 67 new parse failures and 12 recovered parses versus stage control: 55 net additional failures. Tool correctness has 178 harms and 99 saves. Of 178 harms, 44 move from correct to unparsed and 134 remain parsed but choose incorrectly. Formatting alone therefore does not explain the entire regression.
- All 12000 final responses are nonempty and record finish reason stop. No final output-length saturation is recorded. Do not propose a token-cap increase as an established fix for this result.
- All 4000 paired initial-stage task/evidence/decoding fields match except execution slot IDs; 3041 initial response texts match. Preserve independent-predecessor variation and fixed arm order as limitations.
- Independent reconciliation matched all 234 reported native/equal-tier/tier/domain points, with maximum floating discrepancy 1.42e-14. No scorer or bootstrap was rerun for that audit.
- Exposed discovery outcomes are analysis evidence. They do not become admitted corrective-memory records or enter a TRAIN proposal as reference content.

## Reproducibility receipts

- Full analysis: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-A2T-NATIVE-SYSTEM-ANALYSIS-V1/score-contrasts.json; SHA256 c03cf0dff4607c750a1473dc8a5ebc8d19aaee790630a5bb5e2b9ce9a967acb0.
- Root decision: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/coordination/a2t-native-system-root-decision-v1.json; SHA256 9d9df7fa1c9a2572473b74f84ad64f279b0ba6821f4d16882b037415548b5b42.
- Independent reconciliation: DATA analysis/SAEA-A2T-NATIVE-SYSTEM-ANALYSIS-RECONCILIATION-V1/independent-reconciliation-v1.json; SHA256 c2b44d3d7d048b6316dd731816b464b7d2e9ba687331c84ca2a6f84e8eccdba0.
- Executed generation source: 22b56d706e2f5601dc79f58a8fad2bb6a9629f51. Frozen analysis source: 5f79d399dc15016aaeedccac347aebffddfc61ca. Actual read registration: 7e51daf96f801b5f54d65060e15ffe202bfa8f4c.
- The root decision pins all three finalized manifests, first complete scores, the frozen decision rule and the individual diagnostic receipts.

## Next route

Retain the replicated compact SLURP working baseline. Test fixed local Whisper evidence with matched plan/solve/revise arms before evaluating Reviewer targeting. The first Whisper preparation subsequently aborted on its first batched beam decode, after eight charged source contacts and before any sealed observation; recovery is separate from this completed A2T decision.
