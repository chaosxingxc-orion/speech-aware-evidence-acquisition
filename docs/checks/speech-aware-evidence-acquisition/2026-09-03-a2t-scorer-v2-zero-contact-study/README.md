# Slice S1 -- zero-contact re-scoring study of sealed Audio2Tool outputs (2026-09-03)

Model-free, read-only offline re-scoring of three already-sealed Audio2Tool discovery-split
outputs sets, run against the UNCHANGED v1 scorer (`reproduction.toolcall_scoring` --
`parse_tool_calls_text`/`score_item`/`aggregate`, `a2t-scorer-v1`) and the unchanged v1 gold
parser (`reproduction.toolcall_gold`, `a2t-gold-v1`, reached only through
`data.audio2tool.load_expected_calls`). Zero model, GPU, embedding, or network contact: every
number below comes from files that were already written by prior, separately-registered runs.

Suite: `src/speech_aware_evidence_acquisition/analysis/a2t_scorer_v2_study.py` (`main()` CLI).
Deliverables: `summary.json` (machine-readable, this README's tables verbatim plus the identity
check, taxonomy, rule table, and per-row array), `per_row.jsonl` (1,336 rows: 400 A0 + 5x104
semantic-AgentLoop + 4x104 select-fill-AgentLoop), and this README.

## Why

The paper (arXiv:2604.22821, Table 3) reports Tier 1 tool accuracy 92.4 with EM 92.4 for the same
frozen core (Tier 1 is argument-free, so EM equals tool accuracy there). This repo's frozen A0
read (n=400) scores Tier 1 tool acc 58.0 / EM 12.0 -- a much larger EM-vs-tool-acc gap than the
paper shows for the same tier. The paper defines Tool Accuracy as an ORDERED sequence match for
multi-call rows and EM as exact match on all arguments after "deterministic normalization"; the
repo's v1 scorer is order-insensitive (multiset) and has no default/omission normalization. This
study measures how much of the gap is scorer semantics versus genuine model error, per tier, before
any scorer-v2 decision is made.

## Inputs read (all sealed, read-only)

| source | rows | outputs file(s) | text field |
|---|---|---|---|
| A0 direct baseline | 400 (8 tiers x 50) | `SAEA-BASE-a2t-a0-400/attempt-20260818T055500Z-res315/outputs.jsonl` | `response_text` |
| semantic-AgentLoop-104 | 5 arms x 104 | `SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1/.../zero-contact-recovery-v2/<arm>/SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1.outputs.jsonl` | `text` |
| select-fill-AgentLoop-104 | 4 arms x 104 | `SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5/.../{recovered-direct-m0,zero-contact-seal-recovery-v1/*}/*.outputs.jsonl` | `text` |

All 10 arms (1 + 5 + 4) were located and scored; **zero arms were skipped** (`residuals` is empty
in `summary.json`). Split identity hashes: A0 `e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c`;
semantic-104 `84c56416a36d5eb1737fa49f6b255b0a59585df8c8ff1754240a87022983eab0`; select-fill-104
`bcbad5405aa8522ff53a91d624c54a909e01f8a31612b5165844b8e2cbca6eb3`.


Row counts per source in the taxonomy tables below are v1 `exact_match == 0` rows only (the
category `EXACT_MATCH` in `per_row.jsonl` covers everything else); `-` means zero. A0 is 8 tiers x
50 rows = 400; each September arm is 8 tiers x 13 rows = 104.

### Identity check (Step 1)

| file | rows | v1 overall tool_acc | v1 overall EM | matches sealed target |
|---|---|---|---|---|
| A0 direct baseline, `outputs.jsonl` | 400 | 0.5425 | 0.2425 | YES |
| semantic104/direct_m0, `outputs.jsonl` | 104 | 0.5096 | 0.2404 | YES |
| semantic104/transcript_top16_use, `outputs.jsonl` | 104 | 0.5962 | 0.2596 | YES |
| semantic104/model_query_top16_use, `outputs.jsonl` | 104 | 0.5769 | 0.2308 | YES |
| semantic104/rrf_fused_top16_use, `outputs.jsonl` | 104 | 0.5769 | 0.2404 | YES |
| semantic104/same_stratum_shuffled_fused_use, `outputs.jsonl` | 104 | 0.0865 | 0.0385 | YES |
| selectfill104/DIRECT_M0, `outputs.jsonl` | 104 | 0.4038 | 0.1731 | YES |
| selectfill104/JOINT_ONE_CALL, `outputs.jsonl` | 104 | 0.6250 | 0.2404 | YES |
| selectfill104/JOINT_DRAFT_REVISE, `outputs.jsonl` | 104 | 0.6346 | 0.2500 | YES |
| selectfill104/SELECT_THEN_FILL, `outputs.jsonl` | 104 | 0.5962 | 0.2500 | YES |

### Step 2 -- A0 failure taxonomy (tier x category, v1 exact_match==0 rows only)

| tier | PARSE_FAIL | EMPTY | TOOL_SET_WRONG | TOOL_ORDER_ONLY | EXTRA_KEYS_DEFAULT_ONLY | EXTRA_KEYS_NONDEFAULT | MISSING_KEYS_ONLY | CASE_OR_TYPE_ONLY | VALUE_WRONG | MIXED | total failures |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tier1_direct | - | 1 | 20 | - | 14 | 9 | - | - | - | - | 44 |
| tier2_parametric | - | - | 14 | - | 1 | - | 1 | - | 13 | 2 | 31 |
| tier3_multi_intent | 2 | - | 17 | 1 | 5 | 21 | - | - | - | 2 | 48 |
| tier4_implicit | 1 | 10 | 24 | - | - | - | - | - | 2 | 1 | 38 |
| tier5_needle | 16 | - | 7 | - | 4 | - | - | - | 6 | 2 | 35 |
| tier6_correction | 2 | 2 | 14 | - | - | - | - | - | 10 | 2 | 30 |
| tier7_multiturn | - | 4 | 16 | - | - | - | 1 | - | 6 | 1 | 28 |
| tier8_intent_blending | 3 | - | 30 | 2 | 2 | 9 | - | - | 1 | 2 | 49 |
| **overall** | 24 | 17 | 142 | 3 | 26 | 39 | 2 | - | 38 | 12 | **303** |

### Step 2 -- semantic104 failure taxonomy (arm totals summed over 8 tiers, v1 exact_match==0 rows only)

| arm | PARSE_FAIL | EMPTY | TOOL_SET_WRONG | TOOL_ORDER_ONLY | EXTRA_KEYS_DEFAULT_ONLY | EXTRA_KEYS_NONDEFAULT | MISSING_KEYS_ONLY | CASE_OR_TYPE_ONLY | VALUE_WRONG | MIXED | total failures |
|---|---|---|---|---|---|---|---|---|---|---|---|
| direct_m0 | 11 | 6 | 34 | 1 | 5 | 7 | 1 | - | 10 | 4 | 79 |
| transcript_top16_use | - | 7 | 35 | 2 | 8 | 7 | 4 | 2 | 8 | 4 | 77 |
| model_query_top16_use | - | 9 | 35 | 2 | 7 | 7 | 3 | 2 | 11 | 4 | 80 |
| rrf_fused_top16_use | 1 | 9 | 34 | 2 | 8 | 6 | 4 | 2 | 10 | 3 | 79 |
| same_stratum_shuffled_fused_use | - | 75 | 20 | - | - | 1 | - | - | 1 | 3 | 100 |

### Step 2 -- selectfill104 failure taxonomy (arm totals summed over 8 tiers, v1 exact_match==0 rows only)

| arm | PARSE_FAIL | EMPTY | TOOL_SET_WRONG | TOOL_ORDER_ONLY | EXTRA_KEYS_DEFAULT_ONLY | EXTRA_KEYS_NONDEFAULT | MISSING_KEYS_ONLY | CASE_OR_TYPE_ONLY | VALUE_WRONG | MIXED | total failures |
|---|---|---|---|---|---|---|---|---|---|---|---|
| DIRECT_M0 | 15 | 10 | 37 | 1 | 7 | 3 | 2 | - | 10 | 1 | 86 |
| JOINT_ONE_CALL | - | - | 39 | 2 | 8 | 8 | 6 | - | 13 | 3 | 79 |
| JOINT_DRAFT_REVISE | - | - | 38 | 2 | 8 | 8 | 6 | - | 13 | 3 | 78 |
| SELECT_THEN_FILL | - | - | 42 | 1 | 10 | 6 | 3 | - | 12 | 4 | 78 |

### Step 3 -- A0 candidate-rule table (tool_acc / EM, n=50 per tier, n=400 overall)

| tier | paper tool_acc/EM | V1 | V2a | V2b | V2c | V2d | V2e |
|---|---|---|---|---|---|---|---|
| tier1_direct | 92.4/92.4 | 58.00/12.00 | 58.00/12.00 | 58.00/40.00 | 58.00/58.00 | 58.00/40.00 | 58.00/40.00 |
| tier2_parametric | 84.6/15.6 | 72.00/38.00 | 72.00/38.00 | 72.00/40.00 | 72.00/40.00 | 72.00/44.00 | 72.00/44.00 |
| tier3_multi_intent | 74.7/28.6 | 62.00/4.00 | 58.00/4.00 | 62.00/14.00 | 62.00/56.00 | 62.00/14.00 | 58.00/14.00 |
| tier4_implicit | 33.4/11.3 | 30.00/24.00 | 30.00/24.00 | 30.00/24.00 | 30.00/24.00 | 30.00/24.00 | 30.00/24.00 |
| tier5_needle | 90.6/36.0 | 54.00/30.00 | 54.00/30.00 | 54.00/38.00 | 54.00/38.00 | 54.00/38.00 | 54.00/38.00 |
| tier6_correction | 81.5/24.8 | 64.00/40.00 | 64.00/40.00 | 64.00/40.00 | 64.00/40.00 | 64.00/40.00 | 64.00/40.00 |
| tier7_multiturn | 54.6/16.3 | 60.00/44.00 | 60.00/44.00 | 60.00/44.00 | 60.00/44.00 | 60.00/44.00 | 60.00/44.00 |
| tier8_intent_blending | 41.7/12.4 | 34.00/2.00 | 28.00/2.00 | 34.00/6.00 | 34.00/26.00 | 34.00/6.00 | 28.00/6.00 |
| overall | -- | 54.25/24.25 | 53.00/24.25 | 54.25/30.75 | 54.25/40.75 | 54.25/31.25 | 53.00/31.25 |

### Step 3 -- semantic104 candidate-rule table, OVERALL (tool_acc / EM, n=104 per arm)

| arm | V1 | V2a | V2b | V2c | V2d | V2e |
|---|---|---|---|---|---|---|
| direct_m0 | 50.96/24.04 | 50.00/24.04 | 50.96/29.81 | 50.96/36.54 | 50.96/29.81 | 50.00/29.81 |
| transcript_top16_use | 59.62/25.96 | 57.69/25.96 | 59.62/35.58 | 59.62/42.31 | 59.62/37.50 | 57.69/37.50 |
| model_query_top16_use | 57.69/23.08 | 55.77/23.08 | 57.69/30.77 | 57.69/38.46 | 57.69/32.69 | 55.77/32.69 |
| rrf_fused_top16_use | 57.69/24.04 | 55.77/24.04 | 57.69/33.65 | 57.69/39.42 | 57.69/35.58 | 55.77/35.58 |
| same_stratum_shuffled_fused_use | 8.65/3.85 | 8.65/3.85 | 8.65/3.85 | 8.65/4.81 | 8.65/3.85 | 8.65/3.85 |

<details><summary>semantic104 per-tier rule table (n=13 per tier)</summary>

**direct_m0**

| tier | V1 | V2a | V2b | V2c | V2d | V2e |
|---|---|---|---|---|---|---|
| tier1_direct | 53.8/15.4 | 53.8/15.4 | 53.8/38.5 | 53.8/53.8 | 53.8/38.5 | 53.8/38.5 |
| tier2_parametric | 76.9/46.2 | 76.9/46.2 | 76.9/46.2 | 76.9/46.2 | 76.9/46.2 | 76.9/46.2 |
| tier3_multi_intent | 46.2/0.0 | 38.5/0.0 | 46.2/15.4 | 46.2/30.8 | 46.2/15.4 | 38.5/15.4 |
| tier4_implicit | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 |
| tier5_needle | 61.5/38.5 | 61.5/38.5 | 61.5/46.2 | 61.5/46.2 | 61.5/46.2 | 61.5/46.2 |
| tier6_correction | 76.9/46.2 | 76.9/46.2 | 76.9/46.2 | 76.9/46.2 | 76.9/46.2 | 76.9/46.2 |
| tier7_multiturn | 46.2/38.5 | 46.2/38.5 | 46.2/38.5 | 46.2/38.5 | 46.2/38.5 | 46.2/38.5 |
| tier8_intent_blending | 46.2/7.7 | 46.2/7.7 | 46.2/7.7 | 46.2/30.8 | 46.2/7.7 | 46.2/7.7 |

**transcript_top16_use**

| tier | V1 | V2a | V2b | V2c | V2d | V2e |
|---|---|---|---|---|---|---|
| tier1_direct | 61.5/7.7 | 61.5/7.7 | 61.5/53.8 | 61.5/61.5 | 61.5/53.8 | 61.5/53.8 |
| tier2_parametric | 76.9/46.2 | 76.9/46.2 | 76.9/46.2 | 76.9/46.2 | 76.9/46.2 | 76.9/46.2 |
| tier3_multi_intent | 53.8/0.0 | 38.5/0.0 | 53.8/23.1 | 53.8/53.8 | 53.8/23.1 | 38.5/23.1 |
| tier4_implicit | 30.8/23.1 | 30.8/23.1 | 30.8/30.8 | 30.8/30.8 | 30.8/30.8 | 30.8/30.8 |
| tier5_needle | 84.6/69.2 | 84.6/69.2 | 84.6/69.2 | 84.6/69.2 | 84.6/69.2 | 84.6/69.2 |
| tier6_correction | 84.6/30.8 | 84.6/30.8 | 84.6/30.8 | 84.6/30.8 | 84.6/38.5 | 84.6/38.5 |
| tier7_multiturn | 53.8/30.8 | 53.8/30.8 | 53.8/30.8 | 53.8/30.8 | 53.8/38.5 | 53.8/38.5 |
| tier8_intent_blending | 30.8/0.0 | 30.8/0.0 | 30.8/0.0 | 30.8/15.4 | 30.8/0.0 | 30.8/0.0 |

**model_query_top16_use**

| tier | V1 | V2a | V2b | V2c | V2d | V2e |
|---|---|---|---|---|---|---|
| tier1_direct | 76.9/15.4 | 76.9/15.4 | 76.9/61.5 | 76.9/76.9 | 76.9/61.5 | 76.9/61.5 |
| tier2_parametric | 69.2/38.5 | 69.2/38.5 | 69.2/38.5 | 69.2/38.5 | 69.2/38.5 | 69.2/38.5 |
| tier3_multi_intent | 53.8/0.0 | 38.5/0.0 | 53.8/15.4 | 53.8/53.8 | 53.8/15.4 | 38.5/15.4 |
| tier4_implicit | 15.4/7.7 | 15.4/7.7 | 15.4/7.7 | 15.4/7.7 | 15.4/7.7 | 15.4/7.7 |
| tier5_needle | 84.6/61.5 | 84.6/61.5 | 84.6/61.5 | 84.6/61.5 | 84.6/61.5 | 84.6/61.5 |
| tier6_correction | 84.6/30.8 | 84.6/30.8 | 84.6/30.8 | 84.6/30.8 | 84.6/38.5 | 84.6/38.5 |
| tier7_multiturn | 53.8/30.8 | 53.8/30.8 | 53.8/30.8 | 53.8/30.8 | 53.8/38.5 | 53.8/38.5 |
| tier8_intent_blending | 23.1/0.0 | 23.1/0.0 | 23.1/0.0 | 23.1/7.7 | 23.1/0.0 | 23.1/0.0 |

**rrf_fused_top16_use**

| tier | V1 | V2a | V2b | V2c | V2d | V2e |
|---|---|---|---|---|---|---|
| tier1_direct | 61.5/7.7 | 61.5/7.7 | 61.5/53.8 | 61.5/61.5 | 61.5/53.8 | 61.5/53.8 |
| tier2_parametric | 76.9/46.2 | 76.9/46.2 | 76.9/46.2 | 76.9/46.2 | 76.9/46.2 | 76.9/46.2 |
| tier3_multi_intent | 53.8/0.0 | 38.5/0.0 | 53.8/23.1 | 53.8/53.8 | 53.8/23.1 | 38.5/23.1 |
| tier4_implicit | 23.1/7.7 | 23.1/7.7 | 23.1/15.4 | 23.1/15.4 | 23.1/15.4 | 23.1/15.4 |
| tier5_needle | 84.6/69.2 | 84.6/69.2 | 84.6/69.2 | 84.6/69.2 | 84.6/69.2 | 84.6/69.2 |
| tier6_correction | 84.6/30.8 | 84.6/30.8 | 84.6/30.8 | 84.6/30.8 | 84.6/38.5 | 84.6/38.5 |
| tier7_multiturn | 53.8/30.8 | 53.8/30.8 | 53.8/30.8 | 53.8/30.8 | 53.8/38.5 | 53.8/38.5 |
| tier8_intent_blending | 23.1/0.0 | 23.1/0.0 | 23.1/0.0 | 23.1/7.7 | 23.1/0.0 | 23.1/0.0 |

**same_stratum_shuffled_fused_use**

| tier | V1 | V2a | V2b | V2c | V2d | V2e |
|---|---|---|---|---|---|---|
| tier1_direct | 7.7/7.7 | 7.7/7.7 | 7.7/7.7 | 7.7/7.7 | 7.7/7.7 | 7.7/7.7 |
| tier2_parametric | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 |
| tier3_multi_intent | 15.4/0.0 | 15.4/0.0 | 15.4/0.0 | 15.4/7.7 | 15.4/0.0 | 15.4/0.0 |
| tier4_implicit | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 |
| tier5_needle | 7.7/0.0 | 7.7/0.0 | 7.7/0.0 | 7.7/0.0 | 7.7/0.0 | 7.7/0.0 |
| tier6_correction | 7.7/0.0 | 7.7/0.0 | 7.7/0.0 | 7.7/0.0 | 7.7/0.0 | 7.7/0.0 |
| tier7_multiturn | 30.8/23.1 | 30.8/23.1 | 30.8/23.1 | 30.8/23.1 | 30.8/23.1 | 30.8/23.1 |
| tier8_intent_blending | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 |

</details>

### Step 3 -- selectfill104 candidate-rule table, OVERALL (tool_acc / EM, n=104 per arm)

| arm | V1 | V2a | V2b | V2c | V2d | V2e |
|---|---|---|---|---|---|---|
| DIRECT_M0 | 40.38/17.31 | 39.42/17.31 | 40.38/24.04 | 40.38/27.88 | 40.38/24.04 | 39.42/24.04 |
| JOINT_ONE_CALL | 62.50/24.04 | 60.58/24.04 | 62.50/31.73 | 62.50/41.35 | 62.50/31.73 | 60.58/31.73 |
| JOINT_DRAFT_REVISE | 63.46/25.00 | 61.54/25.00 | 63.46/32.69 | 63.46/42.31 | 63.46/32.69 | 61.54/32.69 |
| SELECT_THEN_FILL | 59.62/25.00 | 58.65/25.00 | 59.62/34.62 | 59.62/41.35 | 59.62/34.62 | 58.65/34.62 |

<details><summary>selectfill104 per-tier rule table (n=13 per tier)</summary>

**DIRECT_M0**

| tier | V1 | V2a | V2b | V2c | V2d | V2e |
|---|---|---|---|---|---|---|
| tier1_direct | 53.8/15.4 | 53.8/15.4 | 53.8/46.2 | 53.8/53.8 | 53.8/46.2 | 53.8/46.2 |
| tier2_parametric | 61.5/30.8 | 61.5/30.8 | 61.5/30.8 | 61.5/30.8 | 61.5/30.8 | 61.5/30.8 |
| tier3_multi_intent | 30.8/0.0 | 23.1/0.0 | 30.8/7.7 | 30.8/23.1 | 30.8/7.7 | 23.1/7.7 |
| tier4_implicit | 7.7/0.0 | 7.7/0.0 | 7.7/0.0 | 7.7/0.0 | 7.7/0.0 | 7.7/0.0 |
| tier5_needle | 53.8/38.5 | 53.8/38.5 | 53.8/46.2 | 53.8/46.2 | 53.8/46.2 | 53.8/46.2 |
| tier6_correction | 38.5/23.1 | 38.5/23.1 | 38.5/23.1 | 38.5/23.1 | 38.5/23.1 | 38.5/23.1 |
| tier7_multiturn | 61.5/30.8 | 61.5/30.8 | 61.5/30.8 | 61.5/30.8 | 61.5/30.8 | 61.5/30.8 |
| tier8_intent_blending | 15.4/0.0 | 15.4/0.0 | 15.4/7.7 | 15.4/15.4 | 15.4/7.7 | 15.4/7.7 |

**JOINT_ONE_CALL**

| tier | V1 | V2a | V2b | V2c | V2d | V2e |
|---|---|---|---|---|---|---|
| tier1_direct | 69.2/7.7 | 69.2/7.7 | 69.2/53.8 | 69.2/69.2 | 69.2/53.8 | 69.2/53.8 |
| tier2_parametric | 84.6/30.8 | 84.6/30.8 | 84.6/30.8 | 84.6/30.8 | 84.6/30.8 | 84.6/30.8 |
| tier3_multi_intent | 69.2/0.0 | 61.5/0.0 | 69.2/7.7 | 69.2/46.2 | 69.2/7.7 | 61.5/7.7 |
| tier4_implicit | 38.5/15.4 | 38.5/15.4 | 38.5/23.1 | 38.5/23.1 | 38.5/23.1 | 38.5/23.1 |
| tier5_needle | 84.6/69.2 | 84.6/69.2 | 84.6/69.2 | 84.6/76.9 | 84.6/69.2 | 84.6/69.2 |
| tier6_correction | 76.9/38.5 | 76.9/38.5 | 76.9/38.5 | 76.9/38.5 | 76.9/38.5 | 76.9/38.5 |
| tier7_multiturn | 61.5/30.8 | 61.5/30.8 | 61.5/30.8 | 61.5/30.8 | 61.5/30.8 | 61.5/30.8 |
| tier8_intent_blending | 15.4/0.0 | 7.7/0.0 | 15.4/0.0 | 15.4/15.4 | 15.4/0.0 | 7.7/0.0 |

**JOINT_DRAFT_REVISE**

| tier | V1 | V2a | V2b | V2c | V2d | V2e |
|---|---|---|---|---|---|---|
| tier1_direct | 69.2/7.7 | 69.2/7.7 | 69.2/53.8 | 69.2/69.2 | 69.2/53.8 | 69.2/53.8 |
| tier2_parametric | 84.6/30.8 | 84.6/30.8 | 84.6/30.8 | 84.6/30.8 | 84.6/30.8 | 84.6/30.8 |
| tier3_multi_intent | 69.2/0.0 | 61.5/0.0 | 69.2/7.7 | 69.2/46.2 | 69.2/7.7 | 61.5/7.7 |
| tier4_implicit | 38.5/15.4 | 38.5/15.4 | 38.5/23.1 | 38.5/23.1 | 38.5/23.1 | 38.5/23.1 |
| tier5_needle | 84.6/69.2 | 84.6/69.2 | 84.6/69.2 | 84.6/76.9 | 84.6/69.2 | 84.6/69.2 |
| tier6_correction | 84.6/46.2 | 84.6/46.2 | 84.6/46.2 | 84.6/46.2 | 84.6/46.2 | 84.6/46.2 |
| tier7_multiturn | 61.5/30.8 | 61.5/30.8 | 61.5/30.8 | 61.5/30.8 | 61.5/30.8 | 61.5/30.8 |
| tier8_intent_blending | 15.4/0.0 | 7.7/0.0 | 15.4/0.0 | 15.4/15.4 | 15.4/0.0 | 7.7/0.0 |

**SELECT_THEN_FILL**

| tier | V1 | V2a | V2b | V2c | V2d | V2e |
|---|---|---|---|---|---|---|
| tier1_direct | 69.2/7.7 | 69.2/7.7 | 69.2/61.5 | 69.2/69.2 | 69.2/61.5 | 69.2/61.5 |
| tier2_parametric | 84.6/38.5 | 84.6/38.5 | 84.6/38.5 | 84.6/38.5 | 84.6/38.5 | 84.6/38.5 |
| tier3_multi_intent | 69.2/0.0 | 61.5/0.0 | 69.2/15.4 | 69.2/46.2 | 69.2/15.4 | 61.5/15.4 |
| tier4_implicit | 23.1/15.4 | 23.1/15.4 | 23.1/15.4 | 23.1/15.4 | 23.1/15.4 | 23.1/15.4 |
| tier5_needle | 76.9/69.2 | 76.9/69.2 | 76.9/76.9 | 76.9/76.9 | 76.9/76.9 | 76.9/76.9 |
| tier6_correction | 76.9/38.5 | 76.9/38.5 | 76.9/38.5 | 76.9/38.5 | 76.9/38.5 | 76.9/38.5 |
| tier7_multiturn | 61.5/30.8 | 61.5/30.8 | 61.5/30.8 | 61.5/30.8 | 61.5/30.8 | 61.5/30.8 |
| tier8_intent_blending | 15.4/0.0 | 15.4/0.0 | 15.4/0.0 | 15.4/15.4 | 15.4/0.0 | 15.4/0.0 |

</details>

### September paired-conclusion check -- semantic104 (baseline = direct_m0)

| treatment arm | rule | n | saves | harms | ties | net (saves-harms) |
|---|---|---|---|---|---|---|
| model_query_top16_use | V1 | 104 | 6 | 7 | 91 | -1 |
| model_query_top16_use | V2e | 104 | 10 | 7 | 87 | +3 |
| rrf_fused_top16_use | V1 | 104 | 8 | 8 | 88 | +0 |
| rrf_fused_top16_use | V2e | 104 | 14 | 8 | 82 | +6 |
| same_stratum_shuffled_fused_use | V1 | 104 | 3 | 24 | 77 | -21 |
| same_stratum_shuffled_fused_use | V2e | 104 | 3 | 30 | 71 | -27 |
| transcript_top16_use | V1 | 104 | 10 | 8 | 86 | +2 |
| transcript_top16_use | V2e | 104 | 16 | 8 | 80 | +8 |

### September paired-conclusion check -- selectfill104 (baseline = DIRECT_M0)

| treatment arm | rule | n | saves | harms | ties | net (saves-harms) |
|---|---|---|---|---|---|---|
| JOINT_DRAFT_REVISE | V1 | 104 | 13 | 5 | 86 | +8 |
| JOINT_DRAFT_REVISE | V2e | 104 | 16 | 7 | 81 | +9 |
| JOINT_ONE_CALL | V1 | 104 | 12 | 5 | 87 | +7 |
| JOINT_ONE_CALL | V2e | 104 | 15 | 7 | 82 | +8 |
| SELECT_THEN_FILL | V1 | 104 | 13 | 5 | 86 | +8 |
| SELECT_THEN_FILL | V2e | 104 | 17 | 6 | 81 | +11 |


## Step 3 readings

- **Tier 1 (A0) is unaffected by tool ordering** (0 `TOOL_ORDER_ONLY` rows in that tier): the
  entire Tier-1 EM move under any rule comes from argument-level normalization, not sequence order.
- **V2b (drop registry-default-valued extra keys) moves Tier-1 EM from 12.00 to 40.00 (+28.00pp)**
  -- exactly the 14/50 `EXTRA_KEYS_DEFAULT_ONLY` rows. V2d (adds numeric/boolean-string type
  coercion) adds nothing further in Tier 1 for A0 (0 `CASE_OR_TYPE_ONLY` rows there), so V2e (the
  proposed combination) also lands at 40.00.
- **V2c (forgive ANY extra key, not just default-valued ones) reaches 58.00 EM in Tier 1** --
  exactly equal to Tier-1 tool accuracy, because with every extra key forgiven and no missing/wrong
  shared keys left in that tier, EM collapses onto tool accuracy. This is the "too lenient" rule
  the study brief flagged in advance: it does this by also forgiving the 9/50 `EXTRA_KEYS_NONDEFAULT`
  rows, i.e. keys the model invented that are NOT the tool's documented default -- exactly the
  signal a v2 scorer should keep penalizing.
- **Even under the proposed V2e, Tier-1 EM (40.00) remains far below the paper's 92.4.** Of A0's 44
  Tier-1 v1-failing rows, 20 (45%) are `TOOL_SET_WRONG` and 1 is `EMPTY` -- genuine tool-selection
  failures no argument-level scorer change can touch; V2e closes only the 14 `EXTRA_KEYS_DEFAULT_ONLY`
  rows, leaving the 9 `EXTRA_KEYS_NONDEFAULT` rows and the 21 tool-selection/empty rows as residual,
  scorer-independent gap.
- **Overall A0** (400 rows): V1 tool_acc/EM 54.25/24.25 -> V2e 53.00/31.25 (EM +7.00pp, tool_acc
  -1.25pp -- the ordered-tool-accuracy rule (V2a) is strictly harder than V1's multiset rule and
  costs 3/400 rows their tool-accuracy credit; V2b/V2d's EM gain outweighs it in the combined V2e
  only for EM, not for tool accuracy, by construction). `TOOL_SET_WRONG` is the single largest v1
  failure category overall (142/303 = 46.9% of all A0 v1 failures, 35.5% of all 400 rows) and is
  never touched by any of V2a-V2e.
- **`CASE_OR_TYPE_ONLY` is zero everywhere in A0** (the older flight's JSON tool-call responses
  already carry correctly-typed values) but is small and nonzero in both September AgentLoop
  flights (2-4 rows per arm) -- a real, if minor, benefit specific to the newer response schema.

## September paired-conclusion check

- **select-fill-104**: all three treatment arms (JOINT_ONE_CALL, JOINT_DRAFT_REVISE,
  SELECT_THEN_FILL) stay net-positive (saves > harms) over DIRECT_M0 under BOTH V1 and V2e; no
  sign flips. Magnitudes grow under V2e (e.g. SELECT_THEN_FILL net +8 -> +11) because V2e also
  raises DIRECT_M0's own EM (17.31 -> 24.04), which mechanically increases both saves and harms
  available to be counted, but the net direction and the sealed "not promoted" call are unchanged.
- **semantic-104**: `transcript_top16_use` (net +2 -> +8) and `same_stratum_shuffled_fused_use`
  (net -21 -> -27) keep their V1 direction under V2e. **`model_query_top16_use` (net -1 -> +3) and
  `rrf_fused_top16_use` (net 0 -> +6) flip sign** -- from "no advantage / net harm" under V1 to
  "net save" under V2e. Both flips are small relative to n=104 and no significance test was rerun
  here (the study brief asked only for saves/harms/ties counts), so this is a DIRECTIONAL finding,
  not a re-opened promotion decision -- but it is relevant to how a future semantic-AgentLoop
  iteration should be scored.
- Cross-check: this study's own V1 saves/harms/ties independently reproduce the ALREADY-SEALED
  bootstrap paired-contrast counts in both flights' postseal analyses byte-for-byte (e.g.
  `rrf_fused_top16_use` vs `direct_m0`: 8 saves / 8 harms / 88 ties here matches
  `postseal-result-summary.json`'s `fused_minus_direct_m0.exact_match` wins/losses/ties exactly;
  `SELECT_THEN_FILL` vs `DIRECT_M0`: 13 saves / 5 harms matches `result-summary.json`'s
  `versus_DIRECT_M0.paired_exact_saves`/`paired_exact_harms` exactly) -- independent confirmation
  that this re-scoring pipeline agrees with the two flights' own official scoring.

## Recommendation

Adopt **V2e = V2a (ordered tool accuracy) + V2b (drop registry-default-valued predicted extra
keys before EM) + V2d (numeric-string and boolean-string type coercion before EM)** as `a2t-scorer-v2`
semantics. Each component is a genuine SEMANTICS correction, never a lenience that could hide a
real model error:

- V2a matches the paper's own stated definition ("the ordered sequence of tools must match") --
  it can only ever cost tool-accuracy credit relative to V1, never grant it undeservedly.
- V2b only forgives an extra key whose value is BYTE-FOR-BYTE (post-canonicalization) the tool's
  own documented registry default -- a key the model could omit with no behavioral difference.
- V2d only resolves a serialization-convention difference (`"5"` vs `5`, `"true"` vs `true`) that
  carries no information loss.

**Reject V2c** (forgive every extra key regardless of default-ness): the taxonomy shows
`EXTRA_KEYS_NONDEFAULT` is a real and substantial category (39/303 = 12.9% of all A0 v1 failures,
never smaller than `EXTRA_KEYS_DEFAULT_ONLY` in any September arm), and V2c would silently convert
every one of those genuine over-specification/hallucinated-parameter errors into an exact match.

Even with V2e adopted, the residual v1-vs-paper Tier-1 gap (EM 40.0 vs the paper's 92.4) is
overwhelmingly genuine model/tool-selection performance, not scorer artifact: scorer semantics
account for at most ~28pp of Tier 1's ~80pp EM gap to the paper, and `TOOL_SET_WRONG` alone is
46.9% of every A0 v1 failure. A v2 scorer change is justified on its own merits (matching the
paper's stated definitions and not double-penalizing benign default omission) but should not be
sold as closing most of the observed capability gap.


## Files

- `summary.json` -- schema `saea-a2t-scorer-v2-study-v1`: per-source, per-arm identity check,
  taxonomy (tier x category), and rule table (rule x tier x {n, tool_accuracy, exact_match}), plus
  `paired_vs_baseline` for the two September sources and the `residuals` list (empty here).
- `per_row.jsonl` -- one row per (source, arm, sample_id): category, key/tool-name facts (names
  only, never argument values), v1 and V2e tool_accuracy/exact_match.
- Companion readiness note: `docs/readiness/2026-09-03-a2t-scorer-v2-zero-contact-study.md`.
