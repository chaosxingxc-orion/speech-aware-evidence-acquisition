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

## `flight-1500/` — the cell itself

Attempt `attempt-20260907T090708Z-df36cc`, COMPLETED and FINALIZED on study commit `ab7e6ddb`,
**1,500 of 1,500 contacts**, one attempt, none aborted, **no recovery re-registration used**,
`study_repo_dirt` empty. Config hash `17358fc3`, protocol hash `0fd0d434`, split identity
`8dc9d6a0` — the three the zero-contact wire check had already computed for this cell, unchanged.
Manifest SHA-256 `59c4fbcd…`, outputs `26123a94…`, trace `969a36b0…`, sealed scores `f44b33d2…`.

### The falsifier, run before any score was read

**§4.1 HOLDS ON 1,500 OF 1,500 ROWS.** Measured `prompt_tokens` total **251,782** against the
predicted **251,782** — exactly the `49 × 1,500 + 178,282` the preregistration published before the
cell existed — with **zero** disagreeing rows. The predicted audio-token count is recomputed from
each clip's own `n_samples` through `analysis.e22_short_clip_encoding.llamacpp_audio_tokens`, and
the roster receipt's `audio_tokens` column agrees on every one of the 1,500 rows as well. The
sealed `cost` block's own `prompt_tokens_total` is the same 251,782. The audit's front-end model is
therefore the server's on this media too — and it holds on media two seconds longer than the bytes
the audit was built from.

### What the cell measured, on its own 1,500 rows

**No pairing and no verdict below.** These are this arm's own numbers; the paired contrast against
the sealed comparator, its call-stratified CI90 and the three-clause rule of §4 belong to a later
document.

| | value |
|---|---:|
| corpus WER, Whisper `EnglishTextNormalizer` (paper-facing) | **9.4054 %** |
| corpus WER, frozen `saea-scoring-v1` normalizer | 14.7640 % |
| mean per-utterance WER (Whisper / `saea-scoring-v1`) | 15.4208 % / 19.8547 % |
| equal-call weighting (Whisper / `saea-scoring-v1`) | 9.5453 % / 14.9140 % |
| substitutions / deletions / insertions (Whisper) | 1,041 / 763 / 665 |
| reference words (Whisper / `saea-scoring-v1`) | 26,251 / 26,822 |
| insertion share of errors (Whisper) | 26.93 % |
| hypothesis-to-reference length ratio | 0.9963 |
| agentic error rate (`analysis.e22_error_taxonomy`, HIGH-impact reference-word mass) | **1.7599 %** (462 of 26,251 words over 315 spans) |
| boundary category mass (`segmentation-artifact` + `runaway-tail` + `runaway-head`) | **1.1085 WER points** (228 + 22 + 41 = 291 operations) |

The taxonomy's own alignment reproduces the paper-facing scorer exactly — 1,041 / 763 / 665 over
26,251 reference words, corpus WER 9.4054 either way, recorded as the `taxonomy_identity_gate`
block of `flight-1500/flight-read.json` — so the category split below is a decomposition of the
same number, not a second measurement of it.

**Per call, corpus WER under both normalizers** (natural mixture; the equal-call means are in the
table above):

| call | reference words | Whisper | `saea-scoring-v1` |
|---|---:|---:|---:|
| `4453225` | 2,662 | 10.7438 | 16.0176 |
| `4469088` | 1,946 | 9.6095 | 12.6189 |
| `4470684` | 2,581 | 5.7342 | 14.3530 |
| `4474506` | 2,993 | 7.5175 | 12.7171 |
| `4479944` | 2,773 | 16.3000 | 22.6517 |
| `4481952` | 2,166 | 8.6334 | 14.0492 |
| `4482383` | 3,015 | 8.1260 | 12.7418 |
| `4482613` | 2,386 | 16.6387 | 23.6703 |
| `4483937` | 2,567 | 7.0900 | 12.5278 |
| `4485192` | 3,162 | 5.0601 | 7.7930 |

**By utterance duration** — the slice the encoding audit predicts the effect concentrates in. The
buckets are the published segment's own duration, not the variant's, so the rows are the same rows
in every cell:

| bucket | utterances | reference words | corpus WER | of which `segmentation-artifact` | of which `model-behaviour` |
|---|---:|---:|---:|---:|---:|
| 0–1 s | 116 | 277 | 48.7365 | 3.2491 | 20.5776 |
| 1–2 s | 109 | 537 | 23.4637 | 3.3520 | 2.6071 |
| 2–4 s | 291 | 2,656 | 14.3072 | 2.3720 | 0.4518 |
| 4–8 s | 488 | 7,657 | 9.4815 | 0.9011 | 1.1101 |
| 8–16 s | 425 | 11,695 | 7.5673 | 0.4788 | 0.3762 |
| 16 s+ | 71 | 3,429 | 6.3284 | 0.3791 | 0.1167 |

**Category mass** (spans, error mass, WER points):

| category | spans | error mass | WER points |
|---|---:|---:|---:|
| `other` | 780 | 989 | 3.7675 |
| `acoustic-misrecognition` | 265 | 339 | 1.2914 |
| `named-entity` | 211 | 282 | 1.0742 |
| `reference-convention` | 207 | 241 | 0.9181 |
| `segmentation-artifact` | 170 | 228 | 0.8685 |
| `model-behaviour` | 65 | 216 | 0.8228 |
| `format-convention` | 104 | 120 | 0.4571 |
| `domain-term` | 37 | 54 | 0.2057 |

**Boundary containment.** 39 tail insertion spans carrying 75 words, of which 20 spans (26 words)
are 60 % or more contained in the *next* published utterance's reference; 135 head spans carrying
227 words, of which 68 spans (106 words) are 60 % or more contained in the *previous* one. The full
buckets are in `flight-1500/flight-read.json`.

### Serving and cost

1,500 contacts in **427.571 s** wall at **3.5082 contacts/s** and **2.0538 s** mean latency, slot
occupancy 0.901 on eight slots — **0.1188 GPU-hours** against the 0.50 registered ceiling. Realized
spend 1,500 of 1,600 registered calls and 12,948.983 of 13,500 registered speech-audio seconds;
zero paid API. Monitor summary for the attempt's own contact window: 39 samples over 415.933 s,
**parked 0.0 s, active 415.933 s, parked fraction 0.000**, `requests_delta` 304 (a lower bound at
the 10-second sampling interval, not the throughput figure), mean power **86.985 W**, peak
**89.85 W**, mean GPU utilization **81.69 %**.

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
