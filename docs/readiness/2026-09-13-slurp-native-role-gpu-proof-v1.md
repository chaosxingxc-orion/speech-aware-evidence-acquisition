# SLURP native-role GPU proof readiness

This is a configuration-only, bounded engineering proof for the merged shared `FlightRuntime` and OpenJiuwen native-role path. It defines the new mechanism identity `SAEA-SLURP-NATIVE-ROLE-GPU-PROOF-V1`; it does not change, recover, or replay the immutable 2026-09-12/13 native-tools attempts.

The sole population is the already exposed four-row TRAIN engineering roster from `slurp-native-tools-engineering-4-v1`. Its prepared speech packets and governing dataset lock remain the current-speech input. No new roster is drawn. This proof is engineering evidence only: it does not score task quality, knowledge effectiveness, selective-tool benefit, or autonomous tool-trigger quality.

## Composed proof

The prospective fragments are model `q4km-mmproj-free-slurp-native-role-gpu-proof-np8-max256-v1`, dataset `slurp-native-tools-engineering-4-v1`, baseline `slurp-native-role-gpu-proof-v1`, and experiment `slurp-native-role-gpu-proof-v1`. Their composed configuration hash is `cb814a959eaa044f39f7d8147c4f3f6f1ebc4f3a6142a386cda85c5308cf5dcd`; the shared runtime derives execution-plan protocol hash `c2c26d0e73e26c9144ab745e045732d9220843099a59e543c874d31bb6c4fbdc` from that configuration, arm, and split identity.

The model geometry is one decoder-only service. The lifecycle derives `--no-mmproj` from the pinned inference receipt and rejects an mmproj argument in the fragment. The exact geometry is `-c 65536` and `-np 8`, or eight 8192-token slots, with a 256-token completion ceiling.

The registered `phase-native-review-revise-v1` graph has an 11-contact maximum per sample: Perception 1, then at most two rounds of Solver 1, Reviewer 3, and Planner 1. `max_revisions` is one. The shared dynamic capacity gate operates inside generation before every realized request, so its ceiling is `4 * 11 * (1 speech packet + 3 tokenizer endpoints) = 176`. It is not a standalone pre-run phase.

Perception receives no tool. It must emit one to three distinct legal intent identifiers using the existing compact shared hypothesis object: each candidate has only `intent_id`, `distinction`, `evidence_refs`, and `unresolved_fields`; candidate confidence, probability, score, and rank are not legal fields. Solver receives no tool and is the sole final-answer authority. Reviewer alone has the pinned `saea-tool-task-contract-v1` native scope. Its prompt directs it to call that tool exactly once per review, then review the Solver draft and return findings. The frozen core must originate the function call; the harness does not inject one. Planner has no phase-tool entry in this proof because its one-contact bound cannot complete a tool/result cycle. The shared framework continues to support future Planner tool scopes.

The primary acceptance condition is a model-originated, source-bound Reviewer task-contract receipt followed by an accepted Solver response sealed by Solver request identity. A missing Reviewer call, a call from another role, an invented tool result, or a Planner final answer is a failed observation under this identity and is not retried.

## Knowledge status

This task-contract-only proof binds no `knowledge_stores`, phase-knowledge action, intent card, or slot card. The separately authored sources remain outside its runtime inputs and are not a release dependency. This deliberately keeps knowledge effectiveness and selective-tool benefit out of the proof.

For later separately reviewed work, the held slot construction source is `prepared/SAEA-SLURP-SEMANTIC-AUTHORING-PREPARE-V1/authored-slot-contracts-v1.json`, SHA-256 `34f6c3dc192eca4a30ef7208d10c1e2b797a0ae2ffe5122f16b376e10a30e4c5`; it contains 54 values, 402 observed intent bindings, and 803 reviewed support utterances. The intent v2 source SHA-256 is `1950c4a3a8bed73d0cf810c10a9f32d42b683b3d317cdc24634366faa0808fb1`. Neither is read, supplied, or assessed here. Observed bindings remain indexing evidence only; the original full intent and entity-type inventories stay authoritative.

## Concrete prospective bindings

The root-reviewable protocol is [`protocol-v1.json`](2026-09-13-slurp-native-role-gpu-proof-v1/protocol-v1.json), file SHA-256 `9054277e5a01b779a841e948717371b1514e10f677016c7169e75f39dd49f5ab`. It binds the configuration, fixed roster, role limits, reviewer-only tool scope, dynamic-fit cap, runtime receipt, and new serving-session identity. Its file SHA is custody metadata; the distinct shared runtime execution-plan protocol hash is `c2c26d0e73e26c9144ab745e045732d9220843099a59e543c874d31bb6c4fbdc`.

The concrete structured plans are [`generation-plan-v1.json`](2026-09-13-slurp-native-role-gpu-proof-v1/generation-plan-v1.json) for the 44-call generation ceiling and [`dynamic-fit-plan-v1.json`](2026-09-13-slurp-native-role-gpu-proof-v1/dynamic-fit-plan-v1.json) for the 176-endpoint native gate. The latter is a registration identity for capacity endpoints; it does not authorize a separate fit invocation.

The shared public-entry sequence and prospective exposure rows are in [`launch-recipe-v1.md`](2026-09-13-slurp-native-role-gpu-proof-v1/launch-recipe-v1.md). It uses `scripts/serving_session.sh start`, `core.flight.lease_cli`, and `core.flight.cli worker`; it does not use `coordinate-fit`.

## Launch-readiness checklist

1. Root reviews the four role prompts and the held experiment cell. Confirm the compact Perception schema, Reviewer-only task-contract scope, model-originated call requirement, and Solver-only final authority.
2. Root verifies the existing immutable runtime receipt, build commit, and decoder GGUF hash. Do not regenerate E0 for the WSL boot change.
3. Root creates and records one new root-owned serving-process/session receipt for `serving-slurp-native-role-gpu-proof-np8-v1`. Verify its lifecycle-injected `--no-mmproj`, `-c 65536`, `-np 8`, and 8-by-8192 geometry. Workers attach only.
4. Root reviews and registers the prospective exposure-ledger rows before reading any result, binding the two exact execution-plan files, protocol hash, fixed roster hash, session identity, and one-shot attempt semantics.
5. Root makes the held cell ready under the reviewed registration and launches only the public shared sequence in the launch recipe. The dynamic gate fits each realized request within generation; do not issue a standalone fit command.
6. Preserve request-fit journals, role histories, source-bound tool receipts, and the Solver seal. Do not force a tool call, retry a no-tool outcome, read a scorer, or infer task or knowledge quality from four rows.

No service is started, and no tokenizer, model, tool, scorer, GPU, or speech-data contact is made by this preparation.

## Root admission

The clean successor configuration is READY for the registered public worker only. Protocol v2 and generation/dynamic-fit plan v2 supersede the unexecuted pre-admission v1 documents. Runtime protocol 09d526c6afb5eef77f088d0f2d5cd4c59d926e1b81b00c6502e1e223b43b9774 derives from composed configuration baf5904f45f6fc20df44d61535058791e82c9eb6709a10243146cd2e6bea5c37; protocol document file SHA-256 is 60f54f7d1b852d79f70ee8b19a797da2991f1f1f9135c393dad68d48e5a1966c. These are different identities. All four role prompt bytes are pinned in protocol v2. Final exposure rows are committed in the shared ledger before service or request contact. The root-owned decoder service and monitor use the new session ID. No task-quality score is authorized by this engineering proof.
