# Audio2Tool G6 exhaustive-family-sweep fixed16 v1 preregistration

Date: 2026-09-02. Status: **PREREGISTERED; NO CONTACT AUTHORIZATION**.
Experiment: `SAEA-A2T-G6-EXHAUSTIVE-FAMILY-SWEEP-FIXED16-V1`. Execution profile:
`bounded-discovery-probe`. This is a Stage-2 prospective 16-row bounded discovery ground
screen, not confirmation, scale, pruning, training-free reward-guided control, test evaluation,
or paper work.

## Frozen population and paired comparator

The identity-only receipt is `docs/receipts/a2t/A2T-G6-FAMILY-SWEEP-FIXED16.json`,
SHA-256 `fcc8350312710b6a5831185e265a3b92fe619279acd0924da7b83268b07ff25b`.
It fixes exactly two rows in each of eight tiers, sixteen rows total. Its carrier-prefixed
manifest split identity is
`a99a64f004534516399c520c742132dc31d5c06cab5e59240653ff586a60fcb5`.
VerifiedSplit, the structured ExecutionPlan, protocol hashing, and manifest verification must
use that exact identity, not the receipt selection identity.

The frozen G1 M0 comparator is reused only after this roster is frozen, by identity filtering its
sealed results. It receives zero new model contacts. G3, G4, G5, fresh88, test, future turns,
training-free-RL evaluation surfaces, and the unexposed population remain closed.

## Design and frozen evidence

The design authority is commit `bf14b8bba9e1d100e7864b5ca856b29a6b558c76`, documented in
`docs/checks/speech-aware-evidence-acquisition/2026-09-02-a2t-g6-exhaustive-family-sweep-design/design.md`.
G6 keeps the frozen G5 contract corpus byte-for-byte:
`knowledge/audio2tool/g5-exhaustive-family-contracts-v1/corpus.json`, SHA-256
`92684a16e39985d3c4c6e7e6d62ac54feaa357eaa7c24c744df21950e51f95e5`.

The same frozen Qwen3-Omni Q4_K_M core is used only through the receipt-pinned local llama.cpp
API-shaped boundary. It is served with the `np2` Audio2Tool profile: 32,768 context tokens per
slot, two slots, at most two concurrent requests, and queue depth four. Temperature is zero.

## Fixed 29-contact AgentLoop

Each row has exactly 29 model contacts: 28 independent FAMILY SCAN contacts followed by one
dependent RESOLVE contact, for exactly 464 contacts across 16 rows. Every scan receives original
speech plus exactly one complete frozen family bundle. It may produce only a compact bounded
ASCII applicability report. Invalid scans seal as an empty report for that family only. No retry,
repair, resend, jitter test, or cumulative raw-history append is allowed.

RESOLVE occurs only after all 28 scan reports seal. It receives original speech, all bounded
reports, and only contracts nominated by their own valid reports. It is the sole final-answer
authority. Values must be bound to speech evidence or an explicitly permitted construction
canonicalizer; unspoken optional and default fields are omitted. OBS, ORG, SUPPLY, and USE traces
are emitted separately.

Before every contact, the exact rendered request must be measured, including structured state,
visible knowledge, speech-feature tokens, control framing, special-token reserve, and completion
reserve. Each request must fit 32,768 tokens with at least 8,192 tokens of headroom. Scan output
is capped at 512 completion tokens and RESOLVE at 1,024. A prompt that does not fit is refused
before contact; no silent truncation or completion reduction is allowed.

The selected one-pass audio duration is 87.001 seconds. The repeated speech-audio cap is 2,600
seconds. There are no embedding or tokenizer contacts and paid API spend is zero.

## Scoring, gates, and stop rule

Gold and the unchanged official Audio2Tool scorer remain closed until the complete 16-row final
manifest and all contact/trace manifests seal. The official scorer runs once, whole-manifest, in a
single process. Dataset sharding and averaged shard metrics are forbidden.

The fixed16 gate requires all of: parse at least 15/16, exact at least 15/16, correct tool set
16/16, slot micro-F1 at least 0.90, and at least one exact row in every tier. It also requires
zero out-of-registry tool names, illegal argument-key sets, inventory enumeration, parser repairs,
retries, silent truncations, and synthetic/default task-value copies. Structural checks do not
substitute for the official exact gate.

If any gate fails, do not recontact rows or open 40, 100, or 1,000 rows; do not prune, fit
training-free reward-guided control, or contact fresh88 or test. A sealed mediator analysis may
choose only a construction-only successor on a new identity-only roster. If every gate passes,
freeze the corpus, scan schema, resolver, runtime budget, and decoding settings; then a separately
preregistered disjoint 40-row discovery support gate may be proposed. A 100-row experiment remains
closed until a stable disjoint-40 result at or above 90% exact. A 1,000-row scale is not authorized.

## Contact closure

This preregistration and its baseline/experiment fragments do not authorize a model, network,
gold, scorer, tokenizer, retriever-service, reference-transcript, task-output, score, reward,
test-annotation, or future-turn contact. Before the first model contact, a dedicated launcher must
bind the frozen roster, runtime receipt, exact SCAN prompt-fit receipt, ExecutionPlan, protocol
hash, complete-manifest procedure, and exposure-ledger registration. A RESOLVE request does not
exist until its 28 actual reports seal, so the launcher must measure and record that exact request
after the seal and before the row's sole RESOLVE contact. No precondition may open protected
information.
