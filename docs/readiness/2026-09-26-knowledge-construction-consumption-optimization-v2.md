# Separate knowledge construction from sampled knowledge consumption

For the owner's subsequent intent/slot separation and a correction about the
existing finite supply sampler, read
[task-specific stores and consumption views](2026-09-26-task-specific-knowledge-stores-and-views-v3.md).

## Owner clarification and resulting experiment order

The owner requires two optimization stages. Construction must produce accurate,
compact and discriminative knowledge. Consumption must retrieve relevant knowledge
and support sampled retrieval/supply decisions instead of loading the entire store.
Retrieval performance is an explicit optimization target. Complete-system task
outcomes remain the endpoint; neither better text nor retrieval alone proves gain.
This note supersedes the optimization order in the earlier knowledge-RSI design.
It registers no model, tokenizer, encoder, scorer or external API contact.

Keep separate intent and slot stores. Intent recognition and slot extraction are
distinct related tasks. Candidate intents can condition relevant slot roles; the
observed slot evidence can also justify revising intent. Intent-label coverage and
knowledge-card coverage are different diagnostics and must remain distinguishable.

## Stage A: construct a frozen candidate knowledge version

An offline generator proposes source-supported semantic edits. Optimize accurate
definitions, distinguishing conditions, confusable alternatives, extraction roles,
span/value boundaries and absence/ambiguity behavior. Preserve supporting sources;
do not turn one observed output error into an unsupported universal rule. Grammar
validation and source hashes establish custody, not the truth of generated claims.

Keep key, value and intent-role binding changes separately identifiable. Current
intent activation text enters both key and value; independently optimizing them
requires a shared field boundary first. Current slot routing uses intent bindings,
so editing an unused textual slot key is not a retrieval improvement.

The already implemented slot-value compiler is a bounded construction interface,
not the whole optimization algorithm. It edits existing value fields, preserves
keys/bindings, retains no-change and all construction ancestry, and creates only
candidate rows. Validate semantic consistency with the locked ontology and governed
TRAIN support before release. Mark unresolved empirical advice as a hypothesis;
do not treat generator confidence as a factual qualification.

Compare K0 and candidate K1 using the same frozen consumption policy C0 and the
same full actor. Re-encode changed keys only when necessary, with registered tool
contacts. Never use a reference transcript as a runtime retrieval query. A later
batch tests a frozen candidate; descriptions cannot change during its execution.

## Stage B: sample consumption policies over one frozen knowledge version

Use the ordinary provider path: observed state -> candidate rankings -> bounded
selection -> materialized supply -> full agent trajectory -> terminal feedback.
The store stays on disk. Only the selected packet enters the relevant role.
Proposal-generation feedback is an offline construction context and must never
be mistaken for runtime knowledge supply or exposed to evaluation actors.

Initially sample among a small registered set of meaningful consumption policies,
rather than sampling arbitrary facts or injecting unrelated cards. Potential
actions include relevance-first versus confusion/diversity-aware ranking, bounded
retrieval width, candidate-conditioned slot-role selection, and removing redundant
cards under a common token envelope. Choose only actions supported by the existing
provider or a small shared extension, and retain the incumbent policy. Do not vary
all these factors at once in the first comparison.

Exploration changes which policy or evidence packet is selected; ordinary decoder
temperature alone does not constitute retrieval exploration. Record the pre-action
state, eligible pool, scores, selected policy, selection probability, random seed,
ranking/selection order, omitted items and final supplied bytes. Uniform selection
among a finite action catalog gives tractable policy probabilities. If later
sampling ranked lists without replacement, log the actual conditional probabilities;
never invent propensities retrospectively.

Every sampled consumption action must finish through Solver, Reviewer, Planner,
revision when chosen, and delivery. Existing VAR-2 non-delivering Solver branches
do not supply whole-system returns. The existing complete-system policy catalog
currently permits native behavior and tool settings only; it does not rebuild
knowledge routing per selected action. Register and validate that shared binding
extension before claiming online learned retrieval through that catalog. The
separate finite_supply_policy path already supports sampled exemplar-route
actions and complete downstream execution; reuse it within its supported scope.
It does not yet sample semantic-card views or provide the corresponding verified
credit updater. Serial full configurations
are sufficient for the first matched policy comparison and require no new runner.

## Feedback and learning

Record the following layers without replacing one with another:

| Layer | Measurements and interpretation |
| --- | --- |
| Construction quality | Source support, ontology consistency, contradictions, duplicate information and explicit distinction boundaries |
| Retrieval | Relevant-card recall/precision at the actual budget, candidate-intent coverage, ranking quality where graded relevance exists, and redundancy |
| Delivered information | Needed card retrieved but dropped by the budget, actually supplied values, entity-role coverage and input tokens |
| Whole system | Official aggregate SLU-F1, intent accuracy, exact slots/task, entity FP/FN, failures, revisions and final delivery |

Only call a retrieval number precision, recall or nDCG when its relevance target
has been defined. Gold-intent inclusion or ontology-compatible slot-card coverage
is a labeled proxy, not a complete knowledge-relevance annotation. Such references
belong to registered offline scoring only, never to the runtime query or selector.
Do not reward a retriever for returning more cards while consuming more tokens
without reporting that difference. Keep a common input/output envelope and report
quality against supplied token volume.

During each matched sampling batch, freeze the knowledge version and policy
parameters. After all complete trajectories and official scores close, update
external consumption-policy values from system returns. Return observed retrieval,
supply and consumption failures to the offline constructor for the next knowledge
candidate. This is alternating optimization, not two disconnected pipelines.

Distinguish these failures: useful knowledge absent from the store; present but
not retrieved; retrieved but budget-excluded; delivered but ignored/misused; useful
local correction later overwritten. The same final error cannot identify its
cause without this trace. Component metrics diagnose the failure; terminal system
feedback decides promotion. Update after every complete sampling batch as ordered.

## Minimal comparisons and implementation checkpoint

Start with K0/C0, K1/C0, and K0/C1. If both interventions are usable, add K1/C1 to
measure their interaction. Do not assume their improvements add. Freeze the best
fixed candidate as a comparator for a learned selector; configuration search alone
is not evidence of RL benefit. Construction batches stay small and source-disjoint
from evaluation; stable gains require the pending full-roster evaluation and
same-roster replication. DEV6570/test13078 remain closed.

The current actor geometry remains two live slots, four distinct inputs and four
trajectories per arm, executed serially by configuration. Preserve common initial
prefixes, full output reserves and resource floors. Knowledge versions, retrieval
policies and role inputs are explicit identities. Never turn batch size into GPU
concurrency or reload the entire knowledge store into the actor prompt.

Shared slot-value editing and prepared-feedback integration are implemented.
The first model-free reconstruction covers all four learned batch002 groups,
including ties, and sixteen complete trajectories. Its full semantic-request
view is 1,065,214 context bytes after deterministic sharing. It is an archival
construction input, not an admitted model request. Before generation, define a
bounded evidence view with explicit omissions or a registered hierarchical input
stage; retain all groups and complete-system events. Perform real request fit,
not a character-count substitute. No new GPU flight or candidate release exists.

Keep the current frozen actor as the matched system reference. The memory-batch
Reviewer prompt is not automatically the stable Stage-2 reference; choose and
register a consistent actor for both knowledge and consumption comparisons.
