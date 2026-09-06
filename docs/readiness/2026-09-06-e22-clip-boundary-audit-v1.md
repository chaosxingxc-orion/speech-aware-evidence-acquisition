# Earnings-22 DEV clip-boundary audit — verdict

**THE CLIPS OVERLAP. This study's slicer adds ZERO padding — it cuts the parent PCM at the
published `start_ts`/`end_ts` verbatim — and 4,681 of the 6,028 adjacent dev segment pairs
(77.7 %) still overlap, by up to 0.1804 s and never by more than that. 668.7 seconds of dev
audio is delivered twice, once at the tail of one clip and once at the head of the next.**
Crossing that geometry with the 2026-09-06 semantic scan's own boundary rule: **838 of arm A's
868 tail bleed spans at ≥ 0.6 containment (96.5 %) and 7,318 of its 7,704 tail insertion words
(95.0 %) sit on clips whose published timestamps overlap their next neighbour** — 8.04× the
per-clip rate of tight clips. The frame energy agrees with the timestamps: **94.0 % of
overlapping clips end mid-speech against 51.2 % of tight ones**, and the median overlap zone is
62.5 % active.

**But the overlap cannot carry the words. 668.7 s at this corpus's own 2.632 reference words per
second is at most ≈ 1,760 words, against 7,318 tail insertion words on the same clips.** So the
cut delivers at most about a quarter of the boundary mass and **triggers** the rest: the model
is handed the onset of the next sentence, finishes that word, and keeps going. That is one
mechanism with two halves, and separating them needs the re-cut, not more reading.

Row `SAEA-E22-MF-CLIP-BOUNDARY-AUDIT-V1` (`model-free-check`), registered before the first
segment timestamp or clip sample was read. **Zero model, tokenizer, embedder, retriever, scorer,
network and GPU contacts; zero audio seconds delivered to any service**, and the offline guard
recorded zero outbound connection attempts. 6,038 local PCM reads (1,257,630,368 bytes), every
one re-hashed against the committed D1 media supplement before its energies were taken.
Receipts: `docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-clip-boundary-audit/`
(`summary.json` sha256 `9b3c0a97…`, `per-clip-table.csv` `ab037d1c…`). Module
`analysis/e22_clip_boundary.py`, runner `scripts/run_e22_clip_boundary_audit.py`, tests
`tests/unit/test_e22_clip_boundary.py` (20, on synthetic segments).

**Population: DEV ONLY.** The 6,038 ESB train-split utterances of the ten registered
Earnings-22 dev subset10 calls, and the three sealed 2026-09-05 arms over them. **The six ESB
test calls were not opened**: no test reference, output, segment row or derived clip is read,
named as an input, or reachable from the runner, and `test_split_read` is `false` in the
receipt.

## 1. How the clips were cut

Four layers, each pinned, each checked rather than asserted.

| layer | artifact | identity |
|---|---|---|
| published boundaries | `sanchit-gandhi/earnings22_split`, split `train`, revision `f9fb35f4134e32b9c8100199d949398fd6d08a5f` | six metadata columns read through a pyarrow **column projection**; the parquet's `audio` column is never materialized |
| extracted table | `$SPEECHRL_DATA_DIR/derived/e22-esb-segment-table/segments-dev10.jsonl`, 6,038 rows | sha256 `51257011…`, re-hashed on every load against `docs/checks/speech-aware-evidence-acquisition/2026-09-05-e22-dev-esb-prompt-ab-v1/segment-table/segment-table-receipt.json` (`2ff3aa88…`) |
| the cut | `scripts/build_e22_esb_utterance_roster.py::_cut_one_call` | `pcm[max(0, round(start_ts × 16000)) : min(frames, round(end_ts × 16000))]` |
| the clips | `$SPEECHRL_DATA_DIR/derived/e22-esb-utterances/dev-v1/<call>/<id>.wav` | roster receipt `…/roster/flight-roster-receipt.json`, `items_sha256` `37e45e51…`, `ids_sha256` `dfa2ec01…`; D1 media supplement `docs/receipts/artifacts/d1-e22-esb-dev10-utterances.json` |

**The source of `start_ts` / `end_ts` is the ESB release's own segment table, not Rev's raw
timestamps and not this study's forced alignment.** This study owns no aligner output for
Earnings-22, ran none, and reads the two float32 columns of the published repartition verbatim.
The receipt already records the consequence: the columns are float32, so a boundary carries
about 1e-4 s of representation error, and the cut is made at the float32 value rather than at a
re-rounded one.

**There is no padding, no buffer and no context window.** `_cut_one_call` imports exactly two
things — `reproduction.obs_loop.decode_parent_pcm` and `reproduction.obs_audio.write_wav_bytes`
— and slices the array between two rounded sample indices. The `buf90` convention **did not
leak**: `obs_buffer_seconds`, `boundary_mode` and the whole advancing-window machinery live in
`reproduction.obs_loop`'s Earnings-21 long-form OBS loop and in `reproduction/ojw/`, and the
short-form slicer never enters any of them. The measurement confirms the reading of the code:
**media duration equals `end_ts − start_ts` on 6,037 of 6,038 clips**, and the single exception
is `4481952-631`, the last utterance of its call, whose `end_ts` runs 0.0799 s past the decoded
parent and is clamped to it. Zero clips carry an unexplained duration drift.

**The decoder is librosa, and it must stay librosa.** `decode_parent_pcm` prefers `ffmpeg`,
finds none — ffmpeg is absent by design and its absence is pinned — and falls through to
`librosa.load(sr=16000, mono=True)` followed by `clip(rint(x × 32767), −32768, 32767)` to int16.
The writer is the stdlib `wave` writer with a 44-byte header. Installing ffmpeg would move every
byte of every clip and cold every downstream hash.

**The ESB release's own per-utterance audio was available and was deliberately not used.** The
pinned parquet schema is `source_id, audio:struct<bytes,path>, segment_id, sentence, start_ts,
end_ts, id`: the release carries the audio arrays the published evaluations consume. This study
cut its own clips from the locked `earnings22-original` MP3s instead, because those are the bytes
D1 closed over. **Whether the released arrays are cut at exactly these `start_ts`/`end_ts` — and
therefore whether the published systems also received the overlap — is UNVERIFIED and is the
single most useful cheap check this audit could not make.** The four ESB *test* shards are on
disk (1.10 GB, `derived/e22-esb-segment-table/parquet/`) and would answer it by array length
alone, but they are the test population; the 55 train shards that hold the dev10 rows were never
downloaded, only column-projected over the network.

## 2. The overlap, measured

One entry per adjacent pair, so 6,028 of them over ten calls.

| | pairs | share |
|---|---:|---:|
| **overlapping** (`start_{n+1}` < `end_n`) | **4,681** | **77.7 %** |
| touching exactly | 23 | 0.4 % |
| separated | 1,324 | 22.0 % |

| statistic | seconds |
|---|---:|
| minimum (largest overlap) | **−0.18042** |
| p1 / p5 | −0.180176 / −0.179993 |
| p25 / median / p75 | −0.160004 / **−0.140015** / −0.060303 |
| p95 / p99 / max | 1.319981 / 2.954622 / 14.73999 |
| total duplicated audio | **668.726** |

| gap bucket (s) | pairs |
|---|---:|
| ≤ −0.18 | 291 |
| (−0.18, −0.16] | 1,313 |
| (−0.16, −0.12] | 2,320 |
| (−0.12, −0.08] | 566 |
| (−0.08, −0.04] | 126 |
| (−0.04, 0.00] (includes the 23 exact zeros) | 88 |
| (0.00, 0.25] | 251 |
| (0.25, 1.00] | 605 |
| (1.00, 4.00] | 439 |
| > 4.00 | 29 |

**The hard cap is the finding.** No pair overlaps by more than 0.1804 s, and 1,604 pairs sit
within 0.0005 s of that cap. A distribution that is dense up to a wall and empty past it is not
what jitter looks like; it is what a **fixed symmetric pad of about 0.09 s per side** in the
upstream segmentation looks like, with the observed overlap equal to `0.18 − (the true inter-
segment gap)`. This audit measures the wall; it does not open the upstream builder, so the ±0.09 s
reading is an inference from the cap and is labelled as one.

Every call is affected and none is an outlier:

| call | clips | overlapping pairs | share | duplicated seconds |
|---|---:|---:|---:|---:|
| 4453225 | 635 | 582 | **91.8 %** | 82.87 |
| 4469088 | 922 | 731 | 79.4 % | 105.24 |
| 4470684 | 589 | 489 | 83.2 % | 69.06 |
| 4474506 | 633 | 472 | 74.7 % | 66.49 |
| 4479944 | 588 | 404 | 68.8 % | 58.52 |
| 4481952 | 632 | 498 | 78.9 % | 71.36 |
| 4482383 | 469 | 366 | 78.2 % | 53.87 |
| 4482613 | 592 | 396 | 67.0 % | 52.63 |
| 4483937 | 517 | 414 | 80.2 % | 59.92 |
| 4485192 | 461 | 329 | 71.5 % | 48.78 |

668.7 s is **1.70 %** of the population's 39,292.6 s, and the ten calls' clip durations sum to
more than the parent recording on 4453225 (4,311.2 s of clips against a 4,307.5 s call).

## 3. The audio at the edges

A deliberately crude frame-energy gate, named as such: 20 ms frames, a frame is ACTIVE when its
RMS is within 30 dB of the clip's own loudest frame, floored at −55 dBFS. It is not a VAD and
every figure below inherits that crudeness. No clip in the population is silent throughout.

| edge | clips | median silence | mean silence | p95 | **edge is active** | median overlap-zone active share |
|---|---:|---:|---:|---:|---:|---:|
| tail, overlapping | 4,681 | 0.000 s | 0.012 s | 0.02 s | **94.0 %** | **0.625** |
| tail, tight | 1,347 | 0.000 s | 0.038 s | 0.14 s | 51.2 % | — |
| head, overlapping | 4,681 | 0.040 s | 0.045 s | 0.12 s | 38.5 % | **0.667** |
| head, tight | 1,347 | 0.040 s | 0.051 s | 0.12 s | 32.1 % | — |

**The overlap zone is speech, not room tone.** Where the published segments overlap, the stretch
both of them claim is 62–67 % active by the gate, with an upper quartile of 1.0 — the next
speaker is already talking inside the previous clip.

**And the "tight" clips are not silence-bounded either.** Half of them (51.2 %) also end with the
gate still active: the published boundary falls at a word edge, not at a pause. So a positive gap
means *nobody else's segment claims this audio*, **not** *the speech had stopped*. That distinction
matters for what the re-cut can and cannot buy, and it is why the audit reports both the timestamp
split and the energy split rather than one of them.

## 4. The cross: which bleed sits on which cut

The 2026-09-06 scan published four aggregate containment buckets and no per-row attribution, so
this audit re-derives every tail and head insertion span with the scan's own rule — the longest
contiguous run of the inserted words that also occurs in the neighbouring reference, as a share
of the span — and joins each one to its own clip's geometry.

**The re-derivation reproduces the scan.** Arm A: 2,828 tail spans over 7,704 inserted words,
equal to the scan's figures to the unit. The head side is 594 spans against the scan's 603, and
the 9-span difference is named rather than smoothed: a span that is simultaneously the head *and*
the tail of its hypothesis (the whole output is one insertion, on a row whose reference normalizes
to nothing) is counted on **both** sides by the scan's two separate loops and on the tail only
here. 594 + 9 = 603, and the ≥ 0.6 head bucket is 284 + 3 = 287. The same holds arm by arm.

### Arm A, by the timestamps

| side | edge | spans | words | WER points |
|---|---|---:|---:|---:|
| tail | **overlapping clip** | **2,664** | **7,318** | **7.076** |
| tail | tight clip | 163 | 384 | 0.371 |
| tail | no neighbour | 1 | 2 | 0.002 |
| head | **overlapping clip** | **483** | **820** | **0.793** |
| head | tight clip | 111 | 221 | 0.214 |

At the scan's headline threshold — the spans the *next* published sentence's own reference already
contains at ≥ 0.6:

| | on overlapping clips | on tight clips | share on overlapping |
|---|---:|---:|---:|
| tail (868 spans) | **838** | 30 | **96.5 %** |
| head (284 spans) | 251 | 33 | 88.4 % |

**Per clip, which is the comparison that controls for the base rate.** 77.7 % of clips overlap
their next neighbour, so a share is not evidence on its own; a *rate* is.

| rate per clip | overlapping | tight | ratio |
|---|---:|---:|---:|
| any tail insertion span | 0.5691 | 0.1210 | **4.70×** |
| tail bleed at ≥ 0.6 | 0.1790 | 0.0223 | **8.04×** |
| head bleed at ≥ 0.6 | 0.0536 | 0.0245 | 2.19× |

**8,138 of the 8,745 boundary insertion words — 93.1 %, 7.869 of 8.456 WER points — sit on clips
whose published timestamps overlap that neighbour.** The head side is real but small; the tail
side is the whole effect.

### Arm A, by the audio

The weaker test, run so the timestamps are not the only witness. A span sits on an
`audible_overlap` when its clip's overlap zone is ≥ 50 % active by the gate.

| tail spans at ≥ 0.6 containment | count |
|---|---:|
| audible overlap | **553** |
| quiet overlap | 285 |
| no overlap zone at all | 30 |

### The other two arms

| arm | tail ≥ 0.6 on overlapping / tight | head ≥ 0.6 on overlapping / tight |
|---|---|---|
| A — this study's verbatim instruction | 838 / 30 | 251 / 33 |
| B — the Qwen3-Omni model-card ASR prompt | 871 / 34 | 261 / 35 |
| C — the official request shape | 606 / 19 | 191 / 30 |

Arm C emits a third less boundary mass than arm A and the *ratio* barely moves: whatever the
request shape changes, it does not change which cut produces the bleed.

### The thirty clips that bled without an overlap

Reported because they are the counter-example. Their `gap_next` runs from 0.00 to 2.26 s, and
**17 of the 30 end with zero trailing silence** — the published boundary cut through continuing
speech even though no neighbouring segment claimed it. Those are the rows where the core is
genuinely continuing past audio that stopped, and there are thirty of them against 838.

## 5. What this changes

**The scan's reading survives and gains a mechanism, with one correction.** The scan said 47.6 %
of arm A's error mass is speech at a segment edge. This audit says *which* edge and *why*: the
edge where the published segmentation hands the model 0.14–0.16 s of the next sentence. It is not
this study's slicer — the slicer is exact — and it is not the model choosing to run on: on tight
clips the same model produces the same bleed at one eighth the rate.

**The correction is about size.** 668.7 s of duplicated audio at 2.632 reference words per second
is at most **≈ 1,760 words**, and much of it is inter-sentence pause rather than speech. Against
7,318 tail insertion words on those same clips, **the delivered words are at most a quarter of the
mass**. So the overlap is the *trigger* — a partial onset the model completes — and the
continuation past it is the model's own. Both halves are removed by the same intervention, which
is why the re-cut is a clean single-factor experiment; but nobody should expect it to return 7.076
points, and the preregistration says so before the number exists.

**And it does not, by itself, close the 15.94-vs-9.79 gap.** The published systems very probably
received the same overlapping boundaries — they consume the release's own audio arrays, cut from
the same two columns — so the overlap is not a *difference* between the two systems unless the
released arrays turn out to be tight. Until that is checked, a boundary-exact number is a
statement about **our** sensitivity to the trigger, not about alignment. Section 7 of the
companion preregistration carries that constraint as a binding claim rule.

## 6. The ESB protocol, and the published 9.79 / 12.3

Everything here is taken from this repository's own committed records; no web read was made and
none was needed.

* **The column.** "Earnings22" on the Open ASR Leaderboard is the ESB repartition by source file,
  not the 125-file corpus: test = 4432298, 4450488, 4470290, 4479741, 4483338, 4485244;
  validation = 4420696, 4448760, 4461799, 4469836, 4473238, 4482110; train = the remaining 113,
  ten of which are this study's dev subset10.
* **The audio they feed.** The published evaluations consume the HF release's own per-utterance
  `audio` arrays. Those arrays exist in the pinned parquet and this study never materialized them.
  **Who cut them, and at what boundaries, is not established by anything in this repository.** The
  natural assumption is `[start_ts, end_ts]` — the same two columns — which would mean the
  published systems received the same ±0.09 s overlap; that assumption is stated, not verified.
* **The row counts.** This study's pinned test table carries 2,735 rows; the leaderboard config
  and the NeMo post both state 2,741. The six-row gap is recorded as unexplained in the test
  segment-table receipt and was never reconciled by guesswork. The dev10 table has no published
  counterpart at all — it is a 6,038-row subset of an 11,352-row train split, so there is nothing
  for it to disagree with.
* **The targets.** 9.79 is NVIDIA NeMo AutoModel's "Fine-Tune Qwen3-Omni for ASR" (same model,
  zero-shot, Whisper `EnglishTextNormalizer` both sides, greedy, N = 2,741); 12.3 is the cross-read
  for the same frozen model on the Open ASR Leaderboard English subset (Nemotron 3 Nano Omni,
  arXiv:2604.24954v2 Table 8). Two vendor reports of one frozen model that disagree by 2.5 points.
  whisper-large-v3 scores 11.59 on the same column. **None of these covers the ten dev calls**, and
  nothing in this audit is an alignment statement.
* **The normalizer.** Both sides use the Whisper `EnglishTextNormalizer`; the leaderboard column
  additionally applies `merge_compounds`, which this study does not (worth 0.251 dev points to us,
  and it works against us).

## 7. Limits

* **The ±0.09 s pad is an inference from a cap**, not a reading of the upstream builder. What is
  measured is that no pair overlaps by more than 0.1804 s and that the mass piles up against that
  value.
* **The energy gate is crude.** 20 ms frames and a 30 dB peak-relative threshold will call a
  breath or a chair active and will miss a quiet syllable. It is used only to separate populations,
  never to attribute a single span.
* **The word-rate bound in section 5 is a corpus average.** 2.632 words per second over the whole
  dev population; the overlap regions are systematically quieter than average, so ≈ 1,760 words is
  an upper bound and the true delivered count is lower.
* **The re-derived boundary spans are arm A's alignment, not a re-scoring.** No hypothesis was
  post-processed, no normalizer edited, no scorer changed, and the reference-word denominator
  (103,423) reproduces the sealed table exactly.
* **The dev-to-test transfer is untested here**, exactly as the scan said. The six test calls were
  not opened.

## 8. What this licenses

**No fix, no number, no re-cut.** This row measured a cut and wrote receipts. It writes two
preregistrations and executes neither:
`docs/readiness/2026-09-06-e22-dev-boundary-exact-v1-preregistration.md` carries (i) one
boundary-exact dev cell whose only factor is the clip boundaries, arm A's instruction byte-identical,
and (ii) the `whisper-large-v3` self-run anchor that turns the scan's 4.861-point "core capability"
ceiling into a measurement. Both need their own owner decision, their own exposure row and — for
the anchor — an asset the umbrella lock does not yet carry.
