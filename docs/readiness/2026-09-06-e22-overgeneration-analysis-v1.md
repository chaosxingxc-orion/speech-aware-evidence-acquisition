# Earnings-22 DEV over-generation analysis — verdict

**THE SURPLUS IS NOT A RUNAWAY AND A LENGTH CAP CANNOT REACH IT. Arm A's hypothesis is longer than
its reference on 3,605 of 6,038 dev rows, but the median over-long row is +1 word, the 95th
percentile is +6 and the largest is +27; the longest completion in the whole flight is 130 tokens
against a 1,024-token ceiling nothing came near. The 868 rows whose tail reproduces the NEXT
published sentence are not the long rows — their median excess is +1 word, their p95 is +5, and
623 of them END ON A SENTENCE-FINAL TOKEN. The model is not rambling. It is finishing a sentence,
and on those rows it is the wrong sentence.** The best duration-proportional `n_predict` cap on the
declared ladder is worth **−0.73 dev WER points** and cuts **127 of the 868** bleed rows, and at
that operating point it makes the agentic error rate **worse** (1.9241 → 2.0121). The tightest cap
whose predicted agentic rate does not worsen is worth **−0.23 points**.

**Decision, as this row is scoped: NO CAP IS APPLIED AND NONE IS RECOMMENDED AS A FIX.** No
hypothesis was post-processed, no scorer or normalizer was edited, no arm was re-scored and no
published figure was restated. The cap this note names is an input to
`docs/readiness/2026-09-06-e22-dev-usage-cells-v1-preregistration.md`, nothing more.

Row `SAEA-E22-MF-OVERGENERATION-ANALYSIS-V1` (`model-free-check`), registered before the first
sealed byte was read. **Zero contacts of every kind** — model, tokenizer, embedder, retriever,
scorer, network, GPU, audio decode, paid API — and the offline guard recorded **zero outbound
connection attempts**. The pass is byte-deterministic: run twice back to back it reproduces the same
`MANIFEST.sha256`. Receipts:
`docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-overgeneration-analysis/`
(`summary.json` sha256 `74bce285…`, `per-row-table.csv` `5e66766d…`). The receipt was written
once as `5b6e89b5…` and re-written the same day, under the same row, to add the section 5.4
subset projection the companion preregistration's prediction rests on; the per-row table and every
figure in sections 1 to 5.3 are unchanged between the two, which is why the table's digest did not
move. Module
`analysis/e22_overgeneration.py`, runner `scripts/run_e22_overgeneration_analysis.py`, tests
`tests/unit/test_e22_overgeneration.py` (41, on synthetic rows).

**Population: DEV ONLY.** The sealed `SAEA-E22-DEV-ESB-PROMPT-A-V1` arm (attempt
`attempt-20260905T073641Z-f977d1`) over the 6,038 ESB utterances of this study's own Earnings-22 dev
subset10, 103,423 reference words. **The six ESB test calls were not opened**: the reference loader
is pinned to the dev10 receipt, the segment-table loader to the dev10 extracted table, and no test
output path is reachable from the runner's input set (`test_split_read` is `false` in the receipt).

## 1. The identity gate

Every figure below sits on the alignment the three 2026-09-05 verdicts scored, and that is checked
rather than asserted: this module's own pass through the frozen `scoring.wer.align` reproduces the
sealed arm A table to the unit, and `build_receipts` refuses to write anything otherwise.

| | S | D | I | reference words | corpus WER % |
|---|---:|---:|---:|---:|---:|
| sealed arm A | 4,526 | 2,370 | 11,270 | 103,423 | 17.5648 |
| this module | 4,526 | 2,370 | 11,270 | 103,423 | 17.5648 |

The per-row token counts are the **flight tokenizer's own** — `usage.completion_tokens` from the
sealed trace, joined to the outputs on `request_id`. Nothing is re-tokenized and no tokenizer is
loaded, which is what makes the token axis of this analysis an observation rather than a
reconstruction.

## 2. The surplus, counted

| | value |
|---|---:|
| rows | 6,038 |
| hypothesis words / reference words | 112,323 / 103,423 |
| length ratio | **1.0861** |
| net excess | **+8,900 words** |
| gross excess / gross deficit | +10,247 / −1,347 |
| rows longer / equal / shorter | **3,605 / 1,702 / 731** |

| excess (hypothesis − reference words) | rows |
|---|---:|
| ≤ −20 | 0 |
| [−20, −10) | 7 |
| [−10, −5) | 26 |
| [−5, −2) | 88 |
| [−2, 0) | 610 |
| **0** | **1,702** |
| **[1, 3)** | **1,895** |
| **[3, 6)** | **1,390** |
| [6, 11) | 308 |
| [11, 21) | 11 |
| [21, 51) | 1 |
| ≥ 51 | 0 |

Quantiles of the excess: p05 −1, p25 0, **p50 +1**, p75 +3, **p95 +6**, p99 +8, max **+27**,
min −20.

**This is the first fact and it decides most of the rest.** The over-generation is thin and wide:
3,593 of the 3,605 over-long rows are +1 to +10 words, and twelve rows in the whole population are
more than +10. There is no runaway population.

The completion lengths say the same thing from the token side:

| | tokens |
|---|---:|
| total completion tokens | 145,930 |
| mean per row | 24.17 |
| p50 / p90 / p95 / p99 | 21 / 44 / 53 / 73 |
| **largest completion** | **130** |
| rows at or above 256 / 512 / the 1,024 ceiling | **0 / 0 / 0** |

The flight's declared `max_tokens` was 1,024 and **nothing came within a factor of seven of it**.
Any cap that bites at all has to bite far below the ceiling the arm already flew under.

## 3. Where the surplus sits

### 3.1 Against the published boundary geometry

The split is the 2026-09-06 clip-boundary audit's own, read from its committed per-clip table
(re-hashed against that receipt's `MANIFEST.sha256` on load): a **negative** `gap_next` means the
two published segments themselves overlap, so the clip provably carries some of its neighbour's
speech; a **positive** gap means the clip is tight and anything past its own words is the core
continuing past the audio it was given.

| | rows | ref words | length ratio | mean excess | corpus WER % | rows longer |
|---|---:|---:|---:|---:|---:|---:|
| next segment **overlaps** | 4,681 | 80,138 | **1.1036** | **+1.77 words** | **18.936** | 3,153 |
| next segment is **tight** | 1,347 | 23,197 | 1.0265 | +0.46 words | 12.640 | 448 |
| no next segment (last of call) | 10 | 88 | 0.773 | −2.00 words | 67.045 | 4 |

The overlapping clips carry **3.9× the mean excess** of the tight ones and 6.3 WER points more.
This reproduces the audit's reading from the length side: the excess is a boundary effect.

### 3.2 Against clip duration — and the ratio has been misleading us

| duration | rows | ref words | length ratio | **mean excess (words)** | corpus WER % | tail bleed ≥ 0.6 |
|---|---:|---:|---:|---:|---:|---:|
| 0–1 s | 503 | 1,265 | 1.1581 | **+0.40** | 71.462 | 47 |
| 1–2 s | 483 | 2,464 | 1.1875 | +0.96 | 42.086 | 53 |
| 2–4 s | 1,163 | 10,172 | 1.1424 | +1.25 | 28.628 | 161 |
| 4–8 s | 1,991 | 31,065 | 1.1070 | +1.67 | 19.047 | 312 |
| 8–16 s | 1,625 | 45,298 | 1.0633 | +1.77 | 13.208 | 240 |
| 16 s+ | 273 | 13,159 | 1.0454 | **+2.19** | 10.738 | 55 |

**The length RATIO falls monotonically with duration and the absolute excess RISES monotonically
with it.** Both earlier verdicts reported the ratio and read it as "the model over-generates more
on short clips". In words — which is what the WER numerator counts — the opposite is true: a 16 s+
clip carries 5.5× the surplus of a sub-second one. The ratio was reporting the denominator.

That matters for exactly one decision and it is this note's decision: **a cap proportional to
duration is the wrong shape for a surplus that is roughly constant in absolute words.** A
duration-proportional cap is loosest precisely where the surplus is largest.

### 3.3 The 868 bleed rows are not the long rows

The clip-boundary audit's headline population — rows whose tail insertion span reproduces the NEXT
published sentence's own reference at ≥ 0.6 containment.

| | 868 bleed rows | the other 5,170 |
|---|---:|---:|
| length ratio | 1.1025 | 1.0830 |
| mean excess | +1.89 words | +1.40 words |
| excess p50 / p75 / p95 / max | **1 / 3 / 5 / 15** | — |
| completion tokens p50 / p95 / max | **23 / 57 / 99** | — |
| corpus WER % | 16.265 | 17.803 |
| **rows ending on a sentence-final token** | **623 (71.8 %)** | 4,661 (90.2 %) |

**The rows that bleed into the next sentence look, by length, almost exactly like the rows that do
not.** Their median excess is one word above the rest of the population's; their completion-token
distribution is the population's. No threshold on length separates them, which is why the cap
frontier in section 5 is as flat as it is.

## 4. How the row ends

| | rows | ref words | length ratio | mean excess | corpus WER % | bleed rows |
|---|---:|---:|---:|---:|---:|---:|
| ends on a **sentence-final** token | **5,284 (87.5 %)** | 86,499 | 1.0793 | +1.30 | 17.280 | 623 |
| **runs on** | **754 (12.5 %)** | 16,924 | 1.1205 | +2.70 | 19.020 | 245 |

| duration | rows | sentence-final | runs on |
|---|---:|---:|---:|
| 0–1 s | 503 | 492 | 11 |
| 1–2 s | 483 | 467 | 16 |
| 2–4 s | 1,163 | 1,089 | 74 |
| 4–8 s | 1,991 | 1,716 | 275 |
| 8–16 s | 1,625 | 1,317 | 308 |
| 16 s+ | 273 | 203 | 70 |

Detection reads the RAW hypothesis — the Whisper normalizer strips punctuation from both sides, so
the model's own sentence boundary survives nowhere else — and strips trailing quotes and brackets
first.

**Seven rows in eight end on a full stop.** A run-on is real but it is the minority mode and it is
concentrated in the long clips, not the short ones. The dominant failure is a decode that emits a
COMPLETE sentence that the published reference does not contain — which is what section 3.3's 623
sentence-final bleed rows are. Neither a token cap nor a stop string can distinguish "finished the
right sentence" from "finished the next one": both look identical at the wire.

## 5. The cap, simulated

### 5.1 The rule, and why the simulation is not an oracle

```
n_predict = ceil(alpha * media_seconds * words_per_second_p95 * tokens_per_word)
```

with the two constants measured on this population: **`words_per_second_p95` = 4.9992** (the 95th
percentile of REFERENCE words per second — the reference side deliberately, so the over-generation
the cap is meant to bound cannot set the cap's own scale) and **`tokens_per_word` = 1.2992** (the
flight tokenizer's pooled tokens per normalized hypothesis word). The corpus mean reference word
rate is 2.632 words/s, so alpha 1.0 is already about 1.9× the mean rate.

At alpha 1.5 the cap is 10 tokens for a 1 s clip, 49 for 5 s, 98 for 10 s, 293 for 30 s and 764 for
the 78.36 s longest — under the 1,024 the arm already flew, so the cap is a genuine tightening
everywhere.

**The simulation is honest about one thing and approximate about another.** It is HONEST because a
greedy decode under an `n_predict` cap returns exactly the token PREFIX the uncapped decode
returned — llama.cpp stops generating, it does not re-decode — so unlike the "cut each hypothesis
to its own reference word count" transform the earlier verdicts reported, **this is not an
oracle**: the cap reads only the clip duration, which is known before the request is sent. It is
APPROXIMATE in the token-to-word mapping: where inside a row a cap lands is estimated from that
row's own measured tokens-per-word ratio, and a cap landing mid-word drops the partial word
(`floor`), which never credits the cap with a word it might have cut. Every capped-row figure and
every simulated WER inherits that approximation.

**Disclosed:** the alpha ladder was first written as `(1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0)` and
extended DOWNWARD to 0.6 after the first pass showed every rung at and above 1.0 touching under
10 % of the population. The extension adds rungs that bite HARDER — it can only make the harm side
of the frontier worse — and it was made to find where harm overtakes benefit, not to find a better
number. Both passes are reproducible from the committed module.

### 5.2 The frontier

Harm has two readings and both are reported. **`cap < reference`** is the a-priori one: the cap is
below the row's own reference length in tokens, so the cap would refuse a *perfect* transcript.
**realized harm** is the measured one: the cap bites and leaves fewer words than the reference has.
Benefit is the complement: the cap bites and the cut lands entirely inside surplus.

| alpha | rows capped | benefit rows | harm rows (realized) | harm rows (cap < ref) | ref words at risk | surplus words removed | bleed rows cut (of 868) | corpus WER % | Δ WER | agentic % | Δ agentic |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.60 | 2,778 | 870 | 1,908 | 1,971 | 6,688 | 4,646 | 385 | 17.7668 | **+0.2020** | 2.9152 | +0.9911 |
| 0.70 | 1,699 | 708 | 991 | 1,049 | 2,918 | 2,685 | 217 | 16.8473 | −0.7175 | 2.2393 | +0.3152 |
| **0.80** | 1,109 | 510 | 599 | 599 | 1,432 | 1,647 | 127 | **16.8338** | **−0.7310** | 2.0121 | **+0.0880** |
| 0.90 | 766 | 400 | 366 | 341 | 792 | 1,136 | 93 | 16.8870 | −0.6778 | 1.9802 | +0.0561 |
| 1.00 | 568 | 319 | 249 | 224 | 514 | 828 | 69 | 16.9933 | −0.5715 | 1.9454 | +0.0213 |
| 1.25 | 329 | 222 | 107 | 94 | 246 | 446 | 36 | 17.2060 | −0.3588 | 1.9338 | +0.0097 |
| **1.50** | **204** | **144** | **60** | **51** | **162** | **271** | **22** | **17.3327** | **−0.2321** | **1.9232** | **−0.0009** |
| 1.75 | 129 | 97 | 32 | 29 | 126 | 177 | 10 | 17.4043 | −0.1605 | 1.9203 | −0.0038 |
| 2.00 | 100 | 73 | 27 | 24 | 111 | 129 | 6 | 17.4429 | −0.1219 | 1.9203 | −0.0038 |
| 2.50 | 51 | 37 | 14 | 17 | 85 | 65 | 1 | 17.5000 | −0.0648 | 1.9212 | −0.0029 |
| 3.00 | 27 | 19 | 8 | 13 | 70 | 30 | 1 | 17.5348 | −0.0300 | 1.9232 | −0.0009 |

Sealed arm A: corpus WER **17.5648 %**, agentic error rate **1.9241 %** (strict 2.0469 %). The
agentic column is the 2026-09-06 taxonomy's own definition — HIGH-impact reference-word mass over
reference words — recomputed by `analysis.e22_error_taxonomy` at its committed version on the
capped hypotheses of each rung.

**Three readings, and they are the whole result.**

1. **The frontier turns at alpha 0.8 and its best point is −0.73 points.** Below 0.8 the cap starts
   cutting real transcripts faster than it cuts surplus and at 0.6 the number is *worse* than the
   sealed one. −0.73 dev points is the entire achievable range of this intervention.
2. **The corpus WER and the agentic rate disagree over most of the ladder, and the disagreement is
   the point.** Every rung that buys more than a quarter of a point makes the agentic rate WORSE,
   because the words a cap removes are not only surplus: at alpha 0.8 it costs 1,278 reference
   words, and the ones that carry a number, a negation or a named entity are exactly the errors
   corpus WER cannot see. **A cap chosen on WER alone would be chosen against the study's own
   metric.** This is the first time the two metrics have pointed in opposite directions on a
   candidate change, and it is why the agentic rate was defined.
3. **The cap barely touches the mechanism.** At alpha 1.5 it cuts 22 of the 868 bleed rows; at the
   WER-optimal 0.8 it cuts 127. Section 3.3 already said why: the bleed rows are not the long rows.

### 5.3 The operating point this note names

**alpha = 1.5**, the tightest rung on the declared ladder whose predicted agentic error rate does
not worsen (1.9232 against the sealed 1.9241). Its prediction, fixed here before any capped request
exists: **204 rows capped, 144 benefit, 60 realized harm, corpus WER 17.3327 % (−0.2321), agentic
1.9232 % (−0.0009), 490 completion tokens saved across the whole population.**

It is named, not recommended. Section 7 says what it is worth.

### 5.4 Projected onto the 1,500 rows a cell would actually fly

The three model-usage cells fly `E22-DEV-ESB-1500-V1` (roster
`docs/receipts/rosters/e22-dev-esb-1500-v1.json`, identity `c626e62f…`, 150 rows per call, seed
20260906), not the full 6,038. The same frontier restricted to those rows, with the two constants
**re-measured on the subset** because a cell that flies the subset would measure them there too:

| alpha | rows capped | benefit | harm (realized) | bleed rows cut (of 218) | corpus WER % | Δ WER | agentic % | Δ agentic |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| uncapped baseline | — | — | — | — | **17.4012** | — | **1.9161** | — |
| 0.60 | 778 | 229 | 549 | 112 | 18.3764 | +0.9752 | 3.3751 | +1.4590 |
| 0.70 | 499 | 192 | 307 | 65 | 16.6127 | −0.7885 | 2.3237 | +0.4076 |
| 0.80 | 311 | 134 | 177 | 32 | **16.5251** | **−0.8762** | 2.0418 | +0.1257 |
| 0.90 | 210 | 110 | 100 | 19 | 16.5937 | −0.8076 | 1.9771 | +0.0610 |
| 1.00 | 161 | 89 | 72 | 15 | 16.7536 | −0.6476 | 1.9542 | +0.0381 |
| 1.25 | 83 | 51 | 32 | 7 | 17.0279 | −0.3733 | 1.9390 | +0.0229 |
| **1.50** | **50** | **35** | **15** | **5** | **17.1765** | **−0.2248** | **1.9428** | **+0.0267** |
| 1.75 | 35 | 28 | 7 | 3 | 17.2336 | −0.1676 | 1.9275 | +0.0114 |
| 2.00 | 27 | 22 | 5 | 1 | 17.2679 | −0.1333 | 1.9314 | +0.0153 |
| 2.50 | 14 | 10 | 4 | 0 | 17.3441 | −0.0571 | 1.9123 | −0.0038 |
| 3.00 | 8 | 5 | 3 | 0 | 17.3746 | −0.0267 | 1.9161 | ±0.0000 |

The shape is the full population's and the magnitudes are close, which is the point of reporting
both. **The one thing that does not survive the projection is the exact sign of the agentic delta at
alpha 1.5**: on 6,038 rows it is −0.0009 and on 1,500 it is +0.0267, on 50 capped rows of which 15
are harmed. That is noise around zero at this sample size, and it is exactly why the companion
preregistration's admission rule reads a CI90 against a non-inferiority margin rather than a point
estimate — a rule fixed before the flight, and fixed here in the open with both numbers on the page.

## 6. Stop strings: there are none to add, and this is a code fact

`core.model.request_types.ALLOWED_DECODING_KEYS` is the governance choke point every request passes
through, and it admits exactly `temperature`, `seed`, `top_p`, `top_k`, `min_p`, `max_tokens`,
`presence_penalty`, `frequency_penalty`, `response_format`, `id_slot`, `logprobs`, `top_logprobs`.
**There is no `stop` key and no `repeat_penalty` key**, so this study's transport cannot send a stop
string today; adding one is a seam change with its own tests, not a config value.

Nor is there a stop string to add. The Qwen3-Omni model card's ASR recipe, as this repository's own
records carry it (the 2026-09-05 A/B verdict's arm B and the 2026-09-05 shape-C prompt-fit render),
specifies an instruction string and a message placement and no stop sequence; the pinned GGUF chat
template terminates on `<|im_end|>`, which llama-server already stops on and which every one of the
6,038 sealed rows reached (zero rows hit the 1,024 ceiling, section 2). **Inventing a stop string —
a full stop, a newline — would be this study adding a convention no published recipe carries, on a
corpus whose references are multi-sentence.** It is refused by name here so the stop-cap cell cannot
quietly acquire it later.

The one decode parameter that IS available and unused is `max_tokens`, which llama-server maps to
`n_predict`. It is composed per cell, not per sample, so a duration-proportional cap needs a
per-sample resolution seam — the preregistration specifies it.

## 7. What this licenses, and what it names next

**It licenses no fix, no number and no cap.** No hypothesis was post-processed, no scorer changed,
no arm re-scored, no published figure restated.

**It closes the "over-generation is a runaway" reading, which nothing had yet closed.** The
2026-09-04 test verdict named over-generation on the strength of a 5.48-point oracle length cut; the
2026-09-05 shape-C verdict falsified "length is the cause" by showing an arm that shortened the
output scored worse and its oracle floor ROSE; the 2026-09-06 scan located 47.6 % of the error mass
at the clip boundary. This note supplies the missing piece: the surplus is +1 word on the median
over-long row, it grows with clip length rather than shrinking, the rows that bleed look like the
rows that do not, and 87.5 % of rows end on a full stop. **There is no length signal to act on, so
no length intervention can recover the gap.** The best case on the whole declared ladder is 0.73 dev
points, and taking it costs the agentic rate.

**Is the stop-cap cell worth flying?** On these numbers it buys a predicted 0.23 points against a
6.15-point test gap, and this note says so rather than dressing it up. Its remaining value is that
the prediction is falsifiable: if a capped flight's measured effect diverges from −0.2321, either
the token-to-word mapping or the "greedy under a cap returns the same prefix" assumption is wrong,
and both are assumptions several other pieces of this account rest on. That is a real reason to fly
it and a poor reason to prioritise it.

**Named for the owner, and NOT done here:**

1. **The remaining two model-usage faces**, both preregistered in
   `docs/readiness/2026-09-06-e22-dev-usage-cells-v1-preregistration.md` and neither flown: the
   decoder quantization (Q8_0) and the audio front-end decode path. This note bounds the third face
   — decode discipline — at 0.73 points and shows the achievable share of that is 0.23.
2. **The boundary-exact cell** (`docs/readiness/2026-09-06-e22-dev-boundary-exact-v1-preregistration.md`
   §1) remains the intervention that addresses the mechanism this note keeps pointing at. It is a
   protocol correction rather than a usage knob and is queued behind whatever is flying.
3. **The `whisper-large-v3` anchor** (same preregistration, §2). Its blocking precondition was an
   umbrella lock entry and a fetch; a `whisper-large-v3` directory now exists under
   `$SPEECHRL_DATA_DIR/models/` with a `.speechrl-asset.json` receipt, so that precondition may
   already be cleared. **This row did not open it, did not verify it against the umbrella lock, and
   claims nothing about it** — the check belongs to that cell's own registration.

## 8. Limits

* **The token-to-word mapping inside a row is linear on that row's own measured ratio**, not the
  flight tokenizer's segmentation. Every capped-row figure and every simulated WER inherits it.
* **The simulated WER is a prediction, not a measurement.** No capped request was ever sent.
* **The agentic-rate column re-runs the 2026-09-06 taxonomy on truncated hypotheses.** The
  taxonomy's own stated limits — a bounded span length, a 0.6 acoustic threshold, an unvalidated
  impact model — transfer here unchanged.
* **`words_per_second_p95` and `tokens_per_word` are fitted on this dev population.** A cell that
  applied them to a different population would be transferring two constants, and the
  preregistration says so.
* **Population is DEV ONLY.** Nothing here transfers to the six ESB test calls by measurement.

## 9. Cost and conduct

| | value |
|---|---:|
| frozen-core contacts | **0** |
| tokenizer / embedder / retriever / scorer contacts | **0** |
| outbound network connection attempts (offline guard) | **0** |
| GPU hours | **0** |
| audio decoded | **0** s |
| paid API spend | **0** |
| wall time | ~2 min, one process |

**Conduct.** Only the sealed 2026-09-05 dev arm A outputs and trace, the hash-pinned dev10
reference layer (`8da3a65d…`, re-hashed on load), the hash-pinned dev10 segment table
(`51257011…`, re-hashed on load) and the committed clip-boundary per-clip table (re-hashed against
its own `MANIFEST.sha256`) were read. **The six ESB test calls were not opened.** The 109 remaining
confirmatory Earnings-22 calls were not named, loaded or read. **No dev sentence text is written to
any committed file**: `per-row-table.csv` carries identifiers, durations, word counts, token counts
and flags, and neither a reference nor a hypothesis appears in it — a unit test pins that.

**Gates.** `scripts/checks/engineering_base_check.py` **PASS**. `ruff check` clean on all three new
files. `pytest tests/unit/test_e22_overgeneration.py` 41 passed.
