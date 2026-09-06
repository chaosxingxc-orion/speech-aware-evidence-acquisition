# Preregistration — the three Earnings-22 model-usage alignment cells

**STATUS: PREREGISTERED, NOT AUTHORIZED. One of the three is BLOCKED.** Three single-factor cells
are specified here and **none is flown by the rows that write this document**
(`SAEA-E22-MF-OVERGENERATION-ANALYSIS-V1` and `SAEA-SN-MF-E22-DEV1500-ROSTER-V1`, both
`model-free-check`). Each cell needs its own owner GO, its own exposure row registered before its
first contact, and its own `contracts.ExecutionPlan`. Nothing below may be executed on the
authority of this file.

Basis, all model-free and all landed:

* `docs/readiness/2026-09-05-e22-dev-esb-prompt-ab-v1-verdict.md` — the instruction TEXT is not the
  explanation (arm B is 0.83 points worse).
* `docs/readiness/2026-09-05-e22-dev-esb-shape-c-v1-verdict.md` — the request SHAPE is not the
  explanation (arm C is 0.325 points worse and its oracle floor ROSE).
* `docs/readiness/2026-09-06-e22-semantic-error-scan-v1.md` — 47.6 % of arm A's error mass is
  speech at a clip boundary; a scoring-convention change is worth at most 0.35 points, 0.25 of it
  with a published authority.
* `docs/readiness/2026-09-06-e22-clip-boundary-audit-v1.md` and
  `docs/readiness/2026-09-06-e22-esb-array-durations-v1.md` — the published segmentation overlaps
  and the ESB release's own arrays carry that overlap, so the boundary is **not** a difference
  between this study and the published 9.79 / 12.3.
* `docs/readiness/2026-09-06-e22-overgeneration-analysis-v1.md` — decode discipline is bounded at
  0.73 dev WER points and the achievable share of that, at a non-worsening agentic rate, is 0.23.

What survives all of that is this study's own **model usage** in the two places the analysis above
could not reach: the decoder quantization, and the audio front-end. The third face, decode
discipline, is specified here too because it is the one whose prediction is already fixed and
therefore falsifiable.

The one-experiment-in-flight rule applies: these are queued behind whatever is flying, and behind
the boundary-exact cell of `docs/readiness/2026-09-06-e22-dev-boundary-exact-v1-preregistration.md`
if the owner sequences it first.

---

## 0. The population, fixed for all three

**`E22-DEV-ESB-1500-V1`** — 1,500 of the 6,038 ESB utterances of this study's own registered
Earnings-22 dev subset10, exactly 150 from each of the ten calls, seed 20260906, frozen through
`core.roster.freeze_roster` (row `SAEA-SN-MF-E22-DEV1500-ROSTER-V1`).

| | value |
|---|---|
| roster receipt | `docs/receipts/rosters/e22-dev-esb-1500-v1.json` (sha256 `5d2b4e86…`) |
| probe view the flight hydrates | `docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-dev-esb-1500-v1/roster/flight-roster-receipt.json` (sha256 `fe9528be…`) |
| D1 media supplement | `docs/receipts/artifacts/d1-e22-esb-dev1500-utterances.json` (sha256 `6a3d2472…`) |
| `split_identity_hash` | `c626e62f8876bf52a2904a0d2ec91807a530f3195c10facc8c036f661b2bf88a` |
| rows / strata | 1,500 / 150 per call over all ten |
| speech seconds, one pass | **9,948.983** (2.7636 h) |
| longest / shortest item | 32.88 s / 0.219938 s |
| clamped items in the subset | **none** (`4481952-631` was not drawn) |
| media root | `derived/e22-esb-utterances/dev-v1/` — **unchanged**, the same bytes the sealed arms were served |

**Why a subset and not all 6,038.** The Q8_0 cell costs about 7.9× the per-call latency of the
resident Q4_K_M core (§1.4), so a 6,038-row pass is hours of GPU where a 1,500-row pass is not.
1,500 is far above the owner's `n >= 400` paired-claim floor of 2026-09-03 and keeps every one of
the ten call strata at 150, which is what makes the call-stratified bootstrap well-posed.

**Why the media root is unchanged.** Cells (a) and (b) send the sealed bytes, so each is paired
row for row against sealed arm A on identical audio. Cell (c) cannot be — that is its whole point,
and §3 carries the consequences.

**The comparator, for all three:** the sealed `SAEA-E22-DEV-ESB-PROMPT-A-V1`, attempt
`attempt-20260905T073641Z-f977d1`, restricted to these 1,500 ids. **No new arm A is flown.** Greedy
decoding is not bitwise reproducible across batch compositions on this runtime, so the comparison
is against sealed outputs and never against a re-run.

The subset's own uncapped numbers, measured model-free and fixed here before any cell exists:
**corpus WER 17.4012 %** under the Whisper `EnglishTextNormalizer` and **agentic error rate
1.9161 %** (§5.4 of the over-generation verdict).

---

## 1. Cell (a) — `SAEA-E22-DEV-ESB-Q8-V1`

**One factor: the decoder quantization. Nothing about the request changes.**

### 1.1 What varies

The decoder GGUF is the umbrella lock's **Q8_0** file (`model_lock_key`
`qwen3-omni-30b-a3b-instruct-gguf`, 32,484,494,336 bytes, sha256 `8a50e5a7…`) instead of the
Q4_K_M requant (`qwen3-omni-30b-a3b-instruct-gguf-q4km`, sha256 `0751c279…`). Runtime receipt
`docs/receipts/runtime-q8-featcache-04ccc72a.json`, build commit
`04ccc72a2207347ca76161b93fd9d846dd0a8675` — **the same build the sealed arm flew**.

**The audio encoder is byte-identical and that is a receipt, not an assumption.** Both runtime
receipts pin `mmproj-Qwen3-Omni-30B-A3B-Instruct-bf16.gguf` at sha256
`f0dfe825fb692d426362b1ac79678fc08daa4758f7151526cad110515f122883`.

### 1.2 Held fixed, byte for byte

Arm A's instruction verbatim; the base `TaskAdapter.assemble_prompt` shape (one system message with
the instruction, one user message with the audio), so `omit_system_message` stays false;
temperature 0; seed 20260803; `max_tokens` 1024; one contact per item; no evidence; no OBS
windowing; `core.flight.FlightRuntime` with the shared rails `zero-supply` direct arm and the
OpenJiuwen executor through `scripts/flights/run_e22_esb_cell.py`; the audio path
**`raw-audio-mmproj`** with the bf16 mmproj resident on the GPU and **no feature-cache directory**;
the reference layer; the scorers `asr-wer-esb-whisper` (paper-facing), `asr-wer-esb` and `cost`;
corpus aggregation; `merge_compounds` still not applied; and scoring once per complete manifest
through `core.scoring_batch`, never sharded.

> Transcribe the speech verbatim exactly as spoken. Never insert, repeat, or add any word you do
> not clearly hear in the audio. Output only the transcript text.

**The feature cache is forbidden here and the prohibition is load-bearing.** The legacy
`/home/chao/feat-cache/*` caches hold encoder outputs for other populations and other builds; the
sealed arm A encoded every utterance live on the GPU, and so must this cell, or the contrast
acquires a second factor.

### 1.3 The one forced deviation, and the precondition that decides it

**D-Q8-1, weight placement.** 30.3 GiB cannot be resident on a 24,463 MiB card, so `--n-cpu-moe N`
is forced: the Mixture-of-Experts tensors of the first N layers sit in host RAM while attention,
norms, embeddings, shared parts and the remaining experts stay on the GPU.

**The A2T probe's `N = 24` must NOT be copied, and the reason is on the record.** Caveat 2 of
`docs/readiness/2026-09-04-a2t-q8-quantization-probe-v1-verdict.md`: *"llama.cpp estimates the
audio encoder's worst-case compute buffer at 2,940 MiB against the 2,228 MiB this placement leaves
free. Every one of the 400 rows was a feature-cache hit … so no encode ran. A future Q8 cell on
uncached audio must re-derive the placement."* **This is that cell.** Every one of its 1,500 rows
runs a live mmproj encode, so a placement that leaves 2,228 MiB free is a cell that faults.

**Precondition Q8-P1, model-free, zero generated tokens, before any contact.** Re-derive N on
*this* geometry exactly as the A2T probe derived its own (receipt
`…/2026-09-04-a2t-q8-quantization-probe-400-v1/placement/placement-fit.json`): start from
`--cpu-moe`, lower N in steps of 4, read free VRAM from the live server through `GET /props` and
`nvidia-smi` with **zero `/completion` calls**, and take the largest GPU-resident share that still
leaves at least **3,072 MiB free** — the 2,940 MiB llama.cpp estimates for the encoder's worst-case
compute buffer, rounded up. The A2T ladder at `-c 49152 -np 3` ran 44 → 14,468 MiB, 40 → 12,020,
36 → 9,572, 32 → 7,124, 28 → 4,676, 24 → 2,228, 20 → 14, i.e. about 2,448 MiB per four layers, so
**N = 28 is the expected answer and it is not assumed**: the pass measures it on this geometry,
whose 40,960 q8_0 KV tokens are 8,192 fewer than the A2T geometry's.

**The serving geometry stays `-c 40960 -np 8`, 5,120 tokens per slot** — the sealed arm A geometry,
unchanged, so the request and the KV plane are identical. The fit is now easy rather than tight:
this subset's longest utterance is **32.88 s**, so the worst request needs `13 × ceil(32.88) = 429`
speech tokens plus arm A's 49-token text envelope plus 1,024 completion plus 2 special ≈ 1,504
against a 5,120-token slot, a ratio of 3.4× on the repository's own `slot_tokens >= 2 × worst`
rule.

**If no N clears the 3,072 MiB floor at `-c 40960 -np 8`, the cell STOPS.** It does not silently
shrink `-np`: a slot-count change alters batch composition, greedy decoding is not bitwise
reproducible across batch compositions on this runtime, and the cell would stop being
single-factor. A geometry change is a new registration.

**D-Q8-2, recorded rather than tuned away:** CPU and CUDA kernels accumulate in different orders,
so a rare greedy tie can flip. This was a caveat of the A2T probe and it stays one; it cuts against
over-reading a small effect, not for it.

### 1.4 Budget (`contracts.ExecutionPlan`, to be registered with the row)

| | plan | ceiling | basis |
|---|---:|---:|---|
| model calls | 1,508 | 1,600 | 1,500 rows × 1 contact + 8 canaries |
| speech audio seconds | 10,000 | 10,500 | 9,948.983 for one pass |
| GPU hours | **2.0** | **3.0** | see below |
| paid API spend | 0 | 0 | in force |

**The GPU budget, derived rather than guessed.** Two rates exist and they disagree, so both are
named and the larger is used. The August whole-model-offload note measured **4.17×** the resident
Q4_K_M rate; the 2026-09-05 A2T Q8 flight measured **7.85×** in steady state over 400 calls
(6.141 s mean latency against 0.782 s), and explained the difference — the smoke's 32× figure was a
cold page cache faulting 14 GiB of CPU-resident expert tensors in from ext4. **7.85× is the
measured figure on the same hardware at the same build and is the one this budget uses.** Sealed
arm A ran at 1.927 s mean latency and 3.744 contacts/s at eight slots, so 7.85× gives about 15.1 s
per call and, at eight slots, roughly 2,830 s of dispatch for 1,500 rows. Two additions push the
plan above that arithmetic and both are real: N = 28 puts four more layers on the CPU than the
measured 7.85× was measured at, and every row here pays a live mmproj encode the A2T probe never
paid. The A2T flight's own per-audio-second rate (≈ 0.29 GPU-h for 2,159.7 s) scaled to 9,949 s is
1.34 h; **2.0 planned and 3.0 registered is that with room, and the row's ceiling is what the gate
enforces.**

`contracts.ExecutionPlan` carries no ceiling field; the registered ceilings are the exposure row's
own calls / speech-audio-seconds / GPU-hours cells, and the plan budget is metered **cumulatively
across every attempt of this run id**, so a recovery plan must cover prior durable spend as well as
its own worst case.

### 1.5 What this cell can and cannot conclude

It measures whether the decoder quantization moves this study's Earnings-22 number. The A2T probe
found **+2.25 pp pooled tool accuracy and 0.0 pp on the tier that carried its gap**, and concluded
QUANTIZATION-EXCLUDED there. Nothing transfers: that was a different carrier, a different task and
a cached-audio path. This cell measures Earnings-22 ASR on live encodes and it is the only way to
know.

---

## 2. Cell (b) — `SAEA-E22-DEV-ESB-STOPCAP-V1`

**One factor: a duration-proportional generation cap. Nothing else moves.**

### 2.1 The cap, fixed before the flight

```
n_predict_i = min(1024, max(1, ceil(alpha * media_seconds_i * words_per_second_p95 * tokens_per_word)))
alpha = 1.5    words_per_second_p95 = 4.999220954734555    tokens_per_word = 1.2991996296395218
```

Both constants are measured on the sealed dev population and committed:
`docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-overgeneration-analysis/summary.json`.
`words_per_second_p95` is the 95th percentile of **reference** words per second — the reference side
deliberately, so the over-generation the cap bounds cannot set the cap's own scale — and
`tokens_per_word` is the flight tokenizer's pooled tokens per normalized hypothesis word, taken from
the sealed `usage.completion_tokens`, never from a re-tokenization.

At alpha 1.5 the cap is 10 tokens for a 1 s clip, 49 for 5 s, 98 for 10 s and 321 for this subset's
32.88 s longest — all under the 1,024 the sealed arm flew, so the cap is a genuine tightening
everywhere and never a loosening.

**Why alpha 1.5 and not the better-scoring 0.8.** The whole frontier is published in §5.2 of the
over-generation verdict. Alpha 0.8 is the WER optimum (−0.73 points on 6,038) and it makes the
**agentic error rate worse** (1.9241 → 2.0121, +0.088). Alpha 1.5 is the tightest rung on the
declared ladder whose full-population agentic point estimate does not worsen (1.9232, −0.0009).
**The operating point is chosen on the decision-relevant metric, not on the paper-facing one**, and
it is chosen here, in writing, before any capped request exists.

### 2.2 The prediction, fixed here so it can be wrong

Projected onto these exact 1,500 rows (§5.4 of the over-generation verdict), against the subset's
own uncapped baseline of 17.4012 % corpus WER and 1.9161 % agentic:

| | predicted |
|---|---:|
| rows the cap bites | **50** |
| of those, cut entirely inside surplus (benefit) | 35 |
| of those, cut below their own reference length (harm) | 15 |
| tail-bleed rows cut (of 218 in the subset) | 5 |
| **corpus WER** | **17.1765 % (−0.2248)** |
| **agentic error rate** | **1.9428 % (+0.0267)** |

**The prediction rests on two assumptions and the flight tests both.** First, that a greedy decode
under an `n_predict` cap returns exactly the uncapped decode's token PREFIX — llama.cpp stops
generating, it does not re-decode. Second, that the token-to-word mapping inside a row is
approximately linear in that row's own measured tokens-per-word ratio. If the measured effect
diverges materially from −0.2248, one of those two is wrong, and several other pieces of this
account rest on the first. **That falsifiability is the cell's main value, and this document says so
rather than overselling a quarter of a point against a 6.15-point test gap.**

### 2.3 The seam, and why the cap cannot be a config value today

`decoding_params.max_tokens` is composed **per cell**, not per sample:
`core.flight.FlightRuntime._decoding_params` reads one mapping off the composed config and hands the
same one to every request. A duration-proportional cap therefore needs a per-sample resolution seam,
and there is exactly one precedent for it in this repository — `id_slot: "per-sample"`, which
`FlightRuntime` resolves per request and `core.model.adapter.FrozenCoreAdapter.request` refuses if it
ever arrives unresolved.

**The seam, specified minimally and before it is written:**

* a model fragment may declare `decoding_params.max_tokens: "per-sample-duration"` together with a
  fragment-level `max_tokens_duration_rule` carrying `alpha`, `words_per_second_p95`,
  `tokens_per_word`, `floor_tokens` and `ceiling_tokens`;
* `FlightRuntime` resolves it **where it already resolves `id_slot`**, from the sample's own
  `audio_seconds` (already on the request payload — the sealed trace records it), to the integer of
  §2.1;
* `core.model.request_types.ALLOWED_DECODING_KEYS` is **unchanged**: `max_tokens` is already
  admitted, and only its resolution moves;
* the adapter refuses a non-integer `max_tokens` reaching the transport, exactly as it refuses an
  unresolved `id_slot`, so a silent fall-through is impossible;
* the rule is refused when the sentinel is absent, and the sentinel is refused when the rule is
  absent — fail-closed in both directions;
* absent both, **every fragment that predates this seam renders byte-identical requests**, pinned by
  a test in the manner of
  `tests/unit/test_llama_server_transport.py::test_sealed_e22_arm_a_payload_is_byte_identical_without_the_seam`.

This is a seam on the existing base, not a new module: no `rails/probes/` module, no `TaskAdapter`
subclass, no controller subclass, no `launcher/` directory. `scripts/checks/engineering_base_check.py`
must PASS on the change.

The resolved per-row `max_tokens` already lands in the trace's `decoding_params`, so **every row's
cap is auditable after the fact** without a new receipt shape.

### 2.4 Stop strings: none, and none may be invented

`core.model.request_types.ALLOWED_DECODING_KEYS` admits exactly `temperature`, `seed`, `top_p`,
`top_k`, `min_p`, `max_tokens`, `presence_penalty`, `frequency_penalty`, `response_format`,
`id_slot`, `logprobs`, `top_logprobs`. **There is no `stop` key and no `repeat_penalty` key**, so
this study's transport cannot send a stop string without a seam change of its own.

Nor is there one to send. No Qwen3-Omni ASR recipe in this repository's records carries a stop
sequence — the model card supplies an instruction and a message placement, both already measured and
both already excluded — and the pinned GGUF chat template's own end-of-turn token terminated **every
one of the 6,038 sealed rows** (zero reached the 1,024 ceiling; the largest completion was 130
tokens). **Adding a stop string on a full stop or a newline would be this study inventing a
convention no published recipe carries, on a corpus whose references are multi-sentence.** It is
refused here by name so the cell cannot quietly acquire one later, and the flight agent may not add
one.

### 2.5 Held fixed

Everything in §1.2, plus the Q4_K_M decoder and the sealed `-c 40960 -np 8` geometry. The **only**
difference from the sealed arm A request is the integer in `max_tokens`.

### 2.6 Budget

| | plan | ceiling | basis |
|---|---:|---:|---|
| model calls | 1,508 | 1,600 | 1,500 rows × 1 contact + 8 canaries |
| speech audio seconds | 10,000 | 10,500 | 9,948.983 for one pass |
| GPU hours | **0.20** | **0.35** | sealed arm A used 0.4515 for 6,038 contacts on the same runtime; 1,500 is 24.8 % of that, ≈ 0.112 h, and the cap can only shorten generation |
| paid API spend | 0 | 0 | in force |

Expected dispatch ≈ 400 s at eight slots (arm A: 3.744 contacts/s).

---

## 3. Cell (c) — `SAEA-E22-DEV-ESB-FRONTEND-V1` — **BLOCKED**

**One factor: the audio decode path. And it cannot be flown from anything on this machine.**

### 3.1 The question

This study's clips are `librosa.load(sr=16000, mono=True)` from the locked `earnings22-original`
MP3s, written as 16 kHz mono int16 WAV. The published evaluations consume the ESB release's own
per-utterance `audio` arrays, and the 2026-09-06 array-durations check found those arrays are stored
in **each call's native container** — 16 kHz stereo, 22.05 kHz stereo and 24 kHz mono across the six
test calls — and resampled in process by each system. **The two paths agree on the span and differ
on the decode**: different source container, different resampler, different channel fold. That
difference is real, its sign is unknown, and nothing has measured it.

### 3.2 Why it is BLOCKED

**The dev arrays are not on disk and cannot be put there without a network acquisition.**

* The **four ESB test shards** are on disk (`derived/e22-esb-segment-table/parquet/`, 1.10 GB) and
  they are the **test** population. They may not be used: this cell is scoped to dev, and reading
  test audio content would be a second answer-bearing read of a one-shot asset.
* The **55 ESB train shards** hold the 6,038 dev10 rows and were **never downloaded**. The
  2026-09-05 segment table was built by a pyarrow **column projection over `HfFileSystem`** at the
  pinned revision, which never materialized the `audio` column. Each shard rests on its published
  git-LFS oid; the receipt records `locally_rehashed: false` for all 55.

**The price of unblocking it, stated so the owner can decide:**

| option | cost | hazard |
|---|---|---|
| fetch all 55 train shards | **22,039,334,688 bytes = 22.04 GB**, `sanchit-gandhi/earnings22_split` at revision `f9fb35f4134e32b9c8100199d949398fd6d08a5f` | a program-level asset acquisition: it belongs to the umbrella (`docs/datasets.lock.json`, `scripts/data/`) and this study must not do it unilaterally. The shards also carry the 103 confirmatory calls' audio, so they land inside this study's data root as bytes it may not read |
| targeted row-group projection of the `audio` leaf for the 1,500 drawn ids only | unknown offline; far below 22 GB, but not derivable without the network | the same network read of a repository whose rows are mostly confirmatory. The 2026-09-05 extractor's own discipline — filter on `source_id` **inside** the batch loop, before a row can reach a list, a file, a log line or a receipt — is the precedent that makes this defensible, and it would have to be reproduced exactly |

**Either option needs an owner decision this document does not have.** The cell is therefore
**BLOCKED** and is specified so that it can be executed unchanged if the owner unblocks it.

### 3.3 What it would cost in identity, if unblocked

The re-decoded audio is **different bytes for the same published segment**, so the two populations
must never share an identifier. Following the boundary-exact cell's rule verbatim:

* media under a **new version directory** `derived/e22-esb-utterances/dev-fe-v1/`, so the two
  decodes' bytes never share a root;
* sample ids `<call>-<segment>@fe1`, the published segment key recovered by splitting on `@`, so the
  reference layer and the paired join against sealed arm A stay exact and no id collides;
* a new roster probe view and a new D1 media supplement, both chaining through
  `contracts.gate_media_identity`;
* engineering: a `--profile dev1500-frontend` on the existing builders — one carrier descriptor, one
  profile entry, one id-suffix argument, plus tests. **No new module, no `TaskAdapter` subclass, no
  controller subclass.**

### 3.4 The confound it cannot remove, named in advance

Even unblocked, this is not a clean single factor. The released arrays differ from this study's
clips in **four** ways at once — source container, sample rate, channel fold and a sub-frame span
difference (median +0.0000316 s, 99.89 % of test rows within 1 ms). The span difference is
negligible; the other three travel together and **cannot be separated by one cell**. The verdict
would have to say "the decode path is worth X points" and never "the resampler is worth X points".

### 3.5 Budget, conditional

If unblocked, the flight itself is cell (b)'s budget on the Q4_K_M core: 1,508 calls, 10,000 speech
seconds, 0.20 GPU-h planned and 0.35 registered. **The acquisition is not in that budget** and is an
umbrella action with its own accounting. CPU preprocessing (extract 1,500 arrays, write 1,500 WAVs,
hash them, build the supplement) runs at the campaign cap of 8 workers if a GPU campaign is in
flight and 20 otherwise.

---

## 4. The decision rule, fixed now for all three

**Population:** the same 1,500 rows, the same references, the same reference-word denominator.
**Comparator:** sealed `SAEA-E22-DEV-ESB-PROMPT-A-V1` (`attempt-20260905T073641Z-f977d1`),
restricted to these ids, paired per utterance.

**Statistics:** `analysis.paired.paired_contrast`, **10,000 replicates, stratified by source call
(10 strata), seed 20260903, CI90**, rendered through `analysis.paired.render_markdown`. Two metrics,
both paired, both signed as `cell − arm A`:

* **corpus WER** under the Whisper `EnglishTextNormalizer` (paper-facing), scored once over the
  complete manifest through `core.scoring_batch`, never sharded;
* the **agentic error rate** — HIGH-impact reference-word mass over reference words — recomputed on
  the new outputs by `analysis.e22_error_taxonomy` **at its committed version**.

**ADMITTED as a model-usage local optimization iff both hold:**

1. corpus WER improves **and** the CI90 **upper** bound on the delta is **< 0**; and
2. the agentic error rate does not worsen: the CI90 upper bound on its delta is below **+0.05
   points** — a non-inferiority margin **inherited verbatim** from §1.6 of
   `docs/readiness/2026-09-06-e22-dev-boundary-exact-v1-preregistration.md` and fixed here, before
   any number exists, so it cannot be chosen afterwards.

**Why clause 2 reads a CI and not a point estimate, disclosed.** On the full 6,038 rows the alpha-1.5
cap's predicted agentic delta is −0.0009; on these 1,500 it is +0.0267, on 50 capped rows of which 15
are harmed. That is noise around zero at this sample size. Both numbers are published in §5.4 of the
over-generation verdict and the margin was set to accommodate exactly this, not chosen after seeing
it.

**Mandatory reporting, admitted or not.** The per-call table for all ten calls under both
normalizers; natural-mixture and equal-call weightings side by side; the S/D/I split and the
hypothesis-to-reference length ratio; the utterance-duration decomposition; the boundary category's
mass before and after (`segmentation-artifact` + `runaway-tail` + `runaway-head`) with the tail/head
containment buckets; and, for cell (b), the **measured** rows-capped / benefit / harm counts beside
the §2.2 predictions, named as a prediction check.

**The claim rule, and it is binding.** These are dev numbers on a 1,500-row subset of this study's
own dev split. **No cell here is an alignment verdict**, none is compared to the published 9.79 or
12.3 as a difference, and the published figures appear as orientation only where they appear at all.
The six calibration-exposed ESB test calls are a different population and the 109 confirmatory calls
are untouched.

**The test read, and why none of these three earns one.** An admitted cell's setting is applied to
the sealed six-call test outputs **only where it is a scorer-side change** — a normalizer or an
aggregation, applied to bytes already sealed, needing no new contact. **None of these three is
scorer-side**: Q8_0 changes the decoder, the cap changes the request, and the front end changes the
audio. Every one of them would require **re-flying the six test calls**, which is a **second**
read of a population the 2026-09-04 owner allowance permitted **once**. Such a read may be
**proposed** to the owner and never taken on this file's authority; it would need its own owner
decision and its own exposure row, and it inherits this section's claim rule in full.

---

## 5. Sequence, and what is registered when

1. **Nothing flies on this document.** It is a preregistration written by two `model-free-check`
   rows.
2. Each cell needs: an owner GO, an exposure row registered **before** its first contact, a
   `contracts.ExecutionPlan` carrying the split role, the split identity hash
   `c626e62f…`, the budget of its own section and the protocol hash, and the model-free
   preconditions of §6 landed as receipts.
3. **One experiment in flight at a time.** These are queued behind whatever is flying and behind the
   boundary-exact cell if the owner sequences it first.
4. **At most one recovery re-registration per flight.** A second failure stops the flight and the fix
   is proven on a 4-row dry run before anything else is spent.
5. A new mechanism is admitted only after its predecessor is replicated or root-caused to a named
   component. **None of these three is a mechanism** — (a) and (c) are runtime factors and (b) is a
   decode-discipline knob.

**Recommended order, and the reasoning is on the record.** (b) is the cheapest (0.20 GPU-h) and its
prediction is already fixed, so it is the fastest falsifiable thing available; (a) is the largest
untested runtime factor but costs ten times as much GPU; (c) cannot start without an owner decision.
The over-generation verdict bounds (b)'s payoff at a quarter of a point and says so — if the owner
would rather not spend a flight on that, the honest reading is that **all three faces of model usage
are now bounded small, and the boundary-exact cell is the intervention that addresses the mechanism
every one of these documents keeps pointing at.**

---

## 6. Preconditions, all model-free, all before the first contact

Common to every cell:

1. **Configuration fragments**, none of which exists yet and each of which is one file:
   `configs/dataset/earnings22-esb-dev1500-utterances.json` (naming the §0 probe view, the D1
   supplement and their digests, the reference-layer receipt and the segment-table receipt the
   dev10 fragment already pins); `configs/baseline/e22-esb-dev1500-*.json` per cell; one
   `configs/model/*` fragment per cell; one `configs/experiment/*` fragment. Every `policy`,
   `evidence_source` and `scorers` value must resolve in a `core.base` registry, and
   `scripts/checks/engineering_base_check.py` must PASS.
2. **The roster hydrates.** `FlightRuntime.preflight` must compute
   `c626e62f8876bf52a2904a0d2ec91807a530f3195c10facc8c036f661b2bf88a` from the probe view and the
   exposure row must carry the same value.
3. **Media identity.** `contracts.gate_media_identity` over
   `docs/receipts/artifacts/d1-e22-esb-dev1500-utterances.json`; for cell (c), over its own rebuilt
   supplement.
4. **Prompt fit, re-derived.** The longest item is 32.88 s, so `13 × 33 = 429` speech tokens plus the
   49-token arm A envelope; assert the live `n_ctx` per slot is 5,120 through `GET /props` and that
   the rendered prompt hashes to arm A's, with the media-marker nonce substituted as the 2026-09-05
   shape-C render did.
5. **A wire check** of the whole request path through a fake gate and a fake transport — zero
   contacts, zero servers, zero sockets — writing its receipts **outside** the tree and copying them
   in afterwards. (The 2026-09-05 A/B experiment lost three of four scoring gates to receipts written
   straight into `docs/checks/` making the tree dirty; do not repeat it.)
6. **A 4-row dry run** before the flight, on four of the 1,500.
7. **A clean working tree for the whole run.** A COMPLETED manifest reads `study_commit` at finalize
   and refuses a dirty tree.

Cell-specific:

* **(a)** the placement pass of §1.3, with its own receipt, zero generated tokens, and a refusal if
  no `N` clears 3,072 MiB free at `-c 40960 -np 8`. Also: confirm the Q8_0 GGUF is materialized and
  re-hashes to `8a50e5a7…`, and that **no** `LLAMA_MTMD_FEAT_CACHE_DIR` is set in `server_env`.
* **(b)** the seam of §2.3 with its tests, including the byte-identical-without-the-seam pin; and a
  model-free assertion that the resolver reproduces
  `analysis.e22_overgeneration.cap_tokens(1.5, seconds, 4.999220954734555, 1.2991996296395218)` on
  every one of the 1,500 rows, clamped to 1,024.
* **(c)** unblocking first (§3.2), then the identity rebuild of §3.3, then a byte-determinism check
  — cut twice, assert `items_sha256` is unchanged — exactly as the `dev-v1` cut was proved.

---

## 7. The flight agent's checklist

1. Read the owner GO and this section. **If there is no owner GO for the specific cell, stop.**
2. Register the exposure row **before the first contact**, naming the population, the comparator
   attempt, the budget, the ceilings and the claim rule of §4.
3. Front-load the model load as a background step at mission start; run the CPU preconditions of §6
   during it and join at the first session-bound step.
4. Run every model-free precondition and **stop on any refusal**. Land their receipts.
5. Check the GPU before anything else: `nvidia-smi -q -d POWER` for `enforced.power.limit`, and the
   Legion SmartFanMode. A Quiet-mode 35 W cap silently overrides everything and has recurred.
6. Fly **one attempt**, 1,500 contacts, one serving geometry, no repair, no retry, no resend. At most
   one recovery re-registration; a second failure stops the flight.
7. Score **once**, over the complete manifest, through `core.scoring_batch`, `verified: true`.
8. Run `analysis.e22_error_taxonomy` at its committed version on the new outputs and report the
   agentic rate and the boundary mass beside the WER.
9. Run the paired contrast of §4 against the **sealed** arm A rows — never against a re-run.
10. Write the verdict with the per-stratum table and the claim rule quoted verbatim, and for cell (b)
    the prediction check of §4.
11. **Stop.** No test read, no second cell, no mechanism arm.

**Environment notes that have cost this program time before.** `PYTHONDONTWRITEBYTECODE=1` is
required — bytecode under the frozen scoring package refuses the D3 gate. Data-touching CLIs run in
WSL2, never native Windows Python. `scripts/flights/run_e22_esb_cell.py` pins `REPO` to the primary
checkout path, so a flight runs from that checkout and not from a worktree. Never `pip install` in a
clone: it repoints the shared venv.

---

## 8. Not authorized by any cell here

No mechanism arm. No knob tuned on the test split. No fourth prompt. No few-shot. No post-processing
of any hypothesis. No re-scoring of any sealed arm. No `merge_compounds`. No packet or feature-cache
path. No stop string. No second read of the six calibration-exposed ESB test calls. No read of any
confirmatory call. No `paper-scale-confirmatory` profile, no manuscript, no submission, no Stage-3
activity.
