# DESCRIPTIVE -- cell B6: the locked v2.0 default plan against the bare core on the fresh DEV-2000-ADDED roster (1,000 rows, paired)

**Report-only read (no verdict, no bar).** On a roster no SLURP cell had ever touched, the locked plan beats the bare
core by **+27.3 pp official pooled SLU-F1 (38.09 -> 65.40, CI95 [+24.0, +30.5]) and +14.9 pp intent (61.7 -> 76.6,
CI95 [+11.8, +18.0])**, paired and clustered by utterance, at 4.07 contacts per row and 1.655 GPU hours per 1,000
rows against the core's 1 contact and 0.087 GPU hours. This is the decision-76a comparison of the pure driven model
against the system-level agent for the SLURP carrier; it is a development number (decisions 28, 86) on a dev roster,
never a test claim.

Read 2026-09-22 by the coordinator, model-free, with the reusable stage driver
`scripts/analysis/slurp_paired_roster_read.py` (merged fa761ab3; sha256 recorded in every artifact), stages stop /
structural / contrast / efficiency / verdict, analysis root
`SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-B6-DEV2000-ADDED-PAIRED-ANALYSIS-V1/`. Recipe
`docs/readiness/2026-09-22-slurp-b6-dev2000-added-v1/analysis-recipe-v1.json`.

**Exposure.** Zero model, tokenizer, encoder, ASR, server, GPU, paid-API and network contacts; the official scorer ran
exactly once per arm inside each flight (one score job each) and this read only re-derives from those sealed
per-sample scores; nothing was re-scored. No utterance text, transcript, gold or model output is printed.

**Claim boundary.** DEV-2000-ADDED is the added half of DEV-2000 (decision 34), 1,000 devel recordings, 913 distinct
utterances (87 with two recordings; clusters = utterance id, decision 79 D2), 540 far-field / 460 headset; the sealed
DEV-1000 half is untouched. Official SLURP `evaluate.py` at 8eb16545 (`slurp-slu-official`, devel gold). Both arms
flew once, never re-flown. No superiority, generalisation, component-causal, cross-carrier or geometry claim beyond
this descriptive contrast; nothing here is comparable with a published TEST baseline.

## 0. The arms

| arm | run | form | contacts | repeated speech s | GPU hours | flight commit |
| --- | --- | --- | ---: | ---: | ---: | --- |
| direct (bare core) | `SAEA-SLURP-DIRECT-MAX512-DEV2000-ADDED-V1` | the sealed `slurp-direct-max512` form (decision 88): `phase-direct-only-v1`, closed-list task instruction, 512 completion tokens, np4 | 1,000 (1.0 per row) | 2,983.5 | 0.087 | 54f569c6 |
| plan (locked v2.0) | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1` | cell PLAN's fragment re-pointed at the DEV-2000-ADDED packets, vectors and receipts only (proof test: every other key byte-identical) | 4,071 (4.07 per row; histogram 2: 10, 4: 963, 7: 27) | 12,150.4 | 1.655 | 54f569c6 |

Both FINALIZED, manifests COMPLETED at the flight commit, roster identity reproduced, one score job each, aggregates
reproduced from per-sample scores to 1e-6 (`stop.json` ab18d2f2...). Flown by the SAEA-Batch-Chain-B6 scheduled
task behind B9a-rec (decision 77). No four-row smokes (both forms sealed and flown before; stated in the
preregistration).

## 1. Paired contrast, plan minus direct (utterance-clustered bootstrap, 10,000 draws, seed 20260915)

| metric | direct | plan | delta pp | CI90 | CI95 | saves / harms / ties | McNemar p |
| --- | ---: | ---: | ---: | --- | --- | --- | --- |
| **official pooled SLU-F1 (primary)** | 38.09 | 65.40 | **+27.30** | [+24.59, +30.01] | **[+24.05, +30.50]** | per-row SLU 395 / 42 / 563 | < 0.001 |
| intent (scenario_action) | 61.7 | 76.6 | **+14.90** | [+12.28, +17.49] | **[+11.78, +18.03]** | 199 / 50 / 751 | < 0.001 |
| scenario | 69.4 | 81.6 | +12.20 | [+9.77, +14.64] | [+9.33, +15.15] | 170 / 48 / 782 | < 0.001 |
| action | 65.5 | 79.2 | +13.70 | [+11.15, +16.32] | [+10.61, +16.82] | 192 / 55 / 753 | < 0.001 |
| span-F1 (pooled micro) | 25.19 | 57.05 | +31.86 | [+28.48, +35.18] | [+27.86, +35.86] | | |
| slot-F1 exact (per row) | 15.48 | 40.61 | +25.12 | [+22.73, +27.51] | [+22.24, +27.91] | 334 / 26 / 640 | < 0.001 |

Source: `score-contrasts.json` (a65e7ea9...). The per-scenario table and the equal-scenario weighting are NOT
AVAILABLE for this roster: the roster receipt withholds the per-item stratum (`stratum_withheld_per_item: true`) and
the official scorer's per-sample record carries no scenario field; deriving one would require gold (refused). The
driver records this in `per-scenario-tables.json` (2844f9cb...) rather than omitting it. Per channel (descriptive,
unclustered because a doubled utterance's two recordings can differ in channel):

| channel | n | intent direct -> plan | delta pp | saves / harms | action delta pp |
| --- | ---: | --- | ---: | --- | ---: |
| far-field | 540 | 60.4 -> 73.9 | +13.5 | 108 / 35 | +12.0 |
| headset | 460 | 63.3 -> 79.8 | +16.5 | 91 / 15 | +15.7 |

## 2. Beside the exposed-roster numbers (reported, never chained)

| roster | direct SLU / intent | plan SLU / intent | plan minus direct |
| --- | --- | --- | --- |
| DEV-2000-ADDED (this read, fresh) | 38.09 / 61.7 | 65.40 / 76.6 | +27.3 / +14.9 |
| TRAIN Fold A (exposed discovery roster; the released direct anchor `docs/results/2026-09-17-slurp-train-a-direct-anchor-release.md` vs cell PLAN) | 33.89 / 73.70 | 63.63 / 82.22 | +29.7 / +8.5 (different arms' flights, unpaired here) |
| DEV-1000 (the 2026-09-13 dual-store anchor vs its direct, 500 + 500) | 35.68 / -- | 50.30 / -- | +14.6 SLU |

The plan's SLU on the fresh roster (65.40) is above its TRAIN Fold A number (63.63); the bare core's (38.09) sits
between its TRAIN Fold A (33.89) and DEV-1000 (35.68) figures; the system-over-core gap on a fresh roster is roughly twice the gap the 2026-09-13 dual-store
anchor showed on DEV-1000 (+14.6), consistent with the modules admitted since (M1, M4b, M3). These are three
different rosters and scorer siblings: no chaining, no pooled claim.

## 3. Structure and cost

- Plan arm: E13 finite-completion rows 10, revision-limit 1, 0 ReAct exhaustions, 0 tool calls, 0 compactions; 27
  rows revised (7 contacts). Direct arm: 1,000 single contacts, 0 tool calls (`structural.json` 54333e67...).
- Cost (`efficiency.json` aad25430...): direct 428 s wall, 313 GPU-active s, 140 contacts/min, 2,280 prompt tokens
  per row; plan 6,453 s wall, 5,956 GPU-active s, 37.9 contacts/min, 35,913 client prompt tokens per row (the
  prefilled estimate follows the TRAIN-A plan's about 8,400), mean utilisation 80 %. The gain costs 19x the GPU time
  of the bare core on this geometry; the frontier row for Stage 3 is 65.40 at 1.655 GPU-h per 1,000.

## 4. What this read settles and what it does not

Settled: decision 76a's SLURP comparison -- the system-level agent (the locked plan) is far above the pure driven
model on a roster it never saw, on every official metric, with CI95s that exclude zero by more than 10 pp, on both
channels. The decision-78 seal path is complete (PLAN + PLANr lock, B9a-rec read, B6 read). Not settled: any test-set
number (decision 29: one read after Stage 3), the per-scenario picture on dev (needs a model-free scenario label for
the roster, a registration item), and the Acquisition node (B9a-rec inert; E36b pending the owner).

## Artefacts

`stop.json` ab18d2f2..., `structural.json` 54333e67..., `score-contrasts.json` a65e7ea9..., `efficiency.json`
aad25430..., `per-scenario-tables.json` 2844f9cb..., `verdict.json` d8e67afd... (status DESCRIPTIVE), `README.md`
5bf75a4b..., stage logs. Direct arm: run-manifest 06a0c3a3..., scores 847d932b..., outputs 406f5a58.... Plan arm:
run-manifest 9905ce63..., scores 1ac4402a..., outputs 41ebcea4.... Package
`docs/readiness/2026-09-22-slurp-b6-dev2000-added-v1/`.
