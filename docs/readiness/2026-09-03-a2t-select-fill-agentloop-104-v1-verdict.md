# Audio2Tool SELECT/FILL AgentLoop 104-Row Result

Status: **COMPLETED; CURRENT SPLIT NOT PROMOTED; APPROXIMATELY-1,000-ROW SCALE CLOSED**

## Decision

Keep the staged architecture as an engineering candidate, but do not promote its current
information contract. `SELECT_THEN_FILL` is much cheaper than either joint two-contact workflow and
beats the single-call direct baseline, but it does not beat the knowledge-matched joint controls.
The next bounded experiment must separately test two repairs in a paired factorial: give SELECT
compact executable-interface information, and make FILL occurrence-indexed and evidence-backed.

This result does not require a baseline-stage score above 0.90. The greater-than-0.90 objective is a
post-training-free-RL target.

## 104-row result

The population contains 104 fresh discovery rows, 13 from each of eight registered task tiers.
Official corpus metrics are:

| Arm | Contacts | Exact match | Tool accuracy | Slot F1 | Parse rate | Prompt tokens | Raw latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| `DIRECT_M0` | 104 | 0.1731 | 0.4038 | 0.3019 | 0.8558 | 1,384,357 | 115.8 s |
| `JOINT_ONE_CALL` | 104 | 0.2404 | 0.6250 | 0.4045 | 1.0000 | 763,709 | 584.7 s |
| `JOINT_DRAFT_REVISE` | 208 | 0.2500 | 0.6346 | 0.4068 | 1.0000 | 1,553,399 | 1,185.1 s |
| `SELECT_THEN_FILL` | 208 | 0.2500 | 0.5962 | 0.3652 | 1.0000 | 230,005 | 236.2 s |

Against `DIRECT_M0`, the split workflow gains 7.69 exact-match points, 19.23 tool-accuracy
points, and 6.33 corpus Slot-F1 points. The paired, tier-stratified 90% bootstrap interval for the
exact-match gain is [0.96, 13.46] points. There are 13 exact saves, five harms, and 86 ties.

Against `JOINT_ONE_CALL`, the split workflow gains 0.96 exact-match points, but loses 2.88
tool-accuracy points and 3.93 Slot-F1 points. Its paired exact interval is [-2.88, 4.81] points.
Against the equal-contact `JOINT_DRAFT_REVISE` control, exact match is tied while the split loses
3.85 tool-accuracy points and 4.16 Slot-F1 points. Its paired exact interval is [-2.88, 2.88]
points. The registered promotion rule therefore fails.

The draft/revise step itself changes only one of 104 outputs. It adds only 0.96 exact and tool
points and 0.23 Slot-F1 points over the one-call joint arm while approximately doubling prompt
tokens and raw latency. It is not an accuracy-efficient default.

## What the split does achieve

The split uses 69.88% fewer prompt tokens and 59.60% less raw latency than `JOINT_ONE_CALL`. It
uses 85.19% fewer prompt tokens and 80.07% less raw latency than `JOINT_DRAFT_REVISE`, with the
same number of contacts as the latter. This efficiency comes from loading detailed parameter
evidence only after tools are selected.

It also creates an actionable error decomposition. Of 104 split rows, four fail SUPPLY, 38 fail
SELECT, 36 fail FILL after a correct selection, and 26 are exact successes. By contrast, the
revised joint arm has four SUPPLY, 34 SELECT, 40 FILL, and 26 successes. The present split shifts
four failures from FILL to SELECT without increasing the success count.

## Root cause

The local semantic K=32 candidate set contains every required tool for 100 of 104 rows, or 96.15%.
This is adequate aggregate tool-name reachability but not a uniform ground: tier 8 reaches only
84.62%, while tiers 4 and 7 reach 92.31%. These four SUPPLY failures cap what any consumer of the
same candidate set can achieve, but they explain only four of 78 non-exact split outcomes.

The larger problem is information consumption. The SELECT prompt supplies only a short intended
action plus positive and negative routing cues. The joint prompt supplies those cues and every
candidate's signature, constraints, legal key sets, defaults, omission rules, canonicalizers,
compatibility forms, role guidance, and examples. Parameter interfaces therefore act as evidence
for tool identity, not merely as instructions for parameter filling. Removing all of that evidence
from SELECT lowers tool-name multiset accuracy from 62.50% for joint one-call to 59.62% for split.
The selector is especially weak on the 26 multi-call rows, where exact tool-name multiplicity is
42.31%. Those rows have zero exact answers in every arm. Of the 15 incorrect multi-call selector
outputs, 11 contain mixed or near-neighbor name substitutions, two purely under-select, and two
purely over-select. Across all selector errors, 37 are mixed or semantic substitutions, versus only
two pure under-selections and three pure over-selections. The dominant selector defect is therefore
near-neighbor tool discrimination, not call-count estimation.

FILL is a second independent bottleneck. Even among the 62 rows with the correct selected
tool-name multiset, only 26 are exact, for a conditional rate of 41.94%. Among the 36 non-exact
rows after correct selection, a mechanical, overlapping taxonomy finds extra keys on 20 rows,
missing keys on six, wrong same-type values on 14, and wrong value types on four. `deviceId` is
implicated on 20 rows. Tier 1 expects no scored slots but the split emits 14; tiers 3 and 8 emit 52
and 57 slots for only 17 and 14 expected slots. This is evidence of default-driven overfilling and
weak occurrence binding.

The Audio2Tool construction helper also represents a bare additional tool name with an empty
argument record. Some apparent extra arguments may therefore reflect sparse evaluation labels
rather than a purely semantic model error. The next arm must freeze an evidence-support rule from
construction-only data and permit `{}` when speech and OBS provide no supported parameter. It must
not delete semantically required arguments merely to imitate exposed discovery labels. The 41.94%
conditional value remains an observational diagnostic on an easier, non-random subset; it is not a
causal oracle or an attainable upper bound.

Context truncation does not explain the outcome. The exact maximum required windows are 2,577
tokens for SELECT, 3,010 for FILL, 9,019 for joint one-call, and 9,385 for revision. All are far
below the 24,576-token operating cap and the 32,768-token physical per-slot limit. The 8,192-token
reserve remains intact, and every later phase was measured after its workflow boundary rather than
predicted from a nominal loop length.

## Reachability and attainable upper bounds

Candidate reachability at K=32 is a SUPPLY oracle bound for tool names only. It says that a perfect
selector could find all required tool names on 100 rows; it does not say that the model can attain
96.15% exact calls. A top-K statement such as "three of five labels are gold" is useful only after
its target is made precise. For this multi-call task, report full-required-set recall, partial-call
coverage, candidate count, and per-tier coverage separately.

A useful parameter-support ceiling is also post-seal and component-specific: whether every expected
key is legal for the selected schema and whether every expected value is supported by the speech,
canonical OBS state, or construction-only knowledge. It does not feed gold into runtime. A true
gold-tool or gold-argument runtime arm would violate the study boundary and would overstate the
deployable architecture.

## Next bounded experiment

Use a fresh, non-test, gold-unexposed 128-row discovery roster, balanced at 16 rows per tier. First
qualify the construction-only
retriever ground at at least 0.95 full-required-tool-set coverage overall and at least 0.90 in every
tier. Retain the local encoder as the first-stage baseline; add a fixed local sparse/dense hybrid or
adaptive K only if it passes grouped construction folds without consulting these 104 outcomes.

Then run a paired 2-by-2 split-workflow factorial:

| Factor | Control | Treatment |
|---|---|---|
| SELECT ground | Current routing-only records | Signature, choose/avoid constraints, and argument key/type cues; no values or defaults |
| FILL policy | Current contract/default completion | Occurrence-indexed sparse filling; emit only speech/OBS-supported arguments and explicitly permit `{}` |

This yields four split cells and isolates both main effects and their interaction. Generate each of
the two sealed SELECT states once per row, then reuse each state across its two FILL cells. All cells
keep K=32, speech, OBS, retriever, frozen core, and decoding fixed. SELECT still emits names and
multiplicity only; FILL remains name/count/position locked. Include `DIRECT_M0` and
`JOINT_ONE_CALL` as external references, but do not repeat `JOINT_DRAFT_REVISE`: its second contact
changed only one of 104 outputs.

The interface SELECT main effect is promoted only if it improves selector multiset accuracy and
final exact match. The sparse FILL main effect must reduce unsupported extra keys without increasing
missing supported keys, and must improve exact match without reducing Slot-F1. The combined split
cell must reach or exceed `JOINT_ONE_CALL` without material tier regression. Approximately-1,000-row
expansion remains closed until a positive paired lower bound is reproduced on fresh data.

The staged state remains suitable for a later pinned upstream `vowpalwabbit==9.11.2
cb_explore_adf` controller. Deployment-visible state can include retrieval margin, candidate count,
selected-call count, schema-risk class, validator state, missing-value state, prompt cost, and
trajectory hashes. No policy is fit in this result row.

## Efficiency and integrity

Generation remained one sample per request with two serving slots and queue depth four. Only local
embedding used physical batches of at most 32. The unchanged official single-process scorer ran
once per complete manifest, with four complete manifests scheduled through four outer workers. It
finished four of four jobs in 8.23 seconds versus 26.59 summed process seconds, a 3.23-times
throughput speedup. No manifest was sharded and no shard scores were averaged.

The first local sealing attempt failed after all model outputs were durable because a path was
resolved against the wrong directory. A zero-contact successor verified the source seal and reused
the direct bundle in place. One unsealed partial recovery directory was verified and removed; it
contained no receipt or completed result. No model, embedding, tokenizer, scorer, or gold contact
was repeated by recovery.

Committed compact result: `docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-select-fill-agentloop-104-v1/result-summary.json`.
The external post-seal result has SHA-256
`57e9fc3b5e9a2aa953f9368651eca11697f9d35d1feaff5e23aa792a2eda3b16`; analysis-input seal
`23342b1e08bc833abc4cdfb92bd3d81393aadc7a4a29022d96cbb728ad117913`; official-score batch
`6506eff753c0004d715cacb3c461c327f004c1d335ba38c2d530f82a8893f6e3`; zero-contact recovery
receipt `678dc3ec30b8e855d9351d7b2f45ddd9dd25eaa5060a51e7d0f2675aee3dda1`.

This result authorizes no test, confirmatory, approximately-1,000-row, Stage-3, paper-scale, or
training-free-RL execution.
