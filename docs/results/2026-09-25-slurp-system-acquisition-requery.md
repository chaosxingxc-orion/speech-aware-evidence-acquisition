# Whole-system acquisition availability and query contamination

Status: complete, model-free construction diagnostic, 2026-09-25.
This follows the complete-system trajectory attribution; it does not evaluate a
new system's task quality. No policy is promoted from this report.

## Question and source custody

Can the existing E36b acquisition seam return evidence that the complete native
episode has not already supplied? Replay the first review-to-plan boundary of
all 625 PLAN and all 625 PLANR trajectories, preserving missing boundaries.
These are repeated measurements on the same 625 inputs, not 1,250 independent
samples. Reuse the source's own hash-pinned minus-R01 composite knowledge.

The earlier 18-row E36b replay excluded prepared Perception evidence but did not
fully exclude separately supplied Solver exemplars. Here exclusion is the union
of evidence IDs in actual requests through the first Planner request. Future
revision requests cannot enter it. The normalized Reviewer state comes from that
Planner request, with an explicitly hypothetical ACQUIRE action. This does not
claim the historical Planner chose ACQUIRE.

Every consumed request matches the previously verified full-system export.
Raw trace hashes and composed source configuration hashes are checked again.
No target annotation, fresh DEV, test, F10 outcome, model, tokenizer, encoder,
official scorer or network contact is used. All output is IDs, hashes and counts;
raw text remains in the sealed sources.

## Availability result

| Diagnostic | PLAN | PLANR |
| --- | ---: | ---: |
| Whole roster | 625 | 625 |
| Available first review-to-plan boundary | 620 | 623 |
| Boundary absent, retained explicitly | 5 | 2 |
| Nonempty evidence returns | 613 | 614 |
| Nonempty returns / whole roster | 98.08% | 98.24% |
| Returned train exemplars | 2,725 | 2,720 |
| Returned slot contracts | 246 | 257 |
| Returned intent boundaries | 25 | 21 |
| Distinct ordered returned sets | 80 | 88 |
| Counts of three most frequent returned sets | 151 / 113 / 106 | 138 / 109 / 106 |

All 1,243 replay queries exactly agree with the existing independent diagnostic
ranking. Every returned ID is absent from previously supplied evidence. The
existing evidence renderer preserves returned identities; no next-node model
request was sent, so this is rendering availability, not semantic consumption.

There is no target-scenario stratification in this diagnostic because it excludes
target annotations. Natural full-roster and available-boundary denominators are
explicit. No effectiveness verdict or stratum-independent quality claim follows.

## Post-hoc query-surface diagnosis

High return availability is not evidence of relevance. After the availability
read, inspect protocol artifacts in the same source states without reranking.

| Diagnostic | PLAN | PLANR |
| --- | ---: | ---: |
| Reviewer state is strictly parseable JSON with a top-level tool_call field | 319 | 313 |
| Reviewer state contains the literal tool_call marker | 348 | 336 |
| Splitting a tool_call filter retains its call token as a search key | 317 | 304 |
| Hypothetical ACQUIRE action survives as a search key | 139 | 143 |

Textual tool calls are not executed tools. The preceding source-bound attribution
found zero exposed schemas in every Reviewer request despite instructions to call
the task-contract tool. The present observation identifies a concrete cross-node
failure mode: protocol text passes as a review, the lexical query derivation
accepts it, and a common language token extracted from that protocol can retrieve
new knowledge. The hypothetical routing action can also contaminate the query.

The three most frequent evidence sets account for 370/620 and 353/623 available
boundaries. Concentration alone does not prove irrelevance; combined with the
explicit protocol-to-key path it makes raw nonempty-return counts an inadequate
admission criterion. No result here proves the retrieved content would help or
harm an actual revised answer.

The E36b rule is findings-keyed lexical search over the released composite store.
Owner decision 90 places this named mechanism in Stage 3. Do not describe it as
a speech-vector query merely because older acquisition docstrings describe the
legacy speech-ranking restriction.

## Root decision

Do not fly the unchanged held B9a-v2 policy as the next system treatment.
Retain its production retrieval, routing and rendering seams. The next coherent
policy must connect a specific supported issue to an explicit information need,
a clean query, provenance-preserving evidence, a bounded plan, and a Solver
revision. Wrapper removal alone is engineering and does not establish RL benefit.

Measure its complete delivered result against a matched full-system control.
Retain untriggered, failed, abstaining and action-not-reached episodes; report
correct repairs and newly introduced errors. A local search hit or local Solver
gain never admits the policy on its own.

See docs/readiness/2026-09-25-stage3-coordinated-system-family.md for the next
family design. F10 generation and official scoring continue unchanged on their
frozen checkout, and no partial F10 results were read here.

## Reproduction and receipt

- Registered recipe: docs/readiness/2026-09-25-stage3-system-requery-read-v1.json.
- Availability entry: scripts/analysis/system_acquisition_requery_read.py.
- Post-hoc note: docs/readiness/2026-09-25-stage3-system-requery-query-surface-note.md.
- Post-hoc entry: scripts/analysis/system_acquisition_query_surface.py.
- Receipt: docs/receipts/continuation/2026-09-25-system-requery-replay.json.
- External artifacts: analysis/SAEA-SLURP-STAGE3-SYSTEM-REQUERY-READ-V1/
  replay.json and query-surface-v2.json under SPEECHRL_DATA_DIR. The first query-surface.json is
  preserved as superseded; v2 explicitly checks whether the hypothetical action
  introduced ACQUIRE. It did in all 139/143 cases.
- Validation: 48 focused tests, including actual existing OpenJiuwen acquisition
  integration tests, and the engineering base check passed in WSL.

Other required offline checks returned successfully. The results-ledger check
reported 103 findings and skipped the unreachable umbrella comparison; the
handoff check reported historical-snapshot and in-progress-change warnings.
Neither check supplies launch authority for a new GPU cell.
