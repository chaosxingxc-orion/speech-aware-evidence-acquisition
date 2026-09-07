# `SAEA-E22-ESB-SHORTFORM-TAIL2S-TEST-V1` — the one-time re-read of the six ESB test calls

The cell of `docs/readiness/2026-09-07-e22-esb-shortform-tail2s-test-v1-preregistration.md`: the
**second read** of the six Earnings-22 ESB test calls, on the owner GO of 2026-09-07, with **one
factor — the media**. Exactly 2.0 s (32,000 zero samples) of digital silence appended to each of the
2,735 published test utterances, nothing removed and nothing re-decoded. Everything else is
byte-identical to the sealed comparator `SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1`
(`attempt-20260905T044432Z-8f23ee`, **NOT ALIGNED at corpus Whisper-normalized WER 15.937**):
instruction, prompt shape, decoding params, build, decoder and mmproj by sha256, raw-audio mmproj
path with no packet and no feature cache, `-c 32768 -np 8` geometry, reference layer, scorers,
harness and entry point.

**What this cell cannot do, stated in the preregistration before any number existed.** Appending 200
whole mel frames leaves the residue `(n_samples // 160) % 100` unchanged, so the zero-pad block keeps
its size — the same 136,533 pad frames and the same 17,695 masked-away tokens are still sent — and
its pooled share falls only from 6.52 % to 5.17 % because the request grew. The tail moves the
constant 2.0 s away from the last word; it does not remove it.

**The protocol difference this number always carries (`D-TS2-3`).** The published systems did not
append silence. Every request here carries 2.0 s of digital silence after the published span, and no
statement of this number may omit that.

Exposure rows `SAEA-E22-ESB-SHORTFORM-TAIL2S-TEST-SMOKE-V1` and
`SAEA-E22-ESB-SHORTFORM-TAIL2S-TEST-V1`, both registered before the first contact at commit
`fde1f08a`, both carrying the owner GO in full.

**Always-on serving.** Neither run started or stopped a server. Both attached to the coordinator's
resident session `e22-test-np8-c32768-20260907` (fragment `q4km-e22-esb-mmproj-gpu-04ccc72a-np8`,
`-c 32768 -np 8`, eight 4,096-token slots, port 8080) — **the sealed test flight's own geometry, not
the `-c 40960` dev session** — with `session_reused: true`, `session_source:
attached-serving-session` and `startup_seconds: 0.0`; `stop_serving` is the documented no-op.

## `smoke-4/` — the four-row dry run, and the three reads it exists to make

The four rows are named by the registered fragment itself, never by a command line: the same four
published segments the sealed 2026-09-05 test smoke selected (shortest, longest, median and p90 by
published duration over the 2,735), each exactly two seconds longer than its v1 twin. Attempt
`attempt-20260907T105734Z-72a613`, COMPLETED and FINALIZED on study commit `fde1f08a`, 4 of 4
contacts, one attempt, none aborted, no recovery re-registration used. Config hash `ab212438`,
protocol hash `cb8f4e5e`, split identity `f47de393` — the three the zero-contact wire check had
already computed for this cell, unchanged.

**Read 1, the binding one: §4.2's built-in falsifier HOLDS on 4 of 4 rows.** Every request's
`prompt_tokens` equals 49 + `analysis.e22_short_clip_encoding.llamacpp_audio_tokens(n_samples)` for
that row's variant media, with the predicted audio-token count recomputed from each clip's own
`n_samples` rather than read from the roster column — and the roster column agrees on every row as
well.

| sample | seconds (`@ts2`) | `n_samples` | predicted audio tokens | expected `prompt_tokens` | measured `prompt_tokens` | completion tokens |
|---|---:|---:|---:|---:|---:|---:|
| `4479741-224@ts2` | 2.219937 | 35,519 | 39 | 88 | **88** | 3 |
| `4485244-409@ts2` | 8.120125 | 129,922 | 117 | 166 | **166** | 32 |
| `4485244-115@ts2` | 16.060000 | 256,960 | 221 | 270 | **270** | 72 |
| `4483338-281@ts2` | 38.360125 | 613,762 | 507 | 556 | **556** | 97 |

Measured total **1,080** against the predicted **1,080** — exactly the 88 / 556 / 270 / 166 the
experiment fragment published before the cell existed — zero disagreements, and the sealed `cost`
block's own `prompt_tokens_total` is the same 1,080.

**Read 2: this variant's worst encode completed live.** `4483338-281@ts2`, 38.360125 s at 507 audio
tokens — the largest single request the cell will send, against a 4,096-token slot — ran on slot 1 as
task 210 and the session's server log shows `process_mtmd … encoding mtmd batch` at idx 43, 147, 251,
355 and 459: **exactly the five encoder windows the roster receipt predicts** for that clip. Zero
`cuda error`, zero `out of memory` and zero `GGML_ASSERT` lines in the log, and all four rows encoded
on four different slots (0, 1, 2, 3), so every row paid a **live** mmproj encode and no feature cache
was involved.

**Read 3: both ESB scorers returned per-sample rows.** `asr-wer-esb-whisper`, `asr-wer-esb` and
`cost` all returned on the sealed manifest through `core.scoring_batch` with `verified = true`, one
job, none failed, `include_per_sample = true`, never sharded.

Four contacts in 3.632 s wall at 2.446 s mean latency on eight slots; sealed cost 4 calls,
64.7601875 audio seconds, 1,080 prompt tokens, 204 completion tokens. The attempt's contact window
was shorter than the monitor's 10-second sampling interval and carries no sample, which is why the
flight row and not this one is the GPU accounting. The session was still up with eight idle slots
afterwards.

**The smoke's own WER numbers are on four rows and enter no verdict.**

All three reads are affirmative, so the flight's own go/no-go clause is satisfied.

## `flight-2735/` — the cell itself

Attempt `attempt-20260907T110507Z-cafdc7`, COMPLETED and FINALIZED on study commit `532cbb43`,
**2,735 of 2,735 contacts**, one attempt, none aborted, **no recovery re-registration used**,
`study_repo_dirt` empty. Config hash `f84f2078`, protocol hash `f3442e1b`, split identity `ecd9ab76`
— the three the zero-contact wire check had already computed for this cell, unchanged. Manifest
SHA-256 `2b4025e8…`, outputs `5713b791…`, trace `6893fe85…`, sealed scores `a8bc51f2…`.

### The falsifier, run before any score was read

**§4.2 HOLDS ON 2,735 OF 2,735 ROWS.** Measured `prompt_tokens` total **476,578** against the
predicted **476,578** — exactly the `49 × 2,735 + 342,563` the preregistration published before the
cell existed — with **zero** disagreeing rows. The predicted audio-token count is recomputed from
each clip's own `n_samples` through `analysis.e22_short_clip_encoding.llamacpp_audio_tokens`, and the
roster receipt's `audio_tokens` column agrees on every row as well. The sealed `cost` block's own
`prompt_tokens_total` is the same 476,578.

### What the cell measured

**The verdict lives in `docs/readiness/2026-09-07-e22-esb-shortform-tail2s-test-v1-verdict.md`**, with
the band decision, the deviation label, the paired contrast, the §4.3 slices and the §5 prediction
scored. What follows is the headline only.

| | sealed arm | **cell** |
|---|---:|---:|
| corpus WER, Whisper normalizer (paper-facing) | 15.9365 % | **9.2377 %** |
| corpus WER, frozen `saea-scoring-v1` normalizer | 20.8960 % | 14.3053 % |
| mean per-utterance WER (Whisper) | 28.1291 % | 13.9396 % |
| substitutions / deletions / insertions | 2,236 / 948 / 4,612 | 2,019 / 1,252 / 1,248 |
| insertion share of errors | 59.16 % | 27.62 % |
| hypothesis-to-reference length ratio | 1.0749 | 0.9999 |
| agentic error rate | 1.7641 % | 1.5945 % |
| boundary category mass | 7.1465 WER points | 1.0916 WER points |

Paired against the sealed arm on the same 2,735 published segments, signed cell − sealed: corpus WER
**−6.6988** points, CI90 [−7.0373, −6.3753] stratified by call; 1,385 rows improved, 155 worsened,
1,195 tied, sign test p ≈ 4.65e-247. **Band test PASS, strict floor PASS — ALIGNED under the
silence-tail convention**, with deviation `D-TS2-3` (the published systems did not append silence)
carried on every statement of the number.

The taxonomy's own alignment reproduces the paper-facing scorer exactly on both arms, so the category
split is a decomposition of those numbers rather than a second measurement of them, and the sealed
arm reproduced all seven of its own 2026-09-04 identity anchors before any contrast was computed.

### Serving and cost

2,735 contacts in **799.267 s** wall at **3.4219 contacts/s** and **2.109 s** mean latency, slot
occupancy 0.9021 on eight slots — **0.2220 GPU-hours** against the 1.00 registered ceiling. Realized
spend 2,735 of 2,800 registered calls and 24,964.608 of 25,500 registered speech-audio seconds; zero
paid API. Monitor summary for the attempt's own contact window: 73 samples over 785.894 s, **parked
0.0 s, active 785.894 s, parked fraction 0.000**, `requests_delta` 576 (a lower bound at the
10-second sampling interval), mean power **87.265 W**, peak **91.3 W**, mean GPU utilization
**82.89 %**.

Zero `cuda error`, zero `out of memory` and zero `GGML_ASSERT` lines in the session's server log,
which shows `process_mtmd … encoding mtmd batch` throughout, so every row paid a live mmproj encode
and no feature cache was involved. Scored once over the complete sealed manifest through
`core.scoring_batch` with `verified = true`, one job, none failed, `include_per_sample = true`, never
sharded. The session was still up with eight idle slots afterwards.

## Files

| file | what it is |
|---|---|
| `smoke-4/flight-receipt.json`, `flight-2735/flight-receipt.json` | the launcher's own receipts: every stage, its hash, the serve attach, the seal and the score |
| `smoke-4/falsifier.json`, `flight-2735/falsifier.json` | the §4.2 `prompt_tokens` check, recomputed row by row from the sealed trace |
| `smoke-4/score.json`, `flight-2735/score.json` | the `core.scoring_batch` result over the complete sealed manifest, `verified: true`, per-sample rows included |
| `flight-2735/flight-read.json` | this read's own tables: corpus, per call, per duration on the published span, category and boundary masses, the agentic rate, the paired contrast and the decision — for both arms |
