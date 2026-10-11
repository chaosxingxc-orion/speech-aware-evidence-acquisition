# Decision 265 coverage pre-read on TRAIN Fold B (offline): no iteration-1 knowledge-augmentation candidate reaches +1.5 pp predicted SLU-F1; the largest honest number is about +0.27 pp, and it does not come from the credit table

Read 2026-10-11 by Claude Opus 5.5 (analysis agent, on the coordinator's brief, Fable 5.1) in worktree
`opus/265-coverage-preread` (base master `b4a53fd31`). Read id `SAEA-SLURP-TFRL-COVERAGE-PREREAD-V1`, recipe
`slurp-tfrl-coverage-preread-fold-b-offline-v1`, driver `scripts/analysis/slurp_tfrl_coverage_preread.py`. Machine
outputs: `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-TFRL-COVERAGE-PREREAD-V1/` (`report.json`, `tables.md`,
`content-sha256.json`; content sha256 with `generated_at` stripped: report `15ae9d26...`, tables `7c14fb44...`).
This note answers the 0-GPU pre-read that section 2.1 of
`docs/superpowers/specs/2026-10-11-slurp-autonomous-typed-loop-with-ace-comparator-design.md` requires before the
iteration-1 column of decision 263 / 265 can be registered.

**Status: DESCRIPTIVE.** These are development numbers on a TRAIN construction fold (owner decisions 28 and 86). Fold B
is the selection fold, and every operator number below is cross-fitted inside it. Nothing here registers a cell,
admits a mechanism, releases a store or authorises a flight. Decision 265 is the owner's.

**Contacts: zero.** There were no model, server, tokenizer, encoder, embedder, Whisper, scorer-subprocess, GPU,
network or paid-API contacts, so no exposure-ledger row was needed. Every cosine is arithmetic over pinned,
sha256-verified vector files. The facet-vector file already covers all 11,514 TRAIN utterances, so the offline
re-retrieval needed no encoding. Transcripts come from the existing E5-0 catalog, which is re-hashed against its
receipt. `core.flight.cli`, lease tooling, re-pin scripts, holds, `batch-STOP`, scheduled tasks and the resident
server were not touched. Run time is 6 to 9 min on CPU, with a peak of 0.96 GB.

**Gold and text discipline.** Gold enters offline and only on the scoring side, through the governed TRAIN loader
(`data.slurp.load_slurp_split`). It is used in two places: Fold B rows, and the construction statistics of TRAIN
outside the folds. The devel and test splits are not read. Fold B bad cases choose only which cells and strata are
edited, and only as aggregate counts. Content comes from TRAIN minus Fold A, Fold B, R01 and R01C. No utterance
text, transcript, gold value, filler, card body or model output is printed or persisted. Only ids, slot TYPE names,
scenario and intent names, counts, rates, pp and hashes appear.

## 0. Answer

**Verdict.** Iteration 1 has **no** candidate over decision 192's +1.5 pp predicted SLU-F1 bar.

- The credit-driven composite (a)+(b)+(c), with every threshold and selection cross-fitted on Fold B, predicts
  **-1.00 pp SLU-F1**. Its parts are (a) 0.00, (b) -0.56 (print losses) and (c) -0.45 [-1.13, +0.18]. It predicts
  **+0.07 pp intent**, with a range of [+0.02, +0.12] at the CONV conversion interval.
- Counting only the operators whose own cross-fitted SLU point is positive gives **0.00 pp**.
- The largest honest SLU number is **+0.27 pp**, at 45 % conversion (+0.18 / +0.36 at 30 / 60 %, and +0.03 at the
  measured W4 list rate). It comes from the non-credit reference "every slot card carries its 16 most frequent TRAIN
  values", which costs +651 tokens per row and puts 14,044 lists on rows whose gold lacks that type. That harm is not
  netted.

The three operator numbers (cross-fitted, Fold B, lock v2.2 column):

| operator | what moves | predicted SLU-F1 pp | predicted intent pp |
| --- | --- | ---: | ---: |
| (a) slot-card value-list supply, credit-selected cells | 0 MISSING items newly supplied (0 cells survive the half split) | **0.00** (oracle on all 18 reachable in-store items: +0.54 at 45 %) | 0 |
| (b) exemplar re-weighting by pool selection (expansion material = 0) | gold boundary newly delivered on 5 rows, lost on 2 correct rows; 2 MISSING newly printed, 36 exact items lose their print | **-0.56** (symmetric M1 print rate; +0.03 on the gain side alone) | **+0.07** [+0.02, +0.12] |
| (c) per-scenario anti-pattern guards over the v4g column | 22 SPURIOUS removed, 17 exact and 4 partial entities dropped, on 42 rows | **-0.45 [-1.13, +0.18]** (measured exactly; paired bootstrap) | 0 |

**What blocks the rest.** Four facts on this column, each measured below.

1. **Supply is not the gap for most MISSING items.** 139 of the 228 MISSING items (61 %) already have their value in
   the row's delivered supply. That is a consumption failure, not a construction gap.
2. **Many gold values do not exist in TRAIN outside the folds.** That holds for 49 MISSING items and for 155 of all
   434 gold-side error items (36 %). No TRAIN augmentation can supply them.
3. **Too few items are reachable to select stably.** Only 18 MISSING items are in a store, not delivered, and
   contained in the transcript. They are spread over 14 slot types, so no credit cell holds on both halves.
4. **Intent is not a retrieval gap on this column.** The gold boundary is already delivered on 142 of the 190
   intent-wrong rows. The 48 rows it misses rank deep (median 21). Expansion material is zero, because TRAIN equals
   the lock pool plus the two folds.

## 1. Source column and identities

| item | value |
| --- | --- |
| column | the delivering `lock` column of R6-P1: run `SAEA-SLURP-STAGE3-NX-R6-PERCEPTION-FOLD-B-V1`, attempt `attempt-slurp-native-stage3-nx-r6-perception-fold-b-generation-v1`, flight commit `1f04ce42d`; review-off COMP-1b module graph on lock v2.2 (v4g delivery); the run-level delivered answer is the lock's (I7) |
| why this column | the most recent sealed lock-v2.2-class Fold B column with its delivered outputs, its per-row official scores and its `phases.json` all on disk. VER-1a's greedy S0 has no per-row official score file (its in-flight commit column is the plurality answer). The R1 lock is v2.1 / v3 |
| roster | `SLURP-EVO-FOLD-B-V2`, 1,080 rows (392 empty-gold), split identity `4407794c...`; halves by sha256(utterance id) parity: 527 / 553 rows |
| levels (official = in-process) | SLU-F1 **64.3391**, intent 82.4074, span-F1 55.2546; pooled TP / FP / FN 1,318.0 / 688.52 / 772.52 |
| exchange rates on this column | +1 recovered MISSING **+0.0662 pp**; -1 exact item **-0.0663 pp**; +1 intent row 0.0926 pp (the Fold A analytic rate on file is 0.062) |
| sealed files (sha256) | outputs `4a43685e...`, scores `a13453e4...`, phases `30c2a201...` |
| knowledge pins | exemplar pool `size-pool-annotated-exemplars` (content `4c498dc0...`); legal construction population `...-minus-r01` (content `6eaa03ae...`, 8,554 utterances = TRAIN minus Fold A, Fold B, R01, R01C); slot contracts `slot-contracts-v2` (file `a48ed83e...`); intent-boundaries (file `4579079c...`) |
| vectors | exemplar facets `vectors/slurp-kus3/facet-vectors.jsonl` (`5dfe7523...`); exemplar query `vectors/slurp-stage3-filler-fold-b-v1/query-vectors-speech-content-v1.jsonl` (`573a8a37...`); boundary query segments (`83c5da61...`); centroid keys (`16c33640...`); sealed agreement table `prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-B-V1/agreement.jsonl` (`06990a86...`) |
| transcripts | E5-0 catalog `prepared/SAEA-SLURP-ASR-TRANSCRIPTS-V1/fold-b/catalog.json` (`31462f9b...`); "reachable" = the canonical gold span is contiguous in the row's transcript (the S2a.1 / E5 test) |
| reused code | `slurp_nx_postproc_v4_search` (scoring matrix, `TrainStats`, `Bootstrap`, loaders), the node ledger chain (`GP.load_phases`, `W5.printed_pairs`, `RD.recompute` / `RD.blend`), `e5_transcript_consistency_read` (`load_catalog`, `contiguous`, `canon_tokens`), `analysis.sealed_credit.entity_states.entity_items` |

**Reproduction controls.** If any of these fails, the read stops. Every one held.

- In-process scoring reproduces every sealed per-sample official field on 1,080 / 1,080 rows, and the pooled
  official aggregate.
- The exemplar top-20, recomputed from the pinned vectors (pure cosine, facet-id tie-break), equals the sealed ranked
  order on **1,080 / 1,080** rows.
- The self-excluded exemplar-intent vote equals the sealed agreement table on **1,080 / 1,080** rows. No Fold B
  utterance is in the pool, so 0 values were self-excluded.
- The COMP-1b Perception block (centroid cosine + 1.0 x vote share, top 8) equals the sealed block **in order** on
  **1,080 / 1,080** rows.
- The legal construction population is disjoint from Fold B. The lock pool intersects neither fold.

## 2. Bad-case inventory (item 1)

Modes: **(a)** in the row's delivered supply; **(b)** in a released store but not delivered to this row; **(c)** in
TRAIN outside the folds but in no store; **(d)** nowhere.

For a slot value, (a) means the row's 20 exemplars print the (type, value) (E1), print the value under another type
(E2), or a delivered card names it (E3). (b) means some pool exemplar prints the (type, value), or some card names
it. For intent, (a) means the gold intent's boundary entry is in the delivered block of 8.

Mapping to the coverage note's five modes: (ii) not retrieved = (b), and (iv)+(v) residual = (a). Mode (iii)
budget-excluded is 0 by construction (k == top_l == m; the card cap is never reached). Value-level (c)+(d) is finer
than the note's store-level mode (i): a store entry for the TYPE exists for every type here, but the VALUE may not.

Row classes: CORRECT 504, ENTITY-MIXED 176, INTENT-WRONG 190, ENTITY-FN-ONLY 122, EMPTY-GOLD-FILL 67, ENTITY-FP-ONLY
21. SPURIOUS items number 186. Empty-gold rows number 392, of which 67 are false-filled.

### 2.1 Gold-side error items by class and mode

| class | items | (a) | (b) | (c) | (d) | transcript-reachable | reachable (a) / (b) / (c) / (d) | on intent-wrong rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| MISSING | 228 | 139 | 40 | 0 | 49 | 161 | 118 / 18 / 0 / 25 | 49 |
| WRONG-TYPE | 57 | 23 | 5 | 0 | 29 | 45 | 20 / 3 / 0 / 22 | 20 |
| BOUNDARY | 53 | 21 | 7 | 0 | 25 | 33 | 13 / 4 / 0 / 16 | 4 |
| NEAR | 52 | 14 | 7 | 0 | 31 | 17 | 6 / 2 / 0 / 9 | 6 |
| WRONG-VALUE | 34 | 10 | 8 | 0 | 16 | 10 | 5 / 1 / 0 / 4 | 5 |
| FORMAT | 10 | 4 | 1 | 0 | 5 | 2 | 1 / 1 / 0 / 0 | 0 |
| **all gold-side** | **434** | **211** | **68** | **0** | **155** | **268** | 163 / 29 / 0 / 76 | 84 |

The (a) MISSING items split into E1 121, E2 1 and E3 17. The (b) MISSING items split into a legal-pool exemplar 35,
an R01-only exemplar 1, and a card only 4.

**(c) is zero by construction.** The lock pool already holds every utterance of TRAIN outside the two folds, so
anything TRAIN outside the folds knows is in a store. The construction route therefore has two pools of material.

- (b): 68 items, of which **29 are reachable**, and 18 of those 29 are MISSING.
- (d): 155 values that TRAIN outside the folds never shows. Augmenting from TRAIN cannot supply them.

### 2.2 By scenario

| scenario | rows | intent wrong | of which gold boundary in block | gold-side items | (a) | (b) | (d) | MISSING | SPURIOUS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 60 | 7 | 7 | 12 | 4 | 5 | 3 | 4 | 12 |
| audio | 60 | 17 | 10 | 11 | 2 | 4 | 5 | 5 | 6 |
| calendar | 60 | 10 | 8 | 48 | 31 | 8 | 9 | 24 | 12 |
| cooking | 60 | 5 | 2 | 21 | 3 | 1 | 17 | 5 | 12 |
| datetime | 60 | 3 | 3 | 18 | 11 | 3 | 4 | 8 | 2 |
| email | 60 | 5 | 4 | 14 | 5 | 3 | 6 | 4 | 8 |
| general | 60 | 39 | 31 | 12 | 7 | 3 | 2 | 9 | 16 |
| iot | 60 | 12 | 11 | 19 | 6 | 4 | 9 | 8 | 7 |
| lists | 60 | 10 | 7 | 16 | 6 | 3 | 7 | 10 | 7 |
| music | 60 | 13 | 8 | 9 | 3 | 0 | 6 | 7 | 10 |
| news | 60 | 6 | 4 | 28 | 12 | 4 | 12 | 16 | 7 |
| play | 60 | 15 | 10 | 29 | 10 | 3 | 16 | 17 | 15 |
| qa | 60 | 11 | 7 | 16 | 7 | 3 | 6 | 4 | 12 |
| recommendation | 60 | 8 | 4 | 24 | 10 | 5 | 9 | 12 | 7 |
| social | 60 | 7 | 6 | 29 | 13 | 6 | 10 | 12 | 20 |
| takeaway | 60 | 8 | 6 | 56 | 37 | 6 | 13 | 36 | 13 |
| transport | 60 | 13 | 13 | 36 | 17 | 4 | 15 | 20 | 14 |
| weather | 60 | 1 | 1 | 36 | 27 | 3 | 6 | 27 | 6 |

### 2.3 By slot type (top 12 by gold-side items; the full table is in `tables.md`)

| type | items | (a) | (b) | (d) | MISSING | MISSING (a) / (b) / (d) | MISSING (b), reachable | SPURIOUS |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| date | 61 | 51 | 6 | 4 | 48 | 46 / 2 / 0 | 0 | 11 |
| place_name | 45 | 14 | 12 | 19 | 11 | 3 / 6 / 2 | 2 | 18 |
| business_name | 28 | 10 | 4 | 14 | 4 | 1 / 0 / 3 | 0 | 12 |
| time | 28 | 7 | 10 | 11 | 10 | 1 / 5 / 4 | 3 | 8 |
| media_type | 24 | 15 | 3 | 6 | 18 | 12 / 3 / 3 | 1 | 7 |
| event_name | 22 | 11 | 1 | 10 | 12 | 8 / 1 / 3 | 0 | 11 |
| food_type | 22 | 8 | 2 | 12 | 7 | 5 / 1 / 1 | 1 | 13 |
| order_type | 22 | 17 | 2 | 3 | 21 | 16 / 2 / 3 | 2 | 5 |
| person | 18 | 2 | 6 | 10 | 6 | 1 / 4 / 1 | 1 | 8 |
| business_type | 14 | 12 | 2 | 0 | 10 | 9 / 1 / 0 | 1 | 5 |
| transport_type | 14 | 12 | 1 | 1 | 14 | 12 / 1 / 1 | 1 | 4 |
| weather_descriptor | 14 | 10 | 1 | 3 | 12 | 9 / 1 / 2 | 0 | 4 |

The two largest MISSING types are `date` (48) and `order_type` (21). In both, the value is already printed in the
row's own exemplars on 46 of 48 and 16 of 21 rows. The 18 reachable (b) MISSING items are spread over 14 types, and
no type holds more than 3.

### 2.4 Intent

| quantity | value |
| --- | ---: |
| intent-wrong rows | 190 |
| (a) gold boundary in the delivered block of 8 | **142 (74.7 %)** |
| (b) in the store, not in the block | **48** |
| (c) / (d) | 0 (all 60 intents have an entry) |
| gold-intent exemplar among the row's 20 exemplars (intent-wrong rows) | 133 |
| gold rank in the full COMP-1b ordering on the 48 off-block rows | median **21**; 9-16: 13, 17-30: 20, 31-60: 15, unrankable: 0 |
| off-block rows by gold intent (top) | `general_quirky` 8, `qa_factoid` 4; `audio_volume_mute`, `music_settings`, `audio_volume_up`, `cooking_recipe`, `recommendation_movies` 3 each |
| P(intent correct given gold in block) / (given off block) | 86.17 % / 9.43 % |

The 2026-09-26 rank diagnostic found the gold boundary missing on 55 % of intent-wrong rows. That was on the pre-AGREE
graph. On the lock v2.2 column it is missing on 25 %. The agreement vote (COMP-1b) already did the retrieval job. The
remaining intent error sits inside the block, in the Perception note's choice. It is not a coverage gap.

## 3. Operator (a): slot-card value-list supply (item 2)

**Rule (stated before reading the apply half).**

- **Cell selection.** On the fit half, a cell is selected when it holds at least 2 reachable (b)+(c) MISSING items.
  A cell is (gold scenario x slot type), or (slot type) alone in the coarser form.
- **The list.** The cell's top-N values by utterance count, from TRAIN minus Fold A, Fold B, R01 and R01C. The
  primary N is 16, matching the card value cap.
- **The trigger.** On the apply half the list is appended to the card of that type, on rows where the card is
  delivered and the Perception note names an intent of that scenario. The scenario condition drops out in the type
  form. The trigger is gold-free.
- **Supplied.** An item counts as supplied when the gold value is in the list.
- **Read.** Fit on one half and apply to the other, both ways.

**Cost.** Tokens are the list's characters / 3.634 (the measured M1 exemplar-block ratio) plus 8 tokens of label per
list. They are an ESTIMATE, not a tokenizer count. The budget is the realised Solver prompt (server usage fields):
median 11,590 and max 14,688 tokens against slot 24,576 minus completion 512. The minimum headroom is **9,376 tokens**
per row.

| variant | cells (fit h0 / h1) | newly supplied reachable MISSING | rows triggered | extra tokens per triggered row | lists on rows whose gold lacks the type (empty-gold rows) | pp @30 / 45 / 60 % | pp @W4 0.052 |
| --- | --- | ---: | ---: | ---: | --- | --- | ---: |
| scenario x type, N 8 / 16 / 32, cross-fitted | 0 / 0 | **0** | 0 | 0 | 0 | 0.00 | 0.00 |
| type, N 16, cross-fitted | 1 (`time`) / 0 | **0** | 518 | 48 | 486 (177) | 0.00 | 0.00 |
| scenario x type, N 16, in-sample reference | 1 | 1 | 101 | about 32 | 77 | 0.02 / 0.03 / 0.04 | 0.00 |
| type, N 16, in-sample reference | 3 | 3 | 1,020 | about 91 | 1,803 | 0.06 / 0.09 / 0.12 | 0.01 |
| every card, N 8 (no credit) | -- | 5 | 1,080 | 399 (max 775) | 14,044 (5,377) | 0.10 / 0.15 / 0.20 | 0.02 |
| **every card, N 16 (no credit)** | -- | **9** | 1,080 | **651 (max 1,258)** | 14,044 (5,377) | **0.18 / 0.27 / 0.36** | 0.03 |
| every card, N 32 (no credit) | -- | 11 | 1,080 | 1,141 (max 2,152) | 14,044 (5,377) | 0.22 / 0.33 / 0.44 | 0.04 |

**The ceiling.** 40 MISSING items are (b)+(c). 18 of them are reachable. Of those 18, 17 have their type's card
delivered, and 10 are in their (scenario, type) cell's legal value list at any N. Supplying all 18 and converting
45 % gives **+0.54 pp**.

**The sensitivity.** The credit-driven rule supplies nothing after cross-fitting: no cell holds on both halves.
Selecting from the Fold B credit table is noise at this mass. Dropping the credit and supplying every card buys at
most +0.27 pp at 45 %. The measured analogue of the list form (W4: 5 of 97 listed items moved) gives +0.03.

**The harm.** It is not netted. Over-emission of listed values (W4 K3: 4 -> 7) acts on 14,044 lists on rows whose
gold lacks the type.

The spec's "+1.1 pp from the 40 E4 items" was a Fold A AGREE figure. It counted items whose values are in TRAIN's
list without testing transcript reachability, cell stability or the trigger. Here the Fold B count replaces it:
**0.00 credit-driven, +0.27 as the uncredited reference.**

## 4. Operator (b): exemplar re-weighting / targeted expansion (item 3)

**Expansion material is zero.**

| quantity | utterances |
| --- | ---: |
| TRAIN | 11,514 |
| lock pool | 9,354 |
| Fold A + Fold B | 1,080 + 1,080 |
| pool overlap with either fold | 0 |
| TRAIN minus pool minus both folds | **0** |
| legal population (TRAIN minus A, B, R01, R01C), all already in the pool | 8,554 |

The lock pool is TRAIN minus the two evaluation folds, so "adding TRAIN rows outside the folds that the size-pool
omitted" has nothing to add. Targeted expansion could only come from outside the governed TRAIN split. One example is
SLURP `train_synthetic`, which needs an ENCODE preparation with an exposure-ledger row (an embedder contact). That
contact was **not made**.

**Re-weighting is therefore pool SELECTION.** Each variant changes pool membership only. The variants are:

- a keep-quota per intent, Q in {60, 120, 240};
- thinning of "attractor" intents to a fraction f in {0.75, 0.5, 0.25}. Attractors are the delivered wrong intents
  with at least c in {2, 3, 5} intent-wrong rows on the fit half.

Membership is kept by sha256(value id) order. k stays 20, and the block stays 8. For each variant the script
recomputes, exactly:

- the exemplar top-20;
- the vote;
- the Perception block;
- the printed pairs.

Prediction rules:

- intent = (newly delivered on intent-wrong rows x 32 / 70) minus (lost on currently-correct rows x 0.767), times
  0.0926 pp. The 0.767 is P(correct | in block) minus P(correct | off block), measured on this column.
- SLU = newly printed reachable MISSING x 0.2471 x 0.0662, plus exact items losing their print x 0.2471 x -0.0663.
  The loss term is the M1 printing rate taken as symmetric, which is an assumption.

| variant (in-sample, all 1,080 rows) | gold newly in block, wrong rows | gold lost, correct rows | correct rank-1 demoted inside block | MISSING newly printed | exact losing print | intent pp | SLU pp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| quota 60 | 10 | 4 | 74 | 2 | 66 | +0.14 | -1.05 |
| quota 120 | 5 | 5 | 47 | 2 | 44 | -0.14 | -0.69 |
| quota 240 | 3 | 2 | 12 | 2 | 23 | -0.02 | -0.34 |
| thin c3 f0.75 | 4 | 0 | 13 | 1 | 20 | +0.17 | -0.31 |
| thin c5 f0.75 | 4 | 0 | 10 | 1 | 16 | +0.17 | -0.25 |
| thin c3 f0.25 | 6 | 2 | 64 | 1 | 53 | +0.11 | -0.85 |
| thin c2 f0.25 | 5 | 2 | 77 | 1 | 53 | +0.07 | -0.85 |

The full 12-row grid is in `tables.md`.

**Cross-fitted.**

- **Half 0** chose quota 60. On half 1: +3 gained, 2 lost, intent -0.02.
- **Half 1** chose thin c5 f0.25. On half 0: +2 gained, 0 lost, intent +0.08.
- **Combined:**
  - The gold boundary is newly in the block on **5 of the 48** off-block wrong rows.
  - It is lost on **2 currently-correct rows**.
  - It also leaves the block on 19 intent-wrong rows that are already wrong, which costs them their conversion
    chance.
  - **47 currently-correct rows** see their gold demoted from rank 1 inside the block. This risk is not priced.
  - Predicted intent is **+0.07 pp [+0.02, +0.12]**.
  - 2 MISSING items are newly printed and **36 exact items lose their print**. Predicted SLU is **-0.56 pp**, or
    +0.03 on the gain side alone.
  - Exemplar tokens change by -12 per row.

**P-SV-1/2 lesson, confirmed in a new form.** Every selection that moves a gold boundary into the block also pushes
other rows' gold out or down: 0 to 5 currently-correct rows lose it, and 10 to 77 are demoted from rank 1. It also
removes printed values the Solver was using.

**The ceiling.** Delivering the gold boundary on all 48 off-block rows at 45.7 % with no loss gives 2.03 pp intent.
That would need a ranking change, not a pool view, because those rows rank at a median of 21.

## 5. Operator (c): per-scenario anti-pattern guards (item 4)

**Rules.** The rules apply on top of the delivered v4g column, which has already applied ti1 < 1 % and the
Wilson-guarded ee10. The statistics come from the v4g statistics pool: TRAIN minus Fold A, Fold B, R01 and R01C,
8,554 exemplars. There are three families:

- **ti<theta**: drop an entity whose type appears in fewer than theta of the delivered intent's TRAIN exemplars,
  theta in {2, 5, 10, 20} %.
- **st<theta**: the same test against the delivered scenario, theta in {2, 5, 10} %.
- **ee<theta**: empty the answer when the intent's entity-carrying rate is below theta, theta in {15, 20, 30, 40,
  50} %.

**Selection.** For each delivered scenario, the rule is chosen on one half: the highest strictly positive pooled gain
with at least 2 edited rows, ties going to fewer edits, otherwise no rule. It is applied to the other half, both ways.
Edits are scored exactly with the official arithmetic. The paired bootstrap uses whole-utterance clusters, 10,000
draws and seed 20260915.

| read | rows edited | SPURIOUS removed | exact dropped | partial dropped | SLU-F1 delta pp [CI95] |
| --- | ---: | ---: | ---: | ---: | --- |
| **cross-fitted (h0 -> h1 plus h1 -> h0)** | 42 | 22 | 17 | 4 | **-0.45 [-1.13, +0.18]** |
| h0 rules on h1 (full-roster delta) | 27 | 14 | 11 | 2 | -0.31 |
| h1 rules on h0 (full-roster delta) | 15 | 8 | 6 | 2 | -0.13 |
| in-sample reference (fit = read) | 43 | 32 | 4 | 9 | +0.87 [+0.40, +1.34] |

The rules chosen on the two halves agree in one scenario only (`general`: st < 10 %).

- Half 0 chose calendar st<5 %, general st<10 %, iot ee<40 %, music ti<2 %, play ti<20 %, qa st<2 % and takeaway
  ti<5 %.
- Half 1 chose email ti<10 %, general st<10 %, play st<2 % and recommendation st<5 %.

Every single global rule loses. The least harmful is ti<2 % at -0.14 pp; the worst are st<10 % at -4.26 and ti<20 % at
-5.34.

**Net FP removed minus TP lost**: 22 spurious entities removed, worth about +0.64 at 0.029 each. Against that, 17
exact entities are lost, worth about -1.13. Selection optimism is **1.3 pp**: +0.87 in-sample against -0.45
cross-fitted. Per-scenario negative knowledge on top of v4g does not transfer across halves of the same fold.

## 6. Composite (item 5) and per-scenario table (item 6)

**Overlap.** An (a) or (b) item counts once, and is removed when (c)'s rule on that row would drop its type. Here
(a) contributes no items, (b) contributes 2, and (c) removes none of them.

| composite | (a) pp | (b) SLU pp | (c) pp | **SLU-F1 pp** | intent pp | clears +1.5 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| credit-driven, as selected (conversion 30 / 45 / 60 %, or W4 0.052) | 0.00 | -0.56 | -0.45 | **-1.00** | +0.07 [+0.02, +0.12] | no |
| positive parts only (an upper reading; itself a selection) | 0.00 | 0.00 | 0.00 | **0.00** | +0.07 | no |
| largest honest number: the every-card N 16 reference alone (not credit-driven, harm not netted) | +0.27 (+0.18 / +0.36; W4 +0.03) | -- | -- | **+0.27** | 0 | no |

Per scenario (gold scenario of the row; the (a) and (b) pp are shares of the full roster; the (c) delta is pooled
within the scenario's 60 rows):

| scenario | (a) new MISSING | (b) new print | (b) exact losing print | (b) SLU pp | (b) gain / loss rows | (b) intent pp | (c) rows edited | (c) delta within scenario pp |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| alarm | 0 | 1 | 2 | -0.02 | 0 / 0 | 0.00 | 1 | +0.82 |
| audio | 0 | 0 | 1 | -0.02 | 1 / 0 | +0.04 | 2 | +2.93 |
| calendar | 0 | 0 | 6 | -0.10 | 0 / 0 | 0.00 | 0 | 0.00 |
| cooking | 0 | 0 | 0 | 0.00 | 1 / 0 | +0.04 | 0 | 0.00 |
| datetime | 0 | 0 | 3 | -0.05 | 0 / 0 | 0.00 | 0 | 0.00 |
| email | 0 | 0 | 4 | -0.07 | 0 / 0 | 0.00 | 4 | -2.51 |
| general | 0 | 0 | 1 | -0.02 | 1 / 2 | -0.10 | 8 | +0.04 |
| iot | 0 | 0 | 1 | -0.02 | 0 / 0 | 0.00 | 8 | -7.43 |
| lists | 0 | 0 | 0 | 0.00 | 0 / 0 | 0.00 | 1 | +1.01 |
| music | 0 | 0 | 1 | -0.02 | 0 / 0 | 0.00 | 1 | +1.30 |
| news | 0 | 1 | 2 | -0.02 | 0 / 0 | 0.00 | 0 | 0.00 |
| play | 0 | 0 | 3 | -0.05 | 0 / 0 | 0.00 | 12 | -3.77 |
| qa | 0 | 0 | 2 | -0.03 | 0 / 0 | 0.00 | 2 | -0.68 |
| recommendation | 0 | 0 | 4 | -0.07 | 1 / 0 | +0.04 | 0 | 0.00 |
| social | 0 | 0 | 1 | -0.02 | 0 / 0 | 0.00 | 1 | +0.40 |
| takeaway | 0 | 0 | 2 | -0.03 | 1 / 0 | +0.04 | 2 | -0.54 |
| transport | 0 | 0 | 2 | -0.03 | 0 / 0 | 0.00 | 0 | 0.00 |
| weather | 0 | 0 | 1 | -0.02 | 0 / 0 | 0.00 | 0 | 0.00 |

The (c) equal-scenario mean delta is -0.47, against a natural-mixture delta of -0.45. Its losses concentrate in `iot`
(ee<40 % fired on 8 rows), `play` and `email`.

## 7. What this means for decisions 263 and 265

- **The owner's premise holds in kind but not in size.** TRAIN knowledge is complete for this column's intent and
  type inventory. What is missing is (i) values TRAIN never shows (155 of the 434 items) and (ii) the use of values
  already supplied (211 items in the delivered supply, 139 of them MISSING). Neither is a construction-from-TRAIN
  operation.
- **Decision 265 as stated has no iteration-1 candidate.** The reasons are measured:
  - the composite does not reach the 1.5 pp predicted bar;
  - the credit table cannot select stable cells at this mass;
  - the exemplar pool cannot be expanded from TRAIN;
  - every pool selection that helps intent removes prints that the Solver uses.

  Under the spec's 263-R1 default, iteration 1 would stall at this pre-read.
- **Options the coordinator may put to the owner.** None is recommended here; the verdict is the owner's.
  - (A) Fly the stall default: lock / twin / ACE, with delivery candidates read offline.
  - (B) Fly the every-card N 16 list as a `claims_benefit: false` measurement. It would measure the list conversion
    and over-emission on Fold B. Its predicted ceiling is +0.27 pp, and it costs +651 tokens per row.
  - (C) Redirect iteration 1 to a consumption operator over the 139 in-supply MISSING items, at an exact oracle of
    about 139 x 0.066 = 9.2 pp. That is outside 265's class, and the Solver contract is locked by decision 245.
  - (D) Open an out-of-split expansion source such as `train_synthetic`. It needs an ENCODE contact and its own owner
    row.

## 8. Open questions and deviations

- **Script name.** The spec names `scripts/analysis/tfrl_augmentation_coverage.py`. This read uses the brief's name,
  `scripts/analysis/slurp_tfrl_coverage_preread.py`.
- **Fold A holdout: not run.** The selection fold already reads at or below zero. A Fold A pass needs the VER-1c lock
  column plus the Fold A query vectors and transcripts, roughly doubling the run. Ask if it is wanted.
- **Mode (b) is generous.** It counts a value printed by any pool exemplar of the type, or named by any card. A value
  printed only under another type in the pool counts as (d).
- **The (b) SLU harm term is an assumption.** It treats M1's printing conversion as symmetric. On the gain side alone
  (b) is +0.03 pp. The intent prediction uses the CONV probe rate (32 / 70, Fold A AGREE, gold-selected roster) for
  newly delivered entries, and this column's measured in-block / off-block gap for losses. Rank demotions inside the
  block (47 rows) are not priced.
- **Card-list token counts are estimates.** They are characters / 3.634 plus 8 per list, not tokenizer counts; a
  tokenizer pass would be a local vocab-only contact. The headroom figure uses the server's own usage fields.
- **Contact needed and not made.** Encoding `train_synthetic` (or any non-TRAIN source) for targeted exemplar
  expansion needs an embedder contact. It would need an exposure-ledger row and an ENCODE preparation, and it was not
  attempted.
