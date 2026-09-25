# Candidate-recovery seal failure: raw positions versus distinct labels

The control generation completed all 625 output rows and 3,723 model contacts.
At 2026-09-25T20:59:06Z the durable driver stopped after the bundle verifier
raised SlurpIntentHypothesisError during FlightRuntime.seal. The attempt is
ABORTED despite the already-written manifest having status COMPLETED.
No official score job ran; expanded smoke and expanded625 did not start.

## Named cause and shared repair

validate_candidate_proposal_consumption reconstructed an authority set from
the original/expanded proposal and actually selected exemplar targets. It
passed min(3, number of authority labels) as the parser's candidate limit.
That limit constrained both raw positions and projected distinct candidates.

The registered first-occurrence projection permits repeated labels in up to
three raw positions. If all supporting labels collapse to one, a legitimate
three-position response was therefore rechecked as a one-position response.
Two distinct authority labels could cause the analogous failure. Runtime
parsing used the full legal inventory and did not have this reduced bound.

The shared parser now supports an explicit raw-position bound for this
bounded-three seal projection. Canonical projected candidates still obey the
actual authority inventory and distinct-label limit. Every raw object is
validated; unknown labels and excess positions still refuse. Default runtime
calls retain the prior behavior and identity. No prompt, model setting,
knowledge selection, final answer or registered scientific contrast changed.

## Evidence without task-quality exposure

Eight complete OpenJiuwen graph tests cover four raw candidate shapes in both
proposal modes. Before the fix, four duplicate-collapse cases failed and four
other cases passed. After the fix, all pass. These are synthetic transport
cases, not eight research model calls or measured task outcomes.

The related suite passed 116 tests; all nine offline checks passed. Under the
separately registered model-free structural read, the repaired full bundle
verifier accepted all 625 original rows. All seven pinned source artifacts
remained byte-identical. The raw-position/distinct-label histogram is retained
in the proof receipt; it is not candidate coverage or intent accuracy.

See docs/receipts/continuation/2026-09-25-candidate-recovery-seal-repair.json.
No official scoring, gold join, source rewriting, model call or attempt-state
change occurred during diagnosis.

## Recovery boundary

The existing experiment explicitly allows at most one root-diagnosed recovery
with fresh generation and fit attempt identities after four-row proof.
Its second failure closes the flight. Infrastructure resume is inapplicable:
core.flight.resume permits unchanged-code infrastructure failures, not a
harness defect. finalize_bundle also refuses an ABORTED attempt.

Keep the old failed source, frozen checkout, original registrations and all
costs. Do not relabel those 625 outputs as a new successful generation, reopen
the attempt or invoke a finalizer behind the queue. Prepare a separately
registered fresh recovery on the same roster, prompts, knowledge, geometry,
contrast and decision rule. Use the shared durable driver, conduct its
registered structural smoke and maintain the outcome embargo until both
complete scored arms seal. No recovery has been dispatched by this repair.
