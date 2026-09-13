# SLURP native knowledge-consumption engineering proof v1

## Status

This is an **UNREADY draft**. It creates no exposure-ledger row, readiness admission, service, session, model request, tokenizer request, tool request, GPU request, or scorer request. Root review and registration are required before any contact-capable stage is admitted.

## Purpose and limits

The proposed four-row TRAIN proof exercises one engineering path:

1. Perception produces one to three distinct legal complete scenario_action intent IDs.
2. The named released slot-contracts store reads that source-bound Perception state.
3. Candidate supply materializes the complete associated union of released slot cards and attaches it before the initial Solver draft.
4. Reviewer inspects the Solver draft, Planner decides whether to accept or revise, and Solver retains final-answer authority.

If accepted, it demonstrates legal candidate consumption and full slot-card materialization. It does not assess task quality, knowledge quality or effectiveness, dual-store quality, selective-tool benefit, autonomous tool triggering, or revision effectiveness. The existing Reviewer-only native task-contract tool remains for engineering continuity; it is not an experimental factor.

## Fixed configuration

The policy is phase-native-candidates-review-revise-v1: Perception 1, Reviewer 3, Planner 1, Solver 1, with at most one revision and 11 contacts per realized row. The isolated fit cap is 176 contacts. Generation is capped at 44 model calls across the unchanged four-row TRAIN roster; no generation target forces all 44 calls.

The prospective decoder-only geometry is -c 65536 -np 4, with four 16384-token slots and max_tokens 256. The receipt-bound lifecycle supplies --no-mmproj; the model fragment does not declare an mmproj argument. Dynamic fitting remains a root-owned per-realized-request check.

The three root-authored v2 prompt paths are probes/slurp_native_role_context_v2.txt, probes/slurp_native_role_perception_v2.txt, and probes/slurp_native_role_solver_v2.txt. This draft deliberately does not duplicate their bytes or manifest entries. Reviewer and Planner retain their v1 prompts and only Reviewer has native tool authority. Solver uses the native role history without a duplicate appended predecessor or state_fill. Candidate supply selects the original Perception state explicitly, including on revisions.

## Candidate response contract

Perception uses the existing slurp-intent-hypotheses-v1 response builder with min_candidates 1 and max_candidates 3. Its source_catalog is pinned to:

- prepared/SAEA-SLURP-NATIVE-CANDIDATE-CONTRACTS-PREPARE-V1/catalog.json
- catalog SHA-256 3e60268b3f940c3018ab8b8c80ccd988b1d1efd6c5a198929c6af05ba21f8263
- construction-source SHA-256 deb4e097459157a719e34b3fb46014d5f9bcb86c9e952014c1e02f26474db201

The catalog supplies only the authoritative legal intent-ID enum for structured output. It supplies no semantic card value. The runtime retains strict duplicate rejection and makes no post-hoc repair.

## Released named store and selection

Only knowledge_stores is used. No legacy snapshot binding is present.

The named slot-contracts store is pinned to knowledge/slurp/semantic/slot-contracts-v1/snapshot.json, logical snapshot SHA-256 11c246e4b815a4f966e8cf8785f06b70515755eca71658862c6f98e9914044e6, and knowledge/slurp/semantic/slot-contracts-v1/release.json, file SHA-256 8a29c48bfc5aed2eb27ce38073252d3fc608c9102aa8b8095a072667289b4f3e. The release pins source prepared/SAEA-SLURP-SEMANTIC-AUTHORING-PREPARE-V1/authored-slot-contracts-v1.json, SHA-256 34f6c3dc192eca4a30ef7208d10c1e2b797a0ae2ffe5122f16b376e10a30e4c5.

Candidate supply explicitly names candidate_state_phase perception and compact_source_phase perception; it is attached to Solver before the initial draft. It accepts at most three candidates, permits all 16 released cards associated with each candidate, and permits their full distinct union up to 28 cards. These caps preserve the measured released-store maximum rather than selecting alphabetically or by inverse frequency. Observed intent bindings index cards only; they do not restrict legal entity types or define required slots.

## Root admission checklist

Before a contact-capable stage, root must:

1. Review and pin the three v2 prompt bytes in the prompt manifest.
2. Verify the legal catalog against the task adapter's authoritative inventory.
3. Verify the release, snapshot, and construction-source pins at the configured data root.
4. Review the candidate-supply receipt and its source-sample custody.
5. Recompute the composed configuration and runtime protocol identity after any readiness change.
6. Run model-free configuration and dynamic-fit checks, then register parser-readable exposure and readiness records.
7. Verify the receipt-bound decoder-only serving identity before starting the new np4 session.

This document does not itself authorize any of those steps.
