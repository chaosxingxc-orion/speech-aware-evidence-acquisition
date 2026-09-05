# Earnings-22 DEV ESB prompt A/B, v1 preregistration

Status: **REGISTERED 2026-09-05**, on the owner directive of 2026-09-05 ("align the PROMPT and the
model usage first"). One experiment, profile `baseline-reproduction`, **two paired arms**, one
population, plus one shared 4-row smoke. Written before any model contact.

| Run id | Cell | Population | Fragments |
|---|---|---|---|
| `SAEA-E22-DEV-ESB-PROMPT-A-V1` | `E22-ESB-DEV-A` | 6,038 ESB utterances of the ten Earnings-22 **dev** subset10 calls, 39,292.647 s (10.915 h) | dataset `earnings22-esb-dev-utterances-6038`, baseline `e22-esb-dev-prompt-a`, model `q4km-e22-dev-esb-mmproj-gpu-04ccc72a-np8-c40960`, experiment `e22-dev-esb-prompt-ab-v1` |
| `SAEA-E22-DEV-ESB-PROMPT-B-V1` | `E22-ESB-DEV-B` | the same 6,038 utterances | the same, with baseline `e22-esb-dev-prompt-b` |
| `SAEA-E22-DEV-ESB-PROMPT-AB-SMOKE-V1` | `E22-ESB-DEV-SMOKE-4-A` and `-B` | 4 rows of the same roster, chosen before any contact | dataset `earnings22-esb-dev-utterances-smoke4`, both baselines, same model, experiment `e22-dev-esb-prompt-ab-smoke-v1` |

Predecessor: `docs/readiness/2026-09-04-e22-esb-shortform-alignment-v1-verdict.md`
(`SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1`, **NOT ALIGNED**, corpus Whisper-normalized WER **15.937**
over all 2,735 published ESB **test** utterances against the same frozen model's published zero-shot
**9.79** and cross-read **12.3**). That flight supplies the harness, the entry point, the build, the
audio path, the decoding parameters, the scorers, the reference rail, the receipt shapes, the smoke
design and **arm A's instruction**. Everything it does not supply is named in section 5.

## 1. Why this experiment exists

The test flight's gap has a shape, and the shape is not recognition. Insertions were **59.2 %** of all
errors (4,612 of 7,796), the hypothesis was **1.0749×** the reference length, and an oracle cut of
each hypothesis to its own reference word count — a diagnostic upper bound, never an achievable
result — moved the corpus figure 5.48 points to 10.456, inside the band and under the strict floor.
Collapsing word repeats bought at most 0.33 and dropping every utterance under 3 s bought 1.22.

The instruction that produced that output is this study's own three-sentence ASR instruction, held
byte-identical to the Earnings-21 full-44 flight's **on purpose**, because that is what made the two
Earnings numbers comparable. On Earnings-21, whose `.nlp` references are themselves verbatim, it
scored 8.200 and ALIGNED. On the ESB Earnings-22 column, whose references are Rev's **cleaned**
sentence transcripts, the same instruction asks for exactly the disfluent, continuing output the
reference does not contain. That is deviation D3 of the test preregistration, and it is now the
leading suspect.

The confirmatory read of those six calls is spent. The prompt must therefore be chosen on the **dev**
split, which is the split this study may optimize on, and the owner then decides whether a second and
final test read is made.

### 1.1 One correction to the mission brief, made in the open

The 2026-09-05 mission brief names the flown instruction as `configs/probes/r4_transcribe_nocontext.txt`
("transcribe the spoken English exactly, word for word"). That is a mis-naming. The instruction
`SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1` actually sent — recorded in
`configs/baseline/e22-esb-direct-zero.json`, in section 5 of the test preregistration, and in the
sealed protocol hash — is:

> Transcribe the speech verbatim exactly as spoken. Never insert, repeat, or add any word you do not
> clearly hear in the audio. Output only the transcript text.

`configs/probes/r4_transcribe_nocontext.txt` carries a *different* text ("Transcribe the speech in the
audio exactly, word for word. Output only the transcript.") and no Earnings flight of this study has
ever sent it. The brief's binding requirement is "the **flown** instruction, byte-identical", and arm
A is those bytes. Using the probe file instead would have made the dev arm-A number unreadable
against the sealed 15.937, which is the one comparison arm A exists to support.

## 2. Population and materials

**Split role.** These ten calls — 4453225, 4469088, 4470684, 4474506, 4479944, 4481952, 4482383,
4482613, 4483937, 4485192 — **are** this study's registered `earnings22-original` **dev** subset10
(`docs/receipts/splits.json`, split `dev`, count 10, identity
`89b178d6b1ef46d9ca820ae54349e3d2099c60cde6d6b753ef9f66137c310028`). No owner allowance is involved
and none is claimed. **No confirmatory call is named, loaded, decoded, scored or read**, and the six
calibration-exposed ESB test calls stay a separate population with a separate roster, a separate
reference layer and a separate derived media root.

**The segment table.** `sanchit-gandhi/earnings22_split`, split **`train`**, at the same pinned
revision `f9fb35f4134e32b9c8100199d949398fd6d08a5f` the test flight used. Only the same six metadata
columns are read — `source_id`, `segment_id`, `sentence`, `start_ts`, `end_ts`, `id` — through a
pyarrow **column projection**, so the parquet `audio` column is never materialized. Receipt:
`docs/checks/speech-aware-evidence-acquisition/2026-09-05-e22-dev-esb-prompt-ab-v1/segment-table/segment-table-receipt.json`
(`2ff3aa88…`), extracted table `51257011…`, **6,038 rows**.

**Confinement at extraction, and why it is not optional.** The train split carries 113 source calls
and 103 of them are in this study's `earnings22-original` confirmatory split. The extractor therefore
reads a record batch at a time and drops every row whose `source_id` is not one of the ten dev calls
**before it can reach a list, a file, a log line or a receipt**. No confirmatory sentence, boundary or
per-call count is written down, printed or counted anywhere. The receipt says so in its own words.

**The 55 train shards (22.0 GB) are NOT downloaded.** The column projection reads them over ranged
GETs through `HfFileSystem`, so each shard's pin rests on the published git-LFS `oid` — which is that
file's SHA-256 — rather than on a local re-hash. The receipt records `locally_rehashed: false` for
every one of them, exactly as it records `true` for the four test shards that were fetched. That is a
weaker pin than the test population's and it is recorded as such rather than glossed.

**All ten dev calls appear in the ESB train table.** None had to be dropped.

| call | utterances | audio seconds |
|---|---:|---:|
| 4453225 | 635 | 4,311.155 |
| 4469088 | 922 | 4,546.872 |
| 4470684 | 589 | 4,665.640 |
| 4474506 | 633 | 3,868.831 |
| 4479944 | 588 | 3,810.266 |
| 4481952 | 632 | 3,620.409 |
| 4482383 | 469 | 3,407.436 |
| 4482613 | 592 | 3,890.575 |
| 4483937 | 517 | 3,559.561 |
| 4485192 | 461 | 3,611.903 |
| **all ten** | **6,038** | **39,292.647** |

Duration distribution: median 5.520 s, p90 12.860 s, p99 22.280 s, max **78.360000 s**
(`4470684-13`), min 0.219938 s; 103 utterances exceed 20 s, 12 exceed 30 s, one exceeds 60 s.
**One** utterance (`4481952-631`) has an `end_ts` past the decoded parent and is clamped to it; it is
named in the roster receipt and will be named again in the verdict.

**The audio.** The ten calls come from the locked `earnings22-original` asset already on disk. Each
parent MP3 is decoded exactly once through `reproduction.obs_loop.decode_parent_pcm` — the same
librosa 16 kHz mono decode every earlier slice in this repository used; **ffmpeg is absent by design
and was not used** — and each utterance is written as a 16 kHz mono WAV through
`reproduction.obs_audio.write_wav_bytes`. Derived media live at
`$SPEECHRL_DATA_DIR/derived/e22-esb-utterances/dev-v1/<call>/<id>.wav`, 1,257,630,368 bytes, and
never enter Git. They deliberately do **not** go inside the locked carrier tree, and they use a
**different derived root** from the 2026-09-04 test population's `v1/`, so each population's
confinement root holds exactly its own roster's media.

Roster receipt `20437bcb…` (`ids_sha256` `dfa2ec01…`, `items_sha256` `37e45e51…`).

**Identity.** The 6,038 utterance ids enter D1's identity closure through the additive media
supplement `docs/receipts/artifacts/d1-e22-esb-dev10-utterances.json` (schema
`saea-d1-media-supplement-v1`, `ad01c4ec…`, `manifest_sha256` `96c4a762…`). Every id is new to the
immutable artifact by construction, and the builder refuses any utterance whose parent call is not
one of the ten *and* whose parent bytes do not equal what D1 itself recorded.

**References.** The `sentence` column, verbatim, in a derived reference layer at
`$SPEECHRL_DATA_DIR/derived/e22-esb-segment-table/e22-esb-dev10-references.jsonl` (6,038 rows,
104,808 whitespace words, `8da3a65d…`, receipt `e2030bde…`). It is never committed, never inside the
carrier tree, and **never in the request path**. `reproduction.esb_reference` now resolves **two**
hash-pinned layers — the sealed 2026-09-04 test layer and this one — verifying each independently and
refusing any id that two layers both claim. The test layer's bytes are not touched: the sealed
manifests pin its SHA-256 and it must never move.

**Split identity hashes**, reproduced live before registration: flight `fc14c98b…`, smoke
`5f0b843c…`.

## 3. The two arms

Exactly one thing differs between them: the `task_instruction` string.

**Arm A (control)** — byte-identical to what the sealed ESB test flight sent:

> Transcribe the speech verbatim exactly as spoken. Never insert, repeat, or add any word you do not
> clearly hear in the audio. Output only the transcript text.

**Arm B (aligned candidate)** — the Qwen3-Omni authors' own English ASR prompt, **not invented here**:

> Transcribe the English audio into text.

Source, quoted with its URL and fetch date, from **two independent official places**:

1. The **Qwen3-Omni-30B-A3B-Instruct model card**, section *Setting for Evaluation* → *Default
   Prompts*, row *Auto Speech Recognition (ASR) for Other languages*:
   `Transcribe the <language> audio into text.`
   <https://huggingface.co/Qwen/Qwen3-Omni-30B-A3B-Instruct> (`README.md` fetched 2026-09-05, 90,295
   bytes, sha256 `0e44065c4c4a2707…`).
2. The **official cookbook** `cookbooks/speech_recognition.ipynb`, which spells that template out for
   English verbatim as `"Transcribe the English audio into text."`
   <https://github.com/QwenLM/Qwen3-Omni/blob/main/cookbooks/speech_recognition.ipynb> (fetched
   2026-09-05, sha256 `3827631fb46374a944178dae1e9318e94c99429be414fec4f79fd6bfdace2b3f`).

No variant, no few-shot, no post-processing, no other change of any kind.

### 3.1 What the same official section says that arm B does NOT do, named

The model card's *Setting for Evaluation* section also states, for the same evaluation protocol:

* **"No `system prompt` should be set for any evaluation benchmark."**
* "The question or prompt should be input as user text. Unless otherwise specified by the benchmark,
  the text should come **after** multimodal data in the sequence."

This experiment does **neither**. Both arms keep the base `TaskAdapter.assemble_prompt` shape the
sealed test flight used — one system message carrying the instruction, one user message carrying the
audio — so that exactly **one** factor differs between A and B. Message placement and the presence of
a system role are a **second, unflown suspect** (deviation G2), named here and reported to the owner
rather than confounded into this contrast.

## 4. Budget (ExecutionPlan, registered)

| | plan (per arm) | registered ceiling (per arm) | basis |
|---|---:|---:|---|
| model calls | 6,046 | 6,350 | 6,038 rows × 1 contact + 8 canaries; ceiling about 5 % above |
| speech audio seconds | 39,300 | 41,300 | 39,292.64675 for one pass; ceiling about 5 % above |
| GPU hours | 0.5 | 0.75 | see below |
| paid API spend | 0 | 0 | in force, unchanged |

Across the experiment: **12,092 planned calls**, **78,585 s (21.83 h) of audio**, **1.0 planned /
1.5 registered GPU-hours**.

| smoke | plan | registered ceiling | basis |
|---|---:|---:|---|
| model calls | 20 | 60 | 4 rows × 1 contact × 2 arms = 8 plus headroom |
| speech audio seconds | 200 | 400 | 96.959875 per arm, 193.92 for both |
| GPU hours | 0.5 | 1.0 | essentially all of it model load |

GPU-hour basis: the sealed ESB test flight served 2,735 contacts over 19,494.6 s of audio in **0.226
GPU-h** at `-np 8` with CUDA graphs disabled — 3.54 contacts/s, 25.2× realtime. Each arm here is
2.21× that in contacts and 2.02× in audio, so about **0.47 GPU-h** is expected per arm and 0.75 is
1.6× that.

`core/model/adapter.py` enforces `planned_model_calls` and `planned_speech_audio_seconds` **across
all attempts of a run id**. A partly spent dead attempt therefore cannot be re-run under the same run
id; the one permitted recovery takes a fresh run id and a fresh exposure row. The smoke deliberately
flies **both** arms under one run id as two attempts, which `core.attempts` allows and whose budget is
metered cumulatively.

## 5. Protocol

* **Request**: one utterance per contact, both arms. No OBS loop, no windowing — an ESB utterance *is*
  the request. `policy: fixed`, `rails_arms: ["zero-supply"]`, `arm: bare-core`,
  `evidence_source: none`.
* **Prompt shape**: the base `TaskAdapter.assemble_prompt` default, identical in both arms:

  ```json
  [{"role": "system", "content": "<the arm's instruction>"},
   {"role": "user", "content": [{"type": "input_audio", "media_relpath": "derived/e22-esb-utterances/dev-v1/4470684/4470684-13.wav"}]}]
  ```

* **Decoding**: greedy (`temperature: 0`), `max_tokens: 1024`, `id_slot: per-sample`, seed 20260803
  (inert under greedy) — byte-identical to the test flight in both arms.
* **Model**: frozen Qwen3-Omni-30B-A3B-Instruct Q4_K_M, decoder `0751c279…66d`, bf16 mmproj
  `f0dfe825…883` **resident on the GPU**, build `04ccc72a`, no `LLAMA_MTMD_FEAT_CACHE_DIR`.
* **Serving geometry**: `-c 40960 -np 8`, **5,120 tokens per slot**, `GGML_CUDA_DISABLE_GRAPHS=1`.
* **Harness**: `core.flight.FlightRuntime`, entered through `scripts/flights/run_e22_esb_cell.py` —
  the same harness and entry point the sealed test flight used.

### 5.1 Window fit, derived before any contact (zero tokenizer contacts)

Speech cost follows the mmproj encoder's exact one-second window rule
`n_tokens = 13 × ceil(audio_seconds)` — the rule that reproduces all 342 sealed `COST` records of
`SAEA-E-005B-N10-zero`, all 400 per-packet counts of the Audio2Tool calibration promotion receipt,
and the ESB test flight's measured 530-token worst prompt exactly.

* Longest utterance `4470684-13` = 78.360000 s → `13 × 79` = **1,027** speech tokens.
* Text envelope: the ESB test smoke **measured** exactly **49 tokens** on all four of its requests for
  arm A's three-sentence instruction plus a bare audio user turn. Arm B's instruction is one short
  sentence, so its envelope is strictly smaller; 49 is used as the bound for **both** arms and is
  re-measured live in the smoke.
* Worst required ≈ 1,027 + 49 + 1,024 completion + 2 special = **2,102** tokens, in either arm.
* **The sealed test flight's geometry does not fit this roster.** `-c 32768 -np 8` gives a 4,096-token
  slot and `2 × 2,102 = 4,204 > 4,096`, so it fails this repository's own fit rule
  (`slot_tokens >= 2 × worst_required`).
* Declared slot = 40,960 / 8 = **5,120**, a multiple of 512 so the server's own rounding cannot move
  it. Margin 3,018 tokens, **×2.44**. **FITS.**

VRAM is not certified by arithmetic and is not claimed here. `-c 40960` asks for **8,192 fewer** q8_0
KV tokens than `-c 49152 -np 8`, which this card served at a peak of 23,396 MiB of 24,463 on 90-second
encodes; this roster's longest encode is 78.4 s. The smoke, whose first row *is* the 78.36 s worst
case, proves it live before either flight launches.

### 5.2 Deviations, named

| # | deviation | why | expected effect |
|---|---|---|---|
| G1 | serving geometry `-c 40960 -np 8` (5,120/slot) rather than the test flight's `-c 32768 -np 8` (4,096) | this roster's longest utterance is 78.36 s against 36.36 s, and the smaller slot fails the fit rule | none on any transcript — it changes no request byte — and it is identical in both arms, so it cannot touch the contrast |
| G2 | arm B keeps the system-message prompt shape although the model card says to set no system prompt and to put the text after the audio | one factor at a time | unknown; named as the second, unflown suspect |
| G3 | the population is the ten dev calls, not the published ESB test subset | the confirmatory read is spent; dev is the split this study may optimize on | no number here is an alignment verdict |
| G4 | `merge_compounds` is not applied | this study's Whisper-normalizer scorer does not implement it | identical in both arms, so it cancels in the contrast |
| G5 | the 55 train parquet shards are pinned by published LFS oid only, not by a local re-hash | 22.0 GB, and the column projection needs no local copy | a weaker pin than the test population's; recorded, not glossed |

## 6. Scoring, analysis and the decision rule

Two jobs, two complete manifests, through `core.scoring_batch` — never sharded, never averaged across
shards.

* **Paper-facing number per arm**: `asr-wer-esb-whisper` **corpus** WER — total S+D+I over total
  reference words, Whisper `EnglishTextNormalizer` on both sides, whitespace tokenization.
* Reported beside it, per arm: the mean of per-utterance Whisper-normalized WER; the frozen
  `saea-scoring-v1` corpus and mean; substitutions/deletions/insertions and reference words; the
  hypothesis-to-reference length ratio and the insertion share of errors; and `cost`.
* **Paired per-utterance contrast, B minus A**, through `analysis.paired.paired_contrast`: saves /
  harms / ties, the exact two-sided sign test, and **10,000 replicates stratified by source call
  (10 strata), seed 20260903, CI90**. The metric passed to `analysis.paired` is **negated** per-
  utterance WER, so `delta = right − left = A_wer − B_wer` is **positive when arm B is better** and
  `saves` counts utterances arm B improves; the raw `B − A` WER delta is reported beside it so no
  reader has to hold the convention in their head.
* Mandatory slices in the verdict: the per-call table for all ten calls under both normalizers for
  **both** arms; natural-mixture (corpus) and equal-call weightings side by side; the
  insertion/deletion/substitution split and the length ratio per arm; the duration decomposition; and
  `4481952-631`, the one clamped utterance, named.

### Decision rule, preregistered

1. **The arm with the lower pooled corpus Whisper-normalized WER becomes this study's ASR instruction
   for cleaned-reference protocols.** This holds whatever the significance test says: a selection on a
   dev split does not require significance, only a stated rule fixed in advance.
2. **If the CI90 lower bound on the paired delta is not above 0** (negated-WER convention, so "above
   0" means arm B genuinely lower), then **the prompt is not the explanation** for the test flight's
   gap. In that case the next suspect is *named for the owner and not flown*: (a) **context-free
   clipping** — one sentence-length clip with no context and no way to know where it ends, the
   deviation D1 the test verdict already implicated through a length ratio that rises monotonically as
   clips shorten (1.039 at 16–40 s, 1.147 at 2–4 s), together with decoding limits tied to clip
   duration; and (b) **the prompt shape rather than its text** — the official protocol sets no system
   prompt and puts the instruction after the audio (deviation G2).
3. **In every case** the verdict states whether arm B's dev corpus WER would sit inside the 3-point
   band of the published 9.79 (and of the cross-read 12.3) **as an indication only**. These ten calls
   are not the test subset, no published number covers them, and no alignment verdict is issued here.

## 7. Sequence and invariants

segment-table receipt (dev10) → utterance roster + derived reference layer + D1 media supplement →
config fragments → this preregistration → **exposure rows before any contact** → prompt fit (zero
tokenizer contacts, section 5.1, both arms) → wire check on a clean committed tree (zero sockets) →
4-row smoke, both arms, with its own exposure row → go/no-go → flight A → flight B →
`core.scoring_batch` on both → verdict
`docs/readiness/2026-09-05-e22-dev-esb-prompt-ab-v1-verdict.md` + `result-summary.json` → every
exposure row closed COMPLETED with hashes.

Invariants: `pytest` green apart from the documented pre-existing failures;
`python scripts/checks/engineering_base_check.py` passes; the tree clean and committed before the wire
check, before the smoke and before each flight, and until finalize; `PYTHONDONTWRITEBYTECODE=1`; no
`pip install`, no venv change, no rebuild or checkout of `/home/chao/llama.cpp-featcache` (detached at
`04ccc72a`), no ffmpeg, no fstalign; **no read of any confirmatory call, and no second read of the six
calibration-exposed ESB test calls**; GPU idle and `enforced.power.limit` at 100.00 W before takeoff;
references never enter the request path; `FrozenCoreGate` decides legality and causes get fixed, not
gates.

**Recovery.** At most one recovery re-registration, with a fresh run id and a fresh exposure row (the
budget is metered cumulatively across attempts of a run id). If a second attempt also fails, the
flight stops under the owner's own rule and the fix is proven on a 4-row dry run before anything else
flies.

### Not authorized by this preregistration

No read of any confirmatory call. No second read of the six calibration-exposed ESB test calls. No
third prompt variant. No few-shot. No post-processing of any hypothesis. No message-placement arm. No
Q8_0 cell. No mechanism arm. No test tuning, no paper-scale work, no superiority or generality claim.

---

## Phase log

### 2026-09-05, Phase 1 — materials, receipts, fragments, registration

Segment table pinned and extracted from the ESB **train** split with per-batch `source_id`
confinement (6,038 rows over all ten dev calls, `51257011…`; the 55 shards were not downloaded and
are pinned by their published LFS oids alone, recorded as `locally_rehashed: false`). 6,038
utterances cut in 80 s on ten workers, 39,292.647 s of audio, 1,257,630,368 bytes, **one** end
boundary clamped (`4481952-631`). Roster (`20437bcb…`), derived reference layer (`8da3a65d…`),
reference-layer receipt (`e2030bde…`) and D1 media supplement (`ad01c4ec…`) all written.
`reproduction.esb_reference` now carries two hash-pinned layers instead of one; the sealed
2026-09-04 layer's bytes are untouched, and the 2026-09-04 segment-table receipt still regenerates
**byte for byte** from the parameterized builder (`0c923a73…`), which is the regression that proves
the parameterization did not disturb the sealed population.

Both split identity hashes reproduced live: flight `fc14c98b…`, smoke `5f0b843c…`.

**The window fit refused the sealed flight's geometry, before any contact.** This roster's longest
utterance is `4470684-13` at 78.360000 s — 2.16× the test roster's longest — so `13 × 79 = 1,027`
speech tokens plus the measured 49-token text envelope plus a 1,024 completion ceiling plus 2 special
gives a worst request of **2,102** tokens, and `2 × 2,102 = 4,204` exceeds the sealed `-c 32768 -np 8`
geometry's 4,096-token slot. `-c 40960 -np 8` (5,120 per slot, a multiple of 512) gives ×2.44 and is
registered as deviation **G1**. Receipt: `prompt-fit/prompt-fit.json` (`34cc161d…`), zero model,
server, tokenizer and socket contacts.

Arm B's instruction was located, not invented: the Qwen3-Omni model card's own *Default Prompts*
table and the official cookbook's English ASR cell both give it, and both are pinned by URL, fetch
date and SHA-256 in `prompt-source/qwen3-omni-asr-prompt-source.json`. The same official section's
"no system prompt" and "text after the audio" instructions are deliberately **not** adopted, and are
recorded as deviation **G2**, the second and unflown suspect.

Three exposure rows written before any contact: `SAEA-E22-DEV-ESB-PROMPT-A-V1`,
`SAEA-E22-DEV-ESB-PROMPT-B-V1` and `SAEA-E22-DEV-ESB-PROMPT-AB-SMOKE-V1`.

### 2026-09-05, Phase 2 — wire check

Commit `2a0ec125` (registration). All four cells driven on the clean committed tree against
`core.flight.runtime`'s `WireCheckGate` and `WireCheckTransport`: the real compose, the real adapter
and its roster-bound samples, the real payload binding and allowlist, the real `FrozenCoreAdapter`
accounting, the real manifest builder, the real bundle verifier and both ESB scorers over the **new**
dev10 reference layer. Smoke cells 4 of 4 and 4 of 4, flight cells **6,038 of 6,038** and **6,038 of
6,038**, `seal_and_score` **OK** on all four, and `core.scoring_batch` scored each sealed manifest as
one whole-manifest job. Zero model contacts, zero servers, zero sockets. The WER figures in those
receipts are computed over the transport's canned response and measure nothing.

Running both FLIGHT cells here, not just the smoke cells, was deliberate: the dev10 reference layer
had never been resolved by either scorer on a sealed bundle, and the 6,038-row manifest had never
been built.

**One defect of my own, caught here and fixed before any contact.** The first pass wrote each
wire-check receipt straight into `docs/checks/`, which made the tree dirty for the *next* cell's
scoring gate — `core.scorers._assert_scoring_entry_gate` calls `require_clean_study_repo`, so cells
two, three and four came back `SCORING_FAILED` with `?? .../wire-check/` as the whole reason. Nothing
was spent (a wire check contacts nothing), and the fix is procedural: the receipts are written to a
scratch path outside the tree and copied in afterwards. The re-run is the one recorded above.

### 2026-09-05, Phase 3 — the smoke, and the go/no-go

Commit `0d918bae`. Row `SAEA-E22-DEV-ESB-PROMPT-AB-SMOKE-V1`, two attempts:
`attempt-20260905T073142Z-5d279d` (arm A) and `attempt-20260905T073226Z-ab271d` (arm B), both
**COMPLETED and FINALIZED, 4 of 4**, 96.96 speech seconds each, in 43 s and 25 s end to end.

All four reads affirmative. **GO.**

**Geometry.** `-c 40960 -np 8` served with the resident bf16 mmproj, **eight slots at `n_ctx` 5,120
each** read back from the server log, llama-server started with 23,119 MiB free of 24,462, on the
78.36 s worst case — 2.16× the longest encode the sealed ESB test flight ever sent. No
out-of-memory, no CUDA fault.

**Scorers.** Both ESB scorers returned four per-sample rows on both sealed manifests through
`core.scoring_batch` with `verified: true`, resolving references from the **new** dev10 hash-pinned
layer, which no scorer had read on a sealed bundle before.

**The text envelope, measured exactly rather than bounded.** Arm A: prompt tokens 62 / 127 / 218 /
1,076 against the `13 × ceil(audio_seconds)` speech costs 13 / 78 / 169 / 1,027 — an envelope of
**exactly 49 tokens on all four requests**, the same figure the sealed 2026-09-04 ESB test smoke
measured for the same instruction. Arm B: 36 / 101 / 192 / 1,050 against the same speech costs — an
envelope of **exactly 23 tokens on all four**. Section 5.1 used 49 as a bound for both arms; the
measurement confirms it for A and shows B is 26 tokens smaller. Worst required **2,102** (A) and
**2,076** (B) against a 5,120-token slot, **×2.44** and **×2.47**. Largest completion 44 against a
1,024 ceiling, which therefore never binds.

**Wall time.** Projected 1,707 s of dispatch per arm (about 0.48 GPU-h) against a 0.75-hour
registered ceiling per arm, on the sealed test flight's own measured 3.536 contacts/s at `-np 8`.
The four smoke rows average 24.24 s of audio against the roster's 6.51 s, so a projection made from
the smoke's own latency would be biased long and is reported as an upper bound rather than a rate.

One observation recorded so a future reader does not misread it: on the 0.22 s clip `4469088-654`
(reference *"Thank you."*) arm A returned Arabic script and arm B returned *"Thank you."*. One row of
four. It is recorded because the sealed ESB test flight logged the same class of defect — three
Chinese hypotheses on sub-second clips — and it is **not** evidence for either arm.

### 2026-09-05, Phase 4 — the two flights, and the verdict

Study commit `4012521e` for both arms.

Arm A, row `SAEA-E22-DEV-ESB-PROMPT-A-V1`, attempt `attempt-20260905T073641Z-f977d1`, protocol
hash `a6fc27e1…`, manifest `3d230a2c…`: **COMPLETED and FINALIZED, 6,038 of 6,038**, 39,292.647
speech seconds, 1,612.9 s of dispatch plus 12.7 s of startup = **0.4515 GPU-h** against a 0.75
registered ceiling, 24.36× realtime.

Arm B, row `SAEA-E22-DEV-ESB-PROMPT-B-V1`, attempt `attempt-20260905T080709Z-b77462`, protocol
hash `c0b7fb20…`, manifest `776a2751…`: **COMPLETED and FINALIZED, 6,038 of 6,038**, the same
39,292.647 speech seconds, 1,643.9 s plus 10.8 s = **0.4596 GPU-h**, 23.90× realtime. One
attempt each, no recovery, no CUDA fault, no out-of-memory, no skipped contact.

**Verdict: the prompt is NOT the explanation, and arm A wins.** Corpus WER under the Whisper
`EnglishTextNormalizer` is **17.565 %** for arm A and **18.394 %** for arm B — B is **0.830
points worse**. The paired per-utterance contrast (negated WER, 10,000 replicates stratified by
call, seed 20260903, CI90) gives delta **−0.02741**, CI90 **[−0.0449, −0.0133]**, 686 saves, 821
harms, 4,531 ties, sign test **p = 0.00055**; the corpus-level delta under the same rule is
**−0.830** points, CI90 **[−1.653, −0.172]**. Both intervals lie entirely below zero, so the
preregistered rule's second branch fires and the next suspects — context-free clipping, and the
prompt *shape* rather than its text — are named for the owner without being flown. Full verdict:
`docs/readiness/2026-09-05-e22-dev-esb-prompt-ab-v1-verdict.md`.

**The window fit held to the token on both arms**: largest prompt 1,076 (A) and 1,050 (B),
exactly `13 × ceil(78.36) = 1,027` speech tokens plus the 49- and 23-token envelopes the smoke
measured, against a 5,120-token slot. The two arms' prompt-token totals differ by 156,988 =
`6,038 × 26` exactly. Largest completion 130 (A) and 461 (B) against a 1,024 ceiling neither
reached.

**One real defect in a shared module, found here and fixed at the cause.**
`analysis.paired.mcnemar_exact` computed `sum(comb(n, k)) * (0.5 ** n)` and raised
`OverflowError: int too large to convert to float` on this contrast's 1,507 discordant pairs:
the exact integer numerator leaves the float range while `0.5 ** n` has already underflowed to
0.0 for `n > 1074`. The ratio is now an exact `Fraction` converted once — no approximation, no
value the old spelling could compute changes — with a regression test in
`tests/unit/test_analysis_paired.py`.
