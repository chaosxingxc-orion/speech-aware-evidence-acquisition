# Stage-3 optimization unit: the complete agentic system

Status: owner steering incorporated on 2026-09-25. This supersedes any implication
that optimizing Solver example count is the final research objective. Current
F10 generation is unchanged. This note does not register a new GPU family.

## Research correction

A component can improve locally while the final system does not. A downstream
node can remove a correct entity, amplify an earlier wrong intent, ignore useful
evidence, or repair the baseline equally well. These are hypotheses to test from
complete trajectories, not conclusions already established for this dataset.

Using terminal reward for a single supply knob is a valid controlled baseline,
but is not sufficient coverage of system optimization. Keep the finite supply
bandit as a restricted comparator. The main optimization object is the complete
executable policy: what each role observes, which evidence/action is selected,
what crosses role boundaries, and how the system decides to revise or deliver.

Do not promote a component winner from an isolated prefix, use a local Solver
score as system reward, or assume independent component gains add up.

## The trajectory and outcome contract

The unit is one input's actual full native episode, ending in delivered output
or a registered terminal fallback/abstention. Preserve:

1. Original speech/query identity and the runtime states available at each visit.
2. Every Perception, Solver, Reviewer and Planner visit, including repeated and
   interrupted visits; every metered request/response and its exact role binding.
3. Evidence queries, selected items, supply, tool attempts/results/failures,
   observation changes and consumption evidence. Missing instrumentation is
   unknown, not zero use.
4. State organization, context handoff, Planner route, repair target and revision
   history, retaining their original source identities.
5. Raw Solver answers, deterministic delivery rules and final delivered bytes as
   distinct artifacts. Preserve repairs and regressions introduced downstream.
6. Final official task counts, intent/format/fallback status and complete system
   contact/resource cost. This is offline feedback, never actor observation.

The export is an indexed, content-addressed view of existing frozen artifacts.
Raw text stays in its original source. A reader can resolve hashes and record IDs;
the export is not a new private trace store or a substitute for source custody.
Run/attempt identity is part of each episode fingerprint, so an independent
identical-response repeat is not mistaken for duplicate credit.

Complete terminal failures remain in the population. If a trajectory ends before
an optimized action is reached, retain its system outcome and explicit no-action
status. Do not fabricate a default action, drop the row to improve a denominator,
or count the outcome as evidence for an action that never occurred. The current
finite-policy numeric updater requires a decision per row; handling this boundary
must be specified before that restricted baseline is admitted.

## Implemented shared reader

analysis.system_trajectory.export_system_trajectories consumes a
VerifiedNativeEpisodeSource and preserves every role/contact, Planner route,
tool event, state/transition/consumption reference and final delivery. Known
truncation and illegal Planner-route evidence is explicit and source-addressable;
unavailable instrumentation is distinct from a recorded empty event list.

analysis.system_feedback.load_system_feedback binds a complete official SLURP
TRAIN result to those episodes. It reuses the shared native source verifier,
bundle/attempt checks, flight-receipt seal and official count extractor. The score
job is bound to the generation seal and completed score stage, with preserved
generation and finalized manifest hashes, successful job identity, and the pinned
score ledger. It checks the exact score population and pooled aggregate, preserving official counts
rather than silently substituting a separately reported normalized view.

Terminal feedback is a separate section. It is not inserted into node contexts.
The derived report is immutable and hash-bound; repeated publication of identical
bytes does not create another model call, scorer run or learning credit.

The source verifier requires the retained clean checkout at the recorded flight
commit. Run the new reader code from the implementation checkout while passing the
frozen source checkout separately. Do not change the active flight for analysis.

Entry: scripts/analysis/export_system_feedback.py. Required arguments are
--data-root, --source-repo-root, --binding-relpath, --binding-sha256 and --output.
The binding schema saea-system-feedback-binding-v1 declares model-free-check,
construction, slurp-slu-official-train, and confined raw-hash pins for manifest,
phases, flight_receipts and the single score_jobs record. Attached score bytes
are pinned by the finalized manifest. The retained source config remains the
authority for the complete executed program.

A shared diagnostic bug was fixed: lawful delivery normalization previously
failed the raw-Solver-equals-delivery assumption. The reader now reuses the exact
registered delivery replay validator, keeps raw generation limits attached to
raw completion, and separately records normalized delivery identity.

## Root analysis before choosing the next system intervention

Start with completed, source-bound TRAIN episodes. F10 outcomes remain unread
until both arms qualify for the registered analysis. Use existing complete
results; do not launch a fresh data sweep for exploratory convenience.

For each failure pattern, identify the earliest available evidence, the decision
that used or ignored it, the downstream reaction and terminal outcome. Separate
these cases:

- The correct intent never enters the candidate set.
- The correct intent is present, but the system selects an inconsistent one.
- Intent is correct, but entity meaning/boundary or required emptiness is wrong.
- A Reviewer finds a real issue but its output does not provide an actionable,
  supported correction; or it creates an unsupported objection.
- The Planner chooses an unnecessary or misdirected revision.
- A useful correction is lost during context organization, later reasoning or
  deterministic delivery.

These are descriptive system diagnostics. Gold can label an error offline but
cannot become a trigger feature. A causal claim needs a registered matched
complete-system intervention, including downstream behavior.

For every candidate change, report both repair and new harm. Analyze how many
local changes survive to final delivery and what mediates their disappearance.
If intermediate official scoring is needed, register complete-roster derivatives
and use the standard scorer once per derivative. Do not quietly substitute a
private approximate intermediate metric for an official result.

## Candidate optimization space

The bounded factors below are design candidates, not launched experiments.

| System decision | Observable input | Candidate action | Required downstream contract |
| --- | --- | --- | --- |
| Candidate recovery | First Perception candidates and runtime disagreement | Keep or expand using admitted knowledge/evidence | Solver receives candidate provenance and discriminating evidence |
| Evidence allocation | Candidate ambiguity, available example/slot-contract support | Choose a compact coherent evidence package | Reviewer can inspect the same answer-support relationships |
| Review and acquisition | A specific supported inconsistency or missing evidence | Accept review or invoke an admitted analytical/observation tool | Tool result is normalized and tied to the unresolved issue |
| Repair planning | Structured review, evidence source, affected answer fields | Accept or request a scoped revision | Solver owns the answer and sees a precise evidence-backed repair request |
| Context organization | Prior states and selected evidence | Preserve, normalize or omit task-irrelevant material | Roles retain required provenance and no future-state information |

Use the framework's existing nodes, routing, registries, tools and finite policies.
Availability in a configuration is not proof of useful information gain. The
negative VERIFY-1 finding prevents automatic promotion of its five-choice route;
a new Reviewer intervention needs a named evidence deficit and its own complete
system question. Closed VAR-2 and semantic-delta lines remain closed.

Avoid an uncontrolled Cartesian product. First compare a few coherent system
policies and their matched combinations, so interaction can be measured. Keep
the strongest fixed complete system as a comparator, not just direct inference.

## Sampling, credit and learning

A sampled object is a complete executed system trajectory under a declared
policy/configuration and external action schedule. Log every optimized decision's
pre-action state, available action set, chosen action and actual probability.
Do not substitute token likelihoods for an unobserved system-action propensity.

For a training-free GRPO-style comparison, form groups on the same task input,
execute complete alternative trajectories, compute terminal task feedback, then
perform the declared bounded external experience/policy update and execute again.
Grouped advantage is an outcome comparison, not proof of which individual node
caused it. A memory record should retain the condition, coordinated action,
terminal effect, counterevidence and provenance, not an isolated lucky answer.

The restricted supply bandit tests one small axis. Multi-step learning must
add explicit credit/selection semantics for downstream decisions; repeating the
same terminal reward across all nodes without a declared estimator is not an
algorithm definition. Freeze policy within each construction round and keep
evaluation outcomes out of updates.

Keep the frozen official-count utility and intent guard. Compare learned system
policy with the locked system, best fixed system policy and declared scholarly
baselines on matched rosters. Stable improvement requires replication. If a
component-only improvement vanishes in the complete system, report that failure
and investigate the interaction instead of promoting the local score.

## Next boundary

Finish F10, validate the shared complete-source export on registered sealed data,
perform root-owned cross-node error attribution, and admit a small system action
space. Complete the external sampling-feedback-update loop and same-space
algorithm comparisons on that space. The finite supply baseline remains useful
as a controlled comparison, not the definition of Stage-3 success.
