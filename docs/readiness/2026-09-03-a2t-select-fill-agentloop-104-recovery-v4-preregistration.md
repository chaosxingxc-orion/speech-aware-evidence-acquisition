# Audio2Tool SELECT/FILL 104-Row Flight — Recovery V4 Preregistration

Status: **REGISTERED BEFORE ANY RECOVERY-V4 MODEL, EMBEDDING, TEMPLATE, TOKENIZER, SCORER, OR GOLD CONTACT**  
Execution profile: `bounded-discovery-probe`  
Generation run: `SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V4`  
Embedding-tool run: `SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V4-EMBED`

## Predecessor boundary

Recovery V3 mechanically recovered the immutable V2 M0 and OBS prefix and completed exactly 104
local transcript embeddings in four physical batches. It persisted and reloaded a complete K=32
checkpoint, then stopped in the first model-free JOINT schema inspection before any new frozen-core
send. The public registry contains a legitimate tool argument named `label`; the generic visible-key
walk incorrectly treated that JSON Schema property declaration as a hidden runtime label. JOINT,
SELECT, REVISE, and FILL therefore made zero model contacts. No response meaning, gold, reference
transcript, scorer output, test annotation, or future turn was opened.

The V3 failure receipt SHA-256 is
`5484eabae0aeceb02bbde81c21ed60131db31543cd8405f00262710c62e41c5e`; its finalized embedding tool
receipt and attempt SHA-256 values are
`23cca6915c17709874269fd7da5c6c88a2650f92e25e51c593908ca6f4f6c1a8` and
`710c6fd90f3743bf978708c5ef3b0be43a2f51830cac654fa3ace3c4b1e242bf`. V4 uses fresh run,
mission, and attempt identities. The V3 mission and all source bytes remain immutable.

## Only implementation change

The visible-key walk continues to reject forbidden runtime data fields, including a runtime object
whose key is `label`. It now distinguishes public JSON Schema field declarations under a
`properties` map, where names such as `label` and `reference` are legitimate task-interface names;
the schemas below those names remain recursively checked. A regression test proves both sides of
this distinction. This change neither reads nor changes a prompt, registry contract, candidate set,
model response, selected-row field, gold label, score, or decision rule.

Implementation commit `7f40237256c8d4632d728cc02cc46f6e3efd0dc3` carries coordinator SHA-256
`380cdc9e908d389b53d388d1ae84f061175a72c3c27cebfd4f033c8bcd74811d`, runtime-factory SHA-256
`b5327841ad34b66813ff0555cda7e5508e0086f5e7faf5a4114f7b7d82df2748`, and protocol-config
SHA-256 `3b6e17d9f5ea0f915f0ed6b0209a7920fa606f262d6c18eb541a73e67ae76574`. The expanded
SELECT/FILL suite passes 111 tests and Ruff passes.

## Frozen experiment

V4 preserves the original 104-row fresh discovery roster, 13 rows from each of eight tiers, frozen
speech packets, frozen Qwen3-Omni core, local Qwen3 embedding model, dense K=32 retrieval, prompts,
strict response schemas, decoding, two generation slots, queue depth four, context admission,
phase barriers, official scorer, mechanism decomposition, and promotion rule registered in
`docs/readiness/2026-09-03-a2t-select-fill-agentloop-104-v1-preregistration.md`.

The answer arms remain speech-only `DIRECT_M0`, one-contact `JOINT_ONE_CALL`, equal-contact
`JOINT_DRAFT_REVISE`, and two-workflow `SELECT_THEN_FILL`. The split path transfers a canonical,
hash-bound occurrence state into a fresh FILL workflow. FILL receives selected-only public parameter
contracts and cannot change the selected names, order, positions, or multiplicity. The primary
comparison remains split versus equal-contact joint revision, so any gain cannot be attributed merely
to one extra answer call. Split versus one-call JOINT and M0 remain secondary.

V4 mechanically rehydrates the 104 M0 and 104 OBS records from the exact V2 sources already bound in
Recovery V3, with zero new contact. It repeats exactly one local 104-item transcript embedding pass in
four physical batches and writes a V4-owned hash-bound K=32 checkpoint. The V3 vectors are not loaded
or interpreted. This bounded local repeat is required by the existing one-shot mission ownership and
has no final-answer authority.

V4 authorizes exactly 416 new frozen-core contacts: 104 each for JOINT, SELECT, REVISE, and FILL.
The conservative generation limits are 3,400 speech-audio seconds and 4.0 GPU hours. The local
embedding limits are 104 logical items, four physical requests, one schema-required conservative
audio second, and 0.2 GPU hours. No retry, repair, resend, fallback, response substitution,
network-jitter study, test use, policy fit, approximately-1,000-row expansion, Stage-3 work, or paper
claim is authorized.

## Capacity, sealing, and analysis

Generation uses a physical 32,768-token context per slot and admits each exact request independently
against a 24,576-token operating cap, retaining 8,192 tokens of reserve. Every one of the 104 physical
request variants in a phase must pass live template, grammar, tokenizer, speech-token, and completion
checks before that phase sends. Prompt growth is measured again after every workflow boundary.
Generation requests are individual; only local embedding is batched.

Seal and verify all JOINT and SELECT predecessor states before REVISE or FILL is materialized. Seal
exactly four complete answer manifests before opening response meaning, gold, or scorer output. Score
the four whole manifests with the unchanged official single-process scorer through at most four outer
workers; never shard a manifest or average shard metrics. The recovered M0 source bundle is score-only,
while the three new answer bundles use their normal finalization path.

Report exact match, tool accuracy, slot micro-F1, parse rate, all eight tiers, prompt tokens, contacts,
and wall time. Network jitter is excluded from efficacy. Assign agentic errors in order to `SUPPLY`,
`SELECT`, `FILL`, or `SUCCESS`; report selector multiplicity accuracy and conditional FILL accuracy.
For the primary and secondary paired contrasts, report saves, harms, ties, exact sign tests, and
10,000 tier-stratified bootstrap replicates with seed 20260903.

Promote separation only if its lower 90% exact bound is above zero against both joint controls, tool
and slot effects are nonnegative against both, exact improves over M0, and no tier has more than one
net exact loss. Split beating only one-call JOINT is additional-inference evidence, not decomposition
evidence. Predominant SUPPLY errors return work to knowledge construction; high reachability with weak
FILL returns work to selected parameter supply and use.

This engineering baseline is not required to exceed 0.90. That target applies only after a separately
preregistered training-free RL stage using deployment-visible state and preferentially reusing pinned
upstream `vowpalwabbit==9.11.2` `cb_explore_adf`. V4 opens no test split, training-free policy fit, or
scale expansion.
