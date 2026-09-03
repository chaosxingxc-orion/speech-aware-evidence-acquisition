# Audio2Tool SELECT/FILL 104-Row Flight — Recovery V2 Preregistration

Status: **REGISTERED BEFORE ANY RECOVERY-V2 MODEL, EMBEDDING, TEMPLATE, TOKENIZER, SCORER, OR GOLD CONTACT**  
Generation run: `SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V2`  
Embedding-tool run: `SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V2-EMBED`

## Source attempt and exact failure boundary

The V1 mission reached the complete M0 live template/tokenizer preflight and then stopped before its
first physical generation send. `generation-send-accounting.jsonl` was never created, no request
reached the llama.cpp chat endpoint, no model response exists, and no response meaning, gold, scorer,
test annotation, or future turn was opened. Four concurrent V1 direct workers were conservatively
recorded by `FrozenCoreAdapter` before the transport wrapper rejected their bodies, so the V1 direct
attempt is terminal `ABORTED` with four accounting calls and 8.567208 accounting audio seconds. Every
other V1 generation and embedding attempt remained unopened.

The failure was a deterministic local serialization mismatch. The preflight allowlist rendered
stdlib JSON before the adapter boundary, while the adapter first canonicalized and decoded its full
payload. That round trip sorted decoding, response-schema, and speech-descriptor keys before
`LlamaServerTransport` emitted its insertion-ordered stdlib JSON body. The first four concurrent
bodies were therefore semantically identical to, but byte-distinct from, the allowlist and were
rejected before I/O. The V1 mission failure-receipt SHA-256 is
`cee4ab67d38ad7a61b946c26689c55d9a36ad198838f2809fe12d4300096e29e`; its contact-authority SHA-256
is `fc6ec7d0b1baa96ccc4c16cfa21d10ce8f3fdfdf338c3a8e11c2bafa4e3c78f1`.

Recovery V2 never reuses a V1 attempt, mission, or run identity. The V1 accounting records and
failure artifacts remain immutable.

## Frozen scientific design

Recovery V2 preserves the registered 104-row roster, speech packets, K=32 retrieval ground, model,
embedding model, six phases, four answer arms, prompts, response schemas, context cap, two generation
slots, queue depth four, four embedding batches, phase barriers, official scorer, analysis, and
promotion rule from
`docs/readiness/2026-09-03-a2t-select-fill-agentloop-104-v1-preregistration.md` byte-for-byte. It makes
no scientific change and still compares direct M0, one-call JOINT, equal-contact JOINT draft/revise,
and separate SELECT then FILL on exactly 104 fresh discovery rows.

The only implementation change reproduces the adapter's canonical payload round trip before hashing
the exact physical slot bodies. The regression test constructs that round trip independently and
requires byte equality with the admitted body. Implementation commit
`b10e96d4ef17f2e96e4113492c97cfd73111df56` carries coordinator SHA-256
`d3cf96f9050867187b7565b60d174563831b58538caa0fbba644e992667bdb30` and runtime-factory SHA-256
`6677185342153205a3e99c33873b21667004680e91edd518ab6a07a0be024990`. The model-free focused suite
passes 117 tests; the launcher/runtime subset passes 24 tests and Ruff passes.

## Recovery identities and budgets

Use mission `mission-20260903t233000z-selectfill104-recovery-v2` and six unique generation attempts
with prefix `attempt-20260903t233000z-selectfill104-` plus suffixes `direct-v2`, `obs-v2`, `joint-v2`,
`select-v2`, `revise-v2`, and `fill-v2`. Use embedding attempt
`attempt-20260903t233000z-selectfill104-embedding-v2`. All are verified absent before registration.

Recovery V2 authorizes exactly 624 new frozen-core contacts, 3,400 conservative speech-audio seconds,
and 4.0 GPU hours across the generation run. It separately authorizes 104 logical transcript
embeddings in exactly four physical requests, one schema-required conservative audio second, and 0.2
GPU hours. No retry, repair, resend, fallback, response substitution, network-jitter study, test use,
training-free RL fit, approximately-1,000-row expansion, Stage-3 work, or paper claim is authorized.

All 104 exact physical requests in a phase must pass the live template, schema-to-grammar, tokenizer,
packet-token, and 24,576-token admission checks before that phase sends once. All four answer manifests
must seal before response meaning, gold, or official scoring opens. The four complete manifests are
then scored by four outer workers, each invoking the unchanged official single-process scorer once;
no manifest is sharded and no shard metrics are averaged.
