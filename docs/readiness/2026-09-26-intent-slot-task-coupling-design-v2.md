# Intent recognition and slot extraction: task coupling, not candidate retrieval

## Scope and recommendation

This note supersedes the emphasis of the earlier intent/entity ordering note.
The owner's question concerns two separately defined prediction tasks and the
information they should exchange. Candidate recall versus selection is not the
principal research question. Keep active and sealed actors unchanged.

Intent recognition predicts the operation or semantic frame. Slot extraction
predicts the speech-supported values, spans and task-specific roles. Separate
definitions, knowledge stores and evaluation targets do not imply statistical
independence. Neither task being correct guarantees that the other is correct.

Prefer tentative intent interpretation, followed by intent-conditioned slot
interpretation, followed by evidence-based reconsideration when the two conflict.
This is a practical research preference, not a theorem about the best order.
Top-K can preserve uncertainty at this interface; it is not the objective.

## What each task contributes

| Direction | Useful information | Insufficient or harmful handoff |
| --- | --- | --- |
| Intent to slots | Operation semantics; applicable role explanations; distinctions between similar roles; relevant boundary and omission conventions | A bare label; an unqualified union of slot names; a mandatory value invented because a frame usually contains that slot |
| Slots to intent | Speech-supported mentions and relations; which frame explains their roles; contradictions or unresolved alternatives | Entity types alone; a single uncertain extraction treated as fact; missing optional entities used to exclude an intent |

Distinguish mention detection from task-specific slot interpretation. Detecting
a date expression before knowing the intent is possible; deciding whether it
is a departure date, an event date or a requested replacement date can depend
on the operation. Those are explanatory examples, not new SLURP ontology labels.
Likewise, ticket inquiry and ticket booking may mention the same destination
and date. Action words and the original speech remain necessary.

An entity-first alternative should initially preserve mention and type
uncertainty rather than commit all semantic roles before the intent is known.
An intent-first alternative should preserve speech evidence that does not fit
its initial frame rather than silently delete it.

## Mathematical interpretation

Let X be the available speech and legitimate knowledge, I the intent, and S
the complete structured slot output. The chain rule gives:

    P(I,S | X) = P(I | X) P(S | I,X)
              = P(S | X) P(I | S,X).

Exact inference over the same joint distribution has no inherent ordering
advantage. Practical differences arise from approximation, representation,
early commitments, computational budget and information lost between nodes.
Selecting only the most likely first-task answer is not equivalent to joint
inference or marginalizing uncertainty over that task.

The true intent can reduce uncertainty about slots. A predicted intent is not
an oracle observation: a deterministic prediction computed from X adds no new
information conditional on X. Its practical benefit must come from making
relevant knowledge and intermediate interpretation easier for the bounded
frozen model to use. It can also amplify an incorrect frame. The same caveat
applies when extracted entities are used to guide intent recognition.

This is why an entropy argument alone cannot establish that intent-first wins,
and why the experiment must measure both correction and propagated error.

## Existing implementation and unresolved gap

The current shared path already links Perception candidates to released slot
cards through `intent_bindings` and semantic roles. The common batch002 baseline
allows three intent hypotheses, at most sixteen cards per candidate and
twenty-eight total. The Solver v2 prompt asks for joint intent/entity resolution,
retains the full legal entity inventory and forbids inventing missing values.

Therefore, do not claim that intent and slots have never been linked. The gap
is whether that connection is useful in execution: can the model interpret the
role and boundary of a mention, notice missing evidence, and revise the right
task without damaging the other? Card delivery alone does not establish this.

Maintain separate intent and slot knowledge stores. Build an explicit binding
between an intent's operational meaning and the relevant slot explanations.
TRAIN-observed associations are soft evidence, not an exhaustive legal schema.
Separate knowledge about what a slot means from evidence that its value was
actually spoken. Preserve legitimate empty entity sets.

## Whole-system design and evaluation

The proposed information flow is:

    speech -> intent hypotheses -> bound slot explanations -> slot evidence
                              <- compatibility or contradiction <-
                  Reviewer findings -> Planner route -> Solver delivery

Reviewer checks intent support and slot support separately, then checks their
compatibility. Compatibility is insufficient: two mutually consistent answers
can both be wrong. Reviewer must identify actual supporting or contradicting
evidence. Planner controls acceptance, evidence acquisition or revision. Solver
retains final task-answer authority. Do not let an advisory memory response
replace inspection of the speech or transfer answer authority to Reviewer.

For any prospective order/interface comparison, hold the speech, knowledge
version, legal tools and system budget fixed. Clearly name whether the changed
factor is task order, direction of information exchange or representation;
do not vary all three and attribute the result to order alone. Reuse the shared
controller and configuration path. No new GPU flight is registered by this note.

Evaluate intent accuracy, official slot SLU-F1 and complete-task exact success
separately. Also report the four joint error cells, before/after each relevant
handoff and at final delivery: both correct, only intent correct, only slots
correct, neither correct. Count corrected tasks and newly damaged tasks.
Gold-conditioned offline analyses are diagnostics, never runtime instructions.

The batch002 registered read contains only four distinct TRAIN inputs and is
not an order comparison. Its frequent correct-intent/wrong-slot outcomes show
why the tasks need separate diagnostics; they do not prove which direction is
causally better. See the complete memory-consumption report for source limits.

## Training-free optimization boundary

Potential system actions include which task to revisit, which task-specific
evidence to acquire, and whether an inter-task conflict warrants revision.
States must contain only information available before the decision. Sample
and score complete system trajectories; use terminal task outcomes while
retaining separate intent and slot feedback. Freeze policy within each sampling
batch and update only after that batch completes. A locally better slot answer
that is later overwritten is not a system improvement.

Continue the current complete-system learning chain before registering any
new order comparison. Keep DEV6570/test13078 and closed flights closed.
