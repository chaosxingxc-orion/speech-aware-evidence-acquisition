# Separate intent and slot knowledge: verified reuse and optimization boundary

This note supersedes the implementation-gap statements in v3. It refines the
owner's task-specific construction and consumption direction. It admits no model
contact and does not reopen a historical flight.

## Decision

Keep separate logical stores for intent decisions and slot extraction. A shared
physical database is acceptable, but two text columns behind one undifferentiated
retriever are insufficient. Give the two tasks distinct keys, value schemas,
retrieval/selection policies, version identities and input budgets. Share canonical
facts and provenance rather than maintaining inconsistent copies.

Use this logical relationship:

- Intent ID -> discriminative retrieval keys -> intent-decision value.
- Slot ID -> common meaning, extraction rules, absence and ambiguity handling.
- (Intent ID, slot ID) -> the slot's semantic role in that intent.

Intent recognition and slot extraction remain distinct, correlated prediction
tasks. Candidate labels connect them; candidate retrieval is not a replacement
definition of intent recognition. Likewise, an intent-to-slot relation is useful
evidence, not proof that a slot was spoken or that an unlisted relation is illegal.

## Task-specific construction

Intent values should explain the operation, activating evidence, nearest competing
intents and the evidence that separates them. Broad paraphrase coverage belongs in
retrieval keys; relevant concise contrasts belong in the value actually consumed.

Slot values should explain what information a slot denotes, its role under an
intent, supported span boundaries and value conventions, confusable roles, and
what to do when the speech is absent or ambiguous. They also need discriminative
content: for example, knowing that a phrase is a location does not distinguish an
origin from a destination. Illustrations here describe schema design, not new
assertions about any dataset's legal labels.

Generate and validate the two value types separately against authorized sources.
Never add a task-specific fact merely because a description generator suggests it.
Pin common facts once, record each view's ancestry, and require full-system feedback
before promotion. Model weights and runtime answer authority remain unchanged.

## Consumption by stage

Perception retrieves a bounded intent-decision packet. Solver consumes the shared
slot definitions and role interpretations relevant to all current candidate
intents, retaining the candidate-to-role links. Reviewer obtains the knowledge
needed to check its suspected issue; its scope must also retain a valid draft
intent outside the initial candidates. Planner receives actionable findings and
evidence availability. It need not receive every source card merely because a
previous node acquired it.

Use registered reconsideration or evidence acquisition when observations conflict
with the initial frame. Preserve full-card fallbacks when scope is unavailable or
no binding applies. Do not make a missing candidate binding an implicit hard mask.
Role-specific retrieval and history retention are separate controls; filtering a
slot card alone does not prove that every role's entire context is selective.

## Implementation correction and historical evidence

The current baseline already declares separate intent-boundaries-v1 and
slot-contracts-v2 releases. It does not enable the optional candidate slot view.

The candidate-conditioned view is ALREADY implemented in
rails/slot_binding_view.py and core/model/native_slot_binding_view.py, registered
as native-candidate-slot-view-v1. It binds the released authored source, checks
that it reproduces the canonical snapshot, preserves global guidance, scopes
intent-role rows from validated native history, and records derived wire hashes.
It handles base evidence and native tool returns through the existing transport.
Reuse it; do not add another renderer, store, controller or experiment runner.

The historical four-row proof stopped after four Perception contacts, before the
first Solver generation, on an exact plain-versus-prefixed representation mismatch.
Repair 23b4ec0e is integrated. The proposed rendering proof remains held. Neither
that failure nor the offline repair tests establish task quality. Preserve the
closed attempt and do not dispatch its identity again.

The current audit reran 46 existing focused tests in WSL, including raw/feature
render-to-fake-POST equivalence, default compatibility, source custody and fallback.
It also rebound the current Stage-3 common actor's released v2 knowledge and checked
both canonical representations. See the independently versioned receipt at
docs/receipts/continuation/2026-09-26-task-knowledge-reuse-audit-v1.json.
The source-only scope is synthetic; it is not a campaign read, token fit or benefit
measurement. The audit made no model, tokenizer, encoder or scorer contacts.

## Next experiment and learning space

Use the ordinary Stage-3 common actor as the comparison source; do not silently
substitute the memory-specific Reviewer prompt. Prepare one matched complete-system
comparison that changes only the optional slot-consumption view. Preserve initial
knowledge, candidate policy, exemplar supply, tools, role prompts and decoding.
Report any independently generated predecessor differences rather than assuming
identical Perception. Complete request fit and a newly admitted engineering proof
must precede a scientific launch; the old proof's identity remains closed.

The minimal proposed overlay is already expressible through the shared entry:

```json
{
  "native_evidence_projection": "native-candidate-slot-view-v1",
  "native_evidence_projection_params": {
    "store_id": "slot-contracts",
    "consumer_roles": ["solver", "reviewer", "planner"]
  }
}
```

This is a prospective configuration delta, not a ready flight. A deterministic
projection is an engineering action, not an RL algorithm or a demonstrated gain.
Measure the terminal official SLU score, intent correctness, entity FP/FN,
draft-to-final saves/harms, input amount, fallbacks and complete trajectory costs.
Keep retrieval relevance and candidate coverage as distinct diagnostics. Claims
of stable benefit require full-roster evaluation and same-roster replication.

Construction optimization holds consumption fixed while sampling source-supported
key/value versions. Consumption optimization freezes knowledge while sampling
retrieval, selection and view actions. Log the state available before each action,
action probability, supplied view and the full downstream trajectory. Update only
after a complete sampling batch, as the owner directed.

Intent and slot policies may have distinct state/action spaces but must share the
terminal system outcome as their acceptance criterion. Retain local diagnostics
for attribution; do not optimize two isolated rewards and assume their gains add.
The existing finite_supply_policy supports exemplar-route sampling; the deterministic
slot view does not add semantic-view sampling or verified policy credit by itself.
Extend those existing seams only after defining the concrete sampled action space.

No GPU queue, historical verdict, closed line, or DEV/test boundary changed here.
