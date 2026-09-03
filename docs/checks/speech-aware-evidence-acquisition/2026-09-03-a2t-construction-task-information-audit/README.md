# Audio2Tool construction-dataset task-information audit

## Decision

Analyze the task from the construction/training population before freezing any
AgentLoop retrieval depth or evidence-supply action. Evaluation rows must not
define knowledge. This audit consumed only the block-governed construction
partition and frozen public action contracts. It made zero model, scorer,
network, tokenizer, or audio contact and emitted no construction utterance or
concrete argument value.

The result rejects two shortcuts:

1. A global frequency prior cannot safely reduce the registered label space.
2. Increasing a single global top-k until recall is high creates too many
   distractors, especially for implicit and multiturn requests.

The next knowledge mechanism must therefore use query-conditioned keys,
attach every call label to multi-intent construction keys, separate key
retrieval from value-card loading, and specialize observation/organization for
implicit, correction, multiturn, and blended-intent structure.

A public-registry semantic-key ablation was also rejected as a standalone
repair. Adding each tool's public name, domain, category, and description to
the BM25 index improves full-set coverage by less than 0.3 percentage points.
The information is useful, but a lexical matcher cannot reliably transfer its
meaning to paraphrased desired-state requests. The next comparison therefore
uses the already-pinned local Qwen3-Embedding model outputs as a semantic
tool-level retriever, not a second answer model.

## Population and natural distribution

The construction unit is one `(tier, query_idx)` block-level task, not one
voice rendering. The frozen construction partition contains 12,601 units from
3,871 query blocks and 22,951 speech renderings. It covers 151 gold-used tools
from a 152-tool registry, 28 public tool families, 15,804 ordered call
occurrences, 85 argument keys, and 354 raw primary tool/key patterns. Of 349
legal public tool/skeleton branches, 348 are observed after canonical public
key ordering. The sole unobserved branch is the empty `getLockStatus` call;
that tool is also the one registry tool never used as gold.

| Tier | Construction units | Natural share | Primary information burden |
|---|---:|---:|---|
| direct | 1,546 | 12.27% | explicit label, usually no argument |
| parametric | 2,601 | 20.64% | explicit label plus value binding |
| multi-intent | 1,550 | 12.30% | segment, retrieve, and preserve multiple calls |
| implicit | 1,544 | 12.25% | infer an operation from a desired effect or state |
| needle | 1,554 | 12.33% | isolate the actionable span from distractors |
| correction | 1,547 | 12.28% | discard superseded labels and values |
| multiturn | 1,554 | 12.33% | resolve the final request from prior dialogue state |
| intent blending | 705 | 5.59% | disentangle and order multiple blended calls |

The distribution is not tier-uniform. A future roster with 13 rows per tier is
an equal-tier stress estimand, not an estimate of the natural construction
mixture. Report both the equal-tier result and the result reweighted by the
shares above.

## Output structure the agent must recover

The target is an ordered multiset, not a single class:

| Calls per unit | Units |
|---:|---:|
| 1 | 10,351 |
| 2 | 1,450 |
| 3 | 684 |
| 4 | 87 |
| 5 | 23 |
| 6 | 4 |
| 7 | 2 |

There are 2,250 multi-call units, or 17.86% of construction. Duplicate tool
occurrences can appear, so retrieving every unique label is necessary but not
sufficient: multiplicity and order remain separate output obligations.

Primary-call argument counts are 2,788 with zero keys, 5,622 with one, 3,441
with two, 608 with three, and 142 with four. Public contracts contain 349 legal
tool/skeleton branches and 201 typed key rules. Of the 152 tools, 116 declare
defaults, 141 permit a no-argument call under at least one legal construction,
107 have multiple legal skeletons, 15 have optional keys, and 11 have
conditional keys. Consequently, correct tool selection alone cannot deliver
exact match; skeleton selection, value binding, type/case normalization, and
default-versus-omission semantics are central task information.

Thirty-eight construction rows contain syntax-incompatible historical
argument-key fragments. They remain in tier/tool/call statistics but are
excluded from skeleton-support counts, matching the frozen contract builder.
Concrete values are structurally validated against their key tuples but are
not aggregated, used as analysis features, or emitted.

## Why an unconditional top-k is not the solution

Across all 15,804 call occurrences, the raw tool-frequency entropy is 6.360
bits, equivalent to 82.15 equally likely labels. The most frequent labels do
not concentrate enough mass to justify global pruning:

| Most frequent labels kept | Call mass covered |
|---:|---:|
| 1 | 4.02% |
| 3 | 10.40% |
| 5 | 15.94% |
| 10 | 26.54% |
| 20 | 43.17% |
| 50 | 77.46% |
| 100 | 96.34% |

It takes 64 labels to cover 90% of raw prior mass and 86 labels to cover 95%.
A useful reduction must therefore be conditioned on the current speech-derived
state. Frequency is a feature for ranking or tie breaking, never permission to
exclude a registered label.

## Training-internal label candidate experiment

The 12,601 construction units were split by complete `query_idx` blocks with
seed `20260903`: 10,079 build units in 3,097 blocks and 2,522 validation units
in 774 disjoint blocks. A deterministic BM25 key was built for each build
unit. Every ordered primary and extra call label was attached to the key. For
each validation text, the maximum key score carrying each tool produced one
152-label ranking. This is conditioned on the perfect transcript and measures
retrieval only; it is not runtime performance or a model-consumption upper
bound.

| k | Required-label recall | Full required-set coverage | Precision | Mean distractors |
|---:|---:|---:|---:|---:|
| 1 | 47.17% | 47.26% | 59.20% | 0.41 |
| 3 | 73.49% | 69.79% | 30.74% | 2.08 |
| 5 | 82.62% | 79.02% | 20.74% | 3.96 |
| 8 | 87.96% | 85.09% | 13.80% | 6.90 |
| 16 | 92.48% | 90.56% | 7.25% | 14.84 |
| 32 | 95.80% | 94.73% | 3.76% | 30.80 |
| 64 | 98.52% | 98.14% | 1.93% | 62.76 |
| 100 | 99.43% | 99.29% | 1.25% | 98.75 |

Top-5 is an effective narrowing action for many rows, but it cannot serve as
the knowledge ground because it omits at least one required label on 20.98% of
validation units. Top-64 repairs aggregate coverage at the cost of 62.76 mean
distractors, which recreates the original consumption problem.

The audit now separates positive BM25 support from the deterministic
alphabetical zero-score tail. At k=64, the mean zero-score fallback burden is
0.35 labels and the positive-score full-set coverage remains 98.14%; therefore
the top-64 problem is mostly genuine distractor overload, not an artifact of
alphabetical fallback. At k=152, ordinary full-set coverage is mechanically
100%, while positive-score full-set coverage is 99.84%; the former must not be
called retrieval evidence.

The failure is concentrated:

| Tier | Full set @5 | @16 | @32 | @64 |
|---|---:|---:|---:|---:|
| direct | 89.14% | 96.05% | 97.70% | 99.34% |
| parametric | 92.03% | 97.72% | 99.24% | 100.00% |
| multi-intent | 63.99% | 90.68% | 97.43% | 99.36% |
| implicit | 51.99% | 71.85% | 82.78% | 93.38% |
| needle | 89.07% | 95.18% | 97.11% | 100.00% |
| correction | 98.05% | 99.03% | 99.68% | 100.00% |
| multiturn | 63.95% | 78.68% | 85.89% | 94.04% |
| intent blending | 70.00% | 90.00% | 95.00% | 97.14% |

The training result identifies different causes and therefore different
repairs:

- For implicit requests, add effect/state-to-operation keys and local sibling
  contrasts; merely loading more values is not the first repair.
- For multiturn requests, the final-turn speech is often information-poor.
  Preserve and observe prior dialogue state; knowledge expansion cannot recover
  information absent from OBS.
- For multi-intent and blended requests, segment the actionable spans, retrieve
  per segment, and union candidate labels before loading values.
- For needle requests, retrieve from the actionable span rather than the full
  distractor-bearing observation.
- For corrections, preserve only the surviving intent/value bindings. The
  strong top-5 coverage indicates that more knowledge is unlikely to be the
  main bottleneck.

## Multiturn observation versus construction-key factorial

The earlier exploratory comparison changed both the construction index and
the validation query. It therefore could not attribute the entire gain to
observation. The frozen 2 x 2 construction-only factorial now separates the
two factors on all 319 tier-7 internal-validation units:

| Tier-7 representation | Full set @5 | Delta from final/final |
|---|---:|---:|
| final-turn keys / final-turn query | 63.95% | -- |
| final-turn keys / complete-dialogue query | 83.39% | +19.44 pp |
| complete-dialogue keys / final-turn query | 73.04% | +9.09 pp |
| complete-dialogue keys / complete-dialogue query | 90.91% | +26.96 pp |

The fixed-index query contrast demonstrates missing observation information.
The fixed-query key contrast independently demonstrates incomplete knowledge
organization. The joint cell is a matched representation audit, not a pure
OBS oracle and not runtime performance. Complete-dialogue text here comes only
from the construction partition, is translated to English ASCII under a
closed audited punctuation policy, is hash-addressable, and is never emitted.
At runtime the same information must be derived from presented prior speech
and already-known agent turns; the reference transcript is prohibited.

## Internal-split limitations

The internal validation split is query-block-disjoint but deliberately
retains build support for each primary tool/skeleton. It is therefore
gold-support-conditioned, not a simple random split. It also contains 51 of
2,522 validation units with a case-folded, whitespace-normalized text twin in
the build fold; 45 of those share the same required-label set. Full-set@5 is
92.16% on those twins and 78.75% on the other 2,471 units. Tier 7 has no exact
build-text twin, so duplication does not explain its factorial gain, but the
next retrieval comparison must group normalized twins into the same fold and
report no-near-duplicate and worst-fold results. Validation exercises 138 of
152 registry labels, so no label may be removed based on this audit.

## Label-blind grouped out-of-fold baseline

The corrected primary engineering estimate uses five out-of-fold splits over
all 12,601 construction units. A connected component contains every row linked
by shared `query_idx`, identical normalized text, identical BM25 token
sequence, or an identical representation under the tier-7 complete-dialogue
factorial. Component assignment uses only the seed, the complete sorted member
identity, component size, and fold id. Labels, skeletons, call counts, and
retrieval outcomes do not influence the split.

The result contains 3,689 components, the largest with 30 units. Fold sizes are
2,517--2,523 units, every tier occurs in every fold, and no query block,
normalized text twin, BM25-token twin, or alternate-representation twin crosses
a fold boundary. `setChargingLimit` is the only validation-required label
absent from its fold's build index; the complete 152-label registry remains the
deterministic fail-open tail.

| k | Overall full set | Label recall | Mean distractors | Worst-fold full set | Multi-call full set |
|---:|---:|---:|---:|---:|---:|
| 5 | 79.50% | 82.99% | 3.96 | 78.59% | 67.24% |
| 16 | 91.95% | 93.56% | 14.83 | 90.99% | 92.89% |
| 32 | 95.77% | 96.62% | 30.79 | 94.97% | 97.07% |
| 64 | 98.31% | 98.65% | 62.77 | 97.54% | 98.89% |

No fixed k passes the admission rule. At k=16 the distractor budget passes but
coverage does not. At k=32 aggregate and worst-fold full-set coverage pass, but
label recall is below 97%, implicit full-set coverage is only 85.36%, and the
distractor budget fails. At k=64 coverage passes while candidate-count and
distractor budgets fail. The next improvement must therefore raise implicit
discrimination and retain multi-intent/multiturn recall without widening one
global k.

Only 171 of 12,601 units have maximum token-set Jaccard at least 0.80 against
their fold's build index. On the other 12,430 units, full-set coverage is
79.38% at k=5, 91.90% at k=16, 95.74% at k=32, and 98.29% at k=64. The
failure therefore remains after removing near duplicates; it is not explained
by exact or approximate sentence reuse.

## Public registry semantic-key ablation

The first knowledge-expansion test added one value-free English key per tool
from only four public registry fields: tool name, domain, category, and
description. It used the identical five grouped folds. No sample argument
value, validation label, source utterance, network call, or model contact was
used to construct those keys.

| k | Baseline full set | Registry-key full set | Delta | Recall delta |
|---:|---:|---:|---:|---:|
| 5 | 79.50% | 79.72% | +0.22 pp | +0.18 pp |
| 16 | 91.95% | 92.14% | +0.18 pp | +0.15 pp |
| 32 | 95.77% | 96.05% | +0.28 pp | +0.22 pp |
| 64 | 98.31% | 98.40% | +0.10 pp | +0.08 pp |

At k=5, the no-near-duplicate subgroup improves from 79.38% to 79.60%, the
implicit tier from 53.76% to 54.02%, and multi-call units from 67.24% to
67.29%. Tier-7 multiturn decreases from 66.73% to 66.60%. The k=5 fold deltas
range from 0.00 to +0.44 percentage points; k=16 is positive in every fold but
never exceeds +0.32 points. This is directionally consistent but too small to
count as meaningful information gain, and no fixed k passes the admission
gate. Retain public semantics as content for a semantic or hybrid retriever;
do not promote BM25 plus public descriptions as the engineering baseline.

## Information contract for the successor AgentLoop

Keep retrieval keys and supplied values separate:

1. `OBS` produces bounded English actionable spans, surviving corrections,
   prior-turn dependencies, requested multiplicity, and typed value spans.
2. `ORG` performs segment-aware label retrieval. Its primary metric is full
   required-label-set coverage at k; recall, precision, and distractor burden
   are required diagnostics.
3. `SUPPLY` loads only the selected labels' canonical values: exact tool name,
   operation meaning, sibling contrast, legal skeletons, types, enum casing,
   defaults, omission rules, and canonicalization rules. Construction example
   values are never candidate values.
4. `USE` is a genuine frozen-core call that must choose the ordered call set
   and bind values from speech/OBS under the supplied contracts.

Do not freeze k yet. First implement and compare improved construction-derived
key representations on a normalized-twin-grouped internal validation protocol.
The key stage must reach at least 95% overall full-set coverage, 97% label
recall, 90% in every tier and multi-call subgroup, and no more than 15 mean
distractors, with worst-fold and no-near-duplicate results reported. No tested
fixed k currently passes those gates. Only after the model-free gates, runtime
legality checks, execution-plan/preregistration requirements, and the separate
repository authorization are satisfied may a future >=104-row scored flight
be opened. This audit authorizes zero model contacts.

## Statistical role of the first 104-row flight

Eight rows remain smoke-only. At 104 paired rows, an exact-match gain of about
12.3 percentage points is the approximate 80%-power minimum detectable effect
under the historical 20/104 discordance rate for one two-sided alpha=.05
McNemar test. With two unordered primary tests and alpha=.025 per test, it is
about 13.3 points; freeze either family-wise correction or a hierarchical test
order before contact. Smaller positive effects remain exploratory. Report
paired wins, harms, ties, exact McNemar p-values, and a 10,000-replicate
tier-stratified paired bootstrap interval. Require separate contrasts for
AgentLoop versus single call and matched versus shuffled evidence. Other
registered supply actions contribute only to a descriptive sealed action-set
oracle; selecting the best action post hoc does not create an ordinary
significance claim.

The exposed 104-row cohorts have already influenced the current hypothesis.
They may support adaptive diagnosis but not independent evidence. A future
scored flight, if separately authorized, requires a new >=104-row roster that
is identity-, query-block-, and normalized-twin-disjoint from construction and
all exposed cohorts. Test remains unopened.

## Artifacts

- Machine summary: `summary.json`
- Deterministic generator and verification entry point: `run_audit.py`
- Construction audit implementation:
  `src/speech_aware_evidence_acquisition/analysis/a2t_construction_task_information_audit.py`
- Label candidate audit implementation:
  `src/speech_aware_evidence_acquisition/analysis/a2t_label_candidate_reduction.py`
- Multiturn 2 x 2 factorial implementation:
  `src/speech_aware_evidence_acquisition/analysis/a2t_observation_text_ablation.py`
- Label-blind grouped out-of-fold implementation:
  `src/speech_aware_evidence_acquisition/analysis/a2t_grouped_candidate_validation.py`
- Post-seal reachability metric implementation:
  `src/speech_aware_evidence_acquisition/analysis/a2t_retrieval_reachability.py`
- Proposal-content occurrence metric implementation:
  `src/speech_aware_evidence_acquisition/analysis/a2t_proposal_content_coverage.py`
