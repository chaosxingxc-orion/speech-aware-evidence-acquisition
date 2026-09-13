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

When either sufficient-count field is absent in the verified per-sample rows,
the adapter leaves entity_correct unavailable for that branch input. Negative
or nonfinite counts are rejected as malformed; they are never treated as
ordinary task errors. A verified score roster
mismatch remains a hard error. The resulting value is attached to
BranchOutcomeRow only for diagnostic decomposition; it does not alter the
official score projection, estimand, gate, or branch outcome.

Observed candidate width is the descriptive count of distinct ordered source
candidate IDs after source verification. The runner groups rows at widths 1,
2, and 3 and calls the existing pure aggregate_topn_diagnostics once per
nonempty subgroup. The legacy shared_fixed_top3_source binding remains the
default; shared_distinct_source is an explicit opt-in binding.

Root integration closure: recognize the actual shared source through core.bundle.hypothesis_source.is_derived_hypothesis_bundle after the common bundle verifier rebuilds its first-occurrence projection. Load the original hash-pinned source baseline for the legal candidate catalog. The source remains DERIVED/COMPLETED_DERIVATION with an ABORTED original attempt; never require or fabricate a FINALIZED source run. The hypothesis_artifact pin is explicit, and conflicting source aliases are rejected. The diagnostic config adds measured bindings and the existing offline reference adapter only; it changes no estimand, gate or source population.

Variable-width closure: the distinct opt-in interprets candidate_width as a maximum. Retain every actual candidate set without padding, including widths one and two, in full-population and stratum aggregates. The historical fixed-width path still rejects short rows. Synthetic source-binding and aggregation checks: 42 passed; Ruff passed. This repair changes no source response, official score, primary estimand or threshold.
