# Cell W-SV-1 (same-flight supply variant, Solver train-exemplars k 30) column read: b-exk30 vs a-base official SLU-F1 -0.46 pp CI95 [-1.85, +1.12] against a twin null of +0.37 pp [-0.14, +0.92] on TRAIN Fold A (DESCRIPTIVE)

Read 2026-09-29 by Claude Opus 5.5 in the worktree `fable/wsv1read` (model-free; `core.flight.cli` was not
invoked). READ row `SAEA-SLURP-STAGE3-WSV1-FOLD-A-COLUMN-READ-V1` root countersigned 2026-09-29T06:50:38Z
after the seal (step-done 06:32:43Z) and before any column score existed. Recipe
`docs/readiness/2026-09-28-slurp-stage3-wsv1-fold-a-v1/analysis-recipe-v1.json` (sha256
`36bb7ab20b7e611a9283bf888300562431ffb0980f0ce88e10e5772ac6296ea2`), recipe id
`slurp-stage3-wsv1-fold-a-column-analysis-v1`. Paired row bootstrap, cluster key `sample_id`, 10,000 draws,
seed 20260928, TRAIN gold through `slurp-slu-official-train`. Owner decisions 172, 179 and 183.

Outputs: the columns and their official scores sit under the sealed run's `supply-variants/` directory
(section 4). The two paired reads sit under
`$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-WSV1-FOLD-A-COLUMN-READ-V1/`:

- `twin-null/`: README sha256 `8133b1cb9103c24ba7f2e25d86d8a088d5b354dbd60a5b2e2f83386e6ce377f2`, `verdict.json`
  `fc718c8daa0eb0af0e17648eb108a4007c83ddf0ffa8f94216369665a07a4e21`, `score-contrasts.json`
  `f4d6930cc3b3c9cb8b05a5f61310932986628f6d0624e3150565a5f4836294fd`.
- `knob/`: README sha256 `31dc9112f7d763a3b070a4a86a38521d6b357e1379232efbc490c3b0880e9c1b`, `verdict.json`
  `10c35e6a50550bb32575afd8327294b68ae6113c5a7791dff17376541719afee`, `score-contrasts.json`
  `757f3cabd7d7bd4c7425284e660d0e0cf11d65bbea3a2ddfd140834fa0c60b41`.

The driver was `scripts/analysis/stage3_paired_read.py` (sha256
`a710d956d71315d2497ed3f7cfbc3c07cdea8627ba83e5bad21aa80052760207`, after the repair in section 8).

No utterance text, gold label, slot filler, knowledge content or model output was printed or persisted. Only
aggregate counts and scenario names appear below.

**DESCRIPTIVE.** This note gives the numbers and says which side of the pre-declared rule they fall on. The
nomination word belongs to the coordinator (decision 139). These are development numbers on a TRAIN
construction fold (decisions 28 and 86). The claim ceiling is "nominated" (Q6), and a nomination claims
nothing at system level.

## 1. What flew

The cell was driver step 1 under `SAEA-Queue-WSV1`, at flight commit `1c1e19ce`, with the study tree clean at
the seal. The 4-row smoke passed at 03:28:52Z. The arm started at 03:29:03Z, exited rc 0 at 06:32:36Z, and
arm-inspect PASSED at 06:32:43Z. The run was FINALIZED with its manifest COMPLETED and scored once, and
driver-done came at 06:33:03Z.

| run | rows | contacts | speech s | prompt / completion tokens | GPU-h | state |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| `SAEA-SLURP-STAGE3-WSV1-FOLD-A-V1` | 1,080 | 6,539 | 18,682.420 | 60,002,873 / 312,084 | 2.8205 | COMPLETED, FINALIZED, scored once |
| context: `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1` (wave A/A) | 1,080 | 4,393 | 12,557.168 | -- | 1.7417 | COMPLETED |

Run sha256 values:

- run manifest `523926525b11244435425d8b2fbcf06d076c9e7836c963568a9be469132c5e42`
- outputs `0aeb494b14e07f2752a4cd1217c6b26118d16deee0af8fbe563c20a7b527c4ff`
- scores `3346f909d484aee48651777d0a4673da9ffeaae6614ccac4b220ca3f53baa2aa`
- generation manifest `f64ecb2892f9a6de1dcd723d3105e7fc600229bea386f667639d480a33a249bd`
- phases `400618b4db9823725aba6a7e5f3d523d13be60bce0879298d85afcdf6e2d7346`
- flight receipts `427f83efffef5a11deacdc5f12ae6ce26db29e746f1bed87c6ae00857c119cfb`
- trace manifest `619da8b42e698e15b94da9d00a1c605fb86251a3de03744a7cc87b29f9add40d`

Tool calls were 0. Dispositions were finite_completion on 13 rows and revision_limit on 3. Every row had a
first Solver visit, and 24 rows had a later Solver visit (a revision).

The three first-visit Solver arms, in the declared order:

| column | deliver | knobs | max supplied items |
| --- | --- | --- | ---: |
| `b-exk30` | no | train-exemplars Solver `k` 30, `fuse_coverage` c / m / top_l 30 / 30 / 30 | 68 |
| `t-twin` | no | none (replicate of `a-base`) | 58 |
| `a-base` | yes | none (the AGREE Solver supply modulo program fields) | 58 |

## 2. The delivered arm's own numbers, with context

These are official pooled numbers under `slurp-slu-official-train`. The context rows are separate flights,
so their differences are cross-flight point differences with no paired interval computed here.

| arm | intent % | official SLU-F1 % | span-F1 % |
| --- | ---: | ---: | ---: |
| W-SV-1 delivered (full system, sealed) | 85.74 | 64.33 | 53.59 |
| W-SV-1 `a-base` first-visit column | 85.65 | 64.37 | 53.70 |
| AGREE arm `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` (context) | 85.83 | 65.16 | -- |
| wave A/A `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1` (context) | 85.65 | 64.16 | 53.54 |

- Against the AGREE arm, the delivered arm reads -0.09 pp intent and -0.83 pp SLU-F1.
- Against the wave A/A, it reads +0.09 pp intent and +0.17 pp SLU-F1.
- The cross-flight instrument offset already on record (the wave A/A against the AGREE bytes it re-flies,
  [the W1 read](2026-09-28-slurp-w1-fold-a-read.md)) is -0.19 pp intent and -1.00 pp SLU-F1.
- W-SV-1's delivered path re-flies the same AGREE bytes, modulo program fields. Its distance from AGREE
  (-0.09 / -0.83) therefore falls within that recorded cross-flight offset.

## 3. The contrasts (same flight, same rows, column against column)

The rows are the paired row bootstrap and are gating (the pooled SLU-F1 is primary and intent is the guard).
The utterance-level read (cluster key `utterance_id`) is reported beside them and never gates (Q4). On this
roster every row is a distinct utterance, so the utterance-level intervals equal the row-level ones to the
fourth decimal.

### 3a. The twin null: `t-twin` minus `a-base`

| metric | a-base | t-twin | delta pp | CI95 pp | half-width pp | saves / harms |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| **official pooled SLU-F1** | 64.37 | 64.74 | **+0.37** | **[-0.14, +0.92]** | **0.532** | -- |
| official pooled span-F1 | 53.70 | 54.08 | +0.38 | [-0.27, +1.07] | 0.670 | -- |
| **intent (scenario_action_exact)** | 85.65 | 85.65 | **0.00** | **[0.00, 0.00]** | **0.000** | 0 / 0 |
| per-row SLU-F1 | 43.25 | 43.54 | +0.29 | [-0.06, +0.68] | 0.374 | 13 / 7 |
| per-row slot exact F1 | 35.35 | 35.59 | +0.24 | [-0.17, +0.68] | -- | 10 / 8 |

The twin's requests are the delivering arm's requests: the prompt token totals are equal, 11,008,516 each.
It chose the same intent on all 1,080 rows and a different slot set on 20 rows. That is the decode-level
non-reproducibility of the resident np4 server (greedy decoding is not bitwise reproducible across slots).

**The read's bar (|twin offset| + twin CI95 half-width):**

- SLU-F1: 0.3732 + 0.5324 = **0.9056 pp**
- intent: 0.0000 + 0.0000 = **0.0000 pp**

### 3b. The knob: `b-exk30` minus `a-base`

| metric | a-base | b-exk30 | delta pp | CI95 pp | saves / harms | McNemar p |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| **official pooled SLU-F1, primary** | 64.37 | 63.91 | **-0.46** | **[-1.85, +1.12]** | -- | -- |
| official pooled span-F1 | 53.70 | 52.95 | -0.75 | [-2.48, +1.09] | -- | -- |
| **intent (scenario_action_exact), guard** | 85.65 | 86.02 | **+0.37** | **[-0.09, +0.93]** | 6 / 2 | 0.289 |
| scenario | 89.26 | 89.44 | +0.19 | [-0.19, +0.56] | 3 / 1 | 0.625 |
| action | 86.57 | 86.94 | +0.37 | [-0.09, +0.93] | 6 / 2 | 0.289 |
| per-row SLU-F1 | 43.25 | 43.12 | -0.13 | [-1.05, +0.78] | 45 / 54 | 0.422 |
| per-row slot exact F1 | 35.35 | 34.90 | -0.45 | [-1.51, +0.60] | 33 / 36 | 0.810 |

By channel (descriptive, per-row SLU-F1):

- far-field: +0.94 (33 saves / 27 harms)
- headset: -1.27 (12 / 27)

By channel (descriptive, intent):

- far-field: +0.72 (5 / 1)
- headset: 0.00 (1 / 1)

## 4. The AT1 self-check and the column scoring

`scripts/flights/wsv1/wsv1_read.sh` step 1 (`stage3_rollout_score.py --mode supply-variants --stage all`)
rendered the three first-visit columns through the delivered row's normaliser and projection. It then scored
each one ONCE through `core.scoring_batch.score_complete_derived_copy`. The score summary records 3 scorer
contacts and 0 model, tokenizer, encoder, server or network contacts. The score files are
`arm-<id>-slurp-slu-official-train-scores.json`:

- a-base `df6af579ff5bc7363077996ec4b86c83519877c414b63f645f43a3b86dd9bef4`
- b-exk30 `ba79fa9daece3989c813dfe721173bd51e79f9217488317b6c64e8bf95ab4165`
- t-twin `feb8c5693a0b3817fb1cf836bf649a148fd2961c841214949550d5835cd50364`

The other sha256 values:

- render manifest `828312849311b3b032d36e176bc32b369d12e7ea32e09f53b24889cd4d32ad15`
- score summary `3c953610fd6c84d2b686fa28dc627b2830ea28546a1bb6b40fa9d49da6380f36`
- first-visit rows `88a56ff5d87de06e4c9ca2d524a1a3850f268b1d2fe65631ad1204d995c945b1`

**AT1 passed on 1,056 of 1,056 checkable rows.** On every row with no revision visit (1,080 - 24), the
`a-base` column text equals the sealed delivered text byte for byte. The render refuses on the first
mismatch, and `at1_column_reproduction_checked_rows` = 1,056. The 24 revised rows are not AT1-checkable by
design, because their delivered answer comes from a later visit. One row per column had a malformed first
visit, scored as the canonical empty answer. As a consequence, the column pooled numbers differ from the
delivered ones only on the revised rows: intent 85.65 vs 85.74, SLU-F1 64.37 vs 64.33.

## 5. The pre-declared rule, and where the numbers fall

The rule (package preregistration, recipe steps) has three branches:

- **NOMINATED** iff the SLU-F1 CI95 lower bound is above zero AND the SLU-F1 point delta exceeds the twin bar
  AND the intent CI95 lower bound is not below minus the twin's intent bar.
- **SOLVER-LOCAL HARM** iff a metric's CI95 upper bound is below zero and its point magnitude exceeds that
  metric's twin bar.
- Otherwise **NOT NOMINATED** (within the twin null).

| clause | measured | bar | side |
| --- | ---: | ---: | --- |
| SLU-F1 CI95 lower bound > 0 | -1.8522 | 0 | not met |
| SLU-F1 point delta > twin bar | -0.4582 | 0.9056 | not met (\|delta\| 0.46 is inside the bar) |
| intent CI95 lower bound >= -(twin intent bar) | -0.0926 | -0.0000 | not met (one row: the bootstrap moves in 1/1,080 = 0.0926 pp steps) |
| SLU-F1 harm: CI95 upper bound < 0 and \|delta\| > bar | +1.1209 | 0.9056 | not met |
| intent harm: CI95 upper bound < 0 and \|delta\| > bar | +0.9259 | 0.0000 | not met |

The knob's SLU-F1 point delta, -0.46 pp, sits inside the twin bar of +/-0.91 pp. No harm clause is met. By
the rule, the numbers fall in the residual branch, "within the twin null". The verdict word is the
coordinator's.

- **Declared expectation.** The declared expectation was +0.09 pp, from VAR-1 exk30 against the in-chain
  PLANR. That was below the design's provisional floor of 0.3163 pp, so the cell declared
  `claims_benefit: false`. The measured point, -0.46 pp, is on the other side of zero from the declaration.
  It is within both the twin bar and the knob's own CI95.
- **Equal-scenario weighting.** The knob reads SLU-F1 -0.03 [-1.63, +1.58] and intent +0.37 [-0.09, +0.93].
  The twin reads SLU-F1 +0.36 [-0.14, +0.94] and intent 0.00.

## 6. Per-scenario tables (natural mixture; the equal-scenario row is in section 5)

Each scenario has n = 60. These are CI95 by the paired cluster bootstrap. The strata are descriptive, and
none is powered.

| scenario | intent A | B - A intent | saves / harms | SLU A | B - A SLU | B - A SLU CI95 | T - A SLU |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: |
| alarm | 93.33 | 0.00 | 0 / 0 | 77.00 | -3.79 | [-8.03, -0.58] | -1.06 |
| audio | 80.00 | +1.67 | 1 / 0 | 64.15 | +2.37 | [-7.14, +13.70] | 0.00 |
| calendar | 91.67 | 0.00 | 0 / 0 | 65.51 | -2.11 | [-4.94, +0.28] | +0.36 |
| cooking | 86.67 | 0.00 | 0 / 0 | 64.22 | +1.09 | [-2.88, +5.90] | +2.00 |
| datetime | 91.67 | -1.67 | 0 / 1 | 76.27 | +0.04 | [-4.01, +3.78] | +0.55 |
| email | 90.00 | 0.00 | 0 / 0 | 65.02 | +0.80 | [-3.89, +5.76] | 0.00 |
| general | 46.67 | +1.67 | 1 / 0 | 20.00 | +6.67 | [-4.76, +24.68] | 0.00 |
| iot | 81.67 | +5.00 | 3 / 0 | 71.17 | -6.79 | [-13.63, +0.19] | +0.81 |
| lists | 88.33 | 0.00 | 0 / 0 | 55.54 | +0.66 | [-6.50, +8.78] | +4.13 |
| music | 81.67 | -1.67 | 0 / 1 | 45.58 | -0.73 | [-4.37, +2.20] | 0.00 |
| news | 88.33 | 0.00 | 0 / 0 | 73.75 | -3.61 | [-7.62, -0.67] | -1.99 |
| play | 88.33 | 0.00 | 0 / 0 | 53.12 | +3.53 | [-0.39, +8.40] | +0.35 |
| qa | 90.00 | 0.00 | 0 / 0 | 57.01 | +9.38 | [+0.02, +20.92] | 0.00 |
| recommendation | 96.67 | 0.00 | 0 / 0 | 67.97 | -1.92 | [-7.56, +3.61] | 0.00 |
| social | 81.67 | 0.00 | 0 / 0 | 59.47 | +1.23 | [-2.64, +5.47] | +0.88 |
| takeaway | 83.33 | 0.00 | 0 / 0 | 58.14 | -2.44 | [-8.56, +3.25] | +0.19 |
| transport | 85.00 | +1.67 | 1 / 0 | 65.16 | -2.15 | [-5.69, +0.98] | +1.12 |
| weather | 96.67 | 0.00 | 0 / 0 | 80.03 | -2.74 | [-7.30, +1.90] | -0.79 |

Twin intent deltas are 0.00 in every scenario. For scale, the twin's own scenario SLU spread runs from -1.99
(news) to +4.13 (lists).

## 7. Cost: tokens per column contact, and the +2 contacts per row

These come from the sealed trace (`usage` per MODEL_RESPONSE), mapped to the first-visit contacts through the
sealed row custody (numbers only).

| column | first-visit contacts | prompt tokens per contact | completion tokens per contact | prompt tokens total |
| --- | ---: | ---: | ---: | ---: |
| `a-base` (delivering) | 1,080 | 10,193.1 | 24.0 | 11,008,516 |
| `t-twin` | 1,080 | 10,193.1 | 24.0 | 11,008,516 |
| `b-exk30` | 1,080 | 10,552.4 (+359.3 vs A) | 23.9 | 11,396,578 |

The instrument's price is the K - 1 = 2 non-delivering first-visit Solver contacts per row:

- 2,160 contacts (6,539 vs the wave A/A's 4,393 on the same roster: +2,146; revision counts differ).
- 22,405,094 prompt tokens, about 20,745 per row, or 37.3 % of the flight's 60.0 M.
- About 6,125 s of re-sent speech: 18,682.4 vs 12,557.2 s. The registered projection was 2 x 3,084.5 s.
- About +1.08 GPU-h per 1,080 rows: 2.8205 vs 1.7417, although that GPU-h figure is cross-flight.

By role across the flight:

| role | contacts | prompt tokens per contact |
| --- | ---: | ---: |
| Perception | 1,080 | 3,598 |
| Solver (all visits and arms) | 3,264 | 10,311 |
| Reviewer | 1,104 | 10,168 |
| Planner | 1,091 | 10,300 |

## 8. Two read-path repairs (before any number was opened)

Both are committed in this worktree ahead of the read. Neither changes a registered semantic.

1. **The step-0 countersign gate of `scripts/flights/wsv1/wsv1_read.sh`.** It loaded
   `scripts/checks/flight_registration_check.py` through `spec_from_file_location` without a `sys.modules`
   entry, so that module's `@dataclass` raised an AttributeError. The driver exited 3 before anything was
   opened. The fix registers the module before `exec_module`. The same pattern is present, and untouched
   here, in `scripts/flights/psv/psv_read.sh`, `scripts/flights/e4/e4_read.sh` and
   `scripts/flights/w4sv/w4sv_read.sh`.
2. **`stage3_paired_read.py` `run_pair`.** This is the extension path that `--per-scenario` takes. It called
   `load_arm` without the scorer id, so a column arm was refused with "a column arm needs its scorer id to
   locate the derived score". The same path also skipped the AT4 same-parent refusal
   (`_assert_column_pair_invariants`). It now mirrors the core's own `run_stages`, and the 15 paired-read
   tests pass.

   The refusal came after step 1 had scored the three columns and before any read file was written. The two
   read passes (`twin-null` then `knob`) were therefore run from a scratch script with arguments
   byte-identical to the script's `read_pass`. Re-running the script would have repeated step 1, and so
   repeated the official scoring, which the recipe allows once per column.

## 9. What the instrument's first real use shows

- **Row level.** The provisional floor was an assumption: the ROLL-AA within-flight half-width of 0.735 pp at
  n = 200, scaled to 0.3163 pp at n = 1,080. The twin null measured here, on the Solver-local first-visit
  estimand, has a pooled SLU-F1 half-width of 0.532 pp. That is about 1.7 x the scaled assumption, or
  roughly 1.24 pp if rescaled back to n = 200. With the +0.37 pp offset added, the bar is 0.906 pp, about
  2.9 x the provisional floor.
- **Intent.** The null is exactly zero. At the first Solver visit, identical requests produced identical
  intents on all 1,080 rows, so any intent disagreement between a knob column and the delivering column is
  attributable to the knob. On this metric the bar degenerates to "no net harm row" and cannot absorb even
  one harm.
- **SLU-F1 and the cross-flight comparison.** The same-flight instrument does read far narrower than the
  cross-flight in-chain A/A. For the knob, the SLU-F1 half-width is 1.49 pp, against 1.34 pp for W4 vs the
  wave A/A. The twin half-width is 0.53 pp, against the cross-flight 2.5 pp floor. So it resolves
  effects of roughly 1 pp and above on SLU-F1, and single rows on intent. Resolving the 0.09 pp declared here
  would need a null of that order, and this flight shows the SLU null is about ten times wider.
- **Price.** A 53 % increase in contacts, 37 % of prompt tokens and about 50 % of speech seconds per flight,
  for two extra columns.

## Coordinator verdict (Fable 5.1, 2026-09-29)

- **b-exk30 (exemplar k 30): NOT NOMINATED, inert.** SLU -0.46 [-1.85, +1.12], intent +0.37 [-0.09, +0.93]; both intervals cover zero and neither point clears the twin bar. The exemplar-k line is closed at k 30 on this roster.
- **Instrument finding (the more important result).** The same-flight twin null on intent is exactly 0.00 (T chose A's intent on 1,080 of 1,080 rows); on SLU-F1 the twin half-width is 0.53 (bar 0.91), about 1.7 times the design's assumed 0.3. The same-flight design is therefore a sharp intent instrument for the Perception-branch reads (P-SV-1, P-SV-2) and a moderate SLU instrument; cross-flight remains the only route for whole-system SLU claims above about 1 pp.
- Nothing is admitted or closed for the composed policy by this read (claim ceiling nominated, phase-1 ruling Q6). Development number (decision 28).
