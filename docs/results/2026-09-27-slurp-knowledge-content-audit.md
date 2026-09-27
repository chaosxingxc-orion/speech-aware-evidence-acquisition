# What the SLURP knowledge actually says, and where it falls short: a content audit of the three stores the AGREE arm consumed

Date: 2026-09-27. Read id `SAEA-SLURP-MF-KNOWLEDGE-CONTENT-AUDIT-V1`, recipe `slurp-knowledge-content-audit-v1`, schema `saea-slurp-knowledge-content-audit-v1`. Owner decision 163, analysis track ("make clear where the raw knowledge falls short and what capabilities must be added"); rows 126, 128, 130 and 142 are the framing it inherits.

**DESCRIPTIVE.** A model-free read: zero model, server, tokenizer, encoder, embedder, scorer, ASR, network, GPU and paid-API contacts. Every similarity is float64 arithmetic over sha256-verified vector files the flights pinned; gold is read offline from the governed `train.jsonl` (and only the scenario/action fields of `devel.jsonl`); `test.jsonl` is never opened. No utterance text, transcript, gold filler, predicted filler, delivered answer or knowledge body is printed or persisted: every cell below is an intent id, a slot TYPE name, a count, a rate, a cosine or a hash, and card content is described only schematically. TRAIN Fold A numbers are development numbers (owner decisions 28 and 86), never a test claim. It admits nothing, releases or rebuilds no store, registers no cell and authorises no flight.

**Every "ceiling" below is an ORACLE** -- the pooled gain if every named row or item were repaired and nothing else moved. Where an "expected" figure appears it multiplies a ceiling by a MEASURED conversion rate (CONV: 32 of 70 newly delivered boundary rows converted, 0.457; KPROBE: 24 of 55, 0.436) and is labelled as such; no other conversion is assumed. Official SLU-F1 ceilings for item-level repairs are a **proportional approximation** (a row's soft word/char counts move by the repaired share of its exact items); span-F1 ceilings are exact.

Reproducer `scripts/analysis/slurp_knowledge_content_audit.py` (sha256 `eff323f82d5e44cee77169a96221b22751a9654b78f39e410cfe6bd09df18eb4`); machine output `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-KNOWLEDGE-CONTENT-AUDIT-V1/audit-v1.json` (sha256 `cce8e92d3d014a82604acfd5ed046b58786d87a448abb93e3de54de2258d65bc`), byte-identical across runs (verified by two runs at one driver; the generation stamp lives in `run-stamp-v1.json` beside it). 1 min wall, 0.72 GB peak, numpy capped at 4 threads.

## The answer, first

1. **Delivery is no longer where the intent knowledge fails -- content is.** Of the AGREE arm's 153 remaining intent-wrong rows on TRAIN Fold A, 119 (77.8 %) already had the gold intent's boundary card delivered, and on 114 both the gold card and the card of the intent the system chose were in front of it. The centroid key would newly deliver gold on only **7** of the 34 rows still missing it. What the delivered cards do not carry is **contrast**: every one of the 60 cards has exactly ONE activation sentence and exactly ONE confusable exclusion, while the errors spread over **119 distinct (gold, predicted) pairs**, 95 of the 153 rows sitting in a pair seen once. On **75 rows** both cards were delivered and neither names the other.
2. **The slot-side loss is dominated by three things the cards do not say**: *what not to tag* (278 spurious entities, the largest single error class, 193 of the 202 on intent-right rows of a type legitimately seen with that intent -- so an intent-to-type legality table buys almost nothing), *the value vocabulary* of closed and semi-closed types (157 missed or wrong gold items whose value is in TRAIN's own list; the five closed types have 3-16 values each and their cards name 0-5 of them), and *span extent* (91 of the 183 wrong same-type fillers are a sub- or super-span of gold). Surface **format conventions** (digits, casing, meridiem) are **not** a deficit: 1 of 941 gold fillers and 1 of 1,021 predicted fillers carry a digit, 0 predicted fillers carry an uppercase letter, and only 4 wrong fillers are repairable by punctuation folding.
3. **The exemplar pool is complete but its key space misleads on the rows that fail.** On 93 of the 153 wrong rows the majority of the 20 delivered exemplars carries the intent the system wrongly chose; on 38 rows not one of the 20 carries the gold intent, although that intent's median pool size is 133.5 and only 9 of the 38 sit in the pool's bottom quartile. One pool exemplar in five (20.3 %) is nearer another intent's centroid than its own, yet only 12 of those 1,901 have a near-identical (token Jaccard >= 0.8) sentence of the other intent -- it is the text-embedding key space that is compressed (nearest-neighbour cosine mean 0.966), not the labels that are noisy.
4. **`general_quirky` is a knowledge problem of its own shape**: 29 of the 153 wrong rows (19.0 %), lost to 18 different intents, with its gold card delivered on 21 of the 29. Its pool neighbourhood is the least pure in the store (10-NN label agreement 0.33 against 0.71 overall; 49.8 % of its exemplars nearer another centroid against 20.3 %). A one-sentence card and a one-vector key cannot describe a residual class.

## 0. What was read

| Artefact | Relpath under `SPEECHRL_DATA_DIR` | identity |
| --- | --- | --- |
| `intent-boundaries-v1` snapshot (content hash) | `knowledge/slurp/semantic/intent-boundaries-v1/snapshot.json` | `5520b8449b627530227563d1f8db71f8a391f20f7d0ff7d7bd439e28ec6e48fe` |
| written boundary keys (60 x 2048) | `prepared/SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1/facets.jsonl` | `76e8d16a067ebfc5d67a4ecef2966636310815b950a7d9790ec7c0136f01ecd2` |
| centroid boundary keys (KPROBE / COMP-1 pin) | `prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl` | `16c33640151cff6428bc50e4f00ced93b35f76fa186b8d08fcefdfdb33fd5532` |
| `slot-contracts-v2` snapshot (content hash) | `knowledge/slurp/semantic/slot-contracts-v2/snapshot.json` | `d5992bd12687cbd0204c14fc4e29f987697b8751321d524d7707229032f5bdec` |
| exemplar pool as flown by AGREE, 9,354 (content hash) | `knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json` | `4c498dc0282055b9fe036ed7e950af519bd48b5f26e76876d0250727196a72e9` |
| R01-excluded pool, 8,554 (content hash) | `knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/snapshot.json` | `6eaa03aea96a1928dd1ac29ecc71c3955c136498c9f8114266eaa830d1207c63` |
| pool key vectors (one per TRAIN utterance, 11,514) | `vectors/slurp-kus3/facet-vectors.jsonl` | `5dfe75231c12f2624913988e4643c51b74856465bdbd108358b4f371dacffc1e` |
| Fold A speech query vectors | `vectors/slurp-intent-boundaries-train-fold-a-1080-v1/query-vectors-speech-segments.jsonl` | `e7a5b2264dc61fcab3c63d50fb645d4629d3f0a99f83ad5fbe323c73884e5f0b` |
| governed TRAIN / devel labels | `datasets/slurp/metadata/train.jsonl` / `devel.jsonl` | `4a05a3de...` / `00d346b1...` |
| AGREE arm outputs, official score, phase summary | `runs/SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1/attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1/` | hashed in `audit-v1.json` |
| in-chain A/A phase summary (ranking validation only) | `runs/SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1/...` | -- |
| CONV and KPROBE read results (conversion rates) | `analysis/SAEA-SLURP-STAGE3-{CONV-FOLD-A-70,KPROBE-FOLD-A-55}-CONDITIONAL-RATE-V1/read-v1.json` | `c1aa690c...` / `4223870a...` |

**Which pool.** The brief names "11,514 / 8,554 R01-excluded utterances"; measured, the AGREE arm's Solver-phase `train-exemplars` store is the 9,354-utterance pool (37,407 recordings; 2,160 TRAIN utterances withheld, Fold A among them), keyed through the 11,514-row TRAIN facet file; the 8,554 R01-excluded sibling is the centroid key's construction pool and is counted beside it. No Fold A utterance is in the flown pool (checked).

**Validation before any number.** The AGREE roster reproduces the TRAIN Fold A split identity `61b0f062...`; the pooled word+char SLU-F1 recomputed from the 1,080 per-sample rows reproduces the official 65.1575 exactly; the parsed delivered intent agrees with the sealed official intent flag on 1,080 of 1,080 rows; the official exact-span matcher reproduces the sealed per-row tp/fp/fn on every row; and the written-key cosine ranking reproduces the in-chain A/A arm's sealed delivered boundary set on 1,080 of 1,080 rows (the AGREE arm itself ranks with the agreement term, so its delivered set is read from its sealed consumption records, never recomputed).

| AGREE arm, TRAIN Fold A | value |
| --- | ---: |
| rows | 1,080 |
| official intent accuracy | 85.83 % (153 rows wrong) |
| official SLU-F1 / span-F1 | 65.16 / 54.43 |
| rows with any entity error | 519 |
| gold entities / predicted entities | 941 / 1,021 |
| exact tp / fp / fn | 534 / 487 / 407 |
| mean prompt tokens per contact / per row | 8,592 / 34,886 (4,385 contacts) |

## 1. Intent boundaries (60 cards, their written keys and the centroid keys)

### 1.1 Coverage and card shape

The store has one card per TRAIN intent (60 of 60; devel carries 59 of them, none without a card). Card content is authored text of 702 characters on average (42,133 in all), in four sections:

| section | characters (all 60 cards) | share of the body | distinct values across 60 cards |
| --- | ---: | ---: | ---: |
| Activation boundary | 4,244 | 10.1 % | 60 (exactly one bullet per card) |
| Confusable exclusions | 7,301 | 17.3 % | 60 (**exactly one** named intent per card) |
| Uncertainty behavior | 11,940 | 28.3 % | **1** (identical on all 60) |
| Limitations | 12,362 | 29.3 % | 15 |

So **57.7 % of every delivered boundary card is boilerplate** and the discriminating content is one activation sentence plus one exclusion. The two overlaps the programme has been quoting are both reproduced: the delivered bodies share **0.6073** of their words on average (max 0.9189) -- almost all of it the boilerplate, because the two discriminating sections alone overlap at **0.0985** -- while the 84-character representations the channel actually ENCODES as keys overlap at **0.0814** (max 0.692). Written key cosine mean 0.4756 (max 0.908); the pinned centroid keys sit at 0.9326.

### 1.2 Where the 153 remaining intent errors sit against the knowledge

| state of the knowledge on the wrong row | rows | share of 153 |
| --- | ---: | ---: |
| gold card NOT delivered (of 8) | 34 | 22.2 % |
| ... of which the centroid key alone would deliver it | 7 | 4.6 % |
| ... of which not one of the 20 delivered exemplars carries gold either | 25 | 16.3 % |
| gold card delivered, chosen intent's card not delivered | 5 | 3.3 % |
| **both cards delivered, neither names the other in its exclusion** | **75** | **49.0 %** |
| both cards delivered, one of them names the other | 39 | 25.5 % |

The 34 + 5 + 114 rows partition the 153. On 94 of the 153 the WRITTEN key ranks the chosen intent above gold for the row's own speech vector; on 103 the CENTROID key does -- so the centroid key, which wins on delivery, does not separate the confused pair any better once both are delivered. The 25 rows where neither the boundary channel nor the exemplar channel retrieves gold are rows where the speech query is far from every TRAIN description of its own intent; knowledge content has little leverage there (an OBS / perception question for the error-source read).

**Confusion is diffuse.** 119 distinct pairs; 24 pairs have two or more rows; 95 rows are singletons. The per-gold view:

| gold intent | Fold A rows | wrong | distinct confusers | confusers named on its card |
| --- | ---: | ---: | ---: | ---: |
| `general_quirky` | 45 | 29 | 18 | 1 of 1 |
| `cooking_recipe` | 59 | 9 | 5 | 1 of 1 |
| `news_query` | 60 | 8 | 7 | 0 of 1 |
| `audio_volume_mute` | 24 | 6 | 4 | 1 of 1 |
| `music_query` | 32 | 6 | 5 | 1 of 1 |
| `qa_factoid` | 27 | 6 | 6 | 0 of 1 |
| `datetime_query` | 50 | 5 | 4 | 1 of 1 |
| `social_post` | 47 | 5 | 4 | 0 of 1 |
| `social_query` | 13 | 5 | 4 | 1 of 1 |
| `takeaway_order` | 29 | 5 | 2 | 1 of 1 |
| `audio_volume_other` | 4 | 4 | 1 | 0 of 1 |
| `play_music` | 19 | 4 | 4 | 0 of 1 |

The pairs with two or more rows, with what each card and key says about the pair (`crossings` = pool exemplars of one intent that are nearer the other intent's centroid than their own, leave-one-out):

| gold | chosen | rows | gold card delivered | gold card names it | its card names gold | written key prefers chosen | centroid key prefers chosen | body word Jaccard | written key cosine | crossings gold->chosen | crossings chosen->gold |
| --- | --- | ---: | ---: | :-: | :-: | ---: | ---: | ---: | ---: | ---: | ---: |
| `audio_volume_other` | `audio_volume_up` | 4 | 4 | no | yes | 4 | 2 | 0.733 | 0.696 | 1 | 4 |
| `general_quirky` | `news_query` | 4 | 2 | no | no | 3 | 4 | 0.594 | 0.459 | 10 | 23 |
| `takeaway_order` | `recommendation_locations` | 4 | 4 | no | no | 0 | 3 | 0.504 | 0.546 | 6 | 1 |
| `general_quirky` | `qa_definition` | 3 | 3 | no | no | 3 | 3 | 0.590 | 0.485 | 65 | 15 |
| `general_quirky` | `qa_factoid` | 3 | 3 | yes | no | 2 | 1 | 0.602 | 0.488 | 24 | 29 |
| `general_quirky` | `recommendation_events` | 3 | 2 | no | no | 3 | 1 | 0.514 | 0.420 | 5 | 9 |
| `transport_ticket` | `transport_query` | 3 | 3 | yes | yes | 3 | 1 | 0.785 | 0.655 | 4 | 16 |
| `audio_volume_mute` | `audio_volume_down` | 2 | 2 | yes | yes | 0 | 2 | 0.637 | 0.707 | 4 | 5 |
| `audio_volume_mute` | `calendar_set` | 2 | 2 | no | no | 0 | 1 | 0.562 | 0.484 | 1 | 13 |
| `cooking_recipe` | `cooking_query` | 2 | 2 | yes | yes | 0 | 0 | 0.571 | 0.687 | 1 | 3 |
| `cooking_recipe` | `qa_definition` | 2 | 1 | no | no | 2 | 1 | 0.523 | 0.566 | 2 | 0 |
| `cooking_recipe` | `qa_factoid` | 2 | 2 | no | no | 0 | 0 | 0.519 | 0.492 | 1 | 4 |
| `cooking_recipe` | `recommendation_locations` | 2 | 1 | no | no | 0 | 2 | 0.509 | 0.537 | 0 | 0 |
| `datetime_query` | `datetime_convert` | 2 | 2 | yes | yes | 2 | 2 | 0.786 | 0.690 | 13 | 2 |
| `email_querycontact` | `qa_factoid` | 2 | 1 | no | no | 2 | 1 | 0.544 | 0.482 | 5 | 5 |
| `general_quirky` | `play_game` | 2 | 1 | no | no | 2 | 2 | 0.549 | 0.443 | 4 | 0 |
| `general_quirky` | `recommendation_movies` | 2 | 2 | no | no | 2 | 2 | 0.491 | 0.423 | 5 | 2 |
| `iot_hue_lighton` | `iot_hue_lightup` | 2 | 2 | yes | yes | 2 | 2 | 0.753 | 0.817 | 0 | 4 |
| `music_query` | `play_music` | 2 | 2 | yes | no | 1 | 0 | 0.690 | 0.679 | 6 | 4 |
| `news_query` | `recommendation_events` | 2 | 2 | no | no | 2 | 2 | 0.622 | 0.521 | 2 | 4 |
| `social_post` | `calendar_query` | 2 | 1 | no | no | 0 | 1 | 0.636 | 0.365 | 0 | 0 |
| `social_query` | `news_query` | 2 | 2 | no | no | 2 | 0 | 0.699 | 0.609 | 5 | 11 |
| `takeaway_query` | `takeaway_order` | 2 | 2 | yes | yes | 0 | 1 | 0.607 | 0.736 | 2 | 7 |
| `transport_query` | `recommendation_locations` | 2 | 2 | no | yes | 0 | 1 | 0.652 | 0.520 | 17 | 1 |

Two readings. First, the pairs the authored exclusions DO name (the within-scenario siblings: volume, lights, transport, takeaway, datetime) are still confused on 39 rows, so one sentence of contrast is not sufficient where it exists; the cross-scenario pairs, which are most of the mass, are simply unnamed. Second, the rivals are predictable from TRAIN without Fold A gold: a contrast set of each intent's **5 nearest TRAIN-centroid neighbours** contains the chosen intent on 72 of the 153 wrong rows and on 31 of the 75 unnamed-pair rows (top-3: 61 / 26; top-8: 86 / 39). Descriptively, rows whose gold card's one named confuser is among the delivered eight are right 89.7 % of the time (720 rows) against 78.1 % otherwise (360 rows) -- a correlation, not a causal estimate.

### 1.3 `general_quirky`

| quantity | value |
| --- | ---: |
| Fold A gold rows / right / wrong | 45 / 16 / 29 |
| wrong rows with its card delivered | 21 of 29 |
| wrong rows the centroid key would newly deliver | 5 |
| distinct intents it is lost to | 18 (largest: `news_query` 4, `qa_definition` 3, `qa_factoid` 3, `recommendation_events` 3) |
| rows where it is wrongly chosen | 4 |
| card: activation bullets / exclusions / other cards naming it | 1 / 1 / 1 |
| gold-intent exemplars among the 20, mean on its wrong rows | 2.48 |
| pool exemplars | 456 (TRAIN 555) |
| pool 10-NN label agreement | 0.33 (all intents 0.71) |
| pool exemplars nearer another intent's centroid | 49.8 % (all intents 20.3 %) |

The catch-all is not missed because it is under-represented or undelivered; it is missed because nothing in the knowledge says what it is NOT. Its neighbourhood in the pool is split across the question-answering, news and recommendation intents (65 of its exemplars sit nearer `qa_definition`'s centroid, 24 nearer `qa_factoid`'s), which is the same set of intents it is lost to on Fold A. The 2026-09-26 label-ceiling audit already showed this is not label duplication (0 sentence collisions within either split).

## 2. The exemplar pool (`train-exemplars`, k = 20 delivered)

### 2.1 Size, balance and slot-type coverage

| | TRAIN | pool (9,354) | R01-excluded (8,554) |
| --- | ---: | ---: | ---: |
| utterances | 11,514 | 9,354 | 8,554 |
| intents present | 60 | 60 | 59 (`cooking_query` absent) |
| per-intent min / median / max | 4 / 128.5 / 810 | 3 / 100 / 764 | 0 / 92 / 745 |
| Gini / coefficient of variation | 0.450 / 0.905 | 0.484 / 1.004 | 0.506 / 1.056 |
| intents under 50 utterances | 6 | 11 | 18 |

Smallest in the pool: `cooking_query` 3, `music_dislikeness` 7, `audio_volume_other` 12, `iot_hue_lighton` 16, `general_greet` 18, `music_settings` 32; largest `calendar_set` 764, `play_music` 590. The pool's own annotations match governed gold on intent for 9,354 of 9,354 and on the entity list for 9,350 (4 differ).

(intent, slot type) coverage: TRAIN outside Fold A holds 418 pairs, the pool 402; 16 TRAIN pairs have no pool exemplar and 168 have only one or two. Of the 198 pairs present in Fold A gold, **15 have no pool exemplar** (for example `takeaway_query` with `place_name`, `event_name` and `timeofday`; `calendar_set` with `artist_name` and `song_name`; `music_query` with `music_album`) and 36 have two or fewer.

### 2.2 Near-duplicates and geometry

| measure | value |
| --- | ---: |
| nearest-neighbour cosine, mean / median | 0.966 / 0.972 |
| items with a neighbour at cosine >= 0.99 (of which of another intent) | 1,091 (79) |
| items with a neighbour at cosine >= 0.95 (of which of another intent) | 7,408 (1,232) |
| exact normalised-sentence duplicate groups / items | 46 / 92 |
| 10-NN label agreement, mean | 0.707 |
| items whose 10-NN majority is another intent | 2,314 |
| items nearer another intent's centroid than their own (leave-one-out) | 1,901 (20.3 %) |
| ... of which a near-identical sentence of that other intent exists in TRAIN (token Jaccard >= 1.0 / 0.9 / 0.8) | 1 / 1 / 12 |

The key space is compressed -- 98 % of items have a neighbour above cosine 0.90 -- so cosine thresholds are not a duplicate test here, and the exact-sentence duplicates are few (92 items). The **label-noise versus ambiguity** question the brief asks is answered by the last line: of the 1,901 exemplars that geometrically belong to another intent, 12 have a near-identical sentence carrying that other intent. The crossing is semantic proximity in the key space, not label noise, which agrees with the label-ceiling audit (sentence-level ceiling 100.00 % on Fold A). Largest crossings: `general_quirky` -> `qa_definition` 65, `qa_factoid` -> `qa_definition` 39, `calendar_query` -> `general_quirky` 31, `calendar_set` -> `calendar_query` 31, `play_radio` -> `play_music` 30.

### 2.3 What the 20 delivered exemplars carried on the AGREE rows

| gold-intent exemplars among the 20 | intent-wrong rows (153) | intent-right rows (927) |
| --- | ---: | ---: |
| 0 | 38 | 9 |
| 1-4 | 75 | 58 |
| 5-9 | 30 | 133 |
| 10-20 | 10 | 727 |
| mean | 3.29 (chosen intent: 7.50) | 14.24 |

On the wrong rows the delivered set's majority is the chosen (wrong) intent on **93 of 153** and gold on 18; the chosen intent has at least one exemplar on 138. The 38 zero-gold rows are not a coverage artefact: their gold intents have a median of 133.5 pool exemplars, only 9 of the 38 fall in the pool's bottom quartile (<= 62), and 25 of the 38 also miss the boundary card (section 1.2). The 18 rows where gold IS the majority and the answer is still wrong are a consumption failure, not a knowledge one.

## 3. Slot contracts (`slot-contracts-v2`, 54 cards) and the entity loss

### 3.1 Card content

54 cards, 83,351 characters, six sections (intent bindings and roles, extraction cues, admissible formats, missing behavior -- 8 distinct strings across 54 cards --, ambiguity behavior, limitations). TRAIN has 55 slot types: **`music_album` has no card**. Measured by keyword over the cues and formats sections: all 54 cards speak of the spoken form; 7 mention numbers or digits, 2 ordinals, 7 relative dates, 1 (`time`) meridiem, **0 casing**. That silence is harmless: gold fillers are the lowercased spoken tokens (1 of 941 Fold A gold fillers carries a digit) and the delivered fillers already match that surface (1 of 1,021 with a digit, 0 with an uppercase letter; 4 wrong fillers repairable by punctuation folding alone). **Surface format is not a deficit on the AGREE arm; span extent and vocabulary are.**

**Card usage on this arm** (the 90.6 % measurement, re-read on AGREE): 12.9 cards offered per row, 13,936 in all, of which 1,181 serve a type the delivered answer or gold used; **91.1 %** of the offered card characters (27.4 M of 30.1 M) serve neither, about 27,900 characters or ~5,400 tokens per row at the 5.13 characters per token measured in the M1 compression analysis. The offered set covers every delivered type on 1,073 of 1,080 rows and every gold type on 654 of the 666 rows with gold entities.

### 3.2 Where the entity loss is, by type

Exact-span accounting (the official matcher), decomposed with the bad-case bank's own rule: FN 407 = wrong filler of the right type 183 + type swap 26 + omission 198; FP 487 = 183 + 26 + **over-emission 278**.

| slot type | vocabulary class | tp | fp | fn | F1 | wrong filler | swap in | omission | over-emission | fn on intent-wrong rows |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `date` | semi-closed | 72 | 27 | 66 | 0.608 | 19 | 5 | 42 | 8 | 6 |
| `business_name` | open | 19 | 42 | 33 | 0.336 | 23 | 1 | 9 | 17 | 3 |
| `place_name` | semi-closed | 65 | 37 | 35 | 0.644 | 18 | 3 | 14 | 17 | 3 |
| `time` | semi-closed | 47 | 31 | 29 | 0.610 | 19 | 2 | 8 | 11 | 3 |
| `food_type` | open | 46 | 37 | 19 | 0.622 | 14 | 0 | 5 | 20 | 2 |
| `person` | semi-closed | 21 | 29 | 21 | 0.457 | 14 | 1 | 6 | 14 | 5 |
| `event_name` | semi-closed | 21 | 27 | 20 | 0.472 | 9 | 1 | 10 | 18 | 1 |
| `media_type` | semi-closed | 39 | 15 | 18 | 0.703 | 7 | 2 | 9 | 8 | 5 |
| `business_type` | semi-closed | 15 | 15 | 14 | 0.508 | 5 | 1 | 8 | 7 | 2 |
| `order_type` | **closed** | 5 | 6 | 18 | **0.294** | 2 | 2 | 14 | 4 | 5 |
| `device_type` | semi-closed | 11 | 18 | 4 | 0.500 | 1 | 0 | 3 | 16 | 1 |
| `list_name` | semi-closed | 17 | 17 | 5 | 0.607 | 2 | 0 | 3 | 14 | 1 |
| `news_topic` | open | 8 | 14 | 7 | 0.432 | 4 | 0 | 3 | 9 | 2 |
| `song_name` | open | 2 | 13 | 4 | 0.191 | 1 | 0 | 3 | 12 | 1 |
| `transport_type` | **closed** | 21 | 2 | 15 | 0.712 | 0 | 0 | 15 | 2 | 2 |
| `house_place` | semi-closed | 9 | 10 | 6 | 0.529 | 4 | 0 | 2 | 6 | 2 |

Vocabulary class is a stated rule over TRAIN outside Fold A: a type is **closed** when at least 90 % of its (utterance-deduplicated) mentions carry a value that also occurs in another utterance, **semi-closed** at 60-90 %, **open** below. That gives 5 closed (`transport_type`, `order_type`, `timeofday`, `meal_type`, `transport_agency`), 23 semi-closed and 26 open types.

Most of the entity loss sits on intent-RIGHT rows: 344 of the 407 FN and 387 of the 487 FP are on rows whose intent is correct. The entity deficit is therefore a slot-knowledge question in its own right, not a shadow of the intent errors.

### 3.3 Is the value knowledge there?

| slot type | class | leave-one-out value coverage | distinct TRAIN values | values the card names | card characters | Fold A omissions |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `transport_type` | closed | 0.986 | 10 | 3 | 1,578 | 15 |
| `order_type` | closed | 0.917 | 16 | 5 | 1,438 | 14 |
| `timeofday` | closed | 0.987 | 11 | 5 | 2,412 | 3 |
| `meal_type` | closed | 1.000 | 3 | 3 | 1,599 | 3 |
| `transport_agency` | closed | 0.968 | 3 | 0 | 1,067 | 0 |
| `date` | semi-closed | 0.891 | 276 | 14 | 3,828 | 42 |
| `time` | semi-closed | 0.799 | 223 | 14 | 3,607 | 8 |
| `media_type` | semi-closed | 0.872 | 84 | 4 | 2,448 | 9 |
| `device_type` | semi-closed | 0.806 | 69 | 8 | 2,370 | 3 |
| `house_place` | semi-closed | 0.885 | 37 | 4 | 1,750 | 2 |
| `player_setting` | semi-closed | 0.796 | 45 | 4 | 1,630 | 1 |
| `place_name` | semi-closed | 0.693 | 454 | 7 | 2,535 | 14 |
| `person` | semi-closed | 0.622 | 449 | 0 | 2,635 | 6 |

("values the card names" counts distinct TRAIN values of at least three characters found verbatim in the card; nothing is printed.) The closed types carry 3-16 values each, their cards name 0-5 of them, and two of them (`transport_type`, `order_type`) are among the worst recalled types on Fold A.

**Which Fold A error items a value list could touch** (gold value tested against the type's TRAIN-outside-Fold-A value set, folded):

| error item class | items | closed | semi-closed | open |
| --- | ---: | ---: | ---: | ---: |
| omission, gold value IS in TRAIN's list | 144 | 33 | 92 | 19 |
| omission, gold value not in TRAIN's list | 54 | 2 | 33 | 18 (+1 `music_album`, no class) |
| wrong filler, gold in list, prediction outside it | 43 | 1 | 31 | 11 |
| wrong filler, both in list (a legal but wrong value) | 38 | 1 | 32 | 5 |
| wrong filler, gold not in list | 98 | 2 | 56 | 40 |
| wrong filler that is a sub- or super-span of gold | 91 | -- | -- | -- |
| type swap | 26 | -- | -- | -- |
| over-emission | 278 | -- | -- | -- |

**Span extent.** 91 of the 183 wrong same-type fillers are containment (the prediction is longer on 42, shorter on 37, equal length on 12), concentrated on `date` 14, `time` 12, `food_type` 7, `person` 7, `place_name` 6, `event_name` 5. The cards' admissible-formats sections say how to phrase a value, not where its span starts and stops.

**Type boundaries.** 26 type swaps (each costs one FP and one FN), led by `business_type` -> `order_type` 2, `food_type` -> `ingredient` 2, `general_frequency` -> `date` 2; on 15 of the 26 neither card mentions the other type at all.

**Over-emission.** 278 spurious entities: 202 on intent-right rows, of which **193 are of a type TRAIN does pair with the gold intent** and 9 are not; on intent-wrong rows 40 / 36. Heaviest types: `food_type` 20, `event_name` 18, `business_name` 17, `place_name` 17, `device_type` 16, `list_name` 14, `person` 14, `song_name` 12. A schema legality filter would remove 9 of them. What is absent is the annotation scope -- which mentions SLURP leaves untagged -- and the cards' missing-behavior section (8 distinct strings over 54 cards) is a general instruction, not a per-type convention.

## 4. `train_synthetic` (decisions 132 and 136; deferred)

Measured on 2026-09-26 (`docs/results/2026-09-26-slurp-train-synthetic-efficient-use-analysis.md`): its audio is TTS and is refused by the research boundary, so it can only add TEXT-side knowledge -- labels and fillers -- as construction material, never as a speech key or query. Filtered against devel and test by `slurp_id` and normalised sentence it retains 15,705 of 19,711 rows. It adds no scored label (0 devel and 0 test intents absent from TRAIN) and, measured, almost no vocabulary where this audit finds the vocabulary gaps: of the 12 thinnest entity types, 11 gain support rows but only one gains a filler TRAIN lacks, and of the missed gold items on the two sealed PLAN rosters only **18** are cleanly supplied by it once self-re-synthesis (63 of 81 candidates) is removed -- a ceiling of +0.83 SLU pp on Fold A. In the frame of this audit its useful role is narrower still: more TRAIN-like sentences for the thin (intent, type) pairs of section 2.1 and more untagged-mention evidence for the annotation-scope knowledge of section 3.3, both as construction inputs whose value would have to be measured like any other store change. It stays deferred; nothing here argues for building it before the test read.

## 5. Knowledge deficits -> capability to add

Rows affected are AGREE-arm TRAIN Fold A rows (n = 1,080; 153 intent-wrong, 519 with an entity error). Ceilings are oracles (section preamble). "Expected" multiplies a ceiling by a measured conversion and is only given where a measured conversion applies. SLU ceilings for entity items are the proportional approximation; span-F1 exact beside it. Rows can belong to more than one deficit; the ceilings do not add.

| # | deficit | evidence (counts; AGREE rows affected) | proposed knowledge change (content / key / form) | ceiling, intent pp | ceiling, SLU pp | risk (form cost, context length) |
| --- | --- | --- | --- | --- | --- | --- |
| K1 | **Boundary cards carry no contrast set**: 1 activation sentence and exactly 1 confusable exclusion per card; 57.7 % of each card is boilerplate | 75 wrong rows with both cards delivered and neither naming the other (49.0 % of intent errors); 119 distinct confusion pairs, 95 singleton rows; 39 more rows wrong even where the pair IS named | CONTENT: per-intent contrast set of its k = 5 nearest TRAIN-centroid rivals, one discriminating cue each, derived from TRAIN geometry (covers the chosen intent on 31 of the 75 rows, 72 of 153); FORM: replace, do not append -- the identical `Uncertainty behavior` and the 15-variant `Limitations` sections free about 3,200 characters per 8 delivered cards | 6.94 (75 rows); k = 5 coverage 2.87 (31 rows); **~1.3 if content converted like delivery did (0.457, CONV) -- no measured conversion for contrast text** | <= 3.46 if those rows' entities were also repaired (not an estimate) | about +490 characters per card, ~+760 tokens per contact carrying 8 cards, ~net +130 after removing the boilerplate; the Solver's registered envelope is 21,278 of 21,504 usable tokens (np4 slot 24,576 minus the 3,072 reserve), so it MUST be paid for; the 39 named-but-wrong rows say one sentence per pair is not enough |
| K2 | **No value vocabulary for closed and semi-closed slot types** | closed cards name 0-5 of 3-16 values; 157 gold items whose value is in TRAIN's list are missed (omission 33 closed + 92 semi-closed) or replaced by an out-of-list value (32); `order_type` F1 0.29 and `transport_type` 15 omissions on a 10-value type; 138 rows | CONTENT: complete value lists for the 5 closed types, a frequency-ranked top-N list for semi-closed types, carried with the card or as a pinned gazetteer the Solver consults; KEY: none | 0 | **9.29** (all 157 + 32 items; span 11.79); closed types alone 2.00 | closed lists are tiny (43 values in all); semi-closed lists (date 276, place_name 454, person 449) are not -- top-N only, and only for offered cards; recall gain can raise over-emission (K3) |
| K3 | **No annotation-scope (negative) knowledge**: cards do not say which mentions SLURP leaves untagged; missing-behavior is 8 generic strings | 278 over-emitted entities, the largest error class; 202 on intent-right rows, 193 of them of a type legitimately paired with the gold intent (a legality table removes 9: +0.27); 247 rows | CONTENT: per-type negative conventions mined from TRAIN (how often a candidate phrase of that type occurs UNTAGGED in TRAIN utterances of the same intent), stated as a precision prior on the card; FORM: an emit-only-if-supported rule per type | 0 | **9.30** (all 278; span 8.99); **6.48** on intent-right rows only | form risk: suppression costs recall (the bad-case bank's empty-answer lever); the mining itself is model-free but is a construction act with its own authority; no conversion measured |
| K4 | **No span-extent convention** | 91 of 183 wrong same-type fillers are sub- or super-spans of gold (longer 42, shorter 37); `date` 14, `time` 12, `food_type` 7, `person` 7; 89 rows | CONTENT: per-type extent rules with minimal pairs from TRAIN (what is inside the span and what is not) in the admissible-formats section | 0 | 5.33 (span 9.28; the official SLU-F1 already gives partial credit for containment) | small text per card (the 12 affected types); 23 items overlap K2 |
| K5 | **`general_quirky` has no residual definition** | 29 of 153 wrong rows (19.0 %), 18 distinct confusers, card delivered on 21; pool 10-NN purity 0.33 vs 0.71, 49.8 % of its exemplars nearer another centroid | CONTENT: define it negatively (none of the task intents applies) with its sub-kinds; KEY: several sub-centroid keys instead of one; FORM: a Perception rule that chooses it only when no candidate's activation holds | 2.69 (29 rows); ~1.2 at the CONV rate as a scale only | <= 0.72 | a looser catch-all is over-chosen (4 false rows today); 16 right rows at stake; overlaps K1 on 17 rows |
| K6 | **Exemplar selection is a majority of the wrong intent on failing rows** (key space, not coverage) | 38 wrong rows with 0 gold-intent exemplars in 20 (gold intents median 133.5 in pool; 9 in the bottom quartile); majority is the chosen intent on 93 of 153; 20.3 % of pool items nearer another centroid, 12 of 1,901 near-identical to a sentence of it | FORM: intent-diversified selection (value dedup by intent label, a per-intent cap across the top candidate intents) so the 20 slots carry contrast; KEY: unchanged; CONTENT: unchanged | 3.52 (38 rows); ~1.6 at the CONV rate as a scale only | <= 1.71 | token neutral (still 20); harm risk on the 727 right rows that now get 10-20 gold exemplars; the pruning read showed per-intent caps cost vote accuracy -- this is the delivered set, not the vote, and must be read separately |
| K7 | **Residual boundary delivery** | 34 wrong rows without the gold card; the centroid key newly delivers 7; 25 of the 34 miss gold in the exemplar channel too | KEY: the centroid key (already in COMP-1); nothing further from content | 0.65 (7 rows); **0.28 expected** at the KPROBE rate (0.436) | <= 0.41 | re-pin of the 211 committed configs (already priced for COMP-1); the 25 double-miss rows are a perception question |
| K8 | **Card volume is spent on types the row cannot use** | 12.9 cards per row, 91.1 % of card characters (~5,400 tokens per row) serve neither the delivered nor the gold types; offered set covers gold types on 654 of 666 rows | FORM: cards for the top candidate intents' bound types only, or the index-plus-pointer form (decision 48); CONTENT: unchanged | 0 (enabler) | 0 (enabler) | coverage loss if the offered set shrinks (a cap of 10 measured 99.3 % -> 87.5 % delivered-type cover); this is the budget that pays for K1, K2 and K4 under the 226-token Solver headroom |
| K9 | **Type-boundary contrasts missing** | 26 type swaps (FP + FN each), 15 with neither card naming the other type; 26 rows | CONTENT: pairwise type contrasts in the ambiguity sections for the swapped pairs (`order_type`/`business_type`, `ingredient`/`food_type`, `date`/`general_frequency`, ...) | 0 | 2.41 (span 2.65) | a few sentences on ~15 cards |
| K10 | **Coverage holes** | `music_album` has no card (1 FN); 15 Fold A (intent, type) pairs have no pool exemplar (7 FN items, 6 rows); `cooking_query` absent from the R01-excluded pool | CONTENT: the missing card; exemplars for the uncovered pairs (TRAIN rows not yet in the pool, or `train_synthetic` text as construction input) | 0 | 0.41 + 0.06 | negligible tokens; `train_synthetic` material carries the leakage filter of decision 136 |
| K11 | **`train_synthetic` unused (deferred)** | 18 clean items on the two sealed PLAN rosters | CONTENT: construction-only text/label material (no TTS audio) | 0 | 0.83 (quoted, PLAN Fold A) | decision 136 deferral; self-re-synthesis leakage (63 of 81 candidates) |
| -- | Surface format (digits, casing, meridiem) | 4 wrong fillers repairable by punctuation; 1 digit in 1,021 predicted fillers; 0 uppercase | none needed | 0 | 0.25 | -- |

**The three largest deficits.**

1. **K2, value vocabulary for closed and semi-closed slot types** -- SLU ceiling +9.29 (span +11.79). 157 gold items whose value TRAIN already lists are omitted or replaced by an out-of-list value, on 138 rows; the five closed types have 3-16 values and cards naming 0-5 of them, and two of them (`order_type` F1 0.29, `transport_type` 15 omissions) are among the worst types on Fold A.
2. **K3, annotation-scope (negative) knowledge** -- SLU ceiling +9.30 (+6.48 on intent-right rows). 278 over-emitted entities are the largest single error class; 193 of the 202 on intent-right rows are of a type legitimately paired with the intent, so the missing knowledge is which mentions SLURP does not tag, not which types an intent allows.
3. **K1, contrast sets on the intent boundary cards** -- intent ceiling +6.94 (75 rows; 2.87 within the k = 5 TRAIN-centroid coverage; ~1.3 if it converted like delivery did). The card for the right intent is delivered on 77.8 % of the remaining intent errors; each card distinguishes itself from exactly one rival while the errors spread over 119 pairs.

## 6. Boundary

Zero model, server, encoder, embedder, scorer, tokenizer, network, GPU and paid-API contacts; ports 8080/8081 untouched; nothing under `runs/` or `prepared/` opened for writing; the only write is `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-KNOWLEDGE-CONTENT-AUDIT-V1/`. Tools: `json` reads of three released snapshots, the sealed AGREE and A/A phase summaries, the AGREE outputs and official per-sample score, two sealed read results; `rails.phase_supply.load_sealed_vectors` / `load_sealed_segment_vectors` for the pinned vectors; `rails.knowledge.KnowledgeSnapshot` for the content hashes; `data.slurp` record helpers and `reproduction.slurp_scoring.parse_slu_response` for gold and delivered labels; the bad-case bank's `row_entity_view` and `pair_shape`, imported unchanged. This read proposes knowledge changes by name only; every one of them is a construction act with its own registration, and none is claimed to convert.
