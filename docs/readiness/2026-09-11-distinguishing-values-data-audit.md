# Distinguishing knowledge values: data audit and next decision

Date: September 11, 2026. Root design review during the unchanged SLURP replication. This is a source and hypothesis audit, not admission of a new experiment, knowledge version, memory, tool, or runtime label. Preserve the frozen replication and all closed historical decisions.

## Operational principle

A useful value contributes a supported distinction needed for a task decision. Identify the alternatives, the lawful observation that distinguishes them, the applicability conditions, and remaining uncertainty. Similarity is only a route to the value. A relevant item that lacks the needed relation, has an unsupported scope, or is consumed incorrectly does not establish a benefit.

Distinctions include entity presence versus absence, requested target versus incidental context, one role versus another, one operation versus a neighboring operation, and an acoustic candidate versus a merely plausible name. They need not all take the form of a pairwise explanation. A compact typed relation or qualified spelling can suffice.

Record construction support and contradictions outside the prompt. Expose only the relation and limits the Solver needs. Keep the full legal answer space; do not treat unobserved training combinations as forbidden or empty annotations as proof of absence.

## SLURP evidence and its limits

The governed TRAIN audit uses 11,514 unique utterance IDs, 60 canonical scenario/action pairs, and 55 entity types. Recordings do not inflate support. There are 432 observed intent/type pairs; these are observations, not mandatory-slot contracts. Of 3,961 normalized annotated filler surfaces, 181 have multiple types. Of those, 137 vary only across canonical intents and 44 also vary within at least one intent. Only 29 meet the modest criterion of at least two unique utterances for each type in one role pair; this is a design screen, not validation.

Sources outside Git:

- DATA coordination/slurp-train-entity-association-root-verification-v1.json, SHA256 5b649b68ddf74ff7f1fd8f55b1901360890f39e5ded5215936942a42fc914a73.
- DATA coordination/slurp-train-entity-role-root-verification-v1.json, SHA256 506fe01332c382ce67aac2ae68d1cb1a5c2abf3cae8c93c36b2611ac8e9a9a34.
- DATA coordination/slurp-train-entity-role-ambiguity-audit-v1.json, SHA256 9514ec8226a5b2ae4ec4bf7d03a3bc7ea8234d0c8cceecfc543499242877ba56.
- DATA coordination/slurp-train-entity-role-ambiguity-classification-v2.json, SHA256 99ed0dae1dfc34137f3a6d181c154eb9ef8b537df3e8f5f811b425c9e4fff8ef.

The last artifact conservatively reviews ten candidate groups. Six have observable operation or role cues, three look like task-conditioned annotation conventions, and one remains unresolved. These are root-reviewed design classifications, not an exhaustive automatic separability proof. A news/person group contains closely related prompts with conflicting types; preserve that counterevidence instead of inventing a reliable distinction.

Distinguish three kinds of prospective values:

| Kind | What the value may state | What it must not claim |
|---|---|---|
| Observable task role | The current operation or relation supplies a cue for interpreting an observed span | The word always has one role |
| Task annotation convention | Governed TRAIN repeatedly uses a type in a defined task context | The convention is a universal semantic fact or independently validated rule |
| Unresolved label variation | Available examples conflict and do not support a stable discriminator | A confident conditional rule inferred from label variation alone |

The closed first task-agent family shows more missing-entity loss than type-swap loss in its descriptive attribution. Therefore a role-confusion mechanism alone would address only part of the observed problem. Await the unchanged replication before selecting a new mechanism. Candidate value content must also address coverage: which kinds of roles are worth checking in the current utterance, and which observed spans support them. A role inventory is a reminder to inspect evidence, never permission to fill an absent entity from a catalog.

## Audio2Tool source boundary

The historical G4 corpus remains immutable. Its source partition at commit cbf07c24640b2519a702e4001fcfeba8700c1d75 has SHA256 3bbf77a328c2983fb6299bcfe34a975624fee330a9325614dc1f84a7338678a1. The current file at the same path is a later partition and cannot substitute for that historical source.

Root independently mapped the three current official-population flight-roster receipts using only carrier-qualified IDs and query_idx metadata. The current 4,000 rows include 2,997 in blocks left to historical construction, 498 in historical exposed blocks, and 505 in historical proposed-evaluation blocks.

| Tier | Current rows | Historical construction-block rows |
|---|---:|---:|
| Direct | 500 | 356 |
| Parametric | 500 | 412 |
| Multiple intent | 500 | 361 |
| Implicit | 500 | 355 |
| Needle | 500 | 356 |
| Correction | 500 | 355 |
| Multiple turn | 500 | 370 |
| Intent blending | 500 | 432 |

Authority: DATA coordination/a2t-g4-current-roster-block-membership-root-v5.json, SHA256 bac0928d3d5fe2cb07a8a4fbc1fec550ff3c9ed849037d3bbe711dd6235e01b4.

This is block-membership evidence. It does not prove that each item survived historical quarantine or contributed a rendered card. It is sufficient to reject assumed decontamination of the old corpus for the current full population. Hold that reuse. Recompile source-bound cards from the current permitted construction side after excluding all evaluation identities and related query blocks; preserve historical bytes and conclusions. The card structure can be reused independently of its old construction contents.

Keep the concrete shared-runtime gaps separate: config-scoped Audio2Tool adapter construction, registered phase access to executable cards, live current-observation routing, and real raw-audio request capacity support. A registry entry alone does not implement these paths. Do not advertise the full-population agent as runnable until these four gaps close.

## Task-conditioned values in the common system

| Task | Supported decision | Candidate value structure |
|---|---|---|
| SLURP intent | Which target and operation fit the current speech | A qualified intent boundary or compact intent/role relation |
| SLURP entities | Which spans are present, which roles they have, and how to deliver their forms | Observed role coverage, operation-conditioned role cues, span/form guidance, exceptions |
| Audio2Tool operation | Which available operation achieves the requested change | Preconditions, requested end state, neighboring-operation distinctions |
| Audio2Tool arguments | Which value belongs to which parameter and survives a correction | Argument ownership, legal types, dependency and correction scope |
| E21 native ASR | Which candidate spelling fits acoustic and permitted contextual evidence | Source-bound spellings with person/company relations and explicit scope |
| E22 future native ASR analysis | Whether admitted metadata helps lexical interpretation | Dataset-supported contextual relations only; no new supplier or summary task is admitted here |

These use one shared execution base with task-specific knowledge types and scorers. They do not require treating a whole training set as memory. A reusable factual relation belongs in knowledge. A separately validated conditional procedure about correcting the system belongs in memory. Deterministic governed constraints belong in shared policy.

## Next mechanism and optimization gates

Finish the direct/frame replication, complete each official score once, and review both primary outcomes, all strata, failures and attribution. Select the next component using that closure, not an appealing isolated example.

For a value-content comparison, hold keys, selected items, order, observation, phase program, legal labels and delivery fixed where the hypothesis permits. Report remaining length and formatting differences. If query routing or stage control changes too, register it as a separate system factor instead of attributing the outcome solely to value content.

Evaluate the chain: retrieval availability, distinguishing-content coverage, current-query applicability, final use, and native task outcome. Availability traces do not prove causal use. Preserve newly introduced errors as well as corrected ones.

After a usable system is qualified, training-free optimization can update external knowledge relations and compression, applicable views, tool/observation decisions, and validated corrective memory. Preserve separate construction, optimization, validation and evaluation roles and frozen-core answer authority. Reward native quality and qualified system outcomes; the owner does not require a cost or online-latency penalty. Do not call unsupervised summarization alone reinforcement learning.
