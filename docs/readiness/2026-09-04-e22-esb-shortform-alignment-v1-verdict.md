# Earnings-22 ESB short-form alignment — verdict

**NOT ALIGNED. 15.937 % corpus WER under the Whisper `EnglishTextNormalizer` over all 2,735
published ESB test utterances, against Qwen3-Omni-30B-A3B-Instruct's own published 9.79** (+6.15),
and against the same model's cross-read 12.3 (+3.64). The band test (≤ 12.79) fails, the strict
`whisper-large-v3` floor (≤ 11.59) fails, and the loose `whisper-base.en` floor (≤ 15.09) fails by
0.85 points. Of the nine published floors on this column only `whisper-tiny.en` (19.12) is cleared.

Run `SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1`, attempt `attempt-20260905T044432Z-8f23ee`, study commit
`7f5d2837`, config hash `179c08ef`, protocol hash `d74adf8d`, manifest sha256 `dbfa6efb…`
(recomputed independently in `verdict/result-summary.json`). COMPLETED and FINALIZED, 2,735 of 2,735 contacts.
Preregistration: `docs/readiness/2026-09-04-e22-esb-shortform-alignment-v1-preregistration.md`.
Receipts: `docs/checks/speech-aware-evidence-acquisition/2026-09-04-e22-esb-shortform-alignment-400-v1/`.

This is the study's first **same-model** alignment attempt on any carrier, and it is the first one
to fail. That is worth more than a pass would have been, because the failure has a shape.

## 1. The number

| | value |
|---|---:|
| corpus WER, Whisper `EnglishTextNormalizer`, **paper-facing** | **15.937 %** |
| substitutions / deletions / insertions | 2,236 / 948 / **4,612** |
| reference words | 48,919 |
| mean of per-utterance WER, same normalizer | 28.129 % |
| equal-call weighting (mean of the six per-call corpus figures) | 16.703 % |
| corpus WER, frozen `saea-scoring-v1` | 20.896 % |
| mean of per-utterance WER, `saea-scoring-v1` | 31.661 % |

Scored once, through `core.scoring_batch`, as one whole-manifest job with `verified: true` — never
sharded, never averaged across shards. The manifest declares `asr-wer-esb-whisper`, `asr-wer-esb`
and `cost`; the batch aggregate reproduces the finalize `scores.json` to the digit
(0.1593654817146712).

The `saea-scoring-v1` figure is a different metric family and is **not** an alignment statement,
however it lands.

### Decision, as preregistered

| test | threshold | value | result |
|---|---:|---:|---|
| band | ≤ 12.79 (9.79 + 3) | 15.937 | **FAIL** (+3.15 over) |
| strict floor, `whisper-large-v3` | ≤ 11.59 | 15.937 | **FAIL** |
| loose floor, `whisper-base.en` | ≤ 15.09 | 15.937 | **FAIL** (+0.85 over) |
| ALIGNED-BETTER | < 6.79 | 15.937 | not reached |

Floors cleared: `whisper-tiny.en` 19.12 only. Floors failed: `whisper-large-v3` 11.59,
`-turbo` 11.07, `distil-large-v3.5` 10.83, `Qwen3-ASR-0.6B` 10.78, `Qwen3-ASR-1.7B` 9.73,
`medium.en` 12.63, `small.en` 12.97, `base.en` 15.09.

## 2. Per call

| call | utterances | audio s | ref words | S | D | I | corpus WER % (Whisper) | mean per-utt % | corpus WER % (`saea-scoring-v1`) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4432298 | 351 | 2,527.4 | 5,948 | 448 | 154 | 716 | **22.159** | 30.181 | 25.983 |
| 4450488 | 508 | 4,269.9 | 8,694 | 387 | 157 | 683 | **14.113** | 19.541 | 20.383 |
| 4470290 | 178 | 1,584.8 | 3,566 | 265 | 89 | 343 | **19.546** | 23.595 | 24.639 |
| 4479741 | 473 | 3,499.8 | 8,436 | 362 | 175 | 689 | **14.533** | 30.127 | 19.611 |
| 4483338 | 619 | 4,024.3 | 11,516 | 478 | 213 | 1,049 | **15.109** | 28.848 | 20.212 |
| 4485244 | 606 | 3,588.4 | 10,759 | 296 | 160 | 1,132 | **14.760** | 33.178 | 19.027 |
| **all six** | **2,735** | **19,494.6** | **48,919** | **2,236** | **948** | **4,612** | **15.937** | **28.129** | **20.896** |

Natural mixture 15.937 %, equal-call 16.703 %. The spread is 14.11 to 22.16, and the worst call
(4432298, Polish speakers, 16 kHz) is the one with the strongest accents and the lowest sample rate.
No call is inside the band.

## 3. Where the gap is — and it is not recognition

Full decomposition in `verdict/gap-decomposition.json`. **Every figure below is a diagnostic
computed after the fact on sealed outputs. None of it is the verdict, none of it was fitted, and the
two transforms marked ORACLE use the reference's own length, so they bound a component from above
and are not achievable numbers.**

**Insertions are 59.2 % of all errors** (4,612 of 7,796), against 28.7 % substitutions and 12.2 %
deletions. The hypothesis is systematically longer than the reference: 52,583 hypothesis words
against 48,919 reference words, a ratio of **1.0749**, with a longer hypothesis on 1,556 of 2,735
utterances and a shorter one on only 317.

| transform | oracle? | corpus WER % | Δ vs sealed |
|---|:--:|---:|---:|
| **sealed number** | — | **15.937** | — |
| collapse immediate word repeats in the hypothesis | no | 16.538 | **+0.601** |
| collapse immediate word repeats on both sides | no | 15.605 | −0.331 |
| cut each hypothesis to its own reference word count | **yes** | **10.456** | **−5.480** |
| both, composed | **yes** | 11.241 | −4.696 |

| restriction | utterances | corpus WER % | Δ vs sealed |
|---|---:|---:|---:|
| all | 2,735 | 15.937 | — |
| ≥ 1 s | 2,526 | 15.530 | −0.406 |
| ≥ 2 s | 2,306 | 15.129 | −0.808 |
| ≥ 3 s | 2,093 | 14.714 | −1.222 |

| duration | utterances | hyp/ref length | corpus WER % | insertions' share of errors |
|---|---:|---:|---:|---:|
| 0–1 s | 209 | 1.110 | 51.26 | 48.4 % |
| 1–2 s | 220 | 1.140 | 31.66 | 60.5 % |
| 2–4 s | 454 | 1.147 | 26.14 | 68.6 % |
| 4–8 s | 856 | 1.096 | 17.45 | 64.8 % |
| 8–16 s | 820 | 1.058 | 13.10 | 55.6 % |
| 16–40 s | 176 | 1.039 | 11.35 | 48.2 % |

Reading these together:

1. **Over-generation is the gap.** An oracle length cut moves the number by 5.48 points, from
   15.937 to **10.456** — which would be inside the band (≤ 12.79) and under the strict floor
   (≤ 11.59). Nothing else moves it by even a quarter of that. The residual after removing
   over-generation is roughly consistent with alignment, so what fails here is **output discipline,
   not acoustic recognition**. That is a hypothesis for a future registered cell, not a result:
   the transform is an oracle and no achievable procedure is claimed.
2. **Disfluency repetition is not the driver.** Collapsing repeated words in the hypothesis alone
   makes the number *worse* (+0.60), because the references carry genuine repetitions too;
   collapsing both sides buys 0.33. So the stutters visible in the outputs
   (`we'll we'll we'll we'll have announcements`) cost about a third of a point, not six.
3. **Short utterances are not the driver either.** Dropping everything under 3 s removes 642
   utterances and buys 1.22 points. They are dramatic per-row — 51 % WER under a second — but they
   carry 3.5 % of the reference words.
4. **The failure mode is uniform, not local.** The length ratio is above 1.03 in every duration
   bucket and every call fails the band. This is not a handful of pathological rows.

What the over-generation actually looks like, from the sealed outputs:

* trailing continuation past the segment boundary — `4485244-547`, reference *"We've got execution
  in front of us, we just need to perform."*, hypothesis the same plus *"And I think that's what
  we're going to do."*;
* a fragment of the next sentence — `4432298-250`, hypothesis ends *"…is that a new thing or or is
  that something that's"*;
* verbatim stutters the cleaned reference does not carry — `4432298-222`, *"that's that's that's the
  fact, that's the the the situation. Nothing to announce."*;
* loops on near-empty audio — `4432298-20`, *"That's all from my side. Let's now, let's now, let's
  now."*

Two smaller defects, both recorded rather than removed:

* **Four references normalize to nothing** (`4432298-291` *"mm-hmm <affirmative>."*, `4479741-422`
  and `4483338-364` *"Um."*, `4483338-309` *"<inaudible>."*). They contribute zero reference words to
  the denominator while the 13 hypothesis words they draw count as insertions in the numerator.
  Four rows of 2,735; worth a few hundredths of a point.
* **Three hypotheses come back in Chinese**, all on sub-second clips: `4432298-287` (`呃，对对对。`
  for *"Sorry."*), `4432298-312` and `4485244-268` (for *"Thank you."*). A real defect of the frozen
  core on near-empty audio, three rows of 2,735.

## 4. What this does and does not license

**It does not say the frozen core cannot reach 9.79.** Five named deviations stand between this
number and the published one, and the decomposition points squarely at two of them:

* **D3, the prompt.** The published row's prompt is not published. This cell sent this study's own
  instruction — *"Transcribe the speech verbatim exactly as spoken…"* — chosen deliberately because
  it is byte-identical to the one the Earnings-21 full-44 flight sent, which is what makes the two
  Earnings numbers comparable. On Earnings-21, whose `.nlp` references are themselves verbatim, that
  instruction produced 8.200 % and ALIGNED. On Earnings-22, whose ESB references are Rev's cleaned
  sentence transcripts, the same instruction asks for exactly the disfluent, continuing output the
  reference does not contain. The instruction was held fixed on purpose and the cost of holding it
  fixed is now measured.
* **D1, the segmentation.** Each request is one sentence-length clip with no context. The model has
  no way to know where the sentence it was given ends, and the length ratio rising monotonically as
  clips get shorter (1.039 at 16–40 s, 1.147 at 2–4 s) is what that looks like.

D2 (Q4_K_M against an unstated published precision) is untested by this flight and remains a live
suspect for the residual 10.456 − 9.79 = 0.67 points. D4 (2,735 rows against the published 2,741)
and D5 (no `merge_compounds`) are both small and D5 works against us.

**It does not license a fix.** No knob was tuned on this population, no mechanism arm was flown, and
the owner decision permits exactly one read of these six calls. Any follow-up — a prompt cell, a
context cell, a Q8_0 cell — is a new registration on a *different* population, because these six
calls are now calibration-exposed and 109 confirmatory calls remain untouched.

**The Earnings-21 number stands and is not contradicted.** `SAEA-E21-FULL44-DIRECT-BASELINE-V2`
scored 8.200 % corpus WER over 44 Earnings-21 discovery calls and remains ALIGNED. That is a
different corpus, a different segmentation (fixed 90-second long-form windows, stitched per call)
and a different reference layer (the carrier's own `.nlp` tokens). The two numbers are printed side
by side as context and are never a difference.

## 5. Cost and conduct

| | value |
|---|---:|
| contacts | 2,735 of a registered 2,800 |
| speech audio | 19,494.608 s (5.415 h) of a registered 20,500 |
| dispatch wall time | 773.5 s at eight slots |
| server resident | 812 s ≈ **0.226 GPU-h** of a registered 2.0 |
| realtime factor | 25.2× |
| mean latency | 2.022 s per contact |
| throughput | 3.54 contacts/s |
| prompt tokens | 405,468 (mean 148.3) |
| completion tokens | 67,529 (mean 24.7) |
| peak VRAM | **22,506 MiB** of 24,463 |
| peak power | 90.41 W against a 100.00 W enforced limit |
| paid API spend | 0 |

One attempt, no recovery needed, no CUDA fault, no out-of-memory, no skipped contact.

The window fit holds live over all 2,735 requests. **The largest prompt is 530 tokens** — exactly
the figure section 5.1 of the preregistration derived before any contact, from
`13 × ceil(36.360125)` speech tokens plus the 49-token text envelope the smoke measured — against a
4,096-token slot, ×7.7 on the prompt and ×2.63 on the worst total requirement. **The largest
completion is 137 tokens** against a 1,024 ceiling; **zero requests reached it**, so the ceiling
never binds and no transcript was truncated. The aggregate cross-check is consistent rather than
exact: 405,468 prompt tokens against 405,026 derived from a flat 49-token envelope plus
`sum(13 × ceil(audio_seconds))` = 271,011 over the roster — a 442-token difference, 0.11 %, which is
the rounding of the one-second speech-window rule at these very short durations and not an envelope
that moved.

`GGML_CUDA_DISABLE_GRAPHS=1` was read back from the live server process's own environment
(`/proc/687/environ`) rather than assumed. The `graphs reused = N` lines in the server log count
llama.cpp's host-side graph reuse, not CUDA graph capture, and appear identically in the sealed
Earnings-21 V2 log that set the same variable.

Conduct: exactly the six ESB test calls were read, once. The 109 remaining confirmatory calls —
including the six ESB **validation** calls — were not named, loaded, decoded or sent. The
re-designation is recorded in `docs/receipts/splits-calibration-exposure-2026-09-04.json`, which
pins `docs/receipts/splits.json` rather than rewriting it. References never entered the request
path: the roster the flight entry point reads carries identifiers, media paths, measured media
identity and segment spans only.

## 6. Open items

* **The 2,735-vs-2,741 row-count gap is still unexplained.** Every number here is over the 2,735
  rows the pinned table contains.
* **No self-run anchor exists.** The single most informative next measurement is a `whisper-large-v3`
  run over *these exact utterances* through *this exact scorer*, which would remove the normalizer,
  aggregation, chunking and subset confounds in one step and turn 11.59 from a published row into a
  measured one. It is not a frozen-core contact and needs its own registration.
* **The over-generation hypothesis is untested.** It is the obvious candidate for the next cell, on
  a population that is not these six calls.
* **Three Chinese hypotheses and four empty references** are recorded above; neither was removed
  from the number.
