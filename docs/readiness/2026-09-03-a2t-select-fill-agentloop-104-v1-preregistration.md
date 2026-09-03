# Audio2Tool SELECT/FILL AgentLoop 104-Row Flight — Preregistration

Status: **REGISTERED BEFORE ANY FLIGHT GENERATION, EMBEDDING, TEMPLATE, TOKENIZER, SCORER, OR GOLD CONTACT**  
Execution profile: `bounded-discovery-probe`  
Generation run: `SAEA-A2T-SELECT-FILL-AGENTLOOP-104-V1`  
Embedding-tool run: `SAEA-A2T-SELECT-FILL-AGENTLOOP-104-V1-EMBED`

## Scientific question

Determine whether accurate tool identification and accurate argument extraction should remain in one
frozen-core workflow or be separated into two OpenJiuwen workflows with a canonical state boundary.
The split candidate first receives routing-only knowledge and emits ordered tool occurrences. A fresh
FILL workflow then receives the original speech, canonical observation state, the sealed occurrence
state, and parameter knowledge only for those selected tools. Tool names and multiplicity are locked
during FILL.

The primary comparison is against an equal-contact joint draft/revise controller. A one-contact joint
arm tests the value of a second inference contact, and a true one-contact speech-only M0 arm tests the
complete agent system against the frozen model without agent-supplied task information. The study does
not assume that decomposition wins: parameter cues can help routing, and an early SELECT mistake can
propagate through a locked FILL stage.

This is an engineering-baseline discovery flight. Task performance above 0.90 is not an admission
condition. The greater-than-0.90 objective applies after a later, separately preregistered training-free
RL stage. This flight fits no policy, opens no test split, and authorizes no approximately-1,000-row
expansion by itself.

## Frozen population and knowledge ground

Use exactly the 104 discovery samples in `A2T-SELECT-FILL-FRESH-FLIGHT`, with 13 rows from each of the
eight Audio2Tool tiers. The roster receipt SHA-256 is
`dea74114430ed5e45e29d908dc2ecebf41788edfa2704435a2966f260de5bc4f`; the colon-key split identity used
by `ExecutionPlan` is `bcbad5405aa8522ff53a91d624c54a909e01f8a31612b5165844b8e2cbca6eb3`; the slash-key
bundle identity is `122da6752c7c4011c2f632cee4e737899bfbb451501666fb47aa0676f372d2c8`; one speech pass is
549.489916 seconds. The roster is disjoint from the prior semantic 104 by sample identity, query block,
and normalized-token class.

The promoted 104-packet receipt SHA-256 is
`1f7411359311a012c5162ee5472ef767d055a66521f2b12b4da267d1f0660e07`; its preprocessing report
SHA-256 is `bc1794eb2805bd65a96bb78cd7bf2b70dd4ce0e71d0cc0887a86d77d7727cf6d`. Measured speech tokens
range from 26 to 286, with median 58.5 and p95 169.

The fixed local transcript-vector retriever uses dense K=32. Its construction-only grouped-fold
qualification is bound by
`docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-select-fill-agentloop-104-v1/knowledge-qualification.json`.
It achieves 0.982303 full-set coverage, 0.985842 required-label recall, 0.975822 worst-fold full-set
coverage, and at least 0.941710 tier coverage. This is a retrieval reachability ground, not a task
accuracy claim. Runtime may consume only frozen label-free vectors, centroids, cards, public registry
contracts, compatibility rules, and canonicalizers. It may not reopen construction examples or any
selected-row task field.

Gold calls, reference transcripts, selected-row query text, test annotations, previous answers,
scores, future turns, and scorer output remain unavailable until all four answer manifests seal.

## Frozen workflows and contacts

Run six generation phases over all 104 rows:

1. `M0_DIRECT`: one speech-only complete-registry answer contact.
2. `OBS_SEMANTIC_STATE`: one task-blind speech contact producing a canonical English transcript and
   retrieval state.
3. `JOINT_ONE_CALL`: one fresh answer contact with the OBS state and K=32 joint routing/parameter
   ground.
4. `SELECT`: one fresh contact with the OBS state and K=32 routing-only ground; output is one to seven
   ordered name-only occurrences.
5. `JOINT_DRAFT_REVISE`: one fresh contact that reuses the byte-exact sealed `JOINT_ONE_CALL` response
   as canonical draft state and may revise the complete answer.
6. `FILL`: one fresh contact with selected-only parameter ground; the sealed SELECT occurrence names,
   positions, and multiplicity cannot change.

`JOINT_ONE_CALL` is generated exactly once. The revise arm therefore has two total answer contacts,
not a regenerated first stage. The split and revise paths each have two answer contacts. Every phase
uses a new one-contact OpenJiuwen workflow context, the original speech packet, and no cumulative raw
chat history. Only canonical hash-bound OBS or predecessor state can cross phases.

The generation ceiling is exactly 624 frozen-core contacts. Because all six phases reference the
original speech carrier, the conservative speech-audio ceiling is 3,400 seconds; the GPU ceiling is
4.0 hours. Generation requests remain individual, use two sample-affine slots and queue depth four,
and have no retry, repair, resend, fallback, or response substitution.

The local pinned `Qwen3-Embedding-0.6B-Q8_0` retriever embeds exactly one English OBS transcript for
each sample: 104 logical contacts in four physical requests of at most 32 texts, last pooling, dimension
1,024, and zero speech audio. It is a frozen retrieval tool and has no answer authority. The embedding
server never coexists with the generation server.

## State and schema boundary

Every JOINT draft and SELECT state binds the actual physical slot request body and response bytes,
sample identity, both split identity conventions where required, speech packet, producing query state,
OBS state and source response, K=32 candidate order, exact ground, exact response schema, stage, and
canonical payload. The physical request hash is known only after slot allocation and must never be
pre-populated with an abstract renderer hash.

REVISE and FILL externally verify their complete predecessor envelope before rendering. Raw responses
are not forwarded. FILL receives a deterministic selected-only parameter ground, while candidate-set
lineage remains bound separately. Structured responses are revalidated after generation against the
same strict schema used to create the llama.cpp grammar, including name constants, exact legal argument
skeletons, required fields, public types, numeric limits, enumerations, positional occurrence locks,
and additional-property refusal. Invalid output is a terminal row failure; it is never repaired.

## Context capacity and batching

The generation server uses `-c 65536 -np 2`, yielding a physical 32,768-token context per slot. The
operational admission cap is 24,576 required tokens per request, retaining an 8,192-token reserve for
speech state and implementation variance. Before any generation is sent in a phase, materialize all
104 exact physical request templates. Validate the exact flattened request bodies for both possible
slot identities, compile the strict response schema through the pinned live template path, tokenize
every non-speech prompt segment with the pinned live tokenizer, add measured packet tokens, registered
special-token reserve, and the request-specific completion ceiling, and admit the phase only if every
row fits. One late overflow means zero generation sends for that phase.

This rule applies independently to M0, OBS, JOINT, SELECT, REVISE, and FILL. Prompt growth is measured,
not extrapolated from an average or an earlier loop step. Generation is concurrent but not prompt
batched. Only embeddings use batches. Network jitter is excluded from efficacy analysis; a transport
failure is one-shot run-integrity evidence.

## Phase barriers and final manifests

Complete M0 and OBS before embedding. Complete the four transcript-embedding requests and deterministic
K=32 retrieval before answer workflows. Preflight both JOINT and SELECT in full before either first-stage
send. Seal and verify all 104 JOINT draft states and all 104 SELECT states before materializing either
second-stage phase. Then preflight every REVISE and FILL request before either second-stage send.

Seal exactly four answer manifests: `direct_m0`, `joint_one_call`, `joint_draft_revise`, and
`select_then_fill`. OBS and SELECT are diagnostic phases, not official answer manifests. No response
meaning may be read by a human or analysis process, and no gold-derived reachability, task metric, or
official scorer may be opened, before all four answer manifests and the flight receipt are complete.
The runtime may mechanically parse the exact OBS, JOINT draft, and SELECT schemas only to produce the
preregistered canonical downstream state; those intermediate values cannot change any frozen rule.

## Post-seal evaluation and decision rule

Run the unchanged official single-process scorer as four complete-manifest jobs through an outer pool of
at most four workers. Do not shard a manifest and do not average shard metrics. Report exact match, tool
accuracy, slot micro-F1, parse rate, all eight tiers, tokens, contacts, and wall time.

For each agentic arm, assign each row exactly one mechanism after sealing: `SUPPLY` when a required tool
is outside K=32; `SELECT` when all required tools are reachable but the chosen name multiset or
multiplicity is wrong; `FILL` when names and multiplicity are correct but the official answer is not
exact; and `SUCCESS` when exact match is one. M0 is never assigned a K=32 SUPPLY error. Report selector
name/multiplicity accuracy, joint draft and revised name diagnostics, and conditional FILL accuracy as a
diagnostic only.

The primary contrast is paired `SELECT_THEN_FILL - JOINT_DRAFT_REVISE`. Secondary contrasts are split
minus `JOINT_ONE_CALL` and split minus `DIRECT_M0`. Report paired saves, harms, ties, exact sign tests,
and 10,000 tier-stratified paired bootstrap replicates with seed 20260903 for exact, tool accuracy, slot
F1, and parse rate.

Promote the split architecture only if the lower 90% paired-bootstrap exact bound is above zero against
both joint controls, tool and slot effects are nonnegative against both, exact improves over direct M0,
and no tier has more than one net exact loss. If split beats only one-contact JOINT, attribute the result
to additional inference compute. If FILL improves conditionally but SELECT errors erase the final gain,
retain the mechanism result and design a separately preregistered validator or reselection experiment.
If failures are mainly SUPPLY, return to knowledge construction or organization. If reachability is high
but FILL remains weak, improve selected parameter content and its use before widening K.

No approximately-1,000-row scale, test evaluation, or training-free RL fit starts unless a stable
104-row agentic gain passes the frozen rule. A later training-free controller must use deployment-visible
state only and preferentially reuse pinned upstream `vowpalwabbit==9.11.2` `cb_explore_adf` rather than
introducing a repository-owned learner.

## Artifact bindings and authority

The committed composed experiment config SHA-256 is
`ee0fa0beb4c49e4a8539354c7eec9b336120ee3660f5e7e13e204609412ed2d1`; the core protocol SHA-256 is
`db933dfc8975b30ac8ce07526aa074874e554c1fbc055b39ebbc7719d3e936bd`; and the identity-only official
scorer roster receipt SHA-256 is
`017fce92b63c35e799f52d448ab6da2bf5d406b33cd256bd1f451b9ffda8b499`.

The final contact authority must additionally bind a clean implementation commit, exact coordinator and
runtime-factory hashes, all six generation `ExecutionPlan` objects, the embedding plan, runtime/GGUF
receipts, packet promotion, frozen semantic assets, ground corpus, compatibility rules, knowledge
qualification, and this preregistration. Any code, config, runtime, prompt, schema, knowledge, roster,
packet, plan, or preregistration hash change requires a new authority and fresh attempt identities before
contact.
