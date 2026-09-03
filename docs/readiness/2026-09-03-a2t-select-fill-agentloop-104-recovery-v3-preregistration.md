# Audio2Tool SELECT/FILL 104-Row Flight — Recovery V3 Preregistration

Status: **REGISTERED BEFORE ANY RECOVERY-V3 MODEL, EMBEDDING, TEMPLATE, TOKENIZER, SCORER, OR GOLD CONTACT**  
Execution profile: `bounded-discovery-probe`  
Generation run: `SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V3`  
Embedding-tool run: `SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V3-EMBED`

## Source boundary and reason for recovery

Recovery V2 completed exactly 104 `M0_DIRECT` contacts, 104 `OBS_SEMANTIC_STATE` contacts, and
104 local transcript embeddings in four physical batches. It stopped during model-free ground
construction, before the first `JOINT_ONE_CALL` request, because the canonical public registry
sentinel `No public constraint is declared.` was not normalized as an empty constraint set. The
`JOINT_ONE_CALL`, `SELECT`, `JOINT_DRAFT_REVISE`, and `FILL` phases therefore made zero sends. No
response meaning, gold label, reference transcript, scorer output, test annotation, or future turn
was opened.

The V2 M0 and OBS attempts are terminal `ABORTED`; their 208 responses remain immutable and are
eligible only for mechanical recovery. The V2 embedding attempt is terminal `FINALIZED`, but its
receipt bound request and response hashes rather than the vector values or derived K=32 sets. The
lost process memory makes one new local embedding pass necessary. Recovery V3 never reuses a V2
attempt, run, or mission identity for new contact.

The bound V2 source hashes are:

- generation send accounting: `c3acd1614510527006ab63b2a0098fb6e404388330e6c76f837faf871b188377`;
- M0 and OBS preflights: `e6d1f83bf38a2bc79fe80950c1e1dbfce04ea4a78b2efeb5822679d1c3e130ac`
  and `e47a18d904bef7a0e90b6ee358d0acb3b227ec543c9f3caaeeefd8f31fc00e85`;
- M0 and OBS traces: `985bea38ccfca5429e4e2fe150b57c90195daf1cf20c8e97093ebfe419324e6a`
  and `0426226cdc34db5075de2624e43d2d7517d5e166f7dfbafa69b77b5f1f4afb54`;
- embedding tool receipt: `8f3658d92adb26fbe21d64347db36c195bae465507fd0be22c0c2f290e3e3045`;
- authority binding and generation session receipt:
  `0df4783da0ba03df4a469aa2f19e87e3c12e238a0e6525505bd492d050f1e04e` and
  `4386cd8e9790d9627c955bb46acdc389822960d3d655ba0a94b6a00506729654`;
- terminal M0 attempt: `6fbbf2a1595e27b704cae249175ff30be36b2d5de12effa0d69a0f3fc05cfd0b`.

## Frozen scientific comparison

The scientific design, 104-row fresh discovery roster, eight-tier balance, packets, frozen core,
local embedding model, K=32 retriever, prompts, schemas, decoding, context admission, two generation
slots, queue depth four, scorer, analysis, and promotion rule remain those registered in
`docs/readiness/2026-09-03-a2t-select-fill-agentloop-104-v1-preregistration.md`.

The four answer arms are:

1. `DIRECT_M0`: one speech-only model contact, mechanically recovered from V2.
2. `JOINT_ONE_CALL`: one fresh answer contact with OBS state and K=32 joint knowledge.
3. `JOINT_DRAFT_REVISE`: the byte-exact joint draft plus one fresh revision contact.
4. `SELECT_THEN_FILL`: one fresh routing-only SELECT contact followed by a fresh FILL contact that
   receives only parameter knowledge for the sealed selected tools.

The primary comparison is `SELECT_THEN_FILL - JOINT_DRAFT_REVISE`. Both paths use two answer contacts,
so it isolates workflow decomposition and context specialization from the benefit of a second model
call. Split versus `JOINT_ONE_CALL` and `DIRECT_M0` are secondary. Parameter cues may help joint tool
selection, and SELECT errors may propagate through the locked FILL boundary, so no direction of effect
is assumed.

All predecessor state crossing a workflow boundary is canonical and hash-bound. Raw conversation
history does not accumulate. FILL cannot change selected tool names, order, positions, or multiplicity;
it receives selected-only public parameter contracts. REVISE receives the canonical joint draft state.

## Authorized recovery work and budgets

Recovery V3 mechanically rehydrates all 104 M0 and all 104 OBS records from the exact V2 traces with
zero new frozen-core contact. It derives a standard, verified, source-named M0 run bundle from those
bytes; the source attempt remains `ABORTED`, and that bundle is score-only rather than finalized again.

Recovery V3 re-embeds exactly 104 canonical English OBS transcripts using pinned local
`Qwen3-Embedding-0.6B-Q8_0`, batch size 32, in exactly four physical requests. This tool has no answer
authority and consumes no speech. The resulting vectors and deterministic K=32 candidate sets must be
persisted in a hash-bound checkpoint and reloaded successfully before the first JOINT request.

The new generation authorization is exactly 416 frozen-core contacts: 104 each for
`JOINT_ONE_CALL`, `SELECT`, `JOINT_DRAFT_REVISE`, and `FILL`. The conservative generation budget is
3,400 speech-audio seconds and 4.0 GPU hours. The embedding budget is 104 logical items in four
physical batches, one schema-required conservative audio second, and 0.2 GPU hours. No retry, repair,
resend, fallback, response substitution, network-jitter experiment, test use, policy fit,
approximately-1,000-row expansion, Stage-3 work, or paper-scale claim is authorized.

## Context, batching, and phase barriers

Generation uses `-c 65536 -np 2`, or 32,768 physical tokens per slot. Every request is admitted
individually against a 24,576-token operating cap, retaining 8,192 tokens of reserve. The runtime must
materialize and validate all 104 exact physical request bodies for both slot identities before a phase
sends. Prompt growth is measured independently at every workflow step; no average-length extrapolation
is allowed. Generation remains individual rather than batched. Only local embedding uses batching.

Mechanically recover M0 and OBS, finish embedding and reload the K=32 checkpoint, then preflight JOINT
and SELECT in full before either sends. Seal and verify all JOINT and SELECT predecessor states before
materializing REVISE or FILL. Preflight both second-stage phases in full before either sends. A local
failure or overflow is terminal for the new one-shot identities.

Exactly four complete answer manifests must seal before response meaning, gold, or scorer output is
opened: `direct_m0`, `joint_one_call`, `joint_draft_revise`, and `select_then_fill`. Run the unchanged
official single-process scorer as four outer-parallel whole-manifest jobs with at most four workers.
Do not shard a manifest or average shard metrics. The recovered direct bundle uses score-only mode;
the three new terminal bundles use their normal finalize operation.

## Analysis and decisions

Report exact match, tool accuracy, slot micro-F1, parse rate, all eight tiers, prompt tokens, contacts,
and wall time. Network jitter is excluded from efficacy analysis. Assign every agentic row exactly one
post-seal mechanism: `SUPPLY`, `SELECT`, `FILL`, or `SUCCESS`. Report selector name and multiplicity
accuracy, conditional FILL accuracy, paired saves, harms, ties, exact sign tests, and 10,000
tier-stratified paired-bootstrap replicates with seed 20260903.

Promote workflow separation only if its lower 90% paired-bootstrap exact bound is above zero against
both joint controls, tool and slot effects are nonnegative against both, exact improves over M0, and no
tier has more than one net exact loss. Also report whether its token and latency cost is acceptable;
efficiency does not override the efficacy gate. If split beats only one-call JOINT, attribute the gain
to additional inference rather than decomposition. If SELECT succeeds but FILL remains weak, improve
selected parameter supply and use. If errors are predominantly SUPPLY, return to knowledge
construction or organization before expanding scale.

This 104-row discovery flight is not required to exceed 0.90. That target belongs after a separately
preregistered training-free RL stage, which must use deployment-visible state and preferentially reuse
pinned upstream `vowpalwabbit==9.11.2` `cb_explore_adf`. No approximately-1,000-row scale, test
evaluation, or training-free RL fit begins unless a stable discovery-stage agentic gain passes the
frozen rule.

## Implementation binding

Implementation commit `ff62660a2f1e7fe77521a28dd8eeede11f0edd39` carries coordinator SHA-256
`b2355e8bf1afbf3041b2e498cec2f21ac30dbc477f4a14115beedc7a784e4372`, runtime-factory SHA-256
`27c8f445e04936193f07e1a30d5597f808a97ecb46d66a868245c2644bbbe50a`, and protocol-config SHA-256
`2498bb5da9c66b21d498743b9c78126734d3ca33e41fcee56a7c77758afb4616`. The expanded SELECT/FILL
suite passes 109 tests and Ruff passes. Final authority must bind these bytes, this preregistration,
four fresh generation plans, one fresh embedding plan, the exact V2 source artifacts, all static
runtime assets, and unique absent mission and attempt identities before any contact.
