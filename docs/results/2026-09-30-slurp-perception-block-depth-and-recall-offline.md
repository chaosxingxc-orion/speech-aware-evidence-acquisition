# SLURP Perception boundary block: depth, off-block recall, note behaviour and the P-SV-1 Solver lead (DESCRIPTIVE, offline)

Date: 2026-09-30. Read id `SAEA-SLURP-PERCEPTION-BLOCK-DEPTH-RECALL-OFFLINE-V1`, recipe
`slurp-perception-block-depth-recall-offline-v1`. Written by Claude Opus 5.5 (analysis agent, coordinator's brief,
Fable 5.1) in worktree `fable/blockdepth` (base master `a73aa2bef`).

**Status: DESCRIPTIVE.** These are development numbers on TRAIN Fold A and TRAIN Fold B, both construction rosters
(owner decisions 28 and 86). No test, generalisation or superiority claim is made. The verdict word belongs to the
coordinator (decision 139).

**Contacts: zero of every kind.** No model, server, tokenizer, encoder, embedder, GPU, network or paid-API contact.
No official-scorer subprocess ran: per-row official scores were read from the sealed score files. `core.flight.cli`
and `lease_cli` were not invoked.

- **Gold.** Gold entered only offline, through the governed TRAIN loader `data.slurp.load_slurp_split`.
- **What is never printed or persisted.** Utterance text, transcripts, slot fillers, note text and model output.
- **What appears.** Ids, closed-set intent labels (Q2's per-intent counts only), counts, ranks, rates, AUCs, pp and
  hashes.

**Driver and outputs.**

- Driver: `scripts/analysis/slurp_perception_block_depth_recall.py`, sha256
  `5d577a79794a3676b1ae4e4ddece1c2e206cf325f1c2dba00ebe912bb2d9a6ae`.
- Unit test on fakes: `tests/unit/test_slurp_perception_block_depth_recall.py` (10 passed).
- Machine outputs: `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-PERCEPTION-BLOCK-DEPTH-RECALL-OFFLINE-V1/`. It holds
  `report.json`, `tables.md` and `content-sha256.json`. Every number below comes from `report.json`, and the key is
  named in brackets.
- `--check` re-derived both files IDENTICAL apart from `generated_at`. Content hashes (with `generated_at` removed):
  - `report.json` `5d956d3b0aedbdd697134db6793e0294ed479110be47cd6b6a68c2e233577dce`;
  - `tables.md` `c1b195466771d7848b8a8e6a614e583cfe9d06efe57ebd676cf6f88a62092072`.
- Wall time was 5.4 min per run, with a peak memory of 0.64 GB.

## 0. Pools and custody

| pool | fold | boundary key (rank weights w_cos / w_agree 1 / 1, k 60, fuse m / c / top_l 8 / 1 / 8) | sealed source of block, note and intent |
| --- | --- | --- | --- |
| AGREE `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` | A | description facets `76e8d16a...` + agreement `018ca6ef...` | `phases.json` `783299f1...`, `scores.json` `01db05fa...` (official intent 85.83) |
| COMP-1b `SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1` | A | centroid facets `16c33640...` + the same agreement | `phases.json` `079bcf18...`, `scores.json` `35f4ff5e...` (official intent 85.65) |
| P-SV-1 `a-agree` (delivering branch) | B | description facets + Fold B agreement `06990a86...` | seal-only `outputs.jsonl` `3d97b42b...` (branch records), column scores `a30309f3...` |
| P-SV-3 `a-agree` / `b-depth` / `t-twin` | B | as P-SV-1; `b-depth` overrides `m = top_l = 12` | `outputs.jsonl` `1f23a293...` (branch records) |

The retrieval was recomputed at depths 3, 4, 5, 6, 8 and 12 through the production constructor
`rails.phase_supply._provider_factory`, overriding only `fuse_coverage` `m = top_l = d`. The inputs were the pinned
facet vectors, segment query vectors and agreement table. [`checks`]

- **The recomputation reproduces every sealed block.**
  - The depth-8 block equals the sealed AGREE block on **1,080 / 1,080** rows and the sealed COMP-1b block on
    1,080 / 1,080.
  - It equals P-SV-1's and P-SV-3's `a-agree` supply on 1,080 / 1,080 rows each.
  - The depth-12 block equals P-SV-3's sealed `b-depth` supply on **1,080 / 1,080** rows.
- **Every depth-d block is the prefix of the fused rank list** on 1,080 / 1,080 rows in every pool. "Fused rank"
  below is therefore the block position gold would take at any depth.
- **A few rows recall fewer than 12 facets:** 6 (AGREE), 2 (COMP-1b) and 7 (Fold B) rows are not full width at every
  depth.

The ledger's AGREE counts are reproduced exactly: 153 intent-wrong rows, gold off the Perception note on 83, **49** of
them with gold in the block and **34** outside it. [`q1_shorter_block.agree_fold_a.reproduction`] The same counts for
the other two pools:

| pool | intent-wrong | gold off the note | off the note, in the block ("targets") | off the note, off the block |
| --- | --- | --- | --- | --- |
| COMP-1b | 155 | 75 | 44 | 31 |
| P-SV-1 A | 178 | 88 | 34 | 54 |

## 1. Shorter block (retrieval side)

### 1.1 Gold in the block by depth, the retrieval ceiling on the targets, and the recall cost of truncation

Column definitions:

- **targets in block**: of today's in-block-not-in-note intent-wrong rows (49 / 44 / 34), how many still have gold in
  a depth-d block. This is the retrieval ceiling; what the note would do with them is not simulated.
- **lost vs 8**: rows whose gold leaves the block at depth d.
- **note had gold**: of those lost rows, the ones where today's note lists gold.
- **delivered correct**: of those lost rows, the ones where today's delivered intent is correct.

[`q1_shorter_block.<pool>.depth_table`]

| pool | d | gold in block | targets in block | lost vs 8 | lost: note had gold | lost: delivered correct | gained vs 8 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| AGREE (A) | 3 | 991 | 22 / 49 | 49 | 22 | 12 | 0 |
| | 4 | 1,014 | 30 / 49 | 26 | 7 | 4 | 0 |
| | 5 | 1,020 | 32 / 49 | 20 | 3 | 1 | 0 |
| | 6 | 1,028 | 38 / 49 | 12 | 1 | 1 | 0 |
| | **8 (flown)** | **1,040** | 49 / 49 | 0 | 0 | 0 | 0 |
| | 12 | 1,047 | 49 / 49 | 0 | 0 | 0 | 7 |
| COMP-1b (A) | 3 | 993 | 16 / 44 | 55 | 27 | 14 | 0 |
| | 4 | 1,012 | 24 / 44 | 36 | 16 | 6 | 0 |
| | 5 | 1,027 | 31 / 44 | 21 | 8 | 4 | 0 |
| | 6 | 1,037 | 37 / 44 | 11 | 4 | 2 | 0 |
| | **8 (flown)** | **1,048** | 44 / 44 | 0 | 0 | 0 | 0 |
| | 12 | 1,057 | 44 / 44 | 0 | 0 | 0 | 9 |
| P-SV-1 A (B) | 3 | 964 | 12 / 34 | 51 | 29 | 14 | 0 |
| | 4 | 985 | 19 / 34 | 30 | 15 | 6 | 0 |
| | 5 | 997 | 25 / 34 | 18 | 9 | 4 | 0 |
| | 6 | 1,005 | 30 / 34 | 10 | 6 | 4 | 0 |
| | **8 (flown)** | **1,015** | 34 / 34 | 0 | 0 | 0 | 0 |
| | 12 | 1,022 | 34 / 34 | 0 | 0 | 0 | 7 |

**Gold rank inside the depth-8 block** (rows at block rank 1 / 2 / 3 / 4 / 5 / 6 / 7 / 8; off block)
[`note_given_block_rank`]:

| pool | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | off |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AGREE | 831 | 120 | 40 | 23 | 6 | 8 | 7 | 5 | 40 |
| COMP-1b | 823 | 131 | 39 | 19 | 15 | 10 | 7 | 4 | 32 |
| P-SV-1 A | 800 | 124 | 40 | 21 | 12 | 8 | 4 | 6 | 65 |

**P(gold on the Perception note | gold at block rank r)** falls steeply with r. It is not flat.
[`note_given_block_rank`]

| pool | r 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | off block |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AGREE | 99.6 % | 91.7 % | 75.0 % | 65.2 % | 66.7 % (4/6) | 25.0 % (2/8) | 0 % (0/7) | 20.0 % (1/5) | 12.5 % (5/40) |
| COMP-1b | 99.8 % | 93.9 % | 82.1 % | 57.9 % | 53.3 % | 40.0 % | 42.9 % (3/7) | 25.0 % (1/4) | 3.1 % (1/32) |
| P-SV-1 A | 99.8 % | 97.6 % | 82.5 % | 66.7 % | 50.0 % | 37.5 % (3/8) | 50.0 % (2/4) | 66.7 % (4/6) | 16.9 % (11/65) |

The truncation arithmetic, read off the two tables:

- **d = 6 cut on Fold B.** It keeps 30 of the 34 targets. It removes gold from the block on 10 rows, 6 of which the
  note lists today and 4 of which are delivered correct.
- **d = 6 cut on AGREE.** It keeps 38 of 49 and removes gold on 12 rows, of which the note lists 1.
- **d = 5 and below.** The cost grows quickly: 3 / 8 / 9 note-listed rows at d = 5, and 22 / 27 / 29 at d = 3.

### 1.2 Score profile: does a score or margin cut separate gold from non-gold at a block position?

For each block position p = 2..12, the AUC compares the gold item with the non-gold items at the same position, on
two features. A value below 0.5 means the gold item has the SMALLER feature.

- **gap to top**: s1 − sp;
- **drop from previous**: s(p−1) − sp.

[`score_profile_by_position`, `score_profile_pooled_auc_positions_2_12`, `row_margin_auc_gold_deeper_than_3`]

| pool | AUC gap to top, positions 2-8 | AUC drop from previous, positions 3-8 | pooled over positions 2-12: gap / drop / raw score | row top-1 − top-2 margin, gold deeper than rank 3 |
| --- | --- | --- | --- | --- |
| AGREE | 0.21, 0.17, 0.19, 0.19, 0.11, 0.17, 0.22 | 0.41, 0.51, 0.54, 0.65, 0.48, 0.68 | 0.13 / 0.78 / 0.84 | 0.196 |
| COMP-1b | 0.21, 0.21, 0.22, 0.20, 0.16, 0.26, 0.06 | 0.47, 0.54, 0.67, 0.61, 0.71, 0.52 | 0.14 / 0.80 / 0.85 | 0.196 |
| P-SV-1 A | 0.21, 0.18, 0.26, 0.22, 0.15, 0.11, 0.17 | 0.49, 0.50, 0.49, 0.65, 0.80, 0.48 | 0.15 / 0.79 / 0.83 | 0.230 |

- **The gap to the top score separates.** At a given position, gold sits closer to the top score than a non-gold item
  (inverted AUC about 0.8 at every position).
- **The successive drop does not separate.** Its AUC is 0.4-0.7 with no consistent sign, so a "deliver until the
  margin drops" (cliff) rule has nothing to cut on.
- **A small top-1 − top-2 margin marks rows whose gold sits deeper than rank 3** (inverted AUC 0.80 / 0.80 / 0.77).
  This matches the supply-abstention read's boundary AUC.

**Variable-depth rules, cross-fitted by sha256(utterance id) halves** (541 / 539 rows on Fold A, 533 / 547 on
Fold B). There are two rules:

- **gap**: keep items with s1 − sp ≤ δ, 1 ≤ depth ≤ 12;
- **cliff**: stop after the first drop ≥ δ.

δ is chosen on one half and applied to the other. Two criteria are used:

- **parity**: the smallest mean depth whose in-half recall is at least fixed-8's;
- **budget**: the best in-half recall at a mean depth of at most 5 or 6.

[`crossfit_gap`, `crossfit_cliff`, `crossfit_gap_budget`]

| pool | gap, parity with d 8: mean depth / gold in block (fixed 8) | gap, budget 6: mean depth / gold in block (fixed 6) | gap, budget 5: mean depth / gold in block (fixed 5) | cliff, parity |
| --- | --- | --- | --- | --- |
| AGREE | 7.50 / 1,041 (1,040) | 5.67 / 1,030 (1,028) | 4.56 / 1,020 (1,020) | no δ in the grid reaches parity |
| COMP-1b | 7.53 / 1,048 (1,048) | 5.36 / 1,027 (1,037) | 4.60 / 1,023 (1,027) | none |
| P-SV-1 A | 8.67 / 1,019 (1,015) | 5.63 / 1,003 (1,005) | 4.58 / 983 (997) | none |

**A variable block does not beat a fixed block of the same mean depth out of sample.** Summed over the three pools
at budget 6 it nets −10 rows, and at budget 5 −18 rows. At parity with depth 8 it saves at most 0.5 items per row on
Fold A and needs 0.67 more items on Fold B. The per-position separability is real, but it does not become recall,
because the rows that matter have gold deep in the list, where every item is far from the top.

## 2. Off-block recall

Gold's rank under five keys is given as buckets and as entry into the top 8 / 12 / 20. The five keys are:

- `desc_cos`: the description key, cosine only. This is the router's raw speech key before `rank_weights`.
- `desc_agree`: AGREE, flown in the P-SV cells.
- `cent_cos`: the centroid key, cosine only.
- `cent_agree`: COMP-1b.
- `vote`: the exemplar-intent agreement share alone. Intents with a zero share are unranked.

[`q2_off_block_recall.sets`]

| set (rows) | key | 1-8 | 9-12 | 13-20 | 21-60 | not recalled | top 8 / 12 / 20 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| A: AGREE intent-wrong, gold off the block (34) | desc_agree (flown) | 0 | 7 | 6 | 19 | 2 | 0 / 7 / 13 |
| | desc_cos | 2 | 2 | 6 | 22 | 2 | 2 / 4 / 10 |
| | cent_cos | 7 | 3 | 7 | 16 | 1 | 7 / 10 / 17 |
| | **cent_agree** | **8** | 8 | 8 | 9 | 1 | **8 / 16 / 24** |
| | vote | 7 | 1 | 1 | -- | 25 | 7 / 8 / 9 |
| B: P-SV-3 `a-agree` note absent, gold off the depth-8 block (54 of 90) | desc_agree (flown) | 0 | 7 | 13 | 30 | 4 | 0 / 7 / 20 |
| | desc_cos | 5 | 6 | 6 | 33 | 4 | 5 / 11 / 17 |
| | cent_cos | 12 | 5 | 16 | 21 | 0 | 12 / 17 / 33 |
| | **cent_agree** | **11** | 8 | 12 | 23 | 0 | **11 / 19 / 31** |
| | vote | 9 | 3 | 0 | -- | 42 | 9 / 12 / 12 |
| B: P-SV-3 `b-depth` note absent, gold off the depth-12 block (47 of 105) | desc_agree (flown) | 0 | 0 | 12 | 31 | 4 | 0 / 0 / 12 |
| | cent_agree | 8 | 5 | 11 | 23 | 0 | 8 / 13 / 24 |
| | vote | 6 | 3 | 0 | -- | 38 | 6 / 9 / 9 |

On Fold B the P-SV-3 absent rows split as follows. Of `a-agree`'s 90 absent rows, 36 have gold in the depth-8 block
and 54 off it. Of `b-depth`'s 105, 58 have gold in the depth-12 block and 47 off it. The other sets (the AGREE-wide
40, COMP-1b's own 31, P-SV-1 A's 56) are in `report.json`.

**Net rows at depth 8 over all 1,080 rows, against the flown `desc_agree` block** [`net_rows_at_depth_8`]:

| key | fold A: enters / leaves / net (enters intent-wrong; leaves delivered-correct; leaves with gold on the note) | fold B: same |
| --- | --- | --- |
| desc_cos | 2 / 95 / **−93** (2; 54; 76) | 5 / 113 / **−108** (5; 68; 90) |
| cent_cos | 11 / 36 / **−25** (7; 7; 18) | 20 / 35 / **−15** (13; 9; 18) |
| **cent_agree (COMP-1b key)** | 13 / 5 / **+8** (8; 0; 0) | 17 / 5 / **+12** (12; 0; 3) |
| vote | 11 / 22 / **−11** (7; 7; 9) | 11 / 16 / **−5** (8; 4; 13) |
| hybrid, not pinned: desc_agree top 6 + cent_agree next 2 | 10 / 5 / +5 (6; 0; 0) | 16 / 2 / +14 (11; 0; 1) |
| hybrid, not pinned: desc_agree top 6 + vote next 2 | 8 / 9 / −1 | 10 / 2 / +8 |

- **Only the centroid + agreement key is net positive on both folds.** It gains +8 rows on A and +12 on B, and no
  delivered-correct row loses gold. It is already the COMP-1b key.
- **No pinned key brings gold into the block on most of the 34.** The best is 8 of 34 into the top 8 and 16 of 34
  into the top 12 (`cent_agree`).
- **The flown key's off-block gold is deep.** 19 of 34 sit at 21-60, and widening to k = 20 reaches 13 of 34.
- **The raw speech key is far worse than the agreement-weighted keys.** It loses 93 and 108 rows. The agreement term
  carries the block.
- **The vote key reaches a few rows but is empty elsewhere.** It puts 7 of the 34 into the top 8, and gold has no
  vote at all on 25 of them.

**Dominant gold intents on the misses (top 10)** [`intent_counts`]:

- **A, 34 rows (17 distinct intents):** general_quirky 8, news_query 3, cooking_recipe 3, lists_query 3, qa_factoid 2,
  social_query 2, social_post 2, email_sendemail 2, weather_query 1, play_music 1.
- **B, 54 rows off the depth-8 block (25 distinct):** general_quirky 11, qa_factoid 5, audio_volume_mute 3,
  recommendation_movies 3, takeaway_order 2, news_query 2, music_settings 2, music_query 2, play_music 2,
  audio_volume_up 2.

The catch-all `general_quirky` is the largest single intent on both folds. After it the misses are diffuse.

## 3. Note behaviour vs depth (P-SV-3 sealed branch records, Fold B)

[`q3_note_vs_depth`]

| branch | block depth | note size 1 / 2 / 3 (mean) | gold in block | gold in block and on note | **P(note \| block)** | gold on note but off block |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `a-agree` | 8 | 63 / 266 / 751 (2.637) | 1,015 | 979 | **96.45 %** | 11 |
| `b-depth` | 12 | 94 / 241 / 745 (2.603) | 1,022 | 964 | **94.32 %** | 11 |
| `t-twin` | 8 | 46 / 265 / 769 (2.669) | 1,015 | 975 | **96.06 %** | 10 |

P(gold on note | gold at block rank r), A / B / T:

| r | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9-12 (B only) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rows (same in A, B, T for r ≤ 8) | 800 | 124 | 40 | 21 | 12 | 8 | 4 | 6 | 7 |
| A | 99.6 % | 96.8 % | 87.5 % | 66.7 % | 41.7 % | 25.0 % | 50.0 % | 66.7 % | -- |
| B | 99.0 % | 95.2 % | **77.5 %** | 61.9 % | 41.7 % | 12.5 % | 50.0 % | 33.3 % | 0 / 7 |
| T | 99.6 % | 96.8 % | 85.0 % | 61.9 % | 41.7 % | 25.0 % | 50.0 % | 33.3 % | -- |

**Where B dropped gold that A kept.** On 19 rows A kept gold on the note and B dropped it. The twin T dropped it on 7
rows. In the other direction, B kept what A dropped on 4 rows and T on 2. The net is −15 for B against −5 for the
twin, so about −10 rows are attributable to depth. The 19 dropped rows break down as follows:

- **B-block rank of gold:** 1: 5, 2: 4, 3: 4, 4: 1, 5: 1, 6: 1, 8: 2, off: 1. On 13 of the 19, gold was in B's top 3.
- **A-note rank of gold:** 1: 5, 2: 6, 3: 8.
- **B-note size:** 3 on 13 rows.

**Which block ranks the note draws its candidates from:**

| branch | block ranks 1-3 | block ranks 4-8 | block ranks 9-12 | off the block |
| --- | ---: | ---: | ---: | ---: |
| A | 2,478 | 342 | -- | 28 |
| B | 2,407 | 329 | 45 | 30 |

- **The 45 deep candidates in B's notes include gold on 0 of the 7 rows whose gold sits at ranks 9-12.**
- **The note's rank-1 candidate is block rank 1** on 905 (A), 894 (B) and 908 (T) rows.

What this shows:

- **P(in note | in block) is not flat in block rank.** It is about 97-100 % at ranks 1-2, 78-88 % at rank 3 and
  12-67 % at ranks 4-8 (small n).
- **The model does not keep "only the top few regardless of depth".** Under depth 12 it spends 45 note slots on
  ranks 9-12. Those slots displace gold that sat at ranks 1-3 on 13 rows and recover gold on none.
- **The depth effect is displacement, not missed recall.**
- **A shorter block would remove recall at ranks 7-8.** On Fold B the note lists 6 of 10 such rows. Its only
  possible gain is to reverse the displacement, and nothing here measures that.

## 4. Solver-side contrast (P-SV-1 level-2 columns, Fold B)

**What the `b-top2contrast` Solver received.**

- **Code path.** `rails/runner.py` `perception_branch_solver_messages` renders a non-A branch's Solver contact over
  `_perception_note_view`. That view swaps the sealed Perception state's content for the branch's own note text and
  leaves every other state untouched.
- **Where the contrast block goes.** The block (`_render_perception_branch_presentation`) is appended only to the
  branch's PERCEPTION request.
- **Sealed receipts.** [`what_b_solver_received`]
  - The contrast block was rendered in B's Perception request on 1,035 of 1,080 rows.
  - The Solver's candidate-supply value ids are identical between A and B on **1,080 / 1,080** rows, in both order and
    set.
  - The Solver requests differ on 1,080 / 1,080 rows, because the note text differs.
  - The note candidate lists are identical on 406 rows.
- **Conclusion on what was delivered.** B's Solver never saw the contrast block. It saw only B's note.

**The 41.5 % vs 19.5 % conversions as paired rows** [`conversion_by_own_note_rank`, `paired_*`,
`both_notes_gold_rank2*`, `solver_pick_on_own_rank2_rows`]:

| rows | n | A Solver correct | B Solver correct | paired B − A (rows) |
| --- | ---: | ---: | ---: | ---: |
| gold at rank 2 of **A's** note | 77 | 15 (19.48 %) | 14 | −1 (rate CI95 [−6.49, +2.60] pp) |
| gold at rank 2 of **B's** note | 82 | **34** | 34 (41.46 %) | **0** (CI95 [−3.66, +3.66] pp) |
| of B's 82: gold at rank 1 of A's note | 27 | 24 | 24 | 0 |
| of B's 82: gold at rank 2 of both notes | 50 | 9 | 9 | 0 (1 B-only, 1 A-only) |
| of those 50: the same top-2 pair in both notes | 48 | 8 | 8 | 0 |
| of those 50: identical note lists | 26 | 5 | 6 | +1 |
| of B's 82: gold at rank 3 / absent in A's note | 3 / 2 | 1 / 0 | 1 / 0 | 0 |
| twin check: gold at rank 2 of both A and T notes | 72 | 14 | 13 (T) | −1 |

Solver pick on each branch's own rank-2 rows:

| branch | gold | note rank 1 (not gold) | other | unparsed |
| --- | ---: | ---: | ---: | ---: |
| A | 15 | 60 | 1 | 1 |
| B | 34 | 47 | 1 | 0 |

The parsed pick agrees with the official intent flag on 1,080 / 1,080 rows per branch.

**The doubled rank-2 conversion is a composition artefact of B's note, not a Solver-visible effect.**

- B's rank-2 pool contains 27 rows where A's note had gold at rank 1. The Solver answers those correctly under both
  notes (24 / 24).
- On the rows where both notes put gold at rank 2, the two Solvers convert identically: 9 vs 9 of 50.
- On B's own 82 rank-2 rows, A's Solver is right exactly as often as B's (34 vs 34).
- The contrast block never reached the Solver, and the Solver-side supply was byte-identical.
- There is therefore no measured Solver-node effect for a Solver contrast column to build on.

## What this note does not claim

- It does not predict what the Perception note would contain under a block of depth 3-6. Only the retrieval ceiling
  and the recall cost are measured. P(note | block) at a shorter depth is not observed anywhere.
- It does not claim that the centroid + agreement key raises intent accuracy. It raises gold-in-block by +8 / +12
  rows. The intent effect of those rows depends on note and Solver conversions that are only analogues here.
- It does not claim that a Solver-request contrast block (the block placed in the Solver's own request) would fail.
  It shows only that P-SV-1 carries no evidence for one, because its Solver never received the block.
- The variable-depth grids are fixed quantile grids of the pooled feature. The cross-fit is the guard; in-sample
  sweeps are in `report.json` and are selected numbers.
- The hybrids in section 2 are not pinned keys and were added after the per-key table. They are descriptive.
- Rows at block ranks 5-12 are few (4-12 per rank), so those per-rank rates carry wide uncertainty.
- Every number is a TRAIN development number. Nothing here is a test, system-level or generalisation claim, and
  nothing is nominated or admitted.

## Recommendation to the coordinator

1. **Strike lever (iii), the Solver-side contrast column motivated by P-SV-1's 41.5 % vs 19.5 %.**
   - Paired on the same rows, the effect is 0: 34 vs 34 on B's rank-2 rows, and 9 vs 9 where both notes put gold at
     rank 2.
   - B's Solver never received the contrast block, and its supply was identical on 1,080 / 1,080 rows.
   - Predicted effect of a Solver-node column at the measured conversions: 0 rows. Any design would have to put the
     block into the Solver's own request, and no measurement supports a nonzero prior.
   - Decision needed: amend the P-SV-3 coordinator verdict's remaining-lever list to drop (iii). Record the 41.5 % as
     a composition artefact in the P-SV-1 verdict.
2. **Keep the centroid + agreement key (COMP-1b's) as the module's boundary key, and close off-block recall as an
   intent lever for pinned keys.**
   - It is the only pinned key that is net positive on both folds: +8 (A) and +12 (B) rows in the depth-8 block, with
     0 delivered-correct rows losing gold.
   - No pinned key reaches most of the off-block rows: 8 of 34 into the top 8 and 16 of 34 into the top 12. 19 of the
     34 sit at ranks 21-60, and general_quirky leads the misses.
   - Predicted intent effect of the key at measured conversions: the 12 intent-wrong entrants on Fold B, times
     P(note | block rank 4-8) of about 0.4-0.5, times the ledger's rank-2/3 Solver conversion of 12-27 %, gives about
     1 row (0.1 pp). That is under every intent floor, so no dedicated flight is warranted.
   - Decision needed: confirm that the P-SV / module Perception list uses `cent_agree`. The P-SV cells flew the
     description key. Declare that further intent-recall work requires a new, unpinned key (a separate brief).
3. **Do not dedicate a flight to a shorter block.**
   - Fixed d = 6 removes gold from the block on 10 Fold B rows, 6 of which the note lists today, and keeps 30 of 34
     targets. Variable depth does not beat fixed depth out of sample: −10 rows over the three pools at a mean depth of
     at most 6.
   - The only upside is reversing P-SV-3's displacement (about 10 rows net of the twin). If that reversal were
     symmetric, d = 6 would predict about +4 presence rows (+0.4 pp), under the twin present bar of about 1.0 pp.
     With about 0.2 conversion to intent that is about 1 row. P-SV-3's level-2 already absorbed −15 presence rows at
     0.00 intent.
   - Decision needed: close the boundary-depth line in both directions. Alternatively, allow a d = 6 branch only as a
     zero-marginal-cost extra branch on a Fold B Perception-branch flight that is already scheduled, read on presence
     only.

## Method and reproduce

- **Files read.** Full hashes are in `report.json` `inputs`: the sealed phases, scores and outputs listed in section
  0, the P-SV-1 first-visit outputs and column scores (A, B, T), the P-SV-3 column scores, the boundary snapshot
  `5520b844...`, both facet files, both query-vector files, both agreement tables, and the four baseline configs (repo
  paths).
- **Solver picks.** Parsed in memory with `reproduction.slurp_scoring.parse_slu_response`. Only the pick class is
  kept.
- **Branch note lists.** Read through `slurp_perception_branch_read.branch_candidates`, which applies the collapse and
  the empty/malformed rule.
- **Delivered correctness.** The official `scenario_action_exact` per row.
- **Paired intervals.** A row bootstrap of the paired difference, 10,000 draws, seed 20260929.
- **`--cache`.** A development-only flag that pickles the recomputed rank lists (ids and scores). The committed
  outputs were produced and checked without it.

```bash
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 python scripts/analysis/slurp_perception_block_depth_recall.py \
    --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 python scripts/analysis/slurp_perception_block_depth_recall.py --check \
    --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
```
