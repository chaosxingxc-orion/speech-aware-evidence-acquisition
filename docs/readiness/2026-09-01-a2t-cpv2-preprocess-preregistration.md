# A2T-CPV2-104 speech-packet preprocessing — preregistration

Date: 2026-09-01. Status: **REGISTERED; CONTACT CLOSED UNTIL COMMITTED CLEAN**.
Run: `SAEA-SN-A2T-CPV2-PREPROCESS`. Composed config and protocol SHA-256:
`800f66aa970384889131e77ac79bf47d0da647ced874f2fa4db991b3c210e4d5`.

## Purpose and fixed population

The main contract-preserving cascade uses a receipt-pinned decoder without an
audio encoder. Its new `A2T-CPV2-104` cohort therefore needs one audited speech-feature packet per
recording before inference. A label-free audit found zero current-build legacy cache entries and
zero existing packets for these 104 identities. The input receipt is
`docs/receipts/a2t/A2T-CPV2-104.json`, SHA-256
`8f47922124c61f92fee03273c1165eb1f8f97048d910ddd4a6a7243906d78783`, run identity
`401a28684adea908c80363df0815c9ce04b0ffa46a654975b129d4b69e60f8a1`, with 104 items and
536.05 speech-audio seconds. No other identity is loadable.

## One-shot procedure

The existing audited preprocessing entry point runs under the explicit `--cpv2` profile. A
CPU-only llama.cpp sidecar on loopback port 8081 uses the receipt-pinned preprocessing runtime,
`-ngl 0`, and `--no-mmproj-offload`. Each recording receives the same minimal English instruction
and a one-token completion cap. The instruction contains no tool registry, query text, label,
reference transcript, expected call, prior output, score, test annotation, or future turn. Model
response meaning is never read. The sidecar writes a build-scoped legacy cache, stops, and only
then the carrier-neutral promotion primitive writes packet files and an exclusive-create promotion
receipt at `/home/chao/feat-cache/a2t-q4km-packets-04ccc72a/A2T-CPV2-104-promotion.json`.

The GPU decoder on port 8090 is not started, stopped, reconfigured, or used for an inference
request. Its loopback reachability is observed before and after solely to prove the CPU pass did not
change its service state.

## Bounds and terminal rule

The structured `ExecutionPlan` binds the discovery role, exact run identity, config/protocol hash,
and a ceiling of 120 contacts, 650 speech-audio seconds, 0.2 declared GPU hours, and zero paid API
spend. The intended use is exactly 104 contacts and 536.05 audio seconds. The output is engineering
infrastructure, not a task result, and authorizes no scorer or gold read.

On any failed contact, partial cache, identity drift, hash drift, wrong runtime, response-accounting
drift, or incomplete promotion, the pass stops and refuses a promotion receipt. It is not retried or
repaired without a new prospective registration. A successful receipt authorizes only the still-
closed main v2 preflight; it does not itself authorize the main model flight, support, scale, test,
Stage-3, or paper-scale work.
