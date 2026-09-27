# SLURP AGREE arm: where its gain, its harm and its remaining error come from

Date: 2026-09-27. Read id `SAEA-SLURP-STAGE3-AGREE-ERROR-SOURCES-V1`, recipe `slurp-agree-arm-error-sources-v1`, owner decision 163 (ANALYSIS track). **Status: DESCRIPTIVE.** A model-free read over sealed bytes on TRAIN Fold A (1,080 rows, a construction roster): zero model, server, tokenizer, encoder, embedder, network, GPU and paid-API contacts, and no official-scorer subprocess. It registers no cell, admits nothing, authorises no flight and makes no effectiveness, superiority or generalisation claim; every number is a development number (owner decisions 28 and 86). Gold is read OFFLINE on the scoring side only, through `data.slurp.load_slurp_split` on the governed TRAIN split (the path the bad-case bank and the gold-position read use), and reaches no query, key, selector, config or runtime. No utterance text, transcript, delivered answer, gold filler or predicted filler is printed or persisted: cells are ids, counts, rates, intent label names, slot TYPE names, kind names and hashes.

Driver `scripts/analysis/slurp_agree_arm_error_sources.py`; machine outputs `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-AGREE-ERROR-SOURCES-V1/` (`report.json`, `rows.jsonl`, `tables.md`, `content-sha256.json`). Every table below is quoted from `tables.md`.

## 0. Inputs and structural checks

| Arm | run id | phases sha256 | outputs sha256 | scores sha256 | intent acc |
| --- | --- | --- | --- | --- | ---: |
| A/A (w_agree 0.0) | `SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1` | `26e964aabc14` | `453a9a49340b` | `66cb7ab22bc9` | 82.50 |
| AGREE (w_agree 1.0, k 60, fuse 8-1-8) | `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` | `783299f15626` | `6a4256e09278` | `01db05fa5778` | 85.83 |
| PLAN | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1` | `7cac358a39c4` | `2dcaa925ab7d` | `9f3047fa77a8` | 82.22 |
| PLANr | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-REPLICATE-V1` | `8a334c760706` | `17f0bc027844` | `8083795d1c5a` | 82.50 |

Also read: the exemplar pool `knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json` (`fcb5506c6350`), the Fold A speech query vectors (`e7a5b2264dc6`), the flown intent-boundary store and key vectors (through the rank diagnostic's own `load_store`), and the COMP-1 centroid key file `prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl` (`16c33640151c`). Full hashes are in `report.json`.

| arm | rows | parse agrees | intent agrees with sealed exact | in-process SLU counts agree with sealed | Perception order agrees (trace) | first Solver order agrees (trace) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| aa | 1080 | 1080 | 1080 | 1080 | 1080/1080 | 1080/1080 |
| agree | 1080 | 1080 | 1080 | 1080 | 1080/1080 | 1080/1080 |
| plan | 1080 | 1080 | 1080 | 1080 | n/a | n/a |
| planr | 1080 | 1080 | 1080 | 1080 | n/a | n/a |

The offline agreement replay (written-key cosine at width 60 + 1.0 x self-excluded exemplar-intent vote share over the row's own 20 delivered exemplars) reproduces AGREE's sealed eight-entry block in order on **1080/1080** rows, so every rank quoted below for a gold entry the arm did not deliver is the arm's own arithmetic. The in-process port reproduces every sealed per-sample SLU word/char TP/FP/FN on all four arms, so the counterfactual entity repairs in section 3 are measured on the official metric's own arithmetic.

## 1. The 67 saves and 31 harms, row by row

### 1.1 The noise floor

The three sealed flights of the same plan (A/A, PLAN, PLANr) deliver byte-identical boundary blocks on all 1080 rows; they still disagree on intent on 27-33 rows per pair, and Perception's shortlist differs on 29-32 % of rows (set-level 24-28 %) under identical input.

| null pair | saves | harms | discordant | identical block rows | Perception list changed on identical block | Perception set changed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| aa-vs-plan | 15 | 18 | 33 | 1080 | 334 | 282 |
| aa-vs-planr | 14 | 14 | 28 | 1080 | 341 | 297 |
| plan-vs-planr | 15 | 12 | 27 | 1080 | 311 | 264 |

Pooled over the three pairs, by where the left arm's gold entry sat:

| left gold position | left-correct rows | harms | harm rate % | left-wrong rows | saves | save rate % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2093 | 12 | 0.57 | 31 | 12 | 38.71 |
| 2-8 | 491 | 28 | 5.70 | 226 | 20 | 8.85 |
| not delivered | 86 | 4 | 4.65 | 313 | 12 | 3.83 |

**A no-op arm would have produced about 15 harms and 15 saves on this roster** (expected null harms 14.75, Poisson 95 % [8, 23]; saves 14.79, [8, 23]). A correct row with gold at position 1 almost never flips (0.57 %); one with gold at 2-8 flips ten times as often.

### 1.2 Observed flips against the null, by what AGREE did to the gold entry

| transition A/A -> AGREE | A/A-correct rows | harms | expected null harms | null 95 % | A/A-wrong rows | saves | expected null saves | null 95 % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| demoted | 71 | **21** | 0.82 | [0, 3] | 23 | 3 | 3.83 | [1, 8] |
| dropped | 1 | 1 | 0.06 | [0, 1] | 1 | 0 | 0.09 | [0, 1] |
| identical block | 251 | 2 | 1.73 | [0, 5] | 3 | 1 | 0.56 | [0, 2] |
| never delivered | 4 | 0 | 0.19 | [0, 1] | 32 | 0 | 1.23 | [0, 4] |
| newly delivered | 23 | 1 | 1.07 | [0, 3] | 72 | **32** | 2.76 | [0, 6] |
| promoted | 135 | 1 | 7.70 | [3, 14] | 46 | **28** | 4.07 | [1, 8] |
| same position, block changed | 406 | 5 | 3.20 | [0, 7] | 12 | 3 | 2.26 | [0, 6] |

### 1.3 Saves (67)

| class | rows | gold pos A/A | gold pos AGREE | gold on list A/A | gold on list AGREE | delivered from list AGREE |
| --- | ---: | --- | --- | ---: | ---: | ---: |
| gold newly delivered | 32 | none: 32 | 1: 24, 2: 6, 3: 1, 4: 1 | 0 | 32 | 32 |
| gold promoted | 28 | 2: 10, 3: 3, 4: 3, 5: 2, 6: 2, 7: 3, 8: 5 | 1: 23, 2: 4, 3: 1 | 19 | 28 | 28 |
| gold same position, block changed | 3 | 1: 1, 2: 1, 3: 1 | 1: 1, 2: 1, 3: 1 | 3 | 3 | 3 |
| gold demoted | 3 | 1: 1, 3: 1, 6: 1 | 2: 1, 4: 1, 8: 1 | 2 | 3 | 3 |
| identical block | 1 | 2: 1 | 2: 1 | 1 | 1 | 1 |

Every save has gold on AGREE's Perception shortlist (67/67, against 25/67 in the A/A) and every saved answer came from that shortlist. 60 of 67 saves are delivery events -- 32 newly delivered (24 straight to position 1) and 28 promoted (23 to position 1) -- against about 7 expected under the null for those two transitions. Noise-level saves, summed per transition as min(observed, expected): 12.65.

### 1.4 Harms (31)

| class | rows | gold pos A/A | gold pos AGREE | gold on list A/A | gold on list AGREE | Perception list identical | delivered from list AGREE | wrong answer's entry moved up | exemplar votes favour the delivered intent over gold |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| (i) displaced (gold dropped out of the 8) | 1 | 5 | none | 1 | 0 | 0 | 1 | 1 | 1 |
| (ii) identical block | 2 | 1: 2 | 1: 2 | 2 | 2 | 1 | 2 | 0 | 0 |
| (iii) gold demoted | 21 | 1: 17, 2: 2, 4: 1, 7: 1 | 2: 13, 3: 5, 4: 1, 5: 1, 8: 1 | 21 | 18 | 1 | 20 | 18 | 19 |
| (iii) gold same position, block changed | 5 | 1: 4, 2: 1 | 1: 4, 2: 1 | 5 | 5 | 1 | 5 | 4 | 1 |
| (iii) gold promoted | 1 | 7 | 6 | 1 | 1 | 0 | 1 | 1 | 1 |
| (iii) gold newly delivered | 1 | none | 2 | 1 | 0 | 0 | 0 | 0 | 0 |

**Answer.** Class (i), delivery displacing a delivered gold entry, is 1 harm. Class (ii), identical delivery with a different choice, is 2 harms against 1.73 expected -- pure noise. Class (iii) is 28, and it is not one thing: **21 are demotions** -- gold was at position 1 on 17 of them and fell to 2-3, the delivered wrong intent is the entry the agreement term moved up (18/21), and the self-excluded exemplar vote favoured that wrong intent over gold on 19/21. That is the mechanism's own cost, 21 against 0.82 expected. The other 7 of class (iii) sit inside (or, for promotion, below) their null intervals. **Harms indistinguishable from noise: 10 of 31** (every harm in a transition class whose count lies inside its null 95 % interval: identical 2, same position 5, dropped 1, newly delivered 1, promoted 1); summed as min(observed, expected) the noise share is 7.81. Net of noise: about 54 mechanism saves against about 21-23 mechanism harms. The Solver followed the shortlist in 29/31 harms; Perception kept gold on its list in 26/31 harms and the wrong entry still won.

## 2. The remaining intent error of the AGREE arm (153 rows, 14.17 points)

### 2.1 Exclusive partition by source

Precedence: an unparsed answer first; then a row whose gold or delivered intent is the catch-all `general_quirky` (the label-ceiling audit's definition); then the pipeline stage -- RETRIEVAL (gold boundary entry not among the 8 delivered), CONSUMPTION-PERCEPTION-DROP (delivered, not on Perception's 1-3 shortlist), CONSUMPTION-SOLVER-CHOICE (on the shortlist, not chosen). One row = 0.0926 pp.

| class | rows | pp | share of 14.17 % | within-scenario | cross-scenario | gold position | delivered answer at position 1 | delivered from the shortlist | wrong in all 3 null flights |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| UNPARSED | 1 | 0.09 | 0.65 | 0 | 0 | 1: 1 | 0 | 0 | 1 |
| CATCH-ALL | 33 | 3.06 | 21.57 | 1 | 32 | 1: 2, 2-3: 14, 4-8: 8, none: 9 | 20 | 31 | 30 |
| RETRIEVAL | 25 | 2.31 | 16.34 | 1 | 24 | none: 25 | 17 | 23 | 23 |
| CONSUMPTION-PERCEPTION-DROP | 36 | 3.33 | 23.53 | 13 | 23 | 1: 2, 2-3: 13, 4-8: 21 | 27 | 36 | 29 |
| CONSUMPTION-SOLVER-CHOICE | 58 | 5.37 | 37.91 | 26 | 32 | 1: 13, 2-3: 37, 4-8: 8 | 38 | 56 | 30 |
| **total** | **153** | **14.17** | 100 | 41 | 111 | | 102 | 146 | 113 |

Without the catch-all split the stage partition is RETRIEVAL 34, PERCEPTION-DROP 49, SOLVER-CHOICE 69, UNPARSED 1: **consumption owns 118 of 153 rows (10.93 pp), retrieval 34 (3.15 pp).** Conversion on AGREE: gold on Perception's shortlist is answered correctly on 925/995 rows (93.0 %); gold in the block but off the shortlist on 1/50 (2.0 %).

### 2.2 What the evidence and the shortlist said on those rows

| class | exemplar votes favour the delivered intent | favour gold | tied | delivered = Perception's first hypothesis | gold = Perception's first | gold-intent exemplars among the 20: 0 / 1-2 / 3-5 / 6-10 / 11-20 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| UNPARSED | 0 | 1 | 0 | 0 | 0 | 0 / 0 / 0 / 1 / 0 |
| CATCH-ALL | 18 | 13 | 2 | 29 | 1 | 5 / 11 / 16 / 1 / 0 |
| RETRIEVAL | 21 | 2 | 2 | 20 | 0 | 20 / 5 / 0 / 0 / 0 |
| CONSUMPTION-PERCEPTION-DROP | 30 | 3 | 3 | 34 | 0 | 11 / 14 / 2 / 8 / 1 |
| CONSUMPTION-SOLVER-CHOICE | 38 | 16 | 4 | 49 | 7 | 2 / 15 / 23 / 12 / 6 |

**Reading.** The system follows its evidence: the delivered wrong intent is Perception's first hypothesis on 132 of 153 rows, and the 20 speech-retrieved exemplars carry more examples of the delivered wrong intent than of gold on 107 of 152 parsed rows. On the 58 solver-choice rows gold was Perception's FIRST hypothesis on only 7; on 49 the Solver took Perception's first, which was wrong. Where the knowledge falls short is therefore mostly not presence -- on SOLVER-CHOICE gold is on the shortlist and has 3+ exemplars on 41/58 rows -- but **discrimination**: the supply offers no evidence that separates the gold intent from its top competitor, so the more frequent neighbour wins.

### 2.3 RETRIEVAL: how far the key misses

The 25 retrieval rows rank gold, under the flown agreement order, at 9-12: 5, 13-16: 3, 17-30: 7, 31-60: 9, unranked 1; 20/25 have zero gold-intent exemplars among the 20. The COMP-1 key (centroid boundary key + the same agreement vote) replayed offline puts gold in the top 8 on **4 of 25** (its ranks: 1-8: 4, 9-12: 8, 13-16: 4, 17-30: 6, 31-60: 2, unranked 1). The speech query lands in the wrong region for BOTH stores on these rows (the exemplar vote favours the delivered wrong intent on 21/25), so no reweighting of the flown recall reaches most of them.

### 2.4 CATCH-ALL

`general_quirky` is gold on 45 roster rows and answered correctly on 16 (35.6 %); 29 gold-quirky misses and 4 wrong `general_quirky` deliveries make the 33. By stage: retrieval 9, Perception drop 13, Solver choice 11. 32 of 33 are cross-scenario (top pairs: `general_quirky` -> `news_query` 4, -> `qa_definition` 3, -> `qa_factoid` 3, -> `recommendation_events` 3). The label-ceiling audit found no label-side cause for this class.

### 2.5 Confusion structure

119 distinct (gold, delivered) pairs over 153 rows; 95 pairs occur once; 111 rows cross scenario, 41 stay within it. The largest pairs: `audio_volume_other` -> `audio_volume_up` 4 (within), `general_quirky` -> `news_query` 4, `takeaway_order` -> `recommendation_locations` 4, `transport_ticket` -> `transport_query` 3 (within), then eighteen pairs of 2-3 rows. Gold intents carrying the most errors: `general_quirky` 29, `cooking_recipe` 9, `news_query` 8, `audio_volume_mute` 6, `music_query` 6, `qa_factoid` 6. The error is broad (the decomposition read's conclusion holds for the new arm): no handful of pairs owns it.

### 2.6 PERCEPTION-suspect rows

Criterion (reproducible, no transcript): a row is perception-suspect when one of its delivered entity values, paired with a gold entity value (same type, or cross type), differs from it by a canonical normalised character edit distance in (0, 0.4] and is neither a format variant nor a span containment. Canonical form = the bank's fold (NFKC, casefold, punctuation except apostrophe and hyphen removed) plus apostrophes and hyphens dropped, `a m`/`p m` joined, `o'clock` dropped, number and ordinal words to digits.

| threshold | intent-wrong rows with gold entities | flagged | intent-right rows with gold entities | flagged |
| --- | ---: | ---: | ---: | ---: |
| 0.2 | 76 | 6 (7.9 %) | 590 | 35 (5.9 %) |
| 0.3 | 76 | 9 (11.8 %) | 590 | 46 (7.8 %) |
| 0.4 | 76 | 10 (13.2 %) | 590 | 53 (9.0 %) |
| 0.5 | 76 | 13 (17.1 %) | 590 | 64 (10.8 %) |

Visible mishearing is only mildly elevated on intent-wrong rows (13.2 % vs 9.0 % at 0.4), and 77 of 153 intent-wrong rows carry no gold entity so the criterion cannot see them. **The intent error is not predominantly a hearing error that the entity side makes visible**: 10 rows (0.93 pp) at most, spread across classes (RETRIEVAL 2, PERCEPTION-DROP 2, SOLVER-CHOICE 6).

### 2.7 Stability

113 of 153 wrong rows are also wrong in all three null flights; 40 are right in at least one (SOLVER-CHOICE 28, PERCEPTION-DROP 7, CATCH-ALL 3, RETRIEVAL 2). The sample-aggregation route that would harvest those 40 is closed (decision 112, no qualified gain).

## 3. The official SLU-F1 gap (65.16 -> 100, 34.84 points)

941 gold entity items, 1,021 predicted, 660 error items. Kinds, after exact matches are removed: same-type pairs are classified FORMAT (canonically equal), BOUNDARY (one token span contains the other), NEAR (canonical distance <= 0.4), WRONG-VALUE (otherwise); cross-type leftovers carrying the same, a span-related or a near value are WRONG-TYPE; the rest are MISSING (gold never predicted) or SPURIOUS (prediction with no gold). A repair replaces exactly those items by gold and re-scores the whole roster with the official arithmetic.

| kind | items | on intent-wrong rows | isolated repair pp | cumulative ladder increment pp | type card delivered | type shown in the 20 exemplars |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| MISSING | 173 | 33 | 9.80 | 9.80 | 166 | 154 |
| SPURIOUS | 253 | 70 | 8.46 | 8.93 | 248 | 224 |
| WRONG-TYPE (26 same value, 25 related value) | 51 | 9 | 4.63 | 4.80 | 47 | 39 |
| BOUNDARY (39 prediction longer, 36 shorter) | 75 | 8 | 2.88 | 4.18 | 75 | 74 |
| WRONG-VALUE | 41 | 6 | 2.12 | 3.37 | 41 | 40 |
| NEAR | 56 | 6 | 1.84 | 3.07 | 56 | 55 |
| FORMAT (4 case/punctuation, 7 number/time token) | 11 | 1 | 0.39 | 0.69 | 11 | 11 |
| **all** | **660** | **133** | | **34.84** | | |

The ladder repairs kinds one after another in descending isolated gain; its increments sum exactly to the gap. **Entity errors on intent-right rows own 27.13 of the 34.84 points; on intent-wrong rows 5.96** -- the SLU-F1 gap is an entity problem in its own right, not the shadow of the intent error. The slot-contract card of the item's type was delivered on 644 of 660 error items: the type knowledge is present and the conventions inside it do not bind.

Targeted repairs: date relative-day MISSING (72 gold relative-day date items, 30 missed) **1.81 pp**; all date MISSING 2.35 pp; WRONG-TYPE with the right value 2.36 pp; SPURIOUS on intent-right rows 5.90 pp (on intent-wrong rows 2.14 pp); NEAR + WRONG-VALUE together 4.09 pp.

| slot type | gold items | error items | kinds | isolated repair pp |
| --- | ---: | ---: | --- | ---: |
| date | 138 | 73 | MISSING 39, BOUNDARY 12, WRONG-TYPE 8, SPURIOUS 7, FORMAT 3, NEAR 2, WRONG-VALUE 2 | 4.04 |
| place_name | 100 | 52 | SPURIOUS 17, MISSING 12, NEAR 7, BOUNDARY 6, WRONG-TYPE 5, WRONG-VALUE 5 | 2.39 |
| business_name | 52 | 49 | SPURIOUS 16, NEAR 11, MISSING 8, WRONG-VALUE 5, FORMAT 4, BOUNDARY 3, WRONG-TYPE 2 | 2.05 |
| time | 76 | 36 | BOUNDARY 9, SPURIOUS 7, MISSING 6, NEAR 5, WRONG-TYPE 4, WRONG-VALUE 3, FORMAT 2 | 1.69 |
| event_name | 41 | 36 | SPURIOUS 16, MISSING 8, BOUNDARY 5, NEAR 3, WRONG-TYPE 3, WRONG-VALUE 1 | 1.60 |
| food_type | 65 | 38 | SPURIOUS 19, NEAR 6, BOUNDARY 5, MISSING 4, WRONG-VALUE 3, WRONG-TYPE 1 | 1.50 |
| media_type | 57 | 26 | MISSING 9, SPURIOUS 8, WRONG-VALUE 4, NEAR 3, WRONG-TYPE 2 | 1.32 |
| person | 42 | 31 | SPURIOUS 10, BOUNDARY 7, WRONG-VALUE 6, MISSING 5, WRONG-TYPE 2, NEAR 1 | 1.28 |
| order_type | 23 | 22 | MISSING 14, SPURIOUS 4, WRONG-TYPE 2, BOUNDARY 1, WRONG-VALUE 1 | 1.24 |
| business_type | 29 | 20 | MISSING 7, SPURIOUS 6, NEAR 3, WRONG-TYPE 2, BOUNDARY 1, WRONG-VALUE 1 | 0.99 |
| transport_type | 36 | 15 | MISSING 14, WRONG-TYPE 1 | 0.94 |
| device_type | 15 | 20 | SPURIOUS 16, MISSING 2, NEAR 1, WRONG-TYPE 1 | 0.71 |

Temporal pattern classes (gold items; error items): date relative-day 72 (MISSING 30, BOUNDARY 3, WRONG-TYPE 2); date weekday 23 (BOUNDARY 7, MISSING 1, NEAR 1, WRONG-TYPE 1); date period 23 (MISSING 5); time clock 63 (BOUNDARY 7, NEAR 4, MISSING 3, FORMAT 2, WRONG-VALUE 2). The relative-day date omission reproduces the 2026-09-16 temporal-slot diagnosis on the PLAN anchor (the date card was present on every row with an omitted date). The most frequent wrong-type pair is `date` -> `time` (4).

## 4. Capability gaps

Ceilings are ORACLE (every row or item of the class repaired) unless a measured conversion is named; they overlap across rows and are not additive except where stated.

| capability | evidence (counts) | ceiling intent pp | ceiling SLU-F1 pp | existing registered item that addresses it |
| --- | --- | ---: | ---: | --- |
| Discriminative consumption: choose between the top candidates on contrastive evidence instead of taking Perception's first hypothesis | 94 consumption rows (58 solver choice + 36 Perception drop); delivered = Perception's first on 83/94; gold on the shortlist converts 93.0 %, off it 2.0 %; 28 of the 58 are right in some null flight | 8.70 oracle; Perception-drop rows at the on-list conversion 36 x 0.930 = 3.10 | -- | G5 (Reviewer-instruction repair, round 3, consumption-form round) and COMP-1's citation contract (per-entry credit table) act on this stage; neither supplies contrastive evidence. The aggregation route is closed (decision 112) |
| Contrastive knowledge content: evidence that separates confusable intents (pair-level boundary cues, exemplar supply balanced over the shortlisted candidates) | exemplar votes favour the delivered wrong intent on 107/152 parsed wrong rows; 41/58 solver-choice rows have 3+ gold exemplars and still lose; 119 distinct confusion pairs, 111 cross-scenario | shares the 8.70 above plus RETRIEVAL; not separable | -- | none registered; the knowledge-construction rebuild (decision 130) and `train_synthetic` (decision 136, deferred) are the nearest lines |
| Agreement-term guard: do not let the exemplar vote demote a confident position-1 gold | 21 demotion harms against 0.82 expected; 17 of them from position 1; the vote favoured the wrong intent on 19/21 | up to 1.94 (the 21 harms), less whatever saves a guard would cost | -- | none; the agreement term is COMP-1's first component (decision 161) |
| Catch-all handling for `general_quirky` | 33 rows; 29 of 45 gold-quirky rows missed (35.6 % correct); 32/33 cross-scenario | 3.06 | -- | none registered |
| Retrieval key (speech query to intent boundary and exemplar stores) | 25 RETRIEVAL rows (34 with catch-all); 20/25 carry zero gold exemplars; gold agreement rank 9-16 on 8, 17-60 on 16 | 2.31 oracle; COMP-1 replay delivers 4 -> 4 x 0.436 (KPROBE conversion 24/55) = 0.16; widening to k 16 reaches 8 -> 0.32 | -- | COMP-1 centroid boundary key (decisions 145, 152) |
| Slot recall under the annotation convention | 173 MISSING items; the type card was delivered on 166; relative-day dates 30 of 72 missed | -- | 9.80 isolated; relative-day date alone 1.81 | slot-contracts-v2 and the candidate-conditioned slot view `native-candidate-slot-view-v1` carry the type knowledge already; no item encodes the omission convention |
| Slot precision (what NOT to annotate) | 253 SPURIOUS items, 183 of them on intent-right rows; card delivered on 248 | -- | 8.46 isolated (5.90 on intent-right rows) | none registered |
| Slot-type discrimination | 51 WRONG-TYPE items, 26 with the right value (`date` -> `time` 4) | -- | 4.63 isolated; right-value subset 2.36 | top-K-conditioned slot-card selection (existing baseline behaviour) |
| Span-boundary convention | 75 BOUNDARY items (39 over-extended, 36 truncated) | -- | 2.88 isolated | none registered |
| Perception (hearing) | intent: 10 perception-suspect rows, 13.2 % vs 9.0 % base rate; entity: 56 NEAR + 41 WRONG-VALUE items | at most 0.93 | 4.09 (NEAR + WRONG-VALUE) | none registered for SLURP (E41 is the Earnings Perception note) |
| Format normaliser | 11 FORMAT items | -- | 0.39 isolated | the deliver node's projection v3 already applies the P2 filler normalisation; these 11 survive it |
| Sampling stability | null flips 27-33 per 1,080; Perception shortlist changes on ~30 % of rows under identical input; 40 wrong rows right in some null flight | 3.70 (40 rows) as an upper bound of a perfect selector | -- | aggregation route closed (decision 112) |

**Reading.** The 14.17 remaining intent points are 61 % consumption (8.70 pp), 22 % catch-all (3.06), 16 % retrieval (2.31) and one unparsed row. The system is not failing to receive knowledge -- on the consumption rows gold is delivered, usually shortlisted and usually demonstrated by exemplars -- it is failing to DISCRIMINATE: the delivered wrong intent is Perception's first hypothesis on 132/153 rows and the speech-retrieved exemplars outvote gold on 107/152, and nothing in the supply or the roles contrasts the two. The largest single missing capability is contrastive evidence at the Perception/Solver decision, then catch-all handling. The retrieval key the programme has registered (COMP-1's centroid) reaches 4 of the 25 residual retrieval rows. On the SLU-F1 side the gap is an entity-convention problem on intent-right rows (27.13 of 34.84 points): omission and over-annotation, with the type card present on 644 of 660 error items; the relative-day date omission alone is worth 1.81 points.

## 5. Reproduce

```bash
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 python scripts/analysis/slurp_agree_arm_error_sources.py \
    --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
# byte check against the written outputs (everything except generated_at):
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 python scripts/analysis/slurp_agree_arm_error_sources.py --check \
    --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
```

Content hashes of the outputs with `generated_at` removed: `report.json` 7a30ed88ab27c3ad2c9150a05a5eb1f21299c0f7e00324842a46da8d49209c86, `rows.jsonl` 17a0be507949a3c78765729eef7f72d630389848acbf4de24f778740b8b63508, `tables.md` 16dd0c4709f77440d4628718177b5e3b42e079b6c585c1bbcd7f876b5e0622da (`content-sha256.json`). A `--check` re-run reported IDENTICAL apart from `generated_at`.

## 6. Boundary

Zero model, server, tokenizer, encoder, embedder, network, GPU and paid-API contacts; no official-scorer subprocess; ports 8080 / 8081 untouched; nothing under `runs/` opened for writing. Tools: `json` reads of sealed phases, outputs, scores and (for the order check) traces, with ids kept only; `data.slurp.load_slurp_split` for TRAIN gold (4 workers); the rank diagnostic's cosine recomputation over the pinned vector files; `reproduction.slurp_scoring.score_slu` in-process for the counterfactual repairs. A DIAGNOSTIC: it admits nothing, re-pins nothing, registers no cell, releases no store and states no superiority, generalisation or Stage-3 conclusion.
