# The `general` scenario hole on TRAIN Fold A: a model-free diagnostic

Recipe `slurp-general-scenario-diagnostic-v1`, run id `SAEA-SLURP-GENERAL-SCENARIO-DIAGNOSTIC-V1`, generated 2026-09-24T09:08:02.994258+00:00. Produced by `scripts/analysis/slurp_general_scenario_diagnostic.py` from sealed bytes only: **zero model, tokenizer, encoder, ASR, scorer, server and network contacts**. Every number below is reproduced by re-running that script; the per-row join and the full value tables are written beside it under `$SPEECHRL_DATA_DIR/analysis/SLURP-GENERAL-SCENARIO-DIAGNOSTIC-V1/`.

Labels, identifiers and counts only. No utterance text, transcript, gold filler, delivered filler or delta statement text is read into this document. Gold enters exactly as a scorer input and leaves only as label names and counts.

Population: the 60 `general` rows of roster `SLURP-EVO-FOLD-A-V2` (`docs/receipts/rosters/slurp-evo-fold-a-v2.json`, sha256 `1fe7908c3139`), inside the 1080-row TRAIN Fold A discovery split `61b0f0625497`.

## Headline

- The stratum is three labels wide and dominated by `general_quirky` (45 of 60 rows); only 10 rows carry a gold slot, so the `general` number is an INTENT number, not a slot number.
- The derangement twin loses as much as the arms (intent -11.67 pp versus -6.67 for CELL-2 and -10.00 for CELL-1), so the `general` loss is a FORM cost of carrying a delta supply, not the content of any delta.
- No delta content exists for this stratum: 0 of 200 v2 values declare a `general` target and 0 of the values that reached these rows was learned from a `general` source row.
- Candidate crowding is real but does not explain the loss: 1 of the 6 CELL-2 intent losses also lost candidate coverage.
- The whole recoverable amount is small: 10.00 pp intent and 11.16 pp pooled SLU-F1 on the 60 rows, i.e. 0.56 pp and 0.24 pp on Fold A -- iteration 3 should PROTECT this stratum from the supply, not try to win it.

## Sealed inputs

| arm | run id | attempt | outputs sha256 | scores sha256 | store |
| --- | --- | --- | --- | --- | --- |
| PLAN (v2.0 lock) | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1` | `attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1` | `2dcaa925ab7d` | `9f3047fa77a8` | -- |
| CELL-1 (deltas v1r) | `SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1` | `attempt-slurp-native-stage3-delta-cell-r01-v1-generation-recovery-relaunch-2` | `a2e752b876d2` | `1d3e53364c88` | `stage3-deltas-v1r` |
| CELL-2 (deltas v2) | `SAEA-SLURP-STAGE3-DELTA-CELL-R02-V1` | `attempt-slurp-native-stage3-delta-cell-r02-v1-generation` | `f3940b91c4f2` | `375e2fea7873` | `stage3-deltas-v2` |
| CELL-2 twin (deranged) | `SAEA-SLURP-STAGE3-DELTA-CELL-R02-TWIN-V1` | `attempt-slurp-native-stage3-delta-cell-r02-v1-twin` | `14a348af1545` | `09869e67943a` | `stage3-deltas-twin-v2` |

## 1. What the 60 `general` rows are, and where the cells lose

### 1.1 Gold intent distribution (labels only)

| gold intent | rows | share |
| --- | ---: | ---: |
| `general_quirky` | 45 | 75.0 % |
| `general_joke` | 10 | 16.7 % |
| `general_greet` | 5 | 8.3 % |
| **total** | **60** | |

The stratum is not a mixed bag: `general_quirky` alone carries 45 of 60 rows (75.0 %), only 10 of the 60 rows carry any gold slot at all, and the whole stratum is three intent labels wide.

### 1.2 Per-arm level on the 60 rows

| arm | pooled SLU-F1 | pooled span-F1 | intent exact | scenario exact | mean row SLU-F1 | entity TP | entity FP | entity FN | entities emitted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PLAN (v2.0 lock) | 30.23 | 27.45 | 43.33 | 51.67 | 10.68 | 7 | 32 | 5 | 39 |
| CELL-1 (deltas v1r) | 17.86 | 17.86 | 33.33 | 38.33 | 8.33 | 5 | 39 | 7 | 44 |
| CELL-2 (deltas v2) | 19.61 | 19.61 | 36.67 | 45.00 | 7.78 | 5 | 34 | 7 | 39 |
| CELL-2 twin (deranged) | 20.00 | 20.00 | 31.67 | 38.33 | 7.78 | 5 | 33 | 7 | 38 |

Gold slots on these rows total 12. Every arm parses all 60 rows.

### 1.3 Paired against PLAN on the same rows

| arm | pooled SLU-F1 delta | intent delta (pp) | intent saves / harms | row SLU saves / harms | span-F1 delta (pp) |
| --- | ---: | ---: | ---: | ---: | ---: |
| CELL-1 (deltas v1r) | -12.37 | -10.00 | 0 / 6 | 0 / 2 | -1.67 |
| CELL-2 (deltas v2) | -10.62 | -6.67 | 2 / 6 | 1 / 2 | -2.22 |
| CELL-2 twin (deranged) | -10.23 | -11.67 | 0 / 7 | 1 / 2 | -2.22 |

### 1.4 Delivered-intent confusion, per arm

**PLAN (v2.0 lock)** -- delivered scenario mix: `general` 31, `qa` 10, `recommendation` 4, `audio` 3, `news` 3, `cooking` 2, `iot` 2, `music` 2, `play` 1, `transport` 1, `weather` 1

| gold intent | delivered intent | rows |
| --- | --- | ---: |
| `general_greet` | `general_greet` (correct) | 5 |
| `general_joke` | `general_joke` (correct) | 10 |
| `general_quirky` | `general_quirky` (correct) | 11 |
| `general_quirky` | `qa_factoid` | 6 |
| `general_quirky` | `general_joke` | 4 |
| `general_quirky` | `audio_volume_up` | 3 |
| `general_quirky` | `news_query` | 3 |
| `general_quirky` | `qa_definition` | 3 |
| `general_quirky` | `cooking_recipe` | 2 |
| `general_quirky` | `iot_cleaning` | 2 |
| `general_quirky` | `recommendation_movies` | 2 |
| `general_quirky` | `general_greet` | 1 |
| `general_quirky` | `music_likeness` | 1 |
| `general_quirky` | `music_query` | 1 |
| `general_quirky` | `play_game` | 1 |
| `general_quirky` | `qa_currency` | 1 |
| `general_quirky` | `recommendation_events` | 1 |
| `general_quirky` | `recommendation_locations` | 1 |
| `general_quirky` | `transport_taxi` | 1 |
| `general_quirky` | `weather_query` | 1 |

**CELL-1 (deltas v1r)** -- delivered scenario mix: `general` 23, `qa` 15, `iot` 5, `audio` 4, `recommendation` 4, `news` 3, `cooking` 2, `play` 2, `music` 1, `weather` 1

| gold intent | delivered intent | rows |
| --- | --- | ---: |
| `general_greet` | `general_greet` (correct) | 4 |
| `general_greet` | `audio_volume_up` | 1 |
| `general_joke` | `general_joke` (correct) | 9 |
| `general_joke` | `qa_factoid` | 1 |
| `general_quirky` | `qa_factoid` | 8 |
| `general_quirky` | `general_quirky` (correct) | 7 |
| `general_quirky` | `qa_definition` | 4 |
| `general_quirky` | `audio_volume_up` | 3 |
| `general_quirky` | `general_joke` | 3 |
| `general_quirky` | `iot_cleaning` | 3 |
| `general_quirky` | `news_query` | 3 |
| `general_quirky` | `cooking_recipe` | 2 |
| `general_quirky` | `qa_currency` | 2 |
| `general_quirky` | `recommendation_movies` | 2 |
| `general_quirky` | `iot_coffee` | 1 |
| `general_quirky` | `iot_hue_lighton` | 1 |
| `general_quirky` | `music_query` | 1 |
| `general_quirky` | `play_game` | 1 |
| `general_quirky` | `play_radio` | 1 |
| `general_quirky` | `recommendation_events` | 1 |
| `general_quirky` | `recommendation_locations` | 1 |
| `general_quirky` | `weather_query` | 1 |

**CELL-2 (deltas v2)** -- delivered scenario mix: `general` 27, `qa` 13, `iot` 4, `news` 4, `recommendation` 4, `audio` 3, `weather` 2, `cooking` 1, `music` 1, `play` 1

| gold intent | delivered intent | rows |
| --- | --- | ---: |
| `general_greet` | `general_greet` (correct) | 5 |
| `general_joke` | `general_joke` (correct) | 9 |
| `general_joke` | `qa_factoid` | 1 |
| `general_quirky` | `general_quirky` (correct) | 8 |
| `general_quirky` | `qa_factoid` | 7 |
| `general_quirky` | `news_query` | 4 |
| `general_quirky` | `qa_definition` | 4 |
| `general_quirky` | `general_joke` | 3 |
| `general_quirky` | `iot_cleaning` | 3 |
| `general_quirky` | `audio_volume_up` | 2 |
| `general_quirky` | `general_greet` | 2 |
| `general_quirky` | `recommendation_movies` | 2 |
| `general_quirky` | `weather_query` | 2 |
| `general_quirky` | `audio_volume_mute` | 1 |
| `general_quirky` | `cooking_recipe` | 1 |
| `general_quirky` | `iot_coffee` | 1 |
| `general_quirky` | `music_query` | 1 |
| `general_quirky` | `play_game` | 1 |
| `general_quirky` | `qa_maths` | 1 |
| `general_quirky` | `recommendation_events` | 1 |
| `general_quirky` | `recommendation_locations` | 1 |

**CELL-2 twin (deranged)** -- delivered scenario mix: `general` 23, `qa` 15, `audio` 4, `recommendation` 4, `iot` 3, `play` 3, `cooking` 2, `news` 2, `weather` 2, `alarm` 1, `music` 1

| gold intent | delivered intent | rows |
| --- | --- | ---: |
| `general_greet` | `general_greet` (correct) | 4 |
| `general_greet` | `audio_volume_up` | 1 |
| `general_joke` | `general_joke` (correct) | 9 |
| `general_joke` | `qa_factoid` | 1 |
| `general_quirky` | `qa_factoid` | 9 |
| `general_quirky` | `general_quirky` (correct) | 6 |
| `general_quirky` | `qa_definition` | 5 |
| `general_quirky` | `audio_volume_up` | 3 |
| `general_quirky` | `general_joke` | 3 |
| `general_quirky` | `cooking_recipe` | 2 |
| `general_quirky` | `iot_cleaning` | 2 |
| `general_quirky` | `news_query` | 2 |
| `general_quirky` | `recommendation_movies` | 2 |
| `general_quirky` | `weather_query` | 2 |
| `general_quirky` | `alarm_query` | 1 |
| `general_quirky` | `general_greet` | 1 |
| `general_quirky` | `iot_coffee` | 1 |
| `general_quirky` | `music_query` | 1 |
| `general_quirky` | `play_game` | 1 |
| `general_quirky` | `play_podcasts` | 1 |
| `general_quirky` | `play_radio` | 1 |
| `general_quirky` | `recommendation_events` | 1 |
| `general_quirky` | `recommendation_locations` | 1 |

Loss attribution: the entity side is nearly inert on this stratum -- PLAN emits 39 entities against 12 gold slots, CELL-2 emits 39 and CELL-1 44, moving exact-match FP from 32 to 34 and 39. The pooled SLU-F1 gap is therefore carried by the label half of the metric: `general_quirky` flips out of `general_*`, mostly into `qa_*`.

## 2. Perception candidate coverage of the gold intent

| arm | gold intent among candidates | candidate slots / row | slots spent on `general_*` | rows with any `general_*` candidate |
| --- | ---: | ---: | ---: | ---: |
| PLAN (v2.0 lock) | 25 / 60 (41.7 %) | 2.87 | 48 | 35 |
| CELL-1 (deltas v1r) | 22 / 60 (36.7 %) | 2.90 | 40 | 33 |
| CELL-2 (deltas v2) | 23 / 60 (38.3 %) | 2.85 | 46 | 34 |
| CELL-2 twin (deranged) | 22 / 60 (36.7 %) | 2.77 | 42 | 34 |

| arm vs PLAN | coverage lost | coverage gained | coverage unchanged | rows losing intent | coverage-loss AND intent-loss | intent loss with coverage intact |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CELL-1 (deltas v1r) | 6 | 3 | 51 | 6 | 4 | 2 |
| CELL-2 (deltas v2) | 3 | 1 | 56 | 6 | 1 | 5 |
| CELL-2 twin (deranged) | 5 | 2 | 53 | 7 | 3 | 4 |

The last two columns are the discriminator: coverage loss and answer loss are largely different rows (CELL-1 (deltas v1r) 4 of 6 intent losses also lost coverage; CELL-2 (deltas v2) 1 of 6 intent losses also lost coverage; CELL-2 twin (deranged) 3 of 7 intent losses also lost coverage). Crowding is a real contributing channel in CELL-1 and a minor one in CELL-2, but in no arm does it account for the whole loss.

The unconditional Perception seed is the same four `intent-boundary` values on every row of every arm: CELL-1 (deltas v1r) `delta:1:0098d11d2d55` -> `perception:intent-boundary:scenario`, `delta:1:2705faddd09d` -> `perception:intent-boundary:recommendation_locations`, `delta:1:458b1eb85929` -> `perception:intent-boundary:calendar_query`, `delta:1:4bc644592b9f` -> `perception:intent-boundary:scenario:email`; CELL-2 (deltas v2) `delta:1:0098d11d2d55` -> `perception:intent-boundary:scenario`, `delta:1:2705faddd09d` -> `perception:intent-boundary:recommendation_locations`, `delta:1:458b1eb85929` -> `perception:intent-boundary:calendar_query`, `delta:1:4bc644592b9f` -> `perception:intent-boundary:scenario:email`; CELL-2 twin (deranged) `delta:1:0098d11d2d55` -> `perception:intent-boundary:weather_query`, `delta:1:2705faddd09d` -> `perception:intent-boundary:calendar_query`, `delta:1:458b1eb85929` -> `perception:intent-boundary:qa_factoid`, `delta:1:4bc644592b9f` -> `perception:intent-boundary:lists_createoradd`. None of them targets `general_*` in any arm.

Candidate scenario mix on these rows (PLAN): `general` 48, `qa` 39, `audio` 15, `music` 13, `recommendation` 13, `play` 11, `iot` 8, `weather` 8, `news` 4, `takeaway` 4.

## 3. Which deltas reached the 60 rows, and what they did there

### 3.1 CELL-1 (deltas v1r)

Store `stage3-deltas-v1r` holds 379 values; 106 distinct values reached at least one `general` row. Values whose declared target names `general`: 1. Values whose own source rows are `general`: 2.

| node | rows supplied | distinct values | intent saves / harms on supplied | mean intent delta, supplied | mean intent delta, NOT supplied | mean row SLU delta, supplied | mean row SLU delta, NOT supplied |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| perception | 60 | 4 | 0 / 6 | -10.00 | -- | -2.34 | -- |
| solver | 48 | 62 | 0 / 5 | -10.42 | -8.33 | -2.93 | 0.00 |
| reviewer | 54 | 34 | 0 / 6 | -11.11 | 0.00 | -2.60 | 0.00 |
| planner | 24 | 6 | 0 / 3 | -12.50 | -8.33 | -1.69 | -2.78 |

The `NOT supplied` columns are the within-arm control: Perception's seed reaches every row, so only the three candidate-bound nodes can be contrasted, and the rows those nodes never fed are not protected -- they lose intent as well.

Source scenario of the values that reached `general` rows: `recommendation` 14, `play` 12, `social` 12, `weather` 12, `news` 10, `takeaway` 9, `cooking` 8, `iot` 8, `qa` 8, `lists` 6, `audio` 3, `calendar` 3.

| value id | node | kind | target | rows reached | intent saves / harms | mean row SLU delta |
| --- | --- | --- | --- | ---: | ---: | ---: |
| `delta:1:0098d11d2d55` | perception | intent-boundary | `scenario` | 60 | 0 / 6 | -2.34 |
| `delta:1:2705faddd09d` | perception | intent-boundary | `recommendation_locations` | 60 | 0 / 6 | -2.34 |
| `delta:1:458b1eb85929` | perception | intent-boundary | `calendar_query` | 60 | 0 / 6 | -2.34 |
| `delta:1:4bc644592b9f` | perception | intent-boundary | `scenario:email` | 60 | 0 / 6 | -2.34 |
| `delta:1:0770afdee5ed` | reviewer | reviewer-criterion | `query` | 26 | 0 / 4 | -5.41 |
| `delta:1:21f0f46c86f1` | solver | slot-contract | `place_name` | 26 | 0 / 4 | -5.41 |
| `delta:1:d1c93189ba0c` | solver | slot-contract | `transport_query` | 26 | 0 / 4 | -5.41 |
| `delta:1:5af35e6e8bb9` | solver | slot-contract | `place_name` | 25 | 0 / 4 | -5.62 |
| `delta:1:ffd60d82ee1c` | reviewer | reviewer-criterion | `place_name` | 19 | 0 / 2 | -5.26 |
| `delta:1:f9a136f4aac3` | solver | slot-contract | `entities.filler` | 18 | 0 / 2 | -5.56 |
| `delta:1:b1e97789d3a2` | reviewer | reviewer-criterion | `scenario.qa` | 17 | 0 / 1 | -5.88 |
| `delta:1:958bfd7950e2` | reviewer | reviewer-criterion | `entities` | 14 | 0 / 2 | 0.00 |

Concentration: 47 of 106 values touch at least one harmed row, of which 1 touch harmed rows only; the 7 harmed rows received 47 distinct values between them. No value and no node carries the loss on its own.

### 3.2 CELL-2 (deltas v2)

Store `stage3-deltas-v2` holds 200 values; 81 distinct values reached at least one `general` row. Values whose declared target names `general`: 0. Values whose own source rows are `general`: 0.

| node | rows supplied | distinct values | intent saves / harms on supplied | mean intent delta, supplied | mean intent delta, NOT supplied | mean row SLU delta, supplied | mean row SLU delta, NOT supplied |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| perception | 60 | 4 | 2 / 6 | -6.67 | -- | -2.90 | -- |
| solver | 39 | 51 | 1 / 4 | -7.69 | -4.76 | -4.46 | 0.00 |
| reviewer | 32 | 23 | 2 / 2 | 0.00 | -14.29 | -6.25 | 0.93 |
| planner | 5 | 3 | 0 / 0 | 0.00 | -7.27 | 0.00 | -3.16 |

The `NOT supplied` columns are the within-arm control: Perception's seed reaches every row, so only the three candidate-bound nodes can be contrasted, and the rows those nodes never fed are not protected -- they lose intent as well.

Source scenario of the values that reached `general` rows: `recommendation` 14, `transport` 14, `weather` 14, `datetime` 12, `cooking` 11, `takeaway` 8, `email` 4, `calendar` 2, `lists` 2, `qa` 2, `audio` 1, `play` 1.

| value id | node | kind | target | rows reached | intent saves / harms | mean row SLU delta |
| --- | --- | --- | --- | ---: | ---: | ---: |
| `delta:1:0098d11d2d55` | perception | intent-boundary | `scenario` | 60 | 2 / 6 | -2.90 |
| `delta:1:2705faddd09d` | perception | intent-boundary | `recommendation_locations` | 60 | 2 / 6 | -2.90 |
| `delta:1:458b1eb85929` | perception | intent-boundary | `calendar_query` | 60 | 2 / 6 | -2.90 |
| `delta:1:4bc644592b9f` | perception | intent-boundary | `scenario:email` | 60 | 2 / 6 | -2.90 |
| `delta:1:d1c93189ba0c` | solver | slot-contract | `transport_query` | 19 | 0 / 3 | 1.37 |
| `delta:1:958bfd7950e2` | reviewer | reviewer-criterion | `entities` | 14 | 1 / 1 | 0.00 |
| `delta:1:4ca5a519402c` | solver | slot-contract | `entities` | 9 | 0 / 1 | -11.11 |
| `delta:1:54d15c58d173` | solver | slot-contract | `date` | 8 | 0 / 1 | -12.50 |
| `delta:1:5585ac9178cd` | solver | exemplar-note | `weather_descriptor` | 8 | 0 / 1 | -12.50 |
| `delta:1:5c4d27a08099` | reviewer | reviewer-criterion | `weather` | 8 | 0 / 1 | -12.50 |
| `delta:1:637b0e28eb4a` | solver | slot-contract | `time` | 8 | 0 / 1 | -12.50 |
| `delta:1:68dd85055eaa` | reviewer | reviewer-criterion | `weather` | 8 | 0 / 1 | -12.50 |

Concentration: 37 of 81 values touch at least one harmed row, of which 2 touch harmed rows only; the 8 harmed rows received 37 distinct values between them. No value and no node carries the loss on its own.

### 3.3 CELL-2 twin (deranged)

Store `stage3-deltas-twin-v2` holds 200 values; 58 distinct values reached at least one `general` row. Values whose declared target names `general`: 0. Values whose own source rows are `general`: 0.

| node | rows supplied | distinct values | intent saves / harms on supplied | mean intent delta, supplied | mean intent delta, NOT supplied | mean row SLU delta, supplied | mean row SLU delta, NOT supplied |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| perception | 60 | 4 | 0 / 7 | -11.67 | -- | -2.90 | -- |
| solver | 49 | 35 | 0 / 7 | -14.29 | 0.00 | -3.55 | 0.00 |
| reviewer | 19 | 17 | 0 / 3 | -15.79 | -9.76 | -5.26 | -1.80 |
| planner | 8 | 2 | 0 / 1 | -12.50 | -11.54 | 0.00 | -3.34 |

The `NOT supplied` columns are the within-arm control: Perception's seed reaches every row, so only the three candidate-bound nodes can be contrasted, and the rows those nodes never fed are not protected -- they lose intent as well.

Source scenario of the values that reached `general` rows: `weather` 10, `transport` 9, `datetime` 8, `email` 8, `recommendation` 7, `takeaway` 6, `cooking` 5, `calendar` 3, `lists` 2, `audio` 1, `play` 1, `qa` 1.

| value id | node | kind | target | rows reached | intent saves / harms | mean row SLU delta |
| --- | --- | --- | --- | ---: | ---: | ---: |
| `delta:1:0098d11d2d55` | perception | intent-boundary | `weather_query` | 60 | 0 / 7 | -2.90 |
| `delta:1:2705faddd09d` | perception | intent-boundary | `calendar_query` | 60 | 0 / 7 | -2.90 |
| `delta:1:458b1eb85929` | perception | intent-boundary | `qa_factoid` | 60 | 0 / 7 | -2.90 |
| `delta:1:4bc644592b9f` | perception | intent-boundary | `lists_createoradd` | 60 | 0 / 7 | -2.90 |
| `delta:1:9423be99db6f` | solver | slot-contract | `takeaway_order` | 24 | 0 / 4 | -3.08 |
| `delta:1:098ba951f2a4` | solver | slot-contract | `query` | 12 | 0 / 2 | 0.00 |
| `delta:1:a87351d6173c` | solver | slot-contract | `business_type` | 9 | 0 / 1 | 0.00 |
| `delta:1:0202908d3e8e` | reviewer | reviewer-criterion | `slot-contract` | 8 | 0 / 1 | 0.00 |
| `delta:1:084d7c289ae0` | solver | slot-contract | `slot type 'personal_info'` | 8 | 0 / 1 | 0.00 |
| `delta:1:5585ac9178cd` | solver | exemplar-note | `weather_descriptor` | 8 | 0 / 1 | 0.00 |
| `delta:1:5af80dec3868` | reviewer | reviewer-criterion | `takeaway` | 8 | 0 / 1 | 0.00 |
| `delta:1:818c0e717b88` | solver | slot-contract | `entities` | 8 | 0 / 1 | 0.00 |

Concentration: 44 of 58 values touch at least one harmed row, of which 1 touch harmed rows only; the 9 harmed rows received 44 distinct values between them. No value and no node carries the loss on its own.

The derangement twin is the decisive column: it carries the same supply FORM with deranged statement CONTENT and loses at least as much on `general` as the arm does. A content-borne harm cannot survive a derangement; a form-borne one must.

## 4. Are the losses on rows PLAN already got right?

| arm | metric | PLAN right -> cell right | PLAN right -> cell wrong | PLAN wrong -> cell right | PLAN wrong -> cell wrong |
| --- | --- | ---: | ---: | ---: | ---: |
| CELL-1 (deltas v1r) | intent exact | 20 | 6 | 0 | 34 |
| CELL-1 (deltas v1r) | scenario exact | 23 | 8 | 0 | 29 |
| CELL-2 (deltas v2) | intent exact | 20 | 6 | 2 | 32 |
| CELL-2 (deltas v2) | scenario exact | 25 | 6 | 2 | 27 |
| CELL-2 twin (deranged) | intent exact | 19 | 7 | 0 | 34 |
| CELL-2 twin (deranged) | scenario exact | 23 | 8 | 0 | 29 |

Every `general` loss is a row PLAN answered correctly -- by construction of the metric, a row that was already wrong can only be re-labelled inside the wrong set, and 32 of the 60 rows under CELL-2 are in that set. The delta supply therefore has no visible upside on this stratum and a measurable downside on the rows PLAN was getting right.

## 5. Root-cause hypotheses, ranked, with the recoverable bound

| arm | intent rows lost | intent pp recoverable on `general` | on Fold A | pooled SLU pp recoverable on `general` | on Fold A |
| --- | ---: | ---: | ---: | ---: | ---: |
| CELL-1 (deltas v1r) | 6 | 10.00 | 0.56 | 9.76 | 0.21 |
| CELL-2 (deltas v2) | 6 | 10.00 | 0.56 | 11.16 | 0.24 |
| CELL-2 twin (deranged) | 7 | 11.67 | 0.65 | 11.37 | 0.24 |

The bound undoes every harmed row and keeps every gain, so no iteration-3 mechanism aimed at this stratum can beat it. The second, larger ceiling is the stratum itself: PLAN already answers only 43.33 % of the `general` rows correctly and pools 30.23 SLU-F1 there, so closing the arm-vs-PLAN gap recovers a loss, it does not fix the stratum.

### H1 (PRIMARY -- carries the whole measured loss) -- The `general` loss is a FORM cost of the delta supply, not the content of any delta

- The derangement twin, which carries the same supply form with deranged statement content, loses -11.67 pp intent on these rows against PLAN, versus -6.67 pp for CELL-2 and -10.00 pp for CELL-1: the control loses at least as much as the arms.
- There is almost no delta CONTENT for this stratum to consume: 1 of 379 v1r values and 0 of 200 v2 values declare a `general` target, and of the values that actually reached these rows 2 (CELL-1) and 0 (CELL-2) were learned from a `general` source row at all.
- The harm is diffuse across values: 37 of 81 CELL-2 values touch a harmed row and no single value or node concentrates it.
- The within-arm control agrees: the rows the Solver route never fed lose intent too (CELL-1 (deltas v1r) -8.33 pp on 12 unsupplied rows versus -10.42 pp on 48 supplied rows; CELL-2 (deltas v2) -4.76 pp on 21 unsupplied rows versus -7.69 pp on 39 supplied rows), so what moves the stratum is present on rows no delta statement reached.

**Iteration-3 mechanism it implies.** Iteration 3 must gate the supply itself, not re-author statements: route delta context only to rows whose Perception state names a scenario the store actually covers, and serve an empty supply otherwise, so an uncovered stratum runs the bare PLAN form. A scenario-gated supply is the only mechanism that removes a form cost without removing the gains elsewhere.

**Bound if fully fixed.** CELL-2: up to 10.00 pp intent and 11.16 pp pooled SLU-F1 on the 60 `general` rows, which is 0.56 pp intent and 0.24 pp pooled SLU-F1 on the 1080-row Fold A. CELL-1: 10.00 / 9.76 pp on the stratum (0.56 / 0.21 pp on Fold A). The twin's own bound is 11.67 pp intent, which is what makes this the ceiling of the whole line, not a share of it.

### H2 (CONTRIBUTING -- real crowding, but it predates the delta cells) -- Perception seeds crowd `general_*` out of the candidate list

- Candidate coverage of the gold intent on these rows is PLAN (v2.0 lock) 25/60, CELL-1 (deltas v1r) 22/60, CELL-2 (deltas v2) 23/60, CELL-2 twin (deranged) 22/60.
- Coverage transitions against PLAN: CELL-1 (deltas v1r) 6 lost / 3 gained, CELL-2 (deltas v2) 3 lost / 1 gained, CELL-2 twin (deranged) 5 lost / 2 gained.
- The unconditional Perception seed is served to 60 of 60 `general` rows and is the SAME four `intent-boundary` values on every row, none of them targeting `general_*`, so it cannot be separated row by row inside one arm -- only the twin separates it.
- But coverage loss and answer loss are largely DIFFERENT rows: CELL-1 (deltas v1r) 4 of 6 intent losses also lost coverage; CELL-2 (deltas v2) 1 of 6 intent losses also lost coverage; CELL-2 twin (deranged) 3 of 7 intent losses also lost coverage, so crowding is a contributing channel in CELL-1 and a minor one in CELL-2, never the whole mechanism.

**Iteration-3 mechanism it implies.** A `general_*` candidate floor in Perception (reserve one slot when no `general_*` candidate survives) or a scenario-aware candidate budget. Note the B4a precedent: a standing `general_quirky` fallback was flown on the anchor, lifted coverage to 100 % and was chosen on zero rows, so a floor alone is expected to be inert unless the Solver is also told when to prefer it.

**Bound if fully fixed.** Bounded above by the coverage rows the cells actually lose against PLAN, which is CELL-1 (deltas v1r) 6 rows, CELL-2 (deltas v2) 3 rows, CELL-2 twin (deranged) 5 rows -- at most 10.00 pp intent on the stratum.

### H3 (REJECTED -- the entity side is not where the loss is) -- Solver deltas learned on other scenarios push entity emission on chit-chat rows

- PLAN emits 39 entities on these 60 rows against 12 gold slots; CELL-2 emits 39 and CELL-1 44.
- Exact-match entity FP is 32 under PLAN, 34 under CELL-2 and 39 under CELL-1: CELL-1 adds 7 false positives across all 60 rows, which is a fraction of a point of the 12-point pooled gap.
- Span-F1 on the stratum moves by -2.22 pp per row under CELL-2, an order of magnitude smaller than the intent movement.

**Iteration-3 mechanism it implies.** A no-entity contract for `general_*` would be close to a no-op: the rows already carry almost no gold slots and the arms already emit almost none. Do not spend an iteration-3 cell here.

**Bound if fully fixed.** At most 2.22 pp span-F1 per row on the stratum, i.e. 0.123 pp on Fold A.

### H4 (DESCRIPTIVE -- names the destination, not the cause) -- Intent flips land on a specific foreign family (mostly `qa_*`)

- Delivered scenario mix under PLAN: `general` 31, `qa` 10, `recommendation` 4, `audio` 3, `news` 3, `cooking` 2; under CELL-2: `general` 27, `qa` 13, `iot` 4, `news` 4, `recommendation` 4, `audio` 3.
- Every intent loss sits on a row PLAN answered correctly (6 rows under CELL-2, 6 under CELL-1); no loss comes from a row that was already wrong.

**Iteration-3 mechanism it implies.** A one-directional contrast note (`general_quirky` versus the observed destination family) placed where the flip happens -- but only after the form cost above is removed, since the same note under the current supply form is what FIX-2 of the A3 audit already carried into cell B4a.

**Bound if fully fixed.** Same transition bound as H1 -- it is the same rows seen from the destination side, not additional headroom.

## Provenance

| artefact | sha256 |
| --- | --- |
| docs/receipts/rosters/slurp-evo-fold-a-v2.json | `1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d` |
| SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1.outputs.jsonl | `2dcaa925ab7dad77e5938002d5606189ff7f644a94ade5b7265060e94d3ae17f` |
| SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1.outputs.jsonl | `a2e752b876d27d8932b829412f428b70f85e6307f92399d5953bd4576e7a5075` |
| SAEA-SLURP-STAGE3-DELTA-CELL-R02-V1.outputs.jsonl | `f3940b91c4f28ae9daad619f4236d1cc11108c50880ffb6154c8540a3c7081b3` |
| SAEA-SLURP-STAGE3-DELTA-CELL-R02-TWIN-V1.outputs.jsonl | `14a348af15453656995be3e9e2770e6e81f81b2d81a0e82f16737fbaa38f5f5f` |
| SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1.scores.json | `9f3047fa77a868cb6c8cd72827c0358996288b12cb976a682a960bde5eda707c` |
| SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1.scores.json | `1d3e53364c88d3160ec55b7f95837a50ced7f49c5f915dadff740f785bbab8e7` |
| SAEA-SLURP-STAGE3-DELTA-CELL-R02-V1.scores.json | `375e2fea78731eae2da05a6ad40dba4d52baacfc92e4ca327711e41382e9cdb1` |
| SAEA-SLURP-STAGE3-DELTA-CELL-R02-TWIN-V1.scores.json | `09869e67943a4408109ab068e399fa28e694ed060a8e317b55e98b649a833f4b` |
| SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1.phases.json | `7cac358a39c446c7aa13fcec70722a4669814ea0fad4fc76e9bf291d7b4b8e6f` |
| SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1.phases.json | `b3c446cbde3e371ae42d18f8c739e9fae03be567803e9ca269ba75b74c86c3cc` |
| SAEA-SLURP-STAGE3-DELTA-CELL-R02-V1.phases.json | `e5bacc44823a82b12b8f6c76d65c14fcf5e9ef35b0271d6d2ec5b9eb76d426c1` |
| SAEA-SLURP-STAGE3-DELTA-CELL-R02-TWIN-V1.phases.json | `386574926b4e63835da55578873fc1bbd9d4d22d126a0c4cde1dcc1a8ab84b43` |
| knowledge/slurp/semantic/stage3-deltas-v1r/snapshot.json | `cf6f7fa639c4b1a0e7e7bad0bf071a8672352a25160544431966d7922250e071` |
| knowledge/slurp/semantic/stage3-deltas-v2/snapshot.json | `f960bc84b920e37030a141a81c182df9c928dc2d3a9b7948ae3c9ac42b878085` |
| knowledge/slurp/semantic/stage3-deltas-twin-v2/snapshot.json | `cf8f6037a0aad34ee211120305ad6ca5a7cc4edfb0b3599727d6bdc032e44988` |

Exposure: registered as run id `SAEA-SLURP-GENERAL-SCENARIO-DIAGNOSTIC-V1`, profile `model-free-check`, zero contacts, `consumed = no`.
