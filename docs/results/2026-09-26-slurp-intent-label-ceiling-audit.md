# SLURP intent label ceiling: the maximum intent accuracy attainable under gold as it stands

Date: 2026-09-26. Read id `SAEA-SLURP-MF-INTENT-LABEL-CEILING-AUDIT-V1`, recipe `slurp-intent-label-ceiling-audit-v1`. Generated `2026-09-27T00:06:37+00:00`.

The measurement owner decision 137 made a prerequisite of treating 95 per cent as a distance. A model-free read: zero model, server, tokenizer, encoder, embedder, ASR, scorer, network, GPU and paid-API contacts. Every number is arithmetic over the governed SLURP annotation bytes, three committed roster receipts and one sealed analysis artefact, all sha256-pinned below. **The test split stays closed** -- `test.jsonl` is never opened, hashed or counted, so the census covers `train` and `devel` only and no number here is a test claim. Gold is read offline into aggregate tables and reaches no runtime path. No utterance text, sentence text, transcript, token surface, gold filler or delivered text is printed or persisted: sentence identity enters as a group key consumed in-process and discarded, and every cell below is an intent id, a count, a rate or a hash. A DIAGNOSTIC, never a gate -- it registers no cell, admits no mechanism, releases no store, proposes no mechanism and authorises no flight.

## 0. What was read

| Artefact | Path | sha256 |
| --- | --- | --- |
| governed SLURP `train` annotations | `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/datasets/slurp/metadata/train.jsonl` | `4a05a3de6c7f028aff298c4a90196e6a3fecd1938d96fb1c125d6fd10d5e301e` |
| governed SLURP `devel` annotations | `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/datasets/slurp/metadata/devel.jsonl` | `00d346b183ecc2d160853cd3dc20e8ccd207d9e1809cf6e2c05182076bd0ecc9` |
| sealed bad-case bank (Fold A PLAN arm per-row classes) | `$SPEECHRL_DATA_DIR/analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl` | `26231b86b86f35251fed2b7d7c59bf33e8806b5ef71739b74bf9d5bc2b8a3ccf` |
| roster receipt `roll1-r01c` | `docs/receipts/rosters/slurp-stage3-construction-r01c.json` | `e8abc65ba4626cccb4aae9d2eb1bd73f077a6e9a407b3dba9c18bbe4c03eeddd` |
| roster receipt `train-fold-a` | `docs/receipts/rosters/slurp-evo-fold-a-v2.json` | `1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d` |
| roster receipt `dev2000-added` | `docs/receipts/rosters/slurp-dev-2000-added-v1.json` | `f78dd8ad2894b1fd02bfe6050e39e3fb2c5d178a649e5d20e85ea4ecf4b8dc58` |

Gold intent is the COMPUTED `f"{scenario}_{action}"` pair, exactly what `data.slurp._parse_record` builds, never the governed jsonl's own occasionally inconsistent `intent` field. The metadata directory is resolved through the loader's own `data.slurp._governed_roots` against the umbrella lock, never a hardcoded path.

## 1. Label determinacy from the corpus itself

Three MECHANICAL sentence keys, loosest last, each a deterministic function of the corpus's own `tokens[].surface` sequence -- lowercased, non-alphanumeric characters (the apostrophe excepted) removed, empty tokens dropped. `sequence` is the token order, `bag` the order-insensitive multiset, `set` the order- and repetition-insensitive set. No judgement of this read's enters any of them. A group is COLLIDING when one key carries two or more different gold intents; `min loss` is the honest floor -- inside such a group the best any function of the sentence can do is answer the group's most frequent gold, so every other member is wrong, and a tie resolves in the system's favour because this is an upper bound.

Counted in **utterances**:

| Key | Scope | rows | distinct keys | colliding groups | rows affected | min loss | corpus ceiling % |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `sequence` | train | 11,514 | 11,482 | 3 | 6 | 3 | 99.9739 |
| `sequence` | devel | 2,033 | 2,031 | 0 | 0 | 0 | 100.0000 |
| `sequence` | train+devel | 13,547 | 13,505 | 4 | 8 | 4 | 99.9705 |
| `bag` | train | 11,514 | 11,432 | 3 | 6 | 3 | 99.9739 |
| `bag` | devel | 2,033 | 2,030 | 0 | 0 | 0 | 100.0000 |
| `bag` | train+devel | 13,547 | 13,434 | 5 | 10 | 5 | 99.9631 |
| `set` | train | 11,514 | 11,428 | 4 | 8 | 4 | 99.9653 |
| `set` | devel | 2,033 | 2,028 | 0 | 0 | 0 | 100.0000 |
| `set` | train+devel | 13,547 | 13,423 | 6 | 12 | 6 | 99.9557 |

Counted in **recordings**:

| Key | Scope | rows | distinct keys | colliding groups | rows affected | min loss | corpus ceiling % |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `sequence` | train | 50,628 | 11,482 | 3 | 46 | 16 | 99.9684 |
| `sequence` | devel | 8,690 | 2,031 | 0 | 0 | 0 | 100.0000 |
| `sequence` | train+devel | 59,318 | 13,505 | 4 | 103 | 21 | 99.9646 |
| `bag` | train | 50,628 | 11,432 | 3 | 46 | 16 | 99.9684 |
| `bag` | devel | 8,690 | 2,030 | 0 | 0 | 0 | 100.0000 |
| `bag` | train+devel | 59,318 | 13,434 | 5 | 116 | 27 | 99.9545 |
| `set` | train | 50,628 | 11,428 | 4 | 58 | 22 | 99.9565 |
| `set` | devel | 8,690 | 2,028 | 0 | 0 | 0 | 100.0000 |
| `set` | train+devel | 59,318 | 13,423 | 6 | 128 | 33 | 99.9444 |

**The answer this census gives.** Sentence-level label ambiguity in SLURP is effectively absent. At the strictest key the whole `train` split holds 3 colliding groups over 11,482 distinct sentences, and `devel` holds 0. At the LOOSEST mechanical key -- the token set, which merges sentences no reader would call the same string -- the pooled `train+devel` ceiling is still 99.9444 per cent by recording. Pooling the splits is the harsher reading, because it also counts a sentence carrying one intent in `train` and another in `devel`; it adds 2 groups and no more. `devel` on its own is exactly determinate at every key. Of the 6 pooled colliding groups, 6 are exact ties by utterance, so the bound gives the system the benefit and charges only the corpus's own duplicate mass.

The colliding intent-id pairs, pooled, at the loosest key (group counts):

| Intent id A | Intent id B | groups |
| --- | --- | ---: |
| `calendar_query` | `recommendation_events` | 1 |
| `calendar_remove` | `transport_taxi` | 1 |
| `calendar_set` | `play_music` | 1 |
| `general_greet` | `general_quirky` | 1 |
| `general_greet` | `play_radio` | 1 |
| `recommendation_movies` | `takeaway_order` | 1 |

## 2. The catch-all's geometry

`general_quirky` is the intent the rank diagnostic named as a catch-all: it owns 25.5-31.4 per cent of all not-delivered intent-wrong rows and misses on 39/45 and 45/51 rows there. If that behaviour were LABEL arbitrariness, it would show as sentence collisions. It does not. Both columns are the maximum over the three keys.

| Scope | `general_quirky` gold rows | sentence-identical to a different-intent row | rows of another intent sentence-identical to one of these (reverse) |
| --- | ---: | ---: | ---: |
| train | 555 | 0 | 0 |
| devel | 105 | 0 | 0 |
| train+devel | 660 | 1 | 1 |

Within either split, zero in both directions at every key. Pooling the two splits finds exactly 1 `general_quirky` utterance whose normalised sentence is also carried by one `general_greet` utterance in the other split -- the single cross-split collision section 1's pair table lists. So the catch-all is not a duplicate-label problem: it accounts for one colliding group in the entire corpus, and its other 659 gold utterances share a normalised sentence with nothing.

Because the hard test returns essentially zero, the NEAR-identical test is reported next. It is a SOFT signal and never a cap: two sentences can differ by a single token and still be unambiguously different intents, so a near neighbour bounds nothing. Jaccard is over token sets, against every other utterance of a different intent in the same split.

| Split | gold rows | J>=1.0 | J>=0.9 | J>=0.8 | J>=0.7 | J>=0.6 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 555 | 0 (0.00 %) | 0 (0.00 %) | 5 (0.90 %) | 7 (1.26 %) | 35 (6.31 %) |
| devel | 105 | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | 1 (0.95 %) |

The nearest different-intent partner of a `general_quirky` row in `train`, at J>=0.6, as intent-id pairs and counts:

| Intent id A | Intent id B | rows |
| --- | --- | ---: |
| `general_greet` | `general_quirky` | 6 |
| `calendar_query` | `general_quirky` | 4 |
| `calendar_set` | `general_quirky` | 3 |
| `general_quirky` | `news_query` | 3 |
| `datetime_query` | `general_quirky` | 2 |
| `general_joke` | `general_quirky` | 2 |
| `general_quirky` | `iot_coffee` | 2 |
| `general_quirky` | `qa_definition` | 2 |
| `general_quirky` | `recommendation_events` | 2 |
| `cooking_recipe` | `general_quirky` | 1 |
| `email_querycontact` | `general_quirky` | 1 |
| `general_quirky` | `lists_query` | 1 |

**What that structure says.** The catch-all's residual is not label arbitrariness in the sense this section can cap: even at J>=0.6, a threshold that merges sentences sharing barely half their tokens, only 35 of 555 `train` rows and 1 of 105 `devel` rows have a different-intent near neighbour at all. Whatever makes the catch-all hard, it is not that the corpus labels the same sentence two ways.

## 3. The attainable ceiling, per roster

Three readings of the same bound, strictest last. **roster-local** groups only the roster's own rows, the most generous reading because a system evaluated on one roster could in principle specialise to it. **split-consistent** forms the group over the whole split the roster is drawn from, the honest reading for a deterministic function of the audio: it does not know which rows are in the roster. **pool-consistent** forms it over `train`+`devel` together, the harshest reading available without opening the test split. `tied` counts rows inside a 1-1 group, which the bound resolves in the system's favour.

| Roster | rows | scope | in a colliding group | tied | rows a system must lose | ceiling % |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| `roll1-r01c` | 625 | roster-local | 0 | 0 | 0 | 100.0000 |
| `roll1-r01c` | 625 | split-consistent | 0 | 0 | 0 | 100.0000 |
| `roll1-r01c` | 625 | pool-consistent | 0 | 0 | 0 | 100.0000 |
| `train-fold-a` | 1080 | roster-local | 0 | 0 | 0 | 100.0000 |
| `train-fold-a` | 1080 | split-consistent | 3 | 3 | 0 | 100.0000 |
| `train-fold-a` | 1080 | pool-consistent | 4 | 4 | 0 | 100.0000 |
| `dev2000-added` | 1000 | roster-local | 0 | 0 | 0 | 100.0000 |
| `dev2000-added` | 1000 | split-consistent | 0 | 0 | 0 | 100.0000 |
| `dev2000-added` | 1000 | pool-consistent | 1 | 1 | 0 | 100.0000 |

That table uses the LOOSEST key. The stricter two give the same or a higher ceiling on every roster and every scope:

| Roster | scope | `sequence` % | `bag` % | `set` % |
| --- | --- | ---: | ---: | ---: |
| `roll1-r01c` | roster-local | 100.0000 | 100.0000 | 100.0000 |
| `roll1-r01c` | split-consistent | 100.0000 | 100.0000 | 100.0000 |
| `roll1-r01c` | pool-consistent | 100.0000 | 100.0000 | 100.0000 |
| `train-fold-a` | roster-local | 100.0000 | 100.0000 | 100.0000 |
| `train-fold-a` | split-consistent | 100.0000 | 100.0000 | 100.0000 |
| `train-fold-a` | pool-consistent | 100.0000 | 100.0000 | 100.0000 |
| `dev2000-added` | roster-local | 100.0000 | 100.0000 | 100.0000 |
| `dev2000-added` | split-consistent | 100.0000 | 100.0000 | 100.0000 |
| `dev2000-added` | pool-consistent | 100.0000 | 100.0000 | 100.0000 |

**This is an upper bound from ONE cause only.** It counts sentence-level gold ambiguity and nothing else. It does not count annotation error, scenario/action boundary disagreement between two sentences that are not token-identical, audio that is unintelligible, an entity the scorer reads differently, or any other reason a row might be unanswerable. **The true attainable ceiling is at or below every number in this table.** What the table settles is one direction only: sentence-level ambiguity does not put the ceiling below 95, because it does not put it below 100.0000 on any roster this programme uses, nor below 99.9444 on the pooled corpus. One consequence of the tie rule should not be oversold: every colliding group touching these rosters is a 1-1 tie, so a 100.0000 roster figure means a system may be right on the roster row only at the cost of the partner row outside it -- which is exactly why the corpus-level census in section 1 reads 99.94 to 99.97 rather than 100.

Soft near-identity for the same rosters, the same non-binding signal section 2 reports:

| Roster | rows | J>=1.0 | J>=0.9 | J>=0.8 | J>=0.7 | J>=0.6 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `roll1-r01c` | 625 | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | 5 (0.80 %) |
| `train-fold-a` | 1080 | 3 (0.28 %) | 3 (0.28 %) | 5 (0.46 %) | 22 (2.04 %) | 110 (10.19 %) |
| `dev2000-added` | 1000 | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | 14 (1.40 %) |

## 4. Where the lock arm's error actually sits against that ceiling

The locked v2.0 PLAN arm on TRAIN Fold A, read off the sealed bad-case bank: 192 of 1080 rows carry a wrong intent, so intent accuracy is 82.2222 per cent, reproducing decision 137's own 82.2222 to four decimal places. The 192 wrong rows are partitioned by CAUSE against the pool-consistent loosest-key groups, in a fixed precedence so the classes are mutually exclusive and exhaustive: a row inside a colliding group is classified there first, then a row touching the catch-all in either direction, then the remainder.

| Class | rows | pp of the roster | what it means |
| --- | ---: | ---: | --- |
| `UNWINNABLE` | 0 | 0.00 | gold is a MINORITY label inside a colliding sentence group -- no function of the sentence can be right here |
| `AMBIGUOUS-BUT-MAJORITY` | 0 | 0.00 | inside a colliding group, but gold IS the group's most frequent label -- winnable, though the group is ambiguous |
| `CATCH-ALL` | 36 | 3.33 | gold or delivered is `general_quirky` -- conceded in full below, although section 2 finds no label cause for it |
| `OURS` | 156 | 14.44 | neither cause applies -- the part that is genuinely the system's |
| **total wrong** | **192** | **17.78** | accuracy 82.2222 |

Both label classes are empty for a reason worth stating: 4 Fold A rows sit in a pooled colliding group at all, every one of them is a 1-1 tie, and the lock arm answered 4 of them CORRECTLY. Sentence-level ambiguity therefore removes nothing from this arm's error.

The catch-all class as a gold -> delivered confusion structure between intent ids:

| gold intent id | delivered intent id | rows |
| --- | --- | ---: |
| `general_quirky` | `qa_factoid` | 6 |
| `general_quirky` | `general_joke` | 4 |
| `general_quirky` | `audio_volume_up` | 3 |
| `general_quirky` | `news_query` | 3 |
| `general_quirky` | `qa_definition` | 3 |
| `general_quirky` | `cooking_recipe` | 2 |
| `general_quirky` | `iot_cleaning` | 2 |
| `general_quirky` | `recommendation_movies` | 2 |
| `audio_volume_mute` | `general_quirky` | 1 |
| `general_quirky` | `general_greet` | 1 |
| `general_quirky` | `music_likeness` | 1 |
| `general_quirky` | `music_query` | 1 |
| `general_quirky` | `play_game` | 1 |
| `general_quirky` | `qa_currency` | 1 |
| `general_quirky` | `recommendation_events` | 1 |
| `general_quirky` | `recommendation_locations` | 1 |

**The arithmetic the owner asked for.** The gap from the lock arm to the absolute target is 12.78 points, which is 54 rows of 1080 still allowed to be wrong at 95 per cent against the 192 wrong today. Label ambiguity accounts for 0 of them. Even if the ENTIRE catch-all class were conceded as permanently unreachable -- which section 2 gives no label-side reason to do -- the best attainable accuracy would still be 96.6667 per cent, above the target; and 156 rows (14.44 points) would remain available to recover against the 12.78 points needed.

## 5. The published reference line

Quoted, not recomputed, from the pinned scoring-alignment audit `docs/readiness/2026-09-04-scoring-alignment-audit-slurp-earnings.md` (its own citations are Bastianelli et al., EMNLP 2020, arXiv:2011.13205, Table 7, and He & Garner, arXiv:2305.13512):

| Published system | intent accuracy % | condition |
| --- | ---: | --- |
| Gold/HerMiT | 84.84 | gold transcripts, test split -- the published TEXT-side bound |
| Multi-SLURP/HerMiT | 78.33 | strong trained ASR-to-NLU pipeline, test split |
| Google/SF-ID | 72.06 | weak commercial pipeline, test split |
| ChatGPT, 0-shot prompt-only | 79.25 | oracle transcripts, 60 intents (He & Garner) |

So 95 sits about 10 points above the highest published intent accuracy in this record and about 5 points below this read's own label-side ceiling. Both reference lines are given without editorial: the field has not published 95 on SLURP intent, and nothing in the labels forbids it.

## 6. The answer, in one sentence

**95 per cent intent accuracy is BELOW the label ceiling on every roster this programme uses** -- the sentence-level ceiling is 100.0000 per cent on all three rosters and 99.9444 per cent on the pooled corpus, so the owner's caveat is not what stands between the system and the target. What remains is ours: 12.78 points to recover on TRAIN Fold A, of which 0.00 points are unwinnable under gold, 3.33 points sit on the `general_quirky` catch-all for reasons section 2 shows are NOT label duplication, and 14.44 points are plainly system error. The target is reachable arithmetically even conceding the whole catch-all, and it is a composition problem, not a dataset problem.

One thing this read does not say. It bounds ONE cause. A sentence-level ceiling near 100 is consistent with a lower true ceiling from a cause this read did not measure -- annotation error, unintelligible audio, or scorer-side disagreement. What it rules out is the specific hypothesis decision 137 recorded: that duplicate or arbitrary sentence-level labelling puts 95 out of reach. It does not.

## 7. Boundary

This read makes no model, server, tokenizer, encoder, embedder, ASR, scorer, network, GPU or paid-API contact; it registers no cell, admits no mechanism, releases no store, draws no roster, proposes no mechanism, opens no split beyond `train` and `devel`, and authorises no flight. The test split was not opened. Every number is a development number (owner decisions 28 and 86) and none is a test claim or an effectiveness, superiority or generalisation claim.
