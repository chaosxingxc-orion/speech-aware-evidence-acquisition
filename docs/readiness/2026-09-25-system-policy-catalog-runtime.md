# Pinned complete policies through the shared runtime

Status: offline implementation and integration proof. No algorithm cell is
activated and no learned policy has been applied to research inputs. This
supersedes the pending loader/seal items in
2026-09-25-system-policy-credit-boundary.md; historical receipts remain unchanged.

## Scientific object and limit

Optimize the complete agentic execution, including the information passed between
roles, tool selection, revision, stopping and final delivery. Collect every
actual node visit and tool result, their source identities, state transitions,
the sampling decision and probability, and the complete terminal outcome.
Retain unsuccessful revisions, uninvoked optional tools, fallback and abstention.

Use component measurements to diagnose a complete trajectory. Do not promote a
Solver branch score to a system return or assign the same final reward
independently to every tool/memory item. A selected complete policy receives its
actual episode return, including a trajectory on which its optional tool was
never invoked. That is not positive or negative causal credit to that tool.

The current single episode-start state is a restricted learning comparator.
For stationary expected additive utility, a mixture of fixed policies cannot
outperform its best fixed member in expectation. It can learn which fixed
policy to select. Useful per-input context or a declared multistep policy is
required for the intended adaptive system optimizer. This code is not a
reproduction of MemRL, Training-Free GRPO or GEPA.

## Configuration contract

The optional system_episode_policy declaration has exactly these fields:

- schema: saea-system-episode-policy-config-v1.
- algorithm_id: finite-system-policy-bandit-v1, matching stage3_algorithm.id.
- snapshot and schedule: hash-pinned JSON artifacts under the data root.
- actions: an ordered list of two to four action_id/source entries.

Each action source is a hash-pinned repository file under configs/probes.
Its only fields are schema (saea-system-policy-action-v1), native_episode and
phase_tools. A complete native block is required; partial hidden overrides are
not supported. The ordinary native parser compiles every branch.

The parent declares the common service/program budget and permitted tool
authority. A selected branch can have a lower actual contact ceiling, different
native control settings and a subset of those tools. It cannot add authority,
change tool source parameters, alter the shared knowledge-index or Solver-hint
binding, change local worker geometry, or introduce Solver-only supply variants.
Nested optimized supply decisions are refused. All branches share the original
speech input, model, material builder, request/fit gate, source roots and common
program. No alternate executor, service manager or model is introduced.

The action identity includes its full compiled native config, common program,
raw action asset hash and model/baseline fragment hashes. Keep semantic model
and baseline fragments frozen across a learning cycle; put round-specific
snapshot, schedule, fit identities and preparation bindings in the experiment
fragment. Composition already refuses cross-fragment key collisions. Admission
must retain the same execution implementation and referenced source assets
across the compared rounds; this bounded catalog is not permission to reuse
learned values after an unreviewed implementation or material change.

## Runtime and seal

Preflight loads the pins and verifies the entire ordered roster and split.
Partial-round resume does not silently resample a policy. The shared
FlightRuntime binds each action using the ordinary tool dispatcher and native
execution binding. The existing selector chooses before the first model/fit
contact and runs the selected complete graph.

Actual per-action tool receipts and episode counts are returned in the dispatch
receipt. The unused parent dispatcher is not reported as if it had executed
the selected tools. Neural speech providers are not attached to a selected
branch that lacks their tool authority; the ordinary historical path is
unchanged.

At seal, reload and verify the pinned catalog once, then verify each row's
selection against its original query/speech and frozen allocation. Enforce its
own contact/role ceiling and terminal configuration. A shorter selected policy
cannot borrow the parent's larger revision allowance. Existing response,
delivery, finite-path and source custody checks still apply.

The native source reader repeats catalog/config checks in the retained clean
checkout and requires the explicit data root for a selected-policy source.
It validates the original native terminal rules and refresh rules per row,
then runs the existing full role-contact trace diagnostics. A receipt without
a registered catalog is rejected. Historical unarmed sources take their
original path.

The candidate credit entry invokes this source reader before terminal arithmetic.
Its output remains runtime_application_authorized=false: usefulness of the
actions and the next registered flight are separate scientific decisions.

## Engineering proof

Actual OpenJiuwen graphs with fake model transport execute two selected complete
policies through FlightRuntime. One delivers after the first Solver; the other
revises and delivers the second Solver. The armed fixture additionally exposes
a tool only to the selected Reviewer, executes it through the existing dispatcher,
and verifies its invocation/result custody and per-action receipt. Both graphs
seal and pass the post-seal selected-source reader.

Tests also reject changed assets, escaped pins, excess budgets, added tool
authority, altered prebound source bindings, different algorithm labels, wrong
rosters and unregistered receipt choices. The first concurrency fixture used a
two-party barrier while FlightRuntime intentionally admitted one row at a time;
removing that unrelated barrier fixed the test. No production scheduler or
service geometry was changed to accommodate the fixture.

Validation: 248 focused tests passed before the final dispatch-receipt addition;
131 affected tests passed after it (overlapping populations). All nine required
offline checks passed. The OpenJiuwen check was first invoked without its
required output argument, then rerun with it and passed all six framework proofs.
These are model-free/fake-transport checks, not a scientific pilot or efficacy
result. No new model, tokenizer, encoder, ASR or official-score contact occurred.

## Next scientific boundary

1. Close the already running evidence-path pair, including both full official
   scores and the registered paired terminal verdict, before reading outcomes.
2. Trace information across the whole episode: was evidence absent, requested,
   obtained, normalized, consumed, acted on, and retained in the delivered
   answer? Distinguish repairs, harms and unchanged errors. Observational
   associations are not automatically causal component effects.
3. Admit only a small set of executable complete policies with named scientific
   uses. Run complete matched trajectories; preserve ties and counterevidence.
4. For adaptive selection, define the decision boundary first. For example,
   candidate disagreement is available after Perception, and audit/evidence
   findings after Reviewer. Neither can enter an episode-start choice.
   Couple evidence acquisition with downstream consumption/revision/stopping.
5. Freeze the collection policy for a complete construction round; update from
   verified final official counts plus separate intent/format/fallback facts;
   freeze and reexecute. Compare with the incumbent and best fixed policy.
6. Replicate complete-system gains on the registered roster and exposed
   regression populations. Fresh DEV6570 and test remain closed. Do not reopen
   semantic-delta, F10 or VAR-2 recovery lines.

The evidence-path flight continues from frozen commit
da443cdc1027b3c01034c26485805240ec0e671d. This implementation is merged separately
and does not alter that flight's configuration, model state or queue.
