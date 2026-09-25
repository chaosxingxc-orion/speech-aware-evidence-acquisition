# Complete-episode policy selection: shared graph integration

Status: offline execution seam, not a registered algorithm flight. The active
evidence-path family stays frozen at da443cdc1027b3c01034c26485805240ec0e671d.
No GPU, tokenizer, tool backend or scorer contact was added by this work.

## Research decision

Select a coherent complete native policy before Perception, then execute its
ordinary Perception, Solver, Reviewer, Planner and permitted revision/delivery
path. This differs from selecting a Solver-only supply knob after Perception.
The action is the complete policy; its return is the delivered system outcome.

The first selector has one state, episode-start. It is a global episode-policy
bandit comparator, not yet contextual or multistep RL. Pre-Perception selection
cannot use candidate agreement, review confidence or later tool results.
Do not introduce retrospective state features to make the selector look smarter.

If an episode chooses a tool-enabled policy but never invokes a tool, retain its
terminal feedback for that real policy choice. This does not create an executed
tool action or identify the tool's causal contribution. Failed, unrevised and
registered finite fallback episodes are equally part of the selected policy.

## Shared implementation

SystemEpisodePolicy reuses PolicySnapshot, PolicySchedule and the existing
cumulative-mean update. NativeEpisodeRunBinding adds one optional selector;
the ordinary OpenJiuwen executor selects once before the first fit/model
request and runs the selected binding through its existing graph. There is no
new controller, scheduler, launcher, answering model or model-service lifecycle.

Every choice records the frozen schedule, actual conditional probability vector,
draw, roster position, query/speech identity, action-space definition and selected
source hashes. It enters the ORG trace before the first contact and the terminal
native receipt. The choice remains visible if later execution is interrupted;
partial flights are not silently turned into complete update rounds.

Actions must share their phase program, model-contact ceiling, local-worker
geometry, original material provider, request renderer/gate, source roots and
context-fit budget. The outer binding must match the same envelope before
scheduling. Runtime configuration mutation and duplicate episode selection are
rejected. Concurrent arrival order does not change frozen roster allocations.

Previously learned values must bind the same action-space and selected action
definitions. Reusing action names with changed policy definitions cannot carry
the old values forward. Source hashes in this low-level interface remain a
caller assertion until FlightRuntime validates the corresponding pinned assets.

No selector means the historical path and requests stay unchanged. No config
loader activates this seam yet. The historical grouping reader refuses outputs
with real system-policy decisions rather than erasing their selection metadata.

## Evidence and limits

Offline tests execute the actual OpenJiuwen graph with fake model transport:
two concurrent rows select different complete repair policies, preserve distinct
revision paths and record choices before first fit. A second test assigns
explicitly synthetic terminal counts, updates the frozen value table once,
then executes the full graph again under the learned zero-exploration policy.
Finite fallback feedback remains in that synthetic update.

This is evidence of executable sampling/update/reexecution plumbing. It is not
official task feedback, successful RL optimization, a scholarly-method
reproduction or authorization to fly either synthetic action on research data.
No synthetic counts or outcomes enter the experiment ledger as observations.

The registry label is finite-system-policy-bandit-v1, status planned.
The narrower finite-action-bandit-v1 remains a supply-only comparator.
Training-Free GRPO still needs its declared semantic-experience update and full
evaluation loop; this numerical bandit does not replace that baseline.

## Required next boundary

1. Finish the active complete-system control/tools pair and its sealed analysis.
   Admit useful executable actions from terminal evidence, not local tool novelty.
2. Bind any proposed action catalog from hash-verified complete configuration
   assets in FlightRuntime. Verify every action with the same shared configuration
   loader, actual request builder and finite budgets before exposing this seam.
3. Extend complete native source/seal verification to the selected per-row binding;
   join decision traces, complete trajectories and official terminal counts.
   Reject evaluation updates, incomplete rounds, changed definitions and duplicate
   credits. Do not bypass these checks with the pure update function.
4. Register the construction/evaluation schedules and all-action capacity/contact
   ceilings. Keep policy frozen within each round, then compare the learned
   complete policy with the strongest fixed complete policy.
5. Add pre-action context or multistep decisions only with their own executable
   state, action and credit semantics. A terminal reward copied to each role is
   not a multistep estimator.

No new owner decision is needed for this bounded offline work. Fresh DEV, test,
closed semantic-delta/VAR-2/F10 lines and active flight configuration remain as
previously decided.

## Validation record

The focused native execution, legacy dispatch, grouped Solver, finite update,
configuration and grouping suite passed 172 tests. The final selector/algorithm
registry suite passed 49 tests (overlapping the first suite). Engineering-base,
algorithm-label and finite-completion gates passed.

An additional broad Stage-3 run passed 553 tests and initially failed three.
The algorithm inventory expectation was updated to include the already existing
supply bandit and the newly registered whole-policy comparator; its final suite
passes. The two remaining findings are unchanged ROLL-AA fixture expectations
that still require held while their completed cells are ready. Their test and
configuration bytes equal prior commit 191e99eb. No historical experiment state
was changed to silence those failures. This is not a claim that the full test
suite is clean.

See docs/receipts/continuation/2026-09-25-system-episode-policy-engineering.json.
