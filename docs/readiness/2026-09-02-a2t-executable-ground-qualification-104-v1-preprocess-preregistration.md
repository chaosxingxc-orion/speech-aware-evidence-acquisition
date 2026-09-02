# A2T executable-ground qualification 104 v1 preprocessing preregistration

Date: 2026-09-02. Status: **EXECUTED SUCCESSFULLY; PROMPT-FIT INHERITANCE STOPPED**.
Experiment id: `SAEA-SN-A2T-GROUND-QUAL-104-PREPROCESS`.
Composed config and protocol SHA-256:
`3845d4a8a601e3279a4656ccd0e1c9c92feed33236801758df528e43a7862ae4`.

## Purpose and fixed population

The executable-ground qualification decoder serves without an audio encoder. The roster-pinned
`A2T-GROUND-QUAL-104` population therefore needs one audited speech-feature packet per recording
before any task inference. The only population is
`docs/receipts/a2t/A2T-GROUND-QUAL-104.json`, SHA-256
`eeb90abbe8695e449c676f18339db6618cb6d606d6c1e7c656626e4e9b6b6c16`, run identity
`fbd4addd541ff29214cbff7c35564b15f27e2fb7f438202b79d694b1c5961d4b`, with 104 items and
543.107 speech-audio seconds. It is an identity-only selection from the already-exposed parent 400,
is query-block-disjoint from G1 and CPV2, and does not open the separately protected unexposed 400.

## One-shot procedure

The existing audited Audio2Tool preprocessing entry point gains an explicit `--ground-qual`
profile. A receipt-pinned CPU-only llama.cpp sidecar on loopback port 8081 uses `-ngl 0` and
`--no-mmproj-offload`. Each recording receives the same minimal English instruction and a one-token
completion cap. The instruction contains no registry, handbook, query text, label, reference
transcript, expected call, prior output, score, test annotation, or future turn. Response meaning is
never read. The sidecar writes the current-build legacy cache, stops, and only then the
carrier-neutral promotion primitive writes exclusive audited packets and
`/home/chao/feat-cache/a2t-q4km-packets-04ccc72a/A2T-GROUND-QUAL-104-promotion.json`.

The GPU decoder on port 8090 is not started, stopped, reconfigured, or contacted. The preflight may
observe only whether the two loopback ports are reachable so that the CPU sidecar cannot collide
with another process or change the decoder service state. Network jitter, packet loss, latency
injection, retry stress, and throughput-under-fault measurements are outside this engineering gate.

## Packet-size gate

After promotion, the run records the complete packet token-count distribution from packet metadata.
No packet is truncated, resampled, split, or selected by token count. The landed full-handbook
prompt-fit receipt may be inherited only when all 104 packets exist, every packet/audio/runtime hash
matches, and the measured maximum is at most 455 speech tokens. A maximum above 455 leaves the
packets valid but stops qualification until a separately registered successor recomputes the exact
prompt envelope with that measured maximum. This is a capacity gate, not a result-dependent change.

## Bounds and terminal rule

The structured `ExecutionPlan` binds discovery role, the exact run identity, composed
config/protocol hash, 120 contacts, 650 speech-audio seconds, 0.2 declared GPU hours, and zero paid
API spend. Intended use is exactly 104 contacts and 543.107 audio seconds. No gold, scorer, task
answer, retriever, embedding tool, tokenizer endpoint, external network, or test data may be opened.

Any failed contact, incomplete cache, identity drift, receipt drift, runtime drift, response-
accounting drift, or incomplete promotion stops without a successful receipt. No retry or partial
repair is permitted without a new prospective amendment. Passing authorizes only a separately
implemented and preregistered executable-ground qualification preflight. It does not authorize task
model contact, pruning, training-free control, approximately-1,000 scale, baseline change, test
access, Stage-3, or paper-scale work.

## Pre-contact closure

Implementation commit `c7cf45bc8f5e791fee6b6d6984017e9d5849ab14` passed 74 relevant tests; the
new token-accounting module reached 95% statement coverage, and the changed files passed Ruff. A
clean-tree zero-contact preflight resolved all 104 identities and 543.107 seconds, found 0/104
current-build cache entries, 0/104 packet manifests, no promotion receipt, free sidecar port 8081,
and no GPU decoder on port 8090. It opened no session and ran no frozen-core gate. Receipt:
`docs/checks/speech-aware-evidence-acquisition/2026-09-02-a2t-ground-qual-104-preprocess/preflight-receipt.json`,
SHA-256 `0316f5f309bf48cc2d56a715262660e23d2a177278584f3c8d235c1fbeab9b47`.

The registered one-shot preprocessing pass is now executable. No task-inference contact is opened by
this closure.

## Execution closure

Attempt `attempt-20260902T130411Z-a2tgroundqualpre` completed 104/104 contacts with zero failures and
543.107 speech-audio seconds. The CPU-only sidecar stopped normally, the GPU decoder received no
request, and exactly 104 packets were promoted. Promotion receipt SHA-256:
`b350567a6dd8b5d9021725756424f2b6ae99803c8c0327901c724fe3ebe8a47f`. Repository report SHA-256:
`c2120c9500ac943dc485d1953087965312e13f491ee850775df23347c4dccb0a`.

The complete-packet distribution is min 13, median 65, p90 143, p95 169, max 468, and sum 7,813.
Because 468 exceeds the inherited 455-token reserve by 13, preprocessing passes but qualification
remains closed. No packet is changed. Only a separately preregistered 468-token model-free prompt-fit
successor is opened.
