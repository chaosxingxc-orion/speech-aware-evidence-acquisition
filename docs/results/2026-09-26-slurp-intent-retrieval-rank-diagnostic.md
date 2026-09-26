# SLURP intent-boundary retrieval: where the gold intent ranks, and what the retrieval stage can buy

Date: 2026-09-26. Read id `SAEA-SLURP-MF-INTENT-RETRIEVAL-RANK-DIAGNOSTIC-V1`, recipe `slurp-intent-retrieval-rank-diagnostic-v1`. Generated `2026-09-26T19:59:52+00:00`.

A model-free read. Zero model, server, encoder, embedder, scorer, network, GPU and paid-API contacts. The cosines are **recomputed** -- arithmetic over the two pinned, sha256-verified vector files named below, through this repository's own `rails.kb_policy.multidim_segment_recall` and the flown ranker's own ordering rule -- and section 1 proves the recomputation reproduces what the flights sealed before any of it is used. Token counts come from 110 local vocab-only `llama-tokenize` processes (no server, no port, no GPU).

A DIAGNOSTIC, never a gate. It registers no cell, admits no mechanism, releases no store, authorises no flight and states no effectiveness, superiority or generalisation claim. Every roster below is a discovery or dev roster and every number is a development number (owner decisions 28 and 86), never a test claim. No utterance text, transcript, gold filler, delivered answer or knowledge body is read into a reported value: every cell is an id, a count, a rank, a rate, a margin, a token count or a hash.

## 0. What was read, and the stage it measures

| Artefact | Relpath under `SPEECHRL_DATA_DIR` | sha256 |
| --- | --- | --- |
| `intent-boundaries-v1` snapshot (content hash = the flown store pin) | `knowledge/slurp/semantic/intent-boundaries-v1/snapshot.json` | `5520b8449b627530227563d1f8db71f8a391f20f7d0ff7d7bd439e28ec6e48fe` |
| boundary facet key vectors (60 rows x 2048 dims) | `prepared/SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1/facets.jsonl` | `76e8d16a067ebfc5d67a4ecef2966636310815b950a7d9790ec7c0136f01ecd2` |
| `roll1` speech segment query vectors | `vectors/slurp-stage3-construction-r01c-v1/query-vectors-speech-segments.jsonl` | `ebaa743241a67a2cb759353fa8a9f58a3f09d27c00c8c66cb3172958dcccc1b8` |
| `roll1` sealed phase artefact | `runs/SAEA-SLURP-STAGE3-ROLLOUT-R01-V1/attempt-slurp-native-stage3-rollout-r01-generation-v1/SAEA-SLURP-STAGE3-ROLLOUT-R01-V1.phases.json` | `203aab4861e503a088af6cd67662164c908d0ecf66149ce8bf97bf1706aa4f9d` |
| `train-fold-a-plan` speech segment query vectors | `vectors/slurp-intent-boundaries-train-fold-a-1080-v1/query-vectors-speech-segments.jsonl` | `e7a5b2264dc61fcab3c63d50fb645d4629d3f0a99f83ad5fbe323c73884e5f0b` |
| `train-fold-a-plan` sealed phase artefact | `runs/SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1/attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1/SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1.phases.json` | `7cac358a39c446c7aa13fcec70722a4669814ea0fad4fc76e9bf291d7b4b8e6f` |
| `dev2000-added-plan` speech segment query vectors | `vectors/slurp-dev2000-added-v1/query-vectors-speech-segments.jsonl` | `e2a5fd046dac7c87fcf53830955e41e69d20402a2305a02ebf2bfc1a33001b9d` |
| `dev2000-added-plan` sealed phase artefact | `runs/SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1/attempt-slurp-native-default-plan-dev2000-added-generation-v1/SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1.phases.json` | `7853313714c58b434f306ebbc2df7de8b05801feb8695dbee4663dfacae4aed1` |

The stage is one retrieval: phase `perception`, provider `kb-facet-v1`, dimension `intent-boundary`, `k` 8 over 60 intents, `tau` 0.0, `fuse_coverage` top_l=8 m=8 c=1, rank policy `saea-rank-wcos-prior-agree-v1` at weights w_cos 1.0, w_prior 0.0, w_agree 0.0, fuser `saea-fuse-associated-values-v1`. **Two corrections to the brief this read answers.** The boundary channel's fuser is `saea-fuse-associated-values-v1`, not `saea-fuse-supplyfilter-v1`; and each query row carries exactly one speech segment on all three rosters, so the segment machinery reduces to one whole-utterance vector per row.

| Arm | Rows analysed | Class source | Segments per row | Skipped |
| --- | ---: | --- | --- | --- |
| `roll1` | 625 | `slurp-slu-official-projected-v3-train` | {1: 625} | none |
| `train-fold-a-plan` | 1,080 | `bad-case bank roster train-fold-a` | {1: 1080} | none |
| `dev2000-added-plan` | 1,000 | `bad-case bank roster dev2000-added` | {1: 1000} | none |

## 1. The recomputation reproduces the sealed ranking

The flights seal the *delivered* eight, not the ranked sixty, so the sealed ranking is exactly the flown top-8 set. Widening the recall cannot change that top-8: a facet whose max-over-segments cosine puts it in the global top-`k` is in some segment's own top-`k` (any facet beating it in that segment beats it globally too), so the union the flown recall builds already contains the global top-`k` in the global order. The recomputation is therefore checked against the sealed set, and picking the right 8 of 60 by chance is one outcome in 2.6 billion.

| Arm | Rows checked | Rows where the flight delivered 8 entries | Recomputed top-8 == the sealed set | Every sealed entry ranks 1-8 | Agreement |
| --- | ---: | ---: | ---: | ---: | ---: |
| `roll1` | 625 | 621 | 625 | 625 | 100.00 % |
| `train-fold-a-plan` | 1,080 | 1,076 | 1,080 | 1,080 | 100.00 % |
| `dev2000-added-plan` | 1,000 | 994 | 1,000 | 999 | 100.00 % |

Agreement is exact on every row of all three rosters, so every rank below is the rank the flight itself would have assigned. Two columns need a word. The flight delivered fewer than eight entries on a few rows because the recall admitted fewer than eight candidates there (section 2's `unrankable` column is the same effect), and on those rows the recomputed set matches the shorter sealed set exactly, which is why the third column can exceed the second. The fourth column misses one `dev2000-added-plan` row whose sealed set is EMPTY -- the recall admitted no candidate at all -- and there is no sealed entry on it to rank.

## 2. Where the gold intent actually ranks

The decisive distribution. Ranks are over the boundary entries the flown recall admits, in the flown order (`score` descending, facet id ascending). `unrankable` counts rows whose gold intent the recall never admits as a candidate at all: `kb_policy.multidim_recall` admits an entry only on a strictly positive cosine, so an entry at or below zero has no rank, and no `k` and no reweighting reaches it, because every downstream stage ranks the recalled set. The last column is how many of the 60 entries the recall admitted on the median row of that class.

| Arm | Class | Rows | 1-8 (delivered) | 9-16 | 17-30 | 31-60 | unrankable | median rank | candidates admitted (median) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `roll1` | `INTENT-WRONG` | 184 | 82 (44.6 %) | 27 (14.7 %) | 31 (16.8 %) | 39 (21.2 %) | 5 (2.7 %) | 13 | 60 |
| `roll1` | `CORRECT` | 163 | 155 (95.1 %) | 4 (2.5 %) | 2 (1.2 %) | 1 (0.6 %) | 1 (0.6 %) | 1 | 60 |
| `train-fold-a-plan` | `INTENT-WRONG` | 191 | 86 (45.0 %) | 39 (20.4 %) | 34 (17.8 %) | 29 (15.2 %) | 3 (1.6 %) | 10 | 60 |
| `train-fold-a-plan` | `CORRECT` | 480 | 467 (97.3 %) | 2 (0.4 %) | 5 (1.0 %) | 5 (1.0 %) | 1 (0.2 %) | 1 | 60 |
| `dev2000-added-plan` | `INTENT-WRONG` | 232 | 83 (35.8 %) | 40 (17.2 %) | 50 (21.6 %) | 53 (22.8 %) | 6 (2.6 %) | 14 | 60 |
| `dev2000-added-plan` | `CORRECT` | 398 | 376 (94.5 %) | 6 (1.5 %) | 13 (3.3 %) | 2 (0.5 %) | 1 (0.3 %) | 1 | 60 |

**The answer to the question this distribution was asked to decide.** The missing gold intents are not bunched just outside the window; they are spread down the whole tail: `train-fold-a-plan` 105 missed, of which 37 % at 9-16, 32 % at 17-30, 28 % at 31-60 and 3 % unrankable; `roll1` 102 missed, of which 26 % at 9-16, 30 % at 17-30, 38 % at 31-60 and 5 % unrankable; `dev2000-added-plan` 149 missed, of which 27 % at 9-16, 34 % at 17-30, 36 % at 31-60 and 4 % unrankable. So no `k` short of the full store reaches most of them -- a `k` of 16 leaves over two thirds of the missed rows still missing on every roster -- while the rows that answered correctly hold the gold intent at median rank 1 and inside the top 8 on 94.5-97.3 % of them. That shape rules out a budget story and points at the ranking signal itself, which is what section 3 tests and section 4 characterises.

## 3. What each admissible change would buy, measured

Delivery of the row's own gold-intent boundary entry, on the intent-wrong rows and on the correct rows, with the token cost of the block the change would deliver measured on the tokenizer. One rendered entry is 149.0 tokens on average (median 145, range 134-181), so the block the flown k=8 sends is 1195.4 tokens. Summing per-entry counts and one newline each overshoots the measured block by 7 to 29 tokens -- 0.6 to 2.4 % of it -- over 25 sampled rows at both widths, so the per-row deltas below are upper bounds on the real cost.

Weights are fitted on `train-fold-a-plan` alone, by maximising gold-intent delivery over **every** analysed row of that roster (class-blind, so the error labels do not choose the weight); the other two rosters are read, never fitted. The grid is [0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.6, 0.8, 1.0, 1.5, 2.0], and the winners are `agree-2` and `prior-0.1`.

| Change | Fold A wrong-row delivery | Fold A correct | ROLL-1 wrong-row delivery | ROLL-1 correct | DEV-2000 wrong-row delivery | DEV-2000 correct | tokens/row added | wrong rows gained per 100 tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `agree-1`: w_cos 1.0 + 1 x exemplar agreement, k=8 | 81.7 % (+36.6) | 99.6 % | 75.0 % (+30.4) | 98.8 % | 78.0 % (+42.2) | 99.5 % | +1.4 | token-neutral (+70 rows) |
| `agree-2`: w_cos 1.0 + 2 x exemplar agreement, k=8 | 83.8 % (+38.7) | 99.6 % | 75.0 % (+30.4) | 98.8 % | 79.7 % (+44.0) | 99.5 % | +1.7 | token-neutral (+74 rows) |
| exemplar agreement alone, k=8 (that signal's own ceiling) | 84.3 % (+39.3) | 99.4 % | 75.0 % (+30.4) | 98.2 % | 80.2 % (+44.4) | 99.5 % | +1.7 | token-neutral (+75 rows) |
| `agree-0.4`: w_cos 1.0 + 0.4 x exemplar agreement, k=8 | 75.9 % (+30.9) | 99.6 % | 69.0 % (+24.5) | 98.2 % | 71.1 % (+35.3) | 99.2 % | +0.5 | token-neutral (+59 rows) |
| `agree-0.2`: w_cos 1.0 + 0.2 x exemplar agreement, k=8 | 71.2 % (+26.2) | 99.4 % | 63.0 % (+18.5) | 98.2 % | 62.1 % (+26.3) | 99.0 % | +0.5 | token-neutral (+50 rows) |
| `prior-0.1`: w_cos 1.0 + 0.1 x build-time intent prior, k=8 | 65.4 % (+20.4) | 96.9 % | 57.1 % (+12.5) | 95.1 % | 66.8 % (+31.0) | 97.2 % | -7.3 | token-neutral (+39 rows) |
| widen `k` to 16, pure cosine | 65.4 % (+20.4) | 97.7 % | 59.2 % (+14.7) | 97.5 % | 53.0 % (+17.2) | 96.0 % | +1189.1 | 3.28 |
| widen `k` to 12, pure cosine | 55.0 % (+9.9) | 97.7 % | 50.0 % (+5.4) | 97.5 % | 44.8 % (+9.1) | 95.5 % | +594.8 | 3.19 |
| widen `k` to 24, pure cosine | 75.9 % (+30.9) | 98.5 % | 70.1 % (+25.5) | 98.8 % | 65.9 % (+30.2) | 97.7 % | +2375.8 | 2.48 |
| widen `k` to 30, pure cosine | 83.2 % (+38.2) | 98.8 % | 76.1 % (+31.5) | 98.8 % | 74.6 % (+38.8) | 99.2 % | +3262.3 | 2.24 |

A change is called token-neutral when its measured delta is within 1 % of the flown block (12.0 tokens); the reweightings are, because the block still carries eight entries and the only movement is the length difference between the entries swapped in and out.

Widening `k` is the opposite of free: because `k == top_l == m`, the ranked set IS the materialised set, so every extra rank is an extra rendered entry in the Perception prompt.

**The prior term the policy defines is not reachable by a weight.** Measured on the released snapshot, 0 of the 60 boundary values carry a `prior_score` and 0 carry a `task_target`, and the channel recalls one dimension only, `intent-boundary`, which is not in `kb_policy.PRIOR_MASS_DIMENSIONS`. So `max_prior` is 0.0 for every candidate on every row and **`w_prior` has no effect at any value**: turning it on is a store rebuild (a `prior`/`label` dimension, or a `prior_score` on each value), not a config flip. The `prior-0.1` row above is that rebuild simulated offline, with the prior taken as each intent's share of the store's own construction split divided by the largest such share -- a build-time store property, legal by the standing rule, and keyed on nothing about the evaluation row.

**The agreement term is reachable, but it is a phase-order change, not a weight change.** The agreement used here is the share of the row's delivered exemplars whose pool intent equals the candidate intent. Each pool entry's intent is frozen into the store at build time, and the exemplars are recalled from the same row's own speech vector, so no gold, transcript or future turn enters it. Three things make it admissible and one makes it a change of more than a weight. It is speech-keyed, so the standing query ruling is satisfied. It is **self-excluded**: two of the three rosters are drawn from the same TRAIN split the exemplar pool is built from, so any exemplar whose pool utterance is the evaluated row's own is dropped from the vote before it is used -- measured, that exclusion fired on 0 `train-fold-a-plan` rows, 0 `roll1` rows, 0 `dev2000-added-plan` rows. And the vote is dense: per-row vote totals are {20: 1080}. What it is not is a weight flip, because the flown program runs Perception before the Solver's exemplar retrieval; using it at Perception means pre-computing the exemplar recall first, which is model-free and is exactly the pre-flight bootstrap the boundary channel already uses.

**What that result says about the boundary keys.** The two channels rank in different key spaces. The boundary channel scores a row's speech vector against a 2,048-dimension encoding of a written *boundary description* per intent; the exemplar channel scores the same kind of speech vector against 11,514 encodings of *other utterances*. Utterance-to-utterance similarity already carries the intent -- on the fit roster the exemplar vote alone puts the gold intent at rank 1 on 76.1 % of all rows against 65.6 % for the boundary cosine -- so the weak link is the boundary key space, not the budget, not the store and not the query modality.

## 4. Is the query itself the problem?

For the rows whose gold intent ranks 31 or worse, no admissible `k` reaches it. The margin is the cosine gap between the top-1 entry and the gold entry on the same row.

| Arm | wrong rows | rank 9-30 | rank 31-60 | unrankable | margin, delivered rows (mean) | margin, rank 9-30 (mean) | margin, rank 31-60 (mean) | top-1 family on the unreachable rows: distinct intents | top-3 share | same scenario as gold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `roll1` | 184 | 58 | 39 | 5 | 0.0376 | 0.0765 | 0.1157 | 23 of 44 rows | 31.8 % | 2.3 % |
| `train-fold-a-plan` | 191 | 73 | 29 | 3 | 0.0309 | 0.0774 | 0.1133 | 21 of 32 rows | 28.1 % | 0.0 % |
| `dev2000-added-plan` | 232 | 90 | 53 | 6 | 0.0406 | 0.0834 | 0.1099 | 26 of 59 rows | 35.6 % | 8.5 % |

Two further facts about the unreachable end. The sealed width is not always eight: `train-fold-a-plan` sealed a set of eight on 1076 of 1080 rows, `roll1` sealed a set of eight on 621 of 625 rows, `dev2000-added-plan` sealed a set of eight on 994 of 1000 rows, and 0 `train-fold-a-plan` rows, 0 `roll1` rows, 1 `dev2000-added-plan` rows had NO admitted candidate at all, so those rows received no boundary entry whatever. That is the same recall floor, at its extreme.

Chronic against sporadic. An intent is *chronic* on a roster when it is the gold intent of at least 5 analysed rows and misses delivery on at least 80 % of them.

| Arm | chronic intents | share of the not-delivered intent-wrong rows they own | intents that never miss | most-missed chronic intents (id: missed/rows) |
| --- | ---: | ---: | ---: | --- |
| `roll1` | 0 | 0.0 % | 23 | none |
| `train-fold-a-plan` | 1 | 31.4 % | 30 | `general_quirky`: 39/45 |
| `dev2000-added-plan` | 1 | 25.5 % | 21 | `general_quirky`: 45/51 |

A standing ruling bounds every query change this section could motivate: retrieval queries are speech or speech-plus-state, never a transcript and never gold. The exemplar-agreement term above satisfies it (speech-keyed recall over a frozen store). A re-encoding of the boundary keys, or a speech-plus-draft-state query, would also satisfy it; anything that reads the reference transcript or the gold label would not, and is named inadmissible here rather than measured.

## 5. The ceiling, stated as what it is

Every number in section 3 is a count of **rows that would gain delivery of their own gold intent's boundary entry**. Delivery is not correctness. A row that receives its gold intent's boundary may still answer wrongly -- that is mode (iv), *delivered but ignored or misused* -- and the conversion rate from delivery to correctness is **unmeasured**: it is not a function of bytes already sealed, because it needs the answer the row would give with the entry present, which needs contacts. The correct-row column is the only evidence here that delivery and correctness move together at all, and it is an association on the rows that already worked, not a causal rate. No score gain is claimed, implied or estimated anywhere in this read.

## 6. The one change this read would register next

The selection rule, fixed before the numbers were read: a candidate is registrable only if it raises gold-intent delivery on the intent-wrong rows of **all three** rosters -- the one its weight was fitted on and the two it was not -- while lowering delivery on the correct rows of none of them by more than one point. Among the candidates that pass, a token-neutral change beats a token-buying one; among token-buying ones the best delivery gained per token added wins; ties go to the smaller weight, because the smaller weight keeps more of the flown signal. If nothing passes, this read says so and the programme's next question is mode (iv), not retrieval.

**The change: `agree-1`** -- keep the flown cosine, set `w_agree` to 1 over the self-excluded exemplar-intent vote, leave `k` at 8. 18 of the 27 candidates measured pass the rule; this is the one it selects. On the fit roster it raises the intent-wrong rows' gold-boundary delivery from 45.0 % to 81.7 % (86 to 156 of 191 rows, +70), and the smallest gain it holds across the three rosters is +30.4 points. Its measured token cost is +1.4 tokens per row on the tokenizer (largest single row +97), against the 1195.4-token block the flown eight already send. The nearest `k`-widening alternative, `cos@k30`, buys a comparable +31.5-point floor for +3262.3 tokens per row -- about 2,330 times the cost for the same delivery, and that added form is exactly what sank the index arm.

**And what it does not buy.** The gain is a gain in DELIVERY. The conversion rate from delivery to correctness is unmeasured and is not estimated here: a row that receives its gold intent's boundary entry may still answer wrongly, which is mode (iv), and measuring that needs model contacts this read did not make. Nothing above is a score prediction, and this read authorises no cell, no flight and no store release.

## 7. Boundary

Zero model, server, encoder, embedder, scorer, network, GPU and paid-API contacts: no server was started, stopped or probed, no waveform decoded and no embedding computed. The cosines were RECOMPUTED as arithmetic over two pinned vector files -- `prepared/SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1/facets.jsonl` and each arm's `query-vectors-speech-segments.jsonl` -- each verified against its configured sha256 by the repository's own loader before a number was taken from it, through `rails.kb_policy.multidim_segment_recall` and the flown ranker's ordering rule. The one subprocess is the local vocab-only `llama-tokenize` (110 invocations, 4 workers) loading the pinned `models/qwen3-omni-30b-a3b-instruct-gguf-q4km/Qwen3-Omni-30B-A3B-Instruct-Q4_K_M.gguf` vocab: no server, no port, no GPU. Other tools: `data.slurp.load_slurp_split` for the governed TRAIN gold, `json` reads of the released snapshot and of three sealed `*.phases.json`, a `json` read of the sealed bad-case bank and of the ROLL-1 official score file, and `hashlib` for every identity hash above.

This read admits nothing, promotes nothing, preregisters no cell, releases no store, draws no roster, expands no source, opens no split and reaches no superiority, generalisation or Stage-3 conclusion. It is byte-reproducible across runs apart from its `generated_at` stamp: every container is sorted before it is consumed, there is no resampling, and the tokenizer results are keyed so the worker pool cannot reorder them.
