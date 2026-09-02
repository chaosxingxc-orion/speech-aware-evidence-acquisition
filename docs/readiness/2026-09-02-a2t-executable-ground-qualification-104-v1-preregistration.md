# Audio2Tool executable-ground qualification 104 v1 preregistration

Date: 2026-09-02. Status: **REGISTERED DESIGN; MODEL CONTACT CLOSED**.
Experiment: `SAEA-A2T-EXECUTABLE-GROUND-QUALIFICATION-104-V1`.
Execution profile: `bounded-discovery-probe`.
Composed config SHA-256:
`60b896eea441e94cc6570e5721303762b88da388d0ddc987a6a7b65cdeca8dda`.
Protocol SHA-256: `82680b0bc909a0c6f3f88f87ce4bd815feecdeff03a694e79e8456acc63dc33b`.
These identities supersede both earlier zero-contact design pairs before any model contact. They
freeze the grouped interval procedure plus phase/attempt order, no-recontact failure behavior,
resend payload equivalence, finalized-score consumption, parsed-empty reporting, and resend
agreement semantics.

## Objective and scientific sequence

This experiment implements the owner's required sequence: first establish a query-independent task
knowledge ground that the frozen core can understand and use at at least 90% basic task performance,
targeting 95%; only afterwards discuss candidate reduction, AgentLoop information acquisition, and
training-free control. It does not optimize a candidate set and does not fit a policy.

The roster is the frozen `A2T-GROUND-QUAL-104` identity-only selection: 104 items, 13 per tier,
543.107 speech-audio seconds, receipt SHA-256
`eeb90abbe8695e449c676f18339db6618cb6d606d6c1e7c656626e4e9b6b6c16`, run identity
`fbd4addd541ff29214cbff7c35564b15f27e2fb7f438202b79d694b1c5961d4b`. It is already-exposed-parent
discovery evidence, query-block-disjoint from G1 and CPV2, and construction-block-disjoint from the
handbook. Parent A0 responses and scores did not enter selection. The protected unexposed 400, test,
and future turns remain closed.

## Frozen contrast

`M0_REGISTRY_DIRECT` makes one call per item with the original speech packet and unchanged complete
152-row registry. `G1_FULL_EXECUTABLE_GROUND` makes one call per item with the same speech packet,
model, serving geometry, decoding, and output authority, replacing only the system knowledge with
the exact 54,881-byte executable handbook, SHA-256
`58ba08f3cebbe390156506653051d54aa37796822f49f5b851fd6eba4818fbc8`.

The ground contains no sample utterance, argument value, complete registry default literal, gold,
reference transcript, expected call, prior response, score, test annotation, or future turn. It is
the full task-wide knowledge ground, not a retrieved candidate list. This isolates whether executable
knowledge is usable before any pruning decision.

Sixteen ground requests, two per tier, are selected by the frozen identity-only namespace before
contact and repeated once after both full arms. The resend preserves system/user content, packet
binding, seed, temperature, completion cap, and source slot; only its request/accounting identity is
new. No selection may use a response, parse, score, reward, latency, or gold.

The phase order is M0, then ground, then the 16 resends through one unchanged service session.
Before `start_session`, the launcher writes and hashes one flight plan containing the three concrete
attempt ids derived from the UTC flight stamp (`groundm0`, `groundg1`, and `groundresend`). A partial
failure seals every available trace and accounting record, aborts every still-opened attempt, stops
the service, and ends without recontacting any row. Recovery requires a prospective amendment.

For every selected ground source, the launcher canonicalizes the complete traced payload except
`request_id` as sorted ASCII JSON and records its SHA-256 and source slot. The normalized surface
contains carrier/sample/media facts, task instruction, history, decoding including `id_slot`,
evidence/provenance, speech-feature descriptors and packet hash, query source, key/matcher ids, and
the mmproj flag. Before each resend, the reconstructed intended payload must equal the source hash;
after contact, the actual traced resend must equal it again. Only request/accounting identity may
differ.

## Qualification gates

The basic ground passes only if all conditions hold on the complete 104-row ground manifest:

- at least 103 parseable responses;
- at least 94 exact matches (90.38%);
- at least 99 tool-correct rows (95.19%);
- slot micro-F1 at least 0.90;
- at least +15 exact and +15 tool-correct rows over same-flight M0;
- the query-grouped paired exact-gain 90% interval has a strictly positive lower bound. This is a
  percentile bootstrap with 10,000 replicates, seed 20260902, and NumPy linear 0.05/0.95
  quantiles. Each replicate samples frozen `query_block` identities with replacement, includes
  every paired row in each sampled block, and takes the sample-weighted mean ground-minus-M0 exact
  delta;
- all 16 resends parse, at least 15/16 source/resend pairs have equal parsed call multisets, and at
  least 15/16 have the same exact-correct outcome.

The stronger target is at least 99/104 exact (95.19%) and is reported separately. It cannot replace
or relax any basic condition. Per-tier metrics are descriptive only and cannot tune the handbook or
gate. The same frozen official scorer and exact parser own both complete-manifest results.

## Execution, scoring, and efficiency

Expected contact is 104 M0 + 104 ground + 16 resend = 224. The structured run-level plan reserves
230 calls, 1,300 metered speech-audio seconds, 0.7 GPU hours, and zero paid API, embedding, or
tokenizer contacts. The receipt-pinned Qwen3-Omni core remains the only answer authority.

Both 104-row model surfaces and the 16-row resend trace must seal before gold opens. Then two outer
workers run two unchanged official single-process finalizers concurrently, one per complete 104-row
manifest. There is no dataset shard, shard score, or shard-average metric. The batch reports wall
time, summed job time, effective speedup, worker count, manifest count, and result hashes. The fixed
16-pair stability read runs only after both official jobs settle.

Each finalized manifest is reverified as `FINALIZED`; analysis reads only its manifest-bound scores
artifact. The per-sample id set must equal the frozen 104 ids, and derived parse/exact/tool counts
must cross-check the official aggregate rates and slot micro totals. A parsed empty call means the
unchanged parser returned `parsed=true` and zero calls; parse failures remain separate. Resend
semantic agreement requires both texts to parse and scorer-v1 exact call-multiset equality by
calling `score_item(source_calls, resend_calls)`. Source exact outcome comes from the finalized
ground row; resend exact outcome uses the unchanged gold loader and item scorer only after both
finalizers complete.

Network jitter, packet loss, latency injection, retry stress, and failure-throughput testing are not
engineering gates and are not measured.

## Terminal consequence

If the basic ground passes, freeze it and open only a separately preregistered next approximately-
104 experiment on AgentLoop information gain and candidate reduction while preserving training-free
RL as a distinct later contribution. This qualification alone is not an agent-over-one-call claim.

If it fails, candidate pruning, training-free control, approximately-1,000 scale, and baseline lock
remain closed. A model-free error analysis must separate observation, knowledge coverage, knowledge
execution, value grounding, and output-format channels and decide whether broader knowledge
construction could make the task reachable. No threshold, handbook, prompt, sample, or result may be
tuned on this cohort. Test, Stage-3, and paper-scale work remain closed in every outcome.
