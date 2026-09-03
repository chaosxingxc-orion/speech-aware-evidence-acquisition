# Audio2Tool Local Retrieval and SELECT/FILL 104-Row Successor — Design

Status: **DESIGN FIXED; MODEL-FREE KNOWLEDGE QUALIFICATION PRECEDES ANY NEW MODEL CONTACT**

## Decision from the completed flight

Use the local semantic encoder as the serving retriever baseline. Do not retain the current
per-sample same-core retrieval-query call as the default: it changes the selected set but does not
improve final exact match, tool accuracy, or slot F1 over transcript-vector retrieval. The frozen
core may later enrich knowledge from construction-only material, but that is a separately measured
knowledge-construction intervention, not an unmeasured second runtime query path.

Separate tool selection from parameter construction. The completed fused arm partitions into 25
exact rows, 35 tool-correct but exact-wrong rows, 32 top-16-reachable but tool-wrong rows, and 12
top-16-unreachable rows. In the transcript arm, only 27 of 62 tool-correct rows are exact. The
current full-card, joint-response prompt therefore leaves substantial and separable SUPPLY, SELECT,
and FILL losses.

## Dataset evidence

This design is based on the full construction/training distribution, not on an eight-row or
hand-selected case analysis. The frozen audit covers 12,601 construction units, 3,871 query blocks,
152 registry tools, 28 tool families, and 15,804 call occurrences. It contains:

- 9,813 argument-bearing units and 2,788 no-argument units;
- 348 observed legal parameter-key skeletons and one legal skeleton not observed in construction;
- 107 tools with multiple legal skeletons, 116 with defaults, 117 with typed rules, and 11 with
  conditional keys;
- 2,250 multi-call units, a 17.86% construction rate, with as many as seven calls and four families
  in one unit;
- 10,661 single-family, 1,683 two-family, 252 three-family, and five four-family units.

Grouped, query-block-disjoint perfect-text BM25 reaches 0.9056 full required-tool-set coverage at
K=16, 0.9473 at K=32, and 0.9814 at K=64. Indexing complete-dialogue relations and using the complete
dialogue query raises the same validation population to 0.9278 at K=16, 0.9667 at K=32, and 0.9865
at K=64. On tier-7 multiturn units, complete-dialogue information raises K=16 coverage by 15.0
points and reaches 0.9592. This is direct information-gain evidence for preserving prior-dialogue
state in OBS/ORG.

The implication is not to send 64 complete tool cards to one answer call. `SELECT` can receive a
wider set of small routing records, while `FILL` receives detailed evidence only for the selected
tool occurrences.

## Knowledge qualification ladder

Run a construction-only, grouped-fold retrieval study before a fresh evaluation flight. Freeze all
text renderers, indexes, fusion rules, and cutoffs before opening a new 104-row result.

1. Reproduce complete-dialogue BM25 at K=16/32/64.
2. Compare the existing local dense encoder on the same grouped folds.
3. Fuse dense and BM25 rankings with one prospectively fixed RRF rule. Do not select fusion weights
   from the completed 104-row misses.
4. Add family-to-tool hierarchical retrieval only if the fixed hybrid fails the gate. Family
   selection must support multiple families and cannot hard-prune a candidate unless the frozen
   family route admits it.
5. If model-free construction still fails, allow one separately registered same-core
   construction-enrichment probe over registry and construction-only material. It may generate
   English intent prototypes, negative routing cues, complete-dialogue relations, and
   parameter-normalization explanations. It must not read evaluation identities, outputs, gold,
   reference transcripts, or test annotations. Compare its incremental coverage against the local
   hybrid; do not assume that model generation is beneficial.

The knowledge gate is full required-tool-set coverage at least 0.95 overall and at least 0.90 in
every tier under grouped folds. Prefer maximum K=32. If only an adaptive maximum K=64 passes, require
mean candidate count at most 32 and bind the confidence/margin rule before evaluation. A model-free
failure returns to knowledge construction; it does not authorize a model flight or a larger K by
inspection of evaluation misses.

## Fresh 104-row workflow matrix

Use a new discovery roster that is disjoint from the completed 104 rows and from every test or
confirmatory split. Run all answer arms on the same 104 identities.

| Arm | Contacts per row | Purpose |
|---|---:|---|
| `DIRECT_M0` | 1 | Frozen single-call reference over the complete registry. |
| `JOINT_ONE_CALL` | 1 | Improved local retrieval and knowledge, with tool and parameters decided jointly. |
| `JOINT_DRAFT_REVISE` | 2 | Equal-contact control for generic extra inference and revision. |
| `SELECT_THEN_FILL` | 2 | Specialized tool-only SELECT followed by selected-only parameter FILL. |

All arms share original speech, the frozen local retrieval result, decoding policy, and available
knowledge version. `JOINT_DRAFT_REVISE` is necessary: a split arm cannot be credited merely for
spending two contacts when its comparator spends one.

`SELECT` receives routing-only records: tool identity, domain/family, intended action, positive and
negative cues, compatibility, and multi-intent composition guidance. It emits a strict canonical
tool-call skeleton with occurrence multiplicity preserved. It cannot emit arguments.

`LOAD_PARAMETER_CONTEXT` is deterministic. It maps each selected occurrence to its selected-only
parameter packet and binds the selector-state hash. It deduplicates repeated tool documentation but
never deduplicates call occurrences.

`FILL` receives original speech, canonical OBS state, canonical selector state, and only the selected
tools' schemas, required/optional keys, defaults, enum/range/type constraints, entity-value
normalization rules, correction/multiturn state, and construction-only examples. Its response schema
locks item count, occurrence position, and tool-name constants; it fills arguments only. Empty
selection still receives a const-empty FILL contact during the experiment so the two-contact
comparison stays nominally balanced. A deployed system may later stop early under a separately
measured policy.

Optional `RESELECT` remains disabled. If the hard split demonstrates selector-error propagation, a
future deterministic validator may expose an incompatibility state and request one re-selection.
It may never silently change a tool, normalize an invalid response into validity, or inject a label.

## OpenJiuwen execution shape

Use phase barriers and one-contact workflows:

```text
OBS workflows
  -> batched local RETRIEVE
  -> SELECT workflows
  -> deterministic LOAD_PARAMETER_CONTEXT
  -> FILL workflows
```

Each model stage creates a fresh OpenJiuwen workflow session. Canonical parsed state is carried in a
hash-bound external envelope containing sample identity, split hash, speech-packet hash, stage,
predecessor-state hash, canonical payload, and payload hash. Raw prior responses and cumulative chat
history never enter the next contact. This guarantees fresh request context, but it does not claim
physical KV-cache erasure.

Generation remains one sample per request, with two slots and queue depth four. Only local embeddings
may use physical batches, at no more than 32 texts. Every assembled model request is measured through
the live template/tokenizer path. The physical per-slot limit is 32,768 tokens; the operational
maximum is 24,576, preserving an 8,192-token reserve for state and loop growth. No average-length or
step-count estimate substitutes for exact per-contact measurement.

Trace OBS, retrieval ORG, selector ORG, parameter SUPPLY, and FILL USE separately. Every stage records
request/response/cost hashes, canonical state hashes, selected identities, supplied evidence ids,
packet/schema hashes, and exact prompt accounting. The official scorer remains unchanged and scores
only the final answer manifest.

## Estimands and promotion rule

For each row define post-seal `R` as required tools contained in the frozen candidate set, `C` as
correct selected tool-name multiset, and `E` as official exact canonical call multiset. Report:

- `H_supply = mean(1 - R)`;
- `H_select = mean(R * (1 - C))`;
- `H_fill = mean(C * (1 - E))`;
- exact/tool/slot/parse metrics overall and per tier;
- selector tool-multiset accuracy, selector multiplicity accuracy, and multi-call subgroup results;
- exact and slot metrics conditional on correct SELECT;
- contact count, prompt tokens, and wall time.

The primary architectural contrast is `SELECT_THEN_FILL - JOINT_DRAFT_REVISE` on exact match. Also
report split minus joint-one-call and split minus direct M0. Use paired saves/harms/ties, exact paired
sign tests, and 10,000 paired bootstrap replicates under a prospectively frozen seed. The official
scorer is order-insensitive; no call-order improvement may be claimed unless a separate ordered-call
diagnostic is versioned and registered before contact.

Do not expand toward approximately 1,000 rows unless the split workflow has a positive lower 90%
paired-bootstrap bound versus both joint controls on exact match, nonnegative tool and slot effects,
and no material tier regression. A baseline-stage score above 0.90 is not required. The greater-than-
0.90 objective remains a post-training-free-RL target.

## Training-free RL reservation

This design fits no policy. It exposes deployment-visible action state for a later pinned upstream
`vowpalwabbit==9.11.2 cb_explore_adf` controller: retrieval margins, candidate count, selected-call
count, schema-risk class, validator state, missing-value state, prompt cost, and canonical trajectory
hashes. Later actions may include `STOP_M0`, joint USE, split USE, and prospectively qualified
re-selection. Gold, official scores, reachability, and post-hoc error categories are never runtime
features.

This document is design-only. It authorizes no model, embedding, tokenizer, scorer, gold, new-sample,
test, confirmatory, approximately-1,000-row, Stage-3, or paper-scale contact.
