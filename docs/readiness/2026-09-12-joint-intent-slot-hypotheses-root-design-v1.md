# Root design: retain hypotheses and resolve intent with argument evidence

## Decision and status

Adopt the owner's correction: separate decision responsibilities without committing irreversibly to the first decision. The first pass may retain a compact set of intent hypotheses. The main model then uses current speech, returned observations and candidate-specific parameter contracts to jointly choose the intent and bind its slots. This is a proposed mechanism, not an established effectiveness result or a new flight authorization.

Keep the shared native answer-or-tool controller, runtime and OpenJiuwen executor. First close the existing bounded native tool execution failure. Do not introduce a second controller or revive a private SELECT/FILL runner.

## Why this changes the failure mechanism

A hard Top-1 stage discards alternative hypotheses before the downstream evidence is fully evaluated. A wrong selection then becomes unrecoverable if FILL must preserve the selected identity. Top-N postpones that commitment: argument compatibility, target scope, explicit evidence, missing fields and corrections can change the selected intent.

The decision target is the joint interpretation of the speech: one intent and its supported entity bindings. Factoring that decision into stages does not require greedy commitment after the first stage. The first stage should preserve sufficient competing interpretations for later evidence to change the choice. Rank is a provisional ordering, not a calibrated probability.

For a closed shortlist, candidate recall is only an opportunity ceiling for final intent accuracy. Realized intent gain equals rescued wrong Top-1 decisions minus spoiled correct Top-1 decisions, divided by the roster size. This identity does not equate intent gain with slot or complete-task gain: those outcomes still require separate official scoring.

Top-N does not remove all selection error. A hard shortlist still fails when it excludes the correct intent; the final model can also choose the wrong surviving candidate. A fluent, easily filled schema can attract the model despite weaker speech evidence. Larger lists can increase confusion and consume useful context. These are testable tradeoffs, not reasons to assume that larger N is always better.

Treat the shortlist as guidance. Keep the legal task label inventory available. Permit the main model to request a relevant alternative contract or reopen retrieval when all shortlisted candidates conflict with the evidence. A candidate-set escape is a real recorded decision, not an evaluator-side repair.

For SLURP, the latent decision is one intent and its entities. For Audio2Tool, preserve alternative hypotheses per operation occurrence and their scope, order and multiplicity; a flat Top-N list of tool names cannot represent several requested calls. Do not confuse a candidate count with the number of calls to output.

## Knowledge construction and consumption

Maintain one canonical, versioned source of task semantics and derive compact purpose-specific views.

| View | Key or access | Value that changes a decision |
| --- | --- | --- |
| Routing | Operation, target scope, current candidate pair or unresolved distinction | Choose/avoid boundaries, contrast with a sibling, effects, preconditions and minimal distinguishing interface fields |
| Joint resolution | Candidate IDs plus the current unresolved semantic role | Argument meaning, permitted type/unit/range, evidence-presence rules, extraction anchors, ownership, correction and omission rules |
| Episode state | Operation occurrence and lawful prior state | Current hypotheses, observed spans, missing/conflicting evidence and superseded values |
| Corrective memory | An observable failure pattern | An independently validated correction procedure, its applicability and counterconditions |

Do not open every full parameter manual for every candidate. Start with the fields that discriminate the remaining hypotheses; expand the selected contract only when needed. Do not treat schema satisfiability or public defaults as evidence that a value was spoken.

The hypothesis artifact should contain candidate IDs, their order, compact observable distinctions, evidence references and unresolved fields. Do not require long private reasoning or treat self-reported scores as calibrated probabilities. Preserve the existing final task JSON contract.

## Agentic execution

1. Inspect the speech and task contract. Answer directly if evidence suffices.
2. When the task is unresolved, retain a small candidate set and identify what distinguishes its members.
3. Request the relevant knowledge view or local speech observation only when that action can resolve a named gap. The main model makes the request; preloading weights and preparing base speech packets do not substitute for this decision.
4. Jointly choose an intent and bind arguments from actual returned evidence. Revise a provisional selection when parameter evidence contradicts it.
5. Reopen the candidate set within the registered bound when necessary, or deliver according to the dataset's output contract. Never invent an unsupported clarification answer or add an unknown label where the task disallows it.

For example, a spoken city name can be a weather location or a travel destination. It does not identify the task by itself. The requested operation and any origin/destination relationship jointly determine which interpretation is supported. An available field of the right type is insufficient.

The original local Whisper proof established real execution and returned observations but failed final delivery. Its separately registered single recovery has now sealed four legal final task JSON answers after eight Qwen contacts and four actual CPU Whisper calls. Its source-chain audit passed, and the single recovery is closed for engineering execution only; see 2026-09-12-native-speech-tool-recovery-result-v1.md. The recovery changed native dialogue projection and phase instructions together, so their individual causal effects are not isolated. Neither four-row outcome tests the Top-N mechanism or useful autonomous triggering.

## Minimal experimental sequence

Use SLURP first, a frozen matched roster of at least 500 and the same service, speech route, scoring and final output ceiling. A four-row check may prove execution only. Preserve historical experiments and admissions.

- Establish a functioning native loop and direct baseline on the shared harness.
- Start with a preregistered small N, initially 3 as a design choice rather than an empirically selected optimum. Do not sweep N on the evaluation roster.
- Isolate commitment with a controlled comparison that gives both branches the same candidate hypotheses and compact contracts: one branch must keep the first-ranked intent; the other can jointly choose among candidates. This measures the effect of decision freedom conditional on a shared first pass. If the first pass is generated once and branched, preregister the reuse, count it once in observed contacts and do not call the branches independent replications.
- Separately compare complete systems with their own full trajectories when making a system-level claim. Retain a matched joint reasoning control when distinguishing decomposition from an extra answer contact.
- Add adaptive candidate width, targeted observation, contract expansion and candidate-set reopening only after the predecessor is replicated or root-caused. Change one named decision mechanism at a time.

The smallest interpretable comparison has three answer-stage conditions: direct joint answering as the complete-system reference, shared candidate generation followed by fixed-first selection, and the same candidate generation followed by joint candidate selection plus binding. If claiming a decomposition effect beyond an extra contact, retain a matched two-contact joint control. All final-stage arms see the same compact candidate contracts in the commitment comparison. Do not give the soft branch a richer value format while attributing its difference solely to Top-N.

Do not force three candidates when only one is plausible. Record the actual candidate count and duplicate/invalid candidate refusals. Do not select N from outcomes on the evaluation roster. A model-proposed candidate is not a retrieved neighbor, and a self-reported confidence is not a calibrated probability.

The mechanism comparison can first hold the shortlist closed to measure retained alternatives cleanly; the agentic system should then test explicit reopening separately. Do not bundle hypothesis retention, new knowledge values, Whisper and a new review policy into an uninterpretable single treatment.

## Evaluation and training-free optimization

Use official full-manifest scoring and paired task outcomes. Report intent, scenario, action, official SLU metrics and joint intent-plus-slot exactness where defined. Keep micro F1 distinct from the mean of per-sample F1. Include natural-mixture, equal-stratum and per-stratum results.

After sealing, use gold only in analysis to report:
- Correct-intent recall of the first-pass Top-1 and Top-N.
- Incorrect Top-1 decisions rescued by final joint resolution.
- Correct Top-1 decisions spoiled by final joint resolution.
- Failures where the correct intent was absent, present but rejected, or selected with incorrect slots.
- Unsupported arguments, evidence ownership errors, shortlist escapes, tool calls, returned evidence use and valid termination.

Conditional filling statistics diagnose a component; they do not replace paired complete-task outcomes. Candidate recall measures available opportunity, not realized task gain.

Once the loop is viable, training-free optimization can propose policies for candidate width, contract view, evidence acquisition, reselection and stopping. Use TRAIN trajectories and task rewards to admit compact policies or corrective memory; keep evaluation data isolated. Do not optimize only final answer wording or reward greater tool usage. Quality remains primary; latency is not an objective.

## Existing evidence and scope

The historical Audio2Tool SELECT/FILL configuration retrieves 32 knowledge candidates, then locks selected tool occurrences before filling. Its Top-32 retrieval is not equivalent to a retained Top-32 intent hypothesis set at FILL. The closed 104-row v1 result tied the matched two-answer-contact joint control on exact match, so decomposition alone was not established.

See docs/readiness/2026-09-12-audio2tool-stage-knowledge-root-review-v1.md for the historical score definitions and diagnostic partitions. This design makes no new model, speech, tokenizer, encoder or scorer contact and does not change a closed verdict.

## Concrete implementation consequences

The current SLURP phase material parses one predecessor intent and supplies only that intent's schema; configs/probes/slurp_phase_slots.txt prohibits revising it. The current intent-to-slots delivery also takes scenario/action from the direct predecessor. Therefore a Top-N prompt alone would not implement joint resolution: add a registered hypothesis state/view and a delivery rule that takes the final joint model decision as authority for both intent and entities. Keep the historical state and delivery rules unchanged under their existing configuration identities.

KU-S4N's eight-item model-free candidate bank is not this proposed hypothesis state. Its closed non-inferiority failure remains recorded. Audio2Tool's selected-occurrence list represents requested calls, not mutually exclusive alternatives. Reuse its source-binding machinery only with explicit new hypothesis semantics; never reinterpret historical sealed lists.

The shared native knowledge action currently selects a view, but does not declare a dedicated shortlist-widening action. Add that argument/state transition to the shared registry when its separate experiment is admitted; do not claim that candidate-set reopening is already implemented.

## Reviewed implementation boundary

The shared hypothesis state/view and final-authoritative delivery were merged at 1bc8f347264a63b9a0cdb6c78283f9dd603ea4ce after review. The integrated native, phase-material, hypothesis and delivery checks passed 178 tests in WSL. The view validates source-bound, ordered, unique legal alternatives; the new final delivery accepts the final legal intent and entities without silently restoring the predecessor intent. Historical delivery remains registered separately.

The model-facing native action should contain only compact candidate IDs. Put schema version, sample identity, hashes and custody in runtime-owned records. The more verbose hypothesis artifact is useful for fixed component comparisons, but forcing all its bookkeeping into a 256-token model response would consume task space without adding evidence. A returned task contract is knowledge about labels and fields; it is not evidence that a field value was spoken.

Keep candidate lookup, a bounded closed-shortlist commitment comparison, and later candidate-set reopening distinct. The current final-authoritative rule permits and records a legal out-of-shortlist answer. A closed-shortlist experiment must configure and enforce its own registered restriction; it cannot claim such a restriction merely because a prompt recommends staying inside the list. No full Top-N generation flight is registered by this design document.
