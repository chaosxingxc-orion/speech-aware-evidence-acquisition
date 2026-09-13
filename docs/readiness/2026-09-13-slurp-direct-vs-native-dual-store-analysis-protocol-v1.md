# SLURP direct versus native dual-store paired analysis

Status: frozen model-free analysis method. This protocol authorizes no model,
GPU, encoder, tokenizer, tool, scorer, network, quality read, or result read.
It applies only after both prospective DEV1000 arms seal and root records a
separate result-read release.

The machine-readable method is
`docs/readiness/2026-09-13-slurp-direct-vs-native-dual-store-analysis-recipe-v1.json`.
Its output family is `SAEA-SLURP-DIRECT-VS-NATIVE-DUAL-STORE-PAIRED-ANALYSIS-V1`.

## Compared systems

`SAEA-SLURP-DIRECT-MAX512-DEV1000-V1` sends one direct task-answer request with
the full 60-label task contract and no model-visible knowledge, candidate state,
review, or tool. `SAEA-SLURP-NATIVE-DUAL-STORE-DEV1000-V1` has live
Perception, up to eight retrieved intent-boundary values in Perception,
candidate-associated slot-contract values in Solver, Reviewer-only
task-contract tool authority, Planner acceptance or one bounded revision,
explicit terminal delivery, and Solver-owned final answering.

The arms share the DEV1000 roster, prepared speech packets, frozen max512 model
fragment, four 24576-token slots, deterministic decoding, and full task label
space. They are paired only by sample identity. Direct never shares realized
Perception state or evidence with native. This is a complete-system task-quality
comparison, not a knowledge ablation or a causal estimate for a role, store,
tool, or terminal policy.

The original exploratory positive system result, the strict replication stopped
at revision exhaustion, and the max256 recovery stopped at bounded-Perception
failure remain historical records. None is a matched input to this comparison.

## Scoring and paired read

After each complete 1000-row final-answer manifest seals, run
`slurp-slu-official` once through the shared complete-score batch path and keep
per-sample sufficient counts and the complete-score receipt. Do not shard,
rescore, project labels, repair outputs, or substitute a historical score.

Root binds measured manifest paths and hashes, score-receipt paths and hashes,
and receipt cell IDs in the frozen recipe. Then use the shared read-only
`speech_aware_evidence_acquisition.analysis.score_compare_cli` once. It invokes
no scorer.

Use 10,000 paired whole-speaker cluster bootstrap draws, seed 20260913, and a
two-sided percentile CI90. NEW500 is the primary historically exposed
population. OLD500 and DEV1000 are descriptive sensitivity populations and
cannot replace it. Natural-mixture estimates are primary. Equal-scenario point
estimates, per-scenario tables, and scenario-stratified paired-row bootstrap
remain required sensitivity reports.

Official pooled SLU micro F1 comes only from saved official word and character
TP, FP, and FN fields. It is distinct from mean per-sample official SLU F1.
Report both, with joint scenario/action intent accuracy, scenario and action
accuracy, exact slot/entity F1, final-output failures, saves, harms, and ties.

## Advancement and diagnosis

Advance as an exploratory complete-system capability only when the NEW500
official pooled SLU micro F1 speaker-cluster CI90 lower endpoint is above zero
for native minus direct and pooled-micro point deltas are positive on DEV1000
and equal-scenario reporting. This is an engineering selection rule for bounded
exploratory development, not superiority, generalization, confirmation, or a
component-effect claim.

Intent and regression outcomes remain required diagnostics, not arbitrary hard
vetoes. If the primary interval crosses zero, preserve the inconclusive result
and inspect the named complete-system bottleneck before an extension. If it is
wholly below zero, preserve the harmful result, reverse the prospective step,
and root-cause the named failure. Cost, latency, tokens, and calls are reported
but never reject a quality-positive result.

After release, use the existing `slurp_topn_diagnostics_cli` on the sealed native
bundle and its first official score receipt. It must retain every registered row
and report gold intent inclusion in the actual unpadded Perception candidate set
up to three, observed width, rank-one correctness, parse and saturation states,
candidate-missing cases, covered-but-final-incorrect cases, final-correct
outside-candidate cases, rank-one-to-final saves and harms, and per-population,
per-scenario, and observed-width tables. These are native-arm diagnostics, not
pairing keys, filters, weights, or post-hoc eligibility rules.

Use `analyze_verified_native_episode_statistics` on the same verified native
bundle and trace custody. Report raw role visits, all model contacts by role,
Planner actions and revisions, terminal Solver dispositions, tool events,
supplied values, lexical consumption, and OBS, ORG, SUPPLY, and USE provenance.
Lexical USE/COPY/IGNORE is descriptive overlap, not semantic or causal proof.

Candidate misses direct the next capability diagnosis toward discriminative
Perception evidence. Covered-but-unresolved rows or correct-intent entity errors
direct it toward Solver evidence use or slot resolution. Terminal, malformed, or
saturated deliveries require the named reliability repair first. If no
diagnostic dominates, hold the next mechanism for root review.

## Binding sequence

1. Verify both complete manifests without reading quality.
2. Run and retain each first complete official score and receipt.
3. Bind only measured paths, hashes, and receipt cell IDs in the recipe.
4. Record the result-read release.
5. Run the paired score reader once, then the native diagnostics on the same
   full sealed roster.
6. Preserve positive, inconclusive, and harmful outcomes and make the next
   capability decision from the frozen diagnostic hierarchy.
