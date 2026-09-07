# Earnings-22 DEV cell (b), `SAEA-E22-DEV-ESB-STOPCAP-V1` — flight receipts

Cell (b) of `docs/readiness/2026-09-06-e22-dev-usage-cells-v1-preregistration.md`: one factor, a
**duration-proportional generation cap**, on the 1,500-row `E22-DEV-ESB-1500-V1` subset of this
study's own Earnings-22 DEV subset10. Exposure rows `SAEA-E22-DEV-ESB-STOPCAP-SMOKE-V1` and
`SAEA-E22-DEV-ESB-STOPCAP-V1`, both registered before the first contact at commits `1894f0ab` and
`19be4266`.

The cap is `min(1024, max(1, ceil(1.5 · media_seconds · 4.999220954734555 · 1.2991996296395218)))`,
resolved per sample by `core.flight.FlightRuntime` through the registered
`core.base.MAX_TOKENS_POLICIES` entry `duration-proportional-v1`. Everything else — instruction,
prompt shape, decoder, mmproj, media bytes, build, geometry, harness, entry point — is the sealed
comparator's, byte for byte.

**No verdict lives here.** The paired contrast against the sealed
`SAEA-E22-DEV-ESB-PROMPT-A-V1` (`attempt-20260905T073641Z-f977d1`), its call-stratified CI90, the
preregistered decision rule and the §2.2 prediction check are a later document's; this directory
carries what the cell measured and nothing else.

## `smoke-4/` — the four-row dry run, and the seam it exists to test

Four rows chosen before any contact by the deterministic longest / shortest / median / p90 rule, on
one Q4_K_M server session at the sealed `-c 40960 -np 8` geometry. Attempt
`attempt-20260907T042025Z-b8bfc6`, COMPLETED and FINALIZED on study commit `19be4266`.

**The binding read is that four rows carried four different caps, each equal to the rule's own
answer for that row's duration**, read back out of the sealed trace's `decoding_params` rather than
out of the config:

| sample | seconds | resolved `max_tokens` | the rule's own answer | completion tokens | cap bound |
|---|---:|---:|---:|---:|---|
| `4469088-654` (shortest) | 0.219938 | **3** | 3 | 3 | **yes** |
| `4482613-439` (median) | 5.580313 | **55** | 55 | 18 | no |
| `4479944-334` (p90) | 13.020250 | **127** | 127 | 53 | no |
| `4482383-188` (longest) | 32.880000 | **321** | 321 | 97 | no |

Four different integers on four rows is what makes this a test of the **seam** rather than of one
arbitrary cap. Zero disagreements with the policy, zero rows at the 1,024 ceiling, and every request
carried exactly the four admitted decoding keys (`id_slot`, `max_tokens`, `seed`, `temperature`)
with `id_slot` an integer per slot.

The other three go/no-go reads, all affirmative:

| read | value |
|---|---|
| live `n_ctx` per slot, through the server's own log | 5,120 on all eight slots |
| CUDA fault / out-of-memory / `GGML_ASSERT` in the server log | **0 / 0 / 0** |
| both ESB scorers on the sealed manifest through `core.scoring_batch` | `verified: true`, 1 job, 0 failed |
| model load | 11.38 s |
| four contacts | 2.65 s wall, 1.92 s mean latency — the sealed comparator's own 1.927 s mean |
| llama.cpp's printed worst-case mmproj estimate at this geometry | 2,940.29 MiB |
| projected flight residency | ≈ 0.12 GPU-h against the 0.35 registered ceiling |

**Every row encoded live.** The argv carries no cache flag, `server_env` declares only
`GGML_CUDA_DISABLE_GRAPHS=1`, no `LLAMA_MTMD_FEAT_CACHE_DIR` exists in the launching shell, and the
server log shows `process_mtmd … encoding mtmd batch` for all four rows — exactly as the sealed
comparator encoded them.

The dry run's own WER numbers are on four rows and enter no verdict.

### Files

| path | what it is |
|---|---|
| `smoke-4/caps-4.json` | the per-row read off the sealed trace: resolved cap, the rule's own answer, completion tokens, whether the cap bound |
| `smoke-4/flight-receipt.json` | the launcher's own stage receipt (preflight, preprocess, serve, run_phases, seal, score, stop) |
| `smoke-4/score.json` | the sealed score file `core.scoring_batch` produced, copied byte for byte |

## `flight-1500/` — the cell, flown

One attempt, 1,500 of 1,500 contacts, COMPLETED and FINALIZED on study commit `47adbd43` with
`study_repo_dirt` empty, attempt `attempt-20260907T042641Z-2a48e8`. No recovery re-registration was
used and none was needed. Manifest SHA-256 `4c841511…`, outputs SHA-256 `799c4c68…`, aggregate score
SHA-256 `e0cad827…`, `config_hash` `d47999a6…`, `protocol_hash` `4fda9f67…`, split identity
`c626e62f…`.

### The cap, on the wire, on every row

| | value |
|---|---|
| requests carrying an integer cap resolved from their own `audio_seconds` | **1,500 / 1,500** |
| disagreements against the registered policy's own resolution | **0** |
| caps | 3 to 321 tokens, median 55, mean 65.115, **202 distinct values** |
| rows at the 1,024 ceiling | **0** |
| **rows where the cap bound** (completion tokens equal to that row's own cap) | **68** |
| completion tokens the decoder was ALLOWED | 97,673 against the 1,536,000 a cell-wide 1024 allows |
| completion tokens it actually EMITTED | **36,769** (mean 24.51, largest 109) |

Every integer is read back out of the sealed trace's `decoding_params`, not out of the config. The
largest completion on the whole flight is 109 tokens against a largest cap of 321, so the 1,024
ceiling this rule clamps to never came into it on any row.

### Raw numbers. Nothing here is a contrast.

| | value |
|---|---|
| corpus WER, Whisper `EnglishTextNormalizer` (paper-facing) | **17.2603 %** |
| S / D / I over 26,251 reference words | 1,141 / 593 / 2,797 |
| mean of per-utterance WER, same normalizer | 30.2146 % |
| corpus WER, frozen `saea-scoring-v1` | 22.5524 % over 26,822 reference words |
| agentic error rate (`analysis.e22_error_taxonomy`, HIGH reference-word mass) | **1.9009 %** (358 HIGH spans, 499 HIGH reference words) |
| the same rate with `segmentation-artifact` no longer neutral (strict) | 2.0456 % |
| boundary category mass | 2,125 error operations = **8.0949 WER points** (segmentation 932 + runaway tail 1,137 + runaway head 56) |
| hypothesis-to-reference length ratio | 1.0840 |
| insertion share of all errors | 61.73 % |

Scored **once**, over the complete manifest, through `core.scoring_batch`, `verified: true`, never
sharded, with the manifest's own three scorers. A second pass over the *same* complete manifest with
`include_per_sample=True` produced 1,500 per-row entries for each ESB scorer; those rows live under
`SPEECHRL_DATA_DIR` and never enter this repository, so the receipt pins them by digest instead.

**Both identity conditions hold.** The taxonomy's aligner reproduces the sealed scorer's S/D/I and
corpus WER on these outputs exactly — 1,141 / 593 / 2,797 and 17.2603 % — which is the condition that
module imposes on itself before any figure it produces may be read. The same call on the sealed
comparator's rows restricted to these 1,500 ids reproduces the preregistration's own published subset
figures (17.4012 % corpus WER, 1.9161 % agentic) to the digit. That is a method check on the reading
path, not a comparison.

### Cost

| | value |
|---|---|
| generation wall | 410.8 s |
| GPU-hours, llama-server residency | **0.123 h** against 0.20 planned and 0.35 registered |
| contacts / s at eight occupied slots | 3.652 |
| mean per-call latency | 2.013 s; summed 3,020.0 s |
| realtime factor | 24.22x |
| model load | 10.11 s |
| prompt / completion tokens per call | 141.9 / 24.5 |
| against the sealed comparator's 1.927 s and 3.744 contacts/s | **1.045x** on latency, **0.975x** on throughput |

Latency and throughput sit within 5 % of the sealed comparator's figures in both directions, which
is the size of the run-to-run variation this runtime shows at a fixed geometry; a cap that bites 68
of 1,500 rows is not expected to move either. The flight finished in under two thirds of its planned
GPU-hours and about a third of its registered ceiling.

### The card, over 410 seconds of real work

Over 83 resident samples the card held **1,208 MiB free** at its tightest with 22,930 MiB used —
this is the fully resident Q4_K_M at the sealed `-c 40960 -np 8`, not a placement question — at
70.5 % mean utilisation and a peak of 93.15 W under a 100.00 W enforced limit. Zero CUDA faults, zero
out-of-memory lines and zero `GGML_ASSERT` in the server log; live `n_ctx` 5,120 on all eight slots;
server RSS peaked at 18,041 MiB with host available never below 44,758 MiB; the card back to 0 MiB
after the runner's own `stop_serving`.

**Every row encoded live.** No cache flag in the argv, `server_env` declaring only
`GGML_CUDA_DISABLE_GRAPHS=1`, no `LLAMA_MTMD_FEAT_CACHE_DIR` anywhere, and 2,077 `process_mtmd`
encode lines in the server log — the same path the sealed comparator took.

### Files

| path | what it is |
|---|---|
| `flight-1500/flight-read.json` | the assembled read: identity and hashes, the cap block, budget, throughput, the GPU timeline over the whole flight, both scorers, the agentic decomposition and both identity gates |
| `flight-1500/caps-1500.json` | the per-row read off the sealed trace: for each of the 1,500 rows its resolved cap, the policy's own answer, completion tokens, headroom and whether the cap bound |
| `flight-1500/flight-receipt.json` | the launcher's own stage receipt (preflight, preprocess, serve, run_phases, seal, score, stop) |
| `flight-1500/score.json` | the aggregate score file `core.scoring_batch` produced, copied byte for byte |
| `flight-1500/agentic-read.json` | the `analysis.e22_error_taxonomy` read on this cell's outputs alone, with its reading-path anchor |
