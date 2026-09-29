# Cell W4-SV (same-flight supply variant, release swap to slot-contracts-w4-v1) column read: b-w4 vs a-agree official SLU-F1 -0.15 pp CI95 [-1.40, +1.11] against a twin null of +0.43 pp [-0.19, +1.04] on TRAIN Fold A (DESCRIPTIVE)

Read 2026-09-29 by Claude Opus 5.5 in the worktree `fable/w4svread` (model-free; `core.flight.cli` and
`lease_cli` were not invoked; no GPU contact). READ row `SAEA-SLURP-STAGE3-W4SV-FOLD-A-COLUMN-READ-V1` root
countersigned 2026-09-29T09:46:51Z (master `e39c2a9c4`) after the seal (arm-inspect PASS and step-done
09:40:11Z) and before any column score existed. Recipe
`docs/readiness/2026-09-28-slurp-stage3-w4-sv-fold-a-v1/analysis-recipe-v1.json` (sha256
`f386a4d34ff06e98955d10991107ad9f19719a0164629cb1440b82abf3b6cc67`), recipe id
`slurp-stage3-w4sv-fold-a-column-read-v1`. Paired row bootstrap, cluster key `sample_id`, 10,000 draws, seed
20260928, TRAIN gold through `slurp-slu-official-train`. Owner decisions 170, 172, 179 and 183.

The driver was `scripts/flights/w4sv/w4sv_read.sh` (sha256
`ef0a86a4f2ed82b90af09d50a1fab645a62f2df7fc5c806c14ad75489c91b871`, run once, rc 0, with
`SAEA_REPO_ROOT` pointed at this worktree; no `--rescore`). It called
`scripts/analysis/stage3_rollout_score.py` (sha256
`2eb4b3bc5f1bfd8ea2152701e957ac7c2db4fcc16fa93202b1232637a39151a9`) and
`scripts/analysis/stage3_paired_read.py` (sha256
`a710d956d71315d2497ed3f7cfbc3c07cdea8627ba83e5bad21aa80052760207`, the same bytes as the W-SV-1 read after
its repair). No read-path repair was needed this time.

The two paired reads sit under `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-W4SV-FOLD-A-COLUMN-READ-V1/`:

- `t-vs-a/` (the null): README sha256 `a433bef21e93deaf5ddbe6f0b3e28e298df60d9b12df3f89615d43e3eacb0ba3`,
  `verdict.json` `0189443cc2de8597e53548daac4bdd4edbb823216a798c021bb0e194619b7e86`, `score-contrasts.json`
  `8f64520bc482b3f2eed3b06ca1a8571d648e539e8b19776f808cb00a6fd62e68`, `per-scenario-tables.json`
  `226ece200a310c83ed4599e3b6c730f3c56c8bb34d2b82da146350e4b28c8672`.
- `b-vs-a/` (gating): README sha256 `023a1b7d802358e996453a8742f553191fc38ee9fbc2634ae7b15481d12866c9`,
  `verdict.json` `3ee7842779384393b3d8875e86de61eceacb695470a644dccf204d7afc6b9fe4`, `score-contrasts.json`
  `e75521feeb20fee76dfcabf50b9a4bfd18ee306c939631ca8f2f3c1063311817`, `per-scenario-tables.json`
  `a6da9052406ec2a3bfcd89147982bad3513294578042aef7a9946cb242280102`.

No utterance text, gold label, slot filler, knowledge content or model output was printed or persisted. Only
aggregate counts, scenario names, ids and hashes appear below.

**DESCRIPTIVE.** This note gives the numbers and says which side of the pre-declared rule they fall on. The
verdict word belongs to the coordinator (decision 139). These are development numbers on a TRAIN
construction fold (decisions 28 and 86). The claim ceiling is "nominated" (Q6), and a nomination claims
nothing at system level.

## 1. What flew

The cell was driver step 1 of `scripts/flights/w4sv/batch_chain_w4sv.sh`, at flight commit `4f203ea9`, with
the study tree clean at the seal (`study_repo_dirt` empty). The 4-row smoke passed at 06:37:03Z. The arm
started at 06:37:14Z and arm-inspect PASSED at 09:40:11Z (attempt FINALIZED). The run manifest is COMPLETED
and the delivered rows were scored once (`score-batch/batch-summary.json`: 1 job, succeeded).

| run | rows | contacts | speech s | prompt / completion tokens | GPU-h | state |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| `SAEA-SLURP-STAGE3-W4SV-FOLD-A-V1` | 1,080 | 6,531 | 18,656.917 | 60,930,411 / 309,091 | 2.7883 | COMPLETED, FINALIZED, scored once |
| context: `SAEA-SLURP-STAGE3-WSV1-FOLD-A-V1` (W-SV-1) | 1,080 | 6,539 | 18,682.420 | 60,002,873 / 312,084 | 2.8205 | COMPLETED |
| context: `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1` (wave A/A) | 1,080 | 4,393 | 12,557.168 | -- | 1.7417 | COMPLETED |

The GPU-h figure is the paired read's efficiency stage (`b-vs-a/efficiency.json`, 2.5818 per 1,000 rows).
The reserved plan was 14,040 calls and 12.0 GPU-h.

Run sha256 values:

- run manifest `d344585b0f6f21d0b92463155df822cb2fd3dcb20ab1fbf5b5ad04ab156322eb`
- outputs `1e73a74f3ae73a8c39a082ac1e9b4ccb7b1d3bbd458f82f06100d5846f45cacd`
- scores `d1e2967eac429cceedfbe9e7fa7b8ccb9a9cfff90d53bd24f59700c611719f54`
- generation manifest `e325324604e17e10b96041d8af308817eda3fa34175b309fb732c3988080cd40`
- phases `48164eb798cc6a876eaedf66cc4aec9cd789999f3c85dcc74807ff0a003f6e20`
- flight receipts `2023f39418fabf217541d9a269acf1b6a1c951eac67ad2b796acf34926a1bbcc`
- trace manifest `a12a2f9c45e9b50744fa0838abd918c654785b53e3bb385c86c3bb9275290680`
- raw trace `5e0d1b3d224f69afaf5a8c7025435640408cef11eac8576304377e7e2753d7cf`

Tool calls were 0. Every row had a first Solver visit; 20 rows had a later Solver visit (a revision).

The three first-visit Solver arms, in the declared order:

| column | deliver | what differs | max supplied items |
| --- | --- | --- | ---: |
| `b-w4` | no | slot-contract store swapped to the alternate release `slot-contracts-w4-v1` (same 54 value ids as `slot-contracts-v2`, 19 cards with new content) | 56 |
| `t-twin` | no | none (replicate of `a-agree`) | 56 |
| `a-agree` | yes | none (the AGREE Solver supply, `slot-contracts-v2`, modulo program fields) | 56 |

## 2. The delivered arm's own numbers, with context

Official pooled numbers under `slurp-slu-official-train`. The context rows are separate flights: their
differences are cross-flight point differences with no paired interval computed here.

| arm | intent % | official SLU-F1 % | span-F1 % |
| --- | ---: | ---: | ---: |
| W4-SV delivered (full system, sealed) | 86.02 | 64.25 | 54.04 |
| W4-SV `a-agree` first-visit column | 85.83 | 64.13 | 53.84 |
| AGREE arm `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` (context) | 85.83 | 65.16 | -- |
| wave A/A `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1` (context) | 85.65 | 64.16 | 53.54 |

Against the AGREE arm the delivered arm reads +0.19 pp intent and -0.91 pp SLU-F1; against the wave A/A it
reads +0.37 / +0.09. The recorded cross-flight instrument offset (wave A/A vs the AGREE bytes it re-flies)
is -0.19 pp intent and -1.00 pp SLU-F1, so the delivered arm's distance from AGREE is within it.

## 3. The contrasts (same flight, same rows, column against column)

Row-level paired bootstrap, gating (pooled SLU-F1 primary, intent the guard). The utterance-level read
(cluster key `utterance_id`) is reported beside them and never gates (Q4); on this roster every row is a
distinct utterance and the utterance-level intervals equal the row-level ones.

### 3a. The twin null: `t-twin` minus `a-agree`

| metric | a-agree | t-twin | delta pp | CI95 pp | half-width pp | saves / harms |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| **official pooled SLU-F1** | 64.13 | 64.55 | **+0.43** | **[-0.19, +1.04]** | **0.616** | -- |
| official pooled span-F1 | 53.84 | 54.54 | +0.69 | [-0.08, +1.50] | 0.786 | -- |
| **intent (scenario_action_exact)** | 85.83 | 85.93 | **+0.09** | **[-0.19, +0.46]** | **0.324** | 2 / 1 |
| per-row SLU-F1 | 42.99 | 43.22 | +0.23 | [-0.31, +0.78] | 0.545 | 19 / 10 |
| per-row slot exact F1 | 35.10 | 35.66 | +0.56 | [-0.04, +1.21] | 0.625 | 15 / 7 |

Exact values: SLU-F1 delta +0.42883, CI95 [-0.18696, +1.04428], half-width 0.61562; intent delta +0.09259,
CI95 [-0.18519, +0.46296], half-width 0.32407.

The twin's requests equal the delivering arm's requests: first-visit prompt token totals are 11,037,528 each.
**Unlike W-SV-1, the intent null is not exactly zero here**: the twin disagreed with `a-agree` on the
scenario_action outcome of 3 rows (2 saves, 1 harm). This is the decode-level non-reproducibility of the
resident np4 server (greedy decoding is not bitwise reproducible across slots).

Neither twin CI95 excludes zero under the gating natural-mixture weighting, so the registered
**INSTRUMENT FAULT clause is not met**. Beside it, not gating: under equal-scenario weighting the twin SLU-F1
reads +0.76 pp CI95 [+0.0014, +1.68], a lower bound that clears zero by 0.0014 pp.

**The read's bar (|twin offset| + twin CI95 half-width, never below the provisional floor 0.3163 pp):**

- SLU-F1: 0.4288 + 0.6156 = **1.0445 pp**
- intent: 0.0926 + 0.3241 = **0.4167 pp**

### 3b. The contrast: `b-w4` minus `a-agree`

| metric | a-agree | b-w4 | delta pp | CI95 pp | half-width pp | saves / harms | McNemar p |
| --- | ---: | ---: | ---: | --- | ---: | --- | ---: |
| **official pooled SLU-F1, primary** | 64.13 | 63.97 | **-0.15** | **[-1.40, +1.11]** | 1.255 | -- | -- |
| official pooled span-F1 | 53.84 | 53.75 | -0.09 | [-1.67, +1.51] | 1.593 | -- | -- |
| **intent (scenario_action_exact), guard** | 85.83 | 86.02 | **+0.19** | **[-0.46, +0.83]** | 0.648 | 7 / 5 | 0.774 |
| scenario | 89.72 | 89.72 | 0.00 | [-0.56, +0.56] | 0.556 | 5 / 5 | 1.000 |
| action | 86.48 | 86.85 | +0.37 | [-0.19, +0.93] | 0.556 | 7 / 3 | 0.344 |
| per-row SLU-F1 | 42.99 | 42.38 | -0.60 | [-1.72, +0.49] | 1.103 | 53 / 54 | 1.000 |
| per-row slot exact F1 | 35.10 | 34.89 | -0.21 | [-1.42, +1.00] | 1.211 | 41 / 44 | 0.828 |

Exact values: SLU-F1 delta -0.15190, CI95 [-1.39971, +1.10992]; intent delta +0.18519, CI95 [-0.46296,
+0.83333].

By channel (descriptive, per-row SLU-F1): far-field -2.05 (29 saves / 39 harms, n = 557); headset +0.94
(24 / 15, n = 523). Intent: far-field +0.18 (4 / 3), headset +0.19 (3 / 2).

Weightings:

| weighting | contrast | intent delta pp | intent CI95 pp | SLU-F1 delta pp | SLU-F1 CI95 pp |
| --- | --- | ---: | --- | ---: | --- |
| natural mixture (gating) | B - A | +0.19 | [-0.46, +0.83] | -0.15 | [-1.40, +1.11] |
| equal scenario | B - A | +0.19 | [-0.46, +0.83] | -0.13 | [-1.98, +1.60] |
| natural mixture | T - A | +0.09 | [-0.19, +0.46] | +0.43 | [-0.19, +1.04] |
| equal scenario | T - A | +0.09 | [-0.19, +0.46] | +0.76 | [+0.00, +1.68] |

## 4. The AT1 self-check and the column scoring

Step 1 (`stage3_rollout_score.py --mode supply-variants --stage all`) rendered the three first-visit columns
through the delivered row's normaliser and projection and scored each ONCE through the official evaluator.
The score summary records 3 scorer contacts and 0 model, tokenizer, encoder, server, ASR or network
contacts.

**AT1 passed on 1,060 of 1,060 checkable rows** (`at1_column_reproduction_checked_rows` = 1,060 = 1,080 - 20
revised rows): on every row with no revision visit, the `a-agree` column text equals the sealed delivered
text byte for byte. One row per column had a malformed first visit (1 / 1 / 1), scored as the canonical empty
answer. The column pooled numbers therefore differ from the delivered ones only through the 20 revised rows
(intent 85.83 vs 86.02, SLU-F1 64.13 vs 64.25).

Sha256 values under `<run dir>/supply-variants/`:

- `arm-a-agree-slurp-slu-official-train-scores.json` `311017f0691b54521318ccdcbf16fee4ca08915e2117e4ffe35ce037fc48dbb7`
- `arm-b-w4-slurp-slu-official-train-scores.json` `117bbfe4a6d02a31842a43174f9548df75fc21af17104e260ee600b53244c3fe`
- `arm-t-twin-slurp-slu-official-train-scores.json` `60f6a948dfe2c7828017c9daf4197204aa4c6ef9c7d9765f6033675119bc4aa6`
- render manifest `8d5330c8600aba08f580d56137b667a7175f0f0ffbf8cf2160ff48d2b776cf5e`
- score summary `7fd8b581738dd2ab39c78301d01d673f16a20e4a3eaf2fb9af109f09d345b32e`
- first-visit rows `243cdff837e1489e082b6243556dc2bf041522de98dd5b371f181ede7523a47b`
- arm citation rows (3,240 rows) `4d810d427d06e7b7683adc7997b6a111f15255fdea1442dd168fa0e6d213d632`

## 5. The pre-declared rule, and where the numbers fall

The registered rule (`analysis-recipe-v1.json` `decision_rule`) has four branches:

- **INSTRUMENT FAULT** (no verdict) iff the T - A CI95 excludes zero on either metric.
- **NOMINATED** (the ceiling) iff the B - A pooled SLU-F1 delta exceeds the bar AND its CI95 lower bound is
  above zero AND the B - A intent CI95 upper bound is not below zero.
- **HARMFUL** iff the B - A CI95 upper bound is below zero on either metric.
- Otherwise **NOT NOMINATED (width)**.

| clause | measured | bar | side |
| --- | ---: | ---: | --- |
| instrument fault: T - A SLU-F1 CI95 excludes 0 | [-0.1870, +1.0443] | 0 | not met |
| instrument fault: T - A intent CI95 excludes 0 | [-0.1852, +0.4630] | 0 | not met |
| B - A SLU-F1 point delta > bar | -0.1519 | 1.0445 | not met |
| B - A SLU-F1 CI95 lower bound > 0 | -1.3997 | 0 | not met |
| B - A intent CI95 upper bound >= 0 (guard) | +0.8333 | 0 | met |
| harmful: B - A SLU-F1 CI95 upper bound < 0 | +1.1099 | 0 | not met |
| harmful: B - A intent CI95 upper bound < 0 | +0.8333 | 0 | not met |

By the rule, the numbers fall in the residual branch **NOT NOMINATED (width)**. The verdict word is the
coordinator's.

**Declared expectation.** `registered-facts-v1.json` `stage3_measurement` declares
`expected_effect_pp` 0.79 with `claims_benefit` true (design `same-flight-supply-variant`, admission
`benefit`, claim `nominated`). The 0.79 was transferred from cell W4's cross-flight full-system read
(+0.79 pp CI95 [-0.56, +2.12] against the wave A/A), with the registered ESTIMAND CAVEAT that B - A is the
Solver-local first-visit effect of the W4 cards only, since the Reviewer, the Planner and the Solver revisit
see the AGREE v2 cards here. The measured point, -0.15 pp, lies inside its own CI95, inside the twin bar
(+/-1.04 pp) and 0.94 pp below the declared size.

**Re-calibration caveat** (`docs/results/2026-09-29-slurp-same-flight-floor-recalibration.md`, section 3). At
n = 1,080 the measured same-flight SLU-F1 contrast half-width was 1.4866 pp (W-SV-1). This flight measures
1.2548 pp. A 0.79 pp declaration is underpowered at either width: CI95 excludes zero at 0.79 would need about
n = 1,080 x (1.4866 / 0.79)^2 = 3,824 rows (2,725 at this flight's 1.2548), extrapolations. Also, this
flight's twin bar (1.0445 pp) is itself above 0.79, so a point exactly at the declared size could not clear
the nomination clause. **A verdict short of NOMINATED with a CI excluding zero is therefore "not resolvable
at this n", not evidence that the W4 cards have no Solver-local effect.** The declared size stays neither
confirmed nor refuted.

## 6. Per-scenario tables (natural mixture; the equal-scenario rows are in section 3b)

Each scenario has n = 60. CI95 by the paired cluster bootstrap. The strata are descriptive and none is
powered.

| scenario | intent A | B - A intent | saves / harms | SLU A | B - A SLU | B - A SLU CI95 | T - A SLU |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: |
| alarm | 95.00 | -1.67 | 0 / 1 | 72.86 | +2.34 | [-2.15, +7.57] | -0.74 |
| audio | 80.00 | +1.67 | 1 / 0 | 64.15 | -7.13 | [-29.52, +12.57] | +4.67 |
| calendar | 93.33 | -1.67 | 0 / 1 | 68.90 | -5.06 | [-9.02, -1.53] | 0.00 |
| cooking | 83.33 | 0.00 | 0 / 0 | 62.71 | -0.71 | [-5.38, +3.09] | +0.87 |
| datetime | 91.67 | 0.00 | 0 / 0 | 74.66 | +2.12 | [-0.88, +6.21] | +0.37 |
| email | 90.00 | 0.00 | 0 / 0 | 61.90 | -1.87 | [-8.67, +4.49] | +0.77 |
| general | 48.33 | +1.67 | 1 / 0 | 23.81 | +1.83 | [-10.92, +14.23] | 0.00 |
| iot | 81.67 | +1.67 | 1 / 0 | 69.33 | +0.56 | [-4.37, +5.84] | +1.18 |
| lists | 90.00 | 0.00 | 0 / 0 | 57.04 | -4.54 | [-12.22, +2.00] | +0.72 |
| music | 80.00 | -1.67 | 0 / 1 | 44.90 | +2.63 | [-3.06, +11.11] | +2.63 |
| news | 88.33 | 0.00 | 0 / 0 | 64.69 | +10.49 | [+1.97, +20.45] | +1.84 |
| play | 90.00 | -1.67 | 0 / 1 | 55.72 | -2.25 | [-6.70, +1.63] | -1.47 |
| qa | 90.00 | 0.00 | 0 / 0 | 63.96 | +3.48 | [+0.53, +6.74] | +0.97 |
| recommendation | 98.33 | +1.67 | 1 / 0 | 67.71 | -0.74 | [-7.30, +5.17] | -0.51 |
| social | 81.67 | 0.00 | 0 / 0 | 55.18 | +2.91 | [-0.05, +6.28] | +1.10 |
| takeaway | 83.33 | 0.00 | 1 / 1 | 62.17 | -3.94 | [-9.50, +1.07] | -1.15 |
| transport | 83.33 | +3.33 | 2 / 0 | 65.01 | +0.62 | [-2.70, +4.02] | +1.03 |
| weather | 96.67 | 0.00 | 0 / 0 | 78.82 | -3.01 | [-7.71, +1.11] | +1.43 |

Three strata have a B - A SLU CI95 that excludes zero: news +10.49 and qa +3.48 up, calendar -5.06 down.
With 18 unpowered strata and no multiplicity correction, this is within what chance produces. For scale, the
twin's scenario SLU spread runs from -1.47 (play) to +4.67 (audio). Twin intent deltas are non-zero in 3
scenarios (alarm -1.67, audio +1.67, general +1.67; one row each; see the `t-vs-a` README).

**Entity-class and per-type tables.** The read driver does not emit the SPURIOUS / MISSING / WRONG-TYPE /
BOUNDARY entity-class table, nor the recipe's step-5 mechanism read (per revised type exact TP/FP/FN over the
19 changed cards, B vs A and T vs A). The recipe says every verdict carries the step-5 table. It is
**outstanding**: it needs a model-free helper over the three column outputs and the TRAIN gold (counts only),
and nothing in this read computes it. Flagged for the coordinator.

## 7. Cost: tokens per column contact, and the +2 contacts per row

These come from the sealed trace (`usage` per MODEL_RESPONSE), mapped to the first-visit contacts through
`first-visit-rows.json` (numbers only).

| column | first-visit contacts | prompt tokens per contact | completion tokens per contact | prompt tokens total |
| --- | ---: | ---: | ---: | ---: |
| `a-agree` (delivering) | 1,080 | 10,219.9 | 23.9 | 11,037,528 |
| `t-twin` | 1,080 | 10,219.9 | 23.9 | 11,037,528 |
| `b-w4` | 1,080 | 11,418.9 (+1,199.0 vs A) | 23.6 | 12,332,430 |

The +1,199.0 prompt tokens per Solver contact for `b-w4` matches cell W4's realised +1,207.8 per Solver
contact in its cross-flight read, so the alternate cards did reach arm B's request (the release-swap
renderer fix 3f6688de is in effect; the registration's proof reads ARM-B-VARIES on 120 / 120 rows).

The instrument's price is the K - 1 = 2 non-delivering first-visit Solver contacts per row:

- **2,160 extra contacts, 33.1 % of the flight's 6,531** (6,531 vs the wave A/A's 4,393 on the same roster:
  +2,138; revision counts differ).
- 23,369,958 prompt tokens (B + T first visits), about 21,639 per row, **38.4 % of the flight's 60.93 M**.
- About 6,100 s of re-sent speech (18,656.9 vs 12,557.2 s, cross-flight); the registered projection was
  6,169.057 s.
- About +1.05 GPU-h per 1,080 rows (2.7883 vs 1.7417, cross-flight).

By role across the flight:

| role | contacts | prompt tokens per contact |
| --- | ---: | ---: |
| Perception | 1,080 | 3,598 |
| Solver (all visits and arms) | 3,260 | 10,612 |
| Reviewer | 1,100 | 10,182 |
| Planner | 1,091 | 10,312 |

## 8. What this second same-flight read adds to the instrument

- **The twin SLU null is wider than W-SV-1's**: half-width 0.616 pp vs 0.532, offset +0.43 vs +0.37, bar
  1.04 vs 0.91. Two flights now put the same-flight SLU bar near 1 pp at n = 1,080, about 3.3 x the
  provisional 0.3163 floor.
- **The intent null is not structurally zero.** W-SV-1's twin agreed on intent on all 1,080 rows; this twin
  disagreed on 3 (2 / 1), giving an intent bar of 0.42 pp. The intent guard of this rule (the B - A upper
  bound not below zero) is unaffected, but a rule that uses the twin's intent bar as a margin should not
  assume a zero bar.
- **The contrast SLU half-width is 1.25 pp here** vs 1.49 in W-SV-1, both far above any sub-1 pp
  declaration.

## Verdict (read agent, for the coordinator)

**NOT NOMINATED (width) under the registered rule; not resolvable at this n.** B - A official SLU-F1 -0.15 pp
CI95 [-1.40, +1.11] (bar 1.04), intent +0.19 pp [-0.46, +0.83] (7 / 5). No nomination clause, no harmful
clause and no instrument-fault clause is met (twin T - A SLU +0.43 [-0.19, +1.04], intent +0.09 [-0.19,
+0.46]). The 0.79 pp declaration is underpowered at n = 1,080 (contrast half-width 1.25 here, 1.49 in W-SV-1;
about 2,700-3,800 rows needed), and the twin bar alone (1.04) exceeds it. This read is therefore not evidence
of absence of a Solver-local W4-card effect. The recipe's step-5 per-type TP/FP/FN table is outstanding.
Development number (decisions 28 and 86); claim ceiling nominated (Q6); nothing is admitted or closed for
the composed policy.

## Coordinator verdict (Fable 5.1, 2026-09-29)

- **b-w4 (slot-convention cards as a release swap): NOT NOMINATED (width).** SLU-F1 -0.15 [-1.40, +1.11], intent +0.19 [-0.46, +0.83]; the point sits inside the twin bar (1.04 SLU) and neither bound clears zero. The declared 0.79 pp was below what this design can resolve at n = 1,080 (contrast half-width 1.25 here, 1.49 in W-SV-1), so this is "not resolvable at this n", not evidence of absence.
- **Line status.** Conventions delivered as rule cards (W4, W4-SV) have now read below the floor twice (cross-flight -0.4 region, same-flight -0.15). The line is closed for same-flight reads at n = 1,080; it reopens only as a cross-flight read on DEV-2000-ADDED or larger, and only behind a mechanism that reads above floor on TRAIN first. The SLU main line stays retrieved row-matched slot exemplars (W5, decision 170, held).
- **Instrument note.** Second same-flight measurement: twin intent null +0.09 (3 discordant rows) against 0.00 in W-SV-1; contrast intent half-width 0.65 against 0.51. The per-metric anchors proposed for decision 190 should therefore be the larger of the two measurements: intent 0.65 / SLU 1.49 at n = 1,080.
- Outstanding from the recipe: the per-type TP/FP/FN table over the 19 changed cards (model-free helper), descriptive only. Nothing is admitted or closed for the composed policy by this read (claim ceiling nominated; development number, decisions 28/86).
