# Preregistration — the three Earnings-22 short-clip encoding probe cells

**STATUS: PREREGISTERED, NOT AUTHORIZED.** Three cells are specified here and **none is flown by
the rows that write this document** (`SAEA-E22-MF-SHORT-CLIP-ENCODING-AUDIT-V1` and
`SAEA-SN-MF-E22-DEV1500-ENCODING-VARIANTS-V1`, both `model-free-check`). Each needs its own owner
decision and its own exposure row registered before its first contact. Nothing below may be executed
on the authority of this file, and the `--dry-run` of every cell already refuses at
`contracts.gate_exposure` because no exposure row exists — which is the correct state, not a defect.

Basis: `docs/readiness/2026-09-07-e22-short-clip-encoding-audit-v1.md` (what our path does to a
short clip, measured and proved against 6,038 sealed `prompt_tokens`),
`docs/readiness/2026-09-06-e22-clip-boundary-audit-v1.md` (the published segmentation overlaps),
`docs/readiness/2026-09-06-e22-semantic-error-scan-v1.md` (the error mass, categorised) and
`docs/readiness/2026-09-06-e22-dev-usage-cells-v1-verdict.md` (the comparator's numbers and the
same-request null). The one-experiment-in-flight rule applies: these are queued behind whatever is
flying, and they fly one at a time.

---

## 0. What is being tested, and what has already been excluded

Six explanations of the Earnings-22 short-form gap have been measured and closed: the instruction
text (0.83 points the wrong way), the request shape (0.325 the wrong way), the comparability of the
clip boundary (zero — the ESB release ships the same overlap), a scoring-convention fold (≤ 0.35,
unlicensed), the decoder quantization (0.4305, ADMITTED) and the decode discipline (0.1409, NOT
ADMITTED, half of it jitter). **Nearly half of arm A's error mass — 8.2778 of 17.4012 corpus-WER
points on these 1,500 rows — is the boundary block, and no model-usage knob has moved more than
2.2 % of it.**

The 2026-09-07 encoding audit found one thing the study had never varied: **the audio the protocol
delivers.** `mtmd_audio_preprocessor_qwen3a` keeps one more mel frame than the published path and
rounds the mel spectrogram up to a whole number of 100-frame blocks with the literal float `0.0`,
unmasked, at 13 audio tokens per block. On these 1,500 rows that is **9,740 of 139,282 audio tokens
(6.99 %) computed from 753.3 s of padding on 1,498 of 1,500 clips**, and the share is **42.2 % on
sub-second clips against 2.5 % at 16 s and above** — the same ordering as arm A's WER by duration.
The pad is not silence: `0.0` sits 0.72 units above the clamp floor that appended digital silence
produces (median −0.7152 normalized, span 2.0) and above 66.4 % of a clip's own real mel bins.

**The audit also answered one half of the hypothesis NO.** There is no fixed 30-second window and
no short-audio inflation on our path; both belong to the whisper preprocessor Qwen3-Omni does not
select. That is why `pad-30s` is a cell rather than a repair: it supplies at the wire what the
runtime does not supply internally.

Three cells follow. Each varies the media by one rule and holds everything else byte-identical.

---

## 1. The three cells

The media are **already built and hash-pinned** by
`SAEA-SN-MF-E22-DEV1500-ENCODING-VARIANTS-V1` (receipts:
`docs/checks/speech-aware-evidence-acquisition/2026-09-07-e22-dev1500-encoding-variants/<variant>/`),
from the **sealed `dev-v1` WAV bytes** — every source file re-hashed against the committed D1 media
supplement before it was read, no parent MP3 opened, no decoder run, so librosa never ran and the
pinned absence of ffmpeg is preserved.

| | cell 1 | cell 2 | cell 3 |
|---|---|---|---|
| run id | `SAEA-E22-DEV-ESB-BX-V1` | `SAEA-E22-DEV-ESB-TAIL2S-V1` | `SAEA-E22-DEV-ESB-PAD30S-V1` |
| variant | `boundary-exact` | `tail-silence-2s` | `pad-30s` |
| id suffix | `@bx1` | `@ts2` | `@p30` |
| media root | `derived/e22-esb-utterances/dev1500-bx-v1` | `.../dev1500-tail2s-v1` | `.../dev1500-pad30s-v1` |
| split identity | `87d0cc65…` | `8dc9d6a0…` | `2c13bf01…` |
| the factor | the clip boundary: midpoint of the overlap | the acoustic tail: +2.0 s of digital silence | the acoustic tail at 30.0 s |
| audio seconds | **9,783.571** (−165.412) | **12,948.983** (+3,000.000) | **45,002.880** (+35,053.897) |
| audio tokens | 137,163 | 178,282 | **604,526 (4.34×)** |
| bytes on disk | 313,140,278 | 414,433,456 | 1,440,158,160 |
| longest clip | 32.800063 s / 429 tokens | 34.880000 s / 455 tokens | 32.880000 s / 429 tokens |
| samples added / removed | 0 / 2,646,589 | 48,000,000 / 0 | 560,862,352 / 0 |
| clips unchanged | 0 | 0 | **1** (already past 30.0 s) |

### 1.1 Cell 1 — `boundary-exact`: does the OVERLAP carry the mass?

The midpoint-of-overlap re-cut of §1.1 of
`docs/readiness/2026-09-06-e22-dev-boundary-exact-v1-preregistration.md`, restricted to these 1,500
rows. Because that rule is strictly subtractive, the clip is a **sample-exact slice of the sealed
`dev-v1` clip** rather than a second decode. The build re-derived the geometry over all 6,038 dev10
segments and reproduced the 2026-09-06 audit exactly: **4,681 overlapping adjacent pairs before, 0
after, 0 positive gaps closed.**

This is that preregistration's cell 1, executed on the 1,500-row subset rather than the full 6,038
(the subset is the population every other 2026-09-06/07 cell is paired on, it is far above the
owner's n ≥ 400 floor, and it keeps all ten call strata at 150). **It inherits that
preregistration's honest prior in full**: 668.7 s of duplicated audio at 2.632 reference words per
second is at most ≈ 1,760 words against 7,318 tail insertion words, so most of the block is
continuation the overlap *triggers* rather than speech it *delivers*, and nobody should expect a
re-cut to return the whole 8.2778.

**The media root is `dev1500-bx-v1`, NOT the `dev-bx-v1` root that preregistration reserved for a
full 6,038-row build.** The `@bx1` id suffix is kept verbatim so a later full build shares the
identity convention.

### 1.2 Cell 2 — `tail-silence-2s`: is it the discontinuity?

Exactly 2.0 s (32,000 zero samples) appended. The audit measured, on these exact clips through the
published path's own kernel, that appended digital silence lands on the clamp floor while the
encoder's pad is `0.0`. This cell therefore replaces an out-of-distribution constant abutting the
last word with **the thing a stop actually looks like**.

**What it does NOT do, stated so no verdict can overclaim it.** Appending 200 whole mel frames
leaves the residue `(n_samples // 160) % 100` unchanged, so the zero-pad block keeps its size (the
same 9,740 tokens over the population) and merely stops abutting the speech. The pad's *share* of a
clip's tokens falls from 12.00 % to 6.99 %, and its *position* moves 2.0 s away. This cell separates
"the model completes speech that was cut mid-signal" from "the model is confused by 13 tokens of
constant"; it does not remove the constant. §5 names the probe that would.

### 1.3 Cell 3 — `pad-30s`: does the 30-second convention matter?

Digital silence appended up to exactly 30.0 s. **No clip is truncated**; the single clip already
past 30.0 s (`4482383-188`, 32.88 s) is byte-identical to its `dev-v1` twin and is counted in the
receipt. The audit established that our runtime applies no fixed 30-second window, so this cell
supplies at the wire what the runtime does not supply internally, and pushes the pad block about
30 s from the last word (its share falls to 3.2 %).

**It is the expensive one and that is a property of the design, not an accident**: 45,002.880 s of
audio and 604,526 audio tokens, 4.34× the comparator's, hence 4× the GPU budget of the other two.

---

## 2. Held fixed, byte for byte

Everything the sealed comparator declared, unchanged. Build commit
`04ccc72a2207347ca76161b93fd9d846dd0a8675`, runtime receipt
`docs/receipts/runtime-q4km-featcache-04ccc72a.json`, **Q4_K_M** (not the admitted Q8_0 — see
§7.3), the pinned decoder and mmproj digests, temperature 0, seed 20260803, `max_tokens` 1024, one
contact per item, no evidence, no OBS windowing, `core.flight.FlightRuntime` with the shared rails
zero-supply direct arm and the OpenJiuwen executor through `scripts/flights/run_e22_esb_cell.py`,
the base `TaskAdapter.assemble_prompt` shape (one system message with the instruction, one user
message with the audio), serving geometry `-c 40960 -np 8` at 5,120 tokens per slot from the
comparator's own model fragment `q4km-e22-dev-esb-mmproj-gpu-04ccc72a-np8-c40960`, and **arm A's
instruction verbatim**:

> Transcribe the speech verbatim exactly as spoken. Never insert, repeat, or add any word you do
> not clearly hear in the audio. Output only the transcript text.

**The audio path is `raw-audio-mmproj`**, exactly as the sealed dev arms used it: no
`speech_feature_parts`, no packet promotion, no feature-cache directory. A packet path would be a
second factor **and** would be encoder-invalid, because these are new bytes with no cached features.

The reference layer, the scorers (`asr-wer-esb-whisper` paper-facing, `asr-wer-esb`, `cost`), the
corpus aggregation and the no-`merge_compounds` deviation are all unchanged, and scoring runs once
per complete manifest through `core.scoring_batch`, never sharded.

**Two named deviations, both identity rather than protocol.** `D-ENC-1`: the sample ids carry a
variant suffix, so the split identity hash is not the comparator's — the convention §1.4 of the
2026-09-06 preregistration fixed, and `reproduction.esb_reference.published_segment_key` splits on
`@` for the reference lookup while the per-sample rows keep the suffixed id for the paired join.
`D-ENC-2`: the media root is the variant's own derived directory. Neither changes a request byte
other than the audio, which is the factor.

---

## 3. The comparator and the statistics

**Comparator:** the sealed `SAEA-E22-DEV-ESB-PROMPT-A-V1` (attempt `attempt-20260905T073641Z-f977d1`),
restricted to the 1,500 drawn published segments, **paired per published segment** on the key
recovered by splitting the variant id on `@`. No new arm A is flown: greedy decoding is not bitwise
reproducible across batch compositions on this runtime, so the comparison is against sealed outputs.

**Arm A on these rows** (2026-09-06 usage-cells verdict §1 and §4.5): corpus WER **17.4012**,
agentic error rate **1.9161**, boundary block **8.2778** WER points (924 `segmentation-artifact` +
1,179 `runaway-tail` + 70 `runaway-head` = 2,173 operations), 26,251 reference words.

**Statistics:** `analysis.paired`, 10,000 replicates, stratified by source call (10 strata), seed
20260903, CI90. Pooled ratios (corpus WER, the agentic rate, the boundary mass) go through
`resampled_statistic`, which gets the identical draws; per-utterance saves/harms/ties and the exact
sign test go through `paired_contrast`. Everything is signed as **cell − arm A**.

**The same-request null is the reference spread and it is binding.** The 2026-09-06 verdict measured
it on 1,432 rows whose request differed from arm A's only by an inert integer: **−0.0844 corpus-WER
points, CI90 [−0.2356, +0.0692]**, with 302 of 1,432 rows emitting different bytes. That is this
runtime's own cross-run noise on this population and every contrast below sits on top of it.

---

## 4. The decision rule, fixed now, before any number exists

**ADMITTED** as a model-usage local optimization **iff all three clauses hold**:

1. **Corpus WER, and it must beat the null.** The CI90 upper bound on the delta is **< −0.2356** —
   below zero *and* disjoint from the same-request null's interval [−0.2356, +0.0692]. Stating it as
   disjointness is deliberate: a point estimate near −0.10 with an interval straddling the null is
   exactly what the runtime produces when nothing changed.
2. **The agentic error rate does not worsen.** Its point estimate is ≤ arm A's **and** the CI90 upper
   bound on its delta is below **+0.05 points** — the non-inferiority margin inherited verbatim from
   §1.6 of the 2026-09-06 boundary-exact preregistration.
3. **The boundary block moves.** `segmentation-artifact` + `runaway-tail` + `runaway-head`, recomputed
   by `analysis.e22_error_taxonomy` at its committed version, falls by **at least 2.0 WER points**
   from arm A's 8.2778. Fixed here for a stated reason: no model-usage knob has moved more than
   2.2 % of that block, so a mechanism claim on the encoding needs a visible fraction of the block
   and not a corpus-WER wobble that could be jitter wearing a category label.

A cell that clears 1 and 2 but not 3 is **NOT ADMITTED and is reported as a corpus-WER effect
without a mechanism** — the honest reading, and the one the 2026-09-06 cell (a) verdict already
demonstrated on named entities.

### 4.1 A built-in falsifier the flight must check

The audit predicts every row's audio-token count exactly. **`prompt_tokens` for each flown row must
equal 49 + `analysis.e22_short_clip_encoding.llamacpp_audio_tokens(n_samples)` for that row's variant
media.** If a single row disagrees, the front-end model in the audit is wrong for this media and the
cell **stops and reports** rather than being interpreted. Expected totals: 49 × 1,500 + 137,163 /
178,282 / 604,526 for cells 1 / 2 / 3.

### 4.2 Mandatory reporting, admitted or not

The per-call table for all ten calls under both normalizers; natural-mixture and equal-call
weightings side by side; the S/D/I split and the hypothesis-to-reference length ratio; **the
utterance-duration decomposition**, which is where the audit predicts the effect concentrates and
therefore the one slice that can falsify the mechanism even when the pooled number moves; the
boundary category mass before and after with the tail/head containment buckets; per-utterance saves,
harms, ties and the exact sign test; the measured `prompt_tokens` check of §4.1; and, for cell 1,
the **five re-cut clips that fall under 0.15 s** named — `4469088-522@bx1` (0.120000 s),
`4479944-293@bx1` (0.120063), `4481952-268@bx1` (0.139938), `4469088-654@bx1` (0.139875) and
`4481952-330@bx1` (0.140000) — beside the 1,403 of 1,500 clips that lose audio at a mean of
0.110275 s and a maximum of 0.180188 s.

---

## 5. The probe this preregistration does NOT contain, named so it is not forgotten

**All three variants leave the zero-pad block's SIZE untouched.** Appending 2.0 s adds 200 whole mel
frames and padding to 30.0 s sets the residue to 0; in both cases the last block still carries
99 − r frames of `0.0`, and the re-cut only changes which frames precede it.

A **`frame-exact`** variant — pad each clip with digital silence until `n_samples // 160 + 1` is a
multiple of 100, which costs at most 0.99 s per clip and removes the padded block entirely — is the
only cheap intervention that eliminates the constant rather than moving it. It would separate *the
encoder sees a discontinuity* from *the encoder spends 13 tokens on nothing*. It is **not built and
not preregistered as a cell here**: it needs its own owner decision, and it is deliberately queued
behind cell 2, whose result determines whether it is worth a GPU at all.

---

## 6. Preconditions and the ordered flight checklist

### 6.1 Already done, model-free, and landed

1. The three media variants, built from sealed bytes, each re-hashed on write, with per-variant
   roster receipts, flight probe views and D1 media supplements. ✔
2. The `boundary-exact` geometry properties asserted, not assumed: 0 overlapping pairs after, 0
   positive gaps closed, 0 samples added. ✔
3. The window fit re-derived on the exact front-end rule for all three: worst required 1,504 /
   1,530 / 1,504 tokens against a 5,120-token slot, a ratio of 3.40× / 3.35× / 3.40× on this
   repository's `slot_tokens >= 2 × worst` rule. ✔
4. Fragments composed and **wire-checked with a fake gate and a fake transport — zero servers, zero
   sockets, zero contacts** — for all six cells (three flights and three smokes). ✔
5. The `--dry-run` of every cell run against the REAL gate, which passes config composition, roster
   hydration with a per-file SHA-256 re-hash of all 1,500 media, media-path confinement, the count
   check, `ExecutionPlan` construction and profile validation, and then **correctly refuses at
   `contracts.gate_exposure`** because no exposure row exists for these run ids. ✔

### 6.2 Per cell, in order, one at a time

**Order: cell 1 (`boundary-exact`), then cell 2 (`tail-silence-2s`), then cell 3 (`pad-30s`).**
Cell 1 is first because it is the cheapest, it is already owner-visible as cell 1 of the 2026-09-06
preregistration, and it removes the *delivered* trigger — which changes how the other two are read,
since an encoding effect measured on top of an uncorrected overlap is measured on a different
residual. Cell 3 is last because it is 4× the cost and its own mechanism (a fixed 30-second window)
was already ruled out on our path.

For each cell, and never two at once:

1. **Owner GO for that cell.** This file grants none.
2. Register the exposure row **before the first contact**, naming the population, its split identity
   hash, the comparator attempt, the budget of §7 and the claim rule of §4.
3. Front-load the model load as a background step; the media are already built, so CPU preprocessing
   is nil.
4. Fly the **4-row smoke** first (`e22-dev-encoding-<variant>-smoke4-v1`, its own run id and its own
   exposure row), which puts this variant's worst encode through the live geometry before 1,500
   contacts are spent.
5. Fly one attempt, 1,500 contacts, one serving geometry, no repair, no retry, no resend. At most
   one recovery re-registration; a second failure stops the flight and the fix is proven on a 4-row
   dry run.
6. Score once, over the complete manifest, through `core.scoring_batch`.
7. Run the §4.1 `prompt_tokens` falsifier before reading any score.
8. Run `analysis.e22_error_taxonomy` at its committed version on the new outputs and report the
   boundary mass before and after.
9. Write the verdict with the per-stratum table and the claim rule quoted verbatim.
10. **Stop.** The next cell needs its own owner GO.

### 6.3 Housekeeping

The three media roots hold 2.17 GB, 1.4 GB of it `pad-30s` silence. They may be deleted once their
cell's outputs are sealed and scored; the receipts and supplements are what make the population
reconstructible, and the builder is deterministic.

---

## 7. Budgets

Per cell, as the `contracts.ExecutionPlan` in the experiment fragment and as the exposure row's
ceilings. Derived rather than guessed: the sealed comparator ran 6,038 contacts over 39,292.647 s of
audio in **0.4515 GPU-h** at 1.927 s mean latency and 3.744 contacts/s on eight slots — **1.149e-5
GPU-h per audio second** on this exact geometry and audio path.

| | cell 1 `bx` | cell 2 `tail2s` | cell 3 `pad30s` |
|---|---:|---:|---:|
| model calls, planned / ceiling | 1,508 / 1,600 | 1,508 / 1,600 | 1,508 / 1,600 |
| speech audio seconds, planned / ceiling | 9,800 / 10,200 | 13,000 / 13,500 | 45,100 / 46,000 |
| audio seconds actually needed | 9,783.571 | 12,948.983 | 45,002.880 |
| GPU hours at the measured rate | 0.112 | 0.149 | 0.517 |
| **GPU hours, planned / ceiling** | **0.25 / 0.40** | **0.30 / 0.50** | **1.20 / 2.00** |
| paid API spend | 0 / 0 | 0 / 0 | 0 / 0 |

Planned calls = 1,500 rows × 1 contact + 8 canaries. The GPU plans carry roughly a 2× margin on the
measured rate because every row pays a live mmproj encode and the encode cost is exactly what these
cells change. Each smoke is a separate run id with its own plan (20 calls, 0.25 GPU-h).

**All three together: 4,524 contacts, 67,835.4 s (18.84 h) of audio, 1.75 planned GPU-hours (2.90
at the ceilings).** The plan budget is metered cumulatively across every attempt of a run id, so a
recovery plan must cover prior durable spend as well as its own worst case.

### 7.1 Not a paper-scale campaign

Every cell is `baseline-reproduction`, on dev, at 1,500 rows. No `paper-scale-confirmatory` profile,
no manuscript, no submission, no Stage-3 activity.

### 7.2 No test read

None of these is a scorer-side change — they change the audio — so applying any of them to the six
calibration-exposed ESB test calls would require **re-flying them**, a second read of a population
the 2026-09-04 owner allowance permitted once. It may be **proposed** to the owner and can never be
taken on this file's authority.

### 7.3 Why Q4_K_M and not the admitted Q8_0

Cell (a) of 2026-09-06 admitted Q8_0 on this population, and these cells still serve Q4_K_M. Two
reasons, both stated before the numbers exist: the comparator is a Q4_K_M arm and a paired contrast
must not move two factors at once; and Q8_0 costs about 7.9× the per-call latency, which would turn
1.75 planned GPU-hours into roughly 14. If a cell is admitted, composing it with Q8_0 is a separate
cell with its own owner decision, and the two effects were never shown to compose.

---

## 8. The closing rule (owner, 2026-09-07)

**If none of the three cells moves the boundary category mass — that is, if no cell's boundary block
falls by at least the 2.0 points of clause 3 — Earnings-22 short-form is DROPPED from this work's
scope**, and the recorded reason is the encoding audit's own finding:

> Our serving path's short-clip encoding differs from the published path by one mel frame and by up
> to 0.99 s of unmasked, non-silent constant worth up to 13 audio tokens per clip — 6.99 % of what we
> send on these rows and 42.2 % on sub-second clips — and correcting the acoustic tail, the clip
> boundary and the input length in three single-factor cells did not move the boundary block that
> carries 47.6 % of the arm's error. The residual is therefore not in the serving path this study
> controls, and Earnings-22 short-form stops being a carrier for this work's claims.

Three things survive that closure and must be carried forward rather than discarded: the encoding
audit itself (a reusable, proved account of the front end, and a corrected speech-token rule); the
same-request null, which binds every future Earnings contrast; and the `frame-exact` probe of §5,
which stays available as a named, unbuilt follow-on if the owner wants one more attempt before the
carrier closes.

**If a cell IS admitted**, the closing rule does not fire and the next step is a replication on the
same roster before any further mechanism is admitted — the owner's iteration rule of 2026-09-03, and
the §3.2 sizing requirement of the 2026-09-06 verdict, both apply.

---

## 9. Not authorized by this file

No model contact, no server, no flight, no request. No mechanism arm. No knob tuned on the test
split. No fourth prompt. No few-shot. No post-processing of any hypothesis. No re-scoring of any
sealed arm. No `merge_compounds`. No packet or feature-cache path. No Q8_0 composition. No second
read of the six calibration-exposed ESB test calls. No read of any confirmatory call. No new media
root beyond the three already built. No `paper-scale-confirmatory` profile, no manuscript, no
submission, no Stage-3 activity.
