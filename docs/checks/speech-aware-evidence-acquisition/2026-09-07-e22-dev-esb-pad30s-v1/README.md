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

## `flight-1500/` — the cell itself

Attempt `attempt-20260907T093441Z-3a2278`, COMPLETED and FINALIZED on study commit `d56d616b`,
**1,500 of 1,500 contacts**, one attempt, none aborted, **no recovery re-registration used**,
`study_repo_dirt` empty. Config hash `fa2d6deb`, protocol hash `c7f6bd14`, split identity
`2c13bf01` — the three the zero-contact wire check had already computed for this cell, unchanged.
Manifest SHA-256 `31408b40…`, outputs `178ada5e…`, trace `8b522dcb…`, sealed scores `d41fb760…`.

### The falsifier, run before any score was read

**§4.1 HOLDS ON 1,500 OF 1,500 ROWS.** Measured `prompt_tokens` total **678,026** against the
predicted **678,026** — exactly the `49 × 1,500 + 604,526` the preregistration published before the
cell existed — with **zero** disagreeing rows. The predicted audio-token count is recomputed from
each clip's own `n_samples` through `analysis.e22_short_clip_encoding.llamacpp_audio_tokens`, and
the roster receipt's `audio_tokens` column agrees on every one of the 1,500 rows as well. The
sealed `cost` block's own `prompt_tokens_total` is the same 678,026. The audit's front-end model is
therefore the server's on this media too — and it holds on media **4.34× the comparator's audio
tokens**, at the length where the whisper convention would have applied had our path used it.

### What the cell measured, on its own 1,500 rows

**No pairing and no verdict below.** These are this arm's own numbers; the paired contrast against
the sealed comparator, its call-stratified CI90 and the three-clause rule of §4 belong to a later
document.

| | value |
|---|---:|
| corpus WER, Whisper `EnglishTextNormalizer` (paper-facing) | **9.3254 %** |
| corpus WER, frozen `saea-scoring-v1` normalizer | 14.6261 % |
| mean per-utterance WER (Whisper / `saea-scoring-v1`) | 15.3907 % / 19.8130 % |
| equal-call weighting (Whisper / `saea-scoring-v1`) | 9.4754 % / 14.7857 % |
| substitutions / deletions / insertions (Whisper) | 1,044 / 799 / 605 |
| reference words (Whisper / `saea-scoring-v1`) | 26,251 / 26,822 |
| insertion share of errors (Whisper) | 24.71 % |
| hypothesis-to-reference length ratio | 0.9926 |
| agentic error rate (`analysis.e22_error_taxonomy`, HIGH-impact reference-word mass) | **1.7752 %** (466 of 26,251 words over 319 spans) |
| boundary category mass (`segmentation-artifact` + `runaway-tail` + `runaway-head`) | **0.9295 WER points** (204 + 0 + 40 = 244 operations) |

The taxonomy's own alignment reproduces the paper-facing scorer exactly — 1,044 / 799 / 605 over
26,251 reference words, corpus WER 9.3254 either way, recorded as the `taxonomy_identity_gate`
block of `flight-1500/flight-read.json` — so the category split below is a decomposition of the
same number, not a second measurement of it.

**Per call, corpus WER under both normalizers** (natural mixture; the equal-call means are in the
table above):

| call | reference words | Whisper | `saea-scoring-v1` |
|---|---:|---:|---:|
| `4453225` | 2,662 | 10.1803 | 15.6503 |
| `4469088` | 1,946 | 10.1233 | 12.7692 |
| `4470684` | 2,581 | 5.1918 | 13.7369 |
| `4474506` | 2,993 | 7.5510 | 12.6188 |
| `4479944` | 2,773 | 16.3361 | 22.9769 |
| `4481952` | 2,166 | 8.2641 | 14.0045 |
| `4482383` | 3,015 | 7.8939 | 12.5417 |
| `4482613` | 2,386 | 17.0997 | 23.7515 |
| `4483937` | 2,567 | 6.8952 | 12.0460 |
| `4485192` | 3,162 | 5.2182 | 7.7611 |

**By utterance duration** — the slice the encoding audit predicts the effect concentrates in. The
buckets are the published segment's own duration, not the variant's, so the rows are the same rows
in every cell:

| bucket | utterances | reference words | corpus WER | of which `segmentation-artifact` | of which `model-behaviour` |
|---|---:|---:|---:|---:|---:|
| 0–1 s | 116 | 277 | 49.0975 | 2.8881 | 20.2166 |
| 1–2 s | 109 | 537 | 26.0708 | 2.7933 | 5.4004 |
| 2–4 s | 291 | 2,656 | 14.8343 | 2.1461 | 0.7154 |
| 4–8 s | 488 | 7,657 | 9.1942 | 0.9403 | 0.9273 |
| 8–16 s | 425 | 11,695 | 7.2424 | 0.3420 | 0.2993 |
| 16 s+ | 71 | 3,429 | 6.6200 | 0.3500 | 0.0583 |

**Category mass** (spans, error mass, WER points):

| category | spans | error mass | WER points |
|---|---:|---:|---:|
| `other` | 802 | 1,018 | 3.8779 |
| `acoustic-misrecognition` | 257 | 327 | 1.2457 |
| `named-entity` | 210 | 279 | 1.0628 |
| `reference-convention` | 206 | 238 | 0.9066 |
| `model-behaviour` | 63 | 212 | 0.8076 |
| `segmentation-artifact` | 156 | 204 | 0.7771 |
| `format-convention` | 98 | 113 | 0.4305 |
| `domain-term` | 37 | 57 | 0.2171 |

**Boundary containment.** 21 tail insertion spans carrying 33 words, of which 11 spans (13 words)
are 60 % or more contained in the *next* published utterance's reference; 132 head spans carrying
220 words, of which 63 spans (97 words) are 60 % or more contained in the *previous* one. The full
buckets are in `flight-1500/flight-read.json`.

### Serving and cost

1,500 contacts in **794.462 s** wall at **1.8881 contacts/s** and **3.8510 s** mean latency, slot
occupancy 0.909 on eight slots, 1,933.4 tokens/s — **0.2207 GPU-hours** against the 2.00 registered
ceiling, well under the 1.20 planned. Realized spend 1,500 of 1,600 registered calls and 45,002.880
of 46,000 registered speech-audio seconds; zero paid API. Monitor summary for the attempt's own
contact window: 71 samples over 781.048 s, **parked 0.0 s, active 781.048 s, parked fraction
0.000**, `requests_delta` 546 (a lower bound at the 10-second sampling interval, not the throughput
figure), mean power **89.236 W**, peak **94.38 W**, mean GPU utilization **85.96 %**.

Zero `cuda error`, zero `out of memory` and zero `GGML_ASSERT` lines in the session's server log,
which shows `process_mtmd ... encoding mtmd batch` across all eight slots throughout, so every row
paid a live mmproj encode and no feature cache was involved. Scored once over the complete sealed
manifest through `core.scoring_batch` with `verified = true`, one job, none failed,
`include_per_sample = true`, never sharded. The session was still up with eight idle slots
afterwards.

## Files

| file | what it is |
|---|---|
| `smoke-4/flight-receipt.json`, `flight-1500/flight-receipt.json` | the launcher's own receipts: every stage, its hash, the serve attach, the seal and the score |
| `smoke-4/falsifier.json`, `flight-1500/falsifier.json` | the §4.1 `prompt_tokens` check, recomputed row by row from the sealed trace |
| `smoke-4/score.json`, `flight-1500/score.json` | the `core.scoring_batch` result over the complete sealed manifest, `verified: true`, per-sample rows included |
| `flight-1500/flight-read.json` | this cell's own corpus, per-call, per-duration, category and boundary tables, plus the taxonomy identity gate — no pairing, no verdict |
