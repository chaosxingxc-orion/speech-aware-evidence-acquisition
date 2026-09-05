# Earnings-21, all 44 discovery calls, bare-core direct baseline, v1 — preregistration

One run, profile `baseline-reproduction`, one arm. Written before any model contact.

| Run id | Cell | Population | Fragments |
|---|---|---|---|
| `SAEA-E21-FULL44-DIRECT-BASELINE-V1` | `E21-full44-bare-core-buf90` | `earnings21-original` discovery split, 44 calls, 39.263 h | dataset `earnings21-discovery`, baseline `e21-buf90-zero-locked-scored4`, model `q4km-e21-buf90-mmproj-gpu-04ccc72a`, experiment `e21-full44-direct-baseline-v1` |

Predecessor: `docs/readiness/2026-09-04-scoring-alignment-audit-slurp-earnings.md` (exposure row
`SAEA-E21-MF-SCORING-ALIGNMENT-V1`, receipt
`docs/checks/speech-aware-evidence-acquisition/2026-09-04-scoring-alignment-earnings/`).

## 1. Why this flight exists

The owner's standing 2026-09-04 rule is that each carrier's number must be within 3 points of the
published number or better, and never below a degraded model's published number. Earnings-21 is the
one carrier already inside that band — but conditionally. The sealed bare-core arm
`SAEA-E-005B-N10-zero` scores **7.137 corpus WER under the Whisper `EnglishTextNormalizer`** against
`openai/whisper-large-v3`'s published **9.71**, clearing every degraded floor (medium.en 10.2,
small.en 10.8, base.en 12.5, tiny.en 17.0). Three conditions hang off it:

1. It is **10 of 44 calls** — 8.446 h of the corpus's 39.263 h, 21.5 %. Every published row is all 44.
2. The ten **exclude `4346923`**, the 16 kHz Industrial Goods call (Cementos Argos, 78.5 min, 53
   windows) the Earnings-21 paper singles out as degrading every published system.
3. The number was produced **out of band**: the sealed manifests declare
   `scorers: ["asr-wer", "cost"]`, and `core.scorers.score_bundle` runs exactly the manifest's own
   list, so `core.scoring_batch` could reproduce the sealed `asr-wer` but could not emit
   `asr-wer-whisper` or `entity-wer` for those bundles at all. The audit had to resolve the same
   registered scorer objects directly against the sealed `outputs.jsonl`.

This flight removes all three: **all 44 calls, one protocol, one build, one serving geometry, one
audio path, and the four scorers declared in the manifest itself** so the paper-facing number comes
out of `core.scoring_batch`'s verified path.

## 2. The design decision, and the evidence behind it

The mission offered two designs. **Design (a) — re-run all 44 — is chosen.** Design (b) — run the 34
remaining calls and pool them with the sealed ten — is refused, on its own stated precondition.

Design (b) is admissible only if **build, model file hashes, audio path, window protocol and
instruction** are byte-identical between the sealed ten and the new 34. Read from the sealed session
receipts:

| fact | sealed ten (`SAEA-E-005B-N10-zero`) | sealed 34 (`SAEA-BENCH-kb34-floor`) | this flight | identical? |
|---|---|---|---|---|
| llama-server binary sha256 | `097c96ec…c68` (build `5d9dfcb58`) | `097c96ec…c68` (build `5d9dfcb58`) | `d0b42ace…4f2` (build `04ccc72a`) | **no** |
| decoder GGUF sha256 | `0751c279…66d` | `0751c279…66d` | `0751c279…66d` | yes |
| mmproj GGUF sha256 | `f0dfe825…883` | `f0dfe825…883` | `f0dfe825…883` | yes |
| audio path | `--no-mmproj-offload` (CPU encode) | `--no-mmproj-offload` (CPU encode) | mmproj resident on the GPU | **no** |
| window protocol | fixed 90 s, no VAD trim, no overlap, no tail | same | same | yes |
| instruction | `fixed-batch-zero-locked-buf90` | same fragment | byte-identical text | yes |
| serving geometry | `-c 81920 -np 8` | `-c 65536 -np 16` | `-c 49152 -np 8` | — |
| prompt order | `evidence-first-system-v3` | `evidence-first-system-v2` | `evidence-first-system-v3` | equivalent here |

Two of the five preconditions fail, and they fail structurally rather than by accident:

* **Build.** Both August runs spawned the same retired binary. The pinned current build is
  `04ccc72a2207347ca76161b93fd9d846dd0a8675`
  (`docs/receipts/runtime-q4km-featcache-04ccc72a.json`), the build every September carrier flies.
  New work runs on the pinned build; a pooled number would be half retired-build and half current.
* **Audio path.** Both August runs encoded audio on the CPU against the legacy 26 GB
  `/home/chao/feat-cache/q4km` cache. This flight encodes on the GPU-resident bf16 mmproj, which is
  what the mission requires and what avoids a multi-hour CPU preprocessing pass over 30 h of new
  audio.

The prompt-order difference in the table is **not** a third failure: `core/model/transport.py`
documents and implements that `evidence-first-system-v3` with an empty exemplar bank and no delta
candidates "reduces to EXACTLY v2's shape", and both arms carry `evidence_source: none`.

Two further facts settle it:

* Even the option the mission did not name — pooling the two **already sealed** August runs at zero
  contact — is not one cell. The ten flew `-c 81920 -np 8` and the 34 flew `-c 65536 -np 16`, so the
  44 calls would carry two serving geometries as well as a retired build and a retired audio path.
* The repository already made exactly this call once, on the other carrier: the Audio2Tool
  calibration refused to reuse A0 as a cell because "A0's build (5d9dfcb58) and D2 arm both differ;
  it stays the historical anchor, not a cell."

The two sealed August runs are therefore kept as **anchors, not as data**: the verdict reports the
ten sealed calls re-measured on this build as a build-and-audio-path contrast against their sealed
7.137, which is a better use of them than pooling would have been.

## 3. Population

The whole frozen `earnings21-original` discovery split. No draw. Identity hash
`fcc1b0bc55432d02347dcdf730c6bcef561a9b0ad9605c45b367e1ed3da5d69e`, frozen in
`docs/receipts/splits.json` and recomputed live in the roster receipt
(`docs/checks/speech-aware-evidence-acquisition/2026-09-04-e21-full44-roster/flight-roster-receipt.json`).

| | calls | audio seconds | hours | fixed 90-s windows |
|---|---:|---:|---:|---:|
| all 44 | 44 | 141,348.532 | 39.2635 | 1,593 |
| the sealed ten | 10 | 30,407.739 | 8.4466 | 342 |
| the other 34 | 34 | 110,940.793 | 30.8169 | 1,251 |

The window count is derived, not guessed: in `obs_boundary_mode: "fixed"` the OBS loop advances by
the buffer, so a call of D seconds becomes `ceil(D / 90)` non-overlapping windows with a short last
one. That derivation reproduces the sealed ten's own `calls_used` (342) **exactly**, which is what
licenses it for the other 34. (`SAEA-BENCH-kb34-floor` recorded 1,256 rather than 1,251 because its
figure counts decoded duration while the receipt counts the release's metadata duration; the call
budget carries headroom for the difference.)

Strata, fixed before any result exists, both taken from the release's own
`earnings21-file-metadata.csv`:

* **sector** (9 levels): Basic Materials 5, Conglomerate 4, Consumer Goods 5, Financial 5,
  Healthcare 5, Industrial Goods 5, Services 5, Technology 5, Utilities 5.
* **sample rate** (5 levels): 11,025 Hz 5 calls, 16,000 Hz 6, 22,050 Hz 5, 24,000 Hz 21, 44,100 Hz 7.

Every one of the 44 calls has its media, its `.nlp` reference and its `.wer_tag.json` entity sidecar
materialized (`layers_complete: true`), so none of the four declared scorers can fail on a missing
file after the GPU time is spent.

**Exposure status.** Nothing here is a new sample identity: the frozen ten are exposed many times
over by the E-005 / E-005B / P1R families and the other 34 by `SAEA-BENCH-kb34-floor`
(2026-08-14). Discovery split only; the Earnings-22 confirmatory split is not named, loaded or read.

## 4. Protocol — the sealed arm's own, unchanged

* **OBS**: fixed 90-second windows, `obs_boundary_mode: "fixed"`, `obs_vad_trim_min_seconds: 0` (no
  trim), `obs_condition_tail_chars: 0` (no rolling tail), `obs_preprocess: []`, no overlap,
  `obs_batch_slices: 8`.
* **Instruction**, byte-identical to the sealed arm: *"Transcribe the speech verbatim exactly as
  spoken. Never insert, repeat, or add any word you do not clearly hear in the audio. Output only
  the transcript text."* `configs/baseline/e21-buf90-zero-locked-scored4.json` is byte-identical to
  the sealed `fixed-batch-zero-locked-buf90.json` **apart from the `scorers` list** — verified by
  diffing both fragments with `scorers` removed.
* **Evidence**: none. `evidence_source: none`, no ConEC context, no roster, no bias list.
* **Decoding**: greedy (`temperature: 0`), `max_tokens: 1024`, `id_slot: per-sample`, seed 20260803
  (inert under greedy) — byte-identical to the sealed arm's `q4km-evid-v3`.
* **Model**: frozen Qwen3-Omni-30B-A3B-Instruct Q4_K_M, decoder `0751c279…66d`, bf16 mmproj
  `f0dfe825…883`, on build `04ccc72a`.

### Deviations from the sealed arm, named

| # | deviation | why | expected effect |
|---|---|---|---|
| D1 | build `5d9dfcb58` → `04ccc72a` | new work runs on the pinned current build; it is the whole reason design (a) was chosen | unknown, and measuring it is a deliverable: the ten sealed calls are re-measured and reported against their sealed 7.137 |
| D2 | mmproj moved from the CPU to the GPU | the mission forbids a multi-hour CPU packet preprocessing pass over 30 h of new audio; Factor D was null on Audio2Tool | none on the request bytes (the same encoder file produces the same features); a large throughput gain |
| D3 | `-c 81920` → `-c 49152` (slot 10,240 → 6,144) | pays for 2.2 GB of mmproj weights now resident in VRAM | none: the worst request is 2,258 tokens, so the slot still carries 2.72x |
| D4 | manifest `scorers` `["asr-wer","cost"]` → `["asr-wer-whisper","asr-wer","entity-wer","cost"]` | the audit's defect 1; this is the durable fix | none on the run; it is what makes the paper-facing number come out of the verified scoring path |
| D5 | no `LLAMA_MTMD_FEAT_CACHE_DIR` | the legacy 26 GB cache holds build-`5d9dfcb58` encoder outputs for these very slices, content-addressed on the audio, so pointing at it would silently mix another build's features into this number. It is left untouched and unread | slower than a warm cache would be; homogeneous, which is the point |

## 5. Harness

`core.driver.run_experiment_bundled`, entered through the committed launcher
`scripts/run_arm_sequence.sh` — the exact path that produced the sealed 2026-08-14/15 Earnings arms.

`core.flight.FlightRuntime` was considered first, as the mission prefers, and **cannot** express this
protocol through existing seams: `rails/adapters/earnings.py` yields whole calls with no windowing
(`EarningsSample.audio_seconds` is the whole file), and the 90-second OBS tiling lives in the
registered `core.base` policy `obs-agent-loop` (`reproduction.obs_loop`), which `FlightRuntime` does
not drive. Expressing it there would require a new `TaskAdapter` or controller, which the 2026-09-03
engineering-base rules forbid. The driver path is itself a base seam — a registered policy plus
config fragments — not a new probe module and not a new launcher family; `run_arm_sequence.sh` gains
one backwards-compatible `--execution-profile` flag (default unchanged) because it previously
hard-coded `bounded-discovery-probe`, and this run is `baseline-reproduction`.
`scripts/checks/engineering_base_check.py` must pass.

## 6. Window fit — certified before any contact

`docs/checks/speech-aware-evidence-acquisition/2026-09-04-e21-full44-direct-baseline-v1/window-fit/window-fit.json`,
built by `scripts/build_e21_full44_window_fit_receipt.py`. **Zero model contact of any kind**: this
protocol's envelope was already measured request by request by the sealed run, whose 342 `COST`
records are read out of a trace whose sha256 is re-verified against its sealed run manifest.

* `prompt_tokens − 13 × ceil(audio_seconds)` is the constant **62** on all 332 full windows and 49 on
  the 10 short tails (`ceil` rounds a fractional tail second up, over-counting by 13 tokens;
  62 − 13 = 49). The text envelope is exactly 62 tokens.
* Worst prompt = 13 × 90 + 62 = **1,232 tokens**, which is precisely the sealed maximum.
* Worst required = 1,232 + 1,024 (completion ceiling) + 2 (special) = **2,258 tokens**.
* Declared slot = 49,152 / 8 = **6,144** tokens, a multiple of 512. Margin 3,886 tokens, **×2.72**.
  Fit rule: `slot_tokens >= 2 × worst_required`. **FITS.**
* The completion ceiling never binds: the sealed arm's completions ran 25–392 tokens with **zero**
  requests reaching 1,024.

What this does **not** certify is VRAM. That `-c 49152` plus a GPU-resident 2.2 GB mmproj fits this
machine's 24 GB is a live fact, proven by the smoke's own session receipt and server log before the
flight launches, and by the flight manifest's `peak_vram_mib` afterwards. If the smoke cannot serve
this geometry the documented fallback is `-c 40960 / -np 8` (5,120 tokens per slot, still ×2.27),
recorded as a deviation.

## 7. Budget

| | plan | registered ceiling | basis |
|---|---:|---:|---|
| model calls | 1,750 | 1,800 | 1,593 windows + 157 for `obs_slice_retry_max: 1` retries |
| speech audio seconds | 150,000 | 155,000 | 141,348.532 for one pass + retry headroom |
| GPU hours | 4.0 | 4.5 | the mission ceiling; see the go/no-go below |
| paid API spend | 0 | 0 | in force, unchanged |

`core/model/adapter.py` enforces `planned_model_calls` and `planned_speech_audio_seconds` across
**all attempts of a run id** (`prior_actual_usage`). A partly spent dead attempt therefore cannot be
re-run under this run id; the one permitted recovery re-registration takes a fresh run id and a
fresh exposure row.

**Go/no-go on throughput.** The sealed arm measured a mean per-window latency of 89.15 s at `-np 8`
with the mmproj on the CPU, i.e. about 5.4 windows per minute; extrapolated flat that is 4.9 GPU-h
for 1,593 windows, **over the ceiling**. Moving the encoder onto the GPU (D2) is the whole reason
that extrapolation is not the projection. The smoke measures the real rate on 68 windows of the
identical protocol; the flight launches only if
`1,593 / (measured windows per minute) / 60 <= 4.0 GPU-h`. If it does not, the flight is **not
launched**, the tree is left clean and the measurement is reported.

## 8. Scoring

One job, one complete manifest, through `core.scoring_batch` — never sharded, never averaged across
shards. The manifest declares `["asr-wer-whisper", "asr-wer", "entity-wer", "cost"]`.

* **Paper-facing number**: `asr-wer-whisper` **corpus** WER — total S+D+I over total reference words,
  with the Whisper `EnglishTextNormalizer` applied to both sides and whitespace tokenization. This is
  the aggregation and normalizer family the published Earnings-21 rows use.
* Reported beside it: the mean of per-call `asr-wer-whisper` WER; the frozen `saea-scoring-v1`
  `asr-wer` corpus and mean; `entity-wer` (mention-level `1 − recall` over the `.nlp` `wer_tags`
  sidecar under `normalize_text_v1` — its own normalizer, stated as such, precision 1.0 by
  construction), corpus and per class with each class's gold mention count; and `cost`.

Mandatory slices in the verdict: the per-call table for **all 44 including `4346923`**; the `4346923`
effect as an explicit delta (corpus with and without it); the ten sealed calls on this build against
their sealed 7.137; sector and sample-rate strata in both natural-mixture and equal-stratum
weightings; entity WER by class; throughput.

## 9. Decision rule (preregistered)

Let `W` be the corpus Whisper-normalized WER over all 44 calls.

* **band test**: `W <= 12.71` (9.71 + 3.0).
* **floor test**: `W <= 10.2`, the strict degraded-model floor (Whisper medium.en). The loose floor
  (base.en 12.5) is reported beside it whatever the outcome, as are small.en 10.8 and tiny.en 17.0.
* **ALIGNED** = band test and floor test both pass.
* **ALIGNED-BETTER** = `W < 6.71` (9.71 − 3.0).
* **NOT ALIGNED** otherwise, with the failing half of the rule named and the gap decomposed call by
  call.

Targets, all third-party (no Qwen-published Earnings-21 number exists, so this is a cross-system
comparison and never a reproduction): whisper-large-v3 9.71 (primary), Whisper large-v2 9.7, TRADE
9.75, FastConformer FT+LCA+GT 13.84, Qwen2-Audio-7B 26.06 (normalizer unnamed — a floor only).

### Caveats that travel with the number, verbatim

* Whisper's own long-form decoding heuristics move Earnings-21 by **1.1 points** (10.7 greedy to 9.63
  with previous-text conditioning, Whisper Table 7), so a ±3-point band around 9.71 is only about
  three times the reference literature's own protocol spread.
* The Open ASR Leaderboard applies `merge_compounds=True`; **we do not**. That works against us.
* The **fstalign family is never mixed in**: fstalign is not installed and was not run, and no number
  here is comparable to ConEC's fstalign-based table.
* `saea-scoring-v1` corpus figures happening to land within 3 points of 9.71 is a coincidence between
  two unrelated normalizers and must never be reported as an alignment.

## 10. Sequence and invariants

roster receipt → window-fit receipt → fragments → this preregistration → **exposure rows before any
contact** → wire check on a clean committed tree (`smoke --dry-run`, zero sockets) → 68-window smoke
on `fast-e21-sub3` with its own exposure row → throughput go/no-go → flight → `core.scoring_batch` →
verdict + `result-summary.json` → every exposure row closed COMPLETED with hashes → a note appended
to the alignment audit.

Invariants: `pytest` green apart from the documented pre-existing failures;
`scripts/checks/engineering_base_check.py` passes; the tree clean and committed before the smoke and
before the flight and until finalize; `PYTHONDONTWRITEBYTECODE=1`; no `pip install`, no venv change,
no rebuild or checkout of `/home/chao/llama.cpp-featcache` (detached at `04ccc72a`), no ffmpeg, no
fstalign, no Earnings-22 read; GPU idle and `enforced.power.limit` at 100.00 W before takeoff;
references never enter the request path; `FrozenCoreGate` decides legality and causes get fixed, not
gates.

### Not authorized by this preregistration

No Earnings-22 confirmatory contact. No ConEC supply arm. No mechanism arm. No self-run
whisper-large-v3 calibration anchor (that is its own registration). No fstalign install. No test
tuning, no paper-scale work, no superiority or generality claim.

---

## Phase log

### 2026-09-04, Phase 1 — roster, window fit, fragments, preregistration

Commit `9586e496`. Roster receipt: 44 calls, 141,348.532 s (39.2635 h), 1,593 fixed 90-second
windows, split identity `fcc1b0bc…` recomputed against the frozen receipt, all three layers
materialized for every call, and the window derivation reproducing the sealed ten's 342 exactly.
Window-fit receipt, zero model contact: constant 62-token text envelope, worst prompt 1,232 tokens,
worst requirement 2,258 against a 6,144-token slot (×2.72), completion ceiling never binding.

### 2026-09-04, Phase 2 — exposure rows

Commit `cd77af56`. Both rows written before any contact, both `consumed = no`.

### 2026-09-04, Phase 3 — wire check

Commit `fbc30257`. `core.driver smoke --dry-run` on the clean committed tree: 68 of 68 contacts
through the real compose, split verification, plan validation, OBS slicing, sealing, all four
manifest scorers and finalize, against a fake transport and a no-op gate. Zero sockets, zero
llama-server processes. `asr-wer-whisper`, `asr-wer` and `entity-wer` each returned three per-sample
rows — the proof that a four-scorer manifest actually scores, which is what the sealed August
manifests could not do.

One defect of my own, recorded: the first wire-check attempt ran all 68 contacts and then refused at
finalize because `--ledger-cells` was absent (`core.tracking.ledger_row` is fail-closed on a missing
column). That durably spent the wire-check run id's registered audio seconds, because
`core/model/adapter.py` meters cumulatively across attempts of a run id. It was retired and the
check re-flown under a fresh wire-check run id rather than by raising a budget.

### 2026-09-04, Phase 4 — smoke, and the throughput go/no-go

Commit `9cd2fba0`. Row `SAEA-E21-FULL44-DIRECT-BASELINE-SMOKE-V1`, attempt
`attempt-20260904T222916Z-ef7715`, study commit `75903c26`: **68 of 68 windows, COMPLETED and
FINALIZED in 4 minutes**, 6,034.6 speech seconds, 68 of 100 registered calls.

- **VRAM, the one thing the window-fit receipt could not certify**: `-c 49152 -np 8` with the bf16
  mmproj resident on the GPU peaks at **23,396 MiB of this card's 24,463**. It serves.
- **The window fit holds live**: largest prompt 1,232 tokens, exactly the derived figure; largest
  completion 326; zero requests reached the 1,024 ceiling.
- **Throughput**: mean per-window latency **16.29 s** at eight slots against the sealed arm's
  **89.15 s** with the mmproj on the CPU — a **5.47× speedup**, and the reason the preregistration's
  flat 4.9 GPU-h extrapolation was never the projection. 1,593 windows projected to **1.44 h** at the
  wall-clock rate including model load and 0.90 h at the steady-state rate. **GO.**

### 2026-09-04, Phase 5 — the flight ABORTED, and the one permitted recovery

Row `SAEA-E21-FULL44-DIRECT-BASELINE-V1`, attempt `attempt-20260904T223550Z-99e5d8`, study commit
`9cd2fba0`. **ABORTED after 47 min 51 s, 925 of 1,593 windows, 22 of 44 calls** (through `4367318`),
82,125.57 speech seconds durably spent.

```
47.51.004.242 E CUDA error: an illegal memory access was encountered
47.51.004.250 E ggml/src/ggml-cuda/ggml-cuda.cu:104: CUDA error
  current device: 0, in function ggml_backend_cuda_synchronize at ggml-cuda.cu:3249
  cudaStreamSynchronize(cuda_ctx->stream())
```

llama-server aborted; `core.session.assert_session_alive` then correctly refused the next request
because the receipt-pinned pid was gone (`/proc/717/exe` missing — "I5: liveness alone proves
nothing"). The refusal is the rail working, not the failure.

**Diagnosis.** Memory pressure at the edge of the card is the leading cause, and it is measured
rather than guessed: llama-server started with **23,119 MiB free of 24,462** and the run reported
**23,396 MiB used device-wide** throughout — about 1 GB of headroom — and the fault landed while
eight slots were decoding (9.9 to 34.1 t/s each) and a ninth allocation, the mmproj encode compute
buffer for a 90-second window, was live. The abort surfaced at a `cudaStreamSynchronize`, which is
where an asynchronous illegal access is *always* reported, so the stack does not by itself separate
memory pressure from a CUDA-graph fault; no log line implicates graphs either way.

**The recovery, `SAEA-E21-FULL44-DIRECT-BASELINE-V2`.** A new run id is not a preference: the plan's
budget is metered cumulatively across every attempt of a run id, so V1 has 825 of its 1,750 calls
left — fewer than the 1,593 a complete pass needs — and a second attempt under V1 is arithmetically
impossible.

| | V1 | V2 |
|---|---|---|
| serving geometry | `-c 49152 -np 8` | `-c 36864 -np 6` |
| slot tokens | 6,144 | **6,144, unchanged** |
| server env | none | `GGML_CUDA_DISABLE_GRAPHS=1` |
| model fragment | `q4km-e21-buf90-mmproj-gpu-04ccc72a` | `q4km-e21-buf90-mmproj-gpu-04ccc72a-np6` |
| everything else | — | **identical** |

The slot size is deliberately untouched: it is the size this preregistration's section 6 certified at
×2.72 over the 2,258-token worst request, and 36,864 = 6 × 6,144 is a multiple of 512, so the
server's own rounding cannot move it. Dropping the slot count frees 12,288 tokens of `q8_0` KV —
about 640 MiB at 48 layers × 4 KV heads × 128 dims — and cuts peak concurrent activation by a
quarter. `GGML_CUDA_DISABLE_GRAPHS=1` is **hardening, not a diagnosis**; the pinned build honours it
(`ggml/src/ggml-cuda/common.cuh`). Because the flight rules allow exactly one recovery, both
plausible causes are removed in the same step and **the recovery deliberately does not separate
them** — neither knob changes a single request byte, so neither can move the number.

Population, split identity, baseline fragment, experiment fragment, instruction, OBS protocol,
evidence, decoding params, audio path, feature-cache policy and scorer list are all unchanged.

**Throughput budget.** V1 measured 19.25 windows per minute at `-np 8` with graphs on. Six slots
instead of eight costs about a quarter, and disabling CUDA graphs costs about 34 % of decode rate at
batch > 1 by this repository's own measurement, so V2 is budgeted at 19.25 × 0.75 × 0.66 = **9.5
windows per minute**, putting 1,593 windows at about **2.8 hours** against the 4.0-hour ceiling. No
re-smoke is run: the smoke's two questions were VRAM and throughput, and a strictly *smaller*
geometry answers the first a fortiori, while the second is bounded above by arithmetic even at a
50 % total slowdown.

**If V2 also fails**, the flight stops under the owner's own rule and the fix is proven on a 4-row
dry run before anything else flies.

### 2026-09-04/05, Phase 6 — the recovery flight, and the verdict

Row `SAEA-E21-FULL44-DIRECT-BASELINE-V2`, attempt `attempt-20260904T233816Z-bcd338`, study commit
`44db2e9d`, config hash `e4b133d1…`, protocol hash `06f7f308…`: **COMPLETED and FINALIZED, 1,593 of
1,593 windows**, 141,345.85 speech seconds (39.263 h), **0.973 GPU-h** against a 4.0-hour ceiling,
peak VRAM 22,720 MiB of 24,463 (676 MiB below V1's, exactly the KV the geometry change freed), zero
skipped and zero saturated slices, 40.3× realtime. Measured throughput 17.5 windows per minute — well
above the 9.5 the recovery budgeted, so disabling CUDA graphs cost far less than the 34 % assumed.

Two things happened between the seal and the verdict, both recorded in the verdict's section 8.

**The manifest sealed COMPLETED and then would not score.** `core.scorers.score_bundle` runs a
manifest's whole scorer list; `asr-wer-whisper` and `asr-wer` both got through all 44 calls and then
`entity-wer` refused, because call `4320211` references entity id `1057` and its `wer_tag.json`
sidecar lists only ids 0–904. Scope, measured over every one of the 44 calls: **one id of 38,377, one
tagged token of 55,294** (0.0026 % and 0.0018 %), zero listed-but-corrupt ids anywhere. An annotation
gap in the Earnings-21 release, unfixable from here, and it made a completed 44-call flight
unfinalizable.

`data.references.reference_entity_mentions` now splits two cases the old check conflated: an id the
sidecar **lists** but does not usably label stays fatal, and an id it **does not list at all** yields
a mention typed `__UNTYPED__` — never a real class, always counted, visible as its own
`by_entity_type` row. Regression anchor, holding to the digit: the sealed `SAEA-E-005B-N10-zero`
outputs re-score to the 2026-09-04 audit's published 32.01 % over 8,284 mentions, with no
`__UNTYPED__` class among the ten. Commit `d2d243f3`; receipt
`docs/checks/…/2026-09-04-e21-full44-direct-baseline-v1/entity-annotation-defect/`.

**Then it finalized**, and `core.scoring_batch` re-scored the sealed manifest as one whole-manifest
verified job (`verified: true`, never sharded).

**Verdict: ALIGNED.** Corpus WER under the Whisper `EnglishTextNormalizer` over all 44 calls is
**8.200 %** against `openai/whisper-large-v3`'s **9.71** (−1.51); band test ≤ 12.71 pass, strict
medium.en floor ≤ 10.2 pass, ALIGNED-BETTER < 6.71 not reached. `4346923` is inside the number and
costs +0.312 points. The ten sealed calls re-measured here score 7.185 against their sealed 7.137, so
the distance from August's 7.137 to this 8.200 is the corpus (the other 34 score 8.470), not the
build. Full verdict: `docs/readiness/2026-09-04-e21-full44-direct-baseline-v1-verdict.md`.
Commit `54e4c501`.
