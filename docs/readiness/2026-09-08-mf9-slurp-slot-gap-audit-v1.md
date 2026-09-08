# MF-9 — the SLURP slot-filling gap audit (2026-09-08)

Row id `SAEA-SLURP-MF9-SLOT-GAP-AUDIT-V1`, profile `model-free-check`.
Receipts: `docs/checks/speech-aware-evidence-acquisition/2026-09-08-mf9-slurp-slot-gap-audit/`.
**Zero model, GPU, tool, embedding, network and audio-decode contacts.**

## 0. The question, and what this note is

The owner, 2026-09-08: *our SLU-F1, and slot filling especially, does not align with the industry
best — is there an improvement plan?*

This note answers it with numbers rather than with a plan: it decomposes the loss of the study's
**admitted** slot arm, prices each module that could close part of it, and states the reachable
number honestly. **It admits nothing, promotes nothing and preregisters no cell.** Where a module
clears its own bar the note says so and names the owner decision it would need; it does not take
that decision.

The arm under the microscope is **KC-S1b** — `SAEA-SLURP-KC-S1B-SLOTS-SCHEMA-DEV1000-V1`, sealed
manifest sha256 `088c9307…fe08`, SLU-F1 **44.35** on the scenario-stratified DEV-1000 roster
(`docs/readiness/2026-09-05-slurp-slot-stage-kc-s1-v1-verdict.md`). Every number below is computed
from its sealed bytes and the pinned official `evaluate.py`.

### 0.1 Boundary, stated before the first read

* The held-out `test` split is never named, loaded, hashed or scored.
* **No devel `sentence` string is read anywhere.** `data.slurp.load_slurp_split` does not carry
  one, and this audit does not open the field.
* DEV **gold entity annotations** do enter, and only on the **scoring side** — the same loader,
  the same call, the same place the official scorer already reads them. The precedent is the
  legal-label projection v2 verdict, which re-scored sealed rows through a scoring-side transform
  and was accepted as such. They are an audit statistic and a metric ingredient, **never a
  mechanism input**.
* The value-projection judge of section 2 is mined from **TRAIN alone**;
  `reproduction.slurp_value_projection.load_value_projection_inventory` refuses any other split by
  name, and the loader it calls has no `split` parameter at all.
* TRAIN gold text is read as **knowledge inventory** — construction data under the study's
  split-usage philosophy, already the source of every knowledge receipt in this repository.
* No new speech identity opens. Every DEV-1000 row here has already been contacted.
* The one subprocess this audit runs is the **pinned official SLURP `evaluate.py`**
  (commit `8eb1654…311f1`, `~/.venvs/slurp-official-eval`, used and never modified) — the scorer,
  not a model.

### 0.2 Identity anchors, checked before any new number was trusted

Fail-closed: the read raises rather than reports if the sealed bytes stop reproducing a published
verdict.

| anchor | published | reproduced |
|---|---|---|
| KC-S1b entities strict / Word-F1 / Char-F1 / **SLU-F1**, sealed manifest through `core.scoring_batch` | 31.37 / 41.58 / 47.51 / **44.35** | **identical** |
| the same, from a **re-emitted** canonical prediction envelope | 31.37 / 41.58 / 47.51 / **44.35** | **identical** |
| SLU-F1 rebuilt from the port's own per-sample TP/FP/FN ingredients | 44.35 | **44.3503** |
| KC-S1b schema blocks: full-schema fallback rows / distinct intents (section 3) | 42 / 58 | **42 / 58** |
| MF-7b filler recall@5, sealed speech key, NEW500 / pooled (section 4) | 43.46 / 41.90 | **43.46 / 41.90** |

The re-emission anchor is what licenses every counterfactual below: a parsed prediction re-written
as `{"scenario", "action", "entities"}` and scored again returns **the same four entity columns to
the last decimal**, so a counterfactual that changes exactly one field changes exactly one thing.

---

## 1. Where KC-S1b's 44.35 actually goes

Receipt: `loss-decomposition.json`.

### 1.0 The arithmetic that makes this a decomposition

The official SLU-F1 is `2·TP / (2·TP + FP + FN)` over the **sum** of the word-distance and
char-distance blocks. So a corpus's **loss mass is exactly `FP + FN`** summed over both blocks, and
every unit of it belongs to exactly one prediction or one gold mention. Measured on KC-S1b:

* true-positive mass **846.0**, loss mass **2,123.085**, and `2·846 / (2·846 + 2123.085)` is
  **44.3503** — the published 44.35.
* 950 gold mentions, **682 predicted mentions**, 397 rows (39.7 %) predicting no entity at all,
  3 unparsed rows. All four reproduce the KC-S1b verdict's own section 5.

### 1.1 The decomposition

| # | category | what it is | mass | **share of the loss** | count |
|---|---|---|---|---|---|
| (b) | **missing** | a gold mention with no type-matching prediction at all | 964.0 | **45.41 %** | 482 mentions |
| (e) | **surface form** | right type, right span matched, **wrong surface string** — the partial word/char credit the metric charges | 551.085 | **25.96 %** | 167 pairs |
| (c) | **spurious** | a predicted mention whose type no unmatched gold carries | 428.0 | **20.16 %** | 214 mentions |
| (d) | **wrong TYPE, right value** | an unmatched prediction and an unmatched gold carrying the **same value** under different types | 180.0 | **8.48 %** | 45 pairs |
| (a) | **intent errors** | scenario/action wrong | **0.0** | **0.00 %** | — |

256 matched pairs are already exact and cost nothing. The four categories sum to 2,123.085 — the
corpus mass, to the last unit; the read raises if they do not.

### 1.2 (a) Intent errors cost this metric **nothing**, and the counterfactual proves it

The scoring-side counterfactual the question asks for: the **same sealed entity outputs**
re-scored with the row's **gold** `(scenario, action)` substituted for whatever the response
carried. Stated as such — it reads gold on the scoring side and is never a runtime design.

| view | scenario | action | intent | entities strict | Word-F1 | Char-F1 | **SLU-F1** |
|---|---|---|---|---|---|---|---|
| KC-S1b as sealed | 36.00 | 33.30 | 32.10 | 31.37 | 41.58 | 47.51 | **44.35** |
| **gold intent substituted** | 99.70 | 99.70 | **99.70** | 31.37 | 41.58 | 47.51 | **44.35** |

**Delta 0.0000.** The official script feeds SLU-F1 the two distance blocks alone; the label columns
never touch it. So the honest answer to "how much SLU-F1 does the intent layer cost" is **zero,
directly** — and any plan that proposes to raise SLU-F1 by fixing intent has to say through which
channel. There is one, and it is measurable:

**The indirect channel — intent as the schema selector.** KC-S1b's per-intent block was chosen by
the sealed closed-list arm's own **unprojected** label.

| | rows | SLU-F1 on those rows |
|---|---|---|
| the block sent was the **gold intent's** | 714 | **47.12** |
| the block sent was **another intent's** | 286 | **36.05** |

An **11.07-point** spread. But the spread is not all causal: a row whose intent the core got wrong
is a row it heard less well, and it would have filled slots worse under any block. The part that
**is** attributable to block selection is small and countable: of 950 gold mentions, **81** have a
type that was **not listed in the block the row received**, and **51 of those 81** are listed in
the **gold intent's** block. So perfect intent narrowing hands the slot stage 51 gold mentions'
worth of newly-legal type space — 5.4 % of the gold mass, and an upper bound on what section 5's
rung 1 can buy through this channel.

### 1.3 Per slot type, ranked by lost mass

Top 20 of 53 types carrying loss. `exact` is matched pairs at zero distance; `surf` is matched
pairs paying distance; `swap` is (d); `miss` is (b); `spur` is (c), attributed to the **predicted**
type.

| entity type | gold | exact | surf | swap | miss | spur | mass | **share** |
|---|---|---|---|---|---|---|---|---|
| `date` | 159 | 32 | 11 | 6 | 110 | 4 | 274.64 | **12.94 %** |
| `place_name` | 118 | 35 | 16 | 11 | 56 | 5 | 231.23 | **10.89 %** |
| `time` | 67 | 7 | 27 | 2 | 31 | 9 | 188.24 | **8.87 %** |
| `person` | 56 | 10 | 10 | 10 | 26 | 10 | 132.30 | 6.23 % |
| `media_type` | 70 | 26 | 0 | 5 | 39 | 7 | 112.00 | 5.28 % |
| `event_name` | 42 | 1 | 7 | 0 | 34 | 1 | 88.61 | 4.17 % |
| `business_name` | 36 | 4 | 12 | 0 | 20 | 6 | 85.02 | 4.00 % |
| `food_type` | 42 | 13 | 10 | 1 | 18 | 6 | 83.15 | 3.92 % |
| `list_name` | 19 | 6 | 8 | 1 | 4 | **17** | 73.68 | 3.47 % |
| `player_setting` | 9 | 1 | 5 | 0 | 3 | 6 | 63.26 | 2.98 % |
| `transport_type` | 31 | 9 | 0 | 2 | 20 | 5 | 58.00 | 2.73 % |
| `news_topic` | 27 | 7 | 11 | 0 | 9 | 4 | 57.74 | 2.72 % |
| `weather_descriptor` | 27 | 4 | 0 | 0 | 23 | 3 | 52.00 | 2.45 % |
| `business_type` | 28 | 9 | 6 | 0 | 13 | 1 | 45.21 | 2.13 % |
| `device_type` | 22 | 12 | 2 | 1 | 7 | 8 | 42.13 | 1.98 % |
| `timeofday` | 22 | 4 | 3 | 1 | 14 | 0 | 41.07 | 1.93 % |
| `order_type` | 18 | 4 | 4 | 0 | 10 | 4 | 40.25 | 1.90 % |
| `alarm_type` | 2 | 1 | 0 | 0 | 1 | **18** | 38.00 | 1.79 % |
| `relation` | 14 | 3 | 3 | 0 | 8 | 3 | 29.87 | 1.41 % |
| `artist_name` | 14 | 6 | 5 | 0 | 3 | 2 | 29.15 | 1.37 % |

**Three types carry a third of the whole loss** — `date`, `place_name`, `time` at 32.70 % together
— and they fail in three different ways. `date` is a **recall** failure (110 of 159 gold mentions
never predicted at all). `time` is a **surface-form** failure (27 of 40 matched pairs pay
distance, and `time` has the worst exact rate of any large type: 7 of 67). `place_name` is mixed,
with the largest type-swap count of any type (11).

Two types are almost pure **over-generation**: `alarm_type` (2 gold mentions, 18 spurious) and
`transport_name` (1 gold, 12 spurious), plus `list_name` (19 gold, 17 spurious). The per-intent
schema tells the model these types exist for this intent; on these three it answers them when the
utterance did not.

### 1.4 What the surface-form mass is actually made of

The examples say it plainly, and most of them are not hearing failures:

| gold | predicted | word dist | char dist |
|---|---|---|---|
| `six am` | `six a m` | **1.0** | 0.143 |
| `three pm` | `three p m` | **1.0** | 0.111 |
| `ten am` | `ten a m` | **1.0** | 0.143 |
| `pf changs` | `p f changs` | **1.0** | 0.100 |
| `i will always love you` | `I Will Always Love You` | **1.0** | 0.227 |
| `hilary email issue` | `hillary email issue` | 0.333 | 0.053 |
| `wednesday` | `on wednesday` | **1.0** | 0.250 |
| `delivery` | `deliver` | **1.0** | 0.125 |
| `olive garden` | `the olive garden` | 0.500 | 0.250 |

Three separate normalization artefacts, all of them free to repair and none of them a hearing
error: **letter spacing** (`a m` for `am`), **casing** (the official script lower-cases the gold
side and deliberately does **not** lower-case the prediction —
`reproduction.slurp_scoring`'s module docstring records the asymmetry as fidelity, not a bug), and
**span padding** (`on wednesday`, `the olive garden`). A pure case difference costs a **word
distance of 1.0** — every word differs — which is why `i will always love you` pays as much as a
completely wrong answer would.

That is what section 2's judge is aimed at.

### 1.5 The ceilings, so nothing below is measured against 100

Each row removes ONE category and leaves the rest exactly as they are.

| counterfactual | SLU-F1 | gain |
|---|---|---|
| KC-S1b as it stands | **44.35** | — |
| every matched span carries the gold surface form | **51.84** | +7.49 |
| every spurious mention withheld | 49.95 | +5.60 |
| every type swap re-typed onto its gold | 49.07 | +4.72 |
| every missing gold mention answered exactly | **75.75** | **+31.40** |
| all four at once | 100.00 | +55.65 |

**Recall is the wall, and it is not close.** Answering the 482 gold mentions the arm never
attempts is worth four times what perfect normalization is worth, and more than the other three
categories combined. Every module priced in section 5 is scored against this table: a normalization
module cannot exceed +7.49, a constrained-decoding module cannot exceed +5.60, and only a module
that makes the arm **answer more slots** can reach the twenties.

### 1.6 Per population

| population | n | SLU-F1 | loss mass |
|---|---|---|---|
| pooled | 1,000 | 44.35 | 2,123.09 |
| prior-exposed OLD500 | 500 | 40.76 | 1,110.48 |
| **unexposed NEW500** | 500 | **47.82** | 1,012.61 |

The decision population is the unexposed NEW500, as it is for every SLURP cell in this study.
