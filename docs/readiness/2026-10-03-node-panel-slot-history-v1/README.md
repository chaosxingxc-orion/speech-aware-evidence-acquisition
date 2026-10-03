# Source-bound slot history for the scheduling comparison

This offline extension measures whether uninterrupted node-stage execution retains more usable prefix state on the actual llama.cpp slots. Each node keeps its independent context. The registered sixteen-member schedule comparison and its frozen worker remain unchanged.

The primary question remains business quality and original sample wall time, including the separately reported first and non-first samples. Better cache reuse alone does not establish an end-to-end gain. Summed concurrent contact timers are not exclusive GPU time; generation makespan divided by samples is throughput, not individual latency.

## Measurement contract

- Reuse the complete-family numeric reader, its exact root READ countersignature, all-member operational preflight, original verified seals and unique official scoring records.
- Supply a finite, hash-pinned copy of the original serving log only after the complete-family read qualifies. The log remains outside Git, under the data root. Never operate the service to obtain a preferred cache state.
- Join each original model contact using both evaluated-input/generated-token counts and both prefill/decode timers. The pinned server prints timers to two decimal places; permit at most 0.0051 milliseconds of rounding difference. Require exactly one match without using the requested slot to disambiguate it.
- Verify actual assignment against any explicit requested slot. Reject missing, ambiguous, reused, truncated, conflicting or overlapping task custody. Keep independent run/request identities; local request IDs can repeat across owners.
- Order predecessors using actual server start lines within each slot. Preserve intervening outside-family tasks and snapshot boundaries instead of skipping them.
- Separate same-node/context changed-input calls, same-node/context repeated-input calls, changed context within a node, and cross-node transitions with same/different inputs. Report exact request-body equality separately. Neither role identity nor text hashes prove identical full token prefixes.
- Preserve measured reuse, evaluated input, prefill, decoding and client transport independently. Missing optional values remain unknown. Retain only line numbers for pressure/purge/context-shift terms within the contact scope; absence is not proof that eviction is impossible.
- Recheck source pins and READ authority before writing any fresh report. Export neither optimizer feedback nor raw server-log text.

The reader accepts an optional finite log via `--server-log` and `--server-log-sha256`; both must be supplied together. Without them, the preceding numeric reader behavior is retained. This is a descriptive diagnostic extension, not a new experiment, scoring invocation, data exposure or scientific adoption criterion.

## Verification

The selected analysis and reader suite passes 200 tests. The slot-history module has 100% statement coverage. CLI tests cover unsigned READ refusal before any server log/result source, complete-member orchestration, source mutation refusal, log confinement and explicit hash pairing. Lint, engineering-base and harness-admission checks pass.

A read-only rehearsal reproduces all 53 original task/slot joins from the already accepted eight-row structural proof. The rehearsal uses synthetic context-identity placeholders solely to exercise the numeric join; it does not produce new context-category, quality or speed conclusions. Its first comparison accidentally indexed local request IDs without owner IDs and raised before output. The library already retained owner/request pairs; the corrected rehearsal compares those exact pairs. Preserve that model-free caller correction in the evidence.

The actual sixteen-member experiment is still running. Its READ remains unsigned, its quality unread, and its frozen runtime immutable. This implementation does not establish a benefit. Root only; learning remains held, the heartbeat paused, and owner review remains required before 8x400.
