# a2t-scorer-v2 re-score of the September Audio2Tool runs (2026-09-03)

Model-free, read-only offline re-scoring of already-sealed `outputs.jsonl` files under the registered `a2t-scorer-v2` (`reproduction.toolcall_scoring_v2`), reported side by side with the unchanged v1 scorer. Zero model/tool/network/audio/GPU contact.

Scorer versions: `a2t-scorer-v1` (v1, unchanged) / `a2t-scorer-v2` (v2).

## Per-arm table (v1 identity check, then v1 and v2 aggregate; exact / tool ordered / tool multiset / slot F1 / parse)

| source/arm | run | n | identity | v1 exact | v1 tool | v2 exact | v2 tool (ordered) | v2 tool (multiset) | v2 slot F1 | v1 slot F1 | parse rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a0/zero_supply | SAEA-BASE-a2t-a0-400 | 400 | match | 0.2425 | 0.5425 | 0.3125 | 0.5300 | 0.5425 | 0.4363 | 0.3434 | 0.9400 |
| semantic104/direct_m0 | SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1 | 104 | match | 0.2404 | 0.5096 | 0.2981 | 0.5000 | 0.5096 | 0.4149 | 0.3333 | 0.8942 |
| semantic104/transcript_top16_use | SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1 | 104 | match | 0.2596 | 0.5962 | 0.3750 | 0.5769 | 0.5962 | 0.4296 | 0.3470 | 1.0000 |
| semantic104/model_query_top16_use | SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1 | 104 | match | 0.2308 | 0.5769 | 0.3269 | 0.5577 | 0.5769 | 0.4000 | 0.3185 | 1.0000 |
| semantic104/rrf_fused_top16_use | SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1 | 104 | match | 0.2404 | 0.5769 | 0.3558 | 0.5577 | 0.5769 | 0.4385 | 0.3495 | 0.9904 |
| semantic104/same_stratum_shuffled_fused_use | SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1 | 104 | match | 0.0385 | 0.0865 | 0.0385 | 0.0865 | 0.0865 | 0.1326 | 0.1206 | 1.0000 |
| selectfill104/DIRECT_M0 | SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5 | 104 | match | 0.1731 | 0.4038 | 0.2404 | 0.3942 | 0.4038 | 0.3712 | 0.3019 | 0.8558 |
| selectfill104/JOINT_ONE_CALL | SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5 | 104 | match | 0.2404 | 0.6250 | 0.3173 | 0.6058 | 0.6250 | 0.4756 | 0.4045 | 1.0000 |
| selectfill104/JOINT_DRAFT_REVISE | SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5 | 104 | match | 0.2500 | 0.6346 | 0.3269 | 0.6154 | 0.6346 | 0.4756 | 0.4068 | 1.0000 |
| selectfill104/SELECT_THEN_FILL | SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5 | 104 | match | 0.2500 | 0.5962 | 0.3462 | 0.5865 | 0.5962 | 0.4714 | 0.3652 | 1.0000 |
| cpv2/M0 | SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2 | 104 | match | 0.3077 | 0.5865 | 0.3558 | 0.5865 | 0.5865 | 0.4627 | 0.3742 | 0.9423 |
| cpv2/matched | SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2 | 104 | match | 0.3846 | 0.7019 | 0.4038 | 0.7019 | 0.7019 | 0.4982 | 0.4091 | 1.0000 |
| cpv2/shuffled | SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2 | 104 | match | 0.2692 | 0.4904 | 0.2885 | 0.4808 | 0.4904 | 0.3954 | 0.3208 | 0.9904 |
| cpv2/resend | SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2 | 104 | match | 0.3750 | 0.6923 | 0.3942 | 0.6923 | 0.6923 | 0.4964 | 0.4180 | 1.0000 |
| cpv2/cross_fitted_policy | SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2 | 104 | match | 0.2885 | 0.5673 | 0.3365 | 0.5673 | 0.5673 | 0.4488 | 0.3648 | 0.9423 |
| g1_m0_shared/M0 | SAEA-A2T-G1 | 104 | match | 0.2788 | 0.5962 | 0.3846 | 0.5769 | 0.5962 | 0.5362 | 0.4379 | 0.9615 |
| self_transcript_cascade/USE_MATCHED | SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1 | 104 | match | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0096 |
| self_transcript_cascade/USE_SHUFFLED_EVIDENCE | SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1 | 104 | match | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0192 |
| self_transcript_cascade/MATCHED_RESEND_COMPOSITE | SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1 | 104 | match | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0096 |
| self_transcript_cascade/CROSSFIT_POLICY | SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1 | 104 | match | 0.2788 | 0.5962 | 0.3846 | 0.5769 | 0.5962 | 0.5362 | 0.4379 | 0.9615 |
| self_consistency/REOBSERVE_DIRECT | SAEA-A2T-TFRL-SELF-CONSISTENCY-104-V1 | 104 | match | 0.2212 | 0.5288 | 0.2981 | 0.5192 | 0.5288 | 0.4833 | 0.4063 | 0.9615 |
| self_consistency/SUPPLY_UNION_STRIPPED | SAEA-A2T-TFRL-SELF-CONSISTENCY-104-V1 | 104 | match | 0.2212 | 0.5769 | 0.2500 | 0.5577 | 0.5769 | 0.3955 | 0.3569 | 0.9231 |
| g3/m0 | SAEA-A2T-G3-PLAIN-ENGLISH-V1 | 40 | match | 0.2000 | 0.5250 | 0.2750 | 0.5000 | 0.5250 | 0.4324 | 0.3333 | 0.8750 |
| g3/matched | SAEA-A2T-G3-PLAIN-ENGLISH-V1 | 40 | match | 0.2000 | 0.6750 | 0.2750 | 0.6500 | 0.6750 | 0.4144 | 0.3548 | 1.0000 |
| g3/shuffled | SAEA-A2T-G3-PLAIN-ENGLISH-V1 | 40 | match | 0.1750 | 0.6000 | 0.1750 | 0.5750 | 0.6000 | 0.2679 | 0.2500 | 0.9750 |
| g5/g5 | SAEA-A2T-G5-EXHAUSTIVE-FAMILY-FIXED16-V1 | 16 | match | 0.1875 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.3200 | 0.1702 | 1.0000 |
| g6/g6_seal | SAEA-A2T-G6-EXHAUSTIVE-FAMILY-SWEEP-FIXED16-V1 | 16 | match | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| g7/g7 | SAEA-A2T-G7-MULTIMODAL-EXHAUSTIVE-EXAMPLE-GROUND-FIXED16-V2 | 16 | match | 0.1875 | 0.4375 | 0.1875 | 0.3750 | 0.4375 | 0.4375 | 0.4058 | 1.0000 |
| g8c/STOP_M0 | SAEA-A2T-G8C-ACTION-SUPPORT-REACHABILITY-FIXED12-V1 | 12 | match | 0.3333 | 0.8333 | 0.5000 | 0.8333 | 0.8333 | 0.6111 | 0.5116 | 1.0000 |
| g8c/EXHAUSTIVE_G7 | SAEA-A2T-G8C-ACTION-SUPPORT-REACHABILITY-FIXED12-V1 | 12 | match | 0.0833 | 0.5833 | 0.0833 | 0.5833 | 0.5833 | 0.2105 | 0.1951 | 1.0000 |
| g8c/SUPPORT_ONLY_RESOLVE | SAEA-A2T-G8C-ACTION-SUPPORT-REACHABILITY-FIXED12-V1 | 12 | match | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| g8c/DECOMPOSED_SELECT_BIND_RESOLVE | SAEA-A2T-G8C-ACTION-SUPPORT-REACHABILITY-FIXED12-V1 | 12 | match | 0.0833 | 0.7500 | 0.0833 | 0.7500 | 0.7500 | 0.2857 | 0.2632 | 0.9167 |
| native_structured/REGISTRY_NO_SCHEMA | SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1 | 8 | match | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| native_structured/REGISTRY_STRICT_ACTION | SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1 | 8 | match | 0.2500 | 0.5000 | 0.3750 | 0.5000 | 0.5000 | 0.4615 | 0.3333 | 1.0000 |
| native_structured/HANDBOOK_NO_SCHEMA | SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1 | 8 | match | 0.1250 | 0.6250 | 0.1250 | 0.6250 | 0.6250 | 0.4706 | 0.4211 | 1.0000 |
| native_structured/HANDBOOK_STRICT_ACTION | SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1 | 8 | match | 0.1250 | 0.3750 | 0.2500 | 0.3750 | 0.3750 | 0.2353 | 0.2222 | 1.0000 |

## Paired contrasts vs. each run's direct baseline (v1 and v2, CI90, 10,000 replicates)

### cpv2/cross_fitted_policy_vs_cpv2/M0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 104 | 0.3077 | 0.2885 | -0.0192 | 0 | 2 | 102 | [-0.0385, 0.0000] |
| v1_tool | 104 | 0.5865 | 0.5673 | -0.0192 | 0 | 2 | 102 | [-0.0385, 0.0000] |
| v2_exact | 104 | 0.3558 | 0.3365 | -0.0192 | 0 | 2 | 102 | [-0.0385, 0.0000] |
| v2_tool_ordered | 104 | 0.5865 | 0.5673 | -0.0192 | 0 | 2 | 102 | [-0.0385, 0.0000] |
| v2_tool_multiset | 104 | 0.5865 | 0.5673 | -0.0192 | 0 | 2 | 102 | [-0.0385, 0.0000] |

### cpv2/matched_vs_cpv2/M0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 104 | 0.3077 | 0.3846 | +0.0769 | 14 | 6 | 84 | [0.0096, 0.1442] |
| v1_tool | 104 | 0.5865 | 0.7019 | +0.1154 | 19 | 7 | 78 | [0.0385, 0.1923] |
| v2_exact | 104 | 0.3558 | 0.4038 | +0.0481 | 10 | 5 | 89 | [-0.0096, 0.1058] |
| v2_tool_ordered | 104 | 0.5865 | 0.7019 | +0.1154 | 19 | 7 | 78 | [0.0385, 0.1923] |
| v2_tool_multiset | 104 | 0.5865 | 0.7019 | +0.1154 | 19 | 7 | 78 | [0.0385, 0.1923] |

### cpv2/resend_vs_cpv2/M0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 104 | 0.3077 | 0.3750 | +0.0673 | 13 | 6 | 85 | [0.0000, 0.1346] |
| v1_tool | 104 | 0.5865 | 0.6923 | +0.1058 | 18 | 7 | 79 | [0.0288, 0.1827] |
| v2_exact | 104 | 0.3558 | 0.3942 | +0.0385 | 9 | 5 | 90 | [-0.0192, 0.0962] |
| v2_tool_ordered | 104 | 0.5865 | 0.6923 | +0.1058 | 18 | 7 | 79 | [0.0288, 0.1827] |
| v2_tool_multiset | 104 | 0.5865 | 0.6923 | +0.1058 | 18 | 7 | 79 | [0.0288, 0.1827] |

### cpv2/shuffled_vs_cpv2/M0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 104 | 0.3077 | 0.2692 | -0.0385 | 6 | 10 | 88 | [-0.0962, 0.0192] |
| v1_tool | 104 | 0.5865 | 0.4904 | -0.0962 | 8 | 18 | 78 | [-0.1731, -0.0192] |
| v2_exact | 104 | 0.3558 | 0.2885 | -0.0673 | 6 | 13 | 85 | [-0.1346, 0.0000] |
| v2_tool_ordered | 104 | 0.5865 | 0.4808 | -0.1058 | 7 | 18 | 79 | [-0.1827, -0.0288] |
| v2_tool_multiset | 104 | 0.5865 | 0.4904 | -0.0962 | 8 | 18 | 78 | [-0.1731, -0.0192] |

### g3/matched_vs_g3/m0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 40 | 0.2000 | 0.2000 | +0.0000 | 4 | 4 | 32 | [-0.1000, 0.1000] |
| v1_tool | 40 | 0.5250 | 0.6750 | +0.1500 | 8 | 2 | 30 | [0.0250, 0.2750] |
| v2_exact | 40 | 0.2750 | 0.2750 | +0.0000 | 5 | 5 | 30 | [-0.1250, 0.1250] |
| v2_tool_ordered | 40 | 0.5000 | 0.6500 | +0.1500 | 8 | 2 | 30 | [0.0250, 0.2750] |
| v2_tool_multiset | 40 | 0.5250 | 0.6750 | +0.1500 | 8 | 2 | 30 | [0.0250, 0.2750] |

### g3/shuffled_vs_g3/m0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 40 | 0.2000 | 0.1750 | -0.0250 | 5 | 6 | 29 | [-0.1250, 0.0750] |
| v1_tool | 40 | 0.5250 | 0.6000 | +0.0750 | 6 | 3 | 31 | [-0.0250, 0.2000] |
| v2_exact | 40 | 0.2750 | 0.1750 | -0.1000 | 4 | 8 | 28 | [-0.2250, 0.0250] |
| v2_tool_ordered | 40 | 0.5000 | 0.5750 | +0.0750 | 6 | 3 | 31 | [-0.0250, 0.1750] |
| v2_tool_multiset | 40 | 0.5250 | 0.6000 | +0.0750 | 6 | 3 | 31 | [-0.0250, 0.1750] |

### g5/g5_vs_g1_m0_shared/M0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 16 | 0.3750 | 0.1875 | -0.1875 | 1 | 4 | 11 | [-0.3125, -0.0625] |
| v1_tool | 16 | 0.7500 | 0.2500 | -0.5000 | 0 | 8 | 8 | [-0.6250, -0.3750] |
| v2_exact | 16 | 0.5625 | 0.2500 | -0.3125 | 1 | 6 | 9 | [-0.4375, -0.1875] |
| v2_tool_ordered | 16 | 0.7500 | 0.2500 | -0.5000 | 0 | 8 | 8 | [-0.6250, -0.3750] |
| v2_tool_multiset | 16 | 0.7500 | 0.2500 | -0.5000 | 0 | 8 | 8 | [-0.6250, -0.3750] |

### g6/g6_seal_vs_g1_m0_shared/M0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 16 | 0.1875 | 0.0000 | -0.1875 | 0 | 3 | 13 | [-0.2500, -0.1250] |
| v1_tool | 16 | 0.3750 | 0.0000 | -0.3750 | 0 | 6 | 10 | [-0.5000, -0.2500] |
| v2_exact | 16 | 0.2500 | 0.0000 | -0.2500 | 0 | 4 | 12 | [-0.3750, -0.1250] |
| v2_tool_ordered | 16 | 0.3750 | 0.0000 | -0.3750 | 0 | 6 | 10 | [-0.5000, -0.2500] |
| v2_tool_multiset | 16 | 0.3750 | 0.0000 | -0.3750 | 0 | 6 | 10 | [-0.5000, -0.2500] |

### g7/g7_vs_g1_m0_shared/M0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 16 | 0.2500 | 0.1875 | -0.0625 | 0 | 1 | 15 | [-0.1250, 0.0000] |
| v1_tool | 16 | 0.6875 | 0.4375 | -0.2500 | 0 | 4 | 12 | [-0.3750, -0.1250] |
| v2_exact | 16 | 0.3750 | 0.1875 | -0.1875 | 0 | 3 | 13 | [-0.2500, -0.1250] |
| v2_tool_ordered | 16 | 0.6250 | 0.3750 | -0.2500 | 0 | 4 | 12 | [-0.3750, -0.1250] |
| v2_tool_multiset | 16 | 0.6875 | 0.4375 | -0.2500 | 0 | 4 | 12 | [-0.3750, -0.1250] |

### g8c/DECOMPOSED_SELECT_BIND_RESOLVE_vs_g8c/STOP_M0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 12 | 0.3333 | 0.0833 | -0.2500 | 0 | 3 | 9 | [-0.4167, -0.0833] |
| v1_tool | 12 | 0.8333 | 0.7500 | -0.0833 | 1 | 2 | 9 | [-0.2500, 0.0833] |
| v2_exact | 12 | 0.5000 | 0.0833 | -0.4167 | 0 | 5 | 7 | [-0.5833, -0.2500] |
| v2_tool_ordered | 12 | 0.8333 | 0.7500 | -0.0833 | 1 | 2 | 9 | [-0.2500, 0.0833] |
| v2_tool_multiset | 12 | 0.8333 | 0.7500 | -0.0833 | 1 | 2 | 9 | [-0.2500, 0.0833] |

### g8c/EXHAUSTIVE_G7_vs_g8c/STOP_M0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 12 | 0.3333 | 0.0833 | -0.2500 | 0 | 3 | 9 | [-0.4167, -0.0833] |
| v1_tool | 12 | 0.8333 | 0.5833 | -0.2500 | 0 | 3 | 9 | [-0.4167, -0.0833] |
| v2_exact | 12 | 0.5000 | 0.0833 | -0.4167 | 0 | 5 | 7 | [-0.5833, -0.2500] |
| v2_tool_ordered | 12 | 0.8333 | 0.5833 | -0.2500 | 0 | 3 | 9 | [-0.4167, -0.0833] |
| v2_tool_multiset | 12 | 0.8333 | 0.5833 | -0.2500 | 0 | 3 | 9 | [-0.4167, -0.0833] |

### g8c/SUPPORT_ONLY_RESOLVE_vs_g8c/STOP_M0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 12 | 0.3333 | 0.0000 | -0.3333 | 0 | 4 | 8 | [-0.5000, -0.1667] |
| v1_tool | 12 | 0.8333 | 0.0000 | -0.8333 | 0 | 10 | 2 | [-0.9167, -0.7500] |
| v2_exact | 12 | 0.5000 | 0.0000 | -0.5000 | 0 | 6 | 6 | [-0.6667, -0.3333] |
| v2_tool_ordered | 12 | 0.8333 | 0.0000 | -0.8333 | 0 | 10 | 2 | [-0.9167, -0.7500] |
| v2_tool_multiset | 12 | 0.8333 | 0.0000 | -0.8333 | 0 | 10 | 2 | [-0.9167, -0.7500] |

### native_structured/HANDBOOK_STRICT_ACTION_vs_native_structured/HANDBOOK_NO_SCHEMA

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 8 | 0.1250 | 0.1250 | +0.0000 | 1 | 1 | 6 | [0.0000, 0.0000] |
| v1_tool | 8 | 0.6250 | 0.3750 | -0.2500 | 1 | 3 | 4 | [-0.2500, -0.2500] |
| v2_exact | 8 | 0.1250 | 0.2500 | +0.1250 | 2 | 1 | 5 | [0.1250, 0.1250] |
| v2_tool_ordered | 8 | 0.6250 | 0.3750 | -0.2500 | 1 | 3 | 4 | [-0.2500, -0.2500] |
| v2_tool_multiset | 8 | 0.6250 | 0.3750 | -0.2500 | 1 | 3 | 4 | [-0.2500, -0.2500] |

### native_structured/REGISTRY_STRICT_ACTION_vs_native_structured/REGISTRY_NO_SCHEMA

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 8 | 0.0000 | 0.2500 | +0.2500 | 2 | 0 | 6 | [0.2500, 0.2500] |
| v1_tool | 8 | 0.0000 | 0.5000 | +0.5000 | 4 | 0 | 4 | [0.5000, 0.5000] |
| v2_exact | 8 | 0.0000 | 0.3750 | +0.3750 | 3 | 0 | 5 | [0.3750, 0.3750] |
| v2_tool_ordered | 8 | 0.0000 | 0.5000 | +0.5000 | 4 | 0 | 4 | [0.5000, 0.5000] |
| v2_tool_multiset | 8 | 0.0000 | 0.5000 | +0.5000 | 4 | 0 | 4 | [0.5000, 0.5000] |

### selectfill104/JOINT_DRAFT_REVISE_vs_selectfill104/DIRECT_M0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 104 | 0.1731 | 0.2500 | +0.0769 | 13 | 5 | 86 | [0.0096, 0.1346] |
| v1_tool | 104 | 0.4038 | 0.6346 | +0.2308 | 30 | 6 | 68 | [0.1538, 0.3173] |
| v2_exact | 104 | 0.2404 | 0.3269 | +0.0865 | 16 | 7 | 81 | [0.0192, 0.1635] |
| v2_tool_ordered | 104 | 0.3942 | 0.6154 | +0.2212 | 29 | 6 | 69 | [0.1442, 0.3077] |
| v2_tool_multiset | 104 | 0.4038 | 0.6346 | +0.2308 | 30 | 6 | 68 | [0.1442, 0.3173] |

### selectfill104/JOINT_ONE_CALL_vs_selectfill104/DIRECT_M0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 104 | 0.1731 | 0.2404 | +0.0673 | 12 | 5 | 87 | [0.0000, 0.1250] |
| v1_tool | 104 | 0.4038 | 0.6250 | +0.2212 | 29 | 6 | 69 | [0.1442, 0.3077] |
| v2_exact | 104 | 0.2404 | 0.3173 | +0.0769 | 15 | 7 | 82 | [0.0096, 0.1538] |
| v2_tool_ordered | 104 | 0.3942 | 0.6058 | +0.2115 | 28 | 6 | 70 | [0.1346, 0.2981] |
| v2_tool_multiset | 104 | 0.4038 | 0.6250 | +0.2212 | 29 | 6 | 69 | [0.1346, 0.3077] |

### selectfill104/SELECT_THEN_FILL_vs_selectfill104/DIRECT_M0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 104 | 0.1731 | 0.2500 | +0.0769 | 13 | 5 | 86 | [0.0096, 0.1346] |
| v1_tool | 104 | 0.4038 | 0.5962 | +0.1923 | 26 | 6 | 72 | [0.1154, 0.2692] |
| v2_exact | 104 | 0.2404 | 0.3462 | +0.1058 | 17 | 6 | 81 | [0.0385, 0.1827] |
| v2_tool_ordered | 104 | 0.3942 | 0.5865 | +0.1923 | 26 | 6 | 72 | [0.1154, 0.2692] |
| v2_tool_multiset | 104 | 0.4038 | 0.5962 | +0.1923 | 26 | 6 | 72 | [0.1154, 0.2692] |

### self_consistency/REOBSERVE_DIRECT_vs_g1_m0_shared/M0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 104 | 0.2788 | 0.2212 | -0.0577 | 0 | 6 | 98 | [-0.0962, -0.0192] |
| v1_tool | 104 | 0.5962 | 0.5288 | -0.0673 | 3 | 10 | 91 | [-0.1250, -0.0096] |
| v2_exact | 104 | 0.3846 | 0.2981 | -0.0865 | 0 | 9 | 95 | [-0.1346, -0.0481] |
| v2_tool_ordered | 104 | 0.5769 | 0.5192 | -0.0577 | 3 | 9 | 92 | [-0.1154, -0.0096] |
| v2_tool_multiset | 104 | 0.5962 | 0.5288 | -0.0673 | 3 | 10 | 91 | [-0.1250, -0.0096] |

### self_consistency/SUPPLY_UNION_STRIPPED_vs_g1_m0_shared/M0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 104 | 0.2788 | 0.2212 | -0.0577 | 4 | 10 | 90 | [-0.1154, 0.0000] |
| v1_tool | 104 | 0.5962 | 0.5769 | -0.0192 | 4 | 6 | 94 | [-0.0673, 0.0288] |
| v2_exact | 104 | 0.3846 | 0.2500 | -0.1346 | 2 | 16 | 86 | [-0.1923, -0.0769] |
| v2_tool_ordered | 104 | 0.5769 | 0.5577 | -0.0192 | 4 | 6 | 94 | [-0.0673, 0.0288] |
| v2_tool_multiset | 104 | 0.5962 | 0.5769 | -0.0192 | 4 | 6 | 94 | [-0.0673, 0.0288] |

### self_transcript_cascade/CROSSFIT_POLICY_vs_g1_m0_shared/M0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 104 | 0.2788 | 0.2788 | +0.0000 | 0 | 0 | 104 | [0.0000, 0.0000] |
| v1_tool | 104 | 0.5962 | 0.5962 | +0.0000 | 0 | 0 | 104 | [0.0000, 0.0000] |
| v2_exact | 104 | 0.3846 | 0.3846 | +0.0000 | 0 | 0 | 104 | [0.0000, 0.0000] |
| v2_tool_ordered | 104 | 0.5769 | 0.5769 | +0.0000 | 0 | 0 | 104 | [0.0000, 0.0000] |
| v2_tool_multiset | 104 | 0.5962 | 0.5962 | +0.0000 | 0 | 0 | 104 | [0.0000, 0.0000] |

### self_transcript_cascade/MATCHED_RESEND_COMPOSITE_vs_g1_m0_shared/M0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 104 | 0.2788 | 0.0000 | -0.2788 | 0 | 29 | 75 | [-0.3365, -0.2212] |
| v1_tool | 104 | 0.5962 | 0.0000 | -0.5962 | 0 | 62 | 42 | [-0.6731, -0.5192] |
| v2_exact | 104 | 0.3846 | 0.0000 | -0.3846 | 0 | 40 | 64 | [-0.4519, -0.3173] |
| v2_tool_ordered | 104 | 0.5769 | 0.0000 | -0.5769 | 0 | 60 | 44 | [-0.6442, -0.5096] |
| v2_tool_multiset | 104 | 0.5962 | 0.0000 | -0.5962 | 0 | 62 | 42 | [-0.6731, -0.5192] |

### self_transcript_cascade/USE_MATCHED_vs_g1_m0_shared/M0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 104 | 0.2788 | 0.0000 | -0.2788 | 0 | 29 | 75 | [-0.3365, -0.2212] |
| v1_tool | 104 | 0.5962 | 0.0000 | -0.5962 | 0 | 62 | 42 | [-0.6731, -0.5192] |
| v2_exact | 104 | 0.3846 | 0.0000 | -0.3846 | 0 | 40 | 64 | [-0.4519, -0.3173] |
| v2_tool_ordered | 104 | 0.5769 | 0.0000 | -0.5769 | 0 | 60 | 44 | [-0.6442, -0.5096] |
| v2_tool_multiset | 104 | 0.5962 | 0.0000 | -0.5962 | 0 | 62 | 42 | [-0.6731, -0.5192] |

### self_transcript_cascade/USE_SHUFFLED_EVIDENCE_vs_g1_m0_shared/M0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 104 | 0.2788 | 0.0000 | -0.2788 | 0 | 29 | 75 | [-0.3365, -0.2212] |
| v1_tool | 104 | 0.5962 | 0.0000 | -0.5962 | 0 | 62 | 42 | [-0.6731, -0.5192] |
| v2_exact | 104 | 0.3846 | 0.0000 | -0.3846 | 0 | 40 | 64 | [-0.4519, -0.3173] |
| v2_tool_ordered | 104 | 0.5769 | 0.0000 | -0.5769 | 0 | 60 | 44 | [-0.6442, -0.5096] |
| v2_tool_multiset | 104 | 0.5962 | 0.0000 | -0.5962 | 0 | 62 | 42 | [-0.6731, -0.5192] |

### semantic104/model_query_top16_use_vs_semantic104/direct_m0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 104 | 0.2404 | 0.2308 | -0.0096 | 6 | 7 | 91 | [-0.0673, 0.0481] |
| v1_tool | 104 | 0.5096 | 0.5769 | +0.0673 | 15 | 8 | 81 | [0.0000, 0.1346] |
| v2_exact | 104 | 0.2981 | 0.3269 | +0.0288 | 10 | 7 | 87 | [-0.0385, 0.0865] |
| v2_tool_ordered | 104 | 0.5000 | 0.5577 | +0.0577 | 14 | 8 | 82 | [-0.0096, 0.1250] |
| v2_tool_multiset | 104 | 0.5096 | 0.5769 | +0.0673 | 15 | 8 | 81 | [0.0000, 0.1346] |

### semantic104/rrf_fused_top16_use_vs_semantic104/direct_m0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 104 | 0.2404 | 0.2404 | +0.0000 | 8 | 8 | 88 | [-0.0577, 0.0577] |
| v1_tool | 104 | 0.5096 | 0.5769 | +0.0673 | 16 | 9 | 79 | [-0.0096, 0.1442] |
| v2_exact | 104 | 0.2981 | 0.3558 | +0.0577 | 14 | 8 | 82 | [-0.0096, 0.1250] |
| v2_tool_ordered | 104 | 0.5000 | 0.5577 | +0.0577 | 15 | 9 | 80 | [-0.0096, 0.1346] |
| v2_tool_multiset | 104 | 0.5096 | 0.5769 | +0.0673 | 16 | 9 | 79 | [-0.0096, 0.1442] |

### semantic104/same_stratum_shuffled_fused_use_vs_semantic104/direct_m0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 104 | 0.2404 | 0.0385 | -0.2019 | 3 | 24 | 77 | [-0.2692, -0.1346] |
| v1_tool | 104 | 0.5096 | 0.0865 | -0.4231 | 4 | 48 | 52 | [-0.5000, -0.3365] |
| v2_exact | 104 | 0.2981 | 0.0385 | -0.2596 | 3 | 30 | 71 | [-0.3365, -0.1827] |
| v2_tool_ordered | 104 | 0.5000 | 0.0865 | -0.4135 | 4 | 47 | 53 | [-0.4904, -0.3269] |
| v2_tool_multiset | 104 | 0.5096 | 0.0865 | -0.4231 | 4 | 48 | 52 | [-0.5000, -0.3365] |

### semantic104/transcript_top16_use_vs_semantic104/direct_m0

| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|---|---|
| v1_exact | 104 | 0.2404 | 0.2596 | +0.0192 | 10 | 8 | 86 | [-0.0385, 0.0769] |
| v1_tool | 104 | 0.5096 | 0.5962 | +0.0865 | 18 | 9 | 77 | [0.0096, 0.1635] |
| v2_exact | 104 | 0.2981 | 0.3750 | +0.0769 | 16 | 8 | 80 | [0.0000, 0.1538] |
| v2_tool_ordered | 104 | 0.5000 | 0.5769 | +0.0769 | 17 | 9 | 78 | [0.0000, 0.1538] |
| v2_tool_multiset | 104 | 0.5096 | 0.5962 | +0.0865 | 18 | 9 | 77 | [0.0096, 0.1635] |

## Residuals (skipped arms)

- none

- (not attempted) SAEA-A2T-EXECUTABLE-GROUND-QUALIFICATION-104-V1: has a findable outputs.jsonl per arm (m0-registry-direct, g1-full-executable-ground) but no verdict doc is listed in this task's ownership scope and its sealed aggregate could not be matched with certainty in the time budget available; not attempted.
- (not attempted) SAEA-A2T-CONSTRUCTION-SEMANTIC-GROUND-DIAGNOSTIC-104-V1: result-summary.json reports g1/g2 counts (19, 4) whose n and role are not self-evident from that file alone (not simply /104 against the A2T-G1-104 baseline), and no verdict doc is listed in this task's ownership scope; not attempted.
