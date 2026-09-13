# SLURP native-role GPU proof readiness

This is a configuration-only, bounded engineering proof for the merged shared `FlightRuntime` and OpenJiuwen native-role path. It defines a new mechanism identity, `SAEA-SLURP-NATIVE-ROLE-GPU-PROOF-V1`; it does not change, recover, or replay the immutable 2026-09-12/13 native-tools attempts.

The sole population is the already exposed four-row TRAIN engineering roster from `slurp-native-tools-engineering-4-v1`. Its prepared speech packets and the governing dataset lock remain the source of the current-speech input. No new roster is drawn. The proof is engineering evidence only and makes no effectiveness, scoring, or knowledge-value claim.

## Composed proof

The prospective fragments are model `q4km-mmproj-free-slurp-native-role-gpu-proof-np8-max256-v1`, dataset `slurp-native-tools-engineering-4-v1`, baseline `slurp-native-role-gpu-proof-v1`, and experiment `slurp-native-role-gpu-proof-v1`.

Their current pre-release composed configuration hash is `076757ae208544e15d9bd8bcef643b4445574e4d51ef4ee77aec3c8d6d7b6433`. Releasing the separate named stores intentionally changes that hash; root must recompute it before registration.

The model geometry is one decoder-only `--no-mmproj` service, derived by the inference lifecycle from the pinned runtime receipt, with `-c 65536` and `-np 8`: eight 8192-token slots. The fragment does not name an mmproj argument because the lifecycle injects `--no-mmproj` and refuses mmproj arguments on an inference service. The completion ceiling is 256 tokens.

The registered policy is `phase-native-review-revise-v1`. Its graph ceiling is exactly 11 contacts per sample: Perception 1, then up to two rounds of Solver 1, Reviewer 3, and Planner 1. `max_revisions` is one. The prospective dynamic capacity gate therefore reserves `4 * 11 * (1 + 3) = 176` tokenizer endpoints. It fits actual rendered requests one at a time and does not claim capacity for unvisited branches.

Perception and Solver have no native tool scope. Reviewer and Planner alone expose the same pinned `saea-tool-task-contract-v1` schema, each with exact `source_authority_role` matching its phase. The framework permits one analytical action per native role contact; Reviewer can receive at most three model contacts in a round and Planner at most one. No configuration field currently limits a named-store selection count. The future named-store provider must therefore declare and pin its own bounded selection policy before release; it must return selected evidence only, never the full 60-card intent set or the full 54-card slot set.

The primary acceptance condition is not a forced or static preprocessing branch. At least one Reviewer task-contract call must be proposed by the frozen core through its native function schema, have a counted source-bound tool receipt, and appear in the subsequent role history. The episode must then seal an accepted Solver response by the Solver request identity. A missing Reviewer call, a tool call from another role, an invented tool result, or a Planner answer is a failed proof observation and is not retried under this identity.

## Knowledge status

The present baseline intentionally has no `knowledge_stores` binding and no phase-knowledge action. It retains the existing immutable snapshot only for the shared runtime binding; no knowledge values from that snapshot are supplied to a role. Root authoring of the separate intent and slot stores is in progress.

The slot construction source is now available at `prepared/SAEA-SLURP-SEMANTIC-AUTHORING-PREPARE-V1/authored-slot-contracts-v1.json` with SHA-256 `34f6c3dc192eca4a30ef7208d10c1e2b797a0ae2ffe5122f16b376e10a30e4c5`. It contains 54 values, 402 observed intent bindings, and 803 reviewed support utterances. The intent v2 source SHA-256 is `1950c4a3a8bed73d0cf810c10a9f32d42b683b3d317cdc24634366faa0808fb1`; its data-root-relative path remains an explicit unresolved binding. Neither source is a released store or a runtime input yet.

Before registration, root must supply separately for the intent and slot stores: the store ID and role, construction-source path and SHA-256, snapshot path and SHA-256, release path and SHA-256, provider/fusion policy, and an explicit cardinality limit that preserves discriminative or explanatory value. Observed intent/type bindings may support supply indexing, but are not a required-slot or legal-type whitelist. The original full intent and entity-type inventories remain authoritative.

## Prospective plan skeleton

The following fields are deliberately unresolved and must not be filled with placeholder hashes. They become the protocol and plan identity only after root review:

```json
{
  "schema": "saea-native-role-gpu-proof-prospective-plan-v1",
  "generation": {
    "run_id": "SAEA-SLURP-NATIVE-ROLE-GPU-PROOF-V1",
    "attempt_id": "attempt-slurp-native-role-gpu-proof-generation-v1",
    "execution_profile": "bounded-discovery-probe",
    "split_role": "discovery",
    "split_identity_hash": "4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb",
    "planned_model_calls": 44,
    "planned_speech_audio_seconds": 116.5511875,
    "protocol_hash": null,
    "exposure_pre_registration_binding": null
  },
  "native_contact_fit": {
    "run_id": "SAEA-SLURP-NATIVE-ROLE-GPU-PROOF-FIT-V1",
    "attempt_id": "attempt-slurp-native-role-gpu-proof-fit-v1",
    "contact_cap": 176,
    "max_speech_packets": 1,
    "protocol_hash": null,
    "exposure_pre_registration_binding": null
  },
  "root_owned_service": {
    "session_id": "serving-slurp-native-role-gpu-proof-np8-v1",
    "runtime_receipt_sha256": null,
    "llama_cpp_build_commit": null,
    "decoder_gguf_sha256": null,
    "service_receipt_sha256": null
  },
  "named_knowledge_stores": {
    "intent": {"source_relpath": null, "source_sha256": "1950c4a3a8bed73d0cf810c10a9f32d42b683b3d317cdc24634366faa0808fb1", "snapshot": null, "release": null, "selection_policy": null},
    "slot": {"source_relpath": "prepared/SAEA-SLURP-SEMANTIC-AUTHORING-PREPARE-V1/authored-slot-contracts-v1.json", "source_sha256": "34f6c3dc192eca4a30ef7208d10c1e2b797a0ae2ffe5122f16b376e10a30e4c5", "snapshot": null, "release": null, "selection_policy": null}
  }
}
```

## Launch-readiness checklist

1. Root reviews the four role prompts in `configs/probes/slurp_native_role_*.txt` and the held experiment cell. Confirm that Reviewer tool use remains model-proposed and Solver alone remains final-answer authority.
2. Root releases separately pinned intent and slot stores. Review each source, snapshot, and release hash and the provider's bounded selection policy. Do not activate a broad card dump or turn observed co-occurrence into a constraint.
3. Root updates the baseline to add the released named-store bindings and the corresponding Reviewer/Planner phase-knowledge scopes only if the proposed source semantics have passed review. Recompute the composed and protocol hashes after that final configuration change.
4. Root writes a prospective exposure-ledger row for the native contact-fit run, the generation run, and the possible Reviewer/Planner task-contract action before their results are read. Bind the exact execution plans, roster hash, protocol hash, and one-shot attempt semantics.
5. Root records the fresh WSL boot identity, the llama.cpp build commit, and every decoder GGUF SHA-256 in a new runtime receipt. Confirm that the prepared four speech packets still match the packet-promotion receipt and the governing lock.
6. Root starts and owns exactly one new decoder-only session named `serving-slurp-native-role-gpu-proof-np8-v1`. Verify the service receipt has `--no-mmproj`, `-c 65536`, `-np 8`, and the expected 8-by-8192 geometry. Workers must attach; they must not start, replace, or recover a service.
7. Root runs the exact native dynamic fit plan under the service lease. Preserve every fit journal. A failed fit or contacted identity is not reused.
8. Root starts the registered generation plan only after fit succeeds. Preserve raw responses, role visits, planner routes, tool provenance, and canonical Solver sealing. Do not force a tool call, retry a no-tool outcome, or interpret the four-row proof as an effectiveness result.
9. Root verifies the acceptance condition: at least one model-proposed Reviewer task-contract call with source authority and a sealed accepted Solver output. Defer score reading and any follow-on comparison to separately authorized work.

No service is started, no request is fitted or generated, and no tool, tokenizer, model, scorer, or GPU contact is made by this preparation.
