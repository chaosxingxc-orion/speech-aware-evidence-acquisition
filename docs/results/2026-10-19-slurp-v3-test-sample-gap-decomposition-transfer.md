# SLURP v3.0 gap decomposition on the sealed test sample, with a transfer check against DEV and Fold B
Authority: owner ruling 340; ledger row `SAEA-SLURP-TEST-SAMPLE-3010-V3-GAP-ANALYSIS-V1`. Model-free analyst read, 2026-10-18.
- Zero model, server, encoder, tokenizer or GPU contacts; no generation; read-only on the repo and the data root. Source: sealed run `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR3-THINKING-SYSTEM-V1`, scorer `slurp-slu-official-test`.
- Test gold: governed loader (`allow_heldout=True`), in memory only, filtered to the 3,010 SLURP-TEST-SAMPLE-3010-V1 ids at load; the 10,068 closure-roster rows were dropped at load, never retained or analysed. Aggregates only (counts, rates, pp, intent/scenario/slot-type names); no utterance, transcript, output or reasoning text.
- **Measurement and transfer check only.** No lever, prompt, threshold, knowledge entry or roster is selected, proposed or changed; decisions 338/339 stand as written at 347973d56; every later test-sample claim inherits this analysis as exposure.
- Files here: `gap_decomposition.py` (repo copy + TEST population, row weights, rank conversion, extended bootstrap; repo copy untouched) -> `gap-numbers-test.json` and `gap-numbers-devfb.json` (DEV/FB re-run; oracles and classes identical to the repo `gap-numbers.json`); `transfer.py` -> `test-gap-transfer.json`.
## 0. Reproduction (passed)
Post-stratified natural mixture (58 strata, population-counts-v1 weights): SLU-F1 **73.0527**, intent **86.3274**, exact match to the sealed read. Raw roster mixture: 72.70 / 86.94 (2,617 / 3,010 correct), TP 4,100, FP 1,701.79, FN 1,377.79, exact match. Per row: re-scored counts = sealed counts 3,010/3,010; parsed intent = sealed exact flag 3,010/3,010; receipt candidates = Perception state 3,010/3,010; forced-close status known 3,010/3,010.
Tables in sections 1-2 use raw roster counts, as on DEV/FB. Section 3 gives raw and post-stratified (PS) values side by side; section 4 uses PS.
## 1. Error tables (TEST, n = 3,010)
### 1.1 Intent

| class | TEST rows (pp) | DEV (pp) | FB (pp) |
| --- | ---: | ---: | ---: |
| correct | 2,617 | 845 | 922 |
| (a) gold absent from Perception's shortlist | **290 (9.63)** | 121 (12.1) | 118 (10.9) |
| a1. in the 8-entry block, dropped by Perception | 198 (6.58) | 85 | 78 |
| a2. not in the block either (retrieval miss) | 92 (3.06) | 36 | 40 |
| (b) gold on the shortlist, Solver chose wrong | **103 (3.42)** | 34 (3.4) | 40 (3.7) |
| b: Solver picked another shortlist member / went off the list | 82 / 21 | 27 / 7 | 33 / 7 |
| b: gold was at shortlist rank 1 / 2 / 3 | 39 / 56 / 8 | 12 / 17 / 5 | 19 / 17 / 4 |
| unparsed | 0 | 0 | 0 |

(a) is **73.8 %** of intent errors (DEV 78, FB 75); 286 of 393 errors (73 %) cross scenarios (DEV/FB ~75). Shortlist sizes 1/2/3: 2,406 / 437 / 167; single-candidate share **79.9 %** (DEV 85.2, FB 80.7).
Accuracy by the gold intent's shortlist position (last three rows: off-list rows by gold's position in the 8-entry block):

| gold position | TEST n / acc | DEV n / acc | FB n / acc |
| --- | --- | --- | --- |
| sole candidate | 2,188 / 99.1 % | 752 / 99.3 % | 785 / 99.2 % |
| rank 1 of 2-3 | 337 / 94.1 % | 85 / 91.8 % | 116 / 88.8 % |
| rank 2-3 | 160 / 60.0 % | 34 / 35.3 % | 51 / 58.8 % |
| off the list | 325 / 10.8 % | 129 / 6.2 % | 128 / 7.8 % |
| off-list, gold at block rank 1 | 50 / 28.0 % | 18 / 22 % | 12 / 25 % |
| off-list, gold at block rank 2-8 | 182 / 11.0 % | 74 / 4 % | 75 / 8 % |
| off-list, gold not in block | 93 / 1.1 % | 37 / 3 % | 41 / 2 % |

Error owners: `general_quirky` 60 of 91 rows wrong (55 off-list; 15 % of intent errors vs DEV/FB 22-23 %; top confusions `cooking_recipe` 11, `calendar_query` 9, `news_query` 9); then `play_audiobook` 24/71, `play_radio` 19/74 (15 to `play_music`), `play_podcasts` 18/105, `calendar_query` 17/74 and `lists_createoradd` 17/46.
### 1.2 Slots
Gold entities: 2,485. Predicted entities: 2,647. Empty-gold rows: 1,255. The "SLU pp" column is the gain if that class alone were repaired.

| class | TEST items | TEST SLU pp | DEV pp | FB pp |
| --- | ---: | ---: | ---: | ---: |
| FP, false fill on an empty-gold row | 280 (on 249 of 1,255 rows) | +3.80 | +3.00 | +3.20 |
| FP, extra slot on a non-empty row | 216 | +2.90 | +3.28 | +3.61 |
| FN, missed slot (116 non-empty rows predicted empty) | 334 | **+7.00** | +5.74 | +6.22 |
| FORMAT | 29 | +0.26 | +0.25 | +0.49 |
| BOUNDARY | 162 | +2.61 | +2.23 | +2.35 |
| NEAR | 132 | +1.83 | +1.79 | +2.05 |
| WRONG-VALUE | 79 | +2.05 | +2.38 | +2.14 |
| wrong type (54 same-value swaps, 47 related-value) | 101 | +3.58 | +3.77 | +3.58 |
| all items repaired | 1,333 | +27.30 | +25.31 | +27.26 |

Top types: MISSING `player_setting` 64, `date` 37, `personal_info` 22; SPURIOUS `place_name` 42, `person` 39, `event_name` 34, `podcast_descriptor` 32; BOUNDARY `time` 38; WRONG-TYPE `news_topic` 14, `time` 12.
### 1.3 Forced-close rows (either node hit the 3,072-token budget)
| population | rows forced | intent / SLU on them | intent / SLU on natural rows | share of intent errors | share of slot items |
| --- | ---: | --- | --- | ---: | ---: |
| TEST | 1,492 (Solver 1,219, Perception 592) | 80.6 / 68.1 | 93.1 / 80.4 | 73.5 % (289/393) | 72.1 % (965/1,333) |
| DEV | 529 | 79.4 / 69.7 | 90.2 / 82.4 | 70 % | 73 % |
| FB | 525 | 80.6 / 66.9 | 89.9 / 81.1 | 65 % | 72 % |

Perception-forced rows: intent 70.8, SLU 63.8 (DEV intent 66, FB 69). Forced rows hold 222 of the 280 empty-gold false fills.
### 1.4 By scenario (TEST)
"SLU pp" = gain if every slot item in that scenario were repaired.

| scenario | n | intent | off-shortlist / Solver-wrong errors | SLU-F1 | SLU pp at stake | empty-gold false fills |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| play | 413 | 81.6 | 46 / 30 | 60.4 | 5.39 | 73 |
| calendar | 285 | 89.8 | 22 / 7 | 76.8 | 3.17 | 18 |
| email | 236 | 91.1 | 14 / 7 | 66.0 | 2.57 | 14 |
| qa | 242 | 88.8 | 24 / 3 | 69.7 | 2.14 | 25 |
| iot | 304 | 90.5 | 21 / 8 | 74.7 | 1.67 | 20 |
| general | 175 | 65.7 | 55 / 5 | 65.5 | 0.90 | 35 |
| music | 105 | 71.4 | 21 / 9 | 30.3 | 0.89 | 19 |
| lists | 178 | 81.5 | 22 / 11 | 76.0 | 0.72 | 17 |
| other 10 scenarios (49-214 rows each) | 1,072 | 86.7-97.8 | ≤ 14 / ≤ 6 each | 65.5-92.9 | 0.2-1.2 each | 0-14 each |

Same pattern as DEV/FB: intent loss in general, play, music, lists; SLU loss in play and calendar, then email and qa.
## 2. Oracles on TEST (pp over TEST's own score)
All CIs are 95 % utterance-cluster bootstrap intervals (2,000 draws, seed 20261019, 682 prompt clusters).

| oracle | raw gain [CI95] | PS gain [CI95] |
| --- | --- | --- |
| (i) intent perfect: intent | +13.06 [+10.75, +15.61] | +13.67 [+11.18, +16.44] |
| (i) intent perfect: SLU central (upper end 78.87 raw, +6.17) | +4.13 [+2.87, +5.58] | +4.08 [+2.86, +5.52] |
| (ii) gold always on the shortlist: intent → 96.16 raw | +9.22 [+7.40, +11.31] | +9.82 [+7.77, +12.23] |
| (ii) SLU | +3.24 [+2.15, +4.52] | +3.24 [+2.15, +4.60] |
| (ii-b) gold always in the block: intent | +2.80 [+1.86, +3.89] | +2.88 [+1.82, +4.16] |
| (iii) empty-gold false fills removed: SLU | +3.80 [+2.73, +4.97] | +3.75 [+2.72, +4.98] |
| (iv) FORMAT + BOUNDARY + NEAR normalised: SLU | +4.86 [+3.81, +5.92] | +4.73 [+3.73, +5.80] |
| **(iii) + (iv) jointly**: SLU → 81.89 raw | **+9.19 [+7.71, +10.71]** | **+9.00 [+7.52, +10.51]** |
| (v) forced-close rows at natural rates: intent | +6.21 [+4.46, +7.97] | +6.09 [+4.30, +7.94] |
| (v) SLU | +7.71 [+5.07, +10.30] | +7.84 [+5.09, +10.57] |
| (v-b) Solver forced-close rows only: intent | +3.84 [+2.42, +5.24] | +3.53 [+2.13, +5.03] |

(ii)+(iii)+(iv) together: intent 96.16, SLU 81.89 (raw). (i)-central, (ii) and (v) assume repaired rows behave like rows already right (optimistic); (v) is confounded with difficulty: an upper bound, not an estimate.
## 3. Transfer: DEV vs FB vs TEST
Values are points with CI95, in pp or %. Flag rule: **OUT** if the TEST 95 % CI lies wholly outside [min(DEV, FB), max(DEV, FB)].

| quantity | DEV | FB | TEST raw | TEST PS | flag |
| --- | --- | --- | --- | --- | --- |
| SLU-F1 | 74.69 [72.51, 76.78] | 72.74 [70.52, 74.83] | 72.70 [69.86, 75.68] | 73.05 [70.23, 75.96] | in |
| intent | 84.50 [82.10, 86.93] | 85.37 [83.24, 87.59] | 86.94 [84.39, 89.25] | 86.33 [83.56, 88.82] | in |
| (a) off-shortlist errors, pp | 12.10 | 10.93 | 9.63 [7.71, 11.84] | 10.27 [8.13, 12.80] | in |
| (a1) / (a2), pp | 8.50 / 3.60 | 7.22 / 3.70 | 6.58 / 3.06 | 7.08 / 3.19 | in |
| (b) Solver-wrong, pp | 3.40 | 3.70 | 3.42 [2.43, 4.61] | 3.41 | in |
| (a) share of intent errors, % | 78.1 | 74.7 | 73.8 [66.5, 80.8] | 75.1 | in |
| single-candidate share, % | 85.2 | 80.7 | 79.9 [76.2, 83.5] | 79.3 | in |
| acc. when gold is off the list, % | 6.2 | 7.8 | 10.8 [6.4, 16.1] | 11.5 | in |
| forced-close share, % | 52.9 | 48.6 | 49.6 [46.0, 53.1] | 51.8 | in |
| intent errors on forced rows, % | 70.3 | 64.6 | 73.5 [67.4, 79.1] | 73.3 | in |
| intent on natural rows | 90.23 | 89.91 | **93.15 [90.95, 94.96]** | 92.41 [89.82, 94.49] | **OUT (raw, above); in (PS)** |
| intent / SLU on forced rows | 79.4 / 69.7 | 80.6 / 66.9 | 80.6 / 68.1 | 80.7 / 68.4 | in |
| empty-gold false-fill row rate, % | 25.5 | 20.7 | 19.8 [15.4, 24.3] | 22.9 | in |
| slot pp: FP empty / FP extra / FN | 3.00 / 3.28 / 5.74 | 3.20 / 3.61 / 6.22 | 3.80 / 2.90 / 7.00 | 3.75 / 3.22 / 6.46 | in (all CIs overlap) |
| slot pp: BOUNDARY / NEAR / WRONG-VALUE / type | 2.23 / 1.79 / 2.38 / 3.77 | 2.35 / 2.05 / 2.14 / 3.58 | 2.61 / 1.83 / 2.05 / 3.58 | 2.57 / 1.74 / 1.92 / 3.67 | in |
| (i) SLU central | +3.18 | +3.16 | +4.13 [+2.87, +5.58] | +4.08 | in |
| (ii) intent / SLU | +11.60 / +2.46 | +10.43 / +2.23 | +9.22 [+7.40, +11.31] / +3.24 [+2.15, +4.52] | +9.82 / +3.24 | in |
| (iii) / (iv) | +3.00 / +4.41 | +3.20 / +5.10 | +3.80 / +4.86 | +3.75 / +4.73 | in |
| (iii) + (iv) jointly | +7.79 | +8.78 | +9.19 [+7.71, +10.71] | +9.00 | in |
| (v) intent / SLU | +5.73 / +7.71 | +4.54 / +8.41 | +6.21 / +7.71 | +6.09 / +7.84 | in |

Transfer verdict: **the decomposition transfers.** Of the 39 tracked quantities in `test-gap-transfer.json`, exactly one is flagged: natural-row intent, raw weighting only. It is not flagged under PS.
Drift on TEST, all within CI overlap: slightly fewer off-shortlist errors; slightly more SLU mass in missed slots and empty-gold false fills; slightly larger (iii)+(iv) and (ii)-SLU oracles; equal Solver-wrong rate. The one flag follows the TEST roster's intent mixture (it disappears under PS), not a change of mechanism.
## 4. Gap shares computed on TEST itself (PS gain ÷ TEST gap)
Ours 73.05 / 86.33 (PS). Gaps SLU / intent: LauraGPT +0.40 / +1.54; SFT Qwen2-Audio-7B +3.70 / +1.80; UniverSLU-14 +6.45 / +3.97. **Caveat:** the tiers are full 13,078-row test numbers; ours is the 3,010-row sample post-stratified to the natural mixture; share CIs carry only our sampling error.

| oracle (PS gain) | share of the LauraGPT gap | share of the SFT Qwen2-Audio gap | share of the UniverSLU gap |
| --- | --- | --- | --- |
| SLU (i) central +4.08 | 1026 % | 110 % [77, 149] | 63 % [44, 86] |
| SLU (ii) +3.24 | 814 % | 88 % [58, 124] | 50 % [33, 71] |
| SLU (iii) +3.75 | 945 % | 102 % [73, 135] | 58 % [42, 77] |
| SLU (iv) +4.73 | 1191 % | 128 % [101, 157] | 73 % [58, 90] |
| SLU (iii)+(iv) +9.00 | 2266 % | 243 % [204, 284] | **140 % [117, 163]** |
| SLU (v) +7.84 | 1974 % | 212 % [138, 286] | 122 % [79, 164] |
| intent (ii) +9.82 | 636 % | 545 % [431, 679] | 247 % [196, 308] |
| intent (ii-b) +2.88 | 186 % | 160 % [101, 231] | 72 % [46, 105] |
| intent (v) +6.09 | 395 % | 338 % [238, 440] | 153 % [108, 200] |
| intent (v-b) +3.53 | 229 % | 196 % [118, 279] | 89 % [54, 127] |

Closing UniverSLU on test needs about **72 %** of the joint (iii)+(iv) SLU mass (DEV/FB note: ~83 %) and about **40 %** of the (ii) intent mass (DEV/FB: ~one third).
## 5. Does the DEV/FB ceiling estimate still hold?
**Yes. The band stands unchanged: SLU-F1 about 74.5-77.0, intent about 86.3-88.0.**
- The band was built from DEV/FB oracle masses multiplied by conversion rates measured on DEV/TRAIN folds.
- On test, every oracle mass it rests on falls inside the DEV-FB range or overlaps it within its CI.
- The structural constraints reproduce: off-shortlist Perception errors are 74 % of intent errors; the Solver rarely recovers an off-list gold (11 %); missed slots are the largest SLU mass; forced-close rows hold 73 % of intent errors.
- The band is a reachable ceiling after levers, not a current score. The current test point is 73.05 SLU, 1.45 pp below the band's floor, and 86.33 intent, exactly at its floor.
- Tier reading unchanged: LauraGPT SLU within noise, its intent only at the optimistic end; SFT Qwen2-Audio at or above the band's top; UniverSLU-14 above the method-class ceiling on both metrics.
- Nothing in this read changes a lever ranking, and no lever, threshold or design is proposed from it.
