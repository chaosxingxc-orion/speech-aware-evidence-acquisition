# Earnings-22 encoding probe cell 1, `SAEA-E22-DEV-ESB-BX-V1` — flight receipts

Cell 1 (`boundary-exact`) of
`docs/readiness/2026-09-07-e22-dev-encoding-probes-v1-preregistration.md`: **one factor, the
media** — the midpoint-of-overlap re-cut of the 1,500 drawn published ESB segments of this study's
own Earnings-22 DEV subset10, so no adjacent published pair overlaps and the model is never handed
the onset of the next published sentence. Everything else is the sealed comparator's, byte for
byte: instruction, prompt shape, decoding params, build, decoder and mmproj by sha256, raw-audio
mmproj path with no packet and no feature cache, geometry, harness and entry point.

Exposure rows `SAEA-E22-DEV-ESB-BX-SMOKE-V1` and `SAEA-E22-DEV-ESB-BX-V1`, both registered before
the first contact at commit `d9ee9b5b`.

**Always-on serving.** Neither run started or stopped a server. Both attached to the coordinator's
resident session `e22-dev-np8-c40960-20260907` (fragment
`q4km-e22-dev-esb-mmproj-gpu-04ccc72a-np8-c40960`, `-c 40960 -np 8`, eight 5,120-token slots, port
8080), and `session_reused` is `true` with `session_source` `attached-serving-session` in both serve
receipts; `stop_serving` is the documented no-op.

**No verdict lives here.** The paired contrast against the sealed `SAEA-E22-DEV-ESB-PROMPT-A-V1`
(`attempt-20260905T073641Z-f977d1`), its call-stratified CI90, the three-clause decision rule of
§4 and the boundary-block reading are a later document's; this directory carries what the cell
measured and nothing else.

## `smoke-4/` — the four-row dry run, and the falsifier it exists to test

The four rows are named by the registered fragment itself, never by a command line: the same four
published segments the 2026-09-06 dev1500 smoke selected (longest, shortest, median and p90 by
duration over the drawn 1,500), in this variant's encoding. Attempt
`attempt-20260907T082839Z-88a841`, COMPLETED and FINALIZED on study commit `d9ee9b5b`, 4 of 4
contacts, one attempt, none aborted, no recovery re-registration used.

**The binding read is §4.1's built-in falsifier**: every request's `prompt_tokens` must equal
49 + `analysis.e22_short_clip_encoding.llamacpp_audio_tokens(n_samples)` for that row's variant
media. The predicted audio-token count is recomputed from each clip's own `n_samples` rather than
read from the roster receipt's column, and the two agree on every row as well.

| sample | seconds | `n_samples` | predicted audio tokens | expected `prompt_tokens` | measured `prompt_tokens` | completion tokens |
|---|---:|---:|---:|---:|---:|---:|
| `4469088-654@bx1` | 0.139875 | 2,238 | 13 | 62 | **62** | 5 |
| `4482613-439@bx1` | 5.430063 | 86,881 | 78 | 127 | **127** | 18 |
| `4479944-334@bx1` | 12.890187 | 206,243 | 169 | 218 | **218** | 49 |
| `4482383-188@bx1` | 32.800063 | 524,801 | 429 | 478 | **478** | 100 |

**The falsifier HOLDS on 4 of 4 rows**, measured total 885 against the predicted 885, zero
disagreements, and the sealed `cost` block's own `prompt_tokens_total` is the same 885.

Everything else the smoke exists to check is affirmative. This variant's worst encode
(32.800063 s, 429 audio tokens, five encoder windows) completed live with **zero** `cuda error`,
`out of memory` and `GGML_ASSERT` lines in the session's server log, and the log shows
`process_mtmd ... encoding mtmd batch` for all four rows on four different slots, so every row paid
a **live** mmproj encode and no feature cache was involved. Both ESB scorers plus `cost` returned
on the sealed manifest through `core.scoring_batch` with `verified = true`, one job, none failed,
`include_per_sample = true`. Four contacts in 3.453 s wall at 2.6195 s mean latency.

The smoke's own WER numbers are on four rows and enter no verdict.

## Files

| file | what it is |
|---|---|
| `smoke-4/flight-receipt.json` | the launcher's own receipt: every stage, its hash, the serve attach, the seal and the score |
| `smoke-4/falsifier.json` | the §4.1 `prompt_tokens` check, recomputed row by row from the sealed trace |
| `smoke-4/score.json` | the `core.scoring_batch` result over the complete sealed manifest, `verified: true`, per-sample rows included |
