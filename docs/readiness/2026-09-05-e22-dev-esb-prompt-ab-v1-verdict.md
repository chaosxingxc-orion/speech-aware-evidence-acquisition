# Earnings-22 DEV ESB prompt A/B — verdict

**THE PROMPT IS NOT THE EXPLANATION. The Qwen3-Omni authors' own English ASR prompt is
*worse* than the instruction this study already flies, by 0.83 corpus WER points, and the
paired CI90 excludes zero on the wrong side.** Arm A (the sealed ESB test flight's
instruction, byte for byte) scores **17.565 %** corpus WER under the Whisper
`EnglishTextNormalizer` over all 6,038 ESB utterances of this study's own Earnings-22 dev
subset10; arm B (`Transcribe the English audio into text.`) scores **18.394 %**.

**Decision, as preregistered: arm A's instruction remains this study's ASR instruction for
cleaned-reference protocols.** No knob moved, nothing was tuned, and the two arms differ in
exactly one thing — the instruction string.

Runs `SAEA-E22-DEV-ESB-PROMPT-A-V1` (attempt `attempt-20260905T073641Z-f977d1`, protocol hash
`a6fc27e1…`, manifest `3d230a2c…`) and `SAEA-E22-DEV-ESB-PROMPT-B-V1` (attempt
`attempt-20260905T080709Z-b77462`, protocol hash `c0b7fb20…`, manifest `776a2751…`), both at
study commit `4012521e`, both **COMPLETED and FINALIZED, 6,038 of 6,038 contacts**, both scored
once through `core.scoring_batch` as whole-manifest jobs with `verified: true`.
Preregistration: `docs/readiness/2026-09-05-e22-dev-esb-prompt-ab-v1-preregistration.md`.
Receipts: `docs/checks/speech-aware-evidence-acquisition/2026-09-05-e22-dev-esb-prompt-ab-v1/`.

**No alignment verdict is issued here and none is possible.** These ten calls are this study's
own dev subset10, not the published ESB test subset, and no published number covers them. The
published 9.79 / 12.3 appear below as orientation only, labelled as such.

## 1. The two numbers

| | arm A (control) | arm B (candidate) |
|---|---|---|
| instruction | *Transcribe the speech verbatim exactly as spoken. Never insert, repeat, or add any word you do not clearly hear in the audio. Output only the transcript text.* | *Transcribe the English audio into text.* |
| provenance | byte-identical to what `SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1` sent | the Qwen3-Omni model card's *Default Prompts* table and the official cookbook's English ASR cell |
| **corpus WER %, Whisper normalizer (paper-facing)** | **17.565** | **18.394** |
| mean of per-utterance WER % | 33.125 | 35.866 |
| equal-call weighting % | 17.513 | 18.366 |
| corpus WER %, frozen `saea-scoring-v1` | 23.042 | 24.163 |
| substitutions / deletions / insertions | 4,526 / 2,370 / 11,270 | 4,563 / 2,479 / 11,982 |
| reference words | 103,423 | 103,423 |
| hypothesis / reference length ratio | 1.0861 | 1.0919 |
| insertions' share of all errors | 62.04 % | 62.98 % |

**B − A = +0.830 corpus WER points.** Arm B is worse on every aggregation reported: corpus,
per-utterance mean, equal-call, and the frozen metric family. The `saea-scoring-v1` figures are
a different metric family and are never an alignment statement, however they land.

## 2. The paired contrast, B minus A

Through `analysis.paired.paired_contrast` on the two sealed manifests, over the same 6,038
utterances, with **10,000 replicates stratified by source call (10 strata), seed 20260903,
CI90**. The metric is **negated** per-utterance WER, so a positive delta and a "save" both mean
arm B is better.

| n | mean per-utt WER A | mean per-utt WER B | delta (positive = B better) | CI90 | saves (B better) | harms (B worse) | ties | sign test p |
|---:|---:|---:|---:|---|---:|---:|---:|---:|
| 6,038 | 0.3312 | 0.3587 | **−0.02741** | **[−0.0449, −0.0133]** | 686 | 821 | 4,531 | **0.00055** |

The corpus-level delta, through the same resampling rule and the same seed:
**A − B = −0.830 points, CI90 [−1.653, −0.172]**.

Both intervals lie **entirely below zero**. The preregistered significance rule asked whether
the CI90 lower bound was *above* zero; it is not — and not because the interval straddles zero,
but because the effect runs the other way. Arm B is worse, and significantly so.

Per stratum (source call), the paired delta is negative in **all ten**:

| call | n | delta (negative = B worse) | saves | harms | ties |
|---|---:|---:|---:|---:|---:|
| 4453225 | 635 | −0.0785 | 93 | 111 | 431 |
| 4469088 | 922 | −0.0190 | 81 | 126 | 715 |
| 4470684 | 589 | −0.0023 | 59 | 71 | 459 |
| 4474506 | 633 | −0.0342 | 54 | 89 | 490 |
| 4479944 | 588 | −0.0232 | 88 | 76 | 424 |
| 4481952 | 632 | −0.0023 | 73 | 81 | 478 |
| 4482383 | 469 | −0.0007 | 67 | 47 | 355 |
| 4482613 | 592 | −0.0121 | 82 | 100 | 410 |
| 4483937 | 517 | −0.0826 | 44 | 64 | 409 |
| 4485192 | 461 | −0.0215 | 45 | 56 | 360 |

## 3. Per call, corpus WER under the Whisper normalizer

| call | utterances | ref words | arm A | arm B | B − A |
|---|---:|---:|---:|---:|---:|
| 4453225 | 635 | 11,304 | 20.294 | 23.302 | **+3.008** |
| 4469088 | 922 | 11,493 | 19.856 | 20.595 | +0.739 |
| 4470684 | 589 | 10,862 | 14.298 | 14.491 | +0.193 |
| 4474506 | 633 | 11,534 | 14.947 | 15.285 | +0.338 |
| 4479944 | 588 | 10,882 | 23.663 | 23.828 | +0.165 |
| 4481952 | 632 | 9,827 | 17.116 | 17.014 | −0.102 |
| 4482383 | 469 | 9,763 | 14.258 | 13.838 | −0.420 |
| 4482613 | 592 | 9,168 | 22.939 | 23.288 | +0.349 |
| 4483937 | 517 | 8,680 | 15.472 | 19.389 | **+3.917** |
| 4485192 | 461 | 9,910 | 12.291 | 12.634 | +0.343 |
| **all ten** | **6,038** | **103,423** | **17.565** | **18.394** | **+0.830** |

Arm B is worse on eight of ten calls, better on two, and the two calls where it is much worse
(4453225 and 4483937, +3.0 and +3.9) carry most of the pooled difference. Natural-mixture
(corpus) and equal-call weightings agree: 17.565 / 18.394 against 17.513 / 18.366.

## 4. The error shape, and why the prompt was the wrong suspect

Full decomposition in `verdict/result-summary.json` under each arm's `error_shape`. **Every
figure below is a diagnostic computed after the fact on sealed outputs. None of it is the
verdict, none of it was fitted, and the transforms marked ORACLE use the reference's own length,
so they bound a component from above and are not achievable numbers.**

The failure mode the sealed ESB **test** flight found — over-generation, not recognition — is
present on this dev population in exactly the same shape, and **arm B does not repair it; it
makes it slightly worse**.

| | arm A | arm B | sealed test flight (six ESB test calls) |
|---|---:|---:|---:|
| insertions' share of all errors | 62.04 % | 62.98 % | 59.2 % |
| hypothesis / reference length ratio | 1.0861 | 1.0919 | 1.0749 |
| utterances with a longer hypothesis | 3,605 | 3,648 | 1,556 of 2,735 |
| excess hypothesis tokens | 10,247 | 10,898 | — |

| transform | oracle? | arm A corpus % | Δ vs sealed | arm B corpus % | Δ vs sealed |
|---|:--:|---:|---:|---:|---:|
| **sealed number** | — | **17.565** | — | **18.394** | — |
| collapse immediate word repeats in the hypothesis | no | 18.692 | +1.127 | 19.428 | +1.034 |
| collapse immediate word repeats on both sides | no | 17.334 | −0.231 | 18.074 | −0.321 |
| cut each hypothesis to its own reference word count | **yes** | **10.697** | **−6.868** | **10.813** | **−7.582** |
| both, composed | **yes** | 12.268 | −5.297 | 12.268 | −6.126 |

The two arms' composed-oracle figures being identical to four decimals is a coincidence, not a
copied cell: the error splits differ (5,008 / 4,885 / 2,795 against 5,055 / 4,859 / 2,774) and
happen to total exactly 12,688 on both, over the same 103,423 reference words.

| restriction | utterances | arm A | Δ | arm B | Δ |
|---|---:|---:|---:|---:|---:|
| all | 6,038 | 17.565 | — | 18.394 | — |
| ≥ 1 s | 5,535 | 16.897 | −0.667 | 17.655 | −0.739 |
| ≥ 2 s | 5,052 | 16.275 | −1.290 | 16.997 | −1.397 |
| ≥ 3 s | 4,450 | 15.465 | −2.100 | 15.847 | −2.547 |

| duration | utterances | A length ratio | A WER % | B length ratio | B WER % |
|---|---:|---:|---:|---:|---:|
| 0–1 s | 503 | 1.158 | 71.46 | 1.207 | 78.10 |
| 1–2 s | 483 | 1.188 | 42.09 | 1.215 | 44.28 |
| 2–4 s | 1,163 | 1.142 | 28.63 | 1.178 | 32.51 |
| 4–8 s | 1,991 | 1.107 | 19.05 | 1.119 | 20.28 |
| 8–16 s | 1,625 | 1.063 | 13.21 | 1.058 | 13.04 |
| 16–40 s | 271 | 1.045 | 10.72 | 1.043 | 10.85 |

(Two utterances longer than 40 s fall outside the last bucket and are not in that row; they are
in every pooled figure.)

Reading these together:

1. **Over-generation is still the whole gap, on both arms.** An oracle length cut moves arm A by
   **6.87 points** to 10.697 and arm B by 7.58 to 10.813. Nothing else moves either arm by even
   a fifth of that. This reproduces the test flight's finding on a different population and a
   different segmentation of the same corpus.
2. **The prompt does not touch it.** Arm B's instruction is shorter, plainer, and is the model
   authors' own; the length ratio still rises from 1.043 at 16–40 s to 1.207 under a second, and
   the oracle-cut residual is essentially the same on both arms (10.697 vs 10.813, a 0.12-point
   difference). Whatever makes the model continue past the segment boundary is not being asked
   for by arm A's wording, because removing that wording does not stop it.
3. **Arm B's damage is concentrated where the clip is short.** It is worse than arm A in every
   duration bucket below 8 s and marginally *better* in the two buckets above it. On clips under
   a second it is 6.6 points worse. A one-sentence instruction gives the model less to anchor on
   when the audio carries almost nothing.
4. **Arm B's worst completion is 3.5× arm A's.** Largest completion 461 tokens against arm A's
   130, both against a 1,024 ceiling that neither reached. The plainer instruction produces the
   longer runaway.
5. **Disfluency repetition is not the driver on either arm.** Collapsing repeated words in the
   hypothesis alone makes both arms *worse* (+1.13, +1.03), because the references carry genuine
   repetitions too; collapsing both sides buys 0.23 and 0.32.

Two smaller defects, recorded rather than removed, on both arms identically:

* **Ten references normalize to nothing** (isolated `Um.` / `<inaudible>.` / `mm-hmm` rows).
  They contribute zero reference words to the denominator while any hypothesis words they draw
  count as insertions in the numerator. Ten rows of 6,038.
* **Non-English hypotheses on near-empty audio**: 14 rows in arm A, 12 in arm B carry CJK-range
  characters. The same defect class the sealed test flight recorded (three rows there); it is a
  property of the frozen core on sub-second clips, not of either instruction.

## 5. What this licenses, and what it names next

**It settles the prompt question for cleaned references, in the direction nobody expected.** The
2026-09-04 test verdict named deviation D3 — the prompt — as the leading suspect, on the
reasoning that a "verbatim, never insert" instruction asks for exactly the disfluent, continuing
output a cleaned Rev reference does not contain. That reasoning is now **falsified on 6,038
paired utterances**: replacing it with the model authors' own plain ASR prompt makes the number
*worse*, significantly, on eight of ten calls and in every duration bucket under 8 s.

**Arm A's instruction stands, and it is now chosen rather than inherited.** It was previously
held fixed to keep the two Earnings numbers comparable; it is now the measured better of two
candidates on a population this study is allowed to optimize on.

**The next suspects, named for the owner and NOT flown here:**

1. **Context-free clipping (deviation D1), the leading suspect now.** Each request is one
   sentence-length clip with no context and no way for the model to know where the sentence it
   was given ends. The length ratio rises monotonically as clips shorten on **both** arms
   (1.043 at 16–40 s to 1.207 under a second on arm B; 1.045 to 1.158 on arm A), and the WER
   under a second is 71–78 % against 10.7–10.9 % at 16–40 s. That is the signature of a model
   continuing a sentence it cannot see the end of, and no instruction wording changed it. A cell
   that supplies neighbouring context, or that constrains decoding by clip duration, is the
   obvious next registration — on a population that is not these ten calls if it is to be
   reported, or on these ten if it is a further dev iteration.
2. **The prompt SHAPE rather than its text (deviation G2), still untested.** The same model-card
   section that supplied arm B's wording also says *"No `system prompt` should be set for any
   evaluation benchmark"* and puts the prompt text in the **user** turn **after** the audio.
   Both arms here kept the sealed flight's system-message shape on purpose, so that exactly one
   factor differed. Message placement and the presence of a system role remain completely
   unmeasured, and this experiment's result — that the text does not matter much and what does
   matter is boundary awareness — makes the *placement* question more interesting, not less: a
   user-turn instruction that follows the audio is the only form in which the model has heard
   the clip end before it is told what to do.
3. **Quantization (deviation D2)** is untouched by this experiment and remains a live suspect
   for whatever residual survives the first two.

**It does not license a claim about the published number.** Nothing here is an alignment
verdict. For orientation only: neither arm's dev figure would sit inside the 3-point band of the
published same-model 9.79 (≤ 12.79) or of the cross-read 12.3 (≤ 15.30). These are different
calls from the published subset, no published number covers them, and the comparison is printed
as context, never as a difference.

**It does not license a fix.** No knob was tuned on this population, no mechanism arm was flown,
no hypothesis was post-processed, and no third prompt variant was tried.

## 6. Cost and conduct

| | arm A | arm B |
|---|---:|---:|
| contacts | 6,038 of a registered 6,350 | 6,038 of a registered 6,350 |
| speech audio | 39,292.647 s (10.915 h) of a registered 41,300 | 39,292.647 s of a registered 41,300 |
| dispatch wall time | 1,612.9 s at eight slots | 1,643.9 s |
| server startup | 12.7 s | 10.8 s |
| **GPU hours** | **0.4515** of a registered 0.75 | **0.4596** of a registered 0.75 |
| realtime factor | 24.36× | 23.90× |
| mean latency | 1.927 s | 2.055 s |
| throughput | 3.744 contacts/s | 3.673 contacts/s |
| prompt tokens | 846,854 (mean 140.25) | 689,866 (mean 114.25) |
| completion tokens | 145,930 (mean 24.17) | 147,980 (mean 24.51) |
| largest prompt | **1,076** | **1,050** |
| largest completion | 130 | 461 |
| paid API spend | 0 | 0 |

One attempt per arm, no recovery needed, no CUDA fault, no out-of-memory, no skipped contact.
Across the experiment: 12,076 contacts, 21.83 h of audio, **0.911 GPU-hours** against a
registered 1.5 and a planned 1.0.

**The window fit held live, to the token, on both arms.** The largest prompt is **1,076** in arm
A and **1,050** in arm B — exactly `13 × ceil(78.360000) = 1,027` speech tokens plus the 49- and
23-token text envelopes the smoke measured, with nothing left over. The prompt-token totals
differ by 156,988, which is exactly `6,038 × 26`: the whole difference between the two arms'
request volume is the 26 tokens of instruction, on every single row. Against the 5,120-token
slot the worst request occupied 21 %, and the 1,024-token completion ceiling was never reached
by either arm.

**The geometry deviation G1 was necessary and was neutral.** `-c 40960 -np 8` (5,120 per slot)
replaced the sealed test flight's `-c 32768 -np 8` (4,096) because this roster's longest
utterance is 78.36 s against 36.36 s and the smaller slot fails this repository's own fit rule.
It served at 23,119 MiB free of 24,462 with no fault, it changed no request byte, and it was
identical in both arms, so it can have moved neither a transcript nor the contrast.

**Conduct.** Only this study's own registered `earnings22-original` **dev** subset10 was read —
the split it may optimize on, and one it already held before this experiment. **No confirmatory
call was named, loaded, decoded, scored or read**, and the six calibration-exposed ESB test
calls of 2026-09-04 were not read again. The ESB `train` split carries 113 source calls of which
103 are confirmatory for this study; the extractor dropped every one of them inside the batch
loop before a row could reach a list, a file, a log line or a receipt. References never entered
the request path: the roster the flight entry point reads carries identifiers, media paths,
measured media identity and segment spans only.

## 7. Defects found and fixed, and open items

**A real defect in a shared module, found by this experiment and fixed at the cause.**
`analysis.paired.mcnemar_exact` computed `sum(comb(n, k)) * (0.5 ** n)`. Both halves break above
a few thousand discordant pairs: `0.5 ** n` underflows to 0.0 for `n > 1074`, and the exact
integer numerator overflows when Python coerces it to float. This contrast has 686 saves and
821 harms — **1,507 discordant pairs**, a numerator of about `2**1506` — and raised
`OverflowError: int too large to convert to float`. Every roster this repository had run before
was small enough to stay inside the float range. The ratio is now
formed as an exact `Fraction` and converted once — correctly rounded at any magnitude, no
approximation, no change of definition, and no change to any value the old spelling could
compute. Regression test:
`tests/unit/test_analysis_paired.py::test_mcnemar_exact_survives_thousands_of_discordant_pairs`.

**A procedural defect of my own, caught by the wire check before any contact.** The first
wire-check pass wrote each receipt straight into `docs/checks/`, which made the tree dirty for
the *next* cell's scoring gate, so three of four cells came back `SCORING_FAILED` with
`?? .../wire-check/` as the whole reason. Nothing was spent. Receipts are now written outside the
tree and copied in afterwards.

**Open items:**

* **The pin on the 55 ESB train parquet shards is weaker than the test population's.** They are
  22.0 GB and were not downloaded, so each rests on its published git-LFS oid rather than on a
  local re-hash. The receipt records `locally_rehashed: false` for every one.
* **The over-generation mechanism is still unexplained.** Two prompts, one verbose and one
  minimal, produce the same 1.09 length ratio and the same monotone rise as clips shorten. The
  cause is not the wording.
* **No self-run anchor exists** for these calls or for the published subset. A
  `whisper-large-v3` run over the same utterances through the same scorer would remove the
  normalizer, aggregation and chunking confounds in one step; it is not a frozen-core contact and
  needs its own registration.
* **Message placement is unmeasured** (deviation G2), and is now the cheapest remaining test of
  the "boundary awareness" hypothesis.
