# Cell W4: slot conventions (knowledge wave, owner decision 164)

Registered before contact 2026-09-27 at study commit `eb450736`; both cells **held**.
Nothing here authorises a flight, a flip or an admission entry. Development numbers only (owner decisions 28 and 86).

**What W4 is.** The retained AGREE arm (`SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1`, official SLU-F1 65.16 / intent 85.83 on TRAIN Fold A)
with ONE pin moved: `knowledge_stores.slot-contracts` from the released `slot-contracts-v2` store to
`slot-contracts-w4-v1` (release `c7bdeee6e0859fbba6bce79cd3d42347a5b74770f7564094e3d3a0edfe003fb0`, snapshot content `51d634cfcb398038377feca89d2783f59a705546390839e7cf4dd7d15ad3b9d6`). The new
store is v2 with **19 cards extended** (7,886 bytes in all) by three kinds of slot
convention the 2026-09-27 knowledge content audit found missing (K2 value vocabulary, K3 annotation scope, K4 span
extent), **mined only from the R01-excluded TRAIN exemplar pool** (8,554 utterances; no Fold A, Fold B, DEV or test
byte, no flight output). Every intent binding is byte-identical, so a card still reaches a row only when the row's
candidate intents bind it (W4 composes with W1's card selection), and the facet keys and candidate supply do not move.
Built model-free by `scripts/build_slurp_slot_conventions_w4.py` and `saea-driver prepare-semantic-knowledge`
(registration `docs/readiness/2026-09-27-slurp-slot-contracts-w4-preparation-registration-v1.json`; contacts model 0 / tool 0 / scorer 0).

**Primary metric.** Official pooled SLU-F1, intent accuracy the guard: owner decision 133 makes intent primary only
for intent-acting mechanisms; W4 acts on slots, so decision 115's shape holds.

**Declared expectation: NO-HARM.** From the measured analogue only (row 139): M4b moved SLU-F1 by +2.55 / +1.54
(first / replicate) over 349 FN items; W4 targets 301 FN items with
the card delivered, so the analogue expects **1.3285 to 2.2009 pp (mean 1.7647)** -- below the
2.5 pp benefit floor of this design at n = 1,080. The arm is therefore declared `admission` `no-harm`,
`harm_margin_pp` 1.2485 (SLU) with intent 0.9943 the guard, `expected_effect_pp` 0.0, `claims_benefit` false,
`replicate_run_id` `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1` (the knowledge wave's shared A/A, registered by the coordinator).

## K2 -- value vocabulary (pool statistics; closed = LOO value coverage >= 0.90; semi-closed = N90 <= 20)

| type | class | pool mentions | distinct | LOO coverage | N90 | listed | covered |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `business_name` | open | 229 | 134 | 0.563 | 112 | 0 | 0.000 |
| `business_type` | open | 115 | 44 | 0.730 | 33 | 0 | 0.000 |
| `date` | open | 1391 | 233 | 0.888 | 94 | 0 | 0.000 |
| `device_type` | open | 168 | 58 | 0.792 | 42 | 0 | 0.000 |
| `event_name` | open | 853 | 295 | 0.726 | 210 | 0 | 0.000 |
| `food_type` | open | 97 | 56 | 0.567 | 47 | 0 | 0.000 |
| `house_place` | semi-closed | 151 | 32 | 0.887 | 17 | 17 | 0.901 |
| `list_name` | open | 122 | 48 | 0.656 | 36 | 0 | 0.000 |
| `meal_type` | closed | 51 | 3 | 1.000 | 2 | 3 | 1.000 |
| `media_type` | open | 313 | 71 | 0.850 | 40 | 0 | 0.000 |
| `news_topic` | open | 119 | 78 | 0.496 | 67 | 0 | 0.000 |
| `order_type` | closed | 43 | 9 | 0.907 | 5 | 9 | 1.000 |
| `person` | open | 703 | 406 | 0.578 | 336 | 0 | 0.000 |
| `place_name` | open | 747 | 367 | 0.645 | 293 | 0 | 0.000 |
| `song_name` | open | 107 | 88 | 0.290 | 78 | 0 | 0.000 |
| `time` | open | 563 | 181 | 0.792 | 125 | 0 | 0.000 |
| `timeofday` | closed | 185 | 11 | 0.984 | 6 | 11 | 1.000 |
| `transport_agency` | closed | 30 | 3 | 0.967 | 1 | 3 | 1.000 |
| `transport_type` | closed | 219 | 8 | 0.986 | 2 | 8 | 1.000 |

Closed value lists (TRAIN annotation values): `meal_type`: dinner, lunch, breakfast; `order_type`: delivery, takeaway, deliver, take out, takeout, carryout, delivers, takeaways, to go; `timeofday`: morning, tonight, noon, afternoon, evening, this afternoon, night, this evening, next morning, this am, tonight 's; `transport_agency`: uber, ola, golden taxi; `transport_type`: train, taxi, cab, ride, trains, car, driving, metro. Semi-closed lists live in the store only.

## K3 -- annotation scope (spoken occurrences under the card's intents; tag rate >= 0.85 "tagged when spoken", <= 0.35 "usually left untagged"; >= 5 occurrences)

| type | values with evidence | spoken occurrences | tagged / untagged | tagged-when-spoken values (tagged/spoken) | usually-untagged values (tagged/spoken) |
| --- | ---: | ---: | --- | --- | --- |
| `business_name` | 12 | 119 | 96 / 23 | 15/15, 11/12, 9/9, 8/9, 7/7 | -- |
| `business_type` | 9 | 116 | 89 / 27 | 36/36, 15/16, 10/10 | 1/5 |
| `date` | 42 | 1583 | 1454 / 129 | 398/413, 176/178, 118/128, 75/75, 65/65 | 1/77 |
| `device_type` | 23 | 577 | 368 / 209 | 49/54, 34/38, 35/36, 31/31, 30/30 | 6/125, 5/51, 1/15, 1/7, 2/6 |
| `event_name` | 43 | 1657 | 766 / 891 | 281/305, 89/94, 55/63, 39/44, 25/29 | 1/360, 6/133, 2/90, 7/81, 8/49 |
| `food_type` | 4 | 40 | 37 / 3 | 14/16, 10/11, 8/8, 5/5 | -- |
| `house_place` | 10 | 196 | 175 / 21 | 59/63, 30/30, 24/24, 17/17, 10/10 | 2/8 |
| `list_name` | 8 | 142 | 110 / 32 | 28/30, 27/29, 26/27 | 1/6, 1/5 |
| `meal_type` | 2 | 50 | 48 / 2 | 27/28, 21/22 | -- |
| `media_type` | 16 | 607 | 266 / 341 | 76/79, 42/42, 25/28, 19/20, 19/19 | 5/157, 1/108, 1/25, 4/18, 3/12 |
| `news_topic` | 7 | 55 | 36 / 19 | 9/9, 8/8, 8/8 | 2/10, 1/7 |
| `order_type` | 5 | 47 | 39 / 8 | 14/14, 13/13 | -- |
| `person` | 31 | 438 | 276 / 162 | 60/62, 21/21, 17/17, 12/13, 10/10 | 1/124, 3/20 |
| `place_name` | 42 | 561 | 421 / 140 | 64/66, 23/23, 19/19, 14/15, 14/14 | 4/28, 6/18, 3/11, 2/6, 1/6 |
| `song_name` | 2 | 12 | 9 / 3 | -- | -- |
| `time` | 52 | 1188 | 936 / 252 | 59/65, 50/54, 48/53, 47/50, 44/44 | 8/105, 1/37, 1/8, 2/7, 1/6 |
| `timeofday` | 8 | 209 | 200 / 9 | 65/69, 50/51, 25/25, 19/21, 20/20 | -- |
| `transport_agency` | 1 | 27 | 27 / 0 | 27/27 | -- |
| `transport_type` | 5 | 236 | 213 / 23 | 166/175, 35/35, 8/8 | 2/10, 2/8 |

## K4 -- span extent (rules at >= 0.80 of >= 8 cases; words limited to function words and generic unit/head words)

| type | located mentions | rules (edge, word, side, count/cases) |
| --- | ---: | --- |
| `business_name` | 205 | trail `service` inside 20/20; lead `<preposition>` outside 135/136; trail `<preposition>` outside 25/25 |
| `business_type` | 115 | lead `a` outside 16/16; lead `the` outside 12/12; trail `<preposition>` outside 41/41 |
| `date` | 1310 | lead `this` inside 138/159; trail `week` inside 114/114; lead `the` outside 70/77 |
| `device_type` | 168 | lead `the` outside 89/89; trail `socket` inside 36/38; trail `cleaner` inside 32/32 |
| `event_name` | 820 | lead `my` outside 116/118; lead `the` outside 112/112; lead `a` outside 98/98 |
| `food_type` | 93 | lead `a` outside 13/13; lead `<preposition>` outside 19/19; trail `<preposition>` outside 15/15 |
| `house_place` | 151 | lead `the` outside 85/86; trail `room` inside 41/41; lead `my` outside 16/18 |
| `list_name` | 121 | trail `list` outside 83/91; lead `my` outside 53/54; lead `the` outside 19/19 |
| `meal_type` | 51 | lead `<preposition>` outside 25/25; trail `<preposition>` outside 19/19 |
| `media_type` | 307 | lead `my` outside 28/28; lead `the` outside 20/21; lead `a` outside 15/15 |
| `news_topic` | 113 | lead `the` outside 25/30; trail `news` outside 21/22; lead `<preposition>` outside 47/47 |
| `order_type` | 43 | -- |
| `person` | 621 | lead `<preposition>` outside 340/340; trail `<preposition>` outside 121/121 |
| `place_name` | 735 | lead `the` outside 73/84; trail `station` inside 8/8; lead `<preposition>` outside 538/538 |
| `song_name` | 103 | lead `song` outside 11/11; trail `<preposition>` outside 47/47 |
| `time` | 559 | trail `pm` inside 205/205; trail `am` inside 147/147; lead `the` outside 38/44 |
| `timeofday` | 184 | lead `the` outside 25/25; trail `afternoon` inside 10/10; trail `<preposition>` outside 39/39 |
| `transport_agency` | 30 | lead `an` outside 16/16; trail `<preposition>` outside 10/10 |
| `transport_type` | 216 | lead `a` outside 107/107; lead `the` outside 31/31; lead `next` outside 13/13 |

## Token cost and Fit

| phase | contacts | added tokens mean / max | realised prompt max (AGREE) | projected max |
| --- | ---: | --- | ---: | ---: |
| perception | 1080 | 0.0 / 0.0 | 3769 | 3769 |
| planner | 1099 | 725.3 / 1274.3 | 14561 | 15607 |
| reviewer | 1103 | 724.5 / 1274.3 | 14413 | 15459 |
| solver | 1103 | 724.5 / 1274.3 | 14426 | 15472 |

Per row: +2218.0 tokens mean (max 6520.4), 6.36 % of
the AGREE prompt volume; measured at 5.0067 characters per token on the AGREE
Solver. the projected widest realised request per phase (the sealed AGREE per-contact prompt tokens plus that contact's W4 byte delta at the measured ratio) stays below the live operational budget (24,576 slot - 3,072 reserve - 512 completion = 20,992): no realised request is projected to compact.

W1 has NOT landed (branch fable/w1 carries no commit beyond master at registration), so W4 is registered to fly ALONE on the AGREE form; it composes with W1 later without change (W4 only extends cards a row already receives). The audit's '226 tokens of headroom' is the PREFLIGHT operational margin measured by core.flight.cli check with its placeholder 4-bytes-per-token counter on the widest representative request; under the armed context_fit_policy compact-or-abstain a COMPACT_REQUIRED preflight with a non-negative PHYSICAL margin is recorded and proceeds (the AGREE and COMP-1 cells already read COMPACT_REQUIRED on the Solver), and only a negative physical margin refuses. The binding facts are therefore (a) the check's physical margin after W4 (folded in 'fit'), and (b) the realised requests, projected from the sealed AGREE trace, which stay far below the live budget (token_cost.compaction_projection).

| cell | phase | decision | rendered (4 B/token) | operational margin | physical margin |
| --- | --- | --- | ---: | ---: | ---: |
| arm | perception | COMPACT_REQUIRED | 21379 | -418 | 2654 |
| arm | reviewer | COMPACT_REQUIRED | 21242 | -281 | 2791 |
| arm | planner | COMPACT_REQUIRED | 21182 | -221 | 2851 |
| arm | solver | COMPACT_REQUIRED | 23207 | -2246 | 826 |
| smoke | perception | COMPACT_REQUIRED | 21378 | -417 | 2655 |
| smoke | reviewer | COMPACT_REQUIRED | 21242 | -281 | 2791 |
| smoke | planner | COMPACT_REQUIRED | 21181 | -220 | 2852 |
| smoke | solver | COMPACT_REQUIRED | 23207 | -2246 | 826 |

## Fold A offline estimate (the AGREE arm, types whose W4 card was delivered; counts)

| class | items |
| --- | ---: |
| K2 omission, gold value in the W4 list or tagged-when-spoken list | 74 |
| K2 wrong filler, gold listed, prediction not | 10 |
| K3 over-emission whose value is usually untagged | 6 |
| K4 containment wrong fillers (all) / fixed by a stated rule | 68 / 5 |
| RISK: exact true positives whose value is usually untagged | 2 |
| RISK: listed value spoken but untagged in gold | 42 |

Rows touched {"K2": 80, "K3": 6, "K4": 5, "risk_list": 41}; exact span-F1 oracle ceilings (pp) {"K2": 6.273, "K3": 0.167, "K4": 0.5097, "all": 6.9451}.

## Files

| file | what it holds |
| --- | --- |
| `../2026-09-27-slurp-stage3-w4-slot-conventions-fold-a-v1-preregistration.md` | the preregistration, with the `stage3_measurement` fence |
| `registered-facts-v1.json` | every model-free fact; the CANONICAL `stage3_measurement` |
| `conventions-tables-v1.json` | the K2/K3/K4 tables above (types, counts, closed-type values, schematic rules) |
| `protocol-registered-v1.json` | identities, hashes, the rule |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the smoke's plans |
| `analysis-recipe-v1.json` | the paired read; `run_ids.read` = `SAEA-SLURP-STAGE3-W4-FOLD-A-PAIRED-READ-V1` |
| `root-admission-draft-v1.json` | the receipt root mints with `scripts/flights/w4/w4_mint_receipt.py` |

**Sequence.** (1) The coordinator registers the shared A/A `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1` and the wave's campaign plan. (2) Root
countersigns the DRAFT rows (four flight rows; the READ row stays draft until the seal), mints `coordination/slurp-stage3-w4-fold-a-v1/root-admission-v1.json`
with `scripts/flights/w4/w4_mint_receipt.py`. (3) Flip with `scripts/flights/w4/w4_flip.sh` (smoke, then arm; minted
supplies must reproduce the AGREE digests). (4) Queue behind the np4 session (decision 77).

**Budgets.** Arm 11,880 generation contacts, 47,520 FIT endpoints, 33,930 speech seconds,
12.0 GPU hours; smoke 44 / 176 / 117 / 1.0 -- the AGREE arithmetic.
