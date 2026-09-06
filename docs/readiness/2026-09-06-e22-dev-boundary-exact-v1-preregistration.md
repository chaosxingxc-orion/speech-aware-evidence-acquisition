# Preregistration — the Earnings-22 boundary-exact dev cell, and the whisper-large-v3 anchor

**STATUS: PREREGISTERED, NOT AUTHORIZED.** Two cells are specified here and **neither is flown by
the row that writes this document** (`SAEA-E22-MF-CLIP-BOUNDARY-AUDIT-V1`, `model-free-check`).
Each needs its own owner decision, its own exposure row registered before its first contact, and —
for cell 2 — an asset the umbrella lock does not yet carry. Nothing below may be executed on the
authority of this file.

Basis: `docs/readiness/2026-09-06-e22-clip-boundary-audit-v1.md` (the cut, measured) and
`docs/readiness/2026-09-06-e22-semantic-error-scan-v1.md` (the error mass, categorised). The
one-experiment-in-flight rule applies: these are queued behind whatever is flying, and cell 1
precedes cell 2 only because cell 2 needs an acquisition.

---

## 0. Why these two, and why now

The audit established that this study's slicer is exact and that the **published** segmentation
overlaps: 4,681 of 6,028 adjacent dev pairs overlap, capped at 0.1804 s, 668.7 s of dev audio
delivered twice; 838 of arm A's 868 tail bleed spans at ≥ 0.6 containment sit on those clips, at
8.04× the per-clip rate of tight ones. It also established the ceiling on what a re-cut can return:
668.7 s at 2.632 reference words per second is **at most ≈ 1,760 words** against 7,318 tail
insertion words, so most of the mass is continuation the overlap *triggers* rather than speech it
*delivers*.

Two questions follow, and each needs exactly one cell.

1. **How much of our error is the trigger?** Only a re-cut answers it: change the boundaries, hold
   everything else byte-identical, pair against the sealed arm on the same rows. That is cell 1.
2. **How much of the residual is recognition rather than output discipline?** The scan bounded
   "core capability" at 4.861 dev WER points and could not measure it, because no second system has
   ever seen these clips. A `whisper-large-v3` self-run over the same 6,038 rows through the same
   scorer turns that ceiling into a number. That is cell 2, and both previous verdicts already
   named it.

---

## 1. Cell 1 — `SAEA-E22-DEV-ESB-BOUNDARY-EXACT-V1`

**One factor: the clip boundaries. Nothing else moves.**

### 1.1 The re-cut rule, stated before any byte is written

The published segments overlap, so "the published `start_ts`/`end_ts` with zero padding" is not a
well-defined disjoint cut — it is what we already have. **The rule is the midpoint of the overlap,
and only of the overlap.** For call *c* with segments `0..n−1` in published order:

```
start'_i = start_i                              if i == 0
         = max(start_i, (end_{i-1} + start_i)/2) otherwise
end'_i   = end_i                                 if i == n-1
         = min(end_i, (end_i + start_{i+1})/2)   otherwise
```

then cut `pcm[max(0, round(start'_i × 16000)) : min(frames, round(end'_i × 16000))]` — the same
expression the current slicer uses, on the corrected boundaries.

Three properties, each of which the precondition pass must assert:

* **A positive gap is never closed.** Where the published segments are separated, both boundaries
  stay exactly where they are. Extending into the gap would add audio no segment claims and would
  make this a two-factor experiment.
* **No audio is invented.** Every sample in every new clip is inside the old clip for the same
  segment; the re-cut is strictly subtractive.
* **The clamp survives.** `4481952-631`, whose `end_ts` runs 0.0799 s past the decoded parent,
  stays clamped to the parent.

### 1.2 What the re-cut costs, computed now so a drift is visible later

| quantity | sealed arm A (`dev-v1`) | boundary-exact (`dev-bx-v1`) |
|---|---:|---:|
| clips | 6,038 | 6,038 |
| total audio seconds | 39,292.647 | **38,624.016** |
| total audio hours | 10.9146 | **10.7289** |
| clips that lose audio | — | **5,829** |
| mean loss per clip | — | 0.110737 s |
| maximum loss on one clip | — | 0.180272 s |
| shortest clip | 0.219938 s | **0.119995 s** |
| clips under 0.15 s | 0 | 14 |
| adjacent pairs that still overlap | 4,681 | **0** |

**A precondition fails the cell** if the rebuilt table has any overlapping pair, any clip of
non-positive duration, any clip longer than its `dev-v1` twin, or a total that differs from
38,624.016 s by more than 0.01 s.

### 1.3 Held fixed, byte for byte

Everything the 2026-09-05 arm A cell declared, unchanged: build commit
`04ccc72a2207347ca76161b93fd9d846dd0a8675`, runtime receipt
`docs/receipts/runtime-q4km-featcache-04ccc72a.json`, Q4_K_M, the pinned decoder and mmproj
digests, temperature 0, seed 20260803, `max_tokens` 1024, one contact per item, no evidence, no
OBS windowing, `core.flight.FlightRuntime` with the shared rails zero-supply direct arm and the
OpenJiuwen executor through `scripts/flights/run_e22_esb_cell.py`, the base
`TaskAdapter.assemble_prompt` shape (one system message with the instruction, one user message
with the audio), serving geometry `-c 40960 -np 8` at 5,120 tokens per slot, and **arm A's
instruction verbatim**:

> Transcribe the speech verbatim exactly as spoken. Never insert, repeat, or add any word you do
> not clearly hear in the audio. Output only the transcript text.

**The audio path is `raw-audio-mmproj`**, exactly as the sealed dev arms used it: the arm's D2
field set carries no `speech_feature_parts`, `packets_required` is false, and no packet is
promoted. No feature cache directory is involved and none may be introduced — a packet path would
be a second factor.

The reference layer, the scorers (`asr-wer-esb-whisper` paper-facing, `asr-wer-esb`, `cost`), the
corpus aggregation and the no-`merge_compounds` deviation are all unchanged, and scoring runs once
per complete manifest through `core.scoring_batch`, never sharded.

### 1.4 The D1 supplement rebuild, and the identity rule

The re-cut writes different bytes for the same published segment, so the two populations must never
share an identifier.

* Media: `$SPEECHRL_DATA_DIR/derived/e22-esb-utterances/dev-bx-v1/<call>/<id>.wav`. A **new version
  directory**, so the two cuts' bytes never share a root.
* Sample ids: `<call>-<segment>@bx1`. The published segment key is recovered by splitting on `@`,
  so the reference layer, the neighbour lookup and the paired join against the sealed arm are all
  exact; and no id collides with the `dev-v1` supplement's.
* Roster receipt: `docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-dev-esb-boundary-exact-v1/roster/flight-roster-receipt.json`.
* D1 media supplement: `docs/receipts/artifacts/d1-e22-esb-dev10-utterances-boundary-exact-v1.json`
  (schema `saea-d1-media-supplement-v1`), chaining to the same six-parent media identity through the
  same `parent_sha256` check the `dev-v1` supplement made.
* Engineering: this is a **`--profile dev10-boundary-exact` on the existing builders**, not a new
  module — one carrier descriptor, one profile entry, one id-suffix argument, plus tests. No new
  `rails/probes/` module, no `TaskAdapter` subclass, no separate harness.

### 1.5 Preconditions, all model-free, all before the first contact

1. Rebuild the table under the rule of §1.1 from the **already pinned** `segments-dev10.jsonl`
   (`51257011…`); no new download, no new revision.
2. Assert the four properties of §1.2 and the three of §1.1.
3. Cut, then cut again, and assert `items_sha256` is unchanged — the `dev-v1` cut was proved
   byte-deterministic this way and this one must be too. **ffmpeg stays absent**; a decoder change
   would move every byte.
4. Build the D1 supplement and gate it through `contracts.gate_media_identity`.
5. Re-derive the prompt fit. The re-cut only shrinks clips, so the window fit can only get easier;
   the longest clip stays 78.36 s and its speech-token bound is unchanged in the worst case.
6. Wire-check the whole request path through a fake gate and a fake transport — zero contacts, zero
   servers, zero sockets — as every earlier cell in this family did.
7. A 4-row dry run before the flight, per the one-recovery-per-flight rule.

### 1.6 The decision rule, fixed now

**Population:** the same 6,038 rows, the same references, the same 103,423 reference words.
**Comparator:** the sealed `SAEA-E22-DEV-ESB-PROMPT-A-V1` (attempt-20260905T073641Z-f977d1),
paired per utterance. No new arm A is flown; greedy decoding is not bitwise reproducible across
batch compositions, so the comparison is against the sealed outputs, never against a re-run.

**Statistics:** `analysis.paired.paired_contrast`, 10,000 replicates, stratified by source call
(10 strata), seed 20260903, CI90. Two metrics, both paired, both reported with the delta signed as
`boundary-exact − arm A`:

* **corpus WER** under the Whisper `EnglishTextNormalizer` (paper-facing);
* the **agentic error rate** of the semantic scan — HIGH-impact reference-word mass over reference
  words — recomputed on the new outputs by `analysis.e22_error_taxonomy` at its committed version.

**ADMITTED** as a model-usage local optimization **iff both hold**:

1. corpus WER improves and the **CI90 upper bound on the delta is < 0**; and
2. the agentic error rate does not worsen: its point estimate is ≤ arm A's **and** the CI90 upper
   bound on its delta is below **+0.05 points** — a non-inferiority margin fixed here, before the
   number exists, so it cannot be chosen afterwards.

**Mandatory reporting, admitted or not:** the per-call table for all ten calls under both
normalizers; natural-mixture and equal-call weightings side by side; the S/D/I split and the
hypothesis-to-reference length ratio; the utterance-duration decomposition; **the boundary
category's mass before and after** (`segmentation-artifact` + `runaway-tail` + `runaway-head`,
8.358 points on the sealed arm A) and the tail/head containment buckets recomputed on the new
geometry, where every pair is now tight; and the fourteen clips that fall under 0.15 s, named.

**The claim rule, and it is binding.** A boundary-exact number is a statement about **this study's
sensitivity to the boundary trigger on its own dev split**. It is **not** an alignment argument and
must never be compared to the published 9.79 or 12.3, because those systems consume the ESB
release's own audio arrays and this cell changes the audio the protocol delivers. That prohibition
lifts only if the check in §3 establishes that the released arrays are themselves tight — in which
case the boundary-exact cut is the protocol-faithful one and the comparison becomes legitimate.
Until then: paired against arm A, on dev, and nothing else.

**UPDATE 2026-09-06 — the condition was tested and it FAILED, so the prohibition is now
UNCONDITIONAL and the lifting clause above is dead.** The §3 check ran the same day as row
`SAEA-E22-MF-ESB-ARRAY-DURATIONS-V1` (`model-free-check`, zero contacts of every kind), and the
ESB release's own arrays are **not** tight: 2,732 of 2,735 published test utterances (99.89 %)
match `end_ts − start_ts` to within a millisecond, the median difference is +0.0000316 s and the
implied per-side pad +0.0000158 s — zero — so the arrays are the published spans; placed at their
own published starts, 1,959 of 2,729 adjacent pairs (71.8 %) overlap, hard capped at −0.180452 s
with a −0.139956 s median and 274.3 s delivered twice, against this study's own dev cut's 77.7 %,
−0.18042 s cap and −0.140015 s median. Same wall, same median, same geometry, so the ~0.09 s
per-side pad sits in the boundary table both cutters consume rather than in either cutter, and the
published systems were handed the same onsets. **A boundary-exact number therefore stays a
statement about this study's sensitivity to the boundary trigger on its own dev split, is never an
alignment argument, and is never compared to 9.79 or 12.3 — there is no longer any condition under
which that comparison becomes legitimate.** Verdict and receipts:
`docs/readiness/2026-09-06-e22-esb-array-durations-v1.md`,
`docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-esb-array-durations/`. The same
check recorded a separate deviation this cell does not address and must not be read as addressing:
the release stores each call's native container (16 kHz stereo, 22.05 kHz stereo, 24 kHz mono)
while this study's clips are librosa-decoded 16 kHz mono from the locked MP3s, so the two paths
agree on the span and differ on the decode.

### 1.7 Budget (ExecutionPlan, to be registered with the row)

| | plan | ceiling | basis |
|---|---:|---:|---|
| model calls | 6,046 | 6,100 | 6,038 rows × 1 contact + 8 canaries |
| speech audio seconds | 38,700 | 39,000 | 38,624.016 for one pass |
| GPU hours | 0.50 | 0.75 | arm A used **0.4515** for the same 6,038 contacts at 1.7 % more audio |
| paid API spend | 0 | 0 | in force |

Expected dispatch wall ≈ 1,600 s at eight slots (arm A: 1,612.9 s, 3.744 contacts/s, realtime
factor 24.36×). CPU preprocessing is trivial here — there are no packets — but the re-cut itself is
a parallel decode of ten parent MP3s and runs at the campaign cap of 8 workers if a GPU campaign is
in flight, 20 otherwise.

### 1.8 What the flight agent must do

1. Register the exposure row **before the first contact**, naming the population, the comparator
   attempt, the budget and the claim rule of §1.6.
2. Run the model-free preconditions of §1.5 and stop on any refusal. Land their receipts.
3. Front-load the model load as a background step; do the re-cut and the D1 rebuild during it.
4. Fly one attempt, 6,038 contacts, one serving geometry, no repair, no retry, no resend.
5. Score once, over the complete manifest, through `core.scoring_batch`.
6. Run `analysis.e22_error_taxonomy` at its committed version on the new outputs and report the
   boundary mass before and after.
7. Write the verdict with the per-stratum table and the claim rule quoted verbatim.
8. **Stop.** The test read of §1.9 is not part of this cell.

### 1.9 The test read, if and only if admitted

If cell 1 is ADMITTED, a single boundary-exact read of the six calibration-exposed ESB test calls
may be **proposed** to the owner — never taken on this file's authority. It would be the **second**
read of a population the 2026-09-04 owner decision allowed **once**, it needs its own owner
decision and its own exposure row, and it inherits the claim rule of §1.6 in full. The 109
remaining confirmatory calls stay untouched either way.

### 1.10 Not authorized by cell 1

No mechanism arm. No knob tuned on the test split. No third prompt. No few-shot. No
post-processing of any hypothesis. No Q8_0 cell. No packet path. No `merge_compounds`. No
re-scoring of any sealed arm. No `paper-scale-confirmatory` profile, no manuscript, no Stage-3
activity.

---

## 2. Cell 2 — `SAEA-E22-DEV-WHISPER-ANCHOR-V1`

**A tool-model reference run, not a frozen-core contact.** It answers one question the study has
asked three times and never measured: *how much of our error is recognition, and how much is
output discipline that a published-grade system does not have?*

### 2.1 The asset — **ABSENT**, and its acquisition is an umbrella action

The umbrella lock `docs/datasets.lock.json` carries, under `models`:
`qwen3-omni-30b-a3b-instruct-gguf`, `qwen3-omni-30b-a3b-instruct-gguf-q4km`,
`nemotron3-nano-omni-nvfp4`, `omni-embed-nemotron-3b`, `mms-fa-torchaudio`,
`spkrec-ecapa-voxceleb`, `diar-sortformer-4spk-v2`, `qwen3-embedding-0.6b-gguf`. **There is no
whisper entry**, and `$SPEECHRL_DATA_DIR/models/` holds no whisper directory. No revision or hash
is copied into this document; the cell resolves the asset through `data.lock` at use time, as every
other cell does.

**Blocking precondition:** the umbrella must admit a `whisper-large-v3` entry to
`docs/datasets.lock.json` and materialize it through `scripts/data/fetch-assets.sh`. That is
program-level asset acquisition, it belongs to the umbrella, and this study must not do it
unilaterally. Until it lands, cell 2 cannot start; if the owner declines the acquisition, the
scan's 4.861-point core-capability figure stays a ceiling and must keep being reported as one.

### 2.2 Protocol, pinned before the run

* **Population:** the same 6,038 dev clips the sealed arms were served, **the `dev-v1` media
  bytes**, not the boundary-exact cut. The anchor must sit on the same audio as arm A or it stops
  being an anchor. (If cell 1 is admitted, a second anchor pass on `dev-bx-v1` is a separate cell.)
* **Model:** `whisper-large-v3`, float16, greedy, `language="en"`, `task="transcribe"`, no
  condition-on-previous-text, no prompt, no initial prompt, no temperature fallback.
* **Long form:** 12 clips exceed 30 s and 103 exceed 20 s, with a maximum of 78.36 s, so the
  chunking rule must be fixed **now**: sequential long-form decoding with `return_timestamps=True`
  and no chunk-and-stride overlap. Recorded in the receipt as a named deviation from the short-form
  default, because it is a decode-shape choice that could otherwise be tuned after the fact.
* **Scoring:** the same `asr-wer-esb-whisper` scorer, the same corpus aggregation, the same
  reference layer, once, over the complete manifest, through `core.scoring_batch`.
* **Serving:** the frozen-core llama-server must be **down**. The 2026-09-05 dev flights peaked at
  22,506 MiB of 24,463 on this GPU, so nothing co-resides with them; the anchor runs in a GPU gap,
  and the ready-first scheduling rule decides when.

### 2.3 What it measures, and what it does not

**Reported, all on the same 6,038 rows:**

1. `whisper-large-v3` corpus WER under the Whisper normalizer, pooled and per call, beside arm A's
   17.5648;
2. the full `analysis.e22_error_taxonomy` pass on its outputs — category mass, semantic-impact
   split, **agentic error rate**, and the four-bin estimate — beside arm A's;
3. **the boundary block**, which is the point: `segmentation-artifact` + `runaway-tail` +
   `runaway-head` for whisper against arm A's 8.358 points, and the tail/head containment buckets
   crossed with the same clip geometry this audit measured. A system that receives the identical
   overlapping audio and emits a third of our boundary mass converts "output discipline" from a
   plausible reading into a measured difference;
4. the acoustic block — `acoustic-misrecognition` and the content-word residual — which is the
   direct estimate of the core-capability difference the scan could only bound at 4.861 points.

**There is no published number for these ten calls**, so this cell issues **no alignment verdict
and no pass/fail**. whisper-large-v3's published 11.59 belongs to the ESB *test* column and is
recorded as orientation only. The cell's output is a decomposition, not a score to clear.

### 2.4 Budget (ExecutionPlan, to be registered with the row)

| | plan | ceiling | basis |
|---|---:|---:|---|
| tool-model transcriptions | 6,038 | 6,100 | one per clip, no retry |
| speech audio seconds | 39,300 | 39,500 | 39,292.647 for one pass |
| GPU hours | 1.0 | 1.5 | 10.915 h of audio; whisper-large-v3 fp16 on this GPU runs short clips well above 20× realtime even without batching, so 1.0 is already generous |
| frozen-core contacts | **0** | **0** | this is a tool model; the frozen core is not touched |
| paid API spend | 0 | 0 | in force |

### 2.5 Not authorized by cell 2

No use of whisper output as evidence, as a prompt, as a rescoring signal, as a knowledge source or
as any part of a mechanism arm — **the study's own no-transcript-state ruling stands** and this run
is a measurement instrument only, read once into a verdict. No test-split pass. No fine-tuning of
anything. No substitution of whisper for the frozen core in any claim. No Stage-3 activity.

---

## 3. A cheap check that would settle the comparability question

**TAKEN 2026-09-06, under an owner decision given the same day, as row
`SAEA-E22-MF-ESB-ARRAY-DURATIONS-V1`. ANSWER: the released arrays are cut at `[start_ts, end_ts]`
and carry the published overlap (71.8 % of adjacent pairs, cap −0.180452 s, median −0.139956 s).**
The paragraphs below are the specification as written before the check; the result and its
consequence for §1.6 are in the dated update at the end of §1.6 and in
`docs/readiness/2026-09-06-e22-esb-array-durations-v1.md`.

Named here because §1.6's claim rule turns on it, and because it costs no model contact at all.

**The question.** Are the ESB release's own per-utterance audio arrays cut at exactly
`[start_ts, end_ts]`? If yes, the published systems received the same ±0.09 s overlap and the
boundary-exact cut is a deviation from the protocol. If no — if the released arrays are tight — the
boundary-exact cut is the *faithful* one and §1.6's prohibition lifts.

**How.** The four ESB **test** parquet shards are already on disk
(`$SPEECHRL_DATA_DIR/derived/e22-esb-segment-table/parquet/`, 1.10 GB, digests confirmed against
the repository's own git-LFS oids). Reading each row's `audio` array **length** and comparing it to
`end_ts − start_ts` answers the question with no reference sentence, no hypothesis, no score and no
model. The 55 train shards that hold the dev10 rows were never downloaded, so the dev population
cannot answer it offline.

**Why it is not done here.** Those shards are the calibration-exposed **test** population, and this
audit's row is scoped to dev. Even a durations-only read of them is a touch of that population and
needs its own owner decision and its own exposure row. It is offered as the cheapest next
measurement in the whole area — minutes of CPU, zero contacts — and explicitly not taken.

---

## 4. Sequence, and what is registered when

1. **Nothing flies on this document.** It is a preregistration written by a `model-free-check` row.
2. Cell 1 needs: an owner GO, an exposure row registered before its first contact, and the
   preconditions of §1.5 landed as receipts.
3. Cell 2 needs: an owner GO, an **umbrella** lock entry and fetch for `whisper-large-v3`, an
   exposure row, and a GPU gap.
4. The §3 check needed: an owner decision covering a durations-only read of the calibration-exposed
   test shards, and its own exposure row. **Both were given and it is DONE (2026-09-06, row
   `SAEA-E22-MF-ESB-ARRAY-DURATIONS-V1`); its answer makes §1.6's claim rule unconditional.**
5. One experiment in flight at a time; a new mechanism is admitted only after its predecessor is
   replicated or root-caused to a named component. Neither cell here is a mechanism — cell 1 is a
   protocol correction and cell 2 is an instrument.
