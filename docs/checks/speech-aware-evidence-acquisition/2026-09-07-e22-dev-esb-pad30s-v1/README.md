# Earnings-22 encoding probe cell 3, `SAEA-E22-DEV-ESB-PAD30S-V1` — flight receipts

Cell 3 (`pad-30s`) of
`docs/readiness/2026-09-07-e22-dev-encoding-probes-v1-preregistration.md`: **one factor, the
media** — digital silence appended to each of the 1,500 drawn published ESB segments of this
study's own Earnings-22 DEV subset10 until the clip is exactly 30.0 s long, nothing removed, **no
clip truncated** and nothing re-decoded. Everything else is the sealed comparator's, byte for byte:
instruction, prompt shape, decoding params, build, decoder and mmproj by sha256, raw-audio mmproj
path with no packet and no feature cache, geometry, harness and entry point.

**What this cell separates.** The 2026-09-07 encoding audit established that our serving path
applies **no** fixed 30-second window — the whisper preprocessor's stage-1 pad is not on the
`mtmd_audio_preprocessor_qwen3a` branch Qwen3-Omni selects — so this cell supplies *at the wire*
what the runtime does not supply internally, and pushes the encoder's own unmasked `0.0` pad block
about 30 s away from the last word (its share of a clip's tokens falls from 12.00 % to 3.2 %).

**What this cell cannot do, stated in the preregistration before any number existed.** Padding to
30.0 s sets the residue `(n_samples // 160) % 100` to zero, so the last mel block still carries 99
frames of the literal float `0.0` and the zero-pad block **keeps its size**. This cell moves the
constant; it does not remove it. The `frame-exact` probe of §5 is the one that would; it is not
built and not authorized.

**It is the expensive cell by design**: 45,002.880 s of audio and 604,526 audio tokens, **4.34×**
the comparator's 139,282, which is why it carries its own much larger budget — and the single clip
already past 30.0 s (`4482383-188`, 32.880000 s) is byte-identical to its `dev-v1` twin.

Exposure rows `SAEA-E22-DEV-ESB-PAD30S-SMOKE-V1` and `SAEA-E22-DEV-ESB-PAD30S-V1`, both registered
before the first contact at commit `0a151a5e`.

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
duration over the drawn 1,500), in this variant's encoding — which is why three of them are now
exactly 30.000000 s and the fourth is the untouched 32.880000 s clip. Attempt
`attempt-20260907T093012Z-5b2440`, COMPLETED and FINALIZED on study commit `0a151a5e`, 4 of 4
contacts, one attempt, none aborted, no recovery re-registration used.

**The binding read is §4.1's built-in falsifier**: every request's `prompt_tokens` must equal
49 + `analysis.e22_short_clip_encoding.llamacpp_audio_tokens(n_samples)` for that row's variant
media. The predicted audio-token count is recomputed from each clip's own `n_samples` rather than
read from the roster receipt's column, and the two agree on every row as well.

| sample | seconds | `n_samples` | predicted audio tokens | expected `prompt_tokens` | measured `prompt_tokens` |
|---|---:|---:|---:|---:|---:|
| `4469088-654@p30` | 30.000000 | 480,000 | 403 | 452 | **452** |
| `4479944-334@p30` | 30.000000 | 480,000 | 403 | 452 | **452** |
| `4482383-188@p30` | 32.880000 | 526,080 | 429 | 478 | **478** |
| `4482613-439@p30` | 30.000000 | 480,000 | 403 | 452 | **452** |

**The falsifier HOLDS on 4 of 4 rows**, measured total 1,834 against the predicted 1,834, zero
disagreements, and the sealed `cost` block's own `prompt_tokens_total` is the same 1,834.

Everything else the smoke exists to check is affirmative. This is the variant whose **every** row is
a long encode, so the dry run is where a per-request encode surprise had to surface: the worst
encode (32.880000 s, 429 audio tokens, five encoder windows) and the three padded rows (403 audio
tokens, four encoder windows each) all completed live with **zero** `cuda error`, `out of memory`
and `GGML_ASSERT` lines in the session's server log, and the log shows `process_mtmd ... encoding
mtmd batch` for all four rows on four different slots (0, 1, 2 and 3) in exactly the
4 / 4 / 5 / 4 encoder-window counts the roster receipt predicts for these four clips, so every row
paid a **live** mmproj encode and no feature cache was involved. Both ESB scorers plus `cost`
returned on the sealed manifest through `core.scoring_batch` with `verified = true`, one job, none
failed, `include_per_sample = true`. Four contacts in 3.376 s wall at 2.5056 s mean latency; the
session was still up with eight idle slots afterwards. The monitor window was shorter than the
10-second sampling interval and carries no sample, which is why the flight row and not this one is
the GPU accounting.

The smoke's own WER numbers are on four rows and enter no verdict.

## Files

| file | what it is |
|---|---|
| `smoke-4/flight-receipt.json` | the launcher's own receipt: every stage, its hash, the serve attach, the seal and the score |
| `smoke-4/falsifier.json` | the §4.1 `prompt_tokens` check, recomputed row by row from the sealed trace |
| `smoke-4/score.json` | the `core.scoring_batch` result over the complete sealed manifest, `verified: true`, per-sample rows included |
