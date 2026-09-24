# Where the first out-of-fold loss of the Stage-3 delta line sits

Model-free diagnostic of cell CELL-3 (`SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-V1`) against the sealed DEV-2000-ADDED PLAN arm, with the request-identical replicate PLANr as the roster's own null.

- recipe `slurp-cell3-fresh-roster-loss-diagnostic-v1`, run id `SAEA-SLURP-CELL3-FRESH-ROSTER-LOSS-DIAGNOSTIC-V1`
- generated 2026-09-24T17:16:24.285943+00:00
- contacts: model 0, tokenizer 0, encoder 0, scorer 0
- roster `SLURP-DEV-2000-ADDED-V1` (1000 rows, split role `dev`, identity `ee6c43cd4dd8`)

LABELS, IDS, COUNTS AND HASHES ONLY. No utterance text, transcript, delivered text, gold filler or statement content appears here. The SLURP devel gold is a scoring input read offline; it appears only in aggregate counts.

## Status

**DESCRIPTIVE.** No admission, superiority or generalisation verdict is read here (owner decisions 28 and 86: DEV-2000-ADDED is a development roster and development numbers carry no bar). This read explains WHERE an already-published loss sits.

## Arms

| key | label | run id | attempt | official SLU-F1 | official intent |
| --- | --- | --- | --- | ---: | ---: |
| plan | PLAN (sealed DEV-2000-ADDED comparator) | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1` | `attempt-slurp-native-default-plan-dev2000-added-generation-v1` | 65.40 | 76.60 |
| cell3 | CELL-3 (gated stage3-deltas-v2) | `SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-V1` | `attempt-slurp-native-stage3-delta-cell-r03-gate-v1-generation` | 63.95 | 76.60 |
| planr | PLANr (request-identical replicate) | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-REPLICATE-V1` | `attempt-slurp-native-default-plan-dev2000-added-replicate-generation-v1` | 65.15 | 76.80 |

## 1. Where the rows are, and where the loss is

The three splits are decided from CELL-3's OWN sealed receipts: a row is GATED when every `delta_scenario_gate` decision it carries is CLOSED and no node received a single delta value (the row therefore ran in bare PLAN form, on byte-identical prompts); SUPPLIED when any node received delta values; OPEN-NO-SUPPLY when the gate opened but the store's node slice matched nothing the row's candidates named.

| split | rows | share |
| --- | ---: | ---: |
| gated | 355 | 35.5 % |
| supplied | 568 | 56.8 % |
| open_no_supply | 77 | 7.7 % |
| all | 1000 | 100.0 % |

### 1a. Pooled micro (official count fields), per split

| split | rows | arm | SLU-F1 % | TP | FP | FN | span-F1 % | span TP | span FP | span FN | intent exact % | mean row SLU % | entities emitted |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| gated | 355 | plan | 60.96 | 448.0 | 305.9 | 267.9 | 51.14 | 168 | 170 | 151 | 74.65 | 43.19 | 338 |
| gated | 355 | cell3 | 58.76 | 434.0 | 322.6 | 286.6 | 48.78 | 160 | 177 | 159 | 74.65 | 41.58 | 337 |
| gated | 355 | planr | 61.57 | 462.0 | 321.3 | 255.3 | 51.86 | 174 | 178 | 145 | 75.77 | 43.93 | 352 |
| supplied | 568 | plan | 66.95 | 936.0 | 494.1 | 430.1 | 59.09 | 377 | 277 | 245 | 76.06 | 49.20 | 654 |
| supplied | 568 | cell3 | 65.33 | 950.0 | 568.0 | 440.0 | 56.42 | 369 | 317 | 253 | 76.41 | 49.22 | 686 |
| supplied | 568 | planr | 65.69 | 936.0 | 527.9 | 449.9 | 57.52 | 369 | 292 | 253 | 75.70 | 48.82 | 661 |
| open_no_supply | 77 | plan | 71.11 | 136.0 | 57.3 | 53.3 | 64.37 | 56 | 32 | 30 | 89.61 | 52.87 | 88 |
| open_no_supply | 77 | cell3 | 73.58 | 140.0 | 52.3 | 48.3 | 66.67 | 58 | 30 | 28 | 87.01 | 55.49 | 88 |
| open_no_supply | 77 | planr | 74.95 | 146.0 | 54.8 | 42.8 | 68.54 | 61 | 31 | 25 | 89.61 | 55.50 | 92 |
| all | 1000 | plan | 65.40 | 1520.0 | 857.3 | 751.3 | 57.05 | 601 | 479 | 426 | 76.60 | 47.35 | 1080 |
| all | 1000 | cell3 | 63.95 | 1524.0 | 942.9 | 774.9 | 54.91 | 587 | 524 | 440 | 76.60 | 46.99 | 1111 |
| all | 1000 | planr | 65.15 | 1544.0 | 904.0 | 748.0 | 56.66 | 604 | 501 | 423 | 76.80 | 47.60 | 1105 |

### 1b. The two paired contrasts, per split

| pair | split | rows | pooled SLU delta pp | CI95 pp | pooled span delta pp | per-row SLU mean pp | saves | harms | intent mean pp |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| PLAN -> CELL-3 | gated | 355 | -2.20 | [-4.38, -0.03] | -2.36 | -1.61 | 11 | 21 | 0.00 |
| PLAN -> CELL-3 | supplied | 568 | -1.61 | [-3.46, 0.28] | -2.67 | 0.02 | 40 | 45 | 0.35 |
| PLAN -> CELL-3 | open_no_supply | 77 | 2.47 | [-4.40, 9.16] | 2.30 | 2.62 | 6 | 3 | -2.60 |
| PLAN -> CELL-3 | all | 1000 | -1.44 | [-2.88, -0.05] | -2.14 | -0.36 | 57 | 69 | 0.00 |
| PLAN -> PLANr (own null) | gated | 355 | 0.61 | [-1.45, 2.69] | 0.72 | 0.74 | 20 | 13 | 1.13 |
| PLAN -> PLANr (own null) | supplied | 568 | -1.26 | [-2.79, 0.25] | -1.57 | -0.38 | 28 | 32 | -0.35 |
| PLAN -> PLANr (own null) | open_no_supply | 77 | 3.85 | [-2.05, 10.00] | 4.17 | 2.64 | 5 | 3 | 0.00 |
| PLAN -> PLANr (own null) | all | 1000 | -0.25 | [-1.52, 0.98] | -0.39 | 0.25 | 53 | 48 | 0.20 |

### 1c. Entity FP and FN mass by slot TYPE, per split (top 12 by arm FP)

**gated** (355 rows)

| slot type | PLAN FP | CELL-3 FP | PLANr FP | PLAN FN | CELL-3 FN | PLANr FN | FP delta (CELL-3 - PLAN) | FN delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| media_type | 13 | 12 | 15 | 14 | 19 | 13 | -1 | +5 |
| radio_name | 10 | 13 | 14 | 9 | 9 | 10 | +3 | +0 |
| device_type | 14 | 14 | 11 | 7 | 7 | 7 | +0 | +0 |
| artist_name | 9 | 9 | 7 | 10 | 11 | 9 | +0 | +1 |
| player_setting | 11 | 9 | 11 | 10 | 11 | 11 | -2 | +1 |
| date | 4 | 3 | 3 | 16 | 16 | 13 | -1 | +0 |
| joke_type | 14 | 13 | 12 | 3 | 4 | 2 | -1 | +1 |
| song_name | 7 | 6 | 6 | 10 | 10 | 10 | -1 | +0 |
| person | 7 | 7 | 9 | 7 | 8 | 8 | +0 | +1 |
| playlist_name | 10 | 12 | 11 | 2 | 3 | 4 | +2 | +1 |
| audiobook_name | 5 | 5 | 5 | 7 | 7 | 7 | +0 | +0 |
| news_topic | 8 | 7 | 8 | 4 | 5 | 4 | -1 | +1 |

Totals on this split: PLAN FP 170 / FN 151; CELL-3 FP 177 / FN 159; PLANr FP 178 / FN 145. Gold entities 319.

**supplied** (568 rows)

| slot type | PLAN FP | CELL-3 FP | PLANr FP | PLAN FN | CELL-3 FN | PLANr FN | FP delta (CELL-3 - PLAN) | FN delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| date | 32 | 61 | 36 | 51 | 52 | 53 | +29 | +1 |
| event_name | 39 | 46 | 43 | 43 | 38 | 44 | +7 | -5 |
| person | 46 | 39 | 52 | 28 | 28 | 29 | -7 | +0 |
| place_name | 24 | 28 | 22 | 16 | 22 | 17 | +4 | +6 |
| time | 14 | 17 | 13 | 15 | 18 | 17 | +3 | +3 |
| weather_descriptor | 10 | 14 | 10 | 12 | 14 | 13 | +4 | +2 |
| definition_word | 22 | 22 | 25 | 4 | 4 | 4 | +0 | +0 |
| currency_name | 11 | 11 | 13 | 6 | 6 | 7 | +0 | +0 |
| relation | 3 | 4 | 5 | 13 | 10 | 13 | +1 | -3 |
| business_name | 5 | 7 | 3 | 6 | 6 | 7 | +2 | +0 |
| timeofday | 8 | 4 | 6 | 7 | 9 | 6 | -4 | +2 |
| general_frequency | 8 | 7 | 9 | 4 | 4 | 4 | -1 | +0 |

Totals on this split: PLAN FP 277 / FN 245; CELL-3 FP 317 / FN 253; PLANr FP 292 / FN 253. Gold entities 622.

## 2. Per supplied value id: concentrated or diffuse?

120 distinct value ids reached the 568 supplied rows. Total harm mass 16822.95 pp, total save mass 18278.15 pp (a row is counted once per value it received, so these masses over-count the roster and are a RANKING, not a budget).

| cut | share of harm mass |
| --- | ---: |
| top 1 share of harm mass | 3.5 % |
| top 3 share of harm mass | 8.9 % |
| top 5 share of harm mass | 14.3 % |
| top 10 share of harm mass | 26.3 % |
| top 20 share of harm mass | 45.6 % |
| top 40 share of harm mass | 76.0 % |

Top 20 value ids by harm mass:

| value id | node(s) | kind | slot target | target intents | rows | SLU mean pp | saves | harms | harm mass pp | net mass pp | Fold A rows | Fold A SLU mean pp |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `delta:1:958bfd7950e2` | reviewer | reviewer-criterion | entities | audio_volume_up, calendar_query +1 | 210 | -0.34 | 13 | 16 | 593.34 | -71.82 | 234 | 1.25 |
| `delta:1:54d15c58d173` | solver | slot-contract | date | weather_query | 105 | 1.29 | 10 | 12 | 451.10 | 134.96 | 101 | 7.43 |
| `delta:1:5c4d27a08099` | reviewer | reviewer-criterion | weather | weather_query | 105 | 1.29 | 10 | 12 | 451.10 | 134.96 | 101 | 7.43 |
| `delta:1:637b0e28eb4a` | solver | slot-contract | time | weather_query | 105 | 1.29 | 10 | 12 | 451.10 | 134.96 | 101 | 7.43 |
| `delta:1:68dd85055eaa` | reviewer | reviewer-criterion | weather | weather_query | 105 | 1.29 | 10 | 12 | 451.10 | 134.96 | 101 | 7.43 |
| `delta:1:9c0749f97ac8` | solver | slot-contract | time | weather_query | 105 | 1.29 | 10 | 12 | 451.10 | 134.96 | 101 | 7.43 |
| `delta:1:d0964f759989` | solver | slot-contract | weather_descriptor | weather_query | 105 | 1.29 | 10 | 12 | 451.10 | 134.96 | 101 | 7.43 |
| `delta:1:69f526953cd6` | reviewer | reviewer-criterion | weather_query | weather_query | 96 | 0.28 | 8 | 11 | 439.82 | 26.84 | 95 | 7.20 |
| `delta:1:5585ac9178cd` | solver | exemplar-note | weather_descriptor | weather_query | 102 | 2.30 | 10 | 11 | 351.10 | 234.96 | 98 | 7.32 |
| `delta:1:22caefef992f` | solver | slot-contract | date | calendar_set | 101 | 0.20 | 14 | 14 | 335.46 | 20.30 | 43 | 2.17 |
| `delta:1:a9deafd419a0` | solver | slot-contract | calendar_set | calendar_set | 100 | 0.20 | 14 | 14 | 335.46 | 20.30 | 43 | 2.17 |
| `delta:1:a9f49407e1bd` | reviewer | reviewer-criterion | calendar_set | calendar_set | 100 | 0.20 | 14 | 14 | 335.46 | 20.30 | 43 | 2.17 |
| `delta:1:bfaf2c2cd13a` | solver | slot-contract | event_name | calendar_set | 101 | 0.20 | 14 | 14 | 335.46 | 20.30 | 43 | 2.17 |
| `delta:1:96f7d0a8a52c` | solver | slot-contract | place_name | calendar_set | 97 | 0.30 | 13 | 13 | 326.49 | 28.74 | 36 | 1.57 |
| `delta:1:e0966c32c303` | solver | slot-contract | calendar | calendar_set | 99 | 0.30 | 14 | 13 | 326.49 | 29.27 | 40 | 1.41 |
| `delta:1:0176eda98802` | solver | slot-contract | datetime | datetime_query | 71 | 0.15 | 4 | 7 | 322.36 | 10.97 | 113 | 5.52 |
| `delta:1:9beed9d9f733` | solver | slot-contract | datetime_query.entities | datetime_query | 71 | 0.15 | 4 | 7 | 322.36 | 10.97 | 113 | 5.52 |
| `delta:1:adfed32ac1ca` | reviewer | reviewer-criterion | datetime_query.entities | datetime_query | 71 | 0.15 | 4 | 7 | 322.36 | 10.97 | 113 | 5.52 |
| `delta:1:d1c93189ba0c` | solver | slot-contract | transport_query | qa_factoid, transport_query | 146 | -0.49 | 6 | 6 | 314.79 | -71.65 | 182 | -1.86 |
| `delta:1:4ca5a519402c` | solver | slot-contract | entities | play_music, weather_query | 84 | -0.12 | 5 | 9 | 309.94 | -9.94 | 145 | 5.31 |

### 2a. Transfer from TRAIN Fold A (CELL-2)

| item | value |
| --- | ---: |
| value ids joined to the Fold A read | 117 |
| value ids that only appear here | 3 |
| Fold A winners (mean SLU > 0, >= 10 rows there) | 86 |
| their mean per-row SLU delta on DEV-2000-ADDED | 0.33 pp |
| of those, negative on DEV-2000-ADDED | 37 |
| Fold A losers (mean SLU < 0, >= 10 rows there) | 26 |
| their mean per-row SLU delta on DEV-2000-ADDED | 0.99 pp |
| sign agreement across the two venues | 49 of 96 |

## 3. The entity side of the supplied rows

| item | PLAN | CELL-3 | delta |
| --- | ---: | ---: | ---: |
| entities emitted | 654 | 686 | +32 |

Rows emitting more: 64; fewer: 37; same: 467. Rows that ADDED an exact-match FP: 63 (11.1 % of supplied rows); rows that added an FN: 31.

| slot type | FP delta | FN delta | TP delta |
| --- | ---: | ---: | ---: |
| date | +29 | +1 | -1 |
| place_name | +4 | +6 | -6 |
| time | +3 | +3 | -3 |
| weather_descriptor | +4 | +2 | -2 |
| meal_type | +0 | +4 | -4 |
| business_name | +2 | +0 | +0 |
| device_type | +2 | +0 | +0 |
| event_name | +7 | -5 | +5 |
| food_type | +2 | +0 | +0 |
| time_zone | +2 | +0 | +0 |
| business_type | +1 | +0 | +0 |
| ingredient | +1 | +0 | +0 |
| order_type | +1 | +0 | +0 |
| player_setting | +0 | +1 | -1 |
| audiobook_name | +0 | +0 | +0 |

Which delta KIND sat on the rows that added an FP (against its own reach):

| delta kind | rows reached | rows with added FP | rate |
| --- | ---: | ---: | ---: |
| exemplar-note | 102 | 17 | 16.7 % |
| reviewer-criterion | 484 | 59 | 12.2 % |
| slot-contract | 541 | 59 | 10.9 % |
| planner-rule | 96 | 10 | 10.4 % |

| supplied node | rows reached | rows with added FP | rate |
| --- | ---: | ---: | ---: |
| reviewer | 484 | 59 | 12.2 % |
| solver | 541 | 59 | 10.9 % |
| planner | 96 | 10 | 10.4 % |

And, for the slot types that gained the most FP, which delta (kind, slot target) sat on the rows that gained them -- only targets reaching at least 10 rows:

| slot type gaining FP | FP delta | rows that gained it | delta kind | delta target | rows reached | rows that gained | rate |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: |
| date | +29 | 32 | reviewer-criterion | scenario:email | 55 | 8 | 14.5 % |
| date | +29 | 32 | slot-contract | sendemail.date | 56 | 8 | 14.3 % |
| date | +29 | 32 | reviewer-criterion | relation | 53 | 7 | 13.2 % |
| date | +29 | 32 | slot-contract | relation | 54 | 7 | 13.0 % |
| date | +29 | 32 | reviewer-criterion | calendar_set | 100 | 12 | 12.0 % |
| date | +29 | 32 | slot-contract | calendar_set | 100 | 12 | 12.0 % |
| place_name | +4 | 10 | slot-contract | food_type | 10 | 1 | 10.0 % |
| place_name | +4 | 10 | reviewer-criterion | order_type | 13 | 1 | 7.7 % |
| place_name | +4 | 10 | slot-contract | transport_descriptor | 40 | 3 | 7.5 % |
| place_name | +4 | 10 | slot-contract | business_name | 14 | 1 | 7.1 % |
| place_name | +4 | 10 | slot-contract | takeaway_query | 14 | 1 | 7.1 % |
| place_name | +4 | 10 | planner-rule | takeaway_order | 15 | 1 | 6.7 % |
| time | +3 | 8 | slot-contract | transport_descriptor | 40 | 2 | 5.0 % |
| time | +3 | 8 | reviewer-criterion | place_name | 22 | 1 | 4.5 % |
| time | +3 | 8 | slot-contract | transport_name | 53 | 2 | 3.8 % |
| time | +3 | 8 | reviewer-criterion | recommendation_events | 111 | 4 | 3.6 % |
| time | +3 | 8 | slot-contract | query | 60 | 2 | 3.3 % |
| time | +3 | 8 | reviewer-criterion | query | 61 | 2 | 3.3 % |
| weather_descriptor | +4 | 6 | slot-contract | weather_query | 58 | 5 | 8.6 % |
| weather_descriptor | +4 | 6 | reviewer-criterion | weather_query | 96 | 6 | 6.2 % |
| weather_descriptor | +4 | 6 | exemplar-note | weather_descriptor | 102 | 6 | 5.9 % |
| weather_descriptor | +4 | 6 | reviewer-criterion | weather | 105 | 6 | 5.7 % |
| weather_descriptor | +4 | 6 | slot-contract | weather_descriptor | 105 | 6 | 5.7 % |
| weather_descriptor | +4 | 6 | slot-contract | time | 175 | 6 | 3.4 % |

## 4. Perception, and how stable the gate is

CELL-3 removed the Perception unconditional route, so Perception runs on prompts byte-identical to PLAN's. It is NOT byte-identical in output: greedy decoding is not reproducible across batch compositions, and PLANr shows the same spread.

| pair | identical ordered candidate list | identical set | identical top candidate |
| --- | ---: | ---: | ---: |
| plan vs cell3 | 656 (65.6 %) | 702 (70.2 %) | 965 (96.5 %) |
| plan vs planr | 649 (64.9 %) | 704 (70.4 %) | 960 (96.0 %) |
| cell3 vs planr | 690 (69.0 %) | 732 (73.2 %) | 963 (96.3 %) |

Validation: replaying `rails.stage3_delta_supply.ScenarioGate` over CELL-3's own first Perception candidate list reproduces the receipted decision on 1000 of 1000 rows (100.00 %), with 0 mismatches -- so the counterfactual below runs the flown gate, not a paraphrase.

| candidates the gate is taken on | closed | differs from the flown decision | share |
| --- | ---: | ---: | ---: |
| plan | 355 | 22 | 2.2 % |
| planr | 348 | 23 | 2.3 % |

(The flown gate closed on 355 rows at the Solver, the first gated node.)

## 5. Bounds: store harm against run-to-run noise

| arm / counterfactual | pooled SLU-F1 % | pooled span-F1 % | intent exact % | delta vs PLAN pp |
| --- | ---: | ---: | ---: | ---: |
| PLAN as flown | 65.40 | 57.05 | 76.60 | 0.00 |
| CELL-3 as flown | 63.95 | 54.91 | 76.60 | -1.44 |
| PLANr as flown | 65.15 | 56.66 | 76.80 | -0.25 |
| perfect gate | 64.89 | 56.51 | 76.40 | -0.51 |
| gated rows re-drawn | 64.81 | 55.83 | 77.00 | -0.58 |
| perfect gate AND gated rows re-drawn | 65.76 | 57.43 | 76.80 | 0.37 |
| CELL-3 only where it supplied | 64.45 | 55.45 | 76.80 | -0.95 |
| CELL-3 only on the gated rows | 64.69 | 56.32 | 76.60 | -0.71 |
| CELL-3 only on the open-no-supply rows | 65.60 | 57.24 | 76.40 | 0.20 |

- **perfect gate**: every SUPPLIED row replaced by its PLAN outcome; CELL-3 kept elsewhere.
- **gated rows re-drawn**: every GATED row replaced by PLANr's outcome; CELL-3 kept elsewhere.
- **perfect gate AND gated rows re-drawn**: SUPPLIED rows from PLAN and GATED rows from PLANr; CELL-3 only on the 77 open-no-supply rows -- the most favourable reading this store admits.
- **CELL-3 only where it supplied**: PLAN everywhere except the SUPPLIED rows.
- **CELL-3 only on the gated rows**: PLAN everywhere except the GATED rows -- pure decode noise.
- **CELL-3 only on the open-no-supply rows**: PLAN everywhere except the OPEN-NO-SUPPLY rows -- pure decode noise.

Perfect-gate bound against PLAN, paired whole-cluster bootstrap (seed 20260915, 10000 draws): -0.51 pp [-1.40, 0.37].

## 6. Ranked root cause

| rank | split | rows | contribution to the whole-roster pooled SLU delta pp | within-split arm delta pp | within-split own-null delta pp | arm minus null pp |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | supplied | 568 | -0.95 | -1.61 | -1.26 | -0.35 |
| 2 | gated | 355 | -0.71 | -2.20 | 0.61 | -2.81 |
| 3 | open_no_supply | 77 | 0.20 | 2.47 | 3.85 | -1.37 |

**Ranked root cause.** (1) **The store, where it is applied, is the first cause, and it is small.** On the 568 SUPPLIED rows the arm moves pooled SLU-F1 by -1.61 pp and span-F1 by -2.67 pp, but the own null moves the SAME rows by -1.26 pp, so the part attributable to the store is arm minus null = -0.35 pp; the per-row mean there is 0.02 pp (40 saves against 45 harms), i.e. flat. Its visible signature is on the ENTITY side and is a precision cost: +32 entities emitted, span FP 277 -> 317 with FN essentially unchanged, on 63 rows. (2) **Half of the published loss is not the store at all.** On the 355 GATED rows CELL-3 ran on byte-identical prompts -- no delta reached any node -- so nothing there can be a store effect by construction; yet the arm reads -2.20 pp on that split while the request-identical replicate reads 0.61 pp on the same rows. That 2.81 pp spread between two decode realisations of the identical request bounds what a 355-row split can say, and it carries -0.71 pp of the -1.44 pp whole-roster delta. (3) **The harm is diffuse, not a few bad statements.** Across 120 supplied value ids the ten worst carry only 26.3 % of the harm mass, and no value id reaches a harm concentration that a pruning rule could cut. (4) **Fold A does not transfer.** Of 86 Fold A winners, 37 are negative here and their DEV mean is 0.33 pp -- LOWER than the 26 Fold A losers' 0.99 pp; sign agreement is 49 of 96, i.e. a coin toss. The Fold A per-value ranking is fitted noise. (5) **The gate is stable enough not to be the cause.** Taken on the PLAN arm's own Perception candidates, only 2.2 % of the flown open/closed decisions flip, even though the candidate lists agree exactly on 65.6 % of rows and on the top candidate on 96.5 % -- the majority-scenario rule absorbs the reordering. **Implication for the line.** The bound answers the headroom question directly. If the gate were an ORACLE and every supplied row fell back to PLAN, the roster lands at 64.89 % (-0.51 pp vs PLAN); and with the gated rows additionally re-drawn from PLANr it lands at 65.76 % (0.37 pp) -- both inside the roster's own null band [-1.52, 0.98] pp. So the best an application policy over THIS store can achieve on a fresh roster is to stop doing harm, never to add a gain: an oracle gate buys back the loss and nothing more, while the supply still costs 1773 prompt tokens and 0.087 GPU-h per 1,000 rows. No gating, re-ranking or capping of this store has headroom here; the next move belongs to the store's CONSTRUCTION (what the statements say and which rows they are built from), not to its application.

## Provenance

| artefact | sha256 |
| --- | --- |
| cell2.delta-consumption | `1e106ddfcd1cb0fed8461adafbffba7b72634ecad88771d4c8064b5159e3c58f` |
| cell3.efficiency | `78bb9ce800cce909f95105f3a2aca7d17f380a680477e35dbc3be753411dfc74` |
| cell3.flight-receipts | `f76bab736b36d472871d8298d90de7c787d0c45c9ffaa2b83c45f6e06cf2aca4` |
| cell3.outputs | `8a66dba76c56d810d0d02a5d6f28042c49fca28815ae52e2a1af5f4c3809c6dc` |
| cell3.phases | `a866f3775389529ec0adc02b18a5b8d8fb8f4621b6c10005a8f48d22a3ba00b3` |
| cell3.scores | `354ff83c237ee09585e82f96eac48ab5a55080c358cb7878f8d6e294435169b0` |
| driver | `90fbaf0525c94f5b2ee750077c647478523ee502d93d663f853d45e2ff05ba4a` |
| gold.devel-metadata | `00d346b183ecc2d160853cd3dc20e8ccd207d9e1809cf6e2c05182076bd0ecc9` |
| plan.outputs | `41ebcea4d13ef779e51cdf6c69a4210194c842886db83e892fa7cc43cf053909` |
| plan.phases | `7853313714c58b434f306ebbc2df7de8b05801feb8695dbee4663dfacae4aed1` |
| plan.scores | `1ac4402afce13528d1c2debab1a468f5399c85ff3c6dc7883cd4d995bd2a2b75` |
| planr.outputs | `674e2c08f362386b07739291c5135f105bc27f684e850ea848fb843d2b63831c` |
| planr.phases | `e01fb224856eb9e4a82397d5d4d60d0656a0a21735f55ff9187cb056d7fc6844` |
| planr.scores | `81ae9b49620f90865c16057b1942c008a8a2fdd30035ea24252a4a47794b04c5` |
| roster | `f78dd8ad2894b1fd02bfe6050e39e3fb2c5d178a649e5d20e85ea4ecf4b8dc58` |
| store.snapshot | `f960bc84b920e37030a141a81c182df9c928dc2d3a9b7948ae3c9ac42b878085` |

Caches (counts and labels only): `devel-gold-label-projection.json`, `per-type-exact-counts.json`.

