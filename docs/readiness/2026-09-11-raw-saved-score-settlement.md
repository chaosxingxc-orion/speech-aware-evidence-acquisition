# Complete raw saved-score settlement

The offline E21 direct and KC-E1f repair experiments score their ordinary
complete outputs directly. Their recorded experiment fragments contain no
delivery derivative declarations. The older delivery settlement API therefore
cannot settle these parents, and finalize_bundle would unnecessarily rescore
and attach new bytes to the original manifest.

Use core.bundle.settlement.settle_scored_attempt with the parent manifest,
repository checkout, exactly pinned SavedScoreReceiptRef and a new DATA
settlement path. The common implementation verifies the whole saved score
receipt, configured scorers, complete per-sample roster, original manifest and
output identities. It reads the parent's recorded experiment Git blob and
refuses any phase or legacy delivery obligation. It then uses the existing
atomic publication, independent verification and idempotent finalization path.

Call verify_scored_attempt_settlement afterward. It reconstructs the evidence
and checks the durable attempt's exact finalization binding. The operation
does not invoke a scorer, generate a derivative, rewrite sealed evidence,
change scientific thresholds or grant a scientific admission. Root still
reviews the comparison, lineage, cost caps and scientific decision before
settling either production attempt.

Validation in WSL Ubuntu-24.04:

- The ten initial tests failed because the raw saved-score API was absent.
- All 112 saved-score, settlement and delivery tests passed after implementation.
- The shared settlement module has 81 percent branch-enabled coverage.
- The real synthetic generation-to-saved-score-to-settlement test proves
  immutable source bytes, no scoring during settlement and exact retry reuse.
- Refusal tests cover declared derivative bypass, incomplete/foreign parents,
  changed receipt/score/manifest/cell bindings, terminal attempts, malformed
  saved settlements, output confinement, overwrite and interrupted publication.
- Ruff and the existing engineering-base check passed.

The running SLURP and E21 generation/scoring checkouts were left frozen.
