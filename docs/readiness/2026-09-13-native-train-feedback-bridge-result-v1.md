# Native TRAIN feedback bridge: engineering result

Status: model-free source compatibility proven; no real optimization cycle or
runtime memory admission. Preserve the live direct-versus-native DEV1000 campaign
at frozen runtime commit 7ec4cf340206d52a2cf44f65cdda278352c43363.

## Reproduced integration failure

The native executor emits contact IDs as
`program:role:invocation_index:sample`. Its separate role models each start at
index zero. The former reward-link reader assumed `program:phase:sample`, so
Perception, Solver, Reviewer and Planner all became phase `0`; distinct responses
then failed with `phase has conflicting successful contacts`.

The old continuous-program fixture had one contact per named phase and did not
exercise this native identity. Root reproduced the failure through a synthetic
finalized TRAIN bundle and its complete score receipt before changing the reader.

## Shared correction

The existing reward-link reader now takes role identity from the native-role USE
event and joins its contact ID, request hash and response hashes to the exact
model request/response. It preserves all response identities for a revisited role.
Legacy one-contact phase validation keeps its original semantics.

Native tool events have a request/tool-call hash suffix. Verify their exact
source request, role and response as well as that suffix. Refuse missing role
custody, cross-role state sources and misbound tool responses. Final output stays
bound to the accepted Solver even when Reviewer and Planner execute later.
The change reads source records; it introduces no answering path or runner.

## Evidence and limits

All 137 focused reward-link, grouped-feedback, proposal-context and memory-source
tests passed in WSL. Targeted Ruff and the engineering-base check passed. An
independent source review found no concrete defect.

The native synthetic fixture contains nine contacts per sample: Perception,
Solver, a Reviewer tool/continuation pair, Planner, revised Solver, another
Reviewer pair and final Planner. The final output names the revised Solver,
not the last contact. Negative cases retain valid outer bundle and score bindings
while testing incorrect role IDs, request hashes, missing role events, cross-role
states and native tool sources.

The downstream synthetic pair passes the actual grouped-feedback and legal
proposal-context builders. All nine contacts and the selected Solver survive;
source identities remain outside model-facing proposal text. This proves the
native trajectory-to-feedback preparation seam. It does not prove a model can
produce useful corrective experience or that an updated system improves quality.
No current DEV1000 response, score or diagnostic was read. No new model, encoder,
tokenizer, ASR or official-scorer contact occurred for this implementation.

## Remaining first-cycle work

The source-compatible shared pieces are finalized TRAIN task runs, complete
native scores, reward links, grouped quality feedback, legal proposal contexts,
TRAIN experience-source attestations and frozen runtime memory consumption.

The config-driven proposal/update and selection/admission path remains missing.
It must dispatch a separately registered gold-free proposal role to the same
frozen core, parse bounded provisional edits, evaluate candidate versions on a
predeclared disjoint selection cohort, apply the frozen admission rule and emit
an immutable validated version. Selection is optimization data; subsequent
frozen evaluation disables updates. Never relabel provisional records admitted
merely to make a validation run executable.

Select the actual state/action question after the current complete-system read.
Current DEV1000 material may diagnose a mechanism but cannot become TRAIN memory
records or proposal examples. Keep native quality vectors and the full-cohort
metric in the eventual validation; group-normalized row feedback is not the
cohort micro-F1 estimand. Cross-carrier feedback and candidate-validation support
need their own task-native proof. This note registers no additional GPU flight.
