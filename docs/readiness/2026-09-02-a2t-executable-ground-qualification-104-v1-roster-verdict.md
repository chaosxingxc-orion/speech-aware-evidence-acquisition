# A2T Executable Ground Qualification 104 V1 Roster Verdict

## Decision

The identity-only roster gate passes. Freeze `A2T-GROUND-QUAL-104` as the only roster for executable-
ground qualification V1. Permit only separately preregistered label-free packet preprocessing and
qualification implementation. No task model contact is authorized by this result alone.

## Result

The deterministic selector removed all 208 G1 and CPV2 sample/query blocks from the exposed parent
400, leaving 192 eligible blocks. It selected 13 blocks in each of eight tiers, for 104 unique
samples and 104 unique tier-scoped query blocks. The selected roster has zero sample or query-block
overlap with either predecessor. Eighty-eight exposed-parent blocks remain unused.

The selected audio totals 543.107 seconds; individual durations range from 0.617 to 35.714 seconds.
Every selected media path, manifest duration, WAV header, and audio SHA-256 was verified through the
runtime-legal loader. Reversing the parent and both excluded inputs produced the same selected
objects, and reversing the selected roster and source order produced the same receipt object.

Receipt SHA-256:
`eeb90abbe8695e449c676f18339db6618cb6d606d6c1e7c656626e4e9b6b6c16`.
Split identity:
`c6bb080bb264733087b3da352fe930702ec6509bc02e6a639b0f4c30c5017dac`.
Run identity:
`fbd4addd541ff29214cbff7c35564b15f27e2fb7f438202b79d694b1c5961d4b`.
Roster result SHA-256:
`577184e7b189c2dba1471435e99a8a7ec873787b887af66824e6f68a7829c0c5`.

## Information boundary

The offline guard recorded zero outbound attempts. The selector and receipt accepted only sample
identity, tier, media path, duration, media SHA-256, query block, and deterministic rank. Query text,
expected calls, task annotations, prior outputs, prior scores, rewards, scorer inputs, and test
annotations were not read. There were zero frozen-core, tokenizer, retriever, embedding, HTTP/socket,
audio-decoder, scorer, and GPU contacts.

The proposed unexposed 400-item evaluation tier remains unopened and unchanged at identity
`4d0196ec91858cdc81340ee197c085ff29726a1f1b7fe9119d4e410d62df2f90`. The executable handbook's
construction partition already excludes every exposed-parent query block, so this child roster is
also construction-block-disjoint without consuming the proposed tier.

## Next gate

Packet preprocessing must use this receipt exclusively, keep response meaning unread, measure all
speech-feature token counts, and stop unless the maximum is at most the prompt-fit receipt's 455-token
reserve. Ground qualification then compares the same complete handbook under a direct single-call
path and a same-core OBS -> USE AgentLoop path. Both complete prediction manifests must seal before
the governed discovery labels open.

Candidate pruning and training-free control remain suspended until the primary AgentLoop ground
meets exact at least 0.90, tool at least 0.95, slot micro F1 at least 0.90, and parse at least 0.99;
exact 0.95 remains the target. No approximately-1,000 expansion, baseline change, test access,
Stage-3 claim, or paper-scale work is authorized.

## Engineering scope

Later scoring remains one unchanged official single-process operation per complete manifest, with
independent complete manifests eligible for outer parallel execution. Dataset sharding and
shard-score averaging remain forbidden. Network jitter, packet loss, latency injection, and retry
stress remain outside the engineering baseline.
