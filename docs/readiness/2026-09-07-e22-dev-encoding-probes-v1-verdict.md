# The three Earnings-22 short-clip encoding probes — the paired verdict

**CELL 2 (`tail-silence-2s`) AND CELL 3 (`pad-30s`) ARE BOTH ADMITTED, AND THEY DID WHAT NO
MODEL-USAGE KNOB COULD: THEY MOVED THE BOUNDARY BLOCK.** Two seconds of appended digital silence
takes corpus WER from **17.4012 to 9.4054** — a paired **−7.9959** points with a call-stratified
CI90 of **[−8.5203, −7.5007]** — and takes the boundary block from **8.2778 to 1.0971** WER points,
**−7.1807 [−7.6649, −6.7379]**, which is **86.7 % of the block** against clause 3's 2.0-point
requirement. Padding to 30.0 s lands in the same place (**9.3254**, boundary **0.9181**) for
**3.39× the audio tokens**. **Cell 1 (`boundary-exact`) is NOT ADMITTED**: it is a real effect
(−3.0475 corpus WER, −2.7808 boundary) that fails clause 2 alone, its agentic CI90 upper bound
being **+0.0637** against the **+0.05** margin fixed before any number existed.

**The mechanism is the discontinuity, not the constant.** `pad-30s` more than doubles the encoder's
zero-pad block (75,330 → 148,412 padded mel frames, and every one of the 1,500 clips carries one
instead of 1,498) and still wins by a hair; `tail-silence-2s` leaves the block's size and row count
*exactly* unchanged and merely moves it 2.0 s from the last word, and captures the whole effect.
The 8.2778 points of boundary error were never the encoder spending 13 tokens on a constant. They
were **the model completing an utterance whose signal stopped mid-speech.**

**And the two ends are not the same phenomenon.** Tail insertion spans collapse **704 → 39 → 21**
and tail inserted words **1,950 → 75 → 33**, while head insertion spans barely move
**149 → 135 → 132**. Cell 1, which removes the *delivered* overlap at both ends, cuts the tail to
454 spans and leaves the head at 130 — and actually raises `runaway-head` mass from 70 to 72. A
third of the block is speech the overlap delivers; the rest is continuation the abrupt stop
triggers, and nothing yet tested touches the head.

**The recommended local optimization for the E22 short-form serving surface is
`tail-silence-2s`** — the cheapest admitted variant, 1.28× the comparator's audio tokens against
`pad-30s`'s 4.34×, buying a corpus-WER difference of **−0.0800 [−0.2581, +0.1000]** that sits
entirely inside this runtime's measured same-request null and is a coin-flip per row (82 saves, 75
harms, 1,343 ties, sign test p = 0.632).

**Section 8's closing rule does not fire.** All three cells cleared clause 3; Earnings-22
short-form is not dropped.

Row `SAEA-E22-MF-ENCODING-PROBES-VERDICT-V1` (`model-free-check`), registered before the first
sealed score file was read. **Zero contacts of every kind** — model, tokenizer, embedder,
retriever, network, GPU, audio decode — no media byte opened, the resident serving session neither
started, stopped nor attached, and the offline guard recorded **zero outbound connection
attempts**. Receipts:
`docs/checks/speech-aware-evidence-acquisition/2026-09-07-e22-dev-encoding-probes/verdict/`
(`MANIFEST.sha256`; `summary.json` sha256 `b5a21c8f…`, `per-call-table.csv` `eaab34d9…`,
`README.md` `ff258259…`). Module `analysis/e22_encoding_probes.py` (a thin derivation over the base
`analysis/e22_usage_cells.py`), runner `scripts/e22_encoding_probes_read.py`, tests
`tests/unit/test_e22_encoding_probes.py` and `tests/unit/test_e22_usage_cells.py`. Two back-to-back
writes reproduce the same `MANIFEST.sha256`.

**Population: DEV ONLY.** `E22-DEV-ESB-1500-V1`, split identity
`c626e62f8876bf52a2904a0d2ec91807a530f3195c10facc8c036f661b2bf88a`, 1,500 rows at 150 per call over
all ten dev subset10 calls, 26,251 reference words under the Whisper `EnglishTextNormalizer`. The
pairing key is the **published ESB segment**, recovered from each cell's `@bx1` / `@ts2` / `@p30`
id by splitting on `@` (deviation `D-ENC-1`). **The six calibration-exposed ESB test calls were not
opened** (`test_split_read: false`). The 109 confirmatory calls are not named, loaded or read.

---

## 1. The gates, in the preregistration's own order

### 1.1 The section 4.1 falsifier, before any score

Section 6.2 item 7 puts the `prompt_tokens` falsifier before any score is read, so each cell's
committed flight receipt is re-read and re-hashed first and this verdict refuses to compute
anything unless all three hold on every row.

| cell | rows holding | measured `prompt_tokens` | predicted | verdict |
|---|---:|---:|---:|---|
| 1 `boundary-exact` | 1,500 / 1,500 | 210,663 | 210,663 | HOLDS |
| 2 `tail-silence-2s` | 1,500 / 1,500 | 251,782 | 251,782 | HOLDS |
| 3 `pad-30s` | 1,500 / 1,500 | 678,026 | 678,026 | HOLDS |

The audit's front-end model predicts every row's audio-token count exactly on media re-cut,
extended by 2.0 s and extended to 30.0 s. It is not an approximation.

### 1.2 The identity gate — four raw triples, twelve numbers

| arm | source of the anchor | corpus WER % | agentic % | boundary WER points |
|---|---|---:|---:|---:|
| A, restricted to these 1,500 | 2026-09-06 usage-cells verdict §4.5 | **17.4012** | **1.9161** | **8.2778** |
| cell 1 `SAEA-E22-DEV-ESB-BX-V1` | its own flight row | **14.3537** | **1.8971** | **5.4969** |
| cell 2 `SAEA-E22-DEV-ESB-TAIL2S-V1` | its own flight row | **9.4054** | **1.7599** | **1.1085** |
| cell 3 `SAEA-E22-DEV-ESB-PAD30S-V1` | its own flight row | **9.3254** | **1.7752** | **0.9295** |

All twelve reproduced. Corpus figures come from the sealed per-sample rows of the paper-facing
`asr-wer-esb-whisper` scorer; agentic and boundary figures from `analysis.e22_error_taxonomy` at
its committed version. The three cells' finalize per-sample rows were additionally compared row for
row against their **verified** `core.scoring_batch` results: **1,500 rows per cell, zero
disagreements.** Arm A has no per-sample batch result (it was scored without
`--include-per-sample`), which the receipt records as an *absent* cross-check with its reason
rather than passing over it.

### 1.3 A defect found by reproducing the receipts: the three flights do not share one entity-inventory basis

The per-call entity inventory feeds `classify_span`, so **which reference sentences are offered
changes the agentic rate and, through `runaway-head`, the boundary block.** Reproducing each sealed
receipt shows each one reproduces on exactly one basis, and they are not the same basis:

| arm | its flight's basis | agentic on `dev10` | agentic on `subset1500` | boundary on `dev10` | boundary on `subset1500` |
|---|---|---:|---:|---:|---:|
| A | `dev10` | **1.9161** | 1.8895 | **8.2778** | 8.2892 |
| cell 1 | `dev10` | **1.8971** | 1.8742 | **5.4969** | 5.4969 |
| cell 2 | `subset1500` | 1.7828 | **1.7599** | 1.0971 | **1.1085** |
| cell 3 | `subset1500` | 1.7980 | **1.7752** | 0.9181 | **0.9295** |

**Every contrast in this document is computed on `dev10` for all four arms** — the comparator's own
basis, the one `analysis.e22_usage_cells` has always built, and the richer inventory (the 1,500-row
subset offers about a quarter of each call's sentences). A paired contrast whose arms use different
inventories is not a paired contrast. The discrepancy is small — under 0.03 agentic points and
0.012 boundary points — and changes no decision, but it is recorded rather than smoothed away, and
the identity gate deliberately checks each receipt against the basis *it* used, because that is
what proves this read is over the same sealed tables. **Corpus WER is unaffected**: it comes from
the scorer, not the taxonomy.

**Reporting obligation for every future Earnings-22 cell**: name the inventory basis in the flight
receipt. A raw agentic or boundary number is not self-describing without it.

---

## 2. The decision, clause by clause

Section 4's rule, quoted and applied unmodified:

> **ADMITTED** as a model-usage local optimization **iff all three clauses hold**: (1) the CI90
> upper bound on the corpus-WER delta is **< −0.2356** — below zero *and* disjoint from the
> same-request null's interval [−0.2356, +0.0692]; (2) the agentic error rate's point estimate is
> ≤ arm A's **and** the CI90 upper bound on its delta is below **+0.05 points**; (3)
> `segmentation-artifact` + `runaway-tail` + `runaway-head` falls by **at least 2.0 WER points**
> from arm A's 8.2778.

Signed **cell − arm A**, stratified by source call, 10,000 replicates, seed 20260903, CI90, through
`analysis.paired.resampled_statistic`; the call-clustered interval is beside it and the rule reads
the stratified one, as written.

| | cell 1 `boundary-exact` | cell 2 `tail-silence-2s` | cell 3 `pad-30s` |
|---|---|---|---|
| corpus WER Δ, stratified | **−3.0475** [−3.5344, **−2.5654**] | **−7.9959** [−8.5203, **−7.5007**] | **−8.0759** [−8.6069, **−7.5659**] |
| corpus WER Δ, clustered | −3.0475 [−3.8757, −2.2205] | −7.9959 [−8.7149, −7.3239] | −8.0759 [−8.8804, −7.3327] |
| agentic Δ, stratified | −0.0190 [−0.1026, **+0.0637**] | −0.1333 [−0.2129, **−0.0554**] | −0.1181 [−0.2083, **−0.0269**] |
| agentic Δ, clustered | −0.0190 [−0.1316, +0.0885] | −0.1333 [−0.2044, −0.0661] | −0.1181 [−0.1812, −0.0580] |
| boundary Δ, stratified | **−2.7808** [−3.2253, −2.3505] | **−7.1807** [−7.6649, −6.7379] | **−7.3597** [−7.8431, −6.9204] |
| boundary Δ, clustered | −2.7808 [−3.4937, −2.0728] | −7.1807 [−7.8227, −6.5663] | −7.3597 [−7.9756, −6.7753] |
| clause 1 (< −0.2356) | ✔ | ✔ | ✔ |
| clause 2 (≤ 0 and < +0.05) | ✘ **+0.0637** | ✔ | ✔ |
| clause 3 (≥ 2.0 points) | ✔ | ✔ | ✔ |
| saves / harms / ties | 512 / 265 / 723 | 811 / 97 / 592 | 823 / 103 / 574 |
| exact sign test | p < 1e−6 | p < 1e−6 | p < 1e−6 |
| audio tokens vs arm A | 0.9848× | **1.2800×** | 4.3403× |
| **decision** | **NOT ADMITTED** | **ADMITTED** | **ADMITTED** |

**Cell 1 fails on one clause and nothing else, and the failure is legible.** The re-cut removes up
to 0.180188 s of real audio from **1,403 of 1,500 clips** (mean 0.117899 s), and the five clips it
leaves under 0.15 s are named in §4.6. Its `named-entity` mass **rises** 299 → 301 and its
`domain-term` mass 49 → 58 — the only cell that worsens both — which is exactly what removing real
audio at a clip edge should cost, and it is why the agentic interval cannot clear the
non-inferiority margin even though the corpus-WER and boundary gains are large and signed.

**The two silence cells clear every clause by margins that are not close.** For scale: the largest
single thing this study had previously bought inside its own serving path was the Q8_0 decoder at
−0.4305 corpus-WER points, and the same-request null — this runtime's own cross-run noise — is
−0.0844 [−0.2356, +0.0692]. `tail-silence-2s` is **18.6× the Q8_0 effect and 95× the null's point
estimate**, and its CI90 upper bound of −7.5007 sits 24 whole null-widths below zero.

---

## 3. The mechanism: onset trigger versus pad block

Three cells, three different things done to the media, and read together they separate two
hypotheses the 2026-09-07 audit could not.

### 3.1 What each cell actually did to the encoder's input

| | arm A | cell 1 `bx` | cell 2 `tail2s` | cell 3 `pad30s` |
|---|---:|---:|---:|---:|
| audio seconds | 9,948.983 | 9,783.571 | 12,948.983 | 45,002.880 |
| audio tokens | 139,282 | 137,163 | 178,282 | 604,526 |
| zero-pad mel frames | 75,330 | 75,619 | **75,330** | **148,412** |
| clips carrying a pad block | 1,498 | 1,486 | **1,498** | **1,500** |
| the delivered overlap | present | **removed** | present | present |
| distance from last word to the pad | 0 s | 0 s | **2.0 s** | **up to 30 s** |

### 3.2 What silence alone says

`tail-silence-2s` changes **exactly one thing**: it puts 2.0 s of digital silence between the last
word and the encoder's constant. It adds 200 whole mel frames, so the residue
`(n_samples // 160) % 100` is unchanged, the padded block keeps its size, and the same 1,498 clips
carry one — the preregistration said so in writing before the cell flew, precisely so this reading
could not be overclaimed. The boundary block falls **8.2778 → 1.0971**, and `runaway-tail` mass
falls **1,179 → 22**.

**So the block of constant is not what the model was reacting to. The stop was.**

### 3.3 What 30 seconds of silence says

`pad-30s` **more than doubles** the constant (75,330 → 148,412 padded frames; every clip now
carries a 99-frame block) and pushes it about 30 s away. It lands at 9.3254 against
`tail-silence-2s`'s 9.4054 — a difference of **−0.0800 corpus-WER points, CI90 [−0.2581, +0.1000]**,
which straddles zero and lies inside the same-request null. **Doubling the pad while moving it
further costs nothing and buys nothing measurable.** If the constant were the problem, doubling it
would show; it does not.

The one place `pad-30s` is distinguishable is the boundary block itself: **−0.1790
[−0.2690, −0.0962]** against `tail-silence-2s`, driven by `runaway-tail` mass reaching **0**
(against 22) and tail insertion spans 21 (against 39). That is a real but tiny residue: 0.18 WER
points, for 3.39× the audio tokens and 3.48× the audio seconds.

### 3.4 What the re-cut alone says

`boundary-exact` removes the *delivered* trigger — the onset of the next published sentence that
the ESB release's own overlap puts inside the clip — and leaves the acoustic discontinuity where it
was. It takes the boundary block from 8.2778 to 5.4969: **33.6 % of it**. Against
`tail-silence-2s` it is **+4.9484 corpus-WER points and +4.3998 boundary points worse**, at 0.77×
the audio tokens.

**The split is therefore roughly one third delivered, two thirds triggered.** The 2026-09-06
boundary-exact preregistration's honest prior said most of the block would be continuation the
overlap *triggers* rather than speech it *delivers* — 668.7 s of duplicated audio at 2.632
reference words per second is at most ≈ 1,760 words against 7,318 tail insertion words. The
measurement agrees with that prior and puts a number on it.

### 3.5 The head is a different problem, and none of these cells solves it

| arm | `segmentation-artifact` | `runaway-tail` | `runaway-head` | total ops | WER points | share of arm's WER |
|---|---:|---:|---:|---:|---:|---:|
| A | 924 | 1,179 | 70 | 2,173 | **8.2778** | 47.6 % |
| cell 1 `bx` | 583 | 788 | **72** | 1,443 | 5.4969 | 38.3 % |
| cell 2 `tail2s` | 228 | 22 | 38 | 288 | 1.0971 | 11.7 % |
| cell 3 `pad30s` | 204 | **0** | 37 | 241 | 0.9181 | 9.8 % |

Containment against the neighbouring published utterance's own reference:

| arm | head spans | head words | head at ≥0.6 containment | tail spans | tail words | tail at ≥0.6 |
|---|---:|---:|---:|---:|---:|---:|
| A | 149 | 266 | 73 | 704 | 1,950 | 218 |
| cell 1 `bx` | 130 | 233 | 62 | 454 | 1,234 | 89 |
| cell 2 `tail2s` | 135 | 227 | 68 | 39 | 75 | 20 |
| cell 3 `pad30s` | 132 | 220 | 63 | 21 | 33 | 11 |

**The asymmetry is the finding.** Tail insertion words fall by 96 % under either silence cell; head
insertion words fall by 15 % and 17 %, and head spans hardly move at all. Cell 1, the only cell that
removes the previous utterance's delivered overlap at the head, does **not** reduce `runaway-head`
mass (70 → 72). Whatever makes the model emit words before the reference's first word is neither
the delivered overlap nor the acoustic tail, and this study has not measured it. It is now
**38 operations, 0.1448 WER points of `runaway-head`** on the admitted arm — small enough that it
should be named and left alone rather than chased.

---

## 4. Mandatory reporting (preregistration §4.2)

### 4.1 Per call, all ten, both normalizers

Whisper `EnglishTextNormalizer`, the paper-facing scorer:

| call | rows | ref words | A | 1 `bx` | Δ1 | 2 `ts2` | Δ2 | 3 `p30` | Δ3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `4453225` | 150 | 2,662 | 20.9992 | 16.2284 | −4.7708 | 10.7438 | −10.2554 | 10.1803 | **−10.8189** |
| `4469088` | 150 | 1,946 | 18.5509 | 15.4162 | −3.1347 | 9.6095 | −8.9414 | 10.1233 | −8.4276 |
| `4470684` | 150 | 2,581 | 13.6769 | 11.2360 | −2.4409 | 5.7342 | −7.9427 | 5.1918 | −8.4851 |
| `4474506` | 150 | 2,993 | 13.9659 | 12.2954 | −1.6705 | 7.5175 | −6.4484 | 7.5510 | −6.4149 |
| `4479944` | 150 | 2,773 | 23.8370 | 21.3127 | −2.5243 | 16.3000 | −7.5370 | 16.3361 | −7.5009 |
| `4481952` | 150 | 2,166 | 16.7590 | 13.5734 | −3.1856 | 8.6334 | −8.1256 | 8.2641 | −8.4949 |
| `4482383` | 150 | 3,015 | 14.7927 | 9.1874 | −5.6053 | 8.1260 | −6.6667 | 7.8939 | −6.8988 |
| `4482613` | 150 | 2,386 | 22.6739 | 22.5063 | **−0.1676** | 16.6387 | −6.0352 | 17.0997 | −5.5742 |
| `4483937` | 150 | 2,567 | 16.7900 | 14.8422 | −1.9478 | 7.0900 | −9.7000 | 6.8952 | −9.8948 |
| `4485192` | 150 | 3,162 | 13.7571 | 9.4244 | −4.3327 | 5.0601 | −8.6970 | 5.2182 | −8.5389 |

**All ten calls improve under all three cells** — the first time in this campaign that a cell has
had no losing stratum. Under the frozen `saea-scoring-v1` normalizer the ordering is the same
(corpus 22.6419 → 19.6853 → 14.7640 → 14.6261), so no part of this verdict is a normalizer artefact.
`4482613`, the population's hardest call and the one that resisted both 2026-09-06 cells, is the
weakest here too (cell 1 buys 0.1676 points on it) but still improves by 6.04 under
`tail-silence-2s`.

### 4.2 Weightings, side by side

| arm | natural mixture WER | equal-call WER | natural agentic | equal-call agentic |
|---|---:|---:|---:|---:|
| A | 17.4012 | 17.5803 | 1.9161 | 1.9783 |
| 1 `boundary-exact` | 14.3537 | 14.6022 | 1.8971 | 1.9669 |
| 2 `tail-silence-2s` | **9.4054** | **9.5453** | 1.7828 | 1.8426 |
| 3 `pad-30s` | **9.3254** | **9.4754** | 1.7980 | 1.8570 |

The verdict does not turn on the weighting: `tail-silence-2s` is −7.9959 natural and −8.0350
equal-call.

### 4.3 Error shape and length ratio

| arm | S | D | I | ref words | hyp words | hyp/ref | I share of errors | mean per-utterance WER | `saea-scoring-v1` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 1,140 | 592 | 2,836 | 26,251 | 28,495 | 1.0855 | 62.08 % | 31.3566 | 22.6419 |
| 1 `bx` | 1,141 | 633 | 1,994 | 26,251 | 27,612 | 1.0518 | 52.92 % | 25.1707 | 19.6853 |
| 2 `ts2` | 1,041 | 763 | 665 | 26,251 | 26,153 | **0.9963** | 26.93 % | 15.4208 | 14.7640 |
| 3 `p30` | 1,044 | 799 | 605 | 26,251 | 26,057 | **0.9926** | 24.71 % | 15.3907 | 14.6261 |

**This is a change of shape, not a trim, and it is the first one this campaign has produced.** Arm
A over-generates by 8.6 % and insertions are 62 % of all its errors; under `tail-silence-2s` the
hypothesis is 0.4 % *shorter* than the reference and insertions are 27 % of errors. The trade is
explicit: **2,171 insertions removed for 171 deletions added**, with substitutions falling 99. Both
silence cells stop the model from talking past the clip and make it stop slightly early instead —
and on this corpus that is worth 8 WER points.

### 4.4 Utterance-duration decomposition

Corpus WER by duration bucket:

| bucket | rows | ref words | A | 1 `bx` | Δ1 | 2 `ts2` | Δ2 | 3 `p30` | Δ3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| [0, 1) s | 116 | 277 | 74.0072 | 70.7581 | −3.2491 | 48.7365 | **−25.2707** | 49.0975 | −24.9097 |
| [1, 2) s | 109 | 537 | 42.0857 | 34.4507 | −7.6350 | 23.4637 | **−18.6220** | 26.0708 | −16.0149 |
| [2, 4) s | 291 | 2,656 | 27.2214 | 23.0045 | −4.2169 | 14.3072 | −12.9142 | 14.8343 | −12.3871 |
| [4, 8) s | 488 | 7,657 | 20.2168 | 15.4238 | −4.7930 | 9.4815 | −10.7353 | 9.1942 | −11.0226 |
| [8, 16) s | 425 | 11,695 | 13.1595 | 11.0902 | −2.0693 | 7.5673 | −5.5922 | 7.2424 | −5.9171 |
| [16, ∞) s | 71 | 3,429 | 9.5363 | 8.6906 | −0.8457 | 6.3284 | −3.2079 | 6.6200 | −2.9163 |

The boundary block by the same buckets:

| bucket | A | 1 `bx` | 2 `ts2` | 3 `p30` |
|---|---:|---:|---:|---:|
| [0, 1) s | 30.6859 | 22.7437 | 3.2491 | 2.8881 |
| [1, 2) s | 20.1117 | 12.8492 | 3.3520 | 2.7933 |
| [2, 4) s | 12.8012 | 8.5843 | 2.3720 | 2.2967 |
| [4, 8) s | 10.9442 | 6.8304 | 1.3321 | 1.1885 |
| [8, 16) s | 5.8829 | 4.1300 | 0.6841 | 0.4617 |
| [16, ∞) s | 3.3246 | 2.2456 | 0.4666 | 0.3500 |

**This is the slice that could have falsified the mechanism and did not.** The audit predicted the
padding artefact concentrates on short clips (42.2 % of tokens on sub-second clips against 2.5 % at
16 s and above), and the gain is ordered the same way — but it is present in **every** bucket,
including the 71 rows at 16 s and above where padding is 2.5 % of the tokens and the effect is still
−3.21 points and the boundary block still falls from 3.32 to 0.47. A pure token-accounting artefact
would have vanished at the long end. A discontinuity at the last word does not, because every clip
has exactly one last word whatever its length. The duration ordering is the *denominator* shrinking,
not the mechanism changing.

### 4.5 Category mass, before and after, all three cells

Error operations (Whisper-normalized alignment, `analysis.e22_error_taxonomy` at its committed
version, `dev10` inventory basis):

| category | A | 1 `bx` | 2 `ts2` | 3 `p30` | Δ2 (ops) |
|---|---:|---:|---:|---:|---:|
| `model-behaviour` | 1,390 | 1,015 | 213 | 206 | **−1,177** |
| `segmentation-artifact` | 924 | 583 | 228 | 204 | **−696** |
| `other` | 1,234 | 1,144 | 990 | 1,017 | −244 |
| `named-entity` | 299 | **301** | 289 | 286 | −10 |
| `acoustic-misrecognition` | 343 | 334 | 334 | 327 | −9 |
| `reference-convention` | 233 | 230 | **241** | 238 | +8 |
| `format-convention` | 96 | 103 | **120** | 113 | +24 |
| `domain-term` | 49 | **58** | **54** | **57** | +5 |
| **total** | **4,568** | **3,768** | **2,469** | **2,448** | −2,099 |

**The signature is coherent with a boundary mechanism and with nothing else**: 1,873 of the 2,099
operations `tail-silence-2s` removes are `model-behaviour` and `segmentation-artifact`, and the
categories that go *up* are the three that are impact-neutral or near it (format-convention,
reference-convention, domain-term, +37 between them). No cell buys anything on
`acoustic-misrecognition`, which is the right null: appending silence cannot make a word easier to
hear.

### 4.6 Cell 1's re-cut clips, named

Section 4.2 requires them by name. **1,403 of 1,500 clips lose audio**, at a mean of 0.117899 s and
a maximum of 0.180188 s, and five fall under 0.15 s:

| sample id | re-cut seconds | source seconds |
|---|---:|---:|
| `4469088-522@bx1` | 0.120000 | 0.220250 |
| `4479944-293@bx1` | 0.120063 | 0.260000 |
| `4469088-654@bx1` | 0.139875 | 0.219938 |
| `4481952-268@bx1` | 0.139938 | 0.219938 |
| `4481952-330@bx1` | 0.140000 | 0.260250 |

---

## 5. The recommendation: `tail-silence-2s`, and why not `pad-30s`

**Adopt `tail-silence-2s` as the Earnings-22 short-form serving default on this path**: append
exactly 2.0 s (32,000 zero samples at 16 kHz) to the clip bytes before they are base64-encoded into
the `input_audio` part. It is a wire-level change with no model, decoder, prompt, scorer or
normalizer consequence.

**Why not `pad-30s`, stated as a trade rather than as a preference.**

| | `tail-silence-2s` | `pad-30s` | the difference |
|---|---:|---:|---|
| corpus WER | 9.4054 | 9.3254 | **−0.0800 [−0.2581, +0.1000]** |
| boundary block | 1.0971 | 0.9181 | −0.1790 [−0.2690, −0.0962] |
| per-row saves / harms / ties | — | — | 82 / 75 / 1,343, sign test **p = 0.632** |
| audio seconds | 12,948.983 | 45,002.880 | **3.48×** |
| audio tokens | 178,282 | 604,526 | **3.39×** |
| bytes on disk | 414 MB | 1,440 MB | 3.47× |

The corpus-WER difference **is inside the measured same-request null** [−0.2356, +0.0692] and its
interval straddles zero; per row it is a coin flip. The boundary difference is real and signed but
is **0.18 WER points**, 1.9 % of what the cell already bought. Paying 3.4× the encode for that is
not a trade this study should take, and the cost is not theoretical: at the measured 1.149e-5 GPU-h
per audio second, 1,500 rows cost 0.149 GPU-h under `tail-silence-2s` and 0.517 under `pad-30s`.

**Two honest caveats on the recommendation.**

1. **This is not a repair of the encoder; it is a workaround at the wire.** The published path masks
   the padded block; we move it. A clip we send under `tail-silence-2s` differs from the published
   path's input by 2.0 s of appended silence. Any alignment number produced this way must be
   labelled *"Qwen3-Omni Q4_K_M GGUF via llama.cpp with a 2-second silence tail"*, never as the
   published protocol. It is, however, a **smaller** protocol deviation than cell 1's re-cut, which
   changes the released clip's own content.
2. **Section 8 requires a replication on the same roster before any further mechanism is admitted**
   (the owner's 2026-09-03 iteration rule, and §3.2 of the 2026-09-06 verdict). The effect's CI90
   upper bound is 24 whole null-widths below zero and the sign test is p < 1e−6, so the sizing
   question the rule exists to
   answer is not in doubt — but the rule is not waived here, and whether the replication is run
   standalone or folded into the test re-read is the owner's call.

---

## 6. The alignment projection for the six test calls — a projection, not a number

The Earnings-22 short-form line is **15.937** corpus WER on the six ESB test calls, read **once** on
2026-09-04, against the same frozen model's published **9.79** (NVIDIA NeMo AutoModel, Whisper
`EnglishTextNormalizer`, greedy) and the cross-read **12.3** (Nemotron 3 Nano Omni Table 8), with
`whisper-large-v3` at 11.59 and `base.en` at 15.09.

On dev, `tail-silence-2s` takes 17.4012 to **9.4054**, which is already **below the published
9.79** on this study's own dev subset.

**The transfer assumption, stated so it can be wrong.** The effect is a property of the *serving
path's encoding*, not of the population: every clip in every ESB population is cut at a published
sentence boundary and delivered to the same `mtmd_audio_preprocessor_qwen3a`, so the same
discontinuity is present on the test calls. If that holds, the test number moves by a comparable
amount.

| projection | arithmetic | landing |
|---|---|---:|
| additive | 15.937 − 7.996 | **7.94** |
| proportional | 15.937 × (9.4054 / 17.4012) | **8.61** |

**The band is therefore roughly 7.9 to 8.6, and it is a band around an unmeasured quantity.** Four
reasons it may be wrong, all of them stated before any test byte is opened:

* the test population is a different mixture — 2,735 utterances over six calls, whose arm A reads
  15.937 against this dev subset's 17.4012, so the dev subset is the harder population and the
  headroom may be smaller;
* the gain is largest on short clips (−25.27 points on the 116 sub-second dev rows) and the test
  calls' duration mixture is not read here;
* the Q8_0 decoder admitted on 2026-09-06 (−0.4305) is a **separate, uncomposed** factor, and the
  two effects were never shown to compose;
* there is **no confidence interval** on either projection, because no test row was flown.

**Floors.** The owner's 2026-09-04 goal sets a hard floor at a degraded model's published number.
Both projections land below `whisper-large-v3`'s 11.59, below `base.en`'s 15.09 and below the
published 9.79 — which is precisely the regime in which a projection must not be reported as a
result. **This document claims no test number.**

**The test number requires the owner-authorised one-time re-read now being prepared,
`SAEA-E22-ESB-SHORTFORM-TAIL2S-TEST-V1`.** None of these cells is a scorer-side change — they
change the audio — so the six calibration-exposed test calls must be **re-flown**, a second read of
a population the 2026-09-04 owner allowance permitted once. Section 7.2 forbids taking it on the
preregistration's authority and this verdict's exposure row forbids taking it on its own; it may
only be **proposed**, and it is proposed here.

---

## 7. Cross-carrier implication — a proposal, not a claim

**Nothing below is measured. Each is a hypothesis with an owner GO and a single-factor cell
between it and a number.**

The same `mtmd_audio_preprocessor_qwen3a` front end serves every audio this study sends through
llama.cpp, and the mechanism this verdict identifies is not Earnings-specific: **a signal that stops
abruptly at the end of speech invites the model to continue speaking.** Three surfaces are exposed
to it:

* **SLURP.** Recordings are short spoken commands, typically 2–4 s — the bucket where this verdict
  measured −12.9 corpus-WER points on Earnings and where padding is 13–25 % of the audio tokens. The
  failure mode would not be a WER runaway but a *slot* runaway: extra tokens after the command's
  last word landing in a slot value. The EVO-S1 loop's strict slot-F1 reward would see it as noise.
* **Audio2Tool.** Tier-1 clips are short and the task is a single tool call; a continuation past the
  clip end is exactly the shape of a spurious second call, and the official protocol's first-call
  regex parse would silently absorb some of it.
* **Earnings-21 window ends.** The 90-second obs windows are cut at fixed offsets, so the
  discontinuity there is *mid-word*, not merely mid-utterance — a stronger version of the same
  stimulus, present at all 1,593 window ends.

**The cheapest way to test the proposal on any of them is the same one that worked here**: one
single-factor cell, media rebuilt from sealed bytes with a fixed silence tail, paired against that
carrier's own sealed arm on its own roster, under that carrier's official scorer. On SLURP and
Audio2Tool that is a cheap flight; on Earnings-21 it is not, because the windows are 90 s each.

**What this verdict does *not* license**: applying the tail to any carrier's sealed arm and
comparing against a number produced without it, changing any carrier's serving default on this
document's authority, or reading it as evidence about any carrier other than Earnings-22 dev.

---

## 8. The `frame-exact` probe — the remaining engineering option, reframed by the result

Section 5 named a `frame-exact` variant — pad each clip with digital silence until
`n_samples // 160 + 1` is a multiple of 100, at most 0.99 s per clip — as "the only cheap
intervention that eliminates the constant rather than moving it", and deliberately queued it behind
cell 2 because "cell 2's result determines whether it is worth a GPU at all".

**Cell 2 and cell 3 have now answered that question, and the answer changes what `frame-exact`
is for.** It was framed as the probe that would separate *the encoder sees a discontinuity* from
*the encoder spends 13 tokens on nothing*. Cell 3 already separated them: it **doubled** the padded
frames and still won. The constant is not the mechanism, so removing it is not where the remaining
mass is, and `frame-exact` is no longer a mechanism probe.

**As a cost optimization it is real but weaker than it looks, and the weakness is predictable from
this verdict's own mechanism.** `frame-exact` appends a *variable* 0 to 0.99 s of silence — whatever
that clip needs to reach a block boundary — so the tail relief it delivers is variable and, for a
clip already sitting on a multiple of 100 frames, **zero**. `tail-silence-2s` delivers a guaranteed
2.0 s to every row. On the reading above, `frame-exact` should therefore be **worse than
`tail-silence-2s` on exactly the rows that need the relief most**, while saving roughly 39,000 audio
tokens per 1,500 rows (about 22 % of `tail-silence-2s`'s encode).

**It remains available and unbuilt, and it still needs its own owner decision.** If the owner wants
a cheaper admitted variant, the question the evidence now poses is not "remove the constant" but
"**how short can the guaranteed tail be**" — and answering that is a new cell with a new
preregistration, not this one. This document names it and does not propose it.

---

## 9. What is on the record after this verdict

* **The Earnings-22 boundary block is not a mystery any more.** 8.2778 of arm A's 17.4012 corpus-WER
  points, 47.6 % of its error, is now decomposed: roughly a third is speech the published overlap
  *delivers* (cell 1: −2.7808) and the rest is continuation the abrupt clip end *triggers* (cell 2:
  −7.1807). Six explanations before this measured at most 0.83 points, and all of them the wrong way
  or inside the noise.
* **`tail-silence-2s` is ADMITTED on dev** at −7.9959 corpus-WER points [−8.5203, −7.5007], with the
  agentic rate improving (−0.1333 [−0.2129, −0.0554]) and the boundary block down 86.7 %.
* **`pad-30s` is ADMITTED and is not worth its cost**: −0.0800 [−0.2581, +0.1000] against
  `tail-silence-2s`, inside the same-request null, for 3.39× the audio tokens.
* **`boundary-exact` is NOT ADMITTED**, on clause 2 alone, and the reason is legible: it removes real
  audio from 1,403 of 1,500 clips and is the only cell that worsens both `named-entity` and
  `domain-term` mass.
* **A reporting defect is fixed going forward**: a flight's raw agentic and boundary numbers are not
  self-describing without their entity-inventory basis, and every future Earnings-22 receipt must
  name it.
* **The head runaway is unexplained** and is now the largest untouched named component of the
  boundary block on the admitted arm, at roughly 0.145 WER points. It is small enough to name and
  leave alone.
* **No test number is claimed.** The alignment line stays **NOT ALIGNED at 15.937** until the
  owner-authorised one-time re-read `SAEA-E22-ESB-SHORTFORM-TAIL2S-TEST-V1` is run.
