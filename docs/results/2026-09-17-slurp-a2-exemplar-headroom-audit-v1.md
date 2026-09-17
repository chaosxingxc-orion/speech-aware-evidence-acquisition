# SLURP A2: exemplar-retrieval headroom with the sealed speech keys

Date: 2026-09-17. Root: Fable 5.1. Program: `docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md`
(Phase A, item A2; decides cell B1). Zero model, tokenizer, encoder, ASR, scorer or server contacts;
repository tree untouched; no utterance text or gold filler persisted (filler matching used
SHA-1 digests of normalised pairs).

Machine result: `analysis/SAEA-SLURP-A2-EXEMPLAR-HEADROOM-AUDIT-V1/result.json` under
`SPEECHRL_DATA_DIR`, SHA-256 51b1315a11a5010e90475eb7408eb4fedc10fdb99775bffb32da7cc85655839d,
with `README.md`, `prep.py`, `candidates.py`, `metrics.py` and the three run scripts beside it.

## Inputs and validation

- Query keys: TRAIN A sealed speech vectors
  `vectors/slurp-intent-boundaries-train-fold-a-1080-v1/query-vectors-speech-segments.jsonl`
  (Omni-Embed-Nemotron-3B, prompt `query: `, 2,048-d, masked mean pooling, L2; the file's
  `intent-boundary` dimension is an alias of the `content` dimension, the same space as the KU-S3
  facet side); DEV1000 `vectors/slurp-kus3/query-vectors-speech.jsonl` (99b2e170…).
- Key side: `vectors/slurp-kus3/facet-vectors.jsonl` (5dfe7523…), one text vector per governed
  TRAIN utterance (prompt `passage: `).
- Pool: 9,354 utterances / 60 intents / 54 entity types / 37,407 recordings after excluding every
  utterance with a recording in TRAIN Fold A, Fold B or DEV-1000 (equal to the 2026-09-13
  authoring registration's expected pool on all four counts). DEV1000 is reported with and
  without the fold exclusion; the exclusion costs 0.5-1.0 pp union coverage and about 2.6 pp
  filler recall.
- Self-checks: re-derived first-Perception candidates agree with the sealed diagnostics on
  1,080 / 1,080 rows (coverage 937 / 1,080); the delivered-intent derivation reproduces
  `final_correct` on 1,080 / 1,080 and DEV1000 intent 0.756; DEV1000 sealed coverage 831 / 1,000.
- Cross-modal top-1 cosine: TRAIN A mean 0.370 (0.058-0.567), DEV1000 mean 0.381, the same regime
  the KU-S3 configuration measured (0.3975 on 20 rows).

## TRAIN A (1,080 rows; sealed candidate coverage 0.8676)

| Variant | Exemplars / row | Union coverage | Union top-2 | Union top-3 | Gold intent among neighbours | Type recall | Filler recall | Same-intent type recall | Echo | Mean chars | p95 chars |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| sealed candidates only | 0 | 0.8676 | -- | -- | -- | -- | -- | -- | -- | 0 | 0 |
| plain k=5 | 5.0 | 0.9472 | 0.9324 | 0.9444 | 0.8972 | 0.906 | 0.438 | 0.818 | 0.723 | 490 | 741 |
| plain k=8 | 8.0 | 0.9574 | 0.9324 | 0.9472 | 0.9269 | 0.933 | 0.487 | 0.863 | 0.722 | 773 | 1,145 |
| plain k=12 | 12.0 | 0.9630 | 0.9333 | 0.9481 | 0.9407 | 0.947 | 0.525 | 0.888 | 0.730 | 1,145 | 1,679 |
| plain k=20 | 20.0 | 0.9722 | 0.9343 | 0.9500 | 0.9565 | 0.960 | 0.566 | 0.907 | 0.729 | 1,876 | 2,715 |
| grouped c=1, l=5, k=12 | 2.68 | 0.9574 | 0.9333 | 0.9481 | 0.9324 | 0.817 | 0.324 | 0.709 | 0.688 | 267 | 547 |
| grouped c=1, l=5, k=20 | 3.20 | 0.9620 | 0.9343 | 0.9500 | 0.9398 | 0.834 | 0.338 | 0.709 | 0.688 | 319 | 579 |
| grouped c=2, l=5, k=20 | 5.33 | 0.9620 | 0.9343 | 0.9500 | 0.9398 | 0.903 | 0.414 | 0.811 | 0.704 | 523 | 926 |

Ceiling at k=40: gold intent 0.9731, type recall 0.970, filler recall 0.596. Of the 143 sealed
misses, 86 are recovered by neighbour intents at k=5 and 113 (79.0 %) at k=20. Exact-text
neighbour rate: 0.0000 at k=5 and 8, 0.0009 at k=12, 0.0019 at k=20; metrics on the complement
subset are identical to three decimals, so there is no memorisation channel.

Echo is informative rather than parroting: the neighbour-intent plurality equals the delivered
intent on 0.867 of rows where the delivered answer was right and 0.225 where it was wrong
(DEV1000: 0.806 / 0.205). The exemplar signal disagrees with the model where the model fails.

## DEV1000 (1,000 rows; sealed coverage 0.831; full-pool variant in brackets)

| Variant | Union coverage | Gold intent among neighbours | Type recall | Filler recall | Same-intent type recall | Echo | Mean chars |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| plain k=5 | 0.913 [0.922] | 0.822 [0.838] | 0.827 [0.836] | 0.405 [0.419] | 0.729 | 0.660 | 475 |
| plain k=8 | 0.929 [0.936] | 0.856 [0.871] | 0.873 [0.878] | 0.440 [0.468] | 0.787 | 0.660 | 749 |
| plain k=12 | 0.935 [0.943] | 0.879 [0.887] | 0.895 [0.902] | 0.483 [0.502] | 0.821 | 0.662 | 1,110 |
| plain k=20 | 0.948 [0.953] | 0.905 [0.912] | 0.926 [0.923] | 0.509 [0.535] | 0.857 | 0.661 | 1,811 |
| grouped c=1, l=5, k=20 | 0.934 [0.942] | 0.878 [0.893] | 0.755 | 0.293 | 0.625 | 0.628 | 320 |

## Per scenario, plain k=20 on TRAIN A

| Scenario | Sealed coverage | Union coverage | Filler recall | Type recall |
| --- | ---: | ---: | ---: | ---: |
| general | 0.433 | 0.917 | 0.600 | 0.950 |
| calendar | 0.817 | 0.983 | 0.583 | 0.977 |
| social | 0.817 | 0.933 | 0.667 | 0.959 |
| qa | 0.783 | 0.983 | 0.500 | 1.000 |
| news | 0.833 | 0.967 | 0.492 | 0.900 |
| email | 0.883 | 0.950 | 0.577 | 0.932 |
| lists | 0.850 | 0.950 | 0.519 | 0.923 |
| music | 0.867 | 0.950 | 0.594 | 0.812 |
| audio | 0.917 | 0.967 | 0.200 | 1.000 |
| cooking | 0.917 | 0.983 | 0.265 | 0.924 |
| play | 0.883 | 1.000 | 0.359 | 0.989 |
| alarm, iot, datetime, recommendation, takeaway, transport, weather | 0.917-0.967 | 0.967-1.000 | 0.604-0.756 | 0.927-1.000 |

The `general` hole closes at the availability level: sealed 0.433 (DEV1000 0.230) to union 0.917
(DEV1000 0.869).

## Decision

- Cell B1 flies with the sealed speech vector as the key and plain top-k exemplars, k = 20
  (mean 1,876 characters, about 470 tokens by the chars/4 proxy; p95 2,715, max 3,273); the
  downgrade condition is not met at any k. If the registered per-row supply budget must stay
  under 600 tokens, k = 12 is the fallback registration (mean 1,145, max 2,081; union 0.963,
  filler 0.525). The E3 prompt-fit receipt on the flight tokenizer is the authority for the
  final k.
- Intent diversification buys coverage per character, not coverage: grouped variants never beat
  plain at equal exemplar count, and almost the whole coverage lift sits in the top 2-3 distinct
  neighbour intents (union top-2 0.934, top-3 0.950).
- Correction to the spec's E3 line: `saea-fuse-associated-values-v1` groups per facet, not per
  intent; with one exemplar card per utterance it equals plain top-`top_l` (3,240 / 3,240 rows
  checked) and diversifies nothing. B1 uses plain top-k; any later intent-diversified variant needs
  a target-grouped policy.
- Convention transfer, not coverage, is M1's weak axis (filler recall saturates near 0.60;
  `audio`, `cooking`, `play` weakest), which is what cells B2 (aggregation) and B4b (contract
  revision) address.
- Union coverage is availability, not use: whether the Solver escapes to a neighbour intent is a
  B1 outcome to be reported (candidate union as a deterministic supplement stays a follow-up
  cell, B1b, if escapes are rare).
