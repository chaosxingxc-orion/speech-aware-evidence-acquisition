# Consolidated provisional experience: verified source replay

## Purpose and scope

Connect deterministic experience consolidation to the existing candidate
materializer, source attestation and native runtime reader. Do not create a
second memory loader or promote a provisional record to admitted memory.
The active candidate-recovery experiment is unchanged.

This is one necessary part of a complete-system learning loop. It verifies
where updated experience came from; it does not establish that the model
performed the intended summary, semantic comparison or consolidation reasoning,
nor that the resulting experience improves the final task.

## Source contract

Use the existing prepare_provisional_candidates entry point with schema
saea-provisional-consolidation-materialization-config-v1. The exact top-level
fields are schema, materialization_id, memory_id, max_candidates,
initial_materialization and rounds.

- initial_materialization is null or an absolute path/SHA pin to an original
  typed-proposal materialization config.
- rounds is a nonempty ordered list. Each entry has exactly round_id,
  proposal_materialization, consolidation_bundle, consolidation_sample_id and
  consolidation_protocol_hash and base_snapshot_sha256.
- proposal_materialization pins an original typed-proposal materialization
  config. Rebuild its source authority through the existing implementation,
  including complete finalized reward sources, prepared contexts, the actual
  proposal bundle and its protocol/decision bindings.
- consolidation_bundle pins the actual finalized scoreless construction bundle.
  It uses the existing v1 training-feedback-proposal artifact contract, a
  discovery TRAIN anchor from the construction roster, one output and no
  official scorer. Verify its actual attempt state and protocol hash.
- Read the operation plan only from that sealed model output. Do not accept a
  plan pasted into the materialization config. The raw model response contains
  operations only; it must not author custody hashes. The registered round pins
  the exact base snapshot. After verifying that pin against replay, the adapter
  attaches it to the deterministic plan and applies ADD/UPDATE/DELETE over
  existing proposal/record IDs.
- Keep every round on the same ordered construction roster. Rebuild the entire
  chain, including deleted identities, on cold and warm reads. Preserve memory_id
  when appending rounds; use a new materialization/output identity.

A consolidation response cannot invent guidance text in this contract. New
or rewritten content must first have a sealed, source-bound typed proposal.
This restriction belongs to the declared search space; it is not an unchanged
implementation of upstream free-form batch rewriting.

Original source materialization remains version-bound. Never edit old prepared
artifacts to make new implementation hashes match. Retain the original source
checkout or deliberately prepare a separately identified derivative and bind it
before its dependent model contact.

## Output and runtime connection

Write saea-provisional-consolidated-experience-candidates-v1 through the common
preparation cache. This is a distinct output schema under the existing
provisional-experience-candidates preparation kind. Do not relabel it as an
original model proposal. Retain the complete construction population, including
samples with no remaining records, every round receipt, source pins and the
final candidate snapshot. Do not truncate to satisfy max_candidates.

The existing candidate source-attestation entry replays this materialization.
The existing runtime candidate loader then applies its original disjoint-TRAIN
evaluation decision, record order, role/tool authority and applicability checks.
Runtime never loads source scores or construction answers. Current corrective
memory authority remains with Reviewer/Planner; Solver retains final answer
authority and may consume the resulting evidence in a later revision.

A rejected operation plan writes a separate immutable rejection receipt and
produces no runtime candidate artifact. It retains the original plan, error and
prior round receipts. Missing/invalid source authority fails before publication.
Neither failure is converted into a successful update.

## Verification and remaining work

The integration suite exercises three-round deletion/addition replay, missing
or stale sources, wrong protocol/anchor, extra outputs, invalid operations,
warm replay, candidate caps and unchanged original bytes. Its connected test
uses real proposal/reward-source verification, candidate attestation, the
FlightRuntime dispatch and actual OpenJiuwen role/tool history. Only the new
consolidation-bundle verifier boundary is stubbed in that connected fixture;
it is not evidence of a research model-generated consolidation. Existing bundle
verification tests remain the underlying source-custody evidence.

The connected test also prohibits source materialization/reward reads during
answer execution, while checking that the returned candidate reaches both the
Reviewer tool result and subsequent Solver revision with the same record hash.
All model responses in these engineering tests are synthetic. They support no
task-quality or effectiveness claim.

Next implement and register the model-facing semantic stages and their input
binding, including real-request capacity, complete-stage receipts, feedback
visibility and the permitted whole-system action surface. This existing
candidate evaluation path still requires disjoint construction/evaluation TRAIN
rosters. Do not use this connection to apply newly proposed memory on its own
construction rows. The multi-round protocol must explicitly reconcile its
construction rollout schedule with that retained boundary before launch. Then execute frozen
updated experience, one complete official score per arm and matched replication.
Keep the terminal official-count feedback definition and empty-entity handling;
the inherited proposal-feedback provenance does not replace the new versioned
semantic feedback channel or authorize feeding training outcomes to the actor.

Validation is recorded in
docs/receipts/continuation/2026-09-25-consolidation-materialization-validation.json.
