# Preregistration — the three Earnings-22 model-usage alignment cells

**STATUS: two cells FLIGHT-READY and NOT AUTHORIZED; the third is CLOSED.** Three single-factor
cells are specified here and **none is flown by the rows that write this document**
(`SAEA-E22-MF-OVERGENERATION-ANALYSIS-V1` and `SAEA-SN-MF-E22-DEV1500-ROSTER-V1`, both
`model-free-check`). Each cell needs its own owner GO, its own exposure row registered before its
first contact, and its own `contracts.ExecutionPlan`. Nothing below may be executed on the
authority of this file.

**2026-09-06 update, all model-free.** Cells (a) and (b) are now flight-ready: their fragments,
their model-free preconditions and their contact-free wire checks are landed and are cited in place
(§1.3, §1.3.1, §2.3, §2.3.1, §6, §7). Cell (c) is **CLOSED** by the owner's refusal of the 22 GB
acquisition its population would have required (§3), with its blocking facts kept. **Flight-ready is
not authorized**: no cell here has an owner GO, no exposure row is registered, and no model has been
contacted by any row that produced this update.

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

**Answered offline, 2026-09-06: `N = 28`, and the expectation above is now a derivation.** Receipt
`docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-dev-usage-cells/q8-placement.json`
(`scripts/e22_q8_placement_offline.py`, **zero model contacts, zero servers, zero sockets, zero
GPU, zero network**). The Q8_0 and mmproj GGUF **headers** are parsed in place — metadata block and
tensor table only, no tensor payload, no model load — and the arithmetic is closed by the A2T
probe's own live ladder:

| term | value | where it comes from |
|---|---:|---|
| expert tensors per layer | **612.0 MiB** | the Q8_0 tensor table: `ffn_gate_exps` + `ffn_up_exps` + `ffn_down_exps`, 641,728,512 B, identical on all 48 blocks |
| non-expert weights | **1,597.93 MiB** | the same table, everything else (1,675,550,720 B) |
| q8_0 KV cache | **52,224 B/token** → **2,040.0 MiB** at 40,960 | `block_count` 48 × `head_count_kv` 4 × (`key_length` 128 + `value_length` 128) at 34 B per 32 elements |
| resident bf16 mmproj | **2,105.16 MiB** | the mmproj tensor table (2,207,416,320 B) |
| CUDA context + compute buffers | **1,070.91 MiB** | fitted on the A2T ladder — **spread 0.0 MiB across all seven non-saturated rungs** |

The fit is not a curve through noise: at `-c 49152 -np 3` the measured `used_mib` is *exactly*
`1597.93 + (48 − N)·612 + 2448 + 2105.16 + 1070.91` at N = 48, 44, 40, 36, 32, 28 and 24. The N = 20
rung is excluded by name — the card was full (14 MiB free), so that figure is a truncation rather
than a placement. Re-run at `-c 40960 -np 8` (408 MiB less KV) against the 24,137 MiB an idle card
reports:

| `--n-cpu-moe` | projected used | projected free | ≥ 3,072 MiB |
|---:|---:|---:|:--|
| 32 | 16,606 MiB | 7,531 MiB | yes |
| **28** | **19,054 MiB** | **5,083 MiB** | **yes — chosen, 2,011 MiB of margin** |
| 24 | 21,502 MiB | 2,635 MiB | **no — short by 437 MiB** |

**`N = 24`, the A2T probe's own answer, misses this cell's floor by 437 MiB.** Copying it would have
been the fault caveat 2 warned about.

**The one quantity that does not carry over is named rather than hidden**: the compute-buffer and
CUDA-context constant is measured at `-c 49152 -np 3` and reused at `-c 40960 -np 8`. The answer is
not delicate in either direction — N = 28 still clears the floor if that constant were **2,011 MiB
larger** (nearly triple what the ladder measured), and N = 24 would only clear if it were **437 MiB
smaller** at a geometry with *more* slots, which is the wrong sign. Host RAM is not the binding
constraint either: 28 layers is 17,136 MiB of experts on the CPU, against the 18,533 MiB of server
RSS the A2T ladder measured at that same N with 54,633 MiB available.

Also closed by that pass: the Q8_0 GGUF is materialized at `/home/chao` and **re-hashes to
`8a50e5a7d29ae6a28fea9ca45e3bb0a142e76ec07e6787a7703cd498eb08ffaa`**, and the mmproj to
`f0dfe825…` — the first half of the §6(a) precondition, done by reading 32 GB rather than trusting
a receipt.

**This does not discharge Q8-P1, and the receipt says so in its own `status` field.** Q8-P1 is a
LIVE pass; this is a projection of what it will find, so the rung ladder is short and the answer is
falsifiable before a GPU minute is spent. The live pass still must: start the pinned server at
N = 28 and read free VRAM through `GET /props` and `nvidia-smi` with zero `/completion` calls; read
llama.cpp's **own printed** audio-encoder compute-buffer estimate at this geometry and refuse if it
exceeds the achieved free; confirm no `LLAMA_MTMD_FEAT_CACHE_DIR` in `server_env`; and check
`enforced.power.limit` and the Legion SmartFanMode first. **If the live pass disagrees, the live
number governs and this projection is the thing that was wrong.**

### 1.3.1 The cell's fragments, and its composed identity

| | |
|---|---|
| dataset | `configs/dataset/earnings22-esb-dev1500-utterances.json` |
| baseline | `configs/baseline/e22-esb-dev1500-q8.json` |
| model | `configs/model/q8-e22-dev1500-esb-mmproj-gpu-04ccc72a-np8-c40960.json` |
| experiment | `configs/experiment/e22-dev-usage-q8-v1.json` |
| **`config_hash`** | **`8789a5abfc85926e96c5bdbd57cab688e8a6d7d20809a8b7d0483979730da5ea`** |
| **`protocol_hash`** | **`c77a10accae07c02cdcd7b2df8dbf650a53498408e7d53421059a3c8a341886d`** |
| `split_identity_hash` | `c626e62f8876bf52a2904a0d2ec91807a530f3195c10facc8c036f661b2bf88a` |
| run id | `SAEA-E22-DEV-ESB-Q8-V1` |

The 4-row dry run of §6.6: `configs/dataset/earnings22-esb-dev1500-smoke4.json` +
`configs/experiment/e22-dev-usage-q8-smoke4-v1.json`, `config_hash`
`348506249bbf8874a124a0e20b760aa45b6be05ac9c5589f28409965ad92d51a`, `protocol_hash`
`605b30f7a181815368e7ac17fe92c80c16691d94013d46ecf63729ee0f83979f`, `split_identity_hash`
`c5b9886a421a9d9483c934759d9cb2a9d3b0eee2a029f73726883179f6f5f033`.

One further deviation, **S5**: the model fragment sets `timeout_seconds` to 900 rather than the
comparator's 420. At 7.85× the per-call latency a 420 s client deadline is a real risk of losing the
attempt to a timeout; it is a client-side deadline, not a request field, and changes no byte the
server sees.

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

### 2.3 The seam, and why the cap could not be a config value

`decoding_params.max_tokens` was composed **per cell**, not per sample:
`core.flight.FlightRuntime._decoding_params` read one mapping off the composed config and handed the
same one to every request. A duration-proportional cap therefore needed a per-sample resolution seam,
and there was exactly one precedent for it in this repository — `id_slot: "per-sample"`, which
`FlightRuntime` resolves per request and `core.model.adapter.FrozenCoreAdapter.request` refuses if it
ever arrives unresolved.

**The seam, as specified above before it was written, and as it LANDED on 2026-09-06.** The
specification's substance is unchanged — resolution moves, nothing else does — and the one shape
change is named as a deviation below rather than quietly absorbed.

A config fragment declares the cap as an OBJECT instead of an integer:

```json
"decoding_params": {
  "temperature": 0,
  "seed": 20260803,
  "max_tokens": {
    "policy": "duration-proportional-v1",
    "alpha": 1.5,
    "words_per_second_p95": 4.999220954734555,
    "tokens_per_word": 1.2991996296395218,
    "floor": 1,
    "ceiling": 1024
  },
  "id_slot": "per-sample"
}
```

* **`duration-proportional-v1` is a registered id**, in the new one-entry registry
  `core.base.MAX_TOKENS_POLICIES`, populated from `core/policies.py` — one of the canonical
  registration sites `scripts/checks/engineering_base_check.py` already reads. The check resolves
  this id by PATH (`decoding_params.max_tokens.policy`) across `configs/model`,
  `configs/baseline` and `configs/experiment`, so the owner rule "every component id a config
  declares resolves in a `core.base` registry" now covers the cap too. The check PASSES.
* **The arithmetic is frozen under that id**: `min(ceiling, max(floor, ceil(alpha · seconds ·
  words_per_second_p95 · tokens_per_word)))`, numerically identical to
  `analysis.e22_overgeneration.cap_tokens(...)` clamped — pinned row for row by
  `tests/unit/test_max_tokens_policies.py`, because the simulator's projection and the flight's cap
  must be the same intervention or the §2.2 prediction check compares two different things. A
  different formula is a different id.
* **`FlightRuntime` resolves it where it already resolves `id_slot`**, from the sample's own
  `audio_seconds`: `_sample_decoding_params(sample, base)` is called in the concurrent dispatcher's
  per-request assembly (`_dispatch_concurrent.one`, the path an `-np 8` cell takes), in the
  serial packet path, and — as a per-sample callable `rails.runner.run_rails_experiment` invokes
  once per sample — in the serial raw-audio path. A malformed or unregistered rule is refused in
  `_decoding_params()`, once, **before any sample is dispatched**.
* **`core.model.request_types.ALLOWED_DECODING_KEYS` is unchanged.** `max_tokens` was already
  admitted; only its resolution moved.
* **The adapter refuses a non-integer `max_tokens` reaching the transport**, exactly as it refuses
  an unresolved `id_slot`, so a silent fall-through is impossible
  (`tests/unit/test_frozen_core_adapter.py::test_decoding_params_max_tokens_unresolved_rule_refused`).
* **A phase program is refused outright**: its contacts are built by `rails.phase_runner` from one
  run-level mapping, so a rule there would travel unresolved. `_phase_decoding_params` refuses it
  before a server start rather than after one.
* **Absent a rule, every fragment that predates this seam renders byte-identical requests.** The
  resolver returns the base mapping *by identity*, not a copy, so nothing is rebuilt and no key is
  reordered. Pinned three ways in `tests/unit/test_flight_runtime.py`:
  `test_a_plain_integer_max_tokens_is_handed_on_by_identity`,
  `test_the_serial_rails_path_passes_a_plain_mapping_through_unchanged`, and
  `test_a_token_matched_rule_dispatches_byte_identically_to_the_integer` — which drives two full
  wire checks, one on the plain integer 1024 and one on a rule clamped to 1024 for every sample, and
  asserts the two `request_body_sha256` lists are **equal**.

**Deviation S3, named rather than absorbed.** The specification above imagined a string sentinel
`max_tokens: "per-sample-duration"` beside a sibling fragment-level `max_tokens_duration_rule`
object. What landed puts the rule **in** `max_tokens`, as one object carrying its own `policy` id.
Three reasons, all of which post-date the specification: the owner's 2026-09-03 rule requires the
component id to resolve in a `core.base` registry, which a bare sentinel string is not; a sibling
top-level key would have to stay disjoint across all four fragments (`core.config.compose`) while
being bound to a key in a different object, which nothing else in this repository does; and one
object lets the base check resolve the id by path without teaching it that a nested `"policy"` key
sometimes means something other than an arm program's policy. Fail-closed in both directions is
preserved and strengthened: there is no way to declare half of it.

**Deviation S4.** The seam is **fragment-agnostic**. `core.config.compose` merges the four fragments'
top-level keys into one flat mapping, so whichever fragment carries `decoding_params` carries the
rule. Cell (b) puts it in the MODEL fragment, following this repository's own convention — 67 model
fragments declare `decoding_params` and no baseline fragment does.

This is a seam on the existing base, not a new module: no `rails/probes/` module, no `TaskAdapter`
subclass, no controller subclass, no `launcher/` directory, no new file under `src/` at all.

The resolved per-row `max_tokens` lands in the trace's `decoding_params` (the adapter emits the whole
payload in its `MODEL_REQUEST` record), so **every row's cap is auditable after the fact** without a
new receipt shape. The `run_phases` receipt additionally carries `max_tokens` and
`max_tokens_resolution`, and a wire check carries `max_tokens_policy`, `max_tokens_rule` and
`max_tokens_per_sample` — the resolved integer of **every** request, keyed by sample id, each
re-derived at the transport seam from that request's own `audio_seconds` and refused if it disagrees.

### 2.3.1 The cell's fragments, and its composed identity

| | |
|---|---|
| dataset | `configs/dataset/earnings22-esb-dev1500-utterances.json` |
| baseline | `configs/baseline/e22-esb-dev1500-stopcap.json` |
| model | `configs/model/q4km-e22-dev1500-esb-stopcap-mmproj-gpu-04ccc72a-np8-c40960.json` |
| experiment | `configs/experiment/e22-dev-usage-stopcap-v1.json` |
| **`config_hash`** | **`d47999a6ecc9b16b058017a80253f24dc1a160401ddddd2ecf683901edf6e460`** |
| **`protocol_hash`** | **`4fda9f678991ab09d2280113aa3202db0fa74df41543a3b91235dbb837a8b6e4`** |
| `split_identity_hash` | `c626e62f8876bf52a2904a0d2ec91807a530f3195c10facc8c036f661b2bf88a` |
| run id | `SAEA-E22-DEV-ESB-STOPCAP-V1` |

The 4-row dry run of §6.6 is its own run id with its own exposure row (a different split identity
hash and a much smaller budget cannot share one): fragments
`configs/dataset/earnings22-esb-dev1500-smoke4.json` +
`configs/experiment/e22-dev-usage-stopcap-smoke4-v1.json`, `config_hash`
`78205c9eeb302ee75ba06a52b479a5c2a858f5faf50627f2beee8d5891712d17`, `protocol_hash`
`e03ec753c2b5e0205d24aa9c881e1a4fc636d25a0caa23c1a51e89226fb267e9`, `split_identity_hash`
`c5b9886a421a9d9483c934759d9cb2a9d3b0eee2a029f73726883179f6f5f033`, four rows
(`4469088-654`, `4479944-334`, `4482383-188`, `4482613-439` — shortest, p90, longest, median) whose
caps resolve to **3, 127, 321 and 55**. Four different integers on four rows is what makes the dry
run a test of the seam rather than of one arbitrary cap.

**`protocol_hash` is `compute_protocol_hash(config_hash, arm, split_identity_hash)` and is the value
the `contracts.ExecutionPlan` must carry.** Both hashes move if any fragment byte moves, so a cell
flown under a different hash is a different cell.

Across the whole 1,500-row roster the rule resolves to caps between **3 and 321 tokens**, mean
**65.1**, and **not one row reaches the 1,024 ceiling** — the cap is a genuine tightening on every
row of this population, exactly as §2.1 claims.

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

## 3. Cell (c) — `SAEA-E22-DEV-ESB-FRONTEND-V1` — **CLOSED (owner, 2026-09-06)**

**One factor: the audio decode path. And it cannot be flown from anything on this machine.**

> **CLOSED, 2026-09-06.** §3.2 put the unblocking price to the owner: a 22,039,334,688-byte
> acquisition of all 55 ESB train shards, or a targeted row-group projection of the `audio` leaf
> over the network. **The owner refused the 22 GB fetch.** With no dev arrays on disk and no
> authorization to acquire them, the cell has no population, and it is closed rather than left
> pending: a BLOCKED cell invites a later agent to look for a way around the block, and the way
> around it here runs through the four ESB **test** shards that are on disk — which this cell is
> forbidden to touch, because it is scoped to dev and because reading test audio content would be a
> second answer-bearing read of a one-shot asset.
>
> **Nothing below is deleted, and that is deliberate.** §3.1–§3.5 are the blocking facts, the price
> in identity, and the confound the cell could never have removed. They stay because the front end
> is still an unmeasured difference between this study and the published evaluations, and whoever
> revisits it should start from what was already established rather than re-derive it: the two paths
> agree on the span and differ on the decode; the difference is **four** things at once (source
> container, sample rate, channel fold, a sub-frame span difference with a median of +0.0000316 s),
> and one cell could never have said "the resampler is worth X points".
>
> **Reopening it needs an owner decision and this file is not one.** If the owner ever authorizes the
> acquisition, §3.3's identity rebuild is executable unchanged — new version directory
> `derived/e22-esb-utterances/dev-fe-v1/`, `@fe1`-suffixed sample ids, a new roster probe view and a
> new D1 media supplement — and it is an **umbrella** action with its own accounting
> (`docs/datasets.lock.json`, `scripts/data/`), never something this study does unilaterally.
>
> **What this closure does not mean.** It is not a finding that the front end does not matter. It is
> a finding that this study cannot measure it at an acceptable cost today, and the honest reading of
> §1, §2 and this section together is the one §5 already states: all three faces of model usage are
> bounded small, and the mechanism these documents keep pointing at is elsewhere.

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

**Recommended order — SUPERSEDED as an ORDER by §7.** The owner sequenced (a) before (b) on
2026-09-06. The reasoning below is on the record and stands as reasoning, not as the order.

**The original reasoning.** (b) is the cheapest (0.20 GPU-h) and its
prediction is already fixed, so it is the fastest falsifiable thing available; (a) is the largest
untested runtime factor but costs ten times as much GPU; (c) cannot start without an owner decision.
The over-generation verdict bounds (b)'s payoff at a quarter of a point and says so — if the owner
would rather not spend a flight on that, the honest reading is that **all three faces of model usage
are now bounded small, and the boundary-exact cell is the intervention that addresses the mechanism
every one of these documents keeps pointing at.**

---

## 6. Preconditions, all model-free, all before the first contact

Common to every cell:

1. **Configuration fragments**, none of which existed when this was written and each of which is one
   file: `configs/dataset/earnings22-esb-dev1500-utterances.json` (naming the §0 probe view, the D1
   supplement and their digests, the reference-layer receipt and the segment-table receipt the
   dev10 fragment already pins); `configs/baseline/e22-esb-dev1500-*.json` per cell; one
   `configs/model/*` fragment per cell; one `configs/experiment/*` fragment. Every `policy`,
   `evidence_source` and `scorers` value must resolve in a `core.base` registry, and
   `scripts/checks/engineering_base_check.py` must PASS.

   **Landed 2026-09-06, with one deviation.** The fragments are §2.3.1's for cell (b) and §1.3.1's
   for cell (a). The deviation is **one experiment fragment PER CELL** rather than one for all
   three (deviation S1, recorded in each fragment): a composed experiment fragment declares exactly
   one `execution_plan` object, `core.flight.FlightRuntime._build_execution_plan` reads
   `values["execution_plan"]`, and cell (a) plans 2.0 GPU-hours against cell (b)'s 0.20 — the two
   cannot share one plan. `configs/experiment/a2t-evo-a1-description-evolution-v1.json` already
   records the same constraint for its own split. Each cell's 4-row dry run (§6.6) is a further
   fragment pair for the same reason `contracts.gate_exposure` requires: a different split identity
   hash cannot share a run id. `scripts/checks/engineering_base_check.py` PASSES, and it now
   resolves the cap's own policy id as well (§2.3).
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

   **LANDED 2026-09-06 for all four run ids**, in
   `docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-dev-usage-cells/wire-check/`.
   **Both halves passed on every one**: the client half (1,500 / 1,500 / 4 / 4 requests, payload keys
   exactly `ARM_VISIBLE_FIELDS["bare-core"]`, integer `id_slot` over all eight slots, concurrent
   dispatch) and the seal-and-score half (`status: OK`, manifest built and verified, the complete
   21-column ledger surface validated, every registered scorer run to completion). Cell (b)'s two
   receipts carry `max_tokens_per_sample` — **202 distinct integers across the 1,500 rows, 3 to 321**,
   and 3 / 55 / 127 / 321 on the four dry-run rows — each one re-derived at the transport seam from
   that request's own `audio_seconds` and refused on any disagreement.

   The receipt-hygiene rule above was learned the hard way again while doing this: a first pass ran
   with an edit open in the working tree and **all four scoring jobs failed**, because
   `core.scorers._assert_scoring_entry_gate` calls `require_clean_study_repo`. The receipts here are
   from the re-run on a clean tree at commit `3f33234e`; only documents and receipts were added
   after it.
6. **A 4-row dry run** before the flight, on four of the 1,500. Fragments and go/no-go landed
   (§1.3.1, §2.3.1); the dry run itself is a model contact and is the flight agent's, not this
   document's.
7. **A clean working tree for the whole run.** A COMPLETED manifest reads `study_commit` at finalize
   and refuses a dirty tree — and so does the SCORER, before it reads a row.

Cell-specific:

* **(a)** the placement pass of §1.3, with its own receipt, zero generated tokens, and a refusal if
  no `N` clears 3,072 MiB free at `-c 40960 -np 8`. Also: confirm the Q8_0 GGUF is materialized and
  re-hashes to `8a50e5a7…`, and that **no** `LLAMA_MTMD_FEAT_CACHE_DIR` is set in `server_env`.
  **PROJECTED 2026-09-06, still open as a live pass.** `N = 28` with 5,083 MiB projected free
  (§1.3), receipt
  `docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-dev-usage-cells/q8-placement.json`;
  the Q8_0 GGUF **re-hashed to `8a50e5a7…`** and the mmproj to `f0dfe825…`; the model fragment
  carries no `LLAMA_MTMD_FEAT_CACHE_DIR` in `server_env`. What remains is the live half — one
  zero-token server start at N = 28 reading `GET /props` and `nvidia-smi`, and llama.cpp's own
  printed encoder estimate at this geometry.
* **(b)** the seam of §2.3 with its tests, including the byte-identical-without-the-seam pin; and a
  model-free assertion that the resolver reproduces
  `analysis.e22_overgeneration.cap_tokens(1.5, seconds, 4.999220954734555, 1.2991996296395218)` on
  every one of the 1,500 rows, clamped to 1,024. **CLOSED 2026-09-06.** The seam landed (§2.3) and
  `scripts/e22_stopcap_resolver_check.py` composed the four real fragments, resolved through the
  registered policy and compared row for row against the simulator:
  `docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-dev-usage-cells/stopcap-resolver.json`
  — **1,500 rows checked, 0 disagreements**, caps from 3 to 321 tokens (median 55, mean 65.1),
  **0 rows at the 1,024 ceiling**, and the §2.1 ladder (10 / 49 / 98 / 321) reproduced. The cell's
  planned completion-token ceiling falls from 1,536,000 to **97,673**, a 15.7× reduction in what the
  decoder is allowed to emit — which is the size of the intervention, not of its expected payoff.
* **(c)** **MOOT — the cell is CLOSED (§3).** Kept as written so that an owner who ever
  authorizes the acquisition inherits the sequence rather than re-deriving it: unblocking first
  (§3.2), then the identity rebuild of §3.3, then a byte-determinism check — cut twice, assert
  `items_sha256` is unchanged — exactly as the `dev-v1` cut was proved.

---

## 7. The flight agent's checklist

**Sequence, owner 2026-09-06: (a) then (b).** This supersedes §5's cheapest-first recommendation.
The owner ordered the Earnings-22 Q8 and stop-cap cells as the next GPU item and put Q8 first; §5's
reasoning stands as reasoning and is not the order.

Everything marked LANDED below is done, model-free, and cited in place. Everything else is the
flight agent's, in this order.

### 7.0 Before anything, once

1. **Read the owner GO for the specific cell.** There is none in this file. **If there is no owner GO
   for the cell you are about to fly, stop here.** Flight-ready is not authorized.
2. **Check the GPU before anything else**: `nvidia-smi -q -d POWER` for `enforced.power.limit`, and
   the Legion SmartFanMode. A Quiet-mode 35 W cap silently overrides everything, reverts silently on
   Fn+Q and on reboot, and has recurred.
3. **Front-load the model load** as a background step at mission start; run the CPU work below
   during it and join at the first session-bound step. For cell (a) this matters more than usual: a
   30.3 GiB Q8_0 load faults 17,136 MiB of expert tensors into host RAM.
4. **A clean working tree for the whole run.** A COMPLETED manifest reads `study_commit` at finalize
   and refuses a dirty tree, and receipts written straight into `docs/checks/` are how the
   2026-09-05 A/B experiment lost three of four scoring gates. Write receipts outside the tree and
   copy them in afterwards.

### 7.1 Rows

5. **Register the exposure row before the first contact**, one per run id, naming the population, the
   comparator attempt (`SAEA-E22-DEV-ESB-PROMPT-A-V1` / `attempt-20260905T073641Z-f977d1`), the
   budget, the ceilings and the claim rule of §4. The plan's `split_identity_hash` and the row's must
   both be `c626e62f…` for a flight and `c5b9886a…` for a 4-row dry run. Four run ids exist here and
   each needs its own row: `SAEA-E22-DEV-ESB-Q8-V1`, `SAEA-E22-DEV-ESB-Q8-SMOKE-V1`,
   `SAEA-E22-DEV-ESB-STOPCAP-V1`, `SAEA-E22-DEV-ESB-STOPCAP-SMOKE-V1`. Budget is metered
   **cumulatively across every attempt of a run id**, so a recovery plan must cover prior durable
   spend as well as its own worst case.

### 7.2 Model-free preconditions — stop on any refusal

6. **LANDED — the seam and its resolver check** (§2.3, §6(b)):
   `docs/checks/…/2026-09-06-e22-dev-usage-cells/stopcap-resolver.json`, 1,500 rows, 0 disagreements
   against `analysis.e22_overgeneration.cap_tokens`, 0 rows at the ceiling.
7. **LANDED — the Q8 placement, cited as the projection it is** (§1.3):
   `docs/checks/…/2026-09-06-e22-dev-usage-cells/q8-placement.json` — `--n-cpu-moe 28`, 5,083 MiB
   projected free against a 3,072 MiB floor, and N = 24 short by 437 MiB. The Q8_0 decoder re-hashes
   to `8a50e5a7…` and the mmproj to `f0dfe825…`.
8. **STILL OPEN — the LIVE half of Q8-P1, cell (a) only.** One zero-token server start at
   `--n-cpu-moe 28`, `-c 40960 -np 8`: read free VRAM through `GET /props` and `nvidia-smi`, read
   llama.cpp's **own printed** audio-encoder compute-buffer estimate at this geometry, and **refuse
   if the achieved free is below 3,072 MiB or below that estimate**. No `/completion` call. **If no N
   clears the floor the cell STOPS** — it does not shrink `-np`, and a geometry change is a new
   registration.
9. **LANDED — the wire check**, zero contacts, zero servers, zero sockets, for all four run ids:
   `docs/checks/…/2026-09-06-e22-dev-usage-cells/wire-check/`. It was run in the `wt/e22b` worktree;
   §7.6 says what to re-run on the primary checkout and why.
10. **STILL OPEN — roster hydration, media identity and prompt fit at flight time.**
    `FlightRuntime.preflight` recomputes `c626e62f…` from the probe view; `contracts.gate_media_identity`
    re-reads `docs/receipts/artifacts/d1-e22-esb-dev1500-utterances.json`; and the live `n_ctx` per
    slot must be 5,120 through `GET /props` against a worst request of ≈1,504 tokens
    (429 speech + 49 envelope + 1,024 completion + 2 special).
11. **STILL OPEN — the 4-row dry run**, per cell, on its own run id: `E22-DEV-ESB-Q8-SMOKE-4` then
    `E22-DEV-ESB-STOPCAP-SMOKE-4`. Its go/no-go is written in each smoke fragment's own `decision`
    block. For cell (b) the binding read is that the four requests carried four **different**
    resolved caps — 3, 55, 127 and 321 — each equal to the rule's own resolution for that row's
    duration.

### 7.3 Cell (a), `SAEA-E22-DEV-ESB-Q8-V1`

12. Fly **one attempt**: 1,500 contacts, `-c 40960 -np 8 --n-cpu-moe 28`, no repair, no retry, no
    resend. At most one recovery re-registration; a second failure stops the flight and the fix is
    proven on a 4-row dry run.
13. **Score once**, over the complete manifest, through `core.scoring_batch`, `verified: true`,
    never sharded. Paper-facing scorer `asr-wer-esb-whisper`; `asr-wer-esb` and `cost` beside it.
14. Run **`analysis.e22_error_taxonomy` at its committed version** on the new outputs — the agentic
    rate hook — and report the agentic error rate and the boundary mass beside the WER.

### 7.4 Cell (b), `SAEA-E22-DEV-ESB-STOPCAP-V1`

15. Fly **one attempt**: 1,500 contacts, the same geometry, the Q4_K_M decoder, the per-sample cap.
    Same one-attempt and one-recovery discipline.
16. **Score once**, exactly as step 13.
17. Run the agentic-rate hook, exactly as step 14.

### 7.5 Verdicts

18. Run the paired contrast of §4 against the **sealed** arm A rows restricted to these same 1,500 —
    never against a re-run. `analysis.paired.paired_contrast`, **stratified by source call (10
    strata), 10,000 replicates, seed 20260903, CI90**, on **both** metrics: corpus WER under the
    Whisper `EnglishTextNormalizer` and the agentic error rate, each signed as `cell − arm A`.
19. Apply the decision rule of §4 **as preregistered, unmodified**: ADMITTED iff corpus WER improves
    with a CI90 **upper** bound below 0, **and** the agentic error rate's CI90 upper bound is below
    **+0.05** points.
20. Write each verdict with the per-stratum table for all ten calls, both normalizers, natural-mixture
    and equal-call weightings side by side, the S/D/I split, the hypothesis-to-reference length ratio,
    the utterance-duration decomposition, and the boundary category mass before and after. For cell
    (b) add the **prediction check** of §2.2 — measured rows-capped / benefit / harm beside the
    predicted 50 / 35 / 15 — named as a prediction check. For cell (a) add the achieved free VRAM
    beside the 5,083 MiB projection and the measured Q8_0-to-Q4_K_M latency ratio beside the 7.85×
    the budget assumed.
21. **Stop.** No test read, no third cell, no mechanism arm.

### 7.6 What must be re-run on the primary checkout, and why

The wire checks of step 9 ran in the `wt/e22b` worktree, through the committed launcher's own
`build_runtime` with only its `REPO` constant repointed. That is enough to prove the request path,
the payload allowlist, the dispatch and the per-request resolved cap — none of which depends on
which checkout the code sits in. It is **not** a substitute for the primary checkout's own run,
because two things there are checkout-specific: `study_commit` and the clean-tree assertion the seal
half exercises, and the launcher's `REPO` pin itself. **Re-run
`scripts/flights/run_e22_esb_cell.py --wire-check` on the primary checkout, unpatched, immediately
before the flight**, and land its receipt beside these.

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
