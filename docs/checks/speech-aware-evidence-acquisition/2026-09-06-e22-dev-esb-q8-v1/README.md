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
