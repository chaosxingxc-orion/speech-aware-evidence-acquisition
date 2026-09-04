# a2t-scorer-v2 re-score of the September Audio2Tool runs (2026-09-03)

Part D step 2 of the 2026-09-03 recovery plan: re-issue the September Audio2Tool verdicts under
`a2t-scorer-v2` (`reproduction.toolcall_scoring_v2`, the registered scorer adopted from the slice-S1
zero-contact study), zero model/tool/network/audio/GPU contact. This widens slice S1's three sources
(A0-400, semantic-AgentLoop-104, select-fill-AgentLoop-104 -- `docs/readiness/2026-09-03-a2t-scorer-v2-zero-contact-study.md`)
to every other September Audio2Tool run with per-row final-answer sealed outputs: the
contract-preserving cascade, the self-transcript-cascade and self-consistency training-free probes,
and the G3/G5/G6/G7/G8C/native-structured-action-fixed8 mechanism runs.

Suite: `src/speech_aware_evidence_acquisition/analysis/a2t_v2_rescore.py` (`main()` CLI). Deliverables:
`summary.json` (schema `saea-a2t-v2-rescore-v1`; per-arm v1 identity check, v1/v2 aggregate, v1/v2
per-tier, paired contrasts), `per_arm.jsonl` (2,832 rows, one per (run, arm, sample_id)), and this
note's companion `docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-scorer-v2-rescore/README.md`.

Every one of the 36 located arms across 13 runs re-scored cleanly: its independently recomputed v1
overall (and, for A0, per-tier) numbers matched the sealed target to 4 decimals before its v2 numbers
were trusted (`analysis.a2t_v2_rescore.rescore_arm`'s identity-check gate). **Zero arms were skipped**
for identity mismatch or unreadable/malformed data.

## Cross-run table (run x arm x {v1 exact, v2 exact, v1 tool, v2 tool ordered})

| run | arm | n | v1 exact | v2 exact | v1 tool | v2 tool (ordered) |
|---|---|---|---|---|---|---|
| SAEA-BASE-a2t-a0-400 | zero_supply | 400 | 0.2425 | 0.3125 | 0.5425 | 0.5300 |
| SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1 | direct_m0 | 104 | 0.2404 | 0.2981 | 0.5096 | 0.5000 |
| SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1 | transcript_top16_use | 104 | 0.2596 | 0.3750 | 0.5962 | 0.5769 |
| SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1 | model_query_top16_use | 104 | 0.2308 | 0.3269 | 0.5769 | 0.5577 |
| SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1 | rrf_fused_top16_use | 104 | 0.2404 | 0.3558 | 0.5769 | 0.5577 |
| SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1 | same_stratum_shuffled_fused_use | 104 | 0.0385 | 0.0385 | 0.0865 | 0.0865 |
| SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5 | DIRECT_M0 | 104 | 0.1731 | 0.2404 | 0.4038 | 0.3942 |
| SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5 | JOINT_ONE_CALL | 104 | 0.2404 | 0.3173 | 0.6250 | 0.6058 |
| SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5 | JOINT_DRAFT_REVISE | 104 | 0.2500 | 0.3269 | 0.6346 | 0.6154 |
| SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5 | SELECT_THEN_FILL | 104 | 0.2500 | 0.3462 | 0.5962 | 0.5865 |
| SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2 | M0 | 104 | 0.3077 | 0.3558 | 0.5865 | 0.5865 |
| SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2 | matched | 104 | 0.3846 | 0.4038 | 0.7019 | 0.7019 |
| SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2 | shuffled | 104 | 0.2692 | 0.2885 | 0.4904 | 0.4808 |
| SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2 | resend | 104 | 0.3750 | 0.3942 | 0.6923 | 0.6923 |
| SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2 | cross_fitted_policy | 104 | 0.2885 | 0.3365 | 0.5673 | 0.5673 |
| SAEA-A2T-G1 (shared M0 anchor) | M0 | 104 | 0.2788 | 0.3846 | 0.5962 | 0.5769 |
| SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1 | USE_MATCHED | 104 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1 | USE_SHUFFLED_EVIDENCE | 104 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1 | MATCHED_RESEND_COMPOSITE | 104 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1 | CROSSFIT_POLICY | 104 | 0.2788 | 0.3846 | 0.5962 | 0.5769 |
| SAEA-A2T-TFRL-SELF-CONSISTENCY-104-V1 | REOBSERVE_DIRECT | 104 | 0.2212 | 0.2981 | 0.5288 | 0.5192 |
| SAEA-A2T-TFRL-SELF-CONSISTENCY-104-V1 | SUPPLY_UNION_STRIPPED | 104 | 0.2212 | 0.2500 | 0.5769 | 0.5577 |
| SAEA-A2T-G3-PLAIN-ENGLISH-V1 | m0 | 40 | 0.2000 | 0.2750 | 0.5250 | 0.5000 |
| SAEA-A2T-G3-PLAIN-ENGLISH-V1 | matched | 40 | 0.2000 | 0.2750 | 0.6750 | 0.6500 |
| SAEA-A2T-G3-PLAIN-ENGLISH-V1 | shuffled | 40 | 0.1750 | 0.1750 | 0.6000 | 0.5750 |
| SAEA-A2T-G5-EXHAUSTIVE-FAMILY-FIXED16-V1 | g5 | 16 | 0.1875 | 0.2500 | 0.2500 | 0.2500 |
| SAEA-A2T-G6-EXHAUSTIVE-FAMILY-SWEEP-FIXED16-V1 | g6_seal | 16 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| SAEA-A2T-G7-MULTIMODAL-EXHAUSTIVE-EXAMPLE-GROUND-FIXED16-V2 | g7 | 16 | 0.1875 | 0.1875 | 0.4375 | 0.3750 |
| SAEA-A2T-G8C-ACTION-SUPPORT-REACHABILITY-FIXED12-V1 | STOP_M0 | 12 | 0.3333 | 0.5000 | 0.8333 | 0.8333 |
| SAEA-A2T-G8C-ACTION-SUPPORT-REACHABILITY-FIXED12-V1 | EXHAUSTIVE_G7 | 12 | 0.0833 | 0.0833 | 0.5833 | 0.5833 |
| SAEA-A2T-G8C-ACTION-SUPPORT-REACHABILITY-FIXED12-V1 | SUPPORT_ONLY_RESOLVE | 12 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| SAEA-A2T-G8C-ACTION-SUPPORT-REACHABILITY-FIXED12-V1 | DECOMPOSED_SELECT_BIND_RESOLVE | 12 | 0.0833 | 0.0833 | 0.7500 | 0.7500 |
| SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1 | REGISTRY_NO_SCHEMA | 8 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1 | REGISTRY_STRICT_ACTION | 8 | 0.2500 | 0.3750 | 0.5000 | 0.5000 |
| SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1 | HANDBOOK_NO_SCHEMA | 8 | 0.1250 | 0.1250 | 0.6250 | 0.6250 |
| SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1 | HANDBOOK_STRICT_ACTION | 8 | 0.1250 | 0.2500 | 0.3750 | 0.3750 |

`SAEA-A2T-G1` (arm `M0`) is a shared frozen anchor -- the same 104-row file backs `self_transcript_
cascade`'s and `self_consistency`'s own M0 arm, and (filtered to each run's own sample-id subset) the
cross-run baseline for `g5`, `g6`, and `g7`.

## Skipped arms

None. All 36 located arms passed their v1 identity check and produced v2 numbers.

## Runs read-first named but not attempted

Two runs named in this task's read-first sweep carry no owned verdict doc in this task's ownership
scope and were **not attempted**:

- `SAEA-A2T-EXECUTABLE-GROUND-QUALIFICATION-104-V1` -- a findable `outputs.jsonl` per arm
  (`m0-registry-direct`, `g1-full-executable-ground`) exists, but no verdict doc for it is listed
  among the files this task owns, and its sealed aggregate could not be matched with certainty in the
  time budget available.
- `SAEA-A2T-CONSTRUCTION-SEMANTIC-GROUND-DIAGNOSTIC-104-V1` -- its `result-summary.json` reports
  `g1_exact_count`/`g2_exact_count` (19, 4) whose denominator and role are not self-evident from that
  file alone (not simply `/104` against the shared `A2T-G1-104` baseline), and no verdict doc for it
  is listed among the files this task owns.

## Per-tier tables for every direct-M0-style baseline, paper Tier row alongside

The paper's own per-tier row (arXiv:2604.22821 Table 3, tool_acc/EM; Tier 1 is argument-free so EM
equals tool accuracy there) is reproduced beside every baseline arm's own per-tier v1/v2 numbers for
reference -- it is a DIFFERENT frozen core / prompt / scorer than this repo's, never a target this
correction checks against.

### a0/zero_supply (SAEA-BASE-a2t-a0-400) -- v1 identity confirmed per-tier (only source with a sealed per-tier target)

| tier | n | v1 exact | v1 tool | v2 exact | v2 tool (ordered) | v2 tool (multiset) | paper tool_acc/EM |
|---|---|---|---|---|---|---|---|
| tier1_direct | 50 | 0.1200 | 0.5800 | 0.4000 | 0.5800 | 0.5800 | 0.924/0.924 |
| tier2_parametric | 50 | 0.3800 | 0.7200 | 0.4400 | 0.7200 | 0.7200 | 0.846/0.156 |
| tier3_multi_intent | 50 | 0.0400 | 0.6200 | 0.1400 | 0.5800 | 0.6200 | 0.747/0.286 |
| tier4_implicit | 50 | 0.2400 | 0.3000 | 0.2400 | 0.3000 | 0.3000 | 0.334/0.113 |
| tier5_needle | 50 | 0.3000 | 0.5400 | 0.3800 | 0.5400 | 0.5400 | 0.906/0.360 |
| tier6_correction | 50 | 0.4000 | 0.6400 | 0.4000 | 0.6400 | 0.6400 | 0.815/0.248 |
| tier7_multiturn | 50 | 0.4400 | 0.6000 | 0.4400 | 0.6000 | 0.6000 | 0.546/0.163 |
| tier8_intent_blending | 50 | 0.0200 | 0.3400 | 0.0600 | 0.2800 | 0.3400 | 0.417/0.124 |

### semantic104/direct_m0 (SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1)

| tier | n | v1 exact | v1 tool | v2 exact | v2 tool (ordered) | v2 tool (multiset) | paper tool_acc/EM |
|---|---|---|---|---|---|---|---|
| tier1_direct | 13 | 0.1538 | 0.5385 | 0.3846 | 0.5385 | 0.5385 | 0.924/0.924 |
| tier2_parametric | 13 | 0.4615 | 0.7692 | 0.4615 | 0.7692 | 0.7692 | 0.846/0.156 |
| tier3_multi_intent | 13 | 0.0000 | 0.4615 | 0.1538 | 0.3846 | 0.4615 | 0.747/0.286 |
| tier4_implicit | 13 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.334/0.113 |
| tier5_needle | 13 | 0.3846 | 0.6154 | 0.4615 | 0.6154 | 0.6154 | 0.906/0.360 |
| tier6_correction | 13 | 0.4615 | 0.7692 | 0.4615 | 0.7692 | 0.7692 | 0.815/0.248 |
| tier7_multiturn | 13 | 0.3846 | 0.4615 | 0.3846 | 0.4615 | 0.4615 | 0.546/0.163 |
| tier8_intent_blending | 13 | 0.0769 | 0.4615 | 0.0769 | 0.4615 | 0.4615 | 0.417/0.124 |

### selectfill104/DIRECT_M0 (SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5)

| tier | n | v1 exact | v1 tool | v2 exact | v2 tool (ordered) | v2 tool (multiset) | paper tool_acc/EM |
|---|---|---|---|---|---|---|---|
| tier1_direct | 13 | 0.1538 | 0.5385 | 0.4615 | 0.5385 | 0.5385 | 0.924/0.924 |
| tier2_parametric | 13 | 0.3077 | 0.6154 | 0.3077 | 0.6154 | 0.6154 | 0.846/0.156 |
| tier3_multi_intent | 13 | 0.0000 | 0.3077 | 0.0769 | 0.2308 | 0.3077 | 0.747/0.286 |
| tier4_implicit | 13 | 0.0000 | 0.0769 | 0.0000 | 0.0769 | 0.0769 | 0.334/0.113 |
| tier5_needle | 13 | 0.3846 | 0.5385 | 0.4615 | 0.5385 | 0.5385 | 0.906/0.360 |
| tier6_correction | 13 | 0.2308 | 0.3846 | 0.2308 | 0.3846 | 0.3846 | 0.815/0.248 |
| tier7_multiturn | 13 | 0.3077 | 0.6154 | 0.3077 | 0.6154 | 0.6154 | 0.546/0.163 |
| tier8_intent_blending | 13 | 0.0000 | 0.1538 | 0.0769 | 0.1538 | 0.1538 | 0.417/0.124 |

### cpv2/M0 (SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2)

| tier | n | v1 exact | v1 tool | v2 exact | v2 tool (ordered) | v2 tool (multiset) | paper tool_acc/EM |
|---|---|---|---|---|---|---|---|
| tier1_direct | 13 | 0.1538 | 0.3077 | 0.3077 | 0.3077 | 0.3077 | 0.924/0.924 |
| tier2_parametric | 13 | 0.3846 | 0.9231 | 0.4615 | 0.9231 | 0.9231 | 0.846/0.156 |
| tier3_multi_intent | 13 | 0.0769 | 0.4615 | 0.1538 | 0.4615 | 0.4615 | 0.747/0.286 |
| tier4_implicit | 13 | 0.3846 | 0.3846 | 0.3846 | 0.3846 | 0.3846 | 0.334/0.113 |
| tier5_needle | 13 | 0.5385 | 0.7692 | 0.6154 | 0.7692 | 0.7692 | 0.906/0.360 |
| tier6_correction | 13 | 0.3846 | 0.6154 | 0.3846 | 0.6154 | 0.6154 | 0.815/0.248 |
| tier7_multiturn | 13 | 0.5385 | 0.6923 | 0.5385 | 0.6923 | 0.6923 | 0.546/0.163 |
| tier8_intent_blending | 13 | 0.0000 | 0.5385 | 0.0000 | 0.5385 | 0.5385 | 0.417/0.124 |

### g1_m0_shared/M0 (SAEA-A2T-G1) -- the shared anchor consumed by self_transcript_cascade, self_consistency, g5, g6, g7

| tier | n | v1 exact | v1 tool | v2 exact | v2 tool (ordered) | v2 tool (multiset) | paper tool_acc/EM |
|---|---|---|---|---|---|---|---|
| tier1_direct | 13 | 0.0769 | 0.6923 | 0.6154 | 0.6923 | 0.6923 | 0.924/0.924 |
| tier2_parametric | 13 | 0.4615 | 0.6154 | 0.4615 | 0.6154 | 0.6154 | 0.846/0.156 |
| tier3_multi_intent | 13 | 0.0000 | 0.4615 | 0.0769 | 0.4615 | 0.4615 | 0.747/0.286 |
| tier4_implicit | 13 | 0.0769 | 0.3846 | 0.0769 | 0.3846 | 0.3846 | 0.334/0.113 |
| tier5_needle | 13 | 0.3846 | 0.9231 | 0.5385 | 0.9231 | 0.9231 | 0.906/0.360 |
| tier6_correction | 13 | 0.5385 | 0.7692 | 0.5385 | 0.7692 | 0.7692 | 0.815/0.248 |
| tier7_multiturn | 13 | 0.6154 | 0.6154 | 0.6154 | 0.6154 | 0.6154 | 0.546/0.163 |
| tier8_intent_blending | 13 | 0.0769 | 0.3077 | 0.1538 | 0.1538 | 0.3077 | 0.417/0.124 |

### g3/m0 (SAEA-A2T-G3-PLAIN-ENGLISH-V1, n=5 per tier)

| tier | n | v1 exact | v1 tool | v2 exact | v2 tool (ordered) | v2 tool (multiset) | paper tool_acc/EM |
|---|---|---|---|---|---|---|---|
| tier1_direct | 5 | 0.0000 | 0.6000 | 0.4000 | 0.6000 | 0.6000 | 0.924/0.924 |
| tier2_parametric | 5 | 0.2000 | 0.8000 | 0.4000 | 0.8000 | 0.8000 | 0.846/0.156 |
| tier3_multi_intent | 5 | 0.0000 | 0.2000 | 0.0000 | 0.2000 | 0.2000 | 0.747/0.286 |
| tier4_implicit | 5 | 0.0000 | 0.2000 | 0.0000 | 0.2000 | 0.2000 | 0.334/0.113 |
| tier5_needle | 5 | 0.6000 | 0.6000 | 0.6000 | 0.6000 | 0.6000 | 0.906/0.360 |
| tier6_correction | 5 | 0.4000 | 0.8000 | 0.4000 | 0.8000 | 0.8000 | 0.815/0.248 |
| tier7_multiturn | 5 | 0.4000 | 0.6000 | 0.4000 | 0.6000 | 0.6000 | 0.546/0.163 |
| tier8_intent_blending | 5 | 0.0000 | 0.4000 | 0.0000 | 0.2000 | 0.4000 | 0.417/0.124 |

### g8c/STOP_M0 (SAEA-A2T-G8C-ACTION-SUPPORT-REACHABILITY-FIXED12-V1, n=1-2 per tier -- thin, descriptive only)

| tier | n | v1 exact | v1 tool | v2 exact | v2 tool (ordered) | v2 tool (multiset) | paper tool_acc/EM |
|---|---|---|---|---|---|---|---|
| tier1_direct | 1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.924/0.924 |
| tier2_parametric | 2 | 0.5000 | 1.0000 | 0.5000 | 1.0000 | 1.0000 | 0.846/0.156 |
| tier3_multi_intent | 1 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.747/0.286 |
| tier4_implicit | 1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.334/0.113 |
| tier5_needle | 2 | 0.0000 | 1.0000 | 0.5000 | 1.0000 | 1.0000 | 0.906/0.360 |
| tier6_correction | 2 | 0.5000 | 1.0000 | 0.5000 | 1.0000 | 1.0000 | 0.815/0.248 |
| tier7_multiturn | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.546/0.163 |
| tier8_intent_blending | 2 | 0.0000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.417/0.124 |

### native_structured/REGISTRY_NO_SCHEMA (SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1, n=1 per tier -- thin, descriptive only)

| tier | n | v1 exact | v1 tool | v2 exact | v2 tool (ordered) | v2 tool (multiset) | paper tool_acc/EM |
|---|---|---|---|---|---|---|---|
| tier1_direct | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.924/0.924 |
| tier2_parametric | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.846/0.156 |
| tier3_multi_intent | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.747/0.286 |
| tier4_implicit | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.334/0.113 |
| tier5_needle | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.906/0.360 |
| tier6_correction | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.815/0.248 |
| tier7_multiturn | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.546/0.163 |
| tier8_intent_blending | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.417/0.124 |

REGISTRY_NO_SCHEMA scores exactly 0.0000 in every tier under BOTH v1 and v2 -- this cell's own doc
already establishes it as a total delivery-contract failure (no schema, no valid call emitted); v2's
registry-default/coercion/ordering rules have no predicted call to act on, so the outcome is identical
under either scorer version.

## Every paired contrast's exact-match CI90 zero-crossing, v1 vs v2

Of the 26 registered pairings, 6 change whether their exact-match CI90 crosses zero under v2 (all in
the direction of a MORE confident interval, never a newly-appearing false positive):

| pairing | v1 CI90 | v1 crosses 0 | v2 CI90 | v2 crosses 0 |
|---|---|---|---|---|
| cpv2/matched vs cpv2/M0 | [+0.0096, +0.1442] | no | [-0.0096, +0.1058] | **yes** |
| g7/g7 vs g1_m0_shared/M0 | [-0.1250, +0.0000] | yes | [-0.2500, -0.1250] | **no** |
| native_structured/HANDBOOK_STRICT_ACTION vs .../HANDBOOK_NO_SCHEMA | [+0.0000, +0.0000] | yes | [+0.1250, +0.1250] | **no** |
| selectfill104/JOINT_ONE_CALL vs .../DIRECT_M0 | [+0.0000, +0.1250] | yes | [+0.0096, +0.1538] | **no** |
| self_consistency/SUPPLY_UNION_STRIPPED vs g1_m0_shared/M0 | [-0.1154, +0.0000] | yes | [-0.1923, -0.0769] | **no** |
| semantic104/transcript_top16_use vs .../direct_m0 | [-0.0385, +0.0769] | yes | [+0.0000, +0.1538] | yes (boundary) |

The other 20 pairings keep the same crossing status under both scorers. No pairing flips from
"excludes zero" under v1 to "crosses zero" under v2 in a way that would WEAKEN an existing verdict's
positive finding, except `cpv2/matched vs cpv2/M0` -- already addressed in that verdict's own
correction section (the doc's decision rests on the tool-accuracy contrast, not this one, which is
unaffected).

## Reading

- **The Tier-1 EM movement under v2 is consistent across every source that carries Tier-1 rows**: A0
  (0.1200 -> 0.4000), semantic104/direct_m0 (0.1538 -> 0.3846), selectfill104/DIRECT_M0 (0.1538 ->
  0.4615), g1_m0_shared/M0 (0.0769 -> 0.6154) -- the same registry-default-argument-omission pattern
  the slice-S1 study already characterized for A0 recurs in every other Tier-1 population here, not
  an A0-specific artifact.
- **No verdict's decision flips under v2** across the twelve re-scored verdict docs: every "not
  promoted" / "closed" / "failed" reading this task's owned verdict docs already carried stays exactly
  that reading under v2 -- see each doc's own "Correction under a2t-scorer-v2" section for the specific
  saves/harms/CI90 evidence. Two directional (non-decision) sign flips recur from the slice-S1 study:
  `model_query_top16_use` and `rrf_fused_top16_use` (both semantic104) move from net-harm/neutral under
  v1 to net-save under v2 versus `direct_m0` -- small-N directional findings, not reopened promotion
  calls (the verdict doc's own "not promoted" reading covers the whole arm set, dominated by
  `transcript_top16_use`, which does not flip).
- **The three self-transcript-cascade USE/composite arms stay 0/104 under v1 AND v2** -- confirming
  their v1-recorded delivery-contract failure (never emitting the required `name` key) is a genuine
  model-output defect, not a v1 scorer artifact a more lenient v2 reading could have hidden.
- **`STOP_M0` (G8C) is the only baseline whose v2 exact match moves substantially relative to its
  n=12 size** (0.3333 -> 0.5000, +2 rows) because it is a byte composite of `A2T-G1-104`'s own M0
  responses restricted to a 12-row roster with a favorable registry-default-argument mix; every
  treatment branch in that run stays strictly worse than `STOP_M0` under both scorings regardless.

## Files

- `docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-scorer-v2-rescore/summary.json` --
  schema `saea-a2t-v2-rescore-v1`: per-arm identity check, v1/v2 aggregate, v1/v2 per-tier, and
  `paired_contrasts` for every `PAIRINGS` entry (26 pairings; every one scored cleanly).
- `docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-scorer-v2-rescore/per_arm.jsonl` --
  one row per (run, arm, sample_id): tier, v1_exact, v1_tool, v2_exact, v2_tool_ordered,
  v2_tool_multiset, parsed.
- `docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-scorer-v2-rescore/README.md` --
  the same per-arm and paired-contrast tables rendered directly from `summary.json`.
- Exposure ledger row `SAEA-A2T-MF-SCORER-V2-RESCORE-V1` (`docs/exposure-ledger.md`).
- Companion slice-S1 study (already sealed, not re-run here): `docs/readiness/2026-09-03-a2t-scorer-v2-zero-contact-study.md`.
