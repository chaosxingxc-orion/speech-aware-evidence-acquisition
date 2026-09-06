# Earnings-22 DEV semantic error scan — verdict

**WER IS NOT MEASURING WHAT THE STUDY CARES ABOUT ON THIS CARRIER. 42.6 % of arm A's error mass is
semantically inert, another 43.3 % is wording, and 14.1 % changes a number, a negation or a name.
The decision-relevant residual — the "agentic error rate", HIGH-impact reference-word mass over
reference words — is 1.92 % against a corpus WER of 17.56 %, a factor of 9.1.** And the largest
single block of the WER is not recognition at all: **8.36 of the 17.56 points (47.6 %) is speech at
the clip boundary** — words past the end of the published sentence, words before its start, and
whole clauses the *next* published utterance's own reference already contains.

**Decision, as this row is scoped: NO FIX IS LICENSED AND NONE IS PROPOSED AS A NUMBER.** No
normalizer was edited, no scorer changed, no hypothesis post-processed, no published figure
restated. Every "could be folded" figure below carries the authority that would license it, and
every fold without an authority is refused by name.

Row `SAEA-E22-MF-SEMANTIC-ERROR-SCAN-V1` (`model-free-check`), registered before the first sealed
byte was read. **Zero contacts of every kind** — model, tokenizer, embedder, retriever, network,
GPU, audio decode — and the offline guard recorded **zero outbound connection attempts**.
Receipts: `docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-semantic-error-scan/`
(`summary.json` sha256 `c91703aa…`, `per-arm-tables.md` `a0e0f183…`, `read-sample-ids.json`
`997f912e…`). Module `analysis/e22_error_taxonomy.py`, runner `scripts/run_e22_error_scan.py`,
tests `tests/unit/test_e22_error_taxonomy.py`.

**Population: DEV ONLY.** The three sealed 2026-09-05 arms over this study's own Earnings-22 dev
subset10 — 6,038 ESB utterances, ten calls, 103,423 reference words. **The six ESB test calls were
not opened**: the reference loader is pinned to the dev10 receipt alone, so
`e22-esb-test-references.jsonl` is never read, and `test_split_read` is `false` in the receipt. The
sealed test verdict's published figures appear here only as the numbers its own committed note
already carries.

## 1. The identity gate

Everything below sits on the same alignment the three verdicts scored, and that is checked rather
than asserted. `align_spans` re-implements the frozen `scoring.wer.align` backtrace and emits the
operations it walks over; `build_receipts` refuses to write anything unless the flight-level totals
reproduce the sealed table to the unit.

| arm | S | D | I | reference words | corpus WER % |
|---|---:|---:|---:|---:|---:|
| A — this study's verbatim instruction | 4,526 | 2,370 | 11,270 | 103,423 | 17.5648 |
| B — the Qwen3-Omni model-card ASR prompt | 4,563 | 2,479 | 11,982 | 103,423 | 18.3944 |
| C — the official request shape | 4,433 | 4,975 | 9,094 | 103,423 | 17.8896 |

Reproduced exactly, all three. A unit test additionally asserts the aligner's S/D/I equals the
frozen aligner's on 400 random pairs.

## 2. What the reference layer actually is, counted

The 2026-09-05 shape-C verdict named "Rev's **cleaned** sentence transcript" as the leading
remaining suspect. **It is not cleaned.** On the hash-pinned dev10 layer, of 6,038 rows:

| property of the reference | count |
|---|---:|
| filler tokens (`uh` 2,679, `um` 1,349, `hmm` 8, `mm` 7) | **4,043** |
| rows carrying a redaction tag (`<inaudible>` 117, `<unk>` 27, `<laugh>` 26, `<crosstalk>` 15, `<affirmative>` 8, `<silence>` 4) | 184 |
| rows carrying a truncated word (`Co-`, `internat-`, `increbl-`) — 360 distinct stems | 330 |
| rows with an adjacent repeated word **surviving normalization** — 1,905 of them | 1,232 |

The distinction is the whole point of the taxonomy. The Whisper `EnglishTextNormalizer` deletes the
fillers and the bracket tags from **both** sides, so they cost nothing. It deletes **neither** the
repetitions **nor** the truncation stems from **either** side, so the model is charged every time it
does not reproduce a stutter or a half-spoken word. The reference is close to verbatim, and the
instruction arm A sends ("transcribe verbatim") is therefore *aligned* with it, not fighting it —
which is why arm B's plainer prompt lost, and it is the missing half of that verdict's reasoning.

## 3. The owner's example, measured: what the normalizer already folds

Aligned a second time on the **raw** text (whitespace tokens, casefolded), a raw error span whose
two sides normalize to the same string is mechanically **format-only**.

| arm | raw error operations | format-only | share already folded |
|---|---:|---:|---:|
| A | 34,583 | 6,914 | **20.0 %** |
| B | 35,189 | 6,375 | 18.1 % |
| C | 33,787 | 4,375 | 12.9 % |

*"twenty twenty two"* against *"2022"* is in that 20 %: it is **already spent** on the paper-facing
number and cannot be spent again. Verified directly on the vendored normalizer:
`"twenty twenty two" → "2022"`, `"one point five million dollars" → "$1500000"`,
`"five percent" → "5%"`, `"first quarter" → "1st quarter"`, `"Mr." → "mister"`,
`"don't" → "do not"`, `"year-end" → "year end"`, and `hmm|mm|mhm|mmm|uh|um` plus anything inside
`<…>` / `[…]` / `(…)` deleted outright.

## 4. Category mass, per arm

Eight categories, 32 named first-match-wins rules, every span carrying the rule that decided it.
"Mass" is the error operations the span owns (its reference tokens for a substitution or deletion,
its hypothesis tokens for an insertion); "points" is that mass over 103,423 reference words.

### Arm A (17.5648 %)

| category | spans | mass | share of errors | WER points | NONE | LOW | HIGH |
|---|---:|---:|---:|---:|---:|---:|---:|
| model-behaviour | 1,405 | 5,462 | 30.07 % | **5.281** | 337 | 935 | 133 |
| other (named residual) | 3,534 | 4,906 | 27.01 % | **4.744** | 1,649 | 1,611 | 274 |
| segmentation-artifact | 2,269 | 3,746 | 20.62 % | **3.622** | 2,269 | 0 | 0 |
| acoustic-misrecognition | 1,051 | 1,400 | 7.71 % | 1.354 | 128 | 791 | 132 |
| named-entity | 874 | 1,174 | 6.46 % | 1.135 | 0 | 0 | 874 |
| reference-convention | 752 | 903 | 4.97 % | 0.873 | 752 | 0 | 0 |
| format-convention | 290 | 342 | 1.88 % | 0.331 | 290 | 0 | 0 |
| domain-term | 155 | 233 | 1.28 % | 0.225 | 0 | 144 | 11 |

### Arm B (18.3944 %) and arm C (17.8896 %), WER points

| category | A | B | C |
|---|---:|---:|---:|
| model-behaviour | 5.281 | **5.641** | 4.506 |
| other | 4.744 | 4.976 | **5.165** |
| segmentation-artifact | 3.622 | 3.737 | **2.787** |
| acoustic-misrecognition | 1.354 | 1.349 | 1.430 |
| named-entity | 1.135 | 1.143 | 1.106 |
| reference-convention | 0.873 | 1.008 | **2.366** |
| format-convention | 0.331 | 0.315 | 0.280 |
| domain-term | 0.225 | 0.225 | 0.249 |

**Arm C's regression is now legible.** The shape-C verdict measured it as 0.325 corpus points worse
and could say only that its 2,176 removed insertions came back as 2,605 deletions. This scan says
*which* deletions: arm C's `reference-convention/reference-repetition` mass is **1.645 points against
arm A's 0.364** — 1,388 spans against 345. The shorter output stops reproducing the reference's own
stutters, and every one of those is scored as a deletion while being, by inspection, semantically
inert. Arm C pays 1.49 points of impact-NONE reference-repetition to buy 0.84 points of
segmentation and 0.78 of model behaviour.

Full per-rule tables for all three arms: `per-arm-tables.md`. Arm A's ten largest rules:

| rule | spans | mass | WER points |
|---|---:|---:|---:|
| `model-behaviour/runaway-tail` | 1,087 | 4,635 | **4.482** |
| `segmentation-artifact/boundary-continuation` | 1,288 | 1,775 | 1.716 |
| `segmentation-artifact/neighbour-bleed` | 496 | 1,419 | 1.372 |
| `acoustic-misrecognition/string-near` | 1,051 | 1,400 | 1.354 |
| `other/substituted-content-word` | 1,023 | 1,285 | 1.242 |
| `named-entity/call-inventory` | 874 | 1,174 | 1.135 |
| `other/inserted-content-word` | 532 | 1,168 | 1.129 |
| `other/inserted-function-word` | 636 | 739 | 0.715 |
| `other/deleted-content-word` | 330 | 610 | 0.590 |
| `other/deleted-function-word` | 495 | 562 | 0.543 |

## 5. Semantic impact, and the agentic error rate

Every span is tagged from its own tokens: **HIGH** when a number or value, a currency or percentage,
a negation or a call-inventory named entity is changed or lost; **LOW** when ordinary wording moves;
**NONE** when nothing a task consumes moves. Three categories are NONE **by ruling** rather than by
measurement, and the ruling is stated so it can be reversed: a format equivalence and a reference-side
transcription convention change no fact, and a boundary bleed reproduces the *neighbouring segment's
own reference words*, so nothing is lost or invented at call level.

| arm | NONE | LOW | HIGH |
|---|---|---|---|
| A | 7,734 (42.57 %, 7.478 pts) | 7,866 (43.30 %, 7.606 pts) | **2,566 (14.13 %, 2.481 pts)** |
| B | 7,884 (41.44 %, 7.623 pts) | 7,894 (41.50 %, 7.633 pts) | 3,246 (17.06 %, 3.139 pts) |
| C | 8,259 (44.64 %, 7.986 pts) | 7,612 (41.14 %, 7.360 pts) | 2,631 (14.22 %, 2.544 pts) |

**Definition, stated so it is reproducible.** *Agentic error rate* = HIGH-impact **reference-word
mass** ÷ total reference words. A HIGH substitution or deletion charges the reference tokens it
covers; a HIGH insertion charges one reference-word-equivalent at its anchor. Same denominator as
the corpus WER, so the two are comparable point for point. The **strict** variant re-admits
`segmentation-artifact` to the impact test and is the upper bound.

| arm | corpus WER % | **agentic error rate %** | strict % | ratio WER : agentic |
|---|---:|---:|---:|---:|
| A | 17.5648 | **1.9241** | 2.0469 | 9.1 |
| B | 18.3944 | **1.9270** | 2.0498 | 9.5 |
| C | 17.8896 | **1.9928** | 2.1195 | 9.0 |

**This is the result the owner asked for.** Two flights and 18,114 contacts varied the instruction
text and the request shape and moved the corpus WER by 0.83 points. On the decision-relevant
residual the three arms span **0.069 points**. Arm C, excluded by the shape-C verdict for being
0.325 WER points worse, is 0.069 points worse here. The request-usage campaign moved the metric and
did not move the capability.

Per call, arm A (agentic rate beside WER):

| call | ref words | corpus WER % | agentic % | seg pts | model pts | entity pts | ref-conv pts |
|---|---:|---:|---:|---:|---:|---:|---:|
| 4453225 | 11,304 | 20.294 | 1.115 | 3.300 | 6.263 | 0.575 | 1.929 |
| 4469088 | 11,493 | 19.856 | 2.019 | 4.150 | 6.935 | 0.940 | 1.236 |
| 4470684 | 10,862 | 14.298 | 1.215 | 3.664 | 5.119 | 0.700 | 0.792 |
| 4474506 | 11,534 | 14.947 | 1.509 | 3.607 | 3.928 | 0.668 | 0.694 |
| 4479944 | 10,882 | 23.663 | **2.996** | 3.961 | 7.232 | 1.553 | 0.193 |
| 4481952 | 9,827 | 17.116 | 1.760 | 4.009 | 5.017 | 1.282 | 1.404 |
| 4482383 | 9,763 | 14.258 | 1.639 | 3.032 | 4.097 | 1.301 | 0.502 |
| 4482613 | 9,168 | 22.939 | **4.876** | 3.741 | 4.210 | **2.934** | 0.567 |
| 4483937 | 8,680 | 15.472 | 1.325 | 3.618 | 5.138 | 0.899 | 0.806 |
| 4485192 | 9,910 | 12.291 | 1.060 | 3.068 | 4.400 | 0.797 | 0.474 |

**The two orderings disagree, and where they disagree is informative.** 4453225 is the third-worst
call by WER (20.29) and the second-*best* by agentic rate (1.12): its damage is stutters and
boundaries, and its reference-convention mass, 1.93 points, is the highest in the set. 4482613 is
second-worst by WER (22.94) and by far the worst agentically (4.88), because 2.93 of its points are
named entities — a call dense in proper nouns the core does not know. The same pattern in miniature
is 4479944, where the currency token `inr` alone is deleted 60 times. **A knowledge brief has five
times the headroom on 4482613 that it has on 4453225, and the WER column cannot see that.**

Per clip duration, arm A:

| duration | utterances | ref words | corpus WER % | seg pts | model pts | entity pts | acoustic pts |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0–1 s | 504 | 1,268 | 71.688 | 19.558 | 23.107 | 4.259 | 2.524 |
| 1–2 s | 482 | 2,461 | 41.934 | 10.727 | 9.671 | 3.088 | 2.276 |
| 2–4 s | 1,163 | 10,172 | 28.628 | 7.108 | 7.707 | 2.418 | 1.740 |
| 4–8 s | 1,991 | 31,065 | 19.047 | 4.117 | 6.406 | 1.091 | 1.236 |
| 8–16 s | 1,625 | 45,298 | 13.208 | 2.241 | 4.000 | 0.777 | 1.263 |
| 16 s+ | 273 | 13,159 | 10.738 | 1.649 | 2.622 | 0.813 | 1.360 |

Acoustic misrecognition is **flat** at 1.2–1.4 points from 4 s upward and only doubles under 2 s.
Everything that rises as clips shorten is boundary and model behaviour. The monotone rise the two
earlier verdicts reported as "the length ratio" is, category by category, a boundary effect.

## 6. Where the mass actually is: boundary speech, decided by the segment table

The segment table gives every utterance its neighbours, so "is this the next sentence's speech?" is
a lookup, not a judgement. Arm A:

| | insertion spans | inserted words | ≥ 0.6 contained in the neighbour | 0.34–0.6 | some | none |
|---|---:|---:|---:|---:|---:|---:|
| at the hypothesis **tail**, against the NEXT reference | 2,828 | 7,704 | **868 (30.7 %)** | 459 | 760 | 741 (26.2 %) |
| at the hypothesis **head**, against the PREVIOUS reference | 603 | 1,060 | **287 (47.6 %)** | 45 | 27 | 244 (40.5 %) |

Boundary and over-generation mass, arm A: `segmentation-artifact` 3.622 + `runaway-tail` 4.482 +
`runaway-head` 0.254 = **8.358 WER points, 47.6 % of the whole number.** Only 26.2 % of tail spans
and 40.5 % of head spans have *no* overlap with the neighbouring reference at all, so **at most
about a quarter of the tail block can be hallucination**; the rest is speech the published boundary
cut through.

This is the reading the sealed oracle could not give. The A/B verdict's headline diagnostic was that
cutting each hypothesis to its own reference length was worth 6.87 points on arm A, and the shape-C
verdict then falsified "length is the cause" by showing arm C's oracle floor *rose*. Both are
consistent with what is measured here: the surplus words are not noise to be trimmed, they are the
next sentence, and cutting them blindly discards right words along with them. The lever is the
**boundary**, not the length.

## 7. What a scoring-layer change could legitimately fold — and what is refused

| fold | arm A points | authority |
|---|---:|---|
| `format-convention/merge-compound` — `the U.S. and` vs `the US and`, `et cetera` / `etcetera`, `back end` / `backend`, `e com` / `ecom`, `sports book` / `sportsbook` | **0.251** | **Open ASR Leaderboard `merge_compounds`**, which the published ESB column applies and this study does not (deviation H4/G4, named in the shape-C verdict) |
| `format-convention/stray-punctuation-token` — Rev's ellipsis surviving as a bare `..` token, 37 deletions | 0.036 | **none published**, but no recipe treats a token with zero alphanumeric characters as a word |
| `format-convention/numeric-equal` / `symbol-only` / `whisper-refold` | 0.044 | **none published**; reported so they can be subtracted, never claimed |
| `reference-convention/empty-reference` — 8 rows whose reference normalizes to nothing | 0.017 | the ESB protocol: a row with no denominator |
| **total available to a scoring change** | **0.348** | of which **0.251 has a published authority** |

**Refused by name, with the reason:**

* `reference-convention/false-start-stem` (0.266 pts) — no published normalizer removes Rev's
  truncated-word stems; folding them would be this study inventing a convention to improve its own
  number.
* `reference-convention/reference-repetition` (0.364 pts on arm A, **1.645 on arm C**) — the A/B
  verdict already measured that collapsing repeats makes the number *worse*, and no ESB or
  leaderboard rule collapses them.
* `reference-convention/filler-token` (0.004 pts) — the Whisper filler list is exactly
  `hmm|mm|mhm|mmm|uh|um`; extending it is a new convention, not an existing one.
* `reference-convention/discourse-phrase` and `discourse-single` (0.042 pts) — no authority removes
  "you know" or "I mean" from a reference, and "so"/"right"/"like" are ordinary words as often as
  they are fillers.
* `segmentation-artifact/neighbour-bleed` (1.372 pts) — the ESB protocol scores each published
  utterance against its own sentence; crediting a neighbour's words would change the task, not the
  scoring.

**So the honest ceiling on a scoring-convention change is about a third of a point, and only a
quarter of a point of that has a published authority.** Anyone hoping the 15.94-vs-9.79 gap is a
normalizer argument can stop here: it is not.

## 8. The four-bin gap estimate

Bins are a partition of the rule set — every one of the 32 rules belongs to exactly one bin, and the
receipt records `unassigned_rules: []`. Residual rules are binned by their own impact: a residual
that changes content is core capability, a residual that is impact-NONE by construction (function
words inserted, deleted or swapped) is task definition.

### 8.1 Measured on dev, arm A

| bin | error mass | share | **dev WER points** |
|---|---:|---:|---:|
| scoring convention | 360 | 1.98 % | **0.348** |
| missing pre-meeting context / brief | 1,407 | 7.75 % | **1.360** |
| core capability (acoustic) | 5,027 | 27.67 % | **4.861** |
| task definition | 11,372 | 62.60 % | **10.996** |
| **total** | **18,166** | 100 % | **17.565** |

Task definition breaks down as: boundary and over-generation 8.358, function-word churn 1.782
(`inserted` 0.715 + `deleted` 0.543 + `swapped` 0.524), reference conventions 0.856. Core capability
breaks down as: string-near acoustic 1.354, unrelated content substitutions 1.242, mid-sentence
content insertions 1.129, content deletions 0.590, hypothesis repetition 0.270, truncation 0.215,
non-Latin script 0.032, loops 0.029.

### 8.2 Transferred to the sealed test number, and what it says about 15.94 → 9.79

**The transfer is an assumption and is labelled as one.** The shares are measured on the ten dev
calls; the sealed 15.937 covers six different calls. The two populations share the corpus, the
segmentation protocol, the reference layer's conventions, the instruction and the core, and their
error shapes are close (insertion share 62.0 % dev against 59.2 % test; hypothesis/reference length
ratio 1.086 against 1.075) — but the transfer has not been measured, and only a test-set scan would
measure it.

| bin | share (dev, arm A) | **test-transferred points** |
|---|---:|---:|
| scoring convention | 1.98 % | **0.32** |
| missing pre-meeting context | 7.75 % | **1.23** |
| core capability | 27.67 % | **4.41** |
| task definition | 62.60 % | **9.98** |
| — of which boundary and over-generation | 47.6 % | **7.58** |
| **total** | 100 % | **15.94** |

The gap to close is 15.937 − 9.79 = **6.15 points**, and the four bins do not decompose the *gap* —
they decompose *our number*. The published system faces the same references and the same normalizer,
so its 9.79 also carries reference conventions and acoustic error. The gap can only live where the
two systems **differ**, and the bins bound each candidate:

1. **Scoring convention: at most 0.32 points, and 0.25 of it with an authority.** It cannot be the
   explanation. Ceiling, not estimate.
2. **Missing pre-meeting context: at most 1.23 points.** A perfect brief — speakers, company,
   products, plants, tickers — buys no more than the entity and domain-term mass, and the published
   system had no such brief either, so its true contribution to the *gap* is at most this and
   plausibly near zero. Ceiling.
3. **Core capability: at most 4.41 points, almost certainly far less.** A system scoring 9.79 also
   misrecognizes words. The gap contribution is the *difference* between the two systems' acoustic
   error, which this scan cannot measure without a self-run anchor. Ceiling.
4. **Task definition: 9.98 points, of which 7.58 is boundary.** This is the one bin where a
   difference of *behaviour* between the two systems is both plausible and large enough. **A
   published system emitting a third of our boundary mass would close about 5 points of the 6.15
   on its own** — and the sealed test flight's own oracle length cut, worth 5.48 points, is the same
   phenomenon measured from the other side. The two bracket each other.

**Best reading, stated as a reading:** the 15.94-vs-9.79 gap is most plausibly **output discipline at
the clip boundary, not recognition, not the normalizer, and not the reference's conventions.** The
alternative — that the published system's acoustic core is 4 points better on the same audio — is
not excluded by anything measured here, and separating them needs the `whisper-large-v3` self-run
anchor both previous verdicts already named.

## 9. The top ten recurring patterns, with dev examples

Ordered by mass. Sample ids are in the committed read sample; quotes are normalized text.

1. **A trailing connective past the end of the published sentence** — `so` ×201, `and` ×109,
   `but` ×45, `thank you` ×43. `4453225-102` *"…moving 12 month average"* + `so`; `4453225-124`
   *"…the last few years"* + `and`. 1,288 spans, 1.716 pts, all impact NONE.
2. **A long tail continuation the neighbour does not carry** — `4453225-148`
   *"…the next 12 months"* + *"but that is not the case"*; `4453225-205` + *"thank you very much"*;
   `4469088-665` *"thanks guys"* + *"see you later"*. 1,087 spans, 4.482 pts — the single largest rule.
3. **A whole clause of the NEXT utterance bled in** — `4453225-15` + *"so let us start with"*;
   `4453225-627` + *"thank you"*; `4470684-60` + *"looking at the economy"*. 496 spans, 1.372 pts,
   each one proved against the segment table.
4. **The reference's own repeated word, said once by the model** — `a` ×57, `the` ×34, `and` ×32.
   `4453225-621` *"this is a a target"*; `4469088-717` *"once we get the the the quality"*.
   345 spans on arm A, **1,388 on arm C**.
5. **Rev's truncated words** — `4453225-151` reference *"internat-"* against the model's
   *"international"*; `4453225-111` *"Co- Covid"* against *"under covert"*; `4453225-105` *"al-"*.
   249 spans, 0.266 pts, all impact NONE and none of them foldable by any published rule.
6. **Article and preposition churn** — `a` inserted ×85, `a` deleted ×67, `the` deleted ×50,
   `the`→`a` ×32, `and` deleted ×35. 1,649 spans across three rules, 1.782 pts, impact NONE
   throughout.
7. **Company, plant and person names** — `4469088-120` *"gratkorn"* → *"gretchen"* (and
   *"kirkniemi"* → *"kurt nimmy"*); `4469088-451` *"saiccor"* → *"sykor"*; `4469088-332`
   *"mohammed"* → *"mohamed"*; `4453225-92` *"hbc"* → *"hpc"*; `4453225-574` *"orgaran"* → *"organ"*;
   `4469088-272` *"thrive 25"* → *"525"*. 874 spans, 1.135 pts, **every one HIGH impact**.
8. **A currency unit dropped wholesale** — `inr` deleted ×60, all on 4479944 (`4479944-112`,
   `4479944-113`): the model transcribes *"18000 crores"* and omits the unit the reference carries.
   One call, one token, 60 HIGH-impact spans — the clearest single knowledge-brief target in the set.
9. **Compound boundaries the leaderboard folds and this study does not** — `u`+`s` against `us`
   ×59 (`4469088-548`, `4474506-105`, `4482383-226`), `et`+`cetera`/`etcetera` (`4469088-361`),
   `back`+`end`/`backend` (`4470684-18`), `e`+`com`/`ecom` (`4474506-51`), `sports`+`book`
   (`4482383-161`), `q`+`4`/`q4` (`4469088-40`). 233 spans, 0.251 pts, the only authorized fold.
10. **The model saying the same phrase twice** — `4469088-745` *"thank you very much"* twice;
    `4479944-259` *"same thing applies"* twice; `4453225-583` *"that makes a"* twice; `4481952-76`
    *"good morning everyone"* twice. 196 spans, 0.270 pts; ruled impact-NONE because nothing is
    lost.

Two smaller findings, recorded rather than removed: **27 spans across 19 arm-A rows answer in a
non-Latin script** on near-empty clips (`4474506-499`, reference *"no"*, hypothesis Chinese;
`4482613-325`) — the sealed A/B verdict counted 14 arm-A rows carrying CJK characters, and this
detector's block set is wider — and the class vanishes entirely on arm C; and
**Rev's ellipsis survives normalization as a bare `..` token**, deleted 37 times
(`4453225-4`, `4453225-419`, `4482613-398`).

## 10. Method, and what it rests on

* **Dual pass.** Every utterance aligned twice — raw (whitespace, casefold) and Whisper-normalized.
  All category, impact and rate figures are on the normalized pass, because that is the pass the
  published number lives on; the raw pass sizes what is already folded (section 3).
* **Named rules, first match wins.** 32 rules, 8 categories. Three rules are documented refinements
  of the accepted plan, each for a reason the read sample forced: the compound fold is measured over
  a window reaching two tokens past the span (a split shows up as a deletion plus its aligned
  neighbour); the reference-convention test runs token by token (the aligner merges a repetition and
  a truncation stem into one span); and the non-Latin-script check runs before the cascade (a
  one-word Chinese answer was otherwise absorbed by the boundary rule).
* **Three folds are guarded against meaning.** `-18` against `18`, `$340` against `340` and `14.9%`
  against `14.9` all squash to the same letters and digits. All three rules now require the `+-$%`
  character counts to match before folding, so a sign flip and a dropped unit are charged as what
  they are. The correction moved arm A's agentic rate from 1.879 to 1.924 %.
* **The read.** 1,500 error spans per arm, seed 20260903, stratified by source call, ids and
  assignments committed in `read-sample-ids.json`. The residual bucket was sub-bucketed **from that
  read** into six named rules; nothing is left as a nameless remainder, and the receipt's
  `unassigned_rules` is empty.
* **Entity inventory, model-free.** Built from each call's own reference sentences: a normalized form
  is an entity form when it appears capitalized in a non-sentence-initial position more often than
  lowercase there, plus ticker-shaped uppercase runs, minus the pronoun "I", one-character forms,
  function words, acknowledgements and the pinned domain lexicon (without which the pronouns "it"
  and "us" and the term "EBITDA" all scored as named entities). 64–192 forms per call.
* **Lexicons are committed.** The finance lexicon, the filler and discourse lists, the negation list
  and the stopword list are literal in the module and reproduced in `summary.json`, so any share
  resting on a lexicon can be re-derived from it.

**Limits of the method, stated.** Rules 4 and 5 are bounded to short spans, so an entity inside a
long runaway is reported as a runaway; the acoustic rule's 0.6 string-similarity threshold misses
genuine confusions like *"growth"* → *"gross"* (ratio 0.545), which land in the named residual and
in the same bin; the impact ruling that makes three categories NONE is a judgement, and the strict
variant is published beside it; and the dev-to-test transfer in section 8.2 is an assumption.

## 11. What this licenses, and what it names next

**It licenses one metric change proposal, and no number change.** The agentic error rate is defined,
implemented, tested and reported beside the WER on every table here. Nothing in the receipts
restates a published figure, and no fold was applied to any arm's score.

**It reclassifies the leading suspect for the third time, and this time with a mechanism.**
2026-09-04 named the prompt; the A/B flight falsified that. 2026-09-05 named over-generation; the
shape-C flight falsified that as a *length* story. This scan names the **clip boundary**: 47.6 % of
arm A's error mass is speech at a segment edge, and 73.8 % of the tail insertion spans overlap the
next published sentence's own reference.

**Named for the owner, and NOT done here:**

1. **A `whisper-large-v3` self-run anchor over these same 6,038 utterances.** Both earlier verdicts
   named it; this scan raises it again because bin 3 is a ceiling and only an anchor turns it into a
   measurement. Not a frozen-core contact; needs its own registration.
2. **A boundary-aware request, on a population that is not these ten calls if it is to be reported.**
   The scan says what such a cell should be graded on: boundary mass and the agentic rate, not the
   corpus WER, which will move for reasons that have nothing to do with capability.
3. **A knowledge brief is worth at most 1.23 points on this carrier and is unevenly distributed** —
   2.93 points on 4482613 against 0.58 on 4453225. If a SUPPLY mechanism is ever run on Earnings-22,
   the per-call entity mass is where its headroom is, and the agentic rate is the metric that can see
   it.
4. **`merge_compounds`.** 0.251 points, one published authority, and the only fold this scan would
   defend. It is a scoring-alignment decision for the owner, not an implementer's edit.

**It does not license a claim about the published number**, it is not an alignment verdict, and it
does not license a fix.

## 12. A test-set scan: what it would add, and what it would cost

**What it would add.** Exactly one thing, and it is the assumption section 8.2 rests on: whether the
dev-derived category shares transfer to the six calls the published 9.79 covers. It would replace
"the test-transferred points" with measured points, and it would settle whether the boundary block
is 47.6 % there too. It would add nothing to the taxonomy, the impact model or the agentic-rate
definition, all of which are population-independent.

**What it would cost.** A **second read of the six calibration-exposed ESB test calls**. The
2026-09-04 owner decision permits one read of those calls and it has been spent; the 2026-09-05
shape-C verdict explicitly declined to spend a further read on a shape that was 0.325 points worse.
This scan is model-free — no contacts, no GPU, no audio — so the cost is **exposure only**: the
sealed test outputs and `e22-esb-test-references.jsonl` would be opened a second time, which retires
the last unspent read of a one-shot asset and makes those six calls harder to defend as any future
comparison's clean side.

**Recommendation: do not spend it yet.** The dev shares are stable across three arms that differ in
instruction text and request shape: scoring convention moves 0.04 points between arms, missing
context 0.01 and core capability 0.22, and only task definition moves more (0.61, and that movement
is arm C's reference-repetition trade, section 4). That is the cheapest available evidence that the
shares are a property of the corpus rather than of the arm. Spend
the read, if at all, *after* a boundary-aware cell exists to be measured — so that one read answers
two questions instead of one.

## 13. Cost and conduct

| | value |
|---|---:|
| frozen-core contacts | **0** |
| tokenizer / embedder / retriever contacts | **0** |
| outbound network connection attempts (offline guard) | **0** |
| GPU hours | **0** |
| audio decoded | **0** s |
| paid API spend | **0** |
| wall time | ~20 s, one process |

The offline guard replaces `socket.connect`, `connect_ex` and `create_connection` with counted
refusals before the first input is opened, so "zero contacts" is enforced by the process rather than
asserted by this note.

**Conduct.** Only the three sealed 2026-09-05 dev arms, the hash-pinned dev10 reference layer
(sha256 `8da3a65d…`, re-hashed on load) and the hash-pinned dev10 segment table (sha256
`51257011…`, re-hashed on load) were read. **The six ESB test calls were not opened**: the reference
loader is pinned to the dev10 receipt alone, the segment-table loader to the dev10 extracted table,
and no test-call output path is reachable from the runner's input set. The 109 remaining confirmatory
Earnings-22 calls were not named, loaded or read.

**Gates.** `scripts/checks/engineering_base_check.py --repo-root …/wt-e22` **PASS** (no probe module,
no adapter or controller subclass, no launcher directory, no new config value). `ruff check` clean on
all three new files; the repository-wide count is unchanged at 180 pre-existing findings.
`pytest` on the working tree: **15 failed, 6,796 passed, 15 skipped**, against a measured baseline on
the same tree with the three new files removed of **15 failed, 6,749 passed, 15 skipped** — the same
15 failures by name, and the 47 new passes are exactly this change's tests. The one collection error
(`tests/unit/test_build_a2t_g6_family_sweep.py`, the `verl` top-level `scripts` package shadowing the
repository's own) is pre-existing and unrelated.

## 14. Open items

* **The dev-to-test transfer is unmeasured** (section 8.2), and is the scan's largest stated
  assumption.
* **No self-run anchor exists**, so bin 3 stays a ceiling rather than an estimate.
* **The acoustic rule's threshold is a choice.** At 0.6 string similarity it misses near-miss
  confusions that land in the named residual. Both are in the same bin, so no bin figure moves; the
  category split between `acoustic-misrecognition` and `other/substituted-content-word` would.
* **The impact model has no human validation.** It is mechanical and reproducible; nobody has yet
  checked a sample of HIGH tags against what a downstream agent would actually do differently.
* **`merge_compounds` remains unapplied**, as it has been since the first Earnings-22 number, and is
  now sized: 0.251 points on arm A.
