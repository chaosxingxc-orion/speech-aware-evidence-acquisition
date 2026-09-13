# SLURP Top-N diagnostic entity adapter v1

This note freezes the analysis-only mapping used by the source-bound Top-N
diagnostic runner. It consumes a complete score result already verified by
core.scoring_receipt.verify_complete_score_receipt; it never invokes the
official scorer or reconstructs an entity score.

For each row of the configured official SLURP scorer, the adapter reads exactly
these sufficient-count fields:

- slot_f1_exact_fp
- slot_f1_exact_fn

The row is entity_correct=true exactly when both values are finite,
nonnegative, and equal to zero. These are the official exact
{type, filler} entity matching counts from reproduction.slurp_scoring
(SluScore), so the rule handles empty gold and empty prediction as correct
when both counts are zero. The adapter does not use slot_f1_exact_f1,
official SLU-F1, parsed text, or any other scalar as a substitute.

When either sufficient-count field is absent or invalid in the verified
per-sample rows, the adapter emits entity_correct=null for the affected
diagnostic input, preserving the unavailable state. A verified score roster
mismatch remains a hard error. The resulting value is attached to
BranchOutcomeRow only for diagnostic decomposition; it does not alter the
official score projection, estimand, gate, or branch outcome.

Observed candidate width is the descriptive count of distinct ordered source
candidate IDs after source verification. The runner groups rows at widths 1,
2, and 3 and calls the existing pure aggregate_topn_diagnostics once per
nonempty subgroup. The legacy shared_fixed_top3_source binding remains the
default; shared_distinct_source is an explicit opt-in binding.
