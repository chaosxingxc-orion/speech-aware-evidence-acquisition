# SLURP boundary keys: are the written descriptions the weak link, and do TRAIN-utterance keys close the gap?

Date: 2026-09-27. Read id `SAEA-SLURP-MF-BOUNDARY-KEY-CONSTRUCTION-DIAGNOSTIC-V1`, recipe `slurp-boundary-key-construction-diagnostic-v1`. Generated `2026-09-27T00:56:18+00:00`.

A model-free read. Zero model, server, encoder, embedder, scorer, tokenizer, network, GPU and paid-API contacts. Every cosine is recomputed as arithmetic over sha256-verified vector files the flights pinned, and section 1 proves the recomputation reproduces the sealed delivered set on every row before a number is taken from it. A candidate key is a construction over ALREADY-PINNED utterance vectors -- a mean, or a pinned vector chosen by arithmetic -- so nothing is encoded. A DIAGNOSTIC, never a gate: it admits nothing, releases and rebuilds no store, registers no cell and states no effectiveness claim. Every roster is a discovery or dev roster and every number is a development number (owner decisions 28 and 86). **Every number below is DELIVERY, never correctness.** No utterance text, transcript, gold filler, knowledge body or key description is read into a reported value: every cell is an id, a count, a rank, a rate, a cosine, a ratio or a hash.

## The answer, first

**The written descriptions are the weak link: a key built from TRAIN utterances puts gold first, and delivers it, more often on every roster.** On the intent-wrong rows the written key puts gold at rank 1 on 4.7 % / 3.3 % / 3.9 % (Fold A / ROLL-1 / DEV-2000) and delivers it within eight on 45.0 % / 44.6 % / 35.8 %; the `centroid` key puts gold at rank 1 on 23.0 % / 14.7 % / 17.2 % and delivers it on 71.2 % / 64.7 % / 66.8 %. Over ALL rows gold is at rank 1 on 65.6 % / 47.0 % / 56.4 % with the written key and 65.7 % / 54.1 % / 62.5 % with `centroid`. Each of those reads is held out: the construction pool of every roster excludes that roster's own rows (section 5).

**And one correction to the framing this read inherited.** The text the boundary channel actually ENCODES as its key is the facet representation -- 84 characters per intent on average, whose sha256 matches the encoding receipt on 60 of 60 -- not the 702-character delivered body on which the pruning read measured its 0.6073 word overlap (that body matches the receipt on 0 of 60). Section 6 gives both overlaps. The key that fails is a one-line description, and the body the Solver reads is untouched by any key change here.

## 0. What was read, and why the two key spaces are comparable

| Artefact | Relpath under `SPEECHRL_DATA_DIR` | identity |
| --- | --- | --- |
| `intent-boundaries-v1` snapshot | `knowledge/slurp/semantic/intent-boundaries-v1/snapshot.json` | `5520b8449b627530227563d1f8db71f8a391f20f7d0ff7d7bd439e28ec6e48fe` |
| boundary facet key vectors (60 x 2048) | `prepared/SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1/facets.jsonl` | `76e8d16a067ebfc5d67a4ecef2966636310815b950a7d9790ec7c0136f01ecd2` |
| boundary key encoding receipt | `prepared/SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1/index.json` | `f70cf26726143151e360015bf9a5c4b0922c9e1e9ecc0177878f9b5c77674dab` |
| exemplar pool snapshot (8,554 utterances) | `knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/snapshot.json` | `6eaa03aea96a1928dd1ac29ecc71c3955c136498c9f8114266eaa830d1207c63` |
| exemplar pool snapshot (9,354 utterances) | `knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json` | `4c498dc0282055b9fe036ed7e950af519bd48b5f26e76876d0250727196a72e9` |
| pool facet key vectors (one per TRAIN utterance) | `vectors/slurp-kus3/facet-vectors.jsonl` | `5dfe75231c12f2624913988e4643c51b74856465bdbd108358b4f371dacffc1e` |
| sealed bad-case bank | `analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl` | `26231b86b86f35251fed2b7d7c59bf33e8806b5ef71739b74bf9d5bc2b8a3ccf` |
| `train-fold-a-plan` speech query vectors | `vectors/slurp-intent-boundaries-train-fold-a-1080-v1/query-vectors-speech-segments.jsonl` | `e7a5b2264dc61fcab3c63d50fb645d4629d3f0a99f83ad5fbe323c73884e5f0b` |
| `train-fold-a-plan` sealed phase artefact | `runs/SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1/attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1/SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1.phases.json` | `7cac358a39c446c7aa13fcec70722a4669814ea0fad4fc76e9bf291d7b4b8e6f` |
| `roll1` speech query vectors | `vectors/slurp-stage3-construction-r01c-v1/query-vectors-speech-segments.jsonl` | `ebaa743241a67a2cb759353fa8a9f58a3f09d27c00c8c66cb3172958dcccc1b8` |
| `roll1` sealed phase artefact | `runs/SAEA-SLURP-STAGE3-ROLLOUT-R01-V1/attempt-slurp-native-stage3-rollout-r01-generation-v1/SAEA-SLURP-STAGE3-ROLLOUT-R01-V1.phases.json` | `203aab4861e503a088af6cd67662164c908d0ecf66149ce8bf97bf1706aa4f9d` |
| `dev2000-added-plan` speech query vectors | `vectors/slurp-dev2000-added-v1/query-vectors-speech-segments.jsonl` | `e2a5fd046dac7c87fcf53830955e41e69d20402a2305a02ebf2bfc1a33001b9d` |
| `dev2000-added-plan` sealed phase artefact | `runs/SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1/attempt-slurp-native-default-plan-dev2000-added-generation-v1/SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1.phases.json` | `7853313714c58b434f306ebbc2df7de8b05801feb8695dbee4663dfacae4aed1` |

**Same space.** Both key files were cut by the same frozen encoder (inventory `1548387ba91209921fd747e9eff981027be618c618b732efe20ca7d43680bb31`, Omni-Embed-Nemotron-3B, 2048 dimensions, L2-normalised) under the same literal `passage: ` prefix -- the boundary receipt's own geometry says so, and the exemplar-pool authoring record says the same of the pool file -- and each roster's `intent-boundary` query vector is byte-identical to its `content` query vector (the exemplar-pool query provenance records the rename). So one speech vector is scored against both key sets, and a boundary key built from pool vectors is a key in the boundary channel's own space. Had that not held, this read would have stopped here.

| Arm | Rows | Class source | Construction pool (held-out) | CORRECT | INTENT-WRONG |
| --- | ---: | --- | --- | ---: | ---: |
| `train-fold-a-plan` | 1,080 | `bad-case bank roster train-fold-a` | `size-pool-annotated-exemplars` | 480 | 191 |
| `roll1` | 625 | `slurp-slu-official-projected-v3-train` | `size-pool-annotated-exemplars-minus-r01` | 163 | 184 |
| `dev2000-added-plan` | 1,000 | `bad-case bank roster dev2000-added` | `size-pool-annotated-exemplars` | 398 | 232 |

## 1. The recomputation reproduces the sealed ranking

| Arm | rows | sealed width 8 | repo recall top == sealed set | vectorised top == sealed set | vectorised 60-way order == repo recall order |
| --- | ---: | ---: | ---: | ---: | ---: |
| `train-fold-a-plan` | 1,080 | 1,076 | 1,080 (100.00 %) | 1,080 (100.00 %) | 1,080 (100.00 %) |
| `roll1` | 625 | 621 | 625 (100.00 %) | 625 (100.00 %) | 625 (100.00 %) |
| `dev2000-added-plan` | 1,000 | 994 | 1,000 (100.00 %) | 1,000 (100.00 %) | 1,000 (100.00 %) |

The repository's own `rails.kb_policy.multidim_segment_recall` reproduces the sealed delivered set on every row, and the vectorised arithmetic every construction below is scored with reproduces the recall's full 60-way order on every row. Each row carries one speech segment, so the segment machinery is one vector per row. An entry at cosine zero or below is never admitted (`unrankable`), exactly as flown.

## 2. Every construction, on every roster (held-out pool)

`rank-1` is gold's max-over-keys score ranking first among the 60 intents; `deliv@8` is gold within the top eight INTENTS; `facet@8` is what the flown recall/fuser (`k` 8, `m` 8, `c` 1) would materialise when an intent owns several facets -- one of gold's keys within the top eight KEYS -- and equals `deliv@8` for every single-key construction. `median` is gold's median rank on the intent-wrong rows (unrankable counted as 61).

**`train-fold-a-plan`** (1,080 rows; 191 intent-wrong, 480 correct)

| construction | keys | rank-1, all | rank-1, wrong | rank-1, correct | deliv@8, all | deliv@8, wrong | facet@8, wrong | deliv@8, correct | unrankable | median |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `written` | 60 | 65.6 % (+0.0) | 4.7 % (+0.0) | 80.2 % (+0.0) | 87.7 % | 45.0 % (+0.0) | 45.0 % | 97.3 % (+0.0) | 6 | 10 |
| `centroid` | 60 | 65.7 % (+0.2) | 23.0 % (+18.3) | 76.2 % (-4.0) | 94.0 % | 71.2 % (+26.2) | 71.2 % | 99.0 % (+1.7) | 1 | 3 |
| `medoid-1` | 60 | 54.2 % (-11.4) | 17.3 % (+12.6) | 62.3 % (-17.9) | 87.1 % | 57.6 % (+12.6) | 57.6 % | 94.2 % (-3.1) | 4 | 6 |
| `medoid-3` | 180 | 59.8 % (-5.7) | 20.4 % (+15.7) | 69.6 % (-10.6) | 89.6 % | 62.3 % (+17.3) | 50.3 % | 96.2 % (-1.0) | 2 | 5 |
| `medoid-5` | 298 | 59.3 % (-6.3) | 18.8 % (+14.1) | 70.2 % (-10.0) | 90.0 % | 63.4 % (+18.3) | 48.7 % | 96.7 % (-0.6) | 1 | 4 |
| `all-utterances` | 9,354 | 73.6 % (+8.1) | 35.6 % (+30.9) | 81.2 % (+1.0) | 97.3 % | 88.0 % (+42.9) | 70.2 % | 99.6 % (+2.3) | 0 | 2 |

**`roll1`** (625 rows; 184 intent-wrong, 163 correct)

| construction | keys | rank-1, all | rank-1, wrong | rank-1, correct | deliv@8, all | deliv@8, wrong | facet@8, wrong | deliv@8, correct | unrankable | median |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `written` | 60 | 47.0 % (+0.0) | 3.3 % (+0.0) | 75.5 % (+0.0) | 79.2 % | 44.6 % (+0.0) | 44.6 % | 95.1 % (+0.0) | 9 | 12 |
| `centroid` | 60 | 54.1 % (+7.0) | 14.7 % (+11.4) | 73.0 % (-2.5) | 87.8 % | 64.7 % (+20.1) | 64.7 % | 95.7 % (+0.6) | 2 | 4 |
| `medoid-1` | 60 | 42.6 % (-4.5) | 14.1 % (+10.9) | 56.4 % (-19.0) | 79.7 % | 56.0 % (+11.4) | 56.0 % | 91.4 % (-3.7) | 3 | 7 |
| `medoid-3` | 178 | 47.7 % (+0.6) | 15.8 % (+12.5) | 66.3 % (-9.2) | 78.9 % | 54.9 % (+10.3) | 44.6 % | 90.2 % (-4.9) | 3 | 7 |
| `medoid-5` | 296 | 50.2 % (+3.2) | 16.8 % (+13.6) | 70.6 % (-4.9) | 80.8 % | 55.4 % (+10.9) | 41.3 % | 92.6 % (-2.5) | 3 | 6 |
| `all-utterances` | 8,555 | 63.5 % (+16.5) | 31.5 % (+28.3) | 77.3 % (+1.8) | 92.3 % | 79.9 % (+35.3) | 59.8 % | 97.5 % (+2.5) | 0 | 3 |

**`dev2000-added-plan`** (1,000 rows; 232 intent-wrong, 398 correct)

| construction | keys | rank-1, all | rank-1, wrong | rank-1, correct | deliv@8, all | deliv@8, wrong | facet@8, wrong | deliv@8, correct | unrankable | median |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `written` | 60 | 56.4 % (+0.0) | 3.9 % (+0.0) | 70.9 % (+0.0) | 81.5 % | 35.8 % (+0.0) | 35.8 % | 94.5 % (+0.0) | 8 | 14 |
| `centroid` | 60 | 62.5 % (+6.1) | 17.2 % (+13.4) | 76.4 % (+5.5) | 90.6 % | 66.8 % (+31.0) | 66.8 % | 98.2 % (+3.8) | 0 | 5 |
| `medoid-1` | 60 | 56.1 % (-0.3) | 16.4 % (+12.5) | 67.6 % (-3.3) | 82.0 % | 48.7 % (+12.9) | 48.7 % | 90.7 % (-3.8) | 1 | 9 |
| `medoid-3` | 180 | 59.9 % (+3.5) | 18.5 % (+14.7) | 72.4 % (+1.5) | 85.8 % | 55.2 % (+19.4) | 41.8 % | 94.7 % (+0.3) | 0 | 7 |
| `medoid-5` | 298 | 57.7 % (+1.3) | 19.0 % (+15.1) | 72.1 % (+1.3) | 86.0 % | 57.8 % (+22.0) | 40.9 % | 92.7 % (-1.8) | 0 | 7 |
| `all-utterances` | 9,354 | 73.2 % (+16.8) | 38.8 % (+34.9) | 84.7 % (+13.8) | 96.3 % | 86.2 % (+50.4) | 72.0 % | 99.5 % (+5.0) | 0 | 2 |

## 3. Key geometry: how far apart the keys of different intents sit

Cosine between keys of DIFFERENT intents (mean and max; the 60 written keys are the 0.4756 / 0.908 baseline), and the pairwise Jaccard word overlap of the per-intent word sets where a key has words. A centroid has no text. `min keys` is the smallest number of keys any intent received. Measured on the full construction pool; the R01-excluded pool is given for the two single-key constructions.

| construction | keys | min keys / intent | key-to-key cosine, mean | max | Jaccard, mean | max | wrong-row rank-1 floor over 3 rosters | passes rule |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `written` | 60 | 1 | 0.4756 | 0.908 | 0.0814 | 0.6923 | 3.3 % | -- |
| `centroid` | 60 | 1 | 0.9509 | 0.9932 | -- | -- | 14.7 % | yes |
| `medoid-1` | 60 | 1 | 0.9154 | 0.9895 | 0.0329 | 0.6 | 14.1 % | no |
| `medoid-3` | 180 | 3 | 0.9174 | 0.9895 | 0.0509 | 0.7 | 15.8 % | no |
| `medoid-5` | 298 | 3 | 0.9162 | 0.9916 | 0.0626 | 0.7273 | 16.8 % | no |
| `all-utterances` | 9,354 | 3 | 0.8674 | 0.9967 | -- | -- | 31.5 % | yes |

R01-excluded pool: centroid mean cosine 0.9326 (max 0.993), medoid-1 mean 0.9003 (max 0.9895). Intents with NO construction utterance in a pool keep the flown written key under every construction and are counted as one key: full pool none; R01-excluded pool `cooking_query`. A utterance-built store would have to keep a written key for each of them.

**What the geometry says about the inherited framing.** The centroid keys sit at a mean cosine of 0.9509 to one another (max 0.9932), 2.0 times the written keys' 0.4756, and they separate the intents BETTER on every roster. Key-to-key similarity is therefore not the quantity that decides separation, and the pruning read's inference -- keys that share too much cannot separate sixty intents -- does not hold in this space. What decides it is key-to-QUERY geometry: a mean utterance vector sits where the speech vectors sit, and a one-line description does not, however distinct its words.

## 4. `general_quirky` under each construction

Gold rows whose intent is `general_quirky`, per roster: rank-1 count, band counts of gold's rank, median rank, and the number of DISTINCT intents that take top-1 on its not-delivered rows (36 across rosters in the pruning read).

| roster | construction | gold rows | rank-1 | 1-8 | 9-16 | 17-30 | 31-60 | unrankable | median | distinct top-1 rivals on missed rows |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `train-fold-a-plan` | `written` | 45 | 1 | 6 | 8 | 17 | 14 | 0 | 25 | 23 |
| `train-fold-a-plan` | `centroid` | 45 | 0 | 18 | 12 | 11 | 4 | 0 | 12 | 18 |
| `train-fold-a-plan` | `medoid-1` | 45 | 0 | 5 | 6 | 14 | 20 | 0 | 30 | 25 |
| `train-fold-a-plan` | `medoid-3` | 45 | 0 | 6 | 14 | 18 | 7 | 0 | 19 | 21 |
| `train-fold-a-plan` | `medoid-5` | 45 | 1 | 9 | 14 | 15 | 7 | 0 | 15 | 21 |
| `train-fold-a-plan` | `all-utterances` | 45 | 25 | 42 | 3 | 0 | 0 | 0 | 1 | 3 |
| `roll1` | `written` | 41 | 0 | 10 | 3 | 10 | 17 | 1 | 28 | 16 |
| `roll1` | `centroid` | 41 | 0 | 6 | 16 | 13 | 6 | 0 | 16 | 21 |
| `roll1` | `medoid-1` | 41 | 0 | 1 | 3 | 14 | 22 | 1 | 33 | 20 |
| `roll1` | `medoid-3` | 41 | 0 | 0 | 8 | 15 | 17 | 1 | 27 | 21 |
| `roll1` | `medoid-5` | 41 | 0 | 2 | 8 | 20 | 10 | 1 | 23 | 20 |
| `roll1` | `all-utterances` | 41 | 11 | 36 | 4 | 1 | 0 | 0 | 3 | 4 |
| `dev2000-added-plan` | `written` | 51 | 0 | 6 | 4 | 21 | 18 | 2 | 27 | 22 |
| `dev2000-added-plan` | `centroid` | 51 | 0 | 19 | 17 | 13 | 2 | 0 | 12 | 17 |
| `dev2000-added-plan` | `medoid-1` | 51 | 0 | 3 | 10 | 18 | 20 | 0 | 27 | 19 |
| `dev2000-added-plan` | `medoid-3` | 51 | 0 | 6 | 8 | 27 | 10 | 0 | 21 | 21 |
| `dev2000-added-plan` | `medoid-5` | 51 | 1 | 7 | 14 | 23 | 7 | 0 | 18 | 22 |
| `dev2000-added-plan` | `all-utterances` | 51 | 17 | 46 | 3 | 2 | 0 | 0 | 2 | 5 |

**Reading it.** With the written key `general_quirky` is delivered on 6 of 45 / 10 of 41 / 6 of 51 of its gold rows; with `centroid` on 18 of 45 / 6 of 41 / 19 of 51; and even keyed by EVERY one of its construction utterances (the nearest-neighbour ceiling) on 42 of 45 / 36 of 41 / 46 of 51. The single key moves the catch-all on 2 of 3 rosters (`train-fold-a-plan`, `dev2000-added-plan`) and not on `roll1`, and the ceiling delivers at least 88 % of its rows on every roster. So it is NOT irreducible by construction -- its own utterances do separate it -- but no COMPACT key does: one centroid, three or five medoids all leave most of its rows outside the eight, because a catch-all's utterances have no single centre. What reaches it is dense coverage, which is the exemplar channel's mechanism (the rank diagnostic's `agree-1`), not a boundary-key rewrite. Its share of the miss mass therefore stays reachable, but through the vote, and any single-key rebuild should be read with that intent's rows set aside.

## 5. Held out, and what a key could have seen

No construction is fitted to any roster: a key is a function of the pool's vectors and the pool's own build-time labels. What a key can do is CONTAIN an evaluated row's own utterance. Membership of each roster's own utterances in the two pools -- full pool / R01-excluded pool: `train-fold-a-plan` 0 / 0; `roll1` 625 / 0; `dev2000-added-plan` 0 / 0. So Fold A and DEV-2000 are held out under the full pool and ROLL-1 is held out only under the R01-excluded pool, which is the pool every ROLL-1 number above uses. Reading ROLL-1 under the full pool instead -- keys that have SEEN the row's own utterance -- gives the seen-versus-held-out gap:

| construction | ROLL-1 rank-1 wrong, held out | seen | gap | deliv@8 wrong, held out | seen | gap | rank-1 all, held out | seen |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `centroid` | 14.7 % | 18.5 % | +3.8 | 64.7 % | 71.2 % | +6.5 | 54.1 % | 55.8 % |
| `medoid-1` | 14.1 % | 14.7 % | +0.5 | 56.0 % | 52.7 % | -3.3 | 42.6 % | 42.4 % |
| `medoid-3` | 15.8 % | 14.7 % | -1.1 | 54.9 % | 56.5 % | +1.6 | 47.7 % | 46.6 % |
| `medoid-5` | 16.8 % | 14.7 % | -2.2 | 55.4 % | 56.5 % | +1.1 | 50.2 % | 48.3 % |
| `all-utterances` | 31.5 % | 89.7 % | +58.2 | 79.9 % | 97.3 % | +17.4 | 63.5 % | 95.4 % |

The gap is the optimism a key buys by holding the row it is later asked about. `all-utterances` carries almost all of it (+58.2 points of wrong-row rank-1: every evaluated row is one of its own keys and scores itself at cosine 1), the centroid a few (+3.8: a row is one term in its intent's mean), and the medoid sets almost none (+0.5, -1.1, -2.2: a row is rarely one of the one, three or five chosen). The held-out columns are the ones every verdict above is drawn from, and the seen column is why a 9,354-key store read on its own construction roster would look far better than it is.

## 6. The discriminative-vocabulary key, as text only

A word is removed from every key when it appears in more than the stated share of the OTHER 59 keys (the brief's threshold is one half). Two sources: the text the channel actually encodes (the facet representation) and the delivered body the pruning read measured. **The retrieval effect of this construction is NOT measured**: it would need one encoder pass over 60 strings, an embedder contact this read does not make, so it is priced here as text -- how much of the overlap is generic vocabulary -- and nothing more.

| source | share threshold | vocabulary | words removed | words per key, before -> after | keys emptied | Jaccard mean, before -> after | max, before -> after |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| encoded key text | > 0.25 | 349 | 3 | 11.5 -> 9.7 | 0 | 0.0814 -> 0.0192 | 0.6923 -> 0.6364 |
| encoded key text | > 0.50 | 349 | 2 | 11.5 -> 10.0 | 0 | 0.0814 -> 0.0236 | 0.6923 -> 0.6364 |
| encoded key text | > 0.75 | 349 | 1 | 11.5 -> 10.6 | 0 | 0.0814 -> 0.0392 | 0.6923 -> 0.6667 |
| delivered body | > 0.25 | 616 | 60 | 75.6 -> 18.4 | 0 | 0.6073 -> 0.0225 | 0.9189 -> 0.6667 |
| delivered body | > 0.50 | 616 | 56 | 75.6 -> 19.9 | 0 | 0.6073 -> 0.0354 | 0.9189 -> 0.6667 |
| delivered body | > 0.75 | 616 | 56 | 75.6 -> 19.9 | 0 | 0.6073 -> 0.0354 | 0.9189 -> 0.6667 |

The encoded keys share 0.0814 of their words on average against 0.6073 for the delivered bodies: the 0.6073 figure describes the bodies, which share a template, and the keys themselves overlap less. Removing the words that more than half the other keys carry drops the key overlap to 0.0236 (max 0.6364) and the body overlap to 0.0354 (max 0.6667); the difference between a before and an after is the share of the overlap that is generic vocabulary. Whether the residual, distinctive words retrieve better is the unmeasured encoder question; what section 2 measures instead is whether a key of the same KIND as the query -- an utterance -- separates the intents.

## 7. Price, honesty, and the one construction this read would put forward

**Rebuild price, in one line.** Any key change is a store rebuild: a re-cut `facets.jsonl` for the boundary channel (60 rows; for a centroid or medoid key it is arithmetic over pinned pool vectors, zero encoder contacts, but a centroid has no text source and needs a new receipt kind, where a medoid IS a pinned utterance vector whose text the existing kind can hash), a fresh `intent-boundaries-v2` snapshot release, and a re-pin of every consumer: 211 committed config files pin the flown store today, 179 of them baseline fragments -- above the ~55 the brief estimated -- and the re-pin path has twice rewritten sibling ledger rows in this repository's history. The delivered block is unchanged (the body the Solver reads is the same 1,195 tokens), so the token cost is zero.

**Delivery is not correctness.** Every number above counts rows that would RECEIVE their own gold intent's boundary entry, or would see it ranked first. Whether the Solver then answers correctly with the entry present is mode (iv), unmeasured here, because it needs the answer the row would give, which needs contacts. The correct-row column is the only evidence that delivery and correctness move together, and it is an association on rows that already work. No score gain is claimed, implied or estimated.

**The construction: `centroid`.** It passes the pre-registered rule on all three rosters under their held-out pools -- wrong-row rank-1 up by at least +11.4 points, wrong-row delivery up, correct-row delivery down by no more than a point anywhere -- and among the passers it is the single-key construction with the largest held-out floor. Passing set: `centroid`, `all-utterances`. It would keep the store at 60 facets, the fuser at `m` 8 and the delivered body as it is: only the retrieval key moves, from a one-line description to the intent's mean TRAIN utterance vector. Its cost in the one column the rule does not guard: rank-1 on the CORRECT rows moves by -4.0 / -2.5 / +5.5 points (Fold A / ROLL-1 / DEV-2000), so on rows that already work gold can slip from first to somewhere in the eight, which a flight must read. A construction cell would be a store rebuild plus one flight, and its result would be a delivery result until the flight reads it as a score. This read authorises neither.

`all-utterances` also passes, and reaches further, but it is not a boundary key: it is the exemplar channel's own facets wearing the intent label. As a store it would put 9,354 facets behind the boundary dimension, and with the flown `k` 8 the top eight KEYS crowd with one intent's neighbours, so what it would materialise is its facet-slot column -- 70.2 % / 59.8 % / 72.0 % wrong-row delivery against the intent-level 88.0 % / 79.9 % / 86.2 %. The rank diagnostic's `agree-1` reaches that same signal through the exemplar vote at +1.4 tokens per row without a boundary rebuild, which is the route for the catch-all intents the centroid does not reach.

## 8. Boundary

Zero model, server, encoder, embedder, scorer, tokenizer, network, GPU and paid-API contacts: no server was started, stopped or probed (port 8080 untouched), no waveform decoded, no text encoded, no subprocess run. BLAS was capped at four threads and no worker pool was used. Every cosine was recomputed as arithmetic over the pinned files in section 0, each verified against its configured sha256 by this repository's own loaders or by `hashlib` before a number was taken from it; the written-key ranking went through `rails.kb_policy.multidim_segment_recall` and the vectorised path was proven equal to it on every row. Other tools: `data.slurp.load_slurp_split` for the governed TRAIN gold, `data.slurp.load_slurp_construction_utterances` for TRAIN word sets reduced to a ratio, `json` reads of three released snapshots, one encoding receipt and three sealed `*.phases.json`, and a `json` read of the sealed bad-case bank and of the ROLL-1 official score file.

This read admits nothing, promotes nothing, preregisters no cell, releases no store, rebuilds no store, draws no roster, expands no source, opens no split and reaches no superiority, generalisation or Stage-3 conclusion. It is byte-reproducible across runs apart from its `generated_at` stamp: every container is sorted before it is consumed, every construction is a deterministic function of the pinned bytes, and there is no sampling anywhere.
