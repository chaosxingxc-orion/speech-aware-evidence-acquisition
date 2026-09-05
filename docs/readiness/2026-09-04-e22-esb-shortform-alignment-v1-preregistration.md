# Earnings-22 short-form alignment against the only same-model published number, v1 preregistration

Status: **REGISTERED 2026-09-04**, on the owner decision recorded verbatim in section 2. One run,
profile `baseline-reproduction`, one arm, one cell, plus its own 4-row smoke. Written before any
model contact.

| Run id | Cell | Population | Fragments |
|---|---|---|---|
| `SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1` | `E22-ESB-2735` | the whole published ESB Earnings22 **test** subset: 2,735 utterances from six `earnings22-original` calls, 19,494.608 s (5.415 h) | dataset `earnings22-esb-utterances-2735`, baseline `e22-esb-direct-zero`, model `q4km-e22-esb-mmproj-gpu-04ccc72a-np8`, experiment `e22-esb-shortform-alignment-v1` |
| `SAEA-E22-ESB-SHORTFORM-ALIGNMENT-SMOKE-V1` | `E22-ESB-SMOKE-4` | 4 rows of the same roster, chosen before any contact | dataset `earnings22-esb-utterances-smoke4`, same baseline/model, experiment `e22-esb-shortform-alignment-smoke-v1` |

Predecessor: `docs/readiness/2026-09-04-e21-full44-direct-baseline-v1-verdict.md`
(`SAEA-E21-FULL44-DIRECT-BASELINE-V2`, **ALIGNED**, corpus Whisper-normalized WER 8.200 on all 44
Earnings-21 discovery calls). That flight supplies the instruction, the decoding parameters, the
audio path, the build, the hardened server environment and the geometry rule; everything except the
corpus and the segmentation is carried forward unchanged.

## 1. Why this cell exists

The owner's alignment goal (within 3 points of the published number, or better, and never worse than
a degraded model's published number) has exactly one **same-model** published target across the three
carriers: **Qwen3-Omni-30B-A3B-Instruct, zero-shot, Earnings-22 "short-form" test subset, WER 9.79**
(NVIDIA NeMo AutoModel, "Fine-Tune Qwen3-Omni for ASR"; Whisper `EnglishTextNormalizer` on both
sides; greedy; N = 2,741 utterances), cross-read by **12.3** for the same model on the Open ASR
Leaderboard English subset (Nemotron 3 Nano Omni, arXiv:2604.24954v2 Table 8). Two vendor reports of
the same frozen model disagree by 2.5 points, so the band this study can claim is "consistent with
both" at best. Every other target on every other carrier is a cross-system comparison.

The subset is not the 125-file corpus. "Earnings22" on the leaderboard is the ESB partition by source
file: **test = 4432298, 4450488, 4470290, 4479741, 4483338, 4485244** (validation = 4420696, 4448760,
4461799, 4469836, 4473238, 4482110; train = the remaining 113), cut at punctuation boundaries into
short utterances. Degraded-model floors on the same column (leaderboard revision of 2026-09-04):
whisper-large-v3 **11.59**, whisper-large-v3-turbo 11.07, distil-large-v3.5 10.83, Qwen3-ASR-0.6B
10.78, Qwen3-ASR-1.7B 9.73; older vintage (2026-06-13, before the normalizer/hardware change):
medium.en 12.63, small.en 12.97, base.en **15.09**, tiny.en 19.12. NeMo's fine-tuned 8.89 is context
only and is never a target.

## 2. The owner decision this run rests on

`docs/receipts/splits.json` places all twelve ESB test and validation calls in the study's
**confirmatory** split (115 calls), and the dev subset10 contains none of them. Any Earnings-22
alignment therefore reads confirmatory audio and references. The owner decided, verbatim:

> **Owner decision 2026-09-04 (evening): the six ESB test calls 4432298, 4450488, 4470290, 4479741,
> 4483338, 4485244, all in the study's Earnings-22 confirmatory split, may be read ONCE for this
> direct-baseline calibration; they are re-designated calibration-exposed afterwards; 109
> confirmatory calls remain for final reporting. No mechanism arm, no knob tuned, no other
> confirmatory call read.**

Recorded as a successor receipt, `docs/receipts/splits-calibration-exposure-2026-09-04.json`, which
pins the parent `splits.json` bytes (`b156ad45…`) and **does not rewrite them**; it names the six
calls (calibration-exposed identity `e9d4547b…`) and the 109 that remain (identity `b898b864…`,
unread). The ESB **validation** six are inside those 109 and are explicitly not covered.

**How the role reaches the machine.** `contracts.plan.STAGE2_SPLIT_ROLES` admits only `discovery` and
`dev`, and refuses `confirmatory` outright — the refusal itself names "a dated owner allowance" as one
of the two ways past it. `calibration-exposed` has no machine role of its own, so both ExecutionPlans
declare **`dev`**: the role that means *legal to calibrate against, never a final-reporting split*,
which is exactly what the owner decision makes these six calls. `earnings22-original` already carries
this study's `dev` role for its subset10, so the carrier/role pairing is not new. This is a faithful
expression of the decision, not a relabeling to get past a gate.

## 3. Population and materials

**The segment table.** `sanchit-gandhi/earnings22_split`, split `test`, pinned at revision
`f9fb35f4134e32b9c8100199d949398fd6d08a5f`. Only six metadata columns are read — `source_id`,
`segment_id`, `sentence`, `start_ts`, `end_ts`, `id` — through a pyarrow **column projection**, so the
parquet's `audio` column is never materialized. All four `test-*` parquet shards (1.10 GB) were
fetched with a resumable ranged GET, re-hashed locally, and every digest equals the repository's own
git-LFS `oid`, which is that file's SHA-256. Receipt:
`docs/checks/speech-aware-evidence-acquisition/2026-09-04-e22-esb-shortform-alignment-400-v1/segment-table/segment-table-receipt.json`
(`0c923a73…`), extracted table `7ef6911b…`, 2,735 rows.

**This table is a derived-split reference pinned by hash, not a new umbrella lock asset.** It adds no
entry to `docs/datasets.lock.json`, downloads no new audio for the run, and is never resolved through
`data.lock`/`data.carriers`. The receipt says so in its own words.

**The 2,735-vs-2,741 discrepancy is unresolved.** The pinned table carries 2,735 test rows; the
leaderboard config `hf-audio/open-asr-leaderboard` and the NeMo post both state 2,741. The six-row gap
(0.2 % of the population) is recorded as unexplained. No row is invented, dropped or re-cut to close
it, and every number reported here is over the 2,735 rows the pinned table actually contains.

**The audio.** The six calls come from the locked `earnings22-original` asset already on disk. Each
parent MP3 is decoded exactly once through `reproduction.obs_loop.decode_parent_pcm` — the same
librosa 16 kHz mono decode every earlier slice in this repository used; **ffmpeg is absent by design
and was not used** — and each utterance is written as a 16 kHz mono WAV through
`reproduction.obs_audio.write_wav_bytes`, the same deterministic stdlib writer the OBS slicer uses.
The cut is reproducible: a second full run produced byte-identical files (`items_sha256`
`b03be3e5…` unchanged). One libmpg123 frame warning (`part2_3_length too large`) appears on both runs
and is a property of the source MP3, not of the decode.

Derived media live at `$SPEECHRL_DATA_DIR/derived/e22-esb-utterances/v1/<call>/<id>.wav`, 623,947,810
bytes, and never enter Git. **They deliberately do not go inside the locked carrier tree**: a derived
artifact must not land in a dataset working copy D1 hashed.

| call | utterances | segment seconds | call seconds | coverage | longest utterance |
|---|---:|---:|---:|---:|---:|
| 4432298 | 351 | 2,527.45 | 2,643 | 95.6 % | 34.00 |
| 4450488 | 508 | 4,269.87 | 4,321 | 98.8 % | 33.30 |
| 4470290 | 178 | 1,584.82 | 1,627 | 97.4 % | 25.34 |
| 4479741 | 473 | 3,499.84 | 3,665 | 95.5 % | 30.66 |
| 4483338 | 619 | 4,024.27 | 4,160 | 96.7 % | **36.36** |
| 4485244 | 606 | 3,588.36 | 3,689 | 97.3 % | 30.46 |
| **all six** | **2,735** | **19,494.608** | 20,105 | 97.0 % | 36.360125 |

Duration distribution: median 6.12 s, p90 14.06 s, p99 25.04 s, max 36.360125 s, min 0.219938 s; 74
utterances exceed 20 s and 10 exceed 30 s. **Three** utterances (`4432298-351`, `4470290-178`,
`4483338-619` — the last of three calls) have an `end_ts` past the decoded parent and are clamped to
it; they are named in the roster receipt and will be named again in the verdict.

**Identity.** The 2,735 utterance ids enter D1's identity closure through the additive media
supplement `docs/receipts/artifacts/d1-e22-esb-utterances-2735.json` (schema
`saea-d1-media-supplement-v1`, `caa221ec…`), the same mechanism the Audio2Tool official-population
flights used. Every id is new to the immutable artifact by construction, and the builder refuses any
utterance whose parent call is not one of the six *and* whose parent bytes do not equal what D1 itself
recorded — so a derived utterance can only ever chain to media D1 closed over.

**References.** The `sentence` column, verbatim, in a derived reference layer at
`$SPEECHRL_DATA_DIR/derived/e22-esb-segment-table/e22-esb-test-references.jsonl` (2,735 rows, 50,083
whitespace words, `f6fddf40…`). It is never committed, never inside the carrier tree, and **never in
the request path**: the roster receipt the flight entry point reads carries identifiers, media paths,
measured media identity and segment spans only.

## 4. Budget (ExecutionPlan, registered)

| | plan | registered ceiling | basis |
|---|---:|---:|---|
| model calls (flight) | 2,743 | 2,800 | 2,735 rows × 1 contact + 8 canaries |
| speech audio seconds (flight) | 19,500 | 20,500 | 19,494.608437 for one pass, ceiling about 5 % above |
| GPU hours (flight) | 1.5 | 2.0 | see below |
| model calls (smoke) | 20 | 50 | 4 rows × 1 contact plus headroom |
| speech audio seconds (smoke) | 100 | 200 | 56.760187 for one pass |
| GPU hours (smoke) | 0.5 | 1.0 | essentially all of it model load |
| paid API spend | 0 | 0 | in force, unchanged |

GPU-hour basis: the full-44 flight served 1,593 windows of 90 s in **0.973 GPU-h** at `-np 6` with
CUDA graphs disabled — 143,370 s of audio. This cell is 19,495 s of audio in 2,735 much shorter
requests at `-np 8`, so the encode side is about 7× smaller, and the decode side is bounded by 2,735
completions the full-44 flight's own evidence puts at a few hundred tokens each. 1.5 h is deliberately
generous against that.

`core/model/adapter.py` enforces `planned_model_calls` and `planned_speech_audio_seconds` **across all
attempts of a run id**. A partly spent dead attempt therefore cannot be re-run under the same run id;
the one permitted recovery takes a fresh run id and a fresh exposure row.

## 5. Protocol

* **Request**: one utterance per contact. No OBS loop, no windowing — an ESB utterance *is* the
  request. `policy: fixed`, `rails_arms: ["zero-supply"]`, `arm: bare-core`, `evidence_source: none`.
* **Prompt**: the base `TaskAdapter.assemble_prompt` default — one system message carrying the
  instruction, one user message carrying the audio. Verified before registration:

  ```json
  [{"role": "system", "content": "Transcribe the speech verbatim exactly as spoken. Never insert, repeat, or add any word you do not clearly hear in the audio. Output only the transcript text."},
   {"role": "user", "content": [{"type": "input_audio", "media_relpath": "derived/e22-esb-utterances/v1/4479741/4479741-224.wav"}]}]
  ```

* **Instruction**, byte-identical to the one `SAEA-E21-FULL44-DIRECT-BASELINE-V2` sent, itself
  byte-identical to the sealed 2026-08-14 `fixed-batch-zero-locked-buf90` fragment: *"Transcribe the
  speech verbatim exactly as spoken. Never insert, repeat, or add any word you do not clearly hear in
  the audio. Output only the transcript text."*
* **Decoding**: greedy (`temperature: 0`), `max_tokens: 1024`, `id_slot: per-sample`, seed 20260803
  (inert under greedy) — byte-identical to the full-44 flight. `max_tokens` is deliberately **not**
  reduced for short utterances: a smaller ceiling could truncate a rambling completion and silently
  move WER, and the full-44 flight measured zero requests reaching 1,024 on windows 2.5× longer.
* **Model**: frozen Qwen3-Omni-30B-A3B-Instruct Q4_K_M, decoder `0751c279…66d`, bf16 mmproj
  `f0dfe825…883` **resident on the GPU**, build `04ccc72a`, no `LLAMA_MTMD_FEAT_CACHE_DIR`.
* **Serving geometry**: `-c 32768 -np 8`, 4,096 tokens per slot, `GGML_CUDA_DISABLE_GRAPHS=1`.
* **Harness**: `core.flight.FlightRuntime`, entered through `scripts/flights/run_e22_esb_cell.py` —
  the same harness, entry-point family and adapter-binding pattern every Audio2Tool direct cell flew.

### 5.1 Window fit, derived before any contact

Speech cost follows the mmproj encoder's exact one-second window rule `n_tokens = 13 × ceil(audio_seconds)`
— the rule that reproduces all 342 sealed `COST` records of `SAEA-E-005B-N10-zero` and all 400
per-packet counts of the Audio2Tool calibration promotion receipt without exception.

* Longest utterance `4483338-281` = 36.360125 s → `13 × 37` = **481** speech tokens.
* Text envelope: this three-sentence instruction plus a bare audio user turn, well under 100 tokens.
* Worst required ≈ 481 + 100 + 1,024 completion + 2 special = **about 1,607** tokens.
* Declared slot = 32,768 / 8 = **4,096**, a multiple of 512 so the server's own rounding cannot move
  it. Margin about 2,489 tokens, **×2.55**. Fit rule (the full-44 flight's own):
  `slot_tokens >= 2 × worst_required`. **FITS.**

VRAM is not certified by arithmetic and is not claimed here. This geometry is *strictly smaller* than
two geometries this card is already proven to serve on the resident-mmproj raw-audio path (`-c 49152
-np 8` peaked at 23,396 MiB; `-c 36864 -np 6` at 22,720 MiB of 24,463), on encodes whose longest
window is 36.4 s rather than 90 s. The smoke proves it live before the flight launches.

### 5.2 Deviations from the published row, named

| # | deviation | why | expected effect |
|---|---|---|---|
| D1 | utterances cut locally from the locked MP3s, not the published HF audio bytes | no new audio asset is downloaded; the study already owns the six calls | the spans are the published float32 boundaries verbatim, so the segmentation matches; the decode path differs (librosa 16 kHz mono from MP3). Three end boundaries are clamped to the decoded parent |
| D2 | Q4_K_M against an unstated (presumably bf16) published precision | the frozen core this study may reach is the Q4_K_M GGUF | unknown in sign and size; the leading suspect for any gap |
| D3 | this study's own three-sentence ASR instruction | the published row's prompt is not published | unknown; holding it identical to the Earnings-21 cell is what makes the two comparable |
| D4 | 2,735 rows against the published N = 2,741 | the pinned table contains 2,735 | 0.2 % of the population; recorded as unresolved |
| D5 | `merge_compounds` is not applied | this study's Whisper-normalizer scorer does not implement it | works against us |

### 5.3 Two harness deviations, named, and why neither weakens a rail

**(a) The scorers.** The manifest declares `["asr-wer-esb-whisper", "asr-wer-esb", "cost"]`, not
`asr-wer-whisper`/`asr-wer`. That is forced, not preferred. `data.references.reference_tokens`
resolves exactly one `.nlp` file per **call** id under the locked carrier tree, and
`contracts.FrozenCoreGate.verify_reference_identity` fails closed for any id D1 does not record in
that carrier's `nlp_references` manifest. An ESB utterance is neither, and manufacturing 2,735 `.nlp`
files inside a locked dataset tree D1 hashed is not an option.

So the utterance references travel their own rail, exactly as the two other carriers' gold already
does — `a2t-toolcall` and `slurp-slu` reach their gold through `data.audio2tool`/`data.slurp` and
never touch `data.references` either. The two new scorers live in
`reproduction/esb_reference.py` (outside the E0 D3 frozen `scoring/` package), are registered from
`core/scorers.py` (the one canonical registration site), and use the **same** frozen
`scoring.wer.align`, the **same** `scoring.normalize.tokens_v1` and the **same** vendored Whisper
normalizer as their carrier-layer twins. The only difference between `asr-wer-esb-whisper` and
`asr-wer-whisper` is where a row's reference comes from, which is what keeps the Earnings-22 number
comparable metric for metric with the Earnings-21 one.

The D1 reference-identity guarantee is **replaced, not skipped**:
`reproduction.esb_reference.load_esb_references` re-hashes the derived reference layer against its
committed receipt (`3266c7ba…`, pinning `f6fddf40…` and 2,735 rows) on every call and refuses on any
drift, on a row count that disagrees, on a duplicate id, on an empty sentence, on a path that escapes
the data root, and on any outputs row whose sample id the pinned layer does not contain. Every formal
WER is `f(frozen scoring code, hypothesis text, reference bytes)`: the code is unchanged, the
hypothesis is bound by the bundle contract's `response_text_sha256`, and the reference bytes are bound
by that receipt.

`entity-wer` is absent by construction, not by choice: `data.carriers` registers no entity layer for
`earnings22-original` (no `wer_tags` sidecar exists), so `entity_scoped_carrier_lock_keys` fails it
closed.

**(b) Payload confinement.** `core.model.binding` confines every payload's `media_relpath` under
`binding.carrier_root`, which `FlightRuntime` resolves through its injectable `carrier_root_resolver`
seam. This flight points that seam at the derived-utterance root instead of the carrier asset dir,
because the derived WAVs deliberately live outside the locked tree. This **tightens** confinement: the
derived root holds this roster's 2,735 WAVs and nothing else, where the carrier root holds 125 MP3s
and every transcript. The per-sample exact-relpath binding check and the D1 media-identity re-hash are
both unchanged and both still run — the run may still only ever send exactly the file the binding and
the supplement vouch for, sample by sample.

## 6. Scoring and decision rule

One job, one complete manifest, through `core.scoring_batch` — never sharded, never averaged across
shards.

* **Paper-facing number**: `asr-wer-esb-whisper` **corpus** WER — total S+D+I over total reference
  words, Whisper `EnglishTextNormalizer` on both sides, whitespace tokenization. This is the
  normalizer family and the aggregation the published Earnings22 rows use.
* Reported beside it: the mean of per-utterance Whisper-normalized WER; the frozen `saea-scoring-v1`
  corpus and mean; substitutions/deletions/insertions and reference words; and `cost`.

Mandatory slices in the verdict: the per-call table for all six calls under both normalizers;
natural-mixture (corpus) and equal-call weightings; the duration decomposition, with the 74 utterances
over 20 s reported separately; the three clamped utterances named; and the Earnings-21 full-44 number
(8.200) beside this one with the segmentation, corpus and metric differences named rather than
compared silently.

Let `W` be the corpus Whisper-normalized WER over the 2,735 utterances.

* **band test**: `W <= 12.79` (9.79 + 3.0).
* **floor test (strict)**: `W <= 11.59`, whisper-large-v3 on the same column. The loose floor
  (base.en 15.09) is reported beside it whatever the outcome, as are the other seven floors.
* **ALIGNED** = band test and strict floor test both pass.
* **ALIGNED-BETTER** = `W < 6.79`.
* **NOT ALIGNED** otherwise, with the failing half of the rule named and the gap decomposed call by
  call and against D1–D5.

### Caveats that travel with the number

* The two vendor reports of this same frozen model differ by **2.5 points** (9.79 vs 12.3), which is
  most of the owner's 3-point tolerance. "Consistent with both" is the strongest honest reading.
* The Open ASR Leaderboard applies `merge_compounds=True`; **we do not**. That works against us.
* The published row's precision and prompt are not published. Q4_K_M and this study's instruction are
  named deviations, not controls.
* The **fstalign family is never mixed in**: fstalign is not installed and was not run.
* `saea-scoring-v1` figures are a different metric family and must never be reported as an alignment,
  however close they land.

## 7. Sequence and invariants

segment-table receipt → utterance roster + derived reference layer + D1 media supplement +
calibration-exposure successor receipt → config fragments → this preregistration → **exposure rows
before any contact** → prompt-fit (zero tokens, section 5.1) → wire check on a clean committed tree
(zero sockets) → 4-row smoke with its own exposure row → go/no-go → flight →
`core.scoring_batch` → verdict `docs/readiness/2026-09-04-e22-esb-shortform-alignment-v1-verdict.md`
+ `result-summary.json` → every exposure row closed COMPLETED with hashes → a note appended to
`docs/readiness/2026-09-04-scoring-alignment-audit-slurp-earnings.md`.

Invariants: `pytest` green apart from the documented pre-existing failures;
`python scripts/checks/engineering_base_check.py` passes; the tree clean and committed before the
wire check, before the smoke and before the flight, and until finalize; `PYTHONDONTWRITEBYTECODE=1`;
no `pip install`, no venv change, no rebuild or checkout of `/home/chao/llama.cpp-featcache` (detached
at `04ccc72a`), no ffmpeg, no fstalign; **no read of any confirmatory call other than the six**; GPU
idle and `enforced.power.limit` at 100.00 W before takeoff; references never enter the request path;
`FrozenCoreGate` decides legality and causes get fixed, not gates.

**Recovery.** At most one recovery re-registration, with a fresh run id and a fresh exposure row (the
budget is metered cumulatively across attempts of a run id). The full-44 flight died once on a CUDA
illegal memory access about 1 GB from the edge of the card; this geometry starts 4 GB further back
with graphs already disabled, so that specific cause is pre-empted rather than rediscovered. If a
second attempt also fails, the flight stops under the owner's own rule and the fix is proven on a
4-row dry run before anything else flies.

### Not authorized by this preregistration

No mechanism arm. No read of the other 109 confirmatory calls. No ESB validation-split read. No second
read of these six calls. No Q8_0 cell. No fine-tuning comparison. No fstalign install. No self-run
whisper calibration anchor (that would be its own registration). No test tuning, no paper-scale work,
no superiority or generality claim.

---

## Phase log

### 2026-09-04, Phase 1 — materials, receipts, fragments, registration

Segment table pinned and extracted (2,735 rows, `7ef6911b…`; all four parquet shards locally
re-hashed against their published LFS oids). 2,735 utterances cut in 52 s on six workers,
19,494.608437 s of audio, 623,947,810 bytes, three end boundaries clamped. Roster
(`72be506b…`), derived reference layer (`f6fddf40…`), reference-layer receipt (`3266c7ba…`), D1 media
supplement (`caa221ec…`) and the calibration-exposure successor receipt (`f2b3be4b…`) all written.
Two scorers registered. Config fragments composed and both split identity hashes reproduced live:
flight `9285b321…`, smoke `4de75c34…`.

### 2026-09-05, Phase 2 — wire check

Commit `229d6e63`. Both cells on the clean committed tree against
`core.flight.runtime`'s `WireCheckGate` and `WireCheckTransport`: the real compose, the real
adapter and its roster-bound samples, the real payload binding and allowlist, the real
`FrozenCoreAdapter` accounting, the real manifest builder, the real bundle verifier and both new
scorers. Smoke cell 4 of 4, flight cell **2,735 of 2,735**, `seal_and_score` OK on both, and
`core.scoring_batch` scored the flight cell's sealed manifest as one whole-manifest job with
`verified: true`. Zero model contacts, zero servers, zero sockets. The WER figures in those
receipts are computed over the transport's canned response and measure nothing.

Running the FLIGHT cell here, not just the smoke cell, was deliberate: `asr-wer-esb-whisper` and
`asr-wer-esb` had never run on a sealed bundle, and the Earnings-21 flight is the reason to care —
that manifest sealed COMPLETED and then would not score, after the GPU time was already spent.

### 2026-09-05, Phase 3 — the smoke, and the go/no-go

Commit `f6ed4e0d`. Row `SAEA-E22-ESB-SHORTFORM-ALIGNMENT-SMOKE-V1`, attempt
`attempt-20260905T043920Z-a3a450`: **COMPLETED and FINALIZED, 4 of 4**, 56.76 speech seconds, in
48 seconds end to end.

All three reads affirmative. **Scorers**: both ESB scorers returned per-sample rows through
`core.scoring_batch` with `verified: true` on live outputs. **Geometry**: `-c 32768 -np 8` served
with the resident bf16 mmproj, eight slots at `n_ctx` 4,096 each, llama-server started with 23,119
MiB free of 24,462, no out-of-memory and no CUDA fault. **Throughput**: mean latency 2.213 s per
contact, projecting 2,735 contacts at eight slots to about 757 s (0.21 GPU-h) against a 2.0-hour
ceiling; the four smoke rows average 14.19 s of audio against the roster's 7.13 s, so the
measurement is biased long and the projection is an upper bound, not a rate measurement. **GO.**

**The window fit, measured live.** Prompt tokens 62 / 140 / 244 / 530 against the
`13 × ceil(audio_seconds)` speech costs 13 / 91 / 195 / 481 — a text envelope of **exactly 49
tokens on all four requests**. Worst prompt 530, worst required 1,556 against a 4,096-token slot,
**×2.63**; largest completion 141 against a 1,024 ceiling, which therefore never binds. Section
5.1 bounded that envelope at "well under 100" and derived a worst prompt of about 530; the measured
figure is 530 exactly.

**One defect of my own, caught before any contact.** The flight runner went `preflight → serve`,
and `FlightStageOrderError` refused it: `FLIGHT_STAGES` requires the `preprocess` stage for every
arm, packet or not. Nothing was spent — no contact, no llama-server, no attempt reserved, no ledger
row consumed. The runner now runs `preprocess`, which for this raw-audio arm promotes nothing and
records that it did. Caught by flying the smoke rather than by reading the code, which is what a
4-row smoke is for.

One observation recorded so a future reader does not misread it: the server log prints
`graphs reused = N` per slot. That counts llama.cpp's own host-side graph reuse, not CUDA graph
capture, and it appears identically in the sealed `SAEA-E21-FULL44-DIRECT-BASELINE-V2` log, which
set the same `GGML_CUDA_DISABLE_GRAPHS=1`. The session receipt records `server_env_keys` only for a
non-legacy role, so the flight additionally reads the live server process's own environment and
records it.

### 2026-09-05, Phase 4 — the flight, and the verdict

Row `SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1`, attempt `attempt-20260905T044432Z-8f23ee`, study commit
`7f5d2837`, config hash `179c08ef`, protocol hash `d74adf8d`, manifest sha256 `dbfa6efb…`:
**COMPLETED and FINALIZED, 2,735 of 2,735 utterances**, 19,494.608 speech seconds (5.415 h), 773.5 s
of dispatch at eight slots plus 12.0 s of startup = **0.226 GPU-h** against a 2.0-hour registered
ceiling, 25.2x realtime, peak VRAM 22,506 MiB of 24,463, peak power 90.41 W against the 100.00 W
enforced limit. One attempt, no recovery, no CUDA fault, no out-of-memory, no skipped contact.

The window fit held live over all 2,735 requests: largest prompt **530 tokens**, exactly the figure
section 5.1 derived before any contact; largest completion 137 against a 1,024 ceiling, which
therefore never binds. `GGML_CUDA_DISABLE_GRAPHS=1` was read back from the live server process's own
environment rather than assumed.

**Verdict: NOT ALIGNED.** Corpus WER under the Whisper `EnglishTextNormalizer` is **15.937 %**
against the published 9.79 (+6.15) and the cross-read 12.3 (+3.64). Band test (≤ 12.79) fails,
strict floor (≤ 11.59) fails, loose floor (≤ 15.09) fails by 0.85; only `whisper-tiny.en`'s 19.12 is
cleared. Full verdict, with the per-call table, the duration decomposition and the gap analysis:
`docs/readiness/2026-09-04-e22-esb-shortform-alignment-v1-verdict.md`.

The gap has a shape. Insertions are 59.2 % of all errors and the hypothesis is systematically longer
than the reference (ratio 1.0749). An **oracle** cut of each hypothesis to its own reference word
count — a diagnostic upper bound, not an achievable result — moves the number 5.48 points to 10.456,
inside the band and under the strict floor, while collapsing word repeats buys at most 0.33 and
dropping every utterance under 3 s buys 1.22. What fails here is output discipline, not acoustic
recognition, and that points at deviation D3 (the prompt, held byte-identical to the Earnings-21
flight's on purpose, against a cleaned rather than verbatim reference) and D1 (one sentence-length
clip with no context). Quantization, D2, is untested by this flight and remains the live suspect for
the residual.

Nothing was tuned on this population. The owner allowance is spent: the six calls are now
calibration-exposed, and the 109 remaining confirmatory calls were not named, loaded, decoded or
sent.
