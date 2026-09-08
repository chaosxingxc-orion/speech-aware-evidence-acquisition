# MF-10 — slot vocabulary cards and the normalized SLU scorer (2026-09-08)

Row id `SAEA-SLURP-MF10-VOCAB-CARDS-NORMALIZED-SLU-V1`, profile `model-free-check`.
Receipts: `docs/checks/speech-aware-evidence-acquisition/2026-09-08-mf10-slot-vocab-cards-normalized-slu/`.
**Zero model, GPU, tool, embedding, network, audio-decode and tokenizer contacts.**

## 0. The two questions, and what this note is

The owner, 2026-09-08:

1. *`date` and `time` slots look like FORMAT knowledge that should be pre-loaded into the context —
   the expected surface conventions — while `place` needs PROPER-NOUN recognition. Would
   statistically pre-loading that knowledge into context engineering pay?*
2. *Refer to the Whisper-normalizer WER pattern and adjust the evaluation and the statistics
   accordingly.*

This note answers both with measurements. **It admits nothing, promotes nothing and preregisters no
cell.** Where something clears a bar the note says so and names the owner decision it would need; it
does not take that decision. Two things in it are wrong on purpose and reported as such: the
classification rule this audit declared before it read the table, and the first version of the
normalizer's leading-token rung. Both were caught by checks this audit built to catch exactly that,
and both are kept in the receipts rather than repaired in silence.

### 0.1 Boundary, stated before the first read

* The held-out `test` split is never named, loaded, hashed or scored.
* **No devel `sentence` string is read anywhere.**
* The **DEV verbatim-coverage statistic** of section 1 is READ out of MF-9's committed
  `value-headroom.json` and is never recomputed from DEV text; the classifier takes it as an
  argument for exactly that reason.
* DEV **gold entity annotations** do enter, and only on the **scoring side**, where the official
  scorer already reads them. The normalizer of section 3 applies to gold and prediction **alike**,
  which is what makes it a property of the metric and never a mechanism input. The precedent is the
  legal-label projection v2 verdict.
* The vocabulary cards and the leading-token list are mined from **TRAIN and only TRAIN**; both
  loaders refuse any other split by name.
* **Every token figure is a stated proxy** — whitespace tokens × 1.3, rounded up. No tokenizer was
  called. A cell that ever flies a card must measure its own envelope through the serving
  `/apply-template` + `/tokenize` seam, as KC-S1b did.

### 0.2 Identity anchors, checked before any new number was trusted

Fail-closed: the read raises rather than reports if the sealed bytes stop reproducing a published
verdict. All held.

| anchor | published | reproduced |
|---|---|---|
| KC-S1b entities strict / Word-F1 / Char-F1 / **SLU-F1**, through the normalized scorer's own official half | 31.37 / 41.58 / 47.51 / **44.35** | **identical** |
| the sealed closed-list comparator, same four columns | 21.91 / 33.69 / 38.20 / **35.80** | **identical** |
| the rebuilt value-projected arm (`normalized`, τ = 0.20) | **45.09** | **identical** |
| MF-9 corpus TP mass / loss mass | 846.0 / 2,123.085 | **identical** |
| MF-9's two ceilings, rebuilt from its own per-type table | 75.75 / 51.84 | **75.75 / 51.84** |
| MF-9 DEV verbatim: `date` / `transport_type` / `person` / `song_name` | 90.57 / 100.0 / 57.14 / 0.0 | **identical** |
| the NORMALIZED per-type attribution against the normalized corpus mass | — | **closes to 1e-6** |
| the normalized loss table rebuilds the normalized base | 45.09 | **45.09** |

MF-9's attribution engine is imported **by path** and reused rather than copied, so "missing",
"surface", "spurious" and "type swap" mean the same thing in both notes by construction.

---

## 1. Which slot types are vocabularies

Receipt: `type-classes.json`.

### 1.1 The rule this audit declared, and why it is wrong

The declared rule was: CLOSED when the **novelty ratio** (distinct TRAIN surface forms per TRAIN
mention) is at or below 0.10 **and** DEV verbatim coverage is at or above 85 %; OPEN when the ratio
is at or above 0.35 **or** coverage is at or below 60 %; MIXED otherwise.

It selects **four** types of fifty-five — `meal_type`, `timeofday`, `transport_agency`,
`transport_type` — and puts `date`, the type the owner's question names, in MIXED.

The reason is a defect in the statistic, not a property of the corpus. **The novelty ratio is a rate
estimate bounded below by `1 / mentions`.** `alarm_type` has **four** distinct surface forms in the
entire corpus — as closed a vocabulary as SLURP contains — but only nine TRAIN mentions, so its
ratio is 0.44 and the declared rule calls it open. The ratio measures how fast a corpus mints forms,
which is the same question as "is this a vocabulary" only once the corpus has minted enough of them
to tell.

Both rules' verdicts are in the receipt, along with the eighteen types the corrected rule moves.

### 1.2 The operative rule

`mf10-cardability-v2` puts the three statistics in the roles the measurement supports.

* **Coverage decides.** CLOSED needs DEV verbatim coverage ≥ 85 %; OPEN is ≤ 60 %. A card pays
  exactly when the value DEV needs is inside it, and cannot pay when the value was never said.
* **Re-use disqualifies, where it is estimable.** A novelty ratio ≥ 0.35 forces OPEN — but only at
  ≥ 50 TRAIN mentions, below which the ratio is an artefact of the sample.
* **Size is checked, not capped.** No per-type form limit. The enumerability question is asked where
  it actually binds — of the per-intent card SET against the arm's own measured prompt headroom
  (section 1.4) — so the threshold is a measured budget rather than a taste.

**18 CLOSED / 8 MIXED / 29 OPEN.**

| class | types |
|---|---|
| **CLOSED/FORMAT** (18) | `alarm_type`, `app_name`, `color_type`, `currency_name`, **`date`**, `device_type`, `email_folder`, `house_place`, `meal_type`, `media_type`, `movie_type`, `order_type`, `relation`, `timeofday`, `transport_agency`, `transport_name`, `transport_type`, `weather_descriptor` |
| **MIXED** (8) | `business_type`, `game_type`, `music_album`, `music_genre`, `player_setting`, `sport_type`, **`time`**, `transport_descriptor` |
| **OPEN/PROPER-NOUN** (29) | `place_name`, `person`, `event_name`, `business_name`, `food_type`, `artist_name`, `definition_word`, `list_name`, `news_topic`, `radio_name`, `song_name`, `game_name`, `general_frequency`, `personal_info`, `audiobook_name`, `podcast_descriptor`, `playlist_name`, `podcast_name`, `time_zone`, `change_amount`, `music_descriptor`, `joke_type`, `email_address`, `coffee_type`, `ingredient`, `cooking_type`, `movie_name`, `drink_type`, `audiobook_author` |

### 1.3 The three statistics, for the types the question names

| entity type | TRAIN mentions | distinct forms | novelty ratio | DEV gold | verbatim % | class |
|---|---|---|---|---|---|---|
| **`date`** | 1,823 | 289 | 0.1585 | 159 | **90.6** | **CLOSED** |
| `place_name` | 1,088 | 482 | 0.4430 | 118 | 75.4 | **OPEN** |
| `event_name` | 1,000 | 351 | 0.3510 | 42 | 69.1 | OPEN |
| `person` | 866 | 468 | 0.5404 | 56 | **57.1** | **OPEN** |
| **`time`** | 799 | 237 | 0.2966 | 67 | **82.1** | **MIXED** |
| `media_type` | 478 | 91 | 0.1904 | 70 | 87.1 | CLOSED |
| `weather_descriptor` | 320 | 104 | 0.3250 | 27 | **100.0** | CLOSED |
| `transport_type` | 318 | 10 | 0.0314 | 31 | **100.0** | CLOSED |
| `timeofday` | 239 | 11 | 0.0460 | 22 | **100.0** | CLOSED |
| `news_topic` | 183 | 122 | 0.6667 | 27 | 40.7 | OPEN |
| `radio_name` | 132 | 106 | 0.8030 | 5 | **0.0** | OPEN |
| `song_name` | 128 | 103 | 0.8047 | 7 | **0.0** | OPEN |

**The owner's split is confirmed on `date` and on `place`, and corrected on `time`.** `date` is a
vocabulary: 289 forms carry 90.6 % of what DEV asks for. `place_name` and `person` are not: 482 and
468 forms cover 75.4 % and 57.1 %, and `song_name` and `radio_name` cover **nothing at all**,
because the value was never said before. Enumeration works on the first, recognition is the only
option on the second.

**`time` is neither, and that is the finding of this section.** It sits three points under the
coverage floor at 82.1 %, and MF-9 already said why from the other direction: 27 of its 40 matched
pairs pay distance, and it has the worst exact rate of any large type (7 of 67). `time`'s failure is
not that the model lacks the vocabulary. It is that the model writes `six a m` where the corpus
writes `six am`. Section 3 measures that directly and closes most of it — `time`'s strict entity F1
goes from **12.07 to 34.48** under normalization alone, while `person`'s moves by **0.00**.

### 1.4 The cards, and what they cost

A card is the **whole** TRAIN vocabulary of one type with its mention counts, never a sample:
18 cards, **842 surface forms**, rendered as `- date: tomorrow (188); friday (95); …`.

| quantity | proxy tokens |
|---|---|
| all 18 cards at once | **3,298** |
| per intent, min | 0 — 7 of 60 intents list no carded type |
| per intent, median | **1,432** |
| per intent, worst (`social_query`: `media_type`, `date`, `relation`) | **2,010** |
| the 42 full-schema fallback rows (every card) | 3,313 |

The budget check the v2 rule declines to turn into a per-type cap: KC-S1b's own measured worst
prompt envelope is **10,006 tokens** in a **16,384-token slot at `-np 4`**, so a card set has
**6,378 tokens** to live in. The worst intent's card set fits with **4,368 proxy tokens to spare**.
At `-np 8` the slot is 8,192 and KC-S1b's own envelope does not fit either, which is why that arm
flew `-np 4`; the card does not change that geometry decision.

---

## 2. The knowledge views, priced

Receipt: `knowledge-views.json`. **PRICED, NOT PREREGISTERED.**

### 2.1 The three views

* **KU-S3v — static cards, closed types.** A per-intent slot value card for the 18 closed types,
  rendered as typed content beside the schema block. Deterministic. No query, no vector, no
  retrieval seed, **no GPU hour** — against KU-S3's own 0.68–0.71 h of single-threaded CPU seed per
  arm.
* **KU-S3 — retrieval, open types.** Exactly as preregistered, restricted to the types a card
  cannot enumerate.
* **Combined.** Cards on the closed half, retrieval on the open half, in one supplied block.

### 2.2 What each could reach

Every figure is an **ORACLE** in MF-9's sense: it assumes a perfect reader of the supplied block. A
card supplies a vocabulary, never a decision, and cannot make the core answer a slot it did not
hear. Nothing here claims a cell would reach these.

| view | reachable SLU-F1 | gain | retrieval contacts | seed GPU-h | worst-intent proxy tokens |
|---|---|---|---|---|---|
| KC-S1b as it stands | 44.35 | — | — | — | — |
| **KU-S3v cards** (vocabulary-limited) | **61.81** | **+17.46** | **0** | **0.0** | 2,010 |
| KU-S3v cards (unrestricted) | 62.99 | +18.64 | 0 | 0.0 | 2,010 |
| KU-S3 retrieval, open types (upper bound) | 53.25 | +8.90 | 0 | 0.85 | ~106 |
| **combined** (upper bound) | **69.21** | **+24.86** | 0 | 0.85 | ~2,116 |

The vocabulary-limited figure is the one this note leads with: it scales the repairable mass by the
share of DEV gold TRAIN actually carries, so it cannot credit a card for a value the card does not
contain. The retrieval half is an **upper bound** computed from MF-9's committed per-type counts —
at most `min(missing, in_retrieved)` missing mentions can be repaired, and leftover retrieved
capacity can at best repair surface pairs. Its global version comes out at **69.24** against MF-9's
own **measured** KU-S3 oracle of **58.06**, so the bound holds and is loose, which is what a bound
should do.

### 2.3 The containment check, and why it changes the design

**902 of 1,000 rows collide** at the runner's own 8-character substring floor. The reason is not
that a card leaks: it is that **the schema block KC-S1b already sends prints five example fillers
per type**, and **194** of those are card values. `this week` (282 rows), `today 's` (310),
`tomorrow` (266), `yesterday` (208), `afternoon` (199), `next week` (190), `birthday` (155),
`facebook` (155). The card would be the second place the same string is written, and
`rails.runner._assert_agent_control_excludes_knowledge_payloads` refuses that by design.

Decomposed by surface, over the instruction the cell would actually send (directive + sealed
closed-list state + the row's per-intent schema block):

| surface | rows colliding |
|---|---|
| the directive | **0** |
| the sealed closed-list state | 94 |
| the per-intent schema block **as sent** | **899** |
| the same block with its examples dropped | 83 |
| the whole instruction as sent | **902** |
| the whole instruction with the block's examples dropped | **128** |

**The resolution is one loader parameter the study already has.** `examples_per_type=0` renders the
same block without its example fillers, so the card becomes the *one* place a filler is written
rather than the second. That takes the collision from 902 rows to **128**, and **125 of those 128
are two forms** — `audiobook` and `takeaway` — matching inside the type names `audiobook_name` and
`takeaway_order` the block prints structurally. That is the false-positive class of a raw substring
rule over short English that MF-8 and KU-S3 both already recorded, not a leak. The rest is the
sealed state carrying the previous phase's own predicted fillers, which is a property of the
two-contact shape and not of the card.

**Consequence for any cell built on this view:** a card cannot be shipped beside a schema block that
still prints example fillers. The view must send the block without them — which also means the card
and the block are not independent factors, and a cell would be measuring the card *against* the five
examples rather than *in addition to* them. That is a design constraint, and it is stated here so
that nobody builds the cell on the other assumption.

### 2.4 The twin

`saea-mf10-within-intent-card-derangement-v1`: an intent's carded types are rotated among
**themselves**, so that intent's block holds the same MULTISET of vocabularies. The mapping is **per
intent** for exactly this reason — a single global map would carry one intent's rotation into
another intent that shares a type and break the match.

Measured: **39 intents rotate in place and ZERO of them differ from the arm by a character.**
Fourteen intents list a single carded type and cannot rotate in place; their volume delta is
reported as a covariate, the same treatment KU-S3 gives its own singleton scenario buckets. No type
keeps its own vocabulary anywhere.

---

## 3. The normalized SLU scorer

Receipt: `normalized-slu.json`. Rule: `reproduction.slurp_slot_normalizer`, id
`saea-slurp-slot-normalizer-v1`, scorer id `slurp-slu-f1-normalized-v1`, 35 unit tests.

### 3.1 The rule, stated exactly

One pinned deterministic normalizer applied to **BOTH gold and prediction** before the official
distance blocks. Symmetry is what makes it a property of the METRIC rather than something a system
can game: no arm gains by writing its answers differently from the corpus, only by saying what the
corpus says.

| rung | what it does | corpus dependency |
|---|---|---|
| **R0** | `casefold()` with whitespace collapsed | none |
| **R1** | the vendored, pinned Whisper `EnglishTextNormalizer` (`v20240930`), guarded so a rung that would empty a non-empty value keeps it | none |
| **R2** | the **meridiem join**: a standalone `a m` / `p m` becomes `am` / `pm` | none |
| **R3** | strip one leading token when the remainder is a TRAIN filler of the SAME type | TRAIN only |

**R2 is this study's own rule and is NOT inherited from Whisper.** Measured on the vendored
normalizer at the pinned tag: `six am` → `6 am` but `six a m` → `6 a m`, and `6 a.m.` → `6 a m`. The
Whisper rules *split* a period-spelled meridiem and leave a space-spelled one alone, so they align
neither of the two spellings SLURP actually carries. R2 runs after R1 precisely so the period
spelling has already become the space spelling and one rule catches every form.

### 3.2 The false-merge audit refused the first R3

The first version of R3 took its token list from TRAIN alone: any leading token witnessed on at
least three distinct same-type `(w x, x)` pairs was strippable. Over SLURP that admits `the` and
`in` — and also **`next`, `last`, `this`, `after`, `before`, `every`, `march`, `april`, `5th`, `my`,
`one`**, because the corpus witnesses those pairs just as faithfully.

The scorer's own false-merge audit then reported **17 collapsed gold values**:

> `date:week` ← {`next week`, `last week`, `this week`, `one week`} · `date:month` ← {`next month`,
> `the month`, `this month`} · `date:friday` ← {`after friday`, `every friday`, `friday`,
> `this friday`} · `time:hour` ← {`next hour`, `one hour`} · `time:2 hours` ←
> {`last two hours`, `two hours`} · `device_type:vacuum` ← {`robot vacuum`, `vacuum`} · …

**A metric that forgives the difference between next week and last week is not a cleaner metric, it
is a broken one.** No corpus statistic separates `next` from `on`: both are leading tokens the
corpus attests, and only one carries meaning. So the candidate set is now a **declared** closed list
of English articles and prepositions (`a an at by for in of on the to`) and the corpus's job is to
**confirm** that a candidate is attested at the witness floor, never to discover the list. The
rejected tokens and all 17 merges stay in the receipt as the evidence.

Under the corrected rule the corpus admits **`the` (18 witnesses) and `in` (6)**, and the false
merges drop to **two** — `the fifteenth` → `15th` and `the day after` → `day after` — both of which
are the same value written twice.

**One stated limitation.** MF-9's headline `on wednesday` → `wednesday` example is **not** repaired:
`on` is a declared candidate, but TRAIN never carries `on X` and `X` as fillers of one type, so the
confirmation floor refuses it at zero witnesses. The rule declines to act where the corpus gives it
no evidence, and that residual is charged to the arm rather than forgiven. Lowering the floor after
seeing which errors it would forgive would be tuning the metric on the errors it exists to score.

### 3.3 The three sealed arms, official beside normalized

Complete 1,000-row roster files through the pinned official `evaluate.py`, never sharded. The
official column is computed **first**, on every call, and the scorer refuses to emit a normalized
column at all if the port disagrees with it.

| arm | official SLU-F1 | **normalized SLU-F1** | Δ | official strict | **normalized strict** | Δ | Word-F1 | Char-F1 |
|---|---|---|---|---|---|---|---|---|
| sealed closed-list comparator | 35.80 | **36.43** | +0.63 | 21.91 | **24.98** | **+3.07** | 33.69 → 34.58 | 38.20 → 38.49 |
| **KC-S1b** | 44.35 | **45.09** | +0.74 | 31.37 | **34.44** | **+3.07** | 41.58 → 42.62 | 47.51 → 47.85 |
| KC-S1b + value projection | 45.09 | **45.24** | +0.15 | 34.68 | **35.29** | +0.61 | 42.71 → 42.86 | 47.74 → 47.89 |

The normalizer removes **62.187 of 551.085 surface-form mass units — 11.28 %**. Total loss mass
2,123.085 → 2,060.898.

### 3.4 Per rung, and the rung that pays is not the one you would expect

Cumulative, on KC-S1b.

| rules | SLU-F1 | entity strict | Word-F1 | Char-F1 |
|---|---|---|---|---|
| official (none) | 44.35 | 31.37 | 41.58 | 47.51 |
| R0 | 44.54 (+0.19) | 32.23 | 41.87 | 47.58 |
| R0+R1 | 44.54 (**+0.00**) | 32.60 | 41.80 | 47.66 |
| **R0+R1+R2** | **45.02 (+0.48)** | **34.07** | 42.54 | 47.80 |
| R0+R1+R2+R3 | 45.09 (+0.07) | 34.44 | 42.62 | 47.85 |

**The entire vendored Whisper English normalizer buys zero additional SLU-F1** on this carrier, and
**R2 — the meridiem join Whisper does not carry — buys more than everything above it.** The
literature's convention transfers as a *pattern* and not as a *rule set*: what a transcript
normalizer is built to fix is not what a one-token slot value gets wrong.

### 3.5 Per type

Top movers, strict entity F1, pooled 1,000.

| entity type | gold | official | **normalized** | Δ |
|---|---|---|---|---|
| **`time`** | 67 | 12.07 | **34.48** | **+22.41** |
| `general_frequency` | 5 | 40.00 | 60.00 | +20.00 |
| `radio_name` | 5 | 50.00 | 66.67 | +16.67 |
| `song_name` | 7 | 40.00 | 53.33 | +13.33 |
| `artist_name` | 14 | 42.86 | 50.00 | +7.14 |
| `business_name` | 36 | 13.11 | 19.67 | +6.56 |
| `event_name` | 42 | 3.92 | 7.84 | +3.92 |
| **`date`** | 159 | 30.92 | 33.82 | +2.90 |
| **`place_name`** | 118 | 40.23 | 42.53 | +2.30 |
| **`person`** | 56 | 23.26 | 23.26 | **+0.00** |
| `timeofday` | 22 | 27.59 | 27.59 | +0.00 |

**Three of the owner's types, three different answers, and they are exactly the three the question
proposed — with `time` reassigned.** `date` is knowledge: a card carries it and normalization adds
2.9 points. `time` is format: normalization alone nearly triples it. `person` is recognition:
normalization gives it nothing at all, because how you spell a name was never the difficulty.

### 3.6 Paired contrasts, and the one that changes a verdict

`analysis.paired.paired_contrast`, stratified bootstrap N = 10,000, seed 20260903, CI90, strata =
gold scenario. Decision population is the unexposed NEW500.

| contrast | population | official Δ SLU-F1 | CI90 | normalized Δ SLU-F1 | CI90 |
|---|---|---|---|---|---|
| **KC-S1b − comparator** | **NEW500** | **+10.85** | [+8.75, +13.03] | **+10.96** | [+8.83, +13.17] |
| KC-S1b − comparator | pooled | +8.71 | [+7.32, +10.11] | +8.81 | [+7.41, +10.23] |
| **value projection − KC-S1b** | **NEW500** | **+0.78** | **[+0.47, +1.10]** | **+0.11** | **[−0.02, +0.27]** |
| value projection − KC-S1b | pooled | +0.65 | [+0.45, +0.87] | +0.14 | [+0.04, +0.25] |

**MF-9's value projection was buying spelling, and this is the measurement that says so.** Under the
official metric it is a real effect on the decision population — +0.78, 19 saves against 1 harm,
lower bound comfortably above zero. Under a metric that already forgives spelling it is +0.11 with
an interval that crosses zero and 3 saves against 2 harms. Nothing about the arm changed; the metric
stopped charging for the thing the rule was repairing.

**KC-S1b's own admitted gain is the opposite case, and the two belong in the same table.** +10.85
becomes +10.96 — it does not merely survive the normalized metric, it is marginally larger under it.
The schema mechanism is a gain in what was *heard*, and it is still there when how it was *written*
stops counting.

### 3.7 The reporting rule

**The paper-facing SLURP number stays the official `evaluate.py` one.** `slurp-slu-f1-normalized-v1`
is registered in `core.base.SCORERS` beside `slurp-slu-official`, exactly as `asr-wer-whisper` is
registered beside `asr-wer`, and it is reported **beside** the official number and never in place of
it. No verdict, lock or admission in this repository is restated under it. The scorer enforces its
own subordination: it runs the real, unmodified official subprocess on the raw inputs first, reports
those numbers unchanged, and refuses to compute a normalized column at all if the port disagrees
with them.

---

## 4. The ladder under both scorers

Receipt: `ladder-both-scorers.json`. **PRICED, NOT PREREGISTERED.**

The normalized column is computed from a **normalized per-type loss table** — MF-9's own attribution
engine re-run with the normalizer on both sides — not asserted. Its per-type masses close against
the normalized corpus mass to 1e-6, and it rebuilds the normalized base 45.09.

| # | module | official SLU-F1 | gain | normalized SLU-F1 | gain | measured? |
|---|---|---|---|---|---|---|
| base | KC-S1b | 44.35 | — | 45.09 | — | — |
| 1 | **value projection**, scoring-side | 45.09 | **+0.74** | 45.24 | **+0.15** | **MEASURED** |
| 2 | constrained decoding, structure + 55-type enum | 45.16 | +0.81 | — | — | ceiling, recall channel |
| 3 | intent narrowing → block selection | 48.40 | +4.05 | — | — | ceiling, recall channel |
| 4 | retrieved fillers, KU-S3 | 58.06 | +13.71 | — | — | ceiling, recall channel |
| **4v** | **MF-10 vocabulary cards, closed types** | **62.99** | **+18.64** | **63.78** | **+18.69** | ceiling |
| 4c | MF-10 combined view | 69.21 | +24.86 | — | — | bound |
| 6 | targeted re-ask on judge-flagged rows | 72.87 | +28.52 | — | — | ceiling, recall channel |

Two ceilings under both metrics, and both are consistency checks the arithmetic has to pass:

| counterfactual | official | normalized |
|---|---|---|
| every matched span carries the gold surface form | **51.84** | **51.84** |
| every missing gold mention answered exactly | 75.75 | **76.59** |

The surface ceiling is **identical** under both, and it must be: the normalizer removes part of the
surface mass and the counterfactual removes the rest, so the two paths meet at the same point. The
recall ceiling is 0.84 higher under the normalized metric because the base loss is smaller.

**Rung 4v is the answer to the owner's first question, and it is not the answer this note expected
to write.** The vocabulary card **keeps its gain** under the normalized metric — +18.64 against
+18.69 — because **480 of the 565 mass units it repairs are MISSING, not surface**. The card is a
**recall** mechanism that happens to also fix spelling, not a spelling mechanism. That is why
pre-loading the vocabulary is worth doing at all: it is aimed at the 45 % category, which is the
only category with room in it.

Rung 1 is the exact opposite, and the two rows sit next to each other on purpose.

### 4.1 The admission primary for slot modules

**Recommendation: the official SLU-F1 stays the PRIMARY. The normalized SLU-F1 is a SECONDARY that
must AGREE IN SIGN.**

*Why official is primary.* It is the dataset's standard scorer at a pinned commit, every published
SLURP line is stated in it, and every verdict and lock in this repository already stands on it. A
study that moved its primary to a metric of its own making after seeing the gap would be choosing
the metric that flatters it.

*Why the normalized column is reported beside it.* The official metric charges a full **word
distance of 1.0** for a pure case or spacing difference, so a module can look effective by repairing
spelling, and a module aimed at recall can look weaker than it is. The normalized column separates
the two: a gain that survives it is a gain in what was heard; a gain that vanishes under it was a
gain in how it was written.

*The disagreement rule.* A module whose two columns disagree in **sign** is not admitted on the
strength of either. The disagreement is itself the finding, and it is reported with the per-type
table that produced it.

*Worked, on this note's own numbers.* KC-S1b passes: +10.85 → +10.96, both lower bounds far above
zero. The value projection does not: +0.78 → +0.11, and the second interval crosses zero. Neither
verdict is re-opened here — KC-S1b stays admitted on its official number, and MF-9 already declined
to promote the projection — but a future slot module is held to both columns.

---

## 5. What this note does and does not do

It answers both owner questions with measurements and one recommendation. It **admits nothing,
promotes nothing, preregisters no cell, opens no roster, draws no split, re-locks no comparator and
reaches no superiority, generalization or Stage-3 conclusion.**

The normalized scorer it registers is an **additional** id and never replaces the official number.
The vocabulary cards it prices are **not** proposed as a cell: the containment finding of section
2.3 means a cell built on them would have to send the schema block without its example fillers,
which changes what the factor is, and that is an owner decision this note does not ask for.

Two open items it hands on, neither of them a request:

1. **The card view needs its own design decision** before it could be preregistered — whether the
   card replaces the schema block's five examples or the two are merged into one supplied artefact —
   because section 2.3 shows they cannot both be sent.
2. **`time` is a format problem with a measured fix.** Section 3.5 recovers 22 points of its strict
   entity F1 on the SCORING side alone. Whether any of that is reachable on the SYSTEM side — an
   instruction line that names the corpus's own meridiem convention — is a one-factor question this
   note prices at zero contacts and does not open.
