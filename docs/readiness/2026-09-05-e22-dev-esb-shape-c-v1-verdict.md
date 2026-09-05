# Earnings-22 DEV ESB shape C — verdict

**THE SHAPE DOES EXACTLY WHAT IT WAS PREDICTED TO DO TO THE LENGTH, AND THE NUMBER STILL GETS
WORSE. Over-generation was a symptom, not the cause.** The Qwen3-Omni model card's own
evaluation shape — no system message, instruction as user text after the audio — cut the
NET excess hypothesis length by more than half (hypothesis/reference ratio **1.0861 → 1.0398**,
insertions **11,270 → 9,094**, insertions' share of errors **62.0 % → 49.2 %**) and corpus WER
went **up 0.325 points**, from **17.5648 %** to **17.8896 %**, because every insertion it
removed came back as roughly 1.2 deletions (**2,370 → 4,975**).

**Decision, as preregistered: the official usage shape is EXCLUDED and is NOT adopted, and no
second test read is recommended to the owner.** The rule was a three-way conjunction; its
first and governing condition — that arm C's pooled corpus WER beat arm A — fails.

Run `SAEA-E22-DEV-ESB-SHAPE-C-V1` (attempt `attempt-20260905T094322Z-2174df`, protocol hash
`b75c42cb…`, manifest `a7d304eee2e8…`, study commit `a402f628`), **COMPLETED and FINALIZED,
6,038 of 6,038 contacts**, scored once through `core.scoring_batch` as a whole-manifest job
with `verified: true`. Paired against the two sealed arms of 2026-09-05 on the **same 6,038
utterances**, the same media bytes and the same reference layer.
Preregistration: `docs/readiness/2026-09-05-e22-dev-esb-shape-c-v1-preregistration.md`.
Receipts: `docs/checks/speech-aware-evidence-acquisition/2026-09-05-e22-dev-esb-shape-c-v1/`.

**No alignment verdict is issued here and none is possible.** These ten calls are this study's
own dev subset10, not the published ESB test subset, and no published number covers them.

## 1. The three numbers

| | arm A (control) | arm B | **arm C (official shape)** |
|---|---|---|---|
| wire messages | `[system: instruction][user: audio]` | `[system: instruction][user: audio]` | **`[user: audio, instruction]`** |
| instruction | *Transcribe the speech verbatim exactly as spoken. Never insert, repeat, or add any word you do not clearly hear in the audio. Output only the transcript text.* | *Transcribe the English audio into text.* | *Transcribe the English audio into text.* (byte-identical to B) |
| **corpus WER %, Whisper normalizer (paper-facing)** | **17.5648** | 18.3944 | **17.8896** |
| mean of per-utterance WER % | 33.1249 | 35.8659 | **31.3062** |
| equal-call weighting % | 17.5132 | 18.3664 | 17.8262 |
| corpus WER %, frozen `saea-scoring-v1` | 23.0423 | 24.1634 | 25.2070 |
| substitutions / deletions / insertions | 4,526 / 2,370 / 11,270 | 4,563 / 2,479 / 11,982 | **4,433 / 4,975 / 9,094** |
| total errors | 18,166 | 19,024 | 18,502 |
| reference words | 103,423 | 103,423 | 103,423 |
| hypothesis / reference length ratio | 1.0861 | 1.0919 | **1.0398** |
| insertions' share of all errors | 62.04 % | 62.98 % | **49.15 %** |
| utterances with a longer / shorter hypothesis | 3,605 / 731 | 3,648 / 740 | 2,659 / **1,451** |
| excess hypothesis tokens | 10,247 | 10,898 | **7,458** |
| CJK-character hypotheses | 14 | 12 | **0** |

**C − A = +0.325 corpus WER points.** Note the sign disagreement between the two aggregations,
which is the whole story of this experiment and is explained in section 4: arm C is **worse**
on the corpus number and **better** on the mean of per-utterance WER (31.31 against 33.12).

## 2. The paired contrasts

Through `analysis.paired.paired_contrast` on the sealed manifests, over the same 6,038
utterances, **10,000 replicates stratified by source call (10 strata), seed 20260903, CI90**.
The metric is **negated** per-utterance WER, so a positive delta and a "save" both mean the
right-hand arm is better.

| contrast | n | delta (positive = right better) | CI90 | saves | harms | ties | sign test p |
|---|---:|---:|---|---:|---:|---:|---:|
| **C − A** | 6,038 | **+0.01819** | **[+0.0112, +0.0251]** | 1,436 | 1,537 | 3,065 | 0.0666 |
| C − B | 6,038 | +0.04560 | [+0.0303, +0.0641] | 1,493 | 1,466 | 3,079 | 0.6327 |
| B − A (sealed, reproduced) | 6,038 | −0.02741 | [−0.0449, −0.0133] | 686 | 821 | 4,531 | 0.00055 |

The corpus-level deltas, through the same resampling rule and seed:

| contrast | corpus delta (positive = right better) | CI90 |
|---|---:|---|
| **C − A** | **−0.3249 points** | **[−0.5297, −0.1160]** |
| C − B | +0.5047 points | [−0.1718, +1.3441] |
| B − A (sealed, reproduced) | −0.8296 points | [−1.6530, −0.1719] |

**Both C-minus-A intervals exclude zero, and they point in opposite directions.** On the
per-utterance mean arm C is genuinely better (CI90 entirely above 0); on the corpus number it
is genuinely worse (CI90 entirely below 0). That is not a contradiction and not an artefact —
it is what happens when a change helps the many short utterances and hurts the few long ones
that carry most of the reference words. Section 4 measures exactly that.

Per stratum (source call), the paired **C − A** delta on negated WER — positive means arm C
is better on that call's per-utterance mean:

| call | n | delta | saves (C better) | harms (C worse) | ties |
|---|---:|---:|---:|---:|---:|
| 4453225 | 635 | −0.0036 | 148 | 203 | 284 |
| 4469088 | 922 | +0.0050 | 179 | 286 | 457 |
| 4470684 | 589 | +0.0351 | 151 | 116 | 322 |
| 4474506 | 633 | +0.0173 | 146 | 158 | 329 |
| 4479944 | 588 | **+0.0580** | 237 | 82 | 269 |
| 4481952 | 632 | +0.0014 | 128 | 185 | 319 |
| 4482383 | 469 | +0.0244 | 118 | 132 | 219 |
| 4482613 | 592 | +0.0044 | 160 | 123 | 309 |
| 4483937 | 517 | +0.0341 | 96 | 126 | 295 |
| 4485192 | 461 | +0.0198 | 73 | 126 | 262 |

Nine of ten strata are positive on the per-utterance mean while seven of ten are worse on the
corpus number (section 3) — the same weighting split, visible call by call. `4479944` is the
clearest case: 237 saves against 82 harms and −3.10 corpus points, arm C's best call on both
readings. The full per-stratum tables for all three contrasts are in
`verdict/per-arm-tables.md`.

The three sealed A/B figures in the bottom row are **reproduced, not copied**: the reader was
generalized from two arms to N and re-run on the sealed A/B inputs first, and it returned the
sealed verdict's numbers to the last digit (17.5648 / 18.3944, delta −0.027409449374692085,
CI90 low −0.0449336417097872, 686 / 821 / 4,531, p = 0.0005525225119838559, corpus delta
−0.829602699592936). That regression is why the generalization can be trusted with a third arm.

## 3. Per call, corpus WER under the Whisper normalizer

| call | utterances | ref words | arm A | arm B | arm C | C − A |
|---|---:|---:|---:|---:|---:|---:|
| 4453225 | 635 | 11,304 | 20.294 | 23.302 | 21.568 | +1.274 |
| 4469088 | 922 | 11,493 | 19.856 | 20.595 | 22.005 | **+2.149** |
| 4470684 | 589 | 10,862 | 14.298 | 14.491 | 13.800 | −0.497 |
| 4474506 | 633 | 11,534 | 14.947 | 15.285 | 15.259 | +0.312 |
| 4479944 | 588 | 10,882 | 23.663 | 23.828 | 20.566 | **−3.097** |
| 4481952 | 632 | 9,827 | 17.116 | 17.014 | 18.765 | +1.649 |
| 4482383 | 469 | 9,763 | 14.258 | 13.838 | 15.426 | +1.168 |
| 4482613 | 592 | 9,168 | 22.939 | 23.288 | 21.477 | −1.462 |
| 4483937 | 517 | 8,680 | 15.472 | 19.389 | 15.795 | +0.322 |
| 4485192 | 461 | 9,910 | 12.291 | 12.634 | 13.602 | +1.312 |
| **all ten** | **6,038** | **103,423** | **17.565** | **18.394** | **17.890** | **+0.325** |

Arm C is worse on seven calls and better on three, and the two calls it moves most move in
opposite directions (4479944 −3.10, 4469088 +2.15). Natural-mixture (corpus) and equal-call
weightings agree on the ordering: 17.565 / 18.394 / 17.890 against 17.513 / 18.366 / 17.826.

## 4. The mechanism, measured

**Every figure below is a diagnostic computed after the fact on sealed outputs. None of it is
the verdict, none of it was fitted, and the transforms marked ORACLE use the reference's own
length, so they bound a component from above and are not achievable numbers.**

### 4.1 The shape shortens the output everywhere, and that is only sometimes good

| duration | utterances | ref words | A ratio | A WER % | B ratio | B WER % | **C ratio** | **C WER %** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0–1 s | 503 | 1,265 | 1.158 | 71.46 | 1.207 | 78.10 | **1.115** | **66.80** |
| 1–2 s | 483 | 2,464 | 1.188 | 42.09 | 1.215 | 44.28 | **1.107** | **36.32** |
| 2–4 s | 1,163 | 10,172 | 1.142 | 28.63 | 1.178 | 32.51 | **1.075** | **27.19** |
| 4–8 s | 1,991 | 31,065 | 1.107 | 19.05 | 1.119 | 20.28 | 1.062 | 19.31 |
| 8–16 s | 1,625 | 45,298 | 1.063 | 13.21 | 1.058 | 13.04 | **1.021** | 14.16 |
| 16–40 s | 271 | 13,128 | 1.045 | 10.72 | 1.043 | 10.85 | **1.005** | 12.00 |

(Two utterances longer than 40 s fall outside the last row and are in every pooled figure.)

Arm C's length ratio is **closer to 1.0 in every bucket**, monotonically, and by the 8–16 s and
16–40 s buckets it has arrived (1.021, 1.005). The WER follows a different rule: arm C **wins
below 4 s** (−4.7, −5.8, −1.4 points), ties at 4–8 s, and **loses above 8 s** (+0.95, +1.28).

### 4.2 Why the corpus number and the per-utterance mean disagree

| duration | share of rows | share of the corpus denominator |
|---|---:|---:|
| 0–4 s | 35.6 % | **13.4 %** |
| 4–8 s | 33.0 % | 30.0 % |
| 8–40 s | 31.4 % | **56.5 %** |

The mean of per-utterance WER weights every utterance equally, so it is dominated by the short
rows where arm C wins; the corpus figure weights by reference words, so it is dominated by the
long rows where arm C loses. Both are computed correctly and both are reported. **The
paper-facing number is the corpus one**, as it has been for every Earnings figure this study
has published, and no aggregation was chosen after seeing the result.

### 4.3 The insertions came back as deletions

| | arm A | arm C | change |
|---|---:|---:|---:|
| substitutions | 4,526 | 4,433 | −93 |
| deletions | 2,370 | **4,975** | **+2,605** |
| insertions | 11,270 | **9,094** | **−2,176** |
| **total errors** | **18,166** | **18,502** | **+336** |

Arm C removes 2,176 insertions and pays 2,605 deletions for them — about **1.20 deletions per
insertion removed**. Substitutions barely move, so the words it does emit are neither more nor
less accurate; there are simply fewer of them, and the missing ones were words the reference
wanted.

**This is not a handful of catastrophic truncations.** Rows whose hypothesis is under half the
reference length: **47** in arm A and **47** in arm C (under a quarter: 13 and 19; empty: 2 and
1). The extra deletions are spread thinly across thousands of rows, a few words each, not
concentrated in a collapse. (The 4-row smoke did catch one genuine collapse — see section 6 —
and the flight shows it was an outlier, not the mode.)

### 4.4 The oracle bound moved the wrong way, which settles the question

| transform | oracle? | arm A | Δ | arm B | Δ | **arm C** | **Δ** |
|---|:--:|---:|---:|---:|---:|---:|---:|
| **sealed number** | — | **17.565** | — | **18.394** | — | **17.890** | — |
| collapse immediate word repeats in the hypothesis | no | 18.692 | +1.127 | 19.428 | +1.034 | 18.033 | +0.143 |
| collapse immediate word repeats on both sides | no | 17.334 | −0.231 | 18.074 | −0.321 | 16.607 | −1.283 |
| cut each hypothesis to its own reference word count | **yes** | **10.697** | **−6.868** | 10.813 | −7.582 | **12.273** | **−5.617** |
| both, composed | **yes** | 12.268 | −5.297 | 12.268 | −6.126 | 12.488 | −5.402 |

The A/B verdict's headline diagnostic was that an oracle length cut on arm A was worth **6.87
points**, down to 10.697. Arm C did in reality a large part of what that oracle did
artificially — and its own oracle floor is **12.273, 1.58 points HIGHER than arm A's**.

That is the decisive measurement. If over-generation had been the cause, then removing half of
it should have moved the real number toward the oracle bound and left the bound where it was.
Instead the bound rose. The oracle cut on arm A was recovering points by discarding words that
were *wrong*; arm C, cutting the same length without knowing the reference, discarded words
that were *right*. **The length was never the lever. An oracle length cut measures how much of
arm A's output is surplus, not how much of the gap a shorter output could recover.**

### 4.5 One clean win, recorded

The non-English-output defect is **gone**. Arms A and B produced 14 and 12 hypotheses
containing CJK-range characters, all on sub-second clips, and the sealed 2026-09-04 ESB test
flight produced three of the same class. Arm C produces **zero**. Whatever makes the frozen
core answer a near-empty clip in another script, a user-turn instruction that follows the audio
suppresses it completely. That is a property worth remembering even though it buys no points
here (those 14 rows are a rounding error against 103,423 reference words).

### 4.6 Smaller defects, unchanged and recorded

**Ten references normalize to nothing** (isolated `Um.` / `<inaudible>.` / `mm-hmm` rows) in all
three arms identically. They contribute zero reference words to the denominator while any
hypothesis words they draw count as insertions in the numerator. Ten rows of 6,038.

`4481952-631`, the one utterance whose `end_ts` runs past its decoded parent and is clamped to
it, is in this population as it was in the A/B, named in the roster receipt and named here.

## 5. What was actually sent, proved rather than assumed

Before any generation, all three arms were rendered through the pinned GGUF chat template on
the live server at **zero generated tokens** (`GET /props`, `POST /apply-template`, `POST
/tokenize` only — one `/props`, three `/apply-template` and six `/tokenize` calls, and no `/completion` call of any kind). The wire messages were
not re-spelled for the proof: they were captured from the **real**
`core.model.transport.LlamaServerTransport`, resolved through the same `TRANSPORTS` registry
entry and the same composed config the flight uses, driven with a real
`core.policies.build_arm_payload` payload, with only its HTTP sender replaced.

| arm | wire roles | rendered prompt | text tokens |
|---|---|---|---:|
| A | `["system","user"]` | `<\|im_start\|>system\nTranscribe the speech verbatim exactly as spoken. …<\|im_end\|>\n<\|im_start\|>user\n«MEDIA»<\|im_end\|>\n<\|im_start\|>assistant\n` | 47 |
| B | `["system","user"]` | `<\|im_start\|>system\nTranscribe the English audio into text.<\|im_end\|>\n<\|im_start\|>user\n«MEDIA»<\|im_end\|>\n<\|im_start\|>assistant\n` | 21 |
| **C** | `["user"]` | `<\|im_start\|>user\n«MEDIA»Transcribe the English audio into text.<\|im_end\|>\n<\|im_start\|>assistant\n` | **16** |

Four assertions, fixed in the preregistration before the render ran, all held:

1. arm C's wire roles are exactly `["user"]`;
2. arm C's rendered prompt contains **no system block** — the pinned template does **not**
   inject a default system prompt of its own when the request carries none;
3. arm C's instruction appears verbatim, and every occurrence of it sits **after** the media
   marker;
4. arms A and B, rendered through the identical route, **still show their system block** — the
   control without which an absent block proves nothing.

Chat template sha256 `45777d2e798aae1d…`, build `04ccc72a2207347ca76161b93fd9d846dd0a8675`,
live slot `n_ctx` 5,120. Receipt: `prompt-fit/prompt-fit-render.json` (run
`SAEA-E22-DEV-ESB-SHAPE-C-PROMPT-FIT-V1`, two attempts, the second only to record the build
commit the first receipt had left empty).

**The rendered figures then held live, to the token, three times over.** `/tokenize` runs with
`add_special: false`, so the flight's own two special tokens sit on top: 47 + 2 = **49** and
21 + 2 = **23** are exactly the envelopes the sealed A/B smoke measured, which makes 16 + 2 =
**18** the arm-C prediction — and the arm-C smoke measured exactly 18 on all four of its
requests, and the flight's aggregate confirms it: arm C sent 659,676 prompt tokens against arm
B's 689,866, a difference of **30,190 = 6,038 × 5**, which is precisely the five tokens of
system-block scaffolding the template no longer writes, on every single row. Largest prompt
1,045 = `13 × ceil(78.36) = 1,027` speech tokens plus 18, against a 5,120-token slot.

## 6. The smoke, and what it saw before the flight

`SAEA-E22-DEV-ESB-SHAPE-C-SMOKE-V1`, attempt `attempt-20260905T094034Z-fa6e61`, **COMPLETED and
FINALIZED, 4 of 4**, on exactly the four rows the A/B smoke flew (not re-drawn). All four
registered go/no-go criteria affirmative: every row returned a non-empty completion under the
no-system-message shape; the worst request (1,045 + 1,024 = 2,069) is under half the 5,120-token
slot; both ESB scorers returned per-sample rows through `core.scoring_batch` with
`verified: true`; and the projected flight time was well inside the ceiling. **GO.**

One observation was recorded in the smoke receipt **before the flight launched**, and it earns
its place here because it is the failure mode arm C introduces, caught early: on the longest row
(`4470684-13`, 78.36 s, 32-word reference) arm C returned the single word `yet.` where arms A
and B both returned a full 33- and 34-word transcript. Four rows are not a result and the
smoke's WER figures enter no verdict, so it was not a stop condition — and the flight has now
put it in proportion: collapses of that severity happen on 47 rows of 6,038, the same count as
arm A, so the 0.325-point loss is not made of them.

## 7. The decision, as preregistered

The rule was a three-way conjunction. Two of its three conditions hold and the governing one
does not:

| condition | required | measured | holds? |
|---|---|---|:--:|
| arm C's pooled corpus WER beats arm A | 17.8896 < 17.5648 | **17.8896 > 17.5648** | **NO** |
| paired C−A CI90 lower bound above 0 | > 0 | +0.0112 | yes |
| hypothesis/reference length ratio falls toward 1.0 | C < A | 1.0398 < 1.0861 | yes |

**The official usage shape is EXCLUDED.** It does not become this study's ASR request shape for
cleaned-reference protocols, and **no second test read is recommended to the owner.** Spending
the last unspent read of the six ESB test calls on a shape that is 0.325 points worse on the
split we are allowed to optimize on would spend a one-shot asset to confirm a regression.

*(The length-ratio clause was preregistered as "strictly below arm A's pooled ratio". Arm C also
satisfies the stricter reading — |1.0398 − 1| = 0.0398 against |1.0861 − 1| = 0.0861, so it is
genuinely closer to 1.0 and has not overshot at the pooled level. Both readings are recorded in
`verdict/result-summary.json`; neither can change the outcome, because the conjunction fails on
the first condition either way.)*

**Arm A's instruction and arm A's request shape both stand**, now each chosen against a measured
alternative rather than inherited.

**Orientation only, as preregistered**: neither arm C's 17.890 nor any other arm's dev figure
would sit inside the 3-point band of the published same-model 9.79 (≤ 12.79) or of the cross-read
12.3 (≤ 15.30). These are different calls from the published subset, no published number covers
them, and the comparison is printed as context, never as a difference.

## 8. What this licenses, and what it names next

**It closes the request-usage question.** Two experiments and 18,114 contacts on one roster have now
varied the two things a request can vary without touching the model: the instruction **text**
(A/B, 2026-09-05 — the authors' own prompt is 0.83 points worse) and the instruction's
**placement and the presence of a system role** (this flight — the model card's own evaluation
shape is 0.32 points worse). Neither is the explanation for the sealed ESB test flight's
15.937. The way this study asks is not the problem.

**It reclassifies the leading suspect, which is the real result.** The A/B verdict left
over-generation as the named mechanism, on the strength of a 6.87-point oracle length cut. That
reading is now falsified from the other side: an arm that genuinely produced 19 % fewer
insertions and a length ratio of 1.0398 scored **worse**, and its own oracle bound sat 1.58
points **higher**. Length is a symptom. What the frozen core gets wrong on this corpus is
*which* words, not *how many* — and the surplus words arm A emits are, on balance, closer to
the reference than the silence arm C replaces them with.

**The next suspects, named for the owner and NOT flown here:**

1. **The reference layer itself, now the leading suspect.** The ESB Earnings-22 column is Rev's
   **cleaned** sentence transcript, not a verbatim one. Substitutions are essentially constant
   across all three arms (4,526 / 4,563 / 4,433) while insertions and deletions trade freely,
   which is the signature of a stable recognition core measured against a reference whose
   *conventions* — disfluency removal, number and compound formatting, speaker-boundary
   treatment — differ from what the model emits. `merge_compounds`, which the published ESB
   protocol applies and this study's normalizer does not (deviation H4/G4, identical in all
   three arms and therefore invisible to every contrast here), belongs in that list. A
   normalizer-and-convention audit against the published ESB recipe is a **model-free** check:
   it needs no contact at all.
2. **A self-run anchor.** A `whisper-large-v3` pass over these same 6,038 utterances through the
   same scorer would separate "our normalizer and segmentation" from "this frozen core" in one
   step. It is not a frozen-core contact and needs its own registration. The A/B verdict already
   named this; this flight raises its priority above every remaining prompt-side idea.
3. **Context-free clipping**, still unmeasured as such. This flight changed *where the
   instruction sits* but every request is still one sentence-length clip with no neighbours. A
   cell that supplies neighbouring context is a different experiment from this one and remains
   open.
4. **Quantization (Q4_K_M)** is untouched by both experiments and remains a live suspect for
   whatever residual survives the first three.

**It does not license a claim about the published number.** Nothing here is an alignment
verdict. **It does not license a fix**: no knob was tuned on this population, no mechanism arm
was flown, and no hypothesis was post-processed.

## 9. Cost and conduct

| | arm A (sealed) | arm B (sealed) | **arm C** |
|---|---:|---:|---:|
| contacts | 6,038 of 6,350 | 6,038 of 6,350 | **6,038 of a registered 6,350** |
| speech audio | 39,292.647 s (10.915 h) | 39,292.647 s | **39,292.647 s of a registered 41,300** |
| dispatch wall time | 1,612.9 s | 1,643.9 s | **1,652.1 s** at eight slots |
| server startup | 12.7 s | 10.8 s | 11.1 s |
| **GPU hours** | 0.4515 | 0.4596 | **0.4620** of a registered 1.0, planned 0.6 |
| realtime factor | 24.36× | 23.90× | 23.78× |
| mean latency | 1.927 s | 2.055 s | 2.074 s |
| throughput | 3.744 contacts/s | 3.673 contacts/s | 3.655 contacts/s |
| prompt tokens | 846,854 (mean 140.25) | 689,866 (mean 114.25) | **659,676 (mean 109.25)** |
| completion tokens | 145,930 (mean 24.17) | 147,980 (mean 24.51) | **136,361 (mean 22.58)** |
| largest prompt | 1,076 | 1,050 | **1,045** |
| largest completion | 130 | 461 | **118** |
| paid API spend | 0 | 0 | **0** |

One attempt, no recovery, no CUDA fault, no out-of-memory, no skipped contact. Across the two
experiments: 18,114 contacts, 32.75 h of audio, 1.373 GPU-hours.

**Conduct.** Only this study's own registered `earnings22-original` **dev** subset10 was read —
the split it may optimize on, and the same ten calls the sealed A/B already read. Nothing was
re-cut, re-drawn or re-hashed: the roster (`20437bcb…`), the derived WAV bytes, the derived
reference layer (`8da3a65d…`) and the D1 media supplement (`ad01c4ec…`) are the sealed A/B
artifacts, reused by name and by hash, which is what makes every contrast within-utterance.
**No confirmatory call was named, loaded, decoded, scored or read**, and the six
calibration-exposed ESB test calls of 2026-09-04 were not read again. References never entered
the request path.

## 10. The seam, and what it cannot have moved

One request-shaping config key, `omit_system_message`, on
`core.model.transport.LlamaServerTransport`, beside the `user_turn_text` /
`user_turn_audio_first` pair the 2026-09-04 Audio2Tool official-protocol work already added. It
defaults to false, so every fragment that predates it renders byte-identical requests;
`tests/unit/test_llama_server_transport.py::test_sealed_e22_arm_a_payload_is_byte_identical_without_the_seam`
pins the sealed A/B arms' wire bytes and
`::test_transport_factory_defaults_omit_system_message_to_false` pins the factory default.
`rails.task_adapter.TaskAdapter.assemble_prompt` is unchanged — it still produces the internal
`[system, user]` pair `rails.core_client` parses into `(task_instruction, media_relpath,
supply_texts)`; only the transport's rendering of that payload changes, because the transport is
the one place the wire messages are built. No probe module, no `TaskAdapter` subclass, no
controller subclass; `scripts/checks/engineering_base_check.py` PASS.

The seam is fail-closed because its failure mode is silent — a dropped system message would
otherwise take `task_instruction` off the wire while the payload, the trace records, the config
hash and the protocol hash all still recorded it, and the run would be measuring a prompt nobody
wrote down. Five refusals, each with a test: no `user_turn_text`; a speech-feature prompt order;
a non-bool; a `task_instruction` that is not byte-identical to the `user_turn_text`; and any
request carrying evidence or an exemplar bank (both travel in the system message under the
evidence-first orders).

## 11. Defects found and fixed, and open items

**One defect of my own, caught by reading the artifact rather than by a test.** The first render
receipt recorded `build_commit: ""`, because the pinned runtime receipt keeps that value at
`llama_cpp.build_commit` and the code read a non-existent top-level key — a field that claims to
pin the binary's identity, silently empty. Fixed at `a402f628` and the render re-run; both
attempts are recorded, and the second reproduced the first's token counts and all four
assertions exactly.

**A generalization, with its regression.** `scripts/e22_dev_esb_prompt_ab_analysis.py` took
exactly two arms and one contrast. It now takes N of each (`--arm NAME=run_id,run_dir,receipt`,
`--contrast RIGHT-LEFT`), keeps the legacy flags and the `paired_contrast_b_minus_a` /
`corpus_level_delta` document keys, and was re-run on the sealed A/B inputs **before** being
trusted with arm C — reproducing that verdict to the last digit (section 2).

**Open items:**

* **The reference layer's conventions are unaudited** against the published ESB recipe, and are
  now this study's leading suspect for the Earnings-22 gap. `merge_compounds` is the one known,
  named difference; there may be others. This is a model-free check.
* **No self-run anchor exists** for these calls or for the published subset.
* **The pin on the 55 ESB train parquet shards** remains weaker than the test population's: 22.0
  GB, not downloaded, each resting on its published git-LFS oid rather than a local re-hash.
* **Context-free clipping is still unmeasured as such.** This flight moved the instruction; it
  did not give the model a neighbour.
* **`pytest` carries six pre-existing failures and one collection error**, unchanged in count and
  in name from the measurement taken on the clean tree at `794efac6` before this flight began
  (section 8 of the preregistration). This flight added 15 tests and no failures.
