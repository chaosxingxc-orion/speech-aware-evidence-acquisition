# Verdict — the Earnings-22 short-form TEST re-read with the tail-silence media

Run `SAEA-E22-ESB-SHORTFORM-TAIL2S-TEST-V1`, attempt `attempt-20260907T110507Z-cafdc7`, COMPLETED and
FINALIZED on study commit `532cbb43`, **2,735 of 2,735 contacts**, one attempt, none aborted, **no
recovery re-registration used**, `study_repo_dirt` empty. The cell of
`docs/readiness/2026-09-07-e22-esb-shortform-tail2s-test-v1-preregistration.md`, flown on the owner
GO of 2026-09-07 recorded in its own exposure row before the first contact. This is §8.2 item 10 of
that file, and it is the second read of the six ESB test calls — the whole price of the cell, paid.

---

## 0. The answer, with the label it always carries

**Corpus Whisper-normalized WER `W` = 9.2377 %, under the silence-tail convention**, against the
sealed arm's **15.9365** on the same 2,735 published segments.

| | value |
|---|---:|
| **corpus WER, Whisper `EnglishTextNormalizer` (paper-facing)** | **9.2377 %** |
| sealed comparator `SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1`, same rows | 15.9365 % |
| paired pooled delta, cell − sealed, CI90 stratified by call | **−6.6988** [−7.0373, −6.3753] |
| published NeMo AutoModel row | 9.79 |
| cross-read (Open ASR Leaderboard, same frozen model) | 12.3 |
| **band test `W <= 12.79`** | **PASS** |
| **strict floor `W <= 11.59`** (whisper-large-v3) | **PASS** |
| loose floor `W <= 15.09` (whisper-base.en) | PASS |
| ALIGNED-BETTER (`W < 6.79`) | no |
| **verdict** | **ALIGNED** |

**The label is not decoration and is not detachable.** `D-TS2-3`: the published systems did not
append silence. Every request in this cell carried 2.0 s of digital silence after the published span.
This number is **not a like-for-like reproduction of the published protocol** and must never be
reported as one. §7 below quotes the only sentence it licenses.

**The band is the secondary statement.** The owner GO of 2026-09-07 admitted the alignment band on
this media-changing cell only with the deviation named; the **paired contrast against the sealed
15.937 rows is the primary statement**, and §3 is where it lives.

---

## 1. The falsifier, run before any score was read

**§4.2 HOLDS ON 2,735 OF 2,735 ROWS.** Measured `prompt_tokens` total **476,578** against the
predicted **476,578** — exactly the `49 × 2,735 + 342,563` the preregistration published before the
cell existed — with **zero** disagreeing rows. The predicted audio-token count was recomputed from
each clip's own `n_samples` through `analysis.e22_short_clip_encoding.llamacpp_audio_tokens` rather
than read from the roster receipt's column, and the roster column agrees on every one of the 2,735
rows as well. The sealed `cost` block's own `prompt_tokens_total` is the same 476,578. The audit's
front-end model is the server's on this media too.

The four-row smoke had already returned 88 / 166 / 270 / 556 against its own predicted 88 / 166 /
270 / 556, total 1,080 against 1,080.

Receipts: `docs/checks/speech-aware-evidence-acquisition/2026-09-07-e22-esb-shortform-tail2s-test-v1/`
`flight-2735/falsifier.json` and `smoke-4/falsifier.json`.

---

## 2. The decision rule, quoted verbatim from §4 before it is applied

> Let `W` be the corpus WER of `asr-wer-esb-whisper` over the 2,735 rows — total S+D+I over total
> reference words, Whisper `EnglishTextNormalizer` on both sides, whitespace tokenization. **This is
> the 2026-09-04 alignment rule, unchanged, applied to the same population under the media of §1.1:**
>
> * **band test**: `W <= 12.79` (9.79 + 3.0).
> * **floor test (strict)**: `W <= 11.59`, whisper-large-v3 on the same column.
> * **floor test (loose)**: `W <= 15.09`, whisper-base.en, reported either way, as are the other seven
>   floors.
> * **ALIGNED** = band test and strict floor test both pass.
> * **ALIGNED-BETTER** = `W < 6.79`.
> * **NOT ALIGNED** otherwise, with the failing half named and the gap decomposed call by call and
>   against D1–D5 and `D-TS2-3`.

`W` = 9.2377. Band test passes with 3.55 points to spare; the strict floor passes with 2.35. The
verdict is **ALIGNED**, and no gap decomposition against D1–D5 is owed, because neither half of the
rule failed. `W` is **0.5523 points below the published 9.79** and **3.0623 below the cross-read
12.3**.

**All nine degraded-model floors are cleared**, including the tightest, `qwen3-asr-1.7b` at 9.73:

| floor | published | cleared |
|---|---:|---|
| qwen3-asr-1.7b | 9.73 | yes |
| qwen3-asr-0.6b | 10.78 | yes |
| distil-large-v3.5 | 10.83 | yes |
| whisper-large-v3-turbo | 11.07 | yes |
| whisper-large-v3 | 11.59 | yes |
| whisper-medium.en | 12.63 | yes |
| whisper-small.en | 12.97 | yes |
| whisper-base.en | 15.09 | yes |
| whisper-tiny.en | 19.12 | yes |

The first five are the 2026-09-04 leaderboard revision; the last four are the 2026-06-13 vintage.
**None of these systems appended silence either.** Two vendor reports of this same frozen model
differ by 2.5 points (9.79 against 12.3), which is most of the owner's 3-point tolerance;
*consistent with both* stays the strongest honest reading of any number inside the band.

---

## 3. The primary statement: the paired contrast against the sealed arm

Same 2,735 published segments, paired per segment on the key recovered by splitting the `@ts2`
suffix, signed as **cell − sealed arm**, so a negative delta is an improvement. 10,000 replicates,
stratified by source call, seed 20260903, CI90.

| statistic | point | CI90 (stratified) | CI90 (clustered by call) |
|---|---:|---|---|
| corpus WER, points | **−6.6988** | [−7.0373, −6.3753] | [−7.4623, −5.8858] |
| agentic error rate, points | **−0.1697** | [−0.2374, −0.1044] | [−0.2712, −0.0623] |
| boundary block, WER points | **−6.0549** | [−6.3699, −5.7491] | [−6.8962, −5.2536] |

All three intervals exclude zero on both draws.

**Per utterance**: 2,735 rows, **1,385 improved, 155 worsened, 1,195 tied**, exact sign test
p ≈ 4.65e-247. Mean per-utterance WER 28.1291 → 13.9396, a mean delta of −14.1895 points, CI90
[−15.4418, −12.9668]. Every one of the six calls moves the same way:

| call | n | sealed mean per-utt WER | cell mean per-utt WER | improved | worsened | tied |
|---|---:|---:|---:|---:|---:|---:|
| 4432298 | 351 | 30.181 | 20.285 | 156 | 22 | 173 |
| 4450488 | 508 | 19.541 | 9.135 | 271 | 20 | 217 |
| 4470290 | 178 | 23.595 | 15.306 | 82 | 16 | 80 |
| 4479741 | 473 | 30.127 | 13.041 | 232 | 28 | 213 |
| 4483338 | 619 | 28.848 | 13.644 | 319 | 35 | 265 |
| 4485244 | 606 | 33.178 | 14.893 | 325 | 34 | 247 |

**Identity gate.** No contrast was computed until the sealed arm reproduced its own 2026-09-04
numbers from its sealed score file: corpus 15.9365 Whisper and 20.896 `saea-scoring-v1`, S/D/I
2,236 / 948 / 4,612 over 48,919 reference words on 2,735 utterances. All seven anchors reproduced to
the digit.

---

## 4. The mandatory slices of §4.3

### 4.1 Per call, both normalizers, natural mixture

| call | ref words | sealed Whisper | **cell Whisper** | delta | sealed `saea-v1` | cell `saea-v1` |
|---|---:|---:|---:|---:|---:|---:|
| 4432298 | 5,948 | 22.1587 | **16.4257** | −5.7330 | 25.9835 | 20.4628 |
| 4450488 | 8,694 | 14.1132 | **7.8445** | −6.2687 | 20.3830 | 14.8723 |
| 4470290 | 3,566 | 19.5457 | **14.5541** | −4.9916 | 24.6393 | 19.5616 |
| 4479741 | 8,436 | 14.5330 | **8.6415** | −5.8915 | 19.6114 | 13.5314 |
| 4483338 | 11,516 | 15.1094 | **8.1191** | −6.9903 | 20.2115 | 12.8525 |
| 4485244 | 10,759 | 14.7597 | **6.2924** | −8.4673 | 19.0270 | 10.8106 |
| **all six** | **48,919** | **15.9365** | **9.2377** | **−6.6988** | **20.8960** | **14.3053** |

**There are no published per-call numbers to set beside these.** The 9.79 NeMo AutoModel row and the
12.3 leaderboard row are single corpus figures; neither source publishes a per-call breakdown, so the
comparison column that would sit here does not exist and is not invented. The sealed-arm column is
the alignment verdict's own per-call table, reproduced to the digit.

### 4.2 Natural mixture beside equal-call weighting

| | natural mixture (corpus) | equal call |
|---|---:|---:|
| sealed arm | 15.9365 | 16.7033 |
| **cell** | **9.2377** | **10.3129** |

The equal-call figure is 1.08 points higher than the corpus figure, because the two calls the cell
helps least (4432298 at 16.43, 4470290 at 14.55) are the two smallest. Under the equal-call weighting
the cell would still pass the band and the strict floor.

### 4.3 S / D / I, the insertion share and the length ratio — and what actually moved

| | sealed arm | **cell** | change |
|---|---:|---:|---:|
| substitutions | 2,236 | **2,019** | −217 |
| deletions | 948 | **1,252** | +304 |
| insertions | 4,612 | **1,248** | **−3,364** |
| errors | 7,796 | 4,519 | −3,277 |
| reference words | 48,919 | 48,919 | 0 |
| insertion share of errors | 59.16 % | **27.62 %** | −31.54 pp |
| hypothesis-to-reference length ratio | 1.0749 | **0.9999** | −0.0750 |
| mean per-utterance WER | 28.1291 | 13.9396 | −14.1895 |

**The predicted direction holds on every clause**: corpus WER falls, the insertion share falls, the
length ratio falls to essentially one.

**The §5 caution clause is falsified as it was written, and this is the most important correction in
this document.** The preregistration reasoned: *"both point predictions sit below that arm's own
length-oracle bound of 10.456 … Any result under 10.456 therefore requires the tail to have fixed
substitutions as well as over-generation, not just to have shortened the output, and the verdict must
check the S/D/I split for that rather than assume it."* The split says otherwise. Substitutions fell
by only 217 while deletions rose by 304, so the **substitution-plus-deletion block is 87 operations
WORSE** (3,184 → 3,271) and the entire 3,277-operation gain is the insertion collapse. The result is
nevertheless 1.22 points below the oracle bound.

The inference in §5 was wrong, not the measurement. The length oracle cut each hypothesis to its own
reference **word count** — a blind truncation that discards whichever words sit past the cut, right
or wrong — so it bounds *that* repair family, not any repair. The tail removes the over-generation at
its source instead, so the words that survive are the ones that were correct to begin with. **A
result under 10.456 does not require substitutions to have been fixed; it means the oracle was a
loose bound on a blind repair.** The verdict says so here rather than quietly enjoying the number.

### 4.4 The utterance-duration decomposition on the PUBLISHED span

The buckets are the published segment's own duration, not the variant's, so the rows are the same
rows in both arms. This is the slice the encoding audit predicts the effect concentrates in, and
therefore the one that can falsify the mechanism even when the pooled number moves.

| bucket | utterances | ref words | sealed | **cell** | delta |
|---|---:|---:|---:|---:|---:|
| 0–1 s | 209 | 556 | 51.2590 | **29.8561** | **−21.4029** |
| 1–2 s | 220 | 1,175 | 31.6596 | **20.2553** | **−11.4043** |
| 2–4 s | 454 | 4,005 | 26.1423 | **12.0350** | **−14.1073** |
| 4–8 s | 856 | 13,171 | 17.4550 | **9.1109** | −8.3441 |
| 8–16 s | 820 | 22,081 | 13.1018 | **8.1609** | −4.9409 |
| 16 s+ | 176 | 7,931 | 11.3479 | **7.9561** | −3.3918 |
| **> 20 s, reported separately** | **74** | — | 11.6535 | **8.5564** | −3.0971 |

The bucket counts are exactly the 209 / 220 / 454 / 856 / 820 / 176 the preregistration published,
and the 74 utterances over 20 s are the 74 it named. **The effect is largest exactly where the audit
priced the artifact largest**: 21.4 points on the sub-second bucket against 3.4 on the 16 s+ one, and
it shrinks with duration across every bucket pair but one — the 1–2 s bucket moves 11.4 points
against the 2–4 s bucket's 14.1, so the trend is unambiguous but not strictly monotone, and that
single inversion is reported rather than smoothed over. The mechanism prediction is confirmed on the
one slice that could have falsified it.

### 4.5 The boundary block and its containment buckets

The taxonomy's own alignment reproduces the paper-facing scorer exactly on **both** arms — 2,236 /
948 / 4,612 over 48,919 for the sealed arm and 2,019 / 1,252 / 1,248 over 48,919 for the cell, corpus
WER 15.9365 and 9.2377 either way — so the split below is a **decomposition** of those numbers, not a
second measurement of them.

| | sealed arm | **cell** | change |
|---|---:|---:|---:|
| `segmentation-artifact` mass | 1,732 | **472** | −1,260 |
| `model-behaviour/runaway-tail` mass | 1,706 | **22** | **−1,684** |
| `model-behaviour/runaway-head` mass | 58 | **40** | −18 |
| **boundary block, total error mass** | **3,496** | **534** | −2,962 |
| **boundary block, WER points** | **7.1465** | **1.0916** | **−6.0549** |

The dev cell's admission clause asked for a fall of at least 2.0 WER points; the fall is 6.05.

**Containment**, the diagnostic that says whether the over-generation is the neighbouring utterance's
own words:

| | sealed arm | **cell** |
|---|---|---|
| tail insertion spans / words | 1,186 / 3,068 | **51 / 91** |
| of which ≥ 0.6 contained in the NEXT reference | 450 spans, 773 words | 36 spans, 50 words |
| head insertion spans / words | 315 / 491 | **293 / 430** |
| of which ≥ 0.6 contained in the PREVIOUS reference | 190 spans, 263 words | 181 spans, 255 words |

**This is the mechanism, in one row.** The tail block collapsed by 97 % (3,068 inserted words → 91)
while the head block barely moved (491 → 430, −12 %). The tail is exactly where the encoder's
unmasked constant abutted the last word, and the head is not. A change that moved both blocks would
have been a general decoding effect; a change that moved only the tail is the one the audit
predicted.

### 4.6 The agentic error rate

`analysis.e22_error_taxonomy` at its committed version, HIGH-impact reference-word mass over
reference words, recomputed on both arms' sealed outputs:

| | sealed arm | **cell** |
|---|---:|---:|
| HIGH-impact spans | 626 | 548 |
| HIGH-impact reference-word mass | 863 | 780 |
| **agentic error rate** | **1.7641 %** | **1.5945 %** |
| equal-call weighting | 1.7422 % | 1.5960 % |

**These two sealed-arm figures did not exist before this read.** The 2026-09-04 verdict never ran the
taxonomy on the test population, so 1.7641 and 7.1465 were computed here, from that arm's own sealed
outputs and the same hash-pinned reference layer, and they are labelled as this read's derivation
rather than quoted as a prior receipt's.

The agentic rate falls by 0.1697 points with a CI90 that excludes zero — **but it falls far less than
the corpus number does** (−9.6 % relative against −42.0 % relative). That is the expected shape: the
artifact this cell repairs produced boundary over-generation, which the taxonomy classifies as
`segmentation-artifact` and `model-behaviour`, both largely impact-neutral. Named-entity mass moved
from 0.9710 to 0.9117 WER points and `acoustic-misrecognition` from 1.4596 to 1.4146 — **the parts of
the error mass that are about hearing the words barely moved at all.** What this cell fixed was
output discipline, exactly as the sealed arm's gap analysis said the miss was.

### 4.7 The three clamped utterances, named again

`4432298-351@ts2`, `4470290-178@ts2` and `4483338-619@ts2` keep the sealed flight's clamped end
boundary. They are the same three the media build receipt and §1.1 of the preregistration name.

### 4.8 Earnings-21 beside it, not compared to it

The Earnings-21 full-44 corpus figure is **8.200**. It is placed here because §4.3 requires it, and
it is **not** compared: it is a different corpus, cut into fixed 90-second windows rather than
published utterance boundaries, scored against a different reference convention. Nothing in this
document rests on the two numbers being close.

---

## 5. The prediction, scored against what happened

| | value |
|---|---:|
| preregistered interval | **7.5 – 10.5** |
| additive transfer point | 7.94 |
| multiplicative transfer point | 8.61 |
| **measured** | **9.2377** |

**CONFIRMED: inside the preregistered interval**, and between the two transfer points — 1.30 above
the additive one, 0.63 above the multiplicative one. The transfer assumption survives its own
falsifier: a corpus WER above 12.79 would have refuted it outright, and 9.2377 is 3.55 points below
that line.

The dev delta was −7.9958 points (17.4012 → 9.4054, ratio 0.5405); the test delta is **−6.6988**
(15.9365 → 9.2377, ratio 0.5797). The effect transferred **in kind**, and it transferred slightly
**smaller in size** — which is the direction §5 argued for after withdrawing the earlier claim that
test was the more affected population. Both directional clauses hold: the insertion share and the
length ratio fell, the effect concentrated in the short-duration buckets, and the boundary block fell
by 6.05 points against a clause that asked for 2.0.

---

## 6. Serving, cost and the monitor

Attached to the coordinator's resident session `e22-test-np8-c32768-20260907` — the sealed test
flight's own `-c 32768 -np 8` geometry, eight 4,096-token slots, port 8080, fragment
`q4km-e22-esb-mmproj-gpu-04ccc72a-np8` — with `session_reused: true`, `session_source:
attached-serving-session`, `startup_seconds: 0.0`. **No server was started or stopped**;
`stop_serving` was the documented no-op and the session was still up with eight idle slots
afterwards.

2,735 contacts in **799.267 s** wall at **3.4219 contacts/s** and **2.109 s** mean latency, slot
occupancy 0.9021 on eight slots — **0.2220 GPU-hours** against the 1.00 registered ceiling and the
0.60 plan, and inside the 0.290 h the preregistration derived from the sealed flight's own
1.16e-5 GPU-h per audio second. Realized spend **2,735 of 2,800 registered calls**, **24,964.608 of
25,500 registered speech-audio seconds**, **zero paid API**.

Monitor summary for the attempt's own contact window: 73 samples over 785.894 s, **parked 0.0 s,
active 785.894 s, parked fraction 0.000**, `requests_delta` 576 (a lower bound at the 10-second
sampling interval, not the throughput figure), mean power **87.265 W**, peak **91.3 W**, mean GPU
utilization **82.89 %**.

Zero `cuda error`, zero `out of memory` and zero `GGML_ASSERT` lines in the session's server log,
which shows `process_mtmd … encoding mtmd batch` throughout, so **every row paid a live mmproj encode
and no feature cache was involved**. Scored **once** over the complete sealed manifest through
`core.scoring_batch` with `verified = true`, one job, none failed, `include_per_sample = true`, never
sharded.

Identity: config hash `f84f2078`, protocol hash `f3442e1b`, split identity `ecd9ab76` — the three the
zero-contact wire check had already computed for this cell, unchanged. Manifest SHA-256
`2b4025e8…`, outputs `5713b791…`, trace `6893fe85…`, sealed scores `a8bc51f2…`.

The read itself made **zero** outbound connection attempts under `arm_offline_guard`.

---

## 7. The claim rule, quoted verbatim, and what this number licenses

> **The published systems did not append silence.** The 9.79 (NeMo AutoModel) and 12.3 (Open ASR
> Leaderboard) rows consumed the ESB release's own audio arrays and nothing else. Every request in
> this cell carries 2.0 s of digital silence after the published span. That is `D-TS2-3`, it is a
> **protocol difference**, and **every statement of this number must carry it**. A sentence of the
> form "Qwen3-Omni-30B-A3B-Instruct Q4_K_M scores `W` on ESB Earnings22" is false without it.

> That is the whole warrant. It licenses the sentence *"under a named model-usage local optimization
> of the study's own serving path, the frozen core reaches `W` on the published ESB Earnings22 test
> subset, against a published 9.79 and a cross-read 12.3 that were measured without it"* — and it
> licenses nothing shorter.

With `W` = 9.2377, the licensed sentence is: **under a named model-usage local optimization of the
study's own serving path, the frozen core reaches 9.2377 % corpus Whisper-normalized WER on the
published ESB Earnings22 test subset, against a published 9.79 and a cross-read 12.3 that were
measured without it.**

The three-step warrant of §7.2 holds unchanged and its third step is still where the argument stops:
the tail **adds no information** (digital silence after the published span; no published sample
removed, reordered or altered); it **addresses a defect of our path that the published path does not
have** (17,695 of the tokens we send are unmasked pad the HF `Qwen3OmniMoeProcessor` masks away);
**and it does not make the two identical** — the published path masks the block, we still send it,
two seconds later, and 2.0 s of appended silence is itself additional evidence that speech ended,
which this cell cannot separate from the artifact repair. **The honest reading is that the tail moves
our input processing closer *in effect* to the published path's, not that it reproduces it.**

---

## 8. What this cell does not conclude, and what closes

* **Not that the residual is quantization, prompt or decode.** `D2` — Q4_K_M against an unstated
  published precision — is untested by this cell. The cell landed 0.55 points *below* the published
  9.79, so there is no residual gap to attribute in that direction; what remains unknown is what the
  number would be at the published precision, and that stays unmeasured.
* **Not that the tail is the last difference.** The 2026-09-06 array-durations check recorded a
  second live deviation this cell does not address: the release stores each call's native container
  (16 kHz stereo, 22.05 kHz stereo, 24 kHz mono) while this study's clips are librosa-decoded 16 kHz
  mono from the locked MP3s. Same span, different decode, unknown sign.
* **Not that the encoder pad was removed.** §0.1 said this before any number existed and it is still
  true: appending 200 whole mel frames leaves the residue `(n_samples // 160) % 100` unchanged, so
  the same 136,533 pad frames and the same 17,695 masked-away tokens were still sent — their pooled
  share merely fell from 6.52 % to 5.17 % because the request grew. The `frame-exact` probe that
  would remove them is neither built nor authorized on either split.
* **Nothing about the other 109 confirmatory calls**, nothing about the ESB validation split (which
  is inside those 109), and nothing about generalization, superiority or Stage-3.
* `saea-scoring-v1` figures (20.8960 → 14.3053) are a different metric family and are reported for
  continuity only; they are never an alignment however close they land. `merge_compounds` is not
  applied and works against us. `fstalign` is not installed and was not run.
* **Earnings-22 test is closed.** The read is spent, no third read is proposed, and any further
  Earnings-22 work moves to dev or stops.

---

## 9. Receipts

| what | where |
|---|---|
| flight receipts, falsifier, sealed score, this read's tables | `docs/checks/speech-aware-evidence-acquisition/2026-09-07-e22-esb-shortform-tail2s-test-v1/` |
| the read itself | `scripts/e22_test_tail2s_read.py` (zero contact, offline guard armed) |
| the falsifier | `scripts/e22_test_tail2s_falsifier.py` |
| exposure rows | `docs/exposure-ledger.md`, `SAEA-E22-ESB-SHORTFORM-TAIL2S-TEST-SMOKE-V1` and `SAEA-E22-ESB-SHORTFORM-TAIL2S-TEST-V1` |
| preregistration | `docs/readiness/2026-09-07-e22-esb-shortform-tail2s-test-v1-preregistration.md` |
| sealed comparator | `docs/readiness/2026-09-04-e22-esb-shortform-alignment-v1-verdict.md` |
| the media | `docs/checks/speech-aware-evidence-acquisition/2026-09-07-e22-test2735-tail2s-media/` |
