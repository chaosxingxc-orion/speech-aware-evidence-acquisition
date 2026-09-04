# Audio2Tool Semantic AgentLoop 104-Row Flight — Post-Seal Verdict

Status: **COMPLETED DISCOVERY FLIGHT; LOCAL-VECTOR DIRECTION RETAINED; CURRENT METHOD NOT PROMOTED TO APPROXIMATELY 1,000 SAMPLES**

## Result

The flight completed 624 frozen-core generation contacts and 208 logical local-embedding contacts on
104 discovery samples, 13 from each of eight Audio2Tool tiers. All five answer manifests were scored
with the unchanged official scorer as complete-manifest jobs. Four outer workers finished the five
jobs in 8.401 seconds versus 28.61 summed process seconds, a 3.40-times throughput speedup with no
dataset sharding or shard-score averaging.

| Arm | Exact match | Tool accuracy | Slot F1 | Parse rate |
|---|---:|---:|---:|---:|
| Direct M0, all 152 tools | 0.2404 | 0.5096 | 0.3333 | 0.8942 |
| Transcript-vector top-16 USE | **0.2596** | **0.5962** | 0.3470 | **1.0000** |
| Same-core-query top-16 USE | 0.2308 | 0.5769 | 0.3185 | **1.0000** |
| RRF-fused top-16 USE | 0.2404 | 0.5769 | **0.3495** | 0.9904 |
| Same-tier shuffled fused USE | 0.0385 | 0.0865 | 0.1206 | **1.0000** |

Transcript-vector top-16 versus direct M0 gained 1.9 percentage points exact match and 8.7 points
tool accuracy. The registered paired 90% intervals were [-4.8, 8.7] and [1.0, 16.3] points;
exact-match wins/losses/ties were 10/8/86 and tool wins/losses/ties were 18/9/77. This is encouraging
tool-selection evidence, but it is not stable exact-match superiority.

The same-core retrieval query did not improve the local transcript-vector arm: it changed the
selected set on 93 of 104 rows, but exact match fell 2.9 points and tool accuracy fell 1.9 points.
RRF fusion also failed to beat either single view. The local transcript-vector route is therefore the
retained retrieval baseline; the current same-core query and RRF-60 forms are rejected.

Matched fused evidence beat the same-volume, same-tier shuffled evidence by 20.2 exact-match points
(paired 90% interval [12.5, 27.9], exact sign-test p = 0.000049) and 49.0 tool-accuracy points
([40.4, 57.7], p = 8.55e-14). The control is fully bound: 104/104 shuffled packets map to one unique
fused donor, all donors are non-self and same-tier, and all packet sizes remain 16 cards. This proves
that sample-specific task information carries substantial value; it is not a prompt-volume effect.

## Knowledge construction and consumption diagnosis

Required-tool coverage in the selected top 16 is 92/104 = 0.8846 for transcript, same-core query,
and fusion. The equal aggregate masks different rows: query versus transcript has three coverage
saves and three losses; transcript-plus-query union reaches only 95/104 = 0.9135 even with as many as
32 candidates. The largest top-16 coverage deficits occur in implicit, multiturn, and intent-blending
tiers. This is below the preregistered 0.90–0.95 ground target, so knowledge construction and ORG must
be improved before scale.

Reachability is a necessary candidate-label upper bound, not an achievable task-accuracy ceiling.
Among the 92 transcript-reachable rows, tool accuracy is 62/92 = 0.6739 and exact match is
27/92 = 0.2935. No unreachable row is tool-correct. The 28.8-point gap between retrieval reachability
and observed tool accuracy is a USE/decision gap. Separately, only 27 of the 62 tool-correct
transcript rows are exact, so conditional exact match after correct tool selection is 0.4355. This is
the strongest evidence that parameter and call-structure construction are a second bottleneck.

A post-hoc label oracle over direct M0 and the three semantic USE arms reaches only 0.3365 exact and
0.6827 tool accuracy. It is not a deployable controller, but it demonstrates limited action-dependent
headroom for later training-free RL. Training-free RL cannot manufacture the missing knowledge or
parameter competence; those mechanisms must improve first.

## Next 104-row workflow experiment

The next experiment will separate tool selection from parameter construction while preserving a
matched control for extra test-time compute:

1. `JOINT_ONE_CALL`: original speech plus the improved locally retrieved knowledge, with one joint
   final-call response.
2. `JOINT_DRAFT_REVISE`: two same-core contacts that jointly draft and revise tool calls. This is the
   equal-contact control.
3. `SELECT_THEN_FILL`: `SELECT` receives original speech and routing-only evidence and emits only an
   ordered call skeleton. `FILL` receives original speech, the canonical selector state, and only the
   selected tools' parameter-specific evidence; its response schema locks the selected ordered tool
   skeleton and it fills arguments only.
4. A later `RESELECT` transition is eligible only if the hard split exhibits measurable selector
   error propagation. A deterministic validator may expose an incompatibility state, but it may not
   silently change a tool or inject a label.

`SELECT` context should contain tool intent, positive/negative routing cues, compatibility, and
multi-intent ordering guidance, without detailed argument material. `FILL` context should contain
only the selected tool schemas, required/optional parameters, enum/range constraints, entity-value
normalization rules, correction/multiturn state, and construction examples that do not overlap the
flight identities. This makes context loading sample-dependent and value-bearing: selection narrows
152 tools to an ordered skeleton, and parameter supply then narrows the remaining decision to legal
values for those tools.

Each contact receives a fresh bounded context assembled from canonical state, never cumulative raw
dialogue history. Exact prompt length is measured after assembly against the physical 32,768-token
slot; the operational ceiling retains an 8,192-token reserve. Generation remains individual-request
concurrency with two slots and queue depth four. Only the local encoder uses physical batching.

Before model contact, a construction-only knowledge audit must demonstrate at least 0.95
required-tool coverage on an isolated non-test validation population without selecting rules from
the 104 scored outcomes. The model flight then reports final exact/tool/slot/parse scores; selector
ordered-skeleton accuracy; exact and slot metrics conditional on a correct selector; prompt tokens;
contacts; per-tier paired saves/harms; and both `SELECT_THEN_FILL - JOINT_ONE_CALL` and
`SELECT_THEN_FILL - JOINT_DRAFT_REVISE` contrasts. Approximately-1,000-sample expansion remains
closed unless the split workflow establishes stable exact-match improvement, nonnegative tool and
slot effects, and no material tier regression.

## Training-free RL workspace

No policy is fit in this row. A later pinned `vowpalwabbit==9.11.2 cb_explore_adf` controller may
choose among `STOP_M0`, joint USE, split USE, and eventually validated re-selection only after these
actions have positive, deployment-visible returns. Candidate context includes retrieval coverage
proxies, score margins, selected tool count, ordered-skeleton length, schema-risk class, validator
state, missing-value state, prompt cost, and tier-blind speech/observation structure. Gold labels,
official scores, and post-hoc reachability never become runtime context.

## Binding and scope

The committed summary is
`docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-semantic-agentloop-104-v1/postseal-result-summary.json`.
Its external post-seal report, information-gain diagnostics, and shuffle binding are hash-pinned in
that summary. This verdict uses discovery data only, makes no test-set or confirmatory claim, and
excludes network jitter, retry, resend, and transport timing from scientific interpretation. The
post-training-free-RL greater-than-0.90 objective is not a baseline-admission requirement and has not
been reached by this flight.

## Correction under a2t-scorer-v2 (2026-09-03)

Zero-contact offline re-score of the same five sealed `outputs.jsonl` files (104/104 rows each, v1
identity confirmed to 4 decimals overall for every arm) under the registered `a2t-scorer-v2`
(`analysis.a2t_v2_rescore`, `docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-scorer-v2-rescore/`).

| Arm | v1 exact | v1 tool | v2 exact | v2 tool (ordered) | v2 tool (multiset) | v2 slot F1 | v1 slot F1 | parse rate |
|---|---|---|---|---|---|---|---|---|
| direct_m0 | 0.2404 | 0.5096 | 0.2981 | 0.5000 | 0.5096 | 0.4149 | 0.3333 | 0.8942 |
| transcript_top16_use | 0.2596 | 0.5962 | 0.3750 | 0.5769 | 0.5962 | 0.4296 | 0.3470 | 1.0000 |
| model_query_top16_use | 0.2308 | 0.5769 | 0.3269 | 0.5577 | 0.5769 | 0.4000 | 0.3185 | 1.0000 |
| rrf_fused_top16_use | 0.2404 | 0.5769 | 0.3558 | 0.5577 | 0.5769 | 0.4385 | 0.3495 | 0.9904 |
| same_stratum_shuffled_fused_use | 0.0385 | 0.0865 | 0.0385 | 0.0865 | 0.0865 | 0.1326 | 0.1206 | 1.0000 |

Paired contrasts vs. `direct_m0` (v1 and v2, CI90, 10,000 replicates, tier-stratified):

| treatment | metric | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|
| transcript_top16_use | v1 exact | +0.0192 | 10 | 8 | 86 | [-0.0385, 0.0769] |
| transcript_top16_use | v2 exact | +0.0769 | 16 | 8 | 80 | [0.0000, 0.1538] |
| model_query_top16_use | v1 exact | -0.0096 | 6 | 7 | 91 | [-0.0673, 0.0481] |
| model_query_top16_use | v2 exact | +0.0288 | 10 | 7 | 87 | [-0.0385, 0.0865] |
| rrf_fused_top16_use | v1 exact | +0.0000 | 8 | 8 | 88 | [-0.0577, 0.0577] |
| rrf_fused_top16_use | v2 exact | +0.0577 | 14 | 8 | 82 | [-0.0096, 0.1250] |
| same_stratum_shuffled_fused_use | v1 exact | -0.2019 | 3 | 24 | 77 | [-0.2692, -0.1346] |
| same_stratum_shuffled_fused_use | v2 exact | -0.2596 | 3 | 30 | 71 | [-0.3365, -0.1827] |

These saves/harms counts reproduce the slice-S1 zero-contact study's V1/V2e numbers for this source
exactly (e.g. `model_query_top16_use` net saves-harms flips from -1 under v1 to +3 under v2;
`rrf_fused_top16_use` flips from 0 to +6). The v2 CI90 for `transcript_top16_use` vs `direct_m0`
exact match is [0.0000, 0.1538] — its lower bound sits at zero rather than clearly excluding it, the
same qualitative reading as v1's [-0.0385, 0.0769], which also crosses zero. The verdict's decision
is unchanged: not promoted under v2 either — no arm here reaches stable exact-match superiority over
`direct_m0` under either scoring, and the approximately-1,000-sample expansion gate this doc states
remains closed.
