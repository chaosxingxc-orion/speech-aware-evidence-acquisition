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

---

## 2. The value-projection judge, priced model-free

Receipt: `value-projection.json`. Rule: `reproduction.slurp_value_projection`, id
`slurp-value-projection-v1`, 21 unit tests.

### 2.1 The rule, stated exactly

> Project a predicted slot filler onto the nearest TRAIN surface form **of the same slot type**
> when the official scorer's own normalized character distance is at or below the threshold. The
> comparison string is the prediction case-folded with whitespace collapsed; ties break on the
> larger TRAIN mention count, then lexicographically. The rule never changes a slot type, never
> invents a filler, and never deletes a prediction.

It is the same-type sibling of the admitted legal-label projection, and it is scoring-side in the
same sense: it runs strictly between the parse and the official prediction file. Its inventory is
**4,157 distinct `(type, filler)` pairs over 55 types**, mined from TRAIN and only TRAIN
(`load_value_projection_inventory` refuses any other split by name; identity hash
`bd8f75ce…0315`).

**Two families, because the repair has two halves.**

* **`rule`** — the projection alone. A filler it does not move keeps its own bytes.
* **`normalized`** — the same rule over a **normalization floor**: a filler the projection does not
  move is still emitted case-folded with whitespace collapsed. The floor is free, needs no
  inventory at all, and exists because the official script lower-cases the gold side and
  deliberately does **not** lower-case the prediction side (section 1.4). A system choosing to emit
  the corpus's own surface convention is a system output choice, not a change to the scorer.

### 2.2 The sweep

Every arm is the complete 1,000-row roster through the pinned official `evaluate.py`, never
sharded. Paired deltas are per-sample official scores, stratified bootstrap N = 10,000,
seed 20260903, CI90, strata = gold scenario. The τ = 0.00 anchor is not a no-op: it fires only on an
exact match after case folding.

| family | τ | SLU-F1 | ΔSLU-F1 | ΔWord-F1 | ΔChar-F1 | Δentities strict | rows changed | values changed | saves | harms | CI90 pooled | CI90 NEW500 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rule | 0.00 | 44.43 | +0.08 | +0.13 | +0.03 | +0.37 | 4 | 4 | 4 | 0 | [+0.01, +0.16] | [+0.00, +0.11] |
| rule | 0.10 | 44.53 | +0.18 | +0.27 | +0.07 | +0.74 | 11 | 11 | 9 | 1 | [+0.06, +0.27] | [−0.02, +0.16] |
| rule | 0.15 | 44.89 | +0.54 | +0.84 | +0.16 | +2.33 | 27 | 27 | 24 | 1 | [+0.30, +0.66] | [+0.31, +0.81] |
| rule | 0.20 | 45.01 | +0.66 | +1.01 | +0.20 | +2.82 | 33 | 33 | 28 | 1 | [+0.37, +0.77] | [+0.39, +0.96] |
| rule | 0.25 | 44.94 | +0.59 | +0.92 | +0.17 | +2.94 | 47 | 47 | 31 | 7 | [+0.33, +0.74] | [+0.34, +0.96] |
| rule | 0.30 | 45.00 | +0.65 | +1.02 | +0.17 | +3.19 | 62 | 63 | 35 | 11 | [+0.31, +0.76] | [+0.31, +0.94] |
| rule | 0.35 | 45.06 | +0.71 | +1.15 | +0.14 | +3.19 | 77 | 79 | 40 | 17 | [+0.29, +0.78] | [+0.20, +0.90] |
| rule | 0.40 | 45.05 | +0.70 | +1.14 | +0.14 | +3.43 | 104 | 107 | 48 | 24 | [+0.29, +0.82] | [+0.12, +0.85] |
| normalized | 0.00 | 44.54 | +0.19 | +0.29 | +0.07 | +0.86 | 12 | 13 | 9 | **0** | [+0.07, +0.29] | [+0.03, +0.32] |
| normalized | 0.10 | 44.61 | +0.26 | +0.39 | +0.10 | +1.23 | 18 | 19 | 13 | 1 | [+0.12, +0.38] | [+0.03, +0.35] |
| normalized | 0.15 | 44.97 | +0.62 | +0.96 | +0.19 | +2.82 | 34 | 35 | 28 | 1 | [+0.37, +0.76] | [+0.39, +0.96] |
| **normalized** | **0.20** | **45.09** | **+0.74** | **+1.13** | **+0.23** | **+3.31** | **40** | **41** | **32** | **1** | **[+0.45, +0.87]** | **[+0.47, +1.10]** |
| normalized | 0.25 | 45.02 | +0.67 | +1.03 | +0.20 | +3.31 | 53 | 54 | 34 | 7 | [+0.38, +0.82] | [+0.40, +1.06] |
| normalized | 0.30 | 45.05 | +0.70 | +1.11 | +0.19 | +3.43 | 67 | 68 | 37 | 11 | [+0.36, +0.83] | [+0.36, +1.04] |
| normalized | 0.35 | **45.11** | +0.76 | +1.24 | +0.16 | +3.43 | 82 | 84 | 42 | 17 | [+0.34, +0.84] | [+0.26, +0.99] |
| normalized | 0.40 | 45.08 | +0.73 | +1.18 | +0.15 | +3.56 | 108 | 111 | 49 | 24 | [+0.30, +0.84] | [+0.12, +0.85] |

**The operating point is `normalized` at τ = 0.20**, not the arithmetic maximum at τ = 0.35. It
reaches within 0.02 SLU-F1 of the maximum, has the **tightest confidence interval in the table** on
both populations, and pays **one harm instead of seventeen**. Above 0.20 the rule starts rewriting
values that were merely unusual rather than merely mis-spelled, and every extra harm above that
point is a real answer destroyed.

At that point the branches are: **338 mentions already an exact TRAIN surface form**, 4 repaired by
case folding, **29 projected**, 311 too far to touch (of which 8 are still lower-cased by the
floor). 41 values changed on 40 of 1,000 rows.

### 2.3 What it is worth, and what it is not

| metric | KC-S1b | projected | delta (corpus) | paired pooled | paired NEW500 |
|---|---|---|---|---|---|
| **SLU-F1** | 44.35 | **45.09** | **+0.74** | +0.65, CI90 [+0.45, +0.87], 32 saves / **1 harm** | +0.78, CI90 [+0.47, +1.10] |
| Word-F1 | 41.58 | 42.71 | +1.13 | +0.91, CI90 [+0.63, +1.20] | +1.10, CI90 [+0.68, +1.55] |
| Char-F1 | 47.51 | 47.74 | +0.23 | +0.24, CI90 [+0.16, +0.31] | +0.27, CI90 [+0.16, +0.38] |
| **entities strict** | 31.37 | **34.68** | **+3.31** | +1.99, CI90 [+1.36, +2.65], 26 saves / **0 harms** | +2.43, CI90 [+1.50, +3.47] |

**The exact-match metric moves four and a half times as much as the headline one, and that is the
whole story of this section.** SLU-F1 already pays partial credit for `six a m` against `six am`;
strict entity F1 pays nothing. So a normalization repair is worth **+3.31 points of strict entity
F1** and only **+0.74** of SLU-F1 — which is the precise, quantitative answer to "how much SLU-F1 is
lost to normalization": **about three quarters of a point, no more.** Word-F1 moves +1.13 because
word distance is the metric that charges a full 1.0 for a pure case or spacing difference.

The repairs read exactly as section 1.4 predicted: `six a m` → `six am`, `three p m` → `three pm`,
`ten a m` → `ten am`, `p f changs` → `pf changs`, `on wednesday` → `wednesday`,
`the olive garden` → `olive garden`, `Orlando` → `orlando`. The single harm, and the harms that
appear above τ = 0.20, read just as clearly: `six hundred a m` → `six hundred pm`, `cst` → `ist`,
`chinese restaurant` → `shop restaurant`. The rule cannot tell an unusual value from a mis-spelled
one, and the threshold is the only thing standing between the two.

### 2.4 Verdict on the re-lock question

**NOT a re-lock candidate.** The bar this audit set before running it was **≥ 1 SLU-F1 point with a
CI90 lower bound above zero**; the best arm delivers **+0.76** at its maximum and **+0.74** at its
honest operating point. The lower bound clears zero comfortably on both populations, so the effect
is real — it is simply too small for the bar, and nothing here is proposed for a re-lock.

If the owner ever wanted it, the exact rule is written and tested, and the shape is the one
`slurp-slu-official-projected-v2` already has: a registered scorer id that applies
`slurp-value-projection-v1` at τ = 0.20 in the `normalized` family between the parse and the
official prediction file. **That would require owner GO, and this note does not ask for it.** The
one thing worth flagging on its own merits is the **normalization floor at τ = 0.00**: +0.19 SLU-F1
and +0.86 strict entity F1 for **zero harms**, no inventory, and no threshold to defend.

---

## 3. Schema conformance, and whether the wire can constrain it

Receipt: `schema-conformance.json`. The reference each row is judged against is **the per-intent
block that row actually received**, taken from KC-S1b's own committed prompt-fit receipt
(`schema_block_intent` / `schema_full_fallback` per row) — not a block chosen after the fact. That
receipt's own accounting reproduces: **42** full-schema fallback rows over **58** distinct intents,
and every one of the 42 ids matches its per-row flag.

### 3.1 What the sealed slot outputs violate

| violation | rows | mentions |
|---|---|---|
| response did not parse | **3** | — (those rows carry **10** gold mentions) |
| a slot type the row's **block did not list** | **72** | **73** of 682 (10.7 %) |
| a slot type outside SLURP's **55-type vocabulary** | **0** | **0** |
| the same type twice in one row | 11 | — |
| **fully conforming** | **914 (91.4 %)** | |

**The model never invents a type.** Zero of 682 predicted mentions name something outside the
55-type vocabulary, on an arm whose prompt lists only that intent's few types. Whatever the slot
layer's problem is, it is not a vocabulary problem, and a 55-type enum would be a *guarantee*
rather than a repair.

The 86 violating rows score **SLU-F1 33.44** against **46.43** on the 914 conforming ones — a
13-point spread that is mostly selection (a row the model half-heard is the row it also mis-types).

Illegal-for-block mentions concentrate in exactly the types section 1.3 found over-generating:
`transport_name` 17, `alarm_type` 9, `ingredient` 7, `email_address` 6, `list_name` 5,
`cooking_type` 4.

### 3.2 The block is **not** a superset of the gold, and that is the finding

A per-intent block lists the types holding at least 2 % of that intent's TRAIN slot mass, so a rare
but real type is "illegal" **by construction**. Measured, not assumed:

* **8 of the 73** illegal mentions matched a gold slot **exactly**.
* **81 of 950** gold mentions carry a type the block sent did not list. (The same 81 section 1.2
  found from the other direction — an independent cross-check that the two reads agree.)

So the suppression counterfactual cuts both ways, and both numbers belong in the same sentence:

| view | entities strict | Word-F1 | Char-F1 | **SLU-F1** |
|---|---|---|---|---|
| KC-S1b | 31.37 | 41.58 | 47.51 | **44.35** |
| every **block-illegal** mention suppressed | 31.82 | 42.10 | 48.26 | **44.97** (+0.62) |
| every **vocabulary-illegal** mention suppressed | 31.37 | 41.58 | 47.51 | **44.35** (+0.00) |

Corpus micro says **+0.62**; the paired per-sample read on the same rows says **−0.47 pp**
(CI90 [−0.86, −0.11], 16 saves / **12 harms**, pooled 1,000). Both are true, and the disagreement is
the point: suppression removes more false-positive mass than it removes true positives *in
aggregate*, while making a dozen individual rows strictly worse. **A hard grammar constraint to the
per-intent block would buy a corpus point and cost real answers**, and it would put 81 gold mentions
permanently out of reach.

### 3.3 Is grammar-constrained decoding available? **Yes — end to end, and it is one config key**

Verified by source reading, no server started. Study side, this repository:

| file | lines | what it establishes |
|---|---|---|
| `core/model/request_types.py` | 33 | `response_format` is one of the exact `decoding_params` keys the frozen core accepts — the comment there already calls it "llama-server's OpenAI-compatible schema-constrained decoding" |
| `core/model/adapter.py` | 172–197 | the adapter validates the wrapper: `json_object` with a mapping `schema`, or `json_schema` with a mapping `json_schema.schema`; anything else is refused |
| `core/model/transport.py` | 878–884 | every `decoding_params` key is copied verbatim onto the chat-completions body |
| `rails/controllers.py` | 531–532 | `decoding_params["response_format"] = dict(material.response_format)` |
| `rails/phase_material.py` | 613–637 | `resolve_response_formats(specs, lock, root)` renders one document **per phase** through `core.base.RESPONSE_FORMATS` |
| `core/base.py` | 88–97 | `RESPONSE_FORMATS` is the one registry a config's `response_format_id` resolves in |
| `rails/a2t_response_schema.py` | 449–524, 636–717 | the working precedent: real exact-name enum schemas over the pinned 152-tool registry |

Server side, the **pinned** llama.cpp build `/home/chao/llama.cpp-featcache` at
`04ccc72a2207347ca76161b93fd9d846dd0a8675` — the commit the runtime receipt names:

| file | lines | what it establishes |
|---|---|---|
| `tools/server/server-common.cpp` | 1280–1300 | the server reads `json_schema` and `grammar` off the body, refuses both at once, and maps an OpenAI `response_format` of type `json_object` or `json_schema` onto that same `json_schema` |
| `tools/server/server-schema.cpp` | 246–277 | the `json_schema` request field carries **`grammar` as an alias**; a schema is converted at `:256` by `json_schema_to_grammar(schema)` and installed as `COMMON_GRAMMAR_TYPE_OUTPUT_FORMAT`, a raw GBNF string as `COMMON_GRAMMAR_TYPE_USER` |
| `common/json-schema-to-grammar.cpp` | 1158 | the converter is in the build, not a server-side approximation |

Live checks in the same read: `"response_format" in ALLOWED_DECODING_KEYS` is **true**; the
registered ids are exactly `select-response-v1` and `fill-response-v1` (both Audio2Tool); and
**no SLURP config declares one** — every `response_format_id` in `configs/baseline/slurp-*.json` is
`null`. So the seam is built, exercised on another carrier, and simply not turned on here.

**What is missing, precisely.** `resolve_response_formats` takes `(specs, lock, root)` and **never
sees a sample**, so a *per-sample* schema — which is what KC-S1b's per-intent block would be — is
not reachable. The seam that would reach it already has a twin: `PHASE_STATE_FILLS` resolves a
per-sample state fill inside `build_material_for_phase`, and a `PHASE_RESPONSE_FILLS` registry keyed
the same way would put a per-row schema on the wire with **no change to the transport, the adapter,
or the server**.

### 3.4 Priced as a cell

| module | admission test | what it can buy | cost |
|---|---|---|---|
| **structure + 55-type enum**, phase-level | one config key `response_format_id` on the `slots` phase, module on/off against the sealed rows | at most **+0.81 SLU-F1** (45.16) — it can only repair the 3 unparsed rows' 10 gold mentions, because 0 mentions violate the vocabulary today | 1,000 contacts, ≈ 0.20 GPU-h, one config fragment, no new module |
| **per-intent enum**, per sample | needs the `PHASE_RESPONSE_FILLS` seam first | corpus +0.62 / per-sample **−0.47**, and 81 gold mentions put out of reach | a new registry seam plus the flight |

**Neither is a headline module.** The structural one is worth turning on because it is one key and
removes a failure mode; the per-intent one is measured here so that nobody builds it on the
assumption that it would help.

---

## 4. Knowledge headroom for values

Receipt: `value-headroom.json`. Identity anchor, fail-closed and passed: MF-7b's own filler
recall@5 for the sealed speech key reproduces from the KU-S3 floats at **43.46 (NEW500)** and
**41.90 (pooled)**, and OLD500 at 40.21 — the numbers that audit published, from vectors this read
re-read and never recomputed.

**One structural fact first, because everything else in this section turns on it: 333 of the
1,000 DEV rows carry no gold slot at all.** The 950 gold mentions live on 667 rows. A third of this
roster is a *correct silence*, and any mechanism that pushes the slot layer to answer more has to
be told where not to.

### 4.1 Does TRAIN already carry the value? Mostly yes — and not where you would guess

| population | gold mentions | verbatim in the TRAIN filler set **of the same type** | share |
|---|---|---|---|
| all | 950 | **724** | **76.21 %** |
| MF-8 **standing-state** types (35) | 577 | 417 | 72.27 % |
| MF-8 **utterance-local** types (20) | 373 | 307 | **82.31 %** |

**The partition inverts.** MF-8 called `date`, `time`, `event_name` and `definition_word`
"utterance-local — what the utterance says, not what the assistant has", and warned that putting
them in a state block would be supplying the answer's own material. Measured against DEV gold, they
are the types TRAIN covers *best*: SLURP's dates and times are a small, closed, spoken vocabulary
(`tomorrow`, `friday`, `nine am`), while `place_name` and `person` are open proper nouns
(482 and 468 TRAIN surface forms and still only 75.4 % and 57.1 % coverage). The correct reading is
not that a state block should supply dates; it is that **"utterance-local" is a statement about
provenance, not about vocabulary size**, and the two must not be conflated when a supply block is
designed.

Per type, ranked by gold mass. `verb%` is the verbatim share, `retr%` the share the KU-S3 top-5
already puts in front of the model, and the last two columns are same-speaker exemplar
availability.

| entity type | MF-8 partition | gold | distinct | verbatim | verb% | TRAIN forms | retrieved | retr% | spk>=1 | spk>=5 |
|---|---|---|---|---|---|---|---|---|---|---|
| `date` | utterance-local | 159 | 55 | 144 | **90.6** | 289 | 80 | 50.3 | 100.0 | 99.3 |
| `place_name` | standing | 118 | 89 | 89 | 75.4 | 482 | 35 | 29.7 | 100.0 | 96.3 |
| `media_type` | standing | 70 | 23 | 61 | 87.1 | 91 | 39 | 55.7 | 100.0 | 85.3 |
| `time` | utterance-local | 67 | 47 | 55 | 82.1 | 237 | 12 | **17.9** | 98.5 | 92.3 |
| `person` | standing | 56 | 54 | 32 | **57.1** | 468 | 14 | 25.0 | 100.0 | 100.0 |
| `food_type` | standing | 42 | 31 | 28 | 66.7 | 156 | 20 | 47.6 | 97.5 | 62.5 |
| `event_name` | utterance-local | 42 | 26 | 29 | 69.0 | 351 | 14 | 33.3 | 100.0 | 100.0 |
| `business_name` | standing | 36 | 31 | 24 | 66.7 | 213 | 11 | 30.6 | 94.4 | 83.3 |
| `transport_type` | standing | 31 | 3 | 31 | **100.0** | 10 | 30 | **96.8** | 96.8 | 71.0 |
| `business_type` | standing | 28 | 18 | 22 | 78.6 | 63 | 13 | 46.4 | 96.4 | 42.9 |
| `weather_descriptor` | standing | 27 | 14 | 27 | **100.0** | 104 | 22 | 81.5 | 100.0 | 66.7 |
| `news_topic` | standing | 27 | 24 | 11 | **40.7** | 122 | 5 | 18.5 | 92.6 | 22.2 |
| `timeofday` | utterance-local | 22 | 4 | 22 | **100.0** | 11 | 7 | 31.8 | 100.0 | 40.9 |
| `device_type` | standing | 22 | 13 | 21 | 95.5 | 75 | 13 | 59.1 | 95.5 | 50.0 |
| `list_name` | standing | 19 | 15 | 9 | 47.4 | 79 | 7 | 36.8 | 94.7 | 63.2 |
| `order_type` | utterance-local | 18 | 6 | 18 | **100.0** | 18 | 11 | 61.1 | 94.4 | 5.6 |
| `relation` | utterance-local | 14 | 10 | 13 | 92.9 | 81 | 8 | 57.1 | 92.9 | 57.1 |
| `definition_word` | utterance-local | 14 | 14 | 2 | **14.3** | 179 | 2 | 14.3 | 92.9 | 35.7 |
| `song_name` | standing | 7 | 7 | 0 | **0.0** | 103 | 0 | 0.0 | 57.1 | 42.9 |

Read the two extremes together and the design decision writes itself. `transport_type`,
`weather_descriptor`, `timeofday` and `order_type` are **closed vocabularies TRAIN carries whole**
— for these a supply block is an enumeration, and section 1.3 shows `transport_type` losing 20 of
its 31 gold mentions to pure non-answering. `person`, `news_topic`, `definition_word` and
`song_name` are **open** — for these no amount of TRAIN filler supply helps, because the value was
never seen.

### 4.2 What the KU-S3 retrieved top-5 could reach

The sealed `q-speech-nemotron` query vector against the 11,514 TRAIN content facets, k = 5 — the
exact artifact KU-S3 is registered to consume.

* **390 of 950** gold mentions (41.1 %) appear as a `(type, filler)` pair inside the retrieved
  union.
* Filler recall@5 per row: **41.90** pooled, **43.46** NEW500.
* **Oracle ceiling: SLU-F1 58.06** (entities strict 53.46, Word-F1 54.74, Char-F1 61.81), adding
  246 mentions the arm did not already carry.

**That ceiling is generous and must be read as such**: it lets the arm keep every mention it
already made *and* emit every gold value the retrieval supplied, which is a perfect reader of the
supplied block. No consumption cell reaches it. What it does say is that **retrieval is the only
priced module whose ceiling is in the fifties**, because it is the only one aimed at the category
carrying 45 % of the loss.

Per type, retrieval is strong exactly where the vocabulary is closed (`transport_type` 96.8 %,
`weather_descriptor` 81.5 %) and weak where it is open (`definition_word` 14.3 %, `song_name`
0.0 %) — the same split as 4.1, which is a consistency check rather than a coincidence: a retriever
can only supply what TRAIN contains.

### 4.3 Same-speaker slot exemplars

The unit is one **(DEV row, gold slot type)** pair, and the count is TRAIN utterances **by that
row's own speaker** carrying that slot type. 919 pairs over the 667 rows that have gold.

| threshold | pairs | share | rows where **every** gold type reaches it | share |
|---|---|---|---|---|
| >= 1 | 879 | **95.65 %** | 628 | **94.15 %** |
| >= 3 | 780 | 84.87 % | 534 | 80.06 % |
| >= 5 | 667 | 72.58 % | 433 | 64.92 % |

**Zero rows have a speaker absent from TRAIN**, and the supply is nearly total at the >= 1
threshold. MF-8 found the same-speaker *intent* supply anti-correlated with demand; on the **slot**
side it is not — the thin types are `order_type` (5.6 % at >= 5), `music_genre` (8.3 %) and
`news_topic` (22.2 %), none of them a large share of the loss. If the KU-S4 family is ever pointed
at slots, availability is not what would bind it.

---

## 5. The improvement ladder, priced

Receipt: `improvement-ladder.json`. **PRICED, NOT PREREGISTERED.** Nothing below is admitted,
promoted or registered; no owner decision is anticipated and no cell is flyable on the strength of
this note.

Costs are scaled from KC-S1b's own realized flight — 1,000 contacts in 735.9 s, about **0.20
GPU-h** — because every module here is one contact per row on the same geometry.

### 5.1 The judges, and how sharp each one is

Three deterministic judges can be built today from what this audit already computed. Each flags
rows without a model and without gold. **Precision** is the share of flagged rows that actually
carry an unmatched gold mention — the share where an extra contact could do anything at all.

| judge | what it fires on | rows flagged | of which carry unmatched gold | **precision** | unmatched gold mentions reached |
|---|---|---|---|---|---|
| **schema** (§3) | unparsed, or a type the row's own block did not list, or a repeated type | **86 (8.6 %)** | 62 | **72.09 %** | 88 |
| **value** (§2) | a predicted filler further than τ = 0.20 from any TRAIN surface form of its type | 293 (29.3 %) | 165 | 56.31 % | 217 |
| **silent** | the row parsed and predicted no entity at all | 394 (39.4 %) | 155 | **39.34 %** | 190 |
| union | any of the three | 714 (71.4 %) | 334 | 46.78 % | **428 of 527** |

**The silent judge is the trap.** 239 of the 394 rows it flags are *correctly* silent — the row
genuinely has no gold slot (§4). Firing an extra contact on all of them spends 394 calls to reach
190 gold mentions at 39 % precision. **The schema judge is the sharp one**: 8.6 % of the roster,
72 % precision, and it is free.

### 5.2 The ladder

`ceiling` is what the module could reach if it delivered its own oracle; only rung 1 is a
**measured** number. `gain / GPU-h` is therefore a **ceiling** ratio, not an expectation, and it is
printed so the ordering is visible rather than asserted.

| # | module | SLU-F1 | gain | contacts | GPU-h | gain / GPU-h | measured? |
|---|---|---|---|---|---|---|---|
| 1 | **value projection** (§2), scoring-side | **45.09** | **+0.74** | **0** | **0** | free | **MEASURED**, CI90 [+0.47, +1.10] on NEW500 |
| 2 | constrained decoding, structure + 55-type enum (§3) | 45.16 | +0.81 | 1,000 | 0.20 | 4.0 | ceiling |
| 3 | intent narrowing → better block selection (§1.2) | 48.40 | +4.05 | 1,000 | 0.20 | 20.2 | ceiling |
| 4 | **retrieved fillers, KU-S3** (§4.2) | **58.06** | **+13.71** | 1,000 | 0.20 | **68.5** | ceiling |
| 5 | same-speaker slot exemplars (KU-S4 on slots) | — | — | 1,000 | 0.20 | — | availability only |
| 6 | **targeted slot re-ask on judge-flagged rows** | **72.87** | **+28.52** | **714** | **0.143** | **199.4** | ceiling |

And rung 6 by which judge gates it, which is the sharpest thing in this whole note:

| judge gating the re-ask | rows | precision | unmatched gold reached | ceiling | GPU-h | **gain / GPU-h** |
|---|---|---|---|---|---|---|
| **schema** alone | **86** | **72.09 %** | 88 | 51.21 | **0.017** | **403.5** |
| value alone | 293 | 56.31 % | 217 | 60.25 | 0.059 | 269.5 |
| union of all three | 714 | 46.78 % | 428 | 72.87 | 0.143 | 199.4 |
| silent alone | 394 | 39.34 % | 190 | 58.45 | 0.079 | 178.5 |

Notes that belong beside each number, not in a footnote:

* **Rung 1** is the only measured row, and its verdict is in §2.4: real, below the re-lock bar,
  and it costs nothing because it is a post-processor over already-sealed bytes.
* **Rung 2**'s ceiling is small *because the arm is already well-behaved*: zero of 682 predicted
  mentions violate the 55-type vocabulary, so the enum guarantees rather than repairs, and all it
  can recover is the 3 unparsed rows' 10 gold mentions. It is still worth one config key.
* **Rung 3** assumes perfect intent **and** that all 51 newly-legal gold mentions are then filled
  exactly. Real intent narrowing tops out near 96.4 by MF-8's own candidate-recall ceiling.
  **The coordinator reports a cell named KU-S4N as already GO; this repository carries no
  preregistration or owner record under that name**, so this rung prices the mechanism and does not
  confirm its authorization.
* **Rung 4** is the strongest single-contact module and it is **already preregistered and flyable**
  (`docs/readiness/2026-09-07-slurp-consumption-ku-s3-v1-preregistration.md`). Its ceiling is an
  oracle reader of the supplied block.
* **Rung 6** is the highest ceiling per GPU-hour and the least trustworthy number in the table: it
  assumes every re-asked row then answers every missed gold mention exactly. Its real value is the
  *shape* — an extra contact on 71 % of rows instead of 100 %, gated by judges that cost nothing.

### 5.3 Reading the ladder honestly

**The ordering by ceiling-per-GPU-hour and the ordering by admission are not the same.**

By ceiling per GPU-hour: re-ask (199) > retrieval (68.5) > intent narrowing (20.2) > constrained
decoding (4.0), with the projection free and off the scale.

By admission order — one mechanism in flight, a successor admitted only after its predecessor is
replicated or root-caused (owner 2026-09-03):

1. **KU-S3 retrieved fillers.** Already registered, already has its comparator, its twin and its
   vectors, and it is aimed at the 45 % category. Second-highest ceiling, and the only rung that
   needs no new seam and no new decision.
2. **Constrained decoding, structural.** One config key; it can ride the next flight's own
   contacts rather than buying its own, and it removes a failure mode permanently.
3. **The targeted re-ask, gated by the SCHEMA judge alone** — not the union and not the silent
   judge. 86 rows, 72 % precision, 0.017 GPU-h, and the best ceiling-per-GPU-hour in the note at
   **403.5**. If a two-contact shape cannot pay for itself on the sharpest 8.6 % of the roster, it
   will not pay for itself on 71 %.
4. **Intent narrowing**, whose SLU-F1 channel is 51 gold mentions wide and whose real value is on
   the intent column this metric does not read.
5. **Same-speaker slot exemplars**, last, because availability is proved and value is not.

### 5.4 Where this actually tops out, against the published lines

Published SLURP lines, all of them the official **TEST** split and a natural mixture. DEV-1000 is a
scenario-stratified **dev** roster and no published prompt-only SLU-F1 computed with this script
exists for any audio LLM, so **none of these is a like-for-like target and none is claimed as one.**

| line | SLU-F1 | KC-S1b's distance | distance from the best rung ceiling (72.87) |
|---|---|---|---|
| ChatGPT over oracle transcripts (**a different metric**) | 12–13 | +31 | — |
| **WHISMA zero-shot** | **63.3** | **−18.95** | **+9.57** |
| trained pipelines, 2020 paper | 69.5–70.8 | −25.2 to −26.5 | +2.1 to +3.4 |
| WHISMA supervised reference | 69.9 | −25.55 | +2.97 |
| CTI | 71.1 | −26.75 | +1.77 |
| SFT Qwen2-Audio-7B | 76.75 | −32.40 | **−3.88** |
| NLU over **gold transcripts** | 78.19 | −33.84 | −5.32 |

**If every module delivered its ceiling.** The rungs overlap heavily — rung 6's oracle already
contains most of rungs 3 and 4 — so they do not add. The meaningful composite is the arithmetic
ceiling of the loss decomposition itself, and it says something worth stating plainly:

* **Answering every unmatched gold mention exactly, and changing nothing else, gives SLU-F1 78.04.**
  That is the recall ceiling of this arm, and it lands **0.15 points below the published NLU number
  over gold transcripts (78.19)**. A prompt-side system that solved recall perfectly and left
  precision and normalization exactly as they are would be at the gold-transcript NLU line, and no
  further.
* Removing every remaining loss category on top of that gives 100.0, which is a tautology and is
  reported as one.
* **Nothing in this ladder, at its own oracle, reaches the SFT line 76.75.** The best individual
  rung ceiling is 72.87 and it assumes a perfect answer on 714 re-asked rows.
* The realistic reading: KC-S1b is at **44.35**; the one measured module moves it to **45.09**; the
  strongest registered module has an oracle at **58.06** and will deliver a fraction of it. **A
  crossing of WHISMA's 63.3 is not reachable from this decomposition by any single module**, and
  claiming otherwise would require the re-ask oracle to be taken at face value.

### 5.5 What every one of these would inherit

* **Population** DEV-1000, decision on the unexposed NEW500 (n = 500 ≥ 400, owner 2026-09-03).
* **Comparator** the sealed KC-S1b rows, never a re-flight — greedy decoding is not bitwise
  reproducible across batch shapes on this runtime.
* **The greedy-noise floor**, which should govern expectations: EVO-S1 round 1 measured **286 of
  1,019 byte-identically prompted rows (28.1 %)** returning different text anyway on this carrier
  and this build. A claim read off a handful of moved rows sits below the noise; only a CI90 on 500
  unexposed rows carries a verdict.
* **Per-stratum reporting** with the harm bound, as every SLURP cell in this study already does.

---

## 6. What this note does and does not do

It answers the owner's question with five numbers and one ordering. It **admits nothing, promotes
nothing, preregisters no cell, opens no roster, draws no split, re-locks no comparator and reaches
no superiority, generalization or Stage-3 conclusion.** The value-projection rule it introduces is
tested and registered as a module; it is **not** wired into any scorer id and no verdict is
re-scored through it. The one decision it puts in front of the owner is whether rung 4 (KU-S3, the
registered cell) should be the next thing to fly, and that decision is the owner's alone.
