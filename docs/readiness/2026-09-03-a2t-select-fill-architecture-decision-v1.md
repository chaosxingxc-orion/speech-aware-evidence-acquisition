# Audio2Tool SELECT/FILL Architecture Decision V1

Status: **IMPLEMENT THE SPLIT WORKFLOW AND TEST IT AGAINST MATCHED JOINT CONTROLS; NO NEW CONTACT AUTHORITY**

## Decision

Implement tool identification and parameter extraction as separate OpenJiuwen workflows. Do not
claim that the split is better until a fresh 104-row paired experiment compares it with both a
one-contact joint call and an equal-contact joint draft/revise controller.

The engineering candidate is:

```text
speech + canonical OBS
  -> local dense retrieval (top 32 routing candidates)
  -> fresh SELECT workflow (routing knowledge only)
  -> strict ordered tool-occurrence state
  -> deterministic selected-only parameter loading
  -> fresh FILL workflow (parameter knowledge only; tool names locked)
```

This is a system-level intervention: the two workflows intentionally receive different knowledge
and prompts. Contact-count parity, not prompt-byte identity, is the fair primary control. Actual
prompt and completion tokens remain paired efficiency outcomes; prompts are never padded.

## Why the split is now the leading hypothesis

The completed 104-row semantic flight separates the two largest consumption losses. In its fused
arm, 32 rows have all required tools reachable but select the wrong tool multiset, while 35 rows
select the correct tool multiset but fail exact arguments. Only 25 rows are exact and 12 are
retrieval-unreachable. In the transcript-vector arm, 62 rows have the correct tool multiset but
only 27 are exact. A single prompt is therefore asking the frozen core to resolve a broad routing
space and many unrelated argument schemas at the same time.

The construction-wide local-semantic audit supplies the required retrieval ground without a new
model call. Across 12,601 construction units in five query-block and duplicate-grouped folds,
dense tool-tier centroids at K=32 achieve:

- 98.2303% full required-tool-set coverage;
- 98.5842% required-label recall;
- 97.5822% worst-fold full-set coverage;
- at least 94.1710% full-set coverage in every task tier.

K=16 is cheaper and reaches 96.6193% overall, but the implicit tier is 89.8964%. K=32 is therefore
the first fixed local-semantic ground that clears the 90% tier floor without opening test data or
using a second answering model. It is a retrieval reachability ground, not a claim that the frozen
core already consumes the ground at 90% accuracy.

The context optimization is stage-specific rather than global:

- SELECT sees the sample-specific top-32 identities in score order and only their routing values:
  exact name, family/domain, intended operation, positive and negative cues, and multi-intent
  composition rules.
- FILL sees only parameter values for the selected occurrences: legal skeletons, public types,
  constraints, defaults and omission rules, value normalization, correction/multiturn state, and
  approved construction-only examples.
- Repeated calls retain distinct occurrence positions, while repeated documentation is loaded
  once.
- The dense scores and margins are logged as deployment-visible state for later adaptive-K or
  training-free RL decisions. V1 does not tune a score threshold on evaluation misses.

This directly implements per-sample value-conditioned context: different retrieval outcomes load
different routing values, and different SELECT outcomes load different parameter values.

## Why a joint controller may still win

The split creates a hard information boundary. If parameter names, legal skeletons, or value types
help disambiguate two nearby tools, hiding them from SELECT can lower tool accuracy. A wrong SELECT
also propagates because FILL cannot change the sealed names. Joint reasoning can exploit these
cross-stage cues and revise a mistaken draft. The expected split benefits--less conflicting
context, stricter parsing, and more focused value binding--are therefore hypotheses, not assumed
facts.

## Fresh 104-row experiment

Use one new discovery roster with 13 rows per tier. It must be disjoint by identity, query block,
and normalized-token class from construction, the completed semantic 104, every other exposed
cohort, and all test or confirmatory surfaces.

| Arm | Answer contacts per row | Context and role |
|---|---:|---|
| `DIRECT_M0` | 1 | Existing frozen single-call reference over the complete registry. |
| `JOINT_ONE_CALL` | 1 | Dense K=32 candidate knowledge; select tools and arguments jointly. |
| `JOINT_DRAFT_REVISE` | 2 | First contact matches `JOINT_ONE_CALL`; a fresh second workflow receives only canonical draft state and prospectively frozen joint knowledge, and may revise the full answer. |
| `SELECT_THEN_FILL` | 2 | Routing-only SELECT, then selected-only parameter FILL with names/count locked. |

The three agentic arms share the same speech packet, canonical OBS state, dense retrieval ordering,
frozen core, decoding policy, stage scheduler, and knowledge source version. `DIRECT_M0` remains a
true one-contact speech-only reference and therefore does not consume OBS. The equal-answer-contact
joint arm is the primary comparator. `SELECT_THEN_FILL - JOINT_ONE_CALL` alone cannot distinguish
decomposition from the benefit of an extra inference contact.

Generate `JOINT_ONE_CALL` exactly once. Seal that exact response as the inherited first-contact
draft for `JOINT_DRAFT_REVISE`; do not regenerate it. Both FILL and REVISE receive the original
speech packet, the same canonical OBS state, and their respective sealed first-stage state. The
joint ground exposes the same eligible routing and parameter facts for all K=32 candidates that
the split can expose across its two stages. Different realized prompt lengths are an intended
systems outcome and are measured without padding.

Every agentic answer grammar uses the task-wide one-to-seven call cardinality contract. SELECT
allows one to seven ordered tool occurrences; JOINT allows one to seven complete calls; FILL locks
the exact SELECT count and names. A zero-call result is a stage/schema failure, not a valid
abstention. The speech-only M0 output remains governed by its frozen baseline protocol and is a
secondary comparison.

Each stage runs as a separate `execute_speech_agent_workflows` invocation with `branch_count=1`,
two generation slots, and queue depth four. Generation is never prompt-batched. The local
embedding stage may batch at most 32 texts. Phase barriers require all 104 SELECT rows to seal
before any FILL row starts and all 104 joint answers to seal before any revision starts.

Only canonical, hash-bound state crosses a barrier. It binds sample identity, split identity,
speech packet, source request/response, candidate-set order, ground, response schema, stage,
predecessor state, and payload hashes. The receiving workflow externally verifies every binding,
the one-to-seven cardinality, candidate membership, and the exact legal call schema before using
the state. Raw responses, cumulative chat history, gold, reference transcripts, test annotations,
and future turns never cross the barrier. Fresh workflow/session means a fresh semantic request
context; it does not claim physical KV-cache erasure.

## Context and batching rules

The physical context limit remains 32,768 tokens per slot. Every actual contact must fit the exact
24,576-token operational cap, leaving an 8,192-token reserve for speech state and loop growth.
Measure the assembled request immediately before every contact through the pinned live template,
tokenizer, and JSON-schema-to-grammar path. Before a phase starts, every one of its 104 exact
requests must pass. In particular, materialize and validate the complete dynamic FILL and REVISE
batches after their first-stage barrier and before sending any second-stage contact. Never infer a
length from another stage or from an average, and never allow a late overflow to create a partial
flight.

Batching remains valid only where semantics permit it:

- use individual generation requests with two server slots;
- batch local embeddings up to 32 texts;
- use up to four outer workers for complete-manifest official scorer jobs;
- never shard one official score job or average shard scores.

Network jitter is excluded from the scientific analysis. A transport failure is run-integrity
evidence and triggers the registered one-shot failure path; it is not an efficacy covariate.

## Prospective estimands and decision rule

For each row, assign exactly one mechanism category after sealing:

- `SUPPLY`: at least one required tool is absent from the frozen candidate set;
- `SELECT`: all required tools are reachable, but the selected name multiset or multiplicity is
  wrong;
- `FILL`: the selected name multiset and multiplicity are correct, but the final official call
  multiset is not exact;
- `SUCCESS`: the final official exact metric is one.

Apply this attribution per arm: SELECT uses the sealed selector names; JOINT reports draft and
revised name correctness separately; M0 has full-registry access and is never assigned a K=32
SUPPLY error. Conditional FILL accuracy is diagnostic only because conditioning on a model-selected
event changes the compared subsets. The paired final exact outcome remains the causal decision
criterion.

Parse, schema, transport, and budget failures are reported separately. The official scorer is
order-insensitive, so occurrence order is preserved internally but no order-improvement claim is
made without a preregistered ordered diagnostic.

The primary contrast is paired exact match for `SELECT_THEN_FILL - JOINT_DRAFT_REVISE`. Secondary
contrasts are split minus joint-one-call and split minus direct M0. Report paired saves, harms,
ties, exact paired sign tests, and 10,000 tier-stratified paired bootstrap replicates, plus tool
accuracy, slot F1, parse rate, selector multiplicity, conditional FILL accuracy, tokens, contacts,
and wall time.

Promote the split architecture only if the lower 90% paired-bootstrap bound is above zero against
both joint controls, tool and slot effects are nonnegative, it improves over direct M0, and no tier
has more than one net exact-match loss. If split beats only the one-contact joint arm, attribute the
gain to extra inference compute. If conditional FILL improves but overall exact loses through
SELECT errors, retain the diagnosis and preregister a validator/reselection experiment rather than
silently enabling it. If both systems fail mainly on SUPPLY, return to knowledge construction.

No approximately-1,000-row scale, test evaluation, or training-free RL fit begins from this design.
After a stable 104-row architectural gain, freeze the baseline and use the pinned upstream
`vowpalwabbit==9.11.2 cb_explore_adf` implementation on deployment-visible state only.
