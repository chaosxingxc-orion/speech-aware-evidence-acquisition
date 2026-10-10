# VER-1 offline composer v1 (owner decision 257, 2026-10-10)

Driver `scripts/analysis/slurp_ver1_offline.py`, tests `tests/unit/test_slurp_ver1_offline.py`. Offline, model-free, zero
GPU, zero server, zero network, zero paid API. Status: DESCRIPTIVE tooling plus two development reads; nothing here admits a
mechanism or authorises a flight. No utterance text, transcript, gold value, filler, note body or model output is printed or
persisted anywhere (ids are not persisted either).

## 1. What it computes

The VER-1 delivery rule over sealed pools: per row N Solver samples (the ROLL form), a support filter over the samples, the
c3 presence verdict x N1 gate, and the registered v4g normaliser. Each rule is a delivered column scored in-process with the
official path (the SLURP port, identity-checked against the official `evaluate.py` by the sealed scorers; the v3 / v4 / v4g
text steps are the registered `DELIVERY_NORMALISERS`, never re-implemented).

| input | source | notes |
| --- | --- | --- |
| sample pool | any run whose `<run>.outputs.jsonl` rows carry `solver_group.samples` | generic over `--run-id/--attempt/--split/--rows`; named presets `roll1`, `roll2`, `roll3`; sample 0 may be greedy |
| verdict column | NX R1 iteration `i1` (`r1-c3`) or `i2` (`r1-i2-c3`) on the same TRAIN Fold B rows (`--verdict`), or ANY sealed same-flight Solver template column on the pool's rows (`--verdict-run RUN_ID:ATTEMPT:ARM[:KEY]`, e.g. the VER-1c Fold A `r1-c3` column) | verdict = the arm answered no entity after v4g; lock and A/A (`aa`) columns come with it; the run needs `supply-variants/arm-{lock,aa,ARM}-first-visit-outputs.jsonl` and the matching `slurp-slu-official-train` scores; N1 comes from that run's `phases.json` (`--signature` names the source, default the first verdict) |
| pre-Solver signature | N1 = entity-free share of the 20 supplied exemplars, from the verdict run's `phases.json` (`--signature`) | reused from the R6 driver (`row_signals`), median-filled like R6 |
| normalisers | `saea-deliver-normalise-v3` (pool base), `-v4` (control only), `-v4g` | |

Rules, all at the pool's base normaliser and under v4g: support filter at `s` over the first `n` samples
(`n<n>-s<s>-<base>-<intent>`; base sample `first` = sample 0 or `medoid` = the aggregation read's R1; intent from the
base, from sample 0 or by `plurality`; `s = 1` is the unfiltered base); the registered `saea-commit-plurality-support-v1`
(`n<n>-registered-s<s>`); the gate `+gate[<source>,<theta>]` (theta 0.1 .. 0.9) over the bare sample 0 (`S0`) and over every
filtered column. Selected thresholds (`s`, `theta`) are cross-fitted by utterance-hash halves (`crossfit`). Comparators: `S0`
(sample 0), `MEAN<n>` (mean of the first n single-sample arms), `DELIVERED` (the pool run's sealed delivered commit, re-scored
in-process and proved against the sealed unprojected scores), `lock:<source>` and `aa:<source>`. Per variant: pooled SLU-F1 and
intent, delta with the whole-cluster paired bootstrap (10,000 draws, seed 20260915; `--cluster utterance|row`), false fills
removed, non-empty exact rows lost / gained, intent rows moved, the exchange arithmetic (0.033 / 0.070 / 0.056 pp per row)
beside the realised delta, strata (scenario natural and equal; empty-gold vs non-empty-gold contribution to the pooled
delta), and per-row oracle ceilings (best of the samples, best of the rules, perfect gate; they see the gold and are upper
bounds, never rules).

## 2. How to run

```bash
python -B scripts/analysis/slurp_ver1_offline.py --mode controls --label CONTROLS-V2
python -B scripts/analysis/slurp_ver1_offline.py --mode read --pool roll2 --n 3,5 --label ROLL2-FOLD-A-V2
# the Fold B pool VER-1a, no code change: by run id (3 samples, sample 0 greedy), both R1 verdict columns
python -B scripts/analysis/slurp_ver1_offline.py --mode read --run-id <VER-1a RUN> --attempt <ATTEMPT> --split train \
    --rows 1080 --verdict i1,i2 --n 3 --label VER1A-FOLD-B-V1 [--sealed-scorer slurp-slu-official-train]
# a verdict column other than the R1 iterations (added for the VER-1b Fold A confirmation; `--verdict i1,i2` is unchanged and the two
# options combine; the key defaults to the arm id, a 4th field overrides it):
python -B scripts/analysis/slurp_ver1_offline.py --mode read --run-id <VER-1b RUN> --attempt <ATTEMPT> --split train --rows 1080 \n    --n 3 --s 2 --thetas 0.2 --verdict-run <VER-1c RUN>:<ATTEMPT>:r1-c3 --label VER1B-FOLD-A-V1 --sealed-scorer slurp-slu-official-train
```

Outputs are write-once under `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-VER1-OFFLINE-<LABEL>/` (`report.json`, `report.md`);
`--no-write` prints the tables only. A read takes 2-7 minutes. `--pool-root` points the sample-pool loader at another data root
(used to prove the Fold B path on a surrogate, section 5).

## 3. Machinery controls (all reproduce; `analysis/SAEA-SLURP-VER1-OFFLINE-CONTROLS-V2`)

Tolerance: every point and CI endpoint within 0.0051 pp of the documented two-decimal figure.

| control | reproduced | documented |
| --- | --- | --- |
| ROLL-1 R3 support 3-of-5 vs R0-mean-single, row clusters (aggregation read) | +1.40 [+0.55, +2.29] (pooled 59.28) | +1.40 [+0.55, +2.29] |
| same, utterance clusters (v4 note) | +1.40 [+0.52, +2.28] | +1.40 [+0.52, +2.28] |
| ROLL-1 R1 medoid, row clusters | +0.03 [-0.63, +0.71] | +0.03 [-0.63, +0.71] |
| ROLL-3 support 2-of-3 over single (v3) | +1.46 [+0.83, +2.08] | +1.46 [+0.83, +2.08] |
| ROLL-3 support 2-of-3 + v4 vs single + v4 | +0.84 [+0.19, +1.49] | +0.84 [+0.19, +1.49] |
| ROLL-3 support 3-of-5 over single (v3) | +2.06 [+1.27, +2.88] | +2.06 [+1.27, +2.88] |
| ROLL-3 support 3-of-5 + v4 vs single + v4 | +1.11 [+0.33, +1.91] | +1.11 [+0.33, +1.91] |
| R6 gate c3verdict x N1 >= 0.2, R1 i1, lock v4g | +0.7455 [+0.27, +1.24]; false fills 91 -> 64; non-empty exact lost 3; intent rows 0; fired 326 | +0.75; 91 -> 64; 3 |
| R6 gate, R1 i2 | +0.9831 [+0.50, +1.48]; false fills 93 -> 60; lost 3; intent rows 0; fired 327 | +0.98; 93 -> 60; 3 |

The ROLL-3 "2-of-3" figure is the v4 note's definition: samples 0..2, the R1 medoid as base, entities dropped when supported by
fewer than 2 of the 3 (same type, normalised-filler character F1 >= 0.8), "+v4" = the registered v4 normaliser applied to the
filtered answer and to every single-sample arm, delta = filter+v4 against the mean of the three single+v4 arms, utterance
clusters. The registered `saea-deliver-normalise-v4` reproduces the search driver's rule list exactly. The R6 gate rows are also
asserted identical to `R6.gate_metrics`. The registered commit policy at `s = 3` of 5 equals the sealed delivered text on every
row of ROLL-2 and ROLL-3 (the `DELIVERED` comparator coincides with `n5-registered-s3`).

## 4. First real numbers (development rows; `analysis/SAEA-SLURP-VER1-OFFLINE-ROLL2-FOLD-A-V2`, `...-ROLL3-DEV-V2`)

The V1 directories of the same labels carry a defective empty-gold line (a pooled F1 over empty-gold rows is identically 0) and
are superseded by V2; every other number is identical.

Pooled SLU-F1 pp delta of the VER-1 form (`first-first`: sample 0's entities filtered by support, sample 0's labels) against
`S0` (sample 0), CI95 whole-utterance bootstrap. The pools are five temperature-0.7 draws, so sample 0 is NOT greedy here.

| pool | n | s | base normaliser (v3) | + v4g |
| --- | --- | --- | --- | --- |
| ROLL-2 Fold A (1,080) | 3 | 2 | +1.35 [+0.37, +2.44] | +0.91 [-0.07, +2.03] |
| ROLL-2 | 3 | 3 | +1.31 [-0.24, +2.90] | +0.33 [-1.31, +1.99] |
| ROLL-2 | 5 | 2 | +1.27 [+0.67, +1.94] | +1.03 [+0.47, +1.70] |
| ROLL-2 | 5 | 3 | +1.52 [+0.45, +2.66] | +0.87 [-0.24, +2.04] |
| ROLL-3 DEV-2000-ADDED (1,000) | 3 | 2 | +0.78 [-0.17, +1.72] | +0.18 [-0.71, +1.06] |
| ROLL-3 | 3 | 3 | -0.50 [-1.85, +0.84] | -1.62 [-2.97, -0.32] |
| ROLL-3 | 5 | 2 | +1.34 [+0.60, +2.11] | +0.76 [+0.08, +1.45] |
| ROLL-3 | 5 | 3 | +1.00 [+0.04, +1.97] | +0.22 [-0.70, +1.14] |

Reading (descriptive):

* Against the pool's own sample 0, v4g already takes most of the filter's gain: sample 0 itself moves 62.38 -> 64.40 (Fold A)
  and 63.53 -> 64.63 (DEV) under v4g, and the filter's increment over v4g is resolved only at n = 5, s = 2 on both pools
  (Fold A +1.03 [+0.47, +1.70]; DEV +0.76 [+0.08, +1.45]).
* Against the mean of the single arms the same 2-of-3 filter is larger (v4g: Fold A +1.18 [+0.28, +2.10]; DEV +0.39
  [-0.46, +1.24]); the comparator matters at the 0.3-0.8 pp level in these pools (sample 0 is above its own pool mean).
* The gain is false-fill suppression on empty-gold rows (n = 3, s = 2, v4g, contribution to the pooled delta: Fold A
  empty-gold +1.74 [+1.10, +2.58] on 44 changed rows, non-empty-gold -0.90 [-1.64, -0.20] on 65 changed rows; DEV +1.11
  [+0.76, +1.51] vs -0.97 [-1.78, -0.19]). With three samples the 2-of-3 filter also drops true entities (non-empty exact
  rows lost 16 / gained 5 on Fold A); with five samples the non-empty side is flat (Fold A +0.27 [-0.11, +0.66]).
* The sealed delivered commit (plurality support 3-of-5, re-scored in-process) is 63.99 / 65.68 (Fold A, v3 / v4g) and 65.10 /
  65.51 (DEV); no sample-0 filter rule is resolved above it (all `vs DELIVERED` intervals contain 0).
* Cross-fitted choice of s by utterance-hash halves (vs S0): Fold A n = 3 +1.19 [-0.06, +2.50] (v3) / +0.91 [-0.07, +2.03] (v4g);
  Fold A n = 5 +1.12 [+0.29, +1.98] / +0.56 [-0.28, +1.41]; DEV n = 3 +0.78 [-0.17, +1.72] / +0.23 [+0.00, +0.60] (v4g picks
  "no filter" on both halves); DEV n = 5 +0.88 [-0.03, +1.79] / +0.76 [+0.08, +1.45].
* Intent: the `first-first` form keeps sample 0's labels, so it moves 0 intent rows against S0 except where sample 0 is
  malformed (the filter falls back to the lowest valid sample; S0 renders the empty answer): 0 rows on Fold A, 2 on DEV at n = 3
  (75.5 -> 75.7), 4 at n = 5 (75.5 -> 75.9). The `plurality` intent form moves 6-7 rows on Fold A and 6-10 on DEV (see `report.json`).
* Ceilings (upper bounds, gold-seeing): best of 3 samples +4.9 / +5.3 pp (Fold A v3 / v4g), best of 5 +8.6 / +8.8; a perfect
  empty gate on sample 0 +6.8 / +5.4. The best-of-rules oracle (+2.5 / +2.2 at n = 5) is far under the sample oracle.

## 5. Limitations

* No sample pool exists on Fold B yet. The verdict x N1 path was proven on real data with a surrogate (sample 0..2 = the R1
  i1 `lock`, `aa` and `r1-c1` first-visit columns parsed into the ROLL custody form, scratch directory outside the data root,
  nothing written): S0 + gate[i1, 0.2] under v4g reproduced the R6 gate (+0.75 [+0.27, +1.24]) through the full `read_pool`
  path (`--verdict i1,i2`, N1 from the i1 `phases.json`, lock and A/A comparators, 6 min 36 s). The surrogate numbers are not
  results.
* The ROLL pools have no greedy sample and no c3 column, so the gate and the additivity of filter and gate (the VER-1
  prediction's risk) are not measured here; Fold A has no c3 column by design.
* The custody proof for single samples (S3-3 copies and sealed per-sample fields) needs a score root; VER-1a will not have
  one unless S3-3 renders it. Without it the single arms are still rendered through the canonical path, and the delivered
  commit is proved against the run's `scores.json` when `--sealed-scorer` is given.
* `first` base means sample 0, or the lowest valid sample when sample 0 is malformed (the S0 comparator renders a malformed
  sample as the empty answer, as the S3-3 copies do).
* Thresholds are selected from a two-point `s` grid and a nine-point `theta` grid and cross-fitted by two utterance-hash
  halves; with n <= 1,080 a cross-fitted CI is wide. Strata cells (single scenarios of 26-60 rows) are diagnostics.
* The exposure ledger is not touched: the reads open sealed ROLL-2 (Fold A) and ROLL-3 (DEV) pools that earlier registered
  reads already opened; the coordinator decides whether the V2 outputs need their own read rows. The test-sample runs and
  the flight worktree were never opened.
