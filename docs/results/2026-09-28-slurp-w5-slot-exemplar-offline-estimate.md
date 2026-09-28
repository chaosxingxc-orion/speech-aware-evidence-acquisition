# SLURP W5 slot-exemplar supply: the offline Fold A estimate (descriptive)

Date: 2026-09-28. Author: Claude Opus 5.5 (merge and records agent), for the root coordinator.
Status: **descriptive record, no verdict.** Cell W5 is registered and **HELD, not flown**. Nothing in this
note authorises a flight, a flip or an admission entry. All numbers are development numbers on TRAIN
Fold A (owner decisions 28 and 86), counts only, gold read offline.

Sources (all merged on master):

- package `docs/readiness/2026-09-27-slurp-stage3-w5-fold-a-v1/` (`README.md`, `registered-facts-v1.json`
  field `fold_a_offline`);
- estimate script `scripts/analysis/slurp_w5_fold_a_offline_estimate.py` (sha256 `93ff55b1...`, as pinned in
  the registered facts), output `analysis/SAEA-SLURP-W5-FOLD-A-OFFLINE-ESTIMATE-V1/estimate-v1.json` under
  `SPEECHRL_DATA_DIR` (sha256 `b65a9165...`); exposure-ledger row `SAEA-SLURP-W5-FOLD-A-OFFLINE-ESTIMATE-V1`
  (model-free);
- the coordinator's ruling: the outcome of decision 170 in
  `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`.

This note restates the package's numbers. It recomputes nothing and contacts no model, server, tokenizer,
encoder, embedder, scorer or GPU.

## 1. What W5 would add

W5 is the retained AGREE arm (`SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1`, official SLU-F1 65.16 / intent 85.83 on
TRAIN Fold A) with one added store, `knowledge_stores.slot-exemplars`. The store is a second speech-keyed TRAIN
exemplar route delivered to the Solver and scoped by the row's intent shortlist. It delivers **nine slot-bearing
TRAIN exemplars per row**: three for each of the first three intents of the row's AGREE boundary ranking, and never
an utterance that the M1 route already delivers on that row. Fold A overlap with the pool is 0 utterances.

## 2. The estimate as the package records it

Method (script docstring): an AGREE entity error item counts as NEWLY printed when its gold type and value appear
in a W5 exemplar and in none of the row's M1 exemplars. Expected pp is the sum, over error classes, of newly
printed items x M1's measured delivered-filler conversion (0.2471) x the error-source read's isolated pp per
repaired item.

| error class (error-source taxonomy) | AGREE items | gold value printed by W5 | already printed by M1 | NEWLY printed by W5 | expected pp |
| --- | ---: | ---: | ---: | ---: | ---: |
| MISSING | 173 | 72 | 90 | 9 | 0.126 |
| SPURIOUS | 253 | 0 | 0 | 0 | -- |
| WRONG-TYPE | 51 | 4 | 14 | 0 | 0.0 |
| BOUNDARY | 75 | 18 | 29 | 1 | 0.0095 |
| WRONG-VALUE | 41 | 3 | 6 | 0 | 0.0 |
| NEAR | 56 | 6 | 20 | 0 | 0.0 |
| FORMAT | 11 | 0 | 4 | 0 | -- |

- **Newly shown items: 10 on 10 rows** (9 MISSING + 1 BOUNDARY). Of the 173 MISSING items, M1's twenty exemplars
  already show the gold value for 90, and those items are still missed. By slot type, the newly shown items are:
  MISSING business_name 1, date 2, device_type 1, media_type 2, news_topic 1, order_type 1, podcast_name 1;
  BOUNDARY date 1.
- **Conversion 0.2471** (M1's measured delivered-filler conversion, a lower bound: 133 / (0.5719 x 941)).
- **Expected effect 0.1355 pp SLU-F1.** The ceiling is **0.5482 pp**, reached only if every newly shown item
  converts. Both figures are far below the 2.5 pp benefit floor at n = 1,080 and under the 1.2485 pp SLU harm
  margin. The direct analogue agrees: VAR-1 exemplar budget 30 vs 20 read +0.09 [-1.47, +1.60] SLU.
- **Registered declaration:** admission `no-harm`, `expected_effect_pp` 0.0, `claims_benefit` false, SLU-F1
  primary with harm margin 1.2485 and intent (0.9943) as the guard, replicate
  `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1`.
- **Named risks (AGREE rows):**
  - All **414 rows without gold slots** would receive nine slot-bearing exemplars. SPURIOUS is the largest error
    class, with 253 items.
  - 9,119 of the 12,345 printed (type, value) pairs have types that the row's gold does not carry.
  - On 89 rows the gold intent is outside the scoping shortlist (18 of those rows are intent-correct on AGREE).
  - 98 rows would receive no gold-intent exemplar from W5.
- **Cost:** +451.0 tokens per Solver/Reviewer/Planner contact on average (max 612.8), which is +1,378.7 tokens per
  row and 3.95 % of AGREE prompt volume. Projected realised maxima stay under the 20,992 operational budget. The
  runtime pre-flight reads COMPACT_REQUIRED on the Solver with a physical margin of +1,996.

## 3. The coordinator's ruling (outcome of decision 170, quoted)

> Outcome of decision 170 (2026-09-28 00:20Z): W5 was registered as built (package 2026-09-27-slurp-stage3-w5-fold-a-v1, held) but its model-free offline estimate shows almost no delivery headroom: of the AGREE arm's 173 MISSING slot items W5 newly shows the gold value on 10 (M1's twenty exemplars already show it on 90 that were still missed); at M1's measured conversion 0.247 the expectation is 0.14 pp SLU, ceiling 0.548, under the 1.2485 floor, with an over-tagging risk on the 414 rows without gold slots. Coordinator ruling: W5 stays registered and HELD, not flown; the SLU main line is re-pointed at USE, not delivery (W4 conventions read no-harm, B4 explicit empty-entity decision, and slot-side contrastive consumption at the Solver in B1's family); the +17.4 figure quoted for slot-side retrieval was an oracle, not a delivery headroom.

Precision note: the ruling says "newly shows the gold value on 10" of the MISSING items. The package counts those
10 as 9 MISSING plus 1 BOUNDARY item (section 2). The expectation is the same either way.

## 4. Results-ledger line

`docs/results/stage2-results-ledger.md` carries one appended section for this note ("2026-09-28: cell W5 ...
offline estimate, HELD not flown"). No existing row is rewritten, and the JSON twin is unchanged because W5 has no
flight and no verdict.
