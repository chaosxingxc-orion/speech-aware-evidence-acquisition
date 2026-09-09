# KU-S4 family preparation -- receipt (2026-09-09)

Row `SAEA-SLURP-MF-KU-S4-PREP-V1`, profile `model-free-check`. Producer:
`scripts/slurp_kus4_prep.py`. Preregistration:
`docs/readiness/2026-09-09-slurp-intent-ku-s4-family-v1-preregistration.md`.

**Zero frozen-core, tokenizer, embedder, retriever, network, GPU, audio-decode and
paid-API contacts.** `CUDA_VISIBLE_DEVICES` empty throughout. No devel `sentence`
string is read anywhere; DEV gold labels enter only to REPORT whether a gold-free
candidate set contains the gold. The held-out `test` split is never named, loaded,
hashed or scored. Audio container headers only -- no sample is decoded.

Every token figure is MF-10's STATED PROXY (whitespace tokens x 1.3, rounded up) or
the source-read encoder rate (13 tokens per whole second, `tools/mtmd/clip.cpp`
PROJECTOR_TYPE_QWEN3A). No tokenizer was called.

## Identity anchors, re-derived rather than quoted

The pass RAISES rather than reports if one stops reproducing.

| anchor | value |
|---|---:|
| `comparator_intent_new500` | **75.2** |
| `comparator_intent_old500` | **71.0** |
| `comparator_intent_pooled_1000` | **73.1** |
| `gold_in_candidate_set_all_rows_pct` | **95.8** |
| `gold_in_candidate_set_error_rows_pct` | **86.62** |
| `legality_judge_rows_flagged` | **42.0** |
| `rows_fully_covered_by_own_speaker` | **658.0** |
| `rows_fully_covered_by_own_speaker_new500` | **341.0** |
| `same_speaker_slot_coverage_macro_pct` | **92.14** |

## The candidate view

| quantity | value |
|---|---:|
| k (a CAP) | 8 |
| realized candidates per row, mean | **5.94** |
| rows offered the full k | 417 of 1,000 |
| realized narrowing ratio, mean | **9.89 %** |
| gold in the set, all rows | **95.8** |
| gold in the set, error rows | **86.62** |
| gold in the set, NEW500 | 95.4 |
| gold in the TWIN's set, all rows | **0.6** |
| the arm's own prediction is offered | 983 of 1,000 |
| reachable ceiling, intent | **96.4** |

### Neighbour depth: the registered depth is the better arm

| depth | mean candidates | rows at the full k | gold, all rows | gold, ERROR rows | narrowing |
|---|---:|---:|---:|---:|---:|
| 50 (registered) | 5.94 | 417 | 95.8 | **86.62** | 9.89 % |
| 100 | 6.93 | 647 | 95.9 | **86.62** | 11.55 % |
| 200 | 7.76 | 872 | 95.9 | **86.62** | 12.94 % |
| 400 | 8.0 | 998 | 95.9 | **86.62** | 13.33 % |

Eight times the neighbour list buys +0.10 pp on all rows and **zero** on the rows the
core gets wrong, at a third more of the label space handed back to the core.

## Containment, the legality judge and the exemplar plan

| quantity | value |
|---|---:|
| protected payloads | 120 |
| C1, control turn hits | **0** |
| C2, system message hits | **0** |
| system message sha256 | `4073f79ef25c4796...` |
| judge rows flagged | **42 of 1000** |
| ... still wrong after the projection | 25 |
| candidate slots offered | **5937** |
| slots the row's own speaker fills | 5442 (92.14 % per row) |
| uncovered slots (the counted fallback) | **495 (8.34 %)** |
| rows fully covered | **658** (341 in NEW500) |
| distinct same-speaker exemplar recordings | 2742 |
| distinct other-speaker exemplar recordings | 5082 |
| KU-S4a metered speech, one pass | **18103.4014 s** |
| KU-S4b metered speech, one pass | **18637.4157 s** |
| KU-S4c metered speech, one pass | 2884.7937 s |

## Prompt fit, projected against the sealed geometry

`-c 65536 -np 8`, 8192-token slots.

| arm | mean | worst | headroom | fits |
|---|---:|---:|---:|---|
| KU-S4N / KU-S4N-t | 2354.6 | 2517.0 | 3.48x | yes |
| KU-S4a | 2587.7 | 3089.0 | 3.17x | yes |
| KU-S4b | 2594.3 | 2985.0 | 3.16x | yes |
| KU-S4c | 2400.6 | 2563.0 | 3.41x | yes |

## The packet precondition -- KU-S4a and KU-S4b are BLOCKED

| plan | recordings | already promoted | to promote |
|---|---:|---:|---:|
| KU-S4a (same speaker) | 2742 | **162** (5.91 %) | **2580** |
| KU-S4b (other speaker) | 5082 | **291** (5.73 %) | **4791** |

BLOCKED: KU-S4a and KU-S4b cannot fly until their exemplar recordings are promoted to encoder packets under the comparator's own feature root and build commit. The promotion is a preprocessing session with its own receipt and its own exposure row -- ZERO frozen-core contacts -- and it is a PRECONDITION of those two cells, preregistered as such.

Promotion cost: **7371 recordings**, about **30971.23 audio seconds** to encode, **0 frozen-core contacts**. GPU hours are NOT pinned here: they belong to the
packet-build receipt, which this pass does not own.

## Files

* `kus4-prep.json` -- every number above, with its own boundary block.
* `exemplar-plan-rows.json` -- one summary row per DEV-1000 sample (slots offered,
  slots filled, whether the gold intent's slot is filled). The per-slot table is not
  committed: it is a pure function of the producer, the governed TRAIN metadata and
  the sha256-pinned candidate bank.
* `exemplar-recordings.json` -- the exact TRAIN recordings the KU-S4a and KU-S4b plans
  name, and which of them are already promoted. This is the packet-promotion row's
  own input.

Nothing here is a task measurement, an admission, a promotion or a verdict.
