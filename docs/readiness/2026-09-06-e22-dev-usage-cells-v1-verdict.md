# Earnings-22 model-usage cells (a) and (b) — the paired verdict

**CELL (a), THE Q8_0 DECODER, IS ADMITTED: −0.4305 corpus-WER points with a call-stratified CI90
of [−0.6468, −0.2177] and an agentic CI90 upper bound of +0.0192, so both preregistered clauses
hold. CELL (b), THE DURATION-PROPORTIONAL CAP, IS NOT ADMITTED, and it fails BOTH clauses: the WER
CI90 upper bound is +0.0149 and the agentic CI90 upper bound is +0.0544 against a margin of
+0.05.** The cap bit 68 rows against a predicted 50, and its measured gain is not the mechanism it
was preregistered as — **22 of the 37 error operations it removed came from the 1,432 rows the cap
could not touch**.

**The number that outlasts both decisions is a null.** On those 1,432 cap-inert rows the request
differed from arm A's only by an inert `max_tokens` integer larger than the generation, so nothing
could change — and the corpus WER still moved **−0.0844 points, CI90 [−0.2356, +0.0692]**, with
302 of 1,432 rows emitting different bytes. That is the first *measured* null for this runtime's
greedy non-determinism, it is about a fifth of the admitted cell (a) effect, and every cross-run
Earnings-22 contrast this study has drawn or will draw sits on top of it.

**Model usage is now closed as an explanation of the Earnings-22 gap.** All three of its faces have
been measured: the prompt text (arm B, 0.83 points the wrong way), the request shape (arm C, 0.325
the wrong way, oracle floor rising) and now the decoder quantization (0.43 points the right way) and
the decode discipline (0.14 points, not admitted, half of it jitter). Against the six-call test gap
of **6.15 points** (15.937 against the same model's published 9.79), the largest thing this study
can buy inside its own serving path is **7 %** of it.

Row `SAEA-E22-MF-USAGE-CELLS-VERDICT-V1` (`model-free-check`), registered before the first sealed
score file was read. **Zero contacts of every kind** — model, tokenizer, embedder, retriever,
network, GPU, audio decode — and the offline guard recorded **zero outbound connection attempts**.
Receipts: `docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-dev-usage-cells/verdict/`
(`MANIFEST.sha256`; `summary.json` sha256 `44ded9e3…`, `per-call-table.csv` `e2dc8338…`,
`README.md` `252e5ea9…`). Module `analysis/e22_usage_cells.py`, runner
`scripts/e22_usage_cells_read.py`, tests `tests/unit/test_e22_usage_cells.py`. Two back-to-back
writes reproduce the same `MANIFEST.sha256`.

**Population: DEV ONLY.** `E22-DEV-ESB-1500-V1`, split identity
`c626e62f8876bf52a2904a0d2ec91807a530f3195c10facc8c036f661b2bf88a`, 1,500 rows at 150 per call over
all ten dev subset10 calls, 26,251 reference words under the Whisper `EnglishTextNormalizer`. **The
six calibration-exposed ESB test calls were not opened** (`test_split_read: false`): the reference
loader is pinned to the dev10 receipt alone and the segment-table loader to the dev10 extracted
table. The 109 confirmatory calls are not named, loaded or read.

---

## 1. The identity gate

Nothing below was computed until six hard-coded raw pairs reproduced. They are hard-coded in the
runner, not in the module, so the gate is visible at the call site; `build_receipts` raises and
writes nothing on a single drifted digit.

| arm | source of the anchor | corpus WER % (Whisper) | agentic error rate % |
|---|---|---:|---:|
| A, restricted to these 1,500 | preregistration §0 | **17.4012** | **1.9161** |
| cell (a) `SAEA-E22-DEV-ESB-Q8-V1` | its own flight row | **16.9708** | **1.8552** |
| cell (b) `SAEA-E22-DEV-ESB-STOPCAP-V1` | its own flight row | **17.2603** | **1.9009** |

All six reproduced. The corpus figures come from the sealed per-sample rows of the paper-facing
`asr-wer-esb-whisper` scorer; the agentic figures come from `analysis.e22_error_taxonomy` at its
committed version, whose own aligner independently returns the same S/D/I on every arm.

**The finalize rows are the verified rows.** Arm A was never re-scored with `--include-per-sample`
through `core.scoring_batch`, so the finalize `<run_id>.scores.json` block is the one per-sample
table all three arms carry and is the single reading path. Both cells also have a verified
`score-batch-per-sample` result (`"verified": true`), and each was compared row for row against its
finalize block: **1,500 rows compared per cell, zero disagreements.**

**The statistics module, and why the pooled call is `resampled_statistic`.** Section 4 names
`analysis.paired` with 10,000 replicates, stratified by source call, seed 20260903, CI90. Corpus
WER and the agentic error rate are both `sum(numerator) / sum(denominator)` over the resampled rows,
not the mean of a per-row difference, and `analysis.paired`'s own docstring says a pooled ratio
belongs in `resampled_statistic`, which "gets the identical draws" as `paired_contrast`.
`paired_contrast` is used unchanged for the per-utterance saves / harms / ties and the exact sign
test, which are per-unit statistics.

---

## 2. Cell (a) — the Q8_0 decoder — **ADMITTED**

One factor: the decoder GGUF is the umbrella lock's Q8_0 file instead of the Q4_K_M requant, on the
same build, the same bf16 mmproj by sha256, the same audio bytes, the same instruction, the same
geometry and the same scorers.

| metric, signed `cell − arm A` | point | call-stratified CI90 | call-clustered CI90 |
|---|---:|---|---|
| corpus WER (Whisper normalizer), points | **−0.4305** | **[−0.6468, −0.2177]** | [−0.6063, −0.2368] |
| agentic error rate, points | **−0.0610** | **[−0.1494, +0.0192]** | [−0.1155, −0.0079] |

**The rule, applied unmodified.** Clause 1: corpus WER improves and the CI90 upper bound is
−0.2177 < 0 — **holds**. Clause 2: the agentic CI90 upper bound is +0.0192 < +0.05 — **holds**.
**ADMITTED as a model-usage local optimization.** The agentic metric moved the same way as the WER
rather than against it, which is the first time on this carrier that the two have agreed; the
clustered interval on the agentic delta excludes zero outright.

Per-utterance: **195 saves, 141 harms, 1,164 ties**, exact sign test *p* = 0.0038; mean
per-utterance WER −1.4918 points — the decoder change leaves 1,164 of 1,500 rows scoring exactly as
arm A did.

**Where the 113 removed error operations went, and where they did not.**

| category | arm A mass | cell (a) mass | Δ |
|---|---:|---:|---:|
| other (function/content-word swaps) | 1,234 | 1,191 | **−43** |
| model-behaviour | 1,390 | 1,354 | **−36** |
| acoustic-misrecognition | 343 | 331 | −12 |
| reference-convention | 233 | 223 | −10 |
| segmentation-artifact | 924 | 914 | −10 |
| format-convention | 96 | 94 | −2 |
| **named-entity** | **299** | **299** | **0** |
| **domain-term** | **49** | **49** | **0** |

**The higher-precision decoder buys exactly nothing on named entities or domain terms** — the two
classes the agentic metric is about. Named-entity HIGH spans move 219 → 217, domain-term HIGH stays
at 1. The −0.0610 agentic gain is 13 HIGH spans out of the `other` bucket, not a recognition gain
on names. A cell that is admitted on corpus WER and is neutral on the decision-relevant class is
exactly what the two-clause rule was written to be able to say.

---

## 3. Cell (b) — the duration-proportional cap — **NOT ADMITTED**

One factor: `max_tokens` resolved per sample as
`min(1024, max(1, ceil(1.5 · seconds · 4.9992 · 1.2992)))` instead of the cell-wide 1024, on the
same Q4_K_M decoder and everything else byte-identical.

| metric, signed `cell − arm A` | point | call-stratified CI90 | call-clustered CI90 |
|---|---:|---|---|
| corpus WER (Whisper normalizer), points | −0.1409 | **[−0.2967, +0.0149]** | [−0.3698, +0.0915] |
| agentic error rate, points | −0.0152 | **[−0.0903, +0.0544]** | [−0.0848, +0.0444] |

**The rule, applied unmodified.** Clause 1: the WER CI90 upper bound is +0.0149, not below zero —
**fails**. Clause 2: the agentic CI90 upper bound is +0.0544, above the +0.05 margin fixed before
any number existed — **fails by 0.0044 points**. **NOT ADMITTED, on both clauses.** The margin was
inherited verbatim from §1.6 of the boundary-exact preregistration and is not adjusted here; a
0.0044-point miss is a miss.

Per-utterance: 98 saves, 73 harms, 1,329 ties, sign test *p* = 0.066.

### 3.1 The §2.2 prediction check

The prediction was fixed in writing before any capped request existed, precisely so it could be
wrong. It is wrong in an informative direction on every line.

| | predicted | measured |
|---|---:|---:|
| rows the cap bites | 50 | **68** |
| of those, benefit (cut stayed inside surplus) | 35 | **59** |
| of those, harm (cut below the row's own reference length) | 15 | **9** |
| bound rows that actually **lost reference words** in the alignment | — | **3** |
| corpus WER % | 17.1765 (−0.2248) | **17.2603 (−0.1409)** |
| agentic error rate % | 1.9428 (+0.0267) | **1.9009 (−0.0152)** |

The three rows that lost reference words are all very short clips whose cap is correspondingly
tiny: `4469088-654` (0.2199 s, cap 3, +1 deletion), `4482613-366` (0.4004 s, cap 4, +2) and
`4482613-581` (1.1201 s, cap 11, +3) — six extra deletions in the whole population. **The harm side
of the simulation was over-predicted and the benefit side under-predicted**, and the agentic delta
came out on the opposite side of zero from the projection. The operating point was chosen on the
agentic metric and the agentic metric did not, in the end, worsen; it simply did not worsen for the
reason the simulation gave.

**Assumption 1 of §2.2 — that a capped greedy decode returns the uncapped decode's token prefix —
holds on 56 of the 68 bound rows** (28 of them byte-identical to arm A, 28 strict prefixes) and
fails on 12. That is not a clean refutation: arm A's own text is not bitwise reproducible on this
runtime, so a non-prefix row is jointly the assumption and the jitter §3.2 measures.

### 3.2 The cap-inert null — the finding this cell actually bought

Split the population by whether the cap could bind at all:

| rows | arm A error ops | cell (b) error ops | Δ | pooled delta on their own denominator, stratified CI90 |
|---|---:|---:|---:|---|
| 68 bound (completion tokens = own cap) | 202 | 187 | **−15** | −7.6531 [−14.1243, −2.1858] |
| **1,432 cap-inert** | **4,366** | **4,344** | **−22** | **−0.0844 [−0.2356, +0.0692]** |
| 1,500 total | 4,568 | 4,531 | −37 | −0.1409 [−0.2967, +0.0149] |

**Where it binds, the cap works — and it is not where most of the gain came from.** On the 68 bound
rows the effect is large and its interval excludes zero. On the 1,432 rows where the only difference
from arm A's request was an integer too large to reach, **302 rows emitted different bytes, 159
rows' score rows changed, and the pooled WER still moved −0.0844 points.** Those rows cannot have
been changed by the cap. They were changed by the runtime.

This is the study's first *measurement* of a fact it has been asserting since 2026-09-05: greedy
decoding at temperature 0 is not bitwise reproducible across batch compositions on this llama.cpp
build, so a cross-run paired contrast on this population carries a same-request noise term whose
CI90 is roughly **±0.15 points around a point estimate of −0.08**. Three consequences, and none of
them is optional reading:

1. **It does not overturn cell (a).** The rule was fixed in advance, it reads the paired bootstrap
   over sampling variation, and the null's own point estimate is only −0.0844 with an interval
   straddling zero. Cell (a) is admitted as written.
2. **It sizes cell (a) honestly.** If the same run-level offset applies to the Q8 flight, roughly
   0.08 of the 0.4305 points is run-level rather than quantization. The effect survives that; the
   *point estimate* should never be quoted to four digits as though it were a physical constant.
3. **It is a reporting obligation for every future Earnings-22 cell.** Any single-factor cell whose
   preregistered effect is smaller than about 0.25 corpus-WER points on 1,500 rows cannot be
   distinguished from this null by one flight, and must either be sized larger, replicated, or not
   flown. Cell (b)'s whole preregistered payoff was −0.2248.

### 3.3 Where the cap's mass moved

| category | arm A | cell (b) | Δ |
|---|---:|---:|---:|
| model-behaviour | 1,390 | 1,332 | **−58** |
| named-entity | 299 | 295 | −4 |
| acoustic-misrecognition | 343 | 342 | −1 |
| format-convention | 96 | 101 | +5 |
| reference-convention | 233 | 235 | +2 |
| domain-term | 49 | 51 | +2 |
| segmentation-artifact | 924 | 932 | +8 |
| other | 1,234 | 1,243 | +9 |

The signature is coherent with a length cap and with nothing else: the whole gain is
`model-behaviour` (`runaway-tail` 1,179 → 1,137, `runaway-head` 70 → 56, −56 of the −58), and +26
operations are handed back across six other categories — which is the jitter of §3.2 wearing a
category label.

---

## 4. Mandatory reporting (preregistration §4)

### 4.1 Per call, all ten, both normalizers

| call | rows | ref words | A | (a) | Δ(a) | (b) | Δ(b) | A `saea-v1` | (a) `saea-v1` | (b) `saea-v1` | A agentic | (a) agentic | (b) agentic |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `4453225` | 150 | 2,662 | 20.9992 | 20.3606 | −0.6386 | 20.9992 | +0.0000 | 25.9001 | 25.6429 | 25.7164 | 1.1270 | 1.0518 | 1.0143 |
| `4469088` | 150 | 1,946 | 18.5509 | 17.9342 | −0.6167 | 17.9856 | −0.5653 | 22.4837 | 21.7326 | 21.4321 | 2.6208 | 2.4152 | 2.2610 |
| `4470684` | 150 | 2,581 | 13.6769 | 13.6381 | −0.0388 | 13.6769 | +0.0000 | 21.3121 | 21.6020 | 21.3121 | 1.3948 | 1.3173 | 1.3948 |
| `4474506` | 150 | 2,993 | 13.9659 | 13.6318 | −0.3341 | 13.6318 | −0.3341 | 19.4690 | 19.7640 | 19.2396 | 1.8376 | 1.8710 | 2.0047 |
| `4479944` | 150 | 2,773 | 23.8370 | 23.4043 | −0.4327 | 23.8731 | +0.0361 | 30.4191 | 30.2746 | 30.7442 | 2.8128 | 2.7047 | 2.9210 |
| `4481952` | 150 | 2,166 | 16.7590 | 15.9741 | −0.7849 | 15.6048 | −1.1542 | 21.8792 | 21.4765 | 20.9843 | 1.8467 | 1.9391 | 1.7544 |
| `4482383` | 150 | 3,015 | 14.7927 | 14.0299 | −0.7628 | 14.5937 | −0.1990 | 19.2128 | 18.9460 | 18.9460 | 1.5920 | 1.3599 | 1.5589 |
| `4482613` | 150 | 2,386 | 22.6739 | 23.1350 | **+0.4611** | 23.5960 | **+0.9221** | 29.7605 | 30.6943 | 30.6537 | 4.1492 | 4.1911 | 4.2330 |
| `4483937` | 150 | 2,567 | 16.7900 | 15.9720 | −0.8180 | 16.5563 | −0.2337 | 21.8681 | 21.3491 | 22.0163 | 1.6751 | 1.5582 | 1.5972 |
| `4485192` | 150 | 3,162 | 13.7571 | 13.4092 | −0.3479 | 13.6939 | −0.0632 | 16.1929 | 16.3845 | 16.2568 | 0.7274 | 0.7590 | 0.7590 |

Cell (a) improves nine of ten calls and worsens `4482613` by 0.46; cell (b) improves six, is exactly
flat on two and worsens `4482613` by 0.92. `4482613` is the population's worst call for both cells
and carries its highest agentic rate (4.15 %) — it is the one call where more decoder precision
does not help, and that is on the record rather than smoothed away.

### 4.2 Weightings, side by side

| arm | natural mixture, corpus WER | equal-call, corpus WER | natural agentic | equal-call agentic |
|---|---:|---:|---:|---:|
| A | 17.4012 | 17.5803 | 1.9161 | 1.9783 |
| (a) Q8_0 | **16.9708** | **17.1489** | **1.8552** | **1.9167** |
| (b) cap | 17.2603 | 17.4211 | 1.9009 | 1.9498 |

The verdict does not turn on the weighting: cell (a) is −0.4304 natural and −0.4314 equal-call,
cell (b) −0.1409 and −0.1592.

### 4.3 Error shape and length ratio

| arm | S | D | I | ref words | hyp words | hyp/ref | I share of errors | mean per-utterance WER | `saea-scoring-v1` corpus |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 1,140 | 592 | 2,836 | 26,251 | 28,495 | 1.0855 | 62.08 % | 31.3566 | 22.6419 |
| (a) | 1,117 | 587 | 2,751 | 26,251 | 28,415 | 1.0824 | 61.75 % | 29.8648 | 22.6009 |
| (b) | 1,141 | 593 | 2,797 | 26,251 | 28,455 | 1.0840 | 61.73 % | 30.2146 | 22.5524 |

Insertions are 62 % of all errors on every arm and neither cell moves that materially: cell (a)
removes 85 insertions, 23 substitutions and 5 deletions; cell (b) removes 39 insertions and adds a
substitution and a deletion. **Neither cell changes the shape of this corpus's error — both trim
it.** Under the frozen `saea-scoring-v1` normalizer the ordering flips (cell (b) 22.5524 is the best
of the three), which is a normalizer artefact and is why the paper-facing scorer is named in
advance.

### 4.4 Utterance-duration decomposition

| bucket | rows | ref words | A | (a) | Δ(a) | (b) | Δ(b) |
|---|---:|---:|---:|---:|---:|---:|---:|
| [0, 1) s | 116 | 277 | 74.0072 | 72.5632 | −1.4440 | 68.2310 | **−5.7762** |
| [1, 2) s | 109 | 537 | 42.0857 | 37.9888 | **−4.0969** | 41.8994 | −0.1863 |
| [2, 4) s | 291 | 2,656 | 27.2214 | 26.2801 | −0.9413 | 27.4473 | +0.2259 |
| [4, 8) s | 488 | 7,657 | 20.2168 | 19.6813 | −0.5355 | 19.7858 | −0.4310 |
| [8, 16) s | 425 | 11,695 | 13.1595 | 13.0312 | −0.1283 | 13.2706 | +0.1111 |
| [16, ∞) s | 71 | 3,429 | 9.5363 | 9.3613 | −0.1750 | 9.3613 | −0.1750 |

Both cells' gains concentrate on short clips, which is where the surplus is largest relative to a
tiny denominator; the cap's entire visible win is the 116 sub-second rows (277 reference words,
1.1 % of the corpus), which is a further reason its pooled interval touches zero.

### 4.5 The boundary block, before and after

| arm | `segmentation-artifact` | `runaway-tail` | `runaway-head` | total ops | WER points | share of the arm's WER |
|---|---:|---:|---:|---:|---:|---:|
| A | 924 | 1,179 | 70 | 2,173 | **8.2778** | **47.6 %** |
| (a) Q8_0 | 914 | 1,137 | 77 | 2,128 | 8.1064 | 47.8 % |
| (b) cap | 932 | 1,137 | 56 | 2,125 | 8.0949 | 46.9 % |

Tail insertion containment against the *next* published utterance's own reference, arm A → (a) →
(b): spans at ≥ 0.6 containment 218 → 224 → 214, words matched at 0.6 397 → 404 → 380, total tail
insertion words 1,950 → 1,892 → 1,914. Head: spans at ≥ 0.6 containment 73 → 79 → 71.

**The boundary block does not move.** Cell (a) removes 45 of 2,173 boundary operations (2.1 %) and
cell (b) 48 (2.2 %), and in both cases the block's *share* of the arm's own WER is unchanged or
higher. Nearly half of this corpus's error mass is speech at a clip boundary, and no model-usage
knob touches it.

---

## 5. The alignment account, restated with numbers

The Earnings-22 short-form line is **15.937** corpus WER on the six ESB test calls, read once on
2026-09-04, against the *same frozen model's* published **9.79** (NVIDIA NeMo AutoModel, Whisper
`EnglishTextNormalizer`, greedy) and **12.3** (Nemotron 3 Nano Omni Table 8). That is a 6.15-point
gap against the primary target and 3.64 against the cross-read, with the number sitting above
`whisper-large-v3`'s published 11.59 and even above `base.en`'s 15.09.

Six candidate explanations have now been measured, all on dev, all single-factor, all paired
against sealed arm A:

| suspect | cell | measured worth | direction |
|---|---|---:|---|
| the instruction text | arm B, 2026-09-05 | 0.83 points | **wrong way** |
| the request shape | arm C, 2026-09-05 | 0.325 points, oracle floor rising | **wrong way** |
| the clip boundary as a *comparability* difference | array-durations audit, 2026-09-06 | 0 | the ESB release ships the same overlap |
| a scoring-convention fold | semantic scan, 2026-09-06 | ≤ 0.35 points, 0.25 with a published authority | right way, unlicensed |
| **the decoder quantization** | **cell (a), here** | **0.4305 points** | **right way, ADMITTED** |
| **the decode discipline** | **cell (b), here** | **0.1409 points, half of it jitter** | **right way, NOT ADMITTED** |

**What quantization and decode discipline are worth, stated plainly.** Serving the Q8_0 file instead
of the Q4_K_M requant is worth 0.43 corpus-WER points on this study's dev subset — real, repeatably
signed, and **7 % of the 6.15-point test gap**. A duration-proportional generation cap is worth at
most 0.14 points and does not clear its own preregistered bar. Together, and being generous by
adding two effects that were never shown to compose, the two faces of model usage this study can
still control account for **under 0.6 of 6.15**.

**Where the unexplained mass sits, by category, on arm A's 1,500 rows (17.4012 points):**

| block | WER points | share |
|---|---:|---:|
| boundary (`segmentation-artifact` + `runaway-tail` + `runaway-head`) | **8.2778** | **47.6 %** |
| `other` — function/content-word swaps | 4.7008 | 27.0 % |
| `model-behaviour` outside the two runaway rules | 0.5370 | 3.1 % |
| `acoustic-misrecognition` | 1.3066 | 7.5 % |
| `reference-convention` (verbatim-transcript artefacts) | 0.8876 | 5.1 % |
| `named-entity` | 1.1390 | 6.5 % |
| `format-convention` | 0.3657 | 2.1 % |
| `domain-term` | 0.1867 | 1.1 % |

The residual is dominated by one block, that block is *boundary-triggered continuation*, and cell
(a) — the largest untested runtime factor in the whole account — moved 2.1 % of it. The agentic
error rate, which is what this study says it cares about on this carrier, is **1.9161 %** against a
corpus WER of 17.4012 %, a factor of 9.1, and cell (a) improves it by 0.06 points while leaving
named entities and domain terms untouched to the span.

---

## 6. What an admitted cell does **not** buy

**Neither admitted setting reaches the sealed test outputs, and this document does not authorize a
read that would.** §4 of the preregistration is explicit and is inherited here in full: an admitted
cell's setting is applied to the sealed six-call test outputs **only where it is a scorer-side
change** — a normalizer or an aggregation, applied to bytes already sealed, needing no new contact.

**Cell (a) is not scorer-side.** Q8_0 changes the decoder, so applying it to the test population
would require **re-flying the six ESB test calls** — a *second* read of a population the 2026-09-04
owner allowance permitted **once**. Such a read may be **proposed** to the owner and can never be
taken on this document's authority; it would need its own owner decision, its own exposure row, its
own `contracts.ExecutionPlan`, and it inherits §4's claim rule unchanged. Cell (b) is not
scorer-side either, and it is not admitted, so the question does not arise for it.

Everything in this verdict is therefore a **dev** number on a 1,500-row subset of the split this
study may optimize on. **No cell here is an alignment verdict**, neither is compared to 9.79 or 12.3
as a difference, and those figures appear as orientation only.

---

## 7. Recommendation for the E22 short-form alignment line

**Keep it NOT ALIGNED, at 15.937, and record the serving-path reason as measured rather than
suspected.**

The line in `docs/readiness/2026-09-05-scoring-alignment-conclusions.md` reads *"Earnings-22, ESB
short-form test (6 confirmatory calls, read once) | 15.937 | 9.79 (NeMo) / 12.3 (Nemotron) |
whisper-large-v3 11.59, base.en 15.09 | **NOT ALIGNED**"*. Nothing here changes it, and two separate
reasons say so:

1. **Arithmetically it cannot change.** An admitted dev setting does not alter a test number that
   was never re-flown. 15.937 is what the sealed Q4_K_M test outputs score, and they remain the only
   test measurement this study owns.
2. **Even if it were re-flown, 0.43 points does not close 6.15.** Extrapolating cell (a)'s dev gain
   to the test population at face value would put a re-flown test cell near 15.5 — still above
   `base.en`, still 5.7 points from the target, still NOT ALIGNED and still on the wrong side of
   the owner's hard floor, which says this study's number must never be worse than a degraded
   model's published one — and `base.en`'s 15.09 is a degraded model's published one.

**The documented serving-path reason, now measurable rather than asserted.** The published 9.79 is a
bf16/fp16 HF-transformers serving path; this study serves a Q4_K_M GGUF requant through llama.cpp
across an API-shaped boundary, which is a deliberate, contract-level property of the study and not a
defect. That quantization term is now **measured at 0.43 points at Q8_0**, and Q8_0 is itself not
bf16, so the remaining quantization headroom is unmeasured but bounded in the same direction and
plainly small relative to the gap. Everything else about the serving path that could be varied
inside the boundary — the prompt text, the request shape, the generation cap, the clip cut — has now
been varied, and the largest of them is 0.83 points *the wrong way*. **The residual is not in the
serving path this study controls; it is in how the frozen core behaves on short, overlapping clips,
and that is where the remaining 8.3 dev points sit.**

The line should carry that sentence, and it should carry the 2026-09-04 audit's warning unchanged:
the 3-point band is smaller than the literature's own protocol noise, and — as of this document —
wider than this runtime's own same-request noise interval by only a factor of about ten.

---

## 8. What is still worth a GPU, and what is not

**Worth it, in this order.**

1. **`SAEA-E22-DEV-WHISPER-ANCHOR-V1`, the whisper-large-v3 anchor** (cell 2 of
   `docs/readiness/2026-09-06-e22-dev-boundary-exact-v1-preregistration.md`). It is the only
   remaining measurement that converts *"the residual is output discipline, not recognition"* from a
   reading into a number, because it puts a second system on the identical overlapping audio and
   reports the same boundary block. Its 4.861-point core-capability figure has been a **ceiling**
   in three consecutive verdicts and should stop being one. It is a **tool-model** run: zero
   frozen-core contacts, ~1.0 GPU-h, and the study's no-transcript-state ruling stands — the output
   is a measurement instrument read once into a verdict, never evidence, a prompt, a rescoring
   signal or part of any mechanism. **Its blocker is an umbrella action, not a study action**: the
   umbrella must admit a `whisper-large-v3` entry to `docs/datasets.lock.json`. The over-generation
   row recorded, without acting on it, that such a directory with a `.speechrl-asset.json` receipt
   now exists under `$SPEECHRL_DATA_DIR/models/`; **that observation must be checked against the
   umbrella lock before it is treated as the precondition clearing.**
2. **`SAEA-E22-DEV-ESB-BOUNDARY-EXACT-V1`, the boundary-exact sensitivity cell** (cell 1 of the same
   preregistration), and it should be flown as a **sensitivity test with an honest prior**, not as a
   fix. §4.5 above sharpens what it can return: the boundary block is 8.2778 of arm A's 17.4012
   points on these rows, but the audit's own ceiling says a re-cut can return at most ≈1,760 words
   of the 7,318 tail insertion words on the full 6,038, because most of the mass is continuation the
   overlap *triggers* rather than speech it *delivers*. Its §1.6 rule and its +0.05 agentic margin
   are already written; **§3.2 of this document adds one requirement to it — its preregistered
   effect must be sized against the −0.0844 [−0.2356, +0.0692] same-request null, and if the
   expected effect is under about 0.25 points it needs a replication built into the plan or it
   should not fly.**

**Not worth it.**

* **Another single-factor model-usage cell.** All three cells of the preregistration are closed:
  the audio front end by the owner (cell (c), 2026-09-06), the quantization by cell (a), the decode
  discipline by cell (b). There is nothing left in this family to test.
* **A cap at another alpha.** The frontier was published, alpha 1.5 was chosen on the
  decision-relevant metric in advance, and picking a different rung after seeing this result is
  tuning on the outcome. The measured 68-row bite already exceeds the simulator's own projection, so
  the frontier's arithmetic is the thing that would need repair first, not the operating point.
* **A test read of either cell.** §6, and it is the owner's to give, not this document's to take.
* **A cell (a) replication for the dev claim.** The claim is admitted as preregistered and does not
  need one. A replication *is* required before cell (a) is ever proposed to the owner as the basis
  for a second test read, precisely because §3.2 measured a null that is a fifth of its effect.

---

## 9. Row closure

`SAEA-E22-MF-USAGE-CELLS-VERDICT-V1` is **COMPLETED** as registered. Zero model, tokenizer,
embedder, retriever, scorer, network, GPU and audio contacts; zero outbound connection attempts
recorded by the offline guard; zero paid spend. No cell was re-flown, no hypothesis post-processed,
no scorer or normalizer edited, no population re-scored, no published figure restated, and
`test_split_read` is `false`. No superiority, generality or Stage-3 claim; exposed dev data; no knob
was tuned on it.
