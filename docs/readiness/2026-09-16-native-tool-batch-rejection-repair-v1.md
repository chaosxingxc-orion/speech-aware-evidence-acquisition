# Shared native tool batch rejection repair

Date: 2026-09-16. Root reviewed the shared change. This is an engineering proof,
not a new scientific result or a GPU launch authorization.

## Failure and bounded behavior

The original typed-context system aborted when Reviewer emitted multiple tools in
one completion despite parallel_tool_calls=false. The single-action guard rejected
before dispatch, but did not settle that completion with source-bound feedback.
The next framework request encountered an unsettled tool-bearing source.

Reject the entire batch before any tool execution. Preserve the original assistant
and every raw call identity and argument. Bind one rejection result to each original
call, retain the entire ordered batch, settle once, and let the normal framework
continue within its existing iteration budget and reserved reporting turn.
Do not choose the first call, execute multiple tools, add evidence, increase the
action budget, or silently substitute an answer. Keep ordinary single-tool paths.

The common dispatcher, framework rail, source authority, history projection,
role context selector and exposure audit implement this behavior. Rejection is
feedback about an invalid action, never an executed tool observation or task fact.

## Verification

- 238 tests across 15 relevant modules passed, zero failures; three existing
  third-party deprecation warnings.
- Actual OpenJiuwen execution tests include concurrent samples, repeated rejected
  batches, the reserved final reporting turn, typed role contexts and two different
  requested knowledge stores. Model responses in these proofs are synthetic.
- Changed-file Ruff, git diff check and the engineering base check passed.
- The final wheel built without installation or editable-package mutation.
- Selected regression branch-inclusive coverage across the nine changed production
  modules is 72%. This is not complete-repository coverage. Pyright was unavailable.

The proof made zero experimental model/tool contacts and did not read either current
arm's task-quality values. No live-model four-row proof has run yet.

Receipt: DATA/coordination/slurp-typed-context-vs-direct-v1/native-batch-rejection-repair-proof-v1.json
SHA256: 3bcb86237986e34e94e815dbe4068d620385f063e8a3a94d6d269c2663bea79e

## Recovery boundary

Keep the failed f3189ce2 checkout and aborted original system attempt immutable.
Retain the completed 1080-row direct source and its one complete score, quality unread.
Use a fresh registered four-row subset drawn deterministically from the already
exposed TRAIN A roster for the live current-configuration engineering proof.
The old intent-hypothesis engineering4 configuration contains DEV rows and must not
be mistaken for a TRAIN A subset or copied as its population.

After that proof seals, separately register the sole full1080 system recovery,
with fresh generation/FIT identities and the unchanged scientific configuration.
Do not splice the aborted507-contact prefix, rerun the completed direct arm, or
introduce another mechanism. Preserve the resident decoder-only service geometry,
prepared features and absent GPU mmproj. Keep paired task-quality reading held until
the complete system source and its first complete official score are sealed.
