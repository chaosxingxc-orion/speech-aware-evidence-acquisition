# The bad-case bank of the locked SLURP v2.0 plan

Date: 2026-09-24. Recipe `slurp-plan-bad-case-bank-v1`, schema `saea-slurp-plan-bad-case-bank-v1`, run id `SAEA-SLURP-PLAN-BAD-CASE-BANK-V1`. A model-free read: zero model, tokenizer, encoder, ASR, scorer, embedder, server, network, GPU and paid-API contacts.

Owner directive of 2026-09-24: analyse the bad cases first, because a training-free RL gain comes from rolling out variations of prompts, data and content construction over an optimisation space, not from appending advice text. This note is that inventory. It types every row of the locked plan on two rosters, counts the mass each type carries, states which types survive the run-to-run noise of a request-identical replicate, says which the plan already repaired against the bare core, and gives each type a set of RUNTIME-OBSERVABLE signatures -- things a rollout may condition on without gold.

A DIAGNOSTIC, never a gate. It decides no cell, admits no mechanism, releases no store, authorises no flight and states no effectiveness, superiority or generalisation claim. TRAIN Fold A and DEV-2000-ADDED numbers are development numbers (owner decisions 28 and 86) and are never a test claim.

No utterance text, transcript, delivered text, gold filler, predicted filler or knowledge content appears anywhere below. Every cell is a label, a slot TYPE name, an identifier, a count, a share, a shape statistic or a hash. Gold is used offline as a scoring key exactly as `core.scoring_batch` uses it.

## 0. Inputs and identity

| Roster | Rows | Split role | Split identity | Arm | Run id | Study commit | Official SLU / intent |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| TRAIN Fold A (construction roster, 1,080 rows) | 1080 | discovery | `61b0f0625497` | PLAN | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1` | `e367a6296d` | 63.63 / 82.22 |
| TRAIN Fold A (construction roster, 1,080 rows) | 1080 | discovery | `61b0f0625497` | PLANR | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-REPLICATE-V1` | `e367a6296d` | 63.80 / 82.50 |
| TRAIN Fold A (construction roster, 1,080 rows) | 1080 | discovery | `61b0f0625497` | DIRECT | `SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-SOURCE-RECOVERY-V1` | `f3189ce266` | 33.89 / 73.70 |
| DEV-2000-ADDED (fresh roster, 1,000 rows) | 1000 | dev | `ee6c43cd4dd8` | PLAN | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1` | `54f569c62b` | 65.40 / 76.60 |
| DEV-2000-ADDED (fresh roster, 1,000 rows) | 1000 | dev | `ee6c43cd4dd8` | PLANR | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-REPLICATE-V1` | `a9b48dfc2f` | 65.15 / 76.80 |
| DEV-2000-ADDED (fresh roster, 1,000 rows) | 1000 | dev | `ee6c43cd4dd8` | DIRECT | `SAEA-SLURP-DIRECT-MAX512-DEV2000-ADDED-V1` | `54f569c62b` | 38.09 / 61.70 |

Every arm's sealed per-sample rows reproduce its own sealed official pooled SLU-F1 and span-F1 to 1e-6 before any table below is built, and every row's derived per-slot-TYPE exact decomposition reproduces that row's sealed `slot_f1_exact_{tp,fp,fn}` exactly. The PLAN arm's transition-derived slot-contract supply was checked row by row against the sealed `phase_supply.candidate_selections` receipt of the same flight; disagreements would have refused the read.

| Artefact | sha256 |
| --- | --- |
| train-fold-a plan outputs.jsonl | `2dcaa925ab7dad77` |
| train-fold-a plan scores.json | `9f3047fa77a868cb` |
| train-fold-a planr outputs.jsonl | `17f0bc0278441444` |
| train-fold-a planr scores.json | `8083795d1c5a6698` |
| train-fold-a direct outputs.jsonl | `5c182ddfc81effe2` |
| train-fold-a direct scores.json | `7840a959fe4f4392` |
| train-fold-a PLAN phases.json | `7cac358a39c446c7` |
| train-fold-a PLAN flight-receipts.json | `687b4081b659a1ad` |
| train-fold-a roster receipt | `1fe7908c31396774` |
| train-fold-a gold split metadata | `4a05a3de6c7f028a` |
| dev2000-added plan outputs.jsonl | `41ebcea4d13ef779` |
| dev2000-added plan scores.json | `1ac4402afce13528` |
| dev2000-added planr outputs.jsonl | `674e2c08f362386b` |
| dev2000-added planr scores.json | `81ae9b49620f9086` |
| dev2000-added direct outputs.jsonl | `406f5a5878012d90` |
| dev2000-added direct scores.json | `847d932be41737f0` |
| dev2000-added PLAN phases.json | `7853313714c58b43` |
| dev2000-added PLAN flight-receipts.json | `3fa30daa31021622` |
| dev2000-added roster receipt | `f78dd8ad2894b1fd` |
| dev2000-added gold split metadata | `00d346b183ecc2d1` |
| train-exemplars snapshot | `fcb5506c63653abe` |
| slot-contracts snapshot | `a48ed83eb7878e9e` |

## 1. Row-level error taxonomy of the locked plan

Seven exclusive classes, attributed in order, so a malformed delivery is never also counted as an intent error and an intent error is never also counted as an entity error. `INTENT-UNCOVERED` means Perception's own candidate list never contained the gold intent (a COVERAGE failure of the observation stage); `INTENT-COVERED` means it did and the Solver still delivered another (a SELECTION failure). The two need different rollouts.

| Class | TRAIN Fold A | DEV-2000-ADDED |
| --- | ---: | ---: |
| MALFORMED | 1 (0.1 %) | 2 (0.2 %) |
| INTENT-UNCOVERED | 130 (12.0 %) | 169 (16.9 %) |
| INTENT-COVERED | 61 (5.6 %) | 63 (6.3 %) |
| ENTITY-FN-ONLY | 84 (7.8 %) | 65 (6.5 %) |
| ENTITY-FP-ONLY | 131 (12.1 %) | 108 (10.8 %) |
| ENTITY-MIXED | 193 (17.9 %) | 195 (19.5 %) |
| CORRECT | 480 (44.4 %) | 398 (39.8 %) |

### 1a. Intent errors: coverage against selection

| Roster | Intent-error rows | Covered (selection failure) | Uncovered (coverage failure) | Within scenario | Distinct gold -> delivered pairs |
| --- | ---: | ---: | ---: | ---: | ---: |
| train-fold-a | 191 | 61 | 130 | 55 | 137 |
| dev2000-added | 232 | 63 | 169 | 50 | 132 |

Where the gold intent sat in Perception's FIRST candidate list (rank 0 = absent). The right-hand block is the same statistic on the rows the plan got right, which is what makes the left-hand block readable: rank 1 on a correct row is the normal case.

| Roster | Gold rank on intent-error rows | Gold rank on intent-correct rows |
| --- | --- | --- |
| train-fold-a | 0: 130, 1: 5, 2: 43, 3: 13 | 0: 7, 1: 845, 2: 28, 3: 8 |
| dev2000-added | 0: 169, 1: 1, 2: 47, 3: 15 | 0: 9, 1: 733, 2: 20, 3: 4 |

#### Top confusion pairs -- TRAIN Fold A (construction roster, 1,080 rows)

| Gold -> delivered | Rows | Share of intent errors | Within scenario | Covered / uncovered |
| --- | ---: | ---: | --- | --- |
| `takeaway_order` -> `takeaway_query` | 7 | 3.7 % | yes | 1 / 6 |
| `general_quirky` -> `qa_factoid` | 6 | 3.1 % | no | 2 / 4 |
| `audio_volume_other` -> `audio_volume_up` | 4 | 2.1 % | yes | 3 / 1 |
| `calendar_query` -> `recommendation_events` | 4 | 2.1 % | no | 2 / 2 |
| `general_quirky` -> `general_joke` | 4 | 2.1 % | yes | 0 / 4 |
| `general_quirky` -> `audio_volume_up` | 3 | 1.6 % | no | 0 / 3 |
| `general_quirky` -> `news_query` | 3 | 1.6 % | no | 0 / 3 |
| `general_quirky` -> `qa_definition` | 3 | 1.6 % | no | 0 / 3 |
| `music_query` -> `music_likeness` | 3 | 1.6 % | yes | 3 / 0 |
| `news_query` -> `audio_volume_up` | 3 | 1.6 % | no | 0 / 3 |
| `qa_factoid` -> `recommendation_locations` | 3 | 1.6 % | no | 1 / 2 |
| `recommendation_locations` -> `takeaway_query` | 3 | 1.6 % | no | 1 / 2 |
| `social_query` -> `news_query` | 3 | 1.6 % | no | 2 / 1 |
| `transport_ticket` -> `transport_query` | 3 | 1.6 % | yes | 0 / 3 |
| `audio_volume_mute` -> `audio_volume_up` | 2 | 1.0 % | yes | 2 / 0 |

#### Top confusion pairs -- DEV-2000-ADDED (fresh roster, 1,000 rows)

| Gold -> delivered | Rows | Share of intent errors | Within scenario | Covered / uncovered |
| --- | ---: | ---: | --- | --- |
| `calendar_query` -> `recommendation_events` | 10 | 4.3 % | no | 4 / 6 |
| `general_quirky` -> `qa_factoid` | 10 | 4.3 % | no | 1 / 9 |
| `calendar_set` -> `alarm_set` | 6 | 2.6 % | no | 4 / 2 |
| `calendar_query` -> `alarm_query` | 5 | 2.2 % | no | 3 / 2 |
| `general_quirky` -> `qa_definition` | 5 | 2.2 % | no | 2 / 3 |
| `play_music` -> `music_likeness` | 5 | 2.2 % | no | 4 / 1 |
| `play_music` -> `music_query` | 5 | 2.2 % | no | 2 / 3 |
| `calendar_query` -> `calendar_set` | 4 | 1.7 % | yes | 3 / 1 |
| `calendar_set` -> `calendar_query` | 4 | 1.7 % | yes | 3 / 1 |
| `general_quirky` -> `general_joke` | 4 | 1.7 % | yes | 0 / 4 |
| `general_quirky` -> `weather_query` | 4 | 1.7 % | no | 0 / 4 |
| `play_music` -> `play_radio` | 4 | 1.7 % | yes | 4 / 0 |
| `qa_factoid` -> `music_query` | 4 | 1.7 % | no | 1 / 3 |
| `qa_factoid` -> `qa_definition` | 4 | 1.7 % | yes | 2 / 2 |
| `qa_factoid` -> `recommendation_events` | 4 | 1.7 % | no | 1 / 3 |

### 1b. Entity errors on intent-correct rows

The class split counts INTENT-CORRECT rows only; the two right-hand columns give the roster's WHOLE official FP / FN mass, which also includes the entity defects sitting underneath the intent errors of section 1a. Every per-TYPE and per-component table below is a decomposition of that whole mass, so its shares sum over the roster and are directly comparable with the 2026-09-16 handoff report.

| Roster | FN-only | FP-only | Mixed | Entity-error rows | FP / FN on those rows | Whole-roster span FP | Whole-roster span FN |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| train-fold-a | 84 | 131 | 193 | 408 | 382 / 335 | 492 | 414 |
| dev2000-added | 65 | 108 | 195 | 368 | 350 / 311 | 479 | 426 |

The four loss components of the unmatched remainder, decomposed exactly as the 2026-09-16 handoff report decomposed the released anchor, so the two are comparable. A same-type pair and a type swap each consume one FP and one FN, so their share of the FP+FN mass counts two units per pair.

| Roster | Same-type filler distance | Equal-filler type swap | Over-emission (spurious) | Omission (nothing of that type) |
| --- | --- | --- | --- | --- |
| train-fold-a | 168 pairs, 37.1 % | 20 pairs, 4.4 % | 304, 33.6 % | 226, 24.9 % |
| dev2000-added | 159 pairs, 35.1 % | 34 pairs, 7.5 % | 286, 31.6 % | 233, 25.7 % |

#### FN and FP by slot TYPE -- TRAIN Fold A (construction roster, 1,080 rows)

| Slot TYPE | FN | FN share | FP | FP share | FP on rows whose gold carries no entity |
| --- | ---: | ---: | ---: | ---: | ---: |
| `date` | 70 | 16.9 % | 30 | 6.1 % | 7 |
| `business_name` | 34 | 8.2 % | 41 | 8.3 % | 6 |
| `place_name` | 35 | 8.5 % | 40 | 8.1 % | 14 |
| `food_type` | 23 | 5.6 % | 38 | 7.7 % | 15 |
| `time` | 30 | 7.2 % | 31 | 6.3 % | 4 |
| `person` | 23 | 5.6 % | 30 | 6.1 % | 8 |
| `event_name` | 18 | 4.3 % | 23 | 4.7 % | 8 |
| `media_type` | 19 | 4.6 % | 18 | 3.7 % | 8 |
| `business_type` | 14 | 3.4 % | 13 | 2.6 % | 2 |
| `device_type` | 5 | 1.2 % | 19 | 3.9 % | 15 |
| `order_type` | 18 | 4.3 % | 3 | 0.6 % | 0 |
| `list_name` | 6 | 1.4 % | 14 | 2.8 % | 10 |
| `general_frequency` | 5 | 1.2 % | 14 | 2.8 % | 6 |
| `house_place` | 5 | 1.2 % | 13 | 2.6 % | 8 |

#### FN and FP by slot TYPE -- DEV-2000-ADDED (fresh roster, 1,000 rows)

| Slot TYPE | FN | FN share | FP | FP share | FP on rows whose gold carries no entity |
| --- | ---: | ---: | ---: | ---: | ---: |
| `date` | 74 | 17.4 % | 41 | 8.6 % | 5 |
| `event_name` | 56 | 13.1 % | 45 | 9.4 % | 7 |
| `person` | 35 | 8.2 % | 55 | 11.5 % | 15 |
| `place_name` | 22 | 5.2 % | 27 | 5.6 % | 14 |
| `time` | 25 | 5.9 % | 17 | 3.5 % | 2 |
| `definition_word` | 8 | 1.9 % | 30 | 6.3 % | 21 |
| `currency_name` | 11 | 2.6 % | 20 | 4.2 % | 8 |
| `media_type` | 17 | 4.0 % | 13 | 2.7 % | 6 |
| `player_setting` | 14 | 3.3 % | 11 | 2.3 % | 4 |
| `weather_descriptor` | 13 | 3.1 % | 12 | 2.5 % | 4 |
| `artist_name` | 12 | 2.8 % | 12 | 2.5 % | 1 |
| `device_type` | 8 | 1.9 % | 16 | 3.3 % | 5 |
| `radio_name` | 10 | 2.3 % | 11 | 2.3 % | 1 |
| `joke_type` | 4 | 0.9 % | 16 | 3.3 % | 7 |

Over-emission on rows whose gold carries no entity at all:

| Roster | Rows with empty gold | Of those, emitting entities | Share | Entities emitted |
| --- | ---: | ---: | ---: | ---: |
| train-fold-a | 414 | 172 | 41.5 % | 195 |
| dev2000-added | 314 | 152 | 48.4 % | 166 |

### 1c. Same-type filler mismatch -- SHAPE only

`repair_rung` names the cheapest surface projection that would have made the two fillers equal, on the A1 projection audit's own rungs: `case-whitespace`, `punctuation`, `meridiem`, or `none` when no surface rung reaches it. A rung that is not `none` is a RENDERING defect the USE axis can normalise; `none` is an observation or resolution defect that only a different OBS or SUPPLY construction can reach.

| Roster | Pairs | case-whitespace | punctuation | meridiem | none | Boundary containment |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train-fold-a | 168 | 0 | 4 | 0 | 164 | 77 |
| dev2000-added | 159 | 0 | 1 | 0 | 158 | 77 |

| Roster | Normalised edit-distance buckets | Gold side carries a digit / ordinal / relative form |
| --- | --- | --- |
| train-fold-a | (0, 0.20]: 46, (0.20, 0.50]: 69, (0.50, 0.80]: 34, (0.80, 1.00]: 15, 0 (equal after folding): 4 | 0 / 4 / 8 |
| dev2000-added | (0, 0.20]: 31, (0.20, 0.50]: 69, (0.50, 0.80]: 39, (0.80, 1.00]: 19, 0 (equal after folding): 1 | 0 / 6 / 19 |

| Roster | Token-count delta (predicted minus gold, clipped to +-3) | Top slot TYPEs by pairs |
| --- | --- | --- |
| train-fold-a | -3: 1, -2: 12, -1: 47, 0: 60, 1: 42, 2: 2, 3: 4 | `business_name` 24, `date` 19, `time` 18, `place_name` 16, `food_type` 14, `person` 13, `event_name` 9, `business_type` 5 |
| dev2000-added | -3: 2, -2: 12, -1: 43, 0: 49, 1: 46, 2: 3, 3: 4 | `date` 23, `person` 23, `event_name` 15, `place_name` 9, `currency_name` 8, `radio_name` 8, `time` 8, `artist_name` 7 |

### 1d. Equal-filler type swap, and the disposition rows

| Roster | Top swaps (predicted TYPE <- gold TYPE) |
| --- | --- |
| train-fold-a | `food_type` <- `ingredient` 2, `time` <- `date` 2, `artist_name` <- `music_genre` 1, `artist_name` <- `person` 1, `business_name` <- `person` 1, `business_type` <- `place_name` 1, `currency_name` <- `business_name` 1, `date` <- `time` 1 |
| dev2000-added | `person` <- `relation` 6, `date` <- `time` 4, `event_name` <- `meal_type` 3, `device_type` <- `house_place` 2, `general_frequency` <- `date` 2, `time` <- `date` 2, `artist_name` <- `app_name` 1, `artist_name` <- `person` 1 |

Disposition rows. The locked plan sets `max_revisions = 1`, so a row with an executed revision has spent its whole revision budget; that column is the revision-limit column.

| Roster | Malformed | Abstained | Executed its single allowed revision | Emitted no entity at all |
| --- | ---: | ---: | ---: | ---: |
| train-fold-a | 1 | 1 | 38 | 302 |
| dev2000-added | 2 | 2 | 27 | 214 |

### 1e. The supply's own composition, against the rows it has to serve

The released `train-exemplars` pool is entity-bearing BY CONSTRUCTION. Against a roster where a large minority of rows carry no gold entity at all, the supply therefore never shows the Solver a single example of the correct empty answer. This is a property of the constructed content, not of the model, and it is exactly the kind of thing a construction rollout can vary.

| Exemplar pool | Values | Carrying no entity | Entity-count spread | Distinct intents |
| --- | ---: | ---: | --- | ---: |
| `train-exemplars` (size-pool-annotated-exemplars) | 9354 | 0 | 1: 7082, 2: 1645, 3: 478, 4: 130, 5: 13, 6: 6 | 60 |

| Roster | Rows whose gold carries no entity | Share of the roster |
| --- | ---: | ---: |
| train-fold-a | 414 | 38.3 % |
| dev2000-added | 314 | 31.4 % |

## 2. Stability classes: PLAN against its request-identical replicate

PLANr re-flew the identical requests. A row the two arms disagree on is inside the roster's own run-to-run noise: a rollout that only moves FLIPPING rows has moved nothing that will replicate. STABLE-WRONG is the optimisation target.

| Roster | Axis | STABLE-RIGHT | STABLE-WRONG | FLIPPING | Flipping share |
| --- | --- | ---: | ---: | ---: | ---: |
| train-fold-a | intent | 876 | 177 | 27 | 2.5 % |
| train-fold-a | entity | 499 | 488 | 93 | 8.6 % |
| train-fold-a | joint | 439 | 563 | 78 | 7.2 % |
| dev2000-added | intent | 750 | 216 | 34 | 3.4 % |
| dev2000-added | entity | 440 | 483 | 77 | 7.7 % |
| dev2000-added | joint | 363 | 571 | 66 | 6.6 % |

Class composition of the STABLE-WRONG set on the joint axis (intent AND entities right in both arms is STABLE-RIGHT; neither in either is STABLE-WRONG). This is the bank proper: the mass a rollout must move.

| Roster | MALFORMED | INTENT-UNCOVERED | INTENT-COVERED | ENTITY-FN-ONLY | ENTITY-FP-ONLY | ENTITY-MIXED |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train-fold-a | 0 | 127 | 57 | 72 | 120 | 187 |
| dev2000-added | 1 | 165 | 60 | 60 | 95 | 190 |

The same composition for the FLIPPING rows, i.e. the noise band's own shape:

| Roster | MALFORMED | INTENT-UNCOVERED | INTENT-COVERED | ENTITY-FN-ONLY | ENTITY-FP-ONLY | ENTITY-MIXED | CORRECT |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train-fold-a | 1 | 3 | 4 | 12 | 11 | 6 | 41 |
| dev2000-added | 1 | 4 | 3 | 5 | 13 | 5 | 35 |

## 3. What the plan already fixed, and what it never touched

The bare core is the `direct-only` arm flown on the same roster, the same split identity and the same serving geometry -- one contact, no Perception, no exemplar supply, no slot contracts, no review loop. Its two intent classes collapse to `INTENT-WRONG` because it has no candidate list to be covered by.

| Roster | Direct SLU / intent | PLAN SLU / intent | Rows repaired | Rows broken | Net |
| --- | --- | --- | ---: | ---: | ---: |
| train-fold-a | 33.89 / 73.70 | 63.63 / 82.22 | 240 | 89 | +151 |
| dev2000-added | 38.09 / 61.70 | 65.40 / 76.60 | 235 | 70 | +165 |

#### Direct class -> PLAN class -- TRAIN Fold A (construction roster, 1,080 rows)

| Direct class | Rows | MALFORMED | INTENT-UNCOVERED | INTENT-COVERED | ENTITY-FN-ONLY | ENTITY-FP-ONLY | ENTITY-MIXED | CORRECT |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| INTENT-WRONG | 284 | 0 | 94 | 37 | 12 | 37 | 40 | 64 |
| ENTITY-FN-ONLY | 265 | 0 | 15 | 5 | 61 | 5 | 66 | 113 |
| ENTITY-FP-ONLY | 28 | 0 | 1 | 0 | 0 | 24 | 0 | 3 |
| ENTITY-MIXED | 174 | 1 | 7 | 6 | 11 | 7 | 82 | 60 |
| CORRECT | 329 | 0 | 13 | 13 | 0 | 58 | 5 | 240 |

#### Direct class -> PLAN class -- DEV-2000-ADDED (fresh roster, 1,000 rows)

| Direct class | Rows | MALFORMED | INTENT-UNCOVERED | INTENT-COVERED | ENTITY-FN-ONLY | ENTITY-FP-ONLY | ENTITY-MIXED | CORRECT |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MALFORMED | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| INTENT-WRONG | 382 | 0 | 140 | 44 | 19 | 40 | 51 | 88 |
| ENTITY-FN-ONLY | 196 | 1 | 8 | 4 | 37 | 5 | 44 | 97 |
| ENTITY-FP-ONLY | 22 | 0 | 0 | 2 | 0 | 17 | 0 | 3 |
| ENTITY-MIXED | 166 | 1 | 8 | 5 | 8 | 5 | 92 | 47 |
| CORRECT | 233 | 0 | 13 | 8 | 1 | 41 | 7 | 163 |

Rows that entered the plan in a bad class and left it in the SAME bad class are the ones the review loop, the exemplar supply and the slot store never reached. They are where a new construction has to act, because every module the plan already carries has had its chance at them.

| Roster | MALFORMED | INTENT-WRONG | ENTITY-FN-ONLY | ENTITY-FP-ONLY | ENTITY-MIXED |
| --- | ---: | ---: | ---: | ---: | ---: |
| train-fold-a | 0 | 0 | 61 | 24 | 82 |
| dev2000-added | 0 | 0 | 37 | 17 | 92 |

## 4. Runtime-observable signatures of each bad class

Every signature below is available to a policy at the moment it runs, without gold: it comes from Perception's own state, the supply the episode carried, the Planner's route, the deliver normaliser's receipt, the carrier metadata and the response itself. The reference column is the STABLE-RIGHT rows of the same roster. `lift` is the class value minus the reference value in the signature's own units -- a univariate separation, not a fitted model. A signature with a large lift is a gate a rollout can actually apply.

### TRAIN Fold A (construction roster, 1,080 rows)

| Signature | reference STABLE-RIGHT | MALFORMED (n=1) | INTENT-UNCOVERED (n=130) | INTENT-COVERED (n=61) | ENTITY-FN-ONLY (n=84) | ENTITY-FP-ONLY (n=131) | ENTITY-MIXED (n=193) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Perception candidates proposed (1-3) | 2.74 | 3.00 (+0.26) | 2.86 (+0.12) | 2.67 (-0.07) | 2.77 (+0.04) | 2.72 (-0.02) | 2.63 (-0.11) |
| distinct candidate distinctions | 2.72 | 3.00 (+0.28) | 2.75 (+0.02) | 2.61 (-0.12) | 2.75 (+0.03) | 2.70 (-0.02) | 2.62 (-0.10) |
| candidates share one distinction | 0.91 | 0.00 (-0.91) | 6.15 (+5.24) | 3.28 (+2.37) | 1.19 (+0.28) | 0.76 (-0.15) | 0.52 (-0.39) |
| distinct scenarios among the candidates | 1.80 | 1.00 (-0.80) | 2.31 (+0.51) | 1.84 (+0.04) | 2.00 (+0.20) | 1.95 (+0.15) | 1.82 (+0.02) |
| delivered intent was a candidate | 99.09 | 0.00 (-99.09) | 95.38 (-3.70) | 96.72 (-2.37) | 100.00 (+0.91) | 98.47 (-0.62) | 99.48 (+0.39) |
| rank of the delivered intent (0 = off-list) | 1.02 | 0.00 (-1.02) | 1.08 (+0.07) | 1.07 (+0.05) | 1.02 (+0.01) | 1.13 (+0.11) | 1.04 (+0.02) |
| exemplars delivered to the Solver | 20.00 | 20.00 (+0.00) | 20.00 (+0.00) | 20.00 (+0.00) | 20.00 (+0.00) | 20.00 (+0.00) | 20.00 (+0.00) |
| share of exemplars whose intent is candidate 1 | 0.70 | 0.90 (+0.20) | 0.20 (-0.49) | 0.22 (-0.48) | 0.75 (+0.05) | 0.60 (-0.10) | 0.72 (+0.02) |
| share of exemplars carrying no entity | 0.00 | 0.00 (+0.00) | 0.00 (+0.00) | 0.00 (+0.00) | 0.00 (+0.00) | 0.00 (+0.00) | 0.00 (+0.00) |
| share of supplied contract types an exemplar shows | 0.41 | 0.55 (+0.14) | 0.37 (-0.03) | 0.47 (+0.06) | 0.45 (+0.04) | 0.40 (-0.00) | 0.43 (+0.02) |
| slot contracts delivered to the Solver | 11.55 | 11.00 (-0.55) | 12.42 (+0.86) | 11.39 (-0.16) | 12.60 (+1.04) | 11.98 (+0.43) | 12.34 (+0.79) |
| the date contract was supplied | 88.15 | 100.00 (+11.85) | 95.38 (+7.23) | 81.97 (-6.19) | 94.05 (+5.89) | 87.02 (-1.13) | 94.30 (+6.15) |
| the time contract was supplied | 86.79 | 100.00 (+13.21) | 81.54 (-5.25) | 77.05 (-9.74) | 96.43 (+9.64) | 77.86 (-8.93) | 87.05 (+0.26) |
| the Planner routed REVISE at least once | 1.59 | 0.00 (-1.59) | 8.46 (+6.87) | 6.56 (+4.96) | 0.00 (-1.59) | 7.63 (+6.04) | 3.11 (+1.51) |
| revisions executed | 0.02 | 0.00 (-0.02) | 0.08 (+0.07) | 0.07 (+0.05) | 0.00 (-0.02) | 0.08 (+0.06) | 0.03 (+0.02) |
| Reviewer visits | 1.00 | 0.00 (-1.00) | 1.08 (+0.08) | 1.07 (+0.06) | 0.99 (-0.02) | 1.07 (+0.06) | 1.02 (+0.02) |
| the deliver normaliser changed the answer | 5.92 | 0.00 (-5.92) | 7.69 (+1.77) | 13.11 (+7.19) | 8.33 (+2.41) | 13.74 (+7.82) | 16.06 (+10.14) |
| fillers the normaliser rewrote | 0.05 | 0.00 (-0.05) | 0.07 (+0.02) | 0.07 (+0.02) | 0.05 (+0.00) | 0.06 (+0.02) | 0.15 (+0.10) |
| context-fit compaction fired | 0.00 | 0.00 (+0.00) | 0.00 (+0.00) | 0.00 (+0.00) | 0.00 (+0.00) | 0.00 (+0.00) | 0.00 (+0.00) |
| far-field recording (not headset) | 48.75 | 0.00 (-48.75) | 52.31 (+3.56) | 50.82 (+2.07) | 53.57 (+4.82) | 49.62 (+0.87) | 55.44 (+6.69) |
| utterance duration, seconds | 2.65 | 3.01 (+0.36) | 2.56 (-0.09) | 2.82 (+0.17) | 2.88 (+0.23) | 2.93 (+0.28) | 3.50 (+0.85) |
| delivered response length, characters | 82.19 | 186.00 (+103.81) | 93.55 (+11.35) | 88.44 (+6.25) | 79.75 (-2.44) | 109.20 (+27.00) | 119.09 (+36.90) |
| entities the Solver emitted | 0.70 | 0.00 (-0.70) | 0.92 (+0.22) | 0.77 (+0.07) | 0.60 (-0.10) | 1.30 (+0.60) | 1.49 (+0.79) |

Three signatures are CONSTANTS of the locked plan on both rosters -- twenty exemplars on every row, zero exemplars carrying no entity, and no context-fit compaction -- so they separate nothing and cannot be gated on. They are listed because a rollout that varies the supply will make them vary, and they are the baseline it will vary from.

The strongest separators per class, ranked inside their own unit family. A relative lift on a signature whose STABLE-RIGHT reference is itself near zero -- `revisions executed` is the clear case, at 0.02 on TRAIN Fold A -- is arithmetically large and practically thin; read it beside the absolute share column, which is the honest one.

| Class | Strongest share-type separators (pp) | Strongest mean-type separators (relative) |
| --- | --- | --- |
| MALFORMED | delivered intent was a candidate -99.1; far-field recording (not headset) -48.7; the time contract was supplied +13.2 | delivered response length, characters +126 %; rank of the delivered intent (0 = off-list) -100 %; revisions executed -100 % |
| INTENT-UNCOVERED | the date contract was supplied +7.2; the Planner routed REVISE at least once +6.9; the time contract was supplied -5.2 | revisions executed +431 %; share of exemplars whose intent is candidate 1 -71 %; fillers the normaliser rewrote +52 % |
| INTENT-COVERED | the time contract was supplied -9.7; the deliver normaliser changed the answer +7.2; the date contract was supplied -6.2 | revisions executed +311 %; share of exemplars whose intent is candidate 1 -68 %; fillers the normaliser rewrote +44 % |
| ENTITY-FN-ONLY | the time contract was supplied +9.6; the date contract was supplied +5.9; far-field recording (not headset) +4.8 | revisions executed -100 %; entities the Solver emitted -15 %; distinct scenarios among the candidates +11 % |
| ENTITY-FP-ONLY | the time contract was supplied -8.9; the deliver normaliser changed the answer +7.8; the Planner routed REVISE at least once +6.0 | revisions executed +379 %; entities the Solver emitted +86 %; fillers the normaliser rewrote +34 % |
| ENTITY-MIXED | the deliver normaliser changed the answer +10.1; far-field recording (not headset) +6.7; the date contract was supplied +6.1 | fillers the normaliser rewrote +230 %; entities the Solver emitted +113 %; revisions executed +95 % |

### DEV-2000-ADDED (fresh roster, 1,000 rows)

| Signature | reference STABLE-RIGHT | MALFORMED (n=2) | INTENT-UNCOVERED (n=169) | INTENT-COVERED (n=63) | ENTITY-FN-ONLY (n=65) | ENTITY-FP-ONLY (n=108) | ENTITY-MIXED (n=195) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Perception candidates proposed (1-3) | 2.70 | 2.50 (-0.20) | 2.79 (+0.09) | 2.76 (+0.06) | 2.71 (+0.01) | 2.72 (+0.02) | 2.65 (-0.05) |
| distinct candidate distinctions | 2.67 | 2.50 (-0.17) | 2.72 (+0.05) | 2.65 (-0.02) | 2.68 (+0.00) | 2.72 (+0.05) | 2.64 (-0.03) |
| candidates share one distinction | 1.93 | 0.00 (-1.93) | 3.55 (+1.62) | 7.94 (+6.01) | 1.54 (-0.39) | 0.00 (-1.93) | 0.51 (-1.42) |
| distinct scenarios among the candidates | 1.78 | 2.00 (+0.22) | 2.28 (+0.50) | 1.92 (+0.14) | 1.82 (+0.03) | 1.69 (-0.10) | 1.78 (-0.00) |
| delivered intent was a candidate | 99.72 | 0.00 (-99.72) | 94.67 (-5.05) | 98.41 (-1.31) | 98.46 (-1.26) | 97.22 (-2.50) | 98.97 (-0.75) |
| rank of the delivered intent (0 = off-list) | 1.02 | 0.00 (-1.02) | 0.98 (-0.04) | 1.02 (-0.01) | 0.98 (-0.04) | 1.01 (-0.01) | 1.05 (+0.02) |
| exemplars delivered to the Solver | 20.00 | 20.00 (+0.00) | 20.00 (+0.00) | 20.00 (+0.00) | 20.00 (+0.00) | 20.00 (+0.00) | 20.00 (+0.00) |
| share of exemplars whose intent is candidate 1 | 0.75 | 0.65 (-0.10) | 0.21 (-0.53) | 0.25 (-0.49) | 0.75 (+0.00) | 0.69 (-0.06) | 0.75 (+0.01) |
| share of exemplars carrying no entity | 0.00 | 0.00 (+0.00) | 0.00 (+0.00) | 0.00 (+0.00) | 0.00 (+0.00) | 0.00 (+0.00) | 0.00 (+0.00) |
| share of supplied contract types an exemplar shows | 0.36 | 0.53 (+0.17) | 0.35 (-0.01) | 0.39 (+0.03) | 0.39 (+0.03) | 0.41 (+0.05) | 0.40 (+0.04) |
| slot contracts delivered to the Solver | 13.29 | 15.00 (+1.71) | 13.09 (-0.20) | 15.27 (+1.98) | 14.32 (+1.03) | 13.27 (-0.02) | 14.52 (+1.23) |
| the date contract was supplied | 92.29 | 100.00 (+7.71) | 98.22 (+5.94) | 95.24 (+2.95) | 95.38 (+3.10) | 91.67 (-0.62) | 96.41 (+4.12) |
| the time contract was supplied | 93.66 | 100.00 (+6.34) | 85.80 (-7.87) | 96.83 (+3.16) | 98.46 (+4.80) | 89.81 (-3.85) | 95.38 (+1.72) |
| the Planner routed REVISE at least once | 0.55 | 0.00 (-0.55) | 4.73 (+4.18) | 3.17 (+2.62) | 1.54 (+0.99) | 4.63 (+4.08) | 3.08 (+2.53) |
| revisions executed | 0.01 | 0.00 (-0.01) | 0.05 (+0.04) | 0.03 (+0.03) | 0.02 (+0.01) | 0.05 (+0.04) | 0.03 (+0.03) |
| Reviewer visits | 0.99 | 1.00 (+0.01) | 1.04 (+0.05) | 1.03 (+0.04) | 1.00 (+0.01) | 1.05 (+0.06) | 1.03 (+0.04) |
| the deliver normaliser changed the answer | 9.09 | 0.00 (-9.09) | 10.65 (+1.56) | 14.29 (+5.19) | 7.69 (-1.40) | 10.19 (+1.09) | 20.00 (+10.91) |
| fillers the normaliser rewrote | 0.04 | 0.00 (-0.04) | 0.05 (+0.01) | 0.10 (+0.05) | 0.02 (-0.03) | 0.05 (+0.00) | 0.15 (+0.11) |
| context-fit compaction fired | 0.00 | 0.00 (+0.00) | 0.00 (+0.00) | 0.00 (+0.00) | 0.00 (+0.00) | 0.00 (+0.00) | 0.00 (+0.00) |
| far-field recording (not headset) | 49.04 | 100.00 (+50.96) | 60.36 (+11.32) | 58.73 (+9.69) | 55.38 (+6.35) | 62.04 (+13.00) | 52.82 (+3.78) |
| utterance duration, seconds | 2.80 | 5.02 (+2.22) | 2.93 (+0.13) | 2.87 (+0.07) | 2.96 (+0.16) | 2.95 (+0.15) | 3.42 (+0.62) |
| delivered response length, characters | 91.11 | 405.00 (+313.89) | 89.51 (-1.60) | 98.29 (+7.17) | 82.82 (-8.30) | 107.19 (+16.08) | 125.18 (+34.07) |
| entities the Solver emitted | 0.93 | 0.00 (-0.93) | 0.83 (-0.10) | 1.02 (+0.09) | 0.74 (-0.19) | 1.27 (+0.34) | 1.67 (+0.74) |

Three signatures are CONSTANTS of the locked plan on both rosters -- twenty exemplars on every row, zero exemplars carrying no entity, and no context-fit compaction -- so they separate nothing and cannot be gated on. They are listed because a rollout that varies the supply will make them vary, and they are the baseline it will vary from.

The strongest separators per class, ranked inside their own unit family. A relative lift on a signature whose STABLE-RIGHT reference is itself near zero -- `revisions executed` is the clear case, at 0.02 on TRAIN Fold A -- is arithmetically large and practically thin; read it beside the absolute share column, which is the honest one.

| Class | Strongest share-type separators (pp) | Strongest mean-type separators (relative) |
| --- | --- | --- |
| MALFORMED | delivered intent was a candidate -99.7; far-field recording (not headset) +51.0; the deliver normaliser changed the answer -9.1 | delivered response length, characters +345 %; rank of the delivered intent (0 = off-list) -100 %; revisions executed -100 % |
| INTENT-UNCOVERED | far-field recording (not headset) +11.3; the time contract was supplied -7.9; the date contract was supplied +5.9 | revisions executed +759 %; share of exemplars whose intent is candidate 1 -71 %; fillers the normaliser rewrote +29 % |
| INTENT-COVERED | far-field recording (not headset) +9.7; candidates share one distinction +6.0; the deliver normaliser changed the answer +5.2 | revisions executed +476 %; fillers the normaliser rewrote +130 %; share of exemplars whose intent is candidate 1 -66 % |
| ENTITY-FN-ONLY | far-field recording (not headset) +6.3; the time contract was supplied +4.8; the date contract was supplied +3.1 | revisions executed +179 %; fillers the normaliser rewrote -63 %; entities the Solver emitted -20 % |
| ENTITY-FP-ONLY | far-field recording (not headset) +13.0; the Planner routed REVISE at least once +4.1; the time contract was supplied -3.8 | revisions executed +740 %; entities the Solver emitted +37 %; delivered response length, characters +18 % |
| ENTITY-MIXED | the deliver normaliser changed the answer +10.9; the date contract was supplied +4.1; far-field recording (not headset) +3.8 | revisions executed +458 %; fillers the normaliser rewrote +260 %; entities the Solver emitted +80 % |

## 5. The exemplar and the contract angle

On the STABLE-WRONG entity rows, what did the twenty supplied exemplars look like against the STABLE-RIGHT rows? `matched reference` re-weights the STABLE-RIGHT rows to the delivered-intent mixture of the target rows, so the contrast is not an artefact of which intents are hard.

| Roster | Rows | Measure | STABLE-WRONG entity rows | STABLE-RIGHT (plain) | STABLE-RIGHT (intent-matched) |
| --- | ---: | --- | ---: | ---: | ---: |
| train-fold-a | 379 | exemplars delivered | 20.000 | 20.000 | 20.000 |
| train-fold-a | 379 | share whose intent is candidate 1 | 0.684 | 0.699 | 0.745 |
| train-fold-a | 379 | share carrying no entity | 0.000 | 0.000 | 0.000 |
| train-fold-a | 379 | share of supplied contract TYPEs an exemplar shows | 0.421 | 0.407 | 0.410 |
| train-fold-a | 379 | slot contracts delivered | 12.385 | 11.554 | 12.423 |
| train-fold-a | 379 | share of the row's GOLD slot TYPEs that some supplied exemplar shows | 0.941 | 0.994 | -- |
| dev2000-added | 345 | exemplars delivered | 20.000 | 20.000 | 20.000 |
| dev2000-added | 345 | share whose intent is candidate 1 | 0.728 | 0.745 | 0.754 |
| dev2000-added | 345 | share carrying no entity | 0.000 | 0.000 | 0.000 |
| dev2000-added | 345 | share of supplied contract TYPEs an exemplar shows | 0.400 | 0.362 | 0.384 |
| dev2000-added | 345 | slot contracts delivered | 14.101 | 13.292 | 14.262 |
| dev2000-added | 345 | share of the row's GOLD slot TYPEs that some supplied exemplar shows | 0.953 | 0.996 | -- |

On every FN of slot TYPE `t`, was `slot-contract:t` supplied to that row at all? A supply that never mentions the slot is a SUPPLY defect a rollout can repair by changing what is constructed. A supply that mentions it and is still omitted is an OBS or USE defect, and no amount of contract text will reach it.

#### TRAIN Fold A (construction roster, 1,080 rows)

| Slot TYPE | FN | Rows with an FN of this type | Contract supplied on those rows | Share |
| --- | ---: | ---: | ---: | ---: |
| `date` | 70 | 68 | 68 | 100.0 % |
| `place_name` | 35 | 35 | 33 | 94.3 % |
| `business_name` | 34 | 33 | 31 | 93.9 % |
| `time` | 30 | 30 | 30 | 100.0 % |
| `food_type` | 23 | 22 | 22 | 100.0 % |
| `person` | 23 | 22 | 21 | 95.5 % |
| `media_type` | 19 | 19 | 19 | 100.0 % |
| `event_name` | 18 | 18 | 17 | 94.4 % |
| `order_type` | 18 | 17 | 17 | 100.0 % |
| `business_type` | 14 | 14 | 14 | 100.0 % |
| `transport_type` | 14 | 14 | 14 | 100.0 % |
| `weather_descriptor` | 10 | 9 | 8 | 88.9 % |

#### DEV-2000-ADDED (fresh roster, 1,000 rows)

| Slot TYPE | FN | Rows with an FN of this type | Contract supplied on those rows | Share |
| --- | ---: | ---: | ---: | ---: |
| `date` | 74 | 74 | 74 | 100.0 % |
| `event_name` | 56 | 54 | 52 | 96.3 % |
| `person` | 35 | 35 | 34 | 97.1 % |
| `time` | 25 | 24 | 24 | 100.0 % |
| `place_name` | 22 | 21 | 21 | 100.0 % |
| `media_type` | 17 | 17 | 16 | 94.1 % |
| `player_setting` | 14 | 14 | 10 | 71.4 % |
| `relation` | 14 | 14 | 13 | 92.9 % |
| `weather_descriptor` | 13 | 13 | 12 | 92.3 % |
| `artist_name` | 12 | 12 | 9 | 75.0 % |
| `currency_name` | 11 | 10 | 9 | 90.0 % |
| `radio_name` | 10 | 10 | 10 | 100.0 % |

## 6. Headroom: the recoverable mass of each class

An EXACT upper bound, not an estimate. A perfectly repaired row delivers gold, so every unmatched gold unit becomes a matched one and nothing spurious remains -- `tp -> tp + fn`, `fp -> 0`, `fn -> 0` at word, char and exact-span level alike -- while every other row of the roster is left exactly as flown. No rollout can exceed these numbers by repairing that class; most will reach a fraction of them. The STABLE-WRONG column is the honest target, because the rest of the class is inside the replicate's own noise.

### TRAIN Fold A (construction roster, 1,080 rows)

| Class | Rows | SLU now | SLU if fixed | SLU pp | Intent pp | STABLE-WRONG rows | SLU pp (stable-wrong only) | Intent pp (stable-wrong only) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ENTITY-MIXED | 193 | 63.63 | 81.06 | +17.43 | +0.00 | 187 | +16.65 | +0.00 |
| INTENT-UNCOVERED | 130 | 63.63 | 69.04 | +5.41 | +12.04 | 127 | +5.38 | +11.76 |
| ENTITY-FN-ONLY | 84 | 63.63 | 68.74 | +5.11 | +0.00 | 72 | +4.41 | +0.00 |
| ENTITY-FP-ONLY | 131 | 63.63 | 68.39 | +4.76 | +0.00 | 120 | +4.32 | +0.00 |
| INTENT-COVERED | 61 | 63.63 | 65.98 | +2.35 | +5.65 | 57 | +2.26 | +5.28 |
| MALFORMED | 1 | 63.63 | 63.69 | +0.06 | +0.09 | 0 | +0.00 | +0.00 |
| ALL-BAD | 600 | 63.63 | 100.00 | +36.37 | +17.78 | 563 | +34.20 | +17.04 |

### DEV-2000-ADDED (fresh roster, 1,000 rows)

| Class | Rows | SLU now | SLU if fixed | SLU pp | Intent pp | STABLE-WRONG rows | SLU pp (stable-wrong only) | Intent pp (stable-wrong only) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ENTITY-MIXED | 195 | 65.40 | 81.87 | +16.47 | +0.00 | 190 | +16.08 | +0.00 |
| INTENT-UNCOVERED | 169 | 65.40 | 72.21 | +6.82 | +16.90 | 165 | +6.68 | +16.50 |
| ENTITY-FN-ONLY | 65 | 65.40 | 69.44 | +4.04 | +0.00 | 60 | +3.77 | +0.00 |
| ENTITY-FP-ONLY | 108 | 65.40 | 68.86 | +3.47 | +0.00 | 95 | +3.06 | +0.00 |
| INTENT-COVERED | 63 | 65.40 | 68.07 | +2.67 | +6.30 | 60 | +2.62 | +6.00 |
| MALFORMED | 2 | 65.40 | 65.80 | +0.40 | +0.20 | 1 | +0.23 | +0.10 |
| ALL-BAD | 602 | 65.40 | 100.00 | +34.60 | +23.40 | 571 | +33.11 | +22.60 |

## 7. Reconciliation with the earlier audits

The 2026-09-17 Phase A audits and the 2026-09-16 handoff report measured the RELEASED ANCHOR, an earlier arm on the same TRAIN Fold A roster; this bank measures the LOCKED v2.0 PLAN, which is the base every Stage-3 cell derives from. The two are expected to differ in level and to agree in structure, and they broadly do: the same four components carry the loss, same-type filler distance leads both and the equal-filler swap is a residue in both, the over-emission on reference-empty rows is unchanged in kind, and the intent-error split is still dominated by rows whose gold intent Perception never proposed. The one reordering is that over-emission has overtaken omission in the plan. The anchor column is quoted from those notes; the plan column is this read's own TRAIN Fold A number.

| Statistic | Released anchor (2026-09-16 / -17, TRAIN Fold A) | Locked plan (this read, TRAIN Fold A) |
| --- | --- | --- |
| Same-type filler distance, share of FP+FN mass | 35.04 % | 37.09 % |
| Equal-filler type swap, share of FP+FN mass | 4.65 % | 4.42 % |
| Unmatched reference (omission), share of FP+FN mass | 31.49 % | 24.94 % |
| Unmatched prediction (over-emission), share of FP+FN mass | 28.82 % | 33.55 % |
| Reference-empty rows emitting entities | 184 of 414 | 172 of 414 |
| Intent errors: gold never a candidate / covered but wrong | 143 / 95 (238 total) | 130 / 61 (191 total) |
| Correct-intent rows with non-exact entities: FN-only / FP-only / mixed | 127 / 134 / 264 | 84 / 131 / 193 |

One difference is worth naming, descriptively and without attributing a cause: the covered-but-wrong rows are a SMALLER share of the plan's intent errors than of the anchor's (31.9 % against 39.9 %), so what remains is more sharply a coverage problem -- Perception's list, rather than the Solver's choice inside it. The two arms differ in several respects at once (the tool-free B1 base, the v2 slot store, the deliver normaliser), so no single module can be credited from this comparison; that is what a rollout is for.

## 8. What this read does not say

It states no effectiveness, superiority or generalisation claim, admits no module, releases no store and authorises no flight. The headroom column is an upper bound on a PERFECT repair of a class and is not a forecast of any rollout. The class boundaries are an attribution convention, not a causal claim: a row typed `INTENT-UNCOVERED` may also carry entity defects that the convention hides behind its first failure, and the same-type / swap / over-emission / omission split of the unmatched remainder is a heuristic decomposition, deterministic but not a statement about what the model heard. Every number is a development number on a TRAIN construction fold or on a DEV roster (owner decisions 28 and 86) and is never a test claim.

Machine-readable payload: `$SPEECHRL_DATA_DIR/analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bad-case-bank.json` (schema `saea-slurp-plan-bad-case-bank-v1`, recipe `slurp-plan-bad-case-bank-v1`); per-row typed bank `$SPEECHRL_DATA_DIR/analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl` (ids, class labels, slot TYPE names, counts and signatures only -- no text and no filler); derived per-row caches under `cache/`. Script `scripts/analysis/slurp_plan_bad_case_bank.py`.
