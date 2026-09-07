# Earnings-22 encoding probe cell 2, `SAEA-E22-DEV-ESB-TAIL2S-V1` — flight receipts

Cell 2 (`tail-silence-2s`) of
`docs/readiness/2026-09-07-e22-dev-encoding-probes-v1-preregistration.md`: **one factor, the
media** — exactly 2.0 s (32,000 zero samples) of digital silence appended to each of the 1,500
drawn published ESB segments of this study's own Earnings-22 DEV subset10, nothing removed and
nothing re-decoded, so the model's last word is followed by what a stop actually looks like rather
than by the encoder's own unmasked `0.0` constant. Everything else is the sealed comparator's, byte
for byte: instruction, prompt shape, decoding params, build, decoder and mmproj by sha256,
raw-audio mmproj path with no packet and no feature cache, geometry, harness and entry point.

**What this cell cannot do, stated in the preregistration before any number existed.** Appending
200 whole mel frames leaves the residue `(n_samples // 160) % 100` unchanged, so the zero-pad block
keeps its size — the same 9,740 tokens over the population — and only stops abutting the speech.
Its share of a clip's tokens falls from 12.00 % to 6.99 % and its position moves 2.0 s away. The
`frame-exact` probe of §5 is the one that would remove the constant; it is not built and not
authorized.

Exposure rows `SAEA-E22-DEV-ESB-TAIL2S-SMOKE-V1` and `SAEA-E22-DEV-ESB-TAIL2S-V1`, both registered
before the first contact at commit `052e47d4`.

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
duration over the drawn 1,500), each two seconds longer than its `dev-v1` twin. Attempt
`attempt-20260907T085957Z-35be6e`, COMPLETED and FINALIZED on study commit `052e47d4`, 4 of 4
contacts, one attempt, none aborted, no recovery re-registration used.

**The binding read is §4.1's built-in falsifier**: every request's `prompt_tokens` must equal
49 + `analysis.e22_short_clip_encoding.llamacpp_audio_tokens(n_samples)` for that row's variant
media. The predicted audio-token count is recomputed from each clip's own `n_samples` rather than
read from the roster receipt's column, and the two agree on every row as well.

| sample | seconds | `n_samples` | predicted audio tokens | expected `prompt_tokens` | measured `prompt_tokens` | completion tokens |
|---|---:|---:|---:|---:|---:|---:|
| `4469088-654@ts2` | 2.219938 | 35,519 | 39 | 88 | **88** | 3 |
| `4482613-439@ts2` | 7.580313 | 121,285 | 104 | 153 | **153** | 16 |
| `4479944-334@ts2` | 15.020250 | 240,324 | 208 | 257 | **257** | 49 |
| `4482383-188@ts2` | 34.880000 | 558,080 | 455 | 504 | **504** | 97 |

**The falsifier HOLDS on 4 of 4 rows**, measured total 1,002 against the predicted 1,002, zero
disagreements, and the sealed `cost` block's own `prompt_tokens_total` is the same 1,002.

Everything else the smoke exists to check is affirmative. This variant's worst encode — 34.880000 s
at 455 audio tokens, the **longest clip and the largest single request of the three variants**, and
the one that sits closest to the 5,120-token slot — completed live with **zero** `cuda error`,
`out of memory` and `GGML_ASSERT` lines in the session's server log, and the log shows
`process_mtmd ... encoding mtmd batch` for all four rows on four different slots, in exactly the
1 / 1 / 2 / 5 encoder-window counts the roster receipt predicts for these four clips, so every row
paid a **live** mmproj encode and no feature cache was involved. Both ESB scorers plus `cost`
returned on the sealed manifest through `core.scoring_batch` with `verified = true`, one job, none
failed, `include_per_sample = true`. Four contacts in 2.476 s wall at 1.6714 s mean latency; the
session was still up with eight idle slots afterwards.

The smoke's own WER numbers are on four rows and enter no verdict.

## Files

| file | what it is |
|---|---|
| `smoke-4/flight-receipt.json` | the launcher's own receipt: every stage, its hash, the serve attach, the seal and the score |
| `smoke-4/falsifier.json` | the §4.1 `prompt_tokens` check, recomputed row by row from the sealed trace |
| `smoke-4/score.json` | the `core.scoring_batch` result over the complete sealed manifest, `verified: true`, per-sample rows included |
