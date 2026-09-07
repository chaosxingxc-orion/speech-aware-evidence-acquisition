# Earnings-22 DEV cell (a), `SAEA-E22-DEV-ESB-Q8-V1` — flight receipts

Cell (a) of `docs/readiness/2026-09-06-e22-dev-usage-cells-v1-preregistration.md`: one factor, the
decoder quantization, on the 1,500-row `E22-DEV-ESB-1500-V1` subset of this study's own Earnings-22
DEV subset10. Exposure rows `SAEA-E22-DEV-ESB-Q8-SMOKE-V1` and `SAEA-E22-DEV-ESB-Q8-V1`, both
registered before the first contact at commit `b133f85b`.

**No verdict lives here.** The paired contrast against the sealed comparator, its CI90 and the
preregistered decision rule are a later document's; this directory carries what the flight measured
and nothing else.

## `smoke-4/` — the live half of precondition Q8-P1, and the four-row dry run

One server session carries both, because they are the same load: the Q8_0 decoder starts once at
`--n-cpu-moe 28` on the sealed `-c 40960 -np 8` geometry, free VRAM is read after load with **zero
completions behind it**, and only then do the four requests go out.

| read | value |
|---|---|
| free VRAM after load, zero completions, GPU utilisation still 0 % | **5,100 MiB** (19,038 MiB used) |
| the offline projection this measures | 5,083 MiB free / 19,054 MiB used |
| error in the projection | **+17 MiB free, −16 MiB used** |
| llama.cpp's own printed worst-case mmproj estimate at this geometry | **2,940.29 MiB** |
| the floor | 3,072 MiB — cleared by **2,028 MiB** |
| tightest reading of the whole session, with the 32.88 s live encode in flight | **5,052 MiB free** |
| what the live encode actually cost on the card | **48 MiB** |
| live `n_ctx` per slot through the server's own log | 5,120 on all eight slots |
| CUDA fault / out-of-memory | none |
| both ESB scorers on the sealed manifest | `verified: true` |

The offline receipt
(`docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-dev-usage-cells/q8-placement.json`)
filed itself as a PROJECTION and named the one quantity that did not carry over — the CUDA context
plus compute buffers, fitted at `-c 49152 -np 3` and reused at `-c 40960 -np 8`. It was right to
17 MiB. The A2T probe's own `N = 24` would have left about 2,635 MiB, below both the floor and
llama.cpp's printed 2,940.29 MiB estimate, so declining to copy it was not a formality.

**The encoder's worst case is an estimate, not a measurement, and the difference is large.**
llama.cpp reserves against 2,940.29 MiB; the four rows — including the 32.88 s longest utterance in
the whole 1,500 — moved the card by 48 MiB. The floor stays where it is: it is the right thing to
size against, and this session does not license lowering it.

**No feature cache.** The server argv carries no cache flag, `server_env` declares only
`GGML_CUDA_DISABLE_GRAPHS=1`, and no `LLAMA_MTMD_FEAT_CACHE_DIR` exists in the launching shell or in
any profile. Every one of the four rows encoded live, exactly as the sealed comparator did.

**Latency, reported with its caveat.** Summed per-call latency 71.556 s over four calls, a 17.889 s
mean against the sealed Q4_K_M comparator's 1.927 s — a ratio of **9.28x** against the 7.85x the
flight budget assumed. It is an upper bound rather than a like-for-like figure: the four dry-run
rows average 12.93 s of audio against the roster's 6.63 s, and only four of the eight slots were
ever occupied. Model load was 10.03 s.

The dry run's own WER numbers are on four rows and enter no verdict.

## Files

| path | what it is |
|---|---|
| `smoke-4/q8-placement-live.json` | the live half of Q8-P1: the full GPU timeline the session recorded, llama.cpp's printed estimate, the projection check and the four go/no-go reads |
| `smoke-4/flight-receipt.json` | the launcher's own stage receipt for the dry run (preflight, preprocess, serve, run_phases, seal, score, stop) |
| `smoke-4/score.json` | the sealed score file `core.scoring_batch` produced, copied byte for byte |

## `flight-1500/` — the cell, flown

One attempt, 1,500 of 1,500 contacts, COMPLETED and FINALIZED on study commit `0ec7ef82` with
`study_repo_dirt` empty, attempt `attempt-20260907T030402Z-60e8e1`. No recovery re-registration was
used and none was needed. Manifest SHA-256 `f3475ffb…`, outputs SHA-256 `f9253ba5…`, aggregate score
SHA-256 `eec18bf7…`.

**Raw numbers. Nothing here is a contrast.** The paired read against the sealed comparator, its
call-stratified CI90 and the preregistered decision rule belong to a later document; this one
records what the cell measured.

| | value |
|---|---|
| corpus WER, Whisper `EnglishTextNormalizer` (paper-facing) | **16.9708 %** |
| S / D / I over 26,251 reference words | 1,117 / 587 / 2,751 |
| mean of per-utterance WER, same normalizer | 29.8648 % |
| corpus WER, frozen `saea-scoring-v1` | 22.6009 % over 26,822 reference words |
| agentic error rate (`analysis.e22_error_taxonomy`, HIGH reference-word mass) | **1.8552 %** |
| the same rate with `segmentation-artifact` no longer neutral (strict) | 2.1485 % |
| boundary category mass | 2,128 error operations = **8.1064 WER points** (segmentation 914 + runaway tail 1,137 + runaway head 77) |
| hypothesis-to-reference length ratio | 1.0824 |
| insertion share of all errors | 61.75 % |

Scored **once**, over the complete manifest, through `core.scoring_batch`, `verified: true`, never
sharded, with the manifest's own three scorers. A second pass over the *same* complete manifest with
`include_per_sample=True` produced 1,500 per-row entries for each ESB scorer; those rows live under
`SPEECHRL_DATA_DIR` and never enter this repository, so the receipt pins them by digest instead.

**The taxonomy's own identity gate passes.** `analysis.e22_error_taxonomy`'s aligner reproduces the
sealed scorer's S/D/I and corpus WER on these outputs exactly — 1,117 / 587 / 2,751 and 16.9708 % —
which is the condition that module imposes on itself before any figure it produces may be read. The
same call on the sealed comparator's rows restricted to these 1,500 ids reproduces the
preregistration's own published subset figures (17.4012 % corpus WER, 1.9161 % agentic) to the
digit. That is a method check on the reading path, not a comparison.

### Cost, and the ratio the budget guessed at

| | value |
|---|---|
| generation wall | 3,274.0 s (03:04:59Z to 03:59:50Z) |
| GPU-hours, llama-server residency | **0.919 h** against 2.0 planned and 3.0 registered |
| contacts / s at eight occupied slots | 0.458 |
| mean per-call latency | 16.517 s; summed 24,775.4 s |
| realtime factor | 3.04x |
| model load | 10.12 s |
| prompt / completion tokens per call | 141.9 / 24.6 |
| **measured Q8_0-to-Q4_K_M latency ratio** | **8.57x** against the 7.85x the budget assumed |
| the same ratio on throughput | 8.17x (0.458 contacts/s against the comparator's 3.744) |

The dry run's 9.28x was flagged as an upper bound because its four rows averaged twice the roster's
audio and only half the slots were ever busy. On the whole roster at eight occupied slots the honest
figure is **8.57x** — above the 7.85x the plan used, which is why the plan carried room. The cell
still finished in under half its planned GPU-hours, because the plan's arithmetic (about 15.1 s per
call, roughly 2,830 s of dispatch) was close and the two named additions did not bite.

### The placement, over 3,274 seconds of real work

`--n-cpu-moe 28` never came near the floor. Over 603 samples spanning the whole flight the card held
**5,048 MiB free at every single reading** — 1,976 MiB above the 3,072 MiB floor and 2,108 MiB above
llama.cpp's own printed 2,940.29 MiB worst-case mmproj estimate — with 19,090 MiB used at the peak.
Zero CUDA faults and zero out-of-memory lines in the server log; peak power 82.45 W under a 100.00 W
enforced limit; the card back to 0 MiB after the runner's own `stop_serving`.

Host memory is where the cost actually sits, and it is worth recording: server RSS climbed to
**27,950 MiB** as the 28 CPU-resident expert layers faulted in, against the A2T ladder's 18,533 MiB
at the same `N`, with host available never below **45,108 MiB** of 54,633. The difference is the
resident bf16 mmproj and this geometry's own buffers, and it means the placement's host-RAM headroom
is smaller than the A2T figure suggested — still ample, but not by the margin that number implied.

### Files

| path | what it is |
|---|---|
| `flight-1500/flight-read.json` | the assembled read: identity and hashes, budget, throughput, the placement timeline over the whole flight, both scorers, and the agentic decomposition with its category table |
| `flight-1500/flight-receipt.json` | the launcher's own stage receipt (preflight, preprocess, serve, run_phases, seal, score, stop) |
| `flight-1500/score.json` | the aggregate score file `core.scoring_batch` produced, copied byte for byte |
| `flight-1500/agentic-read.json` | the `analysis.e22_error_taxonomy` read on this cell's outputs alone |
