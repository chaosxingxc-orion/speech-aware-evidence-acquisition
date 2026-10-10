# SCR TF-0: the offline learner of sealed-credit routing (model-free)

Design of record: `docs/readiness/2026-10-10-slurp-tfrl-sealed-credit-routing-design-v1.md` sections 1-3 and 6. Driver:
`scripts/analysis/slurp_scr_offline_learner.py`; tests: `tests/unit/test_slurp_scr_offline_learner.py` (synthetic pools).
Status: DESCRIPTIVE development numbers (owner decisions 28 and 86), TRAIN Fold B only. Zero contacts (model, server, GPU,
network, paid API, scorer subprocess). Gold enters only as reward and evaluation strata through the governed loader
(`DRV.load_gold`, TRAIN); the context signature takes no gold argument. No utterance text, gold value, note body or model
output is printed or persisted.

## What it does

1. **Pools** (all 1,080 Fold B rows): R1 i1 (`lock`, `aa`, `r1-c1..c5`), R1 i2 (`lock`, `aa`, `r1-i2-c1..c5`), R6-P1 level-2 Solver
   answers (`lock`, `aa`, `p1`, `p2`, `p3`; actions `r6-p1..p3`). Each arm's rendered first-visit column is scored in-process with
   the R6 driver's official scorer path; the v3 in-process counts must equal the sealed per-sample fields and the pooled
   value must equal the sealed official aggregate (the run stops otherwise); then the registered `saea-deliver-normalise-v4g`
   normaliser is applied and re-scored. Reward of an action on a row = its count vector (word/char TP/FP/FN, slot-exact
   TP/FP/FN, intent indicator) minus the SAME-FLIGHT lock row. The routed column = the reference lock column (i1) plus the
   chosen actions' same-flight deltas, re-scored exactly (pooled official SLU-F1), paired whole-utterance cluster bootstrap
   (10,000 draws, seed 20260915). Post-Solver actions: `empty` (empty the lock row) and the extra composites
   `empty-if-c3-i1` / `empty-if-c3-i2` (the R6 `c3verdict` delivery: empty the lock row where that flight's c3 answered empty;
   not in the default set, reported in the `*_plus_verdict` subsets).
2. **Signature** (pre-Solver, model-free, gold-free), exact definitions in `report.json` `feature_definitions` and in the
   routing table: N1 (entity-free share of the 20 supplied exemplars) and its within-rank-1-intent share, TRAIN entity rate of
   the rank-1 intent and of the exemplar-majority intent and the shortlist maximum
   (`prepared/SAEA-SLURP-V4-TRAIN-STATISTICS-V1/intent-entity-rate-v1.json`), shortlist size, rank-1 distinction tokens /
   unresolved / evidence-ref counts, audio seconds, channel (roster receipt headset flag), top-1 exemplar cosine. Optional
   groups: `pre+p1tag` (R6-P1 p1 presence tag on the rank-1 candidate, TAG-GRAMMAR-v1) and `pre+post` (lock answer item count and
   delivered-intent entity rate). Missing values take the pinned median fill.
3. **Learner**: per action, a regressor of the per-row gain (linearised pooled SLU-F1 pp: `100 (dN - F dD) / D` at the reference
   lock totals, linear in the TP/FP/FN deltas) on the signature; `tree` = CART depth <= 3, min leaf 60; `logistic` = L2 logistic
   models of P(gain > 0) and P(gain < 0) with the training mean magnitudes. Fitted on one utterance-hash half, predicted on
   the other, both directions. A row is routed to the highest predicted gain only when it exceeds the margin (default
   0.0033 pp per row = 0.1 x the 0.033 pp false-fill exchange rate); otherwise it stays on the lock. The pre-declared headline
   is `tree|pre` (the pre-Solver signature); everything else is reported beside it and labelled secondary.
4. **Routing table** `prepared/SAEA-SLURP-SCR-ROUTING-TABLE-V1/` (`routing-table-v1.json` + `.md` + `receipt.json`): one tree
   per action fitted on all rows, the realised routing cells with n, in-sample gain, per-half gain and the cross-fitted gain, the
   feature definitions and fill values. `route_row(table, signature)` executes it from the signature alone; the run asserts it
   reproduces the fitted policy on all 1,080 rows. The executable policy is the per-action trees plus the margin rule (the 214 joint
   cells are a readable report of it, not the rule).
5. **Outputs** `analysis/SAEA-SLURP-SCR-TF0-V1/` (`report.json`, `tables.md`, `content-sha256.json`), write-once.

## Run

    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_scr_offline_learner.py --dry         # identities only
    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_scr_offline_learner.py --no-write    # full run, nothing written
    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_scr_offline_learner.py --extended    # write-once outputs

`--actions` replaces the default set `lock,r1-c3,r1-i2-c3,r1-c5,r1-i2-c4,empty`; `--margin-pp-per-row`, `--min-leaf`,
`--max-depth`, `--shrink`, `--intent-weight`, `--no-tag` are the knobs. Wall time about 3 minutes.

## Controls and read-outs in `report.json`

- `machinery_control_r6_gate_reproduced`: the R6 fixed gate (empty where c3 empties and N1 >= 0.2, v4g base) reproduced through
  this driver's delta path: i1 +0.7455 [+0.27, +1.24], false fills 91 -> 64; i2 +0.9831 [+0.50, +1.48], 93 -> 60; 3 non-empty
  exact rows lost, 0 intent rows (R6 note: +0.75 / +0.98); a mismatch stops the run.
- `single_action_everywhere`, `twin_nulls` (aa - lock: i1 +0.53, i2 -0.45, r6 +0.72), `oracle` (per-row best action, a ceiling
  inflated by decoding noise; `noise_only_twin_best_of_lock_and_aa` shows what selecting on noise alone buys),
  `crossfit.variants` (learner x feature group x action subset), `margin_sensitivity_headline_default_subset`,
  `leave_one_pool_out` (fit on pool P and one utterance half, score pool Q's other half with Q's own lock: row- and
  flight-disjoint), per-scenario / equal-stratum / empty-vs-non-empty tables and the exchange arithmetic for the headline.

## Deviations and limitations (read before citing a number)

- **Margin default was changed once before the real run.** The first draft default (0.67 pp floor / 60 min-leaf = 0.0112 pp per
  row, "a 60-row leaf must clear the whole floor alone") routed zero rows in a `--no-write` run on these pools; the default
  became 0.1 x the false-fill exchange rate (0.0033 pp per row) and the old value stays in the margin-sensitivity table. Two
  `--no-write` dry-run reads on Fold B preceded the real run.
- **Same rows in every pool.** All pools are the Fold B roster; the cross-fit is row-disjoint (utterance-hash halves) but not
  roster-disjoint, and Fold B exposure is cumulative. These are development numbers; a routed table needs Fold A / DEV
  confirmation (TF-2/TF-3) before any claim.
- **Cross-flight composite.** The routed column is the i1 lock plus same-flight deltas of i2 / r6 actions, not a flown column; a
  flown policy arm (TF-1) additionally carries the lock-vs-action decoding noise of one new sample. The lock itself differs
  between flights by the twin null (+0.53 / -0.45 / +0.72 pp), so "vs lock" and "vs aa" can differ by that much.
- **Perception-level actions are circular under note-derived features.** `r6-p1..p3` change the Perception template; the
  signature features that come from the lock Perception note (rank-1 rate, candidates, distinction tokens, unresolved and
  evidence-ref counts) do not exist before that choice. Results for subsets containing `r6-*` actions
  (`extended_all_loadable`) are descriptive only. The p1 tag group needs the p1 template to have run.
- **Multiplicity.** The report carries 6 learner x feature-group variants x 6 action subsets; only `tree|pre` was declared
  headline. A CI-LB > 0 elsewhere (for example the logistic variants of `extended_all_loadable`, which route 150+ rows to
  `r6-p2`) is one of about 36 looks and is not a finding.
- **Empty-gold rows have pooled F1 = 0 by construction** (no true positive is possible), so the empty-gold line of the
  empty-vs-non-empty table is identically 0.00 pp; the empty-gold effect is the false-fill count (and the exchange arithmetic).
- **Flight-to-flight signature.** Signatures are computed per pool from that pool's own phases; the exemplar supply is identical
  (mean |N1 difference| 0.0000) and the rank-1 intent agrees on 95.2 % (i2) / 96.1 % (r6) of rows against i1; the composite uses
  the i1 signature.
- **Column identities.** Every arm's first-visit and score file sha256 is in `receipt.json` (and in `--dry` output). The i1 lock
  first-visit hash `63d26c02...` matches the R1 results note; the other hashes are recorded, not cross-checked against notes. No
  in-process vs sealed mismatch occurred on any of the 19 arms (the run would have stopped).
