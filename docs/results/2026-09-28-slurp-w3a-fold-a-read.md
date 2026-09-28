# Cell W3a (intent contrast cards) read: intent -0.56 pp CI95 [-1.67, +0.56] and official SLU-F1 +0.32 pp [-1.39, +2.02] against the shared wave A/A on TRAIN Fold A (DESCRIPTIVE)

Read 2026-09-28 by Claude Opus 5.5 (worktree `/home/chao/saea-worktrees/fable-wavereads`, branch
`fable/wavereads`). The registered paired read (READ row `SAEA-SLURP-STAGE3-W3-FOLD-A-PAIRED-ANALYSIS-V1`,
ROOT COUNTERSIGNED before any score was opened; recipe sha256
`ab93f02da0bf21f3f5d1acb38af172be73444f0f63521da8a909ec31c2e9819e`) ran through
`scripts/flights/wave/wave_read.sh w3` -> `scripts/flights/read_paired_cell.sh` ->
`scripts/analysis/stage3_paired_read.py` (sha256 `433bc936c0106f6377ed8ba693539f30dbe36014ec0622650ddafffb0656fad1`):
seed 20260927, 10,000 draws, the row as the resampling unit, TRAIN gold through `slurp-slu-official-train`.
Outputs under `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-W3-FOLD-A-PAIRED-ANALYSIS-V1/`: `vs-aa/` (GATING;
README sha256 `a8785e5267c9eb54868328aab394bd9bb9a9ed13eb0e6f40e9602703cac3e32e`, `verdict.json`
`1f12a9c4f5fac0ed9c3595dd639f477106bb6480b62e703b78d5251b3a68b5b3`, `score-contrasts.json`
`8f64a2bafb5da67349443cfd1b3b0d7c739cefa15c7e55b536a3ca6206048969`) and `vs-comparator/` (the sealed AGREE arm,
CONTEXT only; `verdict.json` `8dbb7343a350a2c9df7866028d7ac187334ff761550d8e274eaa44885d782b31`). The recipe's
row attribution (step 6) and per-role token table (step 7) were computed beside it: the membership by
`scripts/analysis/slurp_w3_membership_read.py`, which imports the offline read's own functions unmodified and
refuses unless it reproduces the registered counts (it did: 153 wrong rows, 41 named before, 89 named after),
into `beside/w3-membership-v1.json` (sha256 `1bf0cbb110b3fafa264068c34ce91d4615940560f4b86e4e4c63e9ebc9ea5cef`);
the transitions and tokens by `scripts/analysis/stage3_wave_beside_read.py` into `beside/beside-v1.json`
(sha256 `68fb36476b8217756ef1c1a202a1eae5a62c823d1234e3cb4135d7e0296b5c9d`). Model-free throughout; gold
enters only offline as the intent label for the membership, compared in memory. No utterance text, gold
label string, intent name or model output is printed or persisted.

**DESCRIPTIVE.** The numbers and the side of the pre-declared rule they fall on; the verdict word is the
coordinator's (decision 139). A development read on a TRAIN construction fold (decisions 28, 86).

## 1. What flew

Driver step 2 (`w3`) at flight commit `5f8b4c9d`, study tree clean at seal; the four-row smoke first
(COMPLETED, 16 calls, unscored). The comparator is the shared wave A/A sealed in step 1 (not re-flown).

| run | sealed at (UTC) | rows | contacts / cap | speech s | GPU-active | state |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1` (shared A/A) | 05:41:00 | 1,080 | 4,393 / 11,880 | 12,557.168 | 1.7417 GPU-h | COMPLETED |
| `SAEA-SLURP-STAGE3-W3-FOLD-A-V1` (arm) | 09:10:30 | 1,080 | 4,364 / 11,880 | 12,458.237 | 5,816.5 s = 1.6157 GPU-h | FINALIZED, scored once |

Arm sha256: run manifest `8ece3c52e572c59ab5c3157ff09d41efda17fb5de0c470b02e9ad67304de399f`, outputs
`26cfb6ae5123788443198b96fe83d321a4672adf3f9ef655e8a2d6c6ba02e534`, scores
`f847c41acaeed95a1ce72300afc3dee24434e0875b1d47b642008a179986a736`, generation manifest
`a63c92ab1275782ebaa2e8e79ecbdd003552912b16d0b207406177b5a1f61a48`, phases
`44560a6bdbd5c5a9cf07b815e76a05eeb6e184e95575e06e47ef5218313d575d`, flight receipts
`d5e3b14876b48e83cda9a5c00043c3cbd3fcbd9ce52b60f535e5ddaa846114c7`. A/A hashes: see
[the W1 read](2026-09-28-slurp-w1-fold-a-read.md) section 1.

## 2. Structural gates

| gate | A/A | arm |
| --- | --- | --- |
| rows admitted | 1,080 | 1,080 |
| tool calls / compacted contacts | 0 / 0 | 0 / 0 |
| Planner ACCEPT / REVISE; revisions executed | 1,066 / 29; 29 | 1,072 / 18; 17 |
| role visits per row (2 / 4 / 7) | 14 / 1,037 / 29 | 7 / 1,056 / 17 |
| deliver-normaliser changed rows | 96 | 87 |
| gold intent boundary delivered | 1,040 | 1,040 (0 newly delivered, 0 newly lost) |

Recipe step 2's byte-level structural stage (the Perception boundary ids and the Solver's 20 exemplars equal
the AGREE arm's on every row; the delivered card bodies hash to the contrast release) is not computed by the
registered driver and was not re-derived here; the delivery counts above are consistent with it.

## 3. The contrasts

Gating, the arm against the shared wave A/A (`vs-aa/`):

| metric | A/A | arm | delta pp | CI95 pp | saves / harms | McNemar p |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| **intent (scenario_action_exact), primary** | 85.65 | 85.09 | **-0.56** | **[-1.67, +0.56]** | 15 / 21 | 0.405 |
| scenario | 89.44 | 88.70 | -0.74 | [-1.76, +0.28] | 12 / 20 | 0.215 |
| action | 86.48 | 86.02 | -0.46 | [-1.48, +0.56] | 14 / 19 | 0.487 |
| **official pooled SLU-F1, guard** | 64.16 | 64.48 | **+0.32** | **[-1.39, +2.02]** | -- | -- |
| official pooled span-F1 | 53.54 | 54.47 | +0.93 | [-0.99, +2.80] | -- | -- |
| per-row SLU-F1 | 42.98 | 42.69 | -0.29 | [-1.63, +1.04] | 72 / 76 | 0.805 |
| per-row slot exact F1 | 35.11 | 35.30 | +0.19 | [-1.22, +1.62] | 54 / 54 | 1.000 |

Per channel (descriptive): intent -0.72 far-field (8 / 12), -0.38 headset (7 / 9).

Context only, against the sealed AGREE arm (`vs-comparator/`): intent 85.83 -> 85.09, -0.74 pp
[-1.85, +0.37] (16 / 24); official SLU-F1 65.16 -> 64.48, -0.68 pp [-2.37, +0.97].

Declared expectation: 0.0 (the recipe declares no expected effect; no measured conversion applies to contrast
text). The intent point estimate is -0.56 pp and the SLU-F1 point estimate +0.32 pp against that 0.0.

## 4. The pre-declared rule, and where the numbers fall

Recipe `decision_rule` (decision 164 brief, row 139): against the shared A/A, intent CI95 lower bound not below
-0.9943 pp AND official pooled SLU-F1 CI95 lower bound not below -1.2485 pp; HARMFUL on a measured loss on
either metric (CI95 upper bound below zero); otherwise the step-5 residual branch. Never reported as a gain.

| clause | measured | side |
| --- | ---: | --- |
| intent CI95 lower bound >= -0.9943 | -1.67 | does not hold (0.68 pp beyond the margin) |
| official SLU-F1 CI95 lower bound >= -1.2485 | -1.39 | does not hold (0.14 pp beyond the margin) |
| intent CI95 upper bound < 0 (harm) | +0.56 | not met |
| official SLU-F1 CI95 upper bound < 0 (harm) | +2.02 | not met |

Neither no-harm clause holds and neither harm clause is met: the numbers fall in the recipe's step-5
residual ("otherwise") branch. Both intervals include zero.

## 5. Per-scenario tables (both weightings)

| weighting | intent delta pp | intent CI95 pp | SLU-F1 delta pp | SLU-F1 CI95 pp |
| --- | ---: | --- | ---: | --- |
| natural mixture | -0.56 | [-1.67, +0.56] | +0.32 | [-1.39, +2.02] |
| equal scenario | -0.56 | [-1.67, +0.46] | -0.19 | [-2.07, +1.70] |

| scenario | intent A/A | intent arm | delta | saves / harms | SLU A/A | SLU arm | delta | SLU CI95 |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| alarm | 91.67 | 90.00 | -1.67 | 1 / 2 | 69.58 | 78.85 | +9.27 | [+3.40, +15.45] |
| audio | 81.67 | 78.33 | -3.33 | 2 / 4 | 60.82 | 64.39 | +3.57 | [-10.19, +19.38] |
| calendar | 91.67 | 93.33 | +1.67 | 1 / 0 | 64.72 | 67.71 | +2.98 | [-1.10, +7.57] |
| cooking | 83.33 | 83.33 | +0.00 | 2 / 2 | 65.98 | 66.83 | +0.84 | [-5.55, +8.27] |
| datetime | 91.67 | 90.00 | -1.67 | 0 / 1 | 74.02 | 72.41 | -1.61 | [-8.01, +4.67] |
| email | 90.00 | 88.33 | -1.67 | 0 / 1 | 62.76 | 61.86 | -0.90 | [-8.46, +6.11] |
| general | 50.00 | 50.00 | +0.00 | 0 / 0 | 26.09 | 19.05 | -7.04 | [-23.67, +4.10] |
| iot | 81.67 | 85.00 | +3.33 | 2 / 0 | 69.75 | 67.91 | -1.84 | [-8.19, +4.32] |
| lists | 90.00 | 88.33 | -1.67 | 0 / 1 | 57.66 | 56.56 | -1.10 | [-11.14, +8.06] |
| music | 81.67 | 78.33 | -3.33 | 0 / 2 | 46.33 | 46.33 | +0.00 | [-4.72, +5.03] |
| news | 91.67 | 88.33 | -3.33 | 0 / 2 | 74.41 | 70.40 | -4.01 | [-12.03, +2.95] |
| play | 88.33 | 90.00 | +1.67 | 1 / 0 | 54.79 | 53.01 | -1.78 | [-6.43, +2.84] |
| qa | 88.33 | 90.00 | +1.67 | 1 / 0 | 65.10 | 66.01 | +0.91 | [-3.85, +5.55] |
| recommendation | 96.67 | 98.33 | +1.67 | 1 / 0 | 73.04 | 66.56 | -6.48 | [-14.10, +0.07] |
| social | 81.67 | 83.33 | +1.67 | 1 / 0 | 58.76 | 59.63 | +0.87 | [-3.96, +6.48] |
| takeaway | 81.67 | 78.33 | -3.33 | 1 / 3 | 55.12 | 63.40 | +8.28 | [+2.89, +13.92] |
| transport | 85.00 | 83.33 | -1.67 | 2 / 3 | 62.97 | 67.13 | +4.16 | [-1.71, +10.16] |
| weather | 95.00 | 95.00 | +0.00 | 0 / 0 | 79.72 | 70.26 | -9.46 | [-20.06, +0.28] |

## 6. Delivery and row attribution

| delivery group | rows | wrong -> right | right -> wrong | right -> right | wrong -> wrong |
| --- | ---: | ---: | ---: | ---: | ---: |
| delivered in both | 1,040 | 15 | 18 | 900 | 107 |
| delivered in neither | 40 | 0 | 3 | 4 | 33 |

Row attribution (recipe step 6; groups fixed on the AGREE arm's intent-wrong rows before contact; transitions
A/A -> arm):

| group | rows | wrong -> right | right -> wrong | right -> right | wrong -> wrong | per-row SLU-F1 A/A -> arm |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| pair newly named by the contrast lines | 48 | 3 | 0 | 2 | 43 | 29.86 -> 33.17 |
| pair already named before | 41 | 3 | 1 | 3 | 34 | 37.91 -> 37.25 |
| wrong, pair unnamed after | 64 | 3 | 3 | 2 | 56 | 8.63 -> 11.79 |
| AGREE-right rows (the rest) | 927 | 6 | 17 | 897 | 7 | 46.25 -> 45.55 |

The 48 newly named rows move 3 / 0; the net intent loss (15 saves / 21 harms overall) sits on the AGREE-right
rows (6 / 17).

## 7. Tokens and cost

| quantity | A/A | arm | arm - A/A |
| --- | ---: | ---: | ---: |
| contacts | 4,393 | 4,364 | -29 |
| prompt tokens per row | 35,061.4 | 33,682.8 | -1,378.6 |
| prefilled tokens per row | 8,762.3 | 8,393.4 | -368.8 |
| completion tokens per row | 245.9 | 217.3 | -28.6 |
| GPU-h per 1,080 rows | 1.7417 | 1.6157 | -0.1260 |

| role | contacts A/A / arm | prompt tokens per contact A/A -> arm | delta | prefilled per contact delta |
| --- | --- | --- | ---: | ---: |
| Perception | 1,080 / 1,080 | 3,598.4 -> 3,541.6 | -56.8 | -56.6 |
| Solver | 1,109 / 1,097 | 10,228.3 -> 9,892.5 | **-335.8** | -212.4 |
| Reviewer | 1,109 / 1,097 | 10,203.6 -> 9,867.4 | -336.2 | -0.3 |
| Planner | 1,095 / 1,090 | 10,338.9 -> 9,977.9 | -361.0 | -17.8 |

The offline projection registered -53.9 tokens per Solver contact (`offline-estimates-v1.json`,
`request_size_projection.net_token_delta_per_solver_contact.mean`, which included the exemplar cap W3a does
not fly); the realised Solver delta is -335.8. This note does not decompose the difference.

Frontier row: intent -0.5556 pp and SLU-F1 +0.3238 pp at -368.8 prefilled tokens per row and -0.1260 GPU-h
per 1,080 rows.

## Coordinator verdict (Fable 5.1, 2026-09-28)

**NOT ADMITTED (neutral by width; the card form of K1 is closed).** Against the shared wave A/A, intent
-0.56 [-1.67, +0.56] (15 saves / 21 harms, p 0.405) and official SLU-F1 +0.32 [-1.39, +2.02]. The intent
no-harm clause does not hold (lower bound -1.67 below -0.9943; the SLU-F1 lower bound -1.39 also sits below
-1.2485) and no harm clause is met, so the cell neither clears nor harms by the registered rule. As a
benefit candidate its point estimate is negative: the K1 ceiling (the +6.94 pp oracle in
[2026-09-27-slurp-knowledge-content-audit.md](2026-09-27-slurp-knowledge-content-audit.md)) did not convert
in card form. This joins the pattern that changes of form without new row-matched content do not gain
([2026-09-27-slurp-mechanism-synthesis.md](2026-09-27-slurp-mechanism-synthesis.md) section 2.1). The
contrast-evidence route continues only at the decision node -- the B1 rank-visible probe (package
`2026-09-27-slurp-stage3-rankvis-probe-fold-a-v1`) and the Reviewer top-2 contrast of decision 165's second
round -- not as cards. W3a does not enter COMP-2. The token saving (-1,378.6 prompt tokens per row, -0.126
GPU-h per 1,080 rows) is noted but is not a reason to retain it. The agent's numbers above are unchanged.
