# A2T-CPV2-104 speech-packet preprocessing — preregistration

Date: 2026-09-01. Status: **EXECUTED SUCCESSFULLY; MAIN V2 PREFLIGHT UNLOCKED**.
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

## Execution closure

The one-shot pass completed as attempt `attempt-20260901T220601Z-a2tcpv2pre`. All 104 contacts
succeeded with zero failures, accounting for 536.05 speech-audio seconds, 10,855 prompt tokens,
104 completion tokens, and 204.858 seconds of summed decode latency. The CPU-only sidecar stopped
normally after `SIGTERM`; no forced stop was needed, and the GPU decoder was unreachable both
before and after the pass. No response was read semantically, and no gold, scorer, test annotation,
network service, paid API, embedding tool, or tokenizer tool was opened.

The promoted packet receipt is
`/home/chao/feat-cache/a2t-q4km-packets-04ccc72a/A2T-CPV2-104-promotion.json`, SHA-256
`a9ae338fbc9ba4734553b97a417403923aa6e085d3bd4446848a2abff3b65c87`. It contains exactly 104
packets built by llama.cpp commit `04ccc72a2207347ca76161b93fd9d846dd0a8675`; every packet hash
matches the promotion receipt and every audio hash matches the subset receipt. The transport trace
manifest SHA-256 is `99236b594568e2cff8ecc380d37ac4fac230866ddbb5ba6737c71c626636aba4`.
The repository copy of the execution report has SHA-256
`f0c7cbcf54753e8d48fe1924cb3dde50152bef3a3bb220dacc9854baa9c1ad25`.

This closes the preprocessing run. Its sole consequence is permission to execute the main v2
zero-contact preflight after the implementation and bindings land on a clean commit.
