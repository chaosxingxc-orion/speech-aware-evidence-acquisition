# Next Stage-3 family: coordinated evidence and repair policies

Status: root design following owner system-level steering and complete-source
diagnostics. Not a GPU registration or a finding of algorithm benefit. F10
is complete and not qualified; fresh DEV and test remain closed.

## Decision and empirical basis

Optimize an executable path through the agentic system, not an isolated prompt,
example count, retrieval hit rate or Solver branch score.

The complete PLAN/PLANR diagnostic found low repair reach, only nine complete
reasoning repairs in total, and offsetting harms. All nine repairs survived
delivery. The next study therefore targets whether supported problems reach an
effective repair path, while continuing to measure downstream loss rather than
assuming it already explains the observed failures.

Full-context E36b replay demonstrates available new evidence on 613/625 and
614/625 inputs. However, protocol text in Reviewer states becomes lexical query
material, including a token split out of a textual tool-call marker. Novelty does
not establish relevance. Keep the existing retrieval and native routing seams;
do not activate the held raw-review E36b cell unchanged.

This is a coordinated intervention at Reviewer -> Planner -> acquisition ->
Solver -> review -> delivery. Focusing the first system family on this path is
deliberate; it does not require changing every component simultaneously.

## One common engineering boundary

Correct the unavailable-tool instruction through versioned role configuration.
Apply the correction equally to the matched new control and treatments, preserve
the locked historical baseline, and report the bridge separately. Do not call an
interface correction a training-free RL improvement.

Reuse existing native role configuration, registered acquisition policy, context
projection and evidence renderer, shared controller, FlightRuntime and
OpenJiuwen executor. The old task-contract tool repeats available instructions;
re-enabling it alone is not useful acquisition. The prior R-PRIM and audit-context
experiments were not qualified; do not rename and rerun their isolated prompts.

A review must distinguish an actionable issue from a textual tool invocation,
routing token, status message, parser failure or unsupported opinion. Preserve
original text and source hashes. Unknown or invalid structure is explicit and
cannot silently turn into a plausible query or a fabricated confidence score.

## Executable policy contract

The following fields describe the information contract to map onto the existing
framework, not a requirement for a new controller or agent implementation.

| Boundary | Required information | Permitted decision |
| --- | --- | --- |
| Solver -> Reviewer | Original speech identity, current answer, candidate identities, selected knowledge and provenance | Identify a specific answer field or candidate distinction that lacks support |
| Reviewer -> Planner | Issue type, affected field, cited available evidence, missing information and an uncertainty flag | Accept, revise using existing evidence, or acquire an admitted kind of evidence |
| Planner -> acquisition | An explicit information need and clean query terms, source issue identity, already supplied IDs | Search the bound store under a bounded item cap |
| Acquisition -> Solver | Source-bound returned items, the issue they address, empty/error disposition | Revise only with evidence; preserve unsupported uncertainty |
| Solver -> final review/delivery | Revised answer, prior answer and actual evidence/action history | Deliver through the registered rule or the registered finite fallback |

Query words must come from the explicit information need. Protocol wrappers and
action names are not evidence needs. Exclude previously supplied IDs over the
complete prefix, not just Perception's prepared supply. Keep the full retrieval
receipt even if the model later ignores the evidence.

Do not force every row to acquire or revise. An empty result is not proof that
the answer is correct, and successful tool execution is not proof of useful
information. A missing boundary retains an explicit no-action episode.

Solver retains final-answer authority. Reviewer proposes issues; Planner chooses
the bounded next action. An acoustic tool is a later admitted action for an
acoustic uncertainty, not a mandatory preprocessing pipeline. Knowledge lookup
cannot resolve every acoustic ambiguity. Likewise, a wrong intent outside the
candidate set requires a separately admitted candidate-recovery transition;
do not silently let a revision violate the existing candidate contract.

## First complete-system comparison

Use the same exposed R01C625 construction roster and frozen minus-R01 knowledge.
Keep geometry, original speech representation, output limits, scorer, population
and delivery rules matched. No knowledge-count sweep.

1. Common-interface control: the full four-node system with the declared role
   interface correction, retaining its ordinary accept/revise path.
2. Coordinated evidence policy: the same initial path plus supported issue-driven
   acquisition, clean query material, source-preserving supply and bounded repair.
3. Preserve the historical locked plan and best qualified fixed system as
   reference points. They do not replace a same-window matched control.

The decisive comparison is the final complete manifest. Use official pooled
SLU-F1 with the registered intent guard, all scenario strata, natural/equal
weights, empty-target FP, nonempty FN/FP, failures and total contacts. A positive
construction interval alone is not stable benefit: replicate the admitted
comparison on the same roster before considering a new one.

Also report repair reach, correct repairs, new harms, newly delivered evidence,
revision acceptance and whether correct intermediate changes survive delivery.
These are explanatory diagnostics, not substitute endpoints. A path can improve
a local answer and still lose at terminal delivery; keep both observations.

A deterministic all-roster query/rendering pass and four-row engineering smoke
only prove executable wiring. Actual complete request capacity and exact contact
ceilings must be derived from the compiled role program before registration.
No inherited cap or unchanged geometry claim may stand in for that check.
This note intentionally does not invent a GPU budget or authorize contact.

## Sampling and training-free optimization after action admission

A sampled object is a complete episode under a declared coordinated policy,
including failed, untriggered and action-not-reached paths. Every optimized
decision records its pre-action state, available actions, chosen action, actual
selection probability, policy version and all subsequent transitions.

Start with a small set of coherent complete policies. Sample alternative full
trajectories on the same input under fixed model weights and within a frozen
construction round. Do not reuse an isolated VAR-2 Solver branch as a new
system trajectory or reopen the closed VAR-2 implementation.

Use terminal official TP/FP/FN feedback, with the pre-frozen F0 utility and intent
guard stored separately. Group-relative advantage compares complete outcomes.
It does not identify which node caused a gain. Do not repeat terminal reward
at every node and describe that as a derived credit-assignment method.

The first adaptive comparator can select among these coordinated policies from
pre-action state. This is a contextual policy-selection baseline; call it that,
even though its choices affect multiple nodes. Compare it with the strongest
fixed complete policy under matched sampling. A single Solver supply bandit
remains a restricted comparator, not the primary system optimization space.

For a genuine multi-step extension, separately define and implement the
conditional policies at review/acquire and repair/stop boundaries, the logged
probabilities and the return estimator. Update external action values or bounded
experience memory only after a complete scored construction round, then execute
again with the updated policy. Freeze evaluation and prohibit its feedback from
updating either memory or selection.

Memory stores a supported state-condition, coordinated action, terminal effect,
uncertainty, contradictory trajectories and provenance. It does not store the
training dataset as memory or turn a lucky answer into a rule. Knowledge
continues to carry stable task facts and distinguishing/explanatory values.

Training-Free GRPO and MemRL comparisons must follow the source-fidelity audit.
A prompt edit by the root, one reflection, a hand-selected configuration or
one numerical update is not a full reproduction of those methods.

## Immediate sequence and stopping conditions

- F10 is closed with benefit not proven. Keep its representation-only interpretation
  and the incumbent knowledge; no selected-scenario rescue.
- Land the complete-trajectory, availability and query-surface reports in master,
  and maintain HANDOFF-TO-FABLE51.md.
- Map the above interface to the existing native configuration and typed state
  machinery. Resolve the protocol-to-query path without creating a new executor.
- Register the matched whole-system comparison, including exact preparation,
  capacity, source versions, budget, one-shot recovery and analysis bindings.
- Fly through the durable WSL-backed queue, score once per complete manifest,
  and read only after the comparison is sealed.
- Admit sampling/learning only on executable system actions with whole-system
  evidence. If clean acquisition is inert or harms final quality, stop or name
  the responsible cross-node information deficit; do not enlarge N blindly.

No new owner preference is needed to continue the authorized SLURP construction
work. A proposed expansion to closed data or a changed scientific objective would
need a concrete separate decision. Existing closed lines remain closed.

## Implementation choice after inspecting the existing framework

Use the existing on-demand semantic target-knowledge tool for the first family.
Its request already names a store, candidate identities and the distinction to
resolve; existing source-bound indices connect authored knowledge to consumption.
This avoids interpreting arbitrary Reviewer/protocol text as a lexical query.
Reviewer may invoke it during its native tool loop, then Planner chooses whether
Solver should revise with the recorded result. No new acquisition framework is
needed. E36b remains available, but its unchanged raw-review policy stays held.

Reuse probes/slurp_native_role_reviewer_evidence_v1.txt with no mandatory call,
and reserve-final-report in both matched arms. Expose only semantic lookup to
the treatment Reviewer; omit the duplicated task-contract tool. Keep all other
runtime fields matched. See the evidence-path readiness package for concrete
held cells and remaining admission work. This is a complete fixed-system policy
comparison preparing actions for learning, not an adaptive RL result.


## Root continuation decision: optimize the realized system path

This section incorporates the owner's system-level steering and the actual
pre-Solver state audit, before reading the active evidence-path pair. It is
a design decision, not another registered flight or an implemented contextual
selector. The current episode-start selector and its pinned catalog are
implemented. The later decision boundary described here is not.

The optimization unit is the complete delivered episode under an executable
coordinated policy. A policy may change one boundary or several; changing every
component at once is not required. Its acceptance depends on the complete
system outcome, including consequences at unchanged downstream nodes. Treat a
component score, knowledge novelty or successful tool execution as a diagnostic.

Use the verified trajectory to distinguish the following failures:

| System boundary | Diagnostic | Optimization question |
| --- | --- | --- |
| Perception to candidate contract | Correct-label coverage and exclusions, measured offline | Does the permitted action space leave a recoverable answer available? |
| Problem recognition to evidence acquisition | Issue, actual tool choice, clean arguments, returned sources and empty/error results | Did the system obtain information relevant to the unresolved distinction? |
| Evidence to Solver revision | Actual supplied content, old/new answers and support | Did the continuation consume the information without introducing unsupported changes? |
| Revision to final delivery | Repairs retained, reversals, parsing, fallback and final output | Did the local change improve the delivered task result? |
| Complete episode to policy update | Terminal counts, intent, failures, chosen policy and probability | Which observable state benefits from which whole continuation? |

Keep these as linked observations of one trajectory. Do not count a source
being supplied as proof that it caused a correction. Do not condition primary
evaluation on a tool firing, revision being reached, or a sample improving.
Diagnostic strata cannot replace the complete population.

The PLAN/PLANR audit found nine complete reasoning repairs, all retained at
delivery. Its immediate deficit is sparse effective repair and offsetting
harms, not observed disappearance of those nine repairs. Continue measuring
downstream loss in new policies without asserting that mechanism in advance.

### Select only after the decision state actually exists

For the first contextual comparator, execute one shared Perception prefix.
At its completion, construct the same source-bound default20 preview and
normalize distinct candidates with the existing shared parser. Select a whole
continuation before action-dependent supply or the first Solver request.

Use the four populated agreement bins from the registered state audit as the
initial proposed state. Keep candidate width and identities as diagnostics;
do not multiply them into sparse state cells. The existing no-exemplars state
remains an explicit fallback if encountered. This state is not confidence,
proof of an action effect, or a guarantee of statistical power.

The audit observed agreement-bin changes on 6/625 repeated inputs, compared
with width changes on 93/625. All 1,250 historical episodes reached the boundary.
Neither observation licenses assuming that every future episode will reach it.
Do not use Reviewer findings, later evidence, revised answers or official
labels in this earlier choice.

A continuation is a pinned complete downstream configuration: permitted
evidence acquisition, role contexts, bounded Planner routes, Solver revision,
review and terminal delivery. The first action set must be small and grounded
in complete-system evidence. Preserve the default continuation. Define its
actual members only after the current pair is sealed and interpreted under its
prospective rule. A failed fixed-policy experiment is not reopened by selecting
a favorable subgroup after seeing its results.

### Reuse the native graph, without a second Perception or executor

Implement an optional model-free selector after the existing perception_state
component in the same OpenJiuwen Workflow. Reuse the existing branch router and
role-construction helpers for uniquely named continuation branches and one
terminal join. Retain one graph invocation and the original Perception contact,
request history, speech identity and cost. Preserve the unarmed graph unchanged.

The runner callback must select from the newly staged Perception context,
before resolving first-Solver supply, then commit that transition exactly once.
An ordinary settle followed by a later selector loses that precise boundary.
Request composition, tools and subsequent role configuration must read the
selected binding consistently; replacing only the supply callback is insufficient.

Preflight must prove identical Perception and fixed preview definitions across
all actions. Shared service geometry alone does not prove a common prefix.
Keep the common finite ceiling and verify each selected continuation, including
the prefix contact, at seal and during source validation.

Record a new versioned continuation decision, separate from the existing
episode-start schema. Bind the actual Perception response/state, original
speech/query, default preview and selected value IDs, state definition,
snapshot, schedule, action definitions, selected sources, actual probability
vector and draw, and receipt hash. Emit it before the first dependent request.
Only the realized branch may produce contacts. No model-logit propensity is
invented for choices made internally by the frozen language model.

### Preserve episodes whose decision is never reached

Keep a prefix failure or other pre-selection terminal disposition in the
complete-system outcome and cost denominator. Record an explicit
decision-not-reached event and its source. Assign no action value, fabricated
default choice or zero-reward credit to an action that was not chosen.

For balanced collection, PolicySchedule already reserves a state-independent
action allocation at each roster position. An unreached position keeps its
reservation; do not reassign it to a later row. Its reservation is not an
executed policy decision. Preserve the actual probability vector for each
reached choice against the original complete schedule.

The present numeric updater requires a decision on every row and remembers
completed rounds through credited trajectories. It therefore needs explicit
round-completion accounting before admitting this later selector: account for
every roster position as reached or unreached, credit only reached decisions,
and reject a duplicate complete round even if every decision was unreached.
Do not remove failed rows or pass a shorter roster to the current updater.

If a policy was actually selected and its optional tool never fired, its
terminal outcome still credits that whole policy. That differs from a failure
before policy selection. Neither case awards causal credit to an unused tool.

### Learning and evaluation boundary

Collect complete trajectories under a frozen construction-round policy, score
the full manifest once, and update external values only after complete feedback
and round accounting. Use terminal official counts with the frozen F0 utility;
retain intent, format, failures and costs separately. Execute again after the
update. Evaluation freezes the policy and cannot update it from labels.

Compare the learned continuation policy with both the locked system and the
strongest fixed complete continuation under matched evaluation. The
episode-start selector remains a fixed-policy learning comparator. A later
single contextual choice is still a contextual bandit, even though its selected
continuation traverses several nodes. Multistep optimization needs separately
defined subsequent decisions, probabilities and a return/credit estimator;
copying terminal reward onto each role is not that estimator.

Do not enlarge the engineering scope while waiting for the active comparison.
Finish its whole-system read first. Then implement the minimum graph and
round-accounting extension needed by the admitted algorithm family, with
focused tests for actual ordering, branch authority, prefix failure, balanced
reservations, all-unreached rounds, concurrency and unchanged default behavior.
No current GPU source, protocol, data boundary or scientific threshold changes.
