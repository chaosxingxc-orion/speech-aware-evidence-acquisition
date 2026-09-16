# Source-bound role-context implementation

Date: 2026-09-16. Root owns design, review and experiment admission.
Status: implemented and model-free verified; the registered paired campaign is described
in STATUS-153. Task benefit remains unverified pending complete paired evaluation.

## Scope

Implement the owner's role-specific analysis, cleaning and normalization contract through
the shared native role binding. Keep canonical episode history, knowledge providers,
original query speech, tools, routing and final Solver authority unchanged.

The config selects a registered ROLE_CONTEXT_COMPILERS factory. Bind legal candidates and
their maximum to the actual Perception response schema. Keep the draft-validation schema
inside the versioned config; it does not change Solver decoding. Reject mixing the typed
compiler with the separate history-only restriction.

Use current typed candidate hypotheses for Solver/Reviewer, the latest draft for
Solver/Reviewer, draft identity and structural status for Planner, and current structured
review declarations for Planner or revision/refresh. Preserve relevant exact native tool
call/result pairs. Keep known tool-call assistant states out of report parsing.

## Information and provenance

Reuse the bounded first-occurrence candidate projection. Preserve ordering, actual width
and unresolved fields. Treat interpretations as unverified hypotheses, not observations.
Do not invent candidates or combine conflicting explanations into a claimed fact.

Require strict closed draft structure, including an explicit entity array. Preserve exact
field strings and repeated entities. A parsed draft remains semantically unverified.
A malformed draft remains source-addressable and visible as malformed; do not turn it into
a valid empty answer.

Reuse the strict structured-review parser at the shared runtime layer, retaining the old
analysis import. A malformed report is unavailable, not a no-issue declaration.
Report citation availability in the destination request only. Availability is not source-role
visibility, entailment or correctness. Preserve recommendations as declarations; Planner
decides the actual action.

Keep model-facing material compact. Store full source hashes, producer identity and
candidate normalization maps in compilation receipts. Give every derived state a distinct
identity while binding its original response hash. Keep original records unchanged.
A valid draft has one canonical parsed representation; its original bytes remain in
canonical history. Retain raw draft text in the view when its structure is malformed.

## Runtime path

Compile after canonical supply resolution and before NativeRoleSpeechBinding freezes
messages and kwargs. Run FIT and dispatch on the same prepared request. Do not invoke
retrieval, ASR, encoding, another model, or an official scorer from the compiler.

Seal per-contact compilation receipts with request/response hashes and emit ORG traces.
Record selected and excluded source versions, derivative hashes and current available
evidence IDs. Preserve existing receipts and requests when the option is absent.

Prepared configuration:
configs/baseline/slurp-native-typed-role-context-train-a-held-v1.json.
Its base is the existing held structured-review v2 configuration. The changed treatment
is the typed role-context policy and its declared draft-validation schema. This is a
system context-policy contrast, not an isolated effect for each individual field.

## Verification and scientific boundary

The focused WSL suite passed 163 tests with zero skips. The three new runtime modules
have 87 percent aggregate line coverage (compiler 87 percent, binding 92 percent, shared
review parser 82 percent). Ruff, engineering-base and diff checks passed. Three existing
dependency deprecation warnings remain. The tests exercise the actual shared episode
and flight dispatch with synthetic responses, including FIT/dispatch identity, tool custody,
current draft selection, unavailable citations, defaults and zero added contacts.

The prepared baseline differs from structured-review v2 only by the declared role-context
policy and descriptive text. Its other values are equal. Both public compiler entry and
registered binding use the same closed, self-contained schema validator.

Verification receipt under SPEECHRL_DATA_DIR:
coordination/slurp-review-measurement-v1/root-role-context-implementation-verification-v1.json.
SHA-256: 13ca848f24c133e629d4e7aceaa3cdd5a924d2132318cdfc6124b8b614b06243.
Real-model capacity, review behavior and task benefit remain unverified. Do not launch this
configuration solely because engineering checks pass.

Keep the active maximum-five flight frozen. After its complete saved-score verdict,
root chooses a required replication or one useful bounded successor. Do not automatically
add the history-only control, no-example contract, new knowledge values or acoustic tools.

Report complete official task quality, common-covered intent choice, correct-intent slot
quality, review saves/harms, actual revisions and context parse/availability failures.
Preserve all rows and all scenario strata. Manual context engineering is not training-free RL.
