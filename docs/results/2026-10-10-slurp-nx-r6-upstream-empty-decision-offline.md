# NX R6 design read (owner decision 239): the empty-entity decision needs the core's own presence verdict gated by the supply's entity-free share; a verdict x N1 gate is worth +0.75 / +0.98 pp on the v4g base (CI-LB > 0 on both R1 flights, 0 intent rows), not the 1.5 pp bar; a deterministic v5 rule is not worth flying (offline, DESCRIPTIVE)

Read 2026-10-10 by Claude Opus 5.5 (analysis agent, on the coordinator's brief, Fable 5.1) in the worktree
`fable/nx-r6-upstream-empty` (base master `9ba3c72d7`). Read id `SAEA-SLURP-NX-R6-UPSTREAM-EMPTY-OFFLINE-V1`, recipe
`slurp-nx-r6-upstream-empty-offline-v1`, driver `scripts/analysis/slurp_nx_r6_upstream_empty.py`.

**Contacts: zero.** No model, server, tokenizer, encoder, embedder, scorer subprocess, network, paid API or GPU contact.
Every SLU-F1 below is an exact in-process re-score. Each sealed column's in-process per-row fields reproduce its sealed
official per-sample fields on 1,080 / 1,080 rows, and the pooled value reproduces the official aggregate; the run stops
otherwise. v4g is applied through the registered normaliser entry (`DELIVERY_NORMALISERS.resolve`, `replay_row`).
v4g(lock) reproduces the registered 63.6854 and v4g(r1-c3) reproduces 63.8994.

**Gold and text discipline.** Gold entered only offline, through the governed loaders (the v4 search driver's
`load_gold`: TRAIN for Folds A and B, `devel` for DEV-2000-ADDED); the test split was not read. No utterance text,
transcript, gold value, filler, exemplar text, Perception note text or model output is printed or persisted. Only ids,
counts, rates, AUCs, pp, intent and slot-type labels, and hashes appear.

**DESCRIPTIVE.** These are development numbers on TRAIN construction folds and DEV-2000-ADDED (decisions 28 and 86),
never a test claim. Thresholds were explored on the same Fold B rows that score them. Cross-fitted numbers (rule chosen
on one utterance-hash half, applied to the other) are reported beside every selected point. The verdict word is the
coordinator's.

## 0. Answer in eight lines

1. **Separability.** The supply's own entity-free exemplar share (N1) is the best signal available before the Solver
   answers: AUC 0.856 [0.832, 0.877] for "gold has no entity". TRAIN intent priors come next (0.73-0.75), then audio
   duration (0.67). Cross-fitted combinations add almost nothing (0.86); adding the lock answer's item count gives
   0.89.
2. **Perception carries no entity information today.** On all 1,080 rows of both flights its note has
   `unresolved_fields` = [] and `evidence_refs` = [] (AUC exactly 0.5). Candidate count, distinction length and note
   length are noise (0.45-0.54).
3. **A gate alone does not empty rows well.** "Empty when the signal fires" (deterministic) gains at most +0.45 / +0.60
   (v3, i1 / i2) and +0.13 / +0.11 (v4g) pp on Fold B; cross-fitted +0.25 / +0.41 (v3) and +0.13 / -0.04 (v4g). On the high-N1 rows, lock already answers empty
   on most empty-gold rows, so every emptied row costs as much true-positive mass as it removes false fills.
4. **The core's presence verdict, gated by N1, works.** Rule `c3verdict`: keep the lock answer and empty it only where
   the aggressive arm answered empty AND N1 >= 0.2. On the v4g base it gives **+0.75 [+0.27, +1.24]** (i1) and
   **+0.98 [+0.50, +1.48]** (i2), with 0 intent rows changed, false fill 91 -> 64 and 93 -> 60, and 3 non-empty exact
   rows lost per flight. On the sealed v3 base it gives +1.38 / +1.56. The ungated verdict gives +0.06 / +0.45 (v4g).
5. **Where the aggressive arm loses.** It loses 22 (i1) and 23 (i2) non-empty rows that lock had exactly right. Of
   these, 17 / 14 were emptied entirely. They are single-entity `date` / `time` / `food_type` / `media_type` rows on
   intents with a TRAIN entity rate of about 0.8, Perception put the gold intent at rank 1 on 18 / 21 of them, and they
   saw 14-20 entity-bearing exemplars. The N1 >= 0.2 gate does not fire on 17 / 22 and 18 / 23 of them: a supply-side
   presence signal would have protected them.
6. **R6 (A), a Perception-side presence verdict, consumed deterministically at delivery with the N1 gate:**
   predicted +0.75..+0.98 pp on the v4g base. The conversion is the Solver-side c3 verdict measured on two flights
   (recall 0.81-0.83, precision 0.74-0.76 on empty-gold rows). Perception's own verdict quality is unmeasured.
   **R6 (B), a supply-side per-intent prior card:** predicted about +0.1 pp. It has no positive measured analogue: the
   prior is already visible to the Solver in the 20 annotated exemplars, the Stage S N1 release gives +0.13 at M1, and
   the i2-c2 soft empty sentence measured false fill +9.95.
7. **Fly (A) first,** with the supply statistic as its gate rather than as a card. Neither variant is predicted to reach
   the 1.5 pp bar on the v4g base. (A) is the first empty-entity mechanism with CI95 lower bound > 0 on both R1 flights
   and zero intent movement.
8. **The deterministic v5 does not do the same at zero GPU.** The best grid rule (N1 >= 0.6, selected on A2) gives A2
   +0.33 [+0.11, +0.63], Fold A +0.16 [-0.18, +0.48] and Fold B +0.04 [-0.23, +0.29]. No rule clears 0.67 pp on any
   pool. Rate rules beyond v4g's `ee-wilson` intent (`qa_maths`) are harmful (Fold A -0.27 to -1.89).

## 1. Inputs and identities

| item | value |
| --- | --- |
| iteration 1 | `SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-V1` / `attempt-slurp-native-stage3-nx-r1-solver-fold-b-generation-v1`; aggressive arm `r1-c3`; phases.json `236cc47c...` |
| iteration 2 | `SAEA-SLURP-STAGE3-NX-R1-I2-SOLVER-FOLD-B-V1` / `attempt-slurp-native-stage3-nx-r1-i2-solver-fold-b-generation-v1`; aggressive arm `r1-i2-c3`; phases.json `ca50953a...` |
| columns read | `supply-variants/arm-{lock,aa,<aggressive>}-first-visit-outputs.jsonl` and `...-slurp-slu-official-train-scores.json` of each run (i1 lock `63d26c02...` / `50e3ab3b...`, c3 `d8190ea7...` / `0778724b...`; i2 lock `58bb98c7...` / `6736870f...`, i2-c3 `bec7beff...` / `87936e36...`) |
| roster | TRAIN Fold B, 1,080 rows (392 empty-gold), 1,080 utterance clusters |
| entity-rate table | `prepared/SAEA-SLURP-V4-TRAIN-STATISTICS-V1/intent-entity-rate-v1.json` `bd43804d...` (pool minus Fold A / Fold B / R01 / R01C: disjoint from every roster here) |
| exemplar pool (N1 annotations) | `knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json` `fcb5506c...` (the cells' store; it excludes Folds A and B) |
| v5 pools | A2 `SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1` (1,000; v3 65.93 -> v4g 66.91, 115 rows), Fold A `SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1` (1,080; 63.61 -> 65.62, 109 rows), Fold B i1 lock (v4g 63.69) |
| outputs | `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-NX-R6-UPSTREAM-EMPTY-OFFLINE-V1/` `report.json` `6445b95a2f2c506c8339ed35109222c98033282a44d9c5722fbbd3dd79ecc522`, `tables.md` `285ce54a4f7051771bac5d20b0a4c911e73a6abcc64e3c0f1f026b6d46433603` (content hashes with `generated_at` stripped; `content-sha256.json` beside them) |
| driver | `scripts/analysis/slurp_nx_r6_upstream_empty.py` sha256 `a76de68c2faf0d60a7a68d17bb47a0c3170a0e8f1f57151c4fce19943f69d3b9`; reuses the v4 search driver (`score_vector`, `pooled`, `Bootstrap`, `load_gold`, `load_delivered`, `POOLS`) |
| bootstrap | contrasts: paired whole-utterance clusters, 10,000 draws, seed 20260915 (the v4 driver's); AUC CI95: 2,000 cluster draws, seed 20261010 |

Levels (in-process = official): i1 lock 62.13, aa 62.70, c3 63.09; v4g lock 63.69, v4g aa 64.22, v4g c3 63.90.
i2 lock 63.43, aa 63.00, i2-c3 64.18; v4g lock 64.86, v4g aa 64.41, v4g i2-c3 64.94.

## 2. Definitions

- **Empty-gold row.** The gold entity list is empty (392 of 1,080 rows).
- **False fill.** On an empty-gold row, the column predicts at least one entity (official exact TP + FP > 0).
- **Non-empty exact.** On a non-empty-gold row, official exact FP = FN = 0.
- **Signals.** Each is oriented so that a higher value means "more likely empty". Missing values (at most 8 rows, an
  intent off the table) are filled with the median.
  - (a) one minus the TRAIN entity-carrying rate of Perception's rank-1 intent, of the shortlist max or mean, or of the
    majority intent of the 20 supplied exemplars;
  - (b) N1, the entity-free share of the 20 supplied exemplars; the same share within the rank-1 intent's exemplars;
    minus the top-1 exemplar cosine;
  - (c) Perception note counts (unresolved fields, slot-type-named fields, evidence refs, candidates, distinction
    tokens, completion tokens);
  - (e) minus the audio seconds of the Perception request;
  - (d, post-Solver) minus the lock item count; one minus the rate of lock's delivered intent.
  - Combinations: an L2 logistic regression cross-fitted over two utterance-hash halves, so each row is scored by a
    model that never saw it.
- **Counterfactual behaviours** on the rows where a rule fires; every other row keeps the lock row:
  - `c3`: the aggressive arm's whole row (its intent label included);
  - `empty`: the lock row with its entities removed (the deterministic rule);
  - `c3verdict`: the lock row with its entities removed only where the aggressive arm answered no entity. The
    aggressive arm is used purely as a presence verdict, so no label can move.
- **Bases.** v3 is the sealed columns as scored. v4g is the same columns after the registered v4g normaliser, which is
  the R5 / lock-v2.2 delivery.

## 3. Question 1: separability of empty-gold rows (Fold B, AUC for "gold empty", CI95)

| signal | i1 AUC [CI95] | i2 AUC [CI95] | median empty / non-empty (i1) |
| --- | --- | --- | --- |
| (b) **N1 entity-free share of the 20 exemplars** | **0.856 [0.832, 0.877]** | **0.856 [0.832, 0.877]** | 0.35 / 0.05 |
| (b) entity-free share within the rank-1 intent's exemplars | 0.819 [0.793, 0.845] | 0.821 [0.795, 0.847] | 0.36 / 0.00 |
| (a) 1 - rate of the exemplar-majority intent | 0.751 [0.721, 0.780] | 0.751 [0.721, 0.780] | rate 0.63 / 0.81 |
| (a) 1 - rate of Perception's rank-1 intent | 0.733 [0.702, 0.764] | 0.747 [0.716, 0.776] | rate 0.60 / 0.80 |
| (a) 1 - mean rate over the shortlist | 0.714 [0.681, 0.745] | 0.716 [0.683, 0.747] | |
| (a) 1 - max rate over the shortlist | 0.678 [0.643, 0.713] | 0.683 [0.647, 0.717] | |
| (e) shorter audio | 0.665 [0.632, 0.699] | 0.665 [0.632, 0.699] | 2.30 s / 2.88 s |
| (c) shorter distinction (rank 1) | 0.537 [0.501, 0.573] | 0.539 [0.502, 0.574] | 6 / 6 tokens |
| (c) shorter note (completion tokens) | 0.487 [0.450, 0.522] | 0.494 [0.459, 0.530] | |
| (b) lower top-1 exemplar cosine | 0.481 [0.444, 0.519] | 0.481 [0.444, 0.519] | |
| (c) fewer candidates | 0.450 [0.426, 0.475] | 0.457 [0.432, 0.482] | 3 / 3 |
| (c) unresolved fields, slot-named fields, evidence refs | **0.500 [0.500, 0.500]** (constant 0 on 1,080 rows) | 0.500 | 0 / 0 |
| combo: rate + N1 (cross-fit) | 0.857 [0.833, 0.878] | 0.858 [0.834, 0.879] | |
| combo: rate + N1 + note (cross-fit) | 0.854 [0.829, 0.876] | 0.855 [0.830, 0.877] | |
| combo: all pre-Solver (cross-fit) | 0.864 [0.839, 0.886] | 0.861 [0.836, 0.883] | |
| (d) fewer lock items (post-Solver) | 0.812 [0.787, 0.836] | 0.809 [0.785, 0.835] | 0 / 1 |
| (d) 1 - rate of lock's delivered intent (post-Solver) | 0.746 [0.715, 0.776] | 0.747 [0.716, 0.777] | |
| combo: all pre-Solver + lock (cross-fit) | 0.893 [0.872, 0.914] | 0.888 [0.866, 0.909] | |

The supply-side signals are identical across the two flights: both flights rendered the same supply.

**The Solver's own presence judgement as a classifier** (rows answered with no entity; recall and precision for
empty-gold):

| column | i1 rows empty | on empty-gold / on non-empty | recall / precision | i2 rows empty | recall / precision |
| --- | ---: | --- | --- | ---: | --- |
| lock | 319 | 257 / 62 | 0.656 / 0.806 | 318 | 0.653 / 0.805 |
| aggressive c3 | 431 | 319 / 112 | 0.814 / 0.740 | 432 | 0.834 / 0.757 |

The N1 signal, binned, shows why a gate helps (i1; i2 is within a few rows):

| N1 share | rows | empty-gold | lock false fill | c3 false fill | non-empty lock-exact | lost by c3 | non-empty rows c3 empties |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| [0.0, 0.1) | 392 | 27 | 18 | 11 | 143 | 11 | 45 |
| [0.1, 0.2) | 202 | 50 | 20 | 14 | 70 | 6 | 26 |
| [0.2, 0.3) | 164 | 74 | 34 | 22 | 43 | 5 | 19 |
| [0.3, 0.5) | 180 | 113 | 36 | 20 | 20 | 0 | 15 |
| [0.5, 0.7) | 74 | 63 | 16 | 3 | 3 | 0 | 7 |
| [0.7, 1.0] | 68 | 65 | 11 | 3 | 2 | 0 | 0 |

Below N1 0.2 the aggressive decision removes 13 false fills but loses 17 exact non-empty rows. At N1 >= 0.2 it removes
49 false fills and loses 5.

## 4. Question 2: oracle value of an upstream verdict (official pooled SLU-F1, pp vs lock on the same base)

References:

| contrast | i1 v3 | i1 v4g | i2 v3 | i2 v4g |
| --- | --- | --- | --- | --- |
| aggressive arm everywhere (the flown arm) | +0.96 [-0.21, +2.11] | +0.21 [-0.91, +1.34] | +0.74 [-0.45, +1.95] | +0.08 [-1.10, +1.29] |
| `c3verdict` everywhere (verdict, no gate) | +0.74 [-0.12, +1.61] | +0.06 [-0.79, +0.89] | +1.25 [+0.35, +2.13] | +0.45 [-0.41, +1.31] |
| perfect gate, `c3` on empty-gold rows only | +1.88 | +1.08 | +2.39 | +1.70 |
| perfect gate, `empty` on empty-gold rows only (ceiling) | +4.53 | +3.38 | +4.72 | +3.46 |
| `aa` twin | +0.57 | +0.53 | -0.43 | -0.45 |

**The declared single rule** is the same for both flights: `c3verdict` with gate N1 >= 0.2 (486 rows fire). The fixed
grid N1 >= {0.1, 0.15, ..., 0.9} is in `report.json` `fixed_n1_rules`, and 0.15-0.25 form a plateau.

| base | flight | delta pp [CI95] | false fill base -> new | non-empty exact lost / gained | intent rows changed |
| --- | --- | --- | --- | --- | --- |
| v3 | i1 | **+1.38 [+0.82, +1.97]** | 135 -> 85 | 3 / 0 | 0 |
| v3 | i2 | **+1.56 [+1.02, +2.13]** | 136 -> 84 | 3 / 0 | 0 |
| **v4g** | **i1** | **+0.75 [+0.27, +1.24]** | 91 -> 64 | 3 / 0 | 0 |
| **v4g** | **i2** | **+0.98 [+0.50, +1.48]** | 93 -> 60 | 3 / 0 | 0 |

**Best operating points over the full sweep.** The sweep covers 25 signals x 3 behaviours x (top 5-60 % of rows, rate
cuts 0.05-0.50, N1 cuts 0.1-0.9), with the in-sample CI and the cross-fitted value:

| base / flight | behaviour, signal group | rule | fired | delta pp [CI95] in-sample | cross-fit delta [CI95] | intent rows |
| --- | --- | --- | ---: | --- | --- | ---: |
| v3 i1 | `c3verdict`, pre-Solver | rate + N1 + note combo, top 60 % | 648 | +1.45 [+0.83, +2.10] | +1.45 [+0.85, +2.08] | 0 |
| v3 i2 | `c3verdict`, pre-Solver | rate + N1 + note combo, top 50 % | 543 | +1.72 [+1.12, +2.35] | +1.62 [+0.94, +2.30] | 0 |
| v3 i2 | `c3`, pre-Solver | same combo, top 50 % | 543 | +1.76 [+1.06, +2.48] | +1.61 [+0.82, +2.42] | 5 |
| v4g i1 | `c3verdict`, pre-Solver | rate + N1 + note combo, top 60 % | 648 | +0.85 [+0.31, +1.41] | +0.85 [+0.34, +1.40] | 0 |
| v4g i2 | `c3verdict`, pre-Solver | N1 within rank-1 intent, top 50 % | 549 | +1.16 [+0.62, +1.73] | +1.16 [+0.62, +1.73] | 0 |
| v4g i2 | `c3`, pre-Solver | rate + N1 + note combo, top 50 % | 543 | +1.34 [+0.69, +2.03] | +1.34 [+0.69, +2.03] | 5 |
| v4g i1 | `empty` (deterministic), pre-Solver | all pre-Solver combo, top 10 % | 108 | +0.13 [-0.17, +0.40] | +0.13 [-0.17, +0.40] | 0 |
| v4g i2 | `empty`, pre-Solver | N1, top 15 % | 176 | +0.11 [-0.38, +0.57] | -0.04 [-0.63, +0.54] | 0 |

**Operating point and the bar.** The best gated verdict reaches +1.45 / +1.72 pp on the sealed v3 columns; i2 clears
1.5 pp and i1 does not. On the v4g base, which R6 would sit on, it reaches +0.85 / +1.16 pp, so **no operating point
clears +1.5 pp**. The perfect-gate ceiling of the c3 verdict on that base is itself only +1.08 / +1.70. v4g already
removes about a third of the false-fill mass (135 -> 91).

**The exchange rates agree.** The declared rule on v4g i1 empties 27 false fills (x 0.033 = +0.89) and loses 3
non-empty exact rows (x 0.070 = -0.21), predicting +0.68 against a measured +0.75. On i2 the same arithmetic gives
33 x 0.033 - 3 x 0.070 = +0.88 against +0.98.

## 5. Question 3: the non-empty rows the aggressive arm lost against lock

These are non-empty-gold rows where lock was exact and the aggressive arm was not. Aggregate counts only.

| | i1 (`r1-c3`) | i2 (`r1-i2-c3`) |
| --- | --- | --- |
| rows | 22 | 23 |
| emptied entirely / truncated or changed | 17 / 5 | 14 / 9 |
| gold entities per row | 1: 22 | 1: 19, 2: 2, 3: 2 |
| gold slot types | date 5, food_type 3, media_type 3, time 3, weather_descriptor 2, and 6 others at 1 | date 11, time 4, business_name 2, list_name 2, media_type 2, place_name 2, and 6 others at 1 |
| gold intents | weather_query 3; cooking_recipe, general_quirky, takeaway_order 2 each; 11 others at 1 | datetime_query 4, calendar_query 3, social_post 2; 14 others at 1 |
| Perception rank-1 = gold intent | 18 / 22 | 21 / 23 |
| TRAIN entity rate of the rank-1 intent: min / median / max | 0.29 / 0.80 / 0.93 (all non-empty rows: 0.00 / 0.80 / 0.97) | 0.30 / 0.79 / 0.93 |
| exemplars with entities, of 20: min / median / max | 15 / 19 / 20 (all non-empty rows: 4 / 19 / 20) | 14 / 18 / 20 |
| Perception unresolved fields / slot-named fields at rank 1 | 0 on all 22 | 0 on all 23 |
| gate N1 >= 0.2 fires (would expose the row) | 5 (protects **17**) | 5 (protects **18**) |
| best sweep rule fires | 7 (N1 within intent, top 55 %) | 6 (combo, top 50 %) |
| rate < 0.30 fires | 2 | 1 |

**Reading.** The losses are heard short values (dates, times, food and media types) on intents that usually carry
entities. On these rows the core decided "empty" against both of the signals it could have used: the supply showed
14-20 entity-bearing exemplars, and the intent prior is about 0.8. The N1 gate calls 17 / 22 and 18 / 23 of the
rows "not empty", and the rate prior (rate < 0.30) calls 20 / 22 and 22 / 23 "not empty". A presence verdict that sees the supply prior (or is gated by it) would have protected them.
Perception's note, as specified today, would not have helped: it carries no field about entities at all.

## 6. Question 4: the R6 mechanism

### 6.1 Variant (A): Perception-side presence evidence, consumed at delivery with the supply gate (recommended first)

**Mechanism.**

- The Perception note gains an explicit `entity_presence` verdict (`none` / `some`) and optionally a
  `heard_values_by_type` list. Its schema already has an unused per-candidate `unresolved_fields` list (empty on all
  rows), but a dedicated field is cleaner.
- Consumption is deterministic, in a delivery-normaliser successor of v4g: drop the delivered entities iff Perception
  says `none` AND the supplied exemplars' entity-free share is >= 0.2. The gate is the knowledge supply's own
  gold-free statistic, computed from the row's sealed `supplied_value_ids`.
- The Solver template stays the lock, and labels never move (intent guard: 0 rows).

**Predicted effect at a measured conversion.**

- **+0.75 [+0.27, +1.24] (i1) / +0.98 [+0.50, +1.48] (i2) pp official pooled SLU-F1 on the v4g base**, and
  +1.38 / +1.56 on v3.
- The conversion is the Solver-side explicit empty verdict of `r1-c3` / `r1-i2-c3`, measured on two Fold B flights:
  recall 0.814 / 0.834 and precision 0.740 / 0.757 on empty-gold rows.
- This assumes that Perception, given an explicit presence instruction, decides about as well as the Solver did. That
  is unmeasured. Perception sees the boundary block but no exemplars. If its verdict is worse, the gate limits the
  damage, because the losses sit on low-N1 rows.

**Registration and cost.**

- Instrument: a level-2 Perception-branch cell (P-SV family, render defect fixed 2026-10-09). Branch A is the lock
  Perception note and delivers. Branch P is the presence-verdict Perception template. Branch T is A's twin. Each
  branch's Solver is the lock template.
- The read uses three views:
  - the node-local verdict quality on branch P against gold (recall and precision on empty-gold, the c3 numbers above
    as the reference);
  - the offline delivery-rule column (v4g + the verdict x N1 rule applied to branch A's sealed answers with branch P's
    verdict), read at 0.67 pp, zero GPU;
  - the branch-P Solver column (the verdict seen by the Solver), as a diagnostic.
- Contacts: about 6 per row (3 Perception + 3 Solver) on 1,080 rows, about 6,500 contacts. That is **about 2.0 GPU-h**
  (P-SV-4: 8,727 contacts, 2.567 GPU-h; R1 i1: 8,640 contacts in 2 h 17 m).
- A Perception template column (E1 generalised to the Perception node: 3 Perception arms + 1 Solver = 4 contacts per
  row, about 1.2 GPU-h) would be cheaper but needs engineering first.
- Model-free work before either: the Perception note schema and parser accept the new field; the delivery-rule
  successor of v4g is registered offline (reads the branch note and the supply ids); and a render test shows the field
  reaches the branch Solver.

### 6.2 Variant (B): supply-side per-intent entity prior card (fly second, or as the gate only)

**Mechanism.** A card in the Solver supply: "intent X: N % of TRAIN utterances carry an entity; typical types t1,
t2". This would be a release swap on `slot-contracts` (a TRAIN-only alternate), or an E42 supply arm.

**Predicted effect at a measured conversion.** About **+0.1 pp**:

- The prior is already in the Solver's supply: the 20 exemplars print their annotations, and the lock Solver already
  follows them. Lock false fill is 67 % at N1 < 0.1 and 17 % at N1 >= 0.7.
- The nearest measured analogues are the Stage S N1 release, +0.13 pp at the M1 conversion (N1 oracle +0.55 / +0.68),
  and iteration 2's soft empty sentence `i2-c2`, which moved false fill +9.95 [+6.37, +13.78] the wrong way.
- Bound: if the card made the Solver behave like the gated verdict above, it would be worth +0.75 / +0.98 on v4g, the
  same as (A). No measured conversion supports a card reaching it.

**Registration and cost.** It needs the Stage S engineering E-S1 (a `supply` column kind on the review-off module
base) and E-S2 (reader support), plus a model-free TRAIN-only prior-card release. Then a supply column of 3-4 arms,
about 1.2-1.5 GPU-h (Stage S design section 6.2 scaled from 9 to 4 contacts per row).

**Use of (B) in R6.** The supply statistic is worth more as the GATE of (A) than as a card. It is gold-free, computed
by the supply node, costs nothing at runtime, and is what protects 17 / 22 and 18 / 23 of the rows the ungated verdict
lost.

### 6.3 Which first, and the bar

Fly (A) first.

- Its predicted effect on the v4g base is +0.75..+0.98 pp. That is below the 1.5 pp same-flight bar and above the
  0.67 pp offline floor at the point on both flights.
- It is the only empty-entity mechanism on file whose CI95 lower bound is above 0 on both R1 flights with zero intent
  movement. It answers the intent guard that failed every R1 arm (9-13 rows).
- If the coordinator holds rounds to 1.5 pp on the v4g base, neither (A) nor (B) qualifies alone. (A) would then be
  carried as a composable component, which needs its own lock rule, like v4g.

A fresh-roster confirmation of the CONSUMPTION RULE needs no new instrument and is available before (A) flies:

- a two-arm Solver template column on TRAIN Fold A (lock + `r1-i2-c3` as the verdict arm + the twin; 4 contacts per
  row, about 1.2 GPU-h);
- the gated rule applied offline;
- under the iteration-2 plan this is also the Fold A confirmation step.

This measures the rule with a Solver-side verdict (an extra Solver contact per row at runtime). Variant (A) then moves
the verdict upstream to Perception.

### 6.4 The deterministic v5 (v4g + "empty when the signal fires"), zero GPU

The rule fires on rows by signal alone and empties the delivered entities (`empty` behaviour) on the v4g column. It is
selected on A2 (point maximum over the declared grid) and read on Fold A and Fold B. The table shows the delta pp, with
(rows fired, false fills removed, non-empty exact lost):

| rule | A2 (1,000) | Fold A (1,080) | Fold B lock (1,080) |
| --- | --- | --- | --- |
| delivered-intent rate < 0.05 | +0.00 (11, 0, 0) | +0.00 (7, 0, 0) | +0.00 (7, 0, 0) |
| delivered-intent rate < 0.10 | +0.12 (19, 3, 0) | -0.27 (52, 4, 6) | -0.09 (46, 3, 2) |
| delivered-intent rate < 0.20 | -0.25 (31, 3, 4) | -0.46 (115, 8, 11) | -0.45 (105, 4, 6) |
| delivered-intent rate < 0.30 | -0.68 (76, 4, 12) | -0.92 (156, 9, 17) | -0.90 (155, 6, 12) |
| rank-1 intent rate < 0.10 | +0.15 (21, 2, 1) | -0.38 (53, 4, 5) | -0.60 (51, 3, 7) |
| N1 >= 0.5 | +0.24 (110, 12, 5) | -0.10 (176, 15, 9) | -0.07 (142, 13, 5) |
| **N1 >= 0.6 (selected on A2)** | **+0.33 [+0.11, +0.63]** (51, 7, 0) | **+0.16 [-0.18, +0.48]** (128, 8, 3) | **+0.04 [-0.23, +0.29]** (100, 7, 2) |
| N1 >= 0.7 | +0.21 (31, 6, 0) | +0.09 (91, 5, 2) | -0.02 (68, 5, 2) |
| N1 >= 0.8 | +0.00 (7, 0, 0) | +0.03 (51, 2, 1) | +0.05 (40, 3, 0) |

The full grid (rates 0.05-0.50, N1 0.5-0.9) is in `report.json` `v5.grid`.

**Answer.** No. A deterministic rule does not do what the gated verdict does: no grid point clears 0.67 pp on any pool,
and the A2-selected rule is +0.04 on Fold B. On the rows a gold-free signal flags, the lock Solver already answers
empty on most empty-gold rows (v4g lock false fill on Fold B is 91 of 392). What remains on those rows is a mix that
only an audio-grounded verdict can separate. The rate rules repeat v4's `ee10` lesson: beyond `ee-wilson`'s single
intent (`qa_maths`) they delete heard values.

## 7. Caveats

- **Selection.** The gate value 0.2 and the best sweep rules were found on the Fold B rows that score them. The
  cross-fitted values shrink little (for example +0.85 -> +0.85, +1.72 -> +1.62), and the N1 0.15-0.25 plateau is
  flat. The confirmation still belongs on Fold A (section 6.3).
- **The verdict analogue.** Variant (A)'s conversion is the Solver's verdict under an explicit-empty instruction with
  the exemplar supply in view. A Perception verdict is a different node with less context; its quality is the first
  thing the R6 read must measure.
- **Two lock columns.** The two flights' lock columns differ (62.13 vs 63.43 officially; twins +0.57 and -0.43). The
  two flights are reported side by side and are never pooled.
- **Gate leakage.** None. The entity-rate table and the exemplar pool exclude Fold A and Fold B. N1 is a property of
  the row's own sealed supply.

## 8. Reproduce

```bash
# WSL Ubuntu-24.04, worktree root
source ~/.venvs/speechrl/bin/activate
export PYTHONPATH=$PWD/src PYTHONDONTWRITEBYTECODE=1 \
       SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
python -B scripts/analysis/slurp_nx_r6_upstream_empty.py --data-root "$SPEECHRL_DATA_DIR" \
    --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json            # writes the outputs
python -B scripts/analysis/slurp_nx_r6_upstream_empty.py --data-root "$SPEECHRL_DATA_DIR" \
    --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json --check    # re-derives, compares
```

Run time is about 4-9 minutes on CPU, almost all of it reading sealed traces and phases. `--keep-sweep` persists every
sweep row in `report.json`.
