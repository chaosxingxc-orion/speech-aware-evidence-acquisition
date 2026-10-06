# SLURP process diagnostics v1

Status: offline diagnostics and complete22-member backfill are complete and root-reviewed.
See docs/results/2026-10-06-slurp-update3-process-diagnostics.md. Prospective
abstract learner integration and actual packet preparation are complete; actor
admission remains separate.
No new task generations, model calls, official scoring, policy adoption or runtime
knowledge changes are authorized or performed by this package.

## Owner direction and objective

The owner requests intermediate statistical monitoring in addition to terminal
quality: determine whether correct targets were available in retrieved evidence,
whether review detected errors, and whether revisions repaired or damaged answers.
Treat latency as one process measure. Prioritize business quality and reliable
completion, then explain failure mechanisms and resource tradeoffs.

Maintain the current fixed-knowledge consumption hypothesis as a working
assumption, not a conclusion proved by zero tool calls or by availability alone.
Do not rebuild knowledge or change retrieval merely to produce these diagnostics.

## Metric contract

Use the first completed Solver draft and its first completed Reviewer before the
next Solver visit as the primary input-level observation. Bind contacts, requests,
responses and final delivery through the existing shared source verifiers. A later
review must never be compared with the initial draft. Additional visits may be
reported descriptively, but must not inflate the independent sample denominator.

| Layer | Metric and denominator | Interpretation |
|---|---|---|
| Retrieval pool | Gold intent inclusion at the actual configured breadth / inputs with a verified pool | Availability before selection; never substitute a new retrieval execution. |
| Actual context | Gold intent card present / inputs with verified initial requests | Delivered support, not evidence of semantic use. |
| Perception | Gold intent in actual initial candidate set / inputs with verified initial states | Distinguish support delivery from model extraction. |
| Slot support | Gold type coverage and exact (type,value) coverage, separately for pool and actual node contexts | Do not merge type knowledge with instance-value availability. Audio may supply unseen values. |
| Selection/assembly | Complete gold coverage lost between pool and delivered context / inputs with both projections | Locate dropped or truncated material. Partial support loss is also retained as hit counts. |
| Initial answer | Intent/entity/full exact and parse validity | Separate semantic errors from invalid/unavailable drafts. Exact slot metrics are diagnostic, not official soft SLU-F1. |
| Review availability | Valid first-draft review / observed first-draft reviews; missing review count separately | A malformed or absent review is not a no-error verdict. |
| Error detection | Alarm on entity-incorrect draft / entity-incorrect drafts with observable reviews | Episode-level sensitivity, not semantic correctness of the criticism. |
| Alarm precision | Entity-incorrect draft with alarm / alarmed drafts with observable draft correctness | Prevent reward for indiscriminate criticism. |
| False alarm and miss | Alarm on entity-correct draft / entity-correct drafts; no alarm on incorrect draft / incorrect drafts | Report both alongside coverage and missingness. |
| Finding localization | Findings aligned to actual erroneous slot types / verifiable findings | Requires a separate source-bound projection; type overlap alone does not prove correct reasoning. Not yet implemented. |
| Handoff | Actual normalized review visible in next Planner request / valid reviews with observable Planner requests | Visibility is not semantic consumption. |
| Revision | Completed revision after alarm / alarmed drafts | Execution association, not proof the alarm caused revision. |
| Repair | Incorrect initial answer becoming correct / incorrect initial answers actually revised | Report entity and full-answer endpoints separately. |
| Damage | Correct initial answer becoming incorrect / correct initial answers actually revised | Retain harms; do not select only repaired cases. |
| Net transition | Wrong-to-correct count minus correct-to-wrong count, with all four transition cells | No causal credit claim; include unknown endpoints. |
| Empty entities | False entity fill / parseable terminal outputs with empty gold entities | Keep empty-target cases and parse failures distinct. |
| Resources | Calls, tokens, prompt processing/decode/queue time, first/non-first input latency, reliable completion | Explain costs after business and process diagnostics, not as a replacement reward. |

The current slot Reviewer has no general intent-review contract. Do not market
its entity-error sensitivity as detection of every SLU error. An alarm on a wrong
sample can still contain a wrong criticism; the current module explicitly makes
no claim of semantically correct criticism or causal node contribution.

## Statistical rules

- Store numerator, observed denominator, eligible count, unknown count, value and
  descriptive Wilson 95% interval for every binary input-level rate.
- Preserve zero-denominator values as null. Preserve missing source as unknown,
  distinct from a verified empty retrieval set or a valid empty findings list.
- Report lower/upper missing-data bounds alongside conditional rates. In particular,
  detection among valid reviews must not hide invalid reviews on erroneous drafts.
- Report scenario strata and gold-empty diagnostics. Keep whole-roster official
  pooled SLU-F1, intent and reliable completion first, including failed/abstaining inputs.
- Use paired resampling by original input for policy differences; retain all branches
  within the same resampled input. Do not pool repeated templates or role visits as
  independent observations. Wilson intervals here are descriptive, not such tests.
- Reused N20 optimization, adaptive selection and multiple comparisons do not establish
  stable benefit. Keep A/A variability visible and do not retroactively change the
  completed trial's retention criterion.
- Do not combine quality, review counts and latency into an arbitrary weighted score.
  High alarm frequency, long reflection or many revisions are not optimization targets.

## Implemented interfaces and remaining source coverage

`analysis.slurp_process_metrics.build_slurp_process_metrics` reuses
`build_slurp_solver_stage_attribution`, native role-response custody and
`analyze_slot_review_episode`. It verifies saved final counts against the existing
deterministic per-input scorer. It never invokes the official corpus evaluator.
Its optional intent-support configuration calls the existing actual Perception
request/state/supply joins, including frozen store identity and request hashes.
Missing or invalid declared mappings fail closed; an absent optional mapping is
explicitly unavailable, not zero coverage.

`measure_support` supplies exact-set arithmetic for intent IDs, slot types and
(type,value) pairs. It does not attest actual source custody. Raw retrieval-pool
coverage and entity content support remain unavailable in the composed report
until their actual sealed selections and request contents are joined. Do not label
a counterfactual retrieval audit as as-flown recall. Existing evidence may establish
card presence only; no substring heuristic establishes knowledge sufficiency.

`aggregate_process_metrics` accepts abstract flags only and rejects unexpected
fields, duplicate input IDs and integer/string substitutes for booleans. All output
is root-only; the statistical reducer does not grant scientific READ authority.

## Next execution order

1. Register exact completed-family diagnostic sources and original saved-score hashes.
   Preserve all complete members, rejected children and no-change versions.
2. Backfill existing sealed traces offline through these interfaces. Add verified raw
   pool/slot-content projections where those sources exist; mark absent evidence as
   unavailable. Do not rerun GPU tasks to manufacture missing historical telemetry.
3. Present the complete process funnel per policy with scenario strata, unknowns and
   uncertainty. Rank repair work by available headroom, error prevalence, harms and
   confidence; do not assume retrieval is the limiting stage.
4. Prospectively version a learner projection of anonymous numeric aggregates and
   editable templates. Exclude gold text, reference transcripts, task answers, source
   lists and concrete cases. Do not automatically export this root-only report.
5. Evaluate new consumption templates on the current registered small-panel protocol.
   Retain official system quality and reliable completion as primary decision evidence;
   use process metrics to explain and prioritize, and latency to quantify cost.

These steps preserve fixed assets, immutable experiment config, temperature/seed,
complete-family READ, existing model/score custody, other-carrier holds and the human
review boundary before 8x400.

## Delivery normalisation compatibility correction

The first complete backfill stopped before any report publication because the
legacy draft/final attribution helper required raw response bytes to equal delivery.
Reuse the existing I7n verifier to replay the registered deterministic normaliser
against the pinned response and exact final bytes. Missing or inconsistent receipts
still fail closed. Preserve both raw and delivered hashes. Report initial raw Solver
versus selected raw Solver separately from selected raw Solver versus final delivery.
These transitions are descriptive and do not establish causal Reviewer contribution.
All original task outputs, scores and failed diagnostic logs remain unchanged.
