# Where the 12.78 points live: SLURP intent-error decomposition of the locked plan by scenario, action and joint intent

Owner decision 137 sets an absolute target of **95 % intent-recognition accuracy**. On TRAIN Fold A the locked v2.0 plan reads `scenario_action` exact **82.2222** (scenario exact 87.3148, action exact 83.5185), a gap of **12.78 points**. Intent is the product of two labels, so this note decomposes the joint error over the sealed PLAN-policy answers of three rosters and states, as arithmetic, where the error mass sits and how much of it must go. Measurement only: no mechanism is designed, no cell is registered, nothing is flown.

**Method.** Model-free, zero contacts (no model, tokenizer, encoder, ASR, scorer, embedder, server, GPU or network). Reproducer `scripts/analysis/slurp_intent_error_decomposition.py` (recipe `slurp-intent-error-decomposition-v1`), analysis root `SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-INTENT-ERROR-DECOMPOSITION-V1/`. Sources, all read-only and hash-verified against their sealed manifests: the three arms' `<run_id>.outputs.jsonl` and `<run_id>.scores.json`, the three committed roster receipts, and the frozen SLURP gold read through `data.slurp.load_slurp_split` (the loader `core.scoring_batch` uses; four probe threads). Per-row correctness is the OFFICIAL per-sample flag of the sealed score file; predicted ids come from `reproduction.slurp_scoring.parse_slu_response` over the sealed delivered text, and the read refuses if the two disagree on any row (they agreed on every row of every roster: 2705 rows). No utterance text, transcript, gold filler, predicted filler or delivered text is printed or persisted: label ids, counts, rates and hashes only. The test split stays closed.

**Claim boundary.** Development numbers (owner decisions 28 and 86) on exposed discovery / dev rosters; nothing here is a test claim, a superiority claim or a generalisation claim. Every "top-k fixed entirely" figure in section 5 is an **oracle**: it assumes a perfect repair of every row of the named labels and says nothing about how such a repair would be built. DEV-2000-ADDED withholds the stratum per item, so its per-scenario rows here are gold-derived aggregates, exactly as in the bad-case bank. The three rosters overlap in neither sample ids nor utterance ids (section 0), so the pooled table simply adds rows.

## 0. Inputs and the three rosters

| roster | sealed arm | gold split | rows | scenario % | action % | intent % | gap to 95 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| TRAIN Fold A (1,080 rows) | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1` | train | 1080 | 87.3148 | 83.5185 | 82.2222 | 12.78 |
| ROLL-1 R01C (625 rows, delivered answers) | `SAEA-SLURP-STAGE3-ROLLOUT-R01-V1` | train | 625 | 74.5600 | 71.2000 | 68.9600 | 26.04 |
| DEV-2000-ADDED (1,000 rows) | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1` | devel | 1000 | 81.6000 | 79.2000 | 76.6000 | 18.40 |
| **pooled** | -- | train+devel | 2705 | 82.2551 | 79.0758 | 77.0795 | 17.92 |

Roster overlap (ids only): shared sample ids 0, shared utterance ids 0 across the three rosters (pairwise: train-fold-a x roll-1-r01c = 0, train-fold-a x dev2000-added = 0, roll-1-r01c x dev2000-added = 0). Label vocabulary seen in gold: 18 scenarios, 46 actions, 60 intents.

## 1. Headline: the two components and how the joint error is composed

| roster | rows | scenario % | action % | joint % | scen x act % | joint errors | action only wrong | scenario only wrong | both wrong | unparsed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| TRAIN Fold A (1,080 rows) | 1080 | 87.31 | 83.52 | 82.22 | 72.92 | 192 | 55 (28.6 %) | 14 (7.3 %) | 122 (63.5 %) | 1 (0.5 %) |
| ROLL-1 R01C (625 rows, delivered answers) | 625 | 74.56 | 71.20 | 68.96 | 53.09 | 194 | 35 (18.0 %) | 14 (7.2 %) | 145 (74.7 %) | 0 (0.0 %) |
| DEV-2000-ADDED (1,000 rows) | 1000 | 81.60 | 79.20 | 76.60 | 64.63 | 234 | 50 (21.4 %) | 26 (11.1 %) | 156 (66.7 %) | 2 (0.9 %) |
| pooled | 2705 | 82.26 | 79.08 | 77.08 | 65.04 | 620 | 140 (22.6 %) | 54 (8.7 %) | 423 (68.2 %) | 3 (0.5 %) |

**Reading.** Action-exact accuracy is below scenario-exact accuracy on 3 of 3 rosters, so in marginal terms the action side is the weaker label. But the largest joint-error class is **both labels wrong**: pooled, 423 of 620 joint errors (68.2 %) have BOTH labels wrong, 140 (22.6 %) have the scenario right and the action wrong, 54 (8.7 %) have the action right and the scenario wrong, and 3 are unparsed. Of the 566 action errors, 426 (75.3 %) sit on rows whose scenario is also wrong; of the 480 scenario errors, 426 (88.8 %) sit on rows whose action is also wrong. The joint accuracy (77.08) is above the product of the two marginals: the two errors coincide on the same rows far more often than independence would give. The action side is therefore not a separable weakness: most action errors are the action changing together with the scenario, i.e. a cross-scenario intent confusion, not an action slip inside the right scenario.

**Two upper bounds, exact arithmetic.** A row is jointly correct only if its scenario is correct AND its action is correct, so joint accuracy can never exceed either component's exact accuracy. Reaching the target therefore needs each component at or above 95 % on its own; the table gives how far each side is from that bound and how many of its own errors would have to go. The within-scenario column is the headroom of a PERFECT action decision inside the correct scenario (its ceiling is exactly the scenario-exact accuracy); the remainder of the gap can only be closed by moving rows across scenarios.

| roster | joint % | joint gap | scenario % | scenario gap (errors to remove) | action % | action gap (errors to remove) | within-scenario headroom (pp -> ceiling) | cross-scenario mass (pp) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| TRAIN Fold A (1,080 rows) | 82.22 | 12.78 | 87.31 | 7.69 (83 of 137) | 83.52 | 11.48 (124 of 178) | +5.09 -> 87.31 | 12.69 |
| ROLL-1 R01C (625 rows, delivered answers) | 68.96 | 26.04 | 74.56 | 20.44 (128 of 159) | 71.20 | 23.80 (149 of 180) | +5.60 -> 74.56 | 25.44 |
| DEV-2000-ADDED (1,000 rows) | 76.60 | 18.40 | 81.60 | 13.40 (134 of 184) | 79.20 | 15.80 (158 of 208) | +5.00 -> 81.60 | 18.40 |
| pooled | 77.08 | 17.92 | 82.26 | 12.74 (345 of 480) | 79.08 | 15.92 (431 of 566) | +5.18 -> 82.26 | 17.74 |

## 2. Error mass by scenario, by action and by joint intent

Each table is sorted by the error mass the gold label owns; `error share` is the label's share of ALL errors of that metric (scenario errors for the scenario table, action errors for the action table, joint errors for the intent table).

### 2.1 Pooled (2,705 rows)

Per scenario (scenario-exact errors):

| scenario | rows | errors | exact % | error share % | cumulative % |
| --- | ---: | ---: | ---: | ---: | ---: |
| general | 164 | 104 | 36.59 | 21.7 | 21.7 |
| calendar | 323 | 85 | 73.68 | 17.7 | 39.4 |
| qa | 255 | 57 | 77.65 | 11.9 | 51.2 |
| play | 300 | 49 | 83.67 | 10.2 | 61.5 |
| email | 189 | 24 | 87.30 | 5.0 | 66.5 |
| social | 99 | 24 | 75.76 | 5.0 | 71.5 |
| lists | 149 | 21 | 85.91 | 4.4 | 75.8 |
| news | 116 | 21 | 81.90 | 4.4 | 80.2 |
| cooking | 91 | 15 | 83.52 | 3.1 | 83.3 |
| music | 87 | 15 | 82.76 | 3.1 | 86.5 |
| audio | 90 | 13 | 85.56 | 2.7 | 89.2 |
| weather | 166 | 11 | 93.37 | 2.3 | 91.5 |
| datetime | 108 | 9 | 91.67 | 1.9 | 93.3 |
| iot | 150 | 9 | 94.00 | 1.9 | 95.2 |
| recommendation | 95 | 8 | 91.58 | 1.7 | 96.9 |
| alarm | 86 | 6 | 93.02 | 1.2 | 98.1 |
| takeaway | 97 | 6 | 93.81 | 1.2 | 99.4 |
| transport | 140 | 3 | 97.86 | 0.6 | 100.0 |

Per action (action-exact errors):

| action | rows | errors | exact % | error share % | cumulative % |
| --- | ---: | ---: | ---: | ---: | ---: |
| query | 840 | 122 | 85.48 | 21.6 | 21.6 |
| quirky | 137 | 114 | 16.79 | 20.1 | 41.7 |
| factoid | 127 | 61 | 51.97 | 10.8 | 52.5 |
| music | 136 | 41 | 69.85 | 7.2 | 59.7 |
| set | 194 | 31 | 84.02 | 5.5 | 65.2 |
| recipe | 90 | 18 | 80.00 | 3.2 | 68.4 |
| post | 76 | 16 | 78.95 | 2.8 | 71.2 |
| order | 52 | 14 | 73.08 | 2.5 | 73.7 |
| volume_mute | 34 | 12 | 64.71 | 2.1 | 75.8 |
| remove | 103 | 11 | 89.32 | 1.9 | 77.7 |
| sendemail | 76 | 11 | 85.53 | 1.9 | 79.7 |
| audiobook | 44 | 9 | 79.55 | 1.6 | 81.3 |
| radio | 56 | 9 | 83.93 | 1.6 | 82.9 |
| definition | 54 | 8 | 85.19 | 1.4 | 84.3 |
| locations | 48 | 7 | 85.42 | 1.2 | 85.5 |
| querycontact | 21 | 7 | 66.67 | 1.2 | 86.7 |
| createoradd | 48 | 6 | 87.50 | 1.1 | 87.8 |
| ticket | 27 | 6 | 77.78 | 1.1 | 88.9 |
| hue_lightdim | 19 | 5 | 73.68 | 0.9 | 89.8 |
| likeness | 25 | 5 | 80.00 | 0.9 | 90.6 |
| podcasts | 38 | 5 | 86.84 | 0.9 | 91.5 |
| settings | 11 | 5 | 54.55 | 0.9 | 92.4 |
| volume_up | 39 | 5 | 87.18 | 0.9 | 93.3 |
| hue_lightchange | 26 | 4 | 84.62 | 0.7 | 94.0 |
| volume_other | 4 | 4 | 0.00 | 0.7 | 94.7 |
| cleaning | 22 | 3 | 86.36 | 0.5 | 95.2 |
| game | 26 | 3 | 88.46 | 0.5 | 95.8 |
| stock | 25 | 3 | 88.00 | 0.5 | 96.3 |
| events | 34 | 2 | 94.12 | 0.4 | 96.6 |
| hue_lightoff | 23 | 2 | 91.30 | 0.4 | 97.0 |
| hue_lighton | 6 | 2 | 66.67 | 0.4 | 97.3 |
| movies | 13 | 2 | 84.62 | 0.4 | 97.7 |
| traffic | 29 | 2 | 93.10 | 0.4 | 98.1 |
| volume_down | 13 | 2 | 84.62 | 0.4 | 98.4 |
| wemo_on | 9 | 2 | 77.78 | 0.4 | 98.8 |
| addcontact | 9 | 1 | 88.89 | 0.2 | 98.9 |
| coffee | 20 | 1 | 95.00 | 0.2 | 99.1 |
| convert | 22 | 1 | 95.45 | 0.2 | 99.3 |
| currency | 35 | 1 | 97.14 | 0.2 | 99.5 |
| hue_lightup | 19 | 1 | 94.74 | 0.2 | 99.6 |
| maths | 14 | 1 | 92.86 | 0.2 | 99.8 |
| wemo_off | 6 | 1 | 83.33 | 0.2 | 100.0 |
| dislikeness | 1 | 0 | 100.00 | 0.0 | 100.0 |
| greet | 6 | 0 | 100.00 | 0.0 | 100.0 |
| joke | 21 | 0 | 100.00 | 0.0 | 100.0 |
| taxi | 27 | 0 | 100.00 | 0.0 | 100.0 |

Per joint intent (scenario_action errors):

| intent | rows | errors | exact % | error share % | cumulative % |
| --- | ---: | ---: | ---: | ---: | ---: |
| general_quirky | 137 | 114 | 16.79 | 18.4 | 18.4 |
| calendar_query | 129 | 61 | 52.71 | 9.8 | 28.2 |
| qa_factoid | 127 | 61 | 51.97 | 9.8 | 38.1 |
| play_music | 136 | 41 | 69.85 | 6.6 | 44.7 |
| calendar_set | 149 | 33 | 77.85 | 5.3 | 50.0 |
| news_query | 116 | 21 | 81.90 | 3.4 | 53.4 |
| cooking_recipe | 90 | 18 | 80.00 | 2.9 | 56.3 |
| social_post | 76 | 16 | 78.95 | 2.6 | 58.9 |
| datetime_query | 86 | 14 | 83.72 | 2.3 | 61.1 |
| takeaway_order | 52 | 14 | 73.08 | 2.3 | 63.4 |
| lists_query | 59 | 13 | 77.97 | 2.1 | 65.5 |
| audio_volume_mute | 34 | 12 | 64.71 | 1.9 | 67.4 |
| email_query | 83 | 12 | 85.54 | 1.9 | 69.4 |
| music_query | 50 | 12 | 76.00 | 1.9 | 71.3 |
| email_sendemail | 76 | 11 | 85.53 | 1.8 | 73.1 |
| weather_query | 166 | 11 | 93.37 | 1.8 | 74.8 |
| play_audiobook | 44 | 9 | 79.55 | 1.5 | 76.3 |
| play_radio | 56 | 9 | 83.93 | 1.5 | 77.7 |
| transport_query | 57 | 9 | 84.21 | 1.5 | 79.2 |
| qa_definition | 54 | 8 | 85.19 | 1.3 | 80.5 |
| social_query | 23 | 8 | 65.22 | 1.3 | 81.8 |
| email_querycontact | 21 | 7 | 66.67 | 1.1 | 82.9 |
| recommendation_locations | 48 | 7 | 85.42 | 1.1 | 84.0 |
| lists_createoradd | 48 | 6 | 87.50 | 1.0 | 85.0 |
| transport_ticket | 27 | 6 | 77.78 | 1.0 | 86.0 |
| alarm_set | 45 | 5 | 88.89 | 0.8 | 86.8 |
| audio_volume_up | 39 | 5 | 87.18 | 0.8 | 87.6 |
| calendar_remove | 45 | 5 | 88.89 | 0.8 | 88.4 |
| iot_hue_lightdim | 19 | 5 | 73.68 | 0.8 | 89.2 |
| music_likeness | 25 | 5 | 80.00 | 0.8 | 90.0 |

(top 30 of 60 by error mass; the full table is in `decomposition.json`)

### 2.2 TRAIN Fold A (1,080 rows)

Per scenario:

| scenario | rows | errors | exact % | error share % | cumulative % |
| --- | ---: | ---: | ---: | ---: | ---: |
| general | 60 | 29 | 51.67 | 21.2 | 21.2 |
| social | 60 | 16 | 73.33 | 11.7 | 32.8 |
| calendar | 60 | 11 | 81.67 | 8.0 | 40.9 |
| news | 60 | 10 | 83.33 | 7.3 | 48.2 |
| qa | 60 | 10 | 83.33 | 7.3 | 55.5 |
| audio | 60 | 8 | 86.67 | 5.8 | 61.3 |
| cooking | 60 | 8 | 86.67 | 5.8 | 67.2 |
| lists | 60 | 8 | 86.67 | 5.8 | 73.0 |
| email | 60 | 6 | 90.00 | 4.4 | 77.4 |
| music | 60 | 6 | 90.00 | 4.4 | 81.8 |
| alarm | 60 | 4 | 93.33 | 2.9 | 84.7 |
| datetime | 60 | 4 | 93.33 | 2.9 | 87.6 |
| play | 60 | 4 | 93.33 | 2.9 | 90.5 |
| recommendation | 60 | 4 | 93.33 | 2.9 | 93.4 |
| weather | 60 | 4 | 93.33 | 2.9 | 96.4 |
| iot | 60 | 2 | 96.67 | 1.5 | 97.8 |
| takeaway | 60 | 2 | 96.67 | 1.5 | 99.3 |
| transport | 60 | 1 | 98.33 | 0.7 | 100.0 |

Per action (top 15):

| action | rows | errors | exact % | error share % | cumulative % |
| --- | ---: | ---: | ---: | ---: | ---: |
| query | 363 | 39 | 89.26 | 21.9 | 21.9 |
| quirky | 45 | 34 | 24.44 | 19.1 | 41.0 |
| factoid | 27 | 13 | 51.85 | 7.3 | 48.3 |
| post | 47 | 10 | 78.72 | 5.6 | 53.9 |
| order | 29 | 8 | 72.41 | 4.5 | 58.4 |
| recipe | 59 | 8 | 86.44 | 4.5 | 62.9 |
| volume_mute | 24 | 8 | 66.67 | 4.5 | 67.4 |
| set | 58 | 7 | 87.93 | 3.9 | 71.3 |
| locations | 30 | 5 | 83.33 | 2.8 | 74.2 |
| createoradd | 22 | 4 | 81.82 | 2.2 | 76.4 |
| music | 19 | 4 | 78.95 | 2.2 | 78.7 |
| ticket | 17 | 4 | 76.47 | 2.2 | 80.9 |
| volume_other | 4 | 4 | 0.00 | 2.2 | 83.1 |
| likeness | 18 | 3 | 83.33 | 1.7 | 84.8 |
| radio | 16 | 3 | 81.25 | 1.7 | 86.5 |

(top 15 of 46 by error mass; the full table is in `decomposition.json`)

Per joint intent (top 15):

| intent | rows | errors | exact % | error share % | cumulative % |
| --- | ---: | ---: | ---: | ---: | ---: |
| general_quirky | 45 | 34 | 24.44 | 17.7 | 17.7 |
| qa_factoid | 27 | 13 | 51.85 | 6.8 | 24.5 |
| news_query | 60 | 10 | 83.33 | 5.2 | 29.7 |
| social_post | 47 | 10 | 78.72 | 5.2 | 34.9 |
| audio_volume_mute | 24 | 8 | 66.67 | 4.2 | 39.1 |
| calendar_query | 27 | 8 | 70.37 | 4.2 | 43.2 |
| cooking_recipe | 59 | 8 | 86.44 | 4.2 | 47.4 |
| takeaway_order | 29 | 8 | 72.41 | 4.2 | 51.6 |
| music_query | 32 | 6 | 81.25 | 3.1 | 54.7 |
| social_query | 13 | 6 | 53.85 | 3.1 | 57.8 |
| datetime_query | 50 | 5 | 90.00 | 2.6 | 60.4 |
| lists_query | 22 | 5 | 77.27 | 2.6 | 63.0 |
| recommendation_locations | 30 | 5 | 83.33 | 2.6 | 65.6 |
| alarm_set | 33 | 4 | 87.88 | 2.1 | 67.7 |
| audio_volume_other | 4 | 4 | 0.00 | 2.1 | 69.8 |

(top 15 of 60 by error mass; the full table is in `decomposition.json`)

### 2.3 ROLL-1 R01C (625 rows, delivered answers)

Per scenario:

| scenario | rows | errors | exact % | error share % | cumulative % |
| --- | ---: | ---: | ---: | ---: | ---: |
| general | 42 | 37 | 11.90 | 23.3 | 23.3 |
| calendar | 42 | 17 | 59.52 | 10.7 | 34.0 |
| play | 37 | 16 | 56.76 | 10.1 | 44.0 |
| qa | 38 | 14 | 63.16 | 8.8 | 52.8 |
| news | 36 | 10 | 72.22 | 6.3 | 59.1 |
| music | 27 | 9 | 66.67 | 5.7 | 64.8 |
| email | 33 | 8 | 75.76 | 5.0 | 69.8 |
| social | 35 | 8 | 77.14 | 5.0 | 74.8 |
| cooking | 31 | 7 | 77.42 | 4.4 | 79.2 |
| lists | 37 | 6 | 83.78 | 3.8 | 83.0 |
| audio | 30 | 5 | 83.33 | 3.1 | 86.2 |
| iot | 33 | 5 | 84.85 | 3.1 | 89.3 |
| recommendation | 29 | 4 | 86.21 | 2.5 | 91.8 |
| takeaway | 37 | 4 | 89.19 | 2.5 | 94.3 |
| datetime | 39 | 3 | 92.31 | 1.9 | 96.2 |
| weather | 41 | 3 | 92.68 | 1.9 | 98.1 |
| alarm | 26 | 2 | 92.31 | 1.3 | 99.4 |
| transport | 32 | 1 | 96.88 | 0.6 | 100.0 |

Per action (top 15):

| action | rows | errors | exact % | error share % | cumulative % |
| --- | ---: | ---: | ---: | ---: | ---: |
| query | 212 | 44 | 79.25 | 24.4 | 24.4 |
| quirky | 41 | 37 | 9.76 | 20.6 | 45.0 |
| factoid | 33 | 16 | 51.52 | 8.9 | 53.9 |
| music | 18 | 13 | 27.78 | 7.2 | 61.1 |
| recipe | 31 | 10 | 67.74 | 5.6 | 66.7 |
| order | 23 | 6 | 73.91 | 3.3 | 70.0 |
| post | 27 | 6 | 77.78 | 3.3 | 73.3 |
| sendemail | 20 | 4 | 80.00 | 2.2 | 75.6 |
| volume_mute | 10 | 4 | 60.00 | 2.2 | 77.8 |
| volume_up | 15 | 4 | 73.33 | 2.2 | 80.0 |
| audiobook | 6 | 3 | 50.00 | 1.7 | 81.7 |
| hue_lightchange | 8 | 3 | 62.50 | 1.7 | 83.3 |
| remove | 22 | 3 | 86.36 | 1.7 | 85.0 |
| events | 10 | 2 | 80.00 | 1.1 | 86.1 |
| likeness | 7 | 2 | 71.43 | 1.1 | 87.2 |

(top 15 of 39 by error mass; the full table is in `decomposition.json`)

Per joint intent (top 15):

| intent | rows | errors | exact % | error share % | cumulative % |
| --- | ---: | ---: | ---: | ---: | ---: |
| general_quirky | 41 | 37 | 9.76 | 19.1 | 19.1 |
| qa_factoid | 33 | 16 | 51.52 | 8.2 | 27.3 |
| calendar_query | 22 | 15 | 31.82 | 7.7 | 35.1 |
| play_music | 18 | 13 | 27.78 | 6.7 | 41.8 |
| cooking_recipe | 31 | 10 | 67.74 | 5.2 | 46.9 |
| news_query | 36 | 10 | 72.22 | 5.2 | 52.1 |
| datetime_query | 27 | 7 | 74.07 | 3.6 | 55.7 |
| music_query | 18 | 6 | 66.67 | 3.1 | 58.8 |
| social_post | 27 | 6 | 77.78 | 3.1 | 61.9 |
| takeaway_order | 23 | 6 | 73.91 | 3.1 | 64.9 |
| transport_query | 21 | 5 | 76.19 | 2.6 | 67.5 |
| audio_volume_mute | 10 | 4 | 60.00 | 2.1 | 69.6 |
| audio_volume_up | 15 | 4 | 73.33 | 2.1 | 71.6 |
| email_sendemail | 20 | 4 | 80.00 | 2.1 | 73.7 |
| lists_query | 11 | 4 | 63.64 | 2.1 | 75.8 |

(top 15 of 52 by error mass; the full table is in `decomposition.json`)

### 2.4 DEV-2000-ADDED (1,000 rows)

Per scenario:

| scenario | rows | errors | exact % | error share % | cumulative % |
| --- | ---: | ---: | ---: | ---: | ---: |
| calendar | 221 | 57 | 74.21 | 31.0 | 31.0 |
| general | 62 | 38 | 38.71 | 20.7 | 51.6 |
| qa | 157 | 33 | 78.98 | 17.9 | 69.6 |
| play | 203 | 29 | 85.71 | 15.8 | 85.3 |
| email | 96 | 10 | 89.58 | 5.4 | 90.8 |
| lists | 52 | 7 | 86.54 | 3.8 | 94.6 |
| weather | 65 | 4 | 93.85 | 2.2 | 96.7 |
| datetime | 9 | 2 | 77.78 | 1.1 | 97.8 |
| iot | 57 | 2 | 96.49 | 1.1 | 98.9 |
| news | 20 | 1 | 95.00 | 0.5 | 99.5 |
| transport | 48 | 1 | 97.92 | 0.5 | 100.0 |
| recommendation | 6 | 0 | 100.00 | 0.0 | 100.0 |
| social | 4 | 0 | 100.00 | 0.0 | 100.0 |

Per action (top 15):

| action | rows | errors | exact % | error share % | cumulative % |
| --- | ---: | ---: | ---: | ---: | ---: |
| quirky | 51 | 43 | 15.69 | 20.7 | 20.7 |
| query | 265 | 39 | 85.28 | 18.8 | 39.4 |
| factoid | 67 | 32 | 52.24 | 15.4 | 54.8 |
| music | 99 | 24 | 75.76 | 11.5 | 66.3 |
| set | 107 | 22 | 79.44 | 10.6 | 76.9 |
| definition | 43 | 8 | 81.40 | 3.8 | 80.8 |
| audiobook | 31 | 6 | 80.65 | 2.9 | 83.7 |
| remove | 49 | 6 | 87.76 | 2.9 | 86.5 |
| sendemail | 37 | 5 | 86.49 | 2.4 | 88.9 |
| radio | 34 | 4 | 88.24 | 1.9 | 90.9 |
| game | 16 | 3 | 81.25 | 1.4 | 92.3 |
| hue_lightdim | 11 | 3 | 72.73 | 1.4 | 93.8 |
| podcasts | 23 | 3 | 86.96 | 1.4 | 95.2 |
| querycontact | 10 | 3 | 70.00 | 1.4 | 96.6 |
| cleaning | 8 | 1 | 87.50 | 0.5 | 97.1 |

(top 15 of 35 by error mass; the full table is in `decomposition.json`)

Per joint intent (top 15):

| intent | rows | errors | exact % | error share % | cumulative % |
| --- | ---: | ---: | ---: | ---: | ---: |
| general_quirky | 51 | 43 | 15.69 | 18.4 | 18.4 |
| calendar_query | 80 | 38 | 52.50 | 16.2 | 34.6 |
| qa_factoid | 67 | 32 | 52.24 | 13.7 | 48.3 |
| calendar_set | 107 | 28 | 73.83 | 12.0 | 60.3 |
| play_music | 99 | 24 | 75.76 | 10.3 | 70.5 |
| email_query | 44 | 8 | 81.82 | 3.4 | 73.9 |
| qa_definition | 43 | 8 | 81.40 | 3.4 | 77.4 |
| play_audiobook | 31 | 6 | 80.65 | 2.6 | 79.9 |
| email_sendemail | 37 | 5 | 86.49 | 2.1 | 82.1 |
| calendar_remove | 34 | 4 | 88.24 | 1.7 | 83.8 |
| lists_query | 26 | 4 | 84.62 | 1.7 | 85.5 |
| play_radio | 34 | 4 | 88.24 | 1.7 | 87.2 |
| weather_query | 65 | 4 | 93.85 | 1.7 | 88.9 |
| email_querycontact | 10 | 3 | 70.00 | 1.3 | 90.2 |
| iot_hue_lightdim | 11 | 3 | 72.73 | 1.3 | 91.5 |

(top 15 of 43 by error mass; the full table is in `decomposition.json`)

## 3. The smallest label sets that own 50 % and 80 % of the errors

Descending greedy on error count (optimal for a coverage-by-count objective); `of` counts the labels that carry at least one error.

**Pooled.**

- scenarios, 50 %: **3** of 18 with errors (51.2 % covered, 246 errors): `general`, `calendar`, `qa`
- scenarios, 80 %: **8** of 18 with errors (80.2 % covered, 385 errors): `general`, `calendar`, `qa`, `play`, `email`, `social`, `lists`, `news`
- actions, 50 %: **3** of 42 with errors (52.5 % covered, 297 errors): `query`, `quirky`, `factoid`
- actions, 80 %: **12** of 42 with errors (81.3 % covered, 460 errors): `query`, `quirky`, `factoid`, `music`, `set`, `recipe`, `post`, `order`, `volume_mute`, `remove`, `sendemail`, `audiobook`
- intents, 50 %: **5** of 56 with errors (50.0 % covered, 310 errors): `general_quirky`, `calendar_query`, `qa_factoid`, `play_music`, `calendar_set`
- intents, 80 %: **20** of 56 with errors (80.5 % covered, 499 errors): `general_quirky`, `calendar_query`, `qa_factoid`, `play_music`, `calendar_set`, `news_query`, `cooking_recipe`, `social_post`, `datetime_query`, `takeaway_order`, `lists_query`, `audio_volume_mute`, `email_query`, `music_query`, `email_sendemail`, `weather_query`, `play_audiobook`, `play_radio`, `transport_query`, `qa_definition`

**TRAIN Fold A (1,080 rows).**

- scenarios, 50 %: **5** of 18 with errors (55.5 % covered, 76 errors): `general`, `social`, `calendar`, `news`, `qa`
- scenarios, 80 %: **10** of 18 with errors (81.8 % covered, 112 errors): `general`, `social`, `calendar`, `news`, `qa`, `audio`, `cooking`, `lists`, `email`, `music`
- actions, 50 %: **4** of 30 with errors (53.9 % covered, 96 errors): `query`, `quirky`, `factoid`, `post`
- actions, 80 %: **12** of 30 with errors (80.9 % covered, 144 errors): `query`, `quirky`, `factoid`, `post`, `order`, `recipe`, `volume_mute`, `set`, `locations`, `createoradd`, `music`, `ticket`
- intents, 50 %: **8** of 43 with errors (51.6 % covered, 99 errors): `general_quirky`, `qa_factoid`, `news_query`, `social_post`, `audio_volume_mute`, `calendar_query`, `cooking_recipe`, `takeaway_order`
- intents, 80 %: **21** of 43 with errors (81.2 % covered, 156 errors): `general_quirky`, `qa_factoid`, `news_query`, `social_post`, `audio_volume_mute`, `calendar_query`, `cooking_recipe`, `takeaway_order`, `music_query`, `social_query`, `datetime_query`, `lists_query`, `recommendation_locations`, `alarm_set`, `audio_volume_other`, `lists_createoradd`, `play_music`, `transport_ticket`, `weather_query`, `alarm_query`, `calendar_set`

**ROLL-1 R01C (625 rows, delivered answers).**

- scenarios, 50 %: **4** of 18 with errors (52.8 % covered, 84 errors): `general`, `calendar`, `play`, `qa`
- scenarios, 80 %: **10** of 18 with errors (83.0 % covered, 132 errors): `general`, `calendar`, `play`, `qa`, `news`, `music`, `email`, `social`, `cooking`, `lists`
- actions, 50 %: **3** of 31 with errors (53.9 % covered, 97 errors): `query`, `quirky`, `factoid`
- actions, 80 %: **10** of 31 with errors (80.0 % covered, 144 errors): `query`, `quirky`, `factoid`, `music`, `recipe`, `order`, `post`, `sendemail`, `volume_mute`, `volume_up`
- intents, 50 %: **6** of 42 with errors (52.1 % covered, 101 errors): `general_quirky`, `qa_factoid`, `calendar_query`, `play_music`, `cooking_recipe`, `news_query`
- intents, 80 %: **18** of 42 with errors (80.4 % covered, 156 errors): `general_quirky`, `qa_factoid`, `calendar_query`, `play_music`, `cooking_recipe`, `news_query`, `datetime_query`, `music_query`, `social_post`, `takeaway_order`, `transport_query`, `audio_volume_mute`, `audio_volume_up`, `email_sendemail`, `lists_query`, `iot_hue_lightchange`, `play_audiobook`, `takeaway_query`

**DEV-2000-ADDED (1,000 rows).**

- scenarios, 50 %: **2** of 11 with errors (51.6 % covered, 95 errors): `calendar`, `general`
- scenarios, 80 %: **4** of 11 with errors (85.3 % covered, 157 errors): `calendar`, `general`, `qa`, `play`
- actions, 50 %: **3** of 21 with errors (54.8 % covered, 114 errors): `quirky`, `query`, `factoid`
- actions, 80 %: **6** of 21 with errors (80.8 % covered, 168 errors): `quirky`, `query`, `factoid`, `music`, `set`, `definition`
- intents, 50 %: **4** of 28 with errors (60.3 % covered, 141 errors): `general_quirky`, `calendar_query`, `qa_factoid`, `calendar_set`
- intents, 80 %: **9** of 28 with errors (82.1 % covered, 192 errors): `general_quirky`, `calendar_query`, `qa_factoid`, `calendar_set`, `play_music`, `email_query`, `qa_definition`, `play_audiobook`, `email_sendemail`

## 4. Confusion structure

### 4.1 Pooled

620 joint errors over 324 distinct (gold, predicted) pairs. Within-scenario (right scenario, wrong action): **140** (22.6 %); cross-scenario: **477** (76.9 %; of which same action 54, different action 423); unparsed: 3 (0.5 %). Catch-all `general_quirky`: predicted IN error on 20 rows (3.2 % of joint errors), gold `general_quirky` missed OUT on 114 rows (18.4 %).

| gold intent | predicted intent | kind | count | share % | cumulative % |
| --- | --- | --- | ---: | ---: | ---: |
| `general_quirky` | `qa_factoid` | cross-scenario | 24 | 3.9 | 3.9 |
| `calendar_query` | `recommendation_events` | cross-scenario | 17 | 2.7 | 6.6 |
| `general_quirky` | `qa_definition` | cross-scenario | 11 | 1.8 | 8.4 |
| `takeaway_order` | `takeaway_query` | within-scenario | 10 | 1.6 | 10.0 |
| `general_quirky` | `recommendation_locations` | cross-scenario | 9 | 1.5 | 11.5 |
| `general_quirky` | `general_joke` | within-scenario | 8 | 1.3 | 12.7 |
| `play_music` | `music_query` | cross-scenario | 8 | 1.3 | 14.0 |
| `transport_query` | `transport_ticket` | within-scenario | 8 | 1.3 | 15.3 |
| `play_music` | `music_likeness` | cross-scenario | 7 | 1.1 | 16.5 |
| `play_music` | `music_play_music` | cross-scenario | 7 | 1.1 | 17.6 |
| `qa_factoid` | `recommendation_events` | cross-scenario | 7 | 1.1 | 18.7 |
| `qa_factoid` | `transport_query` | cross-scenario | 7 | 1.1 | 19.8 |
| `calendar_query` | `datetime_query` | cross-scenario | 6 | 1.0 | 20.8 |
| `calendar_set` | `alarm_set` | cross-scenario | 6 | 1.0 | 21.8 |
| `datetime_query` | `datetime_convert` | within-scenario | 6 | 1.0 | 22.7 |
| `calendar_query` | `alarm_query` | cross-scenario | 5 | 0.8 | 23.5 |
| `general_quirky` | `audio_volume_up` | cross-scenario | 5 | 0.8 | 24.4 |
| `general_quirky` | `weather_query` | cross-scenario | 5 | 0.8 | 25.2 |
| `play_music` | `play_radio` | within-scenario | 5 | 0.8 | 26.0 |
| `qa_factoid` | `music_query` | cross-scenario | 5 | 0.8 | 26.8 |
| `transport_ticket` | `transport_query` | within-scenario | 5 | 0.8 | 27.6 |
| `audio_volume_other` | `audio_volume_up` | within-scenario | 4 | 0.6 | 28.2 |
| `calendar_query` | `calendar_set` | within-scenario | 4 | 0.6 | 28.9 |
| `calendar_query` | `recommendation_events_query` | cross-scenario | 4 | 0.6 | 29.5 |
| `calendar_set` | `calendar_query` | within-scenario | 4 | 0.6 | 30.2 |

**Reading.** The catch-all is a sink of GOLD, not of predictions: gold `general_quirky` is missed on 114 rows (18.4 % of all joint errors, exact 16.8 % on 137 rows), while `general_quirky` is over-predicted on only 20 rows. The largest single pair owns 3.9 % of the joint errors; 216 of the 324 pairs occur exactly once and pairs of one or two rows carry 310 errors (50.0 % of the mass). Cross-scenario errors are 76.9 % of the joint errors on the pooled rosters.

### 4.2 TRAIN Fold A (1,080 rows)

192 joint errors over 138 distinct (gold, predicted) pairs. Within-scenario (right scenario, wrong action): **55** (28.6 %); cross-scenario: **136** (70.8 %; of which same action 14, different action 122); unparsed: 1 (0.5 %). Catch-all `general_quirky`: predicted IN error on 2 rows (1.0 % of joint errors), gold `general_quirky` missed OUT on 34 rows (17.7 %).

| gold intent | predicted intent | kind | count | share % | cumulative % |
| --- | --- | --- | ---: | ---: | ---: |
| `takeaway_order` | `takeaway_query` | within-scenario | 7 | 3.6 | 3.6 |
| `general_quirky` | `qa_factoid` | cross-scenario | 6 | 3.1 | 6.8 |
| `audio_volume_other` | `audio_volume_up` | within-scenario | 4 | 2.1 | 8.9 |
| `calendar_query` | `recommendation_events` | cross-scenario | 4 | 2.1 | 10.9 |
| `general_quirky` | `general_joke` | within-scenario | 4 | 2.1 | 13.0 |
| `general_quirky` | `audio_volume_up` | cross-scenario | 3 | 1.6 | 14.6 |
| `general_quirky` | `news_query` | cross-scenario | 3 | 1.6 | 16.1 |
| `general_quirky` | `qa_definition` | cross-scenario | 3 | 1.6 | 17.7 |
| `music_query` | `music_likeness` | within-scenario | 3 | 1.6 | 19.3 |
| `news_query` | `audio_volume_up` | cross-scenario | 3 | 1.6 | 20.8 |
| `qa_factoid` | `recommendation_locations` | cross-scenario | 3 | 1.6 | 22.4 |
| `recommendation_locations` | `takeaway_query` | cross-scenario | 3 | 1.6 | 24.0 |

### 4.3 ROLL-1 R01C (625 rows, delivered answers)

194 joint errors over 135 distinct (gold, predicted) pairs. Within-scenario (right scenario, wrong action): **35** (18.0 %); cross-scenario: **159** (82.0 %; of which same action 14, different action 145); unparsed: 0 (0.0 %). Catch-all `general_quirky`: predicted IN error on 13 rows (6.7 % of joint errors), gold `general_quirky` missed OUT on 37 rows (19.1 %).

| gold intent | predicted intent | kind | count | share % | cumulative % |
| --- | --- | --- | ---: | ---: | ---: |
| `general_quirky` | `qa_factoid` | cross-scenario | 8 | 4.1 | 4.1 |
| `general_quirky` | `recommendation_locations` | cross-scenario | 7 | 3.6 | 7.7 |
| `play_music` | `music_play_music` | cross-scenario | 7 | 3.6 | 11.3 |
| `transport_query` | `transport_ticket` | within-scenario | 5 | 2.6 | 13.9 |
| `calendar_query` | `recommendation_events_query` | cross-scenario | 4 | 2.1 | 16.0 |
| `datetime_query` | `datetime_convert` | within-scenario | 4 | 2.1 | 18.0 |
| `calendar_query` | `recommendation_events` | cross-scenario | 3 | 1.5 | 19.6 |
| `cooking_recipe` | `cooking_query` | within-scenario | 3 | 1.5 | 21.1 |
| `general_quirky` | `music_query` | cross-scenario | 3 | 1.5 | 22.7 |
| `general_quirky` | `qa_definition` | cross-scenario | 3 | 1.5 | 24.2 |
| `general_quirky` | `qa_maths` | cross-scenario | 3 | 1.5 | 25.8 |
| `news_query` | `general_quirky` | cross-scenario | 3 | 1.5 | 27.3 |

### 4.4 DEV-2000-ADDED (1,000 rows)

234 joint errors over 134 distinct (gold, predicted) pairs. Within-scenario (right scenario, wrong action): **50** (21.4 %); cross-scenario: **182** (77.8 %; of which same action 26, different action 156); unparsed: 2 (0.9 %). Catch-all `general_quirky`: predicted IN error on 5 rows (2.1 % of joint errors), gold `general_quirky` missed OUT on 43 rows (18.4 %).

| gold intent | predicted intent | kind | count | share % | cumulative % |
| --- | --- | --- | ---: | ---: | ---: |
| `calendar_query` | `recommendation_events` | cross-scenario | 10 | 4.3 | 4.3 |
| `general_quirky` | `qa_factoid` | cross-scenario | 10 | 4.3 | 8.5 |
| `calendar_set` | `alarm_set` | cross-scenario | 6 | 2.6 | 11.1 |
| `calendar_query` | `alarm_query` | cross-scenario | 5 | 2.1 | 13.2 |
| `general_quirky` | `qa_definition` | cross-scenario | 5 | 2.1 | 15.4 |
| `play_music` | `music_likeness` | cross-scenario | 5 | 2.1 | 17.5 |
| `play_music` | `music_query` | cross-scenario | 5 | 2.1 | 19.7 |
| `calendar_query` | `calendar_set` | within-scenario | 4 | 1.7 | 21.4 |
| `calendar_set` | `calendar_query` | within-scenario | 4 | 1.7 | 23.1 |
| `general_quirky` | `general_joke` | within-scenario | 4 | 1.7 | 24.8 |
| `general_quirky` | `weather_query` | cross-scenario | 4 | 1.7 | 26.5 |
| `play_music` | `play_radio` | within-scenario | 4 | 1.7 | 28.2 |

## 5. Oracle arithmetic to 95 %

**This section is an oracle framing.** Each row assumes that EVERY row of the named top-k labels (sorted by the error mass they own) is answered correctly and nothing else changes; it is the ceiling of a perfect repair of those labels, not a forecast. `k to reach target` is the number of labels that must be perfected for joint accuracy to reach the target.

**Pooled.** rows 2705, correct 2085, errors 620; joint accuracy 77.0795; gap to 95 % = **17.92 points**; reaching the target needs 2570 correct rows, i.e. **485 of the 620 errors (78.2 %) removed**.

| top-k fixed entirely (oracle) | k=1 | k=2 | k=3 | k=5 | k=8 | k=10 | k=15 | k=20 | k=30 | k to reach target | labels with errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| gold intents | 81.29 | 83.55 | 85.80 | 88.54 | 90.57 | 91.61 | 93.83 | 95.53 | 97.71 | **19** | 56 |
| (gold, predicted) pairs | 77.97 | 78.60 | 79.00 | 79.70 | 80.59 | 81.11 | 82.29 | 83.22 | 84.73 | **189** | 324 |
| gold actions (joint errors) | 83.33 | 87.54 | 89.80 | 92.72 | 94.49 | 95.34 | 96.97 | 98.04 | 99.37 | **10** | 42 |
| gold scenarios (joint errors) | 81.29 | 84.95 | 87.69 | 91.31 | 93.90 | 95.49 | 98.82 | -- | -- | **10** | 18 |

**TRAIN Fold A (1,080 rows).** rows 1080, correct 888, errors 192; joint accuracy 82.2222; gap to 95 % = **12.78 points**; reaching the target needs 1026 correct rows, i.e. **138 of the 192 errors (71.9 %) removed**.

| top-k fixed entirely (oracle) | k=1 | k=2 | k=3 | k=5 | k=8 | k=10 | k=15 | k=20 | k=30 | k to reach target | labels with errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| gold intents | 85.37 | 86.57 | 87.50 | 89.17 | 91.39 | 92.50 | 94.63 | 96.39 | 98.61 | **16** | 43 |
| (gold, predicted) pairs | 82.87 | 83.43 | 83.80 | 84.54 | 85.37 | 85.93 | 87.22 | 88.15 | 90.00 | **84** | 138 |
| gold actions (joint errors) | 87.13 | 90.28 | 91.48 | 93.15 | 95.28 | 96.11 | 97.78 | 98.80 | 100.00 | **8** | 30 |
| gold scenarios (joint errors) | 85.37 | 86.85 | 88.24 | 90.65 | 93.61 | 95.28 | 98.52 | -- | -- | **10** | 18 |

**ROLL-1 R01C (625 rows, delivered answers).** rows 625, correct 431, errors 194; joint accuracy 68.9600; gap to 95 % = **26.04 points**; reaching the target needs 594 correct rows, i.e. **163 of the 194 errors (84.0 %) removed**.

| top-k fixed entirely (oracle) | k=1 | k=2 | k=3 | k=5 | k=8 | k=10 | k=15 | k=20 | k=30 | k to reach target | labels with errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| gold intents | 74.88 | 77.44 | 79.84 | 83.52 | 87.20 | 89.12 | 92.48 | 94.72 | 97.92 | **21** | 42 |
| (gold, predicted) pairs | 70.24 | 71.36 | 72.48 | 73.92 | 75.52 | 76.48 | 78.72 | 80.32 | 83.20 | **104** | 135 |
| gold actions (joint errors) | 78.08 | 84.00 | 86.56 | 90.24 | 92.80 | 94.08 | 96.32 | 97.92 | 99.84 | **12** | 31 |
| gold scenarios (joint errors) | 74.88 | 78.08 | 80.80 | 84.96 | 89.60 | 92.48 | 98.24 | -- | -- | **12** | 18 |

**DEV-2000-ADDED (1,000 rows).** rows 1000, correct 766, errors 234; joint accuracy 76.6000; gap to 95 % = **18.40 points**; reaching the target needs 950 correct rows, i.e. **184 of the 234 errors (78.6 %) removed**.

| top-k fixed entirely (oracle) | k=1 | k=2 | k=3 | k=5 | k=8 | k=10 | k=15 | k=20 | k=30 | k to reach target | labels with errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| gold intents | 80.90 | 84.70 | 87.90 | 93.10 | 95.30 | 96.20 | 98.00 | 99.20 | 100.00 | **8** | 28 |
| (gold, predicted) pairs | 77.60 | 78.60 | 79.20 | 80.20 | 81.60 | 82.40 | 84.40 | 86.00 | 88.20 | **84** | 134 |
| gold actions (joint errors) | 82.50 | 86.80 | 90.00 | 95.20 | 97.20 | 98.10 | 99.40 | 99.90 | -- | **5** | 21 |
| gold scenarios (joint errors) | 83.60 | 87.90 | 92.20 | 97.80 | 99.40 | 99.90 | -- | -- | -- | **4** | 11 |

**Consequence, TRAIN Fold A (the 12.78 points).** The target needs 138 of the 192 joint errors removed (71.9 %). A perfect action decision inside the correct scenario -- every one of the 55 action-only rows repaired -- lifts joint accuracy by 5.09 points to 87.31, the scenario-exact ceiling, and leaves 7.69 of the 12.78 points that only cross-scenario repairs can close. By labels: perfecting the top 16 gold intents of the 43 that carry errors reaches the target; so does perfecting the top 84 of 138 confusion pairs, every joint error of the top 8 of 30 gold actions, or of the top 10 of 18 gold scenarios. The top five intents together move Fold A only to 89.17.

**Consequence, pooled.** 485 of 620 joint errors (78.2 %) must go. Perfecting the top 19 gold intents of 56 with errors would do it; so would the top 189 of 324 confusion pairs, every joint error of the top 10 gold actions, or of the top 10 gold scenarios. The error is broad, not concentrated: no handful of labels reaches the target, the tail of one- and two-row pairs is a large share of the mass (section 4), and a perfect within-scenario action decision closes between 22 % and 40 % of the gap depending on the roster. Any route to 95 has to move rows across scenarios -- the intent decision as a whole -- on most intents at once, not repair a few named confusions or the action label alone.

## 6. Appendix: ROLL-1's five raw Solver samples per row (parse-derived, not official flags)

3125 samples (5 per row x 625 rows): sample-level scenario 74.40 %, action 70.72 %, joint 68.48 %. Rows with at least one correct sample: **440** of 625 (70.40 %); rows with all 5 correct: 413; rows with NO correct sample: **185** (29.60 %). The delivered answer on the same rows reads 68.9600 % (section 0), so the best-of-five oracle ceiling is 1.44 points above the delivered path and still short of the target on this roster.

Top sample-level joint-intent error owners:

| intent | rows | errors | exact % | error share % | cumulative % |
| --- | ---: | ---: | ---: | ---: | ---: |
| general_quirky | 205 | 184 | 10.24 | 18.7 | 18.7 |
| qa_factoid | 165 | 81 | 50.91 | 8.2 | 26.9 |
| calendar_query | 110 | 75 | 31.82 | 7.6 | 34.5 |
| play_music | 90 | 61 | 32.22 | 6.2 | 40.7 |
| news_query | 180 | 52 | 71.11 | 5.3 | 46.0 |
| cooking_recipe | 155 | 50 | 67.74 | 5.1 | 51.1 |
| datetime_query | 135 | 33 | 75.56 | 3.4 | 54.4 |
| social_post | 135 | 33 | 75.56 | 3.4 | 57.8 |
| music_query | 90 | 32 | 64.44 | 3.2 | 61.0 |
| takeaway_order | 115 | 30 | 73.91 | 3.0 | 64.1 |
| transport_query | 105 | 27 | 74.29 | 2.7 | 66.8 |
| audio_volume_up | 75 | 22 | 70.67 | 2.2 | 69.0 |

(top 12 of 52 by error mass; the full table is in `decomposition.json`)

Within-scenario share of sample-level joint errors: 18.8 %; cross-scenario 80.3 %; unparsed 0.9 %.

## 7. Artefacts

Written under `SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-INTENT-ERROR-DECOMPOSITION-V1/`:

| file | sha256 |
| --- | --- |
| `decomposition.json` | `24d0fa4a313fcdf263939ce626fefcaef3ccf197641f9daa067559da0f1407c8` |

Sealed inputs (read-only, verified):

| input | sha256 |
| --- | --- |
| `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1` outputs | `2dcaa925ab7dad77e5938002d5606189ff7f644a94ade5b7265060e94d3ae17f` |
| `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1` scores | `9f3047fa77a868cb6c8cd72827c0358996288b12cb976a682a960bde5eda707c` |
| `docs/receipts/rosters/slurp-evo-fold-a-v2.json` | `1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d` |
| `SAEA-SLURP-STAGE3-ROLLOUT-R01-V1` outputs | `e27faef7c7100fe66e82222f36a17dba6a8b9a5c2a0db7df83937a1e0175df0c` |
| `SAEA-SLURP-STAGE3-ROLLOUT-R01-V1` scores | `2c40964adafafeed40fcd9215b25122f0e0d9365ba2f3bc92f1caf922d395849` |
| `docs/receipts/rosters/slurp-stage3-construction-r01c.json` | `e8abc65ba4626cccb4aae9d2eb1bd73f077a6e9a407b3dba9c18bbe4c03eeddd` |
| `SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1` outputs | `41ebcea4d13ef779e51cdf6c69a4210194c842886db83e892fa7cc43cf053909` |
| `SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1` scores | `1ac4402afce13528d1c2debab1a468f5399c85ff3c6dc7883cd4d995bd2a2b75` |
| `docs/receipts/rosters/slurp-dev-2000-added-v1.json` | `f78dd8ad2894b1fd02bfe6050e39e3fb2c5d178a649e5d20e85ea4ecf4b8dc58` |
| gold metadata `devel` (8690 records) | `00d346b183ecc2d160853cd3dc20e8ccd207d9e1809cf6e2c05182076bd0ecc9` |
| gold metadata `train` (50628 records) | `4a05a3de6c7f028aff298c4a90196e6a3fecd1938d96fb1c125d6fd10d5e301e` |

Generated 2026-09-27T05:09:17+00:00 by `slurp-intent-error-decomposition-v1`; the only non-deterministic bytes in this note are on this line.
