# SLURP knowledge coverage and the decision-123 failure-mode attribution

Date: 2026-09-26. Read id `SAEA-SLURP-MF-KNOWLEDGE-COVERAGE-FAILURE-MODE-V1`, recipe `slurp-knowledge-coverage-and-failure-mode-attribution-v1`. A model-free read over sealed bytes: zero model, server, tokenizer, encoder, embedder, scorer, network, GPU and paid-API contacts. Nothing was executed. Every number is read from artefacts earlier flights already sealed, from the three released knowledge stores, and from the governed SLURP TRAIN split through `data.slurp.load_slurp_split`.

A DIAGNOSTIC, never a gate. It decides no cell, admits no mechanism, releases no store, authorises no flight, expands no source and states no effectiveness, superiority or generalisation claim. Every roster below is a discovery or dev roster and its numbers are development numbers (owner decisions 28 and 86), never a test claim.

**Where gold was read, and that it touched no runtime path.** Gold labels enter this read in exactly two places, both offline and both on the scoring side: the sealed bad-case bank's `gold_intent` / `gold_entity_types` / `fn_types` / `fp_types` fields, and the governed TRAIN split read through the ordinary `data.slurp.load_slurp_split` loader exactly as `core.scoring_batch` reads it. No gold value reaches a runtime query, a retrieval key, a selector, a supply decision or any config; this script writes a report and nothing else, and it opens no config, no policy and no store-construction path. No utterance text, transcript, delivered answer, gold filler, predicted filler or knowledge body text is read into a reported value: every cell below is an id, a class name, a count, a rate, a ratio or a hash.

## 0. Inputs and identity

| Artefact | Relpath under `SPEECHRL_DATA_DIR` | sha256 |
| --- | --- | --- |
| bad-case bank (2,080 rows, both PLAN rosters) | `analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl` | `26231b86b86f35251fed2b7d7c59bf33e8806b5ef71739b74bf9d5bc2b8a3ccf` |
| governed SLURP TRAIN split (11,514 utterances) | `datasets/slurp/metadata/train.jsonl` | `4a05a3de6c7f028aff298c4a90196e6a3fecd1938d96fb1c125d6fd10d5e301e` |
| released `intent-boundaries-v1` snapshot | `knowledge/slurp/semantic/intent-boundaries-v1/snapshot.json` | `4579079c949e7da71125047c8d57027a55f0b90c3fc6db5704ba3c9322e6afd3` |
| released `slot-contracts-v2` snapshot | `knowledge/slurp/semantic/slot-contracts-v2/snapshot.json` | `a48ed83eb7878e9eaedfe4dbdf4ea747e3e582e08899ff1f0edfdfe438ae8904` |
| released `size-pool-annotated-exemplars` snapshot | `knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json` | `fcb5506c63653abe996dea15fdccd7c81a84a837b6377ca13f5b35d73283d6b2` |
| released `size-pool-annotated-exemplars-minus-r01` snapshot | `knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/snapshot.json` | `f549466f22bb0cae00a99849a1a811889eb82af9b632305c815fa123ad5795ca` |
| `roll1` sealed phase artefact | `runs/SAEA-SLURP-STAGE3-ROLLOUT-R01-V1/attempt-slurp-native-stage3-rollout-r01-generation-v1/SAEA-SLURP-STAGE3-ROLLOUT-R01-V1.phases.json` | `203aab4861e503a088af6cd67662164c908d0ecf66149ce8bf97bf1706aa4f9d` |
| `roll1` sealed flight receipt | `runs/SAEA-SLURP-STAGE3-ROLLOUT-R01-V1/attempt-slurp-native-stage3-rollout-r01-generation-v1/flight-receipts.json` | `1606d7aefd3d554564d1d036ac45b78714ebe85864936d722ffded092578bca3` |
| `train-fold-a-plan` sealed phase artefact | `runs/SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1/attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1/SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1.phases.json` | `7cac358a39c446c7aa13fcec70722a4669814ea0fad4fc76e9bf291d7b4b8e6f` |
| `train-fold-a-plan` sealed flight receipt | `runs/SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1/attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1/flight-receipts.json` | `687b4081b659a1ade99a34ab2283b53bb1a5acbae5683db42470b54aafa08cba` |
| `dev2000-added-plan` sealed phase artefact | `runs/SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1/attempt-slurp-native-default-plan-dev2000-added-generation-v1/SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1.phases.json` | `7853313714c58b434f306ebbc2df7de8b05801feb8695dbee4663dfacae4aed1` |
| `dev2000-added-plan` sealed flight receipt | `runs/SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1/attempt-slurp-native-default-plan-dev2000-added-generation-v1/flight-receipts.json` | `3fa30daa31021622c72c6c65c0d23437543e2724988415cd71449ea485859ac7` |
| ROLL-1 as-flown pool official score file | `analysis/SLURP-SAMPLE-AGGREGATION-OFFLINE-READ-V1/PS-registered-support-3-slurp-slu-official-projected-v3-train-scores.json` | `70247697eca510e9dc699983f23996bcb77113d43c94ba340d764083bb04f76d` |

| Population | Rows | Run id | Attempt | Class source |
| --- | ---: | --- | --- | --- |
| ROLL-1 as-flown pool (R01C construction roster, 625 rows) | 625 | `SAEA-SLURP-STAGE3-ROLLOUT-R01-V1` | `attempt-slurp-native-stage3-rollout-r01-generation-v1` | `slurp-slu-official-projected-v3-train` |
| TRAIN Fold A PLAN (construction roster, 1,080 rows) | 1080 | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1` | `attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1` | sealed bad-case bank |
| DEV-2000-ADDED PLAN (fresh roster, 1,000 rows) | 1000 | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1` | `attempt-slurp-native-default-plan-dev2000-added-generation-v1` | sealed bad-case bank |

**Pool identity, and two corrections to the figures this read was asked about.** The ROLL-1 population is the as-flown delivered pool of run `SAEA-SLURP-STAGE3-ROLLOUT-R01-V1` over the 625-row R01C construction roster, re-scored offline by the pinned official evaluator at commit `8eb16545762be97ace75334109d73824217311f1` under scorer `slurp-slu-official-projected-v3-train` at the commit policy the flight actually flew (plurality support 3). Its sealed official intent accuracy is 70.56 % and exactly 184 of its 625 rows are intent-wrong, which is the population asked for. Two figures in the request do not survive contact with the bytes and are corrected here rather than carried forward. This pool's pooled SLU-F1 is 59.4997, not 41.88; the nearest sealed pooled number to 41.88 is this run's in-run unprojected span-F1 of 41.9035, which is a span-F1 and not an SLU-F1. And the released exemplar pool is 9,354 utterances over 37,407 recordings; the 8,554 / 34,474 figures belong to its R01-excluded sibling `size-pool-annotated-exemplars-minus-r01`. Construction/evaluation disjointness holds as designed: the ROLL-1 flight pins the minus-R01 pool (8,554 utterances) and the two PLAN rosters, which are not R01, pin the full pool (9,354).

## 1. The three channels a failed row can fail in, and where a budget can act

This system supplies knowledge through exactly three released stores, so modes (i)-(iii) are channel-local and are attributed channel by channel. A row that fails in two channels is counted once in each, and once at row level under a stated precedence.

| Store | Phase | Provider | Retrieval | Where a budget could act | Store key universe |
| --- | --- | --- | --- | --- | ---: |
| `intent-boundaries-v1` | perception | `kb-facet-v1` | top-8 of 60 by speech-keyed facet | `fuse_coverage` top_l=8, m=8, c=1; k == top_l == m, so nothing retrieved can be dropped | 60 |
| `size-pool-annotated-exemplars` | solver | `kb-facet-v1` | top-20 of the pool by speech-keyed facet | `fuse_coverage` top_l=20, m=20, c=20; again k == top_l == m | 8,554 (ROLL-1's minus-R01 pin; the two PLAN rosters pin 9,354) |
| `slot-contracts-v2` | solver | `slurp-candidate-semantic-v1` | the contracts bound to the row's at most 3 Perception candidate intents | `max_total_values` 28, `max_values_per_candidate` 16; the one place a budget can drop an already-retrieved value | 54 |

**Mode (iii) is measurably empty, and in two channels of three it is not even reachable.** Across all 2,705 rows of the three sealed populations the number of rows on which a retrieved knowledge value failed to reach the episode because of a budget is 0, and the number of such values is 0. In the two facet channels the pinned spec makes it impossible: `k` equals `top_l` equals `m`, so the retrieved set and the carried set are the same set, and the sealed rows agree -- the exemplar channel's ranked set equals its materialised set on 625/625 ROLL-1 rows, 1,080/1,080 on TRAIN Fold A and 1,000/1,000 on DEV-2000-ADDED. In the candidate-semantic channel a budget IS reachable and it never fires: the cap is 28 values and the largest set the rows ever ask it to hold is 23. The only ignored-mapping reason the receipts ever record is `shared-value-already-selected`, which is de-duplication of a value the row does receive under another candidate rather than an exclusion -- every such value appears in the row's own `qualified_selected_value_ids`. The budget is not the binding constraint, and loosening it can buy nothing.

| Arm | rows where a mapped contract was not selected | values | largest mapped set | cap `max_total_values` | ignored-mapping reasons |
| --- | ---: | ---: | ---: | --- | --- |
| `roll1` | 0 | 0 | 23 | (3, 28, 16) | `shared-value-already-selected` 3864 |
| `train-fold-a-plan` | 0 | 0 | 23 | (3, 28, 16) | `shared-value-already-selected` 6908 |
| `dev2000-added-plan` | 0 | 0 | 23 | (3, 28, 16) | `shared-value-already-selected` 7505 |

## 2. Mode shares per error class

The unit of the primary accounting is one **(row, needed knowledge item)** pair, because a row can need several items and an arbitrary per-row winner would not add up. `items` therefore sums over needed items, not rows. Percentages are of the channel's own item total for that class.

### 2.1 ROLL-1 as-flown pool (R01C construction roster, 625 rows)

**Channel 1 -- the `intent-boundaries-v1` entry for the row's own gold intent**

| Error class | (i) absent | (ii) not retrieved | (iii) budget-excluded | (iv)+(v) residual | items |
| --- | ---: | ---: | ---: | ---: | ---: |
| `INTENT-WRONG` | 0 (0.0 %) | 102 (55.4 %) | 0 (0.0 %) | 82 (44.6 %) | 184 |

**Channel 2 -- an exemplar of the row's own gold intent in the pool**

| Error class | (i) absent | (ii) not retrieved | (iii) budget-excluded | (iv)+(v) residual | items |
| --- | ---: | ---: | ---: | ---: | ---: |
| `INTENT-WRONG` | 0 (0.0 %) | 49 (26.6 %) | 0 (0.0 %) | 135 (73.4 %) | 184 |

**Channel 5 -- an exemplar demonstrating the correct EMPTY answer, needed where gold carries no entity and the row emitted one anyway**

| Error class | (i) absent | (ii) not retrieved | (iii) budget-excluded | (iv)+(v) residual | items |
| --- | ---: | ---: | ---: | ---: | ---: |
| `INTENT-WRONG` | 0 (0.0 %) | 2 (4.5 %) | 0 (0.0 %) | 42 (95.5 %) | 44 |
| `ENTITY-FP-ONLY` | 0 (0.0 %) | 5 (10.0 %) | 0 (0.0 %) | 45 (90.0 %) | 50 |

Row-level precedence view (absent > not retrieved > budget-excluded > residual), one mode per failed row: `ENTITY-FP-ONLY` (ii) not retrieved 5, (iv)+(v) residual 45; `INTENT-WRONG` (ii) not retrieved 103, (iv)+(v) residual 81.

Channels 3 and 4 are not attributable on this population: they need the gold-against-predicted slot TYPE alignment, which only the sealed bad-case bank carries, and this population has no bank entry. The rows affected are `ENTITY-FN-ONLY` 41, `ENTITY-FP-ONLY` 69, `ENTITY-MIXED` 168, `INTENT-WRONG` 184. Their contract and exemplar supply is still measured, as a supply rate rather than a per-item attribution, in section 3.

### 2.2 TRAIN Fold A PLAN (construction roster, 1,080 rows)

**Channel 1 -- the `intent-boundaries-v1` entry for the row's own gold intent**

| Error class | (i) absent | (ii) not retrieved | (iii) budget-excluded | (iv)+(v) residual | items |
| --- | ---: | ---: | ---: | ---: | ---: |
| `INTENT-WRONG` | 0 (0.0 %) | 105 (55.0 %) | 0 (0.0 %) | 86 (45.0 %) | 191 |

**Channel 2 -- an exemplar of the row's own gold intent in the pool**

| Error class | (i) absent | (ii) not retrieved | (iii) budget-excluded | (iv)+(v) residual | items |
| --- | ---: | ---: | ---: | ---: | ---: |
| `INTENT-WRONG` | 0 (0.0 %) | 36 (18.8 %) | 0 (0.0 %) | 155 (81.2 %) | 191 |

**Channel 3 -- the `slot-contracts-v2` entry for each slot TYPE the row missed**

| Error class | (i) absent | (ii) not retrieved | (iii) budget-excluded | (iv)+(v) residual | items |
| --- | ---: | ---: | ---: | ---: | ---: |
| `INTENT-WRONG` | 0 (0.0 %) | 19 (24.7 %) | 0 (0.0 %) | 58 (75.3 %) | 77 |
| `ENTITY-MIXED` | 1 (0.4 %) | 3 (1.2 %) | 0 (0.0 %) | 236 (98.3 %) | 240 |
| `ENTITY-FN-ONLY` | 0 (0.0 %) | 1 (1.2 %) | 0 (0.0 %) | 84 (98.8 %) | 85 |
| `MALFORMED` | 0 (0.0 %) | 0 (0.0 %) | 0 (0.0 %) | 1 (100.0 %) | 1 |

**Channel 4 -- an exemplar demonstrating each slot TYPE the row missed**

| Error class | (i) absent | (ii) not retrieved | (iii) budget-excluded | (iv)+(v) residual | items |
| --- | ---: | ---: | ---: | ---: | ---: |
| `INTENT-WRONG` | 0 (0.0 %) | 9 (11.7 %) | 0 (0.0 %) | 68 (88.3 %) | 77 |
| `ENTITY-MIXED` | 1 (0.4 %) | 19 (7.9 %) | 0 (0.0 %) | 220 (91.7 %) | 240 |
| `ENTITY-FN-ONLY` | 0 (0.0 %) | 4 (4.7 %) | 0 (0.0 %) | 81 (95.3 %) | 85 |
| `MALFORMED` | 0 (0.0 %) | 0 (0.0 %) | 0 (0.0 %) | 1 (100.0 %) | 1 |

**Channel 5 -- an exemplar demonstrating the correct EMPTY answer, needed where gold carries no entity and the row emitted one anyway**

| Error class | (i) absent | (ii) not retrieved | (iii) budget-excluded | (iv)+(v) residual | items |
| --- | ---: | ---: | ---: | ---: | ---: |
| `INTENT-WRONG` | 0 (0.0 %) | 1 (1.7 %) | 0 (0.0 %) | 58 (98.3 %) | 59 |
| `ENTITY-FP-ONLY` | 0 (0.0 %) | 7 (6.2 %) | 0 (0.0 %) | 106 (93.8 %) | 113 |

Row-level precedence view (absent > not retrieved > budget-excluded > residual), one mode per failed row: `ENTITY-FN-ONLY` (ii) not retrieved 1, (iv)+(v) residual 83; `ENTITY-FP-ONLY` (ii) not retrieved 7, (iv)+(v) residual 106; `ENTITY-MIXED` (i) absent 1, (ii) not retrieved 2, (iv)+(v) residual 190; `INTENT-WRONG` (ii) not retrieved 108, (iv)+(v) residual 83; `MALFORMED` (iv)+(v) residual 1.

### 2.3 DEV-2000-ADDED PLAN (fresh roster, 1,000 rows)

**Channel 1 -- the `intent-boundaries-v1` entry for the row's own gold intent**

| Error class | (i) absent | (ii) not retrieved | (iii) budget-excluded | (iv)+(v) residual | items |
| --- | ---: | ---: | ---: | ---: | ---: |
| `INTENT-WRONG` | 0 (0.0 %) | 149 (64.2 %) | 0 (0.0 %) | 83 (35.8 %) | 232 |

**Channel 2 -- an exemplar of the row's own gold intent in the pool**

| Error class | (i) absent | (ii) not retrieved | (iii) budget-excluded | (iv)+(v) residual | items |
| --- | ---: | ---: | ---: | ---: | ---: |
| `INTENT-WRONG` | 0 (0.0 %) | 44 (19.0 %) | 0 (0.0 %) | 188 (81.0 %) | 232 |

**Channel 3 -- the `slot-contracts-v2` entry for each slot TYPE the row missed**

| Error class | (i) absent | (ii) not retrieved | (iii) budget-excluded | (iv)+(v) residual | items |
| --- | ---: | ---: | ---: | ---: | ---: |
| `INTENT-WRONG` | 0 (0.0 %) | 27 (25.2 %) | 0 (0.0 %) | 80 (74.8 %) | 107 |
| `ENTITY-MIXED` | 0 (0.0 %) | 2 (0.9 %) | 0 (0.0 %) | 233 (99.1 %) | 235 |
| `ENTITY-FN-ONLY` | 0 (0.0 %) | 0 (0.0 %) | 0 (0.0 %) | 72 (100.0 %) | 72 |
| `MALFORMED` | 0 (0.0 %) | 0 (0.0 %) | 0 (0.0 %) | 7 (100.0 %) | 7 |

**Channel 4 -- an exemplar demonstrating each slot TYPE the row missed**

| Error class | (i) absent | (ii) not retrieved | (iii) budget-excluded | (iv)+(v) residual | items |
| --- | ---: | ---: | ---: | ---: | ---: |
| `INTENT-WRONG` | 0 (0.0 %) | 19 (17.8 %) | 0 (0.0 %) | 88 (82.2 %) | 107 |
| `ENTITY-MIXED` | 0 (0.0 %) | 10 (4.3 %) | 0 (0.0 %) | 225 (95.7 %) | 235 |
| `ENTITY-FN-ONLY` | 0 (0.0 %) | 5 (6.9 %) | 0 (0.0 %) | 67 (93.1 %) | 72 |
| `MALFORMED` | 0 (0.0 %) | 0 (0.0 %) | 0 (0.0 %) | 7 (100.0 %) | 7 |

**Channel 5 -- an exemplar demonstrating the correct EMPTY answer, needed where gold carries no entity and the row emitted one anyway**

| Error class | (i) absent | (ii) not retrieved | (iii) budget-excluded | (iv)+(v) residual | items |
| --- | ---: | ---: | ---: | ---: | ---: |
| `INTENT-WRONG` | 0 (0.0 %) | 5 (8.2 %) | 0 (0.0 %) | 56 (91.8 %) | 61 |
| `ENTITY-FP-ONLY` | 0 (0.0 %) | 4 (4.4 %) | 0 (0.0 %) | 87 (95.6 %) | 91 |

Row-level precedence view (absent > not retrieved > budget-excluded > residual), one mode per failed row: `ENTITY-FN-ONLY` (iv)+(v) residual 65; `ENTITY-FP-ONLY` (ii) not retrieved 4, (iv)+(v) residual 87; `ENTITY-MIXED` (ii) not retrieved 2, (iv)+(v) residual 193; `INTENT-WRONG` (ii) not retrieved 155, (iv)+(v) residual 77; `MALFORMED` (iv)+(v) residual 2.

## 3. Supply rates on every row, failures and successes alike

A retrieval rate only reads as a defect beside the rate on the rows that worked. `gold types` columns are shares of the row's own gold slot TYPEs; the last two columns are the empty-answer demonstration the pool can supply.

| Arm | Class | Rows | gold intent's boundary delivered | an exemplar of the gold intent delivered | gold types whose contract was materialised | gold types an exemplar demonstrated | received an entity-free exemplar | entity-free exemplars per row |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `roll1` | `CORRECT` | 163 | 95.1 % | 97.5 % | 100.0 % | 98.8 % | 68.1 % | 4.48 |
| `roll1` | `INTENT-WRONG` | 184 | 44.6 % | 73.4 % | 80.4 % | 86.5 % | 82.1 % | 4.65 |
| `roll1` | `ENTITY-MIXED` | 168 | 92.9 % | 98.2 % | 99.0 % | 98.3 % | 62.5 % | 2.21 |
| `roll1` | `ENTITY-FN-ONLY` | 41 | 97.6 % | 97.6 % | 98.6 % | 98.6 % | 61.0 % | 2.17 |
| `roll1` | `ENTITY-FP-ONLY` | 69 | 89.9 % | 95.7 % | 100.0 % | 100.0 % | 82.6 % | 5.33 |
| `train-fold-a-plan` | `CORRECT` | 480 | 97.3 % | 98.8 % | 99.4 % | 99.4 % | 82.5 % | 5.45 |
| `train-fold-a-plan` | `INTENT-WRONG` | 191 | 45.0 % | 81.2 % | 83.6 % | 91.4 % | 83.8 % | 5.32 |
| `train-fold-a-plan` | `ENTITY-MIXED` | 193 | 96.9 % | 98.4 % | 98.2 % | 93.0 % | 62.7 % | 1.98 |
| `train-fold-a-plan` | `ENTITY-FN-ONLY` | 84 | 97.6 % | 98.8 % | 99.2 % | 97.0 % | 65.5 % | 2.32 |
| `train-fold-a-plan` | `ENTITY-FP-ONLY` | 131 | 94.7 % | 99.2 % | 100.0 % | 100.0 % | 89.3 % | 5.79 |
| `train-fold-a-plan` | `MALFORMED` | 1 | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 0.0 % | 0.00 |
| `dev2000-added-plan` | `CORRECT` | 398 | 94.5 % | 99.5 % | 100.0 % | 99.7 % | 80.9 % | 4.09 |
| `dev2000-added-plan` | `INTENT-WRONG` | 232 | 35.8 % | 81.0 % | 81.8 % | 86.9 % | 80.2 % | 4.79 |
| `dev2000-added-plan` | `ENTITY-MIXED` | 195 | 96.9 % | 99.0 % | 99.4 % | 95.5 % | 61.5 % | 2.09 |
| `dev2000-added-plan` | `ENTITY-FN-ONLY` | 65 | 93.8 % | 98.5 % | 100.0 % | 94.8 % | 58.5 % | 2.60 |
| `dev2000-added-plan` | `ENTITY-FP-ONLY` | 108 | 96.3 % | 100.0 % | 100.0 % | 100.0 % | 88.9 % | 5.29 |
| `dev2000-added-plan` | `MALFORMED` | 2 | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 50.0 % | 1.50 |

## 4. What modes (iv) and (v) cannot be split into here

The residual bucket is modes (iv) *delivered but ignored or misused* and (v) *locally correct but later overwritten* taken together, and **this read cannot split them**. Splitting requires re-execution: (iv) needs the counterfactual answer the row would have given without that item and (v) needs the intermediate state re-run forward, and neither is a function of bytes already sealed. The sealed `consumption` trace does carry a per-item `outcome` field whose values are `use` and `ignore`, and a `copy_rate`, but that field is a textual-overlap attribution made at trace time rather than a counterfactual, so it bounds neither mode and is deliberately not used as a substitute here. What this read can state about the residual without contacts is its size, above, and that it is where the entity mass sits.

## 5. Coverage inside the existing sources

| Quantity | Value |
| --- | ---: |
| `intent-boundaries-v1` entries (one per intent) | 60 |
| `slot-contracts-v2` entries (one per slot type) | 54 |
| `size-pool-annotated-exemplars` utterances | 9354 |
| `size-pool-annotated-exemplars-minus-r01` utterances | 8554 |
| governed SLURP TRAIN utterances | 11514 |
| distinct TRAIN intents (`scenario_action`) | 60 |
| distinct TRAIN scenarios | 18 |
| distinct TRAIN slot types | 55 |
| TRAIN utterances whose gold carries no entity | 3755 |
| pool utterances whose gold carries no entity | 2949 |
| minus-R01 pool utterances whose gold carries no entity | 2741 |
| TRAIN utterances the released pool does not use | 2160 |
| TRAIN utterances the minus-R01 pool does not use | 2960 |
| of the unused remainder, entity-free | 806 |
| intents the unused remainder touches | 60 |
| slot types the unused remainder touches | 49 |

**The classes the store says nothing about, and the mass they carry.** Every one of the 60 TRAIN intents has an `intent-boundaries-v1` entry, so at intent level the store's coverage is complete and mode (i) is zero by construction. At slot level 54 of the 55 TRAIN slot types have a contract; the one exception is `music_album`, and it carries 1 gold mention and 1 false negative against the 1,881 gold mentions and 824 false negatives the two PLAN rosters carry between them. Widening the net to every slot type the exemplar pool shows at most ten times catches 12 types, and together they carry 13 gold mentions (0.7 % of the gold mass), 10 false negatives (1.2 %) and 22 false positives (2.3 %). A class the store is silent about would be the clearest case for expansion, and on this measurement there is no such class with any mass. Two rows of the per-type table are not gold classes at all: `none` and `general_quirky` appear only on the false-positive side because they are type names the system emitted that SLURP's vocabulary does not contain, and there is nothing for a store to say about them.

**One prior record is corrected by this read.** The 2026-09-24 bad-case bank reported the exemplar pool as entity-bearing by construction, with zero exemplars carrying no entity, and concluded that the Solver never sees an example of the correct empty answer. Measured against the released snapshot joined to the governed gold, 2,949 of the 9,354 pool utterances (31.5 %) carry no gold entity at all, and the sealed rows show them being delivered: 89.3 % of the TRAIN Fold A `ENTITY-FP-ONLY` rows receive at least one entity-free exemplar, 5.79 of them on average. The bank's zero was an artefact of parsing the rendered exemplar body rather than joining the pool to the gold. The empty-answer gap is therefore not an absence in the source; it is a use failure, and it lands in the residual bucket.

### 5.1 Per scenario

| Scenario | boundary entries | pool utterances | minus-R01 pool | TRAIN | TRAIN unused by pool | bank rows | bank any-error rate | ROLL-1 rows | ROLL-1 intent-error rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `alarm` | 3 | 270 | 225 | 390 | 120 | 60 | 41.7 % | 26 | 11.5 % |
| `audio` | 4 | 170 | 125 | 290 | 120 | 60 | 40.0 % | 30 | 30.0 % |
| `calendar` | 3 | 1568 | 1523 | 1688 | 120 | 281 | 70.5 % | 42 | 40.5 % |
| `cooking` | 2 | 91 | 46 | 211 | 120 | 60 | 63.3 % | 31 | 32.3 % |
| `datetime` | 2 | 282 | 237 | 402 | 120 | 69 | 52.2 % | 39 | 17.9 % |
| `email` | 4 | 833 | 788 | 953 | 120 | 156 | 55.1 % | 33 | 24.2 % |
| `general` | 3 | 532 | 487 | 652 | 120 | 122 | 78.7 % | 42 | 88.1 % |
| `iot` | 9 | 649 | 604 | 769 | 120 | 117 | 50.4 % | 33 | 27.3 % |
| `lists` | 3 | 419 | 375 | 539 | 120 | 112 | 38.4 % | 37 | 16.2 % |
| `music` | 4 | 212 | 168 | 332 | 120 | 60 | 43.3 % | 27 | 37.0 % |
| `news` | 1 | 383 | 339 | 503 | 120 | 80 | 43.8 % | 36 | 27.8 % |
| `play` | 5 | 1257 | 1213 | 1377 | 120 | 263 | 64.3 % | 37 | 27.0 % |
| `qa` | 5 | 1063 | 1019 | 1183 | 120 | 217 | 59.9 % | 38 | 42.1 % |
| `recommendation` | 3 | 313 | 269 | 433 | 120 | 66 | 48.5 % | 29 | 17.2 % |
| `social` | 2 | 271 | 227 | 391 | 120 | 64 | 73.4 % | 35 | 22.9 % |
| `takeaway` | 2 | 137 | 93 | 257 | 120 | 60 | 61.7 % | 37 | 24.3 % |
| `transport` | 4 | 451 | 407 | 571 | 120 | 108 | 55.6 % | 32 | 21.9 % |
| `weather` | 1 | 453 | 409 | 573 | 120 | 125 | 48.8 % | 41 | 7.3 % |

### 5.2 Per slot type

Gold mentions, FN and FP are the two PLAN rosters' pooled mass; a type with no gold mention appears only because the system emitted it.

| Slot type | contract entries | pool utterances | minus-R01 pool | TRAIN | TRAIN unused by pool | gold mentions | FN | FP | FN rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `alarm_type` | 1 | 9 | 7 | 9 | 0 | 0 | 0 | 4 | 0.0 % |
| `app_name` | 1 | 46 | 43 | 51 | 5 | 8 | 5 | 2 | 62.5 % |
| `artist_name` | 1 | 209 | 191 | 228 | 19 | 43 | 17 | 22 | 39.5 % |
| `audiobook_author` | 1 | 6 | 5 | 6 | 0 | 0 | 0 | 0 | 0.0 % |
| `audiobook_name` | 1 | 65 | 61 | 73 | 8 | 16 | 12 | 7 | 75.0 % |
| `business_name` | 1 | 280 | 227 | 379 | 99 | 68 | 39 | 47 | 57.4 % |
| `business_type` | 1 | 139 | 115 | 189 | 50 | 30 | 15 | 16 | 50.0 % |
| `change_amount` | 1 | 40 | 31 | 49 | 9 | 6 | 4 | 10 | 66.7 % |
| `coffee_type` | 1 | 18 | 14 | 22 | 4 | 0 | 0 | 0 | 0.0 % |
| `color_type` | 1 | 76 | 68 | 93 | 17 | 13 | 1 | 5 | 7.7 % |
| `cooking_type` | 1 | 11 | 4 | 17 | 6 | 2 | 2 | 4 | 100.0 % |
| `currency_name` | 1 | 109 | 108 | 117 | 8 | 26 | 13 | 21 | 50.0 % |
| `date` | 1 | 1515 | 1365 | 1777 | 262 | 310 | 142 | 71 | 45.8 % |
| `definition_word` | 1 | 208 | 208 | 225 | 17 | 38 | 10 | 43 | 26.3 % |
| `device_type` | 1 | 189 | 167 | 224 | 35 | 28 | 13 | 35 | 46.4 % |
| `drink_type` | 1 | 6 | 4 | 9 | 3 | 3 | 0 | 4 | 0.0 % |
| `email_address` | 1 | 29 | 28 | 31 | 2 | 1 | 1 | 10 | 100.0 % |
| `email_folder` | 1 | 30 | 30 | 32 | 2 | 4 | 2 | 7 | 50.0 % |
| `event_name` | 1 | 897 | 838 | 985 | 88 | 154 | 72 | 68 | 46.8 % |
| `food_type` | 1 | 157 | 96 | 288 | 131 | 64 | 22 | 39 | 34.4 % |
| `game_name` | 1 | 77 | 74 | 87 | 10 | 20 | 7 | 10 | 35.0 % |
| `game_type` | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 0 | 100.0 % |
| `general_frequency` | 1 | 76 | 71 | 84 | 8 | 17 | 9 | 26 | 52.9 % |
| `general_quirky` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0.0 % |
| `house_place` | 1 | 166 | 151 | 197 | 31 | 34 | 10 | 20 | 29.4 % |
| `ingredient` | 1 | 7 | 2 | 18 | 11 | 4 | 4 | 3 | 100.0 % |
| `joke_type` | 1 | 27 | 27 | 34 | 7 | 11 | 5 | 27 | 45.5 % |
| `list_name` | 1 | 148 | 122 | 190 | 42 | 38 | 9 | 30 | 23.7 % |
| `meal_type` | 1 | 54 | 51 | 63 | 9 | 18 | 10 | 4 | 55.6 % |
| `media_type` | 1 | 356 | 310 | 474 | 118 | 88 | 36 | 31 | 40.9 % |
| `movie_name` | 1 | 14 | 13 | 16 | 2 | 0 | 0 | 1 | 0.0 % |
| `movie_type` | 1 | 10 | 5 | 10 | 0 | 0 | 0 | 1 | 0.0 % |
| `music_album` | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 100.0 % |
| `music_descriptor` | 1 | 38 | 31 | 45 | 7 | 5 | 4 | 11 | 80.0 % |
| `music_genre` | 1 | 159 | 152 | 180 | 21 | 34 | 9 | 7 | 26.5 % |
| `news_topic` | 1 | 146 | 119 | 182 | 36 | 27 | 13 | 22 | 48.1 % |
| `none` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0.0 % |
| `order_type` | 1 | 60 | 43 | 106 | 46 | 22 | 17 | 3 | 77.3 % |
| `person` | 1 | 749 | 690 | 848 | 99 | 117 | 57 | 85 | 48.7 % |
| `personal_info` | 1 | 66 | 60 | 74 | 8 | 10 | 8 | 5 | 80.0 % |
| `place_name` | 1 | 806 | 697 | 998 | 192 | 167 | 56 | 63 | 33.5 % |
| `player_setting` | 1 | 135 | 126 | 156 | 21 | 34 | 17 | 17 | 50.0 % |
| `playlist_name` | 1 | 60 | 58 | 62 | 2 | 6 | 2 | 11 | 33.3 % |
| `podcast_descriptor` | 1 | 62 | 61 | 67 | 5 | 8 | 4 | 14 | 50.0 % |
| `podcast_name` | 1 | 50 | 49 | 56 | 6 | 10 | 7 | 3 | 70.0 % |
| `radio_name` | 1 | 114 | 110 | 129 | 15 | 23 | 15 | 19 | 65.2 % |
| `relation` | 1 | 223 | 200 | 246 | 23 | 40 | 22 | 8 | 55.0 % |
| `song_name` | 1 | 115 | 106 | 127 | 12 | 22 | 14 | 17 | 63.6 % |
| `sport_type` | 1 | 5 | 4 | 5 | 0 | 1 | 1 | 0 | 100.0 % |
| `time` | 1 | 618 | 538 | 758 | 140 | 136 | 54 | 48 | 39.7 % |
| `time_zone` | 1 | 32 | 24 | 45 | 13 | 7 | 2 | 2 | 28.6 % |
| `timeofday` | 1 | 207 | 185 | 239 | 32 | 42 | 13 | 13 | 31.0 % |
| `transport_agency` | 1 | 31 | 30 | 31 | 0 | 4 | 0 | 1 | 0.0 % |
| `transport_descriptor` | 1 | 7 | 6 | 8 | 1 | 0 | 0 | 1 | 0.0 % |
| `transport_name` | 1 | 6 | 3 | 9 | 3 | 3 | 3 | 2 | 100.0 % |
| `transport_type` | 1 | 242 | 219 | 316 | 74 | 58 | 22 | 9 | 37.9 % |
| `weather_descriptor` | 1 | 246 | 219 | 308 | 62 | 59 | 22 | 18 | 37.3 % |

### 5.3 Per intent

| Intent | boundary entry | pool utterances | minus-R01 pool | TRAIN | TRAIN unused | bank rows | bank intent-error rate | bank any-error rate | ROLL-1 rows | ROLL-1 intent-error rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `alarm_query` | 1 | 85 | 73 | 130 | 45 | 19 | 15.8 % | 21.1 % | 6 | 0.0 % |
| `alarm_remove` | 1 | 55 | 42 | 78 | 23 | 8 | 0.0 % | 50.0 % | 8 | 25.0 % |
| `alarm_set` | 1 | 130 | 110 | 182 | 52 | 33 | 9.1 % | 51.5 % | 12 | 8.3 % |
| `audio_volume_down` | 1 | 33 | 25 | 52 | 19 | 8 | 12.5 % | 12.5 % | 5 | 20.0 % |
| `audio_volume_mute` | 1 | 60 | 45 | 110 | 50 | 24 | 33.3 % | 58.3 % | 10 | 40.0 % |
| `audio_volume_other` | 1 | 12 | 8 | 18 | 6 | 4 | 100.0 % | 100.0 % | 0 | 0.0 % |
| `audio_volume_up` | 1 | 65 | 47 | 110 | 45 | 24 | 4.2 % | 20.8 % | 15 | 26.7 % |
| `calendar_query` | 1 | 511 | 488 | 566 | 55 | 107 | 43.0 % | 72.9 % | 22 | 68.2 % |
| `calendar_remove` | 1 | 293 | 290 | 312 | 19 | 42 | 9.5 % | 50.0 % | 3 | 0.0 % |
| `calendar_set` | 1 | 764 | 745 | 810 | 46 | 132 | 22.7 % | 75.0 % | 17 | 11.8 % |
| `cooking_query` | 1 | 3 | 0 | 4 | 1 | 1 | 100.0 % | 100.0 % | 0 | 0.0 % |
| `cooking_recipe` | 1 | 88 | 46 | 207 | 119 | 59 | 13.6 % | 62.7 % | 31 | 32.3 % |
| `datetime_convert` | 1 | 38 | 23 | 52 | 14 | 10 | 10.0 % | 50.0 % | 12 | 0.0 % |
| `datetime_query` | 1 | 244 | 214 | 350 | 106 | 59 | 11.9 % | 52.5 % | 27 | 25.9 % |
| `email_addcontact` | 1 | 44 | 43 | 54 | 10 | 9 | 11.1 % | 44.4 % | 0 | 0.0 % |
| `email_query` | 1 | 360 | 350 | 418 | 58 | 75 | 13.3 % | 49.3 % | 8 | 25.0 % |
| `email_querycontact` | 1 | 115 | 106 | 127 | 12 | 16 | 31.2 % | 81.2 % | 5 | 40.0 % |
| `email_sendemail` | 1 | 314 | 289 | 354 | 40 | 56 | 12.5 % | 57.1 % | 20 | 20.0 % |
| `general_greet` | 1 | 18 | 18 | 25 | 7 | 6 | 0.0 % | 16.7 % | 0 | 0.0 % |
| `general_joke` | 1 | 58 | 57 | 72 | 14 | 20 | 0.0 % | 55.0 % | 1 | 0.0 % |
| `general_quirky` | 1 | 456 | 412 | 555 | 99 | 96 | 80.2 % | 87.5 % | 41 | 90.2 % |
| `iot_cleaning` | 1 | 80 | 71 | 93 | 13 | 14 | 14.3 % | 50.0 % | 8 | 12.5 % |
| `iot_coffee` | 1 | 108 | 99 | 124 | 16 | 13 | 0.0 % | 15.4 % | 7 | 14.3 % |
| `iot_hue_lightchange` | 1 | 102 | 92 | 125 | 23 | 18 | 5.6 % | 44.4 % | 8 | 37.5 % |
| `iot_hue_lightdim` | 1 | 63 | 62 | 76 | 13 | 19 | 26.3 % | 63.2 % | 0 | 0.0 % |
| `iot_hue_lightoff` | 1 | 128 | 124 | 153 | 25 | 22 | 9.1 % | 59.1 % | 1 | 0.0 % |
| `iot_hue_lighton` | 1 | 16 | 15 | 22 | 6 | 6 | 33.3 % | 100.0 % | 0 | 0.0 % |
| `iot_hue_lightup` | 1 | 67 | 63 | 76 | 9 | 15 | 0.0 % | 40.0 % | 4 | 25.0 % |
| `iot_wemo_off` | 1 | 46 | 42 | 52 | 6 | 4 | 0.0 % | 25.0 % | 2 | 50.0 % |
| `iot_wemo_on` | 1 | 39 | 36 | 48 | 9 | 6 | 0.0 % | 66.7 % | 3 | 66.7 % |
| `lists_createoradd` | 1 | 134 | 117 | 177 | 43 | 33 | 15.2 % | 45.5 % | 15 | 6.7 % |
| `lists_query` | 1 | 152 | 139 | 198 | 46 | 48 | 18.8 % | 22.9 % | 11 | 36.4 % |
| `lists_remove` | 1 | 133 | 119 | 164 | 31 | 31 | 9.7 % | 54.8 % | 11 | 9.1 % |
| `music_dislikeness` | 1 | 7 | 6 | 14 | 7 | 1 | 0.0 % | 0.0 % | 0 | 0.0 % |
| `music_likeness` | 1 | 76 | 64 | 113 | 37 | 18 | 16.7 % | 27.8 % | 7 | 28.6 % |
| `music_query` | 1 | 97 | 71 | 154 | 57 | 32 | 18.8 % | 46.9 % | 18 | 33.3 % |
| `music_settings` | 1 | 32 | 27 | 51 | 19 | 9 | 33.3 % | 66.7 % | 2 | 100.0 % |
| `news_query` | 1 | 383 | 339 | 503 | 120 | 80 | 13.8 % | 43.8 % | 36 | 27.8 % |
| `play_audiobook` | 1 | 134 | 125 | 150 | 16 | 38 | 15.8 % | 81.6 % | 6 | 16.7 % |
| `play_game` | 1 | 101 | 98 | 112 | 11 | 23 | 13.0 % | 39.1 % | 3 | 0.0 % |
| `play_music` | 1 | 590 | 570 | 639 | 49 | 118 | 23.7 % | 61.9 % | 18 | 33.3 % |
| `play_podcasts` | 1 | 175 | 171 | 193 | 18 | 34 | 8.8 % | 67.6 % | 4 | 50.0 % |
| `play_radio` | 1 | 257 | 249 | 283 | 26 | 50 | 14.0 % | 66.0 % | 6 | 16.7 % |
| `qa_currency` | 1 | 130 | 128 | 142 | 12 | 33 | 3.0 % | 57.6 % | 2 | 0.0 % |
| `qa_definition` | 1 | 246 | 246 | 267 | 21 | 54 | 14.8 % | 50.0 % | 0 | 0.0 % |
| `qa_factoid` | 1 | 484 | 448 | 544 | 60 | 94 | 47.9 % | 72.3 % | 33 | 48.5 % |
| `qa_maths` | 1 | 68 | 66 | 78 | 10 | 13 | 7.7 % | 23.1 % | 1 | 0.0 % |
| `qa_stock` | 1 | 135 | 131 | 152 | 17 | 23 | 13.0 % | 56.5 % | 2 | 0.0 % |
| `recommendation_events` | 1 | 134 | 118 | 190 | 56 | 24 | 0.0 % | 37.5 % | 10 | 20.0 % |
| `recommendation_locations` | 1 | 128 | 109 | 173 | 45 | 32 | 15.6 % | 62.5 % | 16 | 12.5 % |
| `recommendation_movies` | 1 | 51 | 42 | 70 | 19 | 10 | 10.0 % | 30.0 % | 3 | 33.3 % |
| `social_post` | 1 | 197 | 166 | 283 | 86 | 49 | 20.4 % | 71.4 % | 27 | 22.2 % |
| `social_query` | 1 | 74 | 61 | 108 | 34 | 15 | 40.0 % | 80.0 % | 8 | 25.0 % |
| `takeaway_order` | 1 | 75 | 46 | 135 | 60 | 29 | 27.6 % | 65.5 % | 23 | 26.1 % |
| `takeaway_query` | 1 | 62 | 47 | 122 | 60 | 31 | 3.2 % | 58.1 % | 14 | 21.4 % |
| `transport_query` | 1 | 177 | 151 | 227 | 50 | 36 | 11.1 % | 52.8 % | 21 | 23.8 % |
| `transport_taxi` | 1 | 78 | 73 | 100 | 22 | 25 | 0.0 % | 60.0 % | 2 | 0.0 % |
| `transport_ticket` | 1 | 97 | 91 | 127 | 30 | 23 | 21.7 % | 78.3 % | 4 | 25.0 % |
| `transport_traffic` | 1 | 99 | 92 | 117 | 18 | 24 | 4.2 % | 33.3 % | 5 | 20.0 % |
| `weather_query` | 1 | 453 | 409 | 573 | 120 | 125 | 6.4 % | 48.8 % | 41 | 7.3 % |

## 6. Does the error rate fall as a class gets more knowledge?

| Relationship | Classes | Spearman rho | CI90 | Pearson r on log1p(count) | slope pp per log1p unit | residual SD pp | outcome SD pp | R^2 |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| per intent: exemplar-pool utterances vs any-error rate (bank rosters, >= 10 rows) | 49 | 0.265 | [0.032, 0.472] | 0.345 | 8.32 | 16.55 | 17.45 | 0.119 |
| per intent: exemplar-pool utterances vs intent-error rate (bank rosters, >= 10 rows) | 49 | 0.255 | [-0.014, 0.492] | 0.367 | 7.31 | 13.53 | 14.40 | 0.135 |
| per intent: minus-R01 pool utterances vs ROLL-1 intent-error rate (>= 5 rows) | 37 | 0.095 | [-0.212, 0.390] | 0.309 | 6.02 | 16.80 | 17.41 | 0.095 |
| per slot type: exemplar-pool utterances vs FN rate (bank rosters, >= 10 gold mentions) | 33 | -0.396 | [-0.629, -0.098] | -0.299 | -5.37 | 15.84 | 16.33 | 0.089 |
| per scenario: exemplar-pool utterances vs any-error rate (bank rosters, >= 10 rows) | 18 | 0.323 | [-0.089, 0.694] | 0.268 | 4.19 | 11.84 | 11.92 | 0.072 |

*per intent: exemplar-pool utterances vs any-error rate (bank rosters, >= 10 rows)* -- quartiles of the knowledge count against the class's own error rate:

| Quartile | Classes | count min | count median | count max | mean error rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 12 | 38 | 65 | 76 | 47.6 % |
| 2 | 12 | 78 | 99 | 128 | 49.3 % |
| 3 | 13 | 128 | 134 | 244 | 55.0 % |
| 4 | 12 | 246 | 453 | 764 | 61.2 % |

*per intent: exemplar-pool utterances vs intent-error rate (bank rosters, >= 10 rows)* -- quartiles of the knowledge count against the class's own error rate:

| Quartile | Classes | count min | count median | count max | mean error rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 12 | 38 | 65 | 76 | 14.9 % |
| 2 | 12 | 78 | 99 | 128 | 12.3 % |
| 3 | 13 | 128 | 134 | 244 | 11.7 % |
| 4 | 12 | 246 | 453 | 764 | 25.2 % |

*per intent: minus-R01 pool utterances vs ROLL-1 intent-error rate (>= 5 rows)* -- quartiles of the knowledge count against the class's own error rate:

| Quartile | Classes | count min | count median | count max | mean error rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 9 | 23 | 46 | 61 | 24.0 % |
| 2 | 9 | 64 | 92 | 109 | 22.1 % |
| 3 | 10 | 110 | 139 | 249 | 18.6 % |
| 4 | 9 | 289 | 412 | 745 | 36.9 % |

*per slot type: exemplar-pool utterances vs FN rate (bank rosters, >= 10 gold mentions)* -- quartiles of the knowledge count against the class's own error rate:

| Quartile | Classes | count min | count median | count max | mean error rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 8 | 27 | 65 | 76 | 58.0 % |
| 2 | 8 | 77 | 135 | 148 | 48.2 % |
| 3 | 9 | 157 | 207 | 242 | 36.3 % |
| 4 | 8 | 246 | 749 | 1515 | 43.8 % |

*per scenario: exemplar-pool utterances vs any-error rate (bank rosters, >= 10 rows)* -- quartiles of the knowledge count against the class's own error rate:

| Quartile | Classes | count min | count median | count max | mean error rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 4 | 91 | 170 | 212 | 52.1 % |
| 2 | 5 | 270 | 282 | 383 | 51.9 % |
| 3 | 5 | 419 | 453 | 649 | 54.4 % |
| 4 | 4 | 833 | 1257 | 1568 | 62.4 % |

**The honest reading.** Volume does not govern the error rate, and its sign is not even stable across class families. At slot-type level more exemplars go with a lower miss rate -- Spearman rho -0.396, CI90 [-0.629, -0.098], an interval that excludes zero -- but the fit explains only 8.9 % of the between-type variance and the residual spread around it, 15.84 pp, is 97 % of the spread it started from. Doubling a type's exemplar count buys about 3.7 pp of miss rate against a between-type spread of 16.3 pp. At intent level the sign REVERSES: rho +0.265, CI90 [0.032, 0.472] -- the intents with the most exemplars have the HIGHER error rate, because the frequent intents are the confusable ones, so volume is confounded with difficulty rather than protective against it. On ROLL-1 the same relationship is indistinguishable from nothing: rho +0.095, CI90 [-0.212, 0.390]. The quartile curves say it the other way round: they are flat to non-monotone, with no knee to point at. There is therefore no count at which a curve flattens, because there is no falling curve to flatten. The reading the owner asked for follows: more of the same does not buy accuracy, and the bottleneck is retrievability, not volume.

## 7. The unused remainder of TRAIN

The released pool uses 9,354 of the 11,514 governed TRAIN utterances, leaving 2,160 unused (18.8 %); against the R01-excluded sibling the unused remainder is 2,960 (25.7 %). The remainder is not concentrated where the pool is thin. It touches all 60 intents and 49 of the 55 slot types, which makes it a thin uniform layer rather than a reserve aimed at the gaps -- and section 5.1 shows why, because the remainder is exactly 120 utterances in every one of the 18 scenarios, an equal-stratum hold-back by construction rather than a residue that could happen to sit where the coverage is worst. Every one of the 16 bottom-quartile intents does have unused TRAIN rows available, but they amount to 270 utterances in total across all of them, against the 157 roster rows those intents carry; on the slot side only 10 of 17 bottom-quartile types have any unused rows at all, totalling 40 utterances against 27 gold mentions. Legality, stated explicitly: the remainder is TRAIN, so it is legal construction material for any roster not drawn from it, and an expansion aimed at an R01-family evaluation must come from the minus-R01 remainder (2,960 utterances) rather than the full one, exactly as the ROLL-1 flight's own pin already does. One further fact would make an expansion cheap if it were ever wanted: the pinned facet-vector sidecar this system retrieves against already carries 11,514 rows -- all of TRAIN, not just the pool -- so widening the store needs no new encoding contact. That is a statement about cost, not a recommendation; the measurement above says the rows are not what is missing.

| Class family | Classes the pool under-covers | of those, with unused TRAIN available | unused utterances they carry | their error mass |
| --- | ---: | ---: | ---: | ---: |
| intents in the bottom quartile of pool coverage (at most 62 pool utterances) | 16 | 16 | 270 | 157 |
| slot types in the bottom quartile of pool coverage (at most 29 pool utterances) | 17 | 10 | 40 | 27 |

## 8. The answer to the owner's question

**The binding constraint is UNRETRIEVED knowledge, and the measurement is not close.** Absent knowledge is ruled out: all 60 intents have a boundary entry, 54 of 55 slot types have a contract, the one uncovered type carries 1 gold mention and 1 false negative of 1,881 and 824, and mode (i) totals two items across every channel of all three populations -- both of them on one single row, and both of them that same uncovered type. Excluded knowledge is ruled out harder: mode (iii) is 0 rows and 0 values across all 2,705 rows, it is structurally unreachable in two of the three channels, and in the third the cap is 28 against a peak demand of 23 -- there is no budget to loosen. What is left is mode (ii), and it owns the intent errors: of the 184 ROLL-1 intent-wrong rows, 102 (55.4 %) never received the boundary entry for their own gold intent although the store holds it, and the same figure is 55.0 % on TRAIN Fold A (105 of 191) and 64.2 % on DEV-2000-ADDED (149 of 232). What makes this a retrieval finding rather than a difficulty finding is the same quantity on the rows that worked: the gold intent's boundary reaches 95.1 % of ROLL-1's correct rows against 44.6 % of its intent-wrong rows, a gap of 50.5 points on a store whose coverage is complete, against 89.9 to 97.6 % on the entity classes, which do not carry this defect. **The entity errors are a different story and it is not a knowledge story at all.** On the entity-error classes the contract for the missed type had been materialised into the row for 98.2 % of gold types, an exemplar demonstrating it for 93.0 %, and modes (i)-(iii) together account for under 2 % of the slot-contract items and under 8 % of the exemplar items, leaving 92 to 100 % in the residual. **So: do not expand the sources.** Spend on retrieval and selection, and then measure the residual. That last clause is the honest limit of this read: the residual is modes (iv) delivered-but-ignored-or-misused and (v) locally-correct-but-later-overwritten taken together, and no sealed byte can separate them -- (iv) needs the counterfactual answer without the item and (v) needs the intermediate state re-run forward, so both need contacts. This read therefore proves where the constraint is NOT, proves that retrieval owns the intent half, and cannot tell us, for the entity half, whether the delivered knowledge was ignored, misused, or locally right and destroyed downstream.

## 9. Boundary

Zero model, server, tokenizer, encoder, embedder, scorer, network, GPU and paid-API contacts: no server was started or stopped, no waveform decoded, no embedding computed and no subprocess run. The tools used were the `data.slurp.load_slurp_split` loader for the governed TRAIN gold; `json` reads of the released store snapshots and their release files; `json` reads of the sealed `*.phases.json` and `flight-receipts.json` of three completed flights; a `json` read of the sealed bad-case bank and of the sealed official score file of the ROLL-1 as-flown pool; and `hashlib` for every identity hash quoted above. This read admits nothing, promotes nothing, preregisters no cell, releases no store, draws no roster, expands no source, opens no split and reaches no superiority, generalisation or Stage-3 conclusion. It is byte-reproducible across runs apart from its `generated_at` stamp: every container is sorted before it is consumed and the single resampling procedure is seeded at 20260926 with 10000 replicates.
