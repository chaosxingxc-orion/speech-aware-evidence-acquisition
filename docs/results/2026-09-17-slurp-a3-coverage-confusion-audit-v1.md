# SLURP A3: coverage and confusion audit of the sealed TRAIN A anchor

Date: 2026-09-17. Root: Fable 5.1. Program: `docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md`
(Phase A, item A3). Zero model, ASR, encoder, tokenizer, scorer or server contacts; the repository
tree was not touched by the audit; no utterance text, transcript or filler was persisted.

Machine result: `analysis/SAEA-SLURP-A3-COVERAGE-CONFUSION-AUDIT-V1/result.json` under
`SPEECHRL_DATA_DIR`, SHA-256 cdce44cf29f14103e39e35138da0b25e72d1d759d87f71eb8a437f7232db7d6c;
join `join-v1.json` 37f61c5f84164ef5c4165767a6274fc8fc458500dfb3ab6ef5c28371e9d8d9cf; scripts
`a3-coverage-confusion-join-v1.py` bf8b722f… and `a3-coverage-confusion-tables-v1.py` 29c02371….
Before any table was read, the join reproduced the sealed candidate-set hashes and state ids for
all 1,080 rows (parser `rails.slurp_intent_hypotheses`, max 3), the official `parsed`,
`scenario_action_exact` and exact-slot counts, the 842 / 143 / 95 cohorts and the 100 / 60
persistence counts of the 2026-09-16 numeric inventory.

## T1. The 143 gold-candidate-missing rows

| Gold family | Rows | Own card supplied | Any candidate in the gold scenario | Gold proposed |
| --- | ---: | ---: | ---: | ---: |
| general_quirky (all general_*) | 34 | 0 | 9 | 0 |
| qa_* | 13 | 0 | 5 | 0 |
| social_* | 11 | 2 | 1 | 0 |
| play_* | 7 | 2 | 2 | 0 |

Supply on the 143: 33 supplied-but-missed, 110 with the gold card never in the request.
Candidate width 3 / 2 / 1 = 126 / 14 / 3. Scenario-level candidate recall (any candidate in the
gold scenario) is 28.0 % on the missing rows against 90.5 % on all 1,080 rows; by scenario it is
0.26 on `general` (0.58 over all rows), 0.38 `qa`, 0.09 `calendar`, 0.09 `social`, 0.00 `news`,
0.22 `lists`, 0.63 `music`, 0.00 `email`, 0.29 `play`, 0.00 `weather`.

Gold x delivered pairs with at least three rows: takeaway_order -> takeaway_query 5;
general_quirky -> general_joke 4, -> qa_definition 4, -> qa_factoid 4, -> audio_volume_up 3,
-> iot_cleaning 3, -> news_query 3; news_query -> audio_volume_up 3; transport_ticket ->
transport_query 3. Under gold general_quirky the candidate slots go to audio_volume_up 8,
qa_definition 7, general_greet 6, general_joke 6, music_likeness 6, music_query 5, qa_factoid 5,
weather_query 5.

## T2. The 95 covered-but-wrong rows

Gold rank among the candidates: rank 1 = 24, rank 2 = 54, rank 3 = 17 (rank 1 is gold on 818 of
the 842 correct rows). The delivered id was candidate rank 1 in 64 rows, rank 2 in 3, rank 3 in 2
and off the candidate list in 26. Top pairs: play_music -> music_play_music 8; datetime_query ->
datetime_convert 5; audio_volume_other -> audio_volume_up 4; play_radio -> play_play_radio 4;
audio_volume_mute -> audio_volume_up 3; play_audiobook -> play_play_audiobook 3; social_post ->
takeaway_query 3.

## T3. Confusion summary over all 1,080 rows (238 intent errors)

158 distinct error pairs; the top 30 cover 43.7 % of the errors; 74 errors are within-scenario,
157 cross-scenario, 7 unparsed. Sixty-three distinct delivered ids, five outside the legal 60.

| Gold -> delivered | n | Share | Within scenario | Covered / missing |
| --- | ---: | ---: | --- | --- |
| play_music -> music_play_music | 8 | 3.4 % | no | 8 / 0 |
| takeaway_order -> takeaway_query | 7 | 2.9 % | yes | 2 / 5 |
| general_quirky -> qa_factoid | 6 | 2.5 % | no | 2 / 4 |
| datetime_query -> datetime_convert | 5 | 2.1 % | yes | 5 / 0 |
| audio_volume_other -> audio_volume_up | 4 | 1.7 % | yes | 4 / 0 |
| calendar_query -> recommendation_events | 4 | 1.7 % | no | 2 / 2 |
| general_quirky -> general_greet | 4 | 1.7 % | yes | 2 / 2 |
| general_quirky -> general_joke | 4 | 1.7 % | yes | 0 / 4 |
| general_quirky -> qa_definition | 4 | 1.7 % | no | 0 / 4 |
| play_radio -> play_play_radio | 4 | 1.7 % | yes | 4 / 0 |
| transport_ticket -> transport_query | 4 | 1.7 % | yes | 1 / 3 |

Out-of-inventory delivered ids, all 20 rows errors (8.4 % of the error mass): music_play_music 9,
play_play_audiobook 5, play_play_radio 4, music_music_likeness 1, recommendation_locations_query 1.
The form is the scenario prefix duplicated into the action; 15 of the 20 repair to gold by
stripping the duplicate, and all 15 already had gold in the candidate set. Worst strata by
errors: general 38 (34 missing), play 25 (18 covered-wrong), social 20, calendar 15, qa 15.

## T4. Persistence across the anchor, maximum-five and broad/factored arms

The 100 persistent misses carry gold general_quirky 28, qa_factoid 8, news_query 7, social_post 6,
audio_volume_mute 4, calendar_query 4, music_settings 4; their own card was supplied in 13 and a
gold-scenario candidate present in 20. The 60 persistent covered-wrong rows have gold at rank
1 / 2 / 3 = 9 / 43 / 8; top pairs audio_volume_other -> audio_volume_up 4, audio_volume_mute ->
audio_volume_up 3, datetime_query -> datetime_convert 3, social_post -> takeaway_query 3.

## T5. Slot-contract detail (row level)

| Type | Gold rows | Omitted entirely | All exact | Partial / different | Gold mentions exact | Omission concentrates under |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| date | 135 | 81 (64 with correct intent) | 26 | 28 | 28 / 138 | weather_query 26, datetime_query 9, calendar_query 7, news_query 5, recommendation_events 5 |
| time | 72 | 19 | 7 | 46 | 8 / 76 | non-exact under alarm_set 18, datetime_convert 6, transport_taxi 4 |
| place_name | 92 | 22 | 26 | 44 | 30 / 100 | news_query 4, recommendation_locations 4, transport_query 4 |
| business_name | 51 | 13 | 8 | 30 | 8 / 52 | qa_currency, qa_stock, social_post, takeaway_query, transport_taxi (2 each) |
| person | 41 | 15 | 9 | 17 | 9 / 42 | email_sendemail 3, calendar_set 2 |
| event_name | 41 | 22 | 10 | 9 | 10 / 41 | calendar_query 5, calendar_set 3 |

More omission-dominated than date, outside the original M4b scope: media_type 38 / 57 rows
omitted, transport_type 25 / 36, business_type 22 / 29, order_type 19 / 22, relation 15 / 15
(0 of 16 mentions ever emitted).

## T6. Named fixes (upper bound = rows a fix can touch, not a predicted gain)

| Id | Fix | Axis / module | Rows | Evidence |
| --- | --- | --- | ---: | --- |
| FIX-1 | Append `general_quirky` as a standing Perception fallback candidate when absent | ORG / M4a | 34 | 34 missing rows are gold general_quirky; 25 carry no general_* candidate; 28 persist across all three arms; own card supplied in none |
| FIX-2 | qa_* versus general_quirky contrast, one-directional | ORG / M4a | 11 | 11 rows gold general_quirky delivered as qa_*; zero in the reverse direction; qa_* fills 27 candidate slots under gold general_quirky |
| FIX-3 | Repair delivered ids outside the 60-id inventory (duplicated scenario prefix) | USE / M3 | 20 | all 20 are intent errors; 15 repair to gold, all 15 with gold already among the candidates |
| FIX-4 | `date` contract: emit-when-spoken rule; widen to media_type, transport_type, business_type, order_type, relation | ORG / M4b | 81 | 81 / 135 gold-date rows emit no date; 64 already have the correct intent |
| FIX-5 | `time` contract: spoken-form representation rule | ORG / M4b | 46 | 46 / 72 rows emit a non-exact time filler; only 8 / 76 mentions exact |
| FIX-6 | Same-scenario action contrast cards (volume, datetime, iot hue, alarm) | ORG | 36 | 36 of 95 covered-wrong rows deliver a legal in-scenario id with the wrong action; gold at rank 2 in 28 |

Consequences for the program: FIX-3 joins the USE projection v3 (A1 is extended with it before
its decision); FIX-1 and FIX-2 define cell B4a; FIX-4 and FIX-5 define cell B4b with the widened
type list; FIX-6 is recorded as a later ORG candidate, not scheduled. Bounds are ceilings: an
appended fallback can still lose selection, and every fix needs its paired cell under the null
margin.
