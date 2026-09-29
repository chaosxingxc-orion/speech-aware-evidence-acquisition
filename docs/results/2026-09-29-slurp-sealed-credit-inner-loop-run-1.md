# Sealed-credit inner loop, run 1: nominates `phase_supply.k = 10` (+0.4800 pp intent, DESCRIPTIVE, model-free)

Run 2026-09-29 by Claude Sonnet 5 (worktree `/home/chao/saea-worktrees/fable-innerloop`, branch
`fable/innerloop`), implementing `docs/superpowers/specs/2026-09-29-sealed-credit-inner-loop-run-1-design.md`
and its "Coordinator rulings (Fable 5.1, 2026-09-29)" section. This is **not** a registered READ row and
**not** a cell: `sealed_credit_inner_loop.py` registers no cell, authorises no flight, and makes zero model,
server, tokenizer, encoder, scorer-subprocess, network or GPU contact -- it reads only already-sealed
`phases.json` / `scores.json` / `outputs.jsonl` artefacts and the governed TRAIN gold loader. The nomination
below is input to the coordinator's own registration decision, not a claim of benefit.

## What ran

```
scripts/analysis/sealed_credit_inner_loop.py --pools configs/analysis/sealed-credit-pools-v1.json \
    --policy-space configs/analysis/sealed-credit-policy-space-v1.json \
    --read-design same-flight-supply-variant \
    --out "$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-SEALED-CREDIT-INNER-LOOP-RUN-1-V1" \
    --lock <umbrella>/docs/datasets.lock.json --data-root "$SPEECHRL_DATA_DIR"
```

Twelve tuning pools (R01C: `roll-1`, `var1-plan`, `var1-planr`, `var1-ex-k10`, `var1-ex-k30`, `var1-ex-div`;
TRAIN Fold A: `roll-2`, `agree`, `wave-aa`, `w1`, `w3a`, `w4`), fourteen policy-space knobs. Output under
`$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-SEALED-CREDIT-INNER-LOOP-RUN-1-V1/`: `row-states.jsonl`,
`credit.json`, `candidates.json`, `nomination.json`, `report.md`, `content-sha256.json`. Byte-reproducible
(`--check` re-derives and diffs; IDENTICAL apart from `generated_at`).

**DESCRIPTIVE.** No admission or superiority verdict. A development read on TRAIN pools (decisions 28, 86).

## Credit table headline (`agree`, the primary Fold A reference pool, n = 1,080)

`d_ok` 927 (85.83 %), `s1_ok` 907 (83.98 %), `reviewer_visited` 1,076, `revised` 23, `normaliser_changed` 108.
P(Solver's first answer correct | Perception rank) -- reproduces the design spec's own section 2b AGREE
numbers exactly: rank 1 97.57 % (907 rows), rank 2 26.98 % (63 rows), rank 3+ 12.00 % (25 rows), absent
2.35 % (85 rows). By boundary-block position: 1 -> 97.83 % (831), 2-3 -> 60.00 % (160), 4-8 -> 24.49 % (49),
none -> 15.00 % (40).

## Top 5 candidates (ranked by predicted intent gain; guard/floor at n = 1,080, same-flight-supply-variant
design: both 0.3163 pp, `stage3_effect_floor_check.FLOOR_TABLE`)

| rank | knob | value | predicted intent pp | predicted SLU pp | clears floor | note |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `phase_supply.k` | 10 | +0.4800 [-1.12, +2.24] | -0.2827 | **True** | VAR-1 EX-K10 vs PLANR, paired, n=625 |
| 2 | `presentation_id` | rank-visible-v1 | +0.2870 | n/a | False | RANKVIS cited (probe-transfer caveat) |
| 3 | `min_candidates` | 3 | +0.0536 | n/a | False | 6 rows cited (P-SV-2 ceiling) moved absent->3+ |
| 4 | `boundary_phase_supply` | +1 step | 0.0000 | 0.0 | False | unobserved: no moved-row estimate |
| 5 | `candidate_supply.max_candidates` | +1 step | 0.0000 | 0.0 | False | unobserved: no sealed source |

Full 16-candidate ranking also carries: `phase_supply.k = 30` (cited from the W-SV-1 same-flight column
read: intent +0.3704 pp, official pooled SLU-F1 -0.4582 pp -- discarded by the SLU guard), `release_swap =
slot-contracts-w4-v1` (W4 vs wave A/A: intent -0.0926 pp), `deliver_normaliser = off` (-1.9444 pp, harmful),
`reviewer_planner = off` (-1.8519 pp intent, guard-discarded), and five `unobserved` knob values (no sealed
conversion source: `phase_supply.fuse_coverage.{m,c,top_l}`, `presentation_id = top2-contrast-v1`,
`rank_weights.w_agree = 0.0`, both `relisten_acceptance` values).

## Nomination

**`phase_supply.k = 10`** (flown value 20): predicted intent +0.4800 pp (CI95 [-1.12, +2.24], n = 625, VAR-1
EX-K10 vs PLANR paired on their shared R01C rows), predicted SLU -0.2827 pp (mean per-row official
`slu_f1_f1`, not the pooled/micro aggregate) against the same-flight guard of -0.3163 pp -- not discarded.
Floor 0.3163 pp cleared. Claim ceiling `nominated` (never `admitted`: a same-flight read cannot admit, per
the same-flight-supply-variant instrument design's own Q6 ruling).

**Caveats for the coordinator's own reading:**
- The CI95 crosses zero and the two-fold cross-fit is unstable (fold values -0.33 pp and +1.24 pp) --
  `candidates.json`'s `fold_intent_pp` carries both; this run applies the coordinator's own mechanical rule
  (point estimate vs. floor) without an added significance filter.
- The SLU side is a mean-of-per-row `slu_f1_f1` proxy everywhere a pool-pair or exact-offline toggle is used
  (`pool_pair_delta`, `credit_table_reviewer_toggle`), not the official pooled/micro SLU-F1 the paper-facing
  number is; every affected candidate's `evidence` block states this.
- `min_candidates`'s and `presentation_id`'s moved-row / conversion counts are cited from the design spec's
  own text (the P-SV-2 "about 6 rows" ceiling; RANKVIS's m=19/119 vs. a 15.9-row no-op), not independently
  measured in this run.
- `derive_arm` (the node-gain ledger's own row extractor) was not literally lifted into the new package: it
  is two-arm/single-sample/Fold-A-only by the design spec's own admission and its remaining dependencies are
  other `scripts/analysis` drivers, not primitives. `note_state`, `gold_item_states`, `entity_items` and
  their transitive closure (`canonical`, `norm_distance`, `contiguous_in`, `pair_kind`, `fold`,
  `edit_distance`) ARE lifted into `analysis.sealed_credit.entity_states`, and both
  `slurp_agree_arm_error_sources.py` and `slurp_node_gain_ledger.py` now import them (`--check`
  byte-identical apart from `generated_at` and the ledger's own recorded driver-hash provenance line).

## What this run does not claim

No admission, no superiority, no generalisation, no claim about any carrier but SLURP. No candidate other
than the one named above was even offered a floor comparison that it passed. Registration of a cell from
this nomination is the coordinator's own decision.
