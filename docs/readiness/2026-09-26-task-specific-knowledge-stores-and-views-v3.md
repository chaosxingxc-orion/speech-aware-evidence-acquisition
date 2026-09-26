# Task-specific knowledge construction, retrieval and consumption views

## Owner direction

Build intent-recognition knowledge and slot-extraction knowledge separately.
Even when sharing physical storage, keep typed keys, values and stage-specific
consumption views separate. Do not concatenate all views into every role's input.
This refines the two-stage construction/consumption design; no flight is admitted.

The two prediction tasks are related, but their useful evidence differs. Intent
recognition identifies an operation/frame and distinguishes neighboring ones.
Slot extraction identifies speech-supported values and their semantic roles,
boundaries and surface conventions. Slot explanations also need distinctions:
similar types or roles must not be conflated. The distinction is not a rigid
rule that intent knowledge is only contrastive and slot knowledge only descriptive.

## Separate logical stores, shared canonical sources

| Logical object | Construction target | Retrieval key/query | Consumed value |
| --- | --- | --- | --- |
| Intent boundary | Accurate operation definition, activation conditions and confusable alternatives | Speech-derived request meaning and operational cues against intent keys | Compact decisive contrasts and uncertainty conditions |
| Slot contract | Meaning of the slot, intent-conditioned role, extraction boundaries, absent/ambiguous cases | Current candidate intent-role bindings plus legitimate observed evidence | Relevant role explanation, supported span/value rules and omission behavior |
| Shared ontology | Stable identifiers, labels and source-backed relations | Explicit identifiers | Legal inventory and common semantics, without repeating every explanation |

Physical storage can be shared. Use explicit value types such as intent_decision
and slot_extraction with independent indexes, versions, selection rules and budgets.
The same source item can support both types, with shared provenance. Do not assume
one shared textual key is optimal for both tasks, or duplicate common facts into
many independently editable cards. A conceptual layout is:

    intent_id -> intent key(s) -> intent decision value
    (intent_id, slot_id) -> role-specific slot interpretation
    slot_id -> shared slot definition and constraints

This is a logical model, not a request for a new database or framework. Preserve
the existing KeyFacet/ValueBundle, named stores, KnowledgeProvider and versioned
release path. New views must be source-bound derivatives with explicit hashes;
never rewrite a released card in place or pass an unrecorded prompt transformation.

## Existing implementation: already separate, but not yet sufficiently selective

Verified against semantic_knowledge_build.py, candidate_semantic_supply.py,
knowledge_provider.py and the current batch002 common baseline:

- intent-boundaries-v1 and slot-contracts-v2 have separate releases and snapshots.
- Perception retrieves eight intent-boundary values through frozen speech-query
  and text-key vectors. This is a retrieved packet, not the complete intent store.
- Solver maps up to three normalized intent hypotheses to released slot cards,
  with per-candidate and total bounds. The mapping is an intent-ID lookup; it is
  not a semantic similarity search over slot descriptions.
- The slot builder renders ALL intent_bindings and semantic_role descriptions
  into one slot value. Selecting that value brings unrelated intent-role entries
  along with the relevant ones. The provider sorts values within candidates and
  selects round-robin; it does not rank a slot explanation by the current mention.
- Values already accumulated in the episode may remain visible downstream.
  The existence of two stores alone does not prove role-specific context economy.

Do not claim that the project has never linked intent and slots or lacks separate
stores. The next questions concern task-specific retrieval, relevant view selection
and actual use. Missing knowledge, unavailable knowledge and ignored knowledge are
different failure modes. The current date card already has extraction guidance;
one observed date error does not establish that adding another rule is needed.

## Role-specific consumption

Perception consumes a bounded retrieved intent view. Preserve multiple plausible
intent hypotheses and the evidence for their distinctions. It should not receive
all slot extraction explanations merely because the ontology contains them.

Solver consumes slot views related to the current candidate set, preserving the
candidate-to-role mapping. If an intent decision is still ambiguous, retrieve the
specific intent contrast as an additional bounded packet. A flat union of slot
names loses the relationship; all bindings of every selected slot add distraction.
Shared slot definitions need appear only once. An expected slot is not evidence
that its value occurred, and an absent optional slot does not disqualify an intent.

Reviewer consumes evidence relevant to the suspected issue, selecting intent
distinctions for intent ambiguity or slot boundaries for extraction ambiguity.
Its retrieval should be separately observable. Planner receives findings, evidence
availability and legitimate action choices sufficient to route the next step.
Solver retains task-answer authority. No new role may see references or future
events, and no fixed tool invocation is implied by this knowledge design.

If evidence conflicts with the initial candidates, allow a registered expansion
or reconsideration action. Do not turn TRAIN co-occurrence into an exhaustive
legal schema or silently discard speech evidence outside the current frame.

## Sampling and attribution

Keep knowledge construction and consumption as separate interventions. First
freeze the canonical content and compare full-value supply with a registered
candidate-conditioned view. Preserve example identities, candidate predictions
where the comparison requires shared predecessors, and the complete downstream
trajectory. This measures a consumption view, not a newly improved knowledge fact.
Any decrease in input length is part of that intervention and must be reported.

Then sample among a small set of admitted retrieval/view policies, using only
state available before the action. Intent and slot consumption may have separate
state/action tables while sharing the same complete-system trajectory and terminal
reward. Do not independently reward a local intent or slot change that disappears
or causes harm downstream. Construction updates occur with consumption fixed;
consumption updates occur with knowledge fixed; update only after full batches.

Measure intent-card relevance and final intent correctness separately from
slot-card relevance, required-role coverage, entity FP/FN and official SLU-F1.
Keep an explicit definition of relevance. Candidate-label coverage is not the
same metric as knowledge recall. Stable benefit still needs full-roster evaluation
and same-roster replication, not only the four-input construction batches.

## Reuse correction: existing finite supply sampler

Further code inspection found that finite_supply_policy.py already implements
logged stochastic selection after initial Perception, using frozen schedules and
one held action through the ordinary full-system revision/delivery path. It is
separate from both the complete native-policy catalog and VAR-2 side branches.
Reuse it for its supported exemplar-route action space; do not rebuild it.

Its present actions only adjust the Solver exemplar route. It does not yet sample
task-specific semantic-card views. The source-verified offline credit reader for
the complete native-policy catalog rejects nested finite-supply decisions, so it
cannot be relabeled as the finite-supply updater. Audit and extend these specific
shared boundaries if the selected experiment needs them. Existing baseline tests
are not proof of a flown or effective consumption policy.

No historical failed flight is reopened by this note. The full archived knowledge
proposal context remains unfit for the current generator geometry; registration,
bounded input preparation and real fit remain prerequisites for its new flight.
