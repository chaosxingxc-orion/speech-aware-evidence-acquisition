# Next Stage-3 family: coordinated evidence and repair policies

Status: root design following owner system-level steering and complete-source
diagnostics. Not a GPU registration or a finding of algorithm benefit. F10
continues unchanged; fresh DEV and test remain closed.

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

- Finish F10's independent chain and its already registered complete paired read.
  Preserve its representation-only interpretation even if it improves the system.
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
