# Knowledge construction and consumption as a system-level optimization policy

The owner subsequently separated construction quality from sampled retrieval and
consumption optimization. Follow
[the two-stage successor](2026-09-26-knowledge-construction-consumption-optimization-v2.md)
for the next comparison order and implementation boundaries.

## Owner direction and scope

The owner proposes a second optimization object alongside task-execution
memory: sample alternative intent and slot descriptions, optimize retrieval
keys and consumed values, execute the existing full agent system, and return
observed outcomes to the description generator for reflection and adjustment.
The generator may be a text model or the frozen Omni model. Model weights need
not change. This note records the research design; it registers no new model,
embedding, scoring or external API contact.

Treat this as bounded external knowledge-policy improvement. Do not equate a
single generated rewrite, offline retrieval gain, or root-authored correction
with a completed training-free learning loop. The loop must sample, execute,
receive measured feedback, update external state and execute the updated state.
Keep the final answering core and complete-system evaluation fixed.

## Two related tasks, separate knowledge roles

Keep intent and slot knowledge stores separate and preserve their bindings.
Intent values explain operation boundaries and confusion with neighboring
operations. Slot values explain roles, spans, surface forms, omissions and
ambiguity. Intent-to-slot bindings express how the two prediction tasks relate;
they are not a substitute for either task. Knowledge values must not assert
that a value occurred in the current speech merely because it is expected.

| Object | Candidate edits | Construction diagnostics | System endpoint |
| --- | --- | --- | --- |
| Intent key | Activation paraphrases and compact semantic anchors | Relevant knowledge-card coverage, confusion and dilution under the actual frozen speech-to-text-key retriever | Final intent and slot outcomes |
| Intent value | Contrasts, decisive action/relational cues, uncertain cases | Whether delivered distinctions are used correctly | Final intent accuracy with slot protection |
| Slot routing key/binding | Which intent-role state makes a slot explanation relevant | Needed-card availability and budget displacement | Final slot quality with intent protection |
| Slot value | Semantic role, include/exclude boundaries, surface form, absent-value behavior | Evidence-supported corrections, omissions and hallucinations | Official SLU-F1 and complete-task success |

Distinguish relevant knowledge-card coverage from gold-intent coverage in the
model's candidate output. They are separate points in the trajectory. Report
both where relevant without substituting one for the other.

## Important facts about the current implementation

The existing semantic builder already has a KeyFacet/ValueBundle separation.
However, authored intent activation text contributes to BOTH the key and the
value. A change to that field is currently a coupled intervention, not a
key-only experiment. Isolate the fields through the shared builder if a
registered experiment needs independent control; preserve the historical
builder and released snapshots byte-for-byte.

Intent keys are text vectors matched against sealed speech query vectors.
Textual elegance does not guarantee better cross-modal retrieval. Re-encode
only changed keys with the pinned registered encoder, preserve speech queries,
and bind the new vectors to the new knowledge snapshot. New encoding is a
registered tool contact. Do not use reference transcripts as runtime queries.

Current slot supply uses candidate intent IDs and released intent_bindings,
not free-text similarity over a slot key. Merely rewriting an unused slot key
cannot improve this route. First identify the actually consumed field. A slot
text-retrieval route would be a separate registered mechanism; do not add one
silently. Initial slot-value experiments can retain the existing bindings.

Reuse semantic_knowledge_build, semantic_knowledge_preparation, candidate
semantic supply, knowledge release validation and the existing FlightRuntime.
No private experiment runner or alternate baseline path is needed.

## Two sampling levels and one full-system return

Knowledge proposal sampling and task trajectory sampling are different:

1. Freeze the incumbent knowledge, runtime policy and construction feedback.
   The generator proposes bounded, source-supported edits to named fields.
   Keep a no-change candidate. Preserve labels, ontology and source exclusions.
2. Compile and validate candidate snapshots. Deduplicate identical candidates,
   enforce a common supply/token envelope, and prepare only changed key vectors.
3. Freeze each candidate while executing its complete Perception, Solver,
   Reviewer, Planner and terminal-delivery trajectories on the same inputs.
   Reuse the common service; candidates execute serially with two live slots.
4. After the entire matched sampling batch and one full official score per
   actor complete, compare candidate outcomes and return the actual feedback.
5. Update the external candidate-value estimates, accepted knowledge version
   and generator's evidence-backed improvement history. Freeze that result for
   the next batch. NONE/no-change remains valid; never manually repair a lesson.

The immediate construction geometry stays four distinct inputs and four
trajectories per arm. Do not multiply live concurrency by descriptions, inputs
or draws. Initially compare an incumbent and one proposed snapshot, rather
than launching a Cartesian product of every intent, slot and wording variant.
Further candidates belong to future registered batches. All eight actors of
the matched pair must close before its update. These small batches construct
the policy; they do not establish stable gains.

The feedback uses the already frozen official-count utility and separately
retains intent correctness, format, exact slot outcome and failures. Aggregate
paired differences over common inputs and stochastic draws. Group-relative
advantages can guide candidate/operator value updates, but the optimization
object is external knowledge policy, not model parameters. Record actual
proposal/operator probabilities if a stochastic policy is updated; never invent
historical probabilities or describe a simple best-of-N choice as GRPO.

For causal interpretation, the unit of treatment is the full knowledge snapshot
and its resulting system trajectory. Same seeds are not deterministic replay.
The just-completed memory batch already contains pre-treatment trajectory
variation despite matching initial contexts. Do not attribute every individual
paired answer difference to the changed knowledge field.

## Feedback to the generator

Provide structured observed evidence rather than only a scalar or prose verdict:

- Proposed field changes, source support and immutable candidate identity.
- Query/key selection and relevant-card availability under the actual retriever.
- Exact values delivered to each role, including truncation or budget exclusion.
- First task outputs, Reviewer findings, Planner routes, revisions and delivery.
- Official terminal TP/FP/FN, intent and format feedback; group ties and harms.
- Which knowledge was absent, present but unused, misapplied, or used without
  changing delivery. Mark unknown semantic use as unknown.

If a card was never delivered, do not reward its wording as a successful
consumption edit. If a local correction was later overwritten, record that
failure in the full-system return. Description generation must not fabricate
tool calls, elevate a review opinion over speech, or treat absence of memory
guidance as evidence of correctness. Those failure modes were observed in
batch002 and belong in the feedback trace, not a manually installed fix.

Knowledge stores retain stable task semantics and interpretations. Optimizer
memory retains evaluated changes, their contexts, outcomes and uncertainty.
Do not store the training corpus as either a disguised lookup table or a set
of per-sample answer instructions.

## First comparison and path to stable evidence

Prioritize a slot-value-only successor for the first knowledge comparison:
retain intent keys, slot bindings, examples, tools and system routing. The
current construction evidence shows many correct intents with wrong slots;
it motivates a value-consumption hypothesis but does not establish a
population-wide bottleneck. Ground the chosen editable fields in the existing
authorized full-roster diagnostics as well as these complete trajectories.

Prepare the intent-key route on CPU in parallel. Later compare a key-only
successor with the value snapshot frozen. Register a combined candidate only
after learning what each edit changes; key/value interactions remain possible.
Keep the initial action space small and allow no change after uninformative
feedback. Do not re-open the closed delta application or candidate-expansion
flights under a new name.

Compare the frozen learned knowledge policy with the incumbent and the best
fixed candidate under the same full system. Stable improvement still requires
the registered complete-roster evaluation and same-roster replication, with
speaker clustering and separate intent/slot protection. Construction inputs
and evaluation inputs remain source-disjoint; optimizer feedback must never
contain DEV6570/test13078 or validation answers used to update the evaluated
snapshot. Expanded construction scope invalidates use of its members as new
unexposed evaluation inputs.

## Generator choice and execution boundary

Use the local frozen Omni as the first registered generator to reuse the
current execution, source-custody and zero-paid-API boundary. A stronger text
generator, including the owner's suggested Astra model, is a possible separate
offline construction factor. Keep its model/version, prompts, sampling and
source access explicit and fixed for a comparison. It does not become a second
runtime answerer or an unlogged judge, and no external paid call is authorized
by this note. Do not change generator and knowledge optimization method at the
same time and attribute all gains to the method.

## Continuation boundary

Memory batch002 has completed and its root interpretation is recorded. The
next shared semantic update may use its complete learned trajectories and
cumulative construction provenance. Register the knowledge-edit action space
separately before executing it; do not mutate the completed memory experiment.
Before next GPU dispatch, resolve the independently observed resource-clock
guard stop, complete actual request capacity checks and bind a fresh service.
Preserve full output reserves, common prefixes, Windows memory floors and WSL
background execution independent of network or ChatGPT credits.
