# Released TRAIN A temporal-slot diagnosis

Date: 2026-09-16. Analysis and interpretation owner: root.
Scope: the complete released SLURP TRAIN A anchor, exactly 1080 rows; no live A1 result.

## Main finding

Date omission and time representation are different observed failure patterns. The date knowledge card was present in the actual initial Solver and Reviewer requests for all 84 rows with an unmatched reference date. In 25 of these rows, the omitted date expression also occurs in an initial Perception candidate distinction. This establishes an available-information-to-delivery gap in those traces. It does not establish that the model grounded, understood, or consciously consumed the expression.

The same-type time pairs often differ in number representation, AM/PM spelling, or extraction boundaries. The existing slot contracts do not fully specify those serialization boundaries. Generic advice to preserve the speech is already available and is not a new mechanism.

## Complete population and saved-score reconciliation

Use every released row, including all seven unparsed final answers. The shared parser and entity attribution reproduce every saved per-sample word and character TP/FP/FN ingredient, exact entity TP/FP/FN, parse flag and intent-correct flag. No official scorer was invoked again.

| Diagnostic | Date | Time |
| --- | ---: | ---: |
| Reference mentions | 138 | 76 |
| Predicted mentions | 61 | 66 |
| Same-type matched pairs | 54 | 55 |
| Exact filler pairs | 28 | 8 |
| Case/whitespace-only pairs | 10 | 0 |
| Reference token sequence contained in prediction | 9 | 5 |
| Prediction token sequence contained in reference | 2 | 2 |
| Other nonexact pairs | 5 | 40 |
| Unmatched reference mentions | 84 | 21 |
| Unmatched predicted mentions | 7 | 11 |
| Unmatched predictions occurring in reference sentence | 4 | 5 |

The alphanumeric-equivalent category contributes zero pairs for both types. Word and character greedy matching chose the same reference partners for these temporal pairs; this was checked rather than assumed. Pair counts are not sample-level accuracies. An unmatched reference can coexist with another matched entity of that type in the same sample.

Date accounts for 253.16196 and time for 212.67688 units of official combined FP+FN mass, respectively 10.89% and 9.15% of all-type loss mass. Before cross-type residual heuristics, unmatched references contribute 168 date units and 42 time units. Time's same-type surface differences contribute 148.67688 units. These are descriptive partitions of existing score ingredients, not estimated recoverable gains.

Of the 842 rows whose final intent is correct, 67 reference dates and 12 reference times remain unmatched. The pattern therefore survives conditioning on correct intent and cannot be assigned entirely to candidate coverage.

## Actual request exposure

Use the existing native-source verifier and shared role-contact request/response/USE join. Exact slot-card content is matched to the released snapshot, rather than inferred from configuration or index eligibility.

| Diagnostic | Date | Time |
| --- | ---: | ---: |
| Rows with an unmatched reference mention | 84 | 21 |
| Those rows with card exposed to initial Solver | 84 | 20 |
| Those rows with card exposed to initial Reviewer | 84 | 20 |
| Missing mentions occurring in initial candidate distinctions | 25 | 3 |
| Correct-intent rows with an unmatched reference mention | 67 | 12 |
| Correct-intent missing rows with Solver card exposed | 67 | 12 |
| Correct-intent missing mentions occurring in candidate distinctions | 19 | 2 |

All 1080 initial Perception, Solver and Reviewer requests include speech-feature parts and a speech-packet identity. The architecture does not force Solver to rely solely on a text summary. A textual occurrence in a candidate distinction is a hypothesis-side observation, not an independently verified transcript or ground-truth signal. This audit does not prove causal attention failure or an acoustic error.

Root inspected the complete temporal mismatch-pattern display and illustrative source-ordered trace cases offline. The inspection found both omitted temporal modifiers already represented in candidate descriptions and candidate descriptions that abstract away such modifiers. Some words appear under a different predicted entity type. Root also observed number/AM-PM formatting differences and a time revision that improved partial matching while losing a temporal relation. No reference or predicted filler strings are exported into this report, its derivatives, or runtime knowledge.

## Existing knowledge and the remaining gap

The authored date/time contracts already cover explicit mentions, omission when unsupported, distinct temporal roles, range relationships and preservation of spoken forms. The date contract binds 40 intents; time binds 34. These bindings select a complete global card and add a semantic-role label. They do not implement intent-specific token-boundary or normalization rules.

Root verified the two released temporal values directly after the bounded read-only knowledge audit. The underlying construction was based on permitted support IDs. Its limitations explicitly acknowledge inconsistent temporal annotation boundaries. Therefore neither uniform modifier stripping nor inventing canonical dates is justified by this result.

Separate three questions:

1. **Completeness and grounding:** Is every supported, task-relevant speech mention represented, and does every proposed entity have supporting speech? The 25 omitted dates already named in candidate distinctions make this a concrete review target.
2. **Semantic assignment:** Which candidate intent and entity type explains the observed relation? A mention being present does not determine its type. Intent distinctions and slot-role knowledge remain separate stores.
3. **Serialization and span policy:** How should the supported entity be rendered under the dataset contract? Source-derived representation rules may add information beyond generic preservation instructions. Build and validate any such content on admitted construction rows excluding evaluation A/B.

Do not treat these questions as one generic instruction to think harder. Do not infer that another ASR pass repairs all of them.

## Complete scenario view

Every scenario contributes 60 rows. Natural-mixture and equal-scenario row weighting coincide on this balanced roster; pooled official F1 still aggregates mention-level ingredients and is not a mean of scenario F1 values. Do not average the following counts into a new quality verdict.

| Scenario | Date references | Missing date mentions | Missing-date rows with Solver card | Nonexact date pairs | Time references | Missing time mentions | Nonexact time pairs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 18 | 7 | 7 | 5 | 32 | 5 | 23 |
| audio | 0 | 0 | 0 | 0 | 4 | 1 | 2 |
| calendar | 29 | 14 | 14 | 8 | 9 | 5 | 3 |
| cooking | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| datetime | 23 | 10 | 10 | 7 | 7 | 1 | 6 |
| email | 5 | 4 | 4 | 0 | 8 | 4 | 4 |
| general | 4 | 4 | 4 | 0 | 0 | 0 | 0 |
| iot | 0 | 0 | 0 | 0 | 3 | 1 | 2 |
| lists | 4 | 2 | 2 | 0 | 0 | 0 | 0 |
| music | 1 | 0 | 0 | 1 | 0 | 0 | 0 |
| news | 5 | 5 | 5 | 0 | 1 | 1 | 0 |
| play | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| qa | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| recommendation | 9 | 5 | 5 | 1 | 2 | 1 | 0 |
| social | 2 | 2 | 2 | 0 | 0 | 0 | 0 |
| takeaway | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| transport | 6 | 3 | 3 | 1 | 7 | 1 | 6 |
| weather | 31 | 27 | 27 | 3 | 2 | 1 | 1 |

## Decision for the two-track plan

Keep the active maximum-five arm unchanged. Its complete paired verdict determines whether to replicate the coverage lead or diagnose a downstream loss. Do not use this offline follow-up to alter that run.

For Track B, prioritize an evidence-to-answer completeness and provenance check. Reviewer should name the questionable relation and its evidence, rather than accept a fluent answer or promote candidate alternatives into observed facts. Planner chooses whether to request missing knowledge, acquire uncertain speech evidence, or send one bounded revision to Solver. Solver retains final-answer authority.

The held structured Reviewer configuration and optional no-example global contract remain preparation capabilities, not an admitted bundle. Existing full slot cards are already visible in the affected rows; fetching the same card through a tool is not automatically information gain. A later targeted value should resolve a demonstrated missing distinction. ASR or selective listening is appropriate only where the available observation leaves the relevant speech content unresolved.

Finalize one small, source-justified Track B contrast after A1. Do not simultaneously change candidate width, knowledge contents, task-contract examples, Reviewer context and acoustic tools and then attribute the package to one component. Any stable-base claim still requires full-task improvement, same-roster replication and the matched shared-harness direct baseline.

## Custody and reproducibility

- Recipe: docs/readiness/2026-09-16-slurp-temporal-slot-diagnosis-v1.json; SHA256 e38d42c56f479644d23a91737c810512bf32d4ab307f2a44e2dde931aa263cbd.
- Request-exposure recipe: docs/readiness/2026-09-16-slurp-temporal-supply-followup-v1.json; SHA256 aa75a9687a3719ebfd08b49f016a16cb8ea2a628a2b176f2c3e74695e367df5f.
- Numeric temporal artifact: DATA/analysis/SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1/temporal-slot-diagnosis-v1.json; SHA256 107194fa81dc054517aad0d70b0fa521589baaee947bb211253d1243e06f5dcb.
- Numeric request-exposure artifact: same directory, temporal-supply-followup-v1.json; SHA256 1db6affc29c7a8f8a7f4aa11ef3fb8e8fb8dbc74c6ecf5331e1f3d403ec74883.
- Released slot snapshot raw SHA256: 0de5418caaf8642bfabc402a64d228d77ae76d57b23c0d23caf24164fcf0d37a.
- Thin orchestration: DATA/coordination/slurp-review-measurement-v1/temporal-slot-diagnosis-orchestration-v1.py and temporal-supply-followup-orchestration-v1.py; each derivative pins its orchestration hash. They call existing shared loaders, parsers, attribution and native custody APIs. They are offline analysis artifacts, not an experiment execution framework.
- Validation: exact roster, all saved ingredients, type presence/pair counts, both intent cohorts and all scenario totals reconcile. Numeric derivatives contain no reference/prediction sentence or filler strings.

The hypothesis selection is informed by the earlier released loss ranking. This is exploratory diagnosis, not an independent or confirmatory effectiveness result. No model, tokenizer, ASR, encoder, audio decode or official scorer contact occurred. The governed reference loader validates selected audio headers and byte hashes only. Fold B, live A1 quality and aborted-flight quality remain unread. The twice-failed tool flight remains closed.
