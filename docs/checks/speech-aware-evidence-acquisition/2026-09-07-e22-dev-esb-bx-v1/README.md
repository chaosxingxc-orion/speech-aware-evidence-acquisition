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

## `flight-1500/` — the cell itself

Attempt `attempt-20260907T083612Z-20c7c4`, COMPLETED and FINALIZED on study commit `47a96b84`,
**1,500 of 1,500 contacts**, one attempt, none aborted, **no recovery re-registration used**,
`study_repo_dirt` empty. Config hash `ffe61409`, protocol hash `dd0be6a7`, split identity
`87d0cc65` — the three the zero-contact wire check had already computed for this cell, unchanged.
Manifest SHA-256 `0aafd526…`, outputs `d0010c57…`, trace `531af72a…`, sealed scores `b6a29cf4…`.

### The falsifier, run before any score was read

**§4.1 HOLDS ON 1,500 OF 1,500 ROWS.** Measured `prompt_tokens` total **210,663** against the
predicted **210,663** — exactly the `49 × 1,500 + 137,163` the preregistration published before the
cell existed — with **zero** disagreeing rows. The predicted audio-token count is recomputed from
each clip's own `n_samples` through `analysis.e22_short_clip_encoding.llamacpp_audio_tokens`, and
the roster receipt's `audio_tokens` column agrees on every one of the 1,500 rows as well. The
sealed `cost` block's own `prompt_tokens_total` is the same 210,663. The audit's front-end model is
therefore the server's, on this media as on the sealed comparator's.

### What the cell measured, on its own 1,500 rows

**No pairing and no verdict below.** These are this arm's own numbers; the paired contrast against
the sealed comparator, its call-stratified CI90 and the three-clause rule of §4 belong to a later
document.

| | value |
|---|---:|
| corpus WER, Whisper `EnglishTextNormalizer` (paper-facing) | **14.3537 %** |
| corpus WER, frozen `saea-scoring-v1` normalizer | 19.6853 % |
| mean per-utterance WER (Whisper / `saea-scoring-v1`) | 25.1707 % / 29.4574 % |
| equal-call weighting (Whisper / `saea-scoring-v1`) | 14.6022 % / 19.9112 % |
| substitutions / deletions / insertions (Whisper) | 1,141 / 633 / 1,994 |
| reference words (Whisper / `saea-scoring-v1`) | 26,251 / 26,822 |
| insertion share of errors (Whisper) | 52.92 % |
| hypothesis-to-reference length ratio | 1.0518 |
| agentic error rate (`analysis.e22_error_taxonomy`, HIGH-impact reference-word mass) | **1.8971 %** (498 of 26,251 words over 347 spans) |
| boundary category mass (`segmentation-artifact` + `runaway-tail` + `runaway-head`) | **5.4969 WER points** (583 + 788 + 72 = 1,443 operations) |

The taxonomy's own alignment reproduces the paper-facing scorer exactly — 1,141 / 633 / 1,994 over
26,251 reference words, corpus WER 14.3537 either way — so the category split below is a
decomposition of the same number, not a second measurement of it.

**Per call, corpus WER under both normalizers** (natural mixture; the equal-call means are in the
table above):

| call | reference words | Whisper | `saea-scoring-v1` |
|---|---:|---:|---:|
| `4453225` | 2,662 | 16.2284 | 21.1609 |
| `4469088` | 1,946 | 15.4162 | 18.5779 |
| `4470684` | 2,581 | 11.2360 | 19.4998 |
| `4474506` | 2,993 | 12.2954 | 17.6991 |
| `4479944` | 2,773 | 21.3127 | 27.5289 |
| `4481952` | 2,166 | 13.5734 | 18.9262 |
| `4482383` | 3,015 | 9.1874 | 14.0427 |
| `4482613` | 2,386 | 22.5063 | 29.2326 |
| `4483937` | 2,567 | 14.8422 | 20.0519 |
| `4485192` | 3,162 | 9.4244 | 12.3922 |

**By utterance duration** — the slice the encoding audit predicts the effect concentrates in:

| bucket | utterances | reference words | corpus WER | of which `segmentation-artifact` | of which `model-behaviour` |
|---|---:|---:|---:|---:|---:|
| 0–1 s | 116 | 277 | 70.7581 | 13.3574 | 27.7978 |
| 1–2 s | 109 | 537 | 34.4507 | 5.4004 | 9.4972 |
| 2–4 s | 291 | 2,656 | 23.0045 | 4.7063 | 4.5934 |
| 4–8 s | 488 | 7,657 | 15.4238 | 2.4814 | 4.9105 |
| 8–16 s | 425 | 11,695 | 11.0902 | 1.4707 | 2.9072 |
| 16 s+ | 71 | 3,429 | 8.6906 | 0.8749 | 1.4290 |

**Category mass** (spans, error mass, WER points):

| category | spans | error mass | WER points |
|---|---:|---:|---:|
| `other` | 857 | 1,144 | 4.3579 |
| `model-behaviour` | 255 | 1,015 | 3.8665 |
| `segmentation-artifact` | 384 | 583 | 2.2209 |
| `acoustic-misrecognition` | 254 | 334 | 1.2723 |
| `named-entity` | 220 | 301 | 1.1466 |
| `reference-convention` | 194 | 230 | 0.8762 |
| `format-convention` | 88 | 103 | 0.3924 |
| `domain-term` | 42 | 58 | 0.2209 |

**Boundary containment.** 454 tail insertion spans carrying 1,234 words, of which 89 spans (124
words) are 60 % or more contained in the *next* published utterance's reference; 130 head spans
carrying 233 words, of which 62 spans (87 words) are 60 % or more contained in the *previous*
one. The full buckets are in `flight-1500/flight-read.json`.

### Serving and cost

1,500 contacts in **402.643 s** wall at **3.7254 contacts/s** and **1.9373 s** mean latency, slot
occupancy 0.902 on eight slots — **0.1118 GPU-hours** against the 0.40 registered ceiling. Realized
spend 1,500 of 1,600 registered calls and 9,783.571187 of 10,200 registered speech-audio seconds;
zero paid API. Monitor summary for the attempt's own contact window: 37 samples over 392.668 s,
**parked 0.0 s, active 392.668 s, parked fraction 0.000**, `requests_delta` 288 (a lower bound at
the 10-second sampling interval, not the throughput figure), mean power **86.578 W**, peak
**89.91 W**, mean GPU utilization **83.05 %**.

Zero `cuda error`, zero `out of memory` and zero `GGML_ASSERT` lines in the session's server log,
which shows `process_mtmd ... encoding mtmd batch` throughout, so every row paid a live mmproj
encode and no feature cache was involved. Both ESB scorers plus `cost` returned on the complete
sealed manifest through `core.scoring_batch` with `verified = true`, one job, none failed,
`include_per_sample = true`, never sharded.

## Files

| file | what it is |
|---|---|
| `smoke-4/flight-receipt.json`, `flight-1500/flight-receipt.json` | the launcher's own receipts: every stage, its hash, the serve attach, the seal and the score |
| `smoke-4/falsifier.json`, `flight-1500/falsifier.json` | the §4.1 `prompt_tokens` check, recomputed row by row from the sealed trace |
| `smoke-4/score.json`, `flight-1500/score.json` | the `core.scoring_batch` result over the complete sealed manifest, `verified: true`, per-sample rows included |
| `flight-1500/flight-read.json` | this cell's own corpus, per-call, per-duration, category and boundary tables — no pairing, no verdict |
