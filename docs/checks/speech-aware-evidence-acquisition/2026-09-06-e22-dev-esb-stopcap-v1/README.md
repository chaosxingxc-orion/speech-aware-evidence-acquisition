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
