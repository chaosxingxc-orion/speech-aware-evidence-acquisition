# Capability-ladder carrier inventory and split-policy draft (2026-08-17)

Status: **DRAFT for owner review.** Nothing here registers a split, binds a probe, or authorises
a touch. Every carrier that is to be flown still needs its own split-identity registration before
first touch (legality doctrine 2026-08-15, "Named traps": the "no new sample identity" boilerplate
does not extend to new carriers).

Scope of this pass: on-disk byte inventory of the capability-ladder carriers named in the
2026-08-17 pivot (L2 ContextASR-Bench, L3 SLURP, L4 SLUE-SQA-5 / LibriSQA / AMI, L5 Audio2Tool),
plus a feature-cache prebuild feasibility assessment. **No model was loaded, no `llama-server` was
started, no audio was decoded, and no GPU work was run.**

Disclosure, on the record: establishing feature-cache coverage required reading the raw bytes of
350 Audio2Tool wav files to compute their llama.cpp media ids (FNV-1a-64, §4.2). That is a
model-free inventory read of the same class as D0 acquisition verification — no model contact, no
reference/gold layer opened, no derived artifact written, nothing outside a scratchpad. It is
recorded here rather than as an exposure row because it created no exposure; if strict parity with
the `SAEA-TOOL-precut-buf90-v1` hashing precedent is wanted, a `model-free-check` row can be added,
but it would have to be marked as an after-the-fact record, not a pre-registration.

---

## 1. Inventory (verified on disk, 2026-08-17)

All paths relative to `$SPEECHRL_DATA_DIR/datasets/`. Lock identity: every carrier below is pinned
in umbrella `docs/datasets.lock.json` — `audio2tool`, `contextasr-bench`, `slue-sqa-5`,
`librisqa-metadata`, `ami-meeting-corpus` in `asset_catalog`; `slurp` in `datasets` (COMPLETE).

| Carrier | Ladder | On disk | Audio present | Format | Ready to encode? |
|---|---|---|---|---|---|
| `audio2tool` | L5 | 9.9 GB | 36,419 wav | wav, extracted | **Yes** |
| `contextasr-bench` | L2 | 91 GB | 28 tar archives | wav inside **unextracted** tars | **No** — extraction required |
| `slurp` | L3 | 26 GB | 283,304 flac (141,652 unique, duplicated under `audio/`) | flac, extracted | Audio yes / **labels absent** |
| `slue-sqa-5` | L4 | 110 GB | 299 parquet | audio **embedded in parquet** | **No** — extraction required |
| `ami` | L4 | 11 GB | 171 wav | wav, extracted, Mix-Headset | **Yes** |
| `librisqa-metadata` | L4 | 164 MB | **none** (5 json) | metadata only | **No** — needs LibriSpeech join |

### 1.1 Per-carrier detail

**`audio2tool` (L5).** Eight tiers, layout `public/tier{N}_{name}_audios/query_{id:05d}/*.wav` with
a sibling `tier{N}_{name}_data/tier{N}.json` manifest carrying identity, media facts
(`path`/`duration`) and gold tool calls. Pool 30,733 items. `tier7_multiturn` rows carry no
top-level `path`/`duration` — media is per turn, and the loader already handles this.

**`contextasr-bench` (L2).** Four JSONL manifests at the root (Speech/Dialogue × English/Mandarin);
audio lives in per-subset, per-language tar archives that are **not extracted**. English only:

| Subset | Items | Audio hours | Mean duration | Entity mentions | Tars |
|---|---|---|---|---|---|
| Speech / English | 15,326 | 188.0 h | 44.2 s | 116,167 | 8 (~21.9 GB) |
| Dialogue / English | 5,273 | 221.9 h | 151.5 s | 58,741 | 6 (~25.6 GB) |
| **English total** | **20,599** | **409.9 h** | — | **174,908** | **14 (~47.5 GB)** |

Record schema (Speech): `uniq_id`, `language`, `duration`, `audio` (relative path into the
extracted tree), `text` (reference transcript), `domain_label`, `entity_list`. Dialogue records
carry a `dialogue` array of per-turn `{role, tts_text, start, end, text}` instead of a flat `text`.
Mandarin subsets are present and are out of scope for this repository's English-only work.

**`slurp` (L3).** Audio is local and extracted: `slurp_real/` 72,395 flac + `slurp_synth/` 69,257
flac, mirrored again under `audio/` (hence the 283,304 raw file count) and also retained as
`.tar.gz`. **No metadata of any kind is on disk** — no `train`/`devel`/`test` JSONL, no
`slurp.csv`, no intent/slot annotations. SLURP is therefore audio-without-labels and cannot carry
a scored probe until its metadata is acquired under the umbrella lock path.

**`slue-sqa-5` (L4).** HuggingFace parquet, audio embedded in the rows. Splits present:

| Split | Shards | Rows | Bytes |
|---|---|---|---|
| `train` | 270 | (not counted) | ~99 GB |
| `validation` | 12 | 1,939 | 4.31 GiB |
| `test` | 14 | 2,382 | 5.29 GiB |
| `verified_test` | 3 | 408 | 0.81 GiB |

Row schema: `question_id`, `question_audio`, `question_speaker_id`, `raw_question_text`,
`normalized_question_text`, `document_id`, `document_audio`, `document_speaker_id`,
`raw_document_text`, `normalized_document_text`, `word2time`, `answer_spans`. Note **two audio
objects per row** (question and document); the document is the long one, so encode cost is
dominated by `document_audio`.

**`ami` (L4).** 171 meetings under `amicorpus/<ID>/audio/<ID>.Mix-Headset.wav`, by site: ES 60,
TS 40, IS 38, EN 16, IN 10, IB 7. Individual meetings run roughly 20–90 minutes (e.g. `ES2002a`
40.7 MB ≈ 21 min; `EN2001a` 168 MB ≈ 87 min at 16 kHz mono 16-bit), so the corpus is on the order
of 100 hours. Annotations ship as `annotations/ami_public_manual_1.6.2.zip` and
`ami_public_auto_1.5.1.zip` (both unextracted).

**`librisqa-metadata` (L4).** Metadata only — `LibriSQA-PartI/{test,train}.json` and
`LibriSQA-PartII/{test,train}.json`. Records carry `text` (transcript), `duration`, `question`,
`answer`, and `speech_path` pointing into `LibriSpeech/test-clean/<spk>/<chap>/<utt>.wav`. The
audio must be joined from the local `librispeech` carrier; PartI test JSON is 1.0 MB, PartII test
2.6 MB.

---

## 2. Split-policy proposal

One rule applies to every row: the discovery/tuning surface is the **only** split Stage-2A may
touch, and the held-out surface must not be read, sampled from, or inspected until an owner
decision opens it. Where a carrier's public benchmark ships only one evaluation split, the
proposal is to *partition it by identity* and freeze the held-out half unopened, rather than to
tune and report on the same items.

| Carrier | Discovery / tuning surface | Held out (untouched in Stage-2A) | Metric as published | Counts |
|---|---|---|---|---|
| `audio2tool` | the already-frozen 400-item receipt `r1-audio2tool-sample` (50/tier, seed 20260807, hash `e1d751e6…`), role `discovery` | the remaining 30,333 pool items | per-tier tool-selection accuracy + exact match (EM) of the tool call | 400 / 30,733 |
| `contextasr-bench` | a seeded sample drawn from **Speech/English only** | Dialogue/English entirely; all Mandarin; the un-sampled Speech remainder | WER and named-entity WER (NE-WER) | propose 300–400 of 15,326 |
| `slue-sqa-5` | `validation` (1,939) | `test` (2,382) and `verified_test` (408) — `verified_test` is the human-verified headline surface and must stay sealed | spoken-QA span F1 (frame-level F1 in the SLUE phase-2 protocol) | 1,939 / 2,790 |
| `ami` | a seeded sample of the standard **dev** partition | the standard **eval** partition, and all of train | WER, Mix-Headset (IHM-mix) condition | dev/eval meeting ids must be taken from the official partition lists in `ami_public_manual_1.6.2.zip`, never hand-rolled |
| `librisqa` | a seeded sample of `LibriSQA-PartI-test.json` | `LibriSQA-PartII-test.json`; both train files | PartI open-ended QA score; PartII multiple-choice accuracy | TBD after the LibriSpeech join is verified |
| `slurp` | **none — not admissible** | — | intent accuracy + SLU-F1 | labels absent on disk |

Rationale notes:

- **Audio2Tool** needs no new policy: the receipt exists, is `split_role: discovery`, and verifies
  through `reproduction.probe_split`. The draft P-A2T probe should draw its 25–40 headroom samples
  from inside that 400, never from the pool.
- **ContextASR-Bench**: Speech (44 s single-speaker) is the cheaper and more directly
  entity-biasing surface; Dialogue (151 s multi-speaker) is the harder held-out surface and is a
  natural later generalisation check. Keeping Dialogue wholly unopened costs nothing now and
  preserves a clean second surface.
- **SLUE-SQA-5**: `validation` is large enough (1,939) to tune on and is not the published headline
  number; `verified_test` is the human-verified subset and is the single most leak-sensitive
  artifact in the whole ladder.
- **AMI**: the standard full-corpus ASR partition already provides train/dev/eval; use it rather
  than inventing one, and read the ids from the shipped annotation package.

All published-metric names above are stated from the benchmarks' conventions and **must be verified
against each dataset card / paper before any of them is bound into a probe registration.**

---

## 3. Label-leak hazards (gold red line, doctrine dimension 1)

Ranked by how easy the mistake is to make.

1. **`contextasr-bench.entity_list` is not automatically legal-tier.** Each record's `entity_list`
   sits in the same JSONL line as the reference `text` and enumerates exactly which in-call terms
   matter for that utterance. Doctrine dimension 3 bounds keying granularity at what deployment
   truly holds — "call identity — yes; which in-call terms/spans matter — must be earned by the
   system's own matching, never by dataset construction." A **per-utterance** `entity_list`
   supplied as evidence is therefore dataset-constructed selection, i.e. **ceiling tier**
   (`span_source` gold-derived), even though the benchmark itself ships it as the intended context.
   A legal-tier ContextASR arm must instead pool a **global or domain-level** roster (e.g. keyed by
   `domain_label`) and make the control plane earn the per-utterance match — structurally the same
   contrast as arms A1 (exact) versus A3 (global) in the P-A2T design. **This needs an owner ruling
   before any ContextASR arm is designed**, because it decides whether the carrier's headline
   published setting is reproducible at legal tier at all.
2. **`slue-sqa-5` gold columns travel inside the same parquet row as the audio.** `answer_spans`,
   `word2time`, `raw_document_text` and `normalized_document_text` are all gold. Any extraction
   utility must project to `question_audio` / `document_audio` (+ ids) and write the gold columns to
   a separate, `runtime_prohibited`-flagged, scoring-side artifact. `word2time` is the subtle one:
   it is a gold time alignment and would leak answer localisation.
3. **`librisqa` records carry `text` (the full transcript) and `answer` next to `question`.** Only
   `question` (and the joined audio) may reach runtime.
4. **`audio2tool` tier manifests carry gold tool calls next to `path`/`duration`.** Already handled
   scoring-side by `reproduction.toolcall_gold`; any new utility that touches these manifests must
   project to identity + media facts only. (The inventory in §4.2 did exactly that.)
5. **`ami` reference transcripts** live in the annotation zips; they are scoring-side only, and the
   auto (`ami_public_auto_1.5.1`) annotations are additionally machine-generated and must not be
   confused with the manual references.
6. **`slurp`**: no hazard today only because no labels exist on disk; when metadata is acquired,
   intents and slot fillings become gold.

---

## 4. Feature-cache prebuild: feasibility and verdict

### 4.1 How the cache actually works

The persistent audio feature cache is produced by exactly one writer: the patched `llama-server`
(`docs/patches/2026-08-11-mtmd-feature-cache.diff`, in `tools/server/server-context.cpp`, inside
`server_slot`). `scripts/run_arm_sequence.sh --feat-cache-dir` and
`core/session/lifecycle.py::feat_cache_dir` only ever *route* `LLAMA_MTMD_FEAT_CACHE_DIR` to that
server. There is no prebuild CLI in this repository and no standalone encoder binary built on this
host (`/home/chao/llama.cpp-featcache/build/bin/` contains `llama-server` and the shared libraries,
nothing else; the configured-but-never-compiled `llama-mtmd-cli` and `llama-mtmd-debug` both load
the full text model and neither writes `.feat` files).

Two mechanical facts make a standalone prebuild *possible in principle*:

- **The cache key does not depend on decoding.** The media id is FNV-1a-64 over the **raw encoded
  file bytes**, computed before any decode (`tools/mtmd/mtmd-helper.cpp::fnv_hash`, attached via
  `mtmd_bitmap_set_id`), rendered as a decimal string; the cache key appends `_o<media ordinal>`.
  So a prebuild tool never has to reproduce PCM byte-for-byte to land on the right filename. This
  was verified empirically against the live cache: FNV-1a-64 recomputed in Python over existing
  90 s slice wavs reproduces `.feat` filenames already present in `/home/chao/feat-cache/q4km`.
- **The audio weights are entirely in the mmproj.** `mtmd_init_from_file` uses the text model only
  for metadata (vocab, rope type, an `n_embd` sanity check that is skipped when the value is not
  positive), so a `vocab_only=true` model suffices and the 18.5 GB Q4_K_M GGUF is never loaded;
  the encoder footprint is the 2.2 GB mmproj. Batch fusion is off for the qwen3a graph, so a
  standalone single-chunk encode runs the identical graph.

A standalone prebuild tool would therefore be roughly 120 lines of C++ against the already-built
`libmtmd`/`libllama`/`libggml` (the CMake cache is warm, `GGML_CUDA=ON`,
`CMAKE_CUDA_ARCHITECTURES=120`). Recorded here so the assessment does not have to be redone.

### 4.2 Measured workload — and why the campaign should not run today

The frozen Audio2Tool discovery split was measured exactly (identity + media facts only; no gold
field read, no audio decoded):

| Tier | n | Audio (s) | Cached |
|---|---|---|---|
| tier1_direct | 50 | 102.5 | 0/50 |
| tier2_parametric | 50 | 166.2 | 0/50 |
| tier3_multi_intent | 50 | 255.2 | 0/50 |
| tier4_implicit | 50 | 137.1 | 0/50 |
| tier5_needle | 50 | 546.2 | 0/50 |
| tier6_correction | 50 | 262.0 | 0/50 |
| tier7_multiturn | 50 | (per-turn media, not top-level) | — |
| tier8_intent_blending | 50 | 332.2 | 0/50 |
| **Total** | **400** | **1,801.3 s = 30.0 min** | **0/350** |

Cache coverage is **0/350**: the consumed R1 Audio2Tool read predates the 2026-08-11 feature-cache
patch, so none of its audio was ever cached. The legacy `/home/chao/feat-cache/q4km` directory
holds 34,350 `.feat` files across 3,469 distinct media ids — all earnings21/22, and untouched by
this pass.

**Positive control for the coverage method.** A "0/350" result is only meaningful if the key
computation is correct, so the same code was run against audio known to have been encoded: eight
60 s slices under `derived/obs-slices/SAEA-BENCH-a2wave5/4330115/` (1,920,044 bytes each) resolve
to **8/8** cache hits, each with exactly 8 `.feat` files — consistent with the 8 s window split
(60 s → 8 windows). The method therefore demonstrably hits on cached audio and genuinely misses on
Audio2Tool. Cache integrity was re-checked after the pass: 34,350 files, newest mtime
2026-08-16 14:09 (i.e. predating this session), and `/home/chao/feat-cache/` still contains the
single `q4km` directory — nothing was written, created, moved or renamed.

**The whole probe-backed prebuild workload is 30 minutes of audio, 82.5 MiB, ~350 encoder
chunk-forwards** — on the order of a couple of minutes of RTX 5090 time. Building a bespoke
standalone encoder binary to save that is a poor trade, and it has a real cost: the frozen-core
gate hashes `llama_cpp.binary_path` plus `runtime_libraries`, so a new tool binary is an unhashed
artifact that would need its own receipt entry. The cache warms for free on arm 1 of the P-A2T
probe, and arms A1–A4 then hit it — which is exactly the design the patch was written for.

For every other ladder carrier there is **no frozen split receipt, no registered probe, and no
loader in this repository**. Encoding ContextASR (409.9 English hours), SLUE-SQA-5 (110 GB) or AMI
(~100 h) today would be many GPU-hours spent on audio that no registered probe will fly, which is
the specific waste the campaign brief rules out.

**Verdict: no qualifying feature-cache prebuild work exists today.** No exposure row was created
and no encoder forward pass was run.

### 4.3 What is actually on the critical path (CPU/IO, no GPU)

Feature-cache work is not the blocker for the ladder; *carrier readiness* is. In dependency order:

1. **ContextASR-Bench**: extract the 14 English tars (~47.5 GB) so the JSONL `audio` paths resolve;
   then settle the §3.1 `entity_list` tier ruling; then freeze a receipt.
2. **SLUE-SQA-5**: write a parquet→wav projection for `validation` that emits audio + ids only and
   quarantines the gold columns; ~4.3 GiB to process.
3. **SLURP**: acquire the missing metadata under the umbrella lock path, or drop L3 for now.
4. **LibriSQA**: verify that every `speech_path` in PartI-test resolves against the local
   `librispeech` carrier before proposing counts.
5. **AMI**: extract the official dev/eval partition lists from the manual annotation zip.

Each of these is CPU/IO-bound and can proceed without any GPU or model contact.

---

## 5. Open questions for the owner

1. **ContextASR `entity_list` tier** (§3.1) — legal or ceiling? This decides the L2 arm design and
   whether the carrier's published setting is reproducible at legal tier.
2. **Ladder breadth** — the pivot names six carriers; only Audio2Tool has a frozen receipt. Which
   carriers should get split receipts next, given ContextASR and SLUE both need extraction work
   first?
3. **SLURP** — acquire metadata, or drop L3 from the ladder for this stage?
4. **Standalone mmproj encoder** — worth building for a future large campaign (§4.1 says it is
   cheap and safe to key), or is warming through `llama-server` on arm 1 sufficient indefinitely?
   Note that running the mmproj in-process reaches a component of the frozen core *outside* the
   API-shaped service boundary the consolidated contract describes; even though it loads no LLM and
   produces no answer, that framing deserves an explicit owner ruling before such a tool is built.

   *Resolved 2026-08-17*: stand down. The concept was already owner-endorsed in the 2026-08-16 D4
   correction ruling, so the boundary question is settled in principle, but since no prebuild is
   value-positive the tool is **not** to be built. If it ever is, its build hash joins the
   runtime-identity receipt.

---

## 6. Extraction receipt (2026-08-17, CPU/IO only)

Carrier-readiness extraction executed per §4.3. **No GPU work, no model loaded, no `llama-server`,
no audio sent anywhere** — the GPU sat at P8/~8 W throughout. No exposure row: this is asset
preparation, not a touch. Nothing was downloaded. `ffmpeg` remains absent and unused.

Free space before starting: **2.66 TiB of 3.73 TiB on `/mnt/e` (71.3% free)**; after all work,
30% used — far above the 15% floor.

Manifests all under `$SPEECHRL_DATA_DIR/derived/carrier-manifests/2026-08-17/`.

### 6.1 ContextASR-Bench — English Speech extracted

8 tars → `datasets/contextasr-bench/audio/ContextASR-Speech/English/`, extracted **in place** so the
JSONL `audio` field resolves with no path rewriting. All 8 returned rc=0.

| Metric | Value |
|---|---|
| Bytes extracted | 21,668,044,800 (20.18 GiB) |
| Wall | 1,123 s (18.7 min) |
| Average throughput | 18.4 MB/s |
| Throughput range | 44.3 MB/s (tar 1) → 10.1 MB/s (tar 4) → 18.8 MB/s (tar 8) |
| Files extracted | **15,326** — exactly the JSONL record count |

The throughput decay is 9p directory-size scaling (cost per file creation rises as the directory
fills), briefly compounded by the concurrent SLUE job; it recovered once that finished. Extracting
all 8 tars rather than a subset was deliberate: tar 1 is domain-clustered (`BANK-*`), so a sample
drawn from one tar would be domain-biased.

Verification (`contextasr-speech-english.manifest.json`, per-file table in the `.files.json`
sibling): **15,326/15,326 paths resolve, 0 missing, 0 header failures, 0 duration mismatches over
0.5 s, 25/25 full-decode spot-check passed**, and measured duration **187.98 h exactly equals the
declared 187.98 h**. Total 20.17 GiB.

The tars were left in place unmodified, so the `.speechrl-asset.json` receipt (revision
`7906fd98…`, source `MrSupW/ContextASR-Bench`) stays valid; the extracted tree is a local
derivation of already-verified bytes.

**Finding that sharpens the §3.1 open question.** The subset carries **3,275 distinct
`domain_label` values across 15,326 items — about 4.7 utterances per domain.** A "domain-pooled
global roster" is therefore *not* the clean legal-tier construction it looked like on paper: a pool
of ~5 utterances' entities is barely coarser than the per-utterance `entity_list` and would still
sit very close to oracle selection. A genuinely legal-tier ContextASR roster needs a much coarser
pool — subset-wide entity vocabulary, or a large seeded pool — and the roster-precision ladder
should treat `domain_label` as an *intermediate* dilution level, not as the legal anchor.

### 6.2 SLUE-SQA-5 — `validation` projected to playable audio

12 shards → `derived/slue-sqa-5/validation-audio/{questions,documents}/`.

| Metric | Value |
|---|---|
| Rows read | 1,939 |
| Unique questions | 1,939 — 3.23 h, 0.69 GiB |
| Unique documents | 1,624 — 17.95 h, 3.85 GiB (dedup avoided 315 redundant copies) |
| Total | **21.18 h, 4.54 GiB** |
| Wall | 334 s |
| Failures | 0 missing audio, 0 header failures, 20/20 decode check |

Audio bytes were written **verbatim** from the embedded HF `struct<bytes, path>` (RIFF/wav) — no
re-encode, no resample, so no decoder drift and no ffmpeg dependency. Manifest carries id, path,
bytes, sha256, duration, sample rate, channels, subtype.

**Gold quarantine is enforced at the reader, not after the fact**: the parquet projection requests
only `question_id`, `question_audio`, `document_id`, `document_audio`, so `raw_question_text`,
`normalized_question_text`, `raw_document_text`, `normalized_document_text`, `word2time` and
`answer_spans` were never decoded off disk at all.

### 6.3 AMI — dev partition manifest

`ami-dev-partition.manifest.json`: **18/18 dev meetings resolved**, 9.67 h, 1.04 GiB, Mix-Headset;
all 16 eval meetings confirmed present but deliberately not manifested. No re-encoding (the wavs
are already playable). No annotation or transcript file was opened.

**Provenance caveat, recorded in the manifest itself**: the shipped annotation packages
(`ami_public_manual_1.6.2.zip`, `ami_public_auto_1.5.1.zip`) contain **no** partition list, so the
18 dev ids are the published standard partition transcribed from knowledge and verified to exist on
disk — they are *not* sourced from a shipped file. Cross-check against an authoritative source
before binding them into any registration.

### 6.4 LibriSQA — join spec (no download)

`librisqa-join-spec.json`. The outcome is better than the §4.3 plan assumed: **no acquisition is
needed.** LibriSpeech `test-clean` is already local as
`datasets/librispeech/all/test.clean/0000.parquet` (2,620 rows, 334.2 MiB; `clean/test/0000.parquet`
is an identical duplicate view).

- Join key: LibriSQA `speech_path` stem ↔ parquet `id` (e.g. `6930-75918-0000`), 1:1, globally unique.
- **PartI test: 2,620/2,620 resolvable. PartII test: 2,620/2,620 resolvable.** 5.40 h each.
- Runtime-legal: `question`, `speech_path`, `duration`, parquet `audio`/`id`. Runtime-prohibited:
  LibriSQA `text` and `answer`, and the parquet's own `text` column.
- Materialisation (not yet performed): project `audio` + `id` verbatim, attach `question` by stem;
  ~334 MiB for the full 2,620.

### 6.5 SLURP — what is missing (no acquisition attempted)

Per instruction, nothing was acquired. Confirmed by direct search: **no `.json`, `.jsonl`, `.csv`
or `.txt` file exists anywhere under `datasets/slurp/` to depth 4**, and unlike every other carrier
inspected there is **no `.speechrl-asset.json` receipt** either — SLURP's audio was fetched without
the registration the other carriers carry.

Present: `slurp_real/` 72,395 flac + `slurp_synth/` 69,257 flac (141,652 unique; mirrored again
under `audio/`, hence the 283,304 raw file count), plus the original `.tar.gz` pair. Filename
convention `audio--1504190166.flac`, `audio--1504190166-headset.flac`, `audio-…-synth.flac` — these
are exactly the strings SLURP label records reference in `recordings[].file`.

Missing is the entire label side: the split files (`train.jsonl`, `devel.jsonl`, `test.jsonl`, and
`train_synthetic.jsonl` for the synthetic portion) carrying `slurp_id`, `sentence`, `intent`,
`scenario`, `action`, `entities[]` and `recordings[]`. Upstream is the SLURP repository's
`dataset/slurp/` directory — **file names stated from knowledge and to be verified by the
dataset-expansion survey agent**, which owns acquisition and lock registration. Until those land,
SLURP is audio-without-labels: it can carry no scored probe, and the L3 rung has no metric.
This directly constrains the `rails(b0)` SLURP interface stub (commit `7671e75`), which currently
has no label source to bind to.

### 6.6 Nothing failed to decode

Across all carriers touched: **0 files failed to decode**. 45 files were fully decoded as spot
checks (25 ContextASR + 20 SLUE), and 17,265 audio headers were read (15,326 ContextASR + 1,939
SLUE questions, plus 1,624 SLUE documents and 18 AMI meetings) with zero header failures. Decoding
was `soundfile`/`librosa` only; `ffmpeg` was never invoked and remains absent.
