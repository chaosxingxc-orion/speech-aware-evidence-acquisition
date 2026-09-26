# Intent/entity ordering as a complete-system optimization space

The focused successor is
`docs/readiness/2026-09-26-intent-slot-task-coupling-design-v2.md`.
Use it for the owner's task-coupling question; retain this earlier note as
the implementation audit and candidate-interface diagnostic history.

## Owner scope correction: two related prediction tasks

The owner clarified that the question concerns the relationship between intent
recognition and slot extraction as separately defined tasks. It is not the
relationship between retrieving intent candidates and choosing one candidate.
Treat the earlier candidate-coverage factorization below as a secondary
diagnostic only, not as the answer or the principal experiment objective.

Intent recognition predicts the requested operation or semantic frame. Slot
extraction predicts the speech-supported entity spans, types, roles and values.
They have separate outputs and evaluation targets; statistical independence
must not be assumed merely because they are separate tasks.

Study the two directions explicitly:
- Intent-to-slots: whether a tentative frame helps identify entity roles,
  relevant type explanations, boundaries and omission behavior.
- Slots-to-intent: whether observed entity evidence and relations help confirm
  or revise the frame, without discarding action words and original speech.

Prefer an intent-hypothesis-first schedule for initial study, retaining
uncertainty and original speech for the slot task. Let slot evidence inform
a later intent decision when warranted. Top-K is only a way to preserve
uncertainty at the inter-task interface. Its recall is not the central question.
A correctly recognized intent does not guarantee correct slots, and correct
entities do not uniquely determine the intent.

Keep separate intent and slot knowledge stores, with explicit frame-to-role
bindings at consumption. Do not replace them with an undifferentiated union.
Observed TRAIN bindings remain soft evidence; absent optional slots do not
disqualify an intent, and expected slots never justify invented values.

Audit complete trajectories using a joint error table: both tasks correct,
intent correct/slots wrong, intent wrong/slots correct, and both wrong.
Record which task changed after cross-task information, which actual evidence
was available, and whether the correction survived Reviewer, Planner and final
delivery. Raw error association is descriptive: utterance difficulty can affect
both tasks, so correlation alone is not causal evidence of transfer.

A subsequent registered direction comparison must retain the same speech,
knowledge snapshots, tool permissions and matched system budgets, varying the
order and contents of task-to-task information. Compare final intent accuracy,
entity metrics and complete-task success separately. Preserve the full
four-node system for evaluation; do not substitute a component-only score.
No architecture change or new model contact is authorized by this design note.

## Owner question and root recommendation

The owner asks whether the system should first propose Top-K intents and scope
entity interpretation by those intents, or first detect entities and use them
to restrict intent candidates. The recommended default is intent-first proposal
followed by candidate-conditioned entity hypotheses and joint resolution.
This is a research design, not a new generation registration or a change to an
active/frozen actor. Keep closed candidate expansion flights closed.

Let X include the available speech and runtime knowledge, I the intent, and E
the entity spans, types and values. The chain rule gives both factorizations:

P(I,E|X) = P(I|X) P(E|I,X) = P(E|X) P(I|E,X).

With an exact joint distribution and exhaustive inference the factorization
order alone changes no solution. Practical differences arise from limited
candidate sets, approximate models, hard decisions and lossy handoffs. Both
H(E|X,I) <= H(E|X) and H(I|X,E) <= H(I|X) hold on average; entropy alone does
not prove that intent-first is superior.

Intent-first is the pragmatic default here because the finite intent inventory
can propose several hypotheses cheaply, while entity spans/values and semantic
roles are a larger structured space. An early hard entity type/value decision
can discard an alternative interpretation before intent evidence is considered.
Optional or empty entity sets may convey little intent discrimination. On the
already read R01C625 list, 191 references have no entities; this is descriptive,
not an instruction or gold signal for runtime.

## What already exists

The active batch001 baseline uses slot-contracts.candidate_supply.solver:
Perception is the candidate source, max_candidates=3,
max_values_per_candidate=16 and max_total_values=28. Released intent_bindings
map candidate IDs to explanatory slot cards. The selected cards retain extraction
cues, admissible formats, missing/ambiguity behavior and intent semantic roles.

The current Solver v2 prompt instructs joint intent/entity selection from the
Perception candidates. It preserves the full legal entity inventory and treats
knowledge associations as observed uses, not exhaustive or mandatory slot lists.
Its response contract is the final task JSON, not an explicit per-candidate
entity hypothesis comparison. Prompted candidate restriction is not a proven
hard decoding constraint.

Relevant shared implementations:
- rails/candidate_semantic_supply.py: _released_candidate_index and candidate supply.
- rails/semantic_knowledge_build.py: _slot includes intent bindings and semantic roles.
- rails/slot_binding_view.py: existing optional filtering of card bindings.
- configs/probes/slurp_native_role_solver_v2.txt: joint decision instructions.

Thus association is already implemented; do not invent a new claim that it was
absent. Existing card selection/optional filtering must not be renamed as a new
algorithm. What is not established is reliable candidate-specific consumption
and whether structured joint hypotheses improve the delivered whole system.

## Candidate-conditioned entity interpretation and joint resolution

Represent each hypothesis as (intent, applicable slot explanations, entity
evidence, missing/ambiguous evidence). Preserve the link to the candidate instead
of flattening every slot into an unqualified union. Evaluate each candidate
against the same original speech and select the best coherent intent/entity
pair. An explicit large all-candidate answer table is not mandatory: measure
whether a bounded representation helps without consuming the output reserve.

Separate:
1. Hard task ontology rules, if authoritative and complete.
2. TRAIN-observed intent-slot associations: soft evidence only.
3. Actual entity presence/value in the current speech: must be supported by speech.

Do not turn missing optional slots into an exclusion, observed absence into an
illegal type, or a card/example into evidence that its entity value was spoken.
SLURP surface-form extraction must not silently become value normalization.
Always permit the empty entity set when warranted.

If a system strictly restricts final intent to C_K(X), then final intent accuracy
factorizes into candidate coverage times conditional selection accuracy and
cannot exceed coverage. This ceiling is not a bound on entity-only SLU-F1.
If an explicit recovery action allows outside candidates, account for that
recovery branch separately. Current prompt compliance alone does not prove
strict restriction. Record actual outside-candidate predictions.

A candidate-specific search target is

    (I_hat, E_hat) = argmax over i in C_K(X), E in H_i(X)
                    [log P(i|X) + log P(E|i,X)].

Here H_i(X) contains speech-supported entity hypotheses interpreted with the
candidate's slot explanations. It is not a hard whitelist learned from observed
TRAIN pairs. The equation describes a target joint inference problem; the
current frozen model does not expose calibrated probabilities for this score,
and self-reported confidence must not be substituted without validation.

Keep the intent-to-entity-role relation, rather than taking an unlabelled union
of all candidate slot types. The latter removes which role belongs to which
candidate and permits incompatible combinations. Knowledge narrows plausible
interpretations; it never establishes that a value occurred in the speech.
Optional slots and no-entity utterances must remain admissible.

For a strictly candidate-constrained final intent, define
c = P(gold intent in C_K) and
q = P(final intent correct | gold intent in C_K).
Then final intent accuracy equals c*q. For exact joint task accuracy, replace q
with the conditional probability that both intent and the entire entity output
are correct. These identities separate proposal failure from within-candidate
resolution failure; they do not bound entity-only micro F1 in the same way.
An outside-candidate recovery policy requires an additional branch term.

An entity-first alternative should preserve span/type uncertainty and reread X;
using only a single extracted E can discard operation words and relations.
Shared entities across several intents are weak discriminators. This is a
testable alternate system action, not a universally inferior factorization.

## Bounded prospective experiment sequence

Keep all active or frozen actor configurations unchanged and close their registered work.
First audit complete existing traces for:
- candidate coverage and conditional final selection;
- candidate-to-slot-card mappings and supplied binding scope;
- selected intent versus delivered entity semantic compatibility;
- unsupported values, empty-entity hallucinations, omissions and revisions;
- actual outside-candidate outputs and whether reviewer findings change delivery.

Do not use reference labels as runtime features. Offline strata are descriptive.

For a subsequent registered comparison, hold the same initial candidates,
released card identities, example selection, decoding, role budgets and full
controller constant. Compare the current supply representation with a bounded
candidate-conditioned evidence representation. Use existing views where they
already express the intervention. Record residual input/token differences.
Apply common capability/prompt repairs to both arms. Judge full delivered-task
quality, not only Solver output or local schema consistency.

Only after this matched question is closed consider intent-first versus
uncertainty-preserving entity-first sampling. Freeze each full system policy
inside its sampling batch. Record complete trajectories, actual tool events,
Reviewer findings, Planner routes, repairs/harms and terminal official feedback.
Keep four inputs/four trajectories for initial construction; they do not support
an effectiveness claim. Complete-roster evaluation and replication are required.

The later training-free optimizer may select finite system actions such as
candidate-specific evidence assembly, ambiguity-targeted review, or candidate
recovery. The state must be observable before the action; reward comes from the
complete final system. Do not update a slot-only surrogate and claim system RL.
This note neither admits a new tool nor changes frozen memory, reward or data
boundaries. DEV6570/test13078 remain closed.
