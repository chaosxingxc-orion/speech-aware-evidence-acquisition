# Scoreless semantic stages in the existing background driver

## Concrete integration defect

FlightRuntime already seals artifact results as FINALIZED without task scores,
and its score stage records not-applicable with zero jobs. The unattended batch
inspector nevertheless required one official score job for every full arm.
A successful summary, comparison, group update or batch synthesis would stop
the queue after completion. It must not be made to pass by scoring an artifact
as if it were a SLURP prediction.

The existing driver now accepts result_kind, defaulting to task-answer, and
smoke_result_kind, defaulting to the main step's kind. Both accept only
task-answer or artifact and are checked before the existing GPU prelaunch.
The driver forwards the expectation explicitly to its existing inspector.
No new queue, service owner or execution framework is introduced.

## Inspection contract

A task-answer full arm retains exactly one score-job requirement. A historical
task smoke may remain OPENED and unscored, as before.

An artifact, including an artifact smoke, must be FINALIZED and COMPLETED,
declare result_kind=artifact, declare no scorers or score binding, and have
zero score jobs. Its run/attempt identity must match the queue. The inspector
calls the existing authoritative verify_bundle implementation, which checks
the actual output, trace, manifest, attempt and hash bindings. It reports
verified output counts and hashes, not an arbitrary matching filename in the
directory. A task arm cannot bypass its score requirement by requesting an
artifact inspection.

The inspector is read-only. It never calls a scorer, retries a worker, edits
a manifest or prints task text. Its operational summary does not evaluate
the scientific adequacy of a semantic update. Downstream prepared-text source
verification and typed memory validation still govern source consumption.

The old eight positional arguments remain supported. The new optional
--result-kind argument is deliberately explicit: an artifact is not silently
inferred from a convenient absence of scoring files.

## Evidence and remaining work

Read the [validation receipt](../receipts/continuation/2026-09-26-background-artifact-validation-v1.json).
The public inspector CLI consumes a synthetic bundle constructed and finalized
through the real bundle path, with a simulated answering transport and a
scorer that would raise if called. Negative cases include missing/extra scoring,
wrong kind, wrong run or attempt, unfinalized/aborted source, wrong revision,
dirty source, changed output and ambiguous manifests. Legacy task smoke,
score-count, contact-limit and no-tool checks remain exercised.

This proves the inspector boundary, not a complete unattended TF-GRPO cycle.
The shell driver passes syntax checks and its two inspector call sites were
reviewed. No Windows task or real campaign was dispatched in these tests.
Stage dependency preparation, prospective configuration derivation, real fit,
complete budgets and actual multi-round execution remain required.

The existing failed queue, STOP, resident-service state, frozen generation
workers and all historical bundles remain unchanged. This change is for a
separately registered future family. It grants no launch authority.
