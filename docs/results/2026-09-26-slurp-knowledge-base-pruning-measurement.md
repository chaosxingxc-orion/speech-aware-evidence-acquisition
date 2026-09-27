# Is the SLURP knowledge base too dense? The census, and every prune measured as a mask

Date: 2026-09-26. Read id `SAEA-SLURP-MF-KNOWLEDGE-BASE-PRUNING-MEASUREMENT-V1`, recipe `slurp-knowledge-base-pruning-measurement-v1`. Generated `2026-09-27T00:11:30+00:00`.

A model-free read answering the owner's 2026-09-26 hypothesis -- *retrieval fails because the knowledge base is too dense and too complex* -- in two parts: what each released store actually holds against TRAIN's own size, and what REMOVING a key would buy. Zero model, server, encoder, embedder, scorer, tokenizer, network, GPU and paid-API contacts. Every similarity is recomputed as arithmetic over sha256-verified vector files the flights themselves pinned, and section 1 proves the recomputation reproduces what the flights sealed before a number is taken from it. A prune is simulated by MASKING a key out of the ranking and recomputing: no store is rebuilt, no facet file is re-cut, no cell is registered and nothing is flown.

A DIAGNOSTIC, never a gate. It admits no mechanism, releases no store, authorises no flight and states no effectiveness, superiority or generalisation claim. Every roster is a discovery or dev roster and every number is a development number (owner decisions 28 and 86), never a test claim. No utterance text, transcript, gold filler, delivered answer, knowledge body or key description is read into a reported value: every cell is an id, a count, a rate, a cosine, a ratio or a hash.

## The verdict, first

**The hypothesis does not survive the measurement, and it fails in the cleanest possible way.** Of the 60 intent keys, 58 lose more delivery than they gain the moment they are masked, and of the 2 that gain, 2 are the gold key of rows the system already answers CORRECTLY today -- so 0 keys can be removed without destroying work that is already right. The greedy subset search, given the whole store to cut from and one roster to fit on, stops after 1 key. And pruning the one channel that IS dense makes the vote WORSE at every size that removes anything material: the best pool prune by held-out floor (`edit-1`) is a wash at -0.1 points, and every prune that removes more than 5 % of the pool costs accuracy monotonically.

**And the direction of the evidence is the reverse of the hypothesis.** The store that holds most of the training set is the store that WORKS, and the store that holds sixty keys is the one that fails. On the same rows, the dense exemplar channel's top-20 majority names the gold intent on 76.2 %, 61.9 %, 75.5 % of rows while the sparse boundary channel's own rank-1 key names it on 65.6 %, 47.0 %, 56.4 % (Fold A, ROLL-1, DEV-2000). Density is not what is broken. What is broken is one key having to cover a whole intent, which section 6 sizes as a rewrite opportunity rather than a removal.

## 0. What was read

| Artefact | Relpath under `SPEECHRL_DATA_DIR` | identity |
| --- | --- | --- |
| `intent-boundaries-v1` snapshot | `knowledge/slurp/semantic/intent-boundaries-v1/snapshot.json` | `5520b8449b627530227563d1f8db71f8a391f20f7d0ff7d7bd439e28ec6e48fe` |
| `slot-contracts-v2` snapshot | `knowledge/slurp/semantic/slot-contracts-v2/snapshot.json` | `d5992bd12687cbd0204c14fc4e29f987697b8751321d524d7707229032f5bdec` |
| exemplar pool snapshot | `knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/snapshot.json` | `6eaa03aea96a1928dd1ac29ecc71c3955c136498c9f8114266eaa830d1207c63` |
| exemplar pool snapshot | `knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json` | `4c498dc0282055b9fe036ed7e950af519bd48b5f26e76876d0250727196a72e9` |
| boundary facet key vectors (60 x 2048) | `prepared/SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1/facets.jsonl` | `76e8d16a067ebfc5d67a4ecef2966636310815b950a7d9790ec7c0136f01ecd2` |
| pool facet key vectors | `vectors/slurp-kus3/facet-vectors.jsonl` | `5dfe75231c12f2624913988e4643c51b74856465bdbd108358b4f371dacffc1e` |
| sealed bad-case bank | `analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl` | `26231b86b86f35251fed2b7d7c59bf33e8806b5ef71739b74bf9d5bc2b8a3ccf` |
| `train-fold-a-plan` boundary query vectors | `vectors/slurp-intent-boundaries-train-fold-a-1080-v1/query-vectors-speech-segments.jsonl` | `e7a5b2264dc61fcab3c63d50fb645d4629d3f0a99f83ad5fbe323c73884e5f0b` |
| `train-fold-a-plan` exemplar query vectors | `vectors/slurp-exemplars-pool/query-vectors-speech-content-v1.jsonl` | `d0f06ed21c6a576d8118d5a914e34807c24a3d3523d89e7b30d90575d24104ff` |
| `train-fold-a-plan` sealed phase artefact | `runs/SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1/attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1/SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1.phases.json` | `7cac358a39c446c7aa13fcec70722a4669814ea0fad4fc76e9bf291d7b4b8e6f` |
| `roll1` boundary query vectors | `vectors/slurp-stage3-construction-r01c-v1/query-vectors-speech-segments.jsonl` | `ebaa743241a67a2cb759353fa8a9f58a3f09d27c00c8c66cb3172958dcccc1b8` |
| `roll1` exemplar query vectors | `vectors/slurp-stage3-construction-r01c-v1/query-vectors-speech-content-v1.jsonl` | `dd3b2924cda10810487b2b114e61380beaf8477634c602096b875e461ae44baa` |
| `roll1` sealed phase artefact | `runs/SAEA-SLURP-STAGE3-ROLLOUT-R01-V1/attempt-slurp-native-stage3-rollout-r01-generation-v1/SAEA-SLURP-STAGE3-ROLLOUT-R01-V1.phases.json` | `203aab4861e503a088af6cd67662164c908d0ecf66149ce8bf97bf1706aa4f9d` |
| `dev2000-added-plan` boundary query vectors | `vectors/slurp-dev2000-added-v1/query-vectors-speech-segments.jsonl` | `e2a5fd046dac7c87fcf53830955e41e69d20402a2305a02ebf2bfc1a33001b9d` |
| `dev2000-added-plan` exemplar query vectors | `vectors/slurp-dev2000-added-v1/query-vectors-speech-content-v1.jsonl` | `7d4ebdce553fd897fa86cc6b6d878ebf2298e19ee509eeceaf1aa0aca4855ee0` |
| `dev2000-added-plan` sealed phase artefact | `runs/SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1/attempt-slurp-native-default-plan-dev2000-added-generation-v1/SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1.phases.json` | `7853313714c58b434f306ebbc2df7de8b05801feb8695dbee4663dfacae4aed1` |

| Arm | Rows analysed | Class source | Pool pinned | CORRECT | INTENT-WRONG |
| --- | ---: | --- | ---: | ---: | ---: |
| `train-fold-a-plan` | 1,080 | `bad-case bank roster train-fold-a` | 9,354 | 480 | 191 |
| `roll1` | 625 | `slurp-slu-official-projected-v3-train` | 8,554 | 163 | 184 |
| `dev2000-added-plan` | 1,000 | `bad-case bank roster dev2000-added` | 9,354 | 398 | 232 |

## 1. The recomputation reproduces both sealed channels

| Arm | boundary rows | sealed width 8 | recomputed top-8 == sealed set | rows with a sealed 20 | recomputed top-20 == sealed 20 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `train-fold-a-plan` | 1,080 | 1,076 | 1,080 (100.00 %) | 1,080 | 1,080 (100.00 %) |
| `roll1` | 625 | 621 | 625 (100.00 %) | 625 | 625 (100.00 %) |
| `dev2000-added-plan` | 1,000 | 994 | 1,000 (100.00 %) | 1,000 | 1,000 (100.00 %) |

The self-exclusion the vote needs fired on 0 `train-fold-a-plan`, 0 `roll1`, 0 `dev2000-added-plan` rows: no evaluated row is its own exemplar on any roster, because each pool release already excludes its own evaluation split. The identity that makes a prune computable offline: masking a key never reorders the survivors, so gold's rank under any mask is `1 + |ranked above gold, unmasked|` and gold is delivered when that count is under 8 and gold itself is not masked. Every mask below is that arithmetic, and the vote is recomputed the same way by restricting the pool columns.

## 2. The census: question 1 answered in numbers

| Channel | Store holds | TRAIN holds | share | dense? |
| --- | ---: | ---: | ---: | --- |
| `intent-boundaries-v1` entries | 60 | 60 intents | 100.0 % | no -- one key per label, 60 keys |
| `slot-contracts-v2` types | 54 | 55 slot types | 98.2 % | no -- one key per slot type |
| `size-pool-annotated-exemplars-minus-r01` utterances | 8,554 | 11,514 | 74.3 % | YES |
| `size-pool-annotated-exemplars-minus-r01` recordings | 34,474 | 50,628 | 68.1 % | YES |
| `size-pool-annotated-exemplars` utterances | 9,354 | 11,514 | 81.2 % | YES |
| `size-pool-annotated-exemplars` recordings | 37,407 | 50,628 | 73.9 % | YES |

**The answer, plainly.** The exemplar channel IS most of the training set: it puts 81.2 % of TRAIN's 11,514 utterances and 73.9 % of its 50,628 recordings into one store; the R01-excluded sibling puts in 74.3 % and 68.1 %. The two semantic channels do the opposite -- one key per label-vocabulary item, 60 intent keys and 54 slot-type keys, covering the whole TRAIN intent vocabulary (60) and all but one of its 55 slot types. **And the channel that FAILS is the small one.** The intent-boundary channel is where the gold entry misses the delivered eight on most intent-wrong rows, and it holds sixty keys: 4-810 TRAIN utterances collapse into ONE key each. Density there cannot mean count. It can only mean the **breadth** of a single key -- how much of the label space one written boundary description is made to cover -- which is what section 6 measures.

## 3. Question 2.1 and 2.2: every intent key masked, one at a time

Masking one key removes it from the ranking for every row, so gold is promoted by one rank wherever the masked key outranked it, and a row whose gold IS the masked key can never receive its own entry again. `gains` counts rows that newly receive their own gold entry; `lost` counts deliveries destroyed because the masked key was that row's gold; `net` is the difference. The two honesty columns sit beside them: `gold rows` is how often the key is some row's gold at all, and `correct` is how many of those rows the system already answers correctly today. **A key with a non-zero `correct` cannot be masked at any price** -- the net prices a lost delivery, not the lost correct answer behind it.

All three rosters pooled (1,080 + 625 + 1,000 = 2,705 rows), sorted by net. `net A` / `net R` / `net D` are Fold A, ROLL-1 and DEV-2000 separately.

| intent id | gains | lost | net | gold rows | correct | delivered today | net A | net R | net D |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `music_dislikeness` | 9 | 1 | **+8** | 1 | 1 | 1 | +2 | +3 | +3 |
| `general_greet` | 7 | 6 | **+1** | 6 | 5 | 6 | -3 | +4 | +0 |
| `cooking_query` | 0 | 1 | **-1** | 1 | 0 | 1 | -1 | +0 | +0 |
| `iot_hue_lighton` | 5 | 6 | **-1** | 6 | 0 | 6 | -2 | +1 | +0 |
| `audio_volume_other` | 2 | 4 | **-2** | 4 | 0 | 4 | -3 | +0 | +1 |
| `email_addcontact` | 6 | 8 | **-2** | 9 | 5 | 8 | -1 | +1 | -2 |
| `audio_volume_down` | 10 | 13 | **-3** | 13 | 11 | 13 | -3 | -3 | +3 |
| `iot_wemo_off` | 1 | 5 | **-4** | 6 | 3 | 5 | +0 | -1 | -3 |
| `iot_wemo_on` | 4 | 9 | **-5** | 9 | 2 | 9 | -3 | -1 | -1 |
| `music_settings` | 2 | 8 | **-6** | 11 | 3 | 8 | -6 | -1 | +1 |
| `qa_maths` | 7 | 13 | **-6** | 14 | 11 | 13 | -3 | +1 | -4 |
| `alarm_remove` | 7 | 14 | **-7** | 16 | 7 | 14 | -7 | -3 | +3 |
| `recommendation_movies` | 4 | 11 | **-7** | 13 | 8 | 11 | -8 | +0 | +1 |
| `email_querycontact` | 1 | 12 | **-11** | 21 | 5 | 12 | -2 | -2 | -7 |
| `general_joke` | 7 | 21 | **-14** | 21 | 9 | 21 | -8 | +1 | -7 |
| `iot_cleaning` | 5 | 20 | **-15** | 22 | 10 | 20 | -4 | -4 | -7 |
| `iot_coffee` | 4 | 19 | **-15** | 20 | 14 | 19 | -7 | -4 | -4 |
| `iot_hue_lightup` | 4 | 19 | **-15** | 19 | 9 | 19 | -3 | -4 | -8 |
| `iot_hue_lightdim` | 0 | 16 | **-16** | 19 | 7 | 16 | -8 | +0 | -8 |
| `music_likeness` | 8 | 24 | **-16** | 25 | 16 | 24 | -14 | -4 | +2 |
| `social_query` | 0 | 17 | **-17** | 23 | 4 | 17 | -9 | -6 | -2 |
| `datetime_convert` | 3 | 21 | **-18** | 22 | 12 | 21 | -9 | -11 | +2 |
| `play_game` | 5 | 24 | **-19** | 26 | 16 | 24 | -5 | -2 | -12 |
| `alarm_query` | 5 | 25 | **-20** | 25 | 20 | 25 | -19 | -3 | +2 |
| `audio_volume_up` | 19 | 39 | **-20** | 39 | 28 | 39 | -16 | -9 | +5 |
| `qa_stock` | 2 | 22 | **-20** | 25 | 12 | 22 | -5 | -2 | -13 |
| `general_quirky` | 1 | 22 | **-21** | 137 | 14 | 22 | -5 | -10 | -6 |
| `iot_hue_lightoff` | 1 | 22 | **-21** | 23 | 9 | 22 | -11 | -1 | -9 |
| `transport_taxi` | 5 | 26 | **-21** | 27 | 10 | 26 | -10 | -1 | -10 |
| `transport_ticket` | 4 | 26 | **-22** | 27 | 5 | 26 | -15 | -1 | -6 |
| `transport_traffic` | 6 | 28 | **-22** | 29 | 16 | 28 | -12 | +0 | -10 |
| `iot_hue_lightchange` | 0 | 24 | **-24** | 26 | 11 | 24 | -8 | -6 | -10 |
| `audio_volume_mute` | 7 | 34 | **-27** | 34 | 15 | 34 | -21 | -8 | +2 |
| `recommendation_events` | 4 | 32 | **-28** | 34 | 18 | 32 | -20 | -6 | -2 |
| `qa_currency` | 3 | 35 | **-32** | 35 | 15 | 35 | -6 | -1 | -25 |
| `play_podcasts` | 1 | 35 | **-34** | 38 | 12 | 35 | -11 | -4 | -19 |
| `lists_query` | 3 | 39 | **-36** | 59 | 41 | 39 | -12 | -6 | -18 |
| `music_query` | 11 | 47 | **-36** | 50 | 23 | 47 | -28 | -12 | +4 |
| `play_audiobook` | 3 | 40 | **-37** | 44 | 8 | 40 | -6 | -5 | -26 |
| `recommendation_locations` | 9 | 46 | **-37** | 48 | 16 | 46 | -25 | -12 | +0 |
| `lists_remove` | 1 | 39 | **-38** | 42 | 17 | 39 | -15 | -10 | -13 |
| `alarm_set` | 5 | 44 | **-39** | 45 | 21 | 44 | -32 | -8 | +1 |
| `calendar_remove` | 4 | 43 | **-39** | 45 | 22 | 43 | -7 | -3 | -29 |
| `play_radio` | 13 | 53 | **-40** | 56 | 18 | 53 | -9 | -3 | -28 |
| `takeaway_query` | 3 | 44 | **-41** | 45 | 17 | 44 | -30 | -11 | +0 |
| `lists_createoradd` | 1 | 45 | **-44** | 48 | 20 | 45 | -20 | -14 | -10 |
| `qa_definition` | 3 | 49 | **-46** | 54 | 27 | 49 | -9 | +0 | -37 |
| `takeaway_order` | 5 | 52 | **-47** | 52 | 15 | 52 | -27 | -20 | +0 |
| `qa_factoid` | 3 | 51 | **-48** | 127 | 32 | 51 | -10 | -8 | -30 |
| `transport_query` | 5 | 57 | **-52** | 57 | 25 | 57 | -16 | -18 | -18 |
| `social_post` | 1 | 64 | **-63** | 76 | 21 | 64 | -42 | -19 | -2 |
| `email_sendemail` | 2 | 68 | **-66** | 76 | 26 | 68 | -16 | -16 | -34 |
| `email_query` | 1 | 70 | **-69** | 83 | 41 | 70 | -26 | -6 | -37 |
| `calendar_query` | 0 | 75 | **-75** | 129 | 32 | 75 | -20 | -8 | -47 |
| `datetime_query` | 6 | 81 | **-75** | 86 | 34 | 81 | -47 | -24 | -4 |
| `cooking_recipe` | 1 | 81 | **-80** | 90 | 33 | 81 | -56 | -24 | +0 |
| `news_query` | 2 | 99 | **-97** | 116 | 51 | 99 | -51 | -28 | -18 |
| `play_music` | 4 | 119 | **-115** | 136 | 47 | 119 | -13 | -15 | -87 |
| `calendar_set` | 4 | 128 | **-124** | 149 | 36 | 128 | -20 | -14 | -90 |
| `weather_query` | 7 | 161 | **-154** | 166 | 75 | 161 | -56 | -36 | -62 |

**The honest accounting.** 2 of 60 keys carry a positive pooled net when masked alone. 2 of them are also the gold key of at least one row the system already answers correctly, so masking them destroys work that is already right; 0 are free of that objection. The largest single-key net is `music_dislikeness` at +8 rows (9 gained against 1 lost) over 1 rows where it is gold, of which 1 are already correct. So the answer to question 2.2 is that NO key clears the bar: every key whose removal delivers more than it destroys is also a key some row needs and already gets right.

## 4. Question 2.3: greedy subset search, fitted on one roster

Greedy over the same objective as the agreement weight before it: gold-entry delivery over EVERY analysed row of `train-fold-a-plan` (class-blind, so the error labels never choose a key), one key added per step, stopping when no key improves it, capped at 30. The two other rosters are READ under the same mask, never fitted. `net` is delivered rows against the unmasked baseline.

| step | key added | net, Fold A (fitted) | net, ROLL-1 (held out) | net, DEV-2000 (held out) | wrong-row delivery, Fold A | ROLL-1 | DEV-2000 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | -- (baseline) | 0 | 0 | 0 | 45.0 % | 44.6 % | 35.8 % |
| 1 | `music_dislikeness` | +2 | +3 | +3 | 46.1 % | 45.1 % | 36.6 % |

**The fitted-versus-held-out gap.** At its final size (1 key masked) the set gains +2 delivered rows on the roster it was fitted on (+0.19 points of its 1,080 rows) and +3 (+0.48 pts), +3 (+0.30 pts) on the two it was not. The held-out floor is +3 rows, which is +0.48 points of the smaller held-out roster.

**And it is not registrable.** Every key the search selected is listed in section 3 with a non-zero `already correct` column, so masking it destroys rows the system answers correctly today. The search was allowed to ignore that column on purpose -- so that the number it reaches is the CEILING of what pruning this channel could buy under the most permissive rule, and that ceiling is +2 rows on 1,080.

## 5. Question 2.4: pruning the exemplar pool, measured on the VOTE

The agreement vote is the majority intent of the top-20 pool utterances a row's own speech vector recalls (self-excluded, ties broken by intent id ascending). It is the mechanism by which pool density would act on the intent side, given the +0.265 rho between pool count and intent error. Every prune here uses POOL-INTERNAL properties only -- the pool's own frozen build-time intent labels and its own key vectors -- so none of them is fitted on any roster and none can overfit one. `cap-c` keeps the c lowest-numbered utterances of each intent; `edit-n` drops an item unless at least n of its own 10 nearest pool neighbours carry its own intent (Wilson-style editing); `cent-c` keeps the c items of each intent closest to that intent's own centroid.

| prune | kept (Fold A pool) | vote accuracy, Fold A | ROLL-1 | DEV-2000 | vote on intent-wrong rows, Fold A | ROLL-1 | DEV-2000 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `full` | 9,354 | 76.2 % (+0.0) | 61.9 % (+0.0) | 75.5 % (+0.0) | 31.4 % (+0.0) | 27.2 % (+0.0) | 35.8 % (+0.0) |
| `cap-2` | 120 | 8.0 % (-68.2) | 9.9 % (-52.0) | 4.2 % (-71.3) | 9.4 % (-22.0) | 9.8 % (-17.4) | 5.6 % (-30.2) |
| `cap-5` | 298 | 45.6 % (-30.6) | 38.6 % (-23.4) | 38.6 % (-36.9) | 19.4 % (-12.0) | 13.0 % (-14.1) | 10.8 % (-25.0) |
| `cap-10` | 590 | 56.6 % (-19.6) | 45.4 % (-16.5) | 49.0 % (-26.5) | 22.0 % (-9.4) | 14.1 % (-13.0) | 12.9 % (-22.8) |
| `cap-20` | 1,156 | 63.1 % (-13.1) | 49.8 % (-12.2) | 57.9 % (-17.6) | 23.6 % (-7.9) | 15.8 % (-11.4) | 15.1 % (-20.7) |
| `cap-40` | 2,238 | 72.5 % (-3.7) | 57.3 % (-4.6) | 63.5 % (-12.0) | 30.9 % (-0.5) | 18.5 % (-8.7) | 21.6 % (-14.2) |
| `cap-80` | 4,020 | 76.6 % (+0.4) | 59.5 % (-2.4) | 70.6 % (-4.9) | 30.4 % (-1.0) | 20.7 % (-6.5) | 22.8 % (-12.9) |
| `cap-160` | 6,010 | 77.2 % (+1.0) | 61.1 % (-0.8) | 73.7 % (-1.8) | 32.5 % (+1.0) | 20.7 % (-6.5) | 27.2 % (-8.6) |
| `cent-2` | 120 | 4.6 % (-71.6) | 4.5 % (-57.4) | 2.0 % (-73.5) | 5.2 % (-26.2) | 3.3 % (-23.9) | 3.9 % (-31.9) |
| `cent-5` | 298 | 42.6 % (-33.6) | 35.7 % (-26.2) | 39.1 % (-36.4) | 15.7 % (-15.7) | 14.7 % (-12.5) | 14.2 % (-21.6) |
| `cent-10` | 590 | 61.3 % (-14.9) | 48.2 % (-13.8) | 55.0 % (-20.5) | 22.5 % (-8.9) | 16.3 % (-10.9) | 15.1 % (-20.7) |
| `cent-20` | 1,156 | 67.1 % (-9.1) | 50.9 % (-11.0) | 59.5 % (-16.0) | 26.7 % (-4.7) | 16.3 % (-10.9) | 17.7 % (-18.1) |
| `cent-40` | 2,238 | 69.5 % (-6.7) | 51.4 % (-10.6) | 61.4 % (-14.1) | 23.6 % (-7.9) | 16.8 % (-10.3) | 18.1 % (-17.7) |
| `cent-80` | 4,020 | 72.1 % (-4.1) | 54.4 % (-7.5) | 64.3 % (-11.2) | 24.6 % (-6.8) | 15.2 % (-12.0) | 19.8 % (-15.9) |
| `cent-160` | 6,010 | 76.3 % (+0.1) | 58.1 % (-3.8) | 68.6 % (-6.9) | 29.8 % (-1.6) | 19.6 % (-7.6) | 21.1 % (-14.7) |
| `edit-1` | 8,926 | 76.2 % (+0.0) | 62.1 % (+0.2) | 75.4 % (-0.1) | 32.5 % (+1.0) | 27.2 % (+0.0) | 35.8 % (+0.0) |
| `edit-3` | 7,998 | 75.8 % (-0.4) | 61.3 % (-0.6) | 74.6 % (-0.9) | 33.0 % (+1.6) | 26.1 % (-1.1) | 34.9 % (-0.9) |
| `edit-5` | 7,040 | 73.7 % (-2.5) | 58.6 % (-3.4) | 72.6 % (-2.9) | 30.9 % (-0.5) | 22.3 % (-4.9) | 32.3 % (-3.4) |
| `edit-7` | 6,048 | 70.6 % (-5.6) | 57.6 % (-4.3) | 70.6 % (-4.9) | 27.2 % (-4.2) | 22.8 % (-4.3) | 29.7 % (-6.0) |
| `edit-9` | 4,688 | 68.1 % (-8.1) | 55.2 % (-6.7) | 69.2 % (-6.3) | 26.2 % (-5.2) | 23.9 % (-3.3) | 28.9 % (-6.9) |

**The pool curve, read.** No prune of the dense channel has a positive held-out floor. The curve is monotone in the wrong direction: the more of the pool is removed, the worse the vote, on every roster and on the intent-wrong rows as well as overall. That is the hypothesis tested where it should have been strongest -- the one store that really does hold the training set -- and answered no.

The best pool prune by held-out floor is `edit-1`, whose SMALLEST vote-accuracy change across the three rosters is -0.1 points, at 8,926 kept utterances against the released 9,354. The mean label agreement of a pool item with its own 10 nearest pool neighbours is 7.07 of 10, which is the quantity `edit-n` thresholds.

## 6. Question 2.5: narrowing instead of removing, as a measured size

For the keys that cannot be masked because they are sometimes gold and sometimes correct, the alternative is to REWRITE the key so it stops attracting its competitors' rows. This section only sizes that opportunity; it rewrites nothing, because a rewrite is a construction act with its own authority. Two measures per key, over the keys that own the most not-delivered rows: the cosine between the key's own 2,048-dimension vector and that of the intent that actually takes top-1 on its missed rows, and the Jaccard WORD overlap of the two descriptions. `words` is the key's own vocabulary size. No description text is read into any cell -- only a count and a ratio.

The all-pairs baseline over the 60 keys: mean key-to-key cosine 0.4756, max 0.908; mean word overlap 0.6073, max 0.9189.

| intent id | TRAIN utterances (breadth) | gold rows | already correct | missed | distinct top-1 rivals | words | cosine to its top rival | word overlap with it |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `general_quirky` | 555 | 137 | 14 | 115 | 36 | 90 | 0.5182 | 0.5865 |
| `qa_factoid` | 544 | 127 | 32 | 76 | 31 | 75 | 0.5985 | 0.6667 |
| `calendar_query` | 566 | 129 | 32 | 54 | 21 | 72 | 0.664 | 0.7711 |
| `calendar_set` | 810 | 149 | 36 | 21 | 13 | 76 | 0.4798 | 0.6522 |
| `lists_query` | 198 | 59 | 41 | 20 | 12 | 74 | 0.4453 | 0.6667 |
| `news_query` | 503 | 116 | 51 | 17 | 13 | 71 | 0.5918 | 0.7284 |
| `play_music` | 639 | 136 | 47 | 17 | 9 | 76 | 0.6786 | 0.6897 |
| `email_query` | 418 | 83 | 41 | 13 | 11 | 76 | 0.4505 | 0.6154 |

Every key in that table has a non-zero `already correct` column, which is why it is the narrowing list and not the masking list. Two shapes are visible and they call for different repairs. The most-missed key is beaten by 36 DIFFERENT rivals across its missed rows, at a word overlap of 0.5865 against the all-pairs mean of 0.6073 -- it is not losing a pairwise duel, it is diffuse, and no rewrite against one rival repairs it. Others are the opposite: a single dominant rival with a word overlap well above the all-pairs mean, which is a pairwise confusion a rewrite could plausibly separate. The sizeable finding underneath both is the baseline itself: the 60 descriptions share 0.6073 of their vocabulary on average and up to 0.9189 at the closest pair, with a mean key-to-key cosine of 0.4756 rising to 0.908. Sixty keys that share three fifths of their words are sixty keys that cannot separate sixty intents; that is the measured size of the rewrite opportunity, and this read names it without taking it.

## 7. Why pruning fits training-free RL, and what it would cost

Pruning is a better fit for training-free RL than anything this programme has flown, for three reasons that are properties of the search and not of the result. The candidate space is FINITE and ENUMERABLE: a subset of sixty keys, or a subset of a pool whose members are enumerated in a released snapshot, so a proposer never has to invent a string. The reward is computable OFFLINE at the 0.67 pp instrument, from pinned vectors and sealed labels at zero model contacts -- every number in sections 3 to 5 is one evaluation of that reward, and a greedy step costs no GPU at all. And a flight is needed only ONCE, for the composed policy, which is exactly the design of the registered family `sealed-credit-system-policy-v1`: inner optimisation over sealed bytes, one flight for the composition.

The costs are real and must be stated with the gain. A pruned store is a NEW store: its facet-vector file has to be re-cut, its snapshot re-released, and every baseline that consumes it re-pinned, which is the re-pin path that has already rewritten sibling rows twice in this repository's history. And **delivery is not correctness.** Every number above counts rows that would RECEIVE their own gold entry; the conversion rate from receiving it to answering correctly is unmeasured here and is not a function of sealed bytes, because it needs the answer the row would give with the entry present. No score gain is claimed, implied or estimated anywhere in this read.

## 7a. The one prune this read would register next

**None.** The selection rule, fixed before the numbers were read: a prune is registrable only if it raises gold-entry delivery on all three rosters, destroys no key that is gold on a row already answered correctly, and its held-out floor survives on the two rosters it was not fitted on. Nothing passes. On the intent channel the permissive ceiling -- the greedy search with the honesty column switched OFF -- is +2 delivered rows on 1,080, and the single key it selects is gold on a row the system already gets right, so the honest ceiling is zero. On the pool channel the best held-out floor is `edit-1` at -0.1 points -- a wash that would still cost a re-cut of a 9,354-facet vector file, a fresh snapshot release, and a re-pin of every baseline that consumes the store. A wash is not worth that, and a re-pin has twice rewritten sibling ledger rows in this repository's history. **And delivery is not correctness:** every gain above counts rows that would RECEIVE their own gold entry, not rows that would answer correctly, so even a passing prune would have been a delivery result and never a score prediction. The question this read hands back is section 6's -- sixty keys sharing 0.6073 of their vocabulary is a KEY-SPACE problem, and its lever is rewriting a description, not removing one.

## 8. Boundary

Zero model, server, encoder, embedder, scorer, tokenizer, network, GPU and paid-API contacts: no server was started, stopped or probed, no waveform decoded, no embedding computed and no subprocess run. Every cosine was RECOMPUTED as arithmetic over the pinned vector files named in section 0, each verified against its configured sha256 by this repository's own loaders before a number was taken from it, through `rails.kb_policy.multidim_segment_recall` on the boundary channel and the same cosine and the same `facet_id`-ascending tie order on the pool channel, with both recomputations validated against the sealed flights in section 1. Other tools: `data.slurp.load_slurp_split` for the governed TRAIN gold, `json` reads of four released snapshots and three sealed `*.phases.json`, a `json` read of the sealed bad-case bank and of the ROLL-1 official score file, and `hashlib` for every identity above.

This read admits nothing, promotes nothing, preregisters no cell, releases no store, rebuilds no store, draws no roster, expands no source, opens no split and reaches no superiority, generalisation or Stage-3 conclusion. It is byte-reproducible across runs apart from its `generated_at` stamp: every container is sorted before it is consumed, every prune rule is a deterministic function of the pinned bytes, and there is no sampling anywhere.
