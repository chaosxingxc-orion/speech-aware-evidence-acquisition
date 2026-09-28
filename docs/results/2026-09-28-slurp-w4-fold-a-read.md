# Cell W4 (slot conventions) read: official SLU-F1 +0.79 pp CI95 [-0.56, +2.12] and intent -0.09 pp [-1.02, +0.83] against the shared wave A/A on TRAIN Fold A (DESCRIPTIVE)

Read 2026-09-28 by Claude Opus 5.5 on the master checkout (the read drivers are model-free and do not invoke
`core.flight.cli`). The registered paired read (READ row `SAEA-SLURP-STAGE3-W4-FOLD-A-PAIRED-READ-V1`, ROOT
COUNTERSIGNED 2026-09-28T11:19:21Z before any score was opened and after the seal; recipe
`analysis-recipe-v1.json` sha256 `19768c951a197a3eb75d561c87445efdb729f9aa5913c860e7a2af9586f594d0`) ran through
`scripts/flights/wave/wave_read.sh w4` -> `scripts/flights/read_paired_cell.sh` ->
`scripts/analysis/stage3_paired_read.py` (sha256 `433bc936c0106f6377ed8ba693539f30dbe36014ec0622650ddafffb0656fad1`):
seed 20260927, 10,000 draws, the row as the resampling unit, TRAIN gold through `slurp-slu-official-train`.
Outputs under `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-W4-FOLD-A-PAIRED-READ-V1/`: `vs-aa/` (GATING;
README sha256 `8415903853346be8e262499776ca594fd398f090e0c602bfcdd363b6a60f39e6`, `verdict.json`
`7735df4462b9e4038d92bd517de2667d227c3e87ed18ff9b4492f889bf9e03b6`, `score-contrasts.json`
`82992e11f149e8ebcf230040afa56587b0b2c31340a321706ef42b8fbe139aea`) and `vs-comparator/` (the sealed AGREE arm,
CONTEXT only; `verdict.json` `b49a9a788a3c9f8fe74a774a8cfe580bedb52eee53f369ab3e49a9ac692bce28`). Beside it:
the recipe's step-6 mechanism read by `scripts/analysis/slurp_w4_mechanism_read.py` (sha256
`c0f3ab9b34499df7fea856d52a26aab7d1efb989d3cf150a4960458edba4ab38`; it imports the registered estimate script
`scripts/analysis/slurp_w4_fold_a_offline_estimate.py`, sha256
`7eeaa13e6f6787cbcd053fab484f9be122430d8fa3bac9b8fbd84d7b49313408`, unmodified) into
`mechanism/w4-mechanism-read.json` (sha256 `1fd2de53f42c784f37ecb816d04761c77281f7199671328beadf3ab34239db4b`);
the entity-class totals of section 6 by an unregistered scratch script applying the same module's `entity_items`
unmodified, into `mechanism/entity-classes-v1.json` (sha256
`9c4505d458c6608a6ae3e1c2326badd82ea40c6bfcce0908439e2071c4df7fc9`); the per-role tokens by
`scripts/analysis/stage3_wave_beside_read.py` into `beside/beside-v1.json` (sha256
`6a4e322a1476f7f3644acbf95fe1ecc25ac0d34cb16e04b662ebf2f27d218a6f`). Model-free throughout; gold enters only
offline and is compared in memory. No utterance text, gold label string, slot filler or model output is
printed or persisted; only slot TYPE names and counts appear below.

**DESCRIPTIVE.** The numbers and the side of the pre-declared rule they fall on; the verdict word is the
coordinator's (decision 139). A development read on a TRAIN construction fold (decisions 28, 86).

## 1. What flew

Driver step 3 (`w4`) of the knowledge-wave chain at flight commit `5f8b4c9d`, study tree clean at seal
(driver-done 11:15:45Z). The comparator is the shared wave A/A sealed in step 1 (not re-flown). W4 flew alone
on the AGREE form (W1 not composed).

| run | rows | contacts / cap | speech s | GPU-h | state |
| --- | ---: | ---: | ---: | ---: | --- |
| `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1` (shared A/A) | 1,080 | 4,393 / 11,880 | 12,557.168 | 1.7417 | COMPLETED |
| `SAEA-SLURP-STAGE3-W4-FOLD-A-V1` (arm) | 1,080 | 4,377 / 11,880 | 12,494.773 | 1.9059 | COMPLETED, scored once |

Arm sha256: run manifest `52ad5626d78d2556427b5f3c6a497aa70231e1102fbd8e6e507530f96958b9f3`, outputs
`bc5cfb6d0b4c48d53f95c5473e5112ff069d55148ff5dbe4108381dbd17940ce`, scores
`3481650b32b97add3674b7803c38eb4fab4624678c4d22159150c45c49dd6116`, generation manifest
`83b78cb9e88aad1fce34271aded41645d851f0f3b3925e87321fe076f3a0638d`, phases
`9812f2fcc2237a88ca5aaf1cbc24cc31308086178c3616a578888dab6410afae`, flight receipts
`6d294c8f36df4ec77e0925eebc2be0465cd4f17005f6464b43bc7a945f593a82`, trace manifest
`01ac35f3aad07709fc3e41f9fbf8ef0927459fa2abaeba35777395153d9d3d6b`. A/A hashes: see
[the W1 read](2026-09-28-slurp-w1-fold-a-read.md) section 1.

## 2. Structural gates

| gate | A/A | arm |
| --- | --- | --- |
| rows admitted | 1,080 | 1,080 |
| tool calls / compacted contacts | 0 / 0 | 0 / 0 (registered projection: 0) |
| Planner ACCEPT / REVISE; revisions executed | 1,066 / 29; 29 | 1,066 / 25; 23 |
| role visits per row (2 / 4 / 7) | 14 / 1,037 / 29 | 12 / 1,045 / 23 |
| deliver-normaliser applied / changed rows | 1,080 / 96 | 1,079 / 104 |
| gold intent boundary delivered | 1,040 | 1,040 (0 newly delivered, 0 newly lost) |

Recipe step 2's byte-level check that every W4 request carries the `slot-contracts-w4-v1` snapshot identity is
not computed by the registered driver and was not re-derived here; the per-role token deltas in section 7 are
consistent with the cards reaching the Solver, Reviewer and Planner.

## 3. The contrasts

Gating, the arm against the shared wave A/A (`vs-aa/`):

| metric | A/A | arm | delta pp | CI95 pp | saves / harms | McNemar p |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| **official pooled SLU-F1, primary** | 64.16 | 64.95 | **+0.79** | **[-0.56, +2.12]** | -- | -- |
| official pooled span-F1 | 53.54 | 54.94 | +1.40 | [-0.26, +3.04] | -- | -- |
| **intent (scenario_action_exact), guard** | 85.65 | 85.56 | **-0.09** | **[-1.02, +0.83]** | 13 / 14 | 1.000 |
| scenario | 89.44 | 89.35 | -0.09 | [-0.83, +0.65] | 8 / 9 | 1.000 |
| action | 86.48 | 86.39 | -0.09 | [-1.02, +0.83] | 12 / 13 | 1.000 |
| per-row SLU-F1 | 42.98 | 43.40 | +0.43 | [-0.66, +1.55] | 63 / 54 | 0.460 |
| per-row slot exact F1 | 35.11 | 35.94 | +0.83 | [-0.38, +2.10] | 48 / 39 | 0.391 |

Per channel (descriptive): per-row SLU-F1 +1.00 far-field (37 / 32), -0.19 headset (26 / 22); intent +0.18
far-field (9 / 8), -0.38 headset (4 / 6).

Context only, against the sealed AGREE arm (`vs-comparator/`): official SLU-F1 65.16 -> 64.95, -0.21 pp
[-1.64, +1.22]; intent 85.83 -> 85.56, -0.28 pp [-1.20, +0.65] (12 / 15).

Declared expectation (registered-facts `expectation_basis`): `no-harm`, `expected_effect_pp` 0.0. The M4b
analogue (row 139: 301 FN items on the revised types with a card delivered, at M4b's 0.0044 to 0.0073 pp per
item) projects **1.3285 to 2.2009 pp (mean 1.7647)** SLU-F1, below the design's 2.5 pp benefit floor. The
measured SLU-F1 point estimate, +0.79 pp, sits below the analogue's lower end.

## 4. The pre-declared rule, and where the numbers fall

Recipe `decision_rule` (steps 4-5): against the shared A/A, official pooled SLU-F1 CI95 lower bound not below
-1.2485 pp (PRIMARY; the mechanism acts on slots) AND intent CI95 lower bound not below -0.9943 pp (the guard);
HARMFUL on a measured loss on either metric (CI95 upper bound below zero); otherwise NOT ADMITTED (width). A
SLU-F1 lower bound above zero would be reported as a development-fold effect, never as an admitted benefit.

| clause | measured | side |
| --- | ---: | --- |
| SLU-F1 CI95 lower bound >= -1.2485 | -0.5624 | holds (0.69 pp inside the margin) |
| intent CI95 lower bound >= -0.9943 | -1.0185 | does not hold (0.024 pp beyond the margin) |
| SLU-F1 CI95 upper bound < 0 (harm) | +2.1193 | not met |
| intent CI95 upper bound < 0 (harm) | +0.8333 | not met |
| SLU-F1 CI95 lower bound > 0 (development-fold effect) | -0.5624 | not met |

The primary no-harm clause holds; the guard clause misses by 0.024 pp, less than one row (the per-row intent
bootstrap moves in steps of 1/1,080 = 0.0926 pp, so the next attainable bound, -0.9259, would have held). No
harm clause is met. By the recipe's literal step 5 the numbers fall in the residual ("otherwise") branch.

## 5. Per-scenario tables (both weightings)

| weighting | SLU-F1 delta pp | SLU-F1 CI95 pp | intent delta pp | intent CI95 pp |
| --- | ---: | --- | ---: | --- |
| natural mixture | +0.79 | [-0.56, +2.12] | -0.09 | [-1.02, +0.83] |
| equal scenario | +0.10 | [-1.57, +1.68] | -0.09 | [-1.02, +0.83] |

| scenario | SLU A/A | SLU arm | delta | SLU CI95 | intent A/A | intent arm | delta | saves / harms |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| alarm | 69.58 | 71.65 | +2.07 | [-3.10, +7.54] | 91.67 | 93.33 | +1.67 | 2 / 1 |
| audio | 60.82 | 55.06 | -5.77 | [-19.42, +2.11] | 81.67 | 80.00 | -1.67 | 2 / 3 |
| calendar | 64.72 | 65.14 | +0.41 | [-2.04, +3.26] | 91.67 | 88.33 | -3.33 | 0 / 2 |
| cooking | 65.98 | 64.55 | -1.43 | [-6.08, +3.39] | 83.33 | 83.33 | +0.00 | 1 / 1 |
| datetime | 74.02 | 75.71 | +1.70 | [-2.18, +5.91] | 91.67 | 91.67 | +0.00 | 0 / 0 |
| email | 62.76 | 64.61 | +1.85 | [-3.51, +7.31] | 90.00 | 90.00 | +0.00 | 0 / 0 |
| general | 26.09 | 25.00 | -1.09 | [-14.79, +13.09] | 50.00 | 50.00 | +0.00 | 0 / 0 |
| iot | 69.75 | 72.92 | +3.17 | [-3.47, +10.64] | 81.67 | 83.33 | +1.67 | 1 / 0 |
| lists | 57.66 | 55.49 | -2.17 | [-12.50, +6.31] | 90.00 | 90.00 | +0.00 | 0 / 0 |
| music | 46.33 | 47.53 | +1.20 | [-3.08, +5.45] | 81.67 | 78.33 | -3.33 | 0 / 2 |
| news | 74.41 | 71.23 | -3.18 | [-12.52, +4.42] | 91.67 | 90.00 | -1.67 | 0 / 1 |
| play | 54.79 | 51.59 | -3.21 | [-8.09, +0.74] | 88.33 | 88.33 | +0.00 | 1 / 1 |
| qa | 65.10 | 64.39 | -0.71 | [-4.99, +3.40] | 88.33 | 91.67 | +3.33 | 2 / 0 |
| recommendation | 73.04 | 69.32 | -3.72 | [-10.31, +2.50] | 96.67 | 96.67 | +0.00 | 1 / 1 |
| social | 58.76 | 59.45 | +0.69 | [-4.05, +5.67] | 81.67 | 81.67 | +0.00 | 0 / 0 |
| takeaway | 55.12 | 63.48 | +8.37 | [+2.49, +15.03] | 81.67 | 81.67 | +0.00 | 2 / 2 |
| transport | 62.97 | 66.61 | +3.64 | [-0.46, +8.06] | 85.00 | 86.67 | +1.67 | 1 / 0 |
| weather | 79.72 | 79.62 | -0.10 | [-3.64, +3.53] | 95.00 | 95.00 | +0.00 | 0 / 0 |

60 rows per scenario; paired cluster bootstrap on `sample_id`. The natural-mixture SLU-F1 estimate (+0.79)
exceeds the equal-scenario one (+0.10) because the pooled count weights scenarios by their slot volume.

## 6. Mechanism read: entity classes and the revised types

Entity classes (the official exact matcher, then the bad-case bank's attribution as `entity_items` applies it:
EXACT = exact match; BOUNDARY = same type, filler differs; WRONG-TYPE = same filler, other type; SPURIOUS =
predicted and unmatched; MISSING = gold and unmatched), all 1,080 delivered rows:

| class | A/A items | arm items | delta | A/A rows | arm rows | delta rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| EXACT | 529 | 531 | +2 | 434 | 443 | +9 |
| SPURIOUS | 295 | 266 | **-29** | 258 | 240 | -18 |
| MISSING | 201 | 215 | **+14** | 182 | 195 | +13 |
| WRONG-TYPE | 28 | 24 | -4 | 28 | 23 | -5 |
| BOUNDARY | 183 | 171 | -12 | 173 | 163 | -10 |
| exact TP / FP / FN | 529 / 506 / 412 | 531 / 461 / 410 | +2 / -45 / -2 | | | |

Pooled exact span F1 53.54 -> 54.94. The movement is mostly fewer false positives (SPURIOUS -29, BOUNDARY -12,
WRONG-TYPE -4) against more omissions (MISSING +14); exact matches move +2.

Per revised type (19 types), exact TP / FP / FN:

| type | A/A | arm | arm - A/A |
| --- | --- | --- | --- |
| business_name | 19 / 45 / 33 | 20 / 41 / 32 | +1 / -4 / -1 |
| business_type | 14 / 15 / 15 | 14 / 10 / 15 | +0 / -5 / +0 |
| date | 65 / 29 / 73 | 69 / 31 / 69 | +4 / +2 / -4 |
| device_type | 11 / 19 / 4 | 10 / 19 / 5 | -1 / +0 / +1 |
| event_name | 23 / 29 / 18 | 22 / 23 / 19 | -1 / -6 / +1 |
| food_type | 43 / 36 / 22 | 47 / 35 / 18 | +4 / -1 / -4 |
| house_place | 10 / 8 / 5 | 12 / 7 / 3 | +2 / -1 / -2 |
| list_name | 16 / 19 / 6 | 15 / 17 / 7 | -1 / -2 / +1 |
| meal_type | 4 / 2 / 4 | 4 / 3 / 4 | +0 / +1 / +0 |
| media_type | 41 / 21 / 16 | 39 / 16 / 18 | -2 / -5 / +2 |
| news_topic | 9 / 15 / 6 | 9 / 14 / 6 | +0 / -1 / +0 |
| order_type | 3 / 7 / 20 | 4 / 5 / 19 | +1 / -2 / -1 |
| person | 22 / 30 / 20 | 19 / 37 / 23 | -3 / +7 / +3 |
| place_name | 67 / 39 / 33 | 65 / 34 / 35 | -2 / -5 / +2 |
| song_name | 1 / 10 / 5 | 2 / 11 / 4 | +1 / +1 / -1 |
| time | 45 / 32 / 31 | 48 / 29 / 28 | +3 / -3 / -3 |
| timeofday | 13 / 5 / 4 | 12 / 1 / 5 | -1 / -4 / +1 |
| transport_agency | 0 / 1 / 0 | 0 / 0 / 0 | +0 / -1 / +0 |
| transport_type | 18 / 5 / 18 | 18 / 4 / 18 | +0 / -1 / +0 |
| **sum, revised types** | 424 / 367 / 333 | 429 / 337 / 328 | +5 / -30 / -5 |

The registered K2 / K3 / K4 / risk classes (`registered-facts-v1.json` `fold_a_offline`, counted there on the
AGREE arm) re-read on both sealed arms (items; rows touched in parentheses where the estimate reports them):

| class | A/A | arm | delta |
| --- | ---: | ---: | ---: |
| K2 omission, gold value listed | 85 | 83 | -2 |
| K2 wrong filler, gold listed and prediction not | 12 | 9 | -3 |
| K2 rows touched | (92) | (88) | (-4) |
| K3 over-emission of a usually-untagged value | 4 (4) | 7 (7) | +3 |
| K4 containment, wrong filler | 70 | 67 | -3 |
| K4 span rule would fix | 4 (4) | 5 (5) | +1 |
| risk: exact TP on a usually-untagged value | 2 | 2 | 0 |
| risk: listed value spoken, untagged in gold | 43 (42) | 42 (41) | -1 |

The K2 omissions whose gold value the conventions list move 85 -> 83; the K3 over-emission risk class moves
4 -> 7.

## 7. Tokens and cost

| quantity | A/A | arm | arm - A/A |
| --- | ---: | ---: | ---: |
| contacts | 4,393 | 4,377 | -16 |
| prompt tokens per row | 35,061.4 | 38,590.4 | +3,529.0 |
| prefilled tokens per row | 8,762.3 | 9,945.0 | +1,182.7 |
| completion tokens per row | 245.9 | 242.1 | -3.8 |
| GPU-h per 1,080 rows | 1.7417 | 1.9059 | +0.1643 |

| role | contacts A/A / arm | prompt tokens per contact A/A -> arm | delta | prefilled per contact delta |
| --- | --- | --- | ---: | ---: |
| Perception | 1,080 / 1,080 | 3,598.4 -> 3,598.4 | 0.0 | 0.0 |
| Solver | 1,109 / 1,103 | 10,228.3 -> 11,436.1 | **+1,207.8** | +1,198.2 |
| Reviewer | 1,109 / 1,103 | 10,203.6 -> 11,411.0 | +1,207.4 | -0.4 |
| Planner | 1,095 / 1,091 | 10,338.9 -> 11,540.8 | +1,201.9 | -1.1 |

The registered `token_cost` projected +724.5 tokens per Solver contact (mean; max 1,274.3) and +2,218.0 per row,
at 5.0067 characters per token measured on the AGREE Solver; the realised delta is +1,207.8 per Solver contact
and +3,529.0 prompt tokens per row. This note does not decompose the difference. No contact compacted.

Frontier row: SLU-F1 +0.7930 pp and intent -0.0926 pp at +1,182.7 prefilled tokens per row and +0.1643 GPU-h
per 1,080 rows.

## Coordinator verdict (Fable 5.1, 2026-09-28)

**NOT ADMITTED (neutral by width) -- re-registered as the first cell of the same-flight supply-variant
instrument.** Against the shared wave A/A, official SLU-F1 (primary for this cell) +0.79 [-0.56, +2.12]
holds its no-harm margin (-0.56 >= -1.2485) but sits below the M4b analogue's lower end (1.3285) and far
below the 2.5 pp cross-flight floor. The intent guard -0.09 [-1.02, +0.83] misses its margin (0.9943) by
0.024 pp, under one row's step (0.0926), so by the registered rule the cell is in the residual branch:
neither no-harm nor harm is shown. The entity-class movement (SPURIOUS -29, BOUNDARY -12, MISSING +14,
WRONG-TYPE -4; FP 506 -> 461) is the direction the do-not-tag and span conventions were built for. The cost
(+3,529 prompt tokens per row, +1,207.8 per Solver contact against +724.5 registered, +0.1643 GPU-h per
1,080 rows) is above its registration. W4 does not enter COMP-2 and is not an enabler.

Because its plausible effect (about 0.8 pp SLU-F1) is exactly the size the cross-flight design cannot read
and the same-flight supply-variant design can (about 0.7 pp at n = 200;
[docs/superpowers/specs/2026-09-27-same-flight-supply-variant-instrument-design.md](../superpowers/specs/2026-09-27-same-flight-supply-variant-instrument-design.md),
owner decision 172), the coordinator re-registers W4's slot conventions as the **first real cell of that
instrument's phase 1**: Solver-local columns with an in-flight twin arm; base = the AGREE arm bytes; arm A =
the AGREE Solver supply; arm B = the W4 conventions; twin = a replicate of A; `arm_visits: "first"`; claim
`"nominated"` only. The agent's numbers above are unchanged.
