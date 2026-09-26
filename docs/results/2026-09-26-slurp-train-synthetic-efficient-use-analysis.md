# Using SLURP `train_synthetic` efficiently: construction only, on cost, and the ceiling is 18 items

Date: 2026-09-26. Read id `SAEA-SLURP-TRAIN-SYNTHETIC-EFFICIENT-USE-V1`, recipe `slurp-train-synthetic-efficient-use-v1`, schema `saea-slurp-train-synthetic-efficient-use-v1`. Script `scripts/analysis/slurp_train_synthetic_efficient_use.py` renders every number below from the artefacts in section 0; two runs differ only in the payload timestamp.

**Zero contacts.** No model, server, tokenizer, encoder, embedder, scorer, ASR, network, GPU or paid-API contact; 0 audio seconds. Tools: `python` reads of the governed SLURP label files, three released snapshots, the sealed bad-case bank, two sealed per-sample official score files and committed roster receipts, plus `git`. **No synthetic audio file was opened.** `train_synthetic`'s audio is TTS and is refused by this study's research boundary ("Human speech and its linguistic content only"), so only the text and label side enters here; nothing below proposes synthesising, encoding, embedding or supplying that audio, and a reader who expects an OBS-side use of the 69,253 synthetic recordings will not find one.

**Counts, types and ids only.** No utterance text, sentence, transcript, delivered text, gold filler value or knowledge body text is printed or persisted. Fillers and sentences enter set arithmetic in memory and leave it as integers; the entity-masked sentence patterns are counted and never emitted, not even as a hash. Gold is used offline as a scoring key exactly as `core.scoring_batch` uses it.

**A DIAGNOSTIC, never a gate.** It admits nothing, releases no store, registers no cell, expands no source and authorises no flight. Fold A and DEV-2000-ADDED numbers are development numbers (owner decisions 28 and 86) and are never a test claim.

## The answer, first

**1. The route question, with my own opening premise corrected.** A text-only row cannot be a QUERY -- `rails.phase_supply.QUERY_SIGNAL_MODALITIES` is `("speech", "speech+state")` and `assert_query_signal_declares_speech` refuses a non-speech `query_source` before the file is opened -- but a knowledge row does not need to be a query. It needs to be a KEY, and **the key side of every SLURP store is already text**, by design: `kb_policy.multidim_recall` scores the row's own speech embedding against the store facet's TEXT embedding in the same 2048-d space, and the comment at `phase_supply.py:167` says so outright -- "the KEY (facet) side is deliberately UNCONSTRAINED: a key is knowledge text and always has been". So the speech key is **not** an impossibility for this material, and a reader told otherwise would be misled. The obstacle is a price, and it is this: a facet with no row in the sealed, hash-pinned facet-vector file is silently skipped (`.get(...)` then `continue`, no error, no fallback, no receipt field), so admitting these rows means a fresh TEXT-EMBEDDING PASS over 15,703 of them -- a real encoder contact -- a re-cut sealed facet-vector file, and a re-pin of the 55 baselines that pin the exemplar vectors. The new entries would then compete on PURE COSINE (`w_cos 1.0`, the other two weights zeroed) against 9,354 incumbents, with no mechanism that prefers them. Against section 3's ceiling that price is not worth paying. The one channel that needs no vector at all is `slot-contracts-v2`, selected by `intent_bindings[].intent_id` through a static per-intent index with no embedding anywhere on the path -- and it is almost empty (section 4). **Recommendation: construction-side only, on cost rather than on impossibility.**

**2. The honest upper bound is 18 gold items, and most of the apparent bound is contamination.** Of 675 missed (false-negative) gold entity items on the entity-error rows of the two sealed PLAN rosters, 81 carry a (type, filler) pair that is absent from the released exemplar pool **and** present in the retained `train_synthetic` slice. But 63 of those 81 are supplied only by a retained row that is the evaluated utterance itself -- same `slurp_id`, or the same normalised sentence re-synthesised. Handing a scored row its own gold back is leakage, not knowledge. Excluding it leaves **18 items**, whose exact pooled SLU-F1 ceiling is train-fold-a +0.83 pp, dev2000-added +0.59 pp. That is the ceiling to quote for any admission -- not ENTITY-MIXED's +17.43 / +16.47, which is the ceiling of repairing that whole class by any means.

**3. What it buys is difference, not volume -- and one published figure needs correcting.** The 2026-09-26 coverage read proved volume is not the lever (count-versus-error-rate R^2 0.07-0.14, the sign flipping between class families, quartile curves with no knee), so this material is only worth anything as *different* material. It supplies 6,135 entity-masked sentence patterns and 446 (type, filler) pairs TRAIN does not hold. But the survey figure "fillers for 11 of the 12 thinnest entity types" reads as more than it is: measured here, 11 of the 12 thinnest types receive retained ROWS, while only **1** gains a filler value TRAIN does not already have (1 new pair(s) in total across all twelve). The thin types get support, not vocabulary.

## 0. Inputs and identity

| Artefact | Relpath under `SPEECHRL_DATA_DIR` | sha256 | Rows |
| --- | --- | --- | ---: |
| | `datasets/slurp/metadata/train.jsonl` | `4a05a3de6c7f028a` | 11,514 |
| | `datasets/slurp/metadata/devel.jsonl` | `00d346b183ecc2d1` | 2,033 |
| | `datasets/slurp/metadata/test.jsonl` | `fe3449af69b42fda` | 2,974 |
| | `datasets/slurp/metadata/train_synthetic.jsonl` | `8394ac2573e1d72b` | 19,711 |
| | `knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json` | `fcb5506c63653abe` | -- |
| | `knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/snapshot.json` | `f549466f22bb0cae` | -- |
| | `knowledge/slurp/semantic/slot-contracts-v2/snapshot.json` | `a48ed83eb7878e9e` | -- |
| | `analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl` | `26231b86b86f3525` | -- |
| train-fold-a PLAN `scores.json` | `runs/<run id>/<attempt>/` | `9f3047fa77a868cb` | 1,080 |
| dev2000-added PLAN `scores.json` | `runs/<run id>/<attempt>/` | `1ac4402afce13528` | 1,000 |

Each arm's sealed per-sample rows were re-pooled and had to reproduce that arm's own sealed official SLU-F1 and span-F1 to 1e-6 before any table was built, and every bank row's `gold_entity_types` had to agree with the governed gold read here, or the read refuses. Released pool: 9,354 exemplar values over 37,407 source recordings, joining to 9,354 TRAIN utterances and 3,650 distinct (type, filler) pairs; the minus-R01 sibling holds 8,554. `slot-contracts-v2` holds 54 entries, one per slot type. The pool already excludes Fold A, Fold B and DEV-1000 utterances, which is why the two PLAN rosters may pin the full pool.

## 1. What the filter admits (table 1)

Re-run here rather than cited: drop every `train_synthetic` row whose `slurp_id` **or** whose normalised sentence occurs in devel or test. 15,703 of 19,711 rows survive (79.7 %); 3,206 go on the `slurp_id` and a further 802 on the sentence key alone. Devel recurrence is 1,317 of 2,033 (64.8 %) and the test side 1,889 of 2,974 (63.5 %). The 2026-09-26 source survey reported 15,705 retained and 6,382 new sentences against this read's 15,703 and 6,368; the gap is two rows and 14 sentences and it is the sentence normaliser, not the filter -- this read's is NFKC, case-folded, punctuation-to-space, whitespace-collapsed, stated in the script so the number is reproducible.

Against TRAIN: 6,368 normalised sentences and 6,135 entity-masked patterns are new, while 9,229 retained rows (58.8 %) carry a sentence TRAIN already holds -- those are re-synthesised prompts and add nothing but a duplicate. 446 (type, filler) pairs are absent from TRAIN and 724 from the released pool (the pool is smaller than TRAIN because it excludes the fold rosters, so the second number is the larger one). The 9 intent keys outside TRAIN's label space are `general_affirm`, `general_commandstop`, `general_confirm`, `general_dontcare`, `general_explain`, `general_negate`, `general_praise`, `general_repeat`, `qa_query`; the survey measured 0 devel and 0 test `scenario_action` keys absent from TRAIN, so they buy nothing the task is scored on and they are not a fix for INTENT-UNCOVERED.

Per entity type, the 18 leading types by new-vs-store fillers; the full table and the full per-intent table (60 scored keys plus the 9 unscored) are in the payload. `store` counts distinct fillers the released pool holds for the type.

| Slot type | TRAIN fillers | store fillers | retained rows | synth fillers | new vs TRAIN | new vs store |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `person` | 468 | 431 | 1,359 | 537 | 126 | 153 |
| `business_name` | 213 | 169 | 611 | 243 | 49 | 80 |
| `place_name` | 482 | 424 | 870 | 428 | 36 | 63 |
| `definition_word` | 179 | 168 | 322 | 196 | 39 | 50 |
| `food_type` | 156 | 95 | 212 | 129 | 6 | 49 |
| `radio_name` | 106 | 96 | 121 | 106 | 25 | 33 |
| `email_address` | 23 | 22 | 97 | 48 | 25 | 26 |
| `currency_name` | 52 | 51 | 240 | 75 | 24 | 24 |
| `date` | 289 | 270 | 1,401 | 235 | 14 | 24 |
| `event_name` | 351 | 325 | 758 | 271 | 13 | 24 |
| `media_type` | 91 | 74 | 722 | 86 | 6 | 21 |
| `news_topic` | 122 | 98 | 124 | 92 | 7 | 17 |
| `time` | 237 | 208 | 522 | 176 | 8 | 16 |
| `personal_info` | 41 | 38 | 155 | 50 | 10 | 13 |
| `song_name` | 103 | 97 | 100 | 86 | 11 | 13 |
| `list_name` | 79 | 62 | 126 | 57 | 2 | 12 |
| `weather_descriptor` | 104 | 88 | 228 | 86 | 2 | 10 |
| `artist_name` | 130 | 127 | 165 | 107 | 7 | 8 |
| *38 remaining types, summed* | 931 | 807 | 2,183 | 692 | 36 | 88 |

## 2. The 12 thinnest entity types, before and after (table 2)

"Thinnest" is the source survey's own definition: a TRAIN entity type holding fewer than 10 distinct fillers. This is the table the value claim was resting on, and it does not carry it: 11 of 12 types receive retained rows but only 1 gains a filler TRAIN does not have, and 4 gain one the released pool does not have. Read it beside the 2026-09-26 coverage read, which found the 12 types the pool shows at most ten times carry 13 gold mentions (0.7 %), 10 FN (1.2 %) and 22 FP (2.3 %) of the two rosters' mass -- no zero-coverage class carries any error mass to recover.

| Slot type | TRAIN fillers (before) | store fillers | + new from synth | after (TRAIN + new) | retained rows | has contract |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `game_type` | 1 | 1 | 0 | 1 | 0 | yes |
| `music_album` | 1 | 0 | 0 | 1 | 1 | no |
| `transport_agency` | 3 | 3 | 0 | 3 | 22 | yes |
| `alarm_type` | 4 | 4 | 0 | 4 | 7 | yes |
| `sport_type` | 4 | 4 | 0 | 4 | 5 | yes |
| `email_folder` | 5 | 5 | 0 | 5 | 65 | yes |
| `meal_type` | 5 | 3 | 0 | 5 | 60 | yes |
| `audiobook_author` | 6 | 6 | 0 | 6 | 1 | yes |
| `drink_type` | 8 | 5 | 0 | 8 | 7 | yes |
| `transport_descriptor` | 8 | 7 | 0 | 8 | 5 | yes |
| `transport_name` | 8 | 5 | 1 | 9 | 7 | yes |
| `movie_type` | 9 | 9 | 0 | 9 | 9 | yes |

## 3. Where it lands against the measured error mass (table 3)

One row per sealed entity-error class per roster. `missed items` are the row's gold entities whose TYPE the sealed bank records as a false negative -- the only items a new filler VALUE could repair, which is why ENTITY-FP-ONLY contributes none. `absent AND in synth` is the naive upper bound; `self re-synthesis` is the part of it supplied only by a retained row that IS the evaluated utterance (same `slurp_id`, or its sentence re-synthesised), which is leakage; **`clean` is the honest upper bound.**

| Roster | Class | Rows | Missed items | Items, type thickened | Items, value absent | Items, absent AND in synth | Items, self re-synthesis | **Items, clean** | Rows, clean | Of those, STABLE-WRONG |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train-fold-a | `ENTITY-FN-ONLY` | 84 | 87 | 85 | 16 | 7 | 7 | **0** | 0 | 0 |
| train-fold-a | `ENTITY-FP-ONLY` | 131 | 0 | 0 | 0 | 0 | 0 | **0** | 0 | 0 |
| train-fold-a | `ENTITY-MIXED` | 193 | 261 | 259 | 125 | 65 | 56 | **9** | 9 | 9 |
| dev2000-added | `ENTITY-FN-ONLY` | 65 | 75 | 75 | 20 | 2 | 0 | **2** | 2 | 2 |
| dev2000-added | `ENTITY-FP-ONLY` | 108 | 0 | 0 | 0 | 0 | 0 | **0** | 0 | 0 |
| dev2000-added | `ENTITY-MIXED` | 195 | 252 | 243 | 114 | 7 | 0 | **7** | 7 | 7 |

The exact pooled ceiling of repairing every row that carries at least one such item, by the bad-case bank's own identity (a repaired row delivers gold: `tp -> tp + fn`, `fp -> 0`, `fn -> 0`, every other row of the roster untouched):

| Roster | SLU-F1 now | Naive rows | Naive ceiling, SLU pp | **Clean rows** | **Clean ceiling, SLU pp** | Clean span-F1 pp | Clean STABLE-WRONG rows | Ceiling, SLU pp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train-fold-a | 63.63 | 69 | +6.07 | **9** | **+0.83** | +1.09 | 9 | +0.83 |
| dev2000-added | 65.40 | 9 | +0.59 | **9** | **+0.59** | +0.87 | 9 | +0.59 |

**Read this as a disappointment, because it is one, and note where the two rosters diverge.** Fold A's naive column is by far the larger, and that is an artefact of what Fold A is: a TRAIN roster, whose utterances the exemplar pool deliberately excludes, so its gold fillers are 'absent from the store' by design -- and whose prompts `train_synthetic` re-synthesises, so the slice can hand a Fold A row its own gold. DEV-2000-ADDED cannot have that defect, because the filter removes every devel row from the slice first. The clean column is the comparable one and it is small on both. Three prior measurements say the same thing from three directions: the 2026-09-26 coverage read puts mode (i) *absent knowledge* at 2 items in 2,705 rows at TYPE level, leaves 92-100 % of entity items in the delivered-but-ignored-or-misused residual, and shows mode (iii) *budget-excluded* is 0 rows and 0 values. This read asks the same question one grain finer, at VALUE level, and gets the same shape of answer. **The entity half of the SLURP loss is a USE failure, and no source expansion reaches a use failure.**

## 4. How it could enter, and what each route costs (table 4)

Token costs are quoted from two committed measurements made on the pinned tokenizer at registered contacts -- the 2026-09-19 M1 exemplar-compression analysis and the 2026-09-26 supply-dedup measurement -- and this read makes no tokenizer contact of its own. The per-item figures are **~37 tokens for one supplied exemplar** (737 tokens for a 20-line block at a measured 3.63 chars/token) and **~395 tokens for one slot-contract card** (mean 2,028.6 chars at 5.13 chars/token), inside a 7,240-token supply block and a ~9,906-token Solver row. The dedup note's k-sweep agrees at the margin: 10 / 20 / 30 exemplars render 6,898.6 / 7,271.3 / 7,520.0 Solver-block tokens, about 31 tokens per additional exemplar once the block's fixed scaffolding is already paid.

| Route | What it populates | How retrieval reaches it | Token cost at supply time | What goes wrong |
| --- | --- | --- | --- | --- |
| A. Extra exemplar-store entries -- the B1/M1 route, this programme's largest admitted supply gain (+12.61 SLU); the locked plan supplies **k=20** per row, not the top-5 a diagnostic figure suggests | the 9,354-entry `size-pool-annotated-exemplars` pool, one `KeyFacet` and one `ValueBundle` per utterance, 1:1 | **Possible, at a price.** The facet is a TEXT embedding, so these rows can be keyed -- but only after a fresh text-embedding pass over 15,703 rows -- over their TEXT, never over their refused TTS audio -- a re-cut sealed facet-vector file and a re-pin of the 55 baselines. Until then each is silently skipped, and a value whose `task_target` is unset is skipped by the fuser too | **~37 tokens per supplied exemplar** (committed: 737 tokens for a 20-line block at 3.63 chars/token, the densest text in the request) on a 9,906-token row | The pass is the cheap part. The entries then compete on pure cosine (`w_cos 1.0`) against 9,354 incumbents with nothing preferring them, and the k-sweep already showed that 20 genuinely new exemplar bodies per row moved +0.07 / +0.09 pp -- nothing. Plus the snapshot hash changes and re-pins every downstream readiness package |
| B. Slot-contract filler inventories -- typed values per slot, not examples | the 54 `slot-contracts-v2` entries, one per slot type, `facet_id == value_id == "slot-contract:<slot_id>"` | **Yes, and with no vector at all.** `_released_candidate_index` builds a static `{intent_id: value_ids}` map from the authored rows and `select_candidate_semantic_values` visits the row's at most 3 Perception candidates round-robin. No embedding, no cosine, no `query_source` on this path | **~395 tokens per card** (committed: mean 2,028.6 chars at 5.13 chars/token), about 12 cards per row = ~4,855 tokens, **49 % of the row** -- by far the most expensive route | 54 of 55 types already have a contract and the one gap (`music_album`) carries 1 gold mention and 1 FN of 1,881 and 824. 90.6 % of the card characters already describe slot types neither the core nor the annotation used, so lengthening bodies feeds the wrong end. And re-authoring a card is a MODEL contact: `candidate_semantic_supply` rebuilds the snapshot from the authored source and demands byte equality |
| C. Negative / contrastive material for the confusable pairs | `intent-boundaries-v1`, 60 cards, one per intent, top-8 retrieved | **Possible, same price as A** -- its facets come from a text-facet encoding protocol (`saea-text-facet-encoding-protocol-v1`, 60 facets, passage prompt), so a new card needs that pass re-run and re-pinned | ~800 tokens for the 8-card block at 7.53 chars/token, so ~100 tokens per card on a 1,091-token Perception block | This is the route the error mass argues for -- retrieval owns 55-64 % of the intent errors and INTENT-UNCOVERED carries +5.4 / +6.8 SLU and +12.0 / +16.9 intent -- but it needs the confusable PAIR, not a corpus, and the leading confusions (`general_quirky`, `calendar_query`, `play_music`) already sit on the most exemplar-rich intents. This read measures no contrastive gain and claims none |
| D. Construction-side material only, never supplied at runtime | an offline text/label pool a card author, a contract author or a rollout proposer reads | n/a -- it never enters a retrieval path, so no vector, no pass and no re-pin | **0 tokens at supply time, 0 encoder contacts, 0 re-pins** | Bounded by what construction can do with it, which section 3 caps at 18 items; and it must stay disjoint from every roster it is used beside (section 5) |

**Recommended route: D, construction-side only -- on cost, not on impossibility.** A and C are reachable: their keys are text and a text-embedding pass would key these rows. They are refused here because the price (an encoder pass over 15,703 rows, a new sealed vector file, a re-pin of 55 baselines) is paid against an 18-item ceiling, and because the one time this programme bought 20 genuinely new exemplar bodies per row the result was +0.07 / +0.09 pp. B needs no vector at all and is the cheapest to reach and the most expensive to carry -- ~395 tokens a card, 49 % of the row already -- and its gap is one slot type with one gold mention. D is the only route whose cost is zero on every axis, and its value is bounded by the use failure it cannot fix.

## 5. Disjointness and hygiene

The filter's own proof: of the 15,703 retained rows, 0 share a `slurp_id` with devel, 0 with test and 0 share a normalised sentence with either -- zero on all three by construction, which is what makes the filter a proof rather than a hope. 7,473 retained rows share a `slurp_id` with TRAIN and 9,229 share a sentence with it: the slice is mostly TRAIN prompts re-synthesised, which is exactly why section 3's self-re-synthesis column exists.

| Construction roster / pool | Utterances | Retained rows sharing a `slurp_id` | Retained rows sharing a normalised sentence |
| --- | ---: | ---: | ---: |
| R01C (`slurp-stage3-construction-r01c.json`) | 625 | 452 | 543 |
| Fold A (`slurp-evo-fold-a-v2.json`) | 1,080 | 449 | 593 |
| Fold B (`slurp-evo-fold-b-v2.json`) | 1,080 | 532 | 675 |
| exemplar draw (`slurp-evo-exemplars-v2.json`) | 430 | 230 | 290 |

**What must be true for the slice to stay legal beside those rosters.** The construction-versus-knowledge guard is `rails.runner.run_speech_native_agent_loop`, which refuses when a flown roster's sample ids intersect the bound snapshot's own `source_sample_ids`, and again when BUILD and USE share a `split_identity_hash`. It bit once (2026-09-23: 175 R01 utterances were sources of the composed stores, which is why R01C and `size-pool-annotated-exemplars-minus-r01` exist). Four conditions follow, and the devel/test filter satisfies none of them.

1. **The guard compares ids, not sentences, so it would not see this hazard at all.** The table above is the number that must be carried into any registration, per roster: a slice used beside Fold A must have that roster's sentence column at zero, not merely its id column. Identity-level disjointness passing while a sentence is shared is precisely the leakage section 3 measures.
2. **The committed receipt cannot prove the sentence half.** `docs/receipts/knowledge/slurp-split-identity.json` pins devel and test at recording identity only -- its own note says scenario, action, entities, tokens and sentence "are never read" -- so the 79.7 % retention is not reproducible from it. A frozen normalised-sentence receipt would have to be minted, and none exists.
3. **TRAIN exclusions propagate.** A retained row shares its `slurp_id` with a TRAIN utterance, so the fold builders' standing exclusion of every TRAIN utterance this study has already touched (739 named by the committed probe-sample receipts) carries over to the synthetic twin of that utterance.
4. **The legality row must change first.** `analysis/information_audit_specs.py` still reads `"train_synthetic split": "forbidden"` in `_SLURP_CORPUS_STRUCTURE_LEGALITY` -- correct for the undecontaminated split, wrong for this slice. Nothing may read the split until a successor value says `construction-only-knowledge for the decontaminated slice`, and because that table is descriptive rather than executable the loader path in `slurp_spec` has to change with it or the two will disagree silently.

## 6. Recommendation, and the no-harm gate it would need

**Do not admit it as runtime supply and do not open a store for it.** Admit it, if at all, as an offline construction-side text/label pool, under owner decision 127's terms for an engineering-base item: sound logic, a stated ceiling, a no-harm reading, `claims_benefit: false`, and a preregistered harm margin equal to the measured floor of its own design. The ceiling to state is this read's own question-2 number and not the headroom table's: **train-fold-a +0.83 pp, dev2000-added +0.59 pp** from 18 clean gold items across both rosters, against ENTITY-MIXED's +17.43 / +16.47 which belongs to any repair of that class by any means. A construction-side pool touches no arm, so its no-harm design is the offline sealed-pool floor of 0.67 pp rather than the 1.2485 / 1.2525 cross-flight floors; note that `scripts/checks/stage3_effect_floor_check.py` has no no-harm design and no harm-margin field yet, so today `claims_benefit: false` only relaxes the gate and a declared margin would be trusted rather than checked -- decision 127's instruction to teach that check is still open, and a base item should not be flown under it before it is.

**The smallest first step, and it costs no flight and no contact:** amend the one legality row and mint the one receipt it needs. Concretely -- change `_SLURP_CORPUS_STRUCTURE_LEGALITY`'s `train_synthetic` entry to name the decontaminated slice as `construction-only-knowledge`, with this read's filter as its receipt; freeze a normalised-sentence identity receipt for devel and test beside `slurp-split-identity.json` so the filter is reproducible from committed bytes; and record the per-roster sentence-overlap column above as the hygiene condition any consumer must meet. That is a legality edit plus a receipt plus a check. It unblocks every offline use, it commits no store, no cell and no flight, and it can be undone. Only if a construction step then NAMES a specific thin type or a specific confusable pair it wants material for does the question of a store arise -- and on section 3's measurement it should not, because the items are single digits.

## 7. What this read does not say

It states no effectiveness, superiority or generalisation claim, admits nothing, releases no store, expands no source and authorises no flight. The ceilings are exact upper bounds on a PERFECT repair of the rows they name, by any means, and are not a forecast: a filler value appearing in a supplied exemplar is not the same as the Solver using it. It does not measure whether a value the store already holds reached the failing row -- that is mode (ii), and it belongs to the 2026-09-26 coverage read, which owns the finding that retrieval rather than absence is the binding constraint. It says nothing about `train_synthetic`'s audio except that the boundary refuses it, and proposes no use for it. The per-item token costs are quoted from a committed measurement, not measured here. Every roster is a discovery or dev roster and every number is a development number.

Machine-readable payload: `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-TRAIN-SYNTHETIC-EFFICIENT-USE-V1/payload.json` (schema `saea-slurp-train-synthetic-efficient-use-v1`, recipe `slurp-train-synthetic-efficient-use-v1`) -- the full per-type and per-intent tables, ids, counts and hashes only, no text and no filler value.
