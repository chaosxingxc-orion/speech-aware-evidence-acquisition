# NX R0.2 / E3: node-local -> official exchange rates on the sealed COMP-1b bytes (offline, zero GPU)

**Status: DESCRIPTIVE, development numbers (decisions 28 and 86).** Read id `SAEA-SLURP-NX-EXCHANGE-RATES-V1`,
recipe `slurp-nx-exchange-rates-offline-v1`, driver `scripts/analysis/slurp_nx_exchange_rates.py`. Programme:
`docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md` (C0.1, C1 E3, C2 R0.2, C3). Author: Claude Opus
5.5 (analysis agent), 2026-10-09.

**Contacts: zero** -- no model, server, tokenizer, encoder, embedder, official-scorer subprocess, network, GPU or
paid-API contact. Prompt-token counts are the server's own sealed `usage` fields. Gold enters only offline through
the governed SLURP loader (TRAIN through `ES.load_gold`, DEV-2000-ADDED through `data.slurp.load_slurp_split` on
`devel`); the test split is not read. No utterance text, transcript, gold value, filler, card body or model output
is printed or persisted.

## 0. What every R-round should cite (summary)

| exchange rate (pp of official pooled SLU-F1 unless stated) | Fold A (1,080) | DEV-2000-ADDED (1,000) |
| --- | ---: | ---: |
| +1 Solver raw exact-set row (node metric) | +0.056 | +0.057 |
| +10 Solver raw exact-set rows | +0.56 | +0.57 |
| +1 delivered exact-set row (any wrong row, empirical mean) | +0.059 | +0.060 |
| +1 delivered exact row on a non-empty-gold row | +0.070 | +0.071 |
| -1 false-filled empty-gold row (row emptied) | +0.033 | +0.032 |
| +1 recovered MISSING entity (analytic = empirical) | +0.062 | +0.057 |
| -1 removed SPURIOUS entity (analytic = empirical) | +0.029 | +0.028 |
| +1 wrong entity repaired (one FP and one FN removed) | +0.091 | +0.085 |
| per 10 of each row above | x10 (see section 4) | x10 |
| intent: +1 delivered-correct row | +0.093 pp intent | +0.100 pp intent |
| intent: +1 Perception rank-1 gain (gold moved to rank 1) | +0.080 pp intent | +0.089 pp intent |

Reading: decision 192's 1.5 pp same-flight SLU target costs about **27 extra raw-exact Solver rows** (2.5 % of the
roster) on either pool, or 45-47 emptied false-fill rows, or 24-27 recovered MISSING entities, or 52-54 removed
SPURIOUS entities. The 2.5 pp cross-flight bar costs about 45 raw-exact rows. 1.5 pp of intent costs 17
(Fold A) / 15 (DEV) converted rows.

## 1. Sources (sealed, scored once)

| pool | run id | attempt | rows | official SLU-F1 | intent |
| --- | --- | --- | ---: | ---: | ---: |
| `comp1b_fold_a` (TRAIN Fold A) | `SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1` | `attempt-slurp-native-stage3-comp1b-fold-a-generation-v1` | 1,080 | 63.6095 | 85.65 |
| `a2` (DEV-2000-ADDED) | `SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1` | `attempt-slurp-native-stage3-comp1b-dev2000-added-generation-v1` | 1,000 | 65.9327 | 81.50 |

Byte identities (sha256 of the sealed files under `$SPEECHRL_DATA_DIR/runs/<run id>/<attempt>/`):

| file | Fold A | DEV-2000-ADDED |
| --- | --- | --- |
| `phases.json` | `079bcf1812ffb2c62791f4cff71b753ac663b9bec3c8c2468c1ebf000c98e1ec` | `4dc4cb803fd16a074a7ab1716542dc59abc87c71969e05a2b42cdffec559d14c` |
| `outputs.jsonl` | `a724412f987f1c86b72da6daab8a0859c972ced4e438957e73cc604de6bb69b6` | `25e6dd9dae842c333e692391280ca4845705666f34e87fab9f78296bc776f4e3` |
| `scores.json` | `35f4ff5e9cb60645e60d4d8385739dbc74a910f09f48072432011e3b53042d25` | `878babaa69577c5f94bd3f0563e44a6f336535322c6ced3ba757383c872880a9` |
| `trace.jsonl` | `7b2d7cfd5ae2d95d44344a7b1cbefc4709514b752aaff379d358e193575dc5aa` | `c51f08f90c6b822c606a15a805646cc05d00236faec2accca1b2cf0a8c1cee54` |

Knowledge pins: exemplar pool `knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json`
(file `fcb5506c...`, M1 content hash `4c498dc0...`), slot contracts `knowledge/slurp/semantic/slot-contracts-v2/
snapshot.json` (`a48ed83e...`). Output: `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-NX-EXCHANGE-RATES-V1/`
(`report.json` content sha256 `c08fe69104b5349a1cdc75f37782e9798856b9f31c2b13f9974cf849cd93ebc6`, `tables.md`
`db28c4876c7c358395abeb5d9780978def4bc395503124416357aaeca3979980`, both with `generated_at` stripped).

**Reproduction controls.** In-process TP/FP/FN totals reproduce the sealed official totals on both pools (the run
stops otherwise). The delivered class counts reproduce the S1 taxonomy refresh exactly
(`docs/results/2026-09-30-slurp-s1-slu-error-taxonomy-refresh.md`; Fold A SPURIOUS 262 / MISSING 189 / WRONG-TYPE 54
/ BOUNDARY 68 / NEAR 57 / WRONG-VALUE 42 / FORMAT 10; DEV 249 / 188 / 67 / 73 / 36 / 46 / 10). The first Solver
state in `phases.json` parses to the same answer as the first Solver MODEL_RESPONSE in the trace on 1,080 / 1,080
and 1,000 / 1,000 rows. `--check` re-derives byte-identically apart from `generated_at`.

## 2. Definitions

- **s1 (Solver node).** `parse_slu_response` on the response text of the row's first Solver MODEL_RESPONSE (the
  raw first answer; before Reviewer/Planner, revision and the deliver normaliser).
- **d (delivered).** The sealed `outputs.jsonl` text the official scorer read.
- **Entity exact-set row.** `entity_items(gold, pred)` (the S1 / node-ledger matcher) returns no item, i.e. the
  predicted (type, filler) multiset equals gold. An unparsed answer is scored as no entities, as the official
  scorer does (so an unparsed empty-gold row is exact; its gold items, if any, are MISSING).
- **False fill.** A parsed answer with at least one entity on an empty-gold row.
- **Classes.** SPURIOUS / MISSING / WRONG-TYPE / BOUNDARY / NEAR / WRONG-VALUE / FORMAT as in
  `analysis.sealed_credit.entity_states.entity_items`; row classes EMPTY-GOLD-FILL and PARSE-FAIL in addition.
- **Value in supply** (S1 `supply_class` over the headroom note's `evidence_class`): E1 the row's rendered
  exemplars print the (type, value); E2 they print the value under another type; E3 a delivered slot-contract card
  names the value (word-bounded, length >= 3); `none` otherwise. For gold-side classes the value is the gold value;
  for SPURIOUS it is the predicted value.
- **Analytic rate.** The headroom note's `gain_pp`: one entity unit = 2 TP/FP/FN units (word + char) moved in the
  pooled micro F1, from the pool's own totals (Fold A TP 1,396.0 / FP 871.64 / FN 725.64; DEV TP 1,544.0 /
  FP 858.78 / FN 736.78).
- **Empirical rate.** The headroom `Rescorer`: each real candidate edit (one row set to gold; one false-fill row
  emptied; one SPURIOUS item dropped; one MISSING item added) re-scored exactly against the sealed-equal totals;
  mean over all candidates.
- **Node rate.** +1 raw exact row buys `(P(d exact | s1 exact) - P(d exact | s1 parsed, not exact))` delivered exact
  rows times the empirical value of a raw-wrong row made exact. It is an expectation that assumes the measured
  transfer holds for newly exact rows, not a measurement.

## 3. Solver node vs delivery

| metric | Fold A s1 | Fold A d | DEV s1 | DEV d |
| --- | ---: | ---: | ---: | ---: |
| parse valid | 1,079 | 1,079 | 999 | 999 |
| entity exact-set rows | 531 | 551 | 482 | 504 |
| empty-gold rows | 414 | 414 | 314 | 314 |
| empty-gold false fill | 161 | 161 | 138 | 140 |
| non-empty-gold rows | 666 | 666 | 686 | 686 |
| non-empty exact | 278 | 298 | 306 | 330 |
| gold items exact / all | 492 / 941 | 521 / 941 | 572 / 1,027 | 607 / 1,027 |
| SPURIOUS / MISSING / WRONG-TYPE | 264 / 188 / 54 | 262 / 189 / 54 | 245 / 187 / 67 | 249 / 188 / 67 |
| BOUNDARY / NEAR / WRONG-VALUE / FORMAT | 68 / 57 / 42 / 40 | 68 / 57 / 42 / 10 | 74 / 36 / 47 / 44 | 73 / 36 / 46 / 10 |

Transfer s1 -> d:

| conditional | Fold A | DEV |
| --- | ---: | ---: |
| d exact given s1 exact | 528 / 531 (99.44 %) | 479 / 482 (99.38 %) |
| d exact given s1 parsed, not exact | 23 / 549 (4.19 %) | 25 / 517 (4.84 %) |
| d false fill given s1 false fill (empty gold) | 160 / 161 | 138 / 138 |
| d false fill given s1 correct empty | 1 / 252 | 2 / 176 |

Reading: on the COMP-1b graph the delivered entity answer is the Solver's first raw answer except for the deliver
normaliser's FORMAT repairs (40 -> 10, 44 -> 10) and about 4-5 % of raw-wrong rows changed later. **Raw exact-set
at the Solver is a faithful node-local proxy of the delivered entity metric (transfer gap 0.95).** The Solver's raw
parse failure on this graph is 1 / 1,080 and 1 / 1,000 (finish `stop`, leading `{`, no tool tag, no fence; no tool
schemas are rendered on this graph) -- the 87 / 100 parse defect is specific to the seed graph (see the R0.3 note
`2026-10-09-slurp-nx-solver-parse-root-cause.md`).

### 3.1 Per slot type (top 10 by gold items; exact items s1 -> d; spurious s1 -> d)

| Fold A type | gold | exact s1 / d | spurious s1 / d | | DEV type | gold | exact s1 / d | spurious s1 / d |
| --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: |
| date | 138 | 63 / 66 | 8 / 8 | | date | 177 | 102 / 107 | 11 / 12 |
| place_name | 100 | 57 / 63 | 14 / 13 | | event_name | 115 | 71 / 72 | 23 / 24 |
| time | 76 | 38 / 48 | 8 / 8 | | person | 84 | 40 / 51 | 25 / 25 |
| food_type | 65 | 43 / 43 | 20 / 20 | | place_name | 83 | 52 / 56 | 16 / 16 |
| media_type | 57 | 35 / 37 | 11 / 11 | | time | 68 | 40 / 44 | 9 / 10 |
| business_name | 52 | 18 / 19 | 14 / 14 | | currency_name | 38 | 24 / 24 | 10 / 10 |
| person | 42 | 19 / 22 | 13 / 13 | | artist_name | 35 | 17 / 21 | 4 / 4 |
| event_name | 41 | 19 / 21 | 16 / 16 | | media_type | 31 | 10 / 12 | 9 / 9 |
| transport_type | 36 | 20 / 20 | 3 / 3 | | weather_descriptor | 29 | 17 / 17 | 5 / 4 |
| weather_descriptor | 34 | 24 / 24 | 2 / 2 | | definition_word | 28 | 20 / 20 | 28 / 28 |

The full per-type table (all types) is in `report.json` (`pools.<pool>.by_type`). `date` is the largest MISSING
type on both pools (46 Fold A, 43 DEV, at s1).

## 4. Official exchange rates

| rate (pp of pooled SLU-F1) | Fold A | DEV |
| --- | ---: | ---: |
| remove 1 / 10 SPURIOUS entities (analytic) | 0.0290 / 0.2912 | 0.0282 / 0.2828 |
| recover 1 / 10 MISSING entities (analytic) | 0.0621 / 0.6187 | 0.0572 / 0.5701 |
| repair 1 / 10 wrong entities (FP + FN) | 0.0911 / 0.9113 | 0.0854 / 0.8541 |
| remove one SPURIOUS, empirical mean (n) | 0.0290 (262) | 0.0282 (249) |
| recover one MISSING, empirical mean (n) | 0.0621 (189) | 0.0572 (188) |
| one extra exact row, any wrong delivered row: mean / median (n) | 0.0590 / 0.0580 (529) | 0.0603 / 0.0564 (496) |
| one extra exact row, non-empty gold: mean (n) | 0.0702 (368) | 0.0713 (356) |
| one false-fill row emptied: mean (n); spurious entities per such row | 0.0333 (161); 1.149 | 0.0322 (140); 1.143 |
| one extra exact row among s1-parsed-not-exact rows: mean (n) | 0.0591 (526) | 0.0600 (492) |
| **+1 / +10 raw exact Solver rows (node rate)** | **0.0563 / 0.5629** | **0.0567 / 0.5672** |
| oracle: every wrong row exact at once | +36.39 | +34.07 |
| oracle: every false-fill row emptied at once | +5.86 | +4.84 |

The analytic and empirical per-entity rates agree to four decimals (a SPURIOUS or MISSING item always moves one full
word + char unit). For entity units the exact 10-unit rate is within 0.5 % of ten times the 1-unit rate. Per-row
rates are means over real candidate rows; their x10 values are linear extrapolations (the oracle rows show the
curve only bends at the scale of hundreds of rows).

## 5. Intent

| quantity | Fold A | DEV |
| --- | ---: | ---: |
| delivered correct / rows | 925 / 1,080 (85.65 %) | 815 / 1,000 (81.50 %) |
| Solver first answer correct | 913 | 785 |
| pp intent per converted row / per 10 | 0.0926 / 0.926 | 0.100 / 1.000 |
| delivered wrong rows | 155 | 185 |
| -- gold NOT on the Perception shortlist | 75 | 82 |
| -- gold on the shortlist, not rank 1 | 70 | 90 |
| -- gold rank 1, Solver delivered another intent | 9 | 12 |
| -- delivered unparsed | 1 | 1 |
| delivered correct given Perception rank 1 / 2 / 3+ / off list | 904/913 (99.01 %) / 18/69 (26.09 %) / 2/22 (9.09 %) / 1/76 (1.32 %) | 797/810 (98.40 %) / 15/80 (18.75 %) / 2/27 (7.41 %) / 1/83 (1.20 %) |
| pp intent per Perception rank-1 gain | 0.080 | 0.089 |

Fields: `perc_rank` (rank of the gold intent in the sealed Perception note `candidates[].intent_id`), `d_ok`
(official `scenario_action_exact`), `d_parsed`, exactly as `slurp_node_gain_ledger.derive_arm` defines them
(`docs/results/2026-09-28-slurp-node-information-gain-ledger.md`). Reading: the Solver's own intent residual is 9 /
12 rows (about 1 pp); about 93 % of the intent mass is upstream of the Solver (off-list or below rank 1), consistent with
the node gain ledger and re-plan v6 section 1. An R1 (Solver) template should declare intent as a guard, not a
target.

## 6. C3 failure-class contrast table (input to R1 candidate authors)

Solver node (s1), class x value in supply:

| class | Fold A total | E1 | E2 | E3 | none | | DEV total | E1 | E2 | E3 | none |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| SPURIOUS | 264 | 100 | 5 | 27 | 132 | | 245 | 86 | 9 | 23 | 127 |
| MISSING | 188 | 103 | 1 | 14 | 70 | | 187 | 94 | 0 | 14 | 79 |
| WRONG-TYPE | 54 | 14 | 4 | 2 | 34 | | 67 | 21 | 4 | 2 | 40 |
| BOUNDARY | 68 | 29 | 0 | 1 | 38 | | 74 | 27 | 1 | 1 | 45 |
| NEAR | 57 | 19 | 0 | 0 | 38 | | 36 | 7 | 0 | 0 | 29 |
| WRONG-VALUE | 42 | 8 | 1 | 0 | 33 | | 47 | 10 | 0 | 0 | 37 |
| FORMAT | 40 | 14 | 0 | 1 | 25 | | 44 | 15 | 0 | 0 | 29 |
| EMPTY-GOLD-FILL (rows) | 161 | | | | | | 138 | | | | |
| PARSE-FAIL (rows) | 1 | | | | | | 1 | | | | |

Solver node (s1), class x request structure (first-Solver prompt tokens, pool quartiles; rows per bin in brackets):

| class | Fold A Q1 (270) | Q2 (270) | Q3 (270) | Q4 (270) | | DEV Q1 (250) | Q2 (250) | Q3 (250) | Q4 (250) |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| SPURIOUS | 51 | 59 | 69 | 85 | | 60 | 46 | 57 | 82 |
| MISSING | 37 | 44 | 50 | 57 | | 38 | 43 | 52 | 54 |
| WRONG-TYPE | 7 | 16 | 11 | 20 | | 9 | 16 | 25 | 17 |
| BOUNDARY | 14 | 18 | 14 | 22 | | 14 | 16 | 28 | 16 |
| NEAR | 13 | 15 | 10 | 19 | | 8 | 11 | 7 | 10 |
| WRONG-VALUE | 9 | 16 | 8 | 9 | | 18 | 12 | 5 | 12 |
| FORMAT | 8 | 9 | 14 | 9 | | 9 | 8 | 12 | 15 |
| EMPTY-GOLD-FILL | 36 | 37 | 45 | 43 | | 41 | 27 | 24 | 46 |

Quartile cuts: Fold A 9,568.75 / 10,817 / 11,948.5 tokens (mean 10,486); DEV 10,301.75 / 11,532.5 / 12,090.25 (mean
11,038). Supplied-item bins (pool quartiles of `supplied_evidence` length; Fold A cuts 39 / 42 / 45, mean 41.6; DEV
41 / 44 / 46, mean 43.1) show no monotone trend (`tables.md`). Fixed structure at the first Solver contact on both
pools: history 2 entries (Perception note + control), 8 boundary items (1,078 / 1,080; 1,000 / 1,000), 1-25 slot
cards, tool schemas 0, response_format none, tool_choice none, max_tokens 512, finish `stop` on every contact, 0
completions at the token cap.

Top types per class at s1: SPURIOUS Fold A food_type 20, event_name 16, device_type 15, place_name 14,
business_name 14; DEV definition_word 28, person 25, event_name 23, place_name 16. MISSING Fold A date 46,
place_name 17, order_type 15, transport_type 14; DEV date 43, event_name 25, media_type 17, player_setting 14. The
full cube (class x type x supply x prompt bin x supplied bin, counts only) is `report.json`
`pools.<pool>.contrast.<s1|d>.cube`; the delivered-node tables are in `tables.md`.

Readings for candidate authors (descriptive, not causal):

1. **MISSING is mostly a consumption failure:** 103 / 188 (Fold A) and 94 / 187 (DEV) missing gold values are printed
   with their type in the row's own exemplars (E1), 14 more are named by a delivered card (E3). This is the R1
   "value-in-supply" mass.
2. **SPURIOUS is often supply-shaped:** 100 / 264 and 86 / 245 spurious (type, value) pairs are printed in the
   row's exemplars (E1) -- consistent with copying an exemplar's slot onto an utterance that does not carry it. A
   template that pushes harder toward "use the supply" should declare this class as its harm guard.
3. **Empty-gold false fill is the largest single row mass** (161 / 414, 138 / 314 = 39-44 % of empty-gold rows) at
   0.033 pp per row; emptying all of them is a +4.8-5.9 pp oracle.
4. **Errors grow with prompt length** (SPURIOUS Q1 -> Q4 51 -> 85 and 60 -> 82; MISSING 37 -> 57 and 38 -> 54).
   Prompt length is confounded with the number of gold entities and of delivered cards; do not read it as a
   context-length effect without a within-row contrast.

## 7. Exact commands

```bash
# WSL Ubuntu-24.04, from the study worktree (branch fable/nx-exchange, base e5adeb3b2)
cd /home/chao/saea-worktrees/fable-nx-exchange
source ~/.venvs/speechrl/bin/activate
export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_nx_exchange_rates.py \
    --data-root "$SPEECHRL_DATA_DIR" \
    --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_nx_exchange_rates.py \
    --data-root "$SPEECHRL_DATA_DIR" \
    --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json --check
# -> check: IDENTICAL apart from generated_at
```

Wall time about 85 s (two 400 MB trace streams). Driver hashes are recorded in `report.json` (`drivers`).

## 8. Limits

- Development pools, repeatedly exposed (Fold A by COMP-1b and its siblings; DEV-2000-ADDED by A2 and its A/A).
  The rates are properties of the COMP-1b graph and its pools; a round on another base (review-off, R0.1) should
  re-run this script on that base's sealed bytes before citing them.
- The node rate assumes the measured raw -> delivered transfer for newly exact rows. On a review-off base, where
  only the deliver normaliser sits between Solver and delivery, the transfer should be at least as tight.
- Supply classes are lexical (folded exact value in printed exemplar pairs or a word-bounded card match); they say
  the value was visible in the supplied knowledge, not that the model attended to it.
