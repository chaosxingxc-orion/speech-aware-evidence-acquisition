# Preregistration — the Earnings-22 short-form TEST re-read with the tail-silence media

**STATUS: PREREGISTERED, NOT AUTHORIZED.** One cell is specified here and it is **not flown by the
row that writes this document** (`SAEA-SN-MF-E22-TEST-TS2-MEDIA-V1`, `model-free-check`, which built
the media and nothing else). The cell is a **SECOND READ of the six ESB test calls**, a population
the 2026-09-04 owner allowance permitted to be read **once**. It needs the owner's explicit GO,
recorded in its own exposure row, before its first contact. Nothing below may be executed on the
authority of this file, and the `--dry-run` of both cells already refuses at
`contracts.gate_exposure` because no exposure row exists — which is the correct state, not a defect.

Basis, in the order it was established:

* `docs/readiness/2026-09-04-e22-esb-shortform-alignment-v1-preregistration.md` and its verdict —
  the sealed test flight `SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1` (attempt
  `attempt-20260905T044432Z-8f23ee`), **NOT ALIGNED at corpus Whisper-normalized WER 15.937**, whose
  instruction, prompt shape, decoding params, geometry, build, reference layer, scorers, harness and
  entry point this cell reuses byte for byte.
* `docs/readiness/2026-09-07-e22-short-clip-encoding-audit-v1.md` — what our serving path does to a
  short clip, proved against 6,038 sealed `prompt_tokens`.
* `docs/readiness/2026-09-07-e22-dev-encoding-probes-v1-preregistration.md` §1.2 and §4 — the
  `tail-silence-2s` cell, its rule and its falsifier.
* `docs/checks/speech-aware-evidence-acquisition/2026-09-07-e22-dev-esb-tail2s-v1/` — that cell
  flown on 1,500 dev rows: **corpus WER 9.4054** against the sealed dev comparator's 17.4012, the
  agentic error rate 1.7599 against 1.9161, and the boundary block 1.1085 WER points against 8.2778.
* `docs/checks/speech-aware-evidence-acquisition/2026-09-07-e22-test2735-tail2s-media/` — the media
  this cell would send, built model-free from the sealed test bytes.

The one-experiment-in-flight rule applies: this is queued behind whatever is flying.

---

## 0. What is being tested, and what it costs

The sealed test flight measured **15.937** against a published **9.79** and a cross-read **12.3**,
and its own gap analysis put the shape of the miss beyond doubt: **insertions are 59.2 % of all
errors**, the hypothesis is systematically longer than the reference (ratio **1.0749**), and an
oracle cut of each hypothesis to its own reference word count — a diagnostic upper bound, never an
achievable result — moved the number **5.48 points to 10.456**, inside the band and under the strict
floor. What failed there was output discipline, not acoustic recognition.

The 2026-09-07 encoding audit then found a cause of exactly that shape that the study had never
varied: **the audio the protocol delivers**. `mtmd_audio_preprocessor_qwen3a` rounds the mel
spectrogram up to whole 100-frame blocks with the literal float `0.0`, unmasked, at 13 audio tokens
per block, while the published HF `Qwen3OmniMoeProcessor` path records each block's true length and
**masks the pad away**. On **this test population** that is **17,695 of the 271,453 audio tokens we
send (6.52 %)**, computed from **136,533 mel frames = 1,365.3 s** of constant on **2,733 of 2,735
clips**; measured per clip rather than pooled, the masked-away share averages **11.53 %** and reaches
**76.92 %** on the worst clip. And the pad is not silence: it sits 0.72 units above the clamp floor
on a normalized scale whose whole span is 2.0, above 66.4 % of a clip's own real mel bins.

The `tail-silence-2s` cell replaces the out-of-distribution constant abutting the last word with
**the thing a stop actually looks like**, and on dev it moved corpus WER by **−7.9958 points** and
collapsed the boundary category mass from 8.2778 to **1.1085**.

**What it costs to ask the same question on test is a second read of six confirmatory calls.** That
is the whole price of this cell and it is stated first, before any number, so nobody has to go
looking for it.

### 0.1 What this cell CANNOT do, stated before any number exists

Appending 2.0 s adds 200 whole mel frames, so the residue `(n_samples // 160) % 100` is **unchanged**
and the zero-pad block **keeps its size**: the same 136,533 pad frames and the same 17,695
masked-away tokens are still sent, and their share of a request falls only because the request grew
— pooled 6.52 % → **5.17 %**, mean per clip 11.53 % → **6.74 %**, worst clip 76.92 % →
**25.64 %**. This cell moves the constant 2.0 s away from the last word; it does not
remove it. The `frame-exact` probe of §5 of the dev preregistration is the one that would, and it is
neither built nor authorized on either split.

---

## 1. The cell

| | |
|---|---|
| run id | `SAEA-E22-ESB-SHORTFORM-TAIL2S-TEST-V1` |
| cell | `E22-ESB-2735-TS2` |
| population | the whole published ESB Earnings22 **test** subset in its `@ts2` form: 2,735 utterances of the six calibration-exposed calls, **24,964.608437 s (6.9346 h)**, 342,563 audio tokens |
| split identity | `ecd9ab76755ce0158a64e4854a6b716114f7496635f6d02a65a3e3b2fa267335` |
| fragments | dataset `earnings22-esb-test2735-tail2s`, baseline `e22-esb-test2735-tail2s`, model `q4km-e22-esb-mmproj-gpu-04ccc72a-np8`, experiment `e22-esb-shortform-tail2s-test-v1` |
| smoke | `SAEA-E22-ESB-SHORTFORM-TAIL2S-TEST-SMOKE-V1`, cell `E22-ESB-2735-TS2-SMOKE-4`, split identity `f47de393dc03…`, 64.760188 s |

### 1.1 The media, and how it was built

Row `SAEA-SN-MF-E22-TEST-TS2-MEDIA-V1` (`model-free-check`), registered before the first byte was
written. Exactly **2.0 s = 32,000 zero samples** appended to each of the 2,735 **sealed v1 test
clips** — the same bytes the 2026-09-04 flight sent. Strictly additive: **87,520,000 samples added,
zero removed, zero clips left unchanged**, every published sample delivered unaltered and in order.

* **The rule is not re-implemented.** `scripts/build_e22_test_tail2s_media.py` imports
  `transform('tail-silence-2s', ...)` and `read_clip` from
  `scripts/build_e22_dev1500_media_variants.py`, **pinned by SHA-256
  `49e5d910…`**, so the test bytes come from the same code as the dev bytes or the build refuses.
* Every one of the 2,735 source files was **re-hashed against the committed D1 media supplement
  before it was read**, and all 2,735 matched. **No parent MP3 was opened and no decoder ran**, so
  `librosa` never ran and the pinned absence of `ffmpeg` is preserved.
* The writer was pushed twice per clip and its bytes agreed; a second whole build reproduced every
  receipt hash byte for byte.
* **Media bytes only.** `reference_sentences`, `hypothesis_text`, `scores`, `sealed_outputs` and
  `segment_table_columns` are all **0** in the build receipt. `test_split_read` is recorded **true**
  with scope MEDIA ONLY: building the media is not a model contact and is not the read of the
  evaluation surface.

| | value |
|---|---:|
| clips | 2,735 |
| audio seconds, one pass | **24,964.608437** (6.934613 h) |
| audio tokens, one pass | **342,563** |
| longest clip | `4483338-281@ts2`, **38.360125 s**, 507 tokens, 5 encoder windows |
| shortest clip | `4479741-224@ts2`, 2.2199375 s, 39 tokens |
| bytes on disk | 798,987,810, under `derived/e22-esb-utterances/test2735-tail2s-v1` |
| zero-pad frames | 136,533 — **unchanged from v1**, as §0.1 requires |

Three utterances keep the sealed flight's clamped end boundary and are named again here:
`4432298-351@ts2`, `4470290-178@ts2`, `4483338-619@ts2`.

### 1.2 Window fit, derived before any contact

On the exact front-end rule the encoding audit proved against 6,038 sealed `prompt_tokens` — 13
tokens per 100 mel frames, `n_eff = n_samples // 160 + 1` — the longest clip is **507** speech
tokens. Worst required = 507 speech + the **49-token text envelope the sealed test smoke measured
on all four of its rows** for this exact instruction + 1,024 completion + 2 special = **1,582**,
against the sealed flight's own **4,096-token slot** (`-c 32768 -np 8`): a margin of 2,514 and a
ratio of **2.59×** on this repository's `slot_tokens >= 2 × worst_required` rule. **FITS**, so the
geometry is carried forward unchanged rather than re-derived.

VRAM is not certified by arithmetic and is not claimed. This geometry served 2,735 requests at a
peak of 22,506 MiB of 24,463 on 2026-09-05; the longest request is now 507 tokens instead of 481.
The 4-row smoke proves it live before the flight launches.

---

## 2. Held fixed, byte for byte

Everything the sealed test flight declared, unchanged. Build commit
`04ccc72a2207347ca76161b93fd9d846dd0a8675`, runtime receipt
`docs/receipts/runtime-q4km-featcache-04ccc72a.json`, **Q4_K_M** decoder `0751c279…066d` and bf16
mmproj `f0dfe825…2883` **resident on the GPU**, temperature 0, seed 20260803, `max_tokens` 1024,
`id_slot` per-sample, one contact per item, no evidence, no OBS windowing,
`core.flight.FlightRuntime` with the shared rails zero-supply direct arm and the OpenJiuwen executor
through `scripts/flights/run_e22_esb_cell.py`, serving geometry **`-c 32768 -np 8`** at 4,096 tokens
per slot, the base `TaskAdapter.assemble_prompt` shape (one system message with the instruction, one
user message with the audio), and the instruction verbatim:

> Transcribe the speech verbatim exactly as spoken. Never insert, repeat, or add any word you do not
> clearly hear in the audio. Output only the transcript text.

**The audio path is `raw-audio-mmproj`**, exactly as the sealed flight used it: no
`speech_feature_parts`, no packet promotion, no feature-cache directory. A packet path would be a
second factor **and** would be encoder-invalid, because these are new bytes with no cached features.

The reference layer (`f6fddf40…`, re-verified against its committed receipt `3266c7ba…` on every
call), the scorers (`asr-wer-esb-whisper` paper-facing, `asr-wer-esb`, `cost`), the corpus
aggregation and the no-`merge_compounds` deviation are all unchanged, and scoring runs **once per
complete manifest** through `core.scoring_batch`, never sharded.

**Two identity deviations, both named in the experiment fragment.** `D-TS2-1`: the sample ids carry
the `@ts2` suffix, so the split identity hash is not the sealed population's `9285b321…` —
`reproduction.esb_reference.published_segment_key` splits on `@` for the reference lookup while the
per-sample rows keep the suffixed id for the paired join. `D-TS2-2`: the media root is the variant's
own derived directory. Neither changes a request byte other than the audio, which is the factor.

**`D-TS2-3` is not an identity deviation and is treated separately in §7: the published systems did
not append silence.**

---

## 3. The exposure statement

This cell is a **SECOND READ** of the six ESB test calls `4432298`, `4450488`, `4470290`, `4479741`,
`4483338`, `4485244`.

* The 2026-09-04 owner decision re-designated them **calibration-exposed** after **one** read, which
  `SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1` spent. `docs/receipts/splits-calibration-exposure-2026-09-04.json`
  records the re-designation and pins `docs/receipts/splits.json` without rewriting it.
* **A second read requires the owner's explicit GO, recorded in this run's own exposure row before
  the first contact.** The 2026-09-07 GO that flew the three dev encoding cells does **not** cover
  it, and §7.2 of the dev preregistration says so in its own words: applying an encoding cell to the
  six test calls "would require **re-flying** them … It may be **proposed** to the owner and can
  never be taken on this file's authority."
* The **smoke's four contacts are part of that second read** — four contacts on four already-read
  recordings are still four contacts — and get their own exposure row under the same GO.
* **One attempt.** No dev-side tuning after this read: the moment the number exists, no knob,
  prompt, geometry, scorer or media rule may be changed and re-flown on this population. At most one
  recovery re-registration, with a fresh run id and a fresh exposure row (the plan budget is metered
  cumulatively across attempts of a run id); a second failure stops the flight and the fix is proven
  on a 4-row dry run.
* **Nothing else is read.** The 109 remaining confirmatory calls are not named, loaded, decoded or
  scored, and the ESB validation six are inside those 109.
* After this read the six calls remain calibration-exposed. **This file proposes no third read**,
  and the closing rule of §7.3 says what happens instead.

---

## 4. The decision rule, fixed now, before any number exists

Let `W` be the corpus WER of `asr-wer-esb-whisper` over the 2,735 rows — total S+D+I over total
reference words, Whisper `EnglishTextNormalizer` on both sides, whitespace tokenization. **This is
the 2026-09-04 alignment rule, unchanged, applied to the same population under the media of §1.1:**

* **band test**: `W <= 12.79` (9.79 + 3.0).
* **floor test (strict)**: `W <= 11.59`, whisper-large-v3 on the same column.
* **floor test (loose)**: `W <= 15.09`, whisper-base.en, reported either way, as are the other seven
  floors.
* **ALIGNED** = band test and strict floor test both pass.
* **ALIGNED-BETTER** = `W < 6.79`.
* **NOT ALIGNED** otherwise, with the failing half named and the gap decomposed call by call and
  against D1–D5 and `D-TS2-3`.

**Reported beside it, not after it**, both against the sealed arm's own 2026-09-04 values:

* the **agentic error rate** (`analysis.e22_error_taxonomy` at its committed version: HIGH-impact
  reference-word mass over reference words); and
* the **boundary category mass** (`segmentation-artifact` + `runaway-tail` + `runaway-head`) with its
  tail/head containment buckets.

A verdict that reports `W` without those two is incomplete: on dev this factor moved the boundary
block by 7.17 points, and a corpus number that fell without the block moving would mean something
different from one that fell with it.

### 4.1 The standing rule this deviates from, quoted

The 2026-09-06 array-durations verdict made a prohibition **unconditional**, and it is quoted here
rather than paraphrased because this cell sits against it:

> A boundary-exact number therefore stays a statement about this study's sensitivity to the boundary
> trigger on its own dev split, is never an alignment argument, and is never compared to 9.79 or
> 12.3 — there is no longer any condition under which that comparison becomes legitimate.

The `tail-silence-2s` experiment fragment inherited that rule in the same words for a media-changing
cell. **Applying the alignment band to this cell is therefore a deviation from a standing rule, and
this preregistration does not lift it.** It rests on an owner decision, which must be recorded in
this run's exposure row alongside the GO, and §7 states exactly what may and may not be claimed if
it is granted. If the owner does not grant it, the cell can still be flown and the number reported
**without** the band — as a paired contrast against the sealed arm and nothing else — and §4.2's
reporting is unchanged either way.

There is one asymmetry between this cell and the boundary-exact one, and it is an argument, not a
proof: `boundary-exact` **removes** audio the published systems were handed, so its input is no
longer their input; `tail-silence-2s` **adds** digital silence after the published span and removes
nothing, so every published sample still reaches the model in order. §7 develops that and names its
limits.

### 4.2 The built-in falsifier, run before any score is read

Every flown row's `prompt_tokens` must equal
`49 + analysis.e22_short_clip_encoding.llamacpp_audio_tokens(n_samples)` for that row's variant
media. Expected totals: **476,578** for the flight (`49 × 2,735 + 342,563`) and **1,080** for the
smoke (88 / 556 / 270 / 166 on `4479741-224@ts2` / `4483338-281@ts2` / `4485244-115@ts2` /
`4485244-409@ts2`). The predicted audio-token count is recomputed from each row's own `n_samples`,
not read from the roster column, and the roster column is checked against it as well.

**A single disagreeing row means the audit's front-end model is wrong for this media, and the cell
STOPS and reports rather than being interpreted.** The same rule held on 1,500 of 1,500 dev rows,
on media two seconds longer than the bytes the audit was built from.

### 4.3 Mandatory reporting, aligned or not

The per-call table for all six calls under both normalizers; natural-mixture (corpus) and equal-call
weightings side by side; the S/D/I split, the insertion share of errors and the hypothesis-to-reference
length ratio, each beside the sealed arm's 59.2 % and 1.0749; **the utterance-duration decomposition
on the PUBLISHED span** (209 / 220 / 454 / 856 / 820 / 176 utterances in the 0–1 / 1–2 / 2–4 / 4–8 /
8–16 / 16 s+ buckets, and the **74** utterances longer than 20 s separately), which is where the
audit predicts the effect concentrates and therefore the one slice that can falsify the mechanism
even when the pooled number moves; the boundary category mass before and after with the tail/head
containment buckets; per-utterance saves, harms, ties and the exact sign test from `analysis.paired`
(10,000 replicates, stratified by source call, seed 20260903, CI90, signed as cell − sealed arm); the
three clamped utterances named; the §4.2 falsifier check; and the Earnings-21 full-44 corpus number
(8.200) beside this one with the segmentation, corpus and metric differences named rather than
compared silently.

---

## 5. The prediction, fixed in writing, from dev

Preregistered before any contact, so that the verdict cannot be a story told after the fact.

| | value |
|---|---:|
| dev1500 `tail-silence-2s`, corpus WER | **9.4054** |
| dev1500 sealed comparator (arm A), same rows | 17.4012 |
| dev delta | **−7.9958** points |
| dev ratio | **0.5405** |
| sealed TEST arm, 2026-09-04 | **15.937** |
| additive transfer point | **7.94** |
| multiplicative transfer point | **8.61** |
| **preregistered interval** | **7.5 – 10.5** |

**The transfer assumption, stated as an assumption.** Dev and test are two splits of one ESB
repartition at one revision, cut by the same slicer from the same locked MP3s, sent through the same
instruction, the same decoding params and the same build; the encoding artifact the tail addresses is
a property of the **serving path**, not of a call. The assumption is therefore that the effect
transfers **in kind**. It is explicitly **not** assumed to transfer **in size**:

* arguing for transfer in kind — the two populations are near twins in the artifact's footprint:
  mean clip **7.128 s** (test) against **6.633 s** (dev1500), pooled masked-away share **6.52 %**
  against **6.99 %**, mean per-clip share **11.53 %** against **12.00 %**, the same **76.92 %** worst
  clip, and in both cases all but two clips carry a pad. **Nothing here argues that the test
  population is *more* affected — if anything it is marginally less**, so the dev delta is not a
  lower bound;
* arguing for caution — the sealed test arm's error mass has a different shape from the dev arm's
  (59.2 % insertions and a 1.0749 length ratio, against dev's boundary-block-dominated mass), and
  **both point predictions sit below that arm's own length-oracle bound of 10.456**. That oracle cut
  every hypothesis to its own reference word count, so it is the best any purely
  length-discipline repair could do on these rows. **Any result under 10.456 therefore requires the
  tail to have fixed substitutions as well as over-generation, not just to have shortened the
  output**, and the verdict must check the S/D/I split for that rather than assume it. This is the
  single strongest reason the prediction could be too optimistic, and it is stated before the number
  exists.

**Predicted direction**: corpus WER falls; the insertion share and the length ratio fall; the effect
concentrates in the short-duration buckets; the boundary category mass falls by at least 2.0 WER
points, the clause the dev cell's own admission rule used.

**Falsifier of the transfer**: a corpus WER **above 12.79** refutes the transfer assumption outright,
and the verdict must say so in those words rather than reinterpreting the prediction. A number inside
7.5–10.5 is a confirmation. A number below 7.5, or between 10.5 and 12.79, is recorded as **the
prediction missing its interval while keeping its sign**, and the miss is reported as prominently as
the direction.

---

## 6. Budget

As the `contracts.ExecutionPlan` in the experiment fragment and as the exposure row's ceilings.

| | flight, plan | flight, ceiling | smoke, plan | smoke, ceiling |
|---|---:|---:|---:|---:|
| model calls | 2,743 | 2,800 | 20 | 50 |
| speech audio seconds | 25,000 | 25,500 | 100 | 200 |
| GPU hours | 0.60 | 1.00 | 0.25 | 0.50 |
| paid API spend | 0 | 0 | 0 | 0 |

* **Calls**: 2,735 rows × 1 contact + 8 canaries.
* **Audio seconds**: 24,964.608437 for one pass — the roster's own total, test clips plus 2.0 s each.
* **GPU hours, derived rather than guessed**: the sealed test flight served 2,735 contacts over
  19,494.608 s of audio in **0.226 GPU-h** on this exact geometry and audio path — 1.16e-5 GPU-h per
  audio second — which puts this pass at **0.290 h**. The plan carries roughly a 2× margin, the same
  margin the three dev encoding cells used, because every row pays a live mmproj encode and the
  encode cost is exactly what this cell's media changes. At the dev tail2s cell's own measured
  3.5082 contacts/s the dispatch is about 780 s.
* `core/model/adapter.py` meters `planned_model_calls` and `planned_speech_audio_seconds` **across
  all attempts of a run id**, so a recovery plan must cover prior durable spend as well as its own
  worst case.

**Not a paper-scale campaign.** Both cells are `baseline-reproduction`. No `paper-scale-confirmatory`
profile, no manuscript, no submission, no Stage-3 activity.

---

## 7. The claim rule, and the protocol difference it turns on

### 7.1 The difference, stated plainly

**The published systems did not append silence.** The 9.79 (NeMo AutoModel) and 12.3 (Open ASR
Leaderboard) rows consumed the ESB release's own audio arrays and nothing else. Every request in this
cell carries 2.0 s of digital silence after the published span. That is `D-TS2-3`, it is a **protocol
difference**, and **every statement of this number must carry it**. A sentence of the form
"Qwen3-Omni-30B-A3B-Instruct Q4_K_M scores `W` on ESB Earnings22" is false without it.

### 7.2 Why the optimization is legitimate, and where the argument stops

The argument has three steps, and the third is where it stops.

1. **It adds no information.** The tail is digital silence appended *after* the published span. No
   published sample is removed, reordered or altered; nothing about the reference, the segmentation
   or the task changes. It cannot tell the model a word.
2. **It addresses a defect of OUR path that the published path does not have.** The audit established
   that `mtmd_audio_preprocessor_qwen3a` glues up to 0.99 s of unmasked, non-silent `0.0` constant to
   the end of the clip and charges 13 audio tokens for it, where the HF `Qwen3OmniMoeProcessor`
   records each block's true length and masks it away. On this population that is 17,695 tokens —
   6.52 % of what we send pooled, 11.53 % of a clip on average — on 2,733 of 2,735 clips. So the
   difference this cell removes is a difference **between our serving stack and theirs**, not between
   our system and the task.
3. **And it does not make the two identical.** The published path masks the block; we still send it,
   two seconds later, with the clamp floor a real stop produces in between. 2.0 s of appended silence
   is also not nothing to a decoder — it is additional evidence that speech ended, which is a
   behavioural change on top of the artifact repair, and this cell cannot separate the two. **The
   honest reading is that the tail moves our input processing closer *in effect* to the published
   path's, not that it reproduces it.**

That is the whole warrant. It licenses the sentence *"under a named model-usage local optimization of
the study's own serving path, the frozen core reaches `W` on the published ESB Earnings22 test
subset, against a published 9.79 and a cross-read 12.3 that were measured without it"* — and it
licenses nothing shorter.

### 7.3 What this cell cannot conclude, and what closes

* Not that the residual is quantization, prompt or decode. **D2 (Q4_K_M against an unstated published
  precision) is untested by this cell and stays the live suspect for whatever remains.**
* Not that the tail is the last difference. The 2026-09-06 array-durations check recorded a second
  live deviation this cell does not address: the release stores **each call's native container**
  (16 kHz stereo, 22.05 kHz stereo, 24 kHz mono) while this study's clips are librosa-decoded 16 kHz
  mono from the locked MP3s. Same span, different decode, unknown sign.
* Nothing about the other 109 confirmatory calls, nothing about the ESB validation split, and nothing
  about generalization, superiority or Stage-3.
* Two vendor reports of this same frozen model differ by **2.5 points** (9.79 vs 12.3), which is most
  of the owner's 3-point tolerance; "consistent with both" stays the strongest honest reading of any
  number inside the band. The leaderboard applies `merge_compounds=True` and we do not, which works
  against us. `saea-scoring-v1` figures are a different metric family and must never be reported as
  an alignment however close they land. fstalign is not installed and was not run.
* **Whatever this cell returns, Earnings-22 test is closed afterwards.** The read is spent, no third
  read is proposed, and any further Earnings-22 work moves to dev or stops.

---

## 8. Preconditions and the ordered flight checklist

### 8.1 Already done, model-free, and landed

1. The media variant, built from the sealed test bytes by the dev builder's own pinned transform,
   each source file re-hashed on read and each written file re-hashed on write, with its frozen roster
   receipt, its flight probe view and its additive D1 media supplement. ✔
2. The window fit re-derived on the exact front-end rule: worst required 1,582 against a 4,096-token
   slot, ratio 2.59×. ✔
3. Fragments composed and **wire-checked with a fake gate and a fake transport — zero servers, zero
   sockets, zero contacts** — for both cells, both reaching `seal_and_score: OK` over the real
   registered scorers. Flight config `f84f207844ea…`, protocol `f3442e1be030…`, split identity
   `ecd9ab76755c…`, 2,735 of 2,735 contacts; smoke config `ab21243840a0…`, protocol
   `cb8f4e5e65b7…`, split identity `f47de393dc03…`, 4 of 4. Receipts:
   `docs/checks/speech-aware-evidence-acquisition/2026-09-07-e22-test-tail2s-wire-check/`. ✔
4. The `--dry-run` of both cells run against the REAL gate, which passes config composition, roster
   hydration with a per-file SHA-256 re-hash of all 2,735 media, media-path confinement, the count
   check, `ExecutionPlan` construction and profile validation, and then **correctly refuses at
   `contracts.gate_exposure`** because no exposure row exists. ✔

### 8.2 In order, and never two at once

1. **Owner GO for this cell.** This file grants none. The GO has two parts and both must be recorded:
   permission for a **second read** of the six calls (§3), and the decision on whether the **alignment
   band** may be applied to a media-changed cell (§4.1). The second may be refused while the first is
   granted; §4.1 says what the verdict looks like then.
2. Register the smoke's exposure row and the flight's exposure row **before the first contact**, each
   naming the population, its split identity hash, the sealed comparator attempt, the §6 budget, the
   §4 rule, the §5 prediction and the §7 claim rule.
3. **Serving.** This cell's geometry is `-c 32768 -np 8`, which is **not** the resident E22 dev
   session's `-c 40960 -np 8`. Under the always-on serving note the coordinator owns the session, so:
   attach if a resident session **at this geometry** is up; otherwise ask the coordinator to switch
   the geometry for this cell and attach to that. **Attaching to a `-c 40960` session would change the
   serving geometry away from the sealed comparator's and must not be done silently** — it would be a
   named deviation, recorded in the exposure row before takeoff and carried in the verdict, and this
   file's default is not to take it. The agent never starts, stops or kills a server. Front-load the
   model load as a background step; the media are already built, so CPU preprocessing is nil.
4. Fly the **4-row smoke** first, with its own run id and its own exposure row, and read its three
   answers: the §4.2 falsifier on 4 of 4 rows, this media's worst encode (38.360125 s, 507 tokens,
   five encoder windows) completing live with no CUDA fault and no out-of-memory, and both ESB
   scorers returning per-sample rows through `core.scoring_batch` with `verified = true`. Any one
   negative stops the flight.
5. Fly **one attempt**, 2,735 contacts, one serving geometry, no repair, no retry, no resend.
6. Score **once**, over the complete manifest, through `core.scoring_batch` with
   `--include-per-sample`, never sharded.
7. Run the **§4.2 falsifier before reading any score**.
8. Run `analysis.e22_error_taxonomy` at its committed version on the new outputs and report the
   boundary mass and the agentic rate before and after.
9. Run `analysis.paired` against the sealed `SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1` outputs, paired per
   published segment on the key recovered by splitting the variant id on `@`.
10. Write the verdict
    `docs/readiness/2026-09-07-e22-esb-shortform-tail2s-test-v1-verdict.md` with §4.3's slices, the
    §4 rule and the §7 claim rule quoted verbatim, and the §5 prediction scored against what happened.
11. Close every exposure row COMPLETED with hashes, and append a note to
    `docs/readiness/2026-09-04-scoring-alignment-audit-slurp-earnings.md`.
12. **Stop.** §7.3 applies.

### 8.3 Invariants

`pytest` green apart from the documented pre-existing failures;
`python scripts/checks/engineering_base_check.py` passes; the tree clean and committed before the
wire check, before the smoke and before the flight, and until finalize; `PYTHONDONTWRITEBYTECODE=1`;
no `pip install`, no venv change, no rebuild or checkout of `/home/chao/llama.cpp-featcache`
(detached at `04ccc72a`), no ffmpeg, no fstalign; **no read of any confirmatory call other than the
six**; references never enter the request path; `FrozenCoreGate` decides legality and causes get
fixed, not gates.

---

## 9. Not authorized by this file

No model contact, no server, no flight, no request. No second read of the six ESB test calls. No read
of any of the other 109 confirmatory calls. No ESB validation-split read. No mechanism arm. No knob
tuned on this population, before or after. No fourth prompt, no few-shot, no post-processing of any
hypothesis, no re-scoring of any sealed arm, no `merge_compounds`. No packet or feature-cache path.
No Q8_0 composition. No `frame-exact` or `pad-30s` variant on test. No third read, ever, on this
file's authority. No lifting of the 2026-09-06 unconditional comparison prohibition — only an owner
decision can do that. No `paper-scale-confirmatory` profile, no manuscript, no submission, no Stage-3
activity.

---

## Phase log

### 2026-09-07, Phase 1 — media, fragments, wire check, registration

Exposure row `SAEA-SN-MF-E22-TEST-TS2-MEDIA-V1` registered before the first byte was written
(`df1388db`). Media built (`b085ae11`): 2,735 clips, 24,964.608437 s, 342,563 audio tokens,
798,987,810 bytes, +87,520,000 samples and zero removed, split identity `ecd9ab76…`; all 2,735 source
digests matched, no MP3 opened, no decoder run, and a second whole build reproduced every receipt
hash. Fragments composed (`42da8bb4`), wire-checked (`0726f530`), then corrected (`599c7b0a`) and
wire-checked again: both split identity hashes reproduced live — flight `ecd9ab76…`, smoke
`f47de393…` — both cells `seal_and_score: OK`, zero model contacts, zero servers, zero sockets. This
preregistration written last, with the prediction of §5 fixed from the dev cell's sealed numbers and
before any test contact exists.

**One defect of my own, disclosed rather than quietly fixed.** The first pass of the fragments, and
the commit message of `b085ae11`, priced the encoder's zero-pad block as 13 whole tokens per padded
clip — 35,529 tokens, a 13.09 % share — which is not the accounting the encoding audit uses. The
audit prices it as `extra_tokens = llamacpp_tokens − hf_tokens`, the tokens our path sends that the
published path masks away, and recomputed with `analysis.e22_short_clip_encoding.summarize` the
correct figure is **17,695 tokens, 6.52 % pooled and 11.53 % of a clip on average**. The same pass
also claimed the test clips are "much shorter (mean 7.13 s against dev's 26.2 s)"; the dev1500 mean is
6.633 s, so they are marginally **longer**, and the pooled masked-away share is 6.52 % against dev's
6.99 %. **The claim that the test population is more affected than dev — and therefore that the dev
delta is a lower bound — is withdrawn**, and §5 now says the opposite. Every figure in this document
is the corrected one; the superseded numbers are named here so a reader of `b085ae11`'s message is
not left with them. Correcting the fragments moved the flight cell's composed identity, so the wire
check was re-run rather than left stale, which is why §8.1 carries `f84f2078…` and not the
`abf5cf1d…` of the first pass.
